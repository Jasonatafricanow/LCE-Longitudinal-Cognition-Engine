"""SQLite implementation of BaselineStorePort with pointer HEAD and atomic transactions."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from lce.contracts.baseline import Baseline, BaselineHistory
from lce.contracts.consolidation import LceError
from lce.reference_memory.contracts import AuthorizedSelectedSupport
from lce.store.interface import BaselineStorePort

_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS baseline_revisions (
    baseline_id          TEXT PRIMARY KEY,
    region_id            TEXT NOT NULL,
    revision_number      INTEGER NOT NULL,
    content              TEXT NOT NULL,
    content_hash         TEXT NOT NULL,
    previous_baseline_id TEXT,
    created_at           TEXT NOT NULL,
    model_trace_json     TEXT NOT NULL DEFAULT '{}',
    supporting_state_ids_json TEXT NOT NULL DEFAULT '[]',
    selected_support_json TEXT NOT NULL DEFAULT '[]',
    UNIQUE (region_id, revision_number)
);

CREATE TABLE IF NOT EXISTS baseline_memory_refs (
    baseline_id TEXT NOT NULL,
    memory_id   TEXT NOT NULL,
    PRIMARY KEY (baseline_id, memory_id),
    FOREIGN KEY (baseline_id) REFERENCES baseline_revisions(baseline_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS baselines_head (
    region_id   TEXT PRIMARY KEY,
    baseline_id TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    FOREIGN KEY (baseline_id) REFERENCES baseline_revisions(baseline_id)
);
"""


class StorageIntegrityError(LceError):
    """Raised when storage constraints or revision sequences are violated."""


class SqliteBaselineStore(BaselineStorePort):
    """Durable SQLite storage for LCE baselines.

    Caller supplies the storage root directory (e.g. per-namespace directory).
    Enforces atomic transaction for revision persistence, pointer-only HEAD table,
    and zero raw memory tables.
    """

    DB_FILENAME = "lce_baselines.sqlite"

    def __init__(self, storage_root: Path | str) -> None:
        self._storage_root = Path(storage_root)
        self._storage_root.mkdir(parents=True, exist_ok=True)
        self._db_path = self._storage_root / self.DB_FILENAME
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self._db_path),
                timeout=30.0,
                autocommit=True,
            )
            self._conn.execute("PRAGMA foreign_keys = ON;")
            fk_status = self._conn.execute("PRAGMA foreign_keys;").fetchone()
            if fk_status is None or fk_status[0] != 1:
                raise StorageIntegrityError("Failed to enable SQLite foreign keys enforcement")
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        conn.executescript(_SCHEMA)
        columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(baseline_revisions)")}
        if "supporting_state_ids_json" not in columns:
            conn.execute("ALTER TABLE baseline_revisions ADD COLUMN supporting_state_ids_json TEXT NOT NULL DEFAULT '[]'")
        if "selected_support_json" not in columns:
            conn.execute("ALTER TABLE baseline_revisions ADD COLUMN selected_support_json TEXT NOT NULL DEFAULT '[]'")

    def get_head(self, region_id: str) -> Baseline | None:
        """Fetch current HEAD baseline via pointer join."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT r.baseline_id, r.region_id, r.revision_number, r.content,
                   r.content_hash, r.previous_baseline_id, r.created_at, r.model_trace_json,
                   r.supporting_state_ids_json, r.selected_support_json
            FROM baselines_head h
            JOIN baseline_revisions r ON h.baseline_id = r.baseline_id
            WHERE h.region_id = ?
            """,
            (region_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        baseline_id = row[0]
        cursor.execute(
            """
            SELECT memory_id
            FROM baseline_memory_refs
            WHERE baseline_id = ?
            ORDER BY rowid ASC
            """,
            (baseline_id,),
        )
        mem_refs = tuple(r[0] for r in cursor.fetchall())
        state_refs = tuple(json.loads(row[8]))
        selected_support = tuple(
            AuthorizedSelectedSupport(block_id=str(value["block_id"]), state_id=str(value["state_id"]))
            for value in json.loads(row[9])
        )

        model_trace: Mapping[str, object] = json.loads(row[7])
        created_at = datetime.fromisoformat(row[6])

        return Baseline(
            baseline_id=row[0],
            region_id=row[1],
            revision_number=row[2],
            content=row[3],
            content_hash=row[4],
            previous_baseline_id=row[5],
            created_at=created_at,
            supporting_memory_ids=mem_refs,
            model_trace=model_trace,
            supporting_state_ids=state_refs,
            selected_support=selected_support,
        )

    def save_revision(self, baseline: Baseline) -> None:
        """Atomically persist revision, supporting refs, and advance HEAD pointer."""
        conn = self._get_connection()
        conn.execute("BEGIN IMMEDIATE;")
        try:
            current_head = self.get_head(baseline.region_id)

            # Validate monotonic revision sequence
            if current_head is None:
                if baseline.revision_number != 1 or baseline.previous_baseline_id is not None:
                    raise StorageIntegrityError(
                        f"First revision for region '{baseline.region_id}' must have "
                        f"revision_number=1 and previous_baseline_id=None, got "
                        f"rev={baseline.revision_number}, prev={baseline.previous_baseline_id}"
                    )
            else:
                expected_rev = current_head.revision_number + 1
                if baseline.revision_number != expected_rev:
                    raise StorageIntegrityError(
                        f"Expected revision_number={expected_rev} for region '{baseline.region_id}', "
                        f"got {baseline.revision_number}"
                    )
                if baseline.previous_baseline_id != current_head.baseline_id:
                    raise StorageIntegrityError(
                        f"Expected previous_baseline_id='{current_head.baseline_id}' for region "
                        f"'{baseline.region_id}', got '{baseline.previous_baseline_id}'"
                    )

            now_iso = datetime.now(UTC).isoformat()
            trace_json = json.dumps(baseline.model_trace, sort_keys=True)

            # 1. Insert revision
            conn.execute(
                """
                INSERT INTO baseline_revisions (
                    baseline_id, region_id, revision_number, content,
                    content_hash, previous_baseline_id, created_at, model_trace_json,
                    supporting_state_ids_json, selected_support_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    baseline.baseline_id,
                    baseline.region_id,
                    baseline.revision_number,
                    baseline.content,
                    baseline.content_hash,
                    baseline.previous_baseline_id,
                    baseline.created_at.isoformat(),
                    trace_json,
                    json.dumps(baseline.supporting_state_ids),
                    json.dumps([{"block_id": value.block_id, "state_id": value.state_id}
                                for value in baseline.selected_support], sort_keys=True),
                ),
            )
            # 2. Insert memory references
            conn.executemany(
                """
                INSERT INTO baseline_memory_refs (baseline_id, memory_id)
                VALUES (?, ?)
                """,
                [(baseline.baseline_id, m_id) for m_id in baseline.supporting_memory_ids],
            )
            # 3. Advance/Upsert HEAD pointer
            conn.execute(
                """
                INSERT INTO baselines_head (region_id, baseline_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(region_id) DO UPDATE SET
                    baseline_id = excluded.baseline_id,
                    updated_at = excluded.updated_at
                """,
                (baseline.region_id, baseline.baseline_id, now_iso),
            )
            conn.execute("COMMIT;")
        except Exception as exc:
            if conn.in_transaction:
                try:
                    conn.execute("ROLLBACK;")
                except sqlite3.Error:
                    pass
            if isinstance(exc, sqlite3.IntegrityError):
                raise StorageIntegrityError(
                    f"Integrity error saving revision {baseline.baseline_id}: {exc}"
                ) from exc
            raise

    def get_history(self, region_id: str, limit: int | None = None) -> BaselineHistory:
        """Fetch historical revisions ordered by revision descending."""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT baseline_id, region_id, revision_number, content,
                   content_hash, previous_baseline_id, created_at, model_trace_json,
                   supporting_state_ids_json, selected_support_json
            FROM baseline_revisions
            WHERE region_id = ?
            ORDER BY revision_number DESC
        """
        params: list[object] = [region_id]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        revisions: list[Baseline] = []
        for row in rows:
            b_id = row[0]
            cursor.execute(
                """
                SELECT memory_id
                FROM baseline_memory_refs
                WHERE baseline_id = ?
                ORDER BY rowid ASC
                """,
                (b_id,),
            )
            mem_refs = tuple(r[0] for r in cursor.fetchall())
            state_refs = tuple(json.loads(row[8]))
            selected_support = tuple(
                AuthorizedSelectedSupport(block_id=str(value["block_id"]), state_id=str(value["state_id"]))
                for value in json.loads(row[9])
            )
            created_at = datetime.fromisoformat(row[6])
            model_trace: Mapping[str, object] = json.loads(row[7])

            revisions.append(
                Baseline(
                    baseline_id=row[0],
                    region_id=row[1],
                    revision_number=row[2],
                    content=row[3],
                    content_hash=row[4],
                    previous_baseline_id=row[5],
                    created_at=created_at,
                    supporting_memory_ids=mem_refs,
                    model_trace=model_trace,
                    supporting_state_ids=state_refs,
                    selected_support=selected_support,
                )
            )

        return BaselineHistory(region_id=region_id, revisions=tuple(revisions))

    def list_regions(self) -> tuple[str, ...]:
        """Return baseline lineages for targeted dependency propagation."""
        rows = self._get_connection().execute(
            "SELECT region_id FROM baselines_head ORDER BY region_id"
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
