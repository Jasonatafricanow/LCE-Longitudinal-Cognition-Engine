# LCE V1 Closure Regression Suite Report

## Scope

- Repository/worktree: `C:\projects\w\lce-v1-close`
- Test base: `ecf41377224881b51e242222c185acf191b324da`
- Exact test commit: `69fe0bc` (`test: encode LCE V1 closure invariants`)
- Production source changed: **none**
- New test surface: `tests/test_v1_closure_invariants.py`, `tests/test_v1_recovery_fault_matrix.py`

## TDD RED evidence

The new suite is intentionally run on the known-broken base before any production repair.

- B4 pure-recap regression: expected **RED** because the current support identity includes the immutable state ID, so recap-only state history increments qualifying support and can promote.
- B7 package-sensitive recovery matrix: expected **RED** on the six established points `set_status-after`, `worktree-support-evaluated-before`, `worktree-support-evaluated-after`, `promotion-evaluated-before`, `promotion-evaluated-after`, and `complete-before`.
- The package-sensitive fixture records calls and uses only `package.previous_baseline`; it performs no Memory retrieval and no external calls.

Fresh base results before any production repair:

- `python -m pytest tests/test_v1_closure_invariants.py -q`: **6 passed, 4 failed**; the four failures are recap/support-inflation assertions.
- `python -m pytest tests/test_v1_recovery_fault_matrix.py -q --tb=no`: **19 passed, 13 failed**, including the two named B7 regressions; the 30-case matrix is **19/30 equivalent, 11/30 RED** under the required interpreter-call-count oracle.
- The six durable-state B7 failures are the established recovery defects listed above. Five additional matrix RED cases are call-count-only differences at pre-completion retry points (`create-before/after`, `record_support-before/after`, `save_revision-before`), retained because invocation count is an explicit oracle field.
- `python -m pytest tests/test_z0_blocker_repairs.py tests/test_z1_blocker_repairs.py tests/test_runtime_e2e.py -q --tb=short`: **21 passed**.
- `python -m pytest -q --tb=no`: **118 passed, 17 failed**; all failures are in the new B4/B7 regression surface.
- `python -m ruff check tests/test_v1_closure_invariants.py tests/test_v1_recovery_fault_matrix.py`: **All checks passed**.
- `python -m mypy tests/test_v1_closure_invariants.py tests/test_v1_recovery_fault_matrix.py`: **Success: no issues found in 2 source files**.

## Matrix oracle

The 30 cases are the established audit points: before/after `_write_current_state`, `_save_checkpoint`, `commit_compilation`, vector rebuild, snapshot creation, snapshot persistence, worktree creation, support persistence, Baseline revision persistence, worktree status persistence, plus before/after each durable `vector-ready`, `snapshot/discovery-evaluated`, `worktree-support-evaluated`, `promotion-evaluated`, and `complete` marker.

The normalized comparison includes semantic blocks/states and provenance, vectors, snapshots, candidate identity, worktree topology/content/support/status/selected support, support observations, accepted content, Baseline revision ancestry, and interpreter call count/previous-baseline call records. Random worktree UUIDs and wall-clock fields are excluded; Baseline UUID ancestry is normalized to region/revision numbers.

## Existing fixed controls

The retained B1/B2/B3/B5/B6/B8/N2 controls remain in the existing suite and are not duplicated: `tests/test_z0_blocker_repairs.py`, `tests/test_z1_blocker_repairs.py`, `tests/test_runtime_e2e.py`, `tests/test_invalidation_propagation.py`, and the structure/compiler/reference-memory tests. Their focused result is recorded with the RED run.

## Verdict

`CLOSURE REGRESSION SUITE ESTABLISHED — EXPECTED RED ON B4/B7`
