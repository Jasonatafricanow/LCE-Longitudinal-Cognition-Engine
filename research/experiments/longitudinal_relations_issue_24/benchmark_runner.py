"""Benchmark Runner for Issue #24: Time-First Longitudinal Relations.

Executes:
1. Candidate Formation Evaluation across L0, L1, L2.
2. Selective Adjudication (L3) across Dev and Held-Out splits.
3. Falsification Verification Suite (F1 - F5).
4. Cost and latency accounting.
5. Serialization of detailed results.
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from lce.cognition.longitudinal_relation import LongitudinalRelationType
from research.experiments.longitudinal_relations_issue_24.candidate_generator import (
    CandidateGenerator,
)
from research.experiments.longitudinal_relations_issue_24.contracts import (
    AdjudicationOutput,
    CandidateFormationMetrics,
    CorpusBlockRecord,
    CostMetrics,
    GoldRelationRecord,
    RelationAdjudicationMetrics,
    TemporalIntegrityMetrics,
)
from research.experiments.longitudinal_relations_issue_24.falsification_tests import (
    FalsificationSuite,
)
from research.experiments.longitudinal_relations_issue_24.longitudinal_adjudicator import (
    LongitudinalAdjudicator,
)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

CORPUS_FILE = DATA_DIR / "corpus_blocks.jsonl"
GOLD_FILE = DATA_DIR / "gold_relations.jsonl"
SPLITS_FILE = DATA_DIR / "splits.json"


def load_corpus() -> list[CorpusBlockRecord]:
    records = []
    with open(CORPUS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            records.append(
                CorpusBlockRecord(
                    block_id=d["block_id"],
                    content=d["content"],
                    occurred_start=datetime.fromisoformat(d["occurred_start"]).astimezone(UTC),
                    occurred_end=datetime.fromisoformat(d["occurred_end"]).astimezone(UTC),
                    domain=d["domain"],
                    thread_id=d["thread_id"],
                    projections=d["projections"],
                    raw_evidence_ids=tuple(d.get("raw_evidence_ids", ["ev_01"])),
                    compiler_version=d.get("compiler_version", "v0.3"),
                    lineage_id=d.get("lineage_id", "main"),
                )
            )
    return records


def load_gold_relations() -> list[GoldRelationRecord]:
    records = []
    with open(GOLD_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            records.append(
                GoldRelationRecord(
                    pair_id=d["pair_id"],
                    predecessor_block_id=d["predecessor_block_id"],
                    successor_block_id=d["successor_block_id"],
                    relation_type=LongitudinalRelationType(d["relation_type"]),
                    affected_dimension=d["affected_dimension"],
                    prior_unknown_resolved=d["prior_unknown_resolved"],
                    resolved_dimension=d["resolved_dimension"],
                    outcome_or_current_state=d["outcome_or_current_state"],
                    gold_evidence_spans=tuple(d["gold_evidence_spans"]),
                    split=d["split"],
                    contrastive_family=d["contrastive_family"],
                    falsification_tags=tuple(d.get("falsification_tags", [])),
                    reason_competing_rejections=d.get("reason_competing_rejections", {}),
                )
            )
    return records


class LongitudinalBenchmarkRunner:
    def __init__(self) -> None:
        self.blocks = load_corpus()
        self.block_map = {b.block_id: b for b in self.blocks}
        self.gold_relations = load_gold_relations()
        with open(SPLITS_FILE, "r", encoding="utf-8") as f:
            self.splits = json.load(f)

        self.candidate_gen = CandidateGenerator()
        self.adjudicator = LongitudinalAdjudicator()

    def evaluate_candidate_formation(self, blocks: list[CorpusBlockRecord], gold_set: list[GoldRelationRecord]) -> dict[str, CandidateFormationMetrics]:
        """Evaluate L0, L1, L2 candidate generation efficiency and recall."""
        # Non-unrelated gold pairs represent true longitudinal relations to recall
        true_relation_pairs = {
            (g.predecessor_block_id, g.successor_block_id)
            for g in gold_set
            if g.relation_type != LongitudinalRelationType.UNRELATED
        }
        total_true = len(true_relation_pairs)

        # All possible forward pairs
        n = len(blocks)
        total_possible = n * (n - 1) // 2

        # 1. L0
        l0_cands = self.candidate_gen.generate_l0(blocks)
        l0_pairs = {(c.predecessor_block_id, c.successor_block_id) for c in l0_cands}
        l0_recalled = len(l0_pairs.intersection(true_relation_pairs))
        l0_recall = l0_recalled / max(1, total_true)
        l0_false_rate = (len(l0_pairs) - l0_recalled) / max(1, len(l0_pairs))
        l0_reduction = (1.0 - len(l0_pairs) / max(1, total_possible)) * 100.0

        m_l0 = CandidateFormationMetrics(
            level="L0",
            total_possible_pairs=total_possible,
            candidates_produced=len(l0_cands),
            true_relation_pairs_count=total_true,
            true_candidates_recalled=l0_recalled,
            recall=l0_recall,
            candidates_per_block=len(l0_cands) / max(1, n),
            reduction_pct=l0_reduction,
            false_candidate_rate=l0_false_rate,
        )

        # 2. L1
        l1_cands = self.candidate_gen.generate_l1(blocks, l0_cands)
        l1_pairs = {(c.predecessor_block_id, c.successor_block_id) for c in l1_cands}
        l1_recalled = len(l1_pairs.intersection(true_relation_pairs))
        l1_recall = l1_recalled / max(1, total_true)
        l1_false_rate = (len(l1_pairs) - l1_recalled) / max(1, len(l1_pairs))
        l1_reduction = (1.0 - len(l1_pairs) / max(1, total_possible)) * 100.0

        m_l1 = CandidateFormationMetrics(
            level="L1",
            total_possible_pairs=total_possible,
            candidates_produced=len(l1_cands),
            true_relation_pairs_count=total_true,
            true_candidates_recalled=l1_recalled,
            recall=l1_recall,
            candidates_per_block=len(l1_cands) / max(1, n),
            reduction_pct=l1_reduction,
            false_candidate_rate=l1_false_rate,
        )

        # 3. L2
        l2_cands = self.candidate_gen.generate_l2(blocks, l0_cands)
        l2_pairs = {(c.predecessor_block_id, c.successor_block_id) for c in l2_cands}
        l2_recalled = len(l2_pairs.intersection(true_relation_pairs))
        l2_recall = l2_recalled / max(1, total_true)
        l2_false_rate = (len(l2_pairs) - l2_recalled) / max(1, len(l2_pairs))
        l2_reduction = (1.0 - len(l2_pairs) / max(1, total_possible)) * 100.0

        m_l2 = CandidateFormationMetrics(
            level="L2",
            total_possible_pairs=total_possible,
            candidates_produced=len(l2_cands),
            true_relation_pairs_count=total_true,
            true_candidates_recalled=l2_recalled,
            recall=l2_recall,
            candidates_per_block=len(l2_cands) / max(1, n),
            reduction_pct=l2_reduction,
            false_candidate_rate=l2_false_rate,
        )

        return {"L0": m_l0, "L1": m_l1, "L2": m_l2}

    def evaluate_adjudication(
        self,
        gold_pairs: list[GoldRelationRecord],
    ) -> tuple[RelationAdjudicationMetrics, dict[str, AdjudicationOutput]]:
        """Run L3 selective adjudication and compute classification metrics."""
        adjudications: dict[str, AdjudicationOutput] = {}

        matrix = defaultdict(lambda: defaultdict(int))
        correct_count = 0

        # Sub-category counters
        sc_total = 0
        sc_correct = 0

        cr_total = 0
        cr_correct = 0

        sc_cr_confusion = 0  # Confusions between state change and correction

        ur_total = 0
        ur_correct = 0

        persist_total = 0
        persist_correct = 0

        unrelated_total = 0
        unrelated_correct = 0

        unknown_pred_count = 0

        for g in gold_pairs:
            t1 = self.block_map[g.predecessor_block_id]
            t2 = self.block_map[g.successor_block_id]

            adj = self.adjudicator.adjudicate(g.pair_id, t1, t2)
            adjudications[g.pair_id] = adj

            gold_rel = g.relation_type.value
            pred_rel = adj.predicted_relation.value

            matrix[gold_rel][pred_rel] += 1

            if gold_rel == pred_rel:
                correct_count += 1

            if pred_rel == LongitudinalRelationType.UNKNOWN_RELATION.value:
                unknown_pred_count += 1

            # Category tracking
            if g.relation_type == LongitudinalRelationType.STATE_CHANGE:
                sc_total += 1
                if adj.predicted_relation == LongitudinalRelationType.STATE_CHANGE:
                    sc_correct += 1
                elif adj.predicted_relation == LongitudinalRelationType.CORRECTION_RETRACTION:
                    sc_cr_confusion += 1

            elif g.relation_type == LongitudinalRelationType.CORRECTION_RETRACTION:
                cr_total += 1
                if adj.predicted_relation == LongitudinalRelationType.CORRECTION_RETRACTION:
                    cr_correct += 1
                elif adj.predicted_relation == LongitudinalRelationType.STATE_CHANGE:
                    sc_cr_confusion += 1

            elif g.relation_type == LongitudinalRelationType.UNCERTAINTY_RESOLUTION:
                ur_total += 1
                if adj.predicted_relation == LongitudinalRelationType.UNCERTAINTY_RESOLUTION:
                    ur_correct += 1

            elif g.relation_type == LongitudinalRelationType.PERSISTENCE_CONFIRMATION:
                persist_total += 1
                if adj.predicted_relation == LongitudinalRelationType.PERSISTENCE_CONFIRMATION:
                    persist_correct += 1

            elif g.relation_type == LongitudinalRelationType.UNRELATED:
                unrelated_total += 1
                if adj.predicted_relation == LongitudinalRelationType.UNRELATED:
                    unrelated_correct += 1

        total = len(gold_pairs)
        sc_acc = sc_correct / max(1, sc_total)
        cr_acc = cr_correct / max(1, cr_total)
        sc_cr_rate = sc_cr_confusion / max(1, sc_total + cr_total)
        ur_acc = ur_correct / max(1, ur_total)
        persist_acc = persist_correct / max(1, persist_total)
        unrelated_acc = unrelated_correct / max(1, unrelated_total)
        overall_acc = correct_count / max(1, total)

        clean_matrix = {k: dict(v) for k, v in matrix.items()}

        metrics = RelationAdjudicationMetrics(
            level="L3",
            total_evaluated=total,
            overall_accuracy=overall_acc,
            state_change_accuracy=sc_acc,
            correction_retraction_accuracy=cr_acc,
            state_vs_correction_confusion_rate=sc_cr_rate,
            uncertainty_resolution_accuracy=ur_acc,
            persistence_accuracy=persist_acc,
            unrelated_rejection_accuracy=unrelated_acc,
            unknown_relation_rate=unknown_pred_count / max(1, total),
            confusion_matrix=clean_matrix,
        )

        return metrics, adjudications

    def run(self) -> dict[str, Any]:
        print("Starting Benchmark Execution for Issue #24...")

        dev_blocks = [b for b in self.blocks if b.block_id in self.splits["dev_block_ids"]]
        held_out_blocks = [b for b in self.blocks if b.block_id in self.splits["held_out_block_ids"]]

        dev_gold = [g for g in self.gold_relations if g.split == "dev"]
        held_out_gold = [g for g in self.gold_relations if g.split == "held_out"]

        print(f"Loaded: Total Blocks={len(self.blocks)} (Dev={len(dev_blocks)}, Held-Out={len(held_out_blocks)})")
        print(f"Loaded: Gold Pairs={len(self.gold_relations)} (Dev={len(dev_gold)}, Held-Out={len(held_out_gold)})")

        # 1. Candidate Formation (Full & Per Split)
        print("\n=== Phase 1: Candidate Formation (L0, L1, L2) ===")
        cand_metrics_dev = self.evaluate_candidate_formation(dev_blocks, dev_gold)
        cand_metrics_held_out = self.evaluate_candidate_formation(held_out_blocks, held_out_gold)
        cand_metrics_total = self.evaluate_candidate_formation(self.blocks, self.gold_relations)

        for lvl in ["L0", "L1", "L2"]:
            m = cand_metrics_total[lvl]
            print(f"[{lvl}] Candidates: {m.candidates_produced}, Reduction: {m.reduction_pct:.1f}%, True Recall: {m.recall*100:.1f}%, False Cand Rate: {m.false_candidate_rate*100:.1f}%")

        # 2. Adjudication on Dev Split
        print("\n=== Phase 2: L3 Adjudication on Dev Split ===")
        dev_adj_metrics, dev_adjs = self.evaluate_adjudication(dev_gold)
        print(f"Dev Overall Accuracy: {dev_adj_metrics.overall_accuracy*100:.1f}%")
        print(f"Dev State Change Acc: {dev_adj_metrics.state_change_accuracy*100:.1f}%")
        print(f"Dev Correction Acc: {dev_adj_metrics.correction_retraction_accuracy*100:.1f}%")
        print(f"Dev State vs Correction Confusion: {dev_adj_metrics.state_vs_correction_confusion_rate*100:.1f}%")
        print(f"Dev Uncertainty Resolution Acc: {dev_adj_metrics.uncertainty_resolution_accuracy*100:.1f}%")
        print(f"Dev Persistence Acc: {dev_adj_metrics.persistence_accuracy*100:.1f}%")
        print(f"Dev Unrelated Rejection Acc: {dev_adj_metrics.unrelated_rejection_accuracy*100:.1f}%")

        # 3. Adjudication on Held-Out Split
        print("\n=== Phase 3: L3 Adjudication on Held-Out Split ===")
        ho_adj_metrics, ho_adjs = self.evaluate_adjudication(held_out_gold)
        print(f"Held-Out Overall Accuracy: {ho_adj_metrics.overall_accuracy*100:.1f}%")
        print(f"Held-Out State Change Acc: {ho_adj_metrics.state_change_accuracy*100:.1f}%")
        print(f"Held-Out Correction Acc: {ho_adj_metrics.correction_retraction_accuracy*100:.1f}%")
        print(f"Held-Out State vs Correction Confusion: {ho_adj_metrics.state_vs_correction_confusion_rate*100:.1f}%")
        print(f"Held-Out Uncertainty Resolution Acc: {ho_adj_metrics.uncertainty_resolution_accuracy*100:.1f}%")
        print(f"Held-Out Persistence Acc: {ho_adj_metrics.persistence_accuracy*100:.1f}%")
        print(f"Held-Out Unrelated Rejection Acc: {ho_adj_metrics.unrelated_rejection_accuracy*100:.1f}%")

        all_adjs = {**dev_adjs, **ho_adjs}

        # 4. Falsification Suite
        print("\n=== Phase 4: Falsification Suite (F1 - F5) ===")
        suite = FalsificationSuite(
            blocks=self.blocks,
            gold_pairs=self.gold_relations,
            adjudications=all_adjs,
            l2_metrics=cand_metrics_total["L2"],
        )
        falsification_results = suite.run_all()
        for fr in falsification_results:
            status = "PASSED" if fr.passed else "FAILED"
            print(f"[{fr.falsification_id}] {fr.name}: {status} -> {fr.evidence_summary}")

        # 5. Cost Accounting
        total_tokens = sum(a.prompt_tokens + a.completion_tokens for a in all_adjs.values())
        total_latency = sum(a.latency_ms for a in all_adjs.values())
        accepted_relations = len([a for a in all_adjs.values() if a.predicted_relation != LongitudinalRelationType.UNRELATED])

        cost_metrics = CostMetrics(
            total_adjudication_calls=len(all_adjs),
            calls_per_block=len(all_adjs) / max(1, len(self.blocks)),
            tokens_per_accepted_relation=total_tokens / max(1, accepted_relations),
            avg_latency_ms=total_latency / max(1, len(all_adjs)),
        )
        print(f"\nCost Summary: Total Calls={cost_metrics.total_adjudication_calls}, Calls/Block={cost_metrics.calls_per_block:.2f}, Tokens/Accepted={cost_metrics.tokens_per_accepted_relation:.1f}, Avg Latency={cost_metrics.avg_latency_ms:.1f}ms")

        # Save results
        summary_payload = {
            "date": datetime.now(UTC).isoformat(),
            "candidate_metrics": {
                "dev": {k: asdict(v) for k, v in cand_metrics_dev.items()},
                "held_out": {k: asdict(v) for k, v in cand_metrics_held_out.items()},
                "total": {k: asdict(v) for k, v in cand_metrics_total.items()},
            },
            "adjudication_metrics": {
                "dev": asdict(dev_adj_metrics),
                "held_out": asdict(ho_adj_metrics),
            },
            "falsification_results": [asdict(fr) for fr in falsification_results],
            "cost_metrics": asdict(cost_metrics),
        }


        with open(RESULTS_DIR / "benchmark_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary_payload, f, ensure_ascii=False, indent=2)

        adjs_payload = {
            p_id: {
                "pair_id": a.pair_id,
                "predecessor": a.predecessor_block_id,
                "successor": a.successor_block_id,
                "predicted_relation": a.predicted_relation.value,
                "affected_dimension": a.affected_dimension,
                "prior_unknown_resolved": a.prior_unknown_resolved,
                "resolved_dimension": a.resolved_dimension,
                "outcome_or_current_state": a.outcome_or_current_state,
                "evidence_spans": list(a.evidence_spans),
                "reason_competing_rejections": a.reason_competing_rejections,
                "confidence": a.confidence,
                "adjudication_trace": a.adjudication_trace,
                "cached": a.cached,
            }
            for p_id, a in all_adjs.items()
        }
        with open(RESULTS_DIR / "adjudications.json", "w", encoding="utf-8") as f:
            json.dump(adjs_payload, f, ensure_ascii=False, indent=2)

        print("\nAll results saved successfully to research/experiments/longitudinal_relations_issue_24/results/")
        return summary_payload


if __name__ == "__main__":
    runner = LongitudinalBenchmarkRunner()
    runner.run()
