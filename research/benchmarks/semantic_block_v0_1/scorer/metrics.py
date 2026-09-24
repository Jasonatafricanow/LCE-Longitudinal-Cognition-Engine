"""Scoring, metric computation, and hard safety gates for Issue #19."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from research.benchmarks.semantic_block_v0_1.consumer.raw_hidden import RawHiddenConsumer
from research.benchmarks.semantic_block_v0_1.contracts import (
    PredictionRecord,
    PublicRelation,
    PublicSemanticBlock,
)
from research.benchmarks.semantic_block_v0_1.scorer.alignment import StateAlignment, align_states


@dataclass
class CutoffScore:
    case_id: str
    cutoff: str
    arm_id: str
    exact_block_count: bool
    gold_state_count: int
    pred_state_count: int
    aligned_state_count: int
    account_exact_matches: int
    required_fields_total: int
    required_fields_correct: int
    abstentions_justified: int
    abstentions_unjustified: int
    relations_tp: int
    relations_fp: int
    relations_fn: int
    forbidden_violations: list[str] = field(default_factory=list)
    hard_failures: list[str] = field(default_factory=list)
    field_breakdown: dict[str, dict[str, int]] = field(default_factory=dict)


def _normalize_text(text: str) -> str:
    return re.sub(r"\W+", " ", text).strip().lower()


def _canonical_meaning_entailed(pred_text: str, gold_text: str) -> bool:
    """Check if predicted canonical meaning entails gold meaning."""
    if not pred_text or pred_text == "UNKNOWN":
        return False
    p_norm = _normalize_text(pred_text)
    g_norm = _normalize_text(gold_text)
    if p_norm == g_norm:
        return True
    stopwords = {"the", "a", "an", "on", "in", "to", "and", "is", "of", "it", "at", "for", "by", "with"}
    gold_words = set(w for w in g_norm.split() if w not in stopwords and not w.isdigit())
    pred_words = set(p_norm.split())
    if gold_words and (gold_words <= pred_words or len(gold_words & pred_words) / len(gold_words) >= 0.65):
        return True
    return False


def _match_participants(pred_parts: dict[str, Any], gold_parts: dict[str, Any]) -> bool:
    if not pred_parts:
        return not gold_parts
    for g_role, g_val in gold_parts.items():
        matched = False
        gv = str(g_val).lower().strip()
        for p_role, p_val in pred_parts.items():
            pv = str(p_val).lower().strip()
            if gv == pv or gv in pv or pv in gv:
                matched = True
                break
        if not matched:
            return False
    return True


def score_cutoff_prediction(
    prediction: PredictionRecord,
    gold_case: dict[str, Any],
    cutoff: str,
    consumer: RawHiddenConsumer,
) -> CutoffScore:
    """Evaluate one prediction record against frozen gold for a specific cutoff."""
    arm_id = prediction.arm_id
    case_id = prediction.case_id

    # 1. Identify gold visible states and relations at this cutoff
    vis_entry = next((v for v in gold_case["visibility"] if v["cutoff"] == cutoff), None)
    if not vis_entry:
        raise ValueError(f"Cutoff {cutoff} not found in gold visibility for {case_id}")

    gold_vis_keys = set(vis_entry["visible_state_keys"])
    gold_vis_states = [s for s in gold_case["states"] if s["state_key"] in gold_vis_keys]
    gold_by_key = {s["state_key"]: s for s in gold_vis_states}

    # Predicted blocks visible at this cutoff
    pred_vis_blocks = [b for b in prediction.blocks if b.state_available_at <= cutoff]
    pred_by_id = {b.state_id: b for b in pred_vis_blocks}

    # 2. Alignment
    alignment = align_states(pred_vis_blocks, gold_vis_states)

    exact_block_count = (len(pred_vis_blocks) == len(gold_vis_states))

    # 3. Field Scoring via Downstream Consumer Queries
    required_fields = [
        "canonical_content", "predicate_kind", "participants", "holder",
        "utterer", "attribution_mode", "polarity", "modality",
        "epistemic_hedge", "valid_time_precision", "entity_status_uncertainty",
        "availability", "provenance",
    ]

    field_counts = {f: {"correct": 0, "total": len(gold_vis_states)} for f in required_fields}
    account_exact_matches = 0
    justified_abstain = 0
    unjustified_abstain = 0
    hard_failures: list[str] = []
    forbidden_violations: list[str] = []

    for gkey, gold_state in gold_by_key.items():
        pid = alignment.gold_to_pred.get(gkey)
        if not pid:
            # Unmatched gold state: all fields 0
            continue

        pred_blk = pred_by_id[pid]
        # Query consumer
        c_desc = consumer.describe_state(pid)
        c_holder = consumer.holder_and_utterer(pid)
        c_part = consumer.participants_and_predicate(pid)
        c_pol = consumer.polarity_modality_hedge(pid)
        c_time = consumer.time_and_availability(pid)
        c_supp = consumer.support_refs(pid)
        c_ident = consumer.identity_status(pid)

        state_all_correct = True

        # Field 1: canonical_content
        if _canonical_meaning_entailed(c_desc, gold_state["canonical_content"]):
            field_counts["canonical_content"]["correct"] += 1
        else:
            state_all_correct = False
            if c_desc == "UNKNOWN":
                unjustified_abstain += 1

        # Field 2: predicate_kind
        cp = c_part["predicate"].lower()
        gp = gold_state["predicate"].lower()
        pred_match = (cp == gp or gp in cp or cp in gp)
        kind_match = (c_part["kind"].lower() == gold_state["kind"].lower())
        if pred_match and kind_match:
            field_counts["predicate_kind"]["correct"] += 1
        else:
            state_all_correct = False

        # Field 3: participants
        if _match_participants(c_part["participants"], gold_state["participants"]):
            field_counts["participants"]["correct"] += 1
        else:
            state_all_correct = False

        # Field 4: holder
        if c_holder["holder"].lower() == gold_state["holder"].lower():
            field_counts["holder"]["correct"] += 1
        else:
            state_all_correct = False
            # Check silent holder flip: third-party quote attributed to user
            if gold_state["holder"].lower() != "user" and c_holder["holder"].lower() == "user":
                hard_failures.append(f"silent_holder_flip in {gkey}: {gold_state['holder']} -> user")

        # Field 5: utterer
        if c_holder["utterer"].lower() == gold_state["utterer"].lower():
            field_counts["utterer"]["correct"] += 1
        else:
            state_all_correct = False

        # Field 6: attribution_mode
        if c_holder["attribution_mode"].lower() == gold_state["attribution_mode"].lower():
            field_counts["attribution_mode"]["correct"] += 1
        else:
            state_all_correct = False

        # Field 7: polarity
        if c_pol["polarity"].lower() == gold_state["polarity"].lower():
            field_counts["polarity"]["correct"] += 1
        else:
            state_all_correct = False

        # Field 8: modality
        if c_pol["modality"].lower() == gold_state["modality"].lower():
            field_counts["modality"]["correct"] += 1
        else:
            state_all_correct = False

        # Field 9: epistemic_hedge
        if c_pol["epistemic_hedge"].lower() == gold_state["epistemic_hedge"].lower():
            field_counts["epistemic_hedge"]["correct"] += 1
        else:
            state_all_correct = False

        # Field 10: valid_time_precision
        time_match = (str(c_time["valid_time"]) == str(gold_state["valid_time"]))
        prec_match = (c_time["time_precision"] == gold_state["time_precision"])
        if time_match and prec_match:
            field_counts["valid_time_precision"]["correct"] += 1
        else:
            state_all_correct = False

        # Field 11: entity_status_uncertainty
        stat_match = (c_ident["entity_status"] == gold_state["entity_status"])
        unc_match = (c_ident["uncertainty"] == gold_state["uncertainty"])
        if stat_match and unc_match:
            field_counts["entity_status_uncertainty"]["correct"] += 1
        else:
            state_all_correct = False

        # Field 12: availability
        if c_time["state_available_at"] == gold_state["available_at"]:
            field_counts["availability"]["correct"] += 1
        else:
            state_all_correct = False

        # Field 13: provenance (span coordinates match gold source spans)
        gold_spans = gold_state["source_spans"]
        pred_spans = c_supp["source_spans"]
        prov_correct = False
        if len(pred_spans) == len(gold_spans):
            spans_match = True
            for gs in gold_spans:
                if not any(
                    ps["evidence_id"] == gs["evidence_id"]
                    and ps["char_start"] == gs["char_start"]
                    and ps["char_end"] == gs["char_end"]
                    for ps in pred_spans
                ):
                    spans_match = False
                    break
            prov_correct = spans_match
        if prov_correct:
            field_counts["provenance"]["correct"] += 1
        else:
            state_all_correct = False

        if state_all_correct:
            account_exact_matches += 1

    total_req_instances = len(gold_vis_states) * len(required_fields)
    total_correct_instances = sum(v["correct"] for v in field_counts.values())

    # 4. Relations Scoring
    # Gold relations visible at this cutoff:
    gold_vis_rels = [
        r for r in gold_case["relations"]
        if r["source_state_key"] in gold_vis_keys and r["target_state_key"] in gold_vis_keys
    ]

    pred_vis_rels = [
        r for r in prediction.relations
        if r.source_state_id in pred_by_id and r.target_state_id in pred_by_id
    ]

    # Map predicted relations to gold endpoints
    mapped_pred_rels: list[tuple[str, str, str]] = []
    for pr in pred_vis_rels:
        g_src = alignment.pred_to_gold.get(pr.source_state_id)
        g_tgt = alignment.pred_to_gold.get(pr.target_state_id)
        if g_src and g_tgt:
            mapped_pred_rels.append((pr.type, g_src, g_tgt))
        else:
            # Broken or unaligned endpoint
            hard_failures.append(f"invalid_relation_endpoint in relation {pr.source_state_id}->{pr.target_state_id}")

    gold_rel_tuples = [
        (r["type"], r["source_state_key"], r["target_state_key"])
        for r in gold_vis_rels
    ]

    rel_tp = 0
    rel_fp = 0
    matched_gold_rels = set()

    for mpr in mapped_pred_rels:
        if mpr in gold_rel_tuples:
            rel_tp += 1
            matched_gold_rels.add(mpr)
        else:
            rel_fp += 1
            # Check if reversed CAUSE
            rev_cause = ("CAUSE", mpr[2], mpr[1])
            if rev_cause in gold_rel_tuples:
                hard_failures.append(f"reversed_cause {mpr[1]}<-{mpr[2]}")

    rel_fn = len(gold_rel_tuples) - len(matched_gold_rels)

    # 5. Check Forbidden Case Outputs
    forbidden_list = gold_case.get("forbidden_case_outputs", [])
    for fb in forbidden_list:
        if fb == "CAUSE":
            # Any CAUSE relation emitted is forbidden
            if any(r.type == "CAUSE" for r in pred_vis_rels):
                forbidden_violations.append("forbidden_CAUSE_emitted")
                hard_failures.append("forbidden_CAUSE_emitted")
        elif fb == "CAUSE_s1_s3_direct":
            # Direct s1 -> s3 CAUSE edge is forbidden
            s1_id = alignment.gold_to_pred.get("s1")
            s3_id = alignment.gold_to_pred.get("s3")
            if s1_id and s3_id:
                if any(r.type == "CAUSE" and r.source_state_id == s1_id and r.target_state_id == s3_id for r in pred_vis_rels):
                    forbidden_violations.append("forbidden_direct_s1_s3_cause")
                    hard_failures.append("forbidden_direct_s1_s3_cause")
        elif fb == "SAME_ENTITY":
            if any(r.type == "SAME_ENTITY" for r in pred_vis_rels):
                forbidden_violations.append("forbidden_SAME_ENTITY_emitted")
                hard_failures.append("forbidden_SAME_ENTITY_emitted")
        elif fb == "user_believes_migration_safe":
            s1_id = alignment.gold_to_pred.get("s1")
            if s1_id and pred_by_id[s1_id].holder.lower() == "user":
                forbidden_violations.append("user_believes_migration_safe")
                hard_failures.append("silent_holder_flip")
        elif fb == "user_believes_Cedar_ready":
            s1_id = alignment.gold_to_pred.get("s1")
            if s1_id and pred_by_id[s1_id].holder.lower() == "user":
                forbidden_violations.append("user_believes_Cedar_ready")
                hard_failures.append("silent_holder_flip")
        elif fb == "joined_as_occurred":
            s1_id = alignment.gold_to_pred.get("s1")
            if s1_id and pred_by_id[s1_id].modality == "asserted":
                forbidden_violations.append("future_intention_promoted_to_occurred")
                hard_failures.append("unsupported_canonical_assertion")
        elif fb == "move_occurred":
            s1_id = alignment.gold_to_pred.get("s1")
            if s1_id and pred_by_id[s1_id].modality == "asserted":
                forbidden_violations.append("possible_move_promoted_to_occurred")
                hard_failures.append("unsupported_canonical_assertion")
        elif fb in ("actor_Mira", "actor_Lila"):
            s2_id = alignment.gold_to_pred.get("s2")
            if s2_id and any(fb.split("_")[1].lower() in str(v).lower() for v in pred_by_id[s2_id].participants.values()):
                forbidden_violations.append(f"ambiguous_actor_guessed_{fb}")
                hard_failures.append("unsupported_canonical_assertion")

    # Check future leaks across all predicted blocks
    for b in prediction.blocks:
        if b.state_available_at > cutoff and b in pred_vis_blocks:
            hard_failures.append(f"future_cutoff_leak: {b.state_id} at {b.state_available_at} > {cutoff}")

    # Check raw read violations in consumer
    if consumer.audit.raw_read_attempts > 0:
        hard_failures.append(f"raw_reread_attempt: {consumer.audit.raw_read_attempts}")

    return CutoffScore(
        case_id=case_id,
        cutoff=cutoff,
        arm_id=arm_id,
        exact_block_count=exact_block_count,
        gold_state_count=len(gold_vis_states),
        pred_state_count=len(pred_vis_blocks),
        aligned_state_count=len(alignment.pred_to_gold),
        account_exact_matches=account_exact_matches,
        required_fields_total=total_req_instances,
        required_fields_correct=total_correct_instances,
        abstentions_justified=justified_abstain,
        abstentions_unjustified=unjustified_abstain,
        relations_tp=rel_tp,
        relations_fp=rel_fp,
        relations_fn=rel_fn,
        forbidden_violations=forbidden_violations,
        hard_failures=hard_failures,
        field_breakdown=field_counts,
    )
