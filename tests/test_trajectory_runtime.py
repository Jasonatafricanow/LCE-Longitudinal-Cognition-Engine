from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

from lce.cognition.line_graph import LineGraphStore, LineGraphView
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



def test_logical_time_revision_rebuilds_current_line_without_rewriting_history(
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
        for index in range(4)
    )
    _rebuild(memory)
    store = LineGraphStore(tmp_path / "lines")
    runtime = TrajectoryRuntime(
        memory=memory,
        line_store=store,
        trajectory_config=TrajectoryConfig(
            k=2,
            min_similarity=0.0,
            min_support=3,
        ),
        neighbour_provider=_FixedNeighbourProvider(),
    )
    historical_cutoff = BASE + timedelta(days=35)
    seeded = runtime.bootstrap(
        knowledge_cutoff=historical_cutoff,
    )
    assert seeded.candidate_paths
    assert len(store.list_lines()) == 1
    line_id = store.list_lines()[0].line_id
    historical_visible = set(
        LineGraphView(memory=memory, store=store).visible_node_ids(
            line_id,
            knowledge_cutoff=historical_cutoff,
        )
    )
    assert len(historical_visible) == 4

    memory.add_evidence(
        RawEvidence(
            evidence_id="E-revision",
            content="retroactive interval extension",
            occurred_at=BASE + timedelta(days=35),
            known_at=BASE + timedelta(days=40),
            provenance={"source": "test", "canonical": True},
        )
    )
    revised = memory.extend_semantic_block(
        blocks[1].block_id,
        content="retroactive interval extension",
        evidence_id="E-revision",
        occurred_at=BASE + timedelta(days=35),
    )
    _rebuild(memory)

    current_cutoff = BASE + timedelta(days=100)
    result = runtime.observe(
        knowledge_cutoff=current_cutoff,
        current_block_ids=(revised.block_id,),
    )

    # The revised B1 no longer supports its old incident relations. Only that
    # membership/edge neighbourhood is retired; unrelated compiled structure
    # remains directly reusable.
    assert result.candidate_paths == ()
    current_visible = set(
        LineGraphView(memory=memory, store=store).visible_node_ids(
            line_id,
            knowledge_cutoff=current_cutoff,
        )
    )
    revised_node = store.node_for_block(line_id, revised.block_id)
    assert revised_node is not None
    assert revised_node.node_id not in current_visible
    assert len(current_visible) == 3

    # Earlier epistemic replay still sees the graph that existed before the
    # later state revision was known.
    assert set(
        LineGraphView(memory=memory, store=store).visible_node_ids(
            line_id,
            knowledge_cutoff=historical_cutoff,
        )
    ) == historical_visible



def test_material_semantic_state_drift_rebuilds_line_even_when_time_is_unchanged(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            index=index,
            day=index * 10,
            vector=(1.0, 0.0),
        )
        for index in range(3)
    )

    def embed(block: SemanticBlock) -> tuple[float, float]:
        return (
            (0.0, 1.0)
            if "semantic-drift" in block.content
            else (1.0, 0.0)
        )

    memory.rebuild_vector_index(
        embed,
        index_version="semantic-drift-v1",
    )
    store = LineGraphStore(tmp_path / "lines")
    runtime = TrajectoryRuntime(
        memory=memory,
        line_store=store,
        trajectory_config=TrajectoryConfig(
            k=2,
            min_similarity=0.8,
            min_support=3,
        ),
    )
    historical_cutoff = BASE + timedelta(days=30)
    seeded = runtime.bootstrap(
        knowledge_cutoff=historical_cutoff,
    )
    assert seeded.candidate_paths
    assert len(store.list_lines()) == 1
    line_id = store.list_lines()[0].line_id

    middle = blocks[1]
    memory.add_evidence(
        RawEvidence(
            evidence_id="semantic-drift-evidence",
            content="semantic-drift",
            occurred_at=middle.occurred_start,
            known_at=BASE + timedelta(days=40),
            provenance={"source": "test", "canonical": True},
        )
    )
    revised = memory.extend_semantic_block(
        middle.block_id,
        content="semantic-drift",
        evidence_id="semantic-drift-evidence",
        occurred_at=middle.occurred_start,
    )
    memory.rebuild_vector_index(
        embed,
        index_version="semantic-drift-v1",
    )

    current_cutoff = BASE + timedelta(days=100)
    result = runtime.observe(
        knowledge_cutoff=current_cutoff,
        current_block_ids=(revised.block_id,),
    )

    # The revised state moved outside local continuity. The changed
    # membership is retired locally; the unaffected endpoints remain usable.
    assert result.candidate_paths == ()
    current_visible = set(
        LineGraphView(
            memory=memory,
            store=store,
        ).visible_node_ids(
            line_id,
            knowledge_cutoff=current_cutoff,
        )
    )
    middle_node = store.node_for_block(line_id, revised.block_id)
    assert middle_node is not None
    assert middle_node.node_id not in current_visible
    assert len(current_visible) == 2

    assert len(
        LineGraphView(
            memory=memory,
            store=store,
        ).visible_node_ids(
            line_id,
            knowledge_cutoff=historical_cutoff,
        )
    ) == 3



def test_state_revision_revalidates_incident_edges_not_only_self_similarity(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    initial_degrees = (0.0, 30.0, 60.0)
    blocks = tuple(
        _admit(
            memory,
            index=200 + index,
            day=index * 10,
            vector=_vector(degrees),
        )
        for index, degrees in enumerate(initial_degrees)
    )

    def embed(block: SemanticBlock) -> tuple[float, float]:
        if "edge-drift" in block.content:
            return _vector(5.0)
        raw = block.metadata["vector"]
        assert isinstance(raw, tuple)
        assert len(raw) == 2
        return (float(raw[0]), float(raw[1]))

    memory.rebuild_vector_index(
        embed,
        index_version="edge-revalidation-v1",
    )
    store = LineGraphStore(tmp_path / "lines")
    runtime = TrajectoryRuntime(
        memory=memory,
        line_store=store,
        trajectory_config=TrajectoryConfig(
            k=2,
            min_similarity=0.8,
            min_support=3,
        ),
    )
    historical_cutoff = BASE + timedelta(days=30)
    seeded = runtime.bootstrap(
        knowledge_cutoff=historical_cutoff,
    )
    assert seeded.candidate_paths
    line_id = store.list_lines()[0].line_id

    middle = blocks[1]
    memory.add_evidence(
        RawEvidence(
            evidence_id="edge-drift-evidence",
            content="edge-drift",
            occurred_at=middle.occurred_start,
            known_at=BASE + timedelta(days=40),
            provenance={"source": "test", "canonical": True},
        )
    )
    revised = memory.extend_semantic_block(
        middle.block_id,
        content="edge-drift",
        evidence_id="edge-drift-evidence",
        occurred_at=middle.occurred_start,
    )
    memory.rebuild_vector_index(
        embed,
        index_version="edge-revalidation-v1",
    )

    previous_vector = memory.get_vector(
        middle.block_id,
        state_id=middle.state_id,
    ).values
    current_vector = memory.get_vector(
        revised.block_id,
        state_id=revised.state_id,
    ).values
    assert math.isclose(
        sum(a * b for a, b in zip(previous_vector, current_vector)),
        math.cos(math.radians(25.0)),
        rel_tol=1e-6,
    )
    assert sum(
        a * b
        for a, b in zip(
            current_vector,
            memory.get_vector(
                blocks[2].block_id,
                state_id=blocks[2].state_id,
            ).values,
        )
    ) < 0.8

    current_cutoff = BASE + timedelta(days=100)
    result = runtime.observe(
        knowledge_cutoff=current_cutoff,
        current_block_ids=(revised.block_id,),
    )

    assert result.candidate_paths == ()
    current_visible = set(
        LineGraphView(
            memory=memory,
            store=store,
        ).visible_node_ids(
            line_id,
            knowledge_cutoff=current_cutoff,
        )
    )
    middle_node = store.node_for_block(line_id, revised.block_id)
    assert middle_node is not None
    assert middle_node.node_id not in current_visible
    assert len(current_visible) == 2

def test_state_revision_preserves_unrelated_nearline_growth_and_continues_batch(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            index=300 + index,
            day=index * 10,
            vector=(1.0, 0.0),
        )
        for index in range(3)
    )
    nearline = _admit(
        memory,
        index=310,
        day=30,
        vector=(1.0, 0.0),
    )
    later = _admit(
        memory,
        index=311,
        day=40,
        vector=(1.0, 0.0),
    )

    def embed(block: SemanticBlock) -> tuple[float, float]:
        if "local-drift" in block.content:
            return (0.0, 1.0)
        return (1.0, 0.0)

    memory.rebuild_vector_index(embed, index_version="local-revision-v1")
    store = LineGraphStore(tmp_path / "lines")
    runtime = TrajectoryRuntime(
        memory=memory,
        line_store=store,
        trajectory_config=TrajectoryConfig(
            min_similarity=0.8,
            min_support=3,
        ),
    )
    cutoff = BASE + timedelta(days=100)
    seeded = runtime.assembler.apply_path(
        blocks,
        knowledge_cutoff=cutoff,
    )
    assert seeded.line_id is not None
    line_id = seeded.line_id
    tail = store.node_for_block(line_id, blocks[-1].block_id)
    assert tail is not None
    runtime.assembler.attach_block(
        line_id,
        nearline,
        parent_node_ids=(tail.node_id,),
        knowledge_cutoff=cutoff,
    )

    middle = blocks[1]
    memory.add_evidence(
        RawEvidence(
            evidence_id="local-drift-evidence",
            content="local-drift",
            occurred_at=middle.occurred_start,
            known_at=BASE + timedelta(days=50),
            provenance={"source": "test", "canonical": True},
        )
    )
    revised = memory.extend_semantic_block(
        middle.block_id,
        content="local-drift",
        evidence_id="local-drift-evidence",
        occurred_at=middle.occurred_start,
    )
    memory.rebuild_vector_index(embed, index_version="local-revision-v1")

    result = runtime.observe(
        knowledge_cutoff=cutoff,
        current_block_ids=(revised.block_id, later.block_id),
    )

    nearline_node = store.node_for_block(line_id, nearline.block_id)
    later_node = store.node_for_block(line_id, later.block_id)
    revised_node = store.node_for_block(line_id, revised.block_id)
    assert nearline_node is not None
    assert later_node is not None
    assert revised_node is not None
    visible = set(
        LineGraphView(memory=memory, store=store).visible_node_ids(
            line_id,
            knowledge_cutoff=cutoff,
        )
    )
    assert nearline_node.node_id in visible
    assert later_node.node_id in visible
    assert revised_node.node_id not in visible
    assert later_node.node_id in {
        node.node_id
        for node in store.nodes_for_line(line_id)
    }
    assert any(update.line_id == line_id for update in result.line_updates)
