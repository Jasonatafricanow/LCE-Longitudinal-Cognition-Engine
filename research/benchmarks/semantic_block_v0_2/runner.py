"""Shared-input v0.2 runner for B, C, and E.

The dry-run path validates that all routes can use the same candidate input
and adjudicated gold without constructing an LLM client or starting an
experiment. The normal path is an explicit model run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from research.benchmarks.semantic_block_v0_1.adapters.arm_b_one_pass import ArmBOnePassAdapter
from research.benchmarks.semantic_block_v0_1.adapters.arm_b_one_pass import SYSTEM_PROMPT as B_SYSTEM_PROMPT
from research.benchmarks.semantic_block_v0_1.adapters.arm_c_recom import ArmCRecommendedAdapter
from research.benchmarks.semantic_block_v0_1.adapters.arm_c_recom import LINKER_SYSTEM_PROMPT as C_LINKER_PROMPT
from research.benchmarks.semantic_block_v0_1.adapters.arm_c_recom import PROPOSAL_SYSTEM_PROMPT as C_PROPOSAL_PROMPT
from research.benchmarks.semantic_block_v0_1.adapters.base import prepare_visible_input
from research.benchmarks.semantic_block_v0_1.consumer.raw_hidden import RawHiddenConsumer
from research.benchmarks.semantic_block_v0_1.llm_client import DEFAULT_SEED, DEFAULT_TEMP, EMBEDDING_MODEL, MODEL_NAME, embed_texts
from research.benchmarks.semantic_block_v0_1.scorer.metrics import score_cutoff_prediction

from research.benchmarks.semantic_block_v0_2.f8_evaluator import evaluate_f8_probe_v02
from research.benchmarks.semantic_block_v0_2.route_e import LINKER_SYSTEM_PROMPT as E_LINKER_PROMPT
from research.benchmarks.semantic_block_v0_2.route_e import SYSTEM_PROMPT as E_SYSTEM_PROMPT
from research.benchmarks.semantic_block_v0_2.route_e import RouteEAdapter


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUTS = ROOT / "candidate_cases.jsonl"
DEFAULT_PROBES = ROOT / "F8_PROBES.jsonl"
DEFAULT_GOLD = Path(r"C:\projects\semantic_block_v0_2_adjudication\gold_v0_2.jsonl")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _route_input(case: dict[str, Any], cutoff: str):
    # The frozen B/C adapter interface requires these legacy metadata labels;
    # neither is included in their model prompts.
    adapted = {
        **case,
        "family": "V02",
        "variant": "single",
        "split": "v0.2",
    }
    return prepare_visible_input(adapted, cutoff)


def _gold_compatibility_view(gold_case: dict[str, Any]) -> dict[str, Any]:
    """Expose the v0.2 gold through the unchanged legacy scorer field names."""
    states = []
    for state in gold_case["states"]:
        states.append({
            **state,
            "state_key": state["state_id"],
            "available_at": state["state_available_at"],
            "entity_status": state["entity_resolution_status"],
        })
    relations = []
    for relation in gold_case["relations"]:
        relations.append({
            **relation,
            "source_state_key": relation["source_state_id"],
            "target_state_key": relation["target_state_id"],
        })
    visibility = [
        {
            **entry,
            "visible_state_keys": list(entry["visible_state_ids"]),
        }
        for entry in gold_case["visibility"]
    ]
    return {**gold_case, "states": states, "relations": relations, "visibility": visibility}


def validate_shared_inputs(
    input_path: Path,
    gold_path: Path,
    probe_path: Path,
) -> dict[str, Any]:
    inputs = _load_jsonl(input_path)
    gold = _load_jsonl(gold_path)
    probes = _load_jsonl(probe_path)
    input_by_id = {case["case_id"]: case for case in inputs}
    gold_by_id = {case["case_id"]: case for case in gold}
    if len(input_by_id) != len(inputs) or len(gold_by_id) != len(gold):
        raise ValueError("duplicate case_id in input or gold JSONL")
    if set(input_by_id) != set(gold_by_id):
        raise ValueError("candidate inputs and gold must contain the same case IDs")
    cutoff_pairs = 0
    for case_id, case in input_by_id.items():
        gold_case = gold_by_id[case_id]
        scorer_view = _gold_compatibility_view(gold_case)
        if any("state_key" not in state or "available_at" not in state or "entity_status" not in state for state in scorer_view["states"]):
            raise ValueError(f"gold compatibility view is incomplete for {case_id}")
        if any("source_state_key" not in relation or "target_state_key" not in relation for relation in scorer_view["relations"]):
            raise ValueError(f"gold relation compatibility view is incomplete for {case_id}")
        if case["requested_cutoffs"] != gold_case["requested_cutoffs"]:
            raise ValueError(f"requested cutoffs differ for {case_id}")
        cutoff_pairs += len(case["requested_cutoffs"])
        for cutoff in case["requested_cutoffs"]:
            _route_input(case, cutoff)
            if not any(v["cutoff"] == cutoff for v in gold_case["visibility"]):
                raise ValueError(f"gold visibility missing {case_id} at {cutoff}")
    for probe in probes:
        if probe["case_id"] not in gold_by_id:
            raise ValueError(f"probe case missing from gold: {probe['case_id']}")
        gold_case = gold_by_id[probe["case_id"]]
        gold_ids = {state["state_id"] for state in gold_case["states"]}
        referenced = {
            probe["gold_seed_state_key"],
            *probe.get("relevant_gold_endpoint_keys", []),
            *probe.get("temporal_distractor_keys", []),
        }
        for pair in probe.get("required_directed_cause_edge_pairs", []):
            referenced.update(pair)
        for pair in probe.get("forbidden_direct_shortcuts", []):
            referenced.update(pair)
        if not referenced <= gold_ids:
            raise ValueError(f"probe state keys absent from gold: {probe['probe_id']} {sorted(referenced - gold_ids)}")
        visibility = next((v for v in gold_case["visibility"] if v["cutoff"] == probe["cutoff"]), None)
        if visibility is None:
            raise ValueError(f"probe cutoff missing from gold visibility: {probe['probe_id']}")
        visible_gold_ids = set(visibility["visible_state_ids"])
        if not referenced <= visible_gold_ids:
            raise ValueError(f"probe references states not visible at its cutoff: {probe['probe_id']} {sorted(referenced - visible_gold_ids)}")
        for temporal in probe.get("unresolved_temporal_relation_pairs", []):
            if temporal["source_state_key"] not in gold_ids or temporal["target_state_key"] not in gold_ids:
                raise ValueError(f"unresolved temporal probe pair absent from gold: {probe['probe_id']}")
    return {
        "case_count": len(inputs),
        "cutoff_pair_count": cutoff_pairs,
        "probe_count": len(probes),
        "arms": ["B", "C", "E"],
        "input_sha256": _sha256(input_path),
        "gold_sha256": _sha256(gold_path),
        "probe_sha256": _sha256(probe_path),
        "b_e_first_pass_prompt_sha256_match": hashlib.sha256(B_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
        == hashlib.sha256(E_SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
    }


def _execute(
    input_path: Path,
    gold_path: Path,
    probe_path: Path,
    output_dir: Path,
    cache_dir: Path,
) -> dict[str, Any]:
    inputs = _load_jsonl(input_path)
    gold_rows = _load_jsonl(gold_path)
    probes = _load_jsonl(probe_path)
    input_by_id = {case["case_id"]: case for case in inputs}
    gold_by_id = {case["case_id"]: case for case in gold_rows}
    gold_legacy = {cid: _gold_compatibility_view(case) for cid, case in gold_by_id.items()}
    adapters = {
        "B": ArmBOnePassAdapter(cache_dir=cache_dir),
        "C": ArmCRecommendedAdapter(cache_dir=cache_dir),
        "E": RouteEAdapter(cache_dir=cache_dir),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    run_manifest = {
        "input_sha256": _sha256(input_path),
        "gold_sha256": _sha256(gold_path),
        "probe_sha256": _sha256(probe_path),
        "arms": ["B", "C", "E"],
        "gold_path": str(gold_path.resolve()),
        "score_criteria": "unchanged semantic_block_v0_1 scorer compatibility view",
        "model": MODEL_NAME,
        "embedding_model": EMBEDDING_MODEL,
        "seed": DEFAULT_SEED,
        "temperature": DEFAULT_TEMP,
        "prompt_sha256": {
            "B_semantic": hashlib.sha256(B_SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
            "C_semantic": hashlib.sha256(C_PROPOSAL_PROMPT.encode("utf-8")).hexdigest(),
            "C_linker": hashlib.sha256(C_LINKER_PROMPT.encode("utf-8")).hexdigest(),
            "E_semantic_equals_B": hashlib.sha256(E_SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
            "E_linker": hashlib.sha256(E_LINKER_PROMPT.encode("utf-8")).hexdigest(),
        },
        "route_source_sha256": {
            "B": _sha256(ROOT.parent / "semantic_block_v0_1" / "adapters" / "arm_b_one_pass.py"),
            "C": _sha256(ROOT.parent / "semantic_block_v0_1" / "adapters" / "arm_c_recom.py"),
            "E": _sha256(ROOT / "route_e.py"),
            "F8_v0_2": _sha256(ROOT / "f8_evaluator.py"),
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")
    results: dict[str, Any] = {}

    for arm_id, adapter in adapters.items():
        predictions: list[dict[str, Any]] = []
        scores: list[dict[str, Any]] = []
        e_traces: list[dict[str, Any]] = []
        prediction_index: dict[tuple[str, str], Any] = {}
        for case in inputs:
            for cutoff in case["requested_cutoffs"]:
                case_input = _route_input(case, cutoff)
                if arm_id == "E":
                    prediction, trace = adapter.compile_with_trace(case_input)
                    e_traces.append(trace.to_dict())
                else:
                    prediction = adapter.compile(case_input)
                prediction_index[(case["case_id"], cutoff)] = prediction
                predictions.append(prediction.to_dict())
                consumer = RawHiddenConsumer(prediction)
                score = score_cutoff_prediction(
                    prediction,
                    gold_legacy[case["case_id"]],
                    cutoff,
                    consumer,
                )
                scores.append(asdict(score))

        (output_dir / f"{arm_id}_predictions.json").write_text(
            json.dumps(predictions, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (output_dir / f"{arm_id}_scores.json").write_text(
            json.dumps(scores, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        if e_traces:
            (output_dir / "E_gate_trace.json").write_text(
                json.dumps(e_traces, indent=2, ensure_ascii=False), encoding="utf-8"
            )

        arm_f8: list[dict[str, Any]] = []
        for probe in probes:
            prediction = prediction_index.get((probe["case_id"], probe["cutoff"]))
            if prediction is None:
                continue
            blocks = prediction.blocks
            vectors = embed_texts([block.canonical_content for block in blocks], cache_dir=cache_dir / "embeddings")
            embeddings = {block.state_id: vector for block, vector in zip(blocks, vectors, strict=True)}
            visible_evidence = _route_input(input_by_id[probe["case_id"]], probe["cutoff"])
            evidence = [*visible_evidence.context_evidence, *visible_evidence.visible_evidence]
            result = evaluate_f8_probe_v02(
                prediction,
                gold_by_id[probe["case_id"]],
                probe,
                embeddings,
                evidence,
            )
            arm_f8.append(result.to_dict())
        (output_dir / f"{arm_id}_F8.json").write_text(
            json.dumps(arm_f8, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        results[arm_id] = {"prediction_count": len(predictions), "score_count": len(scores), "f8_count": len(arm_f8)}
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or compatibility-check SemanticBlock v0.2 B/C/E against one gold file.")
    parser.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--probes", type=Path, default=DEFAULT_PROBES)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results_v0_2")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".cache" / "v0_2")
    parser.add_argument("--dry-run", action="store_true", help="Validate shared input/gold compatibility; make no model or embedding calls.")
    args = parser.parse_args()
    manifest = validate_shared_inputs(args.inputs, args.gold, args.probes)
    if args.dry_run:
        print(json.dumps({"status": "COMPATIBILITY_OK", **manifest}, indent=2))
        return
    result = _execute(args.inputs, args.gold, args.probes, args.output_dir, args.cache_dir)
    print(json.dumps({"status": "RUN_COMPLETE", "arms": result, "gold_sha256": manifest["gold_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
