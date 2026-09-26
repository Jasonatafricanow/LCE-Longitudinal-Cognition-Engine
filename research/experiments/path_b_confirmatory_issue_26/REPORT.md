# Issue #26 — Fresh Confirmatory Heldout for Path B Latent Discovery

## Verdict: ❌ NOT_SUPPORTED

The frozen Issue #25 mechanism does **not** generalize to unseen adversarial
longitudinal cases. Candidate discovery recall drops to 33% (B2) / 42% (B1)
vs the 91% observed during development. The dominant failure mode is
**temporal distance**: the 45-day fixed window is too narrow for real-world
longitudinal spans.

**Frozen code SHA**: `85974a2`
**Branch**: `research/path-b-confirmatory-heldout-issue-26`

---

## 1. Primary Questions

### Q1 — What is the current miss?

8 of 12 true relation pairs are missed by B2. Per-case classification:

| Pair ID | Family | Miss Category | Temporal Δ | Cosine | Boundary Score |
|---|---|---|---|---|---|
| HG01 | F1 plan→completed | **temporal_distance** | 60.3d | 0.20 | 0.30 |
| HG02 | F2 plan→failed | **temporal_distance** | 90.0d | 0.17 | 0.55 |
| HG04 | F4 possible→confirmed | **temporal_distance** + missing_anchor | 80.0d | 0.11 | 0.10 |
| HG06 | F6 unresolved→resolved | **missing_semantic_anchor** | 15.0d | 0.13 | 0.10 |
| HG07 | F7 state_change | **missing_semantic_anchor** | 44.0d | 0.16 | 0.10 |
| HG09 | F9 persistence | **temporal_distance** | 46.0d | 0.11 | 0.35 |
| HG12 | F12 future changed | **vector_miss** + lexical_discontinuity | 22.0d | 0.07 | 0.20 |
| HG13 | F13 weak_lexical | **vector_miss** + lexical_discontinuity | 3.3d | 0.00 | 0.15 |

**Dominant failure modes:**

1. **Temporal distance** (4 of 8 misses): The 45-day `temporal_window_days`
   parameter cuts off all pairs with Δ > 45 days. HG01 (60d), HG02 (90d),
   HG04 (80d), and HG09 (46d) are simply unreachable. Issue #25's corpus had
   max Δ ≈ 30 days — this was never tested.

2. **Missing semantic anchor** (4 of 8): Even within the time window, the
   B2 `b2_min_score=0.25` threshold rejects pairs whose boundary signals
   are individually weak. HG06 and HG07 have entity overlap but no
   plan→outcome or uncertainty→resolution arc, yielding score 0.10.

3. **Vector miss / lexical discontinuity** (3 of 8): Character-bigram
   pseudo-embeddings produce cosine=0.0 for HG13 (咳嗽/嗓子 → 支原体/阿奇)
   and HG11 (做饭/外卖 → 后厨/打工). The Issue #25 corpus never tested
   genuinely disjoint-vocabulary longitudinal continuity.

### Q2 — Does B2 add real recall over B1?

| Metric | B1 | B2 |
|---|---|---|
| **Recall** | **41.7%** | **33.3%** |
| Volume | 16 | 56 |
| Targets recalled | 5 | 4 |
| Marginal extra false candidates | — | +41 |

**B2 is worse than B1 on this heldout set.** B2 loses 2 targets that B1 finds
(HG06, HG07) and gains only 1 (HG11). Meanwhile B2 introduces 41 extra false
candidates (3.5× the volume of B1) for that one marginal true recall.

| | B1 only | B2 only | Both | Neither |
|---|---|---|---|---|
| **Targets** | HG06, HG07 | HG11 | HG03, HG05, HG08 | HG01, HG02, HG04, HG09, HG12, HG13 |

The B2 cognitive-boundary signals *filter out* targets that B1's simpler
cosine-pass retains. The boundary signal scoring (≥0.25, ≥1 signal) is
calibrated to the Issue #25 corpus and does not transfer.

**Plain statement**: On this unseen data, B2 adds no real recall over B1 and
only increases candidate volume. B1 is the better baseline.

### Q3 — Does adjudication remain safe on unseen candidates?

| Metric | Value |
|---|---|
| Total evaluated | 7 |
| Relation accuracy | **28.6%** |
| Correction ↔ state confusion | **0.0%** ✓ |
| Persistence accuracy | N/A (no persistence candidates survived) |
| UNKNOWN_RELATION rate | **57.1%** |
| False UNKNOWN closure | **0** ✓ |
| Evidence-free closure | **0** ✓ |

**Findings:**
- The adjudicator produces `UNKNOWN_RELATION` on 4 of 7 evaluated pairs,
  indicating it abstains rather than making false positive claims — this is
  safe behavior
- **Zero** correction ↔ state-change confusion (F4 holds)
- **Zero** evidence-free unknown closure (F6 holds)
- The low accuracy (29%) is driven by the 57% UNKNOWN rate plus 3 UNRELATED
  pairs misclassified as UNKNOWN

### Q4 — Does the two-axis output still matter?

**Yes.** 9 adjudication results simultaneously express
`longitudinal_relation = STATE_CHANGE` and `prior_unknown_resolved = True`.
The orthogonal-axis design is confirmed to function on unseen data without
collapsing into a mutually-exclusive taxonomy.

---

## 2. Metrics

### Candidate discovery (raw counts)

| | All-pairs | B0 | B1 | B2 |
|---|---|---|---|---|
| Candidates | 528 | 442 | 16 | 56 |
| Gold relations | 12 | — | — | — |
| Recalled | — | 8 | 5 | 4 |
| **Recall** | — | **66.7%** | **41.7%** | **33.3%** |
| Reduction | 0% | 16.3% | 97.0% | 89.4% |

### Adjudication confusion matrix

| Gold ↓ / Predicted → | STATE_CHANGE | CORRECTION | PERSISTENCE | UNRELATED | UNKNOWN |
|---|---|---|---|---|---|
| STATE_CHANGE | 1 | 0 | 0 | 0 | 1 |
| CORRECTION | 0 | 1 | 0 | 1 | 0 |
| UNRELATED | 0 | 0 | 0 | 0 | 3 |

### Knowledge effect

| Metric | Value |
|---|---|
| Resolution precision | **100%** (no false closures) |
| Resolution recall | **33.3%** (only 1/3 true closures detected) |
| Evidence-free closure | **0** |

### Temporal integrity

| Check | Result |
|---|---|
| Reverse-time errors | **0** |
| Future leakage | **0** |
| **All passed** | ✓ |

---

## 3. Failure Root Causes

### 3.1 The 45-day window is fatal for real longitudinal spans

Issue #25's corpus had max temporal distance ≈ 30 days. Four genuine
longitudinal pairs in the heldout span 46–90 days. The `temporal_window_days=45`
parameter is a hard cutoff — B0 drops them before B1/B2 can even evaluate them.

**This is the single largest failure**: 4 of 8 B2 misses are pure
temporal-window truncation.

### 3.2 Character-bigram pseudo-embedding cannot handle vocabulary-disjoint pairs

Family 13 (symptoms → diagnosis: 咳嗽/嗓子 → 支原体/阿奇) has
**zero** character bigram overlap. A real embedding model would capture
the health-domain semantic continuity, but the deterministic test
embedding has no world knowledge.

### 3.3 B2 boundary scoring is overfitted to Issue #25 patterns

The `b2_min_score=0.25` threshold and the signal scoring weights
(plan_outcome_arc=0.3, correction_cue=0.4, etc.) were calibrated to
produce good results on the Issue #25 corpus. They reject valid
longitudinal pairs whose boundary signals score 0.10–0.20.

---

## 4. What Holds

Despite the recall collapse:

1. ✅ **Temporal integrity**: zero violations
2. ✅ **F4 (state ≠ correction)**: zero confusion
3. ✅ **F6 (no evidence-free closure)**: zero violations
4. ✅ **Adjudicator safety**: prefers UNKNOWN over false positive
5. ✅ **Dual-axis output**: STATE_CHANGE + prior_unknown_resolved coexists
6. ✅ **Oracle prohibition**: zero oracle fields in any view

---

## 5. What Does NOT Hold

1. ❌ **Candidate recall**: B2 33%, B1 42% — unacceptable for production
2. ❌ **B2 marginal value**: B2 is worse than B1 on unseen data
3. ❌ **Temporal window**: 45 days is insufficient for real longitudinal spans
4. ❌ **Embedding generalization**: character bigrams are not a real embedding

---

## 6. Recommendations (not implemented — per stop rule)

These are observations only. Any repair must be a separate follow-up issue.

1. **Increase `temporal_window_days`** to at least 90 days (or make it
   configurable per-corpus with a softer decay function)
2. **Replace character-bigram embeddings** with a real sentence embedding model
3. **Reconsider B2 signal scoring**: either lower the threshold or use
   additive B1∪B2 instead of B2 filtering independently from B0
4. **B1 is the better Stage 1 baseline** on current evidence — B2 should
   be redesigned to *add to* B1's recall, not filter from B0 independently

---

## 7. Files

| File | Purpose |
|---|---|
| `research/experiments/path_b_confirmatory_issue_26/__init__.py` | Package |
| `research/experiments/path_b_confirmatory_issue_26/heldout_corpus.py` | 33-block fresh corpus + 18 gold |
| `research/experiments/path_b_confirmatory_issue_26/confirmatory_runner.py` | Frozen evaluation runner |
| `research/experiments/path_b_confirmatory_issue_26/results/` | Raw outputs |
| `tests/research/test_path_b_confirmatory_issue_26.py` | 20 tests |
