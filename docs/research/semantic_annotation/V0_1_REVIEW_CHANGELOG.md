# Semantic Annotation Contract v0.1 — Review Changelog

**Document:** `V0_1_REVIEW_CHANGELOG.md`  
**Issue:** GitHub Issue #13  
**Status:** Frozen Revision  
**Reference Commit:** Revising initial draft on branch `research/semantic-annotation-ontology`

This document provides a point-by-point mapping of the 11 review recommendations to the concrete modifications made in the schema, ontology, guidelines, examples, and test suite.

---

### 1. Split Holder Identity from Attribution Mode
- **Problem:** Previous draft used `holder: user | quoted | reported | system | unknown`, conflating *who holds the stance* with *how it is syntactically/discursively conveyed*.
- **Change:**
  - Replaced categorical `holder` with two orthogonal fields:
    - `holder_ref: str` (e.g. `"user"`, `"Alice"`, `"VP"`, `"system"`, `"unknown"`).
    - `attribution_mode: AttributionMode` (`direct_speaker`, `direct_quote`, `indirect_report`, `external_source`, `unknown`).
  - Updated in `research/semantic_annotation/schema.py`, `ONTOLOGY_V0_1.md`, and `ANNOTATION_GUIDELINE_V0_1.md`.

### 2. Fix `INCOMPATIBLE` Temporal Semantics
- **Problem:** Cross-time opposite statements (e.g. 2022 preference vs. 2026 preference) were previously allowed to receive an `INCOMPATIBLE` edge, conflating longitudinal shift with local incompatibility.
- **Change:**
  - Added strict temporal validity constraint: `INCOMPATIBLE` requires matching subject, dimension, and scope **with overlapping temporal validity**.
  - Cross-time opposite statements must be represented as distinct dated units with opposite polarity/value and a `BEFORE` temporal ordering. Downstream LCE infers belief revision.
  - Added validation in `SemanticAnnotationDocument.validate_document_semantics()` that rejects `INCOMPATIBLE` between units with non-overlapping exact temporal anchors.

### 3. Ground Every Positive Relation Independently
- **Problem:** Relations relied solely on unit-level status and lacked independent provenance and grounding.
- **Change:**
  - `SemanticRelation` now requires:
    - `provenance: RelationProvenance` (`raw_evidence_id`, `semantic_block_id`).
    - `evidence_status: EvidenceStatus` (`explicit`, `entailed`, `inferred`, `unknown`).
    - `confidence: float` ($0.0 \le c \le 1.0$).
    - `supporting_spans: list[SourceSpan]` (pointing to connective phrases such as "because", "although").

### 4. Keep Control Labels Out of the Graph
- **Problem:** Control outcomes (`NO_RELATION`, `UNKNOWN`, `TEMPORAL_UNKNOWN`) risk polluting downstream graph indexes if serialized as graph edges.
- **Change:**
  - Explicitly defined `CONTROL_RELATION_TYPES = {NO_RELATION, UNKNOWN, TEMPORAL_UNKNOWN}`.
  - Added property `is_graph_edge` and method `to_graph_edge()` on `SemanticRelation`. Attempting to serialize a control outcome as a graph edge raises a `ValueError`.
  - Documented in guideline that control outcomes are solely for inter-annotator evaluation and benchmark scoring.

### 5. Make `SAME_ENTITY` Representable Over Argument Mentions
- **Problem:** `SAME_ENTITY` previously targeted proposition IDs, making argument-level entity coreference impossible to distinguish from event coreference.
- **Change:**
  - Introduced `ArgumentMention` model with `role`, `text`, optional `source_span`, and optional `entity_ref`.
  - `SAME_ENTITY` endpoints are strictly validated to target argument mentions in format `<unit_id>:<role>` (e.g. `u1:actor SAME_ENTITY u2:target`), and verified to exist on the respective units.
  - `SAME_EVENT` remains the relation between proposition/event unit IDs.

### 6. Strengthen Temporal Anchoring
- **Problem:** Relative temporal anchors lacked explicit reference grounding, risking ambiguity.
- **Change:**
  - `TemporalAnchoring` now records:
    - `normalized_value: str` (ISO 8601 string or `"unknown"`).
    - `anchor_type: TemporalAnchorType` (`exact`, `bounded_range`, `relative`, `unanchored`).
    - `source_expression: str | None` (verbatim temporal phrase).
    - `reference_anchor: str | None` (the reference time or unit, e.g. `"evidence:occurred_at"`).
  - Validation requires `reference_anchor` whenever `anchor_type == RELATIVE`.

### 7. Remove Unsupported State Manufacture
- **Problem:** Guideline previously contained an example decomposing `"I moved to London"` into an event `move_to` and a manufactured state `live_in` linked by `CAUSE`.
- **Change:**
  - Removed and deleted the manufactured state example across all documentation.
  - Added an explicit negative invariant in `ANNOTATION_GUIDELINE_V0_1.md` and `EXAMPLES_V0_1.md`: Transition events must never be used to invent unstated continuous result states without explicit bounded textual evidence.
  - Prohibited using `CAUSE` as a generic event-to-result filler.

### 8. Specify Shallow Nested-Attitude Handling
- **Problem:** Complex attitudes (e.g. `"I think I want to leave"`) lacked a deterministic shallow compression policy.
- **Change:**
  - Defined explicit shallow flattening rule: extract the matrix attitude (`leave`), preserve the epistemic hedge by setting `modality: uncertain`, lower confidence to $\le 0.70$, and record `normalization_rule: "shallow_nested_hedge"`.
  - Prohibited silently promoting a hedged belief-about-desire into an unhedged `desired` modality.

### 9. Make Predicate Normalization Reproducible
- **Problem:** Free-form predicate normalization risked arbitrary annotator divergence (e.g. `"want"` vs `"desire"`).
- **Change:**
  - Introduced `PredicateSpec` containing:
    - `surface_predicate: str` (verbatim text).
    - `normalized_predicate: str` (canonical lemma/frame).
    - `normalization_rule: str` (documented rule name, e.g. `"verb_lemma"`, `"standard_frame"`, `"shallow_nested_hedge"`, `"exact_match"`).

### 10. Correct Research-Stage Numbering
- **Problem:** Stage numbers were misaligned in early draft text.
- **Change:**
  - Corrected stage pipeline to:
    - **#13:** Annotation contract (frozen ontology, guideline, schema).
    - **#14:** Gold benchmark dataset creation.
    - **#15:** AGY semantic parser benchmark and freeze.
    - **#16:** Oracle typed graph representation experiment.
    - **#17:** AGY graph vs. Oracle comparison experiment.
  - Updated pipeline diagrams in `ONTOLOGY_V0_1.md` and `ANNOTATION_GUIDELINE_V0_1.md`.

### 11. Prevent Dual-Schema Drift
- **Problem:** Having separate manual Pydantic and JSON Schema files risks divergence over time.
- **Change:**
  - Designated Python Pydantic schema in `research/semantic_annotation/schema.py` as the canonical definition.
  - Automatically exported `research/schemas/semantic_annotation_v0_1.json` via `model_json_schema()`.
  - Added explicit parity regression test `test_schema_parity()` in `tests/research/test_semantic_annotation_schema.py` verifying identical enum members, required fields, and rejection of forbidden cognition labels.
