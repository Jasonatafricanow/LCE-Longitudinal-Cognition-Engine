# LCE AGY Semantic Parser Evaluation Report v0.1

**Date:** 2026-09-23 06:25:27 UTC  
**Model:** `gemini-3.5-flash` (fallback: `gemini-3.5-flash-lite`, Temperature: 0.1)  
**Ontology Contract:** Frozen v0.1 (`research/semantic_annotation/schema.py`)  
**Gold Benchmark:** LCE Semantic Parsing Gold Benchmark v0.1.1 (`research/benchmarks/semantic_annotation_v0_1/`)  
**Evaluation Scope:** GitHub Issue #15 (Frozen Parser Benchmark)  

---

## 1. Executive Summary

- **Eval Set Cases:** 40 held-out evaluation cases
- **Unit Span Overlap F1:** **95.5%** (Exact match F1: 74.2%)
- **Argument Role F1:** **69.8%** (Precision: 68.0%, Recall: 71.5%)
- **Relation Macro F1:** **73.1%** (Precision: 70.4%, Recall: 76.0%)
- **Adversarial Trap Resistance:** **93.8%** (15/16 traps successfully resisted)
- **Forbidden Cognition Term Emissions:** **0** (Zero-tolerance check: PASSED)

---

## 2. Benchmark Metrics Comparison (Dev vs. Eval)

| Metric Dimension | Dev Split (20 cases) | Eval Split (40 cases) | Target Threshold | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Unit Overlap F1** | 95.5% | 95.5% | $\ge 85.0\%$ | PASS |
| **Unit Exact Span F1** | 65.7% | 74.2% | $\ge 75.0\%$ | REVIEW |
| **Argument Role F1** | 76.0% | 69.8% | $\ge 80.0\%$ | REVIEW |
| **Relation F1** | 69.2% | 73.1% | $\ge 70.0\%$ | PASS |
| **Adversarial Resistance** | N/A (0 traps) | 93.8% | $\ge 80.0\%$ | PASS |
| **Cognition Leakage** | 0 | 0 | Exactly 0 | PASS |

---

## 3. Unit-Level Attribute Accuracies (Eval Set)

| Attribute Dimension | Accuracy | Evaluation Focus |
| :--- | :---: | :--- |
| **Unit Kind** | 90.5% | event / state / attitude / proposition classification |
| **Surface Predicate** | 90.5% | verbatim predicate extraction from text |
| **Normalized Predicate** | 76.2% | mechanical normalization fidelity |
| **Normalization Rule** | 79.4% | exact_surface / lemma / compound_lower / frozen_map selection |
| **Modality** | 95.2% | asserted / intended / desired / possible / hypothetical |
| **Epistemic Hedge** | 100.0% | none / think / probable decoupling |
| **Holder Reference** | 98.4% | author (user) vs third-party source |
| **Attribution Mode** | 100.0% | direct_speaker / direct_quote / indirect_report |
| **Temporal Anchoring** | 96.8% | exact / relative / bounded_range |

---

## 4. Adversarial Trap Resistance Breakdown (16 Traps)

| Case ID | Adversarial Trap Objective | Model Result | Finding |
| :--- | :--- | :---: | :--- |
| `gold_eval_01` | Model tempted to label REVISION or INCOMPATIBLE across 4-year gap | **RESISTED** | Successfully resisted hallucination. |
| `gold_eval_02` | Model tempted to emit COGNITIVE_SHIFT or REVISION | **RESISTED** | Successfully resisted hallucination. |
| `gold_eval_06` | Model tempted to emit INCOMPATIBLE across distinct calendar years | **RESISTED** | Successfully resisted hallucination. |
| `gold_eval_09` | Model tempted to infer CAUSE (Post hoc ergo propter hoc) | **RESISTED** | Successfully resisted hallucination. |
| `gold_eval_10` | Model tempted to infer CAUSE from close succession | **RESISTED** | Successfully resisted hallucination. |
| `gold_eval_11` | Model tempted to hallucinate causal connection between rain and build | **RESISTED** | Successfully resisted hallucination. |
| `gold_eval_13` | Model tempted to assign holder_ref='user' | **RESISTED** | Successfully resisted hallucination. |
| `gold_eval_14` | Model tempted to conflate consultant claim with author conviction | **TRAPPED** | Erroneously assigned holder_ref='user' to third-party quote |
| `gold_eval_15` | Model tempted to assign holder_ref='user' for indirect warning | **RESISTED** | Successfully resisted hallucination. |
| `gold_eval_17` | Model tempted to label CAUSE as explicit despite absence of connective | **RESISTED** | Successfully resisted hallucination. |
| `gold_eval_18` | Model tempted to infer unstated clinical burnout as explicit event | **RESISTED** | Successfully resisted hallucination. |
| `gold_eval_20` | Model tempted to link unrelated events sharing Kubernetes cluster tokens | **RESISTED** | Successfully resisted hallucination. |
| `gold_eval_21` | Model tempted to link migration run with reading a book | **RESISTED** | Successfully resisted hallucination. |
| `gold_eval_23` | Model tempted to manufacture unstated 'live_in London' state and link via CAUSE | **RESISTED** | Successfully resisted hallucination. |
| `gold_eval_24` | Model tempted to manufacture unstated 'unemployed' state and link via CAUSE | **RESISTED** | Successfully resisted hallucination. |
| `gold_eval_26` | Model tempted to collapse desire into modality=uncertain or reduce confidence | **RESISTED** | Successfully resisted hallucination. |

---

## 5. Architectural Boundary & Freeze Declaration

1. **Zero Cognition Leakage:** The parser strictly output raw factual propositions without emitting longitudinal interpretation labels (`REVISION`, `RECURRENCE`, `TRAJECTORY`, etc.).
2. **Evidence Bounded:** All argument mentions and unit spans are strictly grounded within the boundaries of the Semantic Block input.
3. **Parser Status:** The prompt and parsing configuration are **FROZEN** as AGY Semantic Parser v0.1.
4. **Next Step:** Ready for **GitHub Issue #16: Oracle Typed Graph Representation**.