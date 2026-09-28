"""SQLite persistence for LCE-owned derived projection state only.

Unlike ReferenceMemoryStore, this store contains no canonical Raw Evidence
table. Source IDs are retained as provenance references, never copied as a
second factual database.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from lce.reference_memory.contracts import (
    CompilerCheckpoint,
    SemanticBlock,
    VectorProjection,
)

_PIPELINE_STAGE_ORDER = {
    "compiled": 1,
    "vector-ready": 2,
    "snapshot/discovery-evaluated": 3,
    "worktree-support-evaluated": 4,
    "promotion-evaluated": 5,
    "complete": 6,
}


class SqliteProjectionStateStore:
    """Restart-safe derived state with no source/canonical mutation surface."""

    DB_FILENAME = "projection_state.sqlite"

    def __init__(self, storage_root: Path | str) -> None:
        self._root = Path(storage_root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._db_path = self._root / self.DB_FILENAME
        self._conn = sqlite3.connect(str(self._db_path), timeout=30.0)
        self._conn.executescript(
            """
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
                FOREIGN KEY (block_id) REFERENCES semantic_blocks(block_id)
            );
            CREATE TABLE IF NOT EXISTS semantic_block_states (
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
                derived_known_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(block_id, state_version)
            );
            CREATE TABLE IF NOT EXISTS vector_projections (
                block_id TEXT PRIMARY KEY,
                values_json TEXT NOT NULL,
                index_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (block_id) REFERENCES semantic_blocks(block_id)
            );
            CREATE TABLE IF NOT EXISTS vector_state_projections (
                block_id TEXT NOT NULL,
                state_id TEXT NOT NULL PRIMARY KEY,
                values_json TEXT NOT NULL,
                index_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (state_id) REFERENCES semantic_block_states(state_id)
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
                processed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pipeline_progress (
                evidence_id TEXT PRIMARY KEY,
                stage TEXT NOT NULL,
                fingerprint TEXT
            );
            """
        )
        state_columns = {
            str(row[1])
            for row in self._conn.execute(
                "PRAGMA table_info(semantic_block_states)"
            )
        }
        if "derived_known_at" not in state_columns:
            self._conn.execute(
                "ALTER TABLE semantic_block_states "
                "ADD COLUMN derived_known_at TEXT"
            )
            self._conn.execute(
                "UPDATE semantic_block_states "
                "SET derived_known_at = created_at "
                "WHERE derived_known_at IS NULL"
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
            raise RuntimeError("SqliteProjectionStateStore is closed")
        return self._conn

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo != UTC:
            raise ValueError("stored datetime is not UTC")
        return parsed

    @staticmethod
    def _state_id(block: SemanticBlock) -> str:
        payload = {
            "block_id": block.block_id,
            "state_version": block.state_version,
            "content": block.content,
            "raw_evidence_ids": block.raw_evidence_ids,
            "occurred_start": block.occurred_start.isoformat(),
            "occurred_end": block.occurred_end.isoformat(),
            "compiler_version": block.compiler_version,
            "lineage_id": block.lineage_id,
            "metadata": dict(block.metadata),
            "derived_known_at": (
                block.derived_known_at.isoformat()
                if block.derived_known_at is not None
                else None
            ),
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()[:24]
        return f"state_{digest}"

    def _write_current_state(
        self, db: sqlite3.Connection, block: SemanticBlock
    ) -> SemanticBlock:
        if block.derived_known_at is None:
            block = replace(
                block,
                derived_known_at=datetime.now(UTC),
            )
        state_id = block.state_id or self._state_id(block)
        stored = replace(block, state_id=state_id)
        metadata_json = json.dumps(
            dict(stored.metadata), ensure_ascii=False, sort_keys=True
        )
        db.execute(
            """
            INSERT OR IGNORE INTO semantic_block_states (
                state_id, block_id, state_version, content,
                occurred_start, occurred_end, compiler_version, lineage_id,
                metadata_json, raw_evidence_ids_json, derived_known_at,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stored.state_id,
                stored.block_id,
                stored.state_version,
                stored.content,
                stored.occurred_start.isoformat(),
                stored.occurred_end.isoformat(),
                stored.compiler_version,
                stored.lineage_id,
                metadata_json,
                json.dumps(stored.raw_evidence_ids),
                stored.derived_known_at.isoformat(),
                datetime.now(UTC).isoformat(),
            ),
        )
        existing = db.execute(
            "SELECT block_id FROM semantic_blocks WHERE block_id = ?",
            (stored.block_id,),
        ).fetchone()
        if existing is None:
            db.execute(
                "INSERT INTO semantic_blocks VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    stored.block_id,
                    stored.content,
                    stored.occurred_start.isoformat(),
                    stored.occurred_end.isoformat(),
                    stored.compiler_version,
                    stored.lineage_id,
                    metadata_json,
                ),
            )
        else:
            db.execute(
                "UPDATE semantic_blocks SET content=?, occurred_start=?, occurred_end=?, "
                "compiler_version=?, lineage_id=?, metadata_json=? WHERE block_id=?",
                (
                    stored.content,
                    stored.occurred_start.isoformat(),
                    stored.occurred_end.isoformat(),
                    stored.compiler_version,
                    stored.lineage_id,
                    metadata_json,
                    stored.block_id,
                ),
            )
            db.execute(
                "DELETE FROM semantic_block_evidence WHERE block_id = ?",
                (stored.block_id,),
            )
        db.executemany(
            "INSERT OR IGNORE INTO semantic_block_evidence(block_id, evidence_id) VALUES (?, ?)",
            [(stored.block_id, evidence_id) for evidence_id in stored.raw_evidence_ids],
        )
        return stored

    def put_semantic_block(self, block: SemanticBlock) -> SemanticBlock:
        existing = self._db().execute(
            "SELECT 1 FROM semantic_blocks WHERE block_id = ?",
            (block.block_id,),
        ).fetchone()
        if existing is not None:
            current = self.get_semantic_block(block.block_id)
            if (
                current.content != block.content
                or current.occurred_start != block.occurred_start
                or current.occurred_end != block.occurred_end
                or current.compiler_version != block.compiler_version
                or current.lineage_id != block.lineage_id
                or dict(current.metadata) != dict(block.metadata)
            ):
                raise ValueError(
                    f"block_id '{block.block_id}' already has different immutable content"
                )
            return current
        with self._db():
            return self._write_current_state(self._db(), block)

    def extend_semantic_block(
        self,
        block_id: str,
        *,
        content: str | None,
        evidence_id: str,
        occurred_at: datetime,
        derived_known_at: datetime | None = None,
    ) -> SemanticBlock:
        current = self.get_semantic_block(block_id)
        evidence_ids = (
            current.raw_evidence_ids
            if evidence_id in current.raw_evidence_ids
            else current.raw_evidence_ids + (evidence_id,)
        )
        merged_content = current.content
        if content and content.strip() and content.strip() not in current.content:
            merged_content = f"{current.content}\n{content.strip()}"
        updated = SemanticBlock(
            block_id=current.block_id,
            content=merged_content,
            raw_evidence_ids=evidence_ids,
            occurred_start=min(current.occurred_start, occurred_at),
            occurred_end=max(current.occurred_end, occurred_at),
            compiler_version=current.compiler_version,
            lineage_id=current.lineage_id,
            metadata=current.metadata,
            state_version=current.state_version + 1,
            derived_known_at=(
                derived_known_at or datetime.now(UTC)
            ),
        )
        with self._db():
            return self._write_current_state(self._db(), updated)

    def get_semantic_block(self, block_id: str) -> SemanticBlock:
        row = self._db().execute(
            "SELECT block_id, content, occurred_start, occurred_end, compiler_version, "
            "lineage_id, metadata_json FROM semantic_blocks WHERE block_id = ?",
            (block_id,),
        ).fetchone()
        if row is None:
            raise KeyError(block_id)
        evidence_ids = tuple(
            item[0]
            for item in self._db().execute(
                "SELECT evidence_id FROM semantic_block_evidence "
                "WHERE block_id = ? ORDER BY rowid",
                (block_id,),
            ).fetchall()
        )
        state = self._db().execute(
            "SELECT state_id, state_version, derived_known_at "
            "FROM semantic_block_states "
            "WHERE block_id = ? ORDER BY state_version DESC LIMIT 1",
            (block_id,),
        ).fetchone()
        return SemanticBlock(
            block_id=row[0],
            content=row[1],
            raw_evidence_ids=evidence_ids,
            occurred_start=self._parse_datetime(row[2]),
            occurred_end=self._parse_datetime(row[3]),
            compiler_version=row[4],
            lineage_id=row[5],
            metadata=json.loads(row[6]),
            state_id=str(state[0]) if state else None,
            state_version=int(state[1]) if state else 1,
            derived_known_at=(
                self._parse_datetime(str(state[2]))
                if state and state[2] is not None
                else None
            ),
        )

    def get_semantic_block_state(self, state_id: str) -> SemanticBlock:
        row = self._db().execute(
            "SELECT state_id, block_id, state_version, content, occurred_start, "
            "occurred_end, compiler_version, lineage_id, metadata_json, "
            "raw_evidence_ids_json, derived_known_at "
            "FROM semantic_block_states WHERE state_id = ?",
            (state_id,),
        ).fetchone()
        if row is None:
            raise KeyError(state_id)
        return SemanticBlock(
            block_id=row[1],
            content=row[3],
            raw_evidence_ids=tuple(json.loads(row[9])),
            occurred_start=self._parse_datetime(row[4]),
            occurred_end=self._parse_datetime(row[5]),
            compiler_version=row[6],
            lineage_id=row[7],
            metadata=json.loads(row[8]),
            state_id=row[0],
            state_version=int(row[2]),
            derived_known_at=(
                self._parse_datetime(str(row[10]))
                if row[10] is not None
                else None
            ),
        )

    def list_semantic_blocks(self) -> tuple[SemanticBlock, ...]:
        ids = tuple(
            row[0]
            for row in self._db().execute(
                "SELECT block_id FROM semantic_blocks ORDER BY occurred_start, block_id"
            )
        )
        return tuple(self.get_semantic_block(block_id) for block_id in ids)

    def list_semantic_block_states(self) -> tuple[SemanticBlock, ...]:
        rows = self._db().execute(
            "SELECT state_id FROM semantic_block_states "
            "ORDER BY occurred_start, block_id, state_version"
        ).fetchall()
        return tuple(self.get_semantic_block_state(row[0]) for row in rows)

    def list_semantic_blocks_at_cutoff(
        self, cutoff: datetime
    ) -> tuple[SemanticBlock, ...]:
        if cutoff.tzinfo != UTC:
            raise ValueError("cutoff must be UTC")
        latest: dict[str, SemanticBlock] = {}
        for state in self.list_semantic_block_states():
            if state.occurred_end <= cutoff:
                prior = latest.get(state.block_id)
                if prior is None or state.state_version > prior.state_version:
                    latest[state.block_id] = state
        return tuple(
            sorted(
                latest.values(),
                key=lambda block: (block.occurred_start, block.block_id),
            )
        )

    def delete_vector_index(self) -> None:
        with self._db():
            self._db().execute("DELETE FROM vector_projections")
            self._db().execute("DELETE FROM vector_state_projections")

    def replace_vector_index(
        self,
        blocks: tuple[SemanticBlock, ...],
        embedder: Callable[[SemanticBlock], tuple[float, ...]],
        *,
        index_version: str,
    ) -> None:
        db = self._db()
        with db:
            db.execute("DELETE FROM vector_projections")
            db.execute("DELETE FROM vector_state_projections")
            current_by_block = {
                block.block_id: self.get_semantic_block(block.block_id).state_id
                for block in blocks
            }
            for block in blocks:
                if block.state_id is None:
                    raise ValueError("vector projection requires immutable Semantic Block state")
                values = tuple(float(value) for value in embedder(block))
                db.execute(
                    "INSERT OR REPLACE INTO vector_state_projections VALUES (?, ?, ?, ?, ?)",
                    (
                        block.block_id,
                        block.state_id,
                        json.dumps(values),
                        index_version,
                        datetime.now(UTC).isoformat(),
                    ),
                )
                if current_by_block.get(block.block_id) == block.state_id:
                    db.execute(
                        "INSERT OR REPLACE INTO vector_projections VALUES (?, ?, ?, ?)",
                        (
                            block.block_id,
                            json.dumps(values),
                            index_version,
                            datetime.now(UTC).isoformat(),
                        ),
                    )

    def vector_projection_ids(self) -> tuple[str, ...]:
        return tuple(
            row[0]
            for row in self._db().execute(
                "SELECT block_id FROM vector_projections ORDER BY block_id"
            )
        )

    def get_vector(
        self, block_id: str, *, state_id: str | None = None
    ) -> VectorProjection:
        if state_id is None:
            query = (
                "SELECT block_id, values_json, index_version "
                "FROM vector_projections WHERE block_id = ?"
            )
            params: tuple[object, ...] = (block_id,)
        else:
            query = (
                "SELECT block_id, values_json, index_version "
                "FROM vector_state_projections WHERE block_id = ? AND state_id = ?"
            )
            params = (block_id, state_id)
        row = self._db().execute(query, params).fetchone()
        if row is None:
            raise KeyError(block_id)
        return VectorProjection(
            row[0],
            tuple(float(value) for value in json.loads(row[1])),
            row[2],
        )

    def save_checkpoint(self, checkpoint: CompilerCheckpoint) -> None:
        with self._db():
            self._save_checkpoint(self._db(), checkpoint)

    @staticmethod
    def _save_checkpoint(
        db: sqlite3.Connection, checkpoint: CompilerCheckpoint
    ) -> None:
        db.execute(
            "INSERT INTO compiler_checkpoints VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(lineage_id) DO UPDATE SET "
            "last_ordering_key=excluded.last_ordering_key, "
            "open_block_id=excluded.open_block_id, "
            "compiler_version=excluded.compiler_version, "
            "state_json=excluded.state_json",
            (
                checkpoint.lineage_id,
                checkpoint.last_ordering_key,
                checkpoint.open_block_id,
                checkpoint.compiler_version,
                json.dumps(
                    dict(checkpoint.state), ensure_ascii=False, sort_keys=True
                ),
            ),
        )

    def get_checkpoint(self, lineage_id: str) -> CompilerCheckpoint | None:
        row = self._db().execute(
            "SELECT lineage_id, last_ordering_key, open_block_id, "
            "compiler_version, state_json FROM compiler_checkpoints "
            "WHERE lineage_id = ?",
            (lineage_id,),
        ).fetchone()
        if row is None:
            return None
        return CompilerCheckpoint(
            row[0], row[1], row[2], row[3], json.loads(row[4])
        )

    def commit_compilation(
        self,
        *,
        evidence_id: str,
        lineage_id: str,
        block_states: tuple[SemanticBlock, ...],
        block_ids: tuple[str, ...],
        decision: Mapping[str, object],
        checkpoint: CompilerCheckpoint,
    ) -> None:
        db = self._db()
        with db:
            for block in block_states:
                self._write_current_state(db, block)
            db.execute(
                "INSERT OR REPLACE INTO compiled_evidence VALUES (?, ?, ?, ?, ?)",
                (
                    evidence_id,
                    lineage_id,
                    json.dumps(block_ids),
                    json.dumps(
                        dict(decision), ensure_ascii=False, sort_keys=True
                    ),
                    datetime.now(UTC).isoformat(),
                ),
            )
            self._save_checkpoint(db, checkpoint)
            self._mark_pipeline_stage_db(
                db, evidence_id, "compiled", None
            )

    def compiled_block_ids(
        self, evidence_id: str
    ) -> tuple[str, ...] | None:
        row = self._db().execute(
            "SELECT block_ids_json FROM compiled_evidence WHERE evidence_id = ?",
            (evidence_id,),
        ).fetchone()
        return None if row is None else tuple(json.loads(row[0]))

    def mark_pending_failure(
        self, lineage_id: str, *, evidence_id: str, ordering_key: str
    ) -> None:
        checkpoint = self.get_checkpoint(lineage_id)
        state = dict(checkpoint.state) if checkpoint else {}
        state["pending_evidence_id"] = evidence_id
        state["pending_ordering_key"] = ordering_key
        pending = CompilerCheckpoint(
            lineage_id=lineage_id,
            last_ordering_key=(
                checkpoint.last_ordering_key if checkpoint else None
            ),
            open_block_id=checkpoint.open_block_id if checkpoint else None,
            compiler_version=(
                checkpoint.compiler_version
                if checkpoint
                else "lce-semantic-stream-v1"
            ),
            state=state,
        )
        self.save_checkpoint(pending)

    def get_pipeline_stage(self, evidence_id: str) -> str | None:
        row = self._db().execute(
            "SELECT stage FROM pipeline_progress WHERE evidence_id = ?",
            (evidence_id,),
        ).fetchone()
        return str(row[0]) if row else None

    def get_pipeline_progress(
        self, evidence_id: str
    ) -> tuple[str, str | None] | None:
        row = self._db().execute(
            "SELECT stage, fingerprint FROM pipeline_progress WHERE evidence_id = ?",
            (evidence_id,),
        ).fetchone()
        if row is None:
            return None
        return (
            str(row[0]),
            str(row[1]) if row[1] is not None else None,
        )

    def _mark_pipeline_stage_db(
        self,
        db: sqlite3.Connection,
        evidence_id: str,
        stage: str,
        fingerprint: str | None,
    ) -> None:
        current = db.execute(
            "SELECT stage, fingerprint FROM pipeline_progress "
            "WHERE evidence_id = ?",
            (evidence_id,),
        ).fetchone()
        if (
            current is not None
            and _PIPELINE_STAGE_ORDER.get(str(current[0]), 0)
            > _PIPELINE_STAGE_ORDER.get(stage, 0)
        ):
            return
        if current is not None and fingerprint is None:
            fingerprint = (
                str(current[1]) if current[1] is not None else None
            )
        db.execute(
            "INSERT INTO pipeline_progress VALUES (?, ?, ?) "
            "ON CONFLICT(evidence_id) DO UPDATE SET "
            "stage=excluded.stage, fingerprint=excluded.fingerprint",
            (evidence_id, stage, fingerprint),
        )

    def mark_pipeline_stage(
        self,
        evidence_id: str,
        stage: str,
        *,
        fingerprint: str | None = None,
    ) -> None:
        with self._db():
            self._mark_pipeline_stage_db(
                self._db(), evidence_id, stage, fingerprint
            )
