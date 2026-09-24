# Issue #19 Cost, Latency & Storage Distribution Report

Empirical measurement of tokens, model calls, execution time, and storage footprints across all four arms.

## 1. Latency & Token Profiles (Held-Out Cases)

| Arm | Median Latency (ms) | p95 Latency (ms) | Input Tokens | Output Tokens | Total Tokens | Model Calls / Case |
| --- | --- | --- | --- | --- | --- | --- |
| **A** | 0.5 | 1.7 | 0* | 0* | 0 | 0 |
| **B** | 5577.3 | 12628.8 | 20241* | 8675* | 28916 | 1 |
| **C** | 8999.9 | 15845.3 | 24733* | 10600* | 35333 | 1.8 |
| **D** | 5833.0 | 19512.8 | 15014* | 6435* | 21449 | 1 |

_*Input/output token breakdown estimated from logged aggregate usage._

## 2. Resource Budget Comparison (Arm C vs. Arm B)

- **Protocol Constraint:** C median tokens and p95 latency must be <= 2.5x B under the same model/machine.
- **Token Ratio (C / B):** `1.22x` (Threshold: `<= 2.50x`) -> **`PASS`**
- **p95 Latency Ratio (C / B):** `1.25x` (Threshold: `<= 2.50x`) -> **`PASS`**

## 3. Storage Footprint Comparison

- **Arm A (V1):** Baseline storage (~250 bytes per block, no relation graph).
- **Arm B (One-pass):** Structured block JSON with typed fields and relations (~1.2 KB per block).
- **Arm C (Recommended):** Normalized public block JSON (~1.1 KB per block; internal proposal objects discarded).
- **Arm D (Full Frame):** Rich frame projected to public block JSON (~1.1 KB per block public, 3.8 KB internal).
