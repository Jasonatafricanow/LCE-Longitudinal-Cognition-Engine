# Issue #19 frozen research corpus: `semantic_block_v0_1`

This is a synthetic Raw Evidence → public SemanticBlock benchmark for [Issue #19](https://github.com/Jasonatafricanow/LCE-Longitudinal-Cognition-Engine/issues/19), derived from the [Issue #18 benchmark specification](../../../docs/research/semantic-block/BENCHMARK_SPEC.md). The four JSONL files are the execution inputs. `build_frozen_corpus.py` records how they were authored; it is **not** an instruction to regenerate or alter them after freeze. `FROZEN_MANIFEST.json` contains SHA-256 hashes of the corpus, validator, execution protocol, and AGY order.

## Inventory and split

| Item | Frozen count / rule |
| --- | --- |
| Families | B01–B18, exactly one canonical (`-C`), paraphrase (`-P`), and adversarial/control (`-N`) each |
| Cases | 54 total: 42 development, 12 held-out |
| Held-out | Negative variant of B03, B04, B05, B07, B08, B11, B13, B14, B15, B16, B17, B18 |
| Gold | One paired row per case; all source offsets are zero-based Unicode character offsets with exclusive end |
| Cutoffs | Explicit timestamps per case; visibility selects the latest available state per `block_key` |

The held-out slice uses negative perturbations of families visible in development. This tests adversarial contrasts but **does not test unseen scenario families**. No independent annotator or adjudicator participated. Gold is marked `single_author_frozen_unadjudicated`; structural validation checks exact spans and time ordering, not semantic entailment. Consequently, this corpus alone cannot support `READY_FOR_PRODUCTION_DESIGN`. AGY must report that limitation even if a route has perfect measured scores. Independent blind annotation and adjudication should precede any later decision-grade benchmark version. Preserve this version and disagreement/correction history; create `v0_2` if gold changes.

Pre-freeze author review corrected an unsupported project name in B02, a non-equivalent B03 paraphrase, a too-short B11 support span, and a B17 fixture that had not separated temporal from causal endpoints. These corrections preceded the manifest and any route execution. There is no independent disagreement log for this version.

## Data contract

Each `*_cases.jsonl` row has `case_id`, `family`, `variant`, `split`, `raw_evidence` records, `requested_cutoffs`, `context_evidence_ids`, and an optional `entity_registry`. Raw Evidence contains `evidence_id`, `content`, `occurred_at`, `available_at`, `thread_id`, `speaker`, `source_id`. All times are UTC. `context_evidence_ids` is an explicit bounded prior-evidence allowance, not a command to expose future information; the case's raw evidence list contains current and allowed prior records.

Each paired `*_gold.jsonl` row has `states`, `relations`, `visibility`, `forbidden_case_outputs`, `rationale`, and `annotation_status`. Each state has `state_key`, stable `block_key`, canonical content, predicate, kind, participants/roles, holder, utterer, attribution mode, polarity, modality, epistemic hedge, valid time and precision, entity resolution status, uncertainty, independent support count, `available_at`, and exact `source_spans`. A state's `available_at` is the earliest legitimate **interpretation/state availability** in this fixture; it is at least the latest availability of its cited Raw Evidence. It is not the validity/event time. For each cutoff, `visibility` enumerates the latest eligible state of each block. Older immutable states remain in gold for replay checks.

Relations name existing state keys, a type (`CAUSE`, `SAME_ENTITY`, or `BEFORE`), grounding basis and cue span where textual, and a fixed traversal flag. `BEFORE` is non-traversable. Empty positive relations are open-world unless `forbidden_case_outputs` explicitly labels a negative control. The string labels in `forbidden_case_outputs` describe prohibited behaviors; they are **not** additional public object types.

## Freeze check

From `C:\projects\LCE` run:

```powershell
python research/benchmarks/semantic_block_v0_1/validate_freeze.py
```

The validator checks counts, splits, identity, exact span slices, relation endpoints, cutoff visibility, and all manifest hashes. It does not certify that a paraphrase preserves meaning or that a canonical assertion is entailed. The benchmark source, [execution protocol](../../../docs/research/semantic-block/ISSUE_19_FROZEN_EXECUTION_PROTOCOL.md), and [AGY order](../../../docs/research/semantic-block/ISSUE_19_AGY_EXECUTION_ORDER.md) are frozen together. The #18 document's 36+12 sizing was a proposal; this version expands all 18 families into C/P/N and reserves 12 of the 54 as held-out.
