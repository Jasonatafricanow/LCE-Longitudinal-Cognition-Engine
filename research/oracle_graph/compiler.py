"""Deterministic Oracle Typed Graph Compiler with strict input provenance security.

Adheres strictly to the frozen v0.1 ontology:
- Only units and relations with evidence_status in {explicit, entailed} are admitted.
- Control relations (NO_RELATION, UNKNOWN, TEMPORAL_UNKNOWN) and inferred relations are strictly excluded.
- Absolute ban on reading prediction artifacts: any attempt to ingest predictions raises SecurityAdmissionError.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from research.oracle_graph.models import (
    ArgumentGraphEdge,
    CanonicalEntityNode,
    MentionGraphNode,
    OracleTypedGraph,
    RelationGraphEdge,
    UnitGraphNode,
)
from research.semantic_annotation.schema import (
    CONTROL_RELATION_TYPES,
    GRAPH_ADMISSIBLE_EVIDENCE_STATUSES,
    SemanticAnnotationDocument,
)


class SecurityAdmissionError(Exception):
    """Raised when predictions or uncertified non-gold artifacts are passed to Oracle Graph."""


class OracleInputProvenanceGuard:
    """Security boundary ensuring only certified gold annotations enter the Oracle Graph."""

    @staticmethod
    def validate_source(source_path: str | Path | None = None, data: dict[str, Any] | None = None) -> None:
        """Reject prediction files and uncertified data sources."""
        if source_path is not None:
            path_str = str(source_path).replace("\\", "/").lower()
            if "prediction" in path_str:
                raise SecurityAdmissionError(
                    f"CRITICAL SECURITY VIOLATION: Attempted to compile Oracle Graph from prediction artifact: '{source_path}'. "
                    "Oracle Graph input is strictly restricted to certified gold annotations."
                )

        if data is not None:
            # Check for prediction-specific keys or missing gold certification
            if "prediction" in data or "pred_document" in data:
                raise SecurityAdmissionError(
                    "CRITICAL SECURITY VIOLATION: Input dictionary contains prediction keys ('prediction' / 'pred_document'). "
                    "Oracle Graph compiler permits only gold annotations."
                )


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
            # Deterministic ordering by string comparison
            if root_x < root_y:
                self.parent[root_y] = root_x
            else:
                self.parent[root_x] = root_y


class OracleGraphCompiler:
    """Compiles certified gold SemanticAnnotationDocuments into OracleTypedGraphs."""

    @classmethod
    def compile_document(
        cls,
        doc: SemanticAnnotationDocument,
        graph_id: str | None = None,
        source_path: str | Path | None = None,
    ) -> OracleTypedGraph:
        """Compile a single SemanticAnnotationDocument into an OracleTypedGraph."""
        # 1. Enforce strict provenance security
        OracleInputProvenanceGuard.validate_source(source_path=source_path)

        gid = graph_id or doc.document_id
        unit_nodes: dict[str, UnitGraphNode] = {}
        mention_nodes: dict[str, MentionGraphNode] = {}
        argument_edges: list[ArgumentGraphEdge] = []
        relation_edges: list[RelationGraphEdge] = []

        # 2. Admit Units and extract Argument Mentions
        for u in doc.units:
            if not u.is_graph_eligible:
                # Inferred and unknown units are audit-only; exclude from positive graph
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

        # 3. Admit Relations and collect Coreference
        uf = UnionFind()
        for r in doc.relations:
            # Must satisfy is_graph_edge (non-control and explicit/entailed)
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

            # If relation is SAME_ENTITY, union mention IDs
            if r.relation_type.value == "SAME_ENTITY":
                uf.union(r.source_id, r.target_id)

        # 4. Resolve Canonical Entity Clusters
        # Group mentions by their Union-Find root
        cluster_groups: dict[str, list[str]] = {}
        for m_id in mention_nodes:
            root = uf.find(m_id)
            cluster_groups.setdefault(root, []).append(m_id)

        canonical_entities: dict[str, CanonicalEntityNode] = {}
        for idx, (root, m_ids) in enumerate(sorted(cluster_groups.items())):
            # Pick representative label: prioritize explicit entity_ref, else surface text
            rep_label = ""
            for mid in m_ids:
                m = mention_nodes[mid]
                if m.entity_ref:
                    rep_label = m.entity_ref
                    break
            if not rep_label:
                rep_label = mention_nodes[m_ids[0]].text

            cluster_id = f"ent_{rep_label.lower().replace(' ', '_')}_{idx}" if rep_label else f"ent_cluster_{idx}"
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
                "source_document_id": doc.document_id,
                "admitted_unit_count": len(unit_nodes),
                "admitted_relation_count": len(relation_edges),
                "excluded_relation_count": len(doc.relations) - len(relation_edges),
            },
        )


def compile_oracle_graph(
    doc: SemanticAnnotationDocument,
    graph_id: str | None = None,
    input_provenance_path: str | Path | None = None,
) -> OracleTypedGraph:
    """Convenience helper to compile certified gold document into OracleTypedGraph."""
    return OracleGraphCompiler.compile_document(
        doc=doc,
        graph_id=graph_id,
        source_path=input_provenance_path,
    )

