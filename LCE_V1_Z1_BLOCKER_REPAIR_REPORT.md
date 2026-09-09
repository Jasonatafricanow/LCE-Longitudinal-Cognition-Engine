# LCE V1 Z1 Blocker Repair Report

## Verdict

**Z1 BLOCKER REPAIR COMPLETE — READY FOR FINAL RE-AUDIT**

This report does not declare `LCE V1 PRODUCT CLOSED`. Product closure remains
owned by the final re-audit.

## Repair identity

- Repair base: `16b014e1a1d3b4a225d4049d7df9615c93921dc4`
- Audited Z1 repair base: `9ea947ab9f495b256644b2d022907678e747ea1c`
- Implementation HEAD before this report: `12d1c6a97808ca81d6822fea4a2be97285c88012` (`fix: preserve selected immutable support`)
- Worktree: `C:\projects\w\lce-v1-close`
- Branch: `w/lce-v1-close`
- Python: `3.14.5` (`C:\Python314\python.exe`)
- pytest: `9.0.3`
- mypy: `2.3.1`
- Ruff: `0.16.5`

The selected-state and replay paths were committed together because both use
the same existing promotion/worktree boundary. There was no speculative
workflow or architecture refactor.

## Exact blocker mapping

### B5 — selected immutable support fidelity

Added the explicit `AuthorizedSelectedSupport(block_id, state_id)` value and
carried it through bounded interpretation, Worktree persistence, Core
candidate, Baseline revision persistence, and the accepted read API.

The runtime validates package membership, block/state ownership, order,
cardinality, uniqueness, and current-valid Raw Evidence. Promotion uses the
authorized immutable state through the existing Core adapter. Reads no longer
reconstruct state attribution with positional `zip()` or latest-state lookup.

The Worktree retains the full authorized structural support set for policy
evaluation while Baseline provenance contains only the interpreter-selected
subset.

### B2 — historical promotion state

Snapshot-bound interpretation now persists the exact selected block/state
pairs. Later CONTINUE/RECAP state versions cannot replace those pairs during
promotion, restart, read, or derived snapshot deletion/rebuild.

### B1 — localized correction

Invalidation continues to remove stale accepted cognition and mark affected
derived worktrees for rebuild. Rebuilt interpretation packages carry the
valid historical states into normal promotion. The old text is never copied or
suffix-corrected, and the ordinary conservative policy is unchanged.

### B7 — recovery and completed replay

Completed inputs return their durable derived result without rerunning
interpretation, adding support, creating Worktrees, promoting, or creating
Baseline revisions. Incomplete inputs resume downstream from their earliest
durable stage. Pipeline stage writes are monotonic.

Promotion now reconciles an already committed equivalent Baseline with an
OPEN Worktree before any equal-content shortcut, changing only the missing
derived status to `MERGED` and linking the existing revision.

Pipeline snapshot fingerprints are used when the substrate provides the
optional progress detail; the required substrate Port remains compatible with
independent replacement backends and can fall back to the durable snapshot
cutoff.

## New regression coverage

`tests/test_z1_blocker_repairs.py` contains eight tests covering:

- strict selected subset and reordered selected subset;
- restart persistence and exact state ownership;
- selected-source versus unselected-source invalidation;
- historical t1 state promotion after a later t2 extension;
- default-policy e1–e8 localized correction;
- post-Baseline-commit Worktree reconciliation;
- completed prefix and complete-corpus replay after newer cognition;
- monotonic pipeline stage progress.

The existing Z0 controls remain in `tests/test_z0_blocker_repairs.py`.

## Verification results

Repository gates:

```text
python -m pytest -q
93 passed in 21.42s

python -m pytest tests/test_runtime_e2e.py -q
2 passed in 1.41s

python -m mypy src/lce
Success: no issues found in 32 source files

python -m ruff check src tests
All checks passed!

git diff --check 16b014e1a1d3b4a225d4049d7df9615c93921dc4..HEAD
passed
```

Recovery and retained controls:

- durable recovery fault matrix: **30/30 equivalent to fault-free reference**;
- split-state transaction rollback, compiled-stage rollback, and partial
  vector recovery: **3/3 passed**;
- B6 ordered failure barrier: passed, calls remained `E1, E1, E2, E3`;
- B8 independent non-subclassing `AuditMemory` backend: passed through actual
  pipeline and invalidation;
- B3 higher-order alias deduplication: passed;
- B4 candidate-relevant support inflation controls: passed;
- N2 linked-structure diff control: passed.

The independent fresh-review controls also passed selected subset provenance,
selected-source invalidation, historical reconstruction after derived snapshot
deletion/rebuild, and invalidation without unsupported copied correction.

## Fresh exact-HEAD install

`git archive HEAD` was exported to a new temporary directory, installed into a
new virtual environment with ordinary pip/PEP 517 build isolation, and
imported with `python -I` without MR. A standalone synthetic batch run with an
explicit one-cycle policy returned accepted cognition from the installed
`site-packages` package.

The first smoke fixture intentionally used the default conservative policy and
did not contain enough repeated structural support; it was rerun with the
fixture policy explicitly configured and passed. This is a fixture-policy
distinction, not an install or import failure.

## Non-blocking limitations

The deterministic embedding, rule-based semantic provider, and rule-based
bounded interpreter remain reference implementations. Their semantic quality,
threshold tuning, and higher-order precision are algorithm-tuning concerns and
are not upgraded by this repair.

No new Structure authority, truth judge, accepted-cognition store, recursive
higher-order layer, MR integration, Body integration, or workflow framework was
introduced.

## Repository boundary

- `C:\projects\LCE` was not modified by this repair.
- The MR repository was not modified.
- `LCE_V1_Z0_FINAL_AUDIT_REPORT.md` and
  `LCE_V1_Z1_FINAL_REAUDIT_REPORT.md` remain local audit authority artifacts
  and were intentionally not committed as implementation inputs.
