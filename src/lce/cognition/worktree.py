"""Persistent OPEN/MERGED/DROPPED cognition worktrees."""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from lce.contracts.baseline import Baseline


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

    def __post_init__(self) -> None:
        if self.status not in {"OPEN", "MERGED", "DROPPED"}:
            raise ValueError("worktree status must be OPEN, MERGED, or DROPPED")
        if not self.candidate_content.strip():
            raise ValueError("candidate_content must be non-empty")


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
                unresolved TEXT
            );
            CREATE TABLE IF NOT EXISTS support_cycles (
                worktree_id TEXT NOT NULL,
                snapshot_id TEXT NOT NULL,
                PRIMARY KEY(worktree_id, snapshot_id),
                FOREIGN KEY(worktree_id) REFERENCES worktrees(worktree_id) ON DELETE CASCADE
            );
            """
        )
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
    ) -> CognitionWorktree:
        now = _now()
        item = CognitionWorktree(
            worktree_id=f"wt_{uuid.uuid4().hex}",
            region_id=region_id,
            base_baseline_id=base_baseline.baseline_id if base_baseline else None,
            base_revision=base_baseline.revision_number if base_baseline else None,
            candidate_content=candidate_content,
            supporting_block_ids=self._tuple(supporting_block_ids),
            supporting_structure_ids=self._tuple(supporting_structure_ids),
            created_at=now,
            updated_at=now,
            status="OPEN",
            applicability=applicability,
            unresolved=unresolved,
        )
        if not item.supporting_block_ids:
            raise ValueError("a worktree requires at least one supporting Semantic Block")
        self.conn.execute(
            "INSERT INTO worktrees VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (item.worktree_id, item.region_id, item.base_baseline_id, item.base_revision, item.candidate_content,
             json.dumps(item.supporting_block_ids), json.dumps(item.supporting_structure_ids), item.created_at.isoformat(),
             item.updated_at.isoformat(), item.status, 0, None, item.applicability, item.unresolved),
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

    def update_support(
        self,
        worktree_id: str,
        *,
        add_block_ids: tuple[str, ...] = (),
        remove_block_ids: tuple[str, ...] = (),
        add_structure_ids: tuple[str, ...] = (),
        remove_structure_ids: tuple[str, ...] = (),
    ) -> CognitionWorktree:
        item = self.get(worktree_id)
        if item.status != "OPEN":
            raise ValueError("only OPEN worktrees can change support")
        blocks = [value for value in item.supporting_block_ids if value not in remove_block_ids]
        structures = [value for value in item.supporting_structure_ids if value not in remove_structure_ids]
        blocks.extend(add_block_ids)
        structures.extend(add_structure_ids)
        if not blocks:
            raise ValueError("an OPEN worktree must retain at least one supporting block")
        now = _now()
        self.conn.execute(
            "UPDATE worktrees SET supporting_block_ids_json=?, supporting_structure_ids_json=?, updated_at=? WHERE worktree_id=?",
            (json.dumps(self._tuple(blocks)), json.dumps(self._tuple(structures)), now.isoformat(), worktree_id),
        )
        self.conn.commit()
        return self.get(worktree_id)

    def record_support(self, worktree_id: str, *, snapshot_id: str) -> None:
        self.get(worktree_id)
        self.conn.execute("INSERT OR IGNORE INTO support_cycles VALUES (?, ?)", (worktree_id, snapshot_id))
        self.conn.commit()

    def support_cycle_count(self, worktree_id: str) -> int:
        row = self.conn.execute("SELECT COUNT(*) FROM support_cycles WHERE worktree_id = ?", (worktree_id,)).fetchone()
        return int(row[0]) if row else 0

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
