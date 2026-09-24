# SemanticBlock v0.3 — Fidelity, Granularity, and Recall Experiment

**Date:** 2026-09-25  
**Status:** Research design only — no production integration authorized  
**Authority:** `docs/architecture/SEMANTIC_BLOCK_DESIGN_FREEZE_2026-09-25.md`

## 1. Research objective

This experiment tests one question only:

> Can a SemanticBlock turn bounded dialogue evidence into a structured representation that preserves the original meaning closely enough for a downstream consumer to reconstruct it, while still exposing enough semantic granularity for selective recall and comparison?

The experiment deliberately does **not** test longitudinal trend discovery, graph traversal, global synthesis, or production readiness.

The order of authority is fixed:

1. semantic fidelity;
2. honest localization of known vs UNKNOWN;
3. useful structure/granularity;
4. later recall utility;
5. complexity only when it buys measurable value.

A representation that retrieves well but changes the meaning fails.

A representation that reconstructs perfectly only because it copied the raw conversation also fails as a SemanticBlock design.

## 2. External research used only as test inspiration

Existing schemes are used to generate adversarial cases, not to define the public SemanticBlock schema.

- DRT / discourse semantics: current meaning can depend on prior discourse, reference resolution, negation, conditionals, and context.
- ISO-style dialogue-act distinctions: mentioning proposition P is not the same as asserting P; questions, requests, corrections, and other communicative acts must remain distinguishable.
- CommitmentBank-style commitment testing: modality, questions, negation, and conditionals change how strongly a speaker commits to a proposition.
- FactBank-style source-relative factuality: “A said P” does not imply the current speaker believes P; nested sources may carry different commitment.

These concepts are benchmark attack surfaces. They are not automatically SemanticBlock fields.

## 3. Primary hypotheses

### H1 — Reconstructability

Given only a SemanticBlock and no Raw Evidence, an independent consumer can reconstruct the original time-local meaning to functional equivalence.

### H2 — Non-trivial structure

Reconstructability is not achieved merely by copying or lightly paraphrasing the raw dialogue into one undivided blob.

### H3 — Surface invariance

Inputs with materially equivalent meaning but different wording or syntax produce structurally compatible representations and are easy to retrieve together.

### H4 — Semantic separability

Inputs with very similar wording but materially different meaning remain structurally separable.

### H5 — Honest UNKNOWN

The representation preserves all supported meaning while keeping genuinely unsupported conclusions UNKNOWN. It neither guesses past the evidence nor uses UNKNOWN to discard information that is already known.

### H6 — Temporal locality

A SemanticBlock records what is true at the cutoff. It does not inject later outcomes into an earlier point or weaken a present fact merely because its future result is unresolved.

### H7 — Recall utility

A later semantically relevant query or structural candidate can recall the correct block from the structured representation without rereading the Raw Evidence corpus.

## 4. Experimental arms

All generative arms use the same frozen model, decoding parameters, cutoff-bounded input, and source metadata. No arm may see future evidence.

### P0 — Raw-text passthrough control

Stores the bounded source text with minimal packaging.

Purpose:
- reconstruction ceiling;
- trivial non-structure control.

P0 is not eligible to become the preferred SemanticBlock representation.

### P1 — Canonical semantic account

One natural-language canonical account intended to preserve the full time-local meaning, plus provenance.

No explicit semantic substructure beyond the canonical account.

Purpose:
- test whether a well-written semantic account alone is sufficient;
- establish the simplest non-raw baseline.

### P2 — Minimal structured SemanticBlock

A canonical semantic account plus a **small, bounded structured projection** sufficient to expose distinctions needed for later recall.

The projection may represent only information that is necessary to distinguish meaning, such as:
- source/attribution where meaning depends on it;
- commitment/qualification where meaning depends on it;
- explicit unresolved/UNKNOWN portions;
- explicit current action/state/requirement/intention distinctions where meaning depends on them;
- deterministic time/provenance references.

The exact internal labels are experimental. They are not frozen public ontology.

Purpose:
- target representation.

### P3 — Atomized / high-structure control

Decompose the same evidence into finer propositions/roles/typed fields.

Purpose:
- test whether additional structural detail provides real retrieval value;
- expose loss of reconstructability from over-decomposition;
- provide an explicit complexity control.

### P4 — Legacy V1 compiler reference

Run the current V1 SemanticBlock path unchanged when technically feasible.

Purpose:
- quantify how much the previous design differs from the frozen v0.3 objective;
- retain negative evidence rather than rewriting history.

P4 is observational and must not be tuned on this benchmark.

## 5. Dataset design

### 5.1 Core set: 48 cases

Eight semantic families, six cases each.

Each family must contain:
- at least one canonical case;
- at least one **same meaning / different surface form** pair;
- at least one **similar surface form / different meaning** hard-negative pair;
- at least one case where UNKNOWN is the correct local result;
- at least one multi-turn context-dependent case.

Families:

1. **Attribution and reported speech**
   - direct user statement;
   - single-level report;
   - nested report;
   - user endorsement unknown;
   - user explicitly endorses or rejects the report.

2. **Communicative act**
   - assertion;
   - question;
   - request/instruction;
   - suggestion;
   - correction/retraction.

3. **Epistemic commitment**
   - certain;
   - probable;
   - possible;
   - explicitly unknown;
   - negated.

4. **Desire / intention / obligation / current requirement**
   - wants to do X;
   - plans to do X;
   - must do X;
   - has done X;
   - asks whether X will happen.

5. **Hypothetical / counterfactual / conditional**
   - if X;
   - if only X had happened;
   - X would happen under condition Y;
   - actual X.

6. **Correction and revision**
   - “I said Tuesday; I meant Wednesday”;
   - world later changed from A to B;
   - explicit retraction;
   - uncertain self-correction.

7. **Context dependence**
   - pronouns;
   - ellipsis;
   - short answers;
   - later local qualification;
   - apparent contradiction resolved by prior turn.

8. **Nonliteral and ambiguous language**
   - sarcasm;
   - exaggeration;
   - joke;
   - idiom;
   - genuinely ambiguous case where UNKNOWN is correct.

### 5.2 Temporal fork set: 12 branch records

Create four identical prefixes, each copied into three different future branches.

Example prefix:

> 09:00 — “我今天必须赶杭州到北京的飞机。”

Possible later branches:

A. arrives and flies normally;  
B. traffic causes the user to miss the flight;  
C. typhoon cancels the flight.

Compile at the 09:00 cutoff.

The three outputs must be semantically equivalent because the visible evidence is identical.

This set tests:
- no-future leakage;
- no premature trajectory;
- no weakening of a current requirement because the eventual outcome is unknown.

### 5.3 Distractor corpus

Add semantically adjacent distractors so retrieval cannot succeed from topic words alone.

For travel examples, distractors should include:
- “可能去北京”;
- “想去北京”;
- “必须去上海”;
- “朋友说明天去北京”;
- “有没有去北京？”;
- completed Beijing trips.

The retrieval task must distinguish semantic structure, not merely entity/topic overlap.

## 6. Gold record

The gold format must not require a fixed production ontology.

Each case records:

```text
case_id
cutoff
visible_dialogue
gold_semantic_account
must_preserve[]
must_not_claim[]
legitimate_unknowns[]
equivalence_group_id?      # same meaning, different surface
hard_negative_group_id?    # similar surface, different meaning
future_fork_group_id?
retrieval_queries[]
retrieval_hard_negatives[]
evidence_spans[]
```

### Example

Input:

> “我朋友说公司可能下个月裁员。”

Gold semantic account:

> 用户转述朋友认为公司可能在下个月裁员。

Must preserve:
- the user is reporting another person's view;
- the friend expresses possibility, not certainty;
- the time reference is next month.

Must not claim:
- the company will definitely lay off staff;
- the user personally believes layoffs will happen.

Legitimate unknowns:
- whether the user agrees with the friend;
- whether layoffs will actually occur.

## 7. Stage A — Blind reconstruction

For every generated representation:

1. hide Raw Evidence;
2. give only the SemanticBlock representation to an independent consumer;
3. ask the consumer to reconstruct the original meaning in plain language;
4. score the reconstruction against the gold constraints.

The consumer must not see:
- original dialogue;
- family label;
- future branch;
- gold account;
- retrieval targets.

### Metrics

Record separately:

- Must-Preserve Recall;
- Forbidden-Claim Rate;
- UNKNOWN Localization Accuracy;
- Attribution Fidelity;
- Temporal Locality;
- full-case semantic equivalence judgment.

Do not collapse these into one headline score.

### Severe contamination errors

Count separately:

- reported speech -> user belief;
- question -> assertion;
- hypothetical/counterfactual -> occurred fact;
- possibility -> certainty;
- desire/intention/obligation -> completed event;
- future outcome injected into earlier cutoff;
- unsupported claim invented to remove UNKNOWN.

Any preferred representation with severe contamination remains research-only regardless of average score.

## 8. Stage B — Contrastive structure test

### Test B1 — Same meaning, different surface

For each equivalence group:

```text
surface form A
surface form B
surface form C
        ↓
representations should remain semantically compatible
```

Measure:
- pairwise representation similarity under one frozen embedding model;
- nearest-neighbour recovery within the equivalence group;
- consumer judgment of whether the blocks encode the same meaning.

### Test B2 — Similar surface, different meaning

For hard-negative groups:

```text
“我明天必须去北京”
“我明天可能去北京”
“我明天想去北京”
“我明天会不会去北京？”
“我朋友说明天要去北京”
```

Measure:
- whether same-topic lexical overlap causes false equivalence;
- margin between the correct semantic neighbour and hard negatives;
- hard-negative false-retrieval rate.

The experiment should favor representations that are invariant to wording but sensitive to meaning.

## 9. Stage C — Recall utility

Build one mixed corpus containing:
- all compiled blocks;
- hard negatives;
- semantically adjacent distractors.

Use the same frozen retrieval mechanism for every arm.

Raw Evidence is not indexed for P1-P4.

Queries should test three kinds of recall:

### C1 — Direct semantic recall

Example:

> “找出用户明确必须完成的出行安排。”

### C2 — Cross-surface recall

Query wording must differ substantially from the source wording.

Example source:

> “北京那边我明天非去不可。”

Query:

> “哪些事情当时属于强制或不可推迟的安排？”

### C3 — Later-trajectory candidate recall

Later evidence:

> “最后因为堵车没赶上。”

Query only asks for plausible earlier points relevant to this later event.

The correct earlier “must catch flight” block should be retrievable.

This stage does **not** authorize the system to claim a trajectory. It tests only whether the block can be woken back up as a relevant candidate.

### Metrics

- Recall@1 / Recall@5;
- MRR;
- hard-negative false retrieval;
- equivalence-group retrieval;
- distractor rate;
- candidate volume.

## 10. Stage D — Granularity / anti-cheating audit

### D1 — Raw-copy audit

Measure:
- representation token length relative to visible source;
- lexical overlap / longest copied span;
- whether reconstruction depends on preserved raw wording.

High copying is not automatically failure, but if P1/P2 only reconstruct because they retain most of the original dialogue unchanged, classify as **TRIVIAL_NON_STRUCTURE**.

### D2 — Structure-only ablation

For structured arms, remove any optional raw source quotation while retaining the structured representation.

Repeat reconstruction and retrieval.

If performance collapses only after source quotation removal, the structure itself is not carrying the meaning.

### D3 — Over-atomization audit

Check whether P3:
- loses source/qualification relations;
- cannot reconstruct the whole;
- requires the consumer to invent glue between fragments;
- creates many tiny units that increase retrieval noise.

## 11. Context sufficiency test

The compiler receives a bounded dialogue prefix, not an isolated sentence.

For selected cases, compare:

A. target utterance only;  
B. target + immediately necessary context;  
C. full bounded local prefix.

The purpose is not to maximize context length.

The question is:

> What is the smallest available context that lets the compiler recover the correct meaning without distortion?

If B succeeds and C adds no value, prefer B.

If only C succeeds, record a context-selection problem rather than adding more SemanticBlock fields.

## 12. Evaluation protocol

### Generation

- one frozen compiler model per run;
- identical temperature/seed policy across P1-P3;
- no prompt tuning after held-out results;
- compiler sees cutoff-bounded evidence only.

### Judging

Use two independent evaluators where possible:
- one blind model judge;
- one independent model or human adjudicator for disagreement/severe-error review.

The generator must not judge its own output as the sole authority.

Gold construction and adjudication remain separate from compiler implementation.

### Dataset split

- Development: 32 core cases + 6 fork records.
- Held-out: 16 core cases + 6 fork records.

Equivalence/hard-negative siblings must remain in the same split to avoid template leakage across dev/held-out.

Do not claim “unseen family” generalization unless held-out families themselves are disjoint.

## 13. Decision rules

There is no overall weighted score.

Architecture selection follows a strict order.

### Gate 1 — Semantic fidelity

An arm cannot be preferred if it materially increases:
- severe contamination;
- forbidden claims;
- attribution drift;
- misplaced UNKNOWN;
- temporal overreach.

### Gate 2 — Reconstructability

Among arms that pass Gate 1, prefer representations whose blind reconstruction preserves the original meaning.

### Gate 3 — Structured utility

A more structured arm is justified only if it improves at least one pre-registered recall/discrimination metric on paired cases **without material reconstruction loss**.

Use paired bootstrap confidence intervals or an equivalent paired comparison; do not credit tiny unpaired headline differences.

### Gate 4 — Minimum sufficient complexity

If P1 and P2 have indistinguishable retrieval/discrimination performance, prefer P1.

If P2 beats P1 but P3 adds no reliable incremental value, prefer P2 and reject P3 complexity.

P3 survives only if extra structure produces reproducible downstream value that P2 cannot provide.

### Gate 5 — Legacy comparison

P4 may be retained as compatibility evidence, but the new design must not be weakened merely to make legacy V1 score better.

## 14. Failure taxonomy

Every failure should be assigned to the earliest defensible layer:

```text
CONTEXT_INSUFFICIENT
SEMANTIC_MISREAD
ATTRIBUTION_DRIFT
OVERCLAIM
UNDERCLAIM
UNKNOWN_MISPLACED
TEMPORAL_OVERREACH
NON_RECONSTRUCTABLE
TRIVIAL_NON_STRUCTURE
GRANULARITY_COLLAPSE
SURFACE_SENSITIVITY
OVER_ATOMIZATION
RETRIEVAL_REPRESENTATION_FAILURE
RETRIEVER_FAILURE
EVALUATION_AMBIGUITY
```

Do not respond to every failure by adding fields.

The failure taxonomy exists to identify where information was lost.

## 15. What this experiment can conclude

Possible outcomes:

### Outcome A — P1 is enough

Canonical semantic accounts reconstruct well and retrieve/separate as well as structured variants.

Conclusion:
- explicit structure is currently unnecessary;
- keep the simpler representation.

### Outcome B — P2 is the useful minimum

P2 preserves meaning and materially improves contrastive/retrieval behavior over P1, while P3 adds little or harms reconstruction.

Conclusion:
- retain minimal structured SemanticBlock as the leading design.

### Outcome C — P3 is justified

Fine structure materially improves recall/discrimination without reconstruction loss and the gain survives held-out cases.

Conclusion:
- investigate which additional structure produced the gain before freezing any schema.

### Outcome D — all arms fail reconstruction

Conclusion:
- the problem is still semantic compilation/context recovery;
- do not proceed to graph or longitudinal structure work.

### Outcome E — reconstruction succeeds but retrieval fails for all non-raw arms

Conclusion:
- the representation preserves meaning but does not expose useful structure;
- study granularity/representation before graph algorithms.

## 16. Explicit non-goals

This experiment does not test:

- graph traversal quality;
- global GraphRAG;
- longitudinal trend correctness;
- full production readiness;
- final ontology design;
- model-general robustness across many compiler models;
- final confidence weighting policy.

Those come later only if SemanticBlock itself passes.

## 17. Deliverables

Required:

- `SEMANTIC_BLOCK_V03_PROTOCOL.md`
- frozen case manifest;
- dev / held-out split manifest;
- gold records;
- compiler prompts/configs for P1-P3;
- legacy P4 adapter if feasible;
- blind reconstruction outputs;
- contrastive/retrieval results;
- error analysis by failure taxonomy;
- cost/latency report;
- final `SUPPORTED | NOT SUPPORTED | INCONCLUSIVE` result.

## 18. Stop condition

After the held-out run:

> stop.

Do not tune P1-P3 against held-out failures and rerun the same benchmark as if it were fresh evidence.

Use the result to design the next benchmark or a new frozen holdout.

The experiment is successful even if every candidate fails, provided it tells us whether meaning was lost at context recovery, semantic compilation, granularity, or recall.
