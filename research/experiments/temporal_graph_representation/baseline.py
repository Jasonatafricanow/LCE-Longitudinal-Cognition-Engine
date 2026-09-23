"""Baseline structure discovery for GitHub Issue #12.

Implements the current LCE structure-discovery baseline unchanged:
Semantic Blocks + frozen vectors -> cosine / k-neighbourhood / multi-scale
neighbourhood structure -> existing structure product.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from research.experiments.temporal_graph_representation.fixtures import SyntheticItem


@dataclass
class BaselineCandidate:
    candidate_id: str
    candidate_type: str  # "cluster", "bridge", "recurrence", "revision", "chain"
    block_ids: list[str]
    carrier_ids: list[str]
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BaselineResult:
    visible_item_ids: list[str]
    components: list[list[str]]
    candidates: list[BaselineCandidate]
    bridge_nodes: list[str]
    multi_membership: dict[str, list[str]]  # item_id -> list of cluster_ids (exclusive in baseline)
    ranked_clusters_by_density: list[tuple[str, float]]
    similarity_matrix: dict[tuple[str, str], float]


def cosine_sim(u: np.ndarray, v: np.ndarray) -> float:
    nu = np.linalg.norm(u)
    nv = np.linalg.norm(v)
    if nu == 0 or nv == 0:
        return 0.0
    val = float(np.dot(u, v) / (nu * nv))
    return max(-1.0, min(1.0, val))


def chord_distance(u: np.ndarray, v: np.ndarray) -> float:
    c = cosine_sim(u, v)
    return float(np.sqrt(max(0.0, 2.0 * (1.0 - c))))


def run_baseline(
    items: list[SyntheticItem],
    *,
    min_similarity: float = 0.70,
    top_k: int = 4,
    stability_min_overlap: float = 0.5,
) -> BaselineResult:
    """Run current LCE vector-neighbourhood baseline over items visible at cutoff."""
    n = len(items)
    if n == 0:
        return BaselineResult([], [], [], [], {}, [], {})

    ordered = sorted(items, key=lambda it: it.item_id)
    ids = [it.item_id for it in ordered]
    vecs = np.array([it.vector for it in ordered])

    # 1. Cosine similarity matrix
    sim_matrix: dict[tuple[str, str], float] = {}
    for i in range(n):
        for j in range(i + 1, n):
            s = cosine_sim(vecs[i], vecs[j])
            sim_matrix[(ids[i], ids[j])] = s
            sim_matrix[(ids[j], ids[i])] = s

    # 2. k-NN neighbourhood sets
    knn_sets: dict[str, set[str]] = {}
    for i, item_id in enumerate(ids):
        ranked: list[tuple[float, str]] = []
        for j in range(n):
            if i == j:
                continue
            s = sim_matrix.get((item_id, ids[j]), 0.0)
            if s >= min_similarity:
                ranked.append((s, ids[j]))
        ranked.sort(key=lambda pair: (-pair[0], pair[1]))
        knn_sets[item_id] = {target for _, target in ranked[:top_k]}

    # 3. Disjoint connected components via neighbourhood overlap / union-find
    parent = {item_id: item_id for item_id in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[max(rx, ry)] = min(rx, ry)

    # Connect if mutual or thresholded kNN
    for i in range(n):
        for j in range(i + 1, n):
            u, v = ids[i], ids[j]
            s = sim_matrix.get((u, v), 0.0)
            if s >= min_similarity and (v in knn_sets[u] or u in knn_sets[v]):
                union(u, v)

    comp_dict: dict[str, list[str]] = {}
    for item_id in ids:
        comp_dict.setdefault(find(item_id), []).append(item_id)

    components = [sorted(members) for members in sorted(comp_dict.values(), key=lambda c: sorted(c))]

    # 4. Exclusive multi-membership (baseline assigns each node strictly to its connected component)
    multi_membership: dict[str, list[str]] = {}
    for c_idx, comp in enumerate(components):
        c_label = f"CLUSTER_{c_idx + 1:02d}"
        for member in comp:
            multi_membership.setdefault(member, []).append(c_label)

    # 5. Density ranking of clusters (average intra-cluster cosine similarity)
    density_ranked: list[tuple[str, float]] = []
    for c_idx, comp in enumerate(components):
        c_label = f"CLUSTER_{c_idx + 1:02d}"
        if len(comp) <= 1:
            density_ranked.append((c_label, 0.0))
            continue
        scores = [sim_matrix.get((u, v), 0.0) for idx_u, u in enumerate(comp) for v in comp[idx_u + 1 :]]
        avg_density = float(np.mean(scores)) if scores else 0.0
        density_ranked.append((c_label, avg_density))
    density_ranked.sort(key=lambda pair: -pair[1])

    # 6. Candidate generation
    candidates: list[BaselineCandidate] = []

    # A. Cluster candidates
    for c_idx, comp in enumerate(components):
        c_label = f"CLUSTER_{c_idx + 1:02d}"
        candidates.append(
            BaselineCandidate(
                candidate_id=f"base_clust_{c_idx + 1}",
                candidate_type="cluster",
                block_ids=comp,
                carrier_ids=comp,
                score=round(dict(density_ranked).get(c_label, 0.0), 4),
                metadata={"member_count": len(comp)},
            )
        )

    # B. Bridge heuristic in baseline:
    # A node whose similarity to two distinct components is non-trivial, or node with highest cross-component similarity
    bridge_nodes: list[str] = []
    if len(components) > 1:
        best_candidate: tuple[str, float] | None = None
        for item_id in ids:
            # Check similarities to each component
            sims_per_comp: list[float] = []
            for comp in components:
                # Max similarity to members of this component (excluding item_id)
                comp_sims = [sim_matrix.get((item_id, other), 0.0) for other in comp if other != item_id]
                sims_per_comp.append(max(comp_sims) if comp_sims else 0.0)
            sims_per_comp.sort(reverse=True)
            if len(sims_per_comp) >= 2 and sims_per_comp[1] >= min_similarity:
                cross_score = sims_per_comp[0] + sims_per_comp[1]
                if best_candidate is None or cross_score > best_candidate[1]:
                    best_candidate = (item_id, cross_score)

        if best_candidate is not None:
            bridge_nodes.append(best_candidate[0])
            candidates.append(
                BaselineCandidate(
                    candidate_id="base_bridge_1",
                    candidate_type="bridge",
                    block_ids=[best_candidate[0]],
                    carrier_ids=[best_candidate[0]],
                    score=round(best_candidate[1], 4),
                    metadata={"heuristic": "cross_component_similarity_sum"},
                )
            )

    return BaselineResult(
        visible_item_ids=ids,
        components=components,
        candidates=candidates,
        bridge_nodes=bridge_nodes,
        multi_membership=multi_membership,
        ranked_clusters_by_density=density_ranked,
        similarity_matrix=sim_matrix,
    )
