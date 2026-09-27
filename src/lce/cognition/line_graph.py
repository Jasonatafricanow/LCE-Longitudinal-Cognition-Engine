"""Stable Line identity, branch-aware Worktree DAG, and callable projections.

This module owns only derived cognition references. Raw Evidence remains in the
injected Memory substrate. Branches are implicit paths inside one Line; a node
may have multiple parents, allowing historical divergence and later rejoin
without cloning Line identity.

A Line node is keyed by stable SemanticBlock identity, not immutable state
revision. State revisions are stored under the node so recap/continuation cannot
manufacture new trajectory points.

Callable projections are materialized on demand and are never persisted as
cognition nodes.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from lce.reference_memory.contracts import (
    AuthorizedSelectedSupport,
    ReferenceMemorySubstratePort,
    SemanticBlock,
)


def _require_utc(value: datetime, name: str) -> None:
    if value.tzinfo != UTC:
        raise ValueError(f"{name} must be an aware UTC datetime")


class LineTraversalLimitExceeded(RuntimeError):
    """Exact graph/provenance traversal could not finish within its safety ceiling."""


def _evidence_valid_at(
    memory: ReferenceMemorySubstratePort,
    evidence_id: str,
    cutoff: datetime,
) -> bool:
    reader = getattr(memory, "evidence_valid_at", None)
    if callable(reader):
        return bool(reader(evidence_id, cutoff))
    item = memory.get_evidence(evidence_id)
    return item.effective_known_at <= cutoff and item.current_valid


def _cosine(
    left: tuple[float, ...],
    right: tuple[float, ...],
) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


@dataclass(frozen=True, slots=True)
class LineRecord:
    line_id: str
    seed_block_ids: tuple[str, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.line_id.strip():
            raise ValueError("line_id must be nonempty")
        if not self.seed_block_ids:
            raise ValueError("seed_block_ids must be nonempty")
        if len(set(self.seed_block_ids)) != len(self.seed_block_ids):
            raise ValueError("seed_block_ids must be unique")
        _require_utc(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class LineNode:
    node_id: str
    line_id: str
    block_id: str
    created_at: datetime

    def __post_init__(self) -> None:
        for value, name in (
            (self.node_id, "node_id"),
            (self.line_id, "line_id"),
            (self.block_id, "block_id"),
        ):
            if not value.strip():
                raise ValueError(f"{name} must be nonempty")
        _require_utc(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class LineNodeState:
    node_id: str
    state_id: str
    occurred_start: datetime
    occurred_end: datetime
    knowledge_at: datetime
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.node_id.strip() or not self.state_id.strip():
            raise ValueError("node_id and state_id must be nonempty")
        for value, name in (
            (self.occurred_start, "occurred_start"),
            (self.occurred_end, "occurred_end"),
            (self.knowledge_at, "knowledge_at"),
            (self.created_at, "created_at"),
        ):
            _require_utc(value, name)
        if self.occurred_end < self.occurred_start:
            raise ValueError("occurred_end must not precede occurred_start")


@dataclass(frozen=True, slots=True)
class LineApplyResult:
    line_id: str | None
    created_line: bool
    added_node_ids: tuple[str, ...]
    added_state_ids: tuple[str, ...]
    added_edges: tuple[tuple[str, str], ...]
    unresolved_reason: str | None = None


@dataclass(frozen=True, slots=True)
class CallableLineProjection:
    """Ephemeral consumer view over a bounded local portion of one Line."""

    line_id: str
    anchor_node_id: str
    node_ids: tuple[str, ...]
    selected_support: tuple[AuthorizedSelectedSupport, ...]
    raw_evidence_ids: tuple[str, ...]
    content_fragments: tuple[str, ...]


class LineGraphStore:
    """SQLite persistence for stable Line identities and internal DAG edges."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.root / "line_graph.sqlite"))
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._derivation_fingerprint = "legacy-unknown"
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS lines (
                line_id TEXT PRIMARY KEY,
                seed_block_ids_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS line_nodes (
                node_id TEXT PRIMARY KEY,
                line_id TEXT NOT NULL,
                block_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(line_id, block_id),
                FOREIGN KEY(line_id) REFERENCES lines(line_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS line_node_states (
                node_id TEXT NOT NULL,
                state_id TEXT NOT NULL,
                occurred_start TEXT NOT NULL,
                occurred_end TEXT NOT NULL,
                knowledge_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(node_id, state_id),
                FOREIGN KEY(node_id) REFERENCES line_nodes(node_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS line_edges (
                line_id TEXT NOT NULL,
                parent_node_id TEXT NOT NULL,
                child_node_id TEXT NOT NULL,
                PRIMARY KEY(line_id, parent_node_id, child_node_id),
                FOREIGN KEY(line_id) REFERENCES lines(line_id)
                    ON DELETE CASCADE,
                FOREIGN KEY(parent_node_id) REFERENCES line_nodes(node_id)
                    ON DELETE CASCADE,
                FOREIGN KEY(child_node_id) REFERENCES line_nodes(node_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS line_node_memberships (
                membership_revision_id TEXT PRIMARY KEY,
                node_id TEXT NOT NULL,
                known_at TEXT NOT NULL,
                retired_at TEXT,
                created_at TEXT NOT NULL,
                derivation_fingerprint TEXT NOT NULL,
                FOREIGN KEY(node_id) REFERENCES line_nodes(node_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS line_edge_revisions (
                edge_revision_id TEXT PRIMARY KEY,
                line_id TEXT NOT NULL,
                parent_node_id TEXT NOT NULL,
                child_node_id TEXT NOT NULL,
                known_at TEXT NOT NULL,
                retired_at TEXT,
                created_at TEXT NOT NULL,
                derivation_fingerprint TEXT NOT NULL,
                FOREIGN KEY(line_id, parent_node_id, child_node_id)
                    REFERENCES line_edges(
                        line_id, parent_node_id, child_node_id
                    )
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_line_nodes_block
                ON line_nodes(block_id);
            CREATE INDEX IF NOT EXISTS idx_line_node_states_state
                ON line_node_states(state_id);
            CREATE INDEX IF NOT EXISTS idx_line_membership_node_time
                ON line_node_memberships(node_id, known_at);
            CREATE INDEX IF NOT EXISTS idx_line_edge_revision_time
                ON line_edge_revisions(
                    line_id, parent_node_id, child_node_id, known_at
                );

            CREATE TABLE IF NOT EXISTS line_graph_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        self._ensure_revision_fingerprint_columns()
        self._backfill_structure_revisions()
        self.conn.commit()

    def _ensure_revision_fingerprint_columns(self) -> None:
        for table in (
            "line_node_memberships",
            "line_edge_revisions",
        ):
            columns = {
                str(row[1])
                for row in self.conn.execute(
                    f"PRAGMA table_info({table})"
                )
            }
            if "derivation_fingerprint" not in columns:
                self.conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN "
                    "derivation_fingerprint TEXT NOT NULL "
                    "DEFAULT 'legacy-unknown'"
                )

    @staticmethod
    def _require_fingerprint(value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("derivation fingerprint must be nonempty")
        return value.strip()

    def set_derivation_fingerprint(self, value: str) -> None:
        self._derivation_fingerprint = self._require_fingerprint(value)

    def get_metadata(self, key: str) -> str | None:
        row = self.conn.execute(
            "SELECT value FROM line_graph_metadata WHERE key = ?",
            (key,),
        ).fetchone()
        return str(row[0]) if row is not None else None

    def set_metadata(self, key: str, value: str) -> None:
        if not key.strip():
            raise ValueError("metadata key must be nonempty")
        self.conn.execute(
            "INSERT OR REPLACE INTO line_graph_metadata VALUES (?, ?)",
            (key, value),
        )
        self.conn.commit()

    @staticmethod
    def _revision_id(kind: str, *parts: str) -> str:
        digest = hashlib.sha256(
            "|".join((kind, *parts)).encode()
        ).hexdigest()[:24]
        return f"{kind}_{digest}"

    def _backfill_structure_revisions(self) -> None:
        """Make pre-revision feature-branch graphs cutoff-queryable.

        LineGraph has not shipped on master yet, but preserving existing
        experimental databases makes the migration deterministic instead of
        silently treating old relations as timeless.
        """
        nodes = self.conn.execute(
            "SELECT node_id, created_at FROM line_nodes"
        ).fetchall()
        for node_id, created_at in nodes:
            exists = self.conn.execute(
                "SELECT 1 FROM line_node_memberships "
                "WHERE node_id = ? LIMIT 1",
                (node_id,),
            ).fetchone()
            if exists is not None:
                continue
            row = self.conn.execute(
                "SELECT MIN(knowledge_at) FROM line_node_states "
                "WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            known_at = str(row[0]) if row and row[0] else str(created_at)
            revision_id = self._revision_id(
                "membership", str(node_id), known_at
            )
            self.conn.execute(
                "INSERT OR IGNORE INTO line_node_memberships ("
                "membership_revision_id, node_id, known_at, retired_at, "
                "created_at, derivation_fingerprint"
                ") VALUES (?, ?, ?, NULL, ?, ?)",
                (
                    revision_id,
                    node_id,
                    known_at,
                    created_at,
                    "legacy-unknown",
                ),
            )

        edges = self.conn.execute(
            "SELECT line_id, parent_node_id, child_node_id FROM line_edges"
        ).fetchall()
        for line_id, parent_id, child_id in edges:
            exists = self.conn.execute(
                "SELECT 1 FROM line_edge_revisions "
                "WHERE line_id = ? AND parent_node_id = ? "
                "AND child_node_id = ? LIMIT 1",
                (line_id, parent_id, child_id),
            ).fetchone()
            if exists is not None:
                continue
            rows = self.conn.execute(
                "SELECT created_at FROM line_nodes "
                "WHERE node_id IN (?, ?)",
                (parent_id, child_id),
            ).fetchall()
            known_at = max(str(row[0]) for row in rows)
            revision_id = self._revision_id(
                "edge",
                str(line_id),
                str(parent_id),
                str(child_id),
                known_at,
            )
            self.conn.execute(
                "INSERT OR IGNORE INTO line_edge_revisions ("
                "edge_revision_id, line_id, parent_node_id, child_node_id, "
                "known_at, retired_at, created_at, derivation_fingerprint"
                ") VALUES (?, ?, ?, ?, ?, NULL, ?, ?)",
                (
                    revision_id,
                    line_id,
                    parent_id,
                    child_id,
                    known_at,
                    known_at,
                    "legacy-unknown",
                ),
            )

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        _require_utc(parsed, "stored datetime")
        return parsed

    @staticmethod
    def _line_id(seed_block_ids: tuple[str, ...]) -> str:
        payload = json.dumps(seed_block_ids, separators=(",", ":"))
        digest = hashlib.sha256(payload.encode()).hexdigest()[:24]
        return f"line_{digest}"

    @staticmethod
    def _node_id(line_id: str, block_id: str) -> str:
        digest = hashlib.sha256(
            f"{line_id}|{block_id}".encode()
        ).hexdigest()[:24]
        return f"lnode_{digest}"

    def create_line(
        self,
        seed_block_ids: tuple[str, ...],
        *,
        created_at: datetime | None = None,
        commit: bool = True,
    ) -> LineRecord:
        if not seed_block_ids:
            raise ValueError("a Line seed requires at least one block")
        ordered = tuple(dict.fromkeys(seed_block_ids))
        line_id = self._line_id(ordered)
        existing = self.conn.execute(
            "SELECT line_id FROM lines WHERE line_id = ?",
            (line_id,),
        ).fetchone()
        if existing is not None:
            return self.get_line(line_id)
        now = created_at or datetime.now(UTC)
        _require_utc(now, "created_at")
        self.conn.execute(
            "INSERT INTO lines VALUES (?, ?, ?)",
            (line_id, json.dumps(ordered), now.isoformat()),
        )
        if commit:
            self.conn.commit()
        return LineRecord(line_id, ordered, now)

    def get_line(self, line_id: str) -> LineRecord:
        row = self.conn.execute(
            "SELECT line_id, seed_block_ids_json, created_at "
            "FROM lines WHERE line_id = ?",
            (line_id,),
        ).fetchone()
        if row is None:
            raise KeyError(line_id)
        return LineRecord(
            line_id=str(row[0]),
            seed_block_ids=tuple(json.loads(str(row[1]))),
            created_at=self._parse_datetime(str(row[2])),
        )

    def list_lines(self) -> tuple[LineRecord, ...]:
        rows = self.conn.execute(
            "SELECT line_id FROM lines ORDER BY created_at, line_id"
        ).fetchall()
        return tuple(self.get_line(str(row[0])) for row in rows)

    def ensure_node(
        self,
        line_id: str,
        block: SemanticBlock,
        *,
        knowledge_at: datetime,
        membership_known_at: datetime | None = None,
        commit: bool = True,
    ) -> tuple[LineNode, bool, bool]:
        self.get_line(line_id)
        if block.state_id is None:
            raise ValueError("Line nodes require immutable SemanticBlock states")
        _require_utc(knowledge_at, "knowledge_at")
        membership_at = membership_known_at or knowledge_at
        _require_utc(membership_at, "membership_known_at")
        node_id = self._node_id(line_id, block.block_id)
        existing = self.conn.execute(
            "SELECT node_id FROM line_nodes "
            "WHERE line_id = ? AND block_id = ?",
            (line_id, block.block_id),
        ).fetchone()
        added_node = False
        if existing is None:
            now = datetime.now(UTC)
            self.conn.execute(
                "INSERT INTO line_nodes VALUES (?, ?, ?, ?)",
                (node_id, line_id, block.block_id, now.isoformat()),
            )
            added_node = True
        else:
            node_id = str(existing[0])

        self._activate_membership(
            node_id,
            membership_at,
            commit=False,
        )
        state_result = self.conn.execute(
            """
            INSERT OR IGNORE INTO line_node_states (
                node_id, state_id, occurred_start, occurred_end,
                knowledge_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                node_id,
                block.state_id,
                block.occurred_start.isoformat(),
                block.occurred_end.isoformat(),
                knowledge_at.isoformat(),
                datetime.now(UTC).isoformat(),
            ),
        )
        if commit:
            self.conn.commit()
        return (
            self.get_node(node_id),
            added_node,
            state_result.rowcount > 0,
        )

    def get_node(self, node_id: str) -> LineNode:
        row = self.conn.execute(
            "SELECT node_id, line_id, block_id, created_at "
            "FROM line_nodes WHERE node_id = ?",
            (node_id,),
        ).fetchone()
        if row is None:
            raise KeyError(node_id)
        return LineNode(
            node_id=str(row[0]),
            line_id=str(row[1]),
            block_id=str(row[2]),
            created_at=self._parse_datetime(str(row[3])),
        )

    def get_node_state(
        self,
        node_id: str,
        state_id: str,
    ) -> LineNodeState:
        row = self.conn.execute(
            """
            SELECT node_id, state_id, occurred_start, occurred_end,
                   knowledge_at, created_at
            FROM line_node_states
            WHERE node_id = ? AND state_id = ?
            """,
            (node_id, state_id),
        ).fetchone()
        if row is None:
            raise KeyError((node_id, state_id))
        return LineNodeState(
            node_id=str(row[0]),
            state_id=str(row[1]),
            occurred_start=self._parse_datetime(str(row[2])),
            occurred_end=self._parse_datetime(str(row[3])),
            knowledge_at=self._parse_datetime(str(row[4])),
            created_at=self._parse_datetime(str(row[5])),
        )

    def states_for_node(self, node_id: str) -> tuple[LineNodeState, ...]:
        rows = self.conn.execute(
            "SELECT state_id FROM line_node_states "
            "WHERE node_id = ? ORDER BY knowledge_at, created_at, state_id",
            (node_id,),
        ).fetchall()
        return tuple(
            self.get_node_state(node_id, str(row[0])) for row in rows
        )

    def node_for_block(
        self,
        line_id: str,
        block_id: str,
    ) -> LineNode | None:
        row = self.conn.execute(
            "SELECT node_id FROM line_nodes "
            "WHERE line_id = ? AND block_id = ?",
            (line_id, block_id),
        ).fetchone()
        return self.get_node(str(row[0])) if row is not None else None

    def nodes_for_line(self, line_id: str) -> tuple[LineNode, ...]:
        rows = self.conn.execute(
            "SELECT node_id FROM line_nodes WHERE line_id = ? "
            "ORDER BY created_at, node_id",
            (line_id,),
        ).fetchall()
        return tuple(self.get_node(str(row[0])) for row in rows)

    def membership_active_at(
        self,
        node_id: str,
        knowledge_cutoff: datetime,
    ) -> bool:
        _require_utc(knowledge_cutoff, "knowledge_cutoff")
        cutoff = knowledge_cutoff.isoformat()
        return self.conn.execute(
            "SELECT 1 FROM line_node_memberships "
            "WHERE node_id = ? AND known_at <= ? "
            "AND (retired_at IS NULL OR retired_at > ?) "
            "ORDER BY known_at DESC LIMIT 1",
            (node_id, cutoff, cutoff),
        ).fetchone() is not None

    def _activate_membership(
        self,
        node_id: str,
        knowledge_at: datetime,
        *,
        commit: bool = True,
    ) -> bool:
        _require_utc(knowledge_at, "knowledge_at")
        if self.membership_active_at(node_id, knowledge_at):
            return False
        iso = knowledge_at.isoformat()
        created_at = datetime.now(UTC).isoformat()
        revision_id = self._revision_id(
            "membership",
            node_id,
            iso,
            created_at,
        )
        result = self.conn.execute(
            "INSERT OR IGNORE INTO line_node_memberships ("
            "membership_revision_id, node_id, known_at, retired_at, "
            "created_at, derivation_fingerprint"
            ") VALUES (?, ?, ?, NULL, ?, ?)",
            (
                revision_id,
                node_id,
                iso,
                created_at,
                self._derivation_fingerprint,
            ),
        )
        if commit:
            self.conn.commit()
        return result.rowcount > 0

    def active_node_ids_at(
        self,
        line_id: str,
        knowledge_cutoff: datetime,
    ) -> tuple[str, ...]:
        _require_utc(knowledge_cutoff, "knowledge_cutoff")
        return tuple(
            node.node_id
            for node in self.nodes_for_line(line_id)
            if self.membership_active_at(
                node.node_id,
                knowledge_cutoff,
            )
        )

    def edge_active_at(
        self,
        line_id: str,
        parent_node_id: str,
        child_node_id: str,
        knowledge_cutoff: datetime,
    ) -> bool:
        _require_utc(knowledge_cutoff, "knowledge_cutoff")
        cutoff = knowledge_cutoff.isoformat()
        return self.conn.execute(
            "SELECT 1 FROM line_edge_revisions "
            "WHERE line_id = ? AND parent_node_id = ? "
            "AND child_node_id = ? AND known_at <= ? "
            "AND (retired_at IS NULL OR retired_at > ?) "
            "ORDER BY known_at DESC LIMIT 1",
            (
                line_id,
                parent_node_id,
                child_node_id,
                cutoff,
                cutoff,
            ),
        ).fetchone() is not None

    def edges_for_line_at(
        self,
        line_id: str,
        knowledge_cutoff: datetime,
    ) -> tuple[tuple[str, str], ...]:
        _require_utc(knowledge_cutoff, "knowledge_cutoff")
        rows = self.conn.execute(
            "SELECT parent_node_id, child_node_id FROM line_edges "
            "WHERE line_id = ? ORDER BY parent_node_id, child_node_id",
            (line_id,),
        ).fetchall()
        return tuple(
            (str(parent_id), str(child_id))
            for parent_id, child_id in rows
            if self.edge_active_at(
                line_id,
                str(parent_id),
                str(child_id),
                knowledge_cutoff,
            )
        )

    def parents_at(
        self,
        node_id: str,
        knowledge_cutoff: datetime,
    ) -> tuple[str, ...]:
        node = self.get_node(node_id)
        return tuple(
            parent_id
            for parent_id, child_id in self.edges_for_line_at(
                node.line_id,
                knowledge_cutoff,
            )
            if child_id == node_id
        )

    def children_at(
        self,
        node_id: str,
        knowledge_cutoff: datetime,
    ) -> tuple[str, ...]:
        node = self.get_node(node_id)
        return tuple(
            child_id
            for parent_id, child_id in self.edges_for_line_at(
                node.line_id,
                knowledge_cutoff,
            )
            if parent_id == node_id
        )

    def retire_current_structure(
        self,
        knowledge_cutoff: datetime,
    ) -> None:
        """Retire current derived membership/edges without erasing history."""
        _require_utc(knowledge_cutoff, "knowledge_cutoff")
        cutoff = knowledge_cutoff.isoformat()
        with self.conn:
            edge_rows = self.conn.execute(
                "SELECT edge_revision_id FROM line_edge_revisions "
                "WHERE known_at <= ? "
                "AND (retired_at IS NULL OR retired_at > ?)",
                (cutoff, cutoff),
            ).fetchall()
            for (revision_id,) in edge_rows:
                self.conn.execute(
                    "UPDATE line_edge_revisions SET retired_at = ? "
                    "WHERE edge_revision_id = ?",
                    (cutoff, revision_id),
                )
            membership_rows = self.conn.execute(
                "SELECT membership_revision_id "
                "FROM line_node_memberships WHERE known_at <= ? "
                "AND (retired_at IS NULL OR retired_at > ?)",
                (cutoff, cutoff),
            ).fetchall()
            for (revision_id,) in membership_rows:
                self.conn.execute(
                    "UPDATE line_node_memberships SET retired_at = ? "
                    "WHERE membership_revision_id = ?",
                    (cutoff, revision_id),
                )

    def _reachable(
        self,
        start_node_id: str,
        target_node_id: str,
        *,
        knowledge_cutoff: datetime,
    ) -> bool:
        pending = [start_node_id]
        seen: set[str] = set()
        while pending:
            current = pending.pop()
            if current == target_node_id:
                return True
            if current in seen:
                continue
            seen.add(current)
            pending.extend(
                self.children_at(current, knowledge_cutoff)
            )
        return False

    def add_edge(
        self,
        line_id: str,
        parent_node_id: str,
        child_node_id: str,
        *,
        knowledge_at: datetime | None = None,
        commit: bool = True,
    ) -> bool:
        if parent_node_id == child_node_id:
            raise ValueError("a Line edge cannot self-reference")
        edge_known_at = knowledge_at or datetime.now(UTC)
        _require_utc(edge_known_at, "knowledge_at")
        parent = self.get_node(parent_node_id)
        child = self.get_node(child_node_id)
        if parent.line_id != line_id or child.line_id != line_id:
            raise ValueError("Line edges cannot cross Line identity")
        if self.edge_active_at(
            line_id,
            parent_node_id,
            child_node_id,
            edge_known_at,
        ):
            return False
        if self._reachable(
            parent_node_id,
            child_node_id,
            knowledge_cutoff=edge_known_at,
        ):
            return False
        if self._reachable(
            child_node_id,
            parent_node_id,
            knowledge_cutoff=edge_known_at,
        ):
            raise ValueError("Line edge would create a cycle")
        self.conn.execute(
            "INSERT OR IGNORE INTO line_edges VALUES (?, ?, ?)",
            (line_id, parent_node_id, child_node_id),
        )
        iso = edge_known_at.isoformat()
        created_at = datetime.now(UTC).isoformat()
        revision_id = self._revision_id(
            "edge",
            line_id,
            parent_node_id,
            child_node_id,
            iso,
            created_at,
        )
        result = self.conn.execute(
            "INSERT OR IGNORE INTO line_edge_revisions ("
            "edge_revision_id, line_id, parent_node_id, child_node_id, "
            "known_at, retired_at, created_at, derivation_fingerprint"
            ") VALUES (?, ?, ?, ?, ?, NULL, ?, ?)",
            (
                revision_id,
                line_id,
                parent_node_id,
                child_node_id,
                iso,
                created_at,
                self._derivation_fingerprint,
            ),
        )
        if commit:
            self.conn.commit()
        return result.rowcount > 0

    def parents(self, node_id: str) -> tuple[str, ...]:
        return self.parents_at(node_id, datetime.now(UTC))

    def children(self, node_id: str) -> tuple[str, ...]:
        return self.children_at(node_id, datetime.now(UTC))

    def edges_for_line(
        self, line_id: str
    ) -> tuple[tuple[str, str], ...]:
        return self.edges_for_line_at(line_id, datetime.now(UTC))

    def lines_for_block(self, block_id: str) -> tuple[str, ...]:
        rows = self.conn.execute(
            "SELECT DISTINCT line_id FROM line_nodes "
            "WHERE block_id = ? ORDER BY line_id",
            (block_id,),
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def overlap_counts(
        self, block_ids: tuple[str, ...]
    ) -> dict[str, int]:
        if not block_ids:
            return {}
        placeholders = ",".join("?" for _ in block_ids)
        rows = self.conn.execute(
            f"""
            SELECT line_id, COUNT(DISTINCT block_id)
            FROM line_nodes
            WHERE block_id IN ({placeholders})
            GROUP BY line_id
            """,
            block_ids,
        ).fetchall()
        return {str(row[0]): int(row[1]) for row in rows}

    def close(self) -> None:
        self.conn.close()


@dataclass(frozen=True, slots=True)
class LineAssemblerConfig:
    min_seed_support: int = 3
    min_shared_support: int = 2
    allow_conjunctive_rejoin: bool = False

    def __post_init__(self) -> None:
        if self.min_seed_support < 2:
            raise ValueError("min_seed_support must be >= 2")
        if self.min_shared_support < 1:
            raise ValueError("min_shared_support must be >= 1")
        if type(self.allow_conjunctive_rejoin) is not bool:
            raise TypeError("allow_conjunctive_rejoin must be bool")


class LineAssembler:
    """Conservatively map trajectory paths into stable Line DAGs."""

    def __init__(
        self,
        *,
        memory: ReferenceMemorySubstratePort,
        store: LineGraphStore,
        config: LineAssemblerConfig | None = None,
    ) -> None:
        self.memory = memory
        self.store = store
        self.config = config or LineAssemblerConfig()

    def _knowledge_at(self, block: SemanticBlock) -> datetime:
        return max(
            self.memory.get_evidence(evidence_id).effective_known_at
            for evidence_id in block.raw_evidence_ids
        )

    def _add_edge(
        self,
        line_id: str,
        parent_node_id: str,
        child_node_id: str,
        *,
        knowledge_cutoff: datetime,
    ) -> bool:
        existing_parents = self.store.parents_at(
            child_node_id,
            knowledge_cutoff,
        )
        if (
            parent_node_id not in existing_parents
            and existing_parents
            and not self.config.allow_conjunctive_rejoin
        ):
            # A second parent changes the child into an AND-rejoin. Similarity
            # alone is not enough authority to make that semantic commitment.
            return False
        return self.store.add_edge(
            line_id,
            parent_node_id,
            child_node_id,
            knowledge_at=knowledge_cutoff,
            commit=False,
        )

    def _visible_overlap_counts(
        self,
        block_ids: tuple[str, ...],
        *,
        knowledge_cutoff: datetime,
    ) -> dict[str, int]:
        view = LineGraphView(memory=self.memory, store=self.store)
        counts: dict[str, int] = {}
        for block_id in block_ids:
            for line_id in self.store.lines_for_block(block_id):
                node = self.store.node_for_block(line_id, block_id)
                if node is None:
                    continue
                if view.state_for_node_at_cutoff(
                    node.node_id,
                    knowledge_cutoff=knowledge_cutoff,
                ) is None:
                    continue
                counts[line_id] = counts.get(line_id, 0) + 1
        return counts

    @staticmethod
    def _precedes(left: SemanticBlock, right: SemanticBlock) -> bool:
        # Same-time/overlapping points stay unordered. This is intentionally a
        # partial order rather than an arbitrary tie-break.
        return (
            left.occurred_start < right.occurred_start
            and left.occurred_end <= right.occurred_start
        )

    def attach_block(
        self,
        line_id: str,
        block: SemanticBlock,
        *,
        parent_node_ids: tuple[str, ...] = (),
        child_node_ids: tuple[str, ...] = (),
        knowledge_cutoff: datetime | None = None,
    ) -> LineApplyResult:
        """Attach one current SemanticBlock to an existing Line.

        This is the nearline growth primitive. It never creates a new Line;
        ambiguous identity must remain unresolved upstream. Multiple parents
        express rejoin, while multiple children can place late-known historical
        evidence into an already-grown Line without rewriting old edges.

        Multiple parents mean conjunctive rejoin in V1: every parent ancestry
        must remain visible. Alternative/OR hypotheses are not represented by
        multiple parent edges and must remain separate unresolved structure.
        """
        if block.state_id is None:
            raise ValueError("Line attachment requires an immutable state")
        self.store.get_line(line_id)
        effective_cutoff = knowledge_cutoff or self._knowledge_at(block)
        _require_utc(effective_cutoff, "knowledge_cutoff")
        with self.store.conn:
            node, node_added, state_added = self.store.ensure_node(
                line_id,
                block,
                knowledge_at=self._knowledge_at(block),
                membership_known_at=effective_cutoff,
                commit=False,
            )
            added_edges: list[tuple[str, str]] = []
            for parent_id in tuple(dict.fromkeys(parent_node_ids)):
                if self.store.get_node(parent_id).line_id != line_id:
                    raise ValueError("parent belongs to another Line")
                if self._add_edge(
                    line_id,
                    parent_id,
                    node.node_id,
                    knowledge_cutoff=effective_cutoff,
                ):
                    added_edges.append((parent_id, node.node_id))
            for child_id in tuple(dict.fromkeys(child_node_ids)):
                if self.store.get_node(child_id).line_id != line_id:
                    raise ValueError("child belongs to another Line")
                if self._add_edge(
                    line_id,
                    node.node_id,
                    child_id,
                    knowledge_cutoff=effective_cutoff,
                ):
                    added_edges.append((node.node_id, child_id))
        return LineApplyResult(
            line_id=line_id,
            created_line=False,
            added_node_ids=(node.node_id,) if node_added else (),
            added_state_ids=(block.state_id,) if state_added else (),
            added_edges=tuple(added_edges),
        )

    def apply_path(
        self,
        blocks: tuple[SemanticBlock, ...],
        *,
        knowledge_cutoff: datetime | None = None,
    ) -> LineApplyResult:
        if len(blocks) < self.config.min_seed_support:
            return LineApplyResult(
                None,
                False,
                (),
                (),
                (),
                "insufficient support for a persistent Line",
            )
        if any(block.state_id is None for block in blocks):
            raise ValueError("trajectory path requires immutable states")
        block_ids = tuple(block.block_id for block in blocks)
        if len(set(block_ids)) != len(block_ids):
            raise ValueError("trajectory path contains duplicate blocks")

        effective_cutoff = knowledge_cutoff or max(
            self._knowledge_at(block) for block in blocks
        )
        _require_utc(effective_cutoff, "knowledge_cutoff")
        overlaps = self._visible_overlap_counts(
            block_ids,
            knowledge_cutoff=effective_cutoff,
        )
        strong = {
            line_id: count
            for line_id, count in overlaps.items()
            if count >= self.config.min_shared_support
        }

        created_line = False
        # Local structures are allowed to overlap. A candidate path that does
        # not share enough support to inherit any existing Line identity seeds
        # a distinct Line even when one or more of its SemanticBlocks already
        # participate elsewhere. This prevents weak exclusive ownership from
        # reappearing through the admission rule.
        new_line_seed = not strong
        if new_line_seed:
            line_id = self.store._line_id(block_ids)
            created_line = True
        elif len(strong) == 1:
            line_id = next(iter(strong))
        else:
            return LineApplyResult(
                None,
                False,
                (),
                (),
                (),
                "trajectory overlaps multiple stable Lines; no auto-merge",
            )

        nodes: list[LineNode] = []
        added_nodes: list[str] = []
        added_states: list[str] = []
        added_edges: list[tuple[str, str]] = []
        with self.store.conn:
            if new_line_seed:
                line = self.store.create_line(
                    block_ids,
                    created_at=effective_cutoff,
                    commit=False,
                )
                line_id = line.line_id
            for block in blocks:
                node, node_added, state_added = self.store.ensure_node(
                    line_id,
                    block,
                    knowledge_at=self._knowledge_at(block),
                    membership_known_at=effective_cutoff,
                    commit=False,
                )
                nodes.append(node)
                if node_added:
                    added_nodes.append(node.node_id)
                if state_added and block.state_id is not None:
                    added_states.append(block.state_id)

            for index in range(len(blocks) - 1):
                parent_block = blocks[index]
                child_block = blocks[index + 1]
                if not self._precedes(parent_block, child_block):
                    continue
                parent = nodes[index]
                child = nodes[index + 1]
                if self._add_edge(
                    line_id,
                    parent.node_id,
                    child.node_id,
                    knowledge_cutoff=effective_cutoff,
                ):
                    added_edges.append((parent.node_id, child.node_id))

        return LineApplyResult(
            line_id=line_id,
            created_line=created_line,
            added_node_ids=tuple(added_nodes),
            added_state_ids=tuple(added_states),
            added_edges=tuple(added_edges),
        )


class LineGraphView:
    """Knowledge-cutoff-aware view over derived Line structure."""

    def __init__(
        self,
        *,
        memory: ReferenceMemorySubstratePort,
        store: LineGraphStore,
    ) -> None:
        self.memory = memory
        self.store = store

    def state_for_node_at_cutoff(
        self,
        node_id: str,
        *,
        knowledge_cutoff: datetime,
    ) -> SemanticBlock | None:
        _require_utc(knowledge_cutoff, "knowledge_cutoff")
        candidates: list[SemanticBlock] = []
        for node_state in self.store.states_for_node(node_id):
            if node_state.knowledge_at > knowledge_cutoff:
                continue
            try:
                block = self.memory.get_semantic_block_state(
                    node_state.state_id
                )
                if not all(
                    _evidence_valid_at(
                        self.memory,
                        evidence_id,
                        knowledge_cutoff,
                    )
                    for evidence_id in block.raw_evidence_ids
                ):
                    continue
            except KeyError:
                continue
            candidates.append(block)
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda block: (
                block.state_version,
                block.state_id or "",
            ),
        )

    def _node_visible(
        self,
        node_id: str,
        cutoff: datetime,
        memo: dict[str, bool],
    ) -> bool:
        """Evaluate conjunctive ancestry without Python recursion."""
        if node_id in memo:
            return memo[node_id]

        pending: list[tuple[str, bool]] = [(node_id, False)]
        while pending:
            current_id, expanded = pending.pop()
            if current_id in memo:
                continue

            if not self.store.membership_active_at(
                current_id,
                cutoff,
            ):
                memo[current_id] = False
                continue

            block = self.state_for_node_at_cutoff(
                current_id,
                knowledge_cutoff=cutoff,
            )
            if block is None:
                memo[current_id] = False
                continue

            parents = self.store.parents_at(current_id, cutoff)
            if not expanded:
                unresolved = tuple(
                    parent_id
                    for parent_id in parents
                    if parent_id not in memo
                )
                if unresolved:
                    pending.append((current_id, True))
                    pending.extend(
                        (parent_id, False)
                        for parent_id in reversed(unresolved)
                    )
                    continue

            # V1 parent edges are conjunctive ancestry, not alternative routes.
            # Every parent must remain visible. Cycles are rejected by storage,
            # so all parents are resolved after the expanded pass.
            memo[current_id] = all(
                memo.get(parent_id, False)
                for parent_id in parents
            )

        return memo[node_id]

    def visible_node_ids(
        self,
        line_id: str,
        *,
        knowledge_cutoff: datetime,
    ) -> tuple[str, ...]:
        _require_utc(knowledge_cutoff, "knowledge_cutoff")
        memo: dict[str, bool] = {}
        return tuple(
            node.node_id
            for node in self.store.nodes_for_line(line_id)
            if self._node_visible(node.node_id, knowledge_cutoff, memo)
        )

    def frontier(
        self,
        line_id: str,
        *,
        knowledge_cutoff: datetime,
    ) -> tuple[str, ...]:
        visible = set(
            self.visible_node_ids(
                line_id,
                knowledge_cutoff=knowledge_cutoff,
            )
        )
        if not visible:
            return ()
        parents_with_visible_children = {
            parent_id
            for parent_id, child_id in self.store.edges_for_line_at(
                line_id,
                knowledge_cutoff,
            )
            if parent_id in visible and child_id in visible
        }
        return tuple(sorted(visible - parents_with_visible_children))

    def paths_to_frontier(
        self,
        line_id: str,
        *,
        knowledge_cutoff: datetime,
        max_paths: int = 128,
        max_nodes: int = 64,
    ) -> tuple[tuple[str, ...], ...]:
        """Enumerate visible root-to-frontier paths without creating view nodes."""
        if max_paths < 1 or max_nodes < 1:
            raise ValueError("path bounds must be positive")
        visible = set(
            self.visible_node_ids(
                line_id,
                knowledge_cutoff=knowledge_cutoff,
            )
        )
        if not visible:
            return ()
        frontiers = self.frontier(
            line_id,
            knowledge_cutoff=knowledge_cutoff,
        )
        paths: list[tuple[str, ...]] = []

        def ascend(
            node_id: str,
            suffix: tuple[str, ...],
        ) -> None:
            if len(paths) >= max_paths:
                return
            path = (node_id, *suffix)
            if len(path) >= max_nodes:
                paths.append(path)
                return
            parents = tuple(
                parent_id
                for parent_id in self.store.parents_at(
                    node_id,
                    knowledge_cutoff,
                )
                if parent_id in visible
            )
            if not parents:
                paths.append(path)
                return
            for parent_id in parents:
                ascend(parent_id, path)
                if len(paths) >= max_paths:
                    return

        for frontier_id in frontiers:
            ascend(frontier_id, ())
            if len(paths) >= max_paths:
                break

        return tuple(sorted(set(paths)))

    def raw_closure(
        self,
        node_id: str,
        *,
        knowledge_cutoff: datetime,
        max_nodes: int = 100_000,
    ) -> tuple[str, ...]:
        """Return the exact visible Raw Evidence ancestry for one Line node.

        Traversal is iterative so deep long-lived Lines do not depend on
        Python recursion depth. The safety ceiling is fail-closed: exceeding it
        raises instead of returning a truncated closure, because an incomplete
        provenance closure must never be presented as authoritative.
        """
        if max_nodes < 1:
            raise ValueError("max_nodes must be positive")

        pending = [node_id]
        seen_nodes: set[str] = set()
        raw_ids: set[str] = set()

        while pending:
            current_id = pending.pop()
            if current_id in seen_nodes:
                continue
            if len(seen_nodes) >= max_nodes:
                raise LineTraversalLimitExceeded(
                    "raw provenance closure exceeded max_nodes="
                    f"{max_nodes}; exact closure was not returned"
                )
            seen_nodes.add(current_id)
            block = self.state_for_node_at_cutoff(
                current_id,
                knowledge_cutoff=knowledge_cutoff,
            )
            if block is None:
                continue
            raw_ids.update(block.raw_evidence_ids)
            pending.extend(
                parent_id
                for parent_id in self.store.parents_at(
                    current_id,
                    knowledge_cutoff,
                )
                if parent_id not in seen_nodes
            )

        return tuple(sorted(raw_ids))


@dataclass(frozen=True, slots=True)
class CallableProjectionConfig:
    max_nodes: int = 6

    def __post_init__(self) -> None:
        if self.max_nodes < 1:
            raise ValueError("max_nodes must be positive")


class CallableLineProjector:
    """Materialize a bounded same-level Line slice for a current SemanticBlock."""

    def __init__(
        self,
        *,
        memory: ReferenceMemorySubstratePort,
        store: LineGraphStore,
        config: CallableProjectionConfig | None = None,
    ) -> None:
        self.memory = memory
        self.store = store
        self.view = LineGraphView(memory=memory, store=store)
        self.config = config or CallableProjectionConfig()

    def project_for_block(
        self,
        line_id: str,
        query_block: SemanticBlock,
        *,
        knowledge_cutoff: datetime,
    ) -> CallableLineProjection | None:
        visible_ids = self.view.visible_node_ids(
            line_id,
            knowledge_cutoff=knowledge_cutoff,
        )
        if not visible_ids:
            return None
        query_vector = self.memory.get_vector(
            query_block.block_id,
            state_id=query_block.state_id,
        ).values

        scored: list[tuple[float, str]] = []
        for node_id in visible_ids:
            node = self.store.get_node(node_id)
            block = self.view.state_for_node_at_cutoff(
                node_id,
                knowledge_cutoff=knowledge_cutoff,
            )
            if block is None:
                continue
            try:
                vector = self.memory.get_vector(
                    node.block_id,
                    state_id=block.state_id,
                ).values
            except KeyError:
                continue
            scored.append((_cosine(query_vector, vector), node_id))
        if not scored:
            return None
        scored.sort(key=lambda item: (-item[0], item[1]))
        anchor_id = scored[0][1]

        visible = set(visible_ids)
        distance: dict[str, int] = {anchor_id: 0}
        queue: deque[str] = deque([anchor_id])
        while queue and len(distance) < self.config.max_nodes * 3:
            current = queue.popleft()
            neighbours = (
                *self.store.parents_at(
                    current,
                    knowledge_cutoff,
                ),
                *self.store.children_at(
                    current,
                    knowledge_cutoff,
                ),
            )
            for neighbour in neighbours:
                if neighbour not in visible or neighbour in distance:
                    continue
                distance[neighbour] = distance[current] + 1
                queue.append(neighbour)

        similarity_by_id = {node_id: score for score, node_id in scored}
        selected_ids = tuple(
            node_id
            for node_id, _distance in sorted(
                distance.items(),
                key=lambda item: (
                    item[1],
                    -similarity_by_id.get(item[0], 0.0),
                    item[0],
                ),
            )[: self.config.max_nodes]
        )

        support: list[AuthorizedSelectedSupport] = []
        raw_ids: set[str] = set()
        fragments: list[str] = []
        for node_id in selected_ids:
            node = self.store.get_node(node_id)
            block = self.view.state_for_node_at_cutoff(
                node_id,
                knowledge_cutoff=knowledge_cutoff,
            )
            if block is None or block.state_id is None:
                continue
            support.append(
                AuthorizedSelectedSupport(
                    block_id=node.block_id,
                    state_id=block.state_id,
                )
            )
            raw_ids.update(
                self.view.raw_closure(
                    node_id,
                    knowledge_cutoff=knowledge_cutoff,
                )
            )
            fragments.append(block.content)

        if not support:
            return None
        return CallableLineProjection(
            line_id=line_id,
            anchor_node_id=anchor_id,
            node_ids=tuple(
                node_id
                for node_id in selected_ids
                if self.view.state_for_node_at_cutoff(
                    node_id,
                    knowledge_cutoff=knowledge_cutoff,
                )
                is not None
            ),
            selected_support=tuple(support),
            raw_evidence_ids=tuple(sorted(raw_ids)),
            content_fragments=tuple(fragments),
        )
