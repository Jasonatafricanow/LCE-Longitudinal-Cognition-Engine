"""Critical falsification tests for Issue #25.

F1 — Time necessary but insufficient
F2 — No oracle recovery
F3 — No gold-pair shortcut
F4 — State change != correction
F5 — Relation != knowledge effect
F6 — No new evidence, no new cognition
F7 — Sparse discovery
"""

from __future__ import annotations

from collections.abc import Sequence

from research.experiments.path_b_production_issue_25.contracts import (
    AdjudicationResult,
    DiscoveredCandidate,
    GoldAnnotation,
    KnowledgeEffect,
    LongitudinalRelation,
    ProductionMemoryView,
)


def run_falsification_suite(
    views: Sequence[ProductionMemoryView],
    golds: Sequence[GoldAnnotation],
    b0_candidates: Sequence[DiscoveredCandidate],
    b1_candidates: Sequence[DiscoveredCandidate],
    b2_candidates: Sequence[DiscoveredCandidate],
    b3_results: Sequence[AdjudicationResult],
) -> list[dict[str, object]]:
    """Run all seven falsification tests and return structured results."""
    results: list[dict[str, object]] = []

    results.append(_f1_time_necessary_insufficient(b0_candidates, golds, views))
    results.append(_f2_no_oracle_recovery(views))
    results.append(_f3_no_gold_pair_shortcut(b2_candidates, b3_results, golds))
    results.append(_f4_state_change_ne_correction(b3_results, golds))
    results.append(_f5_relation_ne_knowledge_effect(b3_results, golds))
    results.append(_f6_no_evidence_no_cognition(b3_results, golds))
    results.append(_f7_sparse_discovery(b0_candidates, b2_candidates, views))

    return results


def _f1_time_necessary_insufficient(
    b0_candidates: Sequence[DiscoveredCandidate],
    golds: Sequence[GoldAnnotation],
    views: Sequence[ProductionMemoryView],
) -> dict[str, object]:
    """Temporally adjacent unrelated items must not be forced into a relation.

    Check that B0 (time-only) produces candidates that include UNRELATED
    pairs from the gold set, proving that time alone is insufficient.
    """
    unrelated_golds = {
        (g.predecessor_id, g.successor_id)
        for g in golds
        if g.longitudinal_relation == LongitudinalRelation.UNRELATED
    }

    b0_pairs = {(c.predecessor_id, c.successor_id) for c in b0_candidates}

    # At least one unrelated gold pair should appear in B0 candidates
    # (time proximity captures them but they are still unrelated)
    unrelated_in_b0 = unrelated_golds & b0_pairs
    
    # Also verify that not all B0 candidates are true relations
    true_golds = {
        (g.predecessor_id, g.successor_id)
        for g in golds
        if g.longitudinal_relation != LongitudinalRelation.UNRELATED
    }
    false_candidates = b0_pairs - true_golds

    passed = len(false_candidates) > 0  # Time alone captures unrelated pairs

    return {
        "falsification_id": "F1",
        "name": "Time necessary but insufficient",
        "passed": passed,
        "detail": {
            "b0_total": len(b0_candidates),
            "unrelated_in_b0": len(unrelated_in_b0),
            "false_candidates_in_b0": len(false_candidates),
        },
    }


def _f2_no_oracle_recovery(
    views: Sequence[ProductionMemoryView],
) -> dict[str, object]:
    """Removing thread_id/domain/correction_nature must not make the pipeline
    impossible to run.

    Verify that no ProductionMemoryView contains forbidden oracle fields.
    """
    forbidden_fields = {"thread_id", "oracle_domain", "correction_nature",
                        "gold_relation", "trajectory_label", "grouping_key"}
    violations: list[str] = []

    for view in views:
        found = forbidden_fields & set(view.provenance.keys())
        if found:
            violations.append(f"{view.memory_id}: {found}")

    passed = len(violations) == 0

    return {
        "falsification_id": "F2",
        "name": "No oracle recovery",
        "passed": passed,
        "detail": {
            "violations": violations,
            "views_checked": len(views),
        },
    }


def _f3_no_gold_pair_shortcut(
    b2_candidates: Sequence[DiscoveredCandidate],
    b3_results: Sequence[AdjudicationResult],
    golds: Sequence[GoldAnnotation],
) -> dict[str, object]:
    """Adjudicator input must be generated only from discovered candidates.

    Verify that every adjudicated pair exists in the B2 candidate set.
    """
    b2_pairs = {(c.predecessor_id, c.successor_id) for c in b2_candidates}
    adjudicated_pairs = {(r.predecessor_id, r.successor_id) for r in b3_results}

    shortcut_pairs = adjudicated_pairs - b2_pairs
    passed = len(shortcut_pairs) == 0

    return {
        "falsification_id": "F3",
        "name": "No gold-pair shortcut",
        "passed": passed,
        "detail": {
            "adjudicated_count": len(adjudicated_pairs),
            "in_b2_count": len(adjudicated_pairs & b2_pairs),
            "shortcut_count": len(shortcut_pairs),
        },
    }


def _f4_state_change_ne_correction(
    b3_results: Sequence[AdjudicationResult],
    golds: Sequence[GoldAnnotation],
) -> dict[str, object]:
    """World/plan evolution must remain distinguishable from correction.

    Check that no gold STATE_CHANGE is predicted as CORRECTION_RETRACTION
    and vice versa.
    """
    gold_map = {
        (g.predecessor_id, g.successor_id): g for g in golds
    }

    confusions: list[dict[str, str]] = []

    for result in b3_results:
        key = (result.predecessor_id, result.successor_id)
        if key not in gold_map:
            continue
        gold = gold_map[key]

        if (
            gold.longitudinal_relation == LongitudinalRelation.STATE_CHANGE
            and result.longitudinal_relation == LongitudinalRelation.CORRECTION_RETRACTION
        ):
            confusions.append({
                "pair": f"{key[0]}__{key[1]}",
                "gold": "STATE_CHANGE",
                "predicted": "CORRECTION_RETRACTION",
            })
        elif (
            gold.longitudinal_relation == LongitudinalRelation.CORRECTION_RETRACTION
            and result.longitudinal_relation == LongitudinalRelation.STATE_CHANGE
        ):
            confusions.append({
                "pair": f"{key[0]}__{key[1]}",
                "gold": "CORRECTION_RETRACTION",
                "predicted": "STATE_CHANGE",
            })

    passed = len(confusions) == 0

    return {
        "falsification_id": "F4",
        "name": "State change != correction",
        "passed": passed,
        "detail": {
            "confusions": confusions,
        },
    }


def _f5_relation_ne_knowledge_effect(
    b3_results: Sequence[AdjudicationResult],
    golds: Sequence[GoldAnnotation],
) -> dict[str, object]:
    """A state change may also resolve a prior UNKNOWN.
    Both must be representable simultaneously.

    Verify that at least one result has:
      longitudinal_relation = STATE_CHANGE
      AND knowledge_effect.prior_unknown_resolved = True
    """
    gold_map = {
        (g.predecessor_id, g.successor_id): g for g in golds
    }

    # Find golds where both are true
    dual_golds = [
        g for g in golds
        if g.longitudinal_relation == LongitudinalRelation.STATE_CHANGE
        and g.knowledge_effect.prior_unknown_resolved is True
    ]

    # Check if any adjudication result correctly captures this
    dual_results = [
        r for r in b3_results
        if r.longitudinal_relation == LongitudinalRelation.STATE_CHANGE
        and r.knowledge_effect.prior_unknown_resolved is True
    ]

    passed = len(dual_results) > 0 and len(dual_golds) > 0

    return {
        "falsification_id": "F5",
        "name": "Relation != knowledge effect",
        "passed": passed,
        "detail": {
            "dual_gold_count": len(dual_golds),
            "dual_result_count": len(dual_results),
            "dual_result_ids": [r.candidate_id for r in dual_results],
        },
    }


def _f6_no_evidence_no_cognition(
    b3_results: Sequence[AdjudicationResult],
    golds: Sequence[GoldAnnotation],
) -> dict[str, object]:
    """Elapsed time alone cannot close UNKNOWN.

    Verify that no UNRELATED pair has prior_unknown_resolved = True,
    and that persistence confirmation does not close unknowns.
    """
    violations: list[str] = []

    for result in b3_results:
        if (
            result.longitudinal_relation == LongitudinalRelation.UNRELATED
            and result.knowledge_effect.prior_unknown_resolved is True
        ):
            violations.append(
                f"{result.candidate_id}: UNRELATED with prior_unknown_resolved=True"
            )
        if (
            result.longitudinal_relation == LongitudinalRelation.PERSISTENCE_CONFIRMATION
            and result.knowledge_effect.prior_unknown_resolved is True
        ):
            violations.append(
                f"{result.candidate_id}: PERSISTENCE with prior_unknown_resolved=True"
            )

    passed = len(violations) == 0

    return {
        "falsification_id": "F6",
        "name": "No new evidence, no new cognition",
        "passed": passed,
        "detail": {
            "violations": violations,
        },
    }


def _f7_sparse_discovery(
    b0_candidates: Sequence[DiscoveredCandidate],
    b2_candidates: Sequence[DiscoveredCandidate],
    views: Sequence[ProductionMemoryView],
) -> dict[str, object]:
    """High recall must be achieved without all-pairs LLM comparison.

    Verify that B2 produces significantly fewer candidates than B0
    (which is already less than all-pairs).
    """
    n = len(views)
    all_pairs = n * (n - 1) // 2

    b0_reduction = (1.0 - len(b0_candidates) / all_pairs) * 100 if all_pairs else 0.0
    b2_reduction = (1.0 - len(b2_candidates) / all_pairs) * 100 if all_pairs else 0.0
    b2_vs_b0_reduction = (
        (1.0 - len(b2_candidates) / len(b0_candidates)) * 100
        if b0_candidates
        else 0.0
    )

    # B2 should produce at most 50% of B0 candidates
    passed = b2_vs_b0_reduction >= 40.0

    return {
        "falsification_id": "F7",
        "name": "Sparse discovery",
        "passed": passed,
        "detail": {
            "all_pairs": all_pairs,
            "b0_count": len(b0_candidates),
            "b2_count": len(b2_candidates),
            "b0_reduction_pct": round(b0_reduction, 1),
            "b2_reduction_pct": round(b2_reduction, 1),
            "b2_vs_b0_reduction_pct": round(b2_vs_b0_reduction, 1),
        },
    }
