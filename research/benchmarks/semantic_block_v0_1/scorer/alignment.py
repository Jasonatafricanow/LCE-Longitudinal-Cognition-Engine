"""One-to-one state matching for Issue #19 evaluation.

Matches predicted and gold visible states by maximum character-range intersection
over shared evidence IDs. Ties resolve by predicate agreement then sorted
(predicted_state_id, gold_state_key). Zero-overlap pairs remain unmatched.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from research.benchmarks.semantic_block_v0_1.contracts import PublicSemanticBlock


@dataclass(frozen=True, slots=True)
class StateAlignment:
    pred_to_gold: dict[str, str]
    gold_to_pred: dict[str, str]
    unmatched_preds: list[str]
    unmatched_golds: list[str]
    overlap_scores: dict[str, int]


def _span_overlap(
    p_spans: list[Any],
    g_spans: list[dict[str, Any]],
) -> int:
    """Calculate total character intersection across shared evidence IDs."""
    total = 0
    for ps in p_spans:
        p_eid = getattr(ps, "evidence_id", ps.get("evidence_id") if isinstance(ps, dict) else "")
        p_start = getattr(ps, "char_start", ps.get("char_start") if isinstance(ps, dict) else 0)
        p_end = getattr(ps, "char_end", ps.get("char_end") if isinstance(ps, dict) else 0)

        for gs in g_spans:
            g_eid = gs["evidence_id"]
            if p_eid == g_eid:
                start = max(p_start, gs["char_start"])
                end = min(p_end, gs["char_end"])
                if end > start:
                    total += (end - start)
    return total


def align_states(
    predicted_states: list[PublicSemanticBlock],
    gold_states: list[dict[str, Any]],
) -> StateAlignment:
    """Align predicted visible states to gold visible states one-to-one."""
    gold_by_key = {g["state_key"]: g for g in gold_states}
    pred_by_id = {p.state_id: p for p in predicted_states}

    candidates: list[tuple[int, bool, str, str]] = []

    for p in predicted_states:
        for g in gold_states:
            overlap = _span_overlap(p.source_spans, g["source_spans"])
            if overlap > 0:
                pred_match = (p.predicate.lower() == g["predicate"].lower())
                candidates.append((overlap, pred_match, p.state_id, g["state_key"]))

    # Sort by overlap desc, predicate match desc, then sorted IDs asc
    candidates.sort(key=lambda x: (-x[0], -int(x[1]), x[2], x[3]))

    matched_preds: set[str] = set()
    matched_golds: set[str] = set()
    pred_to_gold: dict[str, str] = {}
    gold_to_pred: dict[str, str] = {}
    overlap_scores: dict[str, int] = {}

    for overlap, _, pid, gkey in candidates:
        if pid not in matched_preds and gkey not in matched_golds:
            matched_preds.add(pid)
            matched_golds.add(gkey)
            pred_to_gold[pid] = gkey
            gold_to_pred[gkey] = pid
            overlap_scores[f"{pid}<->{gkey}"] = overlap

    unmatched_preds = [p.state_id for p in predicted_states if p.state_id not in matched_preds]
    unmatched_golds = [g["state_key"] for g in gold_states if g["state_key"] not in matched_golds]

    return StateAlignment(
        pred_to_gold=pred_to_gold,
        gold_to_pred=gold_to_pred,
        unmatched_preds=unmatched_preds,
        unmatched_golds=unmatched_golds,
        overlap_scores=overlap_scores,
    )
