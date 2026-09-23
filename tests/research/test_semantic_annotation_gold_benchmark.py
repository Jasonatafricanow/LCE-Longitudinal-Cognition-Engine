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

    case_nested = next(c for c in cases if c.get("trap_description") and "modality=uncertain" in c["trap_description"])
    u = case_nested["gold_document"]["units"][0]
    assert u["modality"] == ModalityType.DESIRED.value
    assert u["epistemic_hedge"] == EpistemicHedge.THINK.value
    assert u["confidence"] == 1.0


def test_argument_spans_strictly_contained_in_unit_spans() -> None:
    """Verify that every argument mention's source span is strictly contained within its unit's span."""
    for split_file in ["dev.jsonl", "eval.jsonl"]:
        path = BENCHMARK_DIR / split_file
        with open(path, encoding="utf-8") as f:
            for line in f:
                case = json.loads(line)
                doc = case["gold_document"]
                for u in doc["units"]:
                    u_start = u["source_span"]["char_start"]
                    u_end = u["source_span"]["char_end"]
                    for role, arg in u["arguments"].items():
                        if arg.get("source_span"):
                            m_start = arg["source_span"]["char_start"]
                            m_end = arg["source_span"]["char_end"]
                            assert u_start <= m_start and m_end <= u_end, (
                                f"Case {case['case_id']} unit {u['annotation_id']} argument {role} "
                                f"[{m_start}:{m_end}] lies outside unit span [{u_start}:{u_end}]"
                            )


def test_same_entity_not_self_referential() -> None:
    """Verify that SAME_ENTITY relations never connect identical mention span offsets."""
    for split_file in ["dev.jsonl", "eval.jsonl"]:
        path = BENCHMARK_DIR / split_file
        with open(path, encoding="utf-8") as f:
            for line in f:
                case = json.loads(line)
                doc = case["gold_document"]
                mention_map = {
                    arg["mention_id"]: arg
                    for u in doc["units"]
                    for arg in u["arguments"].values()
                }
                for rel in doc["relations"]:
                    if rel["relation_type"] == "SAME_ENTITY":
                        src_m = mention_map[rel["source_id"]]
                        tgt_m = mention_map[rel["target_id"]]
                        if src_m.get("source_span") and tgt_m.get("source_span"):
                            s_span = src_m["source_span"]
                            t_span = tgt_m["source_span"]
                            assert not (s_span["char_start"] == t_span["char_start"] and s_span["char_end"] == t_span["char_end"]), (
                                f"Case {case['case_id']} SAME_ENTITY connects identical spans [{s_span['char_start']}:{s_span['char_end']}]"
                            )


def test_dev_split_covers_all_17_case_families() -> None:
    """Verify that the 20-case dev split contains representative examples of all 17 families."""
    dev_file = BENCHMARK_DIR / "dev.jsonl"
    with open(dev_file, encoding="utf-8") as f:
        cases = [json.loads(line) for line in f]

    dev_families = {c["family"] for c in cases}
    expected_families = {
        "asserted_vs_intended",
        "possible_vs_occurred",
        "holder_attribution",
        "evidence_status_distinction",
        "negation_scope",
        "multi_unit_decomposition",
        "same_entity_paraphrase",
        "same_event_vs_similar",
        "temporal_non_causal",
        "explicit_causality",
        "discourse_relations",
        "longitudinal_shift",
        "state_compatibility",
        "nested_attitude",
        "relative_temporal_anchoring",
        "ambiguous_relations",
        "no_relation_control",
    }
    assert dev_families == expected_families, f"Missing families in Dev: {expected_families - dev_families}"

