# LCE Semantic Annotation Guideline v0.1

**Status:** Frozen Research Guideline (GitHub Issue #13)  
**Scope:** Research Only — Applies to annotation contracts, golden benchmarks, and parser validation.  
**Prerequisite:** Readers must review [`ONTOLOGY_V0_1.md`](file:///c:/projects/LCE/docs/research/semantic_annotation/ONTOLOGY_V0_1.md) before applying these guidelines.

---

## 1. Overview and Core Philosophy

This guideline provides the operational manual for annotating semantic units and pairwise relations from text spans within LCE Semantic Blocks.

### Guiding Principles

1. **Source Grounding Over Interpretation:** The annotator must only capture what is linguistically asserted or strictly entailed in the text span. Do not fill missing details from world knowledge, psychological assumptions, or downstream cognitive hypotheses.
2. **First-Class Uncertainty:** `UNKNOWN`, `NO_RELATION`, and `TEMPORAL_UNKNOWN` are valid, necessary outcomes. If the text does not supply evidence for a relation or role, prefer `UNKNOWN` or omission rather than guessing.
3. **Decoupled Cognition:** The annotator must never assign longitudinal cognitive labels (e.g. `REVISION`, `RECURRENCE`, `TRAJECTORY`, `COGNITIVE_SHIFT`). The annotation contract provides raw semantic building blocks for the cognition engine, not the engine's final conclusions.

---

## 2. The 12 Canonical Annotation Rules

The following 12 rules are non-negotiable invariants:

### Rule 1: Bounded Source Span
Every `SemanticUnit` must map to an exact, non-empty character span (`char_start`, `char_end`) within the text of the source `RawEvidence` / `SemanticBlock`. No "floating" or ungrounded annotations are permitted.

### Rule 2: Atomic Unit Decomposition
An atomic proposition is the smallest syntactic/semantic clause that can independently take:
- negation (polarity),
- modality,
- a distinct holder/source, or
- an independent temporal anchor.
If a sentence contains two clauses that differ in any of these four dimensions, they **must** be segmented into separate `SemanticUnit` instances.

### Rule 3: Separation of Multiple Events/States Inside One Boundary Unit
A single `SemanticBlock` typically contains multiple events, states, or attitudes. Annotators must decompose the block into distinct `SemanticUnit` records. Do not merge separate occurrences into a single summary unit.

### Rule 4: Mandatory Holder Attribution for Quoted and Reported Claims
When an assertion, belief, or event is attributed to a third party or quoted directly, the unit's `holder` must be set to `quoted` or `reported`, and the attributing verb/frame must not be merged with the speaker's own beliefs. If the author is stating their own direct experience or belief, `holder` is `user`.

### Rule 5: No Inference Promotion
Never promote an inference to `explicit` or `entailed`.
- `explicit`: The text explicitly uses words conveying the proposition.
- `entailed`: The proposition follows by strict deductive necessity (e.g., "Alice was assassinated" $\implies$ "Alice is dead").
- `inferred`: Any contextual, pragmatic, or probabilistic assumption. Such units must be labeled `evidence_status: inferred` and are excluded from authoritative graph construction.

### Rule 6: Strict Event Coreference (`SAME_EVENT`)
`SAME_EVENT` is strictly stronger than topical or semantic similarity. Two units are `SAME_EVENT` if and only if they refer to the exact same spatio-temporal event token with the same participants. Two separate meetings on the same topic are **not** `SAME_EVENT`.

### Rule 7: Temporal Adjacency Is Not Causality
The fact that unit $A$ occurred immediately before unit $B$ ($A \text{ BEFORE } B$) is **never** sufficient on its own to assert $A \text{ CAUSE } B$.

### Rule 8: Supported Causality
A `CAUSE` relation requires explicit linguistic connective support (e.g., "because", "due to", "as a result of", "therefore", "led to") or incontrovertible causal discourse framing. When causality is merely plausible but unstated, annotate temporal ordering (`BEFORE`) and set the causal relation to `NO_RELATION` or `UNKNOWN`.

### Rule 9: Strict Scope for `INCOMPATIBLE`
Two units are `INCOMPATIBLE` if and only if:
1. They concern the exact same subject, dimension, and scope; and
2. Their asserted values, states, or polarities cannot simultaneously coexist in the same state of affairs.
Cross-time changes (e.g., wanting X in 2022 and rejecting X in 2026) are annotated as `INCOMPATIBLE` with distinct temporal anchors and a `BEFORE` relation. They must **never** be labeled as `REVISION`.

### Rule 10: Prefer `UNKNOWN` Over Guessing
When argument roles, temporal relations, or logical connections are ambiguous between multiple interpretations, annotate `UNKNOWN` or `NO_RELATION`. Forced guessing degrades downstream benchmark calibration.

### Rule 11: Cutoff Integrity (No Future Leakage)
An annotator or parser evaluating evidence up to cutoff timestamp $t$ must **never** inspect or utilize evidence timestamped after $t$. Later events cannot retroactively modify the semantic parse of an earlier unit.

### Rule 12: Annotation Confidence Is Metacognitive
The `confidence` score ($0.0 \le c \le 1.0$) measures the annotator's or model's confidence in the **correctness of the annotation itself** (the mapping from text to unit/relation), **not** whether the real-world proposition is factually true in the world.

---

## 3. Step-by-Step Annotation Procedure

### Step 1: Unit Identification and Span Bounding
1. Read the entire `SemanticBlock` and note its `raw_evidence_id` and `semantic_block_id`.
2. Identify independent predications:
   - Identify main verbs, predicate adjectives, nominalized events, or attitudinal stances.
   - For each predication, determine whether it carries its own negation, modality, holder, or time.
   - Record exact character offsets (`char_start`, `char_end`) for the span expressing the unit.

### Step 2: Assign `kind` and `predicate`
Apply the following decision tree:
```text
Is it a mental stance, desire, preference, or valuation?
  ├── YES ──> kind = "attitude" (predicate = "want", "prefer", "like", "believe", etc.)
  └── NO
      Is it a dynamic action, occurrence, or transition?
        ├── YES ──> kind = "event" (predicate = action lemma, e.g. "resign", "deploy")
        └── NO
            Does it describe an ongoing state, property, or relationship?
              ├── YES ──> kind = "state" (predicate = state lemma, e.g. "employed_at", "live_in")
              └── NO  ──> kind = "proposition" (general assertion, timeless rule)
```

### Step 3: Assign Conservative Argument Roles
For the identified predicate, match arguments strictly against the defined role vocabulary:
- `actor`: Volitional initiator/agent ("**I** resigned").
- `experiencer`: Feeling/sensing entity ("**I** felt exhausted", "**She** noticed the error").
- `theme`: Undergoing entity ("The **server** crashed", "They moved the **database**").
- `target`: Recipient or orientation of attitude/action ("I applied to **Google**").
- `stimulus`: Trigger of mental state ("The **loud noise** frightened me").
- `topic`: Subject of discussion/thought ("We discussed **monorepos**").
- `place`: Spatial location ("in **Berlin**", "at **home**").
- `reason`: Stated rationale ("due to **burnout**").
- `purpose`: Stated objective ("in order to **learn Rust**").
- `result`: Outcome ("resulting in **outage**").
- `time`: Temporal phrase within span ("on **Friday**").

*Rule:* If a role is not explicitly stated in the text, **leave it out**.

### Step 4: Determine Polarity and Modality
1. **Polarity:**
   - Look for syntactic or lexical negation ("not", "never", "no", "failed to").
   - Explicitly negated $\implies$ `negative`.
   - Affirmatively holding $\implies$ `positive`.
   - Ambiguous/indeterminate $\implies$ `unknown`.
2. **Modality:**
   - Look for modal auxiliaries ("might", "could", "would", "will"), conditional markers ("if"), desire verbs ("want", "hope"), or certainty hedges ("perhaps", "doubt").
   - Classify as `asserted`, `possible`, `hypothetical`, `intended`, `desired`, `uncertain`, or `unknown`.

### Step 5: Determine Holder / Source
- Is the statement spoken or written directly by the user/author? $\implies$ `user`.
- Is it directly enclosed in quotation marks attributed to someone else? $\implies$ `quoted`.
- Is it an indirect report of someone else's statement or thought? $\implies$ `reported`.
- Is it output from an automated tool, prompt system, or system log? $\implies$ `system`.
- Unclear? $\implies$ `unknown`.

### Step 6: Temporal Anchoring
1. Extract any temporal expressions in the span or the parent evidence timestamp.
2. Determine `anchor_type`:
   - Exact date/time given ("2023-08-15") $\implies$ `exact`.
   - Bounded window ("Q3 2023", "Summer 2024") $\implies$ `bounded_range`.
   - Relative expression ("yesterday", "three weeks later") $\implies$ `relative`.
   - No temporal expression and timeless $\implies$ `unanchored`.
3. Normalize `value` to ISO 8601 format where possible (e.g. `"2023-08-15"`, `"2023-07/2023-09"`), or `"unknown"`.

### Step 7: Pairwise Relation Annotation
For any pair of units $(U_1, U_2)$ within the same document or across linked blocks:
1. **Identity Check:**
   - Do they describe the exact same event token? $\implies$ `SAME_EVENT`.
   - Do their argument entities refer to the exact same real-world entity? $\implies$ `SAME_ENTITY`.
2. **State Compatibility Check:**
   - Do they assert the exact same proposition under the same polarity? $\implies$ `EQUIVALENT`.
   - Do they assert mutually exclusive states/attitudes about the same subject/dimension? $\implies$ `INCOMPATIBLE`.
3. **Discourse / Logical Check:**
   - Does $U_1$ explicitly cause $U_2$? $\implies$ `CAUSE`.
   - Is $U_1$ an explicit condition for $U_2$? $\implies$ `CONDITION`.
   - Is $U_2$ the explicit purpose of $U_1$? $\implies$ `PURPOSE`.
   - Do they present an explicit contrast? $\implies$ `CONTRAST`.
   - Does $U_2$ hold despite $U_1$? $\implies$ `CONCESSION`.
4. **Temporal Check:**
   - Did $U_1$ end before $U_2$ started? $\implies$ `BEFORE`.
   - Did $U_1$ start after $U_2$ ended? $\implies$ `AFTER`.
   - Do their durations overlap? $\implies$ `OVERLAP`.
   - Ordering unknown? $\implies$ `TEMPORAL_UNKNOWN`.
5. **Default / Control:**
   - Pair examined but no relation exists $\implies$ `NO_RELATION`.
   - Evidence insufficient to decide $\implies$ `UNKNOWN`.

---

## 4. Ambiguous Cases and Resolution Protocols

### Case 1: Polysemous Connectives ("since", "while", "as")
- **"Since":** Can be temporal ("I have lived here since 2020") or causal ("Since the build failed, we postponed deployment").
  - *Resolution:* If purely temporal, annotate `BEFORE` or `OVERLAP`. If expressing cause, annotate `CAUSE`. If genuinely ambiguous, annotate `TEMPORAL_UNKNOWN` and `UNKNOWN`.
- **"While":** Can be temporal overlap ("While I was cooking, the phone rang") or contrast/concession ("While I respect his work, I disagree with his design").
  - *Resolution:* If temporal coexistence $\implies$ `OVERLAP`. If contrastive $\implies$ `CONTRAST` or `CONCESSION`.

### Case 2: Attitude Embedding ("I think I want to leave")
- When an author says "I think I want to leave", is there an attitude about an attitude?
  - *Resolution:* Annotate the primary mental stance as `kind: attitude`, `predicate: leave`, `modality: desired`, `holder: user`. Do not create nested "think" and "want" units unless the text explicitly contrasts the thinking from the wanting.

### Case 3: Negation Scope with Preference ("I don't like Python" vs "I like not having types")
- "I don't like Python": `kind: attitude`, `predicate: like`, `arguments: {experiencer: "I", target: "Python"}`, `polarity: negative`.
- "I like not having types": `kind: attitude`, `predicate: like`, `arguments: {experiencer: "I", target: "not having types"}`, `polarity: positive`.

### Case 4: General Aphorisms vs Personal Beliefs
- "Hard work always pays off" vs "I believe hard work always pays off".
  - *Resolution:* Both represent propositions. If stated as an unhedged claim, `kind: proposition`, `holder: user`, `modality: asserted`. If explicitly hedged as a personal belief ("I believe..."), `kind: attitude`, `predicate: believe`, `arguments: {experiencer: "user", topic: "hard work always pays off"}`.

### Case 5: State Change vs Resulting State ("I moved to London")
- "I moved to London in 2021 and I am living there now."
  - *Resolution:* Decompose into two units:
    - $U_1$: `kind: event`, `predicate: move_to`, `arguments: {actor: "I", target: "London"}`, `time: "2021"`.
    - $U_2$: `kind: state`, `predicate: live_in`, `arguments: {actor: "I", place: "London"}`, `time: "2021-present"`.
    - Relation: $U_1 \text{ CAUSE } U_2$ (or $U_1 \text{ BEFORE } U_2$).

---

## 5. Underdetermined Points in v0.1 (Flagged for v0.2 Calibration)

The v0.1 guideline intentionally refrains from resolving the following edge cases to prevent premature over-specification:

1. **Sub-propositional Modality Scopes:** When multiple modalities appear within a single clause (e.g. "I probably should want to go"), v0.1 selects the dominant matrix modality (`desired`) with reduced confidence ($c = 0.7$). Formal modal compositional trees are deferred to v0.2.
2. **Argument Entity Normalization:** v0.1 stores verbatim argument strings (e.g. `"my previous job"`, `"Acme Corp"`). Entity linking to canonical global entity IDs is deferred to the Typed Meaning Representation layer (Issue #14).
3. **Implicit Discourse Connectives:** Where two sentences appear sequentially without an explicit conjunction (e.g. "The battery died. We couldn't start the car."), v0.1 permits `CAUSE` only if marked `evidence_status: inferred`. Authoritative `explicit` status requires an overt lexical marker.
4. **Graded State Compatibility:** v0.1 enforces binary compatibility (`EQUIVALENT` vs `INCOMPATIBLE`). Degrees of tension or partial overlap (e.g., preference for "hybrid work" vs "fully remote work") are modeled as `CONTRAST` rather than `INCOMPATIBLE`.

---

## 6. Acceptance Checklist for Annotations

Before accepting an annotation document into a golden benchmark:
- [ ] Every unit has a verified, non-empty character span matching the source text.
- [ ] Every unit has valid provenance (`raw_evidence_id`, `semantic_block_id`).
- [ ] No unit or relation uses forbidden cognition labels (`REVISION`, `RECURRENCE`, `TRAJECTORY`, etc.).
- [ ] Roles strictly belong to the 11 approved role labels and are directly grounded in the text.
- [ ] All pairwise relations have positive textual or temporal justification.
- [ ] Ambiguous or unsupported relations are recorded as `UNKNOWN` or `NO_RELATION`.
- [ ] Annotations strictly obey the temporal cutoff of the evaluation run.
