# Issue #19 SemanticBlock Benchmark Evaluation Report

**Date:** 2026-09-24  
**Run ID:** `run_20260924_012403`  
**Git HEAD:** `fc047c0d352dc87bdf514e2861a329adb5c1b2c3` (`research/semantic-block-issue-19`)  
**Frozen Manifest SHA-256:** `b7a0f012b47f211c3afc255c17b6170f7aa69093c243af65ec8fad9ab8fa6997`  
**Overall Pre-Registered Verdict:** **`INCONCLUSIVE`**  

> [!IMPORTANT]
> Per Section 1 and Section 6 of the Frozen Execution Protocol, this benchmark run is **exploratory** because the gold corpus was authored in a single freeze without independent double-annotation or adjudication, and held-out cases share scenario templates with development cases. `READY_FOR_PRODUCTION_DESIGN` is explicitly unavailable on this benchmark version. The pre-registered outcome is capped at `INCONCLUSIVE` even where an arm passes all exploratory gates.

## 1. Executive Summary & Arm Verdicts

| Arm | Description | Held-out Accuracy | Exact Block Count | Held-out Relations F1 | Hard Gate Status | Exploratory Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| **A** | V1 reference memory stream compiler baseline | 8.8% | 35.7% | 0.0% | CLEAN | **`INCONCLUSIVE`** |
| **B** | One-pass structured LLM proposal + deterministic validation | 94.0% | 100.0% | 61.5% | FAIL (1 violations) | **`BLOCKED`** |
| **C** | Recommended two-pass (internal proposal + validation + typed linker) | 82.7% | 78.6% | 66.7% | FAIL (1 violations) | **`BLOCKED`** |
| **D** | Full-frame internal representation projected to public block shape | 86.5% | 92.9% | 50.0% | FAIL (4 violations) | **`BLOCKED`** |

## 2. Held-Out Evaluation (12 Cases)

| Arm | Micro Field Acc | Macro Family Acc | Account Exact Match | Rel TP | Rel FP | Rel FN | Latency Median (ms) | Latency p95 (ms) | Tokens Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 8.79% | 11.22% | 0.0% | 0 | 0 | 5 | 0.5 | 1.7 | 0 |
| B | 93.96% | 92.95% | 53.6% | 4 | 4 | 1 | 5577.3 | 12628.8 | 28916 |
| C | 82.69% | 86.75% | 39.3% | 3 | 1 | 2 | 8999.9 | 15845.3 | 35333 |
| D | 86.54% | 86.00% | 3.6% | 4 | 7 | 1 | 5833.0 | 19512.8 | 21449 |

## 3. Development Evaluation (42 Cases)

| Arm | Micro Field Acc | Macro Family Acc | Exact Block Count | Account Exact Match | Rel Precision | Rel Recall | Rel F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 9.75% | 13.53% | 50.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| B | 88.64% | 87.86% | 80.8% | 24.4% | 80.0% | 100.0% | 88.9% |
| C | 86.58% | 89.71% | 84.6% | 27.9% | 91.7% | 68.8% | 78.6% |
| D | 80.86% | 81.09% | 80.8% | 11.6% | 40.0% | 62.5% | 48.8% |

## 4. Critical Probe Results

### F7 / B03 Cross-Sentence Causality Sentinel
- **B03-C / B03-P (Positive Causal Path):** Requires s1->s2 and s2->s3 directed CAUSE edges, s1->s2->s3 full path retrieval, zero direct s1->s3 shortcut, zero BEFORE substitution.
- **B03-N (Negative Control):** Requires zero CAUSE edges and empty causal path.

| Arm | B03-C Path | B03-P Path | B03-N Negative Gate | Direct Shortcut Absent | F7 Status |
| --- | --- | --- | --- | --- | --- |
| A | FAIL | FAIL | PASS | PASS | **`FAIL`** |
| B | PASS | PASS | PASS | PASS | **`PASS`** |
| C | PASS | PASS | PASS | PASS | **`PASS`** |
| D | FAIL | PASS | FAIL | PASS | **`FAIL`** |

### F8 / B17 Vector-Only vs. Vector+Graph Retrieval Sentinel (Accepted C Blocks)
- Evaluates identical accepted C blocks under $k=3$, 2 relation hops from seeds `s1` (A-login) and `s4` (X-incident).
- In positive fixtures (B17-C, B17-P), graph retrieval along traversable CAUSE edges recovers the s4->s5->s6 incident chain.
- BEFORE edges have `traversal_allowed=False` and contributed **0 generic bridge candidates**.
- In negative fixture (B17-N), zero causal edges are traversed.

| Fixture | Variant | Positive Causal Chain Recovered | Generic BEFORE Bridge Absent | F8 Gate Status |
| --- | --- | --- | --- | --- |
| `B17-C` | C | YES | CLEAN (0 bridge) | **`PASS`** |
| `B17-P` | P | YES | CLEAN (0 bridge) | **`PASS`** |
| `B17-N` | N | YES | CLEAN (0 bridge) | **`PASS`** |

## 5. Gate Evaluation for Recommended Arm C

- **Hard Safety Gates:** Zero held-out unsupported canonical assertions, silent holder flips, future leaks, invalid endpoints, or raw reread attempts.
- **Held-Out Accuracy Gate:** Required answer accuracy >= 90% (Achieved: 82.69%).
- **Exact Block Count Gate:** >= 90% exact count cases (Achieved: 78.6%).
- **Superiority Gate:** C raw-hidden accuracy strictly exceeds Arm A by >5% and matches/exceeds Arm B.
- **Cost/Latency Ceiling Gate:** C median latency and token counts within 2.5x of B.

## 6. Pre-Registered Reproducibility Manifest

```json
{
  "run_id": "run_20260924_012403",
  "created_at_utc": "2026-09-24T01:29:30.046638+00:00",
  "git_head": "fc047c0d352dc87bdf514e2861a329adb5c1b2c3",
  "git_branch": "research/semantic-block-issue-19",
  "frozen_manifest_sha256": "b7a0f012b47f211c3afc255c17b6170f7aa69093c243af65ec8fad9ab8fa6997",
  "source_hashes": {
    "contracts": "8e3d41c3a01465dc7eb59eb6da2b4030125b1905381e25ef8353df9987570846",
    "base": "5955fa84d1b3d29a918c201399461eecbfdd8c90e3663b234d441175349c0d9c",
    "arm_a": "ec095edcbd75f1f30a93075bb6c7e3fdf612839e6f78a176e94bc7a9fb0dd2d0",
    "arm_b": "ed632d7f421b6c86f0e244d6572b132485ed2da504dd36df21001a9dcdb9900e",
    "arm_c": "5522e7260149768815ce78975ca702b726907a32540807610c2dfdda73270438",
    "arm_d": "a8e3fb4b729916cc1da55f5bae3981d5cb2c6ccffa99638c20265f2d6b42fae9",
    "consumer": "8ea59136b1d3be95aecb803c0413a52a3dbbc95a330c4150984a636b455e4b94",
    "alignment": "abd10db2906449f62ac0c2bed1e67cce957662d393dc487b2fe823391445bbca",
    "metrics": "b7e9bb570e475ee79ba7937c3a3f514c7ed503f6c2ca5a0bd225294ee6aa9ded",
    "llm_client": "79a041e533221116c148fadc7f5db80160dbbd1bbb743f49cac706f3de66bce4"
  },
  "model_provider": "Google Generative AI",
  "model_name": "gemini-3.1-flash-lite",
  "embedding_model": "gemini-embedding-001",
  "temperature": 0.0,
  "seed": 42,
  "budget": {
    "max_context_evidence_records": 4,
    "max_context_tokens": 1024,
    "max_input_tokens_per_request": 8192,
    "max_output_tokens_per_request": 2048,
    "semantic_retry_policy": "NO_SEMANTIC_RETRY"
  },
  "arms": {
    "A": "V1 reference memory stream compiler baseline",
    "B": "One-pass structured LLM proposal + deterministic validation",
    "C": "Recommended two-pass (internal proposal + validation + typed linker)",
    "D": "Full-frame internal representation projected to public block shape"
  }
}
```
