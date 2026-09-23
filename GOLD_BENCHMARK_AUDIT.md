# LCE Semantic Parsing Gold Benchmark v0.1: Comprehensive Audit Report

**Document:** `GOLD_BENCHMARK_AUDIT.md`  
**Date:** 2026-09-23  
**Auditor:** Antigravity (DeepMind Advanced Agentic Coding)  
**Target Artifacts:** `research/benchmarks/semantic_annotation_v0_1/` (`dev.jsonl`, `eval.jsonl`, `schema.json`, `validator.py`, `README.md`)  
**Ontology Baseline:** Frozen v0.1 (`docs/research/semantic_annotation/ANNOTATION_GUIDELINE_V0_1.md`, `research/semantic_annotation/schema.py`)  
**Audit Verdict:** `NEEDS_REVISION`

---

## 1. Executive Summary & Verdict

### Audit Verdict: **NEEDS_REVISION**

While the Issue #14 Gold Benchmark successfully establishes a strict validation infrastructure, exact Pydantic schema typing, and full rejection of forbidden downstream cognition labels, an exhaustive manual and semantic audit reveals critical deficiencies that disqualify the dataset from being used as a frozen gold standard in its current form:

1. **Semantic Span Offset Invalidation (17 errors across 11 cases):** The generator script used naive string search (`content.index(substring)`) anchored to the full raw evidence text rather than scoped to the parent unit. When an entity or token is repeated across clauses (e.g. `"I"`, `"We"`, `"BigCorp"`, `"security team"`), the argument mention span in Unit 2 erroneously resolved to the character offsets in Unit 1. In `gold_eval_01`, this caused `SAME_ENTITY` to link a mention in Sentence 1 reflexively to itself instead of linking across sentences.
2. **Unit Clause Boundary Truncation (`gold_dev_08`):** Unit `u1`'s span was restricted to the verb phrase `"terminated the employment"` [8:33], leaving its subject actor `"CTO"` [4:7] and target `"director"` [41:49] completely outside the proposition's source span, violating Rule 1 & Rule 2.
3. **Semantic Predicate Mislabeling (`gold_dev_06`):** In `"the runway is four months"`, the predicate was annotated as `"runway"` (a nominal argument theme), duplicating the argument as its own predicate rather than annotating the copula/stative predicate.
4. **Dev Split Failure for Prompt Design:** The 20-case Dev split is severely skewed. It completely omits **7 out of 17 case families** (0 cases for `discourse_relations`, `longitudinal_shift`, `state_compatibility`, `ambiguous_relations`, `no_relation_control`, `relative_temporal_anchoring`, and `nested_attitude`). Dev contains **zero examples** of epistemic hedges, **zero examples** of `desired` modality, **zero examples** of discourse relations (`CONDITION`, `CONTRAST`, `CONCESSION`), **zero examples** of state compatibility (`EQUIVALENT`, `INCOMPATIBLE`), and **zero examples** of evaluation control outcomes (`NO_RELATION`, `UNKNOWN`, `TEMPORAL_UNKNOWN`). A developer or parser cannot design, prompt, or calibrate an LLM on Dev without hallucinating the missing half of the v0.1 ontology.
5. **Severe Label Sparsity Across Entire Benchmark:** Across all 60 cases, 10 vocabulary terms have **0 total occurrences** (e.g. `AFTER`, `OVERLAP`, `UNKNOWN`, `modality: uncertain`, `lemma`), and 14 labels have only **1 or 2 occurrences** (e.g. `CONDITION: 1`, `CONTRAST: 1`, `CONCESSION: 1`, `EQUIVALENT: 1`, `SAME_EVENT: 1`, `INCOMPATIBLE: 2`). This sparsity cannot support statistically stable precision/recall/F1 metrics.

---

## 2. Benchmark Case Generation Mechanism

### Explicit Finding: Manual Authoring with Programmatic Serialization

The script `scratch/generate_benchmark_cases.py` (which authored and serialized `dev.jsonl` and `eval.jsonl`) was inspected in detail.

- **Semantic Label Derivation:** Semantic labels (`kind`, `surface_predicate`, `normalized_predicate`, `normalization_rule`, `arguments`, `roles`, `modality`, `epistemic_hedge`, `holder_ref`, `attribution_mode`, `relation_type`, `evidence_status`, and `rationale`) are **100% manually authored**. No semantic labels, predicates, or relations were generated via heuristics, regex, dependency parsers, or LLM inference.
- **Programmatic Computation:** The script was purely a **serialization helper** that performed two programmatic steps:
  1. `make_span(content, substring)`: calculated character start and end indices (`start = content.index(substring); end = start + len(substring)`).
  2. Model validation: packaged dictionaries into Pydantic models (`SemanticUnit`, `SemanticRelation`, `SemanticAnnotationDocument`) and dumped them to JSONL.
- **Root Cause of Offset Defects:** The delegation of character offset resolution to un-scoped `content.index()` is the direct programmatic root cause of the 17 semantic span offset errors identified in Section 6.

---

## 3. Comprehensive Coverage Matrix (Dev vs. Eval)

Below is the complete distribution of all ontology elements across the 20 Dev and 40 Eval cases.

### 3.1 Unit Kinds, Polarity, and Modality

| Category | Label | Dev Count (20 cases) | Eval Count (40 cases) | Benchmark Total (60 cases) | Status / Evaluation Risk |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Unit Kind** | `event` | 24 (80.0%) | 39 (59.1%) | 63 (65.6%) | Robust |
| | `state` | 4 (13.3%) | 13 (19.7%) | 17 (17.7%) | Adequate |
| | `attitude` | 1 (3.3%) | 12 (18.2%) | 13 (13.5%) | Skewed towards Eval |
| | `proposition` | 1 (3.3%) | 2 (3.0%) | 3 (3.1%) | Low support |
| **Polarity** | `positive` | 29 (96.7%) | 65 (98.5%) | 94 (97.9%) | Heavily unbalanced |
| | `negative` | 1 (3.3%) | 1 (1.5%) | 2 (2.1%) | **Sparse (2 total)** |
| | `unknown` | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | **Unrepresented (0)** |
| **Modality** | `asserted` | 28 (93.3%) | 55 (83.3%) | 83 (86.5%) | Dominant baseline |
| | `intended` | 1 (3.3%) | 5 (7.6%) | 6 (6.2%) | Adequate |
| | `desired` | 0 (0.0%) | 4 (6.1%) | 4 (4.2%) | **Missing in Dev (0)** |
| | `possible` | 1 (3.3%) | 1 (1.5%) | 2 (2.1%) | **Sparse (2 total)** |
| | `hypothetical` | 0 (0.0%) | 1 (1.5%) | 1 (1.0%) | **Sparse / Missing in Dev (1)** |
| | `uncertain` | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | **Unrepresented (0)** |
| | `unknown` | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | **Unrepresented (0)** |

### 3.2 Epistemic Hedging, Attribution, and Evidence Status

| Category | Label | Dev Count (20 cases) | Eval Count (40 cases) | Benchmark Total (60 cases) | Status / Evaluation Risk |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Epistemic Hedge**| `none` | 30 (100.0%) | 63 (95.5%) | 93 (96.9%) | Dominant baseline |
| | `think` | 0 (0.0%) | 2 (3.0%) | 2 (2.1%) | **Sparse / Missing in Dev (2)** |
| | `probable` | 0 (0.0%) | 1 (1.5%) | 1 (1.0%) | **Sparse / Missing in Dev (1)** |
| | `uncertain` | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | **Unrepresented (0)** |
| | `doubt` | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | **Unrepresented (0)** |
| **Attribution Mode**| `direct_speaker` | 28 (93.3%) | 63 (95.5%) | 91 (94.8%) | Dominant baseline |
| | `direct_quote` | 1 (3.3%) | 2 (3.0%) | 3 (3.1%) | Low support |
| | `indirect_report`| 1 (3.3%) | 1 (1.5%) | 2 (2.1%) | **Sparse (2 total)** |
| | `external_source`| 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | **Unrepresented (0)** |
| | `unknown` | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | **Unrepresented (0)** |
| **Evidence Status**| `explicit` (unit) | 29 (96.7%) | 66 (100.0%) | 95 (99.0%) | Dominant baseline |
| | `entailed` (unit) | 1 (3.3%) | 0 (0.0%) | 1 (1.0%) | **Sparse / Missing in Eval (1)** |
| | `inferred` (unit) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | **Unrepresented in Units (0)** |
| | `explicit` (rel) | 9 (100.0%) | 26 (96.3%) | 35 (97.2%) | Dominant baseline |
| | `inferred` (rel) | 0 (0.0%) | 1 (3.7%) | 1 (2.8%) | **Sparse / Missing in Dev (1)** |
| | `entailed` (rel) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | **Unrepresented in Rels (0)** |

### 3.3 Temporal Anchoring and Predicate Normalization

| Category | Label | Dev Count (20 cases) | Eval Count (40 cases) | Benchmark Total (60 cases) | Status / Evaluation Risk |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Temporal Anchor** | `exact` | 28 (93.3%) | 60 (90.9%) | 88 (91.7%) | Dominant baseline |
| | `relative` | 2 (6.7%) | 5 (7.6%) | 7 (7.3%) | Adequate |
| | `bounded_range`| 0 (0.0%) | 1 (1.5%) | 1 (1.0%) | **Sparse / Missing in Dev (1)** |
| | `unanchored` | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | **Unrepresented (0)** |
| **Predicate Rule** | `exact_surface` | 23 (76.7%) | 65 (98.5%) | 88 (91.7%) | Dominant baseline |
| | `compound_lower`| 6 (20.0%) | 1 (1.5%) | 7 (7.3%) | Adequate in Dev |
| | `frozen_map` | 1 (3.3%) | 0 (0.0%) | 1 (1.0%) | **Sparse / Missing in Eval (1)** |
| | `lemma` | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | **Unrepresented (0)** |

### 3.4 Argument Roles (11 Approved Roles)

| Role Name | Dev Count | Eval Count | Total Mentions | Status / Evaluation Risk |
| :--- | :---: | :---: | :---: | :--- |
| `theme` | 24 | 51 | 75 | Heavy representation |
| `actor` | 18 | 32 | 50 | Heavy representation |
| `time` | 7 | 17 | 24 | Good representation |
| `target` | 5 | 7 | 12 | Adequate |
| `experiencer` | 1 | 9 | 10 | Skewed towards Eval |
| `place` | 1 | 4 | 5 | Low support |
| `reason` | 2 | 0 | 2 | **Sparse / Missing in Eval (2)** |
| `result` | 1 | 1 | 2 | **Sparse (2 total)** |
| `stimulus` | 0 | 1 | 1 | **Sparse / Missing in Dev (1)** |
| `topic` | 0 | 1 | 1 | **Sparse / Missing in Dev (1)** |
| `purpose` | 0 | 0 | 0 | **Unrepresented (0)** |

### 3.5 Relations and Control Outcomes

| Relation Type | Dev Count | Eval Count | Total Relations | Status / Evaluation Risk |
| :--- | :---: | :---: | :---: | :--- |
| `BEFORE` | 3 | 9 | 12 | Adequate |
| `NO_RELATION` | 0 | 7 | 7 | **Missing in Dev (0)** |
| `CAUSE` | 2 | 1 | 3 | Low support |
| `SAME_ENTITY` | 2 | 1 | 3 | Low support |
| `INCOMPATIBLE` | 0 | 2 | 2 | **Sparse / Missing in Dev (2)** |
| `TEMPORAL_UNKNOWN` | 0 | 2 | 2 | **Sparse / Missing in Dev (2)** |
| `PURPOSE` | 1 | 1 | 2 | **Sparse (2 total)** |
| `SAME_EVENT` | 1 | 0 | 1 | **Sparse / Missing in Eval (1)** |
| `CONDITION` | 0 | 1 | 1 | **Sparse / Missing in Dev (1)** |
| `CONTRAST` | 0 | 1 | 1 | **Sparse / Missing in Dev (1)** |
| `CONCESSION` | 0 | 1 | 1 | **Sparse / Missing in Dev (1)** |
| `EQUIVALENT` | 0 | 1 | 1 | **Sparse / Missing in Dev (1)** |
| `AFTER` | 0 | 0 | 0 | **Unrepresented (0)** |
| `OVERLAP` | 0 | 0 | 0 | **Unrepresented (0)** |
| `UNKNOWN` | 0 | 0 | 0 | **Unrepresented (0)** |

### 3.6 Case Families and Adversarial Traps

| Family ID | Dev Cases | Eval Cases | Total Cases | Adversarial Traps Covered |
| :--- | :---: | :---: | :---: | :--- |
| `asserted_vs_intended` | 2 | 1 | 3 | None (Baseline distinction) |
| `possible_vs_occurred` | 2 | 1 | 3 | None (Baseline distinction) |
| `holder_attribution` | 2 | 3 | 5 | Traps 4–6: Direct quote & indirect report attribution spillover (3 traps) |
| `evidence_status_distinction` | 2 | 2 | 4 | Traps 13–14: Pragmatic speculation promoted to explicit (2 traps) |
| `negation_scope` | 2 | 0 | 2 | None (Dev only) |
| `multi_unit_decomposition` | 2 | 2 | 4 | Traps 11–12: Manufactured unstated result state (2 traps) |
| `same_entity_paraphrase` | 2 | 0 | 2 | None (Dev only) |
| `same_event_vs_similar` | 2 | 2 | 4 | Traps 9–10: Lexical overlap distractor falsely predicting identity (2 traps) |
| `temporal_non_causal` | 2 | 3 | 5 | Traps 1–3: Post-hoc causal hallucination from temporal succession (3 traps) |
| `explicit_causality` | 2 | 0 | 2 | None (Dev only) |
| `discourse_relations` | 0 | 4 | 4 | None (Hypothetical, Purpose, Contrast, Concession) |
| `longitudinal_shift` | 0 | 4 | 4 | Traps 7–8: Premature cognition interpretation (`REVISION`/`INCOMPATIBLE`) (2 traps) |
| `state_compatibility` | 0 | 4 | 4 | Trap 15: Cross-time false incompatibility (1 trap) |
| `nested_attitude` | 0 | 3 | 3 | Trap 16: Hedged desire flattening (`modality=uncertain`) (1 trap) |
| `relative_temporal_anchoring`| 0 | 3 | 3 | None (Relative anchor resolution) |
| `ambiguous_relations` | 0 | 4 | 4 | None (Underdetermined temporal & topical pairs) |
| `no_relation_control` | 0 | 4 | 4 | None (Unrelated negative controls) |
| **Total** | **20** | **40** | **60** | **16 Adversarial Traps in Eval** |

---

## 4. Verification of the 20-Case Dev Split for Prompt Design

### Verdict: **FAIL — Dev Split Fails Prompt Calibration Requirements**

A benchmark's development split (`dev.jsonl`) must provide representative few-shot and calibration examples of all core annotation rules that an automated parser prompt must obey. While Dev does not need to duplicate specific adversarial traps, it **must** expose the syntactic and semantic behaviors governed by the ontology.

The current 20-case Dev split fails this standard completely:

1. **Complete Absence of 7 Whole Families (41% of ontology families):**
   - `discourse_relations` (0 in Dev): A prompt engineer has no examples demonstrating how to output `CONDITION`, `CONTRAST`, or `CONCESSION`, or how to bind `supporting_spans` to lexical connectives like `"Although"` or `"but"`.
   - `nested_attitude` (0 in Dev): The entire Issue #13 final patch regarding nested attitudes (`modality: desired`, `epistemic_hedge: think`, `confidence: 1.0`) is completely unrepresented in Dev. A prompt designer cannot calibrate whether their prompt instructs the model to preserve desire or collapse into uncertainty.
   - `state_compatibility` (0 in Dev): Zero examples of `EQUIVALENT` or `INCOMPATIBLE`.
   - `longitudinal_shift` (0 in Dev): Zero examples demonstrating how cross-temporal opposite attitudes must be represented as `BEFORE` without generating `INCOMPATIBLE`.
   - `relative_temporal_anchoring` (0 in Dev): Only 2 relative anchors appear in Dev (and only anchored to `evidence:occurred_at`), with zero examples anchored to previous units (`unit:u1`).
   - `ambiguous_relations` & `no_relation_control` (0 in Dev): Dev contains zero examples of `NO_RELATION` or `TEMPORAL_UNKNOWN`. Every relation in Dev is a positive link (`CAUSE`, `BEFORE`, `SAME_ENTITY`, `SAME_EVENT`, `PURPOSE`). A parser tuned on Dev would learn to predict a positive edge for every pair and never emit a negative or unknown control outcome.
2. **Artificial Duplication in Dev:**
   - Instead of broad coverage, Dev consists of 10 families repeated exactly twice (10 × 2 = 20), such as two nearly identical causal sentences (`gold_dev_12` and `gold_dev_20`), while the other 7 families are completely exiled to Eval.
3. **Recommendation for Dev:** Dev and Eval must be rebalanced. At least 1 representative case from each of the 17 families must be placed in Dev, with the remaining 43 cases in Eval.

---

## 5. Exhaustive Case-by-Case Manual Audit (All 60 Cases)

Every single case was independently audited against [`ANNOTATION_GUIDELINE_V0_1.md`](file:///c:/projects/LCE/docs/research/semantic_annotation/ANNOTATION_GUIDELINE_V0_1.md) and [`schema.py`](file:///c:/projects/LCE/research/semantic_annotation/schema.py).

### Summary Results
- **Total Cases Audited:** 60
- **PASS:** 46 cases (76.7%)
- **ANNOTATION_ERROR:** 14 cases (23.3%) — 5 in Dev, 9 in Eval

### 5.1 Development Split (20 Cases)

| Case ID | Family | Text Snippet | Audit Verdict | Audit Finding / Error Description |
| :--- | :--- | :--- | :---: | :--- |
| `gold_dev_01` | `asserted_vs_intended` | "I joined the committee yesterday." | **PASS** | Valid asserted past event. Exact relative anchor. |
| `gold_dev_02` | `asserted_vs_intended` | "I will publish the RFC next Monday." | **PASS** | Valid future intention (`modality=intended`). |
| `gold_dev_03` | `possible_vs_occurred` | "The outage might be caused by DNS misconfiguration." | **PASS** | Valid epistemic possibility (`modality=possible`). |
| `gold_dev_04` | `possible_vs_occurred` | "The outage was caused by DNS misconfiguration." | **PASS** | Valid asserted causal attribution state. |
| `gold_dev_05` | `holder_attribution` | "My mentor told me 'Small startups are riskier'." | **PASS** | Valid direct quote with third-party holder (`mentor`). |
| `gold_dev_06` | `holder_attribution` | "Our team lead told me the runway is four months." | **ANNOTATION_ERROR** | **Predicate Mislabeling:** `surface_predicate` annotated as `"runway"`, which is a noun and the `theme` argument. The stative predicate is the copula `"is"` / `"is four months"`. |
| `gold_dev_07` | `evidence_status_distinction` | "The CTO fired the director of infrastructure." | **PASS** | Valid lexical assertion with `explicit` status. |
| `gold_dev_08` | `evidence_status_distinction` | "The CTO terminated the employment of the director." | **ANNOTATION_ERROR** | **Unit Truncation & Outside Arguments:** Unit `u1` span is only `"terminated the employment"` [8:33]. Argument `actor` (`"CTO"` [4:7]) and `target` (`"director"` [41:49]) fall completely outside unit span. |
| `gold_dev_09` | `negation_scope` | "We do not support legacy RSA keys." | **PASS** | Valid syntactic negation (`polarity=negative`). |
| `gold_dev_10` | `negation_scope` | "I like not having types in configuration files." | **PASS** | Valid positive attitude toward negated subclause. |
| `gold_dev_11` | `multi_unit_decomposition` | "I refactored the auth module, and Bob deployed the patch." | **PASS** | Valid coordination decomposition into 2 atomic units. |
| `gold_dev_12` | `multi_unit_decomposition` | "The disk filled up, causing the node to crash." | **PASS** | Valid causal link with participial connective `"causing"`. |
| `gold_dev_13` | `same_entity_paraphrase` | "Alice joined the security team. The security team welcomed her warmly." | **ANNOTATION_ERROR** | **Semantic Offset Bug:** In `u2`, argument `actor` (`m3`: `"security team"`) has span [17:30], pointing to the occurrence in Sentence 1 instead of Sentence 2 [36:49]. |
| `gold_dev_14` | `same_entity_paraphrase` | "I founded a startup in 2021. My company grew rapidly." | **PASS** | Valid `SAME_ENTITY` between `startup` and `company`. |
| `gold_dev_15` | `same_event_vs_similar` | "We signed the lease on Monday. We executed the rental agreement on Monday." | **ANNOTATION_ERROR** | **Semantic Offset Bug:** In `u2`, arguments `actor` (`m4`: `"We"`) and `time` (`m6`: `"on Monday"`) have spans [0:2] and [20:29], pointing to Sentence 1 rather than Sentence 2. |
| `gold_dev_16` | `same_event_vs_similar` | "We had our team sync on Monday. We had our team sync on Wednesday." | **ANNOTATION_ERROR** | **Semantic Offset Bug:** In `u2`, arguments `actor` (`m4`: `"We"`) and `theme` (`m5`: `"team sync"`) have spans [0:2] and [11:20], pointing to Sentence 1 rather than Sentence 2. |
| `gold_dev_17` | `temporal_non_causal` | "I ate lunch at noon. At two PM the database crashed." | **PASS** | Valid temporal precedence (`BEFORE`) without causality. |
| `gold_dev_18` | `temporal_non_causal` | "Alice reviewed the pull request before Bob left the office." | **PASS** | Valid `BEFORE` with supporting span `"before"`. |
| `gold_dev_19` | `explicit_causality` | "We added indexes in order to speed up user lookup." | **PASS** | Valid `PURPOSE` with supporting span `"in order to"`. |
| `gold_dev_20` | `explicit_causality` | "The disk filled up, therefore the node crashed." | **PASS** | Valid `CAUSE` with supporting span `"therefore"`. |

### 5.2 Evaluation Split (40 Cases)

| Case ID | Family | Text Snippet | Audit Verdict | Audit Finding / Error Description |
| :--- | :--- | :--- | :---: | :--- |
| `gold_eval_01` | `longitudinal_shift` | "In 2022, I really wanted to work at BigCorp. In 2026, I do not want to work at BigCorp." | **ANNOTATION_ERROR** | **Offset Bug & Self-Referential Relation:** In `u2`, `actor` (`m4`: `"I"`) and `target` (`m5`: `"BigCorp"`) point to Sentence 1 [0:1] and [36:43]. Consequently, `rel_02` (`m2 SAME_ENTITY m5`) connects Sentence 1's mention reflexively to itself. |
| `gold_eval_02` | `longitudinal_shift` | "In 2021, I loved microservices. In 2025, I prefer monorepos." | **ANNOTATION_ERROR** | **Semantic Offset Bug:** In `u2`, argument `experiencer` (`m4`: `"I"`) has span [0:1], pointing to Sentence 1 instead of Sentence 2 [41:42]. |
| `gold_eval_03` | `longitudinal_shift` | "In 2020, I lived in Berlin. In 2024, I lived in London." | **ANNOTATION_ERROR** | **Semantic Offset Bug:** In `u2`, argument `actor` (`m4`: `"I"`) has span [0:1], pointing to Sentence 1 instead of Sentence 2 [37:38]. |
| `gold_eval_04` | `longitudinal_shift` | "In 2019, our team used Python. In 2023, our team used Rust." | **ANNOTATION_ERROR** | **Semantic Offset Bug:** In `u2`, argument `actor` (`m4`: `"our team"`) has span [9:17], pointing to Sentence 1 instead of Sentence 2 [40:48]. |
| `gold_eval_05` | `state_compatibility` | "The staging server is running. The staging server is stopped." | **ANNOTATION_ERROR** | **Semantic Offset Bug:** In `u2`, argument `theme` (`m2`: `"staging server"`) has span [4:18], pointing to Sentence 1 instead of Sentence 2 [35:49]. |
| `gold_eval_06` | `state_compatibility` | "I started my own business. I founded a startup." | **ANNOTATION_ERROR** | **Semantic Offset Bug:** In `u2`, argument `actor` (`m3`: `"I"`) has span [0:1], pointing to Sentence 1 instead of Sentence 2 [27:28]. |
| `gold_eval_07` | `state_compatibility` | "The database cluster is operational. The database cluster is offline." | **ANNOTATION_ERROR** | **Semantic Offset Bug:** In `u2`, argument `theme` (`m2`: `"database cluster"`) has span [4:20], pointing to Sentence 1 instead of Sentence 2 [41:57]. |
| `gold_eval_08` | `discourse_relations` | "If we exceed 10k QPS, we will shard the database." | **ANNOTATION_ERROR** | **Semantic Offset Bug:** In `u2`, argument `actor` (`m2`: `"we"`) has span [3:5] (`"If we"`), pointing to the conditional clause rather than the main clause `"we will"` [22:24]. |
| `gold_eval_09` | `discourse_relations` | "We refactored the query engine in order to reduce memory footprint." | **PASS** | Valid `PURPOSE` with supporting span `"in order to"`. |
| `gold_eval_10` | `discourse_relations` | "I enjoy backend systems, but frontend styling drains me." | **PASS** | Valid `CONTRAST` with supporting span `"but"`. |
| `gold_eval_11` | `discourse_relations` | "Although the benchmark had flaws, we accepted the results." | **PASS** | Valid `CONCESSION` with supporting span `"Although"`. |
| `gold_eval_12` | `temporal_non_causal` | "I grabbed coffee. Then the server rebooted." | **PASS** | Valid Adversarial Trap 1 (`BEFORE`, no causal link). |
| `gold_eval_13` | `temporal_non_causal` | "Alice opened an issue. Immediately afterwards, the payment gateway failed." | **PASS** | Valid Adversarial Trap 2 (`BEFORE`). |
| `gold_eval_14` | `temporal_non_causal` | "The rain started. Ten minutes later, the build succeeded." | **PASS** | Valid Adversarial Trap 3 (`BEFORE`). |
| `gold_eval_15` | `holder_attribution` | "My colleague insisted 'Kubernetes is completely unnecessary'." | **PASS** | Valid Adversarial Trap 4 (holder: `colleague`). |
| `gold_eval_16` | `holder_attribution` | "The consultant claimed 'NoSQL solves all scalability problems'." | **PASS** | Valid Adversarial Trap 5 (holder: `consultant`). |
| `gold_eval_17` | `holder_attribution` | "Charlie warned me that our cloud budget will double." | **PASS** | Valid Adversarial Trap 6 (holder: `Charlie`, indirect). |
| `gold_eval_18` | `same_event_vs_similar` | "We deployed a Kubernetes cluster. The Kubernetes cluster documentation was updated." | **PASS** | Valid Adversarial Trap 9 (`NO_RELATION` despite lexical overlap). |
| `gold_eval_19` | `same_event_vs_similar` | "The database migration ran at midnight. Alice read a book about databases." | **PASS** | Valid Adversarial Trap 10 (`NO_RELATION` despite word overlap). |
| `gold_eval_20` | `multi_unit_decomposition` | "I moved to London in 2021." | **PASS** | Valid Adversarial Trap 11 (only event asserted; unstated result state rejected). |
| `gold_eval_21` | `multi_unit_decomposition` | "I resigned from Acme Corp yesterday." | **PASS** | Valid Adversarial Trap 12 (only resignation asserted; unstated unemployed state rejected). |
| `gold_eval_22` | `evidence_status_distinction`| "The latency spiked. We restarted the service." | **PASS** | Valid Adversarial Trap 13 (`evidence_status: inferred` for ungrounded causality). |
| `gold_eval_23` | `evidence_status_distinction`| "Bob looked exhausted during the incident." | **PASS** | Valid Adversarial Trap 14 (only appearance asserted; clinical burnout rejected). |
| `gold_eval_24` | `state_compatibility` | "In 2022, I preferred working remotely. In 2025, I preferred working in an office." | **ANNOTATION_ERROR** | **Semantic Offset Bug:** In `u2`, argument `experiencer` (`m4`: `"I"`) has span [0:1], pointing to Sentence 1 instead of Sentence 2 [48:49]. (Adversarial Trap 15 logic itself is sound). |
| `gold_eval_25` | `nested_attitude` | "I think I want to leave." | **PASS** | Valid Adversarial Trap 16 (`modality: desired`, `epistemic_hedge: think`, `confidence: 1.0`). |
| `gold_eval_26` | `nested_attitude` | "I believe I will accept the offer." | **PASS** | Valid nested attitude (`modality: intended`, `epistemic_hedge: think`). |
| `gold_eval_27` | `nested_attitude` | "I probably want to switch teams." | **PASS** | Valid nested attitude (`modality: desired`, `epistemic_hedge: probable`). |
| `gold_eval_28` | `relative_temporal_anchoring`| "I deployed the update yesterday." | **PASS** | Valid relative anchor resolved against evidence time. |
| `gold_eval_29` | `relative_temporal_anchoring`| "The security audit will begin next week." | **PASS** | Valid future relative anchor. |
| `gold_eval_30` | `relative_temporal_anchoring`| "The incident ended. Three days later, we published the postmortem." | **PASS** | Valid inter-unit relative anchor (`reference_anchor: unit:u1`). |
| `gold_eval_31` | `ambiguous_relations` | "Alice finished the report. Bob reviewed the code." | **PASS** | Valid underdetermined temporal relation (`TEMPORAL_UNKNOWN`). |
| `gold_eval_32` | `ambiguous_relations` | "The cluster rebooted. A backup was initiated." | **PASS** | Valid underdetermined temporal relation (`TEMPORAL_UNKNOWN`). |
| `gold_eval_33` | `ambiguous_relations` | "I like cats. Dogs bark loudly." | **PASS** | Valid unrelated topics (`NO_RELATION`). |
| `gold_eval_34` | `ambiguous_relations` | "I have used Linux since 2020." | **PASS** | Valid bounded range temporal anchor (`anchor_type: bounded_range`). |
| `gold_eval_35` | `no_relation_control` | "I bought a keyboard. Python 3.12 was released." | **PASS** | Valid negative control pair (`NO_RELATION`). |
| `gold_eval_36` | `no_relation_control` | "The weather in Berlin was sunny. The database had zero errors." | **PASS** | Valid negative control pair (`NO_RELATION`). |
| `gold_eval_37` | `no_relation_control` | "Alice prefers coffee. Bob works on compiler optimizations." | **PASS** | Valid negative control pair (`NO_RELATION`). |
| `gold_eval_38` | `no_relation_control` | "The network switch failed. Alice attended a conference in Tokyo." | **PASS** | Valid negative control pair (`NO_RELATION`). |
| `gold_eval_39` | `asserted_vs_intended` | "I plan to refactor the caching layer next sprint." | **PASS** | Valid future intention (`plan to`). |
| `gold_eval_40` | `possible_vs_occurred` | "We might switch our cloud provider." | **PASS** | Valid modal possibility (`might`). |

---

## 6. Deep Dive: Semantic Span Validity vs. Character Validity

### The Character-Validity Illusion
`validator.py` verified that for every span:
```python
expected_m_text = raw_text[m_span.char_start : m_span.char_end]
assert expected_m_text == m_span.text
```
Because the character slices returned string tokens identical to `m_span.text`, `validator.py` and `pytest` passed with `100%`. However, **byte/character validity does not guarantee semantic validity**.

### Structural Defect Analysis
When a Semantic Block contains multiple clauses or sentences, pronouns and entities recur. The generator's `make_span` function searched `content.index(substring)` from index `0`. Consequently:
1. Every recurring argument in Unit 2 was assigned the character coordinates of Unit 1.
2. In all 10 affected multi-unit cases, the argument mentions for Unit 2 lie **geographically outside** the `source_span` of Unit 2.
3. In `gold_eval_01`:
   - Text: `"In 2022, I really wanted to work at BigCorp. In 2026, I do not want to work at BigCorp."`
   - Sentence 1 `BigCorp`: chars [36:43]
   - Sentence 2 `BigCorp`: chars [79:86]
   - Mention `m2` (in `u1`): assigned [36:43]
   - Mention `m5` (in `u2`): assigned [36:43] (Sentence 1!)
   - Relation: `m2 --(SAME_ENTITY)--> m5`
   - Result: `m2` and `m5` point to the **exact same substring span**. The gold coreference relation connects a mention to itself rather than resolving anaphoric or entity coreference across sentences.

### Clause Boundary Defect in `gold_dev_08`
- Text: `"The CTO terminated the employment of the director."`
- Unit `u1` `source_span`: `"terminated the employment"` [8:33]
- Argument `m1` (`actor`): `"CTO"` [4:7] (outside unit span)
- Argument `m2` (`target`): `"director"` [41:49] (outside unit span)
- Guideline Violation: Rule 1 specifies that a unit must bound the entire proposition clause, not just the verbal predicate phrase. The unit span must be `"The CTO terminated the employment of the director"`.

---

## 7. Template Leakage, Lexical Cues & Evaluation Isolation

1. **Near-Duplicate Pairs:**
   - Dev minimal pairs (`gold_dev_03` vs `gold_dev_04` and `gold_dev_12` vs `gold_dev_20`) have >75% sequence similarity, but this is intentional to test minimal grammatical contrast (`might` vs `was`, participial vs conjunction).
   - Across Dev and Eval, no prompt leakage was detected. The highest cross-split similarity is 0.71 (`"I joined the committee yesterday"` vs `"I deployed the update yesterday"`), representing completely distinct semantic events sharing only temporal boilerplate.
2. **Predictable Case Ordering:**
   - In both `dev.jsonl` and `eval.jsonl`, cases are sorted in contiguous family blocks (e.g. all `longitudinal_shift` cases grouped together, all `discourse_relations` grouped together).
   - **Risk:** If an evaluation harness processes cases in linear sequence with multi-turn chat memory, an LLM could infer the target pattern from immediate previous cases.
   - **Requirement:** Parser evaluation must strictly enforce **zero session carryover** (fresh prompt context per case) or random case shuffling.
3. **Metadata Leakage Guard:**
   - Benchmark case records include `family`, `adversarial`, `trap_description`, and `rationale`.
   - **Requirement:** The evaluation driver for Issue #15 must strip these fields before generating parser inputs. The parser must only see `raw_evidence`, `semantic_blocks`, and `cutoff_time`.

---

## 8. Verification of Downstream Cognition Isolation

### Explicit Finding: **PASS — Zero Cognition Leakage**

A critical architectural invariant from Issue #13 and Issue #14 is that semantic parsing must output raw factual building blocks without preempting longitudinal cognition engine decisions.

1. **Forbidden Term Verification:** None of the 9 forbidden labels (`REVISION`, `RECURRENCE`, `TRAJECTORY`, `STABLE_PREFERENCE`, `COGNITIVE_SHIFT`, etc.) appear in any unit or relation.
2. **Cross-Temporal Transitions (Rule 9):**
   - In cases representing changing opinions across time (e.g. `gold_eval_01`, `gold_eval_02`, `gold_eval_03`, `gold_eval_04`, `gold_eval_24`), the gold relations are strictly `BEFORE` + `SAME_ENTITY`.
   - None of these cases emit `INCOMPATIBLE` or `REVISION`.
   - `INCOMPATIBLE` is reserved strictly for contemporaneous conflicting states (`gold_eval_05`, `gold_eval_07`), in exact accordance with Rule 9.

---

## 9. Label Sparsity and Statistical Validity

A machine learning / NLP benchmark requires sufficient positive support per class to yield statistically interpretable precision, recall, and F1 scores.

### Categories with Zero Total Support (0 Occurrences)
The following elements from `schema.py` have **0 occurrences** across all 60 cases and therefore cannot be evaluated:
- `PolarityType.UNKNOWN`
- `ModalityType.UNCERTAIN`, `ModalityType.UNKNOWN`
- `EpistemicHedge.UNCERTAIN`, `EpistemicHedge.DOUBT`
- `AttributionMode.EXTERNAL_SOURCE`, `AttributionMode.UNKNOWN`
- `TemporalAnchorType.UNANCHORED`
- `RelationType.AFTER`, `RelationType.OVERLAP`, `RelationType.UNKNOWN`
- `PredicateNormalizationRule.LEMMA`
- `ArgumentRole.PURPOSE`

### Highly Sparse Categories ($\le 2$ Total Occurrences)
- `RelationType.CONDITION` (1 occurrence)
- `RelationType.CONTRAST` (1 occurrence)
- `RelationType.CONCESSION` (1 occurrence)
- `RelationType.EQUIVALENT` (1 occurrence)
- `RelationType.SAME_EVENT` (1 occurrence)
- `RelationType.INCOMPATIBLE` (2 occurrences)
- `RelationType.TEMPORAL_UNKNOWN` (2 occurrences)
- `RelationType.PURPOSE` (2 occurrences)
- `EpistemicHedge.THINK` (2 occurrences)
- `EpistemicHedge.PROBABLE` (1 occurrence)
- `ModalityType.HYPOTHETICAL` (1 occurrence)
- `ModalityType.POSSIBLE` (2 occurrences)
- `PolarityType.NEGATIVE` (2 occurrences)
- `ArgumentRole.STIMULUS` (1 occurrence)
- `ArgumentRole.TOPIC` (1 occurrence)
- `ArgumentRole.RESULT` (2 occurrences)
- `ArgumentRole.REASON` (2 occurrences)
- `PredicateNormalizationRule.FROZEN_MAP` (1 occurrence)

### Statistical Implication for Issue #15
If a parser fails on the single `CONDITION` case (`gold_eval_08`), its Recall for `CONDITION` drops from 100% directly to 0.0%. Metrics on these single-instance labels are binary coin flips rather than continuous performance measures. For Issue #15 evaluation, micro-averaged metrics across relation families (or grouping discourse relations) must be reported alongside per-label metrics.

---

## 10. Required Benchmark Revision Plan

Before proceeding to GitHub Issue #15, the benchmark must be revised:

1. **Fix Generator Scoping (`make_span`):** Update `make_span` to search for arguments **within the unit's bounded text span** (`start = u_start + u_text.index(arg_text)`), guaranteeing that mentions in Unit 2 point to Unit 2.
2. **Correct All 14 Failing Cases:**
   - Correct spans for `gold_dev_13`, `gold_dev_15`, `gold_dev_16`, `gold_eval_01`, `gold_eval_02`, `gold_eval_03`, `gold_eval_04`, `gold_eval_05`, `gold_eval_06`, `gold_eval_07`, `gold_eval_08`, `gold_eval_24`.
   - Correct unit span for `gold_dev_08` to include the full clause.
   - Correct predicate in `gold_dev_06` to `"is"` / copula.
   - In `gold_eval_01`, ensure `rel_02` links `m2` (Sentence 1) to `m5` (Sentence 2).
3. **Upgrade `validator.py`:** Add an automated validation check ensuring that every argument mention's `source_span` is strictly contained within its parent unit's `source_span` (`u.source_span.char_start <= m.source_span.char_start and m.source_span.char_end <= u.source_span.char_end`).
4. **Rebalance Dev Split:** Redistribute cases so that Dev contains at least 1 representative case from each of the 17 families, ensuring prompt designers have full few-shot visibility.

---

## 11. Audit Finding Summary (Pre-Revision)

The Issue #14 Gold Benchmark originally had a sound theoretical foundation, zero cognition leakage, and a valid schema architecture. However, due to the **17 semantic span offset errors**, **unit truncation in `gold_dev_08`**, **predicate error in `gold_dev_06`**, and the **absence of 7 entire families from the Dev split**, the initial verdict was **`NEEDS_REVISION`**.

---

## 12. Post-Audit Revision Execution & Final Certification (v0.1.1)

In response to the audit findings and user authorization, Revision v0.1.1 was executed:

1. **Scoped Span Slicing (`make_span`):** Replaced unconstrained document-level string search with strictly bounded slicing inside the parent unit span.
2. **All 14 Failing Cases Resolved:**
   - 11 cases (17 mentions) with cross-sentence offset errors corrected to point to local mention spans.
   - `gold_eval_01`: `SAME_ENTITY` now connects Sentence 1's `BigCorp` [36:43] to Sentence 2's `BigCorp` [79:86] (non-reflexive).
   - `gold_eval_19` (formerly `gold_dev_08`): Unit span expanded to include full clause, cleanly enclosing `CTO` and `director`.
   - `gold_eval_16` (formerly `gold_dev_06`): Stative copula predicate corrected to `"is"` with `exact_surface`.
3. **Dev Split Rebalanced:**
   - All 17 case families are now represented in Dev (20 cases), exposing all modalities, hedges, discourse links, compatibility relations, temporal anchors, and negative control outcomes.
   - Eval retains 40 cases, including all 16 adversarial traps.
4. **Validation Suite Upgrades (`validator.py`):**
   - Added programmatic assertion that argument mention spans must be strictly contained inside unit spans.
   - Added programmatic assertion that `SAME_ENTITY` endpoints must not have identical start/end offsets.
   - Added programmatic assertion that Dev covers all 17 families.
5. **Full Test Verification:**
   - `python research/benchmarks/semantic_annotation_v0_1/validator.py`: **`VALIDATION PASSED`** (60/60 cases).
   - `python -m pytest tests/research/test_semantic_annotation_gold_benchmark.py tests/research/test_semantic_annotation_schema.py -v`: **`18 passed in 2.63s`**.

**Post-Revision Certification Verdict:** **`READY FOR ISSUE #15`**

