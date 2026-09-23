"""Single Generic Candidate Generation Procedure v2 for Issue #16 (Pre-Registered).

ARCHITECTURAL PRINCIPLES (Pre-Registered v2):
1. No flattened graph bonuses (+0.5 / +0.7 / +0.8 to cosine similarity).
2. Dual-channel architecture:
   - A1: Vector & Local-Attribute Channels (cosine similarity, timestamps, polarity).
   - B: Vector Channels + Structural Graph Channels (multi-hop causal paths, entity trajectories, revision graphs).
3. Non-trivial longitudinal synthesis:
   - Evaluates composed structures (transitive multi-hop causal chains, coreference trajectories, bridging subgraphs).
4. Strict Open-World Assumption (OWA):
   - Absence of an edge does NOT equal NO_RELATION.
   - Vector candidates are never suppressed or penalized because an edge is missing.
5. Strictly universal across all fixtures: zero fixture-specific heuristics or branching.
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
    candidate_type: str  # "bridge", "recurrence", "revision", "dependency", "entity_trajectory", "causal_chain"
    item_ids: tuple[str, ...]
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


def _parse_iso_time(time_str: str) -> float:
    """Convert ISO timestamp to unix timestamp float for temporal delta calculations."""
    try:
        clean = time_str.replace("Z", "+00:00")
        if "T" not in clean:
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
    """Unified pre-registered dual-channel candidate generator for A0, A1, and B."""

    def __init__(
        self,
        sim_threshold: float = 0.50,
        max_candidates: int = 15,
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

        # 1. Precompute pairwise cosine similarity and time deltas
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

        # =========================================================================
        # Group A: Vector & Local Attribute Channels (Active in A0, A1, and B)
        # Scores are empirical vector metrics (cosine similarity / difference).
        # =========================================================================

        # A.1: Vector Recurrence Channel (temporal gap >= 7 days)
        for i in range(n):
            for j in range(i + 1, n):
                id_i, id_j = items[i]["id"], items[j]["id"]
                dt = time_deltas[(id_i, id_j)]
                s = sim_matrix[(id_i, id_j)]
                if dt >= 604800.0 and s >= 0.65:
                    proposals.append(
                        CandidateProposal(
                            candidate_id=f"vec_rec_{id_i}_{id_j}",
                            candidate_type="recurrence",
                            item_ids=(id_i, id_j),
                            score=round(s, 4),
                            metadata={"channel": "vector_recurrence", "source": "vector"},
                        )
                    )

        # A.2: Vector Revision Channel (polarity opposition)
        for i in range(n):
            for j in range(i + 1, n):
                id_i, id_j = items[i]["id"], items[j]["id"]
                s = sim_matrix[(id_i, id_j)]
                pol_i = items[i].get("polarity", "positive")
                pol_j = items[j].get("polarity", "positive")
                if pol_i != pol_j and s >= 0.40:
                    proposals.append(
                        CandidateProposal(
                            candidate_id=f"vec_rev_{id_i}_{id_j}",
                            candidate_type="revision",
                            item_ids=(id_i, id_j),
                            score=round(s, 4),
                            metadata={"channel": "vector_revision", "source": "vector"},
                        )
                    )

        # A.3: Vector Dependency Channel (forward chronological flow)
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                id_i, id_j = items[i]["id"], items[j]["id"]
                t_i = _parse_iso_time(items[i]["occurred_at"])
                t_j = _parse_iso_time(items[j]["occurred_at"])
                if t_i <= t_j:
                    s = sim_matrix[(id_i, id_j)]
                    if s >= 0.60:
                        proposals.append(
                            CandidateProposal(
                                candidate_id=f"vec_dep_{id_i}_{id_j}",
                                candidate_type="dependency",
                                item_ids=(id_i, id_j),
                                score=round(s, 4),
                                metadata={"channel": "vector_dependency", "source": "vector"},
                            )
                        )

        # A.4: Vector Bridging Channel (intermediate k links endpoints i, j)
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
                    sim_ij = sim_matrix[(id_i, id_j)]
                    if sim_ij < 0.60:
                        sim_ik = sim_matrix[(id_i, id_k)]
                        sim_jk = sim_matrix[(id_j, id_k)]
                        min_connect = min(sim_ik, sim_jk)
                        score = min_connect - sim_ij
                        if score > 0.20:
                            proposals.append(
                                CandidateProposal(
                                    candidate_id=f"vec_brg_{id_i}_{id_k}_{id_j}",
                                    candidate_type="bridge",
                                    item_ids=(id_i, id_k, id_j),
                                    score=round(score, 4),
                                    metadata={"channel": "vector_bridge", "source": "vector"},
                                )
                            )

        # =========================================================================
        # Group B: Structural Graph Channels (Active ONLY in Condition B)
        # Operates over typed edges and paths. Structural confidence >= 0.90.
        # =========================================================================
        use_graph = self.enable_graph_edges and (graph is not None)

        if use_graph and graph is not None:
            # 1. Index admitted positive graph relations (respecting ablations)
            cause_adj: dict[str, list[str]] = {}
            incompatible_pairs: set[tuple[str, str]] = set()
            equiv_pairs: set[tuple[str, str]] = set()
            all_undirected_adj: dict[str, set[str]] = {}

            for r in graph.relation_edges:
                rel_type = r.relation_type
                if rel_type in self.ablate_edge_types:
                    continue

                src, tgt = r.source_id, r.target_id
                all_undirected_adj.setdefault(src, set()).add(tgt)
                all_undirected_adj.setdefault(tgt, set()).add(src)

                if rel_type == "CAUSE":
                    cause_adj.setdefault(src, []).append(tgt)
                elif rel_type == "INCOMPATIBLE":
                    incompatible_pairs.add((src, tgt))
                    incompatible_pairs.add((tgt, src))
                elif rel_type in {"EQUIVALENT", "SAME_EVENT"}:
                    equiv_pairs.add((src, tgt))
                    equiv_pairs.add((tgt, src))

            # 2. Index coreference clusters across units via argument mentions
            coref_unit_pairs: set[tuple[str, str]] = set()
            if "SAME_ENTITY" not in self.ablate_edge_types:
                mention_to_unit = {m.mention_id: m.unit_id for m in graph.mention_nodes.values()}
                for entity in graph.canonical_entities.values():
                    m_ids = entity.mention_ids
                    for m_a in m_ids:
                        for m_b in m_ids:
                            if m_a != m_b and m_a in mention_to_unit and m_b in mention_to_unit:
                                u_a = mention_to_unit[m_a]
                                u_b = mention_to_unit[m_b]
                                if u_a != u_b:
                                    coref_unit_pairs.add((u_a, u_b))

            # --- Structural Channel B.1: Directed Multi-Hop Causal Paths ---
            # DFS search for multi-hop causal chains up to depth 4
            all_nodes = [it["id"] for it in items]
            for start_node in all_nodes:
                # Explore all paths starting from start_node
                stack: list[list[str]] = [[start_node]]
                while stack:
                    curr_path = stack.pop()
                    curr_node = curr_path[-1]
                    if len(curr_path) >= 5:
                        continue
                    for next_node in cause_adj.get(curr_node, []):
                        if next_node not in curr_path:
                            new_path = curr_path + [next_node]
                            stack.append(new_path)
                            hops = len(new_path) - 1
                            src_end = new_path[0]
                            tgt_end = new_path[-1]

                            if hops == 1:
                                proposals.append(
                                    CandidateProposal(
                                        candidate_id=f"graph_cause_{src_end}_{tgt_end}",
                                        candidate_type="dependency",
                                        item_ids=(src_end, tgt_end),
                                        score=0.95,
                                        metadata={"channel": "graph_causal_path", "hops": 1, "source": "graph"},
                                    )
                                )
                            elif hops >= 2:
                                # Composed multi-hop causal discovery
                                proposals.append(
                                    CandidateProposal(
                                        candidate_id=f"graph_transitive_cause_{src_end}_{tgt_end}",
                                        candidate_type="dependency",
                                        item_ids=(src_end, tgt_end),
                                        score=1.0,
                                        metadata={"channel": "graph_causal_path", "hops": hops, "path": new_path, "source": "graph"},
                                    )
                                )
                                proposals.append(
                                    CandidateProposal(
                                        candidate_id=f"graph_causal_chain_{'_'.join(new_path)}",
                                        candidate_type="causal_chain",
                                        item_ids=tuple(new_path),
                                        score=1.0,
                                        metadata={"channel": "graph_causal_path", "hops": hops, "source": "graph"},
                                    )
                                )

            # --- Structural Channel B.2: Entity Coreference Trajectories ---
            for u_a, u_b in coref_unit_pairs:
                if (u_a, u_b) in time_deltas:
                    ordered = tuple(sorted([u_a, u_b]))
                    proposals.append(
                        CandidateProposal(
                            candidate_id=f"graph_trajectory_{ordered[0]}_{ordered[1]}",
                            candidate_type="entity_trajectory",
                            item_ids=ordered,
                            score=0.98,
                            metadata={"channel": "graph_entity_trajectory", "source": "graph"},
                        )
                    )

            # --- Structural Channel B.3: Incompatible State Revision ---
            for u_a, u_b in incompatible_pairs:
                if (u_a, u_b) in time_deltas:
                    ordered = tuple(sorted([u_a, u_b]))
                    proposals.append(
                        CandidateProposal(
                            candidate_id=f"graph_revision_{ordered[0]}_{ordered[1]}",
                            candidate_type="revision",
                            item_ids=ordered,
                            score=0.96,
                            metadata={"channel": "graph_state_revision", "source": "graph"},
                        )
                    )

            # --- Structural Channel B.4: Bridging Subgraphs (2-hop paths) ---
            for k in all_nodes:
                neighbors = list(all_undirected_adj.get(k, set()))
                for idx_i in range(len(neighbors)):
                    for idx_j in range(idx_i + 1, len(neighbors)):
                        u_i = neighbors[idx_i]
                        u_j = neighbors[idx_j]
                        if (u_i, u_j) in time_deltas or (u_j, u_i) in time_deltas:
                            endpoints = tuple(sorted([u_i, u_j]))
                            proposals.append(
                                CandidateProposal(
                                    candidate_id=f"graph_bridge_{endpoints[0]}_{k}_{endpoints[1]}",
                                    candidate_type="bridge",
                                    item_ids=(endpoints[0], k, endpoints[1]),
                                    score=0.94,
                                    metadata={"channel": "graph_bridging_subgraph", "bridge_node": k, "source": "graph"},
                                )
                            )

            # --- Structural Channel B.5: Structural Recurrence ---
            for u_a, u_b in equiv_pairs:
                if (u_a, u_b) in time_deltas:
                    ordered = tuple(sorted([u_a, u_b]))
                    proposals.append(
                        CandidateProposal(
                            candidate_id=f"graph_rec_{ordered[0]}_{ordered[1]}",
                            candidate_type="recurrence",
                            item_ids=ordered,
                            score=0.95,
                            metadata={"channel": "graph_recurrence", "source": "graph"},
                        )
                    )

        # =========================================================================
        # Merging, Deterministic Sorting, and Deduplication
        # Open-World: All candidates (vector and structural) compete honestly.
        # Deduplication preserves the higher-confidence proposal for identical items.
        # =========================================================================
        # Sort descending by score, then candidate_id
        proposals.sort(key=lambda p: (-p.score, p.candidate_id))

        seen_keys: set[tuple[tuple[str, ...], str]] = set()
        deduped: list[CandidateProposal] = []

        for p in proposals:
            key = (tuple(sorted(p.item_ids)), p.candidate_type)
            if key not in seen_keys:
                seen_keys.add(key)
                deduped.append(p)
                if len(deduped) >= self.max_candidates:
                    break

        return deduped
