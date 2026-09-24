"""Build v0.2 annotation INPUT packets only; never generate a gold answer.

All twelve scenario families are new relative to v0.1 and remain unseen by
route tuning. The packet case IDs are opaque; family labels are kept in the
operator-only manifest. Run once before annotation and record file hashes.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
DEFAULT_OCCURRED = "2026-05-01T12:00:00Z"
DEFAULT_AVAILABLE = "2026-05-02T12:00:00Z"
DEFAULT_CUTOFF = "2026-05-20T00:00:00Z"
CASES: list[dict] = []
SCENARIOS: list[dict] = []


def ev(content: str, *, occurred: str = DEFAULT_OCCURRED,
       available: str = DEFAULT_AVAILABLE, thread: str = "research-diary",
       speaker: str = "user", source: str = "synthetic-v02") -> dict:
    return {"content": content, "occurred_at": occurred, "available_at": available,
            "thread_id": thread, "speaker": speaker, "source_id": source}


def add(family: str, contrast: str, evidence: list[dict], *,
        cutoffs: list[str] | None = None, context_indices: tuple[int, ...] = (),
        registry: dict[str, str] | None = None) -> None:
    case_id = f"V2-{len(CASES) + 1:03d}"
    items = [{"evidence_id": f"{case_id}-E{i+1}", **item} for i, item in enumerate(evidence)]
    CASES.append({
        "case_id": case_id,
        "raw_evidence": items,
        "requested_cutoffs": cutoffs or [DEFAULT_CUTOFF],
        "context_evidence_ids": [items[i]["evidence_id"] for i in context_indices],
        "entity_registry": registry or {},
    })
    SCENARIOS.append({"case_id": case_id, "scenario_family": family,
                      "contrast_role": contrast, "split": "unseen_evaluation"})


# U01: nested report and shifting pronoun speaker, absent from v0.1's single quote cases.
add("U01_nested_report_chain", "a", [
    ev('Iris forwarded Niko\'s message: "Pavel says the north gate is open." Iris has not checked the gate.')])
add("U01_nested_report_chain", "b", [
    ev('Iris forwarded Niko\'s message: "I checked the north gate; it is closed."')])

# U02: nonactual counterfactual versus observed alternate outcome.
add("U02_counterfactual_world", "a", [
    ev("If the backup had started, the import might have completed. The backup never started.")])
add("U02_counterfactual_world", "b", [
    ev("The backup started on May 1. The import still failed that day.")])

# U03: explicit negated cause with replacement versus chronology without cause.
add("U03_negated_causal_scope", "a", [
    ev("The certificate expired before the outage, but the expiry did not cause it."),
    ev("A routing loop saturated the gateway."),
    ev("As a result, the API timed out."),
    ev("The timeout caused checkout retries to fail."),
    ev("A technician signed in before the drill started.")])
add("U03_negated_causal_scope", "b", [
    ev("The certificate expired before the outage. No cause has been established."),
    ev("The API timed out after the outage."),
    ev("Checkout retries failed later."),
    ev("A technician signed in before the drill started.")])

# U04: obligation/permission has a different status from action completion.
add("U04_deontic_requirement", "a", [
    ev("The safety policy requires Jo to sign the inspection by May 8. Jo has not signed it.",
       occurred="2026-05-09T12:00:00Z", available="2026-05-10T12:00:00Z")])
add("U04_deontic_requirement", "b", [
    ev("Jo signed the inspection on May 8. The policy required a signature by that date.",
       occurred="2026-05-09T12:00:00Z", available="2026-05-10T12:00:00Z")])

# U05: quantified set and exception scope.
add("U05_quantifier_exception", "a", [
    ev("Five sensors reported healthy at noon. All except S4 lost signal by evening.",
       occurred="2026-05-01T21:00:00Z")])
add("U05_quantifier_exception", "b", [
    ev("Only S4 lost signal by evening; the other four sensors remained healthy.",
       occurred="2026-05-01T21:00:00Z")])

# U06: repeat event versus repeated report of one event.
add("U06_recurrence_cardinality", "a", [
    ev("The pump stopped on Monday April 27 and again on Tuesday April 28. Both stops were recorded separately.")])
add("U06_recurrence_cardinality", "b", [
    ev("The April 28 alert repeated the April 27 pump stop; there was only one stop.")])

# U07: withdrawn source support is later knowledge, not retroactive early-cutoff knowledge.
add("U07_source_retraction", "a", [
    ev("Tariq's report said pier 2 was open on January 10.",
       occurred="2026-01-10T12:00:00Z", available="2026-01-11T12:00:00Z"),
    ev("Tariq withdrew his January report: pier 2 had been closed on January 10.",
       occurred="2026-03-10T12:00:00Z", available="2026-03-11T12:00:00Z")],
    cutoffs=["2026-02-01T00:00:00Z", "2026-04-01T00:00:00Z"], context_indices=(0,))
add("U07_source_retraction", "b", [
    ev("The February inspection reported twelve cracks in pier 2.",
       occurred="2026-02-10T12:00:00Z", available="2026-02-11T12:00:00Z"),
    ev("The inspector retracted the crack count in April: the sensor was miscalibrated and the count is unknown.",
       occurred="2026-04-10T12:00:00Z", available="2026-04-11T12:00:00Z")],
    cutoffs=["2026-03-01T00:00:00Z", "2026-05-01T00:00:00Z"], context_indices=(0,))

# U08: approximate quantities and incompatible units.
add("U08_quantity_precision", "a", [
    ev("The manager estimated the outage at about two and a half hours; the log records 152 minutes.")])
add("U08_quantity_precision", "b", [
    ev("The timer shows 150 milliseconds, not 150 seconds.")])

# U09: reciprocal actor/recipient roles with the same object.
add("U09_reciprocal_roles", "a", [
    ev("Mina lent Tao the scanner on May 3. Tao returned it to Mina on May 4.",
       occurred="2026-05-05T12:00:00Z", available="2026-05-06T12:00:00Z")])
add("U09_reciprocal_roles", "b", [
    ev("Mina borrowed Tao's scanner on May 3. Mina returned it to Tao on May 4.",
       occurred="2026-05-05T12:00:00Z", available="2026-05-06T12:00:00Z")])

# U10: passive event with supported agent versus unknown agent.
add("U10_passive_agent", "a", [
    ev("The staging gateway was disabled by the deployment bot, according to the audit log.",
       source="audit-log-summary")])
add("U10_passive_agent", "b", [
    ev("The staging gateway was disabled during deployment. The audit log does not identify who did it.",
       source="audit-log-summary")])

# U11: disjunction whose alternatives must not both become asserted facts.
add("U11_disjunctive_failure", "a", [
    ev("Either the cache or the scheduler dropped the job. The trace cannot distinguish them.")])
add("U11_disjunctive_failure", "b", [
    ev("The cache dropped the job. The scheduler was running normally.")])

# U12: local date differs from UTC date; timestamps are exact fixture metadata.
add("U12_timezone_day_boundary", "a", [
    ev("At 23:30 UTC on May 1, Lian posted the alert from Tokyo.",
       occurred="2026-05-01T23:30:00Z", available="2026-05-02T00:00:00Z")])
add("U12_timezone_day_boundary", "b", [
    ev("At 00:30 Tokyo time on May 2, Lian posted the alert.",
       occurred="2026-05-01T15:30:00Z", available="2026-05-02T00:00:00Z")])


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":")) + "\n" for row in rows),
                    encoding="utf-8", newline="\n")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if len(CASES) != 24 or len({r["case_id"] for r in CASES}) != 24:
        raise AssertionError("expected 24 opaque cases")
    if len({r["scenario_family"] for r in SCENARIOS}) != 12:
        raise AssertionError("expected 12 unseen families")
    write_jsonl(ROOT / "candidate_cases.jsonl", CASES)
    write_jsonl(ROOT / "operator_scenario_map.jsonl", SCENARIOS)
    for annotator, seed in (("A", 191), ("B", 307)):
        packet = ROOT / "annotation_packets" / f"annotator_{annotator}"
        shuffled = CASES.copy()
        random.Random(seed).shuffle(shuffled)
        write_jsonl(packet / "CASES.jsonl", shuffled)
        write_jsonl(packet / "ANNOTATIONS_BLANK.jsonl", [
            {"case_id": case["case_id"], "annotator_id": annotator,
             "status": "UNSTARTED", "states": [], "relations": [],
             "visibility": [], "explicit_exclusions": [], "uncertainties": [],
             "block_only_checks": [], "free_notes": ""}
            for case in shuffled
        ])
        instructions = (ROOT / "ANNOTATOR_INSTRUCTIONS.md").read_text(encoding="utf-8")
        instructions = instructions.replace(
            "../../../docs/research/semantic-block/SEMANTIC_BLOCK_DEFINITION.md",
            "SEMANTIC_BLOCK_DEFINITION.md",
        )
        (packet / "ANNOTATOR_INSTRUCTIONS.md").write_text(instructions, encoding="utf-8", newline="\n")
        (packet / "ANNOTATION_TEMPLATE.json").write_bytes((ROOT / "ANNOTATION_TEMPLATE.json").read_bytes())
        definition = REPO / "docs" / "research" / "semantic-block" / "SEMANTIC_BLOCK_DEFINITION.md"
        definition_text = definition.read_text(encoding="utf-8").replace("\r\n", "\n")
        (packet / "SEMANTIC_BLOCK_DEFINITION.md").write_text(
            definition_text, encoding="utf-8", newline="\n")
        packet_files = [packet / f for f in (
            "CASES.jsonl", "ANNOTATIONS_BLANK.jsonl", "ANNOTATOR_INSTRUCTIONS.md",
            "ANNOTATION_TEMPLATE.json", "SEMANTIC_BLOCK_DEFINITION.md",
        )]
        (packet / "PACKET_SHA256.json").write_text(
            json.dumps({"status": "INPUTS_ONLY_NO_GOLD", "annotator": annotator,
                        "sha256": {p.name: digest(p) for p in packet_files}},
                       indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    paths = [ROOT / "candidate_cases.jsonl", ROOT / "operator_scenario_map.jsonl"]
    paths += [ROOT / "annotation_packets" / f"annotator_{a}" / f
              for a in ("A", "B") for f in (
                  "CASES.jsonl", "ANNOTATIONS_BLANK.jsonl", "ANNOTATOR_INSTRUCTIONS.md",
                  "ANNOTATION_TEMPLATE.json", "SEMANTIC_BLOCK_DEFINITION.md", "PACKET_SHA256.json")]
    record = {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}
    (ROOT / "INPUT_PACKET_HASHES.json").write_text(
        json.dumps({"status": "INPUTS_ONLY_NO_GOLD", "sha256": record}, indent=2,
                   ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print("Prepared 24 annotation-only cases in 12 unseen families; no gold generated")


if __name__ == "__main__":
    main()
