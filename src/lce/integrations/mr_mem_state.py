"""Rebuildable MR-Mem projection state, with metadata-only support capabilities."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, replace
from datetime import UTC, datetime
from typing import cast

from mr_mem.contracts import Scope
from mr_mem.memory.contracts import MemoryLifecycle
from mr_mem.memory.semantic_projection import CanonicalSemanticRelationView

from lce.integrations.mr_mem import CanonicalBlockProjection, LifecycleTimeUnknown
from lce.reference_memory.contracts import SemanticBlock
from lce.reference_memory.projection_state import SqliteProjectionStateStore
from lce.reference_memory.support import SupportStatus


class MrMemDerivedSubstrate(SqliteProjectionStateStore):
    """Derived cache only. All canonical mutation and Raw entrypoints are absent."""

    def initialize_annotations(self, scope: Scope, lineage_id: str) -> None:
        binding = json.dumps({"scope": asdict(scope), "lineage_id": lineage_id}, sort_keys=True)
        with self._db():
            self._db().execute("CREATE TABLE IF NOT EXISTS canonical_annotations "
                               "(memory_id TEXT PRIMARY KEY,payload TEXT NOT NULL)")
            self._db().execute("CREATE TABLE IF NOT EXISTS canonical_projection_binding "
                               "(singleton INTEGER PRIMARY KEY CHECK(singleton=1),payload TEXT NOT NULL)")
            row = self._db().execute("SELECT payload FROM canonical_projection_binding").fetchone()
            if row is not None and row[0] != binding:
                raise ValueError("canonical projection scope/lineage binding mismatch")
            self._db().execute("INSERT OR IGNORE INTO canonical_projection_binding VALUES (1,?)",
                               (binding,))

    def put_canonical_projection(self, projection: CanonicalBlockProjection) -> tuple[str, bool]:
        block = projection.block
        payload = json.dumps({
            "lifecycle": projection.lifecycle,
            "transition_known_at": (
                projection.transition_known_at.isoformat()
                if projection.transition_known_at is not None else None
            ),
            "outgoing": [self._relation_data(r) for r in projection.outgoing_relations],
            "incoming": [self._relation_data(r) for r in projection.incoming_relations],
        }, sort_keys=True)
        prior = self._db().execute("SELECT payload FROM canonical_annotations WHERE memory_id=?",
                                   (block.block_id,)).fetchone()
        try:
            existing = self.get_semantic_block(block.block_id)
        except KeyError:
            existing = None
        if existing is not None and replace(existing, state_id=None) != block:
            raise ValueError("canonical immutable Block identity drift")
        with self._db():
            if existing is None:
                self._write_current_state(self._db(), block)
            self._db().execute("INSERT INTO canonical_annotations VALUES (?,?) "
                               "ON CONFLICT(memory_id) DO UPDATE SET payload=excluded.payload",
                               (block.block_id, payload))
        fingerprint = hashlib.sha256(payload.encode()).hexdigest()
        return f"lce-semantic-v1:{block.block_id}:{fingerprint}", prior is not None and prior[0] == payload

    @staticmethod
    def _relation_data(relation: CanonicalSemanticRelationView) -> dict[str, object]:
        return {**asdict(relation), "known_at": relation.known_at.isoformat()}

    def canonical_projection(self, memory_id: str) -> CanonicalBlockProjection:
        row = self._db().execute("SELECT payload FROM canonical_annotations WHERE memory_id=?",
                                 (memory_id,)).fetchone()
        if row is None:
            raise KeyError(memory_id)
        data = json.loads(row[0])
        relations = []
        for name in ("outgoing", "incoming"):
            relations.append(tuple(CanonicalSemanticRelationView(**{
                **r, "known_at": datetime.fromisoformat(r["known_at"]),
            }) for r in data[name]))
        return CanonicalBlockProjection(
            self.get_semantic_block(memory_id), MemoryLifecycle(data["lifecycle"]),
            datetime.fromisoformat(data["transition_known_at"])
            if data["transition_known_at"] else None,
            relations[0], relations[1],
        )

    def block_current_valid(self, memory_id: str) -> bool:
        return self.canonical_projection(memory_id).current_valid

    def block_valid_at(self, memory_id: str, cutoff: datetime) -> bool:
        try:
            return self.canonical_projection(memory_id).valid_at(cutoff)
        except LifecycleTimeUnknown:
            # Algorithms omit unknown historical validity; exact callers can
            # query canonical_projection(...).valid_at(...) to obtain the error.
            return False

    def get_support_status(self, support_id: str) -> SupportStatus:
        blocks = [b for b in super().list_semantic_blocks() if support_id in b.raw_evidence_ids]
        if not blocks:
            raise KeyError(support_id)
        known = [b.derived_known_at for b in blocks if b.derived_known_at is not None]
        occurrences = [datetime.fromisoformat(ref["occurred_at"])
                       for b in blocks
                       for ref in cast(tuple[dict[str, str], ...], b.metadata["source_refs"])
                       if json.dumps([ref["source_namespace"], ref["session_id"], ref["record_id"]],
                                     ensure_ascii=False) == support_id]
        return SupportStatus(min(occurrences), min(known),
                             any(self.block_current_valid(b.block_id) for b in blocks))

    def support_valid_at(self, support_id: str, cutoff: datetime) -> bool:
        blocks = [b for b in super().list_semantic_blocks() if support_id in b.raw_evidence_ids]
        if not blocks:
            raise KeyError(support_id)
        return any(self.block_valid_at(b.block_id, cutoff) for b in blocks)

    def list_semantic_blocks(self, *, current_valid_only: bool = True) -> tuple[SemanticBlock, ...]:
        blocks = super().list_semantic_blocks()
        return tuple(b for b in blocks if not current_valid_only or self.block_current_valid(b.block_id))

    def list_semantic_block_states(self, *, current_valid_only: bool = True) -> tuple[SemanticBlock, ...]:
        states = super().list_semantic_block_states()
        return tuple(b for b in states if not current_valid_only or self.block_current_valid(b.block_id))

    def list_semantic_blocks_at_cutoff(
        self, cutoff: datetime, *, current_valid_only: bool = True,
    ) -> tuple[SemanticBlock, ...]:
        return tuple(b for b in self.list_semantic_blocks(current_valid_only=current_valid_only)
                     if b.occurred_end <= cutoff)

    def list_semantic_blocks_at_knowledge_cutoff(
        self, cutoff: datetime, *, current_valid_only: bool = True,
    ) -> tuple[SemanticBlock, ...]:
        if cutoff.tzinfo != UTC:
            raise ValueError("cutoff must be UTC")
        return tuple(b for b in super().list_semantic_blocks()
                     if b.derived_known_at is not None and b.derived_known_at <= cutoff
                     and (not current_valid_only or self.block_valid_at(b.block_id, cutoff)))

    def rebuild_vector_index(
        self, embedder: Callable[[SemanticBlock], tuple[float, ...]], *, index_version: str,
    ) -> None:
        # Preserve state vectors for historical cognition; current vectors are
        # restricted by canonical current lifecycle.
        self.replace_vector_index(super().list_semantic_block_states(), embedder,
                                  index_version=index_version)
        with self._db():
            for block in super().list_semantic_blocks():
                if not self.block_current_valid(block.block_id):
                    self._db().execute("DELETE FROM vector_projections WHERE block_id=?", (block.block_id,))
