# v0.2 independent annotator instructions

Status: **annotation input only**. The operator assigns exactly one packet to each annotator: `annotation_packets/annotator_A/` or `annotation_packets/annotator_B/`. Complete the packet's `ANNOTATIONS_BLANK.jsonl` as a new file named `ANNOTATIONS_COMPLETED.jsonl`. Do not alter `CASES.jsonl`. The 24 cases have opaque IDs; family labels and any candidate compiler output are intentionally absent.

## Independence and permitted material

Work alone. Do not consult the other annotator, the old v0.1 gold, B/C predictions, reports, caches, Route E prompts, or the operator's scenario map. Do not search for the same synthetic text elsewhere. Use only your packet, this instruction, the [public SemanticBlock definition](SEMANTIC_BLOCK_DEFINITION.md) supplied by the operator, and a UTF-8 editor or annotation tool. Record your own uncertainty rather than guessing. Do not submit an annotation produced or edited by a compiler arm.

The task is to mark what a source-grounded **public SemanticBlock state** must contain so a downstream consumer can answer basic meaning and relation questions without rereading Raw Evidence. Internal clauses may help your reasoning but are not extra public products. A block is the smallest coherent, independently reusable account. Split independent claims when holders, events, objects, times, or later reuse differ; keep an internally connected account together when splitting would lose its meaning. If both choices are defensible, record the boundary dispute in `uncertainties` rather than silently forcing a rule. Do not copy the v0.1 B02 or B17 labels.

## Annotation sequence for every case

1. Read Raw Evidence records and `requested_cutoffs`. Treat `occurred_at` as event/source time and `available_at` as earliest evidence admission time. At each cutoff, ignore later-admitted evidence even if it describes an earlier event. `context_evidence_ids` are allowed prior context, not independent truth or permission to reveal future evidence.
2. Decide reusable block boundaries and immutable state versions first. Use local keys such as `s1`, `s2`, `v1`, `v2` and stable `local_block_key` only for a genuinely continuing account. A changed real-world event normally gets a new block key. A later correction/clarification gets a new state with later `state_available_at`; historical visibility stays unchanged.
3. For every state fill the [uniform field template](ANNOTATION_TEMPLATE.json): canonical content, predicate/kind, participant **roles**, holder, utterer, attribution, polarity, modality, hedge, valid time/precision, entity resolution/uncertainty, independent support count, `support_status`, evidence and interpretation availability, and exact support spans. `support_status` is annotation-only evidence-authority metadata for evaluating retraction, not a new public LCE object. Use `UNKNOWN` with an uncertainty record where source support is insufficient. Do not default holder to the user or possible/required/counterfactual events to occurred facts.
4. Mark exact supporting spans as Unicode character offsets into the corresponding evidence `content`: `char_start` is zero-based, `char_end` is exclusive, and `text == content[start:end]`. One span may cover more than one clause, but each distinct assertion in a multi-claim block needs a `claim_support` entry with its own span(s). A matching substring is necessary, not sufficient: read the whole local context to judge entailment.
5. Add only grounded relations with two local state keys and a cue/registry basis. Distinguish directed CAUSE from BEFORE. BEFORE may carry timing but has no generic graph-bridge authority. SAME_ENTITY needs explicit/authorized referent evidence, not lexical similarity. A chain A→B→C does not imply a direct A→C relation. If relation scope or direction is uncertain, record uncertainty or abstain.
6. For each requested cutoff, list the latest visible state per block in `visibility`; ensure all its support and interpretation were available. Fill `explicit_exclusions` for plausible but unsupported assertions/relations, including negative controls, and state **why**. Do not interpret an absent positive relation as a confirmed negative unless explicitly excluded.
7. Add brief `block_only_checks` for case-specific risks: a query operation (`meaning`, `holder`, `modality`, `time`, `support`, `identity`, `relation_path`), the expected answer from public blocks, and whether that answer would require reopening Raw Evidence. If it would, explain the missing public field. These checks guide adjudication; they do not expose old predictions.
8. Set `status` to `COMPLETE` only after checking every cutoff and every span. Leave unresolved judgments explicit. Submit the completed file privately to the operator; do not place it in the other annotator's folder or shared chat.

## Special distinctions to preserve

- Reported and quoted claims retain their actual holder and utterer. The narrator's act of reporting does not make the reported claim the narrator's belief or an established world fact.
- Counterfactual, conditional, obligation, disjunction, possibility, and approximate quantity are different from an asserted completed event or exact count.
- A repeated alert may be a new source without being a second independent occurrence or independent support.
- Retraction or later interpretation cannot travel backward to an earlier knowledge cutoff. Annotate the source's original status at the early cutoff and later state separately.
- Convert timezone/unit expressions only when the source or fixed metadata makes the conversion determinate; retain source precision and any disagreement between sources.

The operator checks structural completeness and hashes only after both files are independently returned. A third adjudicator then receives both files and the input packet, never compiler predictions, and writes a separate decision log. Annotators do not edit the adjudicated gold.
