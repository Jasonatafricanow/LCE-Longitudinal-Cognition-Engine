"""Stable Line identity, branch-aware Worktree DAG, and callable projections.

This module owns only derived cognition references. Raw Evidence remains in the
injected Memory substrate. Branches are implicit paths inside one Line; a node
may have multiple parents, allowing historical divergence and later rejoin
without cloning Line identity.

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
    seed_state_ids: tuple[str, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.line_id.strip():
            raise ValueError("line_id must be nonempty")
        if not self.seed_state_ids:
            raise ValueError("seed_state_ids must be nonempty")
        if len(set(self.seed_state_ids)) != len(self.seed_state_ids):
            raise ValueError("seed_state_ids must be unique")
        _require_utc(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class LineNode:
    node_id: str
    line_id: str
    block_id: str
    state_id: str
    occurred_start: datetime
    occurred_end: datetime
    knowledge_at: datetime
    created_at: datetime

    def __post_init__(self) -> None:
        for value, name in (
            (self.node_id, "node_id"),
            (self.line_id, "line_id"),
            (self.block_id, "block_id"),
            (self.state_id, "state_id"),
        ):
            if not value.strip():
                raise ValueError(f"{name} must be nonempty")
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
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS lines (
                line_id TEXT PRIMARY KEY,
                seed_state_ids_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS line_nodes (
                node_id TEXT PRIMARY KEY,
                line_id TEXT NOT NULL,
                block_id TEXT NOT NULL,
                state_id TEXT NOT NULL,
                occurred_start TEXT NOT NULL,
                occurred_end TEXT NOT NULL,
                knowledge_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(line_id, state_id),
                FOREIGN KEY(line_id) REFERENCES lines(line_id)
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

            CREATE INDEX IF NOT EXISTS idx_line_nodes_state
                ON line_nodes(state_id);
            CREATE INDEX IF NOT EXISTS idx_line_nodes_block
                ON line_nodes(block_id);
            """
        )
        self.conn.commit()

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        _require_utc(parsed, "stored datetime")
        return parsed

    @staticmethod
    def _line_id(seed_state_ids: tuple[str, ...]) -> str:
        payload = json.dumps(seed_state_ids, separators=(",", ":"))
        digest = hashlib.sha256(payload.encode()).hexdigest()[:24]
        return f"line_{digest}"

    @staticmethod
    def _node_id(line_id: str, state_id: str) -> str:
        digest = hashlib.sha256(
            f"{line_id}|{state_id}".encode()
        ).hexdigest()[:24]
        return f"lnode_{digest}"

    def create_line(
        self,
        seed_state_ids: tuple[str, ...],
        *,
        created_at: datetime | None = None,
    ) -> LineRecord:
        if not seed_state_ids:
            raise ValueError("a Line seed requires at least one state")
        ordered = tuple(dict.fromkeys(seed_state_ids))
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
        self.conn.commit()
        return LineRecord(line_id, ordered, now)

    def get_line(self, line_id: str) -> LineRecord:
        row = self.conn.execute(
            "SELECT line_id, seed_state_ids_json, created_at "
            "FROM lines WHERE line_id = ?",
            (line_id,),
        ).fetchone()
        if row is None:
            raise KeyError(line_id)
        return LineRecord(
            line_id=str(row[0]),
            seed_state_ids=tuple(json.loads(str(row[1]))),
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
    ) -> tuple[LineNode, bool]:
        self.get_line(line_id)
        if block.state_id is None:
            raise ValueError("Line nodes require immutable SemanticBlock states")
        _require_utc(knowledge_at, "knowledge_at")
        node_id = self._node_id(line_id, block.state_id)
        existing = self.conn.execute(
            "SELECT node_id FROM line_nodes "
            "WHERE line_id = ? AND state_id = ?",
            (line_id, block.state_id),
        ).fetchone()
        if existing is not None:
            return self.get_node(str(existing[0])), False
        now = datetime.now(UTC)
        self.conn.execute(
            """
            INSERT INTO line_nodes (
                node_id, line_id, block_id, state_id, occurred_start,
                occurred_end, knowledge_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                node_id,
                line_id,
                block.block_id,
                block.state_id,
                block.occurred_start.isoformat(),
                block.occurred_end.isoformat(),
                knowledge_at.isoformat(),
                now.isoformat(),
            ),
        )
        self.conn.commit()
        return self.get_node(node_id), True

    def get_node(self, node_id: str) -> LineNode:
        row = self.conn.execute(
            """
            SELECT node_id, line_id, block_id, state_id, occurred_start,
                   occurred_end, knowledge_at, created_at
            FROM line_nodes WHERE node_id = ?
            """,
            (node_id,),
        ).fetchone()
        if row is None:
            raise KeyError(node_id)
        return LineNode(
            node_id=str(row[0]),
            line_id=str(row[1]),
            block_id=str(row[2]),
            state_id=str(row[3]),
            occurred_start=self._parse_datetime(str(row[4])),
            occurred_end=self._parse_datetime(str(row[5])),
            knowledge_at=self._parse_datetime(str(row[6])),
            created_at=self._parse_datetime(str(row[7])),
        )

    def node_for_state(
        self,
        line_id: str,
        state_id: str,
    ) -> LineNode | None:
        row = self.conn.execute(
            "SELECT node_id FROM line_nodes "
            "WHERE line_id = ? AND state_id = ?",
            (line_id, state_id),
        ).fetchone()
        return self.get_node(str(row[0])) if row is not None else None

    def nodes_for_line(self, line_id: str) -> tuple[LineNode, ...]:
        rows = self.conn.execute(
            "SELECT node_id FROM line_nodes WHERE line_id = ? "
            "ORDER BY occurred_start, occurred_end, node_id",
            (line_id,),
        ).fetchall()
        return tuple(self.get_node(str(row[0])) for row in rows)

    def add_edge(
        self,
        line_id: str,
        parent_node_id: str,
        child_node_id: str,
    ) -> bool:
        if parent_node_id == child_node_id:
            raise ValueError("a Line edge cannot self-reference")
        parent = self.get_node(parent_node_id)
        child = self.get_node(child_node_id)
        if parent.line_id != line_id or child.line_id != line_id:
            raise ValueError("Line edges cannot cross Line identity")
        if not parent.occurred_start < child.occurred_start:
            raise ValueError(
                "Line edges require strict logical ordering; "
                "same-time or reversed points stay unordered"
            )
        result = self.conn.execute(
            "INSERT OR IGNORE INTO line_edges VALUES (?, ?, ?)",
            (line_id, parent_node_id, child_node_id),
        )
        self.conn.commit()
        return result.rowcount > 0

    def parents(self, node_id: str) -> tuple[str, ...]:
        rows = self.conn.execute(
            "SELECT parent_node_id FROM line_edges "
            "WHERE child_node_id = ? ORDER BY parent_node_id",
            (node_id,),
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def children(self, node_id: str) -> tuple[str, ...]:
        rows = self.conn.execute(
            "SELECT child_node_id FROM line_edges "
            "WHERE parent_node_id = ? ORDER BY child_node_id",
            (node_id,),
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def edges_for_line(
        self, line_id: str
    ) -> tuple[tuple[str, str], ...]:
        rows = self.conn.execute(
            "SELECT parent_node_id, child_node_id FROM line_edges "
            "WHERE line_id = ? ORDER BY parent_node_id, child_node_id",
            (line_id,),
        ).fetchall()
        return tuple((str(row[0]), str(row[1])) for row in rows)

    def overlap_counts(
        self, state_ids: tuple[str, ...]
    ) -> dict[str, int]:
        if not state_ids:
            return {}
        placeholders = ",".join("?" for _ in state_ids)
        rows = self.conn.execute(
            f"""
            SELECT line_id, COUNT(DISTINCT state_id)
            FROM line_nodes
            WHERE state_id IN ({placeholders})
            GROUP BY line_id
            """,
            state_ids,
        ).fetchall()
        return {str(row[0]): int(row[1]) for row in rows}

    def close(self) -> None:
        self.conn.close()


@dataclass(frozen=True, slots=True)
class LineAssemblerConfig:
    min_seed_support: int = 3
    min_shared_support: int = 2

    def __post_init__(self) -> None:
        if self.min_seed_support < 2:
            raise ValueError("min_seed_support must be >= 2")
        if self.min_shared_support < 1:
            raise ValueError("min_shared_support must be >= 1")


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

    def apply_path(
        self,
        blocks: tuple[SemanticBlock, ...],
    ) -> LineApplyResult:
        if len(blocks) < self.config.min_seed_support:
            return LineApplyResult(
                None,
                False,
                (),
                (),
                "insufficient support for a persistent Line",
            )
        if any(block.state_id is None for block in blocks):
            raise ValueError("trajectory path requires immutable states")
        state_ids = tuple(
            block.state_id or "" for block in blocks
        )
        if len(set(state_ids)) != len(state_ids):
            raise ValueError("trajectory path contains duplicate states")

        overlaps = self.store.overlap_counts(state_ids)
        strong = {
            line_id: count
            for line_id, count in overlaps.items()
            if count >= self.config.min_shared_support
        }

        created_line = False
        if not overlaps:
            line = self.store.create_line(state_ids)
            line_id = line.line_id
            created_line = True
        elif len(strong) == 1:
            line_id = next(iter(strong))
        elif len(strong) > 1:
            return LineApplyResult(
                None,
                False,
                (),
                (),
                "trajectory overlaps multiple stable Lines; no auto-merge",
            )
        else:
            return LineApplyResult(
                None,
                False,
                (),
                (),
                "weak overlap with an existing Line; no clone created",
            )

        nodes: list[LineNode] = []
        added_nodes: list[str] = []
        for block in blocks:
            node, added = self.store.ensure_node(
                line_id,
                block,
                knowledge_at=self._knowledge_at(block),
            )
            nodes.append(node)
            if added:
                added_nodes.append(node.node_id)

        added_edges: list[tuple[str, str]] = []
        for parent, child in zip(nodes, nodes[1:], strict=True):
            if not parent.occurred_start < child.occurred_start:
                continue
            if self.store.add_edge(
                line_id, parent.node_id, child.node_id
            ):
                added_edges.append((parent.node_id, child.node_id))

        return LineApplyResult(
            line_id=line_id,
            created_line=created_line,
            added_node_ids=tuple(added_nodes),
            added_edges=tuple(added_edges),
        )


class LineGraphView:
    """Cutoff-aware view over derived Line structure."""

    def __init__(
        self,
        *,
        memory: ReferenceMemorySubstratePort,
        store: LineGraphStore,
    ) -> None:
        self.memory = memory
        self.store = store

    def _node_visible(
        self,
        node_id: str,
        cutoff: datetime,
        memo: dict[str, bool],
    ) -> bool:
        if node_id in memo:
            return memo[node_id]
        node = self.store.get_node(node_id)
        if node.knowledge_at > cutoff:
            memo[node_id] = False
            return False
        try:
            block = self.memory.get_semantic_block_state(node.state_id)
            source_visible = all(
                self.memory.get_evidence(
                    evidence_id
                ).current_valid
                and self.memory.get_evidence(
                    evidence_id
                ).effective_known_at <= cutoff
                for evidence_id in block.raw_evidence_ids
            )
        except KeyError:
            source_visible = False
        if not source_visible:
            memo[node_id] = False
            return False
        parents = self.store.parents(node_id)
        visible = all(
            self._node_visible(parent_id, cutoff, memo)
            for parent_id in parents
        )
        memo[node_id] = visible
        return visible

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
            for parent_id, child_id in self.store.edges_for_line(line_id)
            if parent_id in visible and child_id in visible
        }
        return tuple(sorted(visible - parents_with_visible_children))

    def raw_closure(self, node_id: str) -> tuple[str, ...]:
        seen_nodes: set[str] = set()
        raw_ids: set[str] = set()

        def visit(current_id: str) -> None:
            if current_id in seen_nodes:
                return
            seen_nodes.add(current_id)
            node = self.store.get_node(current_id)
            block = self.memory.get_semantic_block_state(node.state_id)
            raw_ids.update(block.raw_evidence_ids)
            for parent_id in self.store.parents(current_id):
                visit(parent_id)

        visit(node_id)
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
            try:
                vector = self.memory.get_vector(
                    node.block_id,
                    state_id=node.state_id,
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
                *self.store.parents(current),
                *self.store.children(current),
            )
            for neighbour in neighbours:
                if neighbour not in visible or neighbour in distance:
                    continue
                distance[neighbour] = distance[current] + 1
                queue.append(neighbour)

        similarity_by_id = {node_id: score for score, node_id in scored}
        selected_ids = tuple(
            node_id
            for node_id, _dist in sorted(
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
            block = self.memory.get_semantic_block_state(node.state_id)
            support.append(
                AuthorizedSelectedSupport(
                    block_id=node.block_id,
                    state_id=node.state_id,
                )
            )
            raw_ids.update(block.raw_evidence_ids)
            fragments.append(block.content)

        return CallableLineProjection(
            line_id=line_id,
            anchor_node_id=anchor_id,
            node_ids=selected_ids,
            selected_support=tuple(support),
            raw_evidence_ids=tuple(sorted(raw_ids)),
            content_fragments=tuple(fragments),
        )
