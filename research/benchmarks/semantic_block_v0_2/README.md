# SemanticBlock benchmark v0.2 — waiting for independent annotation

Current state: **`WAITING_FOR_ANNOTATION`**. This folder contains candidate Raw Evidence, 12 scenario families unseen in v0.1, two isolated **blank** annotator packets, annotation/adjudication instructions, a corrected B/C/F8 audit, and a Route E research design. It contains **no v0.2 gold, no adjudication result, no Route E implementation, and no B/C/E v0.2 scores**. Do not treat sample-input hashes as a gold freeze.

## What to hand to each annotator

| Recipient | Deliver only this folder | Files inside |
| --- | --- | --- |
| Annotator A | [`annotation_packets/annotator_A/`](annotation_packets/annotator_A/) | `CASES.jsonl`, `ANNOTATIONS_BLANK.jsonl`, `ANNOTATOR_INSTRUCTIONS.md`, `ANNOTATION_TEMPLATE.json`, `SEMANTIC_BLOCK_DEFINITION.md`, `PACKET_SHA256.json` |
| Annotator B | [`annotation_packets/annotator_B/`](annotation_packets/annotator_B/) | The same six file types in a different case order; no A results |
| Operator only | [`operator_scenario_map.jsonl`](operator_scenario_map.jsonl), [`INPUT_PACKET_HASHES.json`](INPUT_PACKET_HASHES.json), [family coverage review](OPERATOR_FAMILY_COVERAGE.md), [adjudication protocol](ADJUDICATION_PROTOCOL.md) | Family map, novelty rationale and packet integrity; do not pass them or old gold to annotators |

Copy A and B folders into separate access-controlled workspaces. The two annotators must not see each other's submissions, old v0.1 gold/results, model predictions, or route prompts. They each return a separate `ANNOTATIONS_COMPLETED.jsonl` to the operator. The adjudicator receives both only after both are sealed. The [instructions](ANNOTATOR_INSTRUCTIONS.md), [field template](ANNOTATION_TEMPLATE.json), and [adjudication protocol](ADJUDICATION_PROTOCOL.md) define the task; the case packets themselves contain no expected answers or family names.

## Research documents and next gate

- [v0.1 B/C and F8 audit](V01_BC_F8_AUDIT.md): no observed C semantic-field mutation during normalization; B17/B07 proposal and scorer effects; F8 PASS invalid against gold.
- [Route E design](ROUTE_E_DESIGN.md): B one-pass semantics + deterministic hard gates + selective linker, with paired ablations.
- [v0.2 comparison protocol](BENCHMARK_V02_PROTOCOL.md): B/C/E on adjudicated unseen families; fixed-budget F8 and separate raw-hidden process.
- [Candidate inputs](candidate_cases.jsonl): 24 opaque cases. All 12 scenario families are reserved for unseen evaluation; v0.1 development cases are the only tuning material.

The input packet generator is [`prepare_annotation_packets.py`](prepare_annotation_packets.py). Do **not** rerun it after distribution to alter case text/order in place; a correction requires a new input-packet version and redistributing both packets. Before distribution run:

```powershell
python research/benchmarks/semantic_block_v0_2/validate_input_packets.py
```

The validator checks that each packet has the same 24 cases with different order, contains no annotations, has exactly 12 two-case unseen families in the operator map, and matches all SHA-256 files. It does not validate semantic gold because no gold exists. The next legitimate milestone is receipt of two independent, completed, hashed annotations. Only then may a separate adjudicator decide and freeze v0.2 gold.

When submissions arrive, the operator can run [`validate_annotation_submission.py`](validate_annotation_submission.py) separately for A and B. That script checks structure, exact spans, relation endpoints, and cutoff visibility without opening the other annotator's file or creating gold.
