# LCE V1 R3 Repair Report

## Verdict

`R3 REPAIR COMPLETE — AUTOMATED CLOSURE GATES GREEN`

This report covers the bounded B4/B7 repair only. It does not declare LCE V1 product closure.

## Repository and authority

- Repair worktree: `C:\projects\w\lce-v1-close`
- Known-broken production base: `ecf41377224881b51e242222c185acf191b324da`
- Permanent test authority: `69fe0bc05bbc232b371f123628a8054340b63f70`
- Final repair HEAD: `d22b33047c6f1526d59d5c2c72f4e16333dae2da`
- Test-authority alignment commits were retained; the permanent tests were not weakened or rewritten.

## Production repair commits

1. `eff90b6` — `fix: separate recap provenance from cognition support`
2. `d22b330` — `fix: reuse durable cognition effects during recovery`

## Exact fixes

### B4 — recap provenance versus cognition support

The immutable `block_id + state_id` selection remains the exact provenance carried through worktree, promotion, Baseline, and read. The qualifying support fingerprint no longer treats a new immutable state ID as new cognition support by itself. It uses the selected block's semantic content and effective structure membership instead.

Pure recap, duplicate source, replay, unrelated cutoff churn, and duplicate local observations therefore retain one support identity. A genuinely relevant semantic change produces a new support identity and can advance the existing conservative policy.

Result: the four B4 RED cases are GREEN; closure invariants are `10 passed`.

### B7 — durable cognition-effect recovery

The existing cognition worktree store now records the processing input identity that created/updated the durable worktree effect. During replay, runtime locates the worktree for the exact input before invoking the bounded interpreter:

- no committed worktree effect: interpretation retry remains allowed (`create-before`);
- committed worktree/support/promotion effect: persisted candidate and selected immutable support are reused;
- committed Baseline with incomplete worktree bookkeeping: existing reconciliation completes `OPEN → MERGED`;
- merged/dropped effect: only downstream durable bookkeeping resumes.

Recovery uses the persisted selected-support ordering/state mapping when constructing the fallback promotion interpretation. It does not fetch latest block state and does not invoke the interpreter again after a durable cognition effect exists.

Result: the normalized recovery matrix is `30/30` equivalent, and the permanent fault-matrix test is `32 passed`.

## Verification

Commands and results from final repair HEAD:

```text
python -m pytest tests/test_v1_closure_invariants.py -q
10 passed

python -m pytest tests/test_v1_recovery_fault_matrix.py -q
32 passed

python -m pytest -q
135 passed

python -m pytest tests/test_runtime_e2e.py -q
2 passed

python -m mypy src/lce
Success: no issues found in 32 source files

python -m ruff check src tests
All checks passed!
```

Retained repair controls also remained GREEN:

```text
python -m pytest tests/test_z0_blocker_repairs.py tests/test_z1_blocker_repairs.py -q
19 passed
```

This includes the retained B1 invalidation correction, B2 historical immutable-state provenance, B3 equivalent-structure deduplication, B5 selected immutable support, B6 ordered failure barrier, B8 alternate substrate, and N2 linked-structure delta controls.

## Clean exact-HEAD install

From final HEAD:

1. `git archive --format=tar HEAD` produced an archive at the exact final HEAD.
2. A fresh virtual environment installed the archive with `pip install .`.
3. `python -I -c "import lce; from lce.runtime import LceRuntime"` succeeded.
4. The isolated standalone synthetic smoke completed with `standalone smoke ok`.

## Remaining limitations

No R3 blocker or known non-blocking B4/B7 test limitation remains. This repair intentionally does not expand architecture, alter the permanent oracle, add a workflow/event-sourcing framework, integrate MR, or change Body/consumer boundaries. Algorithm tuning outside B4/B7 remains deferred to the existing product/audit process.

No MR repository or MR source was modified.
