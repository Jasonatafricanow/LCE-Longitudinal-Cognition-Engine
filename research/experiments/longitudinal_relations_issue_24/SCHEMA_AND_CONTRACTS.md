# First-Layer Longitudinal Relations above SemanticBlock — Schema & Contracts Specification

**Issue:** #24  
**Date:** 2026-09-25  
**Status:** Experimental Milestone Completed & Validated  
**Authority:**
- `docs/architecture/SEMANTIC_BLOCK_DESIGN_FREEZE_2026-09-25.md`
- Issue #24: `[EXP: Validate time-first longitudinal relations above SemanticBlock]`

---

## 1. Executive Principle & Frozen Boundaries

### Core Thesis:
> **SemanticBlock is a local truth at time t. Time is strong alpha because later evidence can close previously open uncertainty, confirm persistence, record real-world change, or correct an earlier cognition.**

### Invariant Design Boundaries:
1. **SemanticBlock is Frozen:**
   - A complete local semantic point responsible only for meaning at its own cutoff.
   - Preserves localized `UNKNOWN`.
   - Never predicts downstream outcomes.
   - Never decides longitudinal relations globally.
2. **Deterministic Time Ordering as Strong Authority:**
   - `t1 < t2` is derived deterministically from source/storage metadata.
   - Chronology is an exogenous fact; the system never asks an LLM to guess temporal order when metadata is present.
3. **No Retrospective Semantic Mutation:**
   - Future facts **never** mutate predecessor SemanticBlocks (`SHA-256(predecessor)` invariant).
   - Longitudinal relations are stored as independent, typed observations over intact blocks.
4. **Epistemic Invariance ("No New Evidence, No New Cognition"):**
   - Time alone cannot manufacture knowledge.
   - `world outcome fixed + no new evidence = LCE knowledge remains UNKNOWN`.
   - Elapsed time without evidence cannot close an open dimension.
5. **Ontological Distinction:**
   - Real-world / plan state change (`STATE_CHANGE`) is strictly separated from earlier cognition being wrong (`CORRECTION_RETRACTION`).

---

## 2. Canonical Six-Relation Taxonomy

This layer deliberately restricts relations to six foundational longitudinal transitions:

```text
               ┌────────────────────────────────────────────────────────┐
               │              Longitudinal Relations                     │
               └──────────────────────────┬─────────────────────────────┘
                                          │
       ┌──────────────────┬───────────────┴───────────────┬──────────────────┐
       ▼                  ▼                               ▼                  ▼
┌──────────────┐   ┌──────────────┐                ┌──────────────┐   ┌──────────────┐
│ UNCERTAINTY  │   │ STATE_CHANGE │                │  CORRECTION_ │   │ PERSISTENCE_ │
│  RESOLUTION  │   │              │                │  RETRACTION  │   │ CONFIRMATION │
└──────────────┘   └──────────────┘                └──────────────┘   └──────────────┘
       ▲                                                  ▲
       │                                                  │
       └──────────────────┬───────────────────────────────┘
                          │
       ┌──────────────────┴──────────────────┐
       ▼                                     ▼
┌──────────────┐                      ┌──────────────┐
│  UNRELATED   │                      │   UNKNOWN_   │
│  CONTINUATION│                      │   RELATION   │
└──────────────┘                      └──────────────┘
```

### 1. `UNCERTAINTY_RESOLUTION`
- **Definition:** Predecessor $t_1$ possesses an open uncertainty, intention, obligation, or localized unknown. Successor $t_2$ brings decisive factual evidence that resolves this uncertainty (success, failure, cancellation, verification).
- **Epistemic Effect:** `prior_unknown_resolved = True`.
- **Constraint:** Does not invalidate $t_1$. The requirement/uncertainty was genuinely real at $t_1$; $t_2$ simply records the outcome.

### 2. `STATE_CHANGE`
- **Definition:** Predecessor $t_1$ was historically true at its cutoff. Subsequent to $t_1$, real-world conditions, schedules, or decisions evolved.
- **Epistemic Effect:** $t_1$ remains an immutable historical fact; $t_2$ establishes the new current state.
- **Contrast:** Distinct from `CORRECTION_RETRACTION` because the earlier state genuinely existed.

### 3. `CORRECTION_RETRACTION`
- **Definition:** Successor $t_2$ explicitly indicates that the earlier statement or cognition at $t_1$ was mistaken, erroneous, or retracted (e.g. slips of the tongue, misread calendars, typos).
- **Epistemic Effect:** Marks earlier representation as mistaken without mutating raw history.
- **Contrast:** The real-world state never changed; the observer's earlier representation was wrong.

### 4. `PERSISTENCE_CONFIRMATION`
- **Definition:** An unresolved state, pending process, or blocking condition established at $t_1$ is confirmed at $t_2$ to still be continuing without resolution.
- **Epistemic Effect:** `prior_unknown_resolved = False`. Confirms ongoing latency.

### 5. `UNRELATED`
- **Definition:** Blocks $t_1$ and $t_2$ are temporally proximate but describe completely independent events, distinct entities, or disjoint threads.
- **Epistemic Effect:** Temporal proximity does **not** create a semantic edge.

### 6. `UNKNOWN_RELATION`
- **Definition:** Time elapsed or thematic overlap exists, but available evidence at $t_2$ is insufficient to confirm or deny any specific longitudinal transition.
- **Epistemic Effect:** Preserves epistemic humility.

---

## 3. Four-Tier Experimental Progression (L0 – L3)

| Tier | Name | Signal Components | Search Complexity | Purpose |
|---|---|---|---|---|
| **L0** | Time Only | Chronological forward order ($t_1 \le t_2$) within temporal window | $O(N^2)$ all pairs | Baseline showing that pure time produces massive candidate noise (~98% false candidates). |
| **L1** | Time + Core Similarity | $t_1 \le t_2$ + Semantic Core embedding cosine similarity ($\ge 0.65$) | Sparse dense thresholding | Tests whether semantic continuity suffices. Fails to separate state change from correction and misses non-lexical transitions. |
| **L2** | Time + Cognitive Boundary Projections | $t_1 \le t_2$ + Entity/Role Anchors + Localized Unknowns match + Action/State transitions + Discourse revision cues | $O(N)$ sparse structural index | Achieves **93.5% candidate reduction** while preserving **100.0% recall** of true longitudinal relations. |
| **L3** | Selective LLM Adjudication | Runs **strictly on L2 candidates** with locked prompt and temperature 0.0 | $O(|L_2|)$ bounded calls | Delivers final typed observation with 0% state-vs-correction confusion and zero SemanticBlock mutation. |

---

## 4. Evidence Contract

For every accepted longitudinal observation, the system persists:
```json
{
  "observation_id": "string",
  "predecessor_block_id": "string",
  "successor_block_id": "string",
  "time_order_valid": true,
  "relation_type": "UNCERTAINTY_RESOLUTION | STATE_CHANGE | CORRECTION_RETRACTION | PERSISTENCE_CONFIRMATION | UNRELATED | UNKNOWN_RELATION",
  "affected_dimension": "string",
  "prior_unknown_resolved": false,
  "resolved_dimension": "string | null",
  "outcome_or_current_state": "string",
  "evidence_spans": ["exact text spans from t1 and t2"],
  "reason_competing_rejections": {
    "STATE_CHANGE": "string",
    "CORRECTION_RETRACTION": "string",
    "UNCERTAINTY_RESOLUTION": "string"
  },
  "confidence": 1.0,
  "created_at": "ISO UTC timestamp"
}
```

---

## 5. Critical Falsification Criteria (F1 – F5)

1. **F1 — Time is necessary but insufficient:** Temporally adjacent unrelated blocks must not be forced into a relation. Tested on hard negative distractor pairs.
2. **F2 — Future evidence does not rewrite earlier truth:** Predecessor SemanticBlock SHA-256 hash must be 100% invariant before and after relation establishment.
3. **F3 — UNKNOWN closes only with evidence:** Elapsed time alone must not convert unknown $\to$ known. Tested on elapsed-time cases without new evidence.
4. **F4 — State change != correction:** Confusion between world evolution (`STATE_CHANGE`) and cognitive error (`CORRECTION_RETRACTION`) must be 0%.
5. **F5 — Sparse candidate formation:** Avoid all-pairs comparison while preserving $\ge 95\%$ true relation recall with $> 70\%$ candidate reduction.
