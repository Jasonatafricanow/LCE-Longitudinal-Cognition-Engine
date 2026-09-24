"""Validate v0.2 candidate inputs and A/B blank packets; never read or emit gold."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKET_FILES = (
    "CASES.jsonl", "ANNOTATIONS_BLANK.jsonl", "ANNOTATOR_INSTRUCTIONS.md",
    "ANNOTATION_TEMPLATE.json", "SEMANTIC_BLOCK_DEFINITION.md",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jsonl(path: Path) -> list[dict]:
    raw = path.read_bytes()
    require(raw.endswith(b"\n") and b"\r" not in raw, f"{path}: expected LF JSONL")
    return [json.loads(line) for line in raw.decode("utf-8").splitlines()]


def timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, f"timezone required: {value}")
    return parsed


def check() -> None:
    cases = jsonl(ROOT / "candidate_cases.jsonl")
    mapping = jsonl(ROOT / "operator_scenario_map.jsonl")
    require(len(cases) == 24 and len(mapping) == 24, "expected 24 cases and scenario-map rows")
    ids = [c["case_id"] for c in cases]
    require(ids == [f"V2-{i:03d}" for i in range(1, 25)], "opaque case IDs changed")
    require([r["case_id"] for r in mapping] == ids, "scenario-map order mismatch")
    families = Counter(r["scenario_family"] for r in mapping)
    require(len(families) == 12 and all(n == 2 for n in families.values()), "expected 12 two-case families")
    require(all(r["split"] == "unseen_evaluation" for r in mapping), "unseen split changed")
    old_root = ROOT.parent / "semantic_block_v0_1"
    old_texts = {
        e["content"] for split in ("dev", "heldout")
        for old in jsonl(old_root / f"{split}_cases.jsonl")
        for e in old["raw_evidence"]
    }
    for c in cases:
        require(set(c) == {"case_id", "raw_evidence", "requested_cutoffs",
                           "context_evidence_ids", "entity_registry"}, f"{c['case_id']}: leaked label")
        evidence = {e["evidence_id"]: e for e in c["raw_evidence"]}
        require(evidence and len(evidence) == len(c["raw_evidence"]), f"{c['case_id']}: evidence IDs")
        require(set(c["context_evidence_ids"]) <= set(evidence), f"{c['case_id']}: context refs")
        require(c["requested_cutoffs"] and len(set(c["requested_cutoffs"])) == len(c["requested_cutoffs"]),
                f"{c['case_id']}: cutoffs")
        cutoffs = [timestamp(t) for t in c["requested_cutoffs"]]
        require(cutoffs == sorted(cutoffs), f"{c['case_id']}: cutoff order")
        for e in evidence.values():
            require(e["content"] and e["speaker"] and e["source_id"] and e["thread_id"],
                    f"{c['case_id']}: empty source")
            require(e["content"] not in old_texts, f"{c['case_id']}: v0.1 source text reused")
            timestamp(e["occurred_at"])
            timestamp(e["available_at"])
        require(any(timestamp(e["available_at"]) <= cutoffs[-1] for e in evidence.values()),
                f"{c['case_id']}: no cutoff-visible evidence")

    top = json.loads((ROOT / "INPUT_PACKET_HASHES.json").read_text(encoding="utf-8"))
    require(top["status"] == "INPUTS_ONLY_NO_GOLD", "packet status changed")
    for rel, expected in top["sha256"].items():
        require(hash_file(ROOT / rel) == expected, f"hash mismatch: {rel}")
    require(set(top["sha256"]) == {
        "candidate_cases.jsonl", "operator_scenario_map.jsonl",
        *(f"annotation_packets/annotator_{a}/{name}" for a in ("A", "B")
          for name in (*PACKET_FILES, "PACKET_SHA256.json")),
    }, "top hash inventory mismatch")

    packet_orders = []
    for annotator in ("A", "B"):
        packet = ROOT / "annotation_packets" / f"annotator_{annotator}"
        p_cases = jsonl(packet / "CASES.jsonl")
        p_blank = jsonl(packet / "ANNOTATIONS_BLANK.jsonl")
        require({json.dumps(x, sort_keys=True) for x in p_cases} ==
                {json.dumps(x, sort_keys=True) for x in cases}, f"{annotator}: case mismatch")
        order = [r["case_id"] for r in p_cases]
        packet_orders.append(order)
        require([r["case_id"] for r in p_blank] == order, f"{annotator}: blank order mismatch")
        for row in p_blank:
            require(row["annotator_id"] == annotator and row["status"] == "UNSTARTED",
                    f"{annotator}: blank status")
            require(not any(row[k] for k in ("states", "relations", "visibility",
                                             "explicit_exclusions", "uncertainties",
                                             "block_only_checks", "free_notes")),
                    f"{annotator}: prefilled annotation")
        own = json.loads((packet / "PACKET_SHA256.json").read_text(encoding="utf-8"))
        require(own["status"] == "INPUTS_ONLY_NO_GOLD" and own["annotator"] == annotator,
                f"{annotator}: packet manifest")
        require(set(own["sha256"]) == set(PACKET_FILES), f"{annotator}: packet inventory")
        for name, expected in own["sha256"].items():
            require(hash_file(packet / name) == expected, f"{annotator}: hash mismatch {name}")
        require("v0.1" not in (packet / "CASES.jsonl").read_text(encoding="utf-8"),
                f"{annotator}: old benchmark text in cases")
    require(packet_orders[0] != packet_orders[1], "A and B order should differ")
    require(not (ROOT / "gold_v0_2.jsonl").exists(), "gold must not exist at this stage")
    print("VALID INPUTS: 24 cases, 12 unseen families, A/B blank packets; no v0.2 gold")


if __name__ == "__main__":
    check()
