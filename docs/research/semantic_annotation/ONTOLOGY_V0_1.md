# LCE Semantic Annotation Ontology v0.1

**Status:** Frozen Research Contract (GitHub Issue #13)  
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
Typed Meaning Representation (Proposition Graph)      <-- Downstream representation (Issue #14)
  │
  ▼
Graph / Structure Discovery (Topological Analysis)    <-- Downstream discovery (Issue #15)
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

## 2. Semantic Unit Specification (`SemanticUnit`)

A `SemanticUnit` is the atomic building block of meaning. It represents a single proposition, event, state, or attitude expressed within a bounded text span.

### 2.1 Unit Fields

Every `SemanticUnit` must provide the following fields:

| Field | Type | Description |
| :--- | :--- | :--- |
| `annotation_id` | `string` | Unique identifier (e.g. `"anno_001"`). |
| `provenance` | `object` | Mandatory links to upstream source material: `raw_evidence_id` and `semantic_block_id`. |
| `source_span` | `object` | Bounded character offsets (`char_start`, `char_end`) and verbatim `text`. |
| `kind` | `enum` | Coarse semantic category: `event`, `state`, `proposition`, `attitude`. |
| `predicate` | `string` | Normalized lemma or frame label (e.g. `"work_at"`, `"want"`, `"resign"`). |
| `arguments` | `map<role, string>` | Conservative semantic roles mapping defined role names to textual arguments. |
| `polarity` | `enum` | Truth/affirmation status: `positive`, `negative`, `unknown`. |
| `modality` | `enum` | Epistemic/intentional mode: `asserted`, `possible`, `hypothetical`, `intended`, `desired`, `uncertain`, `unknown`. |
| `holder` | `enum` | Attributed speaker or source: `user`, `quoted`, `reported`, `system`, `unknown`. |
| `temporal_anchoring` | `object` | Temporal anchoring specifying `value`, `anchor_type`, and optional `source_expression`. |
| `evidence_status` | `enum` | Grounding level: `explicit`, `entailed`, `inferred`, `unknown`. |
| `confidence` | `float` | Annotator confidence in the annotation accuracy ($0.0 \le c \le 1.0$). |

---

## 3. Vocabulary Definitions

### 3.1 Unit Kind (`kind`)

- **`event`**: A dynamic occurrence, action, transition, or change of state occurring at an instantaneous point or over an explicit bounded duration.  
  *Example:* "I resigned from Acme Corp yesterday."
- **`state`**: A static condition, continuous property, ongoing relationship, or status holding over an interval without asserting internal change.  
  *Example:* "I live in Berlin." / "The project is underfunded."
- **`proposition`**: A general assertion, factual claim, universal statement, or timeless rule not anchored to an individual's immediate physical state or singular occurrence.  
  *Example:* "Distributed systems are inherently prone to network partitions."
- **`attitude`**: A mental stance, valuation, desire, preference, or emotional feeling held by a cognitive agent toward a target, topic, or proposition.  
  *Example:* "I prefer remote work." / "I hate corporate bureaucracy."

---

### 3.2 Semantic Roles (`arguments`)

Semantic roles in v0.1 are intentionally conservative and borrow from standard semantic-role frameworks (PropBank, VerbNet, UMR) rather than inventing domain-specific labels.

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

### 3.3 Polarity (`polarity`)

- **`positive`**: The unit is asserted as affirmatively holding or true.  
  *Example:* "I joined the committee." (`polarity: positive`)
- **`negative`**: The unit is explicitly negated or denied.  
  *Example:* "I did not join the committee." (`polarity: negative`)
- **`unknown`**: Polarity is ambiguous, undecidable, or obscured by the source text.

---

### 3.4 Modality (`modality`)

- **`asserted`**: Expressed as an actual, real-world fact or reality in the author's world.
- **`possible`**: Expressed as an epistemic possibility ("might", "may", "could").
- **`hypothetical`**: Expressed under a conditional, counterfactual, or hypothetical premise ("if", "would", "assuming").
- **`intended`**: Expressed as a planned future action, commitment, or decision ("will", "plan to", "aim to").
- **`desired`**: Expressed as a want, wish, aspiration, or preference ("hope to", "want", "wish").
- **`uncertain`**: The speaker explicitly expresses doubt or epistemic ambiguity ("not sure whether", "doubtful").
- **`unknown`**: The modality cannot be reliably determined.

---

### 3.5 Holder / Source (`holder`)

- **`user`**: The first-person author/speaker of the diary, log, or evidence session.
- **`quoted`**: A directly quoted third party whose exact words are cited.
- **`reported`**: A third party whose statements, thoughts, or actions are indirectly reported by the author.
- **`system`**: An automated agent, system log, external tool, or prompt environment.
- **`unknown`**: Source cannot be determined from the span or immediate context.

---

### 3.6 Evidence Status (`evidence_status`)

- **`explicit`**: Directly stated verbatim in the text span.
- **`entailed`**: Strictly and inevitably follows from the text by direct logical deduction without additional world assumptions.
- **`inferred`**: Plausible, probabilistic, or pragmatic inference (e.g. conversational implicature).  
  *Experiment Gate:* Only `explicit` and `entailed` units are eligible for the initial typed-graph experiments. `inferred` units must remain auditable, distinct, and non-authoritative.
- **`unknown`**: Status cannot be determined.

---

### 3.7 Temporal Anchoring (`temporal_anchoring`)

- `value`: Standardized ISO 8601 string (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`, `YYYY-MM-DDTHH:MM:SSZ`), date range, or `"unknown"`.
- `anchor_type`:
  - `exact`: Precise timestamp or calendar date explicitly given.
  - `bounded_range`: Bounded temporal window (e.g. "Summer 2023", "Q1 2025").
  - `relative`: Relative to reference time / session time (e.g. "two days ago", "next month").
  - `unanchored`: Completely unanchored in time or timeless proposition.
- `source_expression`: Verbatim temporal phrase from the span (or null if unanchored).

---

## 4. Initial Relation Ontology (`SemanticRelation`)

Relations link two `SemanticUnit` instances (`source_id` and `target_id`). The v0.1 relation ontology is deliberately compact and constrained to verifiable linguistic, temporal, and logical connections.

### 4.1 Identity Relations

- **`SAME_ENTITY`**: The entity argument in the source unit corefers with the entity argument in the target unit.
- **`SAME_EVENT`**: The source unit and target unit describe the identical real-world event (requiring identical participants, spatio-temporal bounds, and event type).

### 4.2 Temporal Relations

- **`BEFORE`**: The event/state in `source_id` concluded before the event/state in `target_id` began.
- **`AFTER`**: The event/state in `source_id` began after the event/state in `target_id` concluded.
- **`OVERLAP`**: The temporal extents of `source_id` and `target_id` intersect or coincide.
- **`TEMPORAL_UNKNOWN`**: Both units have temporal extent, but their relative chronological ordering is indeterminate.

### 4.3 Logical and Discourse Relations

- **`CAUSE`**: `source_id` is asserted as causing, bringing about, or producing `target_id`. Requires explicit linguistic connectives or incontrovertible causal discourse framing.
- **`CONDITION`**: `source_id` is a conditional premise or contingency required for `target_id` ("if P, then Q").
- **`PURPOSE`**: `target_id` is the stated goal or objective behind the action in `source_id` ("P in order to Q").
- **`CONTRAST`**: `source_id` and `target_id` present contrasting, differing, or antithetical viewpoints or situations without asserting direct logical impossibility.
- **`CONCESSION`**: `target_id` holds unexpectedly despite the circumstance expressed in `source_id` ("although P, Q").

### 4.4 State Compatibility Relations

- **`EQUIVALENT`**: `source_id` and `target_id` express semantically equivalent propositions/states holding over the same scope.
- **`INCOMPATIBLE`**: `source_id` and `target_id` assert contradictory or mutually exclusive states/attitudes about the same subject, dimension, and scope.  
  *Temporal Note:* If two incompatible attitudes or states occur at different times ($t_1 < t_2$), they are still annotated as `INCOMPATIBLE` with their respective temporal anchors and a `BEFORE` temporal relation. They are **not** labeled as a revision.

### 4.5 Control Relations

- **`NO_RELATION`**: The annotator or system evaluated the pair and explicitly determined that no direct semantic, temporal, or logical relation exists.
- **`UNKNOWN`**: The relationship between the two units is ambiguous or cannot be determined from the available context.

---

## 5. Explicitly Forbidden Downstream Labels (Negative Invariants)

To preserve the falsifiability of LCE's cognitive discovery pipeline, the semantic parser must **never** output cognitive or longitudinal interpretation labels.

The following labels are **strictly forbidden** in v0.1:

| Forbidden Label | Rationale | Allowed Lower-Level Representation |
| :--- | :--- | :--- |
| `REVISION` | Conflates longitudinal shift with local semantic incompatibility. | `P1 INCOMPATIBLE P2` + `P1 BEFORE P2` with different timestamps. |
| `RECURRENCE` | Smuggles multi-session cognitive pattern into pairwise parse. | `P1 EQUIVALENT P2` + `P1 BEFORE P2` with distinct temporal anchors. |
| `TRAJECTORY` | Global sequence property, not an atomic parse. | Chain of `BEFORE` / `CAUSE` relations across dated units. |
| `STABLE_PREFERENCE` | A longitudinal hypothesis requiring cross-cutoff persistence. | Individual `attitude` units with `modality: desired` / `polarity: positive`. |
| `COGNITIVE_SHIFT` | Interpretative conclusion belonging to the cognition engine. | Distinct incompatible attitudes/states linked across time. |
| `LONG_TERM_BELIEF` | Smuggles cognitive duration into an instantaneous observation. | Atomic `proposition` or `attitude` with bounded temporal anchor. |
| `LONG_TERM_IDENTITY` | Sociological/psychological concept outside semantic parsing. | Atomic `state` units attributing traits or roles to an actor. |
| `SUPPORTS_LONGITUDINAL_COGNITION`| Meta-level system utility judgment, not a linguistic fact. | Excluded entirely. |
| `SUPERCEDES_LONG_TERM_BELIEF` | Downstream belief maintenance decision. | Excluded entirely from parser. Handled by LCE reference memory / recovery. |

---

## 6. Cutoff Invariant

The semantic annotation contract obeys LCE's global cutoff principle:
- An annotation generated at temporal cutoff $t$ must only inspect evidence where `occurred_at` $\le t$.
- No unit or relation may use future information ($t' > t$) to resolve ambiguity, determine polarity, or establish causality.
- Retrospective annotations (e.g., author in 2026 describing an event in 2022) must anchor the event to 2022 while recording the statement's utterance time as 2026.
