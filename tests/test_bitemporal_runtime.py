from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

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
