# Raw Evidence → SemanticBlock benchmark specification

Status: **pre-registered proposal**, 2026-09-24. The examples below are candidate fixtures, **not adjudicated gold** and not measured results. Freeze a human-reviewed gold set and scoring script before testing a compiler or changing production code. This evaluates the *block output* and its downstream sufficiency, not generic proposition extraction or AGY's annotation F1.

## Unit of evaluation and arms

Input is a sequence of immutable Raw Evidence records with text, source/holder context, occurrence time, admission/availability time, source/thread IDs, and a requested cutoff. Output is a set of public SemanticBlock states plus admitted relation references and a compilation manifest. Gold annotators mark block boundaries, canonical meaning, required fields, exact evidence spans, legitimate unknowns, relations, and exclusions. Their internal clause notes never become required public objects.

Compare under identical evidence, cutoffs, model family, and budget accounting:

- **A / current V1:** current coarse `content` + metadata and vector path, with no new meaning fields.
- **B / one-pass:** one structured LLM compilation call with deterministic span/schema checks.
- **C / recommended:** deterministic provenance and cutoff manifest + internal semantic proposal + validation/normalization + bounded second-pass linker, one public block abstraction.
- **D / full-frame comparator:** richer structured semantic frame, to test whether C omits necessary information.

No arm may read gold, future evidence, accepted cognition, or another arm's output. For graph value, compare C blocks with vectors only against the **same C blocks** plus admitted typed links; do not repeat #16's representation confound. Score same-pass versus deferred linking separately. Log latency, tokens, calls, failure/retry, and storage bytes. Do not optimize on held-out cases.

## Candidate seed fixtures

All examples use synthetic people and projects. Times in examples are source *validity* times; the final fixture record must also have explicit admission time. Expected counts are proposed for adjudication, not gold scores.

| ID / family | Raw Evidence and context seed | Proposed block boundary and required oracle distinction |
| --- | --- | --- |
| B01 single fact | `On 2026-04-02 I joined Project Cedar.` | One asserted author-held event; participant/project and exact time/source span. |
| B02 compound causal sentence | `Because the queue lost quorum, the API returned 503.` | **One** coherent causal account with two internally identifiable clauses and a grounded causal cue; no duplicate parent/child block. This tests when internal structure suffices. |
| B03 cross-sentence causality / F7 | `The storage cluster lost quorum. As a result, the API gateway returned 503. Therefore the checkout failed.` | **Three** independently reusable event blocks with two composable, source-cued `CAUSE` links; no `BEFORE` substitution, orphan endpoint, or duplicated parent/child account. This tests inter-block continuity. |
| B04 quoted attribution | `Mira said, "The migration is safe." I have not verified it.` | Third-party quoted claim plus author's unverified stance, separate holders; never author-belief `safe`. |
| B05 modality and uncertainty | `I might move to Lisbon next spring, but I have not decided.` | Possible future move, not occurred move; explicit uncertainty and temporal precision. |
| B06 temporal state change | `In January I worked on Atlas. In March I worked on Cedar.` | Two time-scoped states; no automatic `REVISION`, `INCOMPATIBLE`, or single timeless employer/project. |
| B07 pronoun/coreference | Prior cutoff-visible item: `Mira owns Cedar.` New item: `She restarted it yesterday.` | Resolve `she`/`it` only with authorized prior context; record the precise context IDs and relative-time anchor. With prior item excluded, abstain. |
| B08 cross-context same entity | Thread A: `The Cedar queue is stalled.` Thread B: `Our task broker for Cedar recovered.` | Link only if an authorized registry or supporting evidence establishes referent identity; low lexical overlap alone is insufficient. Include a different-broker negative variant. |
| B09 recap/repetition | Day 1: `I postponed the launch.` Day 2: `As I said, the launch is postponed.` | Same account may gain provenance but no second independent corroboration or false new occurrence. |
| B10 unrelated topic shift | `Cedar's queue failed. Separately, I booked a dentist visit.` | Two reusable blocks; no merged topic bundle or causal link. |
| B11 one input, two meanings | `Mira approved Cedar. I declined Atlas.` | Two blocks because holders, objects, and predicates differ; each has exact source span and polarity. |
| B12 multiple inputs, one account | `The Cedar queue stalled.` followed by `It is still stalled; no restart yet.` | One continuing state account may have a new immutable state with two source references; preserve changed knowledge/validity time and no duplicate support count. |
| B13 adversarial lexical similarity | `Cedar queue lost quorum.` / `The cedar trees lost leaves.` | Distinct subjects and meanings despite shared tokens; no `SAME_ENTITY` or generic graph bridge. |
| B14 same referent, low lexical similarity | `The task broker for Cedar failed.` / `That scheduling service recovered.` | Admit identity only when thread/registry context supports it; test retrieval without raw reread. |
| B15 quoted disagreement | `Mira: "Cedar is ready." I disagree; its checkout still fails.` | Separate holder-scoped claims; negative author assertion, not a single contradictory author belief or automatic longitudinal `REVISION`. |
| B16 clarification of earlier ambiguity | T1: `It failed after the rollout.` T2: `By it, I meant the Cedar queue, not checkout.` | At T1 keep unresolved referent; T2 creates an availability-dated interpretive state. Historical T1 query must still return ambiguity. |
| B17 F8 density control | `A logged in before B; B before C; D before E` beside one explicit `X caused Y, which caused Z` | Persist temporal order if grounded but generic `BEFORE` edges must not create broad multi-hop bridge candidates; retain true causal-chain recall. |
| B18 late-arrival cutoff | A note about January is admitted in March; query at February cutoff, then April cutoff | The note and any interpretation of it are invisible in February despite January `occurred_at`; visible in April with original event time. |

For every seed, create at least one meaning-preserving paraphrase/format variant and one adversarial variant before freeze. Explicitly reserve held-out identities and source wording by family; do not leak them into prompt examples. A compact first benchmark is the 18 seed families plus 18 paired controls (36 cases), with a separately frozen 12-case held-out slice spanning F7, attribution, cutoffs, boundary changes, and negative relations. These numbers are **proposed design**, not an existing dataset.

## Gold and annotation procedure

Two independent annotators first decide reusable block boundaries and block-only questions without seeing compiler output. They then mark source spans, holder, predicate/kind, polarity, modality, hedge, time/precision, entity resolution status, and permitted relation endpoints/cues. A third adjudicator resolves disagreements while retaining the disagreement log. Annotate `UNKNOWN`/abstain and negative controls explicitly; an absent positive edge means open-world unknown except in a deliberately labeled no-relation control. Keep training/dev/eval partitions by scenario family and surface template to reduce leakage. Freeze source IDs, cutoffs, gold, metric code, and route configurations before held-out execution.

For source grounding, require exact span coordinates and a semantic entailment judgment; a substring match alone does not prove the compiled claim. A block with multiple claims must map each claim to its source span(s). Attribute each relation to two stable endpoint states and its cue span(s). Mark whether cause is explicit, warranted by the annotated context, or unsupported. Record annotator uncertainty instead of forcing a link.

## Block-only downstream test matrix

The evaluator hides raw text from a separate consumer. The consumer sees only candidate block states, relations, versions, and provenance *references*; it may resolve IDs but cannot read source text. It answers or abstains on:

| Question | Pass observation | Critical failure |
| --- | --- | --- |
| Who holds the claim; who uttered it? | Correct holder and direct/indirect/quote mode | Third-party quote attributed to user |
| What happened or was stated? | Correct participants, predicate, kind, polarity | Claimed event invented or negation scope lost |
| Did it occur, remain possible, or express desire? | Correct modality/hedge or explicit unknown | Possible/intended event promoted to occurred fact |
| When does it apply? | Correct validity interval/precision and cutoff visibility | Later evidence or interpretation appears in earlier cutoff |
| Which referent is meant? | Supported ID or explicit unresolved marker | Similar name silently merged |
| What supports it? | Exact evidence IDs/spans and lineage | Unsupported canonical content; provenance cannot reopen source |
| Can two blocks be linked? | Correct CAUSE/SAME_ENTITY endpoints and qualification | Chronology promoted to cause; false identity bridge |
| Can structure discovery use it? | Candidate construction consumes blocks/links only; support is traceable | Downstream rereads raw to recover basic meaning |

The raw-hidden consumer may use deterministic projections of block fields; it may not call an LLM on Raw Evidence. Audit access to Raw Evidence remains available in a separate provenance test.

## Metrics, controls, and proposed gates

Report per family and macro distributions, not a single aggregate: boundary precision/recall and exact account matching; over/under-split count; field accuracy and abstention calibration; span integrity and semantic grounding; holder flip count; CAUSE and SAME_ENTITY precision/recall by within/cross-sentence and within/cross-context; broken-endpoint count; F7 path recovery; F8 candidate volume/precision/recall; block-only answer accuracy and raw-reread attempts; paraphrase semantic equivalence and inappropriate identity merging; cutoff leakage; same-version replay equivalence; and cost/latency. Retain confusion matrices and raw case traces.

Hard gate proposal: **zero** unsupported canonical assertions, silent holder flips, future/cutoff leaks, accepted cognition labels, or invalid relation endpoints in the frozen held-out set. These zero-tolerance conditions are safety gates, not a claim that a small set proves absence in production. For quality, pre-register per-family minimums only after annotator agreement and baseline variability are measured; require C to improve block-only sufficiency and F7 continuity without materially worsening boundary/attribution or F8 bloat relative to B and V1. Require a justified cost ceiling, set before eval. If no arm meets hard gates, outcome is **BLOCKED / revise research contract**, not automatic production authorization.

Controls: source/time shuffle, future-context poison, quote-to-author swap, entity-name collision, connective removal, `BEFORE`-only graph ablation, CAUSE and SAME_ENTITY family ablations, parent/child clause duplication, repetition injection, and one-source invalidation. Compare vector-only and graph-backed retrieval on the same accepted blocks at each cutoff. Log whether extra candidates improve supported discovery rather than count alone.

## Evidence boundaries

[#15 reports](../../../research/benchmarks/semantic_annotation_v0_1/PARSER_EVALUATION_REPORT_V0_1.md) and [integrity audit](../../../research/benchmarks/semantic_annotation_v0_1/PARSER_INTEGRITY_AUDIT_REPORT.md) evaluate an internal annotation parser and disagree on at least one trap/aggregate relation score; neither certifies Raw Evidence → SemanticBlock completeness. [#16](../../../research/experiments/oracle_graph_value/ORACLE_GRAPH_EXPERIMENT_REPORT.md) and [#17](../../../research/experiments/agy_graph_vs_oracle/RECONCILIATION_AUDIT.md) are synthetic graph experiments whose F7/F8 failures directly motivate these controls. [DocRED](https://aclanthology.org/P19-1074/), [PDTB](https://catalog.ldc.upenn.edu/LDC2008T05), and [TimeML](https://timeml.github.io/site/publications/timeMLdocs/timeml_1.2.1.html) motivate cross-sentence, discourse, and temporal test dimensions; their metrics are not LCE acceptance thresholds.
