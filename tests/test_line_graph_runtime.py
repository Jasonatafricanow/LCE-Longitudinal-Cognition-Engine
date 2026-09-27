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
from lce.core.projection import LceProjectionCore, StaleLineGraphError
from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.structure.trajectory import TrajectoryConfig
from lce.testing.reference_memory import InMemoryReferenceMemory

BASE = datetime(2020, 1, 1, tzinfo=UTC)



class _VersionedFixedNeighbourProvider:
    def __init__(self, version: str) -> None:
        self.derivation_fingerprint = version

    def candidates(
        self,
        blocks: tuple[SemanticBlock, ...],
        vectors: dict[str, tuple[float, ...]],
        *,
        k: int,
        min_similarity: float,
    ) -> dict[str, tuple[tuple[float, str], ...]]:
        del vectors, k, min_similarity
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
        config=LineAssemblerConfig(
            min_seed_support=3,
            min_shared_support=2,
            allow_conjunctive_rejoin=True,
        ),
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
        config=LineAssemblerConfig(
            min_seed_support=3,
            min_shared_support=2,
            allow_conjunctive_rejoin=True,
        ),
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
    current_cutoff = datetime.now(UTC)
    branch_a_node = store.node_for_block(first.line_id, "branch-a")
    branch_b_node = store.node_for_block(first.line_id, "branch-b")
    assert branch_a_node is not None
    assert branch_b_node is not None
    assert set(
        view.frontier(
            first.line_id,
            knowledge_cutoff=current_cutoff,
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


def test_line_assembler_rejects_cutoff_invalid_candidate_state(
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

    with pytest.raises(
        ValueError,
        match="cutoff-invalid SemanticBlock state",
    ):
        assembler.apply_path(
            (invalid_later, stable, newcomer),
            knowledge_cutoff=datetime.now(UTC),
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

    assert closure == tuple(sorted(f"P{index}" for index in range(20)))


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
    assembler = LineAssembler(
        memory=memory,
        store=store,
        config=LineAssemblerConfig(allow_conjunctive_rejoin=True),
    )
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
    current_cutoff = datetime.now(UTC)

    assert rejoin_node.node_id not in view.visible_node_ids(
        first.line_id,
        knowledge_cutoff=current_cutoff,
    )
    assert branch_b_node.node_id in view.frontier(
        first.line_id,
        knowledge_cutoff=current_cutoff,
    )



def test_default_assembler_does_not_infer_conjunctive_rejoin_from_overlap(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    trunk = _admit(
        memory,
        evidence_id="DT",
        block_id="d-trunk",
        day=0,
        vector=(1.0, 0.0),
    )
    branch_a = _admit(
        memory,
        evidence_id="DA",
        block_id="d-a",
        day=10,
        vector=(0.9, 0.1),
    )
    branch_b = _admit(
        memory,
        evidence_id="DB",
        block_id="d-b",
        day=12,
        vector=(0.89, 0.11),
    )
    later = _admit(
        memory,
        evidence_id="DL",
        block_id="d-later",
        day=30,
        vector=(0.8, 0.2),
    )

    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(memory=memory, store=store)
    first = assembler.apply_path((trunk, branch_a, later))
    second = assembler.apply_path((trunk, branch_b, later))
    assert first.line_id is not None
    assert second.line_id == first.line_id

    later_node = store.node_for_block(first.line_id, "d-later")
    branch_a_node = store.node_for_block(first.line_id, "d-a")
    branch_b_node = store.node_for_block(first.line_id, "d-b")
    assert later_node is not None
    assert branch_a_node is not None
    assert branch_b_node is not None

    assert store.parents(later_node.node_id) == (branch_a_node.node_id,)
    assert branch_b_node.node_id in LineGraphView(
        memory=memory,
        store=store,
    ).frontier(
        first.line_id,
        knowledge_cutoff=BASE + timedelta(days=100),
    )



def test_apply_path_rolls_back_partial_new_line_on_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"TX{index}",
            block_id=f"TXB{index}",
            day=index * 10,
            vector=(1.0, 0.0),
        )
        for index in range(3)
    )
    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(memory=memory, store=store)
    original = store.ensure_node
    calls = 0

    def failing_ensure_node(*args: object, **kwargs: object):
        nonlocal calls
        result = original(*args, **kwargs)
        calls += 1
        if calls == 2:
            raise RuntimeError("injected node write failure")
        return result

    monkeypatch.setattr(store, "ensure_node", failing_ensure_node)

    with pytest.raises(RuntimeError, match="injected node write failure"):
        assembler.apply_path(blocks)

    assert store.list_lines() == ()
    assert store.conn.execute(
        "SELECT COUNT(*) FROM line_nodes"
    ).fetchone()[0] == 0
    assert store.conn.execute(
        "SELECT COUNT(*) FROM line_node_states"
    ).fetchone()[0] == 0


def test_attach_block_rolls_back_node_when_edge_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    memory = InMemoryReferenceMemory()
    seed = tuple(
        _admit(
            memory,
            evidence_id=f"ATX{index}",
            block_id=f"ATXB{index}",
            day=index * 10,
            vector=(1.0, 0.0),
        )
        for index in range(3)
    )
    newcomer = _admit(
        memory,
        evidence_id="ATX-new",
        block_id="ATXB-new",
        day=40,
        vector=(1.0, 0.0),
    )
    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(memory=memory, store=store)
    initial = assembler.apply_path(seed)
    assert initial.line_id is not None
    parent = store.node_for_block(initial.line_id, seed[-1].block_id)
    assert parent is not None
    before_edges = store.edges_for_line(initial.line_id)

    original = store.add_edge

    def failing_add_edge(*args: object, **kwargs: object):
        original(*args, **kwargs)
        raise RuntimeError("injected edge write failure")

    monkeypatch.setattr(store, "add_edge", failing_add_edge)

    with pytest.raises(RuntimeError, match="injected edge write failure"):
        assembler.attach_block(
            initial.line_id,
            newcomer,
            parent_node_ids=(parent.node_id,),
        )

    assert store.node_for_block(
        initial.line_id,
        newcomer.block_id,
    ) is None
    assert store.edges_for_line(initial.line_id) == before_edges



def test_callable_projection_keeps_full_rejoin_provenance_when_content_is_bounded(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    trunk = _admit(
        memory,
        evidence_id="PRT",
        block_id="pr-trunk",
        day=0,
        vector=(1.0, 0.0),
    )
    branch_a = _admit(
        memory,
        evidence_id="PRA",
        block_id="pr-a",
        day=10,
        vector=(0.9, 0.1),
    )
    branch_b = _admit(
        memory,
        evidence_id="PRB",
        block_id="pr-b",
        day=12,
        vector=(0.88, 0.12),
    )
    rejoin = _admit(
        memory,
        evidence_id="PRR",
        block_id="pr-rejoin",
        day=30,
        vector=(0.8, 0.2),
    )
    _rebuild(memory)

    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(
        memory=memory,
        store=store,
        config=LineAssemblerConfig(allow_conjunctive_rejoin=True),
    )
    first = assembler.apply_path((trunk, branch_a, rejoin))
    assembler.apply_path((trunk, branch_b, rejoin))
    assert first.line_id is not None

    projection = CallableLineProjector(
        memory=memory,
        store=store,
        config=CallableProjectionConfig(max_nodes=1),
    ).project_for_block(
        first.line_id,
        rejoin,
        knowledge_cutoff=BASE + timedelta(days=100),
    )

    assert projection is not None
    assert len(projection.node_ids) == 1
    assert set(projection.raw_evidence_ids) == {
        "PRT",
        "PRA",
        "PRB",
        "PRR",
    }



def test_one_semantic_block_may_support_two_distinct_lines(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    a = _admit(
        memory,
        evidence_id="ML-A",
        block_id="ml-a",
        day=0,
        vector=(1.0, 0.0),
    )
    b = _admit(
        memory,
        evidence_id="ML-B",
        block_id="ml-b",
        day=10,
        vector=(0.9, 0.1),
    )
    shared = _admit(
        memory,
        evidence_id="ML-C",
        block_id="ml-shared",
        day=20,
        vector=(0.8, 0.2),
    )
    d = _admit(
        memory,
        evidence_id="ML-D",
        block_id="ml-d",
        day=30,
        vector=(0.7, 0.3),
    )
    e = _admit(
        memory,
        evidence_id="ML-E",
        block_id="ml-e",
        day=40,
        vector=(0.6, 0.4),
    )
    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(
        memory=memory,
        store=store,
        config=LineAssemblerConfig(
            min_seed_support=3,
            min_shared_support=2,
        ),
    )

    first = assembler.apply_path((a, b, shared))
    second = assembler.apply_path((shared, d, e))

    assert first.line_id is not None
    assert second.line_id is not None
    assert second.line_id != first.line_id
    assert len(store.list_lines()) == 2
    assert set(store.lines_for_block(shared.block_id)) == {
        first.line_id,
        second.line_id,
    }


def test_strong_overlap_still_extends_existing_line_instead_of_cloning(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"SO-{index}",
            block_id=f"so-{index}",
            day=index * 10,
            vector=(1.0 - index * 0.05, index * 0.05),
        )
        for index in range(4)
    )
    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(
        memory=memory,
        store=store,
        config=LineAssemblerConfig(
            min_seed_support=3,
            min_shared_support=2,
        ),
    )

    first = assembler.apply_path(blocks[:3])
    second = assembler.apply_path(blocks[1:])

    assert first.line_id is not None
    assert second.line_id == first.line_id
    assert len(store.list_lines()) == 1



def test_line_relation_rebuild_preserves_history_and_replaces_current_path(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    a = _admit(
        memory,
        evidence_id="RB-A",
        block_id="rb-a",
        day=0,
        vector=(1.0, 0.0),
    )
    b = _admit(
        memory,
        evidence_id="RB-B",
        block_id="rb-b",
        day=10,
        vector=(0.9, 0.1),
    )
    c_block = _admit(
        memory,
        evidence_id="RB-C",
        block_id="rb-c",
        day=20,
        vector=(0.8, 0.2),
    )
    d = _admit(
        memory,
        evidence_id="RB-D",
        block_id="rb-d",
        day=30,
        vector=(0.7, 0.3),
    )

    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(memory=memory, store=store)
    initial = assembler.apply_path((a, b, c_block, d))
    assert initial.line_id is not None
    line_id = initial.line_id
    historical_cutoff = BASE + timedelta(days=100)

    a_node = store.node_for_block(line_id, a.block_id)
    b_node = store.node_for_block(line_id, b.block_id)
    c_node = store.node_for_block(line_id, c_block.block_id)
    d_node = store.node_for_block(line_id, d.block_id)
    assert a_node is not None
    assert b_node is not None
    assert c_node is not None
    assert d_node is not None
    assert set(
        store.edges_for_line_at(line_id, historical_cutoff)
    ) == {
        (a_node.node_id, b_node.node_id),
        (b_node.node_id, c_node.node_id),
        (c_node.node_id, d_node.node_id),
    }

    memory.invalidate(b.raw_evidence_ids[0], reason="later correction")
    current_cutoff = datetime.now(UTC)
    store.retire_current_structure(current_cutoff)
    rebuilt = assembler.apply_path(
        (a, c_block, d),
        knowledge_cutoff=current_cutoff,
    )

    assert rebuilt.line_id == line_id
    assert set(
        store.edges_for_line_at(line_id, historical_cutoff)
    ) == {
        (a_node.node_id, b_node.node_id),
        (b_node.node_id, c_node.node_id),
        (c_node.node_id, d_node.node_id),
    }
    assert set(
        store.edges_for_line_at(line_id, current_cutoff)
    ) == {
        (a_node.node_id, c_node.node_id),
        (c_node.node_id, d_node.node_id),
    }
    view = LineGraphView(memory=memory, store=store)
    assert set(
        view.visible_node_ids(
            line_id,
            knowledge_cutoff=historical_cutoff,
        )
    ) == {
        a_node.node_id,
        b_node.node_id,
        c_node.node_id,
        d_node.node_id,
    }
    assert set(
        view.visible_node_ids(
            line_id,
            knowledge_cutoff=current_cutoff,
        )
    ) == {
        a_node.node_id,
        c_node.node_id,
        d_node.node_id,
    }



def test_core_source_change_rebuilds_current_line_but_keeps_historical_relation(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    a = _admit(
        memory,
        evidence_id="CORE-A",
        block_id="core-a",
        day=0,
        vector=(1.0, 0.0),
    )
    b = _admit(
        memory,
        evidence_id="CORE-B",
        block_id="core-b",
        day=10,
        vector=(0.9, 0.1),
    )
    c_block = _admit(
        memory,
        evidence_id="CORE-C",
        block_id="core-c",
        day=20,
        vector=(0.8, 0.2),
    )
    d = _admit(
        memory,
        evidence_id="CORE-D",
        block_id="core-d",
        day=30,
        vector=(0.7, 0.3),
    )
    _rebuild(memory)
    core = LceProjectionCore(
        tmp_path / "core",
        memory=memory,
        trajectory_config=TrajectoryConfig(
            k=2,
            min_similarity=0.1,
            min_support=3,
        ),
        block_embedder=lambda block: tuple(
            float(value) for value in block.metadata["vector"]
        ),
        block_embedding_version="test-v1",
    )
    historical_cutoff = BASE + timedelta(days=100)
    initial = core.trajectory.assembler.apply_path(
        (a, b, c_block, d),
        knowledge_cutoff=historical_cutoff,
    )
    assert initial.line_id is not None
    line_id = initial.line_id

    a_node = core.lines.node_for_block(line_id, a.block_id)
    b_node = core.lines.node_for_block(line_id, b.block_id)
    c_node = core.lines.node_for_block(line_id, c_block.block_id)
    d_node = core.lines.node_for_block(line_id, d.block_id)
    assert a_node is not None
    assert b_node is not None
    assert c_node is not None
    assert d_node is not None

    memory.invalidate("CORE-B", reason="later correction")
    core.source_changed_and_rebuild("CORE-B")
    current_cutoff = datetime.now(UTC)

    assert set(
        core.lines.edges_for_line_at(line_id, historical_cutoff)
    ) == {
        (a_node.node_id, b_node.node_id),
        (b_node.node_id, c_node.node_id),
        (c_node.node_id, d_node.node_id),
    }
    assert set(
        core.lines.edges_for_line_at(line_id, current_cutoff)
    ) == {
        (a_node.node_id, c_node.node_id),
        (c_node.node_id, d_node.node_id),
    }
    core.close()


def test_line_derivation_fingerprint_rebuilds_without_overwriting_old_revision(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"FP-{index}",
            block_id=f"fp-{index}",
            day=index * 10,
            vector=(1.0 - index * 0.1, index * 0.1),
        )
        for index in range(3)
    )
    _rebuild(memory)
    root = tmp_path / "fingerprint-core"
    config = TrajectoryConfig(
        k=2,
        min_similarity=0.1,
        min_support=3,
    )
    embedder = lambda block: tuple(
        float(value) for value in block.metadata["vector"]
    )

    first = LceProjectionCore(
        root,
        memory=memory,
        trajectory_config=config,
        block_embedder=embedder,
        block_embedding_version="vector-v1",
    )
    seeded = first.trajectory.assembler.apply_path(
        blocks,
        knowledge_cutoff=BASE + timedelta(days=100),
    )
    assert seeded.line_id is not None
    old_fingerprint = first.lines.get_metadata(
        "derivation_fingerprint"
    )
    assert old_fingerprint is not None
    first.close()

    second = LceProjectionCore(
        root,
        memory=memory,
        trajectory_config=config,
        block_embedder=embedder,
        block_embedding_version="vector-v2",
    )
    with pytest.raises(StaleLineGraphError):
        second.line_frontier(
            seeded.line_id,
            knowledge_cutoff=datetime.now(UTC),
        )

    second.bootstrap_trajectory(
        knowledge_cutoff=BASE + timedelta(days=100),
    )
    new_fingerprint = second.lines.get_metadata(
        "derivation_fingerprint"
    )

    assert new_fingerprint is not None
    assert new_fingerprint != old_fingerprint
    all_fingerprints = {
        str(row[0])
        for row in second.lines.conn.execute(
            "SELECT DISTINCT derivation_fingerprint "
            "FROM line_node_memberships"
        ).fetchall()
    }
    assert {old_fingerprint, new_fingerprint} <= all_fingerprints
    active_fingerprints = {
        str(row[0])
        for row in second.lines.conn.execute(
            "SELECT DISTINCT derivation_fingerprint "
            "FROM line_node_memberships WHERE retired_at IS NULL"
        ).fetchall()
    }
    assert active_fingerprints == {new_fingerprint}
    second.close()



def test_relation_revision_can_reactivate_twice_at_same_knowledge_cutoff(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"RETRY-{index}",
            block_id=f"retry-{index}",
            day=index * 10,
            vector=(1.0 - index * 0.1, index * 0.1),
        )
        for index in range(3)
    )
    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(memory=memory, store=store)
    historical_cutoff = BASE + timedelta(days=50)
    initial = assembler.apply_path(
        blocks,
        knowledge_cutoff=historical_cutoff,
    )
    assert initial.line_id is not None

    rebuild_cutoff = BASE + timedelta(days=100)
    store.retire_current_structure(rebuild_cutoff)
    first_retry = assembler.apply_path(
        blocks,
        knowledge_cutoff=rebuild_cutoff,
    )
    assert first_retry.line_id == initial.line_id

    # Simulate a higher-level rebuild abort after one committed path. Retire
    # that partial current revision and retry at exactly the same knowledge
    # cutoff. Revision identity must not collide with the retired attempt.
    store.retire_current_structure(rebuild_cutoff)
    second_retry = assembler.apply_path(
        blocks,
        knowledge_cutoff=rebuild_cutoff,
    )

    assert second_retry.line_id == initial.line_id
    line_id = initial.line_id
    assert len(store.active_node_ids_at(line_id, rebuild_cutoff)) == 3
    assert len(store.edges_for_line_at(line_id, rebuild_cutoff)) == 2
    membership_revisions = store.conn.execute(
        "SELECT COUNT(*) FROM line_node_memberships "
        "WHERE node_id = ?",
        (
            store.node_for_block(
                line_id,
                blocks[0].block_id,
            ).node_id,
        ),
    ).fetchone()[0]
    assert membership_revisions == 3



def test_same_derivation_fingerprint_restarts_without_spurious_rebuild(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"RST-{index}",
            block_id=f"rst-{index}",
            day=index * 10,
            vector=(1.0 - index * 0.1, index * 0.1),
        )
        for index in range(3)
    )
    _rebuild(memory)
    root = tmp_path / "restart-core"
    config = TrajectoryConfig(
        k=2,
        min_similarity=0.1,
        min_support=3,
    )
    embedder = lambda block: tuple(
        float(value) for value in block.metadata["vector"]
    )

    first = LceProjectionCore(
        root,
        memory=memory,
        trajectory_config=config,
        block_embedder=embedder,
        block_embedding_version="stable-v1",
    )
    seeded = first.trajectory.assembler.apply_path(
        blocks,
        knowledge_cutoff=BASE + timedelta(days=100),
    )
    assert seeded.line_id is not None
    expected_frontier = first.line_frontier(
        seeded.line_id,
        knowledge_cutoff=BASE + timedelta(days=100),
    )
    before_revision_count = first.lines.conn.execute(
        "SELECT COUNT(*) FROM line_node_memberships"
    ).fetchone()[0]
    first.close()

    restarted = LceProjectionCore(
        root,
        memory=memory,
        trajectory_config=config,
        block_embedder=embedder,
        block_embedding_version="stable-v1",
    )

    assert restarted.line_frontier(
        seeded.line_id,
        knowledge_cutoff=BASE + timedelta(days=100),
    ) == expected_frontier
    assert restarted.lines.conn.execute(
        "SELECT COUNT(*) FROM line_node_memberships"
    ).fetchone()[0] == before_revision_count
    restarted.close()


def test_neighbour_provider_declared_version_participates_in_line_fingerprint(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"NP-{index}",
            block_id=f"np-{index}",
            day=index * 10,
            vector=(1.0 - index * 0.1, index * 0.1),
        )
        for index in range(3)
    )
    _rebuild(memory)
    root = tmp_path / "provider-version-core"
    config = TrajectoryConfig(
        k=2,
        min_similarity=0.1,
        min_support=3,
    )
    embedder = lambda block: tuple(
        float(value) for value in block.metadata["vector"]
    )

    first = LceProjectionCore(
        root,
        memory=memory,
        trajectory_config=config,
        trajectory_neighbour_provider=_VersionedFixedNeighbourProvider(
            "fixed-provider-v1"
        ),
        block_embedder=embedder,
        block_embedding_version="vector-v1",
    )
    seeded = first.trajectory.assembler.apply_path(
        blocks,
        knowledge_cutoff=BASE + timedelta(days=100),
    )
    assert seeded.line_id is not None
    first.close()

    changed = LceProjectionCore(
        root,
        memory=memory,
        trajectory_config=config,
        trajectory_neighbour_provider=_VersionedFixedNeighbourProvider(
            "fixed-provider-v2"
        ),
        block_embedder=embedder,
        block_embedding_version="vector-v1",
    )

    with pytest.raises(StaleLineGraphError):
        changed.line_frontier(
            seeded.line_id,
            knowledge_cutoff=datetime.now(UTC),
        )
    changed.close()



def test_zero_lifetime_failed_line_revision_cannot_claim_retry_identity(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"FAILID-{index}",
            block_id=f"failid-{index}",
            day=index * 10,
            vector=(1.0 - index * 0.05, index * 0.05),
        )
        for index in range(4)
    )
    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(
        memory=memory,
        store=store,
        config=LineAssemblerConfig(
            min_seed_support=3,
            min_shared_support=2,
        ),
    )
    cutoff = BASE + timedelta(days=100)

    partial = assembler.apply_path(
        blocks[:3],
        knowledge_cutoff=cutoff,
    )
    assert partial.line_id is not None
    store.retire_current_structure(cutoff)

    retry = assembler.apply_path(
        blocks[1:],
        knowledge_cutoff=cutoff,
    )

    assert retry.line_id is not None
    assert retry.created_line is True
    assert retry.line_id != partial.line_id



def test_raw_closure_respects_relation_membership_cutoff(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"CLOSE-{index}",
            block_id=f"close-{index}",
            day=index * 10,
            vector=(1.0 - index * 0.1, index * 0.1),
        )
        for index in range(3)
    )
    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(memory=memory, store=store)
    historical_cutoff = BASE + timedelta(days=50)
    seeded = assembler.apply_path(
        blocks,
        knowledge_cutoff=historical_cutoff,
    )
    assert seeded.line_id is not None
    tail = store.node_for_block(
        seeded.line_id,
        blocks[-1].block_id,
    )
    assert tail is not None
    view = LineGraphView(memory=memory, store=store)

    assert set(
        view.raw_closure(
            tail.node_id,
            knowledge_cutoff=historical_cutoff,
        )
    ) == {"CLOSE-0", "CLOSE-1", "CLOSE-2"}

    current_cutoff = BASE + timedelta(days=100)
    store.retire_current_structure(current_cutoff)

    assert view.raw_closure(
        tail.node_id,
        knowledge_cutoff=current_cutoff,
    ) == ()
    assert set(
        view.raw_closure(
            tail.node_id,
            knowledge_cutoff=historical_cutoff,
        )
    ) == {"CLOSE-0", "CLOSE-1", "CLOSE-2"}



def test_line_assembler_rejects_forged_payload_for_real_state_id(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"AUTH-{index}",
            block_id=f"auth-{index}",
            day=index * 10,
            vector=(1.0 - index * 0.1, index * 0.1),
        )
        for index in range(3)
    )
    forged = SemanticBlock(
        block_id=blocks[1].block_id,
        content="forged derived payload",
        raw_evidence_ids=blocks[1].raw_evidence_ids,
        occurred_start=blocks[1].occurred_start,
        occurred_end=blocks[1].occurred_end,
        compiler_version=blocks[1].compiler_version,
        lineage_id=blocks[1].lineage_id,
        metadata=blocks[1].metadata,
        state_id=blocks[1].state_id,
        state_version=blocks[1].state_version,
    )
    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(memory=memory, store=store)

    with pytest.raises(
        ValueError,
        match="unauthorized or cutoff-invalid",
    ):
        assembler.apply_path(
            (blocks[0], forged, blocks[2]),
            knowledge_cutoff=BASE + timedelta(days=100),
        )

    assert store.list_lines() == ()



def test_reactivating_existing_line_record_does_not_report_new_line(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"CREATEFLAG-{index}",
            block_id=f"createflag-{index}",
            day=index * 10,
            vector=(1.0 - index * 0.1, index * 0.1),
        )
        for index in range(3)
    )
    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(memory=memory, store=store)
    cutoff = BASE + timedelta(days=100)

    first = assembler.apply_path(
        blocks,
        knowledge_cutoff=cutoff,
    )
    assert first.line_id is not None
    assert first.created_line is True

    # Retiring at the same cutoff gives the first revision zero lifetime, so it
    # is not eligible to carry identity into the retry. The deterministic Line
    # record still exists, however, and reactivation must not claim it was
    # created again.
    store.retire_current_structure(cutoff)
    second = assembler.apply_path(
        blocks,
        knowledge_cutoff=cutoff,
    )

    assert second.line_id == first.line_id
    assert second.created_line is False



def test_rebuild_cutoff_cancels_precomputed_future_line_revision(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(
            memory,
            evidence_id=f"FUTURE-{index}",
            block_id=f"future-{index}",
            day=index * 10,
            vector=(1.0 - index * 0.1, index * 0.1),
        )
        for index in range(3)
    )
    store = LineGraphStore(tmp_path / "lines")
    assembler = LineAssembler(memory=memory, store=store)
    future_cutoff = BASE + timedelta(days=200)
    seeded = assembler.apply_path(
        blocks,
        knowledge_cutoff=future_cutoff,
    )
    assert seeded.line_id is not None
    line_id = seeded.line_id

    rebuild_cutoff = BASE + timedelta(days=100)
    store.retire_current_structure(rebuild_cutoff)

    assert store.active_node_ids_at(line_id, future_cutoff) == ()
    assert store.edges_for_line_at(line_id, future_cutoff) == ()
    # The revision did not exist at an earlier historical cutoff either.
    assert store.active_node_ids_at(
        line_id,
        BASE + timedelta(days=50),
    ) == ()
