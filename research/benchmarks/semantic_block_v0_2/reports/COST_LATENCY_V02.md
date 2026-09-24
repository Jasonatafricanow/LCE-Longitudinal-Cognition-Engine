# SemanticBlock v0.2 Cost & Latency Performance Report

**Date:** 2026-09-24  
**Benchmark:** SemanticBlock v0.2 Shared-Input Evaluation (24 cases / 26 cutoffs)  
**Evaluated Arms:** Arm B (One-pass), Arm C (Two-pass), Route E (One-pass + Gates + Selective Linker), Paired E Ablation (No Linker)  
**Model Family:** `gemini-3.1-flash-lite` (Seed: 42, Temperature: 0.0)  
**Embedding Model:** `gemini-embedding-001`

---

## 1. Executive Cost & Latency Summary

Route E was designed to resolve the excessive computational cost and latency overhead of Arm C's unconditional two-pass architecture while avoiding Arm B's structural relation defects.

| Performance Dimension | Arm B (One-Pass) | Arm C (Two-Pass) | Route E (Selective Linker) | E (No-Linker Ablation) | Route E Delta vs. Arm C |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Total LLM Invocations** | 26 | 46 | 28 | 26 | **-18 calls (-39.1%)** |
| **Linker Invocations** | 0 | 20 (76.9%) | 2 (7.7%) | 0 | **-18 calls (-90.0%)** |
| **Total Tokens Consumed** | 54,553 | 68,418 | 57,528 | 54,553 | **-10,890 tokens (-15.9%)** |
| **Prompt Tokens** | 39,212 | 53,654 | 41,619 | 39,212 | **-12,035 tokens (-22.4%)** |
| **Completion Tokens** | 15,341 | 14,764 | 15,909 | 15,341 | +1,145 tokens (+7.8%) |
| **Tokens per Cutoff** | 2,098 | 2,631 | 2,213 | 2,098 | **-418 tokens / cutoff** |
| **Median Latency (ms)** | 16,373 | 111,548 | 16,637 | 16,373 | **-94,911 ms (-85.1%)** |
| **P95 Latency (ms)** | 50,332 | 909,034 | 71,479 | 50,332 | **-837,555 ms (-92.1%)** |

---

## 2. Token Consumption Profile

```
Total Tokens Consumed Across 26 Cutoff Evaluations:
Arm B           [54,553 tokens] ========================
Arm C           [68,418 tokens] ==============================
Route E         [57,528 tokens] =========================  (-15.9% vs C)
E (no linker)   [54,553 tokens] ========================  (identical to B)
```

### Detailed Token Breakdown:
1. **First-Pass Proposal Cost:**  
   Because Route E shares the exact first-pass prompt, schema, seed, and temperature with Arm B, its first-pass token consumption is byte-identical:
   - Prompt Tokens: 39,212
   - Completion Tokens: 15,341
   - Total First-Pass Tokens: 54,553
2. **Linker Stage Overhead:**  
   - In Arm C, the linker was invoked for every case with $\ge 2$ admitted blocks, resulting in **20 linker invocations** consuming **13,865 additional tokens** (14,442 prompt tokens, -577 completion offset due to different proposal formatting).
   - In Route E, deterministic candidate screening filtered out 92.3% of cases. The linker was invoked only twice (`V2-005` and `V2-006`), consuming only **2,975 additional tokens** (2,407 prompt, 568 completion).
   - **Net Token Savings:** Route E saved **10,890 tokens** compared to Arm C while retaining causal edge recovery in F8.

---

## 3. LLM Call Distribution & Linker Invocation Efficiency

| Execution Route | Pass 1 Proposals | Pass 2 Linker Calls | Total Model Calls | Average Calls / Case | Linker Trigger Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Arm B** | 26 | 0 | 26 | 1.00 | 0.0% |
| **Arm C** | 26 | 20 | 46 | 1.77 | 76.9% |
| **Route E** | 26 | 2 | 28 | 1.08 | **7.7%** |
| **E (no linker)** | 26 | 0 | 26 | 1.00 | 0.0% |

### Linker Activation Analysis:
- In Route E, candidate discovery inspects visible evidence spans and entity registries before requesting LLM linking.
- For 24 of the 26 cases, no plausible cross-block causal or temporal candidate pairs were detected, completely bypassing the second LLM pass.
- Only in `V2-005` (4 screened pairs) and `V2-006` (5 screened pairs) was the linker invoked. Both invocations respected the 8-candidate cap and produced zero dangling endpoints.

---

## 4. Latency Distribution & Network Resilience

### Latency Percentiles (Milliseconds):
| Metric | Arm B | Arm C | Route E | E (no linker) |
| :--- | :---: | :---: | :---: | :---: |
| **Min Latency** | 4,756 ms | 8,990 ms | 4,756 ms | 4,756 ms |
| **Median Latency** | 16,373 ms | 111,548 ms | 16,637 ms | 16,373 ms |
| **Mean Latency** | 20,490 ms | 204,360 ms | 23,285 ms | 20,490 ms |
| **P90 Latency** | 40,891 ms | 612,400 ms | 47,820 ms | 40,891 ms |
| **P95 Latency** | 50,332 ms | 909,034 ms | 71,479 ms | 50,332 ms |
| **Max Latency** | 62,110 ms | 1,245,670 ms | 82,340 ms | 62,110 ms |

### Network Backoff & Caching Accounting:
1. **Live Proxy Instability:** During live evaluation, transient connection drops (`SSL: UNEXPECTED_EOF_WHILE_READING`) were encountered on Windows when routing through `127.0.0.1:7890`.  
2. **Expanded Retry Architecture:** The runner's client was hardened with a 35-attempt exponential backoff schedule (`delay = min(30.0, 5.0 * 1.15^attempt)`). This allowed live calls to withstand multi-minute network interruptions without aborting the benchmark run.
3. **Deterministic Disk Caching:** Every successful response was sealed in `.cache/v0_2` by content hash. On re-execution or ablation evaluation, cache hits resolve in < 1ms, guaranteeing 100% reproducible execution at zero marginal API cost.

---

## 5. Cost-Benefit Verdict

1. **Efficiency Hypothesis Validated:** Route E achieved a **90% reduction in linker invocations** and a **15.9% reduction in token consumption** relative to Arm C.
2. **Latency Elimination:** By avoiding redundant second-pass calls on 92.3% of cases, Route E eliminated the severe latency penalty of Arm C, maintaining median response times within 1.6% of single-pass Arm B (16.6s vs. 16.4s).
3. **Targeted Precision:** In the single positive causal test case (`V2-005`), the selective linker successfully activated, recovering the complete causal chain without polluting the other 24 cases with unnecessary model calls.
