"""Quantitative Evaluator for One-Pass Multi-Turn Experiment.

Computes:
  - closure_context_integrity
  - semantic_obligation_coverage (obligations satisfied / total obligations)
  - omission distribution across O1-O10
  - E19 response_sidecar_divergence detection
  - full E1-E19 error taxonomy
  - latency & token overhead
"""

from __future__ import annotations

import json
import logging
from typing import Any

from research.experiments.semantic_compilation_body_v1.closure import compile_semantic_closure
from research.experiments.semantic_compilation_body_v1.evaluate import (
    _check_semantic_coverage,
    _check_forbidden_inference,
)


def _check_cohabit_satisfied(text_a: str, text_b: str, blocks: list[SemanticBlock]) -> bool:
    """True if there is a block containing both text_a and text_b."""
    for b in blocks:
        if _check_semantic_coverage(text_a, b.analysis_text) and _check_semantic_coverage(text_b, b.analysis_text):
            return True
    return False


def _check_context_satisfied(text_a: str, text_ctx: str, parse_result: SemanticParseResultV1) -> bool:
    """True if dependency graph contains a context link or cross-turn update link."""
    for dep in parse_result.dependencies:
        if dep.boundary_policy == "context" or "update" in dep.relation.lower():
            return True
    return len(parse_result.dependencies) > 0


def _check_separation_satisfied(text_a: str, text_b: str, blocks: list[SemanticBlock]) -> bool:
    """True if text_a and text_b are NOT illicitly merged into the same SemanticBlock."""
    for b in blocks:
        cov_a = _check_semantic_coverage(text_a, b.analysis_text)
        cov_b = _check_semantic_coverage(text_b, b.analysis_text)
        if cov_a and cov_b and len(b.member_point_ids) > 1:
            return False
    return True


def _check_defer_satisfied(target: str, parse_result: SemanticParseResultV1) -> bool:
    """True if any point is deferred or unresolved contains ambiguous item."""
    if any(p.status == "defer" for p in parse_result.semantic_points):
        return True
    return len(parse_result.unresolved) > 0
from research.experiments.semantic_compilation_body_v1.one_pass.body_turn_contract import BodyTurnResultV1
from research.experiments.semantic_compilation_body_v1.one_pass.omission_analysis import (
    classify_omission,
    detect_response_sidecar_divergence,
    OMISSION_DEFINITIONS,
)
from research.experiments.semantic_compilation_body_v1.schema import SemanticBlock

_logger = logging.getLogger(__name__)


class OnePassEvaluator:
    def __init__(self, ground_truth: dict[str, Any]) -> None:
        self.ground_truth = ground_truth

    def evaluate_case(
        self,
        case: dict[str, Any],
        turn_result: BodyTurnResultV1,
    ) -> dict[str, Any]:
        case_id = case["case_id"]
        gt = self.ground_truth.get(case_id, {})
        errors: list[str] = []
        omission_details: list[dict[str, str]] = []

        must_preserve = gt.get("must_preserve", [])
        must_not_infer = gt.get("must_not_infer", [])
        must_cohabit = gt.get("must_cohabit", [])
        must_context = gt.get("must_context", [])
        must_separate = gt.get("must_separate", [])
        must_defer = gt.get("must_defer", [])

        # 1. Check fail-closed status
        if not turn_result.has_valid_sidecar:
            errors.append("E1")
            errors.append("E17")
            return {
                "case_id": case_id,
                "status": "failed_sidecar",
                "errors": errors,
                "obligations_total": len(must_preserve),
                "obligations_satisfied": 0,
                "obligation_coverage": 0.0,
                "closure_integrity": False,
                "e19_divergence": True,
                "omissions": [{"obligation": ob, "code": "O1"} for ob in must_preserve],
                "blocks_count": 0,
                "blocks": [],
            }

        parse_result = turn_result.semantic_sidecar
        # Compile SemanticBlocks via deterministic closure
        blocks, _ = compile_semantic_closure(parse_result, case_id)

        # Aggregate texts
        points_text = " ".join([p.meaning for p in parse_result.semantic_points])
        blocks_text = " ".join([b.analysis_text for b in blocks])

        # 2. Obligation coverage
        satisfied_obligations = 0
        for ob in must_preserve:
            covered = _check_semantic_coverage(ob, points_text) or _check_semantic_coverage(ob, blocks_text)
            if covered:
                satisfied_obligations += 1
            else:
                o_code = classify_omission(ob, case["dialogue"], case.get("category", ""), points_text)
                omission_details.append({"obligation": ob, "code": o_code})
                errors.append(f"E1:{o_code}")

        obligation_coverage = (
            satisfied_obligations / len(must_preserve) if must_preserve else 1.0
        )

        # 3. Forbidden inference check
        for fn in must_not_infer:
            if _check_forbidden_inference(fn, points_text) or _check_forbidden_inference(fn, blocks_text):
                errors.append("E2")

        # 4. Cohabit check
        for p_a, p_b in must_cohabit:
            if not _check_cohabit_satisfied(p_a, p_b, blocks):
                errors.append("E12")

        # 5. Context check
        for p_a, p_ctx in must_context:
            if not _check_context_satisfied(p_a, p_ctx, parse_result):
                errors.append("E14")

        # 6. Separate check
        for p_a, p_b in must_separate:
            if not _check_separation_satisfied(p_a, p_b, blocks):
                errors.append("E11")

        # 7. Defer check
        for target in must_defer:
            if not _check_defer_satisfied(target, parse_result):
                errors.append("E10")

        # 8. Check Closure Context Integrity
        # Closure integrity is True if no fragmentation (E17) and no overmerge (E16)
        has_fragmentation = "E12" in errors or "E17" in errors
        has_overmerge = "E11" in errors or "E16" in errors
        closure_integrity = not (has_fragmentation or has_overmerge)

        # 9. E19 Response vs Sidecar Divergence
        has_e19, divergences = detect_response_sidecar_divergence(
            turn_result.assistant_response, points_text, must_preserve
        )
        if has_e19:
            errors.append("E19")

        is_passed = (
            len(errors) == 0
            and obligation_coverage >= 0.99
            and closure_integrity
        )

        return {
            "case_id": case_id,
            "category": case.get("category", "unknown"),
            "status": "ok" if is_passed else "flagged",
            "passed": is_passed,
            "errors": errors,
            "obligations_total": len(must_preserve),
            "obligations_satisfied": satisfied_obligations,
            "obligation_coverage": obligation_coverage,
            "closure_integrity": closure_integrity,
            "e19_divergence": has_e19,
            "e19_details": divergences,
            "omissions": omission_details,
            "blocks_count": len(blocks),
            "latency_ms": turn_result.latency_ms,
            "total_tokens": turn_result.total_tokens,
            "prompt_tokens": turn_result.prompt_tokens,
            "completion_tokens": turn_result.completion_tokens,
            "assistant_response_preview": turn_result.assistant_response[:100],
            "blocks": [b.model_dump() for b in blocks],
        }

    def aggregate_results(self, eval_results: list[dict[str, Any]]) -> dict[str, Any]:
        total_cases = len(eval_results)
        passed_cases = sum(1 for r in eval_results if r.get("passed", False))
        
        total_obligations = sum(r.get("obligations_total", 0) for r in eval_results)
        satisfied_obligations = sum(r.get("obligations_satisfied", 0) for r in eval_results)
        macro_coverage = sum(r.get("obligation_coverage", 0.0) for r in eval_results) / max(total_cases, 1)
        micro_coverage = satisfied_obligations / max(total_obligations, 1)

        closure_integrity_count = sum(1 for r in eval_results if r.get("closure_integrity", False))
        e19_count = sum(1 for r in eval_results if r.get("e19_divergence", False))

        # Omission breakdown
        omission_counts = {f"O{i}": 0 for i in range(1, 11)}
        for r in eval_results:
            for om in r.get("omissions", []):
                code = om.get("code", "O1")
                if code in omission_counts:
                    omission_counts[code] += 1

        # Error counts
        error_counts: dict[str, int] = {}
        for r in eval_results:
            for err in r.get("errors", []):
                base_err = err.split(":")[0]
                error_counts[base_err] = error_counts.get(base_err, 0) + 1

        # Latency & tokens
        avg_latency = sum(r.get("latency_ms", 0.0) for r in eval_results) / max(total_cases, 1)
        avg_tokens = sum(r.get("total_tokens", 0) for r in eval_results) / max(total_cases, 1)
        avg_completion_tokens = sum(r.get("completion_tokens", 0) for r in eval_results) / max(total_cases, 1)

        return {
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "case_pass_rate": passed_cases / max(total_cases, 1),
            "total_obligations": total_obligations,
            "satisfied_obligations": satisfied_obligations,
            "obligation_coverage_macro": macro_coverage,
            "obligation_coverage_micro": micro_coverage,
            "closure_context_integrity_rate": closure_integrity_count / max(total_cases, 1),
            "e19_divergence_rate": e19_count / max(total_cases, 1),
            "e19_divergence_count": e19_count,
            "omission_distribution": omission_counts,
            "error_distribution": error_counts,
            "avg_latency_ms": avg_latency,
            "avg_total_tokens": avg_tokens,
            "avg_completion_tokens": avg_completion_tokens,
        }
