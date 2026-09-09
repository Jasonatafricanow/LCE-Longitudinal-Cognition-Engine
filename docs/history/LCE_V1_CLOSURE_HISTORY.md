# LCE V1 Closure History

## Purpose

This is the engineering-quality record of LCE V1 closure. It preserves the
sequence of green suites, independent rejects, bounded repairs, permanent RED
evidence, and final release verification.

The central lesson is not that the project was chaotic. It is that each audit
layer exposed a different invariant that ordinary feature tests did not
observe. The response was to turn those discoveries into narrower repairs and
permanent executable tests while preserving the standalone authority boundary.

## Closure in one line

```text
74 tests green → Z0 reject
85 tests green → Z1 reject
93 tests green → Z2 reject
permanent regression suite introduced
135 tests green → Z3 finds permutation blind spot
139 tests + canonical-order regression → engineering closure
```

Green counts are not interchangeable with closure verdicts. The audit verdict
is recorded beside each count below.

## Baseline: V1 initial closure candidate

The A1–A5 sequence started from LCE master `c84e528a...` on 2026-09-09:

```text
b838283  A1 Reference Memory substrate
c227fdf  A2 Semantic Block compiler
4cd631f  A3 snapshot structure discovery
d92c989  A4 cognition Worktree and promotion
ac87d71  A5 standalone product pipeline
```

The initial closure candidate was `16b014e1a1d3b4a225d4049d7df9615c93921dc4`.
Its ordinary suite reported 74 passing tests, the install/smoke path worked,
and the product report described the pipeline as closed. That claim was not
accepted as independent closure. The Z0 audit started from this exact HEAD and
found defects through fresh adversarial runtime probes.

## Z0: 74 tests green, closure rejected

**Audited HEAD:** `16b014e1a1d3b4a225d4049d7df9615c93921dc4`

**Verdict:**

```text
REJECT — LCE V1 PRODUCT CLOSURE BLOCKED
```

The audit did not reject embedding quality, research ambition, or the
standalone boundary. It rejected runtime correctness at eight named blockers:

| Blocker | What the green suite failed to observe | Invariant later made executable |
|---|---|---|
| B1 invalidation | Removing invalid support copied old text through a relaxed path instead of proving a supported correction. | Loss of a supporting source must suppress old cognition; replacement needs valid rebuilt support. |
| B2 historical mutability | A later continuation changed the source closure of an earlier historical conclusion. | Cutoff-bound interpretation must retain immutable block/state provenance. |
| B3 higher-order alias | Equivalent center/k observations became multiple cognition structures. | Equivalent effective support deduplicates; distinct overlap remains possible. |
| B4 support inflation | Unrelated global snapshot/provenance change counted as new support. | Qualifying support is candidate-relevant, not every durable state change. |
| B5 missing bounded interpretation | The production path did not contain the required replaceable bounded interpreter seam. | Interpretation receives only an authorized package and returns checked support. |
| B6 failed-input overtaking | A later input could advance while an earlier failed input remained unresolved. | Earliest pending evidence barrier survives restart and blocks later input. |
| B7 incomplete replay | Compiler replay was treated as full-pipeline completion and skipped downstream effects. | Durable stages resume downstream idempotently without losing or duplicating effects. |
| B8 decorative Reference Memory port | A protocol-conforming replacement could not run the actual V1 pipeline. | Independent substrate must execute compile → structure → Worktree → read. |

The audit also found N2: linked-structure diff reported unchanged links as new
links. The important process fact is that ordinary tests were green while
independent runtime probes found real defects. The next step was bounded repair,
not a redesign or an attempt to make the audit wording disappear.

## R1: first bounded repair, then Z1 reject

The first repair tranche addressed the eight Z0 findings and N2 through four
commits:

- `087e5cb` — preserve cutoff-bound cognition state;
- `da1ff50` — make structure support and bounded interpretation explicit;
- `f99d74a` — complete recovery and substrate-replacement seams;
- `a250788` — expose recovery and replacement contracts.

The repair report said `Z0 BLOCKER REPAIR COMPLETE — READY FOR RE-AUDIT` and
recorded 85 passing tests. Z1 nevertheless rejected closure after independent
reproduction.

**Z1 remaining disposition:**

```text
B3 fixed
B4 fixed under the specified controls
B6 fixed
B8 fixed
N2 fixed
B1/B2/B5: shared immutable selected-state mapping defect
B7: recovery/completed-replay defect
```

The four remaining failures converged on two roots:

1. the exact historical block/state selected by interpretation was not carried
   faithfully through promotion and read; and
2. a durable downstream effect did not prevent replay from reinterpreting or
   recreating cognition.

The Z1 verdict remained:

```text
REJECT — LCE V1 PRODUCT CLOSURE BLOCKED
```

This is why “85 tests green” does not appear as a historical closure milestone.

## R2: selected immutable support and replay repair, then Z2 reject

The next implementation commit was:

```text
12d1c6a  fix: preserve selected immutable support
```

It carried explicit `(block_id, state_id)` selection through bounded
interpretation, Worktree persistence, Core candidate/Baseline persistence, and
accepted read. It also repaired historical promotion and completed replay
paths. The repair report was recorded at `ecf4137`.

The Z2 audit found the selected-state path substantially repaired:

- B1, B2, B3, B5, B6, B8, and N2 passed independent controls;
- the reference recovery interpreter produced `30/30` equivalence;
- the full suite reported 93 passing tests.

But Z2 still rejected closure:

### B4 regression

A provenance-only immutable state change from a pure recap advanced support and
could satisfy the default two-support promotion policy. The state was exact for
provenance, but it was not new cognition support.

### B7 not fixed

The reference interpreter did not meaningfully consume prior accepted
cognition, so the matrix looked correct. A legal package-sensitive interpreter
did consume the explicitly supplied previous Baseline and exposed repeated
cognition effects:

```text
reference matrix:       30/30 equivalent
package-sensitive matrix: 24/30 equivalent
```

The six package-sensitive failures produced an expected `MERGED/2` plus an
unintended `OPEN/1`. This was a decisive engineering lesson: a reference
implementation that ignores a legal input is not a sufficient oracle for a
replaceable interpreter boundary.

## Permanent regression authority: RED before repair

The repeated hidden defects caused a deliberate process change:

```text
GPT-6 adversarial discoveries
→ compile discoveries into permanent repo tests
```

**Test authority:**
`69fe0bc05bbc232b371f123628a8054340b63f70`.

The new permanent files were:

- `tests/test_v1_closure_invariants.py`;
- `tests/test_v1_recovery_fault_matrix.py`.

They were committed against the known-broken `ecf4137` base before the R3
production repair. Their deliberate RED evidence was:

```text
closure invariants: 6 passed, 4 failed
recovery suite: 20 passed, 12 failed
30-case recovery matrix: 20/30 equivalent, 10/30 RED
retained Z0/Z1 regressions + E2E: 21 passed
full suite: 119 passed, 16 failed
```

The tests did not use broad skips, xfails, production fixture identifiers, or
threshold weakening. The recovery oracle was then corrected in
`f7ce087` so the durable cognition-effect distinction was explicit:

```text
pre-durable retry may call the interpreter again
post-durable cognition effect must be reused
```

The permanent suite became a record of the audit's RED state, not merely a
green snapshot after the fact.

## R3: 135 tests green, Q1 ready

The bounded R3 production fixes were:

- `eff90b6` — separate recap provenance from cognition support;
- `d22b330` — reuse durable cognition effects during recovery.

The repair deliberately kept exact immutable selected support for provenance
while computing qualifying support from semantic content and effective
structure membership. It also persisted processing-input identity so recovery
could find an existing durable Worktree/cognition effect before invoking the
interpreter.

R3 reported:

```text
closure invariants: 10 passed
recovery suite: 32 passed
normalized matrix: 30/30 equivalent
retained Z0/Z1 controls: 19 passed
full suite: 135 passed
mypy: clean
Ruff: clean
```

Independent Q1 audited HEAD `b89d6a333bc0f806c8964dbd09381d21868d8b10` and
reported:

```text
B4 independently passed
B7 independently passed
30/30 matrix
135 tests
READY FOR FINAL GPT-6 CLOSURE AUDIT
```

This was correctly treated as a readiness gate rather than the final product
verdict.

## Z3: 135 tests green, permutation blind spot found

The final blind audit found another B4 path at the Q1 HEAD. It recapped the
**oldest** selected block rather than the newest one:

```text
pure recap oldest block
→ selected recency order changes
→ order-sensitive support fingerprint changes
→ false promotion
```

The permanent fixture always recapped the newest block, so its selected order
did not change. Removing `state_id` had been necessary, but it was not
sufficient. The independent probe kept block contents and structure IDs
constant and still observed `OPEN/1 → MERGED/2` after a provenance-only recap.

Z3 therefore recorded:

```text
REJECT — LCE V1 PRODUCT CLOSURE BLOCKED
```

This rejection was about test completeness and a real runtime invariant, not
historical authenticity. B7 independently passed; the remaining blocker was
B4. The full 135-test suite and 30/30 reference matrix did not override the
permutation finding.

## Final B4 RED→GREEN repair

The test-first commit was:

```text
516826c  test: cover recap ordering without support inflation
```

Its historical RED was:

```text
3 RED / 1 passed
```

The cases varied recap ordering so the oldest, middle, and newest selected
blocks could be exercised. The test asserted that a pure recap kept semantic
content/effective structure and support identity unchanged, while a genuinely
relevant change advanced support and promotion.

The implementation commit was:

```text
808b148  fix: canonicalize cognition support fingerprint order
```

It canonicalized the ordering used only for qualifying support identity while
preserving exact selected ordering and immutable state for provenance.

The final principle is:

```text
provenance ordering
≠
qualifying cognition-support canonical identity
```

## Final closure evidence

The final gates at implementation HEAD `808b148960f8ae5852cd78a7b8343611539631b2`
were:

| Gate | Result |
|---|---|
| Permanent closure invariants | 14 passed |
| Permanent recovery suite | 32 passed |
| Normalized recovery matrix | 30/30 |
| Retained regressions + E2E | 21 passed |
| Full suite | 139 passed |
| mypy `src/lce` | clean |
| Ruff `src tests` | clean |
| Isolated exact-HEAD install/import/smoke | passed |

F1 then fast-forwarded canonical `master` to `808b148...`, added the
metadata-only release record, and created annotated tag `v1.0.0` resolving to
release metadata commit `047cf4e...`. The implementation identity remains
`808b148...`; the tag's metadata boundary is intentionally separate.

## What each layer made executable

| Layer | Previously invisible condition | Permanent or bounded executable consequence |
|---|---|---|
| Z0 | Invalid/old support could be served or copied; history could mutate; ports/recovery could be decorative. | B1–B8 and N2 independent controls. |
| Z1 | Selected immutable state could be replaced or positionally misattributed; completed replay could duplicate cognition. | Exact selected support, subset/reorder, invalidation, replay and alternate-substrate tests. |
| Z2 | Reference interpreter hid package-sensitive recovery; recap state version inflated support. | Package-sensitive matrix, support-identity controls, permanent RED suite. |
| R3/Q1 | The bounded fixes were green under the current permanent fixture. | 135-test closure and independent B4/B7 readiness evidence. |
| Z3 | Recap of an older selected block permuted order while content/structure stayed unchanged. | Oldest/middle/newest permutation regression and canonical support ordering. |
| F1 | The final source and all gates needed a stable identity. | Frozen implementation HEAD, metadata release commit, immutable tag, and release record. |

## Final scope boundary

LCE V1 is standalone and engineering-closed. The following remain explicitly
non-blocking future work rather than unfinished V1 requirements:

- embedding/model quality;
- threshold tuning;
- higher-order precision;
- future MR/Body integration;
- performance optimization.

No V1.1 or V2 architecture is inferred from this closure history.
