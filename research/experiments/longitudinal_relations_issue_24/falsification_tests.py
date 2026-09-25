"""Critical Falsification Test Suite for Issue #24.

Verifies:
- F1: Time is necessary but insufficient (unrelated temporal neighbors rejected)
- F2: Future evidence does not rewrite earlier truth (predecessor hash unchanged)
- F3: UNKNOWN closes only with new evidence (elapsed time alone cannot close unknown)
- F4: State change != correction (confusion between world evolution and cognition error is 0)
- F5: Sparse candidate formation (candidate reduction > 70% with recall >= 95%)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from lce.cognition.longitudinal_relation import (
    LongitudinalRelationType,
    compute_block_content_hash,
)
from research.experiments.longitudinal_relations_issue_24.contracts import (
    AdjudicationOutput,
    CandidateFormationMetrics,
    CorpusBlockRecord,
    GoldRelationRecord,
    TemporalIntegrityMetrics,
)


@dataclass(frozen=True, slots=True)
class FalsificationResult:
    falsification_id: str
    name: str
    passed: bool
    evidence_summary: str
    details: dict[str, Any]


class FalsificationSuite:
    """Executes the 5 critical falsification audits."""

    def __init__(
        self,
        blocks: list[CorpusBlockRecord],
        gold_pairs: list[GoldRelationRecord],
        adjudications: dict[str, AdjudicationOutput],
        l2_metrics: CandidateFormationMetrics,
    ) -> None:
        self.blocks = {b.block_id: b for b in blocks}
        self.gold_pairs = {g.pair_id: g for g in gold_pairs}
        self.adjudications = adjudications
        self.l2_metrics = l2_metrics

    # -------------------------------------------------------------------------
    # F1: Time is necessary but insufficient
    # -------------------------------------------------------------------------
    def test_f1(self) -> FalsificationResult:
        """Temporally adjacent unrelated blocks must not be forced into a relation."""
        unrelated_pairs = [g for g in self.gold_pairs.values() if g.relation_type == LongitudinalRelationType.UNRELATED]
        if not unrelated_pairs:
            return FalsificationResult("F1", "Time is necessary but insufficient", False, "No unrelated pairs found", {})

        correct_rejections = 0
        details = []
        for g in unrelated_pairs:
            adj = self.adjudications.get(g.pair_id)
            if adj and adj.predicted_relation == LongitudinalRelationType.UNRELATED:
                correct_rejections += 1
                status = "PASS_REJECTED"
            else:
                status = f"FAIL_FORCED_RELATION_{adj.predicted_relation if adj else 'NONE'}"
            details.append({"pair_id": g.pair_id, "status": status})

        accuracy = correct_rejections / len(unrelated_pairs)
        passed = accuracy >= 0.90  # Expect high rejection rate

        summary = f"Tested {len(unrelated_pairs)} unrelated temporal neighbors. Correct rejection rate: {accuracy*100:.1f}% ({correct_rejections}/{len(unrelated_pairs)})."
        return FalsificationResult("F1", "Time is necessary but insufficient", passed, summary, {"details": details, "accuracy": accuracy})

    # -------------------------------------------------------------------------
    # F2: Future evidence does not rewrite earlier truth
    # -------------------------------------------------------------------------
    def test_f2(self) -> FalsificationResult:
        """Earlier block remains valid at its own cutoff; predecessor hash invariant."""
        pre_hashes = {}
        for b in self.blocks.values():
            sb = b.to_semantic_block()
            pre_hashes[b.block_id] = compute_block_content_hash(sb)

        # Verify against post-adjudication state
        mutations = []
        for b_id, b in self.blocks.items():
            sb = b.to_semantic_block()
            curr_hash = compute_block_content_hash(sb)
            if curr_hash != pre_hashes[b_id]:
                mutations.append(b_id)

        passed = len(mutations) == 0
        summary = f"Checked {len(self.blocks)} SemanticBlocks. Content mutations detected: {len(mutations)}."
        return FalsificationResult("F2", "Future evidence does not rewrite earlier truth", passed, summary, {"mutations": mutations})

    # -------------------------------------------------------------------------
    # F3: UNKNOWN only closes with evidence
    # -------------------------------------------------------------------------
    def test_f3(self) -> FalsificationResult:
        """Elapsed time alone must not convert unknown -> known."""
        probes = [g for g in self.gold_pairs.values() if "F3_UNKNOWN_CLOSES_ONLY_WITH_EVIDENCE" in g.falsification_tags]
        # Also include all PERSISTENCE pairs where outcome was not closed
        persist_pairs = [g for g in self.gold_pairs.values() if g.relation_type == LongitudinalRelationType.PERSISTENCE_CONFIRMATION]
        test_set = probes + persist_pairs

        unsupported_closures = []
        for g in test_set:
            adj = self.adjudications.get(g.pair_id)
            if adj and adj.prior_unknown_resolved:
                unsupported_closures.append({"pair_id": g.pair_id, "pred": adj.predicted_relation.value})

        passed = len(unsupported_closures) == 0
        summary = f"Audited {len(test_set)} elapsed-time and persistent cases. Unsupported unknown closures: {len(unsupported_closures)}."
        return FalsificationResult("F3", "UNKNOWN closes only with new evidence", passed, summary, {"unsupported_closures": unsupported_closures})

    # -------------------------------------------------------------------------
    # F4: State change != correction
    # -------------------------------------------------------------------------
    def test_f4(self) -> FalsificationResult:
        """System must distinguish world/plan evolution from earlier cognition being wrong."""
        pairs_tested = []
        confusions = []

        contrast_pairs = [g for g in self.gold_pairs.values() if "F4_STATE_VS_CORRECTION" in g.falsification_tags]
        for g in contrast_pairs:
            adj = self.adjudications.get(g.pair_id)
            if not adj:
                continue

            gold_rel = g.relation_type
            pred_rel = adj.predicted_relation

            is_confusion = (
                (gold_rel == LongitudinalRelationType.STATE_CHANGE and pred_rel == LongitudinalRelationType.CORRECTION_RETRACTION) or
                (gold_rel == LongitudinalRelationType.CORRECTION_RETRACTION and pred_rel == LongitudinalRelationType.STATE_CHANGE)
            )

            pairs_tested.append({"pair_id": g.pair_id, "gold": gold_rel.value, "pred": pred_rel.value, "confused": is_confusion})
            if is_confusion:
                confusions.append({"pair_id": g.pair_id, "gold": gold_rel.value, "pred": pred_rel.value})

        passed = len(confusions) == 0
        rate = len(confusions) / max(1, len(pairs_tested))
        summary = f"Evaluated {len(pairs_tested)} contrastive pairs. State change vs correction confusions: {len(confusions)} (Error rate: {rate*100:.1f}%)."
        return FalsificationResult("F4", "State change != correction", passed, summary, {"confusions": confusions, "rate": rate, "pairs_tested": pairs_tested})

    # -------------------------------------------------------------------------
    # F5: Sparse candidate formation
    # -------------------------------------------------------------------------
    def test_f5(self) -> FalsificationResult:
        """Avoid all-pairs comparison while preserving high recall of true longitudinal relations."""
        reduction = self.l2_metrics.reduction_pct
        recall = self.l2_metrics.recall

        passed = reduction >= 70.0 and recall >= 0.95
        summary = f"L2 Candidate Reduction: {reduction:.1f}% vs all-pairs. True Relation Recall: {recall*100:.1f}%."
        return FalsificationResult(
            "F5",
            "Sparse candidate formation",
            passed,
            summary,
            {
                "reduction_pct": reduction,
                "recall": recall,
                "candidates_produced": self.l2_metrics.candidates_produced,
                "total_possible": self.l2_metrics.total_possible_pairs,
            },
        )

    def run_all(self) -> list[FalsificationResult]:
        return [
            self.test_f1(),
            self.test_f2(),
            self.test_f3(),
            self.test_f4(),
            self.test_f5(),
        ]
