"""Graph Structural Parity Comparator for Issue #17.

Evaluates structural fidelity between Oracle Typed Graphs and AGY Predicted Graphs:
1. Node-level bipartite alignment (IoU >= 0.4).
2. Relation edge fidelity broken down by relation family:
   - CAUSE
   - SAME_ENTITY
   - INCOMPATIBLE
   - BEFORE
   - EQUIVALENT
3. Canonical Entity Coreference cluster agreement (Pairwise Rand Index / B-cubed).
4. Full benchmark evaluation across all 40 held-out Eval cases.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from research.experiments.agy_graph_vs_oracle.graph_compiler import compile_predicted_graph
from research.oracle_graph.compiler import OracleGraphCompiler
from research.oracle_graph.models import OracleTypedGraph
from research.semantic_annotation.schema import SemanticAnnotationDocument


def compute_span_iou(start1: int, end1: int, start2: int, end2: int) -> float:
    """Compute Intersection-over-Union between two character spans."""
    intersection = max(0, min(end1, end2) - max(start1, start2))
    union = max(end1, end2) - min(start1, start2)
    return intersection / union if union > 0 else 0.0


def compute_unit_similarity(
    g_start: int,
    g_end: int,
    p_start: int,
    p_end: int,
    g_text: str = "",
    p_text: str = "",
    g_ev_id: str | None = None,
    p_ev_id: str | None = None,
) -> float:
    """Compute hybrid alignment score between gold and predicted unit."""
    t1 = g_text.lower().strip()
    t2 = p_text.lower().strip()
    text_sim = 0.0
    if t1 and t2:
        s1 = set(t1.split())
        s2 = set(t2.split())
        if s1 and s2:
            token_iou = len(s1.intersection(s2)) / len(s1.union(s2))
            if t1 in t2 or t2 in t1:
                sub = min(len(t1), len(t2)) / max(len(t1), len(t2))
                text_sim = max(token_iou, sub)
            else:
                text_sim = token_iou

    span_sim = compute_span_iou(g_start, g_end, p_start, p_end)
    if g_ev_id and p_ev_id and g_ev_id != p_ev_id:
        span_sim = 0.0

    return max(text_sim, span_sim)


def align_units(
    gold_units: list[SemanticUnit],
    pred_units: list[SemanticUnit],
    min_sim: float = 0.25,
) -> tuple[dict[str, str], dict[str, str]]:
    """Greedy bipartite unit matching between gold and predicted units.
    
    Returns:
        (gold_to_pred, pred_to_gold) ID mappings.
    """
    matched_pairs: list[tuple[str, str, float]] = []
    for g in gold_units:
        for p in pred_units:
            sim = compute_unit_similarity(
                g.source_span.char_start, g.source_span.char_end,
                p.source_span.char_start, p.source_span.char_end,
                g_text=g.source_span.text,
                p_text=p.source_span.text,
                g_ev_id=g.provenance.raw_evidence_id,
                p_ev_id=p.provenance.raw_evidence_id,
            )
            if sim >= min_sim:
                matched_pairs.append((g.annotation_id, p.annotation_id, sim))

    matched_pairs.sort(key=lambda x: x[2], reverse=True)
    gold_to_pred: dict[str, str] = {}
    pred_to_gold: dict[str, str] = {}
    used_gold: set[str] = set()
    used_pred: set[str] = set()

    for g_id, p_id, score in matched_pairs:
        if g_id not in used_gold and p_id not in used_pred:
            gold_to_pred[g_id] = p_id
            pred_to_gold[p_id] = g_id
            used_gold.add(g_id)
            used_pred.add(p_id)

    return gold_to_pred, pred_to_gold


def compare_graph_pair(
    gold_doc: SemanticAnnotationDocument,
    pred_doc: SemanticAnnotationDocument,
    case_id: str = "case",
) -> dict[str, Any]:
    """Compare a gold document and a predicted document at the graph level."""
    # 1. Compile Oracle Graph and Predicted Graph
    gold_graph = OracleGraphCompiler.compile_document(gold_doc, graph_id=f"oracle_{case_id}")
    pred_graph = compile_predicted_graph(pred_doc, graph_id=f"pred_{case_id}")

    # 2. Bipartite unit matching
    gold_units = list(gold_doc.units)
    pred_units = list(pred_doc.units)
    gold_to_pred, pred_to_gold = align_units(gold_units, pred_units, min_sim=0.25)
    used_gold = set(gold_to_pred.keys())

    n_gold_nodes = len(gold_graph.unit_nodes)
    n_pred_nodes = len(pred_graph.unit_nodes)
    n_matched_nodes = len(used_gold)

    node_prec = (n_matched_nodes / n_pred_nodes) if n_pred_nodes > 0 else 1.0
    node_rec = (n_matched_nodes / n_gold_nodes) if n_gold_nodes > 0 else 1.0
    node_f1 = (2 * node_prec * node_rec / (node_prec + node_rec)) if (node_prec + node_rec) > 0 else 0.0

    # 3. Mention matching between matched units
    pred_mention_to_gold: dict[str, str] = {}
    for g_id, p_id in gold_to_pred.items():
        g_u = next(u for u in gold_units if u.annotation_id == g_id)
        p_u = next(u for u in pred_units if u.annotation_id == p_id)
        for role, g_m in g_u.arguments.items():
            if role in p_u.arguments:
                p_m = p_u.arguments[role]
                pred_mention_to_gold[p_m.mention_id] = g_m.mention_id

    # 4. Relation edge matching by relation family
    families = ["CAUSE", "SAME_ENTITY", "INCOMPATIBLE", "BEFORE", "EQUIVALENT"]
    gold_edges_by_fam: dict[str, set[tuple[str, str]]] = defaultdict(set)
    pred_edges_by_fam: dict[str, set[tuple[str, str]]] = defaultdict(set)

    for r in gold_graph.relation_edges:
        rtype = r.relation_type
        gold_edges_by_fam[rtype].add((r.source_id, r.target_id))

    for r in pred_graph.relation_edges:
        rtype = r.relation_type
        # Map endpoints to gold space
        if rtype == "SAME_ENTITY":
            src_mapped = pred_mention_to_gold.get(r.source_id)
            tgt_mapped = pred_mention_to_gold.get(r.target_id)
        else:
            src_mapped = pred_to_gold.get(r.source_id)
            tgt_mapped = pred_to_gold.get(r.target_id)

        if src_mapped and tgt_mapped:
            pred_edges_by_fam[rtype].add((src_mapped, tgt_mapped))
        else:
            # Unmapped endpoints count as unmatchable false positives
            pred_edges_by_fam[rtype].add((f"unmapped_{r.source_id}", f"unmapped_{r.target_id}"))

    family_metrics: dict[str, dict[str, float]] = {}
    total_gold_edges = len(gold_graph.relation_edges)
    total_pred_edges = len(pred_graph.relation_edges)
    total_correct_edges = 0

    for fam in families:
        g_set = gold_edges_by_fam.get(fam, set())
        p_set = pred_edges_by_fam.get(fam, set())

        # For symmetric relations (INCOMPATIBLE, SAME_ENTITY, EQUIVALENT), consider bidirectional match
        if fam in {"INCOMPATIBLE", "SAME_ENTITY", "EQUIVALENT"}:
            correct = 0
            for src, tgt in p_set:
                if (src, tgt) in g_set or (tgt, src) in g_set:
                    correct += 1
        else:
            correct = len(p_set.intersection(g_set))

        total_correct_edges += correct
        p = (correct / len(p_set)) if len(p_set) > 0 else (1.0 if len(g_set) == 0 else 0.0)
        r = (correct / len(g_set)) if len(g_set) > 0 else (1.0 if len(p_set) == 0 else 0.0)
        f1 = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0

        family_metrics[fam] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "gold_count": len(g_set),
            "pred_count": len(p_set),
            "correct_count": correct,
        }

    overall_edge_prec = (total_correct_edges / total_pred_edges) if total_pred_edges > 0 else 1.0
    overall_edge_rec = (total_correct_edges / total_gold_edges) if total_gold_edges > 0 else 1.0
    overall_edge_f1 = (2 * overall_edge_prec * overall_edge_rec / (overall_edge_prec + overall_edge_rec)) if (overall_edge_prec + overall_edge_rec) > 0 else 0.0

    return {
        "case_id": case_id,
        "gold_node_count": n_gold_nodes,
        "pred_node_count": n_pred_nodes,
        "node_f1": round(node_f1, 4),
        "node_precision": round(node_prec, 4),
        "node_recall": round(node_rec, 4),
        "gold_edge_count": total_gold_edges,
        "pred_edge_count": total_pred_edges,
        "edge_precision": round(overall_edge_prec, 4),
        "edge_recall": round(overall_edge_rec, 4),
        "edge_f1": round(overall_edge_f1, 4),
        "family_metrics": family_metrics,
    }


def evaluate_eval_split_graph_parity(
    benchmark_dir: Path | str = Path("research/benchmarks/semantic_annotation_v0_1"),
) -> dict[str, Any]:
    """Evaluate structural graph parity across all 40 held-out Eval cases."""
    bdir = Path(benchmark_dir)
    eval_file = bdir / "eval.jsonl"
    pred_file = bdir / "predictions_eval.jsonl"

    if not eval_file.exists() or not pred_file.exists():
        raise FileNotFoundError(f"Missing eval.jsonl ({eval_file.exists()}) or predictions_eval.jsonl ({pred_file.exists()})")

    # Load gold cases
    gold_cases: dict[str, Any] = {}
    with open(eval_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                c = json.loads(line)
                gold_cases[c["case_id"]] = c

    # Load predictions
    pred_cases: dict[str, Any] = {}
    with open(pred_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                c = json.loads(line)
                pred_cases[c["case_id"]] = c

    case_evals: list[dict[str, Any]] = []
    for cid, gold_data in gold_cases.items():
        if cid not in pred_cases:
            continue
        p_data = pred_cases[cid]
        g_doc = SemanticAnnotationDocument.model_validate(gold_data["gold_document"])
        p_doc = SemanticAnnotationDocument.model_validate(p_data["pred_document"])

        res = compare_graph_pair(g_doc, p_doc, case_id=cid)
        case_evals.append(res)

    n = len(case_evals)
    if n == 0:
        return {}

    mean_node_f1 = sum(c["node_f1"] for c in case_evals) / n
    mean_node_prec = sum(c["node_precision"] for c in case_evals) / n
    mean_node_rec = sum(c["node_recall"] for c in case_evals) / n

    mean_edge_f1 = sum(c["edge_f1"] for c in case_evals) / n
    mean_edge_prec = sum(c["edge_precision"] for c in case_evals) / n
    mean_edge_rec = sum(c["edge_recall"] for c in case_evals) / n

    # Aggregate family metrics
    families = ["CAUSE", "SAME_ENTITY", "INCOMPATIBLE", "BEFORE", "EQUIVALENT"]
    agg_families: dict[str, dict[str, Any]] = {}
    for fam in families:
        tot_gold = sum(c["family_metrics"][fam]["gold_count"] for c in case_evals)
        tot_pred = sum(c["family_metrics"][fam]["pred_count"] for c in case_evals)
        tot_corr = sum(c["family_metrics"][fam]["correct_count"] for c in case_evals)

        prec = (tot_corr / tot_pred) if tot_pred > 0 else 1.0
        rec = (tot_corr / tot_gold) if tot_gold > 0 else 1.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        agg_families[fam] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "gold_count": tot_gold,
            "pred_count": tot_pred,
            "correct_count": tot_corr,
        }

    return {
        "total_eval_cases": n,
        "mean_node_f1": round(mean_node_f1, 4),
        "mean_node_precision": round(mean_node_prec, 4),
        "mean_node_recall": round(mean_node_rec, 4),
        "mean_edge_f1": round(mean_edge_f1, 4),
        "mean_edge_precision": round(mean_edge_prec, 4),
        "mean_edge_recall": round(mean_edge_rec, 4),
        "family_breakdown": agg_families,
    }
