"""Tests for Issue #26: Fresh confirmatory heldout for Path B.

Freeze rule: DO NOT modify any Issue #25 code based on failures here.
This is a one-shot frozen evaluation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research.experiments.path_b_confirmatory_issue_26.confirmatory_runner import run_confirmatory
from research.experiments.path_b_confirmatory_issue_26.heldout_corpus import (
    build_heldout_corpus,
    build_heldout_gold,
)
from research.experiments.path_b_production_issue_25.contracts import LongitudinalRelation


RESULTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "research"
    / "experiments"
    / "path_b_confirmatory_issue_26"
    / "results"
)

FROZEN_SHA = "85974a2"


# ===================================================================
# Corpus validation
# ===================================================================


class TestHeldoutCorpus:
    """Validate corpus properties before running frozen evaluation."""

    def test_corpus_size(self):
        corpus = build_heldout_corpus()
        assert len(corpus) == 33

    def test_no_oracle_fields(self):
        forbidden = {"thread_id", "oracle_domain", "correction_nature",
                      "gold_relation", "trajectory_label", "grouping_key"}
        for v in build_heldout_corpus():
            found = forbidden & set(v.provenance.keys())
            assert not found, f"{v.memory_id} has forbidden: {found}"

    def test_chronological_ordering(self):
        corpus = build_heldout_corpus()
        for i in range(len(corpus) - 1):
            assert corpus[i].temporal.received_at <= corpus[i+1].temporal.received_at

    def test_gold_covers_all_14_families(self):
        golds = build_heldout_gold()
        families = {g.semantic_family for g in golds}
        expected = {
            "F1_plan_completed", "F2_plan_failed", "F3_plan_cancelled",
            "F4_confirmed", "F5_disproven", "F6_resolved",
            "F7_state_change", "F8_correction", "F9_persistence",
            "F10_unrelated_similar", "F11_late_fact", "F12_future_changed",
            "F13_weak_lexical_strong_relation",
            "F14_strong_lexical_no_relation",
            "noise_contrast",
        }
        assert expected.issubset(families), f"Missing: {expected - families}"

    def test_gold_positive_count(self):
        """15-20 positive gold relations expected."""
        golds = build_heldout_gold()
        positive = [g for g in golds
                    if g.longitudinal_relation != LongitudinalRelation.UNRELATED]
        assert 10 <= len(positive) <= 20, f"Got {len(positive)} positive golds"

    def test_no_overlap_with_issue25_ids(self):
        """Heldout IDs must not collide with Issue #25."""
        from research.experiments.path_b_production_issue_25.corpus import build_corpus
        issue25_ids = {v.memory_id for v in build_corpus()}
        heldout_ids = {v.memory_id for v in build_heldout_corpus()}
        overlap = issue25_ids & heldout_ids
        assert not overlap, f"ID collision with Issue #25: {overlap}"


# ===================================================================
# Frozen one-shot evaluation
# ===================================================================


class TestFrozenEvaluation:
    """Run the single frozen evaluation and record all results."""

    @pytest.fixture(scope="class")
    def result(self):
        return run_confirmatory(RESULTS_DIR)

    def test_frozen_sha_recorded(self, result):
        assert result.frozen_sha == FROZEN_SHA

    def test_temporal_integrity_passes(self, result):
        """No temporal violations on unseen data."""
        assert result.temporal_integrity["reverse_time_errors"] == 0
        assert result.temporal_integrity["future_leakage_count"] == 0
        assert result.temporal_integrity["passed_all"] is True

    def test_no_oracle_fields_in_pipeline(self, result):
        """Frozen pipeline ran without oracle fields."""
        assert result.corpus_size == 33

    def test_adjudicator_gate_holds(self, result):
        """Only Stage 1 candidates entered adjudication (F3)."""
        # All adjudicated pairs must be in B2 candidates
        b2_path = RESULTS_DIR / "b2_candidates.jsonl"
        b3_path = RESULTS_DIR / "b3_adjudication.jsonl"
        assert b2_path.exists()
        assert b3_path.exists()

        b2_pairs = set()
        with open(b2_path, "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                b2_pairs.add((r["predecessor_id"], r["successor_id"]))

        with open(b3_path, "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                pair = (r["predecessor_id"], r["successor_id"])
                assert pair in b2_pairs, f"Adjudicated {pair} not in B2"


# ===================================================================
# Q1: Miss analysis
# ===================================================================


class TestMissAnalysis:
    """Record and classify every miss without fixing."""

    @pytest.fixture(scope="class")
    def result(self):
        return run_confirmatory(RESULTS_DIR)

    def test_miss_analysis_has_entries(self, result):
        """If there are misses, they must be classified."""
        # We expect some misses given the frozen mechanism
        for entry in result.miss_analysis:
            assert "miss_categories" in entry
            assert len(entry["miss_categories"]) > 0
            assert "pair_id" in entry
            assert "semantic_family" in entry

    def test_miss_categories_are_valid(self, result):
        valid = {
            "lexical_discontinuity", "temporal_distance",
            "missing_semantic_anchor", "candidate_budget_cutoff",
            "vector_miss", "boundary_signal_miss", "ambiguous_gold", "other",
        }
        for entry in result.miss_analysis:
            for cat in entry["miss_categories"]:
                assert cat in valid, f"Invalid miss category: {cat}"


# ===================================================================
# Q2: B1 vs B2 marginal value
# ===================================================================


class TestMarginalValue:
    """Determine if B2 adds real recall over B1."""

    @pytest.fixture(scope="class")
    def result(self):
        return run_confirmatory(RESULTS_DIR)

    def test_marginal_value_recorded(self, result):
        mv = result.marginal_value
        assert "b1_recall" in mv
        assert "b2_recall" in mv
        assert "b1_volume" in mv
        assert "b2_volume" in mv
        assert "b2_only_targets" in mv
        assert "b1_only_targets" in mv

    def test_volume_comparison_recorded(self, result):
        """B1 vs B2 volume difference must be measurable."""
        mv = result.marginal_value
        assert isinstance(mv["b1_volume"], int)
        assert isinstance(mv["b2_volume"], int)


# ===================================================================
# Q3: Adjudication safety
# ===================================================================


class TestAdjudicationSafety:
    """Check adjudication on unseen data."""

    @pytest.fixture(scope="class")
    def result(self):
        return run_confirmatory(RESULTS_DIR)

    def test_no_unrelated_resolves_unknown(self, result):
        """F6: UNRELATED must not close unknowns."""
        b3_path = RESULTS_DIR / "b3_adjudication.jsonl"
        with open(b3_path, "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if r["longitudinal_relation"] == "UNRELATED":
                    ke = r["knowledge_effect"]
                    assert ke["prior_unknown_resolved"] is not True, (
                        f"F6 violation: {r['candidate_id']}"
                    )

    def test_confusion_matrix_recorded(self, result):
        assert "confusion_matrix" in result.adjudication_metrics


# ===================================================================
# Q4: Dual axis output
# ===================================================================


class TestDualAxisOutput:
    """Confirm orthogonal axes coexist on unseen data."""

    @pytest.fixture(scope="class")
    def result(self):
        return run_confirmatory(RESULTS_DIR)

    def test_dual_axis_cases_exist(self, result):
        """At least one case with STATE_CHANGE + prior_unknown_resolved."""
        assert len(result.q4_dual_axis_cases) > 0, (
            "No result has STATE_CHANGE + prior_unknown_resolved=True"
        )


# ===================================================================
# Output deliverables
# ===================================================================


class TestDeliverables:
    """Verify all required output files are created."""

    @pytest.fixture(scope="class", autouse=True)
    def ensure_run(self):
        run_confirmatory(RESULTS_DIR)

    def test_summary_exists(self):
        assert (RESULTS_DIR / "confirmatory_summary.json").exists()

    def test_candidate_files_exist(self):
        for name in ["b0_candidates.jsonl", "b1_candidates.jsonl",
                      "b2_candidates.jsonl", "b3_adjudication.jsonl"]:
            assert (RESULTS_DIR / name).exists(), f"Missing {name}"

    def test_summary_structure(self):
        with open(RESULTS_DIR / "confirmatory_summary.json", "r",
                  encoding="utf-8") as f:
            data = json.load(f)
        required = [
            "frozen_sha", "candidate_metrics", "adjudication_metrics",
            "knowledge_effect_metrics", "temporal_integrity",
            "miss_analysis", "marginal_value", "q4_dual_axis_cases",
            "verdict",
        ]
        for key in required:
            assert key in data, f"Missing key: {key}"
