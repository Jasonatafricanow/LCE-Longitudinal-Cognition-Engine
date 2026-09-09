"""Persistent OPEN/MERGED/DROPPED cognition worktrees."""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from lce.contracts.baseline import Baseline
from lce.reference_memory.contracts import AuthorizedSelectedSupport


@dataclass(frozen=True, slots=True)
class CognitionWorktree:
    worktree_id: str
    region_id: str
    base_baseline_id: str | None
    base_revision: int | None
    candidate_content: str
    supporting_block_ids: tuple[str, ...]
    supporting_structure_ids: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    status: str
    needs_rebuild: bool = False
    merged_baseline_id: str | None = None
    applicability: str | None = None
    unresolved: str | None = None
    interpretation_trace: Mapping[str, object] = field(default_factory=dict)
    selected_support: tuple[AuthorizedSelectedSupport, ...] = ()
    processing_input_id: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"OPEN", "MERGED", "DROPPED"}:
            raise ValueError("worktree status must be OPEN, MERGED, or DROPPED")
        if not self.candidate_content.strip():
            raise ValueError("candidate_content must be non-empty")
        if len({item.block_id for item in self.selected_support}) != len(self.selected_support):
            raise ValueError("selected_support contains duplicate block IDs")
        if self.selected_support and not {item.block_id for item in self.selected_support}.issubset(self.supporting_block_ids):
            raise ValueError("selected_support block IDs must belong to supporting_block_ids")
        if len({item.state_id for item in self.selected_support}) != len(self.selected_support):
            raise ValueError("selected_support contains duplicate state IDs")


def _now() -> datetime:
    return datetime.now(UTC)


class CognitionWorktreeStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.root / "cognition_worktrees.sqlite"))
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS worktrees (
                worktree_id TEXT PRIMARY KEY,
                region_id TEXT NOT NULL,
                base_baseline_id TEXT,
                base_revision INTEGER,
                candidate_content TEXT NOT NULL,
                supporting_block_ids_json TEXT NOT NULL,
                supporting_structure_ids_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('OPEN', 'MERGED', 'DROPPED')),
                needs_rebuild INTEGER NOT NULL DEFAULT 0,
                merged_baseline_id TEXT,
                applicability TEXT,
                unresolved TEXT,
                interpretation_trace_json TEXT NOT NULL DEFAULT '{}',
                selected_support_json TEXT NOT NULL DEFAULT '[]',
                processing_input_id TEXT
            );
            CREATE TABLE IF NOT EXISTS support_cycles (
                worktree_id TEXT NOT NULL,
                snapshot_id TEXT NOT NULL,
                PRIMARY KEY(worktree_id, snapshot_id),
                FOREIGN KEY(worktree_id) REFERENCES worktrees(worktree_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS support_observations (
                worktree_id TEXT NOT NULL,
                support_identity TEXT NOT NULL,
                PRIMARY KEY(worktree_id, support_identity),
                FOREIGN KEY(worktree_id) REFERENCES worktrees(worktree_id) ON DELETE CASCADE
            );
            """
        )
        columns = {str(row[1]) for row in self.conn.execute("PRAGMA table_info(worktrees)")}
        if "interpretation_trace_json" not in columns:
            self.conn.execute("ALTER TABLE worktrees ADD COLUMN interpretation_trace_json TEXT NOT NULL DEFAULT '{}'")
        if "selected_support_json" not in columns:
            self.conn.execute("ALTER TABLE worktrees ADD COLUMN selected_support_json TEXT NOT NULL DEFAULT '[]'")
        if "processing_input_id" not in columns:
            self.conn.execute("ALTER TABLE worktrees ADD COLUMN processing_input_id TEXT")
        self.conn.commit()

    @staticmethod
    def _tuple(values: Iterable[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(str(value) for value in values if str(value).strip()))

    def create(
        self,
        *,
        region_id: str,
        candidate_content: str,
        supporting_block_ids: tuple[str, ...],
        supporting_structure_ids: tuple[str, ...],
        base_baseline: Baseline | None,
        applicability: str | None = None,
        unresolved: str | None = None,
        interpretation_trace: Mapping[str, object] | None = None,
        selected_support: tuple[AuthorizedSelectedSupport, ...] = (),
        processing_input_id: str | None = None,
    ) -> CognitionWorktree:
        now = _now()
        selected = tuple(selected_support)
        block_ids = self._tuple(supporting_block_ids)
        item = CognitionWorktree(
            worktree_id=f"wt_{uuid.uuid4().hex}",
            region_id=region_id,
            base_baseline_id=base_baseline.baseline_id if base_baseline else None,
            base_revision=base_baseline.revision_number if base_baseline else None,
            candidate_content=candidate_content,
            supporting_block_ids=block_ids,
            supporting_structure_ids=self._tuple(supporting_structure_ids),
            created_at=now,
            updated_at=now,
            status="OPEN",
            applicability=applicability,
            unresolved=unresolved,
            interpretation_trace=interpretation_trace or {},
            selected_support=selected,
            processing_input_id=processing_input_id,
        )
        if not item.supporting_block_ids:
            raise ValueError("a worktree requires at least one supporting Semantic Block")
        self.conn.execute(
            """
            INSERT INTO worktrees (
                worktree_id, region_id, base_baseline_id, base_revision, candidate_content,
                supporting_block_ids_json, supporting_structure_ids_json, created_at, updated_at,
                status, needs_rebuild, merged_baseline_id, applicability, unresolved,
                interpretation_trace_json, selected_support_json, processing_input_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (item.worktree_id, item.region_id, item.base_baseline_id, item.base_revision, item.candidate_content,
             json.dumps(item.supporting_block_ids), json.dumps(item.supporting_structure_ids), item.created_at.isoformat(),
             item.updated_at.isoformat(), item.status, 0, None, item.applicability, item.unresolved,
             json.dumps(dict(item.interpretation_trace), ensure_ascii=False, sort_keys=True),
             json.dumps([{"block_id": value.block_id, "state_id": value.state_id} for value in item.selected_support],
                        ensure_ascii=False, sort_keys=True), item.processing_input_id),
        )
        self.conn.commit()
        return item

    def _row_to_item(self, row: tuple[object, ...]) -> CognitionWorktree:
        return CognitionWorktree(
            worktree_id=str(row[0]), region_id=str(row[1]),
            base_baseline_id=str(row[2]) if row[2] is not None else None,
            base_revision=int(str(row[3])) if row[3] is not None else None,
            candidate_content=str(row[4]),
            supporting_block_ids=tuple(json.loads(str(row[5]))),
            supporting_structure_ids=tuple(json.loads(str(row[6]))),
            created_at=datetime.fromisoformat(str(row[7])), updated_at=datetime.fromisoformat(str(row[8])),
            status=str(row[9]), needs_rebuild=bool(row[10]),
            merged_baseline_id=str(row[11]) if row[11] is not None else None,
            applicability=str(row[12]) if row[12] is not None else None,
            unresolved=str(row[13]) if row[13] is not None else None,
            interpretation_trace=json.loads(str(row[14])) if row[14] is not None else {},
            selected_support=tuple(
                AuthorizedSelectedSupport(block_id=str(value["block_id"]), state_id=str(value["state_id"]))
                for value in json.loads(str(row[15]))
            ) if len(row) > 15 and row[15] is not None else (),
            processing_input_id=str(row[16]) if len(row) > 16 and row[16] is not None else None,
        )

    def get(self, worktree_id: str) -> CognitionWorktree:
        row = self.conn.execute("SELECT * FROM worktrees WHERE worktree_id = ?", (worktree_id,)).fetchone()
        if row is None:
            raise KeyError(worktree_id)
        return self._row_to_item(row)

    def list(self, *, status: str | None = None) -> tuple[CognitionWorktree, ...]:
        if status is None:
            rows = self.conn.execute("SELECT * FROM worktrees ORDER BY created_at").fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM worktrees WHERE status = ? ORDER BY created_at", (status,)).fetchall()
        return tuple(self._row_to_item(row) for row in rows)

    def find_open_by_region(self, region_id: str) -> CognitionWorktree | None:
        row = self.conn.execute(
            "SELECT * FROM worktrees WHERE region_id = ? AND status = 'OPEN' ORDER BY created_at LIMIT 1",
            (region_id,),
        ).fetchone()
        return self._row_to_item(row) if row is not None else None

    def find_by_region_and_input(self, region_id: str, processing_input_id: str) -> CognitionWorktree | None:
        row = self.conn.execute(
            "SELECT * FROM worktrees WHERE region_id = ? AND processing_input_id = ? ORDER BY updated_at DESC LIMIT 1",
            (region_id, processing_input_id),
        ).fetchone()
        return self._row_to_item(row) if row is not None else None

    def update_support(
        self,
        worktree_id: str,
        *,
        add_block_ids: tuple[str, ...] = (),
        remove_block_ids: tuple[str, ...] = (),
        add_structure_ids: tuple[str, ...] = (),
        remove_structure_ids: tuple[str, ...] = (),
        selected_support: tuple[AuthorizedSelectedSupport, ...] | None = None,
        processing_input_id: str | None = None,
    ) -> CognitionWorktree:
        item = self.get(worktree_id)
        if item.status != "OPEN":
            raise ValueError("only OPEN worktrees can change support")
        blocks = [value for value in item.supporting_block_ids if value not in remove_block_ids]
        structures = [value for value in item.supporting_structure_ids if value not in remove_structure_ids]
        blocks.extend(add_block_ids)
        structures.extend(add_structure_ids)
        selected = item.selected_support
        if selected_support is not None:
            selected = tuple(selected_support)
        if not blocks:
            raise ValueError("an OPEN worktree must retain at least one supporting block")
        now = _now()
        self.conn.execute(
            "UPDATE worktrees SET supporting_block_ids_json=?, supporting_structure_ids_json=?, selected_support_json=?, processing_input_id=COALESCE(?, processing_input_id), updated_at=? WHERE worktree_id=?",
            (json.dumps(self._tuple(blocks)), json.dumps(self._tuple(structures)),
             json.dumps([{"block_id": value.block_id, "state_id": value.state_id} for value in selected],
                        ensure_ascii=False, sort_keys=True), processing_input_id, now.isoformat(), worktree_id),
        )
        self.conn.commit()
        return self.get(worktree_id)

    def record_support(
        self, worktree_id: str, *, snapshot_id: str, support_identity: str | None = None,
        processing_input_id: str | None = None,
    ) -> bool:
        self.get(worktree_id)
        identity = support_identity or snapshot_id
        result = self.conn.execute(
            "INSERT OR IGNORE INTO support_observations VALUES (?, ?)", (worktree_id, identity)
        )
        inserted = result.rowcount > 0
        if processing_input_id is not None:
            self.conn.execute(
                "UPDATE worktrees SET processing_input_id=?, updated_at=? WHERE worktree_id=?",
                (processing_input_id, _now().isoformat(), worktree_id),
            )
        self.conn.commit()
        return inserted

    def support_cycle_count(self, worktree_id: str) -> int:
        row = self.conn.execute("SELECT COUNT(*) FROM support_observations WHERE worktree_id = ?", (worktree_id,)).fetchone()
        return int(row[0]) if row else 0

    def support_identities(self, worktree_id: str) -> tuple[str, ...]:
        rows = self.conn.execute(
            "SELECT support_identity FROM support_observations WHERE worktree_id = ? ORDER BY support_identity",
            (worktree_id,),
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def update_candidate(
        self,
        worktree_id: str,
        *,
        candidate_content: str,
        interpretation_trace: Mapping[str, object] | None = None,
    ) -> CognitionWorktree:
        item = self.get(worktree_id)
        if item.status != "OPEN":
            raise ValueError("only OPEN worktrees can change candidate content")
        self.conn.execute(
            "UPDATE worktrees SET candidate_content=?, interpretation_trace_json=?, updated_at=? WHERE worktree_id=?",
            (candidate_content, json.dumps(dict(interpretation_trace or item.interpretation_trace), sort_keys=True),
             _now().isoformat(), worktree_id),
        )
        self.conn.commit()
        return self.get(worktree_id)

    def clear_needs_rebuild(self, worktree_id: str) -> CognitionWorktree:
        self.get(worktree_id)
        self.conn.execute(
            "UPDATE worktrees SET needs_rebuild=0, updated_at=? WHERE worktree_id=?",
            (_now().isoformat(), worktree_id),
        )
        self.conn.commit()
        return self.get(worktree_id)

    def set_status(self, worktree_id: str, status: str, *, merged_baseline_id: str | None = None) -> CognitionWorktree:
        if status not in {"OPEN", "MERGED", "DROPPED"}:
            raise ValueError("worktree status must be OPEN, MERGED, or DROPPED")
        self.get(worktree_id)
        self.conn.execute(
            "UPDATE worktrees SET status=?, merged_baseline_id=?, updated_at=? WHERE worktree_id=?",
            (status, merged_baseline_id, _now().isoformat(), worktree_id),
        )
        self.conn.commit()
        return self.get(worktree_id)

    def mark_needs_rebuild(self, worktree_id: str) -> CognitionWorktree:
        self.get(worktree_id)
        self.conn.execute(
            "UPDATE worktrees SET needs_rebuild=1, updated_at=? WHERE worktree_id=?",
            (_now().isoformat(), worktree_id),
        )
        self.conn.commit()
        return self.get(worktree_id)

    def close(self) -> None:
        self.conn.close()
