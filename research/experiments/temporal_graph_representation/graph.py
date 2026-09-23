"""Minimal Temporal Semantic Graph Representation for GitHub Issue #12.

Builds a deterministic research-only temporal graph from visible blocks at each cutoff:
- Nodes: One node per cutoff-visible Semantic Block.
- Edges:
  1. semantic_neighbour: derived from cosine similarities (same available to baseline),
     preserving score, threshold, and k provenance.
  2. temporal_next: deterministic order edge between successive visible blocks in source time.
  3. same_context_key: deterministic edge if explicit non-LLM identifier is present.
- Strictly no LLM-generated relation labels (supports, contradicts, causes, reconnects).
- Strictly deterministic graph algorithms (Tarjan cut-vertices, overlapping communities,
  temporal-semantic path coherence, cross-cutoff lineage).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

from research.experiments.temporal_graph_representation.baseline import (
    cosine_sim,
)
from research.experiments.temporal_graph_representation.fixtures import SyntheticItem


@dataclass
class GraphEdge:
    source: str
    target: str
    edge_family: str  # "semantic_neighbour", "temporal_next", "same_context_key"
    weight: float
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphCandidate:
    candidate_id: str
    candidate_type: str  # "reconnection_bridge", "distant_recurrence", "structural_revision", "multi_membership", "temporal_coherent_chain"
    block_ids: list[str]
    carrier_ids: list[str]
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TemporalGraphResult:
    visible_item_ids: list[str]
    nodes: dict[str, SyntheticItem]
    edges: list[GraphEdge]
    candidates: list[GraphCandidate]
    articulation_points: list[str]
    bridge_edges: list[tuple[str, str]]
    overlapping_communities: list[set[str]]
    multi_membership: dict[str, list[str]]  # item_id -> list of community_ids
    coherent_chains: list[list[str]]


class TemporalSemanticGraph:
    """Minimal deterministic temporal semantic graph."""

    def __init__(
        self,
        items: list[SyntheticItem],
        *,
        semantic_threshold: float = 0.70,
        semantic_top_k: int = 4,
        include_semantic: bool = True,
        include_temporal: bool = True,
        include_context: bool = True,
    ) -> None:
        self.items = sorted(items, key=lambda it: (it.occurred_at, it.item_id))
        self.nodes = {it.item_id: it for it in self.items}
        self.semantic_threshold = semantic_threshold
        self.semantic_top_k = semantic_top_k
        self.include_semantic = include_semantic
        self.include_temporal = include_temporal
        self.include_context = include_context

        self.edges: list[GraphEdge] = []
        self._build_graph()

    def _build_graph(self) -> None:
        n = len(self.items)
        if n == 0:
            return

        # 1. Semantic edges (undirected, derived from cosine similarity)
        if self.include_semantic:
            ordered_by_id = sorted(self.items, key=lambda it: it.item_id)
            ids = [it.item_id for it in ordered_by_id]
            vecs = np.array([it.vector for it in ordered_by_id])

            # Compute pairwise similarities
            for i in range(n):
                ranked: list[tuple[float, str]] = []
                for j in range(n):
                    if i == j:
                        continue
                    sim = cosine_sim(vecs[i], vecs[j])
                    if sim >= self.semantic_threshold:
                        ranked.append((sim, ids[j]))
                ranked.sort(key=lambda p: (-p[0], p[1]))

                for rank_idx, (sim, target_id) in enumerate(ranked[: self.semantic_top_k]):
                    # Store canonical undirected edge (u < v)
                    u, v = sorted((ids[i], target_id))
                    # Avoid duplicate edge addition
                    if not any(
                        e.edge_family == "semantic_neighbour" and e.source == u and e.target == v
                        for e in self.edges
                    ):
                        self.edges.append(
                            GraphEdge(
                                source=u,
                                target=v,
                                edge_family="semantic_neighbour",
                                weight=round(sim, 6),
                                provenance={
                                    "threshold": self.semantic_threshold,
                                    "top_k": self.semantic_top_k,
                                    "rank": rank_idx + 1,
                                },
                            )
                        )

        # 2. Temporal edges (deterministic order between successive visible blocks)
        if self.include_temporal and n > 1:
            for idx in range(n - 1):
                curr_item = self.items[idx]
                next_item = self.items[idx + 1]
                dt_sec = (next_item.occurred_at - curr_item.occurred_at).total_seconds()
                self.edges.append(
                    GraphEdge(
                        source=curr_item.item_id,
                        target=next_item.item_id,
                        edge_family="temporal_next",
                        weight=round(dt_sec, 2),
                        provenance={"order_index": idx, "dt_seconds": dt_sec},
                    )
                )

        # 3. Same context key edges (if explicit identifier present)
        if self.include_context:
            context_groups: dict[str, list[str]] = {}
            for it in self.items:
                if it.context_key:
                    context_groups.setdefault(it.context_key, []).append(it.item_id)
            for ctx_key, group_ids in context_groups.items():
                if len(group_ids) > 1:
                    for i in range(len(group_ids)):
                        for j in range(i + 1, len(group_ids)):
                            u, v = sorted((group_ids[i], group_ids[j]))
                            self.edges.append(
                                GraphEdge(
                                    source=u,
                                    target=v,
                                    edge_family="same_context_key",
                                    weight=1.0,
                                    provenance={"context_key": ctx_key},
                                )
                            )

    def get_semantic_adjacency(self) -> dict[str, dict[str, float]]:
        adj: dict[str, dict[str, float]] = {item_id: {} for item_id in self.nodes}
        for edge in self.edges:
            if edge.edge_family == "semantic_neighbour":
                adj[edge.source][edge.target] = edge.weight
                adj[edge.target][edge.source] = edge.weight
        return adj

    def get_temporal_adjacency(self) -> dict[str, list[str]]:
        adj: dict[str, list[str]] = {item_id: [] for item_id in self.nodes}
        for edge in self.edges:
            if edge.edge_family == "temporal_next":
                adj[edge.source].append(edge.target)
        return adj


# ==============================================================================
# Deterministic Graph Structural Discovery Operators
# ==============================================================================

def find_articulation_points_and_bridges(
    adj: dict[str, dict[str, float]]
) -> tuple[list[str], list[tuple[str, str]]]:
    """Tarjan's algorithm for cut-vertices (articulation points) and bridge edges."""
    visited: set[str] = set()
    tin: dict[str, int] = {}
    low: dict[str, int] = {}
    timer = 0
    articulation_points: set[str] = set()
    bridges: list[tuple[str, str]] = []

    def dfs(u: str, p: str | None = None) -> None:
        nonlocal timer
        visited.add(u)
        tin[u] = low[u] = timer
        timer += 1
        children = 0

        for v in adj.get(u, {}):
            if v == p:
                continue
            if v in visited:
                low[u] = min(low[u], tin[v])
            else:
                dfs(v, u)
                low[u] = min(low[u], low[v])
                if low[v] >= tin[u] and p is not None:
                    articulation_points.add(u)
                if low[v] > tin[u]:
                    bridges.append(tuple(sorted((u, v))))
                children += 1

        if p is None and children > 1:
            articulation_points.add(u)

    for node in sorted(adj.keys()):
        if node not in visited:
            dfs(node)

    return sorted(articulation_points), sorted(bridges)


def find_semantic_components(adj: dict[str, dict[str, float]]) -> list[list[str]]:
    """Connected components in the semantic graph."""
    visited: set[str] = set()
    components: list[list[str]] = []

    for node in sorted(adj.keys()):
        if node not in visited:
            comp: list[str] = []
            queue = [node]
            visited.add(node)
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for neighbor in adj.get(curr, {}):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            components.append(sorted(comp))

    return sorted(components, key=lambda c: sorted(c))


def find_overlapping_communities(
    adj: dict[str, dict[str, float]], min_size: int = 3
) -> list[set[str]]:
    """Extract overlapping communities via maximal cliques and high-overlap cores."""
    # Find maximal cliques using Bron-Kerbosch
    all_nodes = set(adj.keys())
    cliques: list[set[str]] = []

    def bron_kerbosch(r: set[str], p: set[str], x: set[str]) -> None:
        if not p and not x:
            if len(r) >= min_size:
                cliques.append(set(r))
            return
        for u in sorted(list(p)):
            neighbors = set(adj.get(u, {}).keys())
            bron_kerbosch(r | {u}, p & neighbors, x & neighbors)
            p.remove(u)
            x.add(u)

    bron_kerbosch(set(), set(all_nodes), set())

    # If no cliques of min_size, fall back to ego-networks with min_size
    if not cliques:
        for node, nbrs in adj.items():
            community = {node} | set(nbrs.keys())
            if len(community) >= min_size:
                cliques.append(community)

    # Filter duplicate or subset communities
    filtered: list[set[str]] = []
    for c in sorted(cliques, key=lambda s: -len(s)):
        if not any(c < existing for existing in filtered):
            filtered.append(c)

    return filtered


def evaluate_temporal_semantic_graph(
    items: list[SyntheticItem],
    *,
    semantic_threshold: float = 0.70,
    semantic_top_k: int = 4,
    include_semantic: bool = True,
    include_temporal: bool = True,
    include_context: bool = True,
) -> TemporalGraphResult:
    """Construct minimal temporal semantic graph and extract deterministic candidates."""
    graph = TemporalSemanticGraph(
        items,
        semantic_threshold=semantic_threshold,
        semantic_top_k=semantic_top_k,
        include_semantic=include_semantic,
        include_temporal=include_temporal,
        include_context=include_context,
    )

    sem_adj = graph.get_semantic_adjacency()
    temp_adj = graph.get_temporal_adjacency()

    articulation_points, bridge_edges = find_articulation_points_and_bridges(sem_adj)
    sem_components = find_semantic_components(sem_adj)
    overlapping_comm = find_overlapping_communities(sem_adj, min_size=3)

    # Multi-membership mapping: node -> list of community identifiers
    multi_membership: dict[str, list[str]] = {}
    for comm_idx, comm in enumerate(overlapping_comm):
        comm_id = f"COMMUNITY_{comm_idx + 1:02d}"
        for member in comm:
            multi_membership.setdefault(member, []).append(comm_id)

    candidates: list[GraphCandidate] = []

    # 1. Reconnection / Bridge candidates:
    # An articulation point that connects previously disconnected components
    for ap in articulation_points:
        # Check components formed if ap is removed
        sub_adj = {u: {v: w for v, w in neighbors.items() if v != ap} for u, neighbors in sem_adj.items() if u != ap}
        sub_comps = [c for c in find_semantic_components(sub_adj) if len(c) > 0]
        if len(sub_comps) >= 2:
            candidates.append(
                GraphCandidate(
                    candidate_id=f"graph_bridge_{ap}",
                    candidate_type="reconnection_bridge",
                    block_ids=[ap] + [c[0] for c in sub_comps],
                    carrier_ids=[ap],
                    score=1.0,
                    metadata={"sub_component_count": len(sub_comps), "bridged_nodes": [c[0] for c in sub_comps]},
                )
            )

    # 2. Distant recurrence candidates:
    # A semantic component containing nodes separated by temporal gap with intervening nodes
    if include_temporal and len(items) > 3:
        for comp_idx, comp in enumerate(sem_components):
            if len(comp) >= 2:
                comp_items = sorted([graph.nodes[i] for i in comp], key=lambda it: it.occurred_at)
                # Check for temporal gap between successive members of this component
                has_intervening_gap = False
                for i in range(len(comp_items) - 1):
                    t_a = comp_items[i].occurred_at
                    t_b = comp_items[i + 1].occurred_at
                    # Count visible items occurring strictly between t_a and t_b not in this component
                    intervening = [
                        it.item_id for it in graph.items
                        if t_a < it.occurred_at < t_b and it.item_id not in comp
                    ]
                    if len(intervening) >= 2:
                        has_intervening_gap = True
                        break

                if has_intervening_gap:
                    candidates.append(
                        GraphCandidate(
                            candidate_id=f"graph_recurrence_{comp_idx + 1}",
                            candidate_type="distant_recurrence",
                            block_ids=comp,
                            carrier_ids=comp,
                            score=0.9,
                            metadata={"temporal_gap": True, "member_count": len(comp)},
                        )
                    )

    # 3. Structural revision candidates:
    # A node X arriving at latest time that has strong semantic connection to a newer group
    # but low/broken connection to an older group, with a temporal path from old -> new -> X
    if include_temporal and len(items) >= 4:
        latest_item = graph.items[-1]
        x_id = latest_item.item_id
        x_neighbors = sem_adj.get(x_id, {})
        if x_neighbors:
            # Check earlier components
            for comp in sem_components:
                if x_id in comp:
                    continue
                # If X has zero or very low connection to comp, but comp occurred earlier
                comp_items = [graph.nodes[i] for i in comp]
                max_comp_time = max(it.occurred_at for it in comp_items)
                if max_comp_time < latest_item.occurred_at:
                    # Check if there is an intervening connected group
                    for connected_id in x_neighbors:
                        if graph.nodes[connected_id].occurred_at > max_comp_time:
                            candidates.append(
                                GraphCandidate(
                                    candidate_id=f"graph_revision_{x_id}",
                                    candidate_type="structural_revision",
                                    block_ids=[x_id, connected_id] + comp[:2],
                                    carrier_ids=[x_id],
                                    score=0.85,
                                    metadata={"revised_predecessor": comp[0], "aligned_with": connected_id},
                                )
                            )
                            break

    # 4. Multi-membership candidates:
    for item_id, comm_list in multi_membership.items():
        if len(comm_list) >= 2:
            candidates.append(
                GraphCandidate(
                    candidate_id=f"graph_multi_{item_id}",
                    candidate_type="multi_membership",
                    block_ids=[item_id],
                    carrier_ids=[item_id],
                    score=1.0,
                    metadata={"participating_communities": comm_list},
                )
            )

    # 5. Temporally coherent chains:
    # Trace paths along temporal_next where each step is also a semantic_neighbour
    coherent_chains: list[list[str]] = []
    if include_temporal and include_semantic:
        for it in graph.items:
            start_id = it.item_id
            curr = start_id
            chain = [curr]
            while True:
                next_temporal = temp_adj.get(curr, [])
                if not next_temporal:
                    break
                nxt = next_temporal[0]
                # Check if (curr, nxt) is also a semantic neighbour
                if nxt in sem_adj.get(curr, {}):
                    chain.append(nxt)
                    curr = nxt
                else:
                    break
            if len(chain) >= 3:
                coherent_chains.append(chain)
                candidates.append(
                    GraphCandidate(
                        candidate_id=f"graph_chain_{chain[0]}",
                        candidate_type="temporal_coherent_chain",
                        block_ids=chain,
                        carrier_ids=chain,
                        score=round(len(chain) / len(graph.items), 4),
                        metadata={"chain_length": len(chain)},
                    )
                )

    return TemporalGraphResult(
        visible_item_ids=[it.item_id for it in graph.items],
        nodes=graph.nodes,
        edges=graph.edges,
        candidates=candidates,
        articulation_points=articulation_points,
        bridge_edges=bridge_edges,
        overlapping_communities=overlapping_comm,
        multi_membership=multi_membership,
        coherent_chains=coherent_chains,
    )
