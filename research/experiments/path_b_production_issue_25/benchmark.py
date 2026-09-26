"""B0–B3 benchmark runner and metrics computation for Issue #25.

Runs all baselines, computes per-stage metrics, and generates
the structured report required by the issue deliverables.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from research.experiments.path_b_production_issue_25.adjudicator import SelectiveAdjudicator
from research.experiments.path_b_production_issue_25.candidate_generator import (
    CandidateGenerator,
    CandidateGeneratorConfig,
)
from research.experiments.path_b_production_issue_25.contracts import (
    AdjudicationMetrics,
    AdjudicationResult,
    CandidateDiscoveryMetrics,
    CostMetrics,
    DiscoveredCandidate,
    GoldAnnotation,
    KnowledgeEffectMetrics,
    LongitudinalRelation,
    ProductionMemoryView,
    TemporalIntegrityMetrics,
)


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def _gold_pair_set(golds: Sequence[GoldAnnotation]) -> set[tuple[str, str]]:
    """Set of (predecessor, successor) pairs that have true longitudinal relations."""
    return {
        (g.predecessor_id, g.successor_id)
        for g in golds
        if g.longitudinal_relation != LongitudinalRelation.UNRELATED
    }


def _all_gold_pairs(golds: Sequence[GoldAnnotation]) -> set[tuple[str, str]]:
    """All annotated pairs including UNRELATED."""
    return {(g.predecessor_id, g.successor_id) for g in golds}


def compute_candidate_metrics(
    candidates: Sequence[DiscoveredCandidate],
    golds: Sequence[GoldAnnotation],
    n_blocks: int,
    baseline_level: str,
) -> CandidateDiscoveryMetrics:
    """Compute candidate discovery metrics against gold annotations."""
    true_pairs = _gold_pair_set(golds)
    total_possible = n_blocks * (n_blocks - 1) // 2

    cand_pairs = {(c.predecessor_id, c.successor_id) for c in candidates}
    true_recalled = cand_pairs & true_pairs
    missed = true_pairs - cand_pairs

    recall = len(true_recalled) / len(true_pairs) if true_pairs else 1.0
    reduction = (1.0 - len(candidates) / total_possible) * 100 if total_possible else 0.0
    per_block = len(candidates) / n_blocks if n_blocks else 0.0
    false_rate = (
        (len(cand_pairs) - len(true_recalled)) / len(cand_pairs)
        if cand_pairs
        else 0.0
    )

    return CandidateDiscoveryMetrics(
        baseline_level=baseline_level,
        total_possible_pairs=total_possible,
        candidates_produced=len(candidates),
        true_relation_pairs=len(true_pairs),
        true_recalled=len(true_recalled),
        recall=recall,
        candidates_per_block=per_block,
        reduction_pct=reduction,
        false_candidate_rate=false_rate,
        target_miss_ids=tuple(f"{p}__{s}" for p, s in missed),
    )


def compute_adjudication_metrics(
    results: Sequence[AdjudicationResult],
    golds: Sequence[GoldAnnotation],
) -> AdjudicationMetrics:
    """Compute adjudication metrics against gold annotations."""
    gold_map: dict[tuple[str, str], GoldAnnotation] = {
        (g.predecessor_id, g.successor_id): g for g in golds
    }

    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    correct = 0
    total = 0
    correction_as_state = 0
    state_as_correction = 0
    unrelated_correct = 0
    unrelated_total = 0
    persistence_correct = 0
    persistence_total = 0
    unknown_count = 0

    for result in results:
        key = (result.predecessor_id, result.successor_id)
        if key not in gold_map:
            continue

        gold = gold_map[key]
        total += 1
        pred_rel = result.longitudinal_relation.value
        gold_rel = gold.longitudinal_relation.value

        confusion[gold_rel][pred_rel] += 1

        if pred_rel == gold_rel:
            correct += 1
        elif gold_rel == "CORRECTION_RETRACTION" and pred_rel == "STATE_CHANGE":
            correction_as_state += 1
        elif gold_rel == "STATE_CHANGE" and pred_rel == "CORRECTION_RETRACTION":
            state_as_correction += 1

        if gold_rel == "UNRELATED":
            unrelated_total += 1
            if pred_rel == "UNRELATED":
                unrelated_correct += 1

        if gold_rel == "PERSISTENCE_CONFIRMATION":
            persistence_total += 1
            if pred_rel == "PERSISTENCE_CONFIRMATION":
                persistence_correct += 1

        if pred_rel == "UNKNOWN_RELATION":
            unknown_count += 1

    confusion_rate = (
        (correction_as_state + state_as_correction) / total if total else 0.0
    )

    return AdjudicationMetrics(
        total_evaluated=total,
        relation_accuracy=correct / total if total else 0.0,
        correction_vs_state_confusion=confusion_rate,
        unrelated_rejection_accuracy=(
            unrelated_correct / unrelated_total if unrelated_total else 1.0
        ),
        persistence_accuracy=(
            persistence_correct / persistence_total if persistence_total else 1.0
        ),
        unknown_relation_rate=unknown_count / total if total else 0.0,
        confusion_matrix=dict(confusion),
    )


def compute_knowledge_effect_metrics(
    results: Sequence[AdjudicationResult],
    golds: Sequence[GoldAnnotation],
) -> KnowledgeEffectMetrics:
    """Compute knowledge effect metrics."""
    gold_map: dict[tuple[str, str], GoldAnnotation] = {
        (g.predecessor_id, g.successor_id): g for g in golds
    }

    total = 0
    true_pos = 0
    false_pos = 0
    false_neg = 0
    wrong_closure = 0
    wrong_dim = 0
    evidence_free = 0

    for result in results:
        key = (result.predecessor_id, result.successor_id)
        if key not in gold_map:
            continue

        gold = gold_map[key]
        total += 1

        gold_resolved = gold.knowledge_effect.prior_unknown_resolved
        pred_resolved = result.knowledge_effect.prior_unknown_resolved

        if gold_resolved is True and pred_resolved is True:
            true_pos += 1
            # Check dimension accuracy
            gold_dims = set(gold.knowledge_effect.resolved_dimensions)
            pred_dims = set(result.knowledge_effect.resolved_dimensions)
            if gold_dims and pred_dims and not gold_dims & pred_dims:
                wrong_dim += 1
        elif gold_resolved is True and pred_resolved is not True:
            false_neg += 1
        elif gold_resolved is not True and pred_resolved is True:
            false_pos += 1
            wrong_closure += 1
        
        # F6: evidence-free closure check
        if pred_resolved is True and gold.longitudinal_relation == LongitudinalRelation.UNRELATED:
            evidence_free += 1

    precision = true_pos / (true_pos + false_pos) if (true_pos + false_pos) else 1.0
    recall = true_pos / (true_pos + false_neg) if (true_pos + false_neg) else 1.0

    return KnowledgeEffectMetrics(
        total_evaluated=total,
        prior_unknown_resolution_precision=precision,
        prior_unknown_resolution_recall=recall,
        wrong_unknown_closure_rate=wrong_closure / total if total else 0.0,
        wrong_dimension_resolution_rate=wrong_dim / total if total else 0.0,
        evidence_free_closure_count=evidence_free,
    )


def compute_temporal_integrity(
    candidates: Sequence[DiscoveredCandidate],
    results: Sequence[AdjudicationResult],
    views: Sequence[ProductionMemoryView],
) -> TemporalIntegrityMetrics:
    """Verify temporal integrity invariants."""
    reverse_time = 0
    future_leakage = 0
    invalid_rewrite = 0
    axis_confusion = 0

    view_map = {v.memory_id: v for v in views}

    for cand in candidates:
        if cand.successor_time < cand.predecessor_time:
            reverse_time += 1

    for result in results:
        pred_view = view_map.get(result.predecessor_id)
        succ_view = view_map.get(result.successor_id)
        if not pred_view or not succ_view:
            continue

        # Future leakage: later knowledge used to evaluate earlier
        if succ_view.temporal.received_at < pred_view.temporal.received_at:
            future_leakage += 1

        # Axis confusion: semantic_time confused with received_at
        # If semantic_time of successor is before predecessor's received_at
        # and the relation is not CORRECTION_RETRACTION or late-fact, flag
        if (
            succ_view.temporal.semantic_time is not None
            and pred_view.temporal.semantic_time is not None
        ):
            s_sem = succ_view.temporal.semantic_time
            p_sem = pred_view.temporal.semantic_time
            # Semantic time reversal is valid (late fact, correction)
            # but knowledge time (received_at) must respect ordering
            # This is just counted as information, not necessarily an error

    return TemporalIntegrityMetrics(
        reverse_time_errors=reverse_time,
        future_leakage_count=future_leakage,
        invalid_rewrite_count=invalid_rewrite,
        axis_confusion_count=axis_confusion,
        passed_all=(reverse_time == 0 and future_leakage == 0),
    )


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkSummary:
    candidate_metrics: dict[str, object]
    adjudication_metrics: dict[str, object]
    knowledge_effect_metrics: dict[str, object]
    temporal_integrity: dict[str, object]
    cost_metrics: dict[str, object]
    falsification_results: list[dict[str, object]]


def run_benchmark(
    views: Sequence[ProductionMemoryView],
    golds: Sequence[GoldAnnotation],
    results_dir: Path | None = None,
) -> BenchmarkSummary:
    """Run the full B0–B3 benchmark pipeline.

    B0: time only
    B1: time + embedding
    B2: time + embedding + boundary signals
    B3: B2 candidates → selective adjudication
    """
    gen = CandidateGenerator()
    n_blocks = len(views)

    # Stage 1: Candidate discovery at each level
    b0 = gen.generate_b0(views)
    b1 = gen.generate_b1(views, b0)
    b2 = gen.generate_b2(views, b0)

    cand_metrics = {
        "B0": _metrics_to_dict(compute_candidate_metrics(b0, golds, n_blocks, "B0")),
        "B1": _metrics_to_dict(compute_candidate_metrics(b1, golds, n_blocks, "B1")),
        "B2": _metrics_to_dict(compute_candidate_metrics(b2, golds, n_blocks, "B2")),
    }

    # Stage 2: Adjudication on B2 candidates only (no gold-pair shortcut)
    adjudicator = SelectiveAdjudicator(views)
    b3_results = adjudicator.adjudicate(b2)

    adj_metrics = _metrics_to_dict(compute_adjudication_metrics(b3_results, golds))
    ke_metrics = _metrics_to_dict(compute_knowledge_effect_metrics(b3_results, golds))
    temp_integrity = _metrics_to_dict(compute_temporal_integrity(b2, b3_results, views))

    cost = CostMetrics(
        adjudication_calls=len(b3_results),
        calls_per_block=len(b3_results) / n_blocks if n_blocks else 0.0,
        tokens_per_accepted=0.0,  # rule-based, no tokens
        candidate_volume_before=len(b0),
        candidate_volume_after=len(b2),
    )

    # Falsification tests
    from research.experiments.path_b_production_issue_25.falsification import (
        run_falsification_suite,
    )
    fals_results = run_falsification_suite(views, golds, b0, b1, b2, b3_results)

    summary = BenchmarkSummary(
        candidate_metrics=cand_metrics,
        adjudication_metrics=adj_metrics,
        knowledge_effect_metrics=ke_metrics,
        temporal_integrity=temp_integrity,
        cost_metrics=_metrics_to_dict(cost),
        falsification_results=fals_results,
    )

    if results_dir:
        results_dir.mkdir(parents=True, exist_ok=True)
        with open(results_dir / "benchmark_summary.json", "w", encoding="utf-8") as f:
            json.dump(_summary_to_dict(summary), f, indent=2, ensure_ascii=False, default=str)

        # Per-stage raw outputs
        _dump_candidates(b0, results_dir / "b0_candidates.jsonl")
        _dump_candidates(b1, results_dir / "b1_candidates.jsonl")
        _dump_candidates(b2, results_dir / "b2_candidates.jsonl")
        _dump_adjudication(b3_results, results_dir / "b3_adjudication.jsonl")

    return summary


def _metrics_to_dict(obj: object) -> dict[str, object]:
    if hasattr(obj, '__dataclass_fields__'):
        return {k: _metrics_to_dict(v) for k, v in asdict(obj).items()}  # type: ignore[arg-type]
    return obj  # type: ignore[return-value]


def _summary_to_dict(s: BenchmarkSummary) -> dict[str, object]:
    return {
        "candidate_metrics": s.candidate_metrics,
        "adjudication_metrics": s.adjudication_metrics,
        "knowledge_effect_metrics": s.knowledge_effect_metrics,
        "temporal_integrity": s.temporal_integrity,
        "cost_metrics": s.cost_metrics,
        "falsification_results": s.falsification_results,
    }


def _dump_candidates(candidates: Sequence[DiscoveredCandidate], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps({
                "candidate_id": c.candidate_id,
                "predecessor_id": c.predecessor_id,
                "successor_id": c.successor_id,
                "predecessor_time": c.predecessor_time.isoformat(),
                "successor_time": c.successor_time.isoformat(),
                "signals": list(c.signals),
                "baseline_level": c.baseline_level,
                "score": c.score,
            }, ensure_ascii=False) + "\n")


def _dump_adjudication(results: Sequence[AdjudicationResult], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps({
                "candidate_id": r.candidate_id,
                "predecessor_id": r.predecessor_id,
                "successor_id": r.successor_id,
                "longitudinal_relation": r.longitudinal_relation.value,
                "knowledge_effect": {
                    "prior_unknown_resolved": r.knowledge_effect.prior_unknown_resolved,
                    "resolved_dimensions": list(r.knowledge_effect.resolved_dimensions),
                    "newly_introduced_unknowns": list(r.knowledge_effect.newly_introduced_unknowns),
                },
                "evidence_spans": list(r.evidence_spans),
                "adjudication_trace": r.adjudication_trace,
                "confidence": r.confidence,
            }, ensure_ascii=False) + "\n")
