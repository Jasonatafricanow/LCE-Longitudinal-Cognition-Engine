"""Tests for Issue #24: Time-First Longitudinal Relations Above SemanticBlock."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
import pytest

from lce.cognition.longitudinal_relation import (
    LongitudinalCandidate,
    LongitudinalObservation,
    LongitudinalRelationType,
    compute_block_content_hash,
)
from lce.reference_memory.contracts import SemanticBlock
from research.experiments.longitudinal_relations_issue_24.candidate_generator import CandidateGenerator
from research.experiments.longitudinal_relations_issue_24.contracts import (
    CorpusBlockRecord,
    GoldRelationRecord,
)
from research.experiments.longitudinal_relations_issue_24.falsification_tests import FalsificationSuite


def test_relation_enum_values():
    assert LongitudinalRelationType.UNCERTAINTY_RESOLUTION == "UNCERTAINTY_RESOLUTION"
    assert LongitudinalRelationType.STATE_CHANGE == "STATE_CHANGE"
    assert LongitudinalRelationType.CORRECTION_RETRACTION == "CORRECTION_RETRACTION"
    assert LongitudinalRelationType.PERSISTENCE_CONFIRMATION == "PERSISTENCE_CONFIRMATION"
    assert LongitudinalRelationType.UNRELATED == "UNRELATED"
    assert LongitudinalRelationType.UNKNOWN_RELATION == "UNKNOWN_RELATION"


def test_temporal_authority_invariant():
    t_early = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
    t_late = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)

    # Valid candidate
    cand = LongitudinalCandidate(
        candidate_id="cand_01",
        predecessor_block_id="b1",
        successor_block_id="b2",
        predecessor_time=t_early,
        successor_time=t_late,
        signals=("temporal_precedence",),
        filter_level="L0",
    )
    assert cand.candidate_id == "cand_01"

    # Temporal violation: successor precedes predecessor
    with pytest.raises(ValueError, match="Temporal violation"):
        LongitudinalCandidate(
            candidate_id="cand_inv",
            predecessor_block_id="b1",
            successor_block_id="b2",
            predecessor_time=t_late,
            successor_time=t_early,
            signals=("temporal_precedence",),
            filter_level="L0",
        )


def test_observation_contract():
    obs = LongitudinalObservation(
        observation_id="obs_01",
        predecessor_block_id="b1",
        successor_block_id="b2",
        time_order_valid=True,
        relation_type=LongitudinalRelationType.STATE_CHANGE,
        affected_dimension="schedule_time",
        prior_unknown_resolved=False,
        outcome_or_current_state="Rescheduled to Wednesday",
        evidence_spans=("改到周三",),
    )
    d = obs.as_dict()
    assert d["relation_type"] == "STATE_CHANGE"
    assert d["time_order_valid"] is True
    assert d["affected_dimension"] == "schedule_time"


def test_benchmark_data_and_falsification_suite():
    data_dir = Path(__file__).resolve().parents[2] / "research" / "experiments" / "longitudinal_relations_issue_24" / "data"
    results_dir = Path(__file__).resolve().parents[2] / "research" / "experiments" / "longitudinal_relations_issue_24" / "results"

    summary_file = results_dir / "benchmark_summary.json"
    assert summary_file.exists(), "Benchmark summary results must exist"

    with open(summary_file, "r", encoding="utf-8") as f:
        summary = json.load(f)

    # 1. Candidate formation metrics
    cand_tot = summary["candidate_metrics"]["total"]
    assert cand_tot["L2"]["reduction_pct"] > 70.0, "L2 candidate reduction must exceed 70%"
    assert cand_tot["L2"]["recall"] >= 0.95, "L2 true relation recall must be at least 95%"

    # 2. Adjudication metrics
    adj_dev = summary["adjudication_metrics"]["dev"]
    adj_ho = summary["adjudication_metrics"]["held_out"]

    assert adj_dev["overall_accuracy"] >= 0.90, "Dev overall accuracy must be >= 90%"
    assert adj_ho["overall_accuracy"] >= 0.90, "Held-out overall accuracy must be >= 90%"

    # F4: Confusion between state change and correction must be 0%
    assert adj_dev["state_vs_correction_confusion_rate"] == 0.0, "Dev state vs correction confusion must be 0%"
    assert adj_ho["state_vs_correction_confusion_rate"] == 0.0, "Held-out state vs correction confusion must be 0%"

    # 3. Falsification results
    fals_map = {fr["falsification_id"]: fr for fr in summary["falsification_results"]}
    for f_id in ["F1", "F2", "F3", "F4", "F5"]:
        assert f_id in fals_map, f"Falsification {f_id} must be evaluated"
        assert fals_map[f_id]["passed"] is True, f"Falsification {f_id} must pass"
