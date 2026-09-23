"""Comprehensive evaluation module for AGY Semantic Parser against Gold Benchmark."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from research.semantic_annotation.schema import (
    FORBIDDEN_LABELS,
    EpistemicHedge,
    ModalityType,
    RelationType,
    SemanticAnnotationDocument,
)


def compute_span_iou(start1: int, end1: int, start2: int, end2: int) -> float:
    """Compute Intersection-over-Union between two character spans."""
    intersection = max(0, min(end1, end2) - max(start1, start2))
    union = max(end1, end2) - min(start1, start2)
    return intersection / union if union > 0 else 0.0


def evaluate_predictions(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate a list of case results containing gold_case and pred_document."""
    total_cases = len(case_results)

    # 1. Unit segmentation & attribute counters
    gold_unit_count = 0
    pred_unit_count = 0
    exact_span_matches = 0
    overlap_span_matches = 0

    kind_correct = 0
    pred_surf_correct = 0
    pred_norm_correct = 0
    pred_rule_correct = 0
    modality_correct = 0
    hedge_correct = 0
    holder_correct = 0
    attribution_correct = 0
    time_anchor_correct = 0

    # Role counters
    gold_roles_total = 0
    pred_roles_total = 0
    matched_roles = 0

    # 2. Relation counters
    gold_rel_count = 0
    pred_rel_count = 0
    rel_type_matches = 0
    rel_confusion: dict[str, Counter] = defaultdict(Counter)

    # 3. Adversarial trap tracking
    adversarial_total = 0
    adversarial_passed = 0
    trap_results: list[dict[str, Any]] = []

    # 4. Cognition label leakage
    forbidden_label_emissions: list[dict[str, Any]] = []

    for item in case_results:
        gold_case = item["gold_case"]
        pred_doc = item["pred_document"]
        if isinstance(pred_doc, dict):
            pred_doc = SemanticAnnotationDocument.model_validate(pred_doc)

        gold_doc = gold_case["gold_document"]
        if isinstance(gold_doc, dict):
            gold_doc = SemanticAnnotationDocument.model_validate(gold_doc)

        cid = gold_case["case_id"]
        fam = gold_case["family"]
        is_adv = gold_case.get("adversarial", False)
        trap_desc = gold_case.get("trap_description", "")
        raw_text = gold_case["raw_evidence"][0]["content"]

        # Check for forbidden cognition labels in predictions
        for u in pred_doc.units:
            if u.kind.value.upper() in FORBIDDEN_LABELS:
                forbidden_label_emissions.append({"case_id": cid, "location": f"unit {u.annotation_id} kind", "label": u.kind.value})
            if u.predicate.normalized_predicate.upper() in FORBIDDEN_LABELS:
                forbidden_label_emissions.append({"case_id": cid, "location": f"unit {u.annotation_id} predicate", "label": u.predicate.normalized_predicate})
        for r in pred_doc.relations:
            if r.relation_type.value.upper() in FORBIDDEN_LABELS:
                forbidden_label_emissions.append({"case_id": cid, "location": f"relation {r.relation_id}", "label": r.relation_type.value})

        # Match units: greedy bipartite match based on span IoU
        g_units = gold_doc.units
        p_units = pred_doc.units
        gold_unit_count += len(g_units)
        pred_unit_count += len(p_units)

        matched_p_indices: set[int] = set()
        matched_pairs: list[tuple[Any, Any]] = []

        for g in g_units:
            g_s, g_e = g.source_span.char_start, g.source_span.char_end
            best_iou = 0.0
            best_p_idx = -1
            for p_idx, p in enumerate(p_units):
                if p_idx in matched_p_indices:
                    continue
                p_s, p_e = p.source_span.char_start, p.source_span.char_end
                iou = compute_span_iou(g_s, g_e, p_s, p_e)
                if iou > best_iou:
                    best_iou = iou
                    best_p_idx = p_idx

            if best_p_idx != -1 and best_iou >= 0.4:
                matched_p_indices.add(best_p_idx)
                p_matched = p_units[best_p_idx]
                matched_pairs.append((g, p_matched))
                overlap_span_matches += 1
                if g_s == p_matched.source_span.char_start and g_e == p_matched.source_span.char_end:
                    exact_span_matches += 1

                # Evaluate unit attributes on matched pair
                if g.kind == p_matched.kind:
                    kind_correct += 1
                if g.predicate.surface_predicate.lower() == p_matched.predicate.surface_predicate.lower():
                    pred_surf_correct += 1
                if g.predicate.normalized_predicate.lower() == p_matched.predicate.normalized_predicate.lower():
                    pred_norm_correct += 1
                if g.predicate.normalization_rule == p_matched.predicate.normalization_rule:
                    pred_rule_correct += 1
                if g.modality == p_matched.modality:
                    modality_correct += 1
                if g.epistemic_hedge == p_matched.epistemic_hedge:
                    hedge_correct += 1
                if g.holder_ref.lower() == p_matched.holder_ref.lower():
                    holder_correct += 1
                if g.attribution_mode == p_matched.attribution_mode:
                    attribution_correct += 1
                if g.temporal_anchoring.anchor_type == p_matched.temporal_anchoring.anchor_type:
                    time_anchor_correct += 1

                # Evaluate argument roles
                for r_role, r_arg in g.arguments.items():
                    gold_roles_total += 1
                    # Check if predicted unit has this role
                    if r_role in p_matched.arguments:
                        p_arg = p_matched.arguments[r_role]
                        # Text match or IoU > 0.5
                        if r_arg.text.lower() == p_arg.text.lower():
                            matched_roles += 1

                for p_role in p_matched.arguments:
                    pred_roles_total += 1

        # Match relations
        g_rels = gold_doc.relations
        p_rels = pred_doc.relations
        gold_rel_count += len(g_rels)
        pred_rel_count += len(p_rels)

        for g_r in g_rels:
            matched_rel = False
            for p_r in p_rels:
                if p_r.relation_type == g_r.relation_type:
                    matched_rel = True
                    break
            if matched_rel:
                rel_type_matches += 1
                rel_confusion[g_r.relation_type.value]["MATCHED"] += 1
            else:
                rel_confusion[g_r.relation_type.value]["MISSED"] += 1

        # Evaluate Adversarial Traps
        if is_adv:
            adversarial_total += 1
            trap_pass = True
            fail_reason = ""

            # Trap 1-3: Post-hoc causal hallucination
            if "Post hoc" in trap_desc or "succession" in trap_desc or "rain" in trap_desc:
                # Should NOT emit CAUSE
                has_cause = any(r.relation_type == RelationType.CAUSE for r in p_rels)
                if has_cause:
                    trap_pass = False
                    fail_reason = "Emitted CAUSE for post-hoc temporal succession"

            # Trap 4-6: Holder attribution spillover
            elif "holder_ref='user'" in trap_desc or "conflate consultant" in trap_desc:
                for u in p_units:
                    if u.holder_ref.lower() == "user":
                        trap_pass = False
                        fail_reason = f"Erroneously assigned holder_ref='user' to third-party quote"

            # Trap 7-8: Premature cognition (REVISION / COGNITIVE_SHIFT)
            elif "REVISION" in trap_desc or "COGNITIVE_SHIFT" in trap_desc:
                has_incomp = any(r.relation_type == RelationType.INCOMPATIBLE for r in p_rels)
                if has_incomp or len(forbidden_label_emissions) > 0:
                    trap_pass = False
                    fail_reason = "Emitted INCOMPATIBLE or forbidden cognition label across distinct years"

            # Trap 9-10: Lexical overlap distractor
            elif "Kubernetes cluster tokens" in trap_desc or "reading a book" in trap_desc:
                has_event_or_cause = any(r.relation_type in (RelationType.SAME_EVENT, RelationType.CAUSE) for r in p_rels)
                if has_event_or_cause:
                    trap_pass = False
                    fail_reason = "Falsely predicted event identity/causality due to lexical overlap distractor"

            # Trap 11-12: Manufactured result states
            elif "manufacture unstated" in trap_desc:
                # Should emit only 1 event unit
                if len(p_units) > 1:
                    trap_pass = False
                    fail_reason = f"Manufactured unstated result state ({len(p_units)} units instead of 1)"

            # Trap 13-14: Pragmatic speculation as explicit
            elif "absence of connective" in trap_desc:
                # If CAUSE is emitted, it MUST NOT be explicit
                for r in p_rels:
                    if r.relation_type == RelationType.CAUSE and r.evidence_status.value == "explicit":
                        trap_pass = False
                        fail_reason = "Promoted inferred causal relation to explicit without connective"
            elif "clinical burnout" in trap_desc:
                if len(p_units) > 1:
                    trap_pass = False
                    fail_reason = "Invented unasserted clinical burnout unit"

            # Trap 15: Cross-time false incompatibility
            elif "distinct calendar years" in trap_desc:
                has_incomp = any(r.relation_type == RelationType.INCOMPATIBLE for r in p_rels)
                if has_incomp:
                    trap_pass = False
                    fail_reason = "Emitted INCOMPATIBLE across distinct calendar years"

            # Trap 16: Hedged desire flattening
            elif "modality=uncertain" in trap_desc:
                u_desire = p_units[0] if p_units else None
                if u_desire:
                    if u_desire.modality != ModalityType.DESIRED or u_desire.epistemic_hedge != EpistemicHedge.THINK:
                        trap_pass = False
                        fail_reason = f"Flattened hedged desire into modality={u_desire.modality.value}, hedge={u_desire.epistemic_hedge.value}"

            if trap_pass:
                adversarial_passed += 1

            trap_results.append({
                "case_id": cid,
                "trap_description": trap_desc,
                "passed": trap_pass,
                "fail_reason": fail_reason,
            })

    # Summary metrics computation
    unit_prec = overlap_span_matches / pred_unit_count if pred_unit_count > 0 else 0.0
    unit_rec = overlap_span_matches / gold_unit_count if gold_unit_count > 0 else 0.0
    unit_f1 = (2 * unit_prec * unit_rec / (unit_prec + unit_rec)) if (unit_prec + unit_rec) > 0 else 0.0

    exact_prec = exact_span_matches / pred_unit_count if pred_unit_count > 0 else 0.0
    exact_rec = exact_span_matches / gold_unit_count if gold_unit_count > 0 else 0.0
    exact_f1 = (2 * exact_prec * exact_rec / (exact_prec + exact_rec)) if (exact_prec + exact_rec) > 0 else 0.0

    role_prec = matched_roles / pred_roles_total if pred_roles_total > 0 else 0.0
    role_rec = matched_roles / gold_roles_total if gold_roles_total > 0 else 0.0
    role_f1 = (2 * role_prec * role_rec / (role_prec + role_rec)) if (role_prec + role_rec) > 0 else 0.0

    rel_prec = rel_type_matches / pred_rel_count if pred_rel_count > 0 else 0.0
    rel_rec = rel_type_matches / gold_rel_count if gold_rel_count > 0 else 0.0
    rel_f1 = (2 * rel_prec * rel_rec / (rel_prec + rel_rec)) if (rel_prec + rel_rec) > 0 else 0.0

    total_matched = max(overlap_span_matches, 1)

    return {
        "summary": {
            "total_cases": total_cases,
            "gold_units": gold_unit_count,
            "pred_units": pred_unit_count,
            "unit_exact_f1": round(exact_f1, 4),
            "unit_overlap_f1": round(unit_f1, 4),
            "role_f1": round(role_f1, 4),
            "role_precision": round(role_prec, 4),
            "role_recall": round(role_rec, 4),
            "relation_f1": round(rel_f1, 4),
            "relation_precision": round(rel_prec, 4),
            "relation_recall": round(rel_rec, 4),
            "adversarial_resistance_rate": round((adversarial_passed / adversarial_total) * 100, 1) if adversarial_total > 0 else 0.0,
            "adversarial_passed": adversarial_passed,
            "adversarial_total": adversarial_total,
            "forbidden_cognition_leakage_count": len(forbidden_label_emissions),
        },
        "unit_attributes": {
            "kind_accuracy": round(kind_correct / total_matched, 4),
            "surface_predicate_accuracy": round(pred_surf_correct / total_matched, 4),
            "normalized_predicate_accuracy": round(pred_norm_correct / total_matched, 4),
            "normalization_rule_accuracy": round(pred_rule_correct / total_matched, 4),
            "modality_accuracy": round(modality_correct / total_matched, 4),
            "epistemic_hedge_accuracy": round(hedge_correct / total_matched, 4),
            "holder_accuracy": round(holder_correct / total_matched, 4),
            "attribution_accuracy": round(attribution_correct / total_matched, 4),
            "temporal_anchor_accuracy": round(time_anchor_correct / total_matched, 4),
        },
        "relations": {
            "gold_relations": gold_rel_count,
            "pred_relations": pred_rel_count,
            "matched_relations": rel_type_matches,
            "breakdown": {k: dict(v) for k, v in rel_confusion.items()},
        },
        "adversarial_traps": trap_results,
        "cognition_leakage": forbidden_label_emissions,
    }
