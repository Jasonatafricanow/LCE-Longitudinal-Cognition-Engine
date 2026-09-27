from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from lce.cognition.line_graph import (
    CallableLineProjector,
    CallableProjectionConfig,
    LineAssembler,
    LineAssemblerConfig,
    LineGraphStore,
    LineGraphView,
    LineTraversalLimitExceeded,
)
from lce.core.projection import LceProjectionCore
from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.testing.reference_memory import InMemoryReferenceMemory

BASE = datetime(2020, 1, 1, tzinfo=UTC)


def _admit(
    memory: InMemoryReferenceMemory,
    *,
    evidence_id: str,
    block_id: str,
    day: int,
    vector: tuple[float, ...],
) -> SemanticBlock:
    when = BASE + timedelta(days=day)
    memory.add_evidence(
        RawEvidence(
            evidence_id=evidence_id,
            content=evidence_id,
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


def test_semantic_block_state_revision_stays_one_line_node(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    trunk = _admit(
        memory,
        evidence_id="E0",
        block_id="trunk",
        day=0,
        vector=(1.0, 0.0),
    )
    evolving_v1 = _admit(
        memory,
        evidence_id="E1",
        block_id="evolving",
        day=10,
        vector=(0.9, 0.1),
    )
    tail = _admit(
        memory,
        evidence_id="E2",
        block_id="tail",
        day=30,
        vector=(0.8, 0.2),
    )
    _rebuild(memory)

    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(
        memory=memory,
        store=store,
        config=LineAssemblerConfig(min_seed_support=3, min_shared_support=2),
    )
    first = assembler.apply_path((trunk, evolving_v1, tail))
    assert first.line_id is not None

    memory.add_evidence(
        RawEvidence(
            evidence_id="E3",
            content="new detail",
            occurred_at=BASE + timedelta(days=20),
            known_at=BASE + timedelta(days=40),
            provenance={"source": "test", "canonical": True},
        )
    )
    evolving_v2 = memory.extend_semantic_block(
        "evolving",
        content="new detail",
        evidence_id="E3",
        occurred_at=BASE + timedelta(days=20),
    )
    _rebuild(memory)

    second = assembler.apply_path((trunk, evolving_v2, tail))
    assert second.line_id == first.line_id

    nodes = store.nodes_for_line(first.line_id)
    assert tuple(node.block_id for node in nodes) == (
        "trunk",
        "evolving",
        "tail",
    )
    evolving_node = store.node_for_block(first.line_id, "evolving")
    assert evolving_node is not None
    states = store.states_for_node(evolving_node.node_id)
    assert len(states) == 2
    assert {state.state_id for state in states} == {
        evolving_v1.state_id,
        evolving_v2.state_id,
    }


def test_same_line_can_branch_and_rejoin_without_line_clone(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    trunk = _admit(
        memory,
        evidence_id="T",
        block_id="trunk",
        day=0,
        vector=(1.0, 0.0),
    )
    branch_a = _admit(
        memory,
        evidence_id="A",
        block_id="branch-a",
        day=10,
        vector=(0.9, 0.1),
    )
    branch_b = _admit(
        memory,
        evidence_id="B",
        block_id="branch-b",
        day=12,
        vector=(0.88, 0.12),
    )
    rejoin = _admit(
        memory,
        evidence_id="R",
        block_id="rejoin",
        day=30,
        vector=(0.8, 0.2),
    )
    _rebuild(memory)

    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(
        memory=memory,
        store=store,
        config=LineAssemblerConfig(min_seed_support=3, min_shared_support=2),
    )
    first = assembler.apply_path((trunk, branch_a, rejoin))
    second = assembler.apply_path((trunk, branch_b, rejoin))

    assert first.line_id is not None
    assert second.line_id == first.line_id
    assert len(store.list_lines()) == 1

    rejoin_node = store.node_for_block(first.line_id, "rejoin")
    branch_a_node = store.node_for_block(first.line_id, "branch-a")
    branch_b_node = store.node_for_block(first.line_id, "branch-b")
    assert rejoin_node is not None
    assert branch_a_node is not None
    assert branch_b_node is not None
    assert set(store.parents(rejoin_node.node_id)) == {
        branch_a_node.node_id,
        branch_b_node.node_id,
    }


def test_invalid_rejoin_evidence_reopens_old_branch_frontier(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    trunk = _admit(
        memory,
        evidence_id="T",
        block_id="trunk",
        day=0,
        vector=(1.0, 0.0),
    )
    branch_a = _admit(
        memory,
        evidence_id="A",
        block_id="branch-a",
        day=10,
        vector=(0.9, 0.1),
    )
    branch_b = _admit(
        memory,
        evidence_id="B",
        block_id="branch-b",
        day=12,
        vector=(0.88, 0.12),
    )
    rejoin = _admit(
        memory,
        evidence_id="R",
        block_id="rejoin",
        day=30,
        vector=(0.8, 0.2),
    )
    _rebuild(memory)

    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(
        memory=memory,
        store=store,
        config=LineAssemblerConfig(min_seed_support=3, min_shared_support=2),
    )
    first = assembler.apply_path((trunk, branch_a, rejoin))
    assembler.apply_path((trunk, branch_b, rejoin))
    assert first.line_id is not None

    view = LineGraphView(memory=memory, store=store)
    cutoff = BASE + timedelta(days=100)
    rejoin_node = store.node_for_block(first.line_id, "rejoin")
    assert rejoin_node is not None
    assert view.frontier(
        first.line_id,
        knowledge_cutoff=cutoff,
    ) == (rejoin_node.node_id,)

    memory.invalidate("R", reason="correction")
    branch_a_node = store.node_for_block(first.line_id, "branch-a")
    branch_b_node = store.node_for_block(first.line_id, "branch-b")
    assert branch_a_node is not None
    assert branch_b_node is not None
    assert set(
        view.frontier(
            first.line_id,
            knowledge_cutoff=cutoff,
        )
    ) == {
        branch_a_node.node_id,
        branch_b_node.node_id,
    }


def test_callable_projection_is_bounded_and_not_persisted(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"E{index}",
            block_id=f"B{index}",
            day=index * 10,
            vector=(1.0 - index * 0.05, index * 0.05),
        )
        for index in range(8)
    )
    _rebuild(memory)

    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(memory=memory, store=store)
    applied = assembler.apply_path(blocks)
    assert applied.line_id is not None

    projector = CallableLineProjector(
        memory=memory,
        store=store,
        config=CallableProjectionConfig(max_nodes=3),
    )
    before_lines = len(store.list_lines())
    before_nodes = len(store.nodes_for_line(applied.line_id))

    projection = projector.project_for_block(
        applied.line_id,
        blocks[4],
        knowledge_cutoff=BASE + timedelta(days=100),
    )
    assert projection is not None
    assert 1 <= len(projection.node_ids) <= 3
    assert len(projection.selected_support) == len(projection.node_ids)

    assert len(store.list_lines()) == before_lines
    assert len(store.nodes_for_line(applied.line_id)) == before_nodes


def test_line_store_rejects_cycle_even_if_assembler_is_bypassed(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"E{index}",
            block_id=f"B{index}",
            day=index * 10,
            vector=(1.0, 0.0),
        )
        for index in range(3)
    )
    _rebuild(memory)

    store = LineGraphStore(tmp_path / "lines")
    applied = LineAssembler(memory=memory, store=store).apply_path(blocks)
    assert applied.line_id is not None

    first = store.node_for_block(applied.line_id, "B0")
    last = store.node_for_block(applied.line_id, "B2")
    assert first is not None
    assert last is not None

    with pytest.raises(ValueError, match="cycle"):
        store.add_edge(applied.line_id, last.node_id, first.node_id)


def test_invalid_historical_node_does_not_count_toward_line_absorption(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    trunk = _admit(
        memory,
        evidence_id="T",
        block_id="trunk",
        day=0,
        vector=(1.0, 0.0),
    )
    invalid_later = _admit(
        memory,
        evidence_id="OLD",
        block_id="old",
        day=10,
        vector=(0.9, 0.1),
    )
    stable = _admit(
        memory,
        evidence_id="S",
        block_id="stable",
        day=20,
        vector=(0.8, 0.2),
    )
    newcomer = _admit(
        memory,
        evidence_id="N",
        block_id="new",
        day=30,
        vector=(0.7, 0.3),
    )
    _rebuild(memory)

    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(
        memory=memory,
        store=store,
        config=LineAssemblerConfig(min_seed_support=3, min_shared_support=2),
    )
    initial = assembler.apply_path((trunk, invalid_later, stable))
    assert initial.line_id is not None

    memory.invalidate("OLD", reason="source correction")

    attempted = assembler.apply_path((invalid_later, stable, newcomer))
    assert attempted.line_id is None
    assert attempted.unresolved_reason == (
        "weak overlap with an existing Line; no clone created"
    )
    assert len(store.list_lines()) == 1


def test_core_returns_callable_views_without_persisting_projection_nodes(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"C{index}",
            block_id=f"CB{index}",
            day=index * 10,
            vector=(1.0 - index * 0.04, index * 0.04),
        )
        for index in range(6)
    )
    _rebuild(memory)

    core = LceProjectionCore(
        tmp_path / "core",
        memory=memory,
        callable_projection_config=CallableProjectionConfig(max_nodes=3),
    )
    applied = LineAssembler(
        memory=memory,
        store=core.lines,
    ).apply_path(blocks)
    assert applied.line_id is not None
    before_nodes = len(core.lines.nodes_for_line(applied.line_id))

    projections = core.callable_line_projections(
        (blocks[-1].block_id,),
        knowledge_cutoff=BASE + timedelta(days=100),
    )

    assert len(projections) == 1
    assert projections[0].line_id == applied.line_id
    assert len(projections[0].node_ids) <= 3
    assert len(core.lines.nodes_for_line(applied.line_id)) == before_nodes
    core.close()


def test_line_store_suppresses_redundant_transitive_shortcut(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"R{index}",
            block_id=f"RB{index}",
            day=index * 10,
            vector=(1.0 - index * 0.1, index * 0.1),
        )
        for index in range(3)
    )
    _rebuild(memory)

    store = LineGraphStore(tmp_path / "lines")
    applied = LineAssembler(memory=memory, store=store).apply_path(blocks)
    assert applied.line_id is not None

    first = store.node_for_block(applied.line_id, "RB0")
    last = store.node_for_block(applied.line_id, "RB2")
    assert first is not None
    assert last is not None

    assert store.add_edge(applied.line_id, first.node_id, last.node_id) is False
    assert len(store.edges_for_line(applied.line_id)) == 2



def test_raw_closure_returns_complete_iterative_provenance(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"P{index}",
            block_id=f"PB{index}",
            day=index,
            vector=(1.0, 0.0),
        )
        for index in range(20)
    )
    store = LineGraphStore(tmp_path / "lines")
    applied = LineAssembler(memory=memory, store=store).apply_path(blocks)
    assert applied.line_id is not None

    tail = store.node_for_block(applied.line_id, "PB19")
    assert tail is not None
    closure = LineGraphView(memory=memory, store=store).raw_closure(
        tail.node_id,
        knowledge_cutoff=BASE + timedelta(days=100),
    )

    assert closure == tuple(f"P{index}" for index in range(20))


def test_raw_closure_fails_closed_when_safety_ceiling_is_exceeded(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"L{index}",
            block_id=f"LB{index}",
            day=index,
            vector=(1.0, 0.0),
        )
        for index in range(8)
    )
    store = LineGraphStore(tmp_path / "lines")
    applied = LineAssembler(memory=memory, store=store).apply_path(blocks)
    assert applied.line_id is not None

    tail = store.node_for_block(applied.line_id, "LB7")
    assert tail is not None
    with pytest.raises(
        LineTraversalLimitExceeded,
        match="exact closure was not returned",
    ):
        LineGraphView(memory=memory, store=store).raw_closure(
            tail.node_id,
            knowledge_cutoff=BASE + timedelta(days=100),
            max_nodes=4,
        )


def test_multi_parent_visibility_is_conjunctive_rejoin_not_alternative_or(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    trunk = _admit(
        memory,
        evidence_id="CT",
        block_id="c-trunk",
        day=0,
        vector=(1.0, 0.0),
    )
    branch_a = _admit(
        memory,
        evidence_id="CA",
        block_id="c-a",
        day=10,
        vector=(0.9, 0.1),
    )
    branch_b = _admit(
        memory,
        evidence_id="CB",
        block_id="c-b",
        day=12,
        vector=(0.88, 0.12),
    )
    rejoin = _admit(
        memory,
        evidence_id="CR",
        block_id="c-rejoin",
        day=30,
        vector=(0.8, 0.2),
    )

    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(memory=memory, store=store)
    first = assembler.apply_path((trunk, branch_a, rejoin))
    assembler.apply_path((trunk, branch_b, rejoin))
    assert first.line_id is not None

    rejoin_node = store.node_for_block(first.line_id, "c-rejoin")
    branch_b_node = store.node_for_block(first.line_id, "c-b")
    assert rejoin_node is not None
    assert branch_b_node is not None

    view = LineGraphView(memory=memory, store=store)
    cutoff = BASE + timedelta(days=100)
    assert rejoin_node.node_id in view.visible_node_ids(
        first.line_id,
        knowledge_cutoff=cutoff,
    )

    # One parent remains fully valid, but invalidating the other parent must
    # hide the conjunctive rejoin. Alternative/OR semantics are intentionally
    # not represented by multi-parent Line edges in V1.
    memory.invalidate("CA", reason="parent hypothesis falsified")

    assert rejoin_node.node_id not in view.visible_node_ids(
        first.line_id,
        knowledge_cutoff=cutoff,
    )
    assert branch_b_node.node_id in view.frontier(
        first.line_id,
        knowledge_cutoff=cutoff,
    )
