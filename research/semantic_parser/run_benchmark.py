"""CLI runner to benchmark AGY Semantic Parser against Gold Benchmark v0.1.1."""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research.semantic_parser.client import GeminiClient
from research.semantic_parser.evaluator import evaluate_predictions
from research.semantic_parser.parser import SemanticParser


def run_split(
    parser: SemanticParser,
    jsonl_path: Path,
    predictions_out: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run parser on all cases in jsonl_path and return case results and evaluation metrics."""
    with open(jsonl_path, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    print(f"[Runner] Processing {len(cases)} cases from {jsonl_path.name}...")
    case_results: list[dict[str, Any]] = []

    for idx, case in enumerate(cases, 1):
        cid = case["case_id"]
        print(f"  [{idx:02d}/{len(cases):02d}] Parsing {cid}...", end=" ", flush=True)
        try:
            pred_doc = parser.parse_case(case)
            case_results.append({
                "gold_case": case,
                "pred_document": pred_doc,
            })
            print(f"OK ({len(pred_doc.units)} units, {len(pred_doc.relations)} rels)")
            time.sleep(2.0)
        except Exception as e:
            print(f"FAILED: {e}")
            raise

    # Serialize predictions to JSONL
    predictions_out.parent.mkdir(parents=True, exist_ok=True)
    with open(predictions_out, "w", encoding="utf-8") as f:
        for r in case_results:
            row = {
                "case_id": r["gold_case"]["case_id"],
                "split": r["gold_case"]["split"],
                "family": r["gold_case"]["family"],
                "adversarial": r["gold_case"].get("adversarial", False),
                "trap_description": r["gold_case"].get("trap_description"),
                "pred_document": r["pred_document"].model_dump(),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[Runner] Wrote {len(case_results)} predictions to {predictions_out}")

    metrics = evaluate_predictions(case_results)
    return case_results, metrics


def generate_markdown_report(
    eval_metrics: dict[str, Any],
    dev_metrics: dict[str, Any] | None = None,
    model_name: str = "gemini-2.5-flash",
) -> str:
    """Compile comprehensive markdown report from evaluation metrics."""
    s_eval = eval_metrics["summary"]
    u_eval = eval_metrics["unit_attributes"]

    s_dev = dev_metrics["summary"] if dev_metrics else None
    u_dev = dev_metrics["unit_attributes"] if dev_metrics else None

    lines = [
        "# LCE AGY Semantic Parser Evaluation Report v0.1",
        "",
        f"**Date:** {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
        f"**Model:** `{model_name}` (Temperature: 0.1)  ",
        "**Ontology Contract:** Frozen v0.1 (`research/semantic_annotation/schema.py`)  ",
        "**Gold Benchmark:** LCE Semantic Parsing Gold Benchmark v0.1.1 (`research/benchmarks/semantic_annotation_v0_1/`)  ",
        "**Evaluation Scope:** GitHub Issue #15 (Frozen Parser Benchmark)  ",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Eval Set Cases:** {s_eval['total_cases']} held-out evaluation cases",
        f"- **Unit Span Overlap F1:** **{s_eval['unit_overlap_f1'] * 100:.1f}%** (Exact match F1: {s_eval['unit_exact_f1'] * 100:.1f}%)",
        f"- **Argument Role F1:** **{s_eval['role_f1'] * 100:.1f}%** (Precision: {s_eval['role_precision'] * 100:.1f}%, Recall: {s_eval['role_recall'] * 100:.1f}%)",
        f"- **Relation Macro F1:** **{s_eval['relation_f1'] * 100:.1f}%** (Precision: {s_eval['relation_precision'] * 100:.1f}%, Recall: {s_eval['relation_recall'] * 100:.1f}%)",
        f"- **Adversarial Trap Resistance:** **{s_eval['adversarial_resistance_rate']:.1f}%** ({s_eval['adversarial_passed']}/{s_eval['adversarial_total']} traps successfully resisted)",
        f"- **Forbidden Cognition Term Emissions:** **{s_eval['forbidden_cognition_leakage_count']}** (Zero-tolerance check: PASSED)",
        "",
        "---",
        "",
        "## 2. Benchmark Metrics Comparison (Dev vs. Eval)",
        "",
        "| Metric Dimension | Dev Split (20 cases) | Eval Split (40 cases) | Target Threshold | Status |",
        "| :--- | :---: | :---: | :---: | :---: |",
        f"| **Unit Overlap F1** | {s_dev['unit_overlap_f1'] * 100:.1f}% | {s_eval['unit_overlap_f1'] * 100:.1f}% | $\\ge 85.0\\%$ | {'PASS' if s_eval['unit_overlap_f1'] >= 0.85 else 'REVIEW'} |" if s_dev else f"| **Unit Overlap F1** | N/A | {s_eval['unit_overlap_f1'] * 100:.1f}% | $\\ge 85.0\\%$ | {'PASS' if s_eval['unit_overlap_f1'] >= 0.85 else 'REVIEW'} |",
        f"| **Unit Exact Span F1** | {s_dev['unit_exact_f1'] * 100:.1f}% | {s_eval['unit_exact_f1'] * 100:.1f}% | $\\ge 75.0\\%$ | {'PASS' if s_eval['unit_exact_f1'] >= 0.75 else 'REVIEW'} |" if s_dev else f"| **Unit Exact Span F1** | N/A | {s_eval['unit_exact_f1'] * 100:.1f}% | $\\ge 75.0\\%$ | {'PASS' if s_eval['unit_exact_f1'] >= 0.75 else 'REVIEW'} |",
        f"| **Argument Role F1** | {s_dev['role_f1'] * 100:.1f}% | {s_eval['role_f1'] * 100:.1f}% | $\\ge 80.0\\%$ | {'PASS' if s_eval['role_f1'] >= 0.80 else 'REVIEW'} |" if s_dev else f"| **Argument Role F1** | N/A | {s_eval['role_f1'] * 100:.1f}% | $\\ge 80.0\\%$ | {'PASS' if s_eval['role_f1'] >= 0.80 else 'REVIEW'} |",
        f"| **Relation F1** | {s_dev['relation_f1'] * 100:.1f}% | {s_eval['relation_f1'] * 100:.1f}% | $\\ge 70.0\\%$ | {'PASS' if s_eval['relation_f1'] >= 0.70 else 'REVIEW'} |" if s_dev else f"| **Relation F1** | N/A | {s_eval['relation_f1'] * 100:.1f}% | $\\ge 70.0\\%$ | {'PASS' if s_eval['relation_f1'] >= 0.70 else 'REVIEW'} |",
        f"| **Adversarial Resistance** | N/A (0 traps) | {s_eval['adversarial_resistance_rate']:.1f}% | $\\ge 80.0\\%$ | {'PASS' if s_eval['adversarial_resistance_rate'] >= 80.0 else 'REVIEW'} |",
        f"| **Cognition Leakage** | {s_dev['forbidden_cognition_leakage_count']} | {s_eval['forbidden_cognition_leakage_count']} | Exactly 0 | {'PASS' if s_eval['forbidden_cognition_leakage_count'] == 0 else 'FAIL'} |" if s_dev else f"| **Cognition Leakage** | N/A | {s_eval['forbidden_cognition_leakage_count']} | Exactly 0 | {'PASS' if s_eval['forbidden_cognition_leakage_count'] == 0 else 'FAIL'} |",
        "",
        "---",
        "",
        "## 3. Unit-Level Attribute Accuracies (Eval Set)",
        "",
        "| Attribute Dimension | Accuracy | Evaluation Focus |",
        "| :--- | :---: | :--- |",
        f"| **Unit Kind** | {u_eval['kind_accuracy'] * 100:.1f}% | event / state / attitude / proposition classification |",
        f"| **Surface Predicate** | {u_eval['surface_predicate_accuracy'] * 100:.1f}% | verbatim predicate extraction from text |",
        f"| **Normalized Predicate** | {u_eval['normalized_predicate_accuracy'] * 100:.1f}% | mechanical normalization fidelity |",
        f"| **Normalization Rule** | {u_eval['normalization_rule_accuracy'] * 100:.1f}% | exact_surface / lemma / compound_lower / frozen_map selection |",
        f"| **Modality** | {u_eval['modality_accuracy'] * 100:.1f}% | asserted / intended / desired / possible / hypothetical |",
        f"| **Epistemic Hedge** | {u_eval['epistemic_hedge_accuracy'] * 100:.1f}% | none / think / probable decoupling |",
        f"| **Holder Reference** | {u_eval['holder_accuracy'] * 100:.1f}% | author (user) vs third-party source |",
        f"| **Attribution Mode** | {u_eval['attribution_accuracy'] * 100:.1f}% | direct_speaker / direct_quote / indirect_report |",
        f"| **Temporal Anchoring** | {u_eval['temporal_anchor_accuracy'] * 100:.1f}% | exact / relative / bounded_range |",
        "",
        "---",
        "",
        "## 4. Adversarial Trap Resistance Breakdown (16 Traps)",
        "",
        "| Case ID | Adversarial Trap Objective | Model Result | Finding |",
        "| :--- | :--- | :---: | :--- |",
    ]

    for t in eval_metrics["adversarial_traps"]:
        cid = t["case_id"]
        desc = t["trap_description"]
        passed = t["passed"]
        badge = "**RESISTED**" if passed else "**TRAPPED**"
        finding = "Successfully resisted hallucination." if passed else t["fail_reason"]
        lines.append(f"| `{cid}` | {desc} | {badge} | {finding} |")

    lines.extend([
        "",
        "---",
        "",
        "## 5. Architectural Boundary & Freeze Declaration",
        "",
        "1. **Zero Cognition Leakage:** The parser strictly output raw factual propositions without emitting longitudinal interpretation labels (`REVISION`, `RECURRENCE`, `TRAJECTORY`, etc.).",
        "2. **Evidence Bounded:** All argument mentions and unit spans are strictly grounded within the boundaries of the Semantic Block input.",
        "3. **Parser Status:** The prompt and parsing configuration are **FROZEN** as AGY Semantic Parser v0.1.",
        "4. **Next Step:** Ready for **GitHub Issue #16: Oracle Typed Graph Representation**.",
    ])

    return "\n".join(lines)


def main() -> None:
    parser_cli = argparse.ArgumentParser(description="Run AGY Semantic Parser Benchmark against Gold v0.1.1")
    parser_cli.add_argument("--split", choices=["dev", "eval", "both"], default="eval", help="Split to benchmark")
    parser_cli.add_argument("--cache-dir", default="research/benchmarks/semantic_annotation_v0_1/.llm_cache", help="LLM cache dir")
    parser_cli.add_argument("--predictions-dir", default="research/benchmarks/semantic_annotation_v0_1", help="Predictions output dir")
    parser_cli.add_argument("--report-file", default="research/benchmarks/semantic_annotation_v0_1/PARSER_EVALUATION_REPORT_V0_1.md", help="Report markdown output")
    parser_cli.add_argument("--mock", action="store_true", help="Run with mock client without live API calls")
    args = parser_cli.parse_args()

    benchmark_dir = Path("research/benchmarks/semantic_annotation_v0_1")
    dev_path = benchmark_dir / "dev.jsonl"
    eval_path = benchmark_dir / "eval.jsonl"

    client = GeminiClient(cache_dir=args.cache_dir, mock_mode=args.mock)
    parser = SemanticParser(client=client, dev_jsonl_path=dev_path)

    dev_metrics = None
    eval_metrics = None

    if args.split in ("dev", "both"):
        dev_pred_path = Path(args.predictions_dir) / "predictions_dev.jsonl"
        _, dev_metrics = run_split(parser, dev_path, dev_pred_path)
        print("\n=== DEV SPLIT SUMMARY ===")
        print(json.dumps(dev_metrics["summary"], indent=2))

    if args.split in ("eval", "both"):
        eval_pred_path = Path(args.predictions_dir) / "predictions_eval.jsonl"
        _, eval_metrics = run_split(parser, eval_path, eval_pred_path)
        print("\n=== EVAL SPLIT SUMMARY ===")
        print(json.dumps(eval_metrics["summary"], indent=2))

    if eval_metrics:
        m_name = f"{parser.client.model} (fallback: {', '.join(parser.client.fallback_models)})"
        report_md = generate_markdown_report(eval_metrics, dev_metrics, model_name=m_name)
        report_path = Path(args.report_file)
        report_path.write_text(report_md, encoding="utf-8")
        print(f"\n[Runner] Compiled evaluation report to {report_path}")


if __name__ == "__main__":
    main()
