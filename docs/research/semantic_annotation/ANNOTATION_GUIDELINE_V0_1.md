# LCE Semantic Annotation Guideline v0.1

**Status:** Frozen Research Guideline (GitHub Issue #13, Post-Review Revision)  
**Scope:** Research Only — Applies to annotation contracts, golden benchmarks (Issue #14), and parser validation (Issue #15).  
**Prerequisite:** Readers must review [`ONTOLOGY_V0_1.md`](file:///c:/projects/LCE/docs/research/semantic_annotation/ONTOLOGY_V0_1.md) before applying these guidelines.

---

## 1. Overview and Core Philosophy

This guideline provides the operational manual for annotating semantic units and pairwise relations from text spans within LCE Semantic Blocks.

### Guiding Principles

1. **Source Grounding Over Interpretation:** The annotator must only capture what is linguistically asserted or strictly entailed in the text span. Do not fill missing details from world knowledge, psychological assumptions, or downstream cognitive hypotheses.
2. **First-Class Uncertainty:** `UNKNOWN`, `NO_RELATION`, and `TEMPORAL_UNKNOWN` are valid, necessary outcomes for evaluation. If the text does not supply evidence for a relation or role, record the control outcome. Control outcomes are never persisted as graph edges.
3. **Decoupled Cognition:** The annotator must never assign longitudinal cognitive labels (e.g. `REVISION`, `RECURRENCE`, `TRAJECTORY`, `COGNITIVE_SHIFT`). The annotation contract provides raw semantic building blocks for the cognition engine, not the engine's final conclusions.
4. **No Unsupported State Manufacture:** Transition events (e.g. "I moved to London") must **never** be used to invent unstated continuous result states (e.g. "I live in London").

---

## 2. The 12 Canonical Annotation Rules (Revised)

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

### Rule 4: Decoupled Holder Identity and Attribution Mode
Every unit must explicitly distinguish *who* holds the proposition from *how* it was attributed:
- `holder_ref`: Identify the specific referent (e.g. `"user"`, `"VP"`, `"Alice"`, `"system"`, `"unknown"`).
- `attribution_mode`: Set to `direct_speaker`, `direct_quote`, `indirect_report`, `external_source`, or `unknown`.
Never confuse a third party's quoted assertion with the author's own belief.

### Rule 5: No Inference Promotion
Never promote an inference to `explicit` or `entailed`.
- `explicit`: Directly stated verbatim in the text span.
- `entailed`: Follows by strict deductive necessity.
- `inferred`: Any contextual, pragmatic, or probabilistic assumption. Such units must be labeled `evidence_status: inferred` and are excluded from authoritative graph construction.

### Rule 6: Argument-Mention Grounding for `SAME_ENTITY`
`SAME_ENTITY` is defined over **argument mentions**, not proposition unit IDs.
- Endpoints must target specific argument roles: format `<unit_id>:<role>` (e.g. `u1:actor SAME_ENTITY u2:target`).
- Both endpoints must exist and be valid argument roles on the respective units.
- `SAME_EVENT` remains a relation between event units (`u1 SAME_EVENT u2`), requiring identical participants and spatio-temporal bounds.

### Rule 7: Temporal Adjacency Is Not Causality
The fact that unit $A$ occurred before unit $B$ ($A \text{ BEFORE } B$) is **never** sufficient on its own to assert $A \text{ CAUSE } B$.

### Rule 8: Supported Causality and Independent Relation Grounding
Every positive relation (`CAUSE`, `CONDITION`, `PURPOSE`, `CONTRAST`, `CONCESSION`, etc.) must be independently grounded with its own `provenance`, `evidence_status`, `confidence`, and `supporting_spans` (e.g. pointing to "because", "therefore", "although"). Unit-level status is not inherited by relations.

### Rule 9: Strict Temporal Overlap for `INCOMPATIBLE`
Two units are `INCOMPATIBLE` if and only if:
1. They concern the exact same subject, dimension, and scope; and
2. Their asserted values, states, or polarities cannot simultaneously coexist in the same state of affairs; and
3. **They have overlapping temporal validity**.
*Cross-time changes:* If two opposite preferences or states occur at distinct, non-overlapping times (e.g. 2022 positive vs 2026 negative), they are **not** `INCOMPATIBLE`. They are modeled as two distinct units with distinct temporal anchors and a `BEFORE` temporal ordering. Downstream LCE infers revision/change.

### Rule 10: Control Labels Are Gated From Graph Persistence
`NO_RELATION`, `UNKNOWN`, and `TEMPORAL_UNKNOWN` are annotation and evaluation outcomes only. They are used for inter-annotator agreement and benchmark scoring, and **must never be serialized as positive graph edges**.

### Rule 11: Cutoff Integrity (No Future Leakage)
An annotator or parser evaluating evidence up to cutoff timestamp $t$ must **never** inspect or utilize evidence timestamped after $t$. Later events cannot retroactively modify the semantic parse of an earlier unit.

### Rule 12: Metacognitive Confidence
The `confidence` score ($0.0 \le c \le 1.0$) measures confidence in the **correctness of the annotation mapping**, not whether the real-world proposition is factually true.

---

## 3. Step-by-Step Annotation Procedure

### Step 1: Unit Identification and Span Bounding
1. Read the `SemanticBlock` and note its `raw_evidence_id` and `semantic_block_id`.
2. Segment independent clauses. Identify the exact character span (`char_start`, `char_end`) for each unit.

### Step 2: Assign `kind`, `predicate`, and `normalization_rule`
Record:
- `surface_predicate`: Verbatim verb/predicate string.
- `normalized_predicate`: Standard lemma or frame.
- `normalization_rule`: Name of rule applied (`verb_lemma`, `standard_frame`, `shallow_nested_hedge`, `exact_match`).

### Step 3: Extract Grounded Argument Mentions
Populate `arguments` mapping role to `ArgumentMention`:
- `role`: One of the 11 approved roles (`actor`, `experiencer`, `theme`, `target`, `stimulus`, `topic`, `place`, `reason`, `purpose`, `result`, `time`).
- `text`: Verbatim argument phrase.
- `source_span`: Character span of the argument mention within the raw evidence.
- `entity_ref`: Optional local coreference key (e.g. `"user"`, `"ent_bigcorp"`).
*Rule:* Only annotate roles directly expressed in the text.

### Step 4: Determine Polarity and Modality
- Polarity: `positive`, `negative`, `unknown`.
- Modality: `asserted`, `possible`, `hypothetical`, `intended`, `desired`, `uncertain`, `unknown`.

### Step 5: Assign Holder Reference and Attribution Mode
- `holder_ref`: Identify the entity who holds the proposition (`"user"`, `"Alice"`, `"VP"`, `"system"`).
- `attribution_mode`:
  - Author speaking for self $\implies$ `direct_speaker`.
  - Verbatim quotation in quotation marks $\implies$ `direct_quote`.
  - Indirect speech ("X told me Y") $\implies$ `indirect_report`.
  - External log/doc $\implies$ `external_source`.

### Step 6: Temporal Anchoring
- `normalized_value`: ISO 8601 string or `"unknown"`.
- `anchor_type`: `exact`, `bounded_range`, `relative`, `unanchored`.
- `source_expression`: Verbatim temporal phrase (or null).
- `reference_anchor`: For relative anchors, record what it anchors to (e.g. `"evidence:occurred_at"`).

### Step 7: Pairwise Relation Annotation
1. **Coreference:** Use `SAME_ENTITY` between argument mentions (`u1:actor SAME_ENTITY u2:target`).
2. **Event Identity:** Use `SAME_EVENT` between identical event units.
3. **Discourse / Logic:** Use `CAUSE`, `CONDITION`, `PURPOSE`, `CONTRAST`, `CONCESSION` between units. Provide `supporting_spans` for lexical connectives.
4. **Temporal:** Use `BEFORE`, `AFTER`, `OVERLAP`, `TEMPORAL_UNKNOWN`.
5. **State Compatibility:** Use `EQUIVALENT` or `INCOMPATIBLE` (strictly requiring overlapping temporal validity).
6. **Control:** If no relation or indeterminate, record `NO_RELATION` or `UNKNOWN`.

---

## 4. Policy on Special Cases

### 4.1 Shallow Nested-Attitude Policy
*Example:* `"I think I want to leave."`
- In v0.1's shallow propositional schema, nested attitude ASTs are flattened into the matrix attitude:
  - `kind`: `attitude`
  - `surface_predicate`: `"think I want to leave"`
  - `normalized_predicate`: `"leave"`
  - `normalization_rule`: `"shallow_nested_hedge"`
  - `modality`: `uncertain` (preserving the epistemic hedge of "think")
  - `confidence`: `0.70` (reflecting shallow scope compression)
- *Prohibition:* Never silently convert a hedged thought ("I think I want") into an unhedged `desired` modality.

### 4.2 Prohibition on Result-State Manufacture
*Example:* `"I moved to London in 2021."`
- The text only asserts an event of relocation.
- **Correct:** A single unit:
  - `kind`: `event`, `predicate`: `move_to`, `actor`: `"I"`, `target`: `"London"`, `time`: `"2021"`.
- **Forbidden:** Do **not** invent an unstated second unit `kind: state, predicate: live_in, place: London` and link it via `CAUSE`. Persistent result states must be explicitly stated in the text to be annotated.

### 4.3 Longitudinal Preference Shifts (2022 vs. 2026)
*Example:*
- 2022: `"I really want to work at a big tech company."`
- 2026: `"I will never work at a big company again."`
- **Correct Representation:**
  - $U_1$: `kind: attitude`, `predicate: work_at`, `target: big tech company`, `polarity: positive`, `modality: desired`, `time: 2022`.
  - $U_2$: `kind: attitude`, `predicate: work_at`, `target: big company`, `polarity: negative`, `modality: intended`, `time: 2026`.
  - Relations:
    - $U_1 \text{ BEFORE } U_2$
    - $U_1 \text{:target SAME_ENTITY } U_2\text{:target}$
  - **Forbidden:** $U_1 \text{ INCOMPATIBLE } U_2$ is invalid because their times do not overlap! $U_1 \text{ REVISION } U_2$ is strictly forbidden as a downstream cognition label.
