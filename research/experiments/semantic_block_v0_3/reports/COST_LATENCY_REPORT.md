# SemanticBlock v0.3 — Cost & Latency Accounting Report

**Date:** 2026-09-25
**Model:** gemini-2.5-flash (Seed 42, Temperature 0.0)
**Embedding Model:** gemini-embedding-001 (Dimension 3072)

---

## 1. Overall Accounting Summary

- **Total API Calls:** 780
- **Total Prompt Tokens:** 423,647
- **Total Completion Tokens:** 134,811
- **Total Tokens Consumed:** 558,458
- **Total Execution Latency:** 3210.42 seconds

## 2. Resource Discipline

1. **Deterministic Disk Caching:** All raw JSON responses and text embeddings cached by SHA256 key.
2. **Zero-Token P0 & P4 Arms:** Raw passthrough and legacy V1 reference require zero LLM generation calls.
3. **Budget Guardrails:** No unbounded generation; all outputs constrained by responseMimeType='application/json'.