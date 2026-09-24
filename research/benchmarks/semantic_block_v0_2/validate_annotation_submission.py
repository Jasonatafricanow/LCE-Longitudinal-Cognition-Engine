"""Structural check for one independently completed v0.2 annotation file.

This reads only that annotator's packet and submission. It never opens the
other annotator's file, compiler predictions, v0.1 gold, or adjudicated gold.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATE_FIELDS = {
    "local_state_key", "local_block_key", "canonical_content", "predicate",
    "kind", "participants", "holder", "utterer", "attribution_mode",
    "polarity", "modality", "epistemic_hedge", "valid_time",
    "time_precision", "evidence_available_at", "state_available_at",
    "entity_resolution_status", "uncertainty", "independent_support_count",
    "support_status", "source_spans", "claim_support", "lineage_reason",
}


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"invalid timestamp {value!r}") from exc
    require(parsed.tzinfo is not None, f"timezone required: {value}")
    return parsed


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def check_span(span: dict, evidence: dict[str, dict], cid: str) -> None:
    require(set(span) == {"evidence_id", "char_start", "char_end", "text"},
            f"{cid}: span fields")
    eid = span["evidence_id"]
    require(eid in evidence, f"{cid}: unknown evidence {eid}")
    start, end = span["char_start"], span["char_end"]
    text = evidence[eid]["content"]
    require(isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text),
            f"{cid}: span coordinates")
    require(text[start:end] == span["text"], f"{cid}: nonexact span")


def check(path: Path, annotator: str) -> None:
    packet = ROOT / "annotation_packets" / f"annotator_{annotator}"
    cases = rows(packet / "CASES.jsonl")
    answers = rows(path)
    require(len(answers) == len(cases) == 24, "expected 24 completed rows")
    require([a["case_id"] for a in answers] == [c["case_id"] for c in cases],
            "annotation case order must match the assigned packet")
    for case, answer in zip(cases, answers):
        cid = case["case_id"]
        require(answer["annotator_id"] == annotator and answer["status"] == "COMPLETE",
                f"{cid}: incomplete/wrong annotator")
        evidence = {e["evidence_id"]: e for e in case["raw_evidence"]}
        states = answer["states"]
        require(states and len({s["local_state_key"] for s in states}) == len(states),
                f"{cid}: missing/duplicate state")
        by_key = {s["local_state_key"]: s for s in states}
        for state in states:
            require(STATE_FIELDS <= set(state), f"{cid}: missing fields {STATE_FIELDS - set(state)}")
            require(state["local_block_key"] and state["canonical_content"] and state["predicate"],
                    f"{cid}: incomplete meaning")
            require(isinstance(state["participants"], dict), f"{cid}: roles")
            require(state["independent_support_count"] >= 1, f"{cid}: support count")
            require(state["source_spans"] and state["claim_support"], f"{cid}: source support")
            for span in state["source_spans"]:
                check_span(span, evidence, cid)
            for claim in state["claim_support"]:
                require(claim["claim_text"] and claim["source_spans"], f"{cid}: unsupported subclaim")
                for span in claim["source_spans"]:
                    check_span(span, evidence, cid)
            latest_source = max(timestamp(evidence[sp["evidence_id"]]["available_at"])
                                for sp in state["source_spans"])
            evidence_at = timestamp(state["evidence_available_at"])
            state_at = timestamp(state["state_available_at"])
            require(evidence_at >= latest_source and state_at >= evidence_at,
                    f"{cid}: interpretation before source admission")
        for relation in answer["relations"]:
            require(relation["type"] in {"CAUSE", "SAME_ENTITY", "BEFORE"},
                    f"{cid}: unsupported public relation")
            source, target = relation["source_local_state_key"], relation["target_local_state_key"]
            require(source in by_key and target in by_key and source != target,
                    f"{cid}: relation endpoints")
            require(not (relation["type"] == "BEFORE" and relation["traversal_allowed"]),
                    f"{cid}: BEFORE bridge forbidden")
            for span in relation["cue_spans"]:
                check_span(span, evidence, cid)
            require(relation["basis"], f"{cid}: relation basis")
        require([v["cutoff"] for v in answer["visibility"]] == case["requested_cutoffs"],
                f"{cid}: visibility cutoffs")
        for view in answer["visibility"]:
            cutoff = timestamp(view["cutoff"])
            visible = view["visible_local_state_keys"]
            require(len(visible) == len(set(visible)) and set(visible) <= set(by_key),
                    f"{cid}: visibility IDs")
            for key in visible:
                state = by_key[key]
                require(timestamp(state["state_available_at"]) <= cutoff,
                        f"{cid}: future interpretation leak")
                require(all(timestamp(evidence[s["evidence_id"]]["available_at"]) <= cutoff
                            for s in state["source_spans"]), f"{cid}: future source leak")
            # A later state of one block supersedes its earlier state at this cutoff.
            for block_key in {s["local_block_key"] for s in states}:
                eligible = [s for s in states if s["local_block_key"] == block_key
                            and timestamp(s["state_available_at"]) <= cutoff]
                if eligible:
                    latest = max(eligible, key=lambda s: timestamp(s["state_available_at"]))
                    require(latest["local_state_key"] in visible,
                            f"{cid}: latest state absent at cutoff")
                    require(sum(by_key[k]["local_block_key"] == block_key for k in visible) == 1,
                            f"{cid}: multiple states of one block visible")
        require(isinstance(answer["explicit_exclusions"], list) and
                isinstance(answer["uncertainties"], list) and
                isinstance(answer["block_only_checks"], list), f"{cid}: missing review lists")
    print(f"VALID SUBMISSION: annotator {annotator}, {len(answers)} cases; semantic review still required")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("annotator", choices=("A", "B"))
    parser.add_argument("completed_file", type=Path)
    args = parser.parse_args()
    check(args.completed_file, args.annotator)
