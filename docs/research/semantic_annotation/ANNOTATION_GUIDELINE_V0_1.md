# LCE Semantic Annotation Guideline v0.1

**Status:** Frozen Research Guideline (GitHub Issue #13, Final Patch)  
**Scope:** Research Only — Applies to annotation contracts, golden benchmarks (Issue #14), and parser validation (Issue #15).  
**Prerequisite:** Readers must review [`ONTOLOGY_V0_1.md`](file:///c:/projects/LCE/docs/research/semantic_annotation/ONTOLOGY_V0_1.md) before applying these guidelines.

---

## 1. Overview and Core Philosophy

This guideline provides the operational manual for annotating semantic units and pairwise relations from text spans within LCE Semantic Blocks.

### Guiding Principles

1. **Source Grounding Over Interpretation:** The annotator must only capture what is linguistically asserted or strictly entailed in the text span. Do not fill missing details from world knowledge, psychological assumptions, or downstream cognitive hypotheses.
2. **First-Class Uncertainty & Audit-Only Inferences:** `UNKNOWN`, `NO_RELATION`, and `TEMPORAL_UNKNOWN` are valid, necessary outcomes for evaluation. Inferred annotations are audit-only and gated from positive graph admission.
3. **Decoupled Cognition:** The annotator must never assign longitudinal cognitive labels (e.g. `REVISION`, `RECURRENCE`, `TRAJECTORY`, `COGNITIVE_SHIFT`). The annotation contract provides raw semantic building blocks for the cognition engine, not the engine's final conclusions.
4. **Deterministic Reproducibility:** Predicate normalization is strictly mechanical. Open-ended synonym canonicalization (e.g. `want ≈ desire ≈ wish`) without a frozen lookup table is prohibited.

---

## 2. The 12 Canonical Annotation Rules (Final Patch)

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
- `inferred`: Any contextual, pragmatic, or probabilistic assumption. Such units must be labeled `evidence_status: inferred` and remain audit-only.

### Rule 6: Stable Mention IDs for `SAME_ENTITY`
Every argument mention must be assigned its own stable unique `mention_id` (e.g. `"m_001"`, `"m_alice_1"`).
- `SAME_ENTITY` strictly connects two stable `mention_id`s (`source_id="m_001", target_id="m_002"`).
- Pseudo-identifiers such as `<unit_id>:<role>` are **strictly forbidden**.
- `SAME_EVENT` remains the relation between event unit IDs (`u1 SAME_EVENT u2`), requiring identical participants and spatio-temporal bounds.

### Rule 7: Temporal Adjacency Is Not Causality
The fact that unit $A$ occurred before unit $B$ ($A \text{ BEFORE } B$) is **never** sufficient on its own to assert $A \text{ CAUSE } B$.

### Rule 8: Supported Causality and Independent Relation Grounding
Every positive relation (`CAUSE`, `CONDITION`, `PURPOSE`, `CONTRAST`, `CONCESSION`, etc.) must be independently grounded with its own `provenance`, `evidence_status`, `confidence`, and `supporting_spans` (pointing to "because", "therefore", "although").

### Rule 9: Strict Temporal Overlap for `INCOMPATIBLE`
Two units are `INCOMPATIBLE` if and only if:
1. They concern the exact same subject, dimension, and scope; and
2. Their asserted values, states, or polarities cannot simultaneously coexist in the same state of affairs; and
3. **They have overlapping temporal validity**.
*Cross-time changes:* If two opposite preferences or states occur at distinct, non-overlapping times (e.g. 2022 positive vs 2026 negative), they are **not** `INCOMPATIBLE`. They are modeled as two distinct units with distinct temporal anchors and a `BEFORE` temporal ordering. Downstream LCE infers revision/change.

### Rule 10: Frozen Graph Admission (Inferred is Audit-Only)
In v0.1 and subsequent graph experiments (#16/#17):
- Only `explicit` and `entailed` units and relations are admitted as positive graph nodes and edges.
- `inferred` units and relations are **audit-only** and **MUST NOT** be admitted into the graph.
- Control labels (`NO_RELATION`, `UNKNOWN`, `TEMPORAL_UNKNOWN`) are evaluation outcomes and **MUST NEVER** be serialized as positive graph edges.

### Rule 11: Cutoff Integrity (No Future Leakage)
An annotator or parser evaluating evidence up to cutoff timestamp $t$ must **never** inspect or utilize evidence timestamped after $t$. Later events cannot retroactively modify the semantic parse of an earlier unit.

### Rule 12: Metacognitive Confidence
The `confidence` score ($0.0 \le c \le 1.0$) measures confidence in the **correctness of the annotation mapping**, not whether the real-world proposition is factually true. Do not use confidence penalties to encode lost semantics or structural compromises.

---

## 3. Step-by-Step Annotation Procedure

### Step 1: Unit Identification and Span Bounding
1. Read the `SemanticBlock` and note its `raw_evidence_id` and `semantic_block_id`.
2. Segment independent clauses. Identify the exact character span (`char_start`, `char_end`) for each unit.

### Step 2: Mechanical Predicate Normalization
Populate `PredicateSpec`:
- `surface_predicate`: Verbatim verb/predicate string from text.
- `normalization_rule`: Select one of the frozen deterministic rules:
  - `exact_surface`: Normalized matches lowercase surface form.
  - `lemma`: Mechanical base lemma.
  - `compound_lower`: Lowercase with underscores.
  - `frozen_map`: Explicit entry in `FROZEN_PREDICATE_MAP`.
- `normalized_predicate`: The mechanically derived predicate. (Open-ended synonym rewriting is prohibited).

### Step 3: Extract Grounded Argument Mentions with Stable IDs
For each argument role present in the text:
- Assign a globally unique `mention_id` (e.g. `"m_001"`).
- Record `role` from the 11 approved roles (`actor`, `experiencer`, `theme`, `target`, `stimulus`, `topic`, `place`, `reason`, `purpose`, `result`, `time`).
- Record `text`, optional `source_span`, and optional `entity_ref`.

### Step 4: Modality and Epistemic Hedging
- `modality`: Record the core mode of the proposition/attitude (`asserted`, `desired`, `intended`, `possible`, `hypothetical`, `uncertain`, `unknown`).
- `epistemic_hedge`: Record outer epistemic qualification separately:
  - `"I think I want to leave"` $\implies$ `modality: desired`, `epistemic_hedge: think`, `confidence: 1.0`.
  - Do not collapse desire into `uncertain`, and do not penalize confidence.

### Step 5: Assign Holder Reference and Attribution Mode
- `holder_ref`: Identify the entity who holds the proposition (`"user"`, `"Alice"`, `"VP"`, `"system"`).
- `attribution_mode`: `direct_speaker`, `direct_quote`, `indirect_report`, `external_source`, or `unknown`.

### Step 6: Temporal Anchoring
- `normalized_value`: ISO 8601 string or `"unknown"`.
- `anchor_type`: `exact`, `bounded_range`, `relative`, `unanchored`.
- `source_expression`: Verbatim temporal phrase.
- `reference_anchor`: For relative anchors, record what it anchors to (e.g. `"evidence:occurred_at"`).

### Step 7: Pairwise Relation Annotation
1. **Coreference:** Use `SAME_ENTITY` strictly connecting stable mention IDs (`m_001 SAME_ENTITY m_002`).
2. **Event Identity:** Use `SAME_EVENT` between event unit IDs.
3. **Discourse / Logic:** Use `CAUSE`, `CONDITION`, `PURPOSE`, `CONTRAST`, `CONCESSION` between units with `supporting_spans`.
4. **State Compatibility:** Use `EQUIVALENT` or `INCOMPATIBLE` (strictly requiring overlapping temporal validity).
5. **Control:** Record `NO_RELATION` or `UNKNOWN` where applicable (gated from graph).
