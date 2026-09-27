from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path

import pytest

from lce.cognition.line_graph import (
    LineAssembler,
    LineAssemblerConfig,
    LineGraphStore,
)
from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.structure.surface import (
    SurfaceConfig,
    SurfaceRuntime,
    SurfaceSearchLimitExceeded,
)
from lce.testing.reference_memory import InMemoryReferenceMemory

BASE = datetime(2020, 1, 1, tzinfo=UTC)

SHAPE = (
    (0.0, 0.0),
    (1.0, 0.2),
    (2.0, 1.0),
    (3.0, 2.4),
)

DISTRACTOR = (
    (0.0, 0.0),
    (0.2, 1.0),
    (1.0, 2.0),
    (2.5, 2.4),
)


def _densify(
    vertices: tuple[tuple[float, float], ...],
    subdivisions: int,
) -> tuple[tuple[float, float], ...]:
    output = [vertices[0]]
    for left, right in pairwise(vertices):
        for step in range(1, subdivisions + 1):
            ratio = step / subdivisions
            output.append(
                (
                    left[0] + (right[0] - left[0]) * ratio,
                    left[1] + (right[1] - left[1]) * ratio,
                )
            )
    return tuple(output)


def _add_line(
    memory: InMemoryReferenceMemory,
    store: LineGraphStore,
    *,
    prefix: str,
    anchor: tuple[float, float, float, float],
    states: tuple[tuple[float, float], ...],
) -> str:
    blocks = []
    for index, state in enumerate(states):
        evidence_id = f"{prefix}-E{index}"
        block_id = f"{prefix}-B{index}"
        when = BASE + timedelta(days=index * 30)
        vector = (*anchor, *state)
        memory.add_evidence(
            RawEvidence(
                evidence_id=evidence_id,
                content=block_id,
                occurred_at=when,
                known_at=when,
                provenance={"source": "test", "canonical": True},
            )
        )
        blocks.append(
            memory.put_semantic_block(
                SemanticBlock(
                    block_id=block_id,
                    content=block_id,
                    raw_evidence_ids=(evidence_id,),
                    occurred_start=when,
                    occurred_end=when,
                    compiler_version="test",
                    lineage_id=prefix,
                    metadata={"vector": vector},
                )
            )
        )
    result = LineAssembler(memory=memory, store=store).apply_path(
        tuple(blocks)
    )
    assert result.line_id is not None
    return result.line_id


def _rebuild(memory: InMemoryReferenceMemory) -> None:
    memory.rebuild_vector_index(
        lambda block: tuple(float(value) for value in block.metadata["vector"]),
        index_version="test-v1",
    )


def _fixture(
    tmp_path: Path,
) -> tuple[InMemoryReferenceMemory, LineGraphStore, tuple[str, ...]]:
    memory = InMemoryReferenceMemory()
    store = LineGraphStore(tmp_path / "lines")
    line_ids = (
        _add_line(
            memory,
            store,
            prefix="trade",
            anchor=(10.0, 0.0, 0.0, 0.0),
            states=_densify(SHAPE, 1),
        ),
        _add_line(
            memory,
            store,
            prefix="eng",
            anchor=(0.0, 10.0, 0.0, 0.0),
            states=_densify(SHAPE, 2),
        ),
        _add_line(
            memory,
            store,
            prefix="write",
            anchor=(0.0, 0.0, 10.0, 0.0),
            states=_densify(SHAPE, 4),
        ),
        _add_line(
            memory,
            store,
            prefix="other",
            anchor=(0.0, 0.0, 0.0, 10.0),
            states=_densify(DISTRACTOR, 2),
        ),
    )
    _rebuild(memory)
    return memory, store, line_ids


def test_surface_matches_same_trajectory_across_different_line_lengths(
    tmp_path: Path,
) -> None:
    memory, store, line_ids = _fixture(tmp_path)
    runtime = SurfaceRuntime(
        memory=memory,
        line_store=store,
        config=SurfaceConfig(min_shape_similarity=0.95),
    )

    candidates = runtime.discover(
        knowledge_cutoff=BASE + timedelta(days=500),
    )

    assert len(candidates) == 1
    owners = {view.line_id for view in candidates[0].views}
    assert owners == set(line_ids[:3])
    assert line_ids[3] not in owners
    assert candidates[0].min_pairwise_similarity > 0.999999


def test_surface_raw_closure_is_only_underlying_member_raw_evidence(
    tmp_path: Path,
) -> None:
    memory, store, _line_ids = _fixture(tmp_path)
    runtime = SurfaceRuntime(
        memory=memory,
        line_store=store,
        config=SurfaceConfig(min_shape_similarity=0.95),
    )

    candidate = runtime.discover(
        knowledge_cutoff=BASE + timedelta(days=500),
    )[0]

    assert len(candidate.raw_evidence_ids) == 24
    assert all(
        raw_id.startswith(("trade-", "eng-", "write-"))
        for raw_id in candidate.raw_evidence_ids
    )
    assert not any(
        raw_id.startswith("other-")
        for raw_id in candidate.raw_evidence_ids
    )


def test_surface_discovery_is_non_mutating_and_drops_invalid_member(
    tmp_path: Path,
) -> None:
    memory, store, line_ids = _fixture(tmp_path)
    runtime = SurfaceRuntime(
        memory=memory,
        line_store=store,
        config=SurfaceConfig(min_shape_similarity=0.95),
    )
    cutoff = BASE + timedelta(days=500)

    before_lines = len(store.list_lines())
    before_nodes = {
        line_id: len(store.nodes_for_line(line_id))
        for line_id in line_ids
    }
    assert len(runtime.discover(knowledge_cutoff=cutoff)) == 1

    memory.invalidate("trade-E1", reason="source correction")
    current_cutoff = datetime.now(UTC)

    assert runtime.discover(knowledge_cutoff=current_cutoff) == ()
    assert len(store.list_lines()) == before_lines
    assert {
        line_id: len(store.nodes_for_line(line_id))
        for line_id in line_ids
    } == before_nodes



def test_surface_returns_only_maximal_cross_line_clique(
    tmp_path: Path,
) -> None:
    memory, store, line_ids = _fixture(tmp_path)
    fourth_same = _add_line(
        memory,
        store,
        prefix="learn",
        anchor=(0.0, 0.0, 0.0, 20.0),
        states=_densify(SHAPE, 3),
    )
    _rebuild(memory)

    runtime = SurfaceRuntime(
        memory=memory,
        line_store=store,
        config=SurfaceConfig(min_shape_similarity=0.95),
    )
    candidates = runtime.discover(
        knowledge_cutoff=BASE + timedelta(days=500),
    )

    assert len(candidates) == 1
    assert {view.line_id for view in candidates[0].views} == {
        *line_ids[:3],
        fourth_same,
    }


def test_surface_search_limit_fails_closed_instead_of_returning_partial_set(
    tmp_path: Path,
) -> None:
    memory, store, _line_ids = _fixture(tmp_path)
    _add_line(
        memory,
        store,
        prefix="learn",
        anchor=(0.0, 0.0, 0.0, 20.0),
        states=_densify(SHAPE, 3),
    )
    _rebuild(memory)

    runtime = SurfaceRuntime(
        memory=memory,
        line_store=store,
        config=SurfaceConfig(
            min_shape_similarity=0.95,
            max_search_steps=1,
        ),
    )

    with pytest.raises(
        SurfaceSearchLimitExceeded,
        match="max_search_steps",
    ):
        runtime.discover(
            knowledge_cutoff=BASE + timedelta(days=500),
        )



def test_surface_view_provenance_includes_all_conjunctive_rejoin_parents(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    store = LineGraphStore(tmp_path / "lines")

    def admit(evidence_id: str, block_id: str, day: int) -> SemanticBlock:
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
                lineage_id="rejoin",
                metadata={"vector": (1.0, float(day))},
            )
        )

    trunk = admit("RT", "r-trunk", 0)
    branch_a = admit("RA", "r-a", 10)
    branch_b = admit("RB", "r-b", 12)
    rejoin = admit("RR", "r-rejoin", 30)
    _rebuild(memory)

    assembler = LineAssembler(
        memory=memory,
        store=store,
        config=LineAssemblerConfig(allow_conjunctive_rejoin=True),
    )
    first = assembler.apply_path((trunk, branch_a, rejoin))
    assembler.apply_path((trunk, branch_b, rejoin))
    assert first.line_id is not None

    runtime = SurfaceRuntime(
        memory=memory,
        line_store=store,
        config=SurfaceConfig(),
    )
    views = runtime._line_path_views(
        knowledge_cutoff=BASE + timedelta(days=100),
    )
    ending_at_rejoin = [
        view
        for view in views
        if store.get_node(view.node_ids[-1]).block_id == "r-rejoin"
    ]

    assert len(ending_at_rejoin) == 2
    for view in ending_at_rejoin:
        assert {"RT", "RA", "RB", "RR"} <= set(view.raw_evidence_ids)
