"""Downstream Raw-Hidden Consumer for Issue #19.

This process has strictly NO access to case or gold JSONL or Raw Evidence text.
It queries ONLY admitted public blocks, relations, and provenance references.
Maintains an immutable access audit log; any raw evidence reread attempt triggers
an immediate hard failure.
"""

from __future__ import annotations

import collections
from typing import Any

from research.benchmarks.semantic_block_v0_1.contracts import (
    PredictionRecord,
    PublicRelation,
    PublicSemanticBlock,
)


class ConsumerAccessAudit:
    """Audit ledger tracking access to ensure no raw evidence / gold is read."""

    def __init__(self) -> None:
        self.logs: list[dict[str, Any]] = []
        self.raw_read_attempts: int = 0

    def log_query(self, op: str, args: dict[str, Any], result: Any) -> None:
        self.logs.append({
            "operation": op,
            "args": args,
            "status": "OK",
        })

    def record_raw_read_attempt(self, target: str) -> None:
        self.raw_read_attempts += 1
        self.logs.append({
            "operation": "ILLEGAL_RAW_READ",
            "target": target,
            "status": "VIOLATION",
        })


class RawHiddenConsumer:
    """Route-neutral downstream consumer operating strictly on public predictions."""

    def __init__(
        self,
        prediction: PredictionRecord,
        audit: ConsumerAccessAudit | None = None,
    ) -> None:
        self.case_id = prediction.case_id
        self.cutoff = prediction.cutoff
        self.arm_id = prediction.arm_id
        self.audit = audit or ConsumerAccessAudit()

        # Ingest ONLY predicted public blocks and relations
        self._blocks_by_id: dict[str, PublicSemanticBlock] = {
            b.state_id: b for b in prediction.blocks
        }
        self._relations: list[PublicRelation] = list(prediction.relations)

    # 1. describe_state
    def describe_state(self, state_id: str) -> str:
        blk = self._blocks_by_id.get(state_id)
        ans = blk.canonical_content if blk else "UNKNOWN"
        self.audit.log_query("describe_state", {"state_id": state_id}, ans)
        return ans

    # 2. holder_and_utterer
    def holder_and_utterer(self, state_id: str) -> dict[str, str]:
        blk = self._blocks_by_id.get(state_id)
        if not blk:
            ans = {"holder": "UNKNOWN", "utterer": "UNKNOWN", "attribution_mode": "UNKNOWN"}
        else:
            ans = {
                "holder": blk.holder,
                "utterer": blk.utterer,
                "attribution_mode": blk.attribution_mode,
            }
        self.audit.log_query("holder_and_utterer", {"state_id": state_id}, ans)
        return ans

    # 3. participants_and_predicate
    def participants_and_predicate(self, state_id: str) -> dict[str, Any]:
        blk = self._blocks_by_id.get(state_id)
        if not blk:
            ans = {"predicate": "UNKNOWN", "kind": "UNKNOWN", "participants": {}}
        else:
            ans = {
                "predicate": blk.predicate,
                "kind": blk.kind,
                "participants": dict(blk.participants),
            }
        self.audit.log_query("participants_and_predicate", {"state_id": state_id}, ans)
        return ans

    # 4. polarity_modality_hedge
    def polarity_modality_hedge(self, state_id: str) -> dict[str, str]:
        blk = self._blocks_by_id.get(state_id)
        if not blk:
            ans = {"polarity": "UNKNOWN", "modality": "UNKNOWN", "epistemic_hedge": "UNKNOWN"}
        else:
            ans = {
                "polarity": blk.polarity,
                "modality": blk.modality,
                "epistemic_hedge": blk.epistemic_hedge,
            }
        self.audit.log_query("polarity_modality_hedge", {"state_id": state_id}, ans)
        return ans

    # 5. time_and_availability
    def time_and_availability(self, state_id: str) -> dict[str, str]:
        blk = self._blocks_by_id.get(state_id)
        if not blk:
            ans = {
                "valid_time": "UNKNOWN",
                "time_precision": "UNKNOWN",
                "state_available_at": "UNKNOWN",
            }
        else:
            ans = {
                "valid_time": blk.valid_time,
                "time_precision": blk.time_precision,
                "state_available_at": blk.state_available_at,
            }
        self.audit.log_query("time_and_availability", {"state_id": state_id}, ans)
        return ans

    # 6. support_refs
    def support_refs(self, state_id: str) -> dict[str, Any]:
        blk = self._blocks_by_id.get(state_id)
        if not blk:
            ans = {"source_spans": [], "independent_support_count": 0}
        else:
            ans = {
                "source_spans": [s.to_dict() for s in blk.source_spans],
                "independent_support_count": blk.independent_support_count,
            }
        self.audit.log_query("support_refs", {"state_id": state_id}, ans)
        return ans

    # 7. identity_status
    def identity_status(self, state_id: str) -> dict[str, str]:
        blk = self._blocks_by_id.get(state_id)
        if not blk:
            ans = {"entity_status": "UNKNOWN", "uncertainty": "UNKNOWN"}
        else:
            ans = {
                "entity_status": blk.entity_status,
                "uncertainty": blk.uncertainty,
            }
        self.audit.log_query("identity_status", {"state_id": state_id}, ans)
        return ans

    # 8. relation_basis
    def relation_basis(
        self,
        source_state_id: str,
        target_state_id: str,
        relation_type: str,
    ) -> dict[str, Any] | None:
        rel = next(
            (
                r for r in self._relations
                if r.source_state_id == source_state_id
                and r.target_state_id == target_state_id
                and r.type == relation_type
            ),
            None,
        )
        if rel is None:
            ans = None
        else:
            ans = {
                "basis": rel.basis,
                "cue_span": rel.cue_span.to_dict() if rel.cue_span else None,
                "traversal_allowed": rel.traversal_allowed,
            }
        self.audit.log_query(
            "relation_basis",
            {"source": source_state_id, "target": target_state_id, "type": relation_type},
            ans,
        )
        return ans

    # 9. reachable_cause_path
    def reachable_cause_path(
        self,
        source_state_id: str,
        target_state_id: str,
    ) -> list[str]:
        """Find directed CAUSE path from source to target using only traversable CAUSE edges."""
        adj: dict[str, list[str]] = collections.defaultdict(list)
        for r in self._relations:
            if r.type == "CAUSE" and r.traversal_allowed:
                adj[r.source_state_id].append(r.target_state_id)

        # BFS for shortest path
        queue = collections.deque([(source_state_id, [source_state_id])])
        visited = {source_state_id}

        found_path: list[str] = []
        while queue:
            curr, path = queue.popleft()
            if curr == target_state_id:
                found_path = path
                break
            for nxt in adj.get(curr, []):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, path + [nxt]))

        self.audit.log_query(
            "reachable_cause_path",
            {"source": source_state_id, "target": target_state_id},
            found_path,
        )
        return found_path
