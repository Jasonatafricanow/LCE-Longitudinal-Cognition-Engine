# LCE V1 Q1 Pre-Closure Audit

## Verdict

`READY FOR FINAL GPT-6 CLOSURE AUDIT`

This is the low-cost independent pre-closure verdict only. It does not declare
LCE V1 product closed.

## Authority and reviewed range

- Worktree: `C:\projects\w\lce-v1-close`
- Branch: `w/lce-v1-close`
- Exact audited HEAD: `b89d6a333bc0f806c8964dbd09381d21868d8b10`
- Permanent test authority: `69fe0bc05bbc232b371f123628a8054340b63f70`
- Known-broken production base: `ecf41377224881b51e242222c185acf191b324da`
- Reviewed range: `69fe0bc..b89d6a3`

Relevant commits, in order:

1. `fbd0b87` — record exact closure test commit
2. `f7ce087` — align recovery oracle with durable cognition effects
3. `eff90b6` — separate recap provenance from cognition support
4. `d22b330` — reuse durable cognition effects during recovery
5. `b89d6a3` — record R3 repair verification

The checkout was otherwise unchanged by this audit except for this report. It
already contained three unrelated untracked prior audit reports, which were
preserved.

## Test-integrity verdict

`PASS`

The ancestry and timestamps prove that the permanent tests preceded both
production repairs:

- `69fe0bc` and `f7ce087` are ancestors of `eff90b6`; `eff90b6` is an ancestor
  of `d22b330`.
- The permanent tests are tracked and committed:
  - `tests/test_v1_closure_invariants.py` at `69fe0bc`
  - `tests/test_v1_recovery_fault_matrix.py` at `69fe0bc`, with only the
    durable-effect oracle correction at `f7ce087` before production repair.

Historical RED was reproduced in temporary detached worktrees without changing
the audited checkout:

- At the known-broken source with the closure tests: `4 failed, 6 passed`; all
  four failures were B4 recap/support-inflation failures.
- At pre-repair `f7ce087`, with the corrected matrix oracle: `20 passed,
  12 failed`. The 30-case fault matrix portion was `20/30` equivalent and
  `10/30` RED; the two additional named recovery tests were also RED.

The corrected oracle exempts only `create-before`, where the worktree INSERT
has not committed. For every other case it compares the complete durable
signature and interpreter calls. The signature includes semantic block states
and provenance, vectors, snapshots, candidates, worktree topology/content/
support/status, support observations, accepted content, Baseline ancestry, and
selected immutable support. There are no `skip`, `xfail`, broad exception
swallows, or fixture-bypass branches. Production contains no references to the
test fixture identifiers, and no promotion-policy threshold was changed to
hide B4.

## Independent B4 reproduction

`B4 = FIXED`

A newly authored corpus and fixture used production `LceRuntime` APIs with the
unchanged default `ConservativePromotionPolicy`:

```text
four related distinct cognition blocks -> OPEN / support=1
restart
pure recap #1 -> OPEN / support=1
pure recap #2 -> OPEN / support=1
new candidate-relevant semantic information -> MERGED / support=2
```

Observed independently:

- raw immutable state history changed from `4` to `6` across the recaps;
- the selected immutable state changed and retained the recap raw-evidence
  provenance;
- pure-recap support identity remained stable and no Baseline was created;
- the relevant semantic change added the second support identity and merged.

The repair is behavioral, not fixture-specific: `src/lce/runtime.py` retains
`block_id + state_id` for exact provenance, while the qualifying support
fingerprint uses semantic block content and effective structure membership and
does not treat a state ID alone as new cognition support.

## Independent B7 reproduction

`B7 = FIXED`

A newly authored deterministic bounded interpreter recorded every call and
legally branched on `package.previous_baseline` (`None` versus a present
Baseline). It used only the supplied package and no Memory/model access.

All ten required post-durable probes passed:

```text
create-after
record_support-before
record_support-after
save_revision-before
set_status-after
worktree-support-evaluated-before
worktree-support-evaluated-after
promotion-evaluated-before
promotion-evaluated-after
complete-before
```

For every case, recovery produced the same normalized Baseline history and
HEAD revision/content and ancestry, selected immutable support, worktree
status/topology, accepted read, and pipeline completion state as the
uninterrupted reference. Interpreter call records were equal after durable
cognition-effect existence; every case ended with zero OPEN worktrees and no
duplicate cognition effect.

The independent pre-durable probe also passed: `create-before` faulted before
the worktree INSERT, leaving zero worktrees; restart retried the interpreter as
allowed and converged to the reference state with zero OPEN worktrees.

The production repair remains bounded: it persists the processing-input
identity on the existing cognition worktree, reuses committed candidate and
selected support during replay, and resumes downstream bookkeeping without a
new interpretation.

## Permanent closure and recovery tests

- `python -m pytest tests/test_v1_closure_invariants.py -q` — `10 passed`
- `python -m pytest tests/test_v1_recovery_fault_matrix.py -q` — `32 passed`
- The recovery file evaluates 30 injection cases plus two named recovery
  controls; the 30-case normalized oracle is implemented, not merely reported.
- Permanent coverage remains for pure recap, multiple pure recaps, genuine new
  support, restart/replay stability, and post-durable recovery.

## Retained controls

The requested retained surface passed:

`python -m pytest tests/test_z0_blocker_repairs.py tests/test_z1_blocker_repairs.py tests/test_runtime_e2e.py -q` — `21 passed`

State by control:

- B1 — FIXED
- B2 — FIXED
- B3 — FIXED
- B4 — FIXED, independently reproduced above
- B5 — FIXED
- B6 — FIXED
- B7 — FIXED, independently reproduced above
- B8 — FIXED
- N2 — FIXED

## Full command gates

- `python -m pytest -q` — `135 passed`
- `python -m pytest tests/test_runtime_e2e.py -q` — `2 passed`
- `python -m mypy src/lce` — success, 32 source files
- `python -m ruff check src tests` — all checks passed
- `git diff --check 69fe0bc..HEAD` — clean

The implementer evidence matches the fresh results; no discrepancy remains.

## Clean exact-HEAD installation

`git archive --format=zip HEAD` was exported at the audited HEAD and installed
normally with PEP 517 into a fresh virtual environment using `pip install`.
From an outside-repository working directory, `python -I` verified:

- `lce` imported from the venv `site-packages` path;
- no MR runtime was required;
- standalone `LceRuntime` initialization succeeded;
- nonempty synthetic processing completed;
- the explicit fixture policy `explicit-static-package-v1` was persisted;
- one accepted cognition view was observable with `status=MERGED` and
  `support_cycles=2`.

## Architecture and scope check

`PASS`. The R3 production diff touches only:

- `src/lce/runtime.py`
- `src/lce/cognition/worktree.py`
- `src/lce/cognition/promotion.py`

No canonical Structure authority, new truth judge, duplicate accepted-cognition
store, interpretation journal/event-sourcing system, heavyweight workflow
engine, MR dependency, Body/current-turn reasoning, recursive cognition,
Derived Cognition to Raw Evidence path, or threshold-only workaround was
introduced. The B4 and B7 repairs remain respectively:

```text
provenance identity != qualifying cognition-support identity
pre-durable retry allowed -> post-durable committed cognition effect reused
```

## Final Q1 decision

All required Q1 conditions are satisfied: independent B4 and B7 probes,
permanent closure tests, normalized 30/30 recovery matrix, retained controls,
full tests, type/lint/diff gates, clean installation, test permanence, and
architecture/scope review.

`READY FOR FINAL GPT-6 CLOSURE AUDIT`
