# Semantic Annotation Contract v0.1 — Review Changelog

**Document:** `V0_1_REVIEW_CHANGELOG.md`  
**Issue:** GitHub Issue #13  
**Status:** Frozen Revision & Final Patch Complete  
**Reference Branch:** `research/semantic-annotation-ontology`

This document records all modifications made to v0.1: Part 1 maps the initial 11 post-implementation review recommendations, and Part 2 maps the 4 final patch requirements.

---

## Part 1: Initial Review Points (1–11)

### 1. Split Holder Identity from Attribution Mode
- Replaced categorical `holder` with two orthogonal fields:
  - `holder_ref: str` (e.g. `"user"`, `"Alice"`, `"VP"`, `"system"`, `"unknown"`).
  - `attribution_mode: AttributionMode` (`direct_speaker`, `direct_quote`, `indirect_report`, `external_source`, `unknown`).

### 2. Fix `INCOMPATIBLE` Temporal Semantics
- Added strict temporal validity constraint: `INCOMPATIBLE` requires matching subject, dimension, and scope **with overlapping temporal validity**.
- Cross-time opposite statements are modeled as distinct dated units with opposite polarity/value and a `BEFORE` temporal ordering. Downstream LCE infers belief revision.

### 3. Ground Every Positive Relation Independently
- `SemanticRelation` now requires its own:
  - `provenance: RelationProvenance` (`raw_evidence_id`, `semantic_block_id`).
  - `evidence_status: EvidenceStatus` (`explicit`, `entailed`, `inferred`, `unknown`).
  - `confidence: float` ($0.0 \le c \le 1.0$).
  - `supporting_spans: list<SourceSpan>`.

### 4. Keep Control Labels Out of the Graph
- Defined `CONTROL_RELATION_TYPES = {NO_RELATION, UNKNOWN, TEMPORAL_UNKNOWN}`.
- Added `is_graph_edge` property and `to_graph_edge()` serialization guard that raises a `ValueError` if called on any control label.

### 5. Make `SAME_ENTITY` Representable Over Mentions
- Introduced `ArgumentMention` model with `role`, `text`, optional `source_span`, and optional `entity_ref`.
- (Refined further in Final Patch: see Part 2 Item 1).

### 6. Strengthen Temporal Anchoring
- `TemporalAnchoring` records `normalized_value`, `anchor_type`, `source_expression`, and `reference_anchor`.
- Relative anchors must explicitly specify their reference anchor (e.g. `"evidence:occurred_at"`).

### 7. Remove Unsupported State Manufacture
- Removed and deleted the manufactured state example across all documentation.
- Added explicit negative invariant: Transition events (e.g. "I moved to London") must never invent unstated continuous result states (e.g. "I live in London") without explicit bounded evidence.

### 8. Specify Nested-Attitude Handling
- (Refined in Final Patch: see Part 2 Item 2).

### 9. Make Predicate Normalization Reproducible
- Introduced `PredicateSpec` containing `surface_predicate`, `normalized_predicate`, and `normalization_rule`.
- (Refined in Final Patch: see Part 2 Item 3).

### 10. Correct Research-Stage Numbering
- Standardized stage pipeline: #13 (Annotation Contract) $\to$ #14 (Gold Benchmark) $\to$ #15 (AGY Parser Benchmark & Freeze) $\to$ #16 (Oracle Typed Graph) $\to$ #17 (AGY Graph vs. Oracle).

### 11. Prevent Dual-Schema Drift
- Designated Pydantic schema in `research/semantic_annotation/schema.py` as canonical source of truth.
- Derived `research/schemas/semantic_annotation_v0_1.json` directly from Pydantic and added automated parity test `test_schema_parity()`.

---

## Part 2: Final Patch Requirements

### 1. Stable `mention_id` for Argument Mentions & Mention-Based `SAME_ENTITY`
- **Requirement:** Give every argument/entity mention its own stable `mention_id`; `SAME_ENTITY` must connect mention IDs, not `<unit_id>:<role>` pseudo-identifiers.
- **Change:**
  - Added required `mention_id: str` (e.g. `"m_001"`, `"m_alice_1"`) to `ArgumentMention`.
  - Document-level validation collects all `mention_id`s across all units and enforces global uniqueness.
  - `SAME_ENTITY` relations strictly require `source_id` and `target_id` to be valid, existing `mention_id`s. Any attempt to use `<unit_id>:<role>` strings or non-existent mention IDs triggers a `ValidationError`.

### 2. Nested-Attitude Semantics: Decouple Epistemic Hedge from Modality
- **Requirement:** Do not collapse "I think I want to leave" into `modality=uncertain`, and do not use arbitrary annotation-confidence reduction to encode lost semantics. Preserve desire separately from epistemic hedging with the smallest explicit schema extension necessary.
- **Change:**
  - Introduced `EpistemicHedge` enum on `SemanticUnit`: `NONE = "none"`, `THINK = "think"`, `PROBABLE = "probable"`, `UNCERTAIN = "uncertain"`, `DOUBT = "doubt"`.
  - "I think I want to leave" is now annotated with:
    - `modality: ModalityType.DESIRED` (preserving the desire modal dimension!).
    - `epistemic_hedge: EpistemicHedge.THINK` (preserving the outer epistemic qualification explicitly and independently).
    - `confidence: 1.0` (annotation confidence measures annotator mapping accuracy, not semantic loss).

### 3. Deterministic Mechanical Predicate Normalization
- **Requirement:** Restrict predicate normalization v0.1 to deterministic mechanical normalization. No open-ended synonym/frame canonicalization such as `want ≈ desire ≈ wish` unless backed by an explicit frozen mapping. Gold scoring must be reproducible.
- **Change:**
  - Restricted `normalization_rule` to `PredicateNormalizationRule` enum:
    - `EXACT_SURFACE`: normalized predicate must match lowercase surface form.
    - `LEMMA`: mechanical English base lemma.
    - `COMPOUND_LOWER`: lowercase with whitespace converted to underscores.
    - `FROZEN_MAP`: strictly verified against explicit `FROZEN_PREDICATE_MAP` table.
  - Model validator in `PredicateSpec` programmatically enforces that unlisted synonyms fail validation unless registered in the frozen map.

### 4. Frozen Graph Admission: Inferred Annotations Are Audit-Only
- **Requirement:** Freeze graph admission: `inferred` annotations/relations are audit-only and MUST NOT become positive graph edges in v0.1/#16/#17. Only `explicit` and `entailed` are eligible.
- **Change:**
  - Formalized `GRAPH_ADMISSIBLE_EVIDENCE_STATUSES = {EXPLICIT, ENTAILED}`.
  - On `SemanticUnit`: added `is_graph_eligible` property; `to_graph_node()` raises `ValueError` if `evidence_status` is `inferred` or `unknown`.
  - On `SemanticRelation`: updated `is_graph_edge` property and `to_graph_edge()` method; any relation with `inferred` or `unknown` evidence status raises `ValueError` on serialization.
