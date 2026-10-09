# LCE V1 Z1 Final Blocker Re-Audit

**REJECT — LCE V1 PRODUCT CLOSURE BLOCKED**

Audited HEAD: `9ea947ab9f495b256644b2d022907678e747ea1c`  
Repair implementation HEAD: `a2507888d5615868510682f0e799f2a1faf6f014`  
Rejected base: `16b014e1a1d3b4a225d4049d7df9615c93921dc4`  
Worktree: `C:\projects\w\lce-v1-close`, branch `w/lce-v1-close`  
Audit date: 2026-09-09

## Remaining blockers

### B1 — REGRESSION

- **File/line:** `src/lce/cognition/promotion.py:155–160`; `src/lce/cognition/block_adapter.py:17–20`; correction caller `src/lce/runtime.py:230–233`.
- **Independent reproduction:** With the unchanged default two-support-cycle policy, process four related points and three genuinely informative recaps of block 3. Accepted revision 2 has sources e1–e7. Invalidate e7: the old Understanding is immediately unavailable and a corrected candidate using block 3's earlier valid state enters OPEN with one support. Add genuinely relevant e8 to block 2. The second support attempts normal promotion but raises `UnauthorizedSourceError` for block 3. The interpreter's corrected snapshot contains its valid pre-e7 state; promotion fetches its latest state containing invalid e7 and excludes it. Both reviewers reproduced this. The original loss-of-one-side negative control now correctly creates no copied/suffixed replacement and preserves an unrelated accepted Understanding.
- **Runtime consequence:** A genuinely supported localized correction cannot complete through normal promotion. Additionally, the source/state mismatch described in B5 can leave accepted cognition served after its actual selected source is invalidated.
- **Minimal repair:** Carry the authorized immutable block states from interpretation through worktree promotion into the existing Core adapter. Validate those exact states against Memory validity instead of replacing them with current block state. Preserve the ordinary promotion policy.
- **Required regression:** Run the default-policy e1–e8 sequence above across restart; require old cognition unavailable, corrected OPEN support followed by one correct accepted revision and ancestry, no exception, and unaffected unrelated cognition. Retain the no-supported-replacement negative control.

### B2 — REGRESSION

- **File/line:** `src/lce/cognition/block_adapter.py:17`; `src/lce/cognition/promotion.py:109–117,155–159`; `src/lce/read_api.py:45–53`.
- **Independent reproduction:** Immutable t1 snapshots themselves now survive later CONTINUE/RECAP and deletion followed by chronological rebuild exactly, including content, sources, occurred range, vectors, descriptors and candidate closure. However, accepting/replaying historical interpretation still resolves current blocks at promotion. In the completed-input replay probe, revision 2 contains findings 5/6/7; replaying older completed R1–R5 creates revision 3 whose interpretation contains only finding 5 but whose accepted provenance contains R1–R7. Separately, an interpreter legally selecting only block 4 yields `supporting_memory_ids=(block4,)` alongside state IDs for all four blocks; accepted reads expand block 4 through state 1 and return e1 instead of e4.
- **Runtime consequence:** Historical snapshot reconstruction is repaired, but the interpretation-to-accepted historical provenance boundary is not. A cutoff-bound interpretation can acquire future or unrelated evidence when promoted or read.
- **Minimal repair:** Persist and consume an explicitly aligned selection of authorized block IDs and immutable state IDs throughout the existing candidate/Baseline path. Validate state ownership, cardinality and ordering; do not substitute live state. Apply the completed-replay repair in B7.
- **Required regression:** Interpret t1, append t2 CONTINUE/RECAP, then recover/promote t1 and assert exact t1 accepted provenance with no t2 source. Exercise subset and reordered interpreter selections, restart, and snapshot deletion/rebuild; require correct state-to-block ownership throughout.

### B5 — REGRESSION

- **File/line:** `src/lce/cognition/promotion.py:109–117`; `src/lce/read_api.py:45–53`; `src/lce/runtime.py:149–160`.
- **Independent reproduction:** A recording interpreter receives the real authorized immutable package and returns only its last authorized block as support. Promotion retains that selected block ID but records state IDs for every fetched block. The read API positionally zips the two unequal lists with `strict=False`. In a four-block fixture, selected block 4 is resolved through state 1: query returns e1 although the selected source is e4. Invalidating e4 leaves the same Baseline served. Both reviewers executed the probe. The fixture uses an explicitly configured one-cycle policy to isolate this mapping defect; it does not claim the default policy automatically merges one candidate.
- **Runtime consequence:** A valid provider response corrupts accepted source attribution and current-valid filtering. The interpreter seam is now genuine and used, but its supported subset contract is not preserved downstream. This shares the provenance root with B2, rather than indicating an absent or unused interpreter.
- **Minimal repair:** Build the accepted state selection from the interpreter's selected block IDs in the same order, using the exact authorized package states. Fail closed on absent/mismatched ownership. Retain that selection through persistence and reads.
- **Required regression:** A recording interpreter selects a strict subset and then a reordered subset; assert exact corresponding state IDs/source refs before and after restart. Invalidating any actually selected source must suppress that Understanding; invalidating an unselected source must not invalidate it merely through an erroneous mapping.

### B7 — NOT FIXED

- **File/line:** `src/lce/runtime.py:95–116,152–153`; `src/lce/cognition/promotion.py:159–160`.
- **Independent reproduction:** (1) Inject a failure immediately after the real Baseline `save_revision` commit, or immediately before worktree `set_status`. Close, reopen and replay. The accepted Baseline exists, but its worktree remains OPEN with two supports, whereas the fault-free reference is MERGED. The equal-content return at runtime lines 152–153 prevents reconciliation. (2) Process R1–R7: four related points followed by three new-information recaps. Default policy accepts revision 2 containing findings 5/6/7. Close/reopen and replay already-complete R1–R5. Runtime reinterprets the historical snapshots and accepts revision 3 containing only finding 5. The fresh reviewer independently reran this second reproduction. A shorter completed-corpus replay also creates an extra stale OPEN worktree.
- **Runtime consequence:** Durable completion is not respected for downstream mutation. Recovery can leave contradictory accepted/worktree states; ordinary idempotent replay can create a duplicate semantic revision and roll accepted cognition backward. The stage check currently gates vector work only, and later stages overwrite the complete marker.
- **Minimal repair:** Make completed input replay non-mutating for cognition while returning/reconstructing its derived result as needed. Resume incomplete stages without repeating committed cognition effects. Reconcile an already committed Baseline with its worktree before the equal-content shortcut, using existing identities/stores; no new workflow framework is needed.
- **Required regression:** Inject both post-Baseline/pre-status interruptions and compare the full recovered state with the reference, including MERGED status and Baseline linkage. Replay every completed prefix and the complete corpus after newer accepted revisions, across restart; require unchanged HEAD/content/ancestry, no new OPEN candidates, no extra support and no additional revision.

## B1–B8 disposition

| ID | Result | Bounded conclusion |
| --- | --- | --- |
| B1 | REGRESSION | Copied correction and relaxed policy removed; supported correction still fails on live-state resolution, and selected-source invalidation can leak through B5. |
| B2 | REGRESSION | Immutable snapshot reconstruction passes; accepted state/source fidelity fails at promotion/read. |
| B3 | FIXED | Effective-member alias deduplication passes negative and positive controls. |
| B4 | FIXED | Candidate-relevant support fingerprints resist the specified OPEN-worktree inflation controls. Completed historical replay defects are accounted for under B7. |
| B5 | REGRESSION | Real bounded interpreter seam works, but legal subset selection corrupts accepted source/state mapping. |
| B6 | FIXED | Failed-input ordering barrier survives restart, including equal timestamp ordering. |
| B7 | NOT FIXED | Post-commit reconciliation and completed-input replay remain incorrect. |
| B8 | FIXED | Independently implemented backend runs the actual pipeline and invalidation through documented ports. |

N2: **FIXED**. Identical structures in a later snapshot produce no newly linked structures.

## Independent verification

The Z0 report, repair report, repair diff and affected original paths were inspected against the original frozen A1–A5 requirements. Repair declarations were treated as evidence, not authority. A fresh `gpt-6-astra` reviewer with high reasoning, separate from the repair agent, performed bounded source inspection and independently authored controls; the coordinating auditor reran those controls and independently authored the recovery/backend probes. No production implementation was modified.

### Requested commands

Interpreter: `C:\Python314\python.exe`, Python **3.14.5**. Observed pytest **9.0.3**, Ruff **0.16.5**.

| Command | Actual result |
| --- | --- |
| `python -m pytest -q` | 85 passed in 12.69s |
| `python -m pytest tests/test_runtime_e2e.py -q` | 2 passed in 1.88s |
| `python -m mypy src/lce` | Success, 32 source files |
| `python -m ruff check src tests` | All checks passed |
| `git diff --check 16b014e..9ea947a` | Passed |

These green results reproduce the implementer's command evidence; they do not cover the failing independent cases above.

### Clean exact-HEAD installation

Exported `9ea947ab9f495b256644b2d022907678e747ea1c` with `git archive`, created a new virtual environment, and installed the exported source using ordinary pip/PEP 517 build isolation. Installation and import succeeded without MR. The installed environment contained `lce-core` and `pip`; import resolved to the new environment's `site-packages/lce/__init__.py`.

Executed an independently authored standalone script with the venv interpreter and `-I`. A nonempty deterministic corpus produced one accepted Understanding. Batch and one-item-at-a-time nearline processing with close/reopen after every item produced equivalent accepted outcomes. Built wheel SHA-256: `b27b721fb9cfb448d1a56946789812aa67980b79e3ceeda8bddc0093aaf6294a`.

### Recovery fault matrix

An independently authored deterministic five-input corpus creates real higher-order candidates, worktree support and accepted cognition under the default policy. After each injected fault, the runtime was closed, reopened, and the interrupted input plus remaining ordered corpus replayed. Comparison included block identities and immutable state/provenance, vectors, snapshots/descriptors, higher-order candidates, worktree content/support/status/linkage, accepted content and normalized Baseline revision ancestry.

Thirty before/after injection cases covered:

- Block state write, checkpoint write and compilation transaction completion.
- Vector projection, snapshot creation and snapshot persistence.
- Worktree creation and support recording.
- Baseline revision commit and worktree status persistence.
- Each durable progress marker: vector-ready, snapshot/discovery-evaluated, worktree-support-evaluated, promotion-evaluated and complete.

**28/30 matched the fault-free reference.** The two failures were post-Baseline-commit and pre-worktree-status persistence, described in B7. This matrix does not imply recovery correctness for all possible executions.

Three additional internal partial-write tests passed: failure after the second state write in a split transaction; failure after writing the compiled stage within that transaction; and an embedder failure after vector deletion and one insertion. Close/reopen/retry restored the expected blocks/vectors/completion. Completed-corpus/prefix replay was tested separately and failed as documented above.

### Other independently authored controls

| Area | Observed result |
| --- | --- |
| Original B1 loss of support | No copied/suffixed conclusion, no unsupported replacement revision, unrelated accepted cognition preserved. The original two-side setup was seeded through the existing promoter because B3 now correctly prevents its alias-generated higher-order candidate. |
| Historical reconstruction | t1 block content, refs, occurred range, vectors, snapshot descriptors and candidate source closure unchanged after later CONTINUE/RECAP; deleting snapshots and rebuilding chronologically reproduces them. Previously accepted historical refs in the all-source case remain unchanged. |
| Higher-order alias negative | Two-point local structure observed through six center/k observations using k=1,2,4, plus unchanged repeated snapshots: zero higher-order candidates. |
| Higher-order positive | Distinct overlapping structures in a four-point k=2 fixture produce a bounded higher-order candidate; legitimate overlap retained. |
| OPEN support negatives | Initial, replay, restart, pure recap, duplicate source replay, orthogonal evidence, and new global snapshot/repeated observation counts remain `[1,1,1,1,1,1,1]`. |
| Genuine new support | Relevant new-information recap advances the count to two and MERGED under the same policy. |
| Interpreter seam | Recording interpreter receives authorized structures, immutable blocks and source closure; previous accepted cognition appears only as the explicitly supplied package field. No Memory search/ingestion/promotion capability is passed. Returned text reaches worktree. |
| Interpreter controls | UNKNOWN and REJECTED create no accepted cognition; forged support ID fails closed; equivalent normalized content creates no revision; changed content creates revision 2 with correct parent; reads invoke interpreter zero times; recording provider/model metadata retained truthfully. Subset provenance nevertheless fails as B5. |
| Failed-input barrier | E1 fails; equal-timestamp E2 is blocked before and after restart. E1 succeeds, then E2, then E3 at +1 microsecond. Calls are `E1,E1,E2,E3`; each successful input compiles once, replay makes no provider calls, final checkpoint is E3. |
| Alternate substrate | A new plain-object dictionary backend, neither subclassing ReferenceMemoryStore nor using its private methods or the shipped test double, implements documented composed ports. Actual injected LceRuntime pipeline produces vectors, snapshots, higher-order candidate, MERGED worktree and accepted read; invalidating a supporting source suppresses the old Baseline. Backend is deliberately ephemeral; durable restart was verified against default SQLite separately. |
| N2 | Identical structures at a later cutoff yield no newly linked structures. |

Reproduction scripts were created outside the repository, not added to production or its tests. Local audit artifacts are under `C:/Users/Temp/AppData/Local/Temp/lce-z1-audit-f4dcaa32539d43d2ad85664ad9da9ee2/`: `fault_matrix.py`, `fault_matrix.json`, `completed_replay.py`, `in_transaction_faults.py`, `backend_barrier.py`, and `clean_smoke.py`. Fresh-reviewer probes are `C:/Users/Temp/AppData/Local/Temp/lce-z1-fresh-review-probes.py`, `lce-z1-fresh-review-controls.py`, and `lce-z1-fresh-default-correction.py` in the same Temp directory. These temporary paths are execution evidence, not a durable package deliverable; the reproduction descriptions above specify the required regression cases.

## Architecture boundary and re-audit scope

No architecture drift was found in the bounded repair paths: immutable Semantic Block states are used for historical reconstruction; snapshot persistence remains derived; accepted cognition still uses existing Core/Baseline/HEAD storage. No new factual truth judge, canonical Structure authority, duplicate accepted store, Body/current-turn reasoning, MR code, recursive cognition loop, derived-cognition-to-Evidence path, or large workflow framework was found. The rejection concerns correctness of the frozen mechanics, not a demand for new architecture.

Deterministic embedding and rule-based semantic/interpretation providers remain reference implementations. Their semantic quality, thresholds and higher-order precision are non-blocking tuning limits. No conclusion here upgrades historical structure-to-structure experimental quality beyond PARTIALLY SUPPORTED.

After repair, re-audit only B1/B2/B5's shared immutable selected-state path and B7's recovery/completed-replay paths, with their regressions above. Repeat the requested command gates and clean exact-HEAD install; retain B3/B4/B6/B8/N2 controls as regression checks. No V2 redesign or new architecture work is requested.

This report is the sole repository write for Z1. The pre-existing untracked Z0 report is preserved. No merge, tag, production repair or research-timeline write was performed.
