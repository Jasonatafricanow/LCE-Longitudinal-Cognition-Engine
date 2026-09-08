"""SQLite Reference Memory implementation with canonical/derived separation."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

from lce.reference_memory.contracts import (
    AuditEvent,
    CompilerCheckpoint,
    RawEvidence,
    SemanticBlock,
    VectorProjection,
)


class ReferenceMemoryStore:
    """Restart-safe local Memory substrate for standalone LCE."""

    DB_FILENAME = "reference_memory.sqlite"

    def __init__(self, storage_root: Path | str) -> None:
        self._root = Path(storage_root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._db_path = self._root / self.DB_FILENAME
        self._conn = sqlite3.connect(str(self._db_path), timeout=30.0)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS raw_evidence (
                evidence_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                ordering_key TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                state TEXT NOT NULL,
                superseded_by TEXT,
                created_at TEXT NOT NULL,
                CHECK (state IN ('VALID', 'INVALID', 'SUPERSEDED'))
            );
            CREATE TABLE IF NOT EXISTS raw_evidence_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                reason TEXT,
                occurred_at TEXT NOT NULL,
                FOREIGN KEY (evidence_id) REFERENCES raw_evidence(evidence_id)
            );
            CREATE TABLE IF NOT EXISTS semantic_blocks (
                block_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                occurred_start TEXT NOT NULL,
                occurred_end TEXT NOT NULL,
                compiler_version TEXT NOT NULL,
                lineage_id TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS semantic_block_evidence (
                block_id TEXT NOT NULL,
                evidence_id TEXT NOT NULL,
                PRIMARY KEY (block_id, evidence_id),
                FOREIGN KEY (block_id) REFERENCES semantic_blocks(block_id),
                FOREIGN KEY (evidence_id) REFERENCES raw_evidence(evidence_id)
            );
            CREATE TABLE IF NOT EXISTS vector_projections (
                block_id TEXT PRIMARY KEY,
                values_json TEXT NOT NULL,
                index_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (block_id) REFERENCES semantic_blocks(block_id)
            );
            CREATE TABLE IF NOT EXISTS compiler_checkpoints (
                lineage_id TEXT PRIMARY KEY,
                last_ordering_key TEXT,
                open_block_id TEXT,
                compiler_version TEXT NOT NULL,
                state_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS compiled_evidence (
                evidence_id TEXT PRIMARY KEY,
                lineage_id TEXT NOT NULL,
                block_ids_json TEXT NOT NULL,
                decision_json TEXT NOT NULL,
                processed_at TEXT NOT NULL,
                FOREIGN KEY (evidence_id) REFERENCES raw_evidence(evidence_id)
            );
            """
        )
        self._conn.commit()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None  # type: ignore[assignment]

    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("ReferenceMemoryStore is closed")
        return self._conn

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo != UTC:
            raise ValueError("stored datetime is not UTC")
        return parsed

    @staticmethod
    def _canonical_provenance(provenance: Mapping[str, object]) -> str:
        if not provenance.get("source") or provenance.get("canonical") is not True:
            raise ValueError("canonical source provenance is required")
        if provenance.get("derived") is True:
            raise ValueError("derived cognition cannot be written as evidence")
        return json.dumps(dict(provenance), ensure_ascii=False, sort_keys=True)

    def add_evidence(self, item: RawEvidence) -> RawEvidence:
        provenance_json = self._canonical_provenance(item.provenance)
        db = self._db()
        existing = db.execute(
            "SELECT content, occurred_at, ordering_key, provenance_json, state, superseded_by "
            "FROM raw_evidence WHERE evidence_id = ?",
            (item.evidence_id,),
        ).fetchone()
        if existing is not None:
            expected = (
                item.content,
                item.occurred_at.isoformat(),
                item.effective_ordering_key,
                provenance_json,
            )
            if tuple(existing[:4]) != expected:
                raise ValueError(f"evidence_id '{item.evidence_id}' already has different immutable content")
            return RawEvidence(
                evidence_id=item.evidence_id,
                content=existing[0],
                occurred_at=self._parse_datetime(existing[1]),
                ordering_key=existing[2],
                provenance=json.loads(existing[3]),
                state=existing[4],
                superseded_by=existing[5],
            )
        db.execute(
            "INSERT INTO raw_evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                item.evidence_id,
                item.content,
                item.occurred_at.isoformat(),
                item.effective_ordering_key,
                provenance_json,
                item.state,
                item.superseded_by,
                datetime.now(UTC).isoformat(),
            ),
        )
        db.execute(
            "INSERT INTO raw_evidence_events(evidence_id, event_type, reason, occurred_at) VALUES (?, 'ADMITTED', NULL, ?)",
            (item.evidence_id, datetime.now(UTC).isoformat()),
        )
        db.commit()
        return item

    def get_evidence(self, evidence_id: str) -> RawEvidence:
        row = self._db().execute(
            "SELECT evidence_id, content, occurred_at, ordering_key, provenance_json, state, superseded_by "
            "FROM raw_evidence WHERE evidence_id = ?",
            (evidence_id,),
        ).fetchone()
        if row is None:
            raise KeyError(evidence_id)
        return RawEvidence(
            evidence_id=row[0],
            content=row[1],
            occurred_at=self._parse_datetime(row[2]),
            ordering_key=row[3],
            provenance=json.loads(row[4]),
            state=row[5],
            superseded_by=row[6],
        )

    def list_current_valid_evidence(self) -> tuple[RawEvidence, ...]:
        rows = self._db().execute(
            "SELECT evidence_id FROM raw_evidence WHERE state = 'VALID' AND superseded_by IS NULL "
            "ORDER BY ordering_key, evidence_id"
        ).fetchall()
        return tuple(self.get_evidence(row[0]) for row in rows)

    def invalidate(self, evidence_id: str, *, reason: str) -> None:
        item = self.get_evidence(evidence_id)
        db = self._db()
        if item.state == "INVALID":
            return
        db.execute(
            "UPDATE raw_evidence SET state = 'INVALID', superseded_by = NULL WHERE evidence_id = ?",
            (evidence_id,),
        )
        db.execute(
            "INSERT INTO raw_evidence_events(evidence_id, event_type, reason, occurred_at) VALUES (?, 'INVALIDATED', ?, ?)",
            (evidence_id, reason, datetime.now(UTC).isoformat()),
        )
        db.commit()

    def supersede(self, evidence_id: str, replacement_evidence_id: str) -> None:
        self.get_evidence(evidence_id)
        replacement = self.get_evidence(replacement_evidence_id)
        if not replacement.current_valid:
            raise ValueError("replacement evidence must be current-valid")
        db = self._db()
        db.execute(
            "UPDATE raw_evidence SET state = 'SUPERSEDED', superseded_by = ? WHERE evidence_id = ?",
            (replacement_evidence_id, evidence_id),
        )
        db.execute(
            "INSERT INTO raw_evidence_events(evidence_id, event_type, reason, occurred_at) VALUES (?, 'SUPERSEDED', ?, ?)",
            (evidence_id, replacement_evidence_id, datetime.now(UTC).isoformat()),
        )
        db.commit()

    def audit_events(self, evidence_id: str) -> tuple[AuditEvent, ...]:
        rows = self._db().execute(
            "SELECT evidence_id, event_type, reason, occurred_at FROM raw_evidence_events "
            "WHERE evidence_id = ? ORDER BY event_id",
            (evidence_id,),
        ).fetchall()
        return tuple(
            AuditEvent(row[0], row[1], row[2], self._parse_datetime(row[3])) for row in rows
        )

    def put_semantic_block(self, block: SemanticBlock) -> SemanticBlock:
        db = self._db()
        for evidence_id in block.raw_evidence_ids:
            self.get_evidence(evidence_id)
        metadata_json = json.dumps(dict(block.metadata), ensure_ascii=False, sort_keys=True)
        existing = db.execute(
            "SELECT content, occurred_start, occurred_end, compiler_version, lineage_id, metadata_json "
            "FROM semantic_blocks WHERE block_id = ?",
            (block.block_id,),
        ).fetchone()
        if existing is not None:
            expected = (
                block.content,
                block.occurred_start.isoformat(),
                block.occurred_end.isoformat(),
                block.compiler_version,
                block.lineage_id,
                metadata_json,
            )
            if tuple(existing) != expected:
                raise ValueError(f"block_id '{block.block_id}' already has different immutable content")
            return self.get_semantic_block(block.block_id)
        db.execute(
            "INSERT INTO semantic_blocks VALUES (?, ?, ?, ?, ?, ?, ?)",
            (block.block_id, block.content, block.occurred_start.isoformat(), block.occurred_end.isoformat(),
             block.compiler_version, block.lineage_id, metadata_json),
        )
        db.executemany(
            "INSERT INTO semantic_block_evidence(block_id, evidence_id) VALUES (?, ?)",
            [(block.block_id, evidence_id) for evidence_id in block.raw_evidence_ids],
        )
        db.commit()
        return block

    def get_semantic_block(self, block_id: str) -> SemanticBlock:
        row = self._db().execute(
            "SELECT block_id, content, occurred_start, occurred_end, compiler_version, lineage_id, metadata_json "
            "FROM semantic_blocks WHERE block_id = ?",
            (block_id,),
        ).fetchone()
        if row is None:
            raise KeyError(block_id)
        evidence_ids = tuple(
            item[0]
            for item in self._db().execute(
                "SELECT evidence_id FROM semantic_block_evidence WHERE block_id = ? ORDER BY rowid",
                (block_id,),
            ).fetchall()
        )
        return SemanticBlock(
            block_id=row[0],
            content=row[1],
            raw_evidence_ids=evidence_ids,
            occurred_start=self._parse_datetime(row[2]),
            occurred_end=self._parse_datetime(row[3]),
            compiler_version=row[4],
            lineage_id=row[5],
            metadata=json.loads(row[6]),
        )

    def list_semantic_blocks(self, *, current_valid_only: bool = True) -> tuple[SemanticBlock, ...]:
        ids = [row[0] for row in self._db().execute("SELECT block_id FROM semantic_blocks ORDER BY occurred_start, block_id")]
        blocks = tuple(self.get_semantic_block(block_id) for block_id in ids)
        if not current_valid_only:
            return blocks
        return tuple(
            block
            for block in blocks
            if all(self.get_evidence(evidence_id).current_valid for evidence_id in block.raw_evidence_ids)
        )

    def delete_vector_index(self) -> None:
        self._db().execute("DELETE FROM vector_projections")
        self._db().commit()

    def rebuild_vector_index(
        self,
        embedder: Callable[[SemanticBlock], tuple[float, ...]],
        *,
        index_version: str,
    ) -> None:
        db = self._db()
        db.execute("DELETE FROM vector_projections")
        for block in self.list_semantic_blocks(current_valid_only=True):
            values = tuple(float(value) for value in embedder(block))
            projection = VectorProjection(block.block_id, values, index_version)
            db.execute(
                "INSERT INTO vector_projections VALUES (?, ?, ?, ?)",
                (projection.block_id, json.dumps(projection.values), projection.index_version, datetime.now(UTC).isoformat()),
            )
        db.commit()

    def vector_projection_ids(self) -> tuple[str, ...]:
        return tuple(row[0] for row in self._db().execute("SELECT block_id FROM vector_projections ORDER BY block_id"))

    def get_vector(self, block_id: str) -> VectorProjection:
        row = self._db().execute(
            "SELECT block_id, values_json, index_version FROM vector_projections WHERE block_id = ?",
            (block_id,),
        ).fetchone()
        if row is None:
            raise KeyError(block_id)
        return VectorProjection(row[0], tuple(float(value) for value in json.loads(row[1])), row[2])

    def save_checkpoint(self, checkpoint: CompilerCheckpoint) -> None:
        self._db().execute(
            "INSERT INTO compiler_checkpoints VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(lineage_id) DO UPDATE SET last_ordering_key=excluded.last_ordering_key, "
            "open_block_id=excluded.open_block_id, compiler_version=excluded.compiler_version, state_json=excluded.state_json",
            (checkpoint.lineage_id, checkpoint.last_ordering_key, checkpoint.open_block_id,
             checkpoint.compiler_version, json.dumps(dict(checkpoint.state), ensure_ascii=False, sort_keys=True)),
        )
        self._db().commit()

    def get_checkpoint(self, lineage_id: str) -> CompilerCheckpoint | None:
        row = self._db().execute(
            "SELECT lineage_id, last_ordering_key, open_block_id, compiler_version, state_json "
            "FROM compiler_checkpoints WHERE lineage_id = ?",
            (lineage_id,),
        ).fetchone()
        if row is None:
            return None
        return CompilerCheckpoint(row[0], row[1], row[2], row[3], json.loads(row[4]))

    def record_compiled_evidence(
        self, evidence_id: str, lineage_id: str, block_ids: tuple[str, ...], decision: Mapping[str, object]
    ) -> None:
        self._db().execute(
            "INSERT OR REPLACE INTO compiled_evidence VALUES (?, ?, ?, ?, ?)",
            (evidence_id, lineage_id, json.dumps(block_ids), json.dumps(dict(decision), ensure_ascii=False, sort_keys=True), datetime.now(UTC).isoformat()),
        )
        self._db().commit()

    def compiled_block_ids(self, evidence_id: str) -> tuple[str, ...] | None:
        row = self._db().execute("SELECT block_ids_json FROM compiled_evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
        if row is None:
            return None
        return tuple(json.loads(row[0]))
