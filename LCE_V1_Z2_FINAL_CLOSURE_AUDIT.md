# LCE V1 Z2 Final Product Closure Audit

**REJECT — LCE V1 PRODUCT CLOSURE BLOCKED**

## Exact audit identity

- Worktree: `C:\projects\w\lce-v1-close`
- Branch: `w/lce-v1-close`
- Actual audited HEAD: **`ecf41377224881b51e242222c185acf191b324da`**
- Previous rejected HEAD: `9ea947ab9f495b256644b2d022907678e747ea1c`
- Implementation commit: `12d1c6a97808ca81d6822fea4a2be97285c88012`
- Subsequent commit: `ecf4137 docs: record Z1 blocker repair`
- Reviewed range: `9ea947a..ecf4137`, including affected original call paths; 15 files, 864 insertions, 41 deletions.
- Initial status: only the pre-existing untracked Z0 and Z1 audit reports. No tracked/staged changes.
- Date: 2026-09-09.

The Z0 audit/repair reports, Z1 audit/repair reports, actual repair diff, affected production paths and both blocker-repair test files were read against the supplied frozen requirements. A fresh `gpt-6-astra` high-reasoning reviewer, separate from the repair agent and prior reviewers, independently probed selected support, historical promotion, invalidation and retained controls. The coordinating auditor independently reran those probes and performed recovery, ordering, replacement-backend, command and installation verification. Repair-report verdicts were not used as authority.

## Actual remaining blockers

### B4 — REGRESSION

- **File/line:** `src/lce/runtime.py:273–281`, especially the inclusion of `item.state_id` in the support fingerprint at line 277; support recording/promotion at lines 223–227.
- **Independent reproduction:** Process four related, distinct Semantic Blocks with `StructureConfig(k_values=(2,), min_similarity=0.9)` and the unchanged default conservative policy. The real higher-order worktree is OPEN with one support and no accepted Understanding. Close/reopen. Supply e5 as a pure recap of block 4, with no new information. Block content remains exactly `observation 4`; its immutable state changes from sources `(e4)` to `(e4,e5)`. The support count becomes two, the worktree becomes MERGED and one accepted Understanding appears. Both reviewers ran this reproduction. Separate controls show restart, completed replay, duplicate source, unrelated point, duplicate structure observation and global snapshot churn remain at OPEN/1; genuinely relevant new information correctly advances to MERGED/2.
- **Runtime consequence:** A provenance-only state version is treated as new qualifying cognition support. Mere repetition can satisfy the default promotion policy, contrary to the explicit pure-recap negative control. This is a repair-induced regression from the Z1 content-based support fingerprint, not threshold tuning.
- **Minimal repair:** Keep exact immutable state bindings for provenance, but deduplicate qualifying support by candidate-relevant semantic/structural change. A state-ID change caused only by recap provenance must not advance support. Preserve genuine relevant-change promotion.
- **Required regression:** Under the unchanged default policy, create OPEN/1, restart, and add one or multiple pure recaps with different evidence IDs. Assert unchanged qualifying support, no accepted revision and OPEN status despite updated audit provenance. Then add genuinely new relevant information and require the expected second support and promotion. Retain all other separate inflation controls.

### B7 — NOT FIXED

- **File/line:** `src/lce/runtime.py:98–120`, especially unconditional candidate evaluation at lines 114–115 for every incomplete stage; `src/lce/cognition/promotion.py:164–180` only reconciles OPEN worktrees. Monotonic marker storage is at `src/lce/reference_memory/sqlite.py:627–640`.
- **Independent reproduction:** Use the same ordered four-point-plus-informative-recap corpus and default policy as the independent recovery matrix. Use a legal deterministic bounded interpreter whose result depends only on the supplied package: it returns the reference interpretation and a distinct comparison statement when `package.previous_baseline` is present. In the fault-free run, the fifth input leaves exactly one MERGED worktree with two supports. Inject failure after that MERGED status commits, or after `promotion-evaluated` commits but before COMPLETE. Close/reopen and replay the fifth input. The runner invokes the interpreter again with the newly accepted Baseline now supplied as previous cognition, creating an additional OPEN worktree with one support. HEAD remains unchanged at this point, but recovered worktree state differs from the fault-free reference. Both reviewers reproduced this. Expanding the entire 30-point matrix with this deterministic package-sensitive interpreter yields **24/30 equivalent**; all six failures add the extra OPEN worktree.
- **Runtime consequence:** Incomplete-input recovery repeats already committed cognition effects instead of resuming the earliest incomplete effect. A replaceable interpreter can therefore create spurious candidates/support after a crash. Correctness currently depends on the reference interpreter ignoring previous accepted cognition. Monotonic progress writes prevent marker rollback but do not prevent repeated interpretation/effects.
- **Minimal repair:** Honor durable downstream completion and reuse the already committed interpretation/promotion outcome when resuming the same input. Reconcile that input's existing outcome before invoking the interpreter, including when its worktree is already MERGED. Finish missing markers without creating new cognition effects; use the existing stores/identities rather than a new workflow framework.
- **Required regression:** Repeat the full fault matrix with a deterministic interpreter that legitimately consumes the explicitly supplied previous Baseline. After MERGED or promotion-stage persistence but before COMPLETE, recovery must make zero additional interpreter calls, create no OPEN worktree/support/revision, and match fault-free content, selected states, worktree status and ancestry. Cover failures before/after `worktree-support-evaluated`, before/after `promotion-evaluated`, after MERGED and before COMPLETE, while retaining the now-passing post-Baseline/pre-MERGED and completed-prefix cases.

## Final disposition

| ID | Result |
| -- | -- |
| B1 | FIXED |
| B2 | FIXED |
| B3 | FIXED |
| B4 | REGRESSION |
| B5 | FIXED |
| B6 | FIXED |
| B7 | NOT FIXED |
| B8 | FIXED |
| N2 | FIXED |

## Independently obtained results

### Command gates

Interpreter: `C:\Python314\python.exe`, Python **3.14.5**; pytest **9.0.3**.

| Command | Result |
| -- | -- |
| `python -m pytest -q` | **93 passed in 24.12s** |
| `python -m pytest tests/test_runtime_e2e.py -q` | **2 passed in 1.99s** |
| `python -m mypy src/lce` | Success: 32 source files |
| `python -m ruff check src tests` | All checks passed |
| `git diff --check 9ea947a..HEAD` | Passed |

The command counts match the report. The remaining blockers are independently reproduced cases outside those assertions.

### Recovery and replay

- **Original independent 30-point matrix with the reference interpreter: 30/30 equivalent.** Compared immutable blocks/states/provenance, vectors, snapshots, higher-order candidates, worktree content/status/support, accepted cognition and normalized revision ancestry.
- **Same 30 injection points with deterministic package-sensitive interpretation: 24/30 equivalent.** Worktree selected bindings were also included. Failing points: `set_status-after`, `worktree-support-evaluated-before`, `worktree-support-evaluated-after`, `promotion-evaluated-before`, `promotion-evaluated-after`, `complete-before`. Each produces expected MERGED/2 plus unintended OPEN/1. This establishes B7 despite the first matrix's passing result.
- **Three internal partial-write controls passed:** second block/state write inside split transaction; compiled-stage write inside transaction; partial vector rebuild after deletion and one insertion. Close/reopen/retry restored expected blocks, vectors and completion.
- **Post-Baseline/pre-MERGED crash is repaired:** failures after actual Baseline commit and before status persistence reconcile to the existing revision, MERGED/2, without a new interpretation or duplicate Baseline.
- **Completed historical replay is repaired:** the R1–R7 corpus accepts revision 2 containing findings 5/6/7. Thirty individual-input, every-prefix and full-corpus replay cases, before and after restart, leave full HEAD/history/accepted content, worktree objects/status/support and interpreter calls unchanged. In particular R1–R5 no longer rolls revision 2 backward. Explicit lower-stage writes after COMPLETE also remain COMPLETE.

### Selected-state, history and invalidation controls

- **B5:** Strict selection of B4 and reordered selection B4/B2 preserve exact block/state ownership and ordering through package, worktree, Baseline persistence and accepted read. Eight selected/unselected-source and restart combinations pass. Selected-source invalidation suppresses the Understanding; an exclusively unselected source does not. Wrong owner, missing/unknown state, conflicting duplicate, mismatched cardinality, empty selection and an existing but unauthorized later state all fail closed before acceptance.
- **B2:** A block's t1 state has e1/e2; its later t2 state adds e4. A durable t1 worktree is reopened and promoted after t2 exists. Accepted support remains exactly the t1 state and e1/e2. Another restart, derived-snapshot deletion and chronological rebuild preserve complete snapshot objects, block content/occurrence range, vectors, structures, package state and accepted provenance. No e4 leaks into t1.
- **B1 negative:** Losing one meaningful side removes the old Understanding without copied/suffixed text, relaxed promotion or unsupported replacement revision; unrelated accepted cognition remains unchanged.
- **B1 positive:** Exact default-policy e1–e7 sequence accepts revision 2; invalidating e7 suppresses it and creates corrected OPEN/1. After restart, genuinely informative e8 supplies the second support and creates revision 3 with the correct predecessor, sources e1–e6/e8 and exact pre-e7 selected state. No `UnauthorizedSourceError`; separate unrelated accepted HEAD remains unchanged.
- **B3/N2:** Six equivalent center/k observations of a two-point structure produce zero higher-order candidates; distinct overlapping structures retain a positive candidate. Unchanged links at a later snapshot yield an empty `linked_structures` delta.
- **B6:** Failed E1 blocks equal-timestamp E2 before/after restart. Successful E1 then E2, followed by E3 at +1 microsecond, compile once each; provider calls are `E1,E1,E2,E3`, replay adds no calls and checkpoint ends at E3.
- **B8:** Independently authored plain-object `AuditMemory`, with no ReferenceMemoryStore inheritance, private SQLite access or shipped test-double reuse, runs the actual injected pipeline through vectors, snapshots, higher-order candidate, MERGED worktree and accepted read. Selected-source invalidation suppresses the old Baseline. This backend is intentionally ephemeral; SQLite restart behavior was tested separately.
- **Interpreter boundary:** Authorized package/source closure, UNKNOWN, REJECTED, forged support rejection, equivalent-content no revision, changed-content correct revision ancestry, truthful recording trace and zero read-time interpreter calls all pass. The package exposes no Memory search, evidence-write or promotion capability.

### Clean exact-HEAD installation

Exported **ecf41377224881b51e242222c185acf191b324da** with `git archive`, installed the export in a fresh venv using ordinary pip/PEP 517 build isolation, and ran an independent script from outside the repository with `python -I`. Import resolved to the venv's `site-packages/lce/__init__.py`; installed distributions were only `lce-core` and `pip`, with no MR requirement.

The nonempty fixture explicitly used `ConservativePromotionPolicy(min_blocks=2, min_structures=2, min_support_cycles=2)`. It produced one accepted Understanding; batch and nearline with close/reopen after each input matched. Built wheel SHA-256: `107ac164de0984a239801e67eec093a856fee3531615ee80a071d7be338da212`.

### Scope and retained execution evidence

No repair-induced architecture drift was found: selected-state bindings remain within the existing candidate/Core/Baseline authority; no canonical Structure authority, second truth judge, duplicate accepted store, recursive cognition, Body/current-turn reasoning, MR implementation, derived-cognition-to-Evidence loop or heavyweight workflow framework was introduced. The rejection is limited to B4 and B7 correctness. Algorithm/model quality and threshold tuning are not rejection grounds, and research history is unchanged.

Independent scripts and JSON matrix results are in `C:/Users/Temp/AppData/Local/Temp/lce-z2-audit-c3065411593046509e34521fbeb8f93d/`, notably `fault_matrix.py`, `contextual_fault_matrix.py`, `replay_and_stage.py`, `backend_barrier.py`, `in_transaction_faults.py` and `clean_smoke_explicit.py`. Fresh reviewer probes in the Temp directory are `lce-z2-fresh-extra.py`, `lce-z2-fresh-history.py`, `lce-z2-fresh-retained.py` and `lce-z2-fresh-review-controls.py`. These are local execution artifacts; the reproductions and required regressions above define the remaining work.

Only this Z2 report was written in the repository. Production/tests/dependencies were not modified; earlier audit reports were preserved. No merge, tag or research-timeline write was performed. Re-audit only the B4/B7 repairs and their affected paths, retaining the passing controls and command/install gates as regression checks.
