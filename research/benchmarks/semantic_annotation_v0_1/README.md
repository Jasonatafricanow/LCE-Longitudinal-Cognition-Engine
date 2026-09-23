# LCE Semantic Parsing Gold Benchmark v0.1

**Status:** Gold Standard Benchmark Dataset (GitHub Issue #14)  
**Contract Version:** Frozen v0.1 Semantic Annotation Ontology (`research/semantic_annotation/schema.py`)  
**Scope:** Research Only — Used to evaluate semantic parsers (Issue #15) prior to typed-graph experiments (Issue #16/17).  
**Target Size:** 60 cases (20 Dev, 40 Eval, including $\ge 15$ Adversarial Traps).

---

## 1. Objective and Architectural Boundary

This benchmark evaluates whether an automated semantic parser or human annotator can convert cutoff-bounded evidence into the frozen v0.1 meaning representation **without hindsight, world-knowledge hallucination, or downstream cognition-level interpretation**.

```text
Raw Evidence + Bounded Semantic Blocks
                  │
                  ▼
          [Semantic Parser]
                  │
                  ▼
     Predicted Semantic Units & Relations
                  │
                  ▼
      [Gold Benchmark Evaluator] <─── dev.jsonl / eval.jsonl (Gold v0.1)
```

### Core Design Rules
1. **Source-Bounded:** Every unit and mention must map to an exact, non-empty character span within the input raw evidence.
2. **Decoupled Cognition:** No downstream cognition labels (`REVISION`, `RECURRENCE`, `TRAJECTORY`, `COGNITIVE_SHIFT`, etc.) appear in gold annotations.
3. **First-Class Uncertainty:** Where evidence is missing, unstated, or genuinely ambiguous, the gold label is strictly `UNKNOWN` or `NO_RELATION`. Guessing is penalized.
4. **Mention-Based Coreference:** `SAME_ENTITY` strictly connects stable argument `mention_id`s, not proposition IDs or pseudo-identifiers.
5. **Decoupled Nested Attitudes:** Epistemic hedging ("I think") is captured via `epistemic_hedge` without collapsing the desire `modality` or penalizing annotation confidence.
6. **Deterministic Predicate Normalization:** Normalization is mechanical (`exact_surface`, `lemma`, `compound_lower`, `frozen_map`). Open-ended synonym substitution is prohibited.
7. **Audit-Only Inferences:** `inferred` units/relations are audit-only and must never enter the positive graph.

---

## 2. Dataset Split and Case Distribution

| Split | File | Cases | Adversarial Traps | Primary Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Development** | `dev.jsonl` | 20 | 0 | Prompt engineering, error analysis, rule refinement |
| **Evaluation** | `eval.jsonl` | 40 | 16 | Held-out frozen evaluation of parser accuracy |
| **Total** | | **60** | **16** | |

---

## 3. Case Family Coverage Matrix

| Case Family | Dev Count | Eval Count | Description & Invariants Tested |
| :--- | :---: | :---: | :--- |
| `asserted_vs_intended` | 2 | 2 | Distinguishes completed/ongoing occurrences (`asserted`) from planned future commitments (`intended`). |
| `possible_vs_occurred` | 2 | 2 | Distinguishes epistemic possibility (`possible`, "might") from factually occurred events (`asserted`). |
| `holder_attribution` | 2 | 3 | Distinguishes first-person author belief (`direct_speaker`) from direct quotes (`direct_quote`) and reported hearsay (`indirect_report`). |
| `evidence_status_distinction` | 2 | 2 | Explicit text vs strict logical entailment vs contextual inference (`explicit`, `entailed`, `inferred`). |
| `negation_scope` | 2 | 2 | Syntactic negation vs lexical negation; attitude towards negative targets vs negative attitudes. |
| `multi_unit_decomposition` | 2 | 2 | Multiple independent clauses inside a single Semantic Block segmented into separate atomic units. |
| `same_entity_paraphrase` | 2 | 2 | Coreferent argument mentions across paraphrased spans connected via `SAME_ENTITY` using stable mention IDs. |
| `same_event_vs_similar` | 2 | 2 | Strict event token coreference (`SAME_EVENT`) vs topical similarity without token identity (`NO_RELATION`). |
| `temporal_non_causal` | 2 | 2 | Chronological sequence without causal connection (`BEFORE` with `NO_RELATION` for cause). |
| `explicit_causality` | 2 | 2 | Direct causal relation supported by explicit lexical connectives (`CAUSE` with `supporting_spans`). |
| `discourse_relations` | 0 | 4 | Structured logical discourse links: `CONDITION`, `PURPOSE`, `CONTRAST`, and `CONCESSION`. |
| `longitudinal_shift` | 0 | 4 | Opposite states at non-overlapping times (e.g. 2022 vs 2026): modeled via `BEFORE` + opposite polarities, **never** `INCOMPATIBLE` or `REVISION`. |
| `state_compatibility` | 0 | 3 | Contemporaneous state equivalence (`EQUIVALENT`) vs contemporaneous conflict (`INCOMPATIBLE` under overlapping time). |
| `ambiguous_relations` | 0 | 4 | Underdetermined pairs where the only sound answer is `UNKNOWN`. Penalizes forced guessing. |
| `no_relation_control` | 0 | 4 | Unrelated proposition pairs evaluated as `NO_RELATION`. |
| `relative_temporal_anchoring` | 0 | 3 | Relative time resolution requiring explicit `reference_anchor`. |
| `nested_attitude` | 0 | 3 | Shallow nested attitude: `modality: desired`, `epistemic_hedge: think`, `confidence: 1.0`. |
| **Adversarial Traps** | **0** | **16** | Specific traps designed to catch over-helpful LLM hallucinations (see Section 4). |

---

## 4. Adversarial Trap Taxonomy (16 Eval Cases)

At least 15 evaluation cases (16 implemented) test resistance against common LLM hallucination patterns:

1. **Post-Hoc Causal Hallucination (Traps 1–3):**
   - Two events occur chronologically adjacent without connective (e.g. "I grabbed coffee. Then the server rebooted.").
   - *Model Failure:* Predicting `CAUSE`.
   - *Gold Target:* `BEFORE` + `NO_RELATION` (causal relation).
2. **Holder Attribution Spillover (Traps 4–6):**
   - Quotation or report of a controversial view (e.g. "My colleague insisted 'Microservices are dead'").
   - *Model Failure:* Attributing `holder_ref: "user"`.
   - *Gold Target:* `holder_ref: "colleague"`, `attribution_mode: "direct_quote"` (or `"indirect_report"`).
3. **Premature Cognition Interpretation (Traps 7–8):**
   - Author states opposite preference across 4 years (2022 vs 2026).
   - *Model Failure:* Predicting `REVISION`, `COGNITIVE_SHIFT`, or `TRAJECTORY`.
   - *Gold Target:* Atomic units linked by `BEFORE` and opposite polarity/value. Forbidden labels rejected.
4. **Lexical Overlap Distractor (Traps 9–10):**
   - Two sentences share heavy domain terminology ("Kubernetes cluster pods deployment") but describe unrelated events.
   - *Model Failure:* Predicting `SAME_EVENT` or `EQUIVALENT` due to embedding / token similarity.
   - *Gold Target:* `NO_RELATION`.
5. **Manufactured Result State (Traps 11–12):**
   - Sentence describes relocation or resignation ("I resigned from Acme Corp").
   - *Model Failure:* Inventing an unstated ongoing state ("unemployed" or "not working at Acme") and linking via `CAUSE`.
   - *Gold Target:* Only the single asserted `event` unit.
6. **Pragmatic Speculation as Explicit (Traps 13–14):**
   - Plausible implicature not asserted in text ("The server was slow. We investigated the database.").
   - *Model Failure:* Emitting `CAUSE` or `theme` with `evidence_status: "explicit"`.
   - *Gold Target:* Only explicit text, or marked `evidence_status: "inferred"`.
7. **Cross-Time False Incompatibility (Trap 15):**
   - Opposite attitudes at non-overlapping dates.
   - *Model Failure:* Predicting `INCOMPATIBLE`.
   - *Gold Target:* `BEFORE` with opposite polarities; `INCOMPATIBLE` rejected due to lack of temporal overlap.
8. **Hedged Desire Flattening (Trap 16):**
   - "I think I want to leave."
   - *Model Failure:* Collapsing into `modality: "uncertain"` or arbitrarily reducing annotation confidence.
   - *Gold Target:* `modality: "desired"`, `epistemic_hedge: "think"`, `confidence: 1.0`.

---

## 5. Machine-Readable Format

Every JSONL record conforms to [`schema.json`](file:///c:/projects/LCE/research/benchmarks/semantic_annotation_v0_1/schema.json):
```json
{
  "case_id": "gold_eval_01",
  "split": "eval",
  "family": "longitudinal_shift",
  "adversarial": true,
  "trap_description": "LLM tempted to emit REVISION or INCOMPATIBLE across 4-year gap",
  "raw_evidence": [
    {
      "evidence_id": "ev_01",
      "content": "In 2022, I loved working at BigCorp. In 2026, I hate big corporations.",
      "occurred_at": "2026-09-23T00:00:00Z"
    }
  ],
  "semantic_blocks": [
    {
      "block_id": "b_01",
      "content": "In 2022, I loved working at BigCorp. In 2026, I hate big corporations.",
      "occurred_start": "2022-01-01T00:00:00Z",
      "occurred_end": "2026-09-23T00:00:00Z",
      "raw_evidence_ids": ["ev_01"]
    }
  ],
  "cutoff_time": "2026-09-23T00:00:00Z",
  "gold_document": { ... },
  "rationale": "Exact justification for labels and exclusion of forbidden cognition terms."
}
```

---

## 6. Validation and Quality Gate

Run the benchmark validator:
```powershell
python research/benchmarks/semantic_annotation_v0_1/validator.py
```
The validator enforces:
- Exact character slice alignment between `source_span` and `raw_evidence.content`.
- Global uniqueness of `annotation_id`s and `mention_id`s.
- Strict mention-based `SAME_ENTITY` endpoints.
- Exclusion of forbidden cognition labels.
- Exclusion of inferred units/relations from graph admission.
- Exact total of 60 cases (20 dev, 40 eval, $\ge 15$ adversarial).
