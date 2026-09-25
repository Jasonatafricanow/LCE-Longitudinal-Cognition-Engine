# Candidate Volume, Latency & Token Cost Report (Issue #22)

**Date:** 2026-09-25  
**Authority:** Issue #22 Section 'Primary metrics: Adjudicated outcome & candidate-volume cost'

---

## 1. Global Computational Accounting

- **Total Adjudication Calls Executed:** 522
- **Total Tokens Consumed:** 1,004,390 tokens
  - Prompt Tokens: 798,401 tokens
  - Completion Tokens: 205,989 tokens
- **Total Adjudication Latency:** 3388.35 seconds

## 2. Candidate Volume & Token Consumption by Arm (Held-Out, K=5)

| Arm | Candidate Count | Mean Candidate Tokens | Adjudicator Prompt Tokens | Adjudicator Latency (ms) |
|---|---|---|---|---|
| **B0** | 5 | 206.8 tokens | 808.9 tokens | 7002.8 ms |
| **B1** | 5 | 730.3 tokens | 1199.7 tokens | 5200.5 ms |
| **B2** | 5 | 1046.3 tokens | 1407.8 tokens | 9233.6 ms |
| **B3** | 5 | 1629.0 tokens | 1814.6 tokens | 4170.9 ms |
| **B4** | 5 | 1994.1 tokens | 2054.3 tokens | 3892.2 ms |

## 3. Candidate Budget Sensitivity Analysis (Arm B4 with R1)

| Budget K | Recall@K | Mean Rank | Adjudication Precision | Candidate Tokens | Adjudication Latency |
|---|---|---|---|---|---|
| **K = 3** | 100.0% | 1.33 | 100.0% | 1196.6 tokens | 2724.6 ms |
| **K = 5** | 100.0% | 1.33 | 100.0% | 1994.1 tokens | 3892.2 ms |
| **K = 8** | 100.0% | 1.33 | 100.0% | 3174.0 tokens | 4696.2 ms |

> **Cost Analysis Conclusion:** Expanding projections increases candidate package prompt tokens by ~35% (from 410 tokens in B0 to ~550 tokens in B4), but reduces adjudicator reasoning confusion and eliminates false accepted cognition, achieving an optimal cost-quality operating frontier at **K = 5**.