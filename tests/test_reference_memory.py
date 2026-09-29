from __future__ import annotations

from datetime import UTC, datetime
import sqlite3

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
        derived_known_at=item.effective_known_at,
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

def test_reference_memory_rejects_missing_derived_known_at(
    tmp_path,
) -> None:
    store = ReferenceMemoryStore(tmp_path / "derived-time-required")
    item = evidence("E-required", "source")
    store.add_evidence(item)
    with pytest.raises(
        ValueError,
        match="derived_known_at must be supplied",
    ):
        store.put_semantic_block(
            SemanticBlock(
                block_id="SB-required",
                content="derived state",
                raw_evidence_ids=(item.evidence_id,),
                occurred_start=item.occurred_at,
                occurred_end=item.occurred_at,
                compiler_version="test-v1",
                lineage_id="lineage",
            )
        )
    store.close()


def test_sqlite_semantic_block_metadata_roundtrips_canonically(
    tmp_path,
) -> None:
    store = ReferenceMemoryStore(tmp_path / "metadata-canonical")
    item = evidence("E-meta", "source")
    store.add_evidence(item)
    written = store.put_semantic_block(
        SemanticBlock(
            block_id="SB-meta",
            content="derived state",
            raw_evidence_ids=(item.evidence_id,),
            occurred_start=item.occurred_at,
            occurred_end=item.occurred_at,
            compiler_version="test-v1",
            lineage_id="lineage",
            metadata={
                "vector": (1.0, 2.0),
                "nested": {"path": ["a", "b"]},
            },
            derived_known_at=item.effective_known_at,
        )
    )
    persisted = store.get_semantic_block_state(
        written.state_id or ""
    )

    assert written == persisted
    assert written.metadata["vector"] == (1.0, 2.0)
    assert written.metadata["nested"] == {"path": ("a", "b")}
    store.close()


def test_legacy_state_migration_uses_raw_knowledge_time_not_row_creation_time(
    tmp_path,
) -> None:
    root = tmp_path / "legacy-derived-time"
    root.mkdir()
    db_path = root / ReferenceMemoryStore.DB_FILENAME
    occurred = datetime(2020, 1, 1, tzinfo=UTC)
    known = datetime(2020, 3, 1, tzinfo=UTC)
    created = datetime(2026, 9, 29, tzinfo=UTC)

    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE raw_evidence (
                evidence_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                known_at TEXT,
                ordering_key TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                state TEXT NOT NULL,
                superseded_by TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE semantic_blocks (
                block_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                occurred_start TEXT NOT NULL,
                occurred_end TEXT NOT NULL,
                compiler_version TEXT NOT NULL,
                lineage_id TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );
            CREATE TABLE semantic_block_evidence (
                block_id TEXT NOT NULL,
                evidence_id TEXT NOT NULL,
                PRIMARY KEY (block_id, evidence_id)
            );
            CREATE TABLE semantic_block_states (
                state_id TEXT PRIMARY KEY,
                block_id TEXT NOT NULL,
                state_version INTEGER NOT NULL,
                content TEXT NOT NULL,
                occurred_start TEXT NOT NULL,
                occurred_end TEXT NOT NULL,
                compiler_version TEXT NOT NULL,
                lineage_id TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                raw_evidence_ids_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(block_id, state_version)
            );
            """
        )
        conn.execute(
            "INSERT INTO raw_evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "LEGACY-E",
                "legacy source",
                occurred.isoformat(),
                known.isoformat(),
                known.isoformat(),
                '{"canonical": true, "source": "legacy"}',
                "VALID",
                None,
                created.isoformat(),
            ),
        )
        conn.execute(
            "INSERT INTO semantic_blocks VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "LEGACY-B",
                "legacy state",
                occurred.isoformat(),
                occurred.isoformat(),
                "legacy-v1",
                "legacy",
                "{}",
            ),
        )
        conn.execute(
            "INSERT INTO semantic_block_evidence VALUES (?, ?)",
            ("LEGACY-B", "LEGACY-E"),
        )
        conn.execute(
            "INSERT INTO semantic_block_states VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "legacy-state",
                "LEGACY-B",
                1,
                "legacy state",
                occurred.isoformat(),
                occurred.isoformat(),
                "legacy-v1",
                "legacy",
                "{}",
                '["LEGACY-E"]',
                created.isoformat(),
            ),
        )

    store = ReferenceMemoryStore(root)
    migrated = store.get_semantic_block_state("legacy-state")

    assert migrated.derived_known_at == known
    assert tuple(
        block.block_id
        for block in store.list_semantic_blocks_at_knowledge_cutoff(
            datetime(2020, 6, 1, tzinfo=UTC)
        )
    ) == ("LEGACY-B",)
    store.close()


@pytest.mark.parametrize(
    ("metadata", "error_type", "message"),
    (
        ({1: "a"}, TypeError, "keys must be strings"),
        ({"value": float("nan")}, ValueError, "floats must be finite"),
        ({"value": float("inf")}, ValueError, "floats must be finite"),
        ({"value": {1, 2}}, TypeError, "JSON-compatible"),
        ({"value": b"bytes"}, TypeError, "JSON-compatible"),
        (
            {"value": datetime(2026, 1, 1, tzinfo=UTC)},
            TypeError,
            "JSON-compatible",
        ),
    ),
)
def test_semantic_block_metadata_rejects_backend_divergent_values(
    metadata,
    error_type,
    message,
) -> None:
    when = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(error_type, match=message):
        SemanticBlock(
            block_id="metadata-invalid",
            content="invalid metadata",
            raw_evidence_ids=("E-invalid",),
            occurred_start=when,
            occurred_end=when,
            compiler_version="test",
            lineage_id="test",
            metadata=metadata,
            derived_known_at=when,
        )
