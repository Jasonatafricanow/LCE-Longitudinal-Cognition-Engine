# LCE V1 Z0 Blocker Repair Report

## Verdict

**Z0 BLOCKER REPAIR COMPLETE — READY FOR RE-AUDIT**

This report does not declare `LCE V1 PRODUCT CLOSED`. The repair was bounded to
the audited implementation failures and preserves the frozen LCE V1 chain.

## Repository identity

- Repair base / audited base: `16b014e1a1d3b4a225d4049d7df9615c93921dc4`
- Worktree: `C:\projects\w\lce-v1-close`
- Branch: `w/lce-v1-close`
- Final implementation repair HEAD: `a2507888d5615868510682f0e799f2a1faf6f014`
- Repair commits:
  - `087e5cb37e3b96ed0d05e51b11a84eeba07535fe` — preserve cutoff-bound cognition state
  - `da1ff503fd4d1099c745f811a964f381fb181442` — structure support and bounded interpretation
  - `f99d74a39f55402ad9be35b7d05313989ec6a40c` — recovery and substrate replacement seams
  - `a2507888d5615868510682f0e799f2a1faf6f014` — expose recovery and replacement contracts
- Verification environment: `C:\Python314\python.exe`, Python `3.14.5`, pytest `9.0.3`, Ruff `0.16.5`.

The audit authority `LCE_V1_Z0_FINAL_AUDIT_REPORT.md` was preserved in this
worktree as pre-existing untracked audit material and was not used as an
implementation input beyond the user-authorized audit authority.

## Frozen architecture map

```text
Raw Evidence
  -> Reference Memory validity/provenance
  -> immutable Semantic Block states
  -> state-bound vector projections
  -> cutoff Structure Snapshot / diff
  -> higher-order candidate
  -> bounded interpreter package
  -> OPEN cognition worktree
  -> conservative promotion through Baseline / HEAD
  -> accepted current-valid Understanding read
```

Reference Memory remains replaceable through focused ports. Structure,
vectors, snapshots, support observations, and worktrees remain derived; no
canonical Structure authority or second truth judge was added.

## B1-B8 fix mapping

| Audit blocker | Exact repair |
|---|---|
| B1 invalidation copied old text | `invalidate_and_rebuild` now rebuilds the valid derived slice and evaluates only newly interpreted candidates through normal policy. Affected HEADs are filtered by current-valid evidence until valid support exists; no correction suffix or relaxed policy remains. |
| B2 mutable historical block state | Reference Memory stores immutable `semantic_block_states`; continuation creates a new state. Snapshots persist visible block states and their vectors. Baselines persist promoted state IDs, so historical source closure does not grow with future continuation. Snapshot identity includes state/vector/config inputs. |
| B3 equivalent observations became HOC | Higher-order generation groups observations by effective member support identity before relation generation. Center/k lenses remain in the local observation layer; equivalent full support produces one effective structure, while non-equivalent overlap remains possible. |
| B4 global snapshot ID inflated support | Worktrees persist `support_observations` keyed by candidate-relevant fingerprints. Replay, restart, recap-only state, unrelated points, and duplicate lenses do not count; changed candidate block content or effective support can count. |
| B5 absent bounded interpretation | Added replaceable `BoundedInterpreter`, `BoundedInterpretationPackage`, and reference rule-based implementation. LCE resolves structures, immutable block states, authorized source refs, and previous HEAD before interpretation. Returned support is checked against the package and trace metadata is truthful. Read never invokes it. |
| B6 failed input overtaken | Compiler checkpoints persist the earliest pending evidence barrier. Later material raises `PendingInputError` before advancing. Retry after restart clears the barrier only when the original input compiles; ordering uses `(ordering_key, evidence_id)`. |
| B7 compiler replay skipped downstream | `commit_compilation` atomically writes block states, compiled marker, checkpoint, and compiled stage. Separate durable pipeline stages track vector, snapshot/discovery, worktree support, promotion, and completion. Replay continues downstream idempotently instead of being treated as full-pipeline completion. |
| B8 decorative Memory Port | Added focused evidence, Semantic Block/state, vector, compiler-progress, and composed substrate contracts. `LceRuntime` accepts an injected `ReferenceMemorySubstratePort`; `InMemoryReferenceMemory` independently implements it without subclassing or private SQLite calls and runs the V1 pipeline. |

## N2 and N1

- `linked_structures` now reports only newly linked effective structures compared
  with the previous snapshot; unchanged overlap is omitted.
- Reference fallback documentation now states that `RuleBasedSemanticProvider`
  consumes caller semantic hints, supplied fixture vectors are topology fixtures
  rather than semantic-accuracy evidence, and supplied-vector lifecycle is
  bound to immutable block state. Real providers should use the replaceable
  semantic/embedder seams.

## Regression coverage

New/updated adversarial coverage includes:

- immutable cutoff snapshot/state/vector rebuild and accepted state provenance;
- equivalent center/k observation negative control and positive structure-level
  behavior retained;
- candidate-relevant support deduplication and genuine relevant support;
- recording bounded interpreter, exact package/source boundary, UNKNOWN filtering,
  and read-path zero interpretation calls;
- invalidation loss-of-support suppression and valid replacement promotion;
- ordered failure barrier across restart;
- atomic compiler-unit rollback and runtime vector-stage replay;
- unchanged linked-structure delta;
- independent in-memory substrate compile/vector/discovery/worktree/promotion/read.

## Required commands and results

```text
python -m pytest -q
85 passed in 13.59s

python -m pytest tests/test_runtime_e2e.py -q
2 passed in 2.16s

python -m mypy src/lce
Success: no issues found in 32 source files

python -m ruff check src tests
All checks passed!
```

Fresh exact-HEAD export/install was run with `git archive`, a new Python venv,
`pip install --no-deps <export>`, and an isolated `-I` smoke process. The wheel
was built as `lce_core-0.1.0-py3-none-any.whl`; the isolated import resolved to
the venv `site-packages/lce/__init__.py`, and standalone processing created a
Semantic Block and snapshot without MR.

The standalone recovery/composition probe produced:

```text
BATCH_NEARLINE_EQUAL= True
REPLAY_IDEMPOTENT= True
FAILURE_RECOVERY_ORDER= (('F1',), ('F2',))
ALTERNATE_SUBSTRATE_ACCEPTED= True
INVALIDATION_SUPPRESSES_OLD= True
```

The alternate substrate probe used a five-point synthetic corpus and the same
conservative policy with `min_support_cycles=1` to make the accepted read
observable in one bounded run. The durable restart contract is provided by the
default SQLite substrate; the in-memory backend is intentionally a replacement
test double.

## Remaining non-blocking limitations

- The reference semantic provider and deterministic embedding fallback are
  reproducibility implementations, not semantic quality claims.
- Structure thresholds and higher-order relation quality remain tunable policy
  parameters; no new algorithm research, model leaderboard, or TDA authority
  was introduced.
- Derived snapshots and structure observations remain rebuildable artifacts;
  the repair does not create a heavy Structure database or ontology.

## Deliberately deferred

MR integration/adapters, Body, C10, Persona, Agent identity, Intent,
ActionPolicy, RuntimeBinding, current-turn reasoning, recursive cognition,
TDA/H1 productionization, embedding-model optimization, and product closure
re-audit remain outside this repair.

## MR protection confirmation

No MR repository files were modified. No MR integration, merge, tag, release,
or publication action was performed. The repair is limited to
`C:\projects\w\lce-v1-close`.
