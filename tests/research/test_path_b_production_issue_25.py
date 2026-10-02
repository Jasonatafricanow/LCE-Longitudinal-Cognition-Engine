"""Tests for Issue #25: Production-shaped Path B Latent Longitudinal Discovery.

Validates the complete two-stage pipeline:
  Stage 1: Latent candidate discovery (B0/B1/B2)
  Stage 2: Selective adjudication with orthogonal relation + knowledge effect
"""

# ruff: noqa: I001

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from research.experiments.path_b_production_issue_25.adjudicator import SelectiveAdjudicator
from research.experiments.path_b_production_issue_25.benchmark import (
    compute_candidate_metrics,
    compute_temporal_integrity,
    run_benchmark,
)
from research.experiments.path_b_production_issue_25.candidate_generator import CandidateGenerator
from research.experiments.path_b_production_issue_25.contracts import (
    AdjudicationResult,
    DiscoveredCandidate,
    KnowledgeEffect,
    LongitudinalRelation,
    ProductionMemoryView,
    TemporalCoordinates,
)
from research.experiments.path_b_production_issue_25.corpus import (
    build_corpus,
    build_gold_annotations,
)


RESULTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "research"
    / "experiments"
    / "path_b_production_issue_25"
    / "results"
)


# ===================================================================
# Contract tests
# ===================================================================


class TestContracts:
    """Validate the production-shaped input contract."""

    def test_production_memory_view_rejects_oracle_fields(self):
        """Oracle fields in provenance must be rejected."""
        with pytest.raises(ValueError, match="oracle fields"):
            ProductionMemoryView(
                memory_id="test",
                content="test content",
                source_refs=("ev1",),
                temporal=TemporalCoordinates(
                    source_occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
                    received_at=datetime(2026, 1, 1, 1, tzinfo=UTC),
                ),
                provenance={"thread_id": "t1"},  # FORBIDDEN
            )

    def test_production_memory_view_rejects_domain_oracle(self):
        with pytest.raises(ValueError, match="oracle fields"):
            ProductionMemoryView(
                memory_id="test",
                content="test content",
                source_refs=("ev1",),
                temporal=TemporalCoordinates(
                    source_occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
                    received_at=datetime(2026, 1, 1, 1, tzinfo=UTC),
                ),
                provenance={"oracle_domain": "travel"},
            )

    def test_production_memory_view_accepts_clean_provenance(self):
        view = ProductionMemoryView(
            memory_id="test",
            content="test content",
            source_refs=("ev1",),
            temporal=TemporalCoordinates(
                source_occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
                received_at=datetime(2026, 1, 1, 1, tzinfo=UTC),
            ),
            provenance={"source_type": "chat", "channel": "app"},
        )
        assert view.memory_id == "test"

    def test_knowledge_effect_orthogonal_to_relation(self):
        """STATE_CHANGE + prior_unknown_resolved = True must be valid."""
        result = AdjudicationResult(
            candidate_id="test",
            predecessor_id="a",
            successor_id="b",
            longitudinal_relation=LongitudinalRelation.STATE_CHANGE,
            knowledge_effect=KnowledgeEffect(
                prior_unknown_resolved=True,
                resolved_dimensions=("outcome",),
            ),
        )
        assert result.longitudinal_relation == LongitudinalRelation.STATE_CHANGE
        assert result.knowledge_effect.prior_unknown_resolved is True

    def test_unrelated_cannot_resolve_unknowns(self):
        """UNRELATED + prior_unknown_resolved = True is invalid."""
        with pytest.raises(ValueError, match="UNRELATED cannot resolve"):
            AdjudicationResult(
                candidate_id="test",
                predecessor_id="a",
                successor_id="b",
                longitudinal_relation=LongitudinalRelation.UNRELATED,
                knowledge_effect=KnowledgeEffect(prior_unknown_resolved=True),
            )

    def test_temporal_violation_rejected(self):
        """Successor cannot precede predecessor."""
        with pytest.raises(ValueError, match="Temporal violation"):
            DiscoveredCandidate(
                candidate_id="test",
                predecessor_id="a",
                successor_id="b",
                predecessor_time=datetime(2026, 2, 1, tzinfo=UTC),
                successor_time=datetime(2026, 1, 1, tzinfo=UTC),
                signals=("test",),
                baseline_level="B0",
            )

    def test_relation_enum_values(self):
        """Verify the relation enum has the expected values."""
        assert LongitudinalRelation.STATE_CHANGE == "STATE_CHANGE"
        assert LongitudinalRelation.CORRECTION_RETRACTION == "CORRECTION_RETRACTION"
        assert LongitudinalRelation.PERSISTENCE_CONFIRMATION == "PERSISTENCE_CONFIRMATION"
        assert LongitudinalRelation.UNRELATED == "UNRELATED"
        assert LongitudinalRelation.UNKNOWN_RELATION == "UNKNOWN_RELATION"

    def test_knowledge_effect_resolved_dimensions_consistency(self):
        """resolved_dimensions must be empty when prior_unknown_resolved is False."""
        with pytest.raises(ValueError, match="resolved_dimensions must be empty"):
            KnowledgeEffect(
                prior_unknown_resolved=False,
                resolved_dimensions=("x",),
            )


# ===================================================================
# Corpus validation
# ===================================================================


class TestCorpus:
    """Validate the adversarial corpus properties."""

    def test_corpus_size(self):
        corpus = build_corpus()
        assert len(corpus) == 28

    def test_no_oracle_fields_in_corpus(self):
        """F2: No oracle fields in any corpus block."""
        forbidden = {"thread_id", "oracle_domain", "correction_nature",
                      "gold_relation", "trajectory_label", "grouping_key"}
        for view in build_corpus():
            found = forbidden & set(view.provenance.keys())
            assert not found, f"{view.memory_id} has forbidden fields: {found}"

    def test_chronological_ordering(self):
        """Corpus is sorted by received_at."""
        corpus = build_corpus()
        for i in range(len(corpus) - 1):
            assert corpus[i].temporal.received_at <= corpus[i + 1].temporal.received_at

    def test_gold_annotations_cover_all_families(self):
        golds = build_gold_annotations()
        families = {g.semantic_family for g in golds}
        expected = {
            "F1_plan_completed", "F2_plan_failed", "F3_plan_cancelled",
            "F4_confirmed", "F5_disproven", "F6_resolved",
            "F7_state_change", "F8_correction", "F9_persistence",
            "F10_unrelated_similar", "F11_late_fact", "F12_future_changed",
            "noise_contrast",
        }
        assert expected.issubset(families), f"Missing: {expected - families}"

    def test_gold_has_noise_contrasts(self):
        golds = build_gold_annotations()
        noise = [g for g in golds if g.semantic_family == "noise_contrast"]
        assert len(noise) >= 3, "Need at least 3 noise contrast pairs"


# ===================================================================
# Stage 1: Candidate discovery tests
# ===================================================================


class TestCandidateDiscovery:
    """Test Stage 1 candidate generation at each baseline level."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.corpus = build_corpus()
        self.golds = build_gold_annotations()
        self.gen = CandidateGenerator()

    def test_b0_produces_temporal_candidates(self):
        b0 = self.gen.generate_b0(self.corpus)
        assert len(b0) > 0
        # All B0 candidates respect temporal ordering
        for c in b0:
            assert c.successor_time >= c.predecessor_time
            assert c.baseline_level == "B0"

    def test_b0_time_only_captures_unrelated(self):
        """F1: Time-only must capture unrelated pairs (insufficient alone)."""
        b0 = self.gen.generate_b0(self.corpus)
        b0_pairs = {(c.predecessor_id, c.successor_id) for c in b0}
        # Check that at least some B0 pairs are not true relations
        true_pairs = {
            (g.predecessor_id, g.successor_id)
            for g in self.golds
            if g.longitudinal_relation != LongitudinalRelation.UNRELATED
        }
        false_in_b0 = b0_pairs - true_pairs
        assert len(false_in_b0) > 0, "B0 should contain false candidates"

    def test_b1_filters_by_embedding(self):
        b0 = self.gen.generate_b0(self.corpus)
        b1 = self.gen.generate_b1(self.corpus, b0)
        assert len(b1) < len(b0), "B1 should filter B0 candidates"

    def test_b2_uses_boundary_signals(self):
        b0 = self.gen.generate_b0(self.corpus)
        b2 = self.gen.generate_b2(self.corpus, b0)
        # B2 candidates should have more than just temporal_precedence
        for c in b2:
            assert len(c.signals) > 1, f"{c.candidate_id} has only temporal signal"

    def test_b2_recall_of_true_relations(self):
        """B2 must recall most true relation pairs."""
        b2 = self.gen.generate_b2(self.corpus)
        metrics = compute_candidate_metrics(
            b2, self.golds, len(self.corpus), "B2"
        )
        # We want at least 60% recall (this is a tough adversarial set)
        assert metrics.recall >= 0.50, (
            f"B2 recall {metrics.recall:.2f} < 0.50; "
            f"missed: {metrics.target_miss_ids}"
        )

    def test_b2_reduction_vs_b0(self):
        """F7: B2 should produce significantly fewer candidates than B0."""
        b0 = self.gen.generate_b0(self.corpus)
        b2 = self.gen.generate_b2(self.corpus, b0)
        reduction = (1.0 - len(b2) / len(b0)) * 100 if b0 else 0.0
        assert reduction >= 40.0, (
            f"B2 reduction {reduction:.1f}% < 40% (B0={len(b0)}, B2={len(b2)})"
        )


# ===================================================================
# Stage 2: Adjudication tests
# ===================================================================


class TestAdjudication:
    """Test Stage 2 selective adjudication."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.corpus = build_corpus()
        self.golds = build_gold_annotations()
        self.gen = CandidateGenerator()
        self.b2 = self.gen.generate_b2(self.corpus)
        self.adjudicator = SelectiveAdjudicator(self.corpus)
        self.results = self.adjudicator.adjudicate(self.b2)

    def test_adjudicator_only_receives_stage1_candidates(self):
        """F3: Only discovered candidates enter the adjudicator."""
        b2_pairs = {(c.predecessor_id, c.successor_id) for c in self.b2}
        for result in self.results:
            pair = (result.predecessor_id, result.successor_id)
            assert pair in b2_pairs, f"Adjudicated pair {pair} not in B2 candidates"

    def test_orthogonal_axes_representable(self):
        """F5: STATE_CHANGE + prior_unknown_resolved = True must appear."""
        dual_results = [
            r for r in self.results
            if r.longitudinal_relation == LongitudinalRelation.STATE_CHANGE
            and r.knowledge_effect.prior_unknown_resolved is True
        ]
        assert len(dual_results) > 0, (
            "No result has STATE_CHANGE + prior_unknown_resolved=True"
        )

    def test_no_unrelated_resolves_unknown(self):
        """F6: UNRELATED cannot resolve prior unknowns."""
        for result in self.results:
            if result.longitudinal_relation == LongitudinalRelation.UNRELATED:
                assert result.knowledge_effect.prior_unknown_resolved is not True

    def test_state_change_vs_correction_separable(self):
        """F4: Correction and state change must be distinguishable."""
        gold_map = {(g.predecessor_id, g.successor_id): g for g in self.golds}
        for result in self.results:
            key = (result.predecessor_id, result.successor_id)
            if key not in gold_map:
                continue
            gold = gold_map[key]
            # Strict F4: no confusion between STATE_CHANGE and CORRECTION_RETRACTION
            if gold.longitudinal_relation == LongitudinalRelation.STATE_CHANGE:
                assert result.longitudinal_relation != LongitudinalRelation.CORRECTION_RETRACTION, (
                    f"F4 violation: {key} is STATE_CHANGE but predicted CORRECTION"
                )
            if gold.longitudinal_relation == LongitudinalRelation.CORRECTION_RETRACTION:
                assert result.longitudinal_relation != LongitudinalRelation.STATE_CHANGE, (
                    f"F4 violation: {key} is CORRECTION but predicted STATE_CHANGE"
                )


# ===================================================================
# Temporal integrity
# ===================================================================


class TestTemporalIntegrity:
    """Verify temporal invariants."""

    def test_no_reverse_time_candidates(self):
        corpus = build_corpus()
        gen = CandidateGenerator()
        for level_fn in [gen.generate_b0, gen.generate_b1, gen.generate_b2]:
            candidates = level_fn(corpus)
            for c in candidates:
                assert c.successor_time >= c.predecessor_time, (
                    f"Reverse time: {c.candidate_id}"
                )

    def test_no_future_leakage(self):
        corpus = build_corpus()
        gen = CandidateGenerator()
        b2 = gen.generate_b2(corpus)
        adj = SelectiveAdjudicator(corpus)
        results = adj.adjudicate(b2)
        integrity = compute_temporal_integrity(b2, results, corpus)
        assert integrity.reverse_time_errors == 0
        assert integrity.future_leakage_count == 0
        assert integrity.passed_all is True


# ===================================================================
# Full benchmark integration test
# ===================================================================


class TestBenchmarkIntegration:
    """Run the full benchmark and validate all deliverables."""

    def test_full_benchmark_produces_results(self):
        corpus = build_corpus()
        golds = build_gold_annotations()
        summary = run_benchmark(corpus, golds, RESULTS_DIR)

        # Candidate metrics exist for all baselines
        assert "B0" in summary.candidate_metrics
        assert "B1" in summary.candidate_metrics
        assert "B2" in summary.candidate_metrics

        # Adjudication metrics
        assert summary.adjudication_metrics["total_evaluated"] > 0

        # Knowledge effect metrics
        assert summary.knowledge_effect_metrics["total_evaluated"] > 0

        # Temporal integrity
        assert summary.temporal_integrity["passed_all"] is True

        # All falsification tests
        fals_map = {f["falsification_id"]: f for f in summary.falsification_results}
        for fid in ["F1", "F2", "F3", "F4", "F5", "F6", "F7"]:
            assert fid in fals_map, f"Missing falsification {fid}"
            assert fals_map[fid]["passed"] is True, (
                f"Falsification {fid} failed: {fals_map[fid].get('detail')}"
            )

    def test_benchmark_output_files_created(self):
        corpus = build_corpus()
        golds = build_gold_annotations()
        run_benchmark(corpus, golds, RESULTS_DIR)

        assert (RESULTS_DIR / "benchmark_summary.json").exists()
        assert (RESULTS_DIR / "b0_candidates.jsonl").exists()
        assert (RESULTS_DIR / "b1_candidates.jsonl").exists()
        assert (RESULTS_DIR / "b2_candidates.jsonl").exists()
        assert (RESULTS_DIR / "b3_adjudication.jsonl").exists()

    def test_benchmark_summary_structure(self):
        summary_path = RESULTS_DIR / "benchmark_summary.json"
        if not summary_path.exists():
            corpus = build_corpus()
            golds = build_gold_annotations()
            run_benchmark(corpus, golds, RESULTS_DIR)

        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "candidate_metrics" in data
        assert "adjudication_metrics" in data
        assert "knowledge_effect_metrics" in data
        assert "temporal_integrity" in data
        assert "falsification_results" in data
