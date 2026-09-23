"""Validate the Issue #19 research corpus and its immutable file manifest.

This checks structural integrity and exact source coordinates. It cannot prove
semantic entailment or replace independent human annotation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
MANIFEST = ROOT / "FROZEN_MANIFEST.json"
FILES = [
    "research/benchmarks/semantic_block_v0_1/.gitattributes",
    "research/benchmarks/semantic_block_v0_1/build_frozen_corpus.py",
    "research/benchmarks/semantic_block_v0_1/validate_freeze.py",
    "research/benchmarks/semantic_block_v0_1/README.md",
    "research/benchmarks/semantic_block_v0_1/dev_cases.jsonl",
    "research/benchmarks/semantic_block_v0_1/dev_gold.jsonl",
    "research/benchmarks/semantic_block_v0_1/heldout_cases.jsonl",
    "research/benchmarks/semantic_block_v0_1/heldout_gold.jsonl",
    "docs/research/semantic-block/.gitattributes",
    "docs/research/semantic-block/ISSUE_19_FROZEN_EXECUTION_PROTOCOL.md",
    "docs/research/semantic-block/ISSUE_19_AGY_EXECUTION_ORDER.md",
]
VARIANTS = {"C": "canonical", "P": "paraphrase", "N": "negative"}
HELDOUT = {"B03", "B04", "B05", "B07", "B08", "B11", "B13", "B14", "B15", "B16", "B17", "B18"}
STATE_FIELDS = {
    "state_key", "block_key", "canonical_content", "predicate", "kind",
    "participants", "holder", "utterer", "attribution_mode", "polarity",
    "modality", "epistemic_hedge", "valid_time", "time_precision",
    "entity_status", "uncertainty", "independent_support_count",
    "available_at", "source_spans",
}


def fail(message: str) -> None:
    raise ValueError(message)


def instant(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"invalid timestamp {value!r}") from exc
    if parsed.tzinfo is None:
        fail(f"timezone required: {value!r}")
    return parsed


def rows(name: str) -> list[dict]:
    path = ROOT / name
    data = path.read_bytes()
    if not data.endswith(b"\n") or b"\r" in data:
        fail(f"{name}: expected LF-terminated UTF-8 JSONL")
    return [json.loads(line) for line in data.decode("utf-8").splitlines()]


def check_span(span: dict, evidence: dict[str, dict], where: str) -> None:
    if set(span) != {"evidence_id", "char_start", "char_end", "text"}:
        fail(f"{where}: malformed span")
    ref = span["evidence_id"]
    if ref not in evidence:
        fail(f"{where}: missing evidence {ref}")
    start, end = span["char_start"], span["char_end"]
    content = evidence[ref]["content"]
    if not isinstance(start, int) or not isinstance(end, int) or not (0 <= start < end <= len(content)):
        fail(f"{where}: invalid coordinates")
    if content[start:end] != span["text"]:
        fail(f"{where}: source text mismatch")


def check() -> tuple[int, int]:
    all_cases: dict[str, dict] = {}
    all_gold: dict[str, dict] = {}
    for split, expected_count in (("dev", 42), ("heldout", 12)):
        cases = rows(f"{split}_cases.jsonl")
        gold = rows(f"{split}_gold.jsonl")
        if len(cases) != expected_count or len(gold) != expected_count:
            fail(f"{split}: expected {expected_count} paired rows")
        if [row["case_id"] for row in cases] != [row["case_id"] for row in gold]:
            fail(f"{split}: case/gold order mismatch")
        for case, answer in zip(cases, gold):
            cid = case["case_id"]
            if cid in all_cases or cid in all_gold:
                fail(f"duplicate case {cid}")
            all_cases[cid], all_gold[cid] = case, answer
            if case["split"] != split or answer["case_id"] != cid:
                fail(f"{cid}: split or pairing mismatch")
            family, code = cid.split("-")
            if case["family"] != family or case["variant"] != VARIANTS.get(code):
                fail(f"{cid}: family/variant mismatch")
            expected_split = "heldout" if family in HELDOUT and code == "N" else "dev"
            if split != expected_split:
                fail(f"{cid}: split allocation mismatch")
            if answer["annotation_status"] != "single_author_frozen_unadjudicated":
                fail(f"{cid}: annotation provenance changed")
            evidence = {e["evidence_id"]: e for e in case["raw_evidence"]}
            if len(evidence) != len(case["raw_evidence"]) or not evidence:
                fail(f"{cid}: missing or duplicate Raw Evidence")
            for e in evidence.values():
                for key in ("content", "speaker", "source_id", "thread_id"):
                    if not isinstance(e[key], str) or not e[key]:
                        fail(f"{cid}: empty evidence {key}")
                instant(e["occurred_at"])
                instant(e["available_at"])
            if not set(case["context_evidence_ids"]) <= set(evidence):
                fail(f"{cid}: unrecognized context evidence")
            if not case["requested_cutoffs"] or len(set(case["requested_cutoffs"])) != len(case["requested_cutoffs"]):
                fail(f"{cid}: missing or repeated cutoff")
            for cutoff in case["requested_cutoffs"]:
                instant(cutoff)
            if not isinstance(case["entity_registry"], dict):
                fail(f"{cid}: invalid entity registry")

            states = answer["states"]
            if not states or len({s["state_key"] for s in states}) != len(states):
                fail(f"{cid}: missing or repeated state key")
            state_by_key = {s["state_key"]: s for s in states}
            latest_availability: dict[str, datetime] = {}
            for state in states:
                if not STATE_FIELDS <= set(state):
                    fail(f"{cid}: missing state fields {STATE_FIELDS - set(state)}")
                if not state["canonical_content"] or not state["predicate"] or not state["kind"]:
                    fail(f"{cid}: empty meaning field")
                if not isinstance(state["participants"], dict) or not state["participants"]:
                    fail(f"{cid}: missing roles")
                if not state["source_spans"] or state["independent_support_count"] < 1:
                    fail(f"{cid}: missing support")
                for span in state["source_spans"]:
                    check_span(span, evidence, f"{cid}/{state['state_key']}")
                earliest = max(instant(evidence[s["evidence_id"]]["available_at"])
                               for s in state["source_spans"])
                available = instant(state["available_at"])
                if available < earliest:
                    fail(f"{cid}: state precedes supporting evidence")
                block = state["block_key"]
                if block in latest_availability and available <= latest_availability[block]:
                    fail(f"{cid}: non-increasing state version availability")
                latest_availability[block] = available
            for relation in answer["relations"]:
                if relation["type"] not in {"CAUSE", "SAME_ENTITY", "BEFORE"}:
                    fail(f"{cid}: unsupported relation type")
                if relation["source_state_key"] not in state_by_key or relation["target_state_key"] not in state_by_key:
                    fail(f"{cid}: orphan relation endpoint")
                if relation["source_state_key"] == relation["target_state_key"]:
                    fail(f"{cid}: self relation")
                if relation["traversal"] != (relation["type"] in {"CAUSE", "SAME_ENTITY"}):
                    fail(f"{cid}: illegal traversal policy")
                cue = relation["cue_span"]
                if cue is not None:
                    check_span(cue, evidence, f"{cid}/relation")
                elif relation["basis"] != "authorized_registry":
                    fail(f"{cid}: missing relation cue")
            if [v["cutoff"] for v in answer["visibility"]] != case["requested_cutoffs"]:
                fail(f"{cid}: visibility cutoffs mismatch")
            for visibility in answer["visibility"]:
                cutoff = instant(visibility["cutoff"])
                latest: dict[str, str] = {}
                for state in states:
                    if instant(state["available_at"]) <= cutoff:
                        latest[state["block_key"]] = state["state_key"]
                if visibility["visible_state_keys"] != list(latest.values()):
                    fail(f"{cid}: future leak or stale state at {visibility['cutoff']}")
            if not isinstance(answer["forbidden_case_outputs"], list) or not answer["rationale"]:
                fail(f"{cid}: missing negative control or rationale")
    expected_ids = {f"B{i:02d}-{code}" for i in range(1, 19) for code in VARIANTS}
    if set(all_cases) != expected_ids:
        fail(f"corpus coverage mismatch: {expected_ids ^ set(all_cases)}")
    if Counter(c["family"] for c in all_cases.values()) != {f"B{i:02d}": 3 for i in range(1, 19)}:
        fail("family count mismatch")
    return len(all_cases), sum(c["split"] == "heldout" for c in all_cases.values())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(write: bool) -> str:
    hashes = {name: sha256(REPO / name) for name in FILES}
    if write:
        record = {
            "benchmark_id": "semantic_block_v0_1",
            "issue": "https://github.com/Jasonatafricanow/LCE-Longitudinal-Cognition-Engine/issues/19",
            "source_head_before_freeze": "a9450a50c0c1bb665ae58b509647b6b364d23b2a",
            "frozen_on": "2026-09-24",
            "hash_algorithm": "sha256",
            "case_count": 54,
            "dev_count": 42,
            "heldout_count": 12,
            "gold_status": "single_author_frozen_unadjudicated",
            "files": hashes,
        }
        MANIFEST.write_text(json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                            encoding="utf-8", newline="\n")
    else:
        record = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if record["files"] != hashes or record["case_count"] != 54 or record["heldout_count"] != 12:
            fail("manifest hash/count mismatch: freeze has changed")
    return sha256(MANIFEST)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-manifest", action="store_true", help="freeze once after review")
    args = parser.parse_args()
    total, heldout = check()
    digest = manifest(args.write_manifest)
    print(f"VALID: {total} cases, {heldout} heldout; manifest SHA256 {digest}")
