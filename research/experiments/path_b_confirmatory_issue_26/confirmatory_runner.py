"""Issue #26 confirmatory runner.

Imports the FROZEN Issue #25 candidate generator, adjudicator, and
benchmark infrastructure. Runs exactly ONE frozen evaluation.
Records all failures without repair.

Answers four primary questions:
  Q1 — What is the current ~9% miss?
  Q2 — Does B2 add real recall over B1?
  Q3 — Does adjudication remain safe on unseen candidates?
  Q4 — Does the two-axis output still matter?
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# Frozen Issue #25 imports — DO NOT MODIFY
from research.experiments.path_b_production_issue_25.adjudicator import SelectiveAdjudicator
from research.experiments.path_b_production_issue_25.benchmark import (
    compute_adjudication_metrics,
    compute_candidate_metrics,
    compute_knowledge_effect_metrics,
    compute_temporal_integrity,
)
from research.experiments.path_b_production_issue_25.candidate_generator import (
    CandidateGenerator,
)
from research.experiments.path_b_production_issue_25.contracts import (
    AdjudicationResult,
    DiscoveredCandidate,
    GoldAnnotation,
    LongitudinalRelation,
    ProductionMemoryView,
)

# Heldout corpus (new, never seen during #25)
from research.experiments.path_b_confirmatory_issue_26.heldout_corpus import (
    build_heldout_corpus,
    build_heldout_gold,
)


# ===================================================================
# Q1: Miss analysis
# ===================================================================

MISS_CATEGORIES = (
    "lexical_discontinuity",
    "temporal_distance",
    "missing_semantic_anchor",
    "candidate_budget_cutoff",
    "vector_miss",
    "boundary_signal_miss",
    "ambiguous_gold",
    "other",
)


def _classify_miss(
    pred_view: ProductionMemoryView,
    succ_view: ProductionMemoryView,
    gold: GoldAnnotation,
    gen: CandidateGenerator,
) -> dict[str, object]:
    """Classify why a true relation was missed by B1 and/or B2."""
    import re
    from research.experiments.path_b_production_issue_25.candidate_generator import (
        _cosine_similarity,
        _simple_token_overlap_vector,
        _extract_boundary_signals,
    )

    emb_p = _simple_token_overlap_vector(pred_view.content)
    emb_s = _simple_token_overlap_vector(succ_view.content)
    cosine = _cosine_similarity(emb_p, emb_s)

    delta = succ_view.temporal.received_at - pred_view.temporal.received_at
    delta_days = delta.total_seconds() / 86400

    boundary_signals, boundary_score = _extract_boundary_signals(pred_view, succ_view)

    # Classify
    reasons: list[str] = []

    if delta_days > gen.config.temporal_window_days:
        reasons.append("temporal_distance")

    if cosine < gen.config.b1_cosine_threshold:
        reasons.append("vector_miss")
        # Sub-classify: is it lexical discontinuity?
        p_chars = set(re.findall(r'[\u4e00-\u9fff]{2,}', pred_view.content))
        s_chars = set(re.findall(r'[\u4e00-\u9fff]{2,}', succ_view.content))
        p_bg = set()
        s_bg = set()
        for c in p_chars:
            for i in range(len(c) - 1):
                p_bg.add(c[i:i+2])
        for c in s_chars:
            for i in range(len(c) - 1):
                s_bg.add(c[i:i+2])
        if len(p_bg & s_bg) < 2:
            reasons.append("lexical_discontinuity")

    if not boundary_signals:
        reasons.append("boundary_signal_miss")
    elif boundary_score < gen.config.b2_min_score:
        reasons.append("missing_semantic_anchor")

    if not reasons:
        reasons.append("other")

    return {
        "pair_id": gold.pair_id,
        "predecessor_id": gold.predecessor_id,
        "successor_id": gold.successor_id,
        "semantic_family": gold.semantic_family,
        "cosine_sim": round(cosine, 4),
        "temporal_delta_days": round(delta_days, 1),
        "boundary_signals": boundary_signals,
        "boundary_score": round(boundary_score, 3),
        "miss_categories": reasons,
    }


# ===================================================================
# Q2: B1 vs B2 marginal value
# ===================================================================

@dataclass
class MarginalValueTable:
    b1_recall: float
    b2_recall: float
    b1_volume: int
    b2_volume: int
    b1_only_targets: list[str]  # recalled by B1 but not B2
    b2_only_targets: list[str]  # recalled by B2 but not B1
    both_recall: list[str]      # recalled by both
    neither_recall: list[str]   # missed by both
    b2_marginal_false: int      # extra false candidates in B2 vs B1


def compute_marginal_value(
    b1_candidates: Sequence[DiscoveredCandidate],
    b2_candidates: Sequence[DiscoveredCandidate],
    golds: Sequence[GoldAnnotation],
) -> MarginalValueTable:
    """Compute per-target marginal value of B2 vs B1."""
    true_pairs = {
        (g.predecessor_id, g.successor_id): g.pair_id
        for g in golds
        if g.longitudinal_relation != LongitudinalRelation.UNRELATED
    }
    b1_set = {(c.predecessor_id, c.successor_id) for c in b1_candidates}
    b2_set = {(c.predecessor_id, c.successor_id) for c in b2_candidates}

    b1_hit = {k: v for k, v in true_pairs.items() if k in b1_set}
    b2_hit = {k: v for k, v in true_pairs.items() if k in b2_set}

    both = set(b1_hit.values()) & set(b2_hit.values())
    b1_only = set(b1_hit.values()) - set(b2_hit.values())
    b2_only = set(b2_hit.values()) - set(b1_hit.values())
    neither = set(true_pairs.values()) - set(b1_hit.values()) - set(b2_hit.values())

    b1_false = len(b1_set) - len(b1_hit)
    b2_false = len(b2_set) - len(b2_hit)

    return MarginalValueTable(
        b1_recall=len(b1_hit) / len(true_pairs) if true_pairs else 1.0,
        b2_recall=len(b2_hit) / len(true_pairs) if true_pairs else 1.0,
        b1_volume=len(b1_candidates),
        b2_volume=len(b2_candidates),
        b1_only_targets=sorted(b1_only),
        b2_only_targets=sorted(b2_only),
        both_recall=sorted(both),
        neither_recall=sorted(neither),
        b2_marginal_false=b2_false - b1_false,
    )


# ===================================================================
# Full confirmatory run
# ===================================================================

@dataclass
class ConfirmatoryResult:
    frozen_sha: str
    corpus_size: int
    gold_count: int
    candidate_metrics: dict[str, object]
    adjudication_metrics: dict[str, object]
    knowledge_effect_metrics: dict[str, object]
    temporal_integrity: dict[str, object]
    miss_analysis: list[dict[str, object]]
    marginal_value: dict[str, object]
    q4_dual_axis_cases: list[str]
    verdict: str


def run_confirmatory(
    results_dir: Path | None = None,
) -> ConfirmatoryResult:
    """One frozen confirmatory run. No repair permitted."""
    frozen_sha = "85974a2"

    views = build_heldout_corpus()
    golds = build_heldout_gold()
    n_blocks = len(views)
    view_map = {v.memory_id: v for v in views}

    # Run frozen generator
    gen = CandidateGenerator()
    b0 = gen.generate_b0(views)
    b1 = gen.generate_b1(views, b0)
    b2 = gen.generate_b2(views, b0)

    # Candidate metrics
    from research.experiments.path_b_production_issue_25.benchmark import (
        _metrics_to_dict,
    )
    cand_metrics = {
        "B0": _metrics_to_dict(compute_candidate_metrics(b0, golds, n_blocks, "B0")),
        "B1": _metrics_to_dict(compute_candidate_metrics(b1, golds, n_blocks, "B1")),
        "B2": _metrics_to_dict(compute_candidate_metrics(b2, golds, n_blocks, "B2")),
    }

    # Adjudication on B2 only
    adj = SelectiveAdjudicator(views)
    b3_results = adj.adjudicate(b2)

    adj_metrics = _metrics_to_dict(compute_adjudication_metrics(b3_results, golds))
    ke_metrics = _metrics_to_dict(compute_knowledge_effect_metrics(b3_results, golds))
    temp_int = _metrics_to_dict(compute_temporal_integrity(b2, b3_results, views))

    # Q1: Miss analysis
    true_pairs = {
        (g.predecessor_id, g.successor_id): g
        for g in golds
        if g.longitudinal_relation != LongitudinalRelation.UNRELATED
    }
    b2_set = {(c.predecessor_id, c.successor_id) for c in b2}
    missed = {k: v for k, v in true_pairs.items() if k not in b2_set}
    miss_analysis = [
        _classify_miss(view_map[k[0]], view_map[k[1]], v, gen)
        for k, v in missed.items()
    ]

    # Also classify B1-specific misses
    b1_set = {(c.predecessor_id, c.successor_id) for c in b1}
    b1_missed = {k: v for k, v in true_pairs.items() if k not in b1_set}
    for k, v in b1_missed.items():
        if k not in missed:
            entry = _classify_miss(view_map[k[0]], view_map[k[1]], v, gen)
            entry["b1_only_miss"] = True
            miss_analysis.append(entry)

    # Q2: Marginal value
    mv = compute_marginal_value(b1, b2, golds)

    # Q4: Dual axis cases
    dual_results = [
        r.candidate_id for r in b3_results
        if r.longitudinal_relation == LongitudinalRelation.STATE_CHANGE
        and r.knowledge_effect.prior_unknown_resolved is True
    ]

    # Verdict
    b2_recall = cand_metrics["B2"]["recall"]
    adj_acc = adj_metrics["relation_accuracy"]
    temp_pass = temp_int["passed_all"]
    corr_conf = adj_metrics["correction_vs_state_confusion"]

    if (
        b2_recall >= 0.70
        and adj_acc >= 0.50
        and temp_pass
        and corr_conf <= 0.1
    ):
        verdict = "SUPPORTED"
    elif b2_recall < 0.50 or adj_acc < 0.30 or not temp_pass:
        verdict = "NOT_SUPPORTED"
    else:
        verdict = "INCONCLUSIVE"

    result = ConfirmatoryResult(
        frozen_sha=frozen_sha,
        corpus_size=n_blocks,
        gold_count=len(golds),
        candidate_metrics=cand_metrics,
        adjudication_metrics=adj_metrics,
        knowledge_effect_metrics=ke_metrics,
        temporal_integrity=temp_int,
        miss_analysis=miss_analysis,
        marginal_value={
            "b1_recall": mv.b1_recall,
            "b2_recall": mv.b2_recall,
            "b1_volume": mv.b1_volume,
            "b2_volume": mv.b2_volume,
            "b1_only_targets": mv.b1_only_targets,
            "b2_only_targets": mv.b2_only_targets,
            "both_recall": mv.both_recall,
            "neither_recall": mv.neither_recall,
            "b2_marginal_false": mv.b2_marginal_false,
        },
        q4_dual_axis_cases=dual_results,
        verdict=verdict,
    )

    if results_dir:
        results_dir.mkdir(parents=True, exist_ok=True)
        _dump_json(result, results_dir / "confirmatory_summary.json")
        _dump_candidates(b0, results_dir / "b0_candidates.jsonl")
        _dump_candidates(b1, results_dir / "b1_candidates.jsonl")
        _dump_candidates(b2, results_dir / "b2_candidates.jsonl")
        _dump_adjudication(b3_results, results_dir / "b3_adjudication.jsonl")

    return result


def _dump_json(result: ConfirmatoryResult, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "frozen_sha": result.frozen_sha,
            "corpus_size": result.corpus_size,
            "gold_count": result.gold_count,
            "candidate_metrics": result.candidate_metrics,
            "adjudication_metrics": result.adjudication_metrics,
            "knowledge_effect_metrics": result.knowledge_effect_metrics,
            "temporal_integrity": result.temporal_integrity,
            "miss_analysis": result.miss_analysis,
            "marginal_value": result.marginal_value,
            "q4_dual_axis_cases": result.q4_dual_axis_cases,
            "verdict": result.verdict,
        }, f, indent=2, ensure_ascii=False, default=str)


def _dump_candidates(candidates: Sequence[DiscoveredCandidate], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps({
                "candidate_id": c.candidate_id,
                "predecessor_id": c.predecessor_id,
                "successor_id": c.successor_id,
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
                },
                "confidence": r.confidence,
                "adjudication_trace": r.adjudication_trace,
            }, ensure_ascii=False) + "\n")
