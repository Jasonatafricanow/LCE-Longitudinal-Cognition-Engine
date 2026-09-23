# LCE Semantic Annotation Ontology v0.1

**Status:** Frozen Research Contract (GitHub Issue #13, Post-Review Revision)  
**Scope:** Research Only — Does not modify production runtime or contracts  
**Audience:** Human annotators, synthetic annotation pipeline authors, semantic parser implementers  

---

## 1. Architectural Role and System Boundary

The Longitudinal Cognition Engine (LCE) processes unstructured longitudinal evidence across extended temporal horizons. To prevent ungrounded hallucinations, candidate explosion, and circular reasoning, LCE maintains a strict separation of concerns across its representation layers:

```text
Raw Evidence
  │
  ▼
Semantic Boundary / Evidence Span (Semantic Block)   <-- Upstream boundary layer (LCE V1)
  │
  ▼
Semantic Parsing (Atomic Units & Local Relations)     <-- THIS CONTRACT (Issue #13)
  │
  ▼
Gold Benchmark Dataset                                <-- Issue #14
  │
  ▼
AGY Semantic Parser Benchmark & Freeze                <-- Issue #15
  │
  ▼
Oracle Typed Graph Representation                     <-- Issue #16
  │
  ▼
AGY Graph vs. Oracle Comparison Experiment            <-- Issue #17
  │
  ▼
Longitudinal Interpretation (Cognition State / Belief)<-- Downstream engine (LCE Core)
```

### 1.1 Critical Distinction: Semantic Block vs. Semantic Parse

A **Semantic Block** in LCE is strictly a **semantic-boundary unit**, not a semantic parse:
- **What a Semantic Block is:** An evidence-span segmentation boundary that answers *which pieces of raw evidence belong together* in a coherent context. It provides temporal bounding (`occurred_start`, `occurred_end`), source lineage, and bounded grouping.
- **What a Semantic Block is NOT:** It is **not** a proposition, **not** an event extraction, **not** a role labeling, **not** a modality/polarity assignment, and **not** a typed relation graph.
- **Rule of Non-Conflation:** Under no circumstances should a Semantic Block be renamed or treated as a semantic parse. The output of the semantic parser defined herein operates *within* and *across* Semantic Blocks, taking Semantic Blocks as upstream input provenance.

### 1.2 Boundary with Longitudinal Interpretation

The semantic parser defined in this ontology outputs **descriptive, atomic, source-grounded semantic facts** and **direct local relations**. It does **not** make longitudinal or cognitive-level inferences. Downstream cognition labels (such as belief shifts, trajectory changes, or preference revisions) are strictly the responsibility of the downstream Longitudinal Interpretation layer and are **forbidden** within this parser ontology.

---

## 2. Canonical Schema Designation

To prevent schema drift across implementations:
- **Canonical Schema:** The Python Pydantic specification in [`research/semantic_annotation/schema.py`](file:///c:/projects/LCE/research/semantic_annotation/schema.py) is designated as the single canonical source of truth for v0.1.
- **Parity Schema:** The JSON Schema in [`research/schemas/semantic_annotation_v0_1.json`](file:///c:/projects/LCE/research/schemas/semantic_annotation_v0_1.json) is derived directly from the canonical Pydantic model and verified via automated parity regression tests.

---

## 3. Semantic Unit Specification (`SemanticUnit`)

A `SemanticUnit` is the atomic building block of meaning. It represents a single proposition, event, state, or attitude expressed within a bounded text span.

### 3.1 Unit Fields

Every `SemanticUnit` must provide the following fields:

| Field | Type | Description |
| :--- | :--- | :--- |
| `annotation_id` | `string` | Unique identifier (e.g. `"anno_001"`). |
| `provenance` | `UnitProvenance` | Mandatory links to upstream source: `raw_evidence_id` and `semantic_block_id`. |
| `source_span` | `SourceSpan` | Bounded character offsets (`char_start`, `char_end`) and verbatim `text`. |
| `kind` | `UnitKind` | Coarse category: `event`, `state`, `proposition`, `attitude`. |
| `predicate` | `PredicateSpec` | Reproducible predicate representation: `surface_predicate`, `normalized_predicate`, and `normalization_rule`. |
| `arguments` | `map<role, ArgumentMention>` | Conservative semantic roles mapping defined role names to grounded argument mentions. |
| `polarity` | `PolarityType` | Truth/affirmation status: `positive`, `negative`, `unknown`. |
| `modality` | `ModalityType` | Epistemic/intentional mode: `asserted`, `possible`, `hypothetical`, `intended`, `desired`, `uncertain`, `unknown`. |
| `holder_ref` | `string` | Referent of the proposition holder (e.g. `"user"`, `"VP"`, `"Alice"`, `"system"`, `"unknown"`). |
| `attribution_mode` | `AttributionMode` | Attribution mechanism: `direct_speaker`, `direct_quote`, `indirect_report`, `external_source`, `unknown`. |
| `temporal_anchoring` | `TemporalAnchoring` | Normalized temporal value, `anchor_type`, `source_expression`, and `reference_anchor`. |
| `evidence_status` | `EvidenceStatus` | Grounding level: `explicit`, `entailed`, `inferred`, `unknown`. |
| `confidence` | `float` | Annotator confidence in the annotation accuracy ($0.0 \le c \le 1.0$). |

---

## 4. Vocabulary Definitions

### 4.1 Unit Kind (`kind`)

- **`event`**: A dynamic occurrence, action, transition, or change of state occurring at an instantaneous point or over an explicit bounded duration.  
  *Example:* "I submitted my resignation to Acme Corp yesterday."
- **`state`**: A static condition, continuous property, ongoing relationship, or status holding over an interval without asserting internal change.  
  *Example:* "I live in Berlin." / "The server is running out of memory."
- **`proposition`**: A general assertion, factual claim, universal statement, or timeless rule not anchored to an individual's immediate physical state or singular occurrence.  
  *Example:* "Distributed systems are inherently prone to network partitions."
- **`attitude`**: A mental stance, valuation, desire, preference, or emotional feeling held by a cognitive agent toward a target, topic, or proposition.  
  *Example:* "I prefer remote work." / "I hate corporate bureaucracy."

---

### 4.2 Semantic Roles (`arguments`)

Semantic roles in v0.1 are intentionally conservative and borrow from standard semantic-role frameworks (PropBank, VerbNet, UMR) rather than inventing domain-specific labels:

- **`actor`**: The volitional entity initiating, driving, or executing an action or event.
- **`experiencer`**: The cognitive or sentient entity experiencing a psychological state, feeling, perception, or attitude.
- **`theme`**: The entity undergoing an action, moving, changing state, or being described, without initiating volition.
- **`target`**: The entity, person, institution, or proposition toward which an action or attitude is directed.
- **`stimulus`**: The external event, entity, or circumstance that evokes an experience, reaction, or mental state.
- **`topic`**: The general subject matter, domain, or theme of a proposition, discussion, or thought.
- **`place`**: The physical, virtual, or geographical location where an event or state occurs.
- **`reason`**: The stated justification, explanation, or motivation for an event, state, or attitude.
- **`purpose`**: The intended outcome, goal, or objective behind an action.
- **`result`**: The actual consequence, subsequent state, or product resulting from an event.
- **`time`**: An explicit temporal phrase or anchor within the text span (e.g. "in October 2024").

*Role Policy:* Roles must only be annotated when directly supported by the source text. Omit unstated roles; **never** invent arguments from world knowledge.

---

### 4.3 Holder Identity vs. Attribution Mode

To avoid conflating *who* holds a proposition with *how* it was conveyed in text, v0.1 decouples them into two orthogonal fields:

1. **`holder_ref`**: A string indicating the referent who holds the belief, state, or action:
   - `"user"`: The first-person author/speaker.
   - Named entity / role: E.g. `"Alice"`, `"VP"`, `"mentor"`, `"team_lead"`.
   - `"system"`: Automated engine or log source.
   - `"unknown"`: Unattributable source.
2. **`attribution_mode`**:
   - **`direct_speaker`**: Author asserts it directly in their own voice.
   - **`direct_quote`**: Directly quoted verbatim speech/text (e.g. enclosed in quotes).
   - **`indirect_report`**: Indirect reporting or hearsay (e.g. "Bob told me that...").
   - **`external_source`**: Document, system log, or prompt context.
   - **`unknown`**: Attribution mode cannot be resolved.

---

### 4.4 Temporal Anchoring (`temporal_anchoring`)

- `normalized_value`: Standardized ISO 8601 string (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`, `YYYY-MM-DDTHH:MM:SSZ`), date range, or `"unknown"`.
- `anchor_type`:
  - `exact`: Precise calendar date or timestamp explicitly stated.
  - `bounded_range`: Bounded temporal window (e.g. "Q3 2023", "Summer 2024").
  - `relative`: Expressed relative to a reference time (e.g. "yesterday", "next week").
  - `unanchored`: Timeless proposition or unanchorable statement.
- `source_expression`: Verbatim temporal phrase from the span (e.g. "last Tuesday").
- `reference_anchor`: For relative anchors, the explicit base anchor (e.g. `"evidence:occurred_at"`, `"doc_time"`). If unresolved, it remains explicit rather than guessed.

---

### 4.5 Predicate Normalization (`PredicateSpec`)

To ensure evaluation does not fail due to unconstrained synonym choices:
- `surface_predicate`: The verbatim verb, adjective, or predicate phrase from the source text.
- `normalized_predicate`: Standardized lemma or canonical frame label.
- `normalization_rule`: The deterministic rule applied:
  - `"verb_lemma"`: English lemmatization (e.g. `"resigned"` $\implies$ `"resign"`).
  - `"standard_frame"`: Canonical frame (e.g. `"love"`, `"like"` $\implies$ `"prefer"` or `"desire"`).
  - `"shallow_nested_hedge"`: Policy for flattened nested attitudes.
  - `"exact_match"`: Surface matches normalized lemma.

---

## 5. Relation Specification (`SemanticRelation`)

Relations link two semantic endpoints. Every relation must be **independently grounded** with its own provenance, evidence status, and confidence.

### 5.1 Relation Fields

| Field | Type | Description |
| :--- | :--- | :--- |
| `relation_id` | `string` | Unique identifier (e.g. `"rel_001"`). |
| `source_id` | `string` | Source endpoint (`unit_id` or argument mention `unit_id:role`). |
| `target_id` | `string` | Target endpoint (`unit_id` or argument mention `unit_id:role`). |
| `relation_type` | `RelationType` | The relation label. |
| `evidence_status` | `EvidenceStatus` | Grounding of the relation itself: `explicit`, `entailed`, `inferred`, `unknown`. |
| `confidence` | `float` | Annotator confidence in the relation ($0.0 \le c \le 1.0$). |
| `provenance` | `RelationProvenance` | `raw_evidence_id` and `semantic_block_id` where the relation is evidenced. |
| `supporting_spans`| `list<SourceSpan>` | Explicit lexical connective spans (e.g. "because", "although"). |

---

### 5.2 Relation Ontology Categories

#### 1. Identity Relations (Argument Mention Endpoints)
- **`SAME_ENTITY`**: Links two argument mentions (format: `<unit_id>:<role>`, e.g. `u1:actor SAME_ENTITY u2:target`). Denotes coreference between participant mentions. It is **never** drawn between two proposition unit IDs.
- **`SAME_EVENT`**: Links two event units (`u1 SAME_EVENT u2`) denoting the identical real-world event occurrence with identical participants and spatio-temporal bounds.

#### 2. Temporal Relations (Unit Endpoints)
- **`BEFORE`**: `source_id` concluded before `target_id` began.
- **`AFTER`**: `source_id` began after `target_id` concluded.
- **`OVERLAP`**: The durations of `source_id` and `target_id` intersect.
- **`TEMPORAL_UNKNOWN`**: Both units have temporal extent, but relative order is indeterminate. (Control label; never persisted as graph edge).

#### 3. Logical / Discourse Relations (Unit Endpoints)
- **`CAUSE`**: `source_id` explicitly caused or produced `target_id`. Requires explicit connective or clear causal discourse framing.
- **`CONDITION`**: `source_id` is a conditional premise for `target_id` ("if P, then Q").
- **`PURPOSE`**: `target_id` is the goal of action `source_id` ("P in order to Q").
- **`CONTRAST`**: Antithetical viewpoints or contrasting states without mutual exclusion.
- **`CONCESSION`**: `target_id` holds unexpectedly despite `source_id` ("although P, Q").

#### 4. State Compatibility Relations (Unit Endpoints)
- **`EQUIVALENT`**: `source_id` and `target_id` express semantically equivalent propositions/states over the same scope.
- **`INCOMPATIBLE`**: `source_id` and `target_id` assert mutually exclusive states/attitudes about the same subject, dimension, and scope **with overlapping temporal validity**.  
  *Crucial Temporal Invariant:* Opposite states or attitudes occurring at **distinct, non-overlapping times** (e.g., 2022 preference vs 2026 preference) are **not** `INCOMPATIBLE`. They are modeled as distinct units with distinct temporal anchors and a `BEFORE` temporal ordering. Downstream LCE infers revision/shift. `INCOMPATIBLE` is reserved strictly for contemporaneous/overlapping mutual exclusion.

#### 5. Control Outcomes (Evaluation Only)
- **`NO_RELATION`**: Evaluated pair has no semantic, temporal, or logical relation.
- **`UNKNOWN`**: Indeterminate from available context.
- **Rule of Graph Gating:** Control labels (`NO_RELATION`, `UNKNOWN`, `TEMPORAL_UNKNOWN`) are evaluation outcomes and **must never be serialized as positive graph edges**.

---

## 6. Explicitly Forbidden Downstream Labels (Negative Invariants)

The semantic parser must **never** output cognitive or longitudinal interpretation labels:

`REVISION`, `RECURRENCE`, `TRAJECTORY`, `STABLE_PREFERENCE`, `COGNITIVE_SHIFT`, `LONG_TERM_BELIEF`, `LONG_TERM_IDENTITY`, `SUPPORTS_LONGITUDINAL_COGNITION`, `SUPERCEDES_LONG_TERM_BELIEF`.

Attempting to serialize these labels in `kind`, `predicate`, or `relation_type` triggers strict validation errors.

---

## 7. Shallow Nested-Attitude Policy

v0.1 employs a shallow propositional schema (no nested AST):
- When an attitude embeds another attitude/thought (e.g. *"I think I want to leave"*):
  1. The inner attitude is extracted: `kind: attitude`, `predicate: leave`.
  2. If hedged with epistemic doubt ("think", "wonder"), the epistemic uncertainty is preserved by setting `modality: uncertain` and lowering confidence ($c \le 0.70$).
  3. The normalization rule is recorded as `"shallow_nested_hedge"`.
  4. The annotator must **never** silently promote a hedged belief-about-desire into an unhedged `desired` modality.
