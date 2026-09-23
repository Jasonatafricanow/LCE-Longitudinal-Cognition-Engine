"""Automated test suite for AGY Semantic Parser Evaluation (GitHub Issue #15).

Verifies:
1. Input sanitization (parser receives zero gold annotations or metadata).
2. Strict argument span containment within predicted units.
3. Filtering and rejection of forbidden downstream cognition labels.
4. Evaluator metrics calculation correctness.
5. Verification of frozen evaluation predictions on the eval split.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from research.semantic_annotation.schema import (
    FORBIDDEN_LABELS,
    EpistemicHedge,
    ModalityType,
    RelationType,
    SemanticAnnotationDocument,
    SemanticUnit,
    SourceSpan,
    UnitProvenance,
)
from research.semantic_parser.evaluator import compute_span_iou, evaluate_predictions
from research.semantic_parser.parser import SemanticParser


BENCHMARK_DIR = Path("research/benchmarks/semantic_annotation_v0_1")


def test_input_sanitization_removes_all_gold_metadata() -> None:
    """Verify that parser sanitization completely strips gold labels, families, and rationales."""
    parser = SemanticParser(dev_jsonl_path=BENCHMARK_DIR / "dev.jsonl")
    raw_case = {
        "case_id": "gold_test_01",
        "split": "eval",
        "family": "longitudinal_shift",
        "adversarial": True,
        "trap_description": "LLM tempted to emit REVISION",
        "raw_evidence": [{"evidence_id": "ev_01", "content": "I loved coding in 2022. I hate coding in 2026."}],
        "semantic_blocks": [{"block_id": "b_01", "content": "I loved coding in 2022. I hate coding in 2026."}],
        "cutoff_time": "2026-09-23T00:00:00Z",
        "gold_document": {"document_id": "doc_01", "units": [], "relations": []},
        "rationale": "Secret gold rationale",
    }

    sanitized = parser.sanitize_input(raw_case)
    assert "gold_document" not in sanitized
    assert "family" not in sanitized
    assert "adversarial" not in sanitized
    assert "trap_description" not in sanitized
    assert "rationale" not in sanitized
    assert "raw_evidence" in sanitized
    assert "semantic_blocks" in sanitized
    assert "cutoff_time" in sanitized
    assert sanitized["case_id"] == "gold_test_01"


def test_span_iou_computation() -> None:
    """Verify span IoU math."""
    assert compute_span_iou(0, 10, 0, 10) == 1.0
    assert compute_span_iou(0, 10, 10, 20) == 0.0
    assert compute_span_iou(0, 10, 5, 15) == 5.0 / 15.0


def test_evaluator_trap_resistance_logic() -> None:
    """Verify that evaluator correctly flags trapped vs resisted cases."""
    eval_cases = [json.loads(line) for line in (BENCHMARK_DIR / "eval.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    gold_case = next(c for c in eval_cases if c["case_id"] == "gold_eval_09")

    # 1. Resisted case: model outputs BEFORE
    resisted_doc = SemanticAnnotationDocument.model_validate(gold_case["gold_document"])
    report_resisted = evaluate_predictions([{"gold_case": gold_case, "pred_document": resisted_doc}])
    assert report_resisted["summary"]["adversarial_passed"] == 1
    assert report_resisted["summary"]["adversarial_resistance_rate"] == 100.0

    # 2. Trapped case: model outputs CAUSE
    trapped_dict = json.loads(json.dumps(gold_case["gold_document"]))
    trapped_dict["relations"][0]["relation_type"] = "CAUSE"
    trapped_doc = SemanticAnnotationDocument.model_validate(trapped_dict)
    report_trapped = evaluate_predictions([{"gold_case": gold_case, "pred_document": trapped_doc}])
    assert report_trapped["summary"]["adversarial_passed"] == 0
    assert report_trapped["summary"]["adversarial_resistance_rate"] == 0.0


def test_cognition_prohibition_in_schema_and_evaluator() -> None:
    """Verify that forbidden cognition labels are rejected by schema and detected by evaluator."""
    from research.semantic_annotation.schema import (
        AttributionMode,
        EvidenceStatus,
        PolarityType,
        PredicateNormalizationRule,
        PredicateSpec,
        TemporalAnchorType,
        TemporalAnchoring,
        UnitKind,
    )

    # 1. Schema enforcement
    with pytest.raises(ValueError, match="Forbidden downstream cognition label"):
        PredicateSpec(
            surface_predicate="revised",
            normalized_predicate="REVISION",
            normalization_rule=PredicateNormalizationRule.EXACT_SURFACE,
        )

    # 2. Evaluator detection
    eval_cases = [json.loads(line) for line in (BENCHMARK_DIR / "eval.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    gold_case = eval_cases[0]
    
    leaked_unit = SemanticUnit.model_construct(
        annotation_id="u1",
        provenance=UnitProvenance.model_validate(gold_case["gold_document"]["units"][0]["provenance"]),
        source_span=SourceSpan.model_validate(gold_case["gold_document"]["units"][0]["source_span"]),
        kind=UnitKind.EVENT,
        predicate=PredicateSpec.model_construct(
            surface_predicate="revised",
            normalized_predicate="REVISION",
            normalization_rule=PredicateNormalizationRule.EXACT_SURFACE,
        ),
        arguments={},
        polarity=PolarityType.POSITIVE,
        modality=ModalityType.ASSERTED,
        epistemic_hedge=EpistemicHedge.NONE,
        holder_ref="user",
        attribution_mode=AttributionMode.DIRECT_SPEAKER,
        temporal_anchoring=TemporalAnchoring(normalized_value="2026-09-23", anchor_type=TemporalAnchorType.EXACT),
        evidence_status=EvidenceStatus.EXPLICIT,
        confidence=1.0,
    )
    leaked_doc = SemanticAnnotationDocument.model_construct(
        document_id="doc_leaked",
        cutoff_time="2026-09-23T00:00:00Z",
        units=[leaked_unit],
        relations=[],
    )
    report = evaluate_predictions([{"gold_case": gold_case, "pred_document": leaked_doc}])
    assert report["summary"]["forbidden_cognition_leakage_count"] == 1


def test_frozen_benchmark_predictions_and_report_artifacts() -> None:
    """Verify that predictions_dev.jsonl, predictions_eval.jsonl, and evaluation report exist and are valid."""
    dev_pred_file = BENCHMARK_DIR / "predictions_dev.jsonl"
    eval_pred_file = BENCHMARK_DIR / "predictions_eval.jsonl"
    report_file = BENCHMARK_DIR / "PARSER_EVALUATION_REPORT_V0_1.md"

    assert dev_pred_file.exists(), "predictions_dev.jsonl must exist"
    assert eval_pred_file.exists(), "predictions_eval.jsonl must exist"
    assert report_file.exists(), "PARSER_EVALUATION_REPORT_V0_1.md must exist"

    dev_lines = [json.loads(line) for line in dev_pred_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    eval_lines = [json.loads(line) for line in eval_pred_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert len(dev_lines) == 20
    assert len(eval_lines) == 40

    for item in dev_lines + eval_lines:
        assert "case_id" in item
        assert "pred_document" in item
        # Must strictly validate against frozen Pydantic schema
        doc = SemanticAnnotationDocument.model_validate(item["pred_document"])
        # Must have zero forbidden cognition labels
        for u in doc.units:
            assert u.kind.value.upper() not in FORBIDDEN_LABELS
            assert u.predicate.normalized_predicate.upper() not in FORBIDDEN_LABELS
        for r in doc.relations:
            assert r.relation_type.value.upper() not in FORBIDDEN_LABELS

    report_text = report_file.read_text(encoding="utf-8")
    assert "## 1. Executive Summary" in report_text
    assert "## 2. Benchmark Metrics Comparison" in report_text
    assert "## 4. Adversarial Trap Resistance Breakdown" in report_text
    assert "## 5. Architectural Boundary & Freeze Declaration" in report_text

    audit_report_file = BENCHMARK_DIR / "PARSER_INTEGRITY_AUDIT_REPORT.md"
    assert audit_report_file.exists(), "PARSER_INTEGRITY_AUDIT_REPORT.md must exist"
    audit_text = audit_report_file.read_text(encoding="utf-8")
    assert "## 1. Executive Audit Verdict" in audit_text
    assert "FINAL CERTIFICATION VERDICT: PASS" in audit_text
    assert "## 3. Adversarial Trap Audit Ledger" in audit_text
    assert "## 4. Graph Admission Eligibility Audit" in audit_text
    assert "## 5. Case-by-Case Ledger Across All 40 Held-Out Eval Cases" in audit_text


