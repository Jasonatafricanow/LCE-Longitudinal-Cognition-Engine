from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from lce.reference_memory.contracts import RawEvidence
from lce.semantic.compiler import SemanticCompiler
from lce.testing.reference_memory import InMemoryReferenceMemory

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))

ALLOWED_SPEECH_ACTS = {"assertion", "question", "directive"}
ALLOWED_POLARITY = {"positive", "negative", "unknown"}
ALLOWED_EPISTEMIC = {"asserted", "planned", "uncertain", "hypothetical", "counterfactual", "reported", "unknown"}
ALLOWED_TEMPORAL = {"past", "current", "future", "atemporal", "unknown"}


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def _validate_candidate(case: dict) -> dict[str, bool]:
    raw_ids = {item["evidence_id"] for item in case["raw"]}
    req = case["requirements"]
    candidate = case["candidate"]
    blocks = candidate["blocks"]
    relations = candidate["relations"]
    block_ids = {block["local_id"] for block in blocks}

    checks: dict[str, bool] = {}
    checks["decomposition"] = len(blocks) == req["block_count"]
    checks["source_grounding"] = all(
        block["source_refs"]
        and set(block["source_refs"]) <= raw_ids
        and block["canonical_meaning"].strip()
        for block in blocks
    )
    checks["typed_operators"] = all(
        block["speech_act"] in ALLOWED_SPEECH_ACTS
        and block["polarity"] in ALLOWED_POLARITY
        and block["epistemic_status"] in ALLOWED_EPISTEMIC
        and block["temporal"]["kind"] in ALLOWED_TEMPORAL
        and 0.0 <= float(block["confidence"]) <= 1.0
        for block in blocks
    )
    checks["required_speech_acts"] = set(req["speech_acts"]) <= {block["speech_act"] for block in blocks}
    checks["required_epistemic"] = set(req["epistemic"]) <= {block["epistemic_status"] for block in blocks}
    checks["required_temporal"] = set(req["temporal_kinds"]) <= {block["temporal"]["kind"] for block in blocks}
    checks["ambiguity_discipline"] = sum(len(block["unresolved_refs"]) for block in blocks) == req["unresolved_refs"]

    relation_types = {rel["relation"] for rel in relations}
    checks["required_relations"] = set(req["relation_types"]) <= relation_types
    checks["relation_grounding"] = all(
        rel["from"] in block_ids
        and rel["to"] in block_ids
        and rel["source_refs"]
        and set(rel["source_refs"]) <= raw_ids
        and 0.0 <= float(rel["confidence"]) <= 1.0
        for rel in relations
    )
    return checks


def _legacy_baseline(case: dict) -> dict[str, object]:
    store = InMemoryReferenceMemory()
    compiler = SemanticCompiler(
        store,
        None,
        lineage_id="legacy-" + case["id"],
        compiler_version="experiment-legacy-stream-v1",
    )
    for index, raw in enumerate(case["raw"], start=1):
        compiler.process(
            RawEvidence(
                evidence_id=raw["evidence_id"],
                content=raw["text"],
                occurred_at=_utc(raw["occurred_at"]),
                known_at=_utc(raw["occurred_at"]),
                ordering_key=f"{index:04d}",
                provenance={"source": "semantic-compilation-experiment", "canonical": True},
            )
        )
    blocks = store.list_semantic_blocks(current_valid_only=False)
    metadata_keys = set().union(*(set(block.metadata) for block in blocks)) if blocks else set()
    return {
        "block_count": len(blocks),
        "decomposition_matches": len(blocks) == case["requirements"]["block_count"],
        "has_typed_semantics": bool(
            {"speech_act", "polarity", "epistemic_status", "temporal"} & metadata_keys
        ),
        "relation_count": 0,
        "raw_source_coverage": sorted(
            {eid for block in blocks for eid in block.raw_evidence_ids}
        ) == sorted(item["evidence_id"] for item in case["raw"]),
        "contents": [block.content for block in blocks],
    }


def main() -> None:
    all_checks: Counter[str] = Counter()
    total = 0
    legacy_decomposition = 0
    legacy_typed = 0
    legacy_relation_cases = 0
    legacy_source = 0
    details = []

    for case in MANIFEST["cases"]:
        checks = _validate_candidate(case)
        if not all(checks.values()):
            failed = [name for name, passed in checks.items() if not passed]
            raise SystemExit(f"{case['id']}: candidate protocol failed checks: {failed}")
        all_checks.update({name: int(passed) for name, passed in checks.items()})
        total += 1

        legacy = _legacy_baseline(case)
        legacy_decomposition += int(legacy["decomposition_matches"])
        legacy_typed += int(legacy["has_typed_semantics"])
        legacy_relation_cases += int(
            not case["requirements"]["relation_types"] or legacy["relation_count"] > 0
        )
        legacy_source += int(legacy["raw_source_coverage"])
        details.append(
            {
                "case": case["id"],
                "candidate_blocks": len(case["candidate"]["blocks"]),
                "legacy_blocks": legacy["block_count"],
                "legacy_decomposition_matches": legacy["decomposition_matches"],
                "legacy_contents": legacy["contents"],
            }
        )

    report = {
        "schema_version": MANIFEST["schema_version"],
        "cases": total,
        "candidate_protocol_checks": dict(all_checks),
        "candidate_all_checks_pass": all(value == total for value in all_checks.values()),
        "legacy_current_compiler": {
            "decomposition_match_cases": legacy_decomposition,
            "typed_semantic_cases": legacy_typed,
            "relation_requirement_cases_satisfied": legacy_relation_cases,
            "source_coverage_cases": legacy_source,
        },
        "details": details,
        "interpretation": {
            "candidate_claim": "The proposition-centric contract can represent the frozen adversarial cases without losing source grounding, logical operators, time, correction relations, or explicit ambiguity.",
            "legacy_claim": "The current BLOCK-03 compiler is a stream/boundary mechanism. Its reference provider preserves source provenance but does not implement the missing Raw Evidence -> typed semantic proposition compilation layer.",
            "not_claimed": "This run does not validate production AGY semantic quality, real embeddings, or downstream LCE structure quality."
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
