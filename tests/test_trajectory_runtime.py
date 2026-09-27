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

    result = runtime.observe(
        knowledge_cutoff=BASE + timedelta(days=200),
        current_block_ids=(blocks[-1].block_id,),
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
