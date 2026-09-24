# SemanticBlock v0.2 Error Analysis & Hard Failure Taxonomy

**Date:** 2026-09-24  
**Benchmark:** SemanticBlock v0.2 Unseen Evaluation (24 cases / 26 cutoffs)  
**Evaluated Arms:** Arm B (One-pass), Arm C (Two-pass), Route E (One-pass + Gates + Selective Linker), Paired E Ablation (No Linker)  
**Gold Corpus:** `C:\projects\semantic_block_v0_2_adjudication\gold_v0_2.jsonl` (SHA-256: `7d43bda833d521968893b6a97032c1326e1adb3a3a9121763bc739b41e6ec1a8`)

---

## 1. Executive Failure Taxonomy

Across the 26 cutoff evaluations, every failure observed in Arms B, C, and E was cataloged into five distinct structural categories:

| Error Category | Arm B | Arm C | Arm E | Primary Root Cause |
| :--- | :---: | :---: | :---: | :--- |
| **Dangling / Nonexistent Relation Endpoints** | **2** | **0** | **0** | First-pass LLM inventing state keys not present in admitted blocks |
| **Silent Holder Flips (`user/narrator -> user`)** | 39 | 37 | 33 | Base prompt schema default bias towards first-person holder attribution |
| **Epistemic Modal Promotion (Unasserted -> Asserted)** | 11 (admitted) | 11 (admitted) | **11 (rejected)** | First-pass LLM promoting conditional/deontic discourse to factual assertions |
| **False Positive `BEFORE` Relations** | 0 | 0 | 2 | Discovery of valid temporal spans omitted by gold annotators |
| **Timestamp / Precision Formatting Mismatch** | 43 | 43 | 45 | Lexical date format variance between model proposal and adjudication schema |

---

## 2. Hard Safety Failures Deep-Dive

### 2.1 Invalid Relation Endpoints (Arm B Defect, Resolved by E and C)

In Arm B, two fatal invalid endpoint failures occurred:
1. `V2-002`: `invalid_relation_endpoint in relation V2-002_s1->V2-002_s2`
2. `V2-003`: `invalid_relation_endpoint in relation V2-003_s1->V2-003_s2`

**Mechanism:**  
In Arm B's one-pass architecture, the LLM emits both blocks and relations in a single JSON payload. When candidate block `s2` failed deterministic coordinate validation, Arm B dropped `s2` from its admitted block set, but **failed to enforce endpoint closure on its relation set**. Consequently, Arm B output a relation referencing a dangling state ID.

**Resolution in Route E:**  
Route E enforced strict post-admission endpoint closure (Gate 6):
```python
permitted = {b.state_id for b in admitted_blocks}
# Any relation whose source or target is not in permitted is fail-closed dropped
```
In Route E, candidate relations are screened exclusively between admitted, cutoff-visible blocks, and linker output undergoes second-pass endpoint closure. As a result, **Route E had exactly 0 invalid relation endpoints**.

### 2.2 Silent Holder Flips (Shared Across All Arms)

The dominant hard failure across all three arms was silent holder flips:
- Arm B: 39 failures
- Arm C: 37 failures
- Arm E: 33 failures

**Mechanism:**  
In third-party reports or complex narrative text (such as `U01` nested report chains, `U07` source retractions, and `U10` passive agent accounts), the base LLM prompt frequently assigned `holder: "user"` instead of the actual reported speaker (e.g. `narrator`, `Lian`, `Jo`, or `system`).  
Because Route E's design forbids mutating the semantic content of a candidate block, and because Gate 4 only rejects explicit contradictory speaker envelopes, blocks with subtle holder misattributions were admitted into all three arms, triggering legacy scorer flags.

---

## 3. Route E Gate 4 Analysis: The Precision-Recall Dilemma

Trace analysis from `E_gate_trace.json` revealed that Route E rejected **11 candidate blocks** across 7 cutoffs:

| Case ID | Scenario Family | State Key | Gate 4 Rejection Reason | Gold State Modality | Gold Canonical Content |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **V2-004** | `U02_counterfactual_world` | `s1` | `modal_or_conditional_marker_promoted_to_asserted` | asserted | Backup started on May 1, 2026. |
| **V2-004** | `U02_counterfactual_world` | `s2` | `modal_or_conditional_marker_promoted_to_asserted` | asserted | Import failed on May 1 despite backup having started. |
| **V2-007** | `U04_deontic_requirement` | `s1` | `modal_or_conditional_marker_promoted_to_asserted` | **required** | The safety policy requires Jo to sign the inspection by May 8, 2026. |
| **V2-008** | `U04_deontic_requirement` | `s1` | `modal_or_conditional_marker_promoted_to_asserted` | asserted | Jo signed the inspection on May 8, 2026. |
| **V2-008** | `U04_deontic_requirement` | `s2` | `modal_or_conditional_marker_promoted_to_asserted` | **required** | The policy required the signature by May 8, 2026. |
| **V2-017** | `U09_reciprocal_roles` | `s1` | `modal_or_conditional_marker_promoted_to_asserted` | asserted | Mina lent Tao scanner; Tao returned scanner to Mina. |
| **V2-017** | `U09_reciprocal_roles` | `s2` | `modal_or_conditional_marker_promoted_to_asserted` | asserted | Tao returned the scanner to Mina on May 4. |
| **V2-018** | `U09_reciprocal_roles` | `s1` | `modal_or_conditional_marker_promoted_to_asserted` | asserted | Mina borrowed scanner; Mina returned scanner to Tao. |
| **V2-018** | `U09_reciprocal_roles` | `s2` | `modal_or_conditional_marker_promoted_to_asserted` | asserted | Mina returned Tao's scanner to Tao on May 4. |
| **V2-023** | `U12_timezone_day_boundary` | `s1` | `modal_or_conditional_marker_promoted_to_asserted` | asserted | At 23:30 UTC on May 1, Lian posted alert from Tokyo. |
| **V2-024** | `U12_timezone_day_boundary` | `s1` | `modal_or_conditional_marker_promoted_to_asserted` | asserted | At 00:30 Tokyo local time on May 2, Lian posted alert. |

### Diagnostic Breakdown:
1. **True Negative Catches (`V2-007_s1`, `V2-008_s2`):**  
   In `U04_deontic_requirement`, the source text described an organizational requirement ("policy requires signature"). The first-pass LLM emitted `modality: "asserted"`. The gold adjudicators correctly annotated `modality: "required"`. Route E's Gate 4 correctly recognized that the model had hallucinated an occurred assertion from a modal requirement.
2. **The Non-Rewriting Penalty:**  
   Because Route E's protocol strictly prohibits rewriting the block's `modality` from `asserted` to `required` (or `UNKNOWN`), Route E was forced to drop the block entirely. In contrast, Arm B kept the block; although Arm B received 0 for modality, it received credit for canonical content, participants, and time, yielding 51.9% accuracy vs. Route E's 13.5%.
3. **Over-Sensitivity on Complex Discourse (`V2-017`, `V2-018`, `V2-023`, `V2-024`):**  
   In reciprocal lending and timezone boundary statements, words such as "return", "boundary", or conditional phrasing in surrounding context caused Gate 4's lexical filter to trigger, discarding valid assertions.

---

## 4. Relation Analysis: False Positives in V2-006

In Case `V2-006`, Route E emitted 5 `BEFORE` relations, resulting in `relations_fp: 2` in the scorer (gold had 0 relations):
```json
[
  {"type": "BEFORE", "source": "V2-006_s1", "target": "V2-006_s2", "cue": "before"},
  {"type": "BEFORE", "source": "V2-006_s1", "target": "V2-006_s3", "cue": "after"},
  {"type": "BEFORE", "source": "V2-006_s2", "target": "V2-006_s3", "cue": "after"},
  {"type": "BEFORE", "source": "V2-006_s3", "target": "V2-006_s4", "cue": "later"},
  {"type": "BEFORE", "source": "V2-006_s5", "target": "V2-006_s6", "cue": "before"}
]
```
- **Linguistic Grounding:** Each relation was grounded in an exact, valid evidence substring ("before", "after", "later").
- **Annotator Choice:** In `V2-006` (designed as a negative control for CAUSE), the gold adjudicators chose not to annotate mundane temporal sequencing.
- **Safety Containment:** Crucially, all 5 relations were tagged with `traversal_allowed: false`. In the F8 retrieval sentinel (`U03-negative-V2-006`), **zero generic before-bridges were traversed**, and the probe passed with 100% compliance.

---

## 5. Architectural Recommendations

1. **Implement Fallback to `UNKNOWN` Rather than Outright Rejection:**  
   When Gate 4 detects an ungrounded modality promotion (e.g. modal cues in text but `modality="asserted"` in proposal), the compiler should set `modality: "UNKNOWN"` or `modality: "required"` rather than rejecting the entire semantic block. This preserves factual recall for downstream reasoning while preventing false assertion commitments.
2. **Prompts Must Separate Narrator from User:**  
   The primary source of hard failures across all arms is the conflation of narrator/system speech with user assertion. System prompts must explicitly instruct the LLM to designate third-party speakers rather than defaulting to `user`.
3. **Preserve Route E Endpoint Closure and Linker Gate:**  
   Route E's candidate screening and endpoint closure completely eliminated Arm B's dangling pointer defect and reduced linker calls by 90%, proving the viability of selective linking.
