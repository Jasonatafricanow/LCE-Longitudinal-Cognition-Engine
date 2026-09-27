from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

from lce.cognition.line_graph import LineGraphStore
from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.structure.trajectory import (
    MutualKnnTrajectorySupplier,
    TrajectoryConfig,
    TrajectoryRuntime,
)
from lce.testing.reference_memory import InMemoryReferenceMemory

BASE = datetime(2020, 1, 1, tzinfo=UTC)


class _FixedNeighbourProvider:
    def __init__(self) -> None:
        self.calls = 0

    def candidates(
        self,
        blocks: tuple[SemanticBlock, ...],
        vectors: dict[str, tuple[float, ...]],
        *,
        k: int,
        min_similarity: float,
    ) -> dict[str, tuple[tuple[float, str], ...]]:
        del vectors, k, min_similarity
        self.calls += 1
        ids = [block.block_id for block in blocks]
        output: dict[str, tuple[tuple[float, str], ...]] = {}
        for index, block_id in enumerate(ids):
            neighbours: list[tuple[float, str]] = []
            if index > 0:
                neighbours.append((0.99, ids[index - 1]))
            if index + 1 < len(ids):
                neighbours.append((0.99, ids[index + 1]))
            output[block_id] = tuple(neighbours)
        return output


def _vector(degrees: float) -> tuple[float, float]:
    radians = math.radians(degrees)
    return (math.cos(radians), math.sin(radians))


def _admit(
    memory: InMemoryReferenceMemory,
    *,
    index: int,
    day: int,
    vector: tuple[float, ...],
) -> SemanticBlock:
    evidence_id = f"E{index}"
    block_id = f"B{index}"
    when = BASE + timedelta(days=day)
    memory.add_evidence(
        RawEvidence(
            evidence_id=evidence_id,
            content=block_id,
            occurred_at=when,
            known_at=when,
            provenance={"source": "test", "canonical": True},
        )
    )
    return memory.put_semantic_block(
        SemanticBlock(
            block_id=block_id,
            content=block_id,
            raw_evidence_ids=(evidence_id,),
            occurred_start=when,
            occurred_end=when,
            compiler_version="test",
            lineage_id="main",
            metadata={"vector": vector},
        )
    )


def _rebuild(memory: InMemoryReferenceMemory) -> None:
    memory.rebuild_vector_index(
        lambda block: tuple(float(value) for value in block.metadata["vector"]),
        index_version="test-v1",
    )


def test_local_continuity_recovers_drifting_line_without_endpoint_similarity() -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            index=index,
            day=index * 100,
            vector=_vector(index * 15.0),
        )
        for index in range(6)
    )
    _rebuild(memory)

    supplier = MutualKnnTrajectorySupplier(
        memory=memory,
        config=TrajectoryConfig(
            k=2,
            min_similarity=0.90,
            min_support=3,
        ),
    )
    paths = supplier.propose(blocks)

    full = next(
        path for path in paths if len(path.block_ids) == len(blocks)
    )
    assert full.block_ids == tuple(block.block_id for block in blocks)
    assert full.min_local_similarity > 0.96

    endpoint_similarity = sum(
        left * right
        for left, right in zip(
            blocks[0].metadata["vector"],
            blocks[-1].metadata["vector"],
            strict=True,
        )
    )
    assert endpoint_similarity < 0.30


def test_same_logical_time_points_are_not_forced_into_sequence() -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            index=index,
            day=0,
            vector=_vector(float(index)),
        )
        for index in range(4)
    )
    _rebuild(memory)

    supplier = MutualKnnTrajectorySupplier(
        memory=memory,
        config=TrajectoryConfig(
            k=3,
            min_similarity=0.90,
            min_support=3,
        ),
    )

    assert supplier.propose(blocks) == ()


def test_trajectory_runtime_materializes_one_stable_line_from_current_path(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            index=index,
            day=index * 30,
            vector=_vector(index * 10.0),
        )
        for index in range(6)
    )
    _rebuild(memory)

    line_store = LineGraphStore(tmp_path / "lines")
    runtime = TrajectoryRuntime(
        memory=memory,
        line_store=line_store,
        trajectory_config=TrajectoryConfig(
            k=2,
            min_similarity=0.95,
            min_support=3,
        ),
    )

    result = runtime.bootstrap(
        knowledge_cutoff=BASE + timedelta(days=200),
    )

    assert result.candidate_paths
    assert any(update.created_line for update in result.line_updates)
    assert len(line_store.list_lines()) == 1
    line = line_store.list_lines()[0]
    assert {
        node.block_id for node in line_store.nodes_for_line(line.line_id)
    } == {block.block_id for block in blocks}


def test_trajectory_runtime_does_not_emit_unrelated_historical_path(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    history = tuple(
        _admit(
            memory,
            index=index,
            day=index * 30,
            vector=_vector(index * 10.0),
        )
        for index in range(5)
    )
    current = _admit(
        memory,
        index=99,
        day=200,
        vector=(-1.0, 0.0),
    )
    _rebuild(memory)

    runtime = TrajectoryRuntime(
        memory=memory,
        line_store=LineGraphStore(tmp_path / "lines"),
        trajectory_config=TrajectoryConfig(
            k=2,
            min_similarity=0.95,
            min_support=3,
        ),
    )
    result = runtime.observe(
        knowledge_cutoff=BASE + timedelta(days=250),
        current_block_ids=(current.block_id,),
    )

    assert history
    assert result.candidate_paths == ()
    assert result.line_updates == ()


def test_nearline_observe_extends_existing_line_without_full_bootstrap(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    history = tuple(
        _admit(
            memory,
            index=index,
            day=index * 30,
            vector=_vector(index * 8.0),
        )
        for index in range(5)
    )
    _rebuild(memory)

    line_store = LineGraphStore(tmp_path / "lines")
    runtime = TrajectoryRuntime(
        memory=memory,
        line_store=line_store,
        trajectory_config=TrajectoryConfig(
            k=2,
            min_similarity=0.95,
            min_support=3,
        ),
    )
    bootstrap = runtime.bootstrap(
        knowledge_cutoff=BASE + timedelta(days=150),
    )
    assert bootstrap.candidate_paths
    assert len(line_store.list_lines()) == 1
    line_id = line_store.list_lines()[0].line_id
    before = {
        node.block_id for node in line_store.nodes_for_line(line_id)
    }
    assert before == {block.block_id for block in history}

    current = _admit(
        memory,
        index=99,
        day=180,
        vector=_vector(5 * 8.0),
    )
    _rebuild(memory)
    result = runtime.observe(
        knowledge_cutoff=BASE + timedelta(days=200),
        current_block_ids=(current.block_id,),
    )

    assert result.candidate_paths == ()
    assert len(result.line_updates) == 1
    assert result.line_updates[0].line_id == line_id
    assert {
        node.block_id for node in line_store.nodes_for_line(line_id)
    } == {*before, current.block_id}


def test_nearline_observe_does_not_seed_line_from_point_cloud(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            index=index,
            day=index * 30,
            vector=_vector(index * 8.0),
        )
        for index in range(5)
    )
    _rebuild(memory)
    line_store = LineGraphStore(tmp_path / "lines")
    runtime = TrajectoryRuntime(
        memory=memory,
        line_store=line_store,
        trajectory_config=TrajectoryConfig(
            k=2,
            min_similarity=0.95,
            min_support=3,
        ),
    )

    result = runtime.observe(
        knowledge_cutoff=BASE + timedelta(days=150),
        current_block_ids=(blocks[-1].block_id,),
    )

    assert result.candidate_paths == ()
    assert result.line_updates == ()
    assert line_store.list_lines() == ()


def test_nearline_state_revision_updates_existing_line_membership(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            index=index,
            day=index * 30,
            vector=_vector(index * 8.0),
        )
        for index in range(5)
    )
    _rebuild(memory)
    store = LineGraphStore(tmp_path / "lines")
    runtime = TrajectoryRuntime(
        memory=memory,
        line_store=store,
        trajectory_config=TrajectoryConfig(
            k=2,
            min_similarity=0.95,
            min_support=3,
        ),
    )
    runtime.bootstrap(
        knowledge_cutoff=BASE + timedelta(days=150),
    )
    line_id = store.list_lines()[0].line_id
    target = blocks[2]
    node = store.node_for_block(line_id, target.block_id)
    assert node is not None
    assert len(store.states_for_node(node.node_id)) == 1

    memory.add_evidence(
        RawEvidence(
            evidence_id="REV",
            content="later revision",
            occurred_at=BASE + timedelta(days=70),
            known_at=BASE + timedelta(days=200),
            provenance={"source": "test", "canonical": True},
        )
    )
    revised = memory.extend_semantic_block(
        target.block_id,
        content="later revision",
        evidence_id="REV",
        occurred_at=BASE + timedelta(days=70),
    )
    _rebuild(memory)

    result = runtime.observe(
        knowledge_cutoff=BASE + timedelta(days=210),
        current_block_ids=(target.block_id,),
    )

    assert len(result.line_updates) == 1
    assert result.line_updates[0].line_id == line_id
    assert len(store.list_lines()) == 1
    assert len(store.states_for_node(node.node_id)) == 2
    assert revised.state_id in {
        state.state_id for state in store.states_for_node(node.node_id)
    }


def test_bootstrap_neighbour_candidate_source_is_replaceable() -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            index=index,
            day=index * 30,
            vector=_vector(index * 20.0),
        )
        for index in range(4)
    )
    _rebuild(memory)
    provider = _FixedNeighbourProvider()
    supplier = MutualKnnTrajectorySupplier(
        memory=memory,
        config=TrajectoryConfig(
            k=2,
            min_similarity=0.95,
            min_support=3,
        ),
        neighbour_provider=provider,
    )

    paths = supplier.propose(blocks)

    assert provider.calls == 1
    assert any(
        path.block_ids == tuple(block.block_id for block in blocks)
        for path in paths
    )



def test_long_bootstrap_path_is_segmented_without_losing_tail(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            index=index,
            day=index * 10,
            vector=_vector(index * 4.0),
        )
        for index in range(10)
    )
    _rebuild(memory)

    store = LineGraphStore(tmp_path / "lines")
    runtime = TrajectoryRuntime(
        memory=memory,
        line_store=store,
        trajectory_config=TrajectoryConfig(
            k=2,
            min_similarity=0.99,
            min_support=3,
            max_path_length=4,
            max_paths=32,
        ),
    )

    result = runtime.bootstrap(
        knowledge_cutoff=BASE + timedelta(days=200),
    )

    assert result.candidate_paths
    covered = {
        block_id
        for path in result.candidate_paths
        for block_id in path.block_ids
    }
    assert covered == {block.block_id for block in blocks}
    assert len(store.list_lines()) == 1
    line_id = store.list_lines()[0].line_id
    assert {
        node.block_id for node in store.nodes_for_line(line_id)
    } == covered



def test_deep_trajectory_segmentation_does_not_depend_on_python_recursion() -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        SemanticBlock(
            block_id=f"deep-{index}",
            content=f"deep-{index}",
            raw_evidence_ids=(f"raw-{index}",),
            occurred_start=BASE + timedelta(days=index),
            occurred_end=BASE + timedelta(days=index),
            compiler_version="test",
            lineage_id="deep",
            state_id=f"state-deep-{index}",
        )
        for index in range(1500)
    )
    outgoing = {
        block.block_id: (
            (blocks[index + 1].block_id,)
            if index + 1 < len(blocks)
            else ()
        )
        for index, block in enumerate(blocks)
    }
    edge_scores = {
        (blocks[index].block_id, blocks[index + 1].block_id): 0.99
        for index in range(len(blocks) - 1)
    }
    supplier = MutualKnnTrajectorySupplier(
        memory=memory,
        config=TrajectoryConfig(
            min_support=3,
            max_path_length=16,
            max_paths=128,
        ),
    )

    paths = supplier._paths(blocks, outgoing, edge_scores)

    covered = {
        block_id
        for path in paths
        for block_id in path.block_ids
    }
    assert blocks[0].block_id in covered
    assert blocks[-1].block_id in covered
