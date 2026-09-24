# Route E research design: one-pass semantics, hard gates, selective linker

Status: **design only**. No Route E implementation, model run, or production change has occurred. This design responds to the read-only [v0.1 B/C audit](V01_BC_F8_AUDIT.md). The public output remains one `SemanticBlock` state type plus admitted typed relation references; internal proposals and linker candidates are not public product objects.

## Hypothesis and comparator identity

E takes B's single structured semantic compilation output as the candidate block set. Deterministic gates then **admit, reject, or abstain** on each candidate and relation; they never rewrite predicate, roles, holder, modality, canonical meaning, or block boundary. A selective linker runs only when admitted blocks have a source-cued cross-block relation candidate. This tests whether B's stronger local meaning can be retained while C's useful relation discipline is added.

Run unchanged v0.1 B and C adapters as frozen historical comparators, with their code/prompt hashes recorded. For the new benchmark, pin one model revision, seed/settings, case ordering and total token budget for B/C/E. E's first pass must use **the exact B semantic prompt and schema** (or byte-identical B model response in a paired ablation). Any changed prompt is a separately named E variant. This isolates gate/linker effects from prompt effects. Do not call E superior on a single run with different proposals. Report paired case-level deltas and prompt fingerprints.

## Pipeline

```text
cutoff-visible Raw Evidence + authorized bounded context
  -> B one-pass structured proposal (same semantic prompt/schema)
  -> deterministic hard gates (no semantic repair)
  -> admitted public SemanticBlock states + rejection/abstention ledger
  -> selective cross-block candidate screening
  -> optional bounded linker on screened pairs only
  -> deterministic relation admission and traversal policy
  -> public blocks + admitted relation refs + full run manifest
```

### Hard gates, in order

1. **Input authority:** enforce evidence ID allowlist, availability cutoff, context record count/token ceiling, source/thread namespace, and no accepted cognition or future interpretation. The state availability is at least the latest cited evidence availability and the interpretation creation time. Reject a source whose access cannot be established.
2. **Shape and identity:** require unique state/block keys, allowed enum values, nonempty grounded content, complete required fields or explicit `UNKNOWN`, and immutable state IDs. Never default missing holder to `user`, modality to `asserted`, entity to `resolved`, or time to the request cutoff.
3. **Source coordinates:** require exact `(evidence_id, char_start, char_end, text)` against the admitted evidence bytes. If the model supplies only text, a unique exact occurrence may be resolved deterministically and logged; zero or multiple occurrences causes abstention/rejection. A valid substring is only coordinate integrity; semantic entailment remains a separate review.
4. **Attribution and epistemics:** validate a proposed quote/report against its cited speaker/quotation envelope. An explicit third-party attribution with `holder=user` is rejected or marked unresolved; no regex silently changes holder. A future/conditional/counterfactual marker cannot be admitted as an occurred assertion without explicit independent evidence. If scope is ambiguous, preserve `UNKNOWN` and a review reason. These are conservative syntactic gates, not proof of truth.
5. **Version and duplicate authority:** a repeated source or recap cannot increment independent support count. An existing block may gain a later immutable state only with a recorded continuation reason and availability; distinct world events keep distinct block IDs. Any merge/split that cannot be justified from spans is rejected for review, not auto-normalized.
6. **Post-admission endpoint closure:** rebuild the permitted state-ID set from **actually admitted, cutoff-visible** blocks. Drop and log any relation whose endpoint is absent, same as itself, or whose cue/registry basis is missing. Distinguish `nonexistent_endpoint`, `unmatched_to_gold`, and `unsupported_edge` in evaluation; the latter two are not runtime endpoint failures.

Rejecting an entire block loses recall, so E records a machine-readable reason and evaluates rejected proposal quality offline. A safe gate may preserve a block with explicit unknown fields when that is authorized by the public contract; it cannot turn uncertainty into a positive claim. Compare admitted, abstained, and rejected counts per family.

### Selective linker

Do not invoke the linker for a single admitted block or when no eligible pair exists. Candidate pairs come only from (a) explicit cross-block causal/discourse cue with a source span and two visible state candidates, or (b) an authorized entity-registry mapping or explicit co-reference evidence. Limit to adjacent evidence entries plus at most four bounded prior records; cap at eight pairs and two hops per case. The linker receives admitted IDs, minimal block summaries, the cue spans/registry entries, and the cutoff manifest. It cannot invent a block, change a block field, or cite a rejected state.

Admit `CAUSE` only with direction and scoped evidence that supports the specific endpoint pair; a causal chain is not a direct shortcut. Admit `SAME_ENTITY` only with explicit identity evidence/registry and namespace consistency. `BEFORE` may be retained as timing metadata with `traversal_allowed=false`; do not spend an LLM call merely to mint BEFORE bridges. All linker proposals undergo endpoint, cue, cutoff and type validation again after screening. Unsupported, ambiguous, or low-confidence links remain absent/unknown, and absence is open-world unless a negative control explicitly forbids a link.

## Required ablations and success criteria

Run B, C, E on exactly the same adjudicated v0.2 inputs and raw-hidden consumer. Also report `B + gates only` and `E linker disabled` on the same **cached first-pass B proposal** to attribute changes without extra model sampling. E's first pass should be byte-identical to B's proposal in this paired mode. Report answer accuracy and exact boundaries, safety violations, relation precision/recall, F7 paths, fixed-budget F8 retrieval, rejection rate, abstention quality, call count, tokens, p50/p95 latency, and case-level deltas. Evaluate zero-tolerance violations before aggregate scores. E fails if a gate silently edits semantic meaning or if a relation references an unadmitted state. Do not tune on unseen v0.2 families; freeze E code/prompt and thresholds before their packet is opened.

This is a research hypothesis. Neither v0.1 B's score nor the flawed v0.1 F8 PASS proves E will work. A production choice requires independently adjudicated gold and the v0.2 comparison.
