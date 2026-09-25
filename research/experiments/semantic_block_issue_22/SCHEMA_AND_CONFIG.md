# SemanticBlock Projection Expansion (Issue #22) — Schema & Configuration Specification

**Date:** 2026-09-25  
**Experiment Authority:**  
- `docs/architecture/SEMANTIC_BLOCK_DESIGN_FREEZE_2026-09-25.md`  
- `docs/research/SEMANTIC_BLOCK_V03_FIDELITY_GRANULARITY_EXPERIMENT.md`  
- Issue #22: `[EXP: Expand SemanticBlock projections around a fixed semantic core]`  

---

## 1. Core Architectural Invariant

Every experimental arm must preserve the **identical canonical Semantic Core**.
Projections are views/indexes over the same semantic whole.
They are **not** an alternative ontology, nor a decomposition into independent proposition particles.

```text
SemanticBlock
├── semantic_core (FROZEN & IDENTICAL ACROSS ALL ARMS)
├── provenance
├── deterministic temporal metadata
└── projections (EXPANDED HORIZONTALLY)
    ├── source / attribution
    ├── epistemic state
    ├── communicative act
    ├── action status
    ├── polarity
    ├── condition
    ├── correction / revision
    ├── unresolved dimensions
    └── entity / role anchors
```

### Invariant Verification Contract:
`SHA-256(arm.semantic_core) == SHA-256(canonical_semantic_core)` for every case across B0, B1, B2, B3, B4.
Any deviation is a semantic violation.

---

## 2. Experimental Arms (B0 – B4)

### Arm B0: Core Only
- **Components**: `semantic_core` + `provenance` + `deterministic_temporal_metadata`.
- **Purpose**: Broad vector recall baseline; establishes what canonical semantics alone recover.

### Arm B1: Current Minimal Projections
- **Components**: B0 +
  - `source_attribution`:
    - `speaker`: "user" | string
    - `reported_source`: null | string
    - `user_endorsement`: "direct" | "endorsed" | "skeptical_rejected" | "uncommitted_unknown"
  - `epistemic_commitment`: "certain" | "probable" | "possible" | "explicitly_unknown" | "negated"
  - `action_or_state`:
    - `status`: "current_requirement_obligation" | "intention_plan" | "desire_preference" | "completed_past" | "hypothetical" | "cancelled_retracted" | "state_observation"
    - `summary`: string
  - `localized_unknowns`: list[string]
- **Purpose**: Reproduce the validated P2-style bounded baseline from v0.3.

### Arm B2: Expanded Discourse-State Projections
- **Components**: B1 +
  - `communicative_act`: "assertion" | "question" | "tentative_suggestion" | "command_obligation" | "correction_retraction" | "hypothetical_counterfactual" | "expressive_irony"
  - `polarity`: "positive" | "negative" | "mixed_contrastive" | "unknown"
  - `condition_or_hypothesis`:
    - `type`: "actual_unconditional" | "conditional_hypothetical" | "counterfactual_wish" | "counterfactual_relief"
    - `condition_text`: null | string
    - `consequent_text`: null | string
- **Purpose**: Disentangle utterances with heavy lexical overlap but opposite communicative or conditional force (e.g. question vs assertion, negation vs affirmation, condition vs fact).

### Arm B3: Expanded Longitudinal-State Projections
- **Components**: B2 +
  - `temporal_status`: "past_completed" | "present_current_requirement" | "future_planned" | "timeless_habitual" | "unknown"
  - `change_type`: "first_report" | "real_world_state_change" | "correction_retraction" | "no_change"
  - `revision_retraction`:
    - `is_revision`: boolean
    - `retracted_target`: null | string
    - `correction_nature`: null | "speaker_slip_repair" | "external_state_change"
  - `scoped_unresolved_dimensions`: list of objects:
    - `dimension`: string
    - `scope`: "time_point_local" | "trajectory_dependent" | "external_world_dependent"
    - `blocking_condition`: null | string
- **Purpose**: Provide candidate organization hooks for longitudinal lineage (world change vs correction) without violating time-locality.

### Arm B4: Entity / Role Anchor Projections
- **Components**: B3 +
  - `entity_role_anchors`:
    - `actor_agent`: list[string] (who initiated or holds responsibility)
    - `target_recipient`: list[string] (recipient, partner, or affected party)
    - `affected_object`: list[string] (tangible object, report, topic, resource)
    - `destination_or_location`: list[string] (spatial endpoint or setting)
    - `key_entities`: list[string] (all grounded entity mentions)
- **Constraint**: Anchors are strictly indexes into the intact core. They do NOT atomize the core into standalone semantic tuples.
- **Purpose**: Distinguish same-topic hard negatives under entity role reversal (e.g., A notified B vs B notified A; A lent B vs B lent A).

---

## 3. Retrieval Implementations (R0 – R3)

- **R0 (Core-vector only)**: Embed only `semantic_core`. Broad recall baseline.
- **R1 (Core-vector + projection rerank)**: Broad core-vector Top-K retrieval -> projection compatibility score adjustment -> reranked package.
- **R2 (Mixed representation embedding - diagnostic)**: Embed concatenated core + serialized projections directly. Diagnostic test of embedding pollution vs enrichment.
- **R3 (Projection-aware soft expansion)**: Broad core-vector retrieval + soft structured candidate promotion under fixed budget K.

---

## 4. Adjudication Stage Contract

The adjudicator operates downstream of retrieval under an identical prompt contract across all arms:
- Input: Query Cognition Goal + Bounded Candidate Package (K = 3, 5, 8).
- Decision: For each candidate, decide `accept` or `reject` with reasoning.
- Objective: Measure whether projections reduce false candidate acceptance, improve target discovery, and reduce token burden.
