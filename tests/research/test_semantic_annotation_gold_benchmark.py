"""Automated regression test suite for LCE Semantic Parsing Gold Benchmark v0.1 (GitHub Issue #14).

Validates:
- Full dataset integrity and split count (20 dev, 40 eval, >=15 adversarial traps).
- Verbatim character span alignment against raw evidence text.
- Stable mention IDs for SAME_ENTITY.
- Decoupled nested attitude semantics.
- Rejection of downstream cognition labels.
- Inferred and control label graph admission gating.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from research.semantic_annotation.schema import (
    FORBIDDEN_LABELS,
    EpistemicHedge,
    EvidenceStatus,
    ModalityType,
    RelationType,
    SemanticAnnotationDocument,
)
from research.benchmarks.semantic_annotation_v0_1.validator import (
    validate_benchmark_files,
    validate_case,
)

BENCHMARK_DIR = Path("research/benchmarks/semantic_annotation_v0_1")


def test_benchmark_overall_validation() -> None:
    """Run full deterministic validator and verify acceptance criteria."""
    report = validate_benchmark_files(BENCHMARK_DIR)
    assert report["status"] == "PASS"
    assert report["total_cases"] == 60
    assert report["dev_cases"] == 20
    assert report["eval_cases"] == 40
    assert report["adversarial_traps"] >= 15
    assert report["unique_case_ids"] == 60


def test_adversarial_traps_coverage() -> None:
    """Verify eval split contains at least 15 adversarial traps with explicit trap descriptions."""
    eval_file = BENCHMARK_DIR / "eval.jsonl"
    adversarial_cases = []
    with open(eval_file, encoding="utf-8") as f:
        for line in f:
            case = json.loads(line)
            if case.get("adversarial"):
                adversarial_cases.append(case)
                assert case.get("trap_description"), f"Case {case['case_id']} missing trap_description"

    assert len(adversarial_cases) >= 15, f"Expected >= 15 adversarial cases, found {len(adversarial_cases)}"


def test_source_spans_verbatim_alignment() -> None:
    """Verify that every source span in all 60 cases matches the exact slice in raw evidence."""
    for split_file in ["dev.jsonl", "eval.jsonl"]:
        path = BENCHMARK_DIR / split_file
        with open(path, encoding="utf-8") as f:
            for line in f:
                case = json.loads(line)
                raw_text = case["raw_evidence"][0]["content"]
                doc = case["gold_document"]

                for u in doc["units"]:
                    span = u["source_span"]
                    slice_text = raw_text[span["char_start"] : span["char_end"]]
                    assert slice_text == span["text"], f"Span mismatch in case {case['case_id']}"

                    for role_name, mention in u["arguments"].items():
                        if mention.get("source_span"):
                            m_span = mention["source_span"]
                            m_slice = raw_text[m_span["char_start"] : m_span["char_end"]]
                            assert m_slice == m_span["text"], (
                                f"Mention span mismatch in case {case['case_id']} argument {role_name}"
                            )


def test_same_entity_connects_stable_mention_ids() -> None:
    """Verify that all SAME_ENTITY relations connect stable mention IDs, never pseudo-identifiers."""
    for split_file in ["dev.jsonl", "eval.jsonl"]:
        path = BENCHMARK_DIR / split_file
        with open(path, encoding="utf-8") as f:
            for line in f:
                case = json.loads(line)
                doc = case["gold_document"]
                mention_ids = {
                    arg["mention_id"]
                    for u in doc["units"]
                    for arg in u["arguments"].values()
                }

                for rel in doc["relations"]:
                    if rel["relation_type"] == "SAME_ENTITY":
                        assert ":" not in rel["source_id"], (
                            f"Case {case['case_id']} SAME_ENTITY source_id contains pseudo-colon: {rel['source_id']}"
                        )
                        assert ":" not in rel["target_id"], (
                            f"Case {case['case_id']} SAME_ENTITY target_id contains pseudo-colon: {rel['target_id']}"
                        )
                        assert rel["source_id"] in mention_ids
                        assert rel["target_id"] in mention_ids


def test_prohibition_of_cognition_labels_across_all_cases() -> None:
    """Verify that zero downstream cognition labels appear anywhere in the gold benchmark."""
    for split_file in ["dev.jsonl", "eval.jsonl"]:
        path = BENCHMARK_DIR / split_file
        with open(path, encoding="utf-8") as f:
            for line in f:
                case = json.loads(line)
                doc = case["gold_document"]

                for u in doc["units"]:
                    assert u["kind"].upper() not in FORBIDDEN_LABELS
                    norm_pred = u["predicate"]["normalized_predicate"].upper()
                    for forbidden in FORBIDDEN_LABELS:
                        assert forbidden != norm_pred, f"Forbidden label {forbidden} found in unit predicate"

                for rel in doc["relations"]:
                    assert rel["relation_type"].upper() not in FORBIDDEN_LABELS


def test_nested_attitude_semantics_in_benchmark() -> None:
    """Verify that nested attitude cases preserve desire modality, epistemic_hedge, and confidence 1.0."""
    eval_file = BENCHMARK_DIR / "eval.jsonl"
    with open(eval_file, encoding="utf-8") as f:
        cases = [json.loads(line) for line in f]

    case_25 = next(c for c in cases if c["case_id"] == "gold_eval_25")
    u = case_25["gold_document"]["units"][0]
    assert u["modality"] == ModalityType.DESIRED.value
    assert u["epistemic_hedge"] == EpistemicHedge.THINK.value
    assert u["confidence"] == 1.0
