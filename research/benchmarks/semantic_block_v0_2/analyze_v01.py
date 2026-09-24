"""Read-only differential audit of the local v0.1 B/C run and cached C proposals.

No model calls, fixture edits, or v0.1 report rewrites. The output is a derived
audit aid; inspect source evidence before making semantic entailment claims.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from research.benchmarks.semantic_block_v0_1.adapters.arm_c_recom import PROPOSAL_SYSTEM_PROMPT
from research.benchmarks.semantic_block_v0_1.adapters.base import prepare_visible_input
from research.benchmarks.semantic_block_v0_1.contracts import PublicSemanticBlock
from research.benchmarks.semantic_block_v0_1.llm_client import DEFAULT_SEED, DEFAULT_TEMP, MODEL_NAME
from research.benchmarks.semantic_block_v0_1.scorer.alignment import align_states


V01 = Path(__file__).resolve().parent.parent / "semantic_block_v0_1"
RESULTS = V01 / "results"
FIELDS = (
    "canonical_content", "predicate", "kind", "participants", "holder", "utterer",
    "attribution_mode", "polarity", "modality", "epistemic_hedge", "valid_time",
    "time_precision", "entity_status", "uncertainty",
)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def cache_key(prompt: str, instruction: str) -> str:
    digest = hashlib.sha256()
    for chunk in (MODEL_NAME, str(DEFAULT_SEED), str(DEFAULT_TEMP), instruction, prompt):
        digest.update(chunk.encode("utf-8"))
    return digest.hexdigest()


def proposal(case: dict, cutoff: str) -> tuple[list[dict], str]:
    visible = prepare_visible_input(case, cutoff)
    prompt = json.dumps({
        "case_id": visible.case_id,
        "cutoff": visible.cutoff,
        "visible_evidence": visible.visible_evidence,
        "bounded_context": visible.context_evidence,
        "entity_registry": visible.entity_registry,
    }, indent=2, ensure_ascii=False)
    digest = cache_key(prompt, PROPOSAL_SYSTEM_PROMPT)
    path = V01 / ".cache" / f"{digest}.json"
    if not path.exists():
        return [], "MISSING_CACHE"
    return json.loads(path.read_text(encoding="utf-8"))["content"].get("units", []), digest


def main() -> None:
    run_manifest = json.loads((RESULTS / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
    expected = run_manifest["source_hashes"]
    for key, rel in {
        "arm_b": "adapters/arm_b_one_pass.py",
        "arm_c": "adapters/arm_c_recom.py",
        "alignment": "scorer/alignment.py",
        "metrics": "scorer/metrics.py",
        "llm_client": "llm_client.py",
    }.items():
        actual = hashlib.sha256((V01 / rel).read_bytes()).hexdigest()
        if actual != expected[key]:
            raise ValueError(f"v0.1 source hash changed: {rel}")
    manifest_hash = hashlib.sha256((V01 / "FROZEN_MANIFEST.json").read_bytes()).hexdigest()
    if manifest_hash != run_manifest["frozen_manifest_sha256"]:
        raise ValueError("v0.1 benchmark manifest hash changed")
    details: list[dict] = []
    strict_f8: list[dict] = []
    for split in ("dev", "heldout"):
        cases = read_jsonl(V01 / f"{split}_cases.jsonl")
        scores = json.loads((RESULTS / f"{split}_scores.json").read_text(encoding="utf-8"))
        preds = json.loads((RESULTS / f"{split}_predictions.json").read_text(encoding="utf-8"))
        lookup_score = {(s["case_id"], s["cutoff"]): s for s in scores["B"]}
        lookup_score_c = {(s["case_id"], s["cutoff"]): s for s in scores["C"]}
        lookup_pred_b = {(p["case_id"], p["cutoff"]): p for p in preds["B"]}
        lookup_pred_c = {(p["case_id"], p["cutoff"]): p for p in preds["C"]}
        for case in cases:
            for cutoff in case["requested_cutoffs"]:
                key = case["case_id"], cutoff
                bscore, cscore = lookup_score[key], lookup_score_c[key]
                bpred, cpred = lookup_pred_b[key], lookup_pred_c[key]
                units, digest = proposal(case, cutoff)
                final_by_key = {b["state_id"].removeprefix(case["case_id"] + "_"): b for b in cpred["blocks"]}
                mutations: list[dict] = []
                dropped: list[dict] = []
                for unit in units:
                    state_key = str(unit.get("state_key", ""))
                    final = final_by_key.get(state_key)
                    if final is None:
                        dropped.append({
                            "state_key": state_key,
                            "canonical_content": unit.get("canonical_content"),
                            "source_spans": unit.get("source_spans", []),
                        })
                        continue
                    changed = {field: {"proposal": unit.get(field), "final": final.get(field)}
                               for field in FIELDS if unit.get(field) != final.get(field)}
                    if changed:
                        mutations.append({"state_key": state_key, "changed_fields": changed})
                field_delta = {
                    field: bscore["field_breakdown"][field]["correct"] - cscore["field_breakdown"][field]["correct"]
                    for field in bscore["field_breakdown"]
                }
                focused_trace = case["case_id"] in {
                    "B02-C", "B07-N", "B08-P", "B11-N", "B17-C", "B17-P", "B17-N"
                }
                details.append({
                    "split": split, "case_id": case["case_id"], "family": case["family"],
                    "cutoff": cutoff, "proposal_cache_key": digest,
                    "b_accuracy": bscore["accuracy"], "c_accuracy": cscore["accuracy"],
                    "b_minus_c_correct": bscore["required_fields_correct"] - cscore["required_fields_correct"],
                    "field_delta_b_minus_c": field_delta,
                    "b_blocks": bpred["blocks"] if focused_trace else [],
                    "c_proposal_units": units if focused_trace else [],
                    "c_blocks": cpred["blocks"] if focused_trace else [],
                    "c_relations": cpred["relations"] if focused_trace else [],
                    "gold_state_count": cscore["gold_state_count"],
                    "b_state_count": bscore["pred_state_count"],
                    "c_state_count": cscore["pred_state_count"],
                    "c_mutations": mutations, "c_dropped": dropped,
                    "b_hard_failures": bscore["hard_failures"],
                    "c_hard_failures": cscore["hard_failures"],
                })
                if case["family"] == "B17":
                    gold_map = {g["case_id"]: g for g in read_jsonl(V01 / f"{split}_gold.jsonl")}
                    gold = gold_map[case["case_id"]]
                    alignment = align_states(
                        [PublicSemanticBlock.from_dict(b) for b in cpred["blocks"]], gold["states"]
                    )
                    mapped_edges = []
                    for relation in cpred["relations"]:
                        src = alignment.pred_to_gold.get(relation["source_state_id"])
                        tgt = alignment.pred_to_gold.get(relation["target_state_id"])
                        mapped_edges.append({"type": relation["type"], "source_gold": src,
                                             "target_gold": tgt,
                                             "traversal_allowed": relation["traversal_allowed"]})
                    required = {("s4", "s5"), ("s5", "s6")} if case["variant"] != "negative" else set()
                    mapped_cause = {(e["source_gold"], e["target_gold"]) for e in mapped_edges
                                    if e["type"] == "CAUSE"}
                    strict_f8.append({
                        "case_id": case["case_id"],
                        "pred_to_gold": alignment.pred_to_gold,
                        "unmatched_gold": alignment.unmatched_golds,
                        "mapped_edges": mapped_edges,
                        "required_cause_edges": sorted(required),
                        "missing_cause_edges": sorted(required - mapped_cause),
                        "false_cause_edges": sorted(mapped_cause - required),
                        "before_traversable_count": sum(e["type"] == "BEFORE" and e["traversal_allowed"]
                                                        for e in mapped_edges),
                        "reported_seed_s4_id": f"{case['case_id']}_s4",
                        "reported_seed_s4_maps_to_gold": alignment.pred_to_gold.get(f"{case['case_id']}_s4"),
                        "strict_positive_path": bool(required and required <= mapped_cause),
                    })

    by_family: dict[str, dict] = defaultdict(lambda: {"b_correct": 0, "c_correct": 0,
                                                      "denominator": 0, "cutoffs": 0,
                                                      "dropped_units": 0, "semantic_field_mutations": 0})
    for row in details:
        bucket = by_family[row["family"]]
        bucket["b_correct"] += row["b_accuracy"] * 13 * row["gold_state_count"]
        bucket["c_correct"] += row["c_accuracy"] * 13 * row["gold_state_count"]
        bucket["denominator"] += 13 * row["gold_state_count"]
        bucket["cutoffs"] += 1
        bucket["dropped_units"] += len(row["c_dropped"])
        bucket["semantic_field_mutations"] += sum(len(m["changed_fields"]) for m in row["c_mutations"])
    output = {"source_run": "run_20260924_012403", "by_family": dict(sorted(by_family.items())),
              "case_cutoffs": details, "strict_f8": strict_f8}
    outpath = Path(__file__).with_name("v01_bc_audit.json")
    outpath.write_text(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                       encoding="utf-8", newline="\n")

    print("family Bcorrect Ccorrect total delta dropped mutations")
    for family, b in sorted(by_family.items()):
        print(f"{family:6} {b['b_correct']:8.0f} {b['c_correct']:8.0f} {b['denominator']:5} "
              f"{b['b_correct']-b['c_correct']:5.0f} {b['dropped_units']:7} {b['semantic_field_mutations']:9}")
    print("\nLargest B-over-C cutoff deltas:")
    for row in sorted(details, key=lambda r: r["b_minus_c_correct"], reverse=True)[:15]:
        print(row["case_id"], row["cutoff"], f"+{row['b_minus_c_correct']}",
              "B/C blocks", row["b_state_count"], row["c_state_count"],
              "C drops", len(row["c_dropped"]), "C mutations", len(row["c_mutations"]))
    print("\nStrict F8 against frozen gold:")
    for row in strict_f8:
        print(row["case_id"], "missing_gold", row["unmatched_gold"],
              "missing_edges", row["missing_cause_edges"],
              "seed_s4_maps_to", row["reported_seed_s4_maps_to_gold"],
              "path", row["strict_positive_path"])
    print(f"Wrote {outpath}")


if __name__ == "__main__":
    main()
