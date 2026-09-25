# SemanticBlock v0.3 — Failure Taxonomy Error Analysis

**Date:** 2026-09-25

---

## 1. Failure Taxonomy Breakdown

Following the frozen failure taxonomy:

| Failure Category | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| `CONTEXT_INSUFFICIENT` | 0 | 0 | 0 | 6 | 0 |
| `SEMANTIC_MISREAD` | 1 | 2 | 3 | 15 | 2 |
| `ATTRIBUTION_DRIFT` | 0 | 0 | 0 | 1 | 1 |
| `OVERCLAIM` | 2 | 7 | 8 | 14 | 3 |
| `UNDERCLAIM` | 3 | 2 | 1 | 3 | 2 |
| `UNKNOWN_MISPLACED` | 26 | 29 | 27 | 30 | 16 |
| `TEMPORAL_OVERREACH` | 2 | 2 | 2 | 2 | 1 |
| `NON_RECONSTRUCTABLE` | 0 | 0 | 0 | 6 | 0 |
| `TRIVIAL_NON_STRUCTURE` | 0 | 0 | 0 | 0 | 0 |
| `GRANULARITY_COLLAPSE` | 1 | 0 | 0 | 1 | 1 |
| `SURFACE_SENSITIVITY` | 0 | 0 | 0 | 0 | 0 |
| `OVER_ATOMIZATION` | 0 | 0 | 0 | 0 | 0 |
| `RETRIEVAL_REPRESENTATION_FAILURE` | 0 | 0 | 0 | 0 | 0 |
| `RETRIEVER_FAILURE` | 0 | 0 | 0 | 0 | 0 |
| `EVALUATION_AMBIGUITY` | 0 | 0 | 0 | 0 | 0 |

## 2. Severe Contamination Error Breakdown

| Contamination Type | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| `reported_to_belief` | 0 | 0 | 0 | 0 | 0 |
| `question_to_assertion` | 0 | 0 | 0 | 1 | 0 |
| `counterfactual_to_fact` | 0 | 1 | 1 | 1 | 0 |
| `possibility_to_certainty` | 4 | 4 | 4 | 12 | 2 |
| `obligation_to_completed` | 0 | 1 | 3 | 2 | 1 |
| `future_to_past` | 1 | 1 | 1 | 0 | 1 |
| `invented_certainty` | 12 | 15 | 12 | 23 | 9 |