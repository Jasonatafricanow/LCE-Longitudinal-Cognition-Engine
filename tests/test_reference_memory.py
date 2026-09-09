from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lce.reference_memory.contracts import (
    RawEvidence,
    ReferenceMemoryPort,
    SemanticBlock,
)
from lce.reference_memory.sqlite import ReferenceMemoryStore


def evidence(evidence_id: str, content: str, *, when: int = 0) -> RawEvidence:
    return RawEvidence(
        evidence_id=evidence_id,
        content=content,
        occurred_at=datetime(2026, 1, 1 + when, tzinfo=UTC),
        ordering_key=f"{when:04d}:{evidence_id}",
        provenance={"source": "synthetic", "canonical": True, "lineage": "test"},
    )


def test_reference_memory_is_a_replaceable_port() -> None:
    class Double:
        def __init__(self) -> None:
            self.items: dict[str, RawEvidence] = {}

        def add_evidence(self, item: RawEvidence) -> RawEvidence:
            self.items[item.evidence_id] = item
            return item

        def list_current_valid_evidence(self) -> tuple[RawEvidence, ...]:
            return tuple(self.items.values())

    double = Double()
    assert isinstance(double, ReferenceMemoryPort)
    item = evidence("E1", "stable source")
    assert double.add_evidence(item) == item


def test_evidence_and_semantic_block_ids_survive_restart(tmp_path) -> None:
    db_root = tmp_path / "memory"
    item = evidence("E-stable", "a canonical observation")
    block = SemanticBlock(
        block_id="SB-stable",
        content="canonical observation",
        raw_evidence_ids=(item.evidence_id,),
        occurred_start=item.occurred_at,
        occurred_end=item.occurred_at,
        compiler_version="test-v1",
        lineage_id="lineage",
    )

    first = ReferenceMemoryStore(db_root)
    first.add_evidence(item)
    first.put_semantic_block(block)
    first.close()

    second = ReferenceMemoryStore(db_root)
    assert second.get_evidence("E-stable").evidence_id == "E-stable"
    assert second.get_semantic_block("SB-stable").block_id == "SB-stable"
    second.close()


def test_invalidate_and_supersede_remove_evidence_from_current_valid_view(tmp_path) -> None:
    store = ReferenceMemoryStore(tmp_path / "memory")
    old = evidence("E-old", "old fact")
    replacement = evidence("E-new", "replacement fact", when=1)
    store.add_evidence(old)
    store.add_evidence(replacement)

    store.supersede("E-old", "E-new")
    assert tuple(item.evidence_id for item in store.list_current_valid_evidence()) == ("E-new",)
    assert store.get_evidence("E-old").superseded_by == "E-new"
    assert store.audit_events("E-old")[-1].event_type == "SUPERSEDED"

    store.invalidate("E-new", reason="synthetic correction")
    assert store.list_current_valid_evidence() == ()
    assert store.audit_events("E-new")[-1].event_type == "INVALIDATED"
    store.close()


def test_derived_cognition_cannot_be_written_as_canonical_evidence(tmp_path) -> None:
    store = ReferenceMemoryStore(tmp_path / "memory")
    with pytest.raises(ValueError, match="derived"):
        store.add_evidence(
            RawEvidence(
                evidence_id="derived-1",
                content="candidate understanding",
                occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
                provenance={"source": "lce", "canonical": True, "derived": True},
            )
        )
    store.close()


def test_unknown_source_is_not_silently_canonical(tmp_path) -> None:
    store = ReferenceMemoryStore(tmp_path / "memory")
    with pytest.raises(ValueError, match="canonical source"):
        store.add_evidence(
            RawEvidence(
                evidence_id="unknown-1",
                content="unattributed",
                occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
                provenance={"source": "unknown", "canonical": False},
            )
        )
    store.close()
