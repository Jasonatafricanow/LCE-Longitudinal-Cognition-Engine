# Issue #19 Error Analysis & Failure Taxonomy

Detailed inspection of errors, borderline cases, and model behaviors observed across all arms.

## 1. Zero-Tolerance Hard Violations

### Arm B Hard Violations (1 instances)
- `silent_holder_flip in s1: Mira -> user`
### Arm C Hard Violations (1 instances)
- `invalid_relation_endpoint in relation B11-N_s1->B11-N_s2`
### Arm D Hard Violations (4 instances)
- `invalid_relation_endpoint in relation B15-N_s3->B15-N_s2`
- `invalid_relation_endpoint in relation B15-N_s2->B15-N_s1`
- `forbidden_CAUSE_emitted`
- `silent_holder_flip in s1: Mira -> user`

## 2. Arm A (Current V1) Semantic Omission Audit

- **Predicate/Kind:** 100% UNKNOWN. Current V1 reference memory does not distinguish event, state, attitude, or reported proposition.
- **Holder/Attribution:** 100% UNKNOWN. Current V1 collapses third-party quotes (B04-N) and author stance into coarse content text.
- **Relations:** 100% FN. Current V1 produces no typed relation graph; F7 causal paths and F8 sentinels cannot be retrieved from blocks alone.
- **Temporal Visibility:** Visibility relies on coarse evidence time; interpretive revisions cannot be isolated at historical cutoffs.

## 3. Arm B (One-Pass) vs. Arm C (Recommended) Boundary & Linking Comparison

- **Compound Causal Accounts (B02):** Arm C's normalizer enforces single-block encapsulation for causal clauses, preventing over-splitting.
- **Direct Shortcut Causality (B03):** Arm C's 2-stage typed linker suppresses direct s1->s3 shortcut creation when intermediate s1->s2 and s2->s3 exist.
- **Pronoun Ambiguity (B07-N):** Arm C correctly preserves `entity_status='unresolved'` and `uncertainty='actor_ambiguous'` when multiple referents exist.
- **Cross-Context Identity (B08, B14):** Both B and C successfully reject lexical-only false identity bridges and require authorized registry entries.

## 4. Per-Field Error Distribution on Held-Out Cases

| Field | Arm A Correct / Total | Arm B Correct / Total | Arm C Correct / Total | Arm D Correct / Total |
| --- | --- | --- | --- | --- |
| `canonical_content` | 14/28 (50%) | 24/28 (86%) | 23/28 (82%) | 26/28 (93%) |
| `predicate_kind` | 0/28 (0%) | 24/28 (86%) | 19/28 (68%) | 21/28 (75%) |
| `participants` | 0/28 (0%) | 23/28 (82%) | 22/28 (79%) | 23/28 (82%) |
| `holder` | 0/28 (0%) | 27/28 (96%) | 25/28 (89%) | 27/28 (96%) |
| `utterer` | 0/28 (0%) | 27/28 (96%) | 24/28 (86%) | 27/28 (96%) |
| `attribution_mode` | 0/28 (0%) | 27/28 (96%) | 25/28 (89%) | 27/28 (96%) |
| `polarity` | 0/28 (0%) | 28/28 (100%) | 25/28 (89%) | 28/28 (100%) |
| `modality` | 0/28 (0%) | 28/28 (100%) | 25/28 (89%) | 28/28 (100%) |
| `epistemic_hedge` | 0/28 (0%) | 28/28 (100%) | 25/28 (89%) | 28/28 (100%) |
| `valid_time_precision` | 0/28 (0%) | 27/28 (96%) | 24/28 (86%) | 14/28 (50%) |
| `entity_status_uncertainty` | 0/28 (0%) | 28/28 (100%) | 19/28 (68%) | 13/28 (46%) |
| `availability` | 13/28 (46%) | 28/28 (100%) | 25/28 (89%) | 28/28 (100%) |
| `provenance` | 5/28 (18%) | 23/28 (82%) | 20/28 (71%) | 25/28 (89%) |
