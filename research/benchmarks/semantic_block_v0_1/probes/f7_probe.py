"""Probe F7: Cross-sentence causality and path recovery (B03 sentinel).

Evaluates whether directed CAUSE edges are grounded and whether the full s1->s2->s3
path is recovered without direct shortcut invention (s1->s3) or BEFORE substitution.
On negative variant B03-N, verifies zero CAUSE edges and empty causal path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from research.benchmarks.semantic_block_v0_1.consumer.raw_hidden import RawHiddenConsumer
from research.benchmarks.semantic_block_v0_1.contracts import PredictionRecord
from research.benchmarks.semantic_block_v0_1.scorer.alignment import align_states


@dataclass
class F7ProbeResult:
    case_id: str
    arm_id: str
    variant: str
    pass_gate: bool
    s1_s2_cause_present: bool
    s2_s3_cause_present: bool
    full_path_recovered: bool
    direct_shortcut_emitted: bool
    before_substituted: bool
    negative_cause_emitted: bool
    errors: list[str]


def evaluate_f7_probe(
    prediction: PredictionRecord,
    gold_case: dict[str, Any],
    consumer: RawHiddenConsumer,
) -> F7ProbeResult:
    case_id = prediction.case_id
    arm_id = prediction.arm_id
    variant = case_id.split("-")[1]  # C, P, or N

    cutoff = prediction.cutoff
    gold_vis = next(v for v in gold_case["visibility"] if v["cutoff"] == cutoff)
    gold_states = [s for s in gold_case["states"] if s["state_key"] in gold_vis["visible_state_keys"]]
    pred_blocks = [b for b in prediction.blocks if b.state_available_at <= cutoff]

    alignment = align_states(pred_blocks, gold_states)
    s1_id = alignment.gold_to_pred.get("s1")
    s2_id = alignment.gold_to_pred.get("s2")
    s3_id = alignment.gold_to_pred.get("s3")

    errors: list[str] = []
    s1_s2_cause = False
    s2_s3_cause = False
    full_path_recovered = False
    direct_shortcut = False
    before_substituted = False
    negative_cause_emitted = False

    if variant in ("C", "P"):
        if not (s1_id and s2_id and s3_id):
            errors.append(f"Missing aligned blocks for s1/s2/s3 (found: s1={s1_id}, s2={s2_id}, s3={s3_id})")

        # Check CAUSE edges
        for r in prediction.relations:
            if r.type == "CAUSE":
                if r.source_state_id == s1_id and r.target_state_id == s2_id:
                    s1_s2_cause = True
                elif r.source_state_id == s2_id and r.target_state_id == s3_id:
                    s2_s3_cause = True
                elif r.source_state_id == s1_id and r.target_state_id == s3_id:
                    direct_shortcut = True
                    errors.append("Forbidden direct shortcut s1->s3 emitted.")
            elif r.type == "BEFORE":
                if (r.source_state_id == s1_id and r.target_state_id == s2_id) or \
                   (r.source_state_id == s2_id and r.target_state_id == s3_id):
                    before_substituted = True
                    errors.append("BEFORE substituted for CAUSE.")

        # Test consumer path retrieval
        if s1_id and s3_id:
            path = consumer.reachable_cause_path(s1_id, s3_id)
            if path == [s1_id, s2_id, s3_id]:
                full_path_recovered = True
            else:
                errors.append(f"Path s1->s2->s3 not recovered; consumer returned {path}")

        pass_gate = (s1_s2_cause and s2_s3_cause and full_path_recovered and not direct_shortcut and not before_substituted)

    else:  # Negative variant 'N'
        # Must have NO CAUSE edges
        cause_rels = [r for r in prediction.relations if r.type == "CAUSE"]
        if cause_rels:
            negative_cause_emitted = True
            errors.append(f"Negative control B03-N emitted {len(cause_rels)} CAUSE relations.")

        if s1_id and s3_id:
            path = consumer.reachable_cause_path(s1_id, s3_id)
            if path:
                negative_cause_emitted = True
                errors.append(f"Negative control B03-N found non-empty cause path: {path}")

        pass_gate = not negative_cause_emitted

    return F7ProbeResult(
        case_id=case_id,
        arm_id=arm_id,
        variant=variant,
        pass_gate=pass_gate,
        s1_s2_cause_present=s1_s2_cause,
        s2_s3_cause_present=s2_s3_cause,
        full_path_recovered=full_path_recovered,
        direct_shortcut_emitted=direct_shortcut,
        before_substituted=before_substituted,
        negative_cause_emitted=negative_cause_emitted,
        errors=errors,
    )
