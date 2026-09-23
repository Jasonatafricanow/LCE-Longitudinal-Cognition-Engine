"""Single Generic Candidate Generation Procedure for Issue #16.

PRE-REGISTERED ARCHITECTURAL INVARIANT:
- This is the ONLY candidate-generation algorithm used across all 8 fixtures.
- Strictly NO fixture-specific branching (e.g. no "run causal query on causal fixture").
- Emits candidate structural proposals across four universal channels:
  1. Bridge / Reconnection: bottleneck cut-edges across weakly connected components.
  2. Long-Range Recurrence: non-adjacent temporal pairs with high structural/semantic affinity.
  3. State Revision / Contradiction: opposing polarity/modality or explicit INCOMPATIBLE relations.
  4. Directed Dependency / Causality: chronologically ordered pairs with causal edges or temporal flow.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from research.experiments.oracle_graph_value.embeddings import cosine_similarity
from research.oracle_graph.models import OracleTypedGraph


@dataclass(frozen=True)
class CandidateProposal:
    """A proposed structural candidate emitted by the generic generator."""

    candidate_id: str
    candidate_type: str  # "bridge", "recurrence", "revision", "dependency"
    item_ids: tuple[str, ...]
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


def _parse_iso_time(time_str: str) -> float:
    """Convert ISO timestamp to unix timestamp float for temporal delta calculations."""
    try:
        clean = time_str.replace("Z", "+00:00")
        if "T" not in clean:
            # Date only e.g. "2020" or "2026-04-01"
            parts = clean.split("-")
            if len(parts) == 1:
                return datetime(int(parts[0]), 1, 1).timestamp()
            elif len(parts) == 2:
                return datetime(int(parts[0]), int(parts[1]), 1).timestamp()
            else:
                return datetime(int(parts[0]), int(parts[1]), int(parts[2])).timestamp()
        return datetime.fromisoformat(clean).timestamp()
    except Exception:
        return 0.0


class GenericCandidateGenerator:
    """Unified pre-registered candidate generator for A0, A1, and B."""

    def __init__(
        self,
        sim_threshold: float = 0.35,
        max_candidates: int = 10,
        enable_graph_edges: bool = True,
        ablate_edge_types: set[str] | None = None,
    ) -> None:
        self.sim_threshold = sim_threshold
        self.max_candidates = max_candidates
        self.enable_graph_edges = enable_graph_edges
        self.ablate_edge_types = ablate_edge_types or set()

    def generate(
        self,
        items: list[dict[str, Any]],
        graph: OracleTypedGraph | None = None,
    ) -> list[CandidateProposal]:
        """Generate ranked candidate proposals over visible items.
        
        items format:
        [
            {
                "id": str,
                "vector": list[float],
                "occurred_at": str,
                "polarity": str (optional),
                "modality": str (optional),
                "holder": str (optional),
            }, ...
        ]
        """
        if len(items) < 2:
            return []

        proposals: list[CandidateProposal] = []
        n = len(items)

        # Build pairwise cosine similarity matrix
        sim_matrix: dict[tuple[str, str], float] = {}
        time_deltas: dict[tuple[str, str], float] = {}

        for i in range(n):
            for j in range(i + 1, n):
                id_i, id_j = items[i]["id"], items[j]["id"]
                s = cosine_similarity(items[i]["vector"], items[j]["vector"])
                sim_matrix[(id_i, id_j)] = s
                sim_matrix[(id_j, id_i)] = s

                t_i = _parse_iso_time(items[i]["occurred_at"])
                t_j = _parse_iso_time(items[j]["occurred_at"])
                dt = abs(t_j - t_i)
                time_deltas[(id_i, id_j)] = dt
                time_deltas[(id_j, id_i)] = dt

        # Collect graph edge lookups if graph is enabled (Condition B)
        rel_map: dict[tuple[str, str], list[str]] = {}
        coref_pairs: set[tuple[str, str]] = set()

        # Determine whether graph edges are active
        use_graph = self.enable_graph_edges and (graph is not None)

        if use_graph and graph is not None:
            # Map unit relations
            for r in graph.relation_edges:
                if r.relation_type in self.ablate_edge_types:
                    continue
                rel_map.setdefault((r.source_id, r.target_id), []).append(r.relation_type)

            # Map coreference across units via arguments
            mention_to_unit = {m.mention_id: m.unit_id for m in graph.mention_nodes.values()}
            for e in graph.canonical_entities.values():
                m_list = e.mention_ids
                for m_a in m_list:
                    for m_b in m_list:
                        if m_a != m_b and m_a in mention_to_unit and m_b in mention_to_unit:
                            u_a, u_b = mention_to_unit[m_a], mention_to_unit[m_b]
                            if u_a != u_b and "SAME_ENTITY" not in self.ablate_edge_types:
                                coref_pairs.add((u_a, u_b))
                                coref_pairs.add((u_b, u_a))

        # --- Universal Channel 1: Bridge / Reconnection ---
        # Detects bridging node k linking two otherwise distant nodes i and j
        for k in range(n):
            id_k = items[k]["id"]
            for i in range(n):
                if i == k:
                    continue
                id_i = items[i]["id"]
                for j in range(i + 1, n):
                    if j == k:
                        continue
                    id_j = items[j]["id"]

                    base_sim_ij = sim_matrix[(id_i, id_j)]
                    # Distant endpoints: low similarity
                    if base_sim_ij < 0.60:
                        sim_ik = sim_matrix[(id_i, id_k)]
                        sim_jk = sim_matrix[(id_j, id_k)]
                        min_connect = min(sim_ik, sim_jk)

                        bridge_bonus = 0.0
                        if use_graph:
                            # Graph relational connectivity bonus
                            has_edge_ik = (id_i, id_k) in rel_map or (id_k, id_i) in rel_map
                            has_edge_jk = (id_j, id_k) in rel_map or (id_k, id_j) in rel_map
                            if has_edge_ik and has_edge_jk:
                                bridge_bonus = 0.50

                        score = min_connect - base_sim_ij + bridge_bonus
                        if score > 0.20:
                            proposals.append(
                                CandidateProposal(
                                    candidate_id=f"bridge_{id_i}_{id_k}_{id_j}",
                                    candidate_type="bridge",
                                    item_ids=(id_i, id_k, id_j),
                                    score=round(score, 4),
                                    metadata={"bridge_node": id_k, "endpoints": (id_i, id_j)},
                                )
                            )

        # --- Universal Channel 2: Long-Range Recurrence ---
        # Detects matching items across significant temporal gap (> 7 days = 604800s)
        for i in range(n):
            for j in range(i + 1, n):
                id_i, id_j = items[i]["id"], items[j]["id"]
                dt = time_deltas[(id_i, id_j)]
                base_sim = sim_matrix[(id_i, id_j)]

                rec_bonus = 0.0
                if use_graph:
                    rels = rel_map.get((id_i, id_j), []) + rel_map.get((id_j, id_i), [])
                    if "EQUIVALENT" in rels or "SAME_EVENT" in rels:
                        rec_bonus = 0.60
                    if (id_i, id_j) in coref_pairs:
                        rec_bonus += 0.30

                if (dt >= 604800.0 and base_sim >= self.sim_threshold) or rec_bonus > 0:
                    score = base_sim + rec_bonus
                    proposals.append(
                        CandidateProposal(
                            candidate_id=f"recurrence_{id_i}_{id_j}",
                            candidate_type="recurrence",
                            item_ids=(id_i, id_j),
                            score=round(score, 4),
                            metadata={"delta_time_days": round(dt / 86400.0, 1)},
                        )
                    )

        # --- Universal Channel 3: State Revision / Contradiction ---
        # Detects opposing states: conflicting polarity or explicit INCOMPATIBLE relation
        for i in range(n):
            for j in range(i + 1, n):
                id_i, id_j = items[i]["id"], items[j]["id"]
                base_sim = sim_matrix[(id_i, id_j)]

                # Check attribute-level opposition
                pol_i = items[i].get("polarity", "positive")
                pol_j = items[j].get("polarity", "positive")
                has_pol_opposition = (pol_i != pol_j)

                rev_bonus = 0.0
                is_incompatible_edge = False
                if use_graph:
                    rels = rel_map.get((id_i, id_j), []) + rel_map.get((id_j, id_i), [])
                    if "INCOMPATIBLE" in rels:
                        rev_bonus = 0.80
                        is_incompatible_edge = True
                    # Check holder separation: if holders differ, penalize false contradiction
                    holder_i = items[i].get("holder", "user")
                    holder_j = items[j].get("holder", "user")
                    if holder_i != holder_j:
                        rev_bonus -= 0.50

                if (base_sim >= 0.40 and has_pol_opposition) or is_incompatible_edge:
                    score = base_sim + rev_bonus
                    if score > 0.30:
                        proposals.append(
                            CandidateProposal(
                                candidate_id=f"revision_{id_i}_{id_j}",
                                candidate_type="revision",
                                item_ids=(id_i, id_j),
                                score=round(score, 4),
                                metadata={"is_incompatible_edge": is_incompatible_edge},
                            )
                        )

        # --- Universal Channel 4: Directed Dependency / Causality ---
        # Detects chronological progression and causal dependencies
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                id_i, id_j = items[i]["id"], items[j]["id"]
                t_i = _parse_iso_time(items[i]["occurred_at"])
                t_j = _parse_iso_time(items[j]["occurred_at"])

                # Strictly forward in time
                if t_i <= t_j:
                    base_sim = sim_matrix[(id_i, id_j)]
                    dep_bonus = 0.0
                    has_cause = False

                    if use_graph:
                        rels = rel_map.get((id_i, id_j), [])
                        if "CAUSE" in rels:
                            dep_bonus = 0.70
                            has_cause = True
                        elif "BEFORE" in rels:
                            dep_bonus = 0.20
                        elif "NO_RELATION" in rels:
                            # Graph explicitly suppresses spurious association
                            dep_bonus = -0.80

                    score = base_sim + dep_bonus
                    # High threshold for vectors alone to avoid post-hoc false positives
                    if has_cause or (score >= 0.55 and not use_graph):
                        proposals.append(
                            CandidateProposal(
                                candidate_id=f"dependency_{id_i}_{id_j}",
                                candidate_type="dependency",
                                item_ids=(id_i, id_j),
                                score=round(score, 4),
                                metadata={"has_cause_edge": has_cause},
                            )
                        )

        # Sort all proposals deterministically by score (descending), then candidate_id
        proposals.sort(key=lambda p: (-p.score, p.candidate_id))

        # Deduplicate redundant candidate item sets
        seen_items: set[tuple[str, ...]] = set()
        deduped: list[CandidateProposal] = []
        for p in proposals:
            key = tuple(sorted(p.item_ids))
            if key not in seen_items:
                seen_items.add(key)
                deduped.append(p)
                if len(deduped) >= self.max_candidates:
                    break

        return deduped
