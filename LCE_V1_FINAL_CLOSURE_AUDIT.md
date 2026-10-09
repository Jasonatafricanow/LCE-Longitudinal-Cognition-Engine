# LCE V1 Z3 Final Sign-off Audit

**REJECT — LCE V1 PRODUCT CLOSURE BLOCKED**

Audited HEAD: `b89d6a333bc0f806c8964dbd09381d21868d8b10`  
Worktree: `C:\projects\w\lce-v1-close`  
Branch: `w/lce-v1-close`  
Permanent test authority: `69fe0bc05bbc232b371f123628a8054340b63f70`  
Known-broken production base: `ecf41377224881b51e242222c185acf191b324da`  
Date: 2026-09-09

Actual HEAD matches Q1. Initial status contained only the pre-existing untracked Q1, Z0, Z1 and Z2 audit reports. A fresh GPT-6 (`gpt-6-astra`, high reasoning) reviewer independently inspected test history and reproduced the defect below; the coordinating auditor reran it on a separate fresh database. No production code was modified.

## Newly reproduced blocking defect: B4

- **File/line:** `src/lce/runtime.py:284–287` reorders selected blocks by occurrence end time; `src/lce/runtime.py:321–329` hashes their sequence without canonicalizing its order.
- **Reproduction:** Using production `LceRuntime`, default interpreter and default conservative promotion policy, process four distinct related sensor observations with `StructureConfig(k_values=(2,), min_similarity=0.9)`. Observe one OPEN worktree, one support identity and no Baseline. Close/reopen. Supply a pure recap of the **oldest** selected block, with no new information. All block contents and exact structure IDs, centers, memberships and k values remain unchanged. Immutable history grows from four to five states. Selected order changes from `[4,3,2,1]` to `[1,4,3,2]`; the order-sensitive fingerprint adds a second support identity. The worktree becomes MERGED and an accepted Baseline is created. Both reviewers reproduced this independently.
- **Runtime consequence:** A recap-only recency/provenance change still satisfies the default two-support promotion policy. Removing state IDs from the fingerprint did not remove this alternative inflation path.
- **Violated invariant:** Provenance identity and recency are distinct from qualifying cognition-support identity. Pure recap without semantic or structural change must preserve OPEN/support=1.
- **Minimal repair:** Canonicalize the block ordering used solely for qualifying support fingerprints independently of recency and selected-provenance ordering. Preserve exact immutable selected support for provenance.
- **Required permanent regression:** Parameterize pure recaps over oldest, middle and newest selected blocks, across restart and successive recaps. Assert unchanged semantic content/effective structure yields the same support identity, OPEN/1 and no Baseline. Then assert genuinely relevant semantic change advances to MERGED/2. The current fixture repeatedly recaps only the newest block, so its selected order stays unchanged and the defect is missed.

Independent runnable probe: `C:/Users/Temp/AppData/Local/Temp/lce-z3-review-f70ba2edf13d4cc586c15735d3eeed8c/b4_spot.py`. The probe asserts identical contents and structures and the actual erroneous OPEN/1 → MERGED/2 transition. Its successful execution demonstrates the defect, not product acceptance.

## Final closure table

| Item | Result |
| -- | -- |
| Test integrity | FAIL |
| B1 | FIXED |
| B2 | FIXED |
| B3 | FIXED |
| B4 | BLOCKED |
| B5 | FIXED |
| B6 | FIXED |
| B7 | FIXED |
| B8 | FIXED |
| N2 | FIXED |
| Recovery matrix | 30/30 |
| Full tests | PASS |
| Clean install | PASS |
| Architecture drift | NONE |

The test-integrity sign-off fails the requested completeness condition, not historical authenticity: RED→GREEN ancestry is real, but the recap oracle misses the above permutation, and the permanent durable signature omits the newly significant `processing_input_id` used to find committed recovery effects. The independent B7 probe included that field and found no mismatch. This omission is not asserted as a second runtime blocker. Only B4 blocks the product verdict here.

## Verification evidence

### Permanent-test history

The independent reviewer exported exact pre-repair `f7ce087`; its production source matches broken `ecf4137`. Fresh historical results:

- Closure invariants: **4 failed, 6 passed**.
- Corrected recovery suite: **12 failed, 20 passed**: **10/30 matrix cases RED**, plus two named recovery tests RED.
- Tests at `69fe0bc`, and the oracle correction at `f7ce087`, precede production fixes `eff90b6` and `d22b330`.
- `git diff f7ce087..HEAD -- tests` is empty, independently verified by the coordinating auditor. No post-RED weakening, skip/xfail, fixture-ID production branch or promotion-threshold workaround was found.
- The matrix actually compares normalized durable state in each of 30 parameterized cases. Only `create-before` is exempt from interpreter-call equality; durable state equality remains mandatory there.

### Current command gates

Interpreter: `C:\Python314\python.exe`, Python **3.14.5**, pytest **9.0.3**.

| Command | Actual result |
| -- | -- |
| `python -m pytest tests/test_v1_recovery_fault_matrix.py -q` | 32 passed in 48.03s; 30 matrix cases plus two named tests |
| `python -m pytest tests/test_v1_closure_invariants.py -q` | 10 passed in 8.71s |
| `python -m pytest tests/test_z0_blocker_repairs.py tests/test_z1_blocker_repairs.py tests/test_runtime_e2e.py -q` | 21 passed in 17.37s |
| `python -m pytest -q` | 135 passed in 82.69s |
| `python -m pytest tests/test_runtime_e2e.py -q` | 2 passed in 2.00s |
| `python -m mypy src/lce` | Success, 32 source files |
| `python -m ruff check src tests` | All checks passed |
| `git diff --check 69fe0bc..HEAD` | Passed |

Retained controls remain green; no new reproduction reopened B1/B2/B3/B5/B6/B8/N2. The passing current commands match Q1 evidence but do not override the new B4 reproduction.

### Independent B7 spot checks

A newly authored deterministic interpreter consumes only the supplied bounded package and changes its result when previous accepted cognition is present. Six independent fault/restart/replay cases pass:

| Injection | Interpreter calls on retry | Final state |
| -- | -- | -- |
| create-before | 1, allowed before durable effect | Equivalent MERGED/2 |
| create-after | 0 | Equivalent MERGED/2 |
| record_support-after | 0 | Equivalent MERGED/2 |
| set_status-after | 0 | Equivalent MERGED/2 |
| promotion-evaluated-after | 0 | Equivalent MERGED/2 |
| complete-before | 0 | Equivalent MERGED/2 |

The independent comparison includes all dataclass fields for worktrees, Baselines, selected immutable states, vectors, snapshots, candidates and accepted views, plus support identities, pipeline progress and checkpoint. Only random ID labels and created/updated wall-clock fields are normalized. It includes `processing_input_id`, model trace and normalized HEAD/history links. No extra OPEN worktree, support or revision appears.

### Clean exact-HEAD install

Exported `b89d6a333bc0f806c8964dbd09381d21868d8b10` with `git archive`, installed the source in a fresh venv using ordinary pip/PEP 517, and ran outside the repository with `python -I`. Import resolves to the venv's `site-packages/lce/__init__.py`; installed distributions are only `lce-core` and `pip`, with no MR requirement.

Standalone processing with explicit `ConservativePromotionPolicy(min_blocks=2, min_structures=2, min_support_cycles=2)` produces one accepted Understanding. Batch and nearline with restart after every input match. Wheel SHA-256: `9d82ef59b0b725113972d0df6bbe9512649a6b6ca3f6dc0fcb400b3b0f620e84`.

Parent execution artifacts are under `C:/Users/Temp/AppData/Local/Temp/lce-z3-audit-7c0211ec34374307a36b2b41fdb3cfc7/`, including `independent_b7.py`, `clean_smoke.py` and the exact source export.

### Repair scope

The repair touches runtime, the existing worktree store and promotion. No canonical Structure authority, second truth judge, duplicate accepted store, heavyweight workflow/event-sourcing system, MR dependency, Body/current-turn reasoning, recursive cognition or derived-cognition-to-Evidence path was found. No historical research questions were reopened. Model quality, thresholds and performance are not rejection grounds.

This report is the sole repository write in Z3. No implementation/test changes, merge, tag or research-timeline write was performed. The remaining work is the B4 fingerprint-order repair and permanent regression above; no V2 or architectural redesign is requested.
