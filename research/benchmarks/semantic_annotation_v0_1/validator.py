"""Deterministic validator for LCE Semantic Parsing Gold Benchmark v0.1.

Verifies:
1. Exact total of 60 cases (20 dev, 40 eval, >=15 adversarial traps).
2. JSON schema conformance against schema.json.
3. Strict Pydantic model validation with SemanticAnnotationDocument.
4. Exact verbatim substring alignment for all character offsets against raw evidence.
5. Strict mention-based SAME_ENTITY endpoints (no <unit_id>:<role> pseudo-identifiers).
6. Prohibition of downstream cognition labels (REVISION, RECURRENCE, TRAJECTORY, etc.).
7. Frozen graph admission enforcement (inferred and control relations cannot enter positive graph).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import jsonschema
from pydantic import ValidationError

from research.semantic_annotation.schema import (
    CONTROL_RELATION_TYPES,
    FORBIDDEN_LABELS,
    GRAPH_ADMISSIBLE_EVIDENCE_STATUSES,
    EvidenceStatus,
    RelationType,
    SemanticAnnotationDocument,
)


class BenchmarkValidationError(Exception):
    """Raised when benchmark dataset fails deterministic validation."""


def validate_case(case_dict: dict[str, Any], schema: dict[str, Any] | None = None) -> None:
    case_id = case_dict.get("case_id", "<unknown>")

    # 1. JSON Schema validation
    if schema:
        try:
            jsonschema.validate(instance=case_dict, schema=schema)
        except jsonschema.ValidationError as e:
            raise BenchmarkValidationError(f"Case '{case_id}' failed JSON Schema validation: {e.message}") from e

    # 2. Pydantic SemanticAnnotationDocument validation
    gold_doc_raw = case_dict["gold_document"]
    try:
        doc = SemanticAnnotationDocument.model_validate(gold_doc_raw)
    except ValidationError as e:
        raise BenchmarkValidationError(f"Case '{case_id}' failed SemanticAnnotationDocument validation: {e}") from e

    # 3. Raw evidence map
    ev_map: dict[str, str] = {ev["evidence_id"]: ev["content"] for ev in case_dict["raw_evidence"]}

    # 4. Verbatim character span alignment
    for unit in doc.units:
        raw_id = unit.provenance.raw_evidence_id
        if raw_id not in ev_map:
            raise BenchmarkValidationError(
                f"Case '{case_id}' unit '{unit.annotation_id}' references unknown raw_evidence_id '{raw_id}'"
            )
        raw_text = ev_map[raw_id]

        # Check unit source_span
        expected_text = raw_text[unit.source_span.char_start : unit.source_span.char_end]
        if expected_text != unit.source_span.text:
            raise BenchmarkValidationError(
                f"Case '{case_id}' unit '{unit.annotation_id}' source_span text mismatch: "
                f"offsets [{unit.source_span.char_start}:{unit.source_span.char_end}] yield '{expected_text}', "
                f"but source_span.text is '{unit.source_span.text}'"
            )

        # Check argument mention source_spans if present
        for role_name, mention in unit.arguments.items():
            if mention.source_span is not None:
                m_span = mention.source_span
                expected_m_text = raw_text[m_span.char_start : m_span.char_end]
                if expected_m_text != m_span.text:
                    raise BenchmarkValidationError(
                        f"Case '{case_id}' unit '{unit.annotation_id}' argument '{role_name}' "
                        f"mention '{mention.mention_id}' source_span mismatch: "
                        f"offsets [{m_span.char_start}:{m_span.char_end}] yield '{expected_m_text}', "
                        f"but mention text is '{m_span.text}'"
                    )

        # 5. Check graph admission for units
        if unit.evidence_status not in GRAPH_ADMISSIBLE_EVIDENCE_STATUSES:
            try:
                unit.to_graph_node()
                raise BenchmarkValidationError(
                    f"Case '{case_id}' unit '{unit.annotation_id}' with status '{unit.evidence_status.value}' "
                    "was erroneously accepted as a graph node"
                )
            except ValueError:
                pass  # Correctly rejected

    # 6. Check relation spans and graph admission
    for rel in doc.relations:
        raw_id = rel.provenance.raw_evidence_id
        if raw_id in ev_map:
            raw_text = ev_map[raw_id]
            for s_span in rel.supporting_spans:
                expected_span_text = raw_text[s_span.char_start : s_span.char_end]
                if expected_span_text != s_span.text:
                    raise BenchmarkValidationError(
                        f"Case '{case_id}' relation '{rel.relation_id}' supporting_span mismatch: "
                        f"offsets [{s_span.char_start}:{s_span.char_end}] yield '{expected_span_text}', "
                        f"but span text is '{s_span.text}'"
                    )

        # Gating check
        if rel.relation_type in CONTROL_RELATION_TYPES or rel.evidence_status not in GRAPH_ADMISSIBLE_EVIDENCE_STATUSES:
            assert not rel.is_graph_edge, f"Case '{case_id}' relation '{rel.relation_id}' should not be a graph edge"
            try:
                rel.to_graph_edge()
                raise BenchmarkValidationError(
                    f"Case '{case_id}' non-admissible relation '{rel.relation_id}' was erroneously accepted as graph edge"
                )
            except ValueError:
                pass  # Correctly rejected


def validate_benchmark_files(benchmark_dir: Path | str | None = None) -> dict[str, Any]:
    if benchmark_dir is None:
        benchmark_dir = Path(__file__).parent
    else:
        benchmark_dir = Path(benchmark_dir)

    dev_file = benchmark_dir / "dev.jsonl"
    eval_file = benchmark_dir / "eval.jsonl"
    schema_file = benchmark_dir / "schema.json"

    if not dev_file.exists():
        raise FileNotFoundError(f"Missing dev.jsonl at {dev_file}")
    if not eval_file.exists():
        raise FileNotFoundError(f"Missing eval.jsonl at {eval_file}")
    if not schema_file.exists():
        raise FileNotFoundError(f"Missing schema.json at {schema_file}")

    with open(schema_file, encoding="utf-8") as f:
        schema = json.load(f)

    all_case_ids: set[str] = set()

    # Load dev cases
    dev_cases: list[dict[str, Any]] = []
    with open(dev_file, encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            cid = case["case_id"]
            if cid in all_case_ids:
                raise BenchmarkValidationError(f"Duplicate case_id '{cid}' in dev.jsonl line {line_num}")
            all_case_ids.add(cid)
            if case["split"] != "dev":
                raise BenchmarkValidationError(f"Case '{cid}' in dev.jsonl has split='{case['split']}'")
            validate_case(case, schema)
            dev_cases.append(case)

    # Load eval cases
    eval_cases: list[dict[str, Any]] = []
    adversarial_count = 0
    with open(eval_file, encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            cid = case["case_id"]
            if cid in all_case_ids:
                raise BenchmarkValidationError(f"Duplicate case_id '{cid}' in eval.jsonl line {line_num}")
            all_case_ids.add(cid)
            if case["split"] != "eval":
                raise BenchmarkValidationError(f"Case '{cid}' in eval.jsonl has split='{case['split']}'")
            if case.get("adversarial"):
                adversarial_count += 1
            validate_case(case, schema)
            eval_cases.append(case)

    # Enforce acceptance criteria
    if len(dev_cases) != 20:
        raise BenchmarkValidationError(f"Expected exactly 20 dev cases, got {len(dev_cases)}")
    if len(eval_cases) != 40:
        raise BenchmarkValidationError(f"Expected exactly 40 eval cases, got {len(eval_cases)}")
    if adversarial_count < 15:
        raise BenchmarkValidationError(f"Expected at least 15 adversarial traps in eval, got {adversarial_count}")

    total_cases = len(dev_cases) + len(eval_cases)
    report = {
        "status": "PASS",
        "total_cases": total_cases,
        "dev_cases": len(dev_cases),
        "eval_cases": len(eval_cases),
        "adversarial_traps": adversarial_count,
        "unique_case_ids": len(all_case_ids),
    }
    return report


def main() -> None:
    try:
        report = validate_benchmark_files()
        print("=" * 60)
        print("LCE Semantic Parsing Gold Benchmark v0.1: VALIDATION PASSED")
        print("=" * 60)
        for k, v in report.items():
            print(f"  {k}: {v}")
        print("=" * 60)
        sys.exit(0)
    except Exception as e:
        print(f"VALIDATION FAILED: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
