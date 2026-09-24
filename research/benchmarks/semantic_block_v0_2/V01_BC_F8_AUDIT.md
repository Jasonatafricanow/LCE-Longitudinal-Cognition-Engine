# v0.1 B/C differential and F8 report audit

Status: **read-only forensic audit**, based on local `run_20260924_012403` results and all 66 cached C Pass-1 proposals. Source commit recorded by that run: `fc047c0d352dc87bdf514e2861a329adb5c1b2c3`; frozen v0.1 manifest SHA-256: `b7a0f012b47f211c3afc255c17b6170f7aa69093c243af65ec8fad9ab8fa6997`. Reproduce the differential with `python -m research.benchmarks.semantic_block_v0_2.analyze_v01` from the repo root. The generated [`v01_bc_audit.json`](v01_bc_audit.json) contains all case/cutoff differences, focused raw B/C traces for the disputed families, C proposal cache keys, and a strict F8 remapping. This audit does not edit v0.1 artifacts or run a model.

## Answer: where did C normalization damage correct semantics?

**No observed family.** The source labeled “Pass 1 Normalization” in `arm_c_recom.py` admits/rejects spans and cutoff visibility, maps registry participant values, computes support count, and copies the proposal's semantic fields into a public block. Across all **66 case/cutoff executions**, cached C proposals were found for all 66; **zero proposal units were dropped** and **zero `canonical_content`/predicate/kind/roles/holder/utterer/attribution/polarity/modality/hedge/time/entity-status/uncertainty fields changed** between C Pass 1 and final C blocks. Thus the measured B/C gap cannot be assigned to a semantic rewrite by the deterministic normalizer. This finding is specific to the frozen run; it does not prove the normalizer safe on future inputs.

| Source of B advantage | Observed evidence | Attribution |
| --- | --- | --- |
| B17-C / B17-P / B17-N | B emitted six event blocks per case; C Pass 1 already proposed four compound blocks, and final C kept exactly those four. B scored +34/+30/+32 field instances. | C **proposal granularity**, amplified by alignment/field denominators; no normalization mutation. |
| B07-N | Gold has two visible states, including a prior context state. B emitted two; C Pass 1 emitted only the new `She restarted it` state and final C kept it. B scored +12 fields at this cutoff. | C **proposal/context output scope** and unresolved target; no normalization mutation. |
| B08-P | B had the gold `SAME_ENTITY` link; C had the two blocks but its selective second pass missed the link. | **Linker recall** loss, not normalization. |
| B11-N | C Pass 1 split one approval account into two blocks. Both `B11-N_s1` and `B11-N_s2` survived; the linker added `CAUSE s1→s2`. | Proposal over-split plus unsupported linker edge. The report's “s2 was not admitted / dangling endpoint” explanation is contradicted by the stored prediction. |

Held-out field totals are **B 342/364 (93.96%)** versus **C 301/364 (82.69%)**, a 41-instance gap. B17-N alone accounts for **32**; B07-N adds **12**; all other held-out cases net **3 in C's favor**. On development, B17-C/P account for **64** of B's net 23-instance advantage; without B17, C leads B by 41 instances. This is a concentration of errors, not broad evidence that C normalization corrupts meaning. B still had a held-out holder flip in B11-N; its aggregate advantage does not pass the safety gate.

The v0.1 annotation boundary itself needs adjudication: B02's single causal compound is gold-labeled **one** account, while B17-C/P's single source sentences such as `X failed, causing Y to stop.` are gold-labeled as **separate** event blocks. C's Pass-1 prompt explicitly teaches the B02 one-compound rule. The B17 mismatch could be a route failure, a gold inconsistency, or an underspecified granularity exception. The single-author v0.1 gold cannot settle that question. v0.2 must ask independent annotators to decide boundaries without seeing these predictions or old gold.

## F8: the reported PASS and 33.3%→100% comparison are unsupported

The v0.1 F8 probe derives both its seed and relevant-target set from **C's predicted IDs/content**. It selects `_s4` as the “X” seed even when C's four-block output assigns `_s4` to `Y stopped, causing Z to stall`. It derives targets from available predicted `_s4/_s5/_s6` IDs, so missing gold states shrink the denominator. The vector arm returns top 3, while the graph arm **appends** relation neighbors to those 3, allowing a larger candidate budget. `pass_gate` checks set inclusion, not the two gold CAUSE edges. The negative control also ignores a false causal neighbor already present in vector candidates. `render_benchmark_report()` prints “YES” for the negative variant by construction. Consequently the report's F8 PASS is not a gold-grounded path result, and its retrieval gain is not a fixed-budget comparison.

A strict remap of C's predictions to the frozen B17 gold gives:

| Fixture | Missing gold states after alignment | Missing required gold CAUSE edge(s) | Predicted `_s4` maps to gold | Gold-grounded F8 positive path |
| --- | --- | --- | --- | --- |
| B17-C | `s3`, `s4` | `s4→s5` | `s6` | **FAIL** |
| B17-P | `s1`, `s6` | `s5→s6` | `s5` | **FAIL** |
| B17-N | `s3`, `s6` | No positive CAUSE expected | `s5` | Negative cause absent, but incomplete block coverage |

This does **not** establish that graph links have no value. It establishes that the reported F8 probe did not measure the stated gold path or a fair same-`k` retrieval comparison. The v0.1 score's `invalid_relation_endpoint` flag also conflates an endpoint missing from **gold alignment** with an endpoint missing from the admitted prediction. The C B11-N relation endpoints both exist in its prediction; that error should be classified as over-split/unmatched account and unsupported relation, not runtime dangling reference.

## Additional measurement limits to repair in v0.2

- `_canonical_meaning_entailed()` accepts roughly 65% lexical overlap; this is not an entailment reviewer. `_match_participants()` ignores role labels and accepts substring value matches. The 93.96%/82.69% figures are **mechanical scorer outputs**, not independently verified semantic accuracy.
- `align_states()` uses greedy span-overlap matching rather than a globally optimal assignment; log alternative mappings and adjudicate contested boundaries.
- `BenchmarkRunner` loads gold and instantiates `RawHiddenConsumer` in the same process. Its access-log count does not establish process-level isolation from raw/gold files.
- `llm_client.py` retries transient API errors despite the run manifest saying `NO_SEMANTIC_RETRY`; replay hits disk cache, so “100% deterministic replay” is a cache equivalence check, not an independent model determinism measurement.

Preserve the v0.1 report as historical evidence. Use this audit as a correction note and design input; do not rescore or relabel the frozen v0.1 held-out set in place.
