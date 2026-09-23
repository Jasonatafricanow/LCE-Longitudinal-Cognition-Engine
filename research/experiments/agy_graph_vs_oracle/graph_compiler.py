"""Predicted Graph Compiler for AGY Semantic Parser predictions (GitHub Issue #17).

Compiles predicted SemanticAnnotationDocument instances into typed property graphs
adhering strictly to frozen v0.1 graph admission rules:
- Only units and relations with evidence_status in {explicit, entailed} are admitted.
- Control relations (NO_RELATION, UNKNOWN, TEMPORAL_UNKNOWN) and inferred relations are excluded.
- Canonical entity clusters are computed via Union-Find transitive closure over SAME_ENTITY.
"""
from __future__ import annotations

from typing import Any

from research.oracle_graph.models import (
    ArgumentGraphEdge,
    CanonicalEntityNode,
    MentionGraphNode,
    OracleTypedGraph,
    RelationGraphEdge,
    UnitGraphNode,
)
from research.semantic_annotation.schema import SemanticAnnotationDocument


class UnionFind:
    """Disjoint-set data structure for computing connected components over SAME_ENTITY."""

    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        if x not in self.parent:
            self.parent[x] = x
            return x
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: str, y: str) -> None:
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x != root_y:
            # Deterministic string-order tie-breaking
            if root_x < root_y:
                self.parent[root_y] = root_x
            else:
                self.parent[root_x] = root_y


def compile_predicted_graph(
    doc: SemanticAnnotationDocument,
    graph_id: str | None = None,
) -> OracleTypedGraph:
    """Compile a predicted SemanticAnnotationDocument into an OracleTypedGraph."""
    gid = graph_id or doc.document_id
    unit_nodes: dict[str, UnitGraphNode] = {}
    mention_nodes: dict[str, MentionGraphNode] = {}
    argument_edges: list[ArgumentGraphEdge] = []
    relation_edges: list[RelationGraphEdge] = []

    # 1. Admit Units and extract Argument Mentions
    for u in doc.units:
        if not u.is_graph_eligible:
            continue

        node_dict = u.to_graph_node()
        unit_nodes[u.annotation_id] = UnitGraphNode(
            node_id=u.annotation_id,
            kind=node_dict["kind"],
            predicate=node_dict["predicate"],
            polarity=node_dict["polarity"],
            modality=node_dict["modality"],
            epistemic_hedge=node_dict["epistemic_hedge"],
            holder_ref=node_dict["holder_ref"],
            attribution_mode=node_dict["attribution_mode"],
            temporal_anchoring=node_dict["temporal_anchoring"],
            evidence_status=node_dict["evidence_status"],
            confidence=node_dict["confidence"],
            provenance={
                "raw_evidence_id": u.provenance.raw_evidence_id,
                "semantic_block_id": u.provenance.semantic_block_id,
            },
        )

        # Mentions and Argument Edges
        for role_name, mention in u.arguments.items():
            m_node = MentionGraphNode(
                mention_id=mention.mention_id,
                unit_id=u.annotation_id,
                role=role_name,
                text=mention.text,
                entity_ref=mention.entity_ref,
            )
            mention_nodes[mention.mention_id] = m_node
            argument_edges.append(
                ArgumentGraphEdge(
                    source_unit_id=u.annotation_id,
                    target_mention_id=mention.mention_id,
                    role=role_name,
                )
            )

    # 2. Admit Relations and collect Coreference
    uf = UnionFind()
    for r in doc.relations:
        if not r.is_graph_edge:
            continue

        edge_dict = r.to_graph_edge()
        relation_edges.append(
            RelationGraphEdge(
                relation_id=edge_dict["relation_id"],
                source_id=edge_dict["source_id"],
                target_id=edge_dict["target_id"],
                relation_type=edge_dict["relation_type"],
                evidence_status=edge_dict["evidence_status"],
                confidence=edge_dict["confidence"],
                provenance=edge_dict["provenance"],
                supporting_spans=edge_dict.get("supporting_spans", []),
            )
        )

        if r.relation_type.value == "SAME_ENTITY":
            uf.union(r.source_id, r.target_id)

    # 3. Resolve Canonical Entities via Union-Find connected components
    clusters: dict[str, list[str]] = {}
    for mid in mention_nodes.keys():
        root = uf.find(mid)
        clusters.setdefault(root, []).append(mid)

    canonical_entities: dict[str, CanonicalEntityNode] = {}
    for root_id, m_ids in sorted(clusters.items()):
        rep_mention = mention_nodes[min(m_ids)]
        rep_label = rep_mention.entity_ref or rep_mention.text
        cluster_id = f"ent_{root_id}"

        canonical_entities[cluster_id] = CanonicalEntityNode(
            entity_id=cluster_id,
            mention_ids=sorted(m_ids),
            canonical_label=rep_label,
        )

        # Update mention_nodes with canonical_entity_id
        for mid in m_ids:
            old_m = mention_nodes[mid]
            mention_nodes[mid] = MentionGraphNode(
                mention_id=old_m.mention_id,
                unit_id=old_m.unit_id,
                role=old_m.role,
                text=old_m.text,
                entity_ref=old_m.entity_ref,
                canonical_entity_id=cluster_id,
            )

    return OracleTypedGraph(
        graph_id=gid,
        cutoff_time=doc.cutoff_time,
        unit_nodes=unit_nodes,
        mention_nodes=mention_nodes,
        canonical_entities=canonical_entities,
        relation_edges=relation_edges,
        argument_edges=argument_edges,
        metadata={
            "graph_type": "agy_predicted",
            "source_document_id": doc.document_id,
            "admitted_unit_count": len(unit_nodes),
            "admitted_relation_count": len(relation_edges),
            "excluded_relation_count": len(doc.relations) - len(relation_edges),
        },
    )
