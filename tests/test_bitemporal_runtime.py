from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from lce.core.projection import LceProjectionCore
from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.semantic.compiler import SemanticCompiler
from lce.testing.reference_memory import InMemoryReferenceMemory


def _raw(
    evidence_id: str,
    *,
    occurred_year: int,
    known_year: int,
) -> RawEvidence:
    return RawEvidence(
        evidence_id=evidence_id,
        content=evidence_id,
        occurred_at=datetime(occurred_year, 1, 1, tzinfo=UTC),
        known_at=datetime(known_year, 1, 1, tzinfo=UTC),
        provenance={"source": "test", "canonical": True},
    )


def test_default_stream_order_uses_knowledge_time() -> None:
    late_history = _raw("late", occurred_year=2020, known_year=2026)

    assert late_history.effective_ordering_key == datetime(
        2026, 1, 1, tzinfo=UTC
    ).isoformat()


def test_knowledge_cutoff_blocks_future_leak_for_late_historical_evidence() -> None:
    memory = InMemoryReferenceMemory()
    item = _raw("E1", occurred_year=2020, known_year=2026)
    memory.add_evidence(item)
    memory.put_semantic_block(
        SemanticBlock(
            block_id="SB1",
            content="historical cognition",
            raw_evidence_ids=("E1",),
            occurred_start=item.occurred_at,
            occurred_end=item.occurred_at,
            compiler_version="test",
            lineage_id="main",
            derived_known_at=item.effective_known_at,
        )
    )

    assert memory.list_semantic_blocks_at_knowledge_cutoff(
        datetime(2025, 1, 1, tzinfo=UTC)
    ) == ()

    visible = memory.list_semantic_blocks_at_knowledge_cutoff(
        datetime(2026, 1, 1, tzinfo=UTC)
    )
    assert tuple(block.block_id for block in visible) == ("SB1",)
    assert visible[0].occurred_start.year == 2020


def test_sqlite_roundtrip_preserves_knowledge_time(tmp_path: Path) -> None:
    store = ReferenceMemoryStore(tmp_path / "memory")
    item = _raw("E1", occurred_year=2020, known_year=2026)

    store.add_evidence(item)
    recovered = store.get_evidence("E1")

    assert recovered.occurred_at.year == 2020
    assert recovered.effective_known_at.year == 2026
    store.close()


def test_compiler_accepts_late_known_earlier_logical_evidence() -> None:
    memory = InMemoryReferenceMemory()
    compiler = SemanticCompiler(
        memory,
        None,
        lineage_id="main",
    )

    compiler.process(
        _raw("current", occurred_year=2024, known_year=2024)
    )
    result = compiler.process(
        _raw("late-history", occurred_year=2020, known_year=2026)
    )

    assert result.evidence_id == "late-history"
    assert memory.get_checkpoint("main") is not None
    assert (
        memory.get_checkpoint("main").last_ordering_key
        == datetime(2026, 1, 1, tzinfo=UTC).isoformat()
    )



def test_knowledge_cutoff_preserves_past_wrong_belief_after_later_invalidation() -> None:
    memory = InMemoryReferenceMemory()
    item = _raw("E-old", occurred_year=2020, known_year=2020)
    memory.add_evidence(item)
    memory.put_semantic_block(
        SemanticBlock(
            block_id="SB-old",
            content="belief later falsified",
            raw_evidence_ids=(item.evidence_id,),
            occurred_start=item.occurred_at,
            occurred_end=item.occurred_at,
            compiler_version="test",
            lineage_id="main",
            derived_known_at=item.effective_known_at,
        )
    )

    before_invalidation = datetime.now(UTC)
    memory.invalidate(item.evidence_id, reason="later correction")
    after_invalidation = datetime.now(UTC)

    assert tuple(
        block.block_id
        for block in memory.list_semantic_blocks_at_knowledge_cutoff(
            before_invalidation
        )
    ) == ("SB-old",)
    assert memory.list_semantic_blocks_at_knowledge_cutoff(
        after_invalidation
    ) == ()


def test_sqlite_historical_validity_replays_lifecycle_at_cutoff(
    tmp_path: Path,
) -> None:
    store = ReferenceMemoryStore(tmp_path / "history-memory")
    item = _raw("E-history", occurred_year=2020, known_year=2020)
    store.add_evidence(item)
    store.put_semantic_block(
        SemanticBlock(
            block_id="SB-history",
            content="historical state",
            raw_evidence_ids=(item.evidence_id,),
            occurred_start=item.occurred_at,
            occurred_end=item.occurred_at,
            compiler_version="test",
            lineage_id="main",
            derived_known_at=item.effective_known_at,
        )
    )

    before_invalidation = datetime.now(UTC)
    store.invalidate(item.evidence_id, reason="later correction")
    after_invalidation = datetime.now(UTC)

    assert store.evidence_valid_at(item.evidence_id, before_invalidation)
    assert not store.evidence_valid_at(item.evidence_id, after_invalidation)
    assert tuple(
        block.block_id
        for block in store.list_semantic_blocks_at_knowledge_cutoff(
            before_invalidation
        )
    ) == ("SB-history",)
    assert store.list_semantic_blocks_at_knowledge_cutoff(
        after_invalidation
    ) == ()
    store.close()



def test_historical_state_vector_survives_later_invalidation_and_rebuild() -> None:
    memory = InMemoryReferenceMemory()
    item = _raw("E-vector", occurred_year=2020, known_year=2020)
    memory.add_evidence(item)
    state = memory.put_semantic_block(
        SemanticBlock(
            block_id="SB-vector",
            content="vector history",
            raw_evidence_ids=(item.evidence_id,),
            occurred_start=item.occurred_at,
            occurred_end=item.occurred_at,
            compiler_version="test",
            lineage_id="main",
            derived_known_at=item.effective_known_at,
        )
    )
    memory.rebuild_vector_index(
        lambda block: (float(block.state_version), 1.0),
        index_version="v1",
    )
    assert state.state_id is not None

    memory.invalidate(item.evidence_id, reason="later correction")
    memory.rebuild_vector_index(
        lambda block: (float(block.state_version), 1.0),
        index_version="v2",
    )

    assert memory.get_vector(
        state.block_id,
        state_id=state.state_id,
    ).values == (1.0, 1.0)
    with pytest.raises(KeyError):
        memory.get_vector(state.block_id)


def test_sqlite_historical_state_vector_survives_rebuild(
    tmp_path: Path,
) -> None:
    store = ReferenceMemoryStore(tmp_path / "vector-history")
    item = _raw("E-sql-vector", occurred_year=2020, known_year=2020)
    store.add_evidence(item)
    state = store.put_semantic_block(
        SemanticBlock(
            block_id="SB-sql-vector",
            content="vector history",
            raw_evidence_ids=(item.evidence_id,),
            occurred_start=item.occurred_at,
            occurred_end=item.occurred_at,
            compiler_version="test",
            lineage_id="main",
            derived_known_at=item.effective_known_at,
        )
    )
    store.rebuild_vector_index(
        lambda block: (float(block.state_version), 2.0),
        index_version="v1",
    )
    assert state.state_id is not None

    store.invalidate(item.evidence_id, reason="later correction")
    store.rebuild_vector_index(
        lambda block: (float(block.state_version), 2.0),
        index_version="v2",
    )

    assert store.get_vector(
        state.block_id,
        state_id=state.state_id,
    ).values == (1.0, 2.0)
    with pytest.raises(KeyError):
        store.get_vector(state.block_id)
    store.close()



def test_bitemporal_divergence_skips_legacy_cognition_evaluation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    memory = InMemoryReferenceMemory()
    core = LceProjectionCore(
        tmp_path / "core",
        memory=memory,
    )

    def forbidden(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError(
            "legacy cognition must not evaluate bitemporal-divergent input"
        )

    monkeypatch.setattr(core.frontier, "candidates", forbidden)
    monkeypatch.setattr(
        core.discovery,
        "higher_order_candidates",
        forbidden,
    )

    result = core.process(
        _raw(
            "retro",
            occurred_year=2020,
            known_year=2026,
        )
    )

    assert result.higher_order_candidates == ()
    assert result.promotions == ()
    core.close()



def test_legacy_path_stays_closed_after_lineage_becomes_bitemporal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    memory = InMemoryReferenceMemory()
    core = LceProjectionCore(
        tmp_path / "core-lineage-barrier",
        memory=memory,
        lineage_id="main",
    )

    core.process(
        _raw(
            "ordinary-before",
            occurred_year=2024,
            known_year=2024,
        )
    )
    core.process(
        _raw(
            "retro-lineage",
            occurred_year=2020,
            known_year=2026,
        )
    )

    def forbidden(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError(
            "legacy cognition must remain closed after bitemporal divergence"
        )

    monkeypatch.setattr(core.frontier, "candidates", forbidden)
    monkeypatch.setattr(
        core.discovery,
        "higher_order_candidates",
        forbidden,
    )

    result = core.process(
        _raw(
            "ordinary-after",
            occurred_year=2027,
            known_year=2027,
        )
    )

    assert result.higher_order_candidates == ()
    assert result.promotions == ()
    core.close()



def test_bitemporal_lineage_barrier_also_applies_to_source_rebuild(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    memory = InMemoryReferenceMemory()
    core = LceProjectionCore(
        tmp_path / "core-rebuild-barrier",
        memory=memory,
        lineage_id="main",
    )
    core.process(
        _raw(
            "barrier-before",
            occurred_year=2024,
            known_year=2024,
        )
    )
    core.process(
        _raw(
            "barrier-retro",
            occurred_year=2020,
            known_year=2026,
        )
    )

    memory.invalidate("barrier-before", reason="later correction")

    def forbidden(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError(
            "legacy higher-order evaluation must stay closed during rebuild"
        )

    monkeypatch.setattr(
        core.discovery,
        "higher_order_candidates",
        forbidden,
    )

    core.source_changed_and_rebuild("barrier-before")
    core.close()

def test_derived_state_known_at_prevents_reinterpretation_time_travel_in_memory() -> None:
    memory = InMemoryReferenceMemory()
    item = _raw("E-derived", occurred_year=2020, known_year=2020)
    memory.add_evidence(item)
    original = memory.put_semantic_block(
        SemanticBlock(
            block_id="SB-derived",
            content="original interpretation",
            raw_evidence_ids=(item.evidence_id,),
            occurred_start=item.occurred_at,
            occurred_end=item.occurred_at,
            compiler_version="test",
            lineage_id="main",
            derived_known_at=item.effective_known_at,
        )
    )
    revised_time = datetime(2026, 6, 1, tzinfo=UTC)
    revised = memory.extend_semantic_block(
        original.block_id,
        content="later reinterpretation",
        evidence_id=item.evidence_id,
        occurred_at=item.occurred_at,
        derived_known_at=revised_time,
    )

    before = memory.list_semantic_blocks_at_knowledge_cutoff(
        datetime(2025, 1, 1, tzinfo=UTC)
    )
    after = memory.list_semantic_blocks_at_knowledge_cutoff(
        revised_time
    )

    assert len(before) == 1
    assert before[0].state_id == original.state_id
    assert len(after) == 1
    assert after[0].state_id == revised.state_id
    assert revised.derived_known_at == revised_time


def test_derived_state_known_at_survives_sqlite_restart(
    tmp_path: Path,
) -> None:
    root = tmp_path / "derived-state-time"
    item = _raw("E-derived-sql", occurred_year=2020, known_year=2020)
    first = ReferenceMemoryStore(root)
    first.add_evidence(item)
    original = first.put_semantic_block(
        SemanticBlock(
            block_id="SB-derived-sql",
            content="original interpretation",
            raw_evidence_ids=(item.evidence_id,),
            occurred_start=item.occurred_at,
            occurred_end=item.occurred_at,
            compiler_version="test",
            lineage_id="main",
            derived_known_at=item.effective_known_at,
        )
    )
    revised_time = datetime(2026, 6, 1, tzinfo=UTC)
    revised = first.extend_semantic_block(
        original.block_id,
        content="later reinterpretation",
        evidence_id=item.evidence_id,
        occurred_at=item.occurred_at,
        derived_known_at=revised_time,
    )
    first.close()

    restarted = ReferenceMemoryStore(root)
    before = restarted.list_semantic_blocks_at_knowledge_cutoff(
        datetime(2025, 1, 1, tzinfo=UTC)
    )
    after = restarted.list_semantic_blocks_at_knowledge_cutoff(
        revised_time + timedelta(seconds=1)
    )

    assert len(before) == 1
    assert before[0].state_id == original.state_id
    assert len(after) == 1
    assert after[0].state_id == revised.state_id
    assert restarted.get_semantic_block_state(
        revised.state_id or ""
    ).derived_known_at == revised_time
    restarted.close()
