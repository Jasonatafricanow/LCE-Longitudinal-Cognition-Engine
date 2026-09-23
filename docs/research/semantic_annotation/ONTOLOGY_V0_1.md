# LCE Semantic Annotation Ontology v0.1

**Status:** Frozen Research Contract (GitHub Issue #13, Final Patch)  
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
| `predicate` | `PredicateSpec` | Deterministic mechanical predicate: `surface_predicate`, `normalized_predicate`, and `normalization_rule`. |
| `arguments` | `map<role, ArgumentMention>` | Conservative semantic roles mapping role names to grounded mentions with stable `mention_id`. |
| `polarity` | `PolarityType` | Truth/affirmation status: `positive`, `negative`, `unknown`. |
| `modality` | `ModalityType` | Inner proposition/desire mode: `asserted`, `possible`, `hypothetical`, `intended`, `desired`, `uncertain`, `unknown`. |
| `epistemic_hedge` | `EpistemicHedge` | Decoupled outer epistemic hedge: `none`, `think`, `probable`, `uncertain`, `doubt`. |
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

### 4.2 Semantic Roles & Argument Mentions (`arguments`)

Arguments are modeled as `ArgumentMention` instances with stable unique identifiers:
- `mention_id`: Stable identifier (e.g. `"m_001"`, `"m_alice_1"`).
- `role`: One of the 11 conservative roles:
  - `actor`, `experiencer`, `theme`, `target`, `stimulus`, `topic`, `place`, `reason`, `purpose`, `result`, `time`.
- `text`: Verbatim argument substring.
- `source_span`: Character span of the mention within the raw evidence.
- `entity_ref`: Optional local entity identifier (e.g. `"ent_user"`, `"ent_bigcorp"`).

*Role Policy:* Roles must only be annotated when directly supported by the source text. Omit unstated roles; **never** invent arguments from world knowledge.

---

### 4.3 Nested Attitude Semantics: Modality vs. Epistemic Hedging

To prevent conflating desire with certainty, and to eliminate arbitrary confidence penalties, v0.1 decouples inner attitude modality from outer epistemic qualification:

1. **`modality`**: Captures the matrix mode of the core proposition or attitude:
   - `asserted`: Unqualified factual claim.
   - `desired`: Want, desire, aspiration, or preference.
   - `intended`: Plan, decision, or future commitment.
   - `possible`: Possibility ("might", "may").
   - `hypothetical`: Conditional or counterfactual ("would if").
   - `uncertain`: Inherently uncertain matrix proposition.
   - `unknown`: Undetermined.
2. **`epistemic_hedge`**: Captures outer epistemic qualification:
   - `none`: Unhedged assertion (default).
   - `think`: Outer belief/opinion hedge ("I think", "I believe").
   - `probable`: Likelihood hedge ("probably", "likely").
   - `uncertain`: Direct epistemic doubt ("wonder if", "not sure if").
   - `doubt`: Negative epistemic hedge ("I doubt that").

*Example:* `"I think I want to leave."`  
- `modality`: `desired` (preserving the desire modal dimension).
- `epistemic_hedge`: `think` (preserving the epistemic qualification explicitly).
- `confidence`: `1.0` (annotation confidence measures mapping accuracy, not semantic loss).

---

### 4.4 Predicate Normalization (`PredicateSpec`)

To ensure gold scoring is 100% reproducible across annotators and automated parsers, open-ended synonym rewriting (e.g. `want ≈ desire ≈ wish`) is **strictly forbidden** in v0.1.

Normalization is restricted to deterministic mechanical rules (`PredicateNormalizationRule`):
- **`exact_surface`**: Normalized predicate must strictly equal the lowercase surface form.
- **`lemma`**: Mechanical lowercased English base lemma (no synonym substitution).
- **`compound_lower`**: Lowercase with whitespace replaced by underscores (e.g. `"drop database"` $\implies$ `"drop_database"`).
- **`frozen_map`**: Verified against an explicit, frozen lookup table ([`FROZEN_PREDICATE_MAP`](file:///c:/projects/LCE/research/semantic_annotation/schema.py)).

---

## 5. Relation Specification (`SemanticRelation`)

Relations link two semantic endpoints. Every relation must be **independently grounded** with its own provenance, evidence status, and confidence.

### 5.1 Relation Fields

| Field | Type | Description |
| :--- | :--- | :--- |
| `relation_id` | `string` | Unique identifier (e.g. `"rel_001"`). |
| `source_id` | `string` | Source endpoint: unit `annotation_id` or argument `mention_id`. |
| `target_id` | `string` | Target endpoint: unit `annotation_id` or argument `mention_id`. |
| `relation_type` | `RelationType` | The relation label. |
| `evidence_status` | `EvidenceStatus` | Grounding of the relation itself: `explicit`, `entailed`, `inferred`, `unknown`. |
| `confidence` | `float` | Annotator confidence in the relation ($0.0 \le c \le 1.0$). |
| `provenance` | `RelationProvenance` | `raw_evidence_id` and `semantic_block_id` where the relation is evidenced. |
| `supporting_spans`| `list<SourceSpan>` | Explicit lexical connective spans (e.g. "because", "although"). |

---

### 5.2 Identity Relations: Mention-Based `SAME_ENTITY`

- **`SAME_ENTITY`**: Strictly connects two stable `mention_id`s (`source_id="m_001", target_id="m_002"`). It denotes coreference between participant mentions.  
  *Strict Invariant:* `SAME_ENTITY` must **never** connect proposition unit IDs or `<unit_id>:<role>` pseudo-identifiers.
- **`SAME_EVENT`**: Connects two event unit IDs (`source_id="u1", target_id="u2"`) denoting the identical real-world event occurrence with identical participants and spatio-temporal bounds.

---

### 5.3 Frozen Graph Admission: Inferred Annotations Are Audit-Only

To ensure empirical validity and prevent ungrounded graph hallucination in Issues #16 and #17:
- **`explicit` and `entailed`** are the **only** evidence statuses eligible for admission into the typed graph.
- **`inferred` and `unknown`** units and relations are **audit-only**. They are retained for annotator review and error tracking, but **MUST NOT** become positive graph nodes or edges. Calling `to_graph_node()` or `to_graph_edge()` on an inferred element triggers a strict runtime error.
- **Control labels** (`NO_RELATION`, `UNKNOWN`, `TEMPORAL_UNKNOWN`) are evaluation outcomes and **MUST NEVER** be serialized as positive graph edges.

---

### 5.4 State Compatibility Invariant

- **`INCOMPATIBLE`**: Requires matching subject, dimension, and scope **with overlapping temporal validity**.
- *Cross-time changes:* If two opposite preferences or states occur at distinct, non-overlapping times (e.g. 2022 preference vs. 2026 preference), they are **not** `INCOMPATIBLE`. They are modeled as two distinct units with distinct temporal anchors and a `BEFORE` temporal ordering. Downstream LCE infers revision/change.
