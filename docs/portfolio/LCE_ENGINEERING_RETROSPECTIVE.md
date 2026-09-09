# LCE V1 — Engineering Retrospective

## What this retrospective is for

LCE V1 was an experiment in building a bounded longitudinal-understanding
runtime, but it was also an experiment in engineering with LLMs. The useful
retrospective is not “the model wrote a lot of code.” It is how the project
turned uncertain research into explicit boundaries, how independent review
rejected plausible green implementations, and how those discoveries became
permanent executable tests.

The release is frozen at implementation HEAD
`808b148960f8ae5852cd78a7b8343611539631b2`. This document does not extend the
claim into V2.

## The path in retrospect

The project moved through three different kinds of uncertainty:

1. **Representation uncertainty:** raw text, blocks, time boundaries, and
   structure abstractions had to be tested rather than assumed.
2. **Authority uncertainty:** Memory, derived understanding, model
   interpretation, and current-turn reasoning needed separate owners.
3. **Runtime correctness uncertainty:** persistence, invalidation, replay, and
   support identity had to survive adversarial faults, not merely ordinary
   examples.

The resulting path was:

```text
research negative controls
→ explicit architecture boundaries
→ bounded standalone implementation
→ independent rejection
→ permanent RED regressions
→ bounded repair and re-audit
→ final canonical-order correction
→ frozen release
```

## What was underestimated

### 1. The gap between a research boundary and a runtime boundary

The research artifacts made the Semantic Block rule clear: semantic streams
should split at semantic changes and preserve meaningful continuation. Turning
that rule into a restartable production pipeline introduced state identity,
vectors, checkpoints, snapshots, Worktrees, and downstream stage progress. Z0
showed that “the architecture is clear” did not mean the runtime path obeyed it
under invalidation or fault injection.

**Lesson:** every important architectural boundary needs a concrete state model,
failure point, and regression, not just a design statement.

### 2. The interaction between provenance and support

The project correctly preserved immutable state for historical provenance. It
then initially allowed provenance changes to look like new qualifying support.
After fixing the `state_id` leak, Z3 found that recency-based ordering could
still change the fingerprint. The same abstraction leaked through two
different channels.

**Lesson:** identify every representation used for both audit identity and
decision identity. They may need to be related, but they are not the same.

### 3. Recovery after a durable effect

It was not enough to make individual writes idempotent. A crash between
interpretation, Worktree status, promotion, and completion could leave an
effect committed but a marker incomplete. A reference interpreter that ignored
previous accepted cognition hid this problem; a legal package-sensitive
interpreter exposed it.

**Lesson:** recovery tests must vary both fault position and legal component
behavior. A forgiving reference implementation is not a complete oracle.

### 4. The economics of repeated independent review

The first adversarial reviews had high discovery value. Repeating broad
first-principles review after each bounded repair was increasingly expensive,
because much of the same surface had to be rediscovered before reaching the
new defect.

**Lesson:** use an independent reviewer to discover an invariant once, encode
it deterministically, and narrow the next review to the changed boundary plus
the permanent regression surface.

## Which abstractions survived

The following decisions survived research, implementation, and audit:

- raw evidence remains provenance/audit material, not automatically cognition;
- Semantic Blocks precede embedding and are semantic rather than time units;
- derived structures may overlap and evolve but are not canonical authority;
- Core V0 remains a small contract-first linear Baseline/HEAD system;
- Memory remains factual authority;
- bounded interpretation receives an authorized package and cannot self-promote;
- Worktree state is separate from accepted Baseline history;
- selected immutable block/state provenance is explicit;
- qualifying support identity is separate from provenance identity;
- committed cognition effects are reused during recovery;
- reads remain model-free and non-mutating;
- MR binding is optional, one-way, and separate from standalone closure.

The historical decision record is in
[`LCE_DECISION_EVOLUTION.md`](../history/LCE_DECISION_EVOLUTION.md).

## Which assumptions repeatedly failed

### “Green means closed”

The sequence is the evidence:

```text
74 tests green → Z0 reject
85 tests green → Z1 reject
93 tests green → Z2 reject
135 tests green → Z3 reject
139 tests + final regression → closure
```

The green suites were useful, but they answered narrower questions than the
independent audits.

### “A current state is equivalent to the interpreted state”

Z1 showed that latest-state lookup could corrupt historical provenance and
invalidation. The fix required carrying exact selected immutable state, not
reconstructing it from live blocks later.

### “A reference interpreter is representative enough”

The reference recovery matrix was 30/30, while a legal package-sensitive
interpreter was 24/30. The difference was not model quality; it was whether the
interpreter consumed the supplied previous Baseline, which the contract allowed.

### “Removing state_id closes support inflation”

It removed one inflation path. Z3 showed that an oldest-block recap could
permute recency order and still change an order-sensitive support fingerprint.
The final repair canonicalized support order independently of provenance order.

### “A protocol test proves replaceability”

Z0 found that a backend could satisfy the declared port and still fail when the
compiler asked for operations the port did not expose. B8 only became credible
after an independent backend ran the actual compile/vector/discovery/Worktree/
read pipeline.

## Which tests provided false confidence

The tests were not useless; they were incomplete in specific ways.

### Feature-path tests

They showed that the happy-path pipeline worked: blocks formed, structures
appeared, Worktrees promoted, and reads returned data. They did not prove
invalidation semantics or full pipeline recovery.

### Reference interpreter recovery

It proved that the reference implementation converged, but not that every legal
bounded interpreter would converge after a durable cognition effect.

### Newest-only recap fixture

The permanent B4 fixture repeatedly recapped the newest selected block. That
kept selected order stable and missed the oldest/middle permutation. The
fixture was semantically reasonable but adversarially incomplete.

### Latest-state lookup

The shortcut looked harmless while all examples used current state. It failed
only when a historical cutoff was promoted after later continuation.

The engineering response was not to discard these tests. It was to name the
unobserved invariant and add the missing negative or permutation case.

## The audit cycle as an engineering asset

The audits exposed progressively narrower problems:

| Gate | Green result | Independent discovery | What became executable |
|---|---:|---|---|
| Initial V1 candidate | 74 | B1–B8 and N2 runtime defects | Blocker-specific controls and repair boundaries |
| R1 / Z1 | 85 | Shared selected-state mapping root and B7 replay | Exact immutable state ownership and replay controls |
| R2 / Z2 | 93 | `state_id` support inflation; package-sensitive recovery `24/30` | Support identity split and permanent RED suite |
| R3 / Q1 | 135 | B4 order/recency permutation | Oldest/middle/newest recap regression |
| Final F1 | 139 | No remaining known closure defect in the bounded surface | Frozen implementation and release identity |

This is why the project should not be described as “tests were added until the
build passed.” The test surface became more semantically precise after each
failure.

## Division of labor: human judgment and LLM leverage

### Human responsibilities

The human role was not to manually author every implementation detail. It was
to own the problem and the decisions that code generation cannot safely infer:

- define the problem as reusable longitudinal understanding rather than solved
  general cognition;
- decide that Memory, LCE, and current-turn Body have different authority;
- choose experiments that could falsify attractive representations;
- reject raw points, exclusive clusters, H1/TDA authority, and unlimited
  recursive cognition when evidence was insufficient;
- authorize bounded implementation scope and stop unauthorized expansion;
- dispatch agents for implementation, research, and independent review;
- compare claims against source, tests, Git ancestry, and runtime evidence;
- decide that a green report was a candidate, reject, repair, readiness gate,
  or closure—not let the report decide that for itself;
- require reviewer discoveries to become permanent deterministic tests.

### LLM contributions

LLMs supplied substantial execution leverage:

- implementation of the V1 pipeline and bounded seams;
- source and artifact inspection across a large repository surface;
- local experiment execution and quantitative comparison;
- independent adversarial probes and re-audits;
- review of repair diffs against original runtime paths;
- drafting technical and historical documentation.

The LLMs were powerful at breadth, iteration, and finding counterexamples. They
were not the final authority for what the project meant, what was in scope, or
whether a release gate was actually satisfied.

## Which reviewer strategies were worth the token cost?

### High-value strategies

- Start with a fresh reviewer who treats implementation reports as untrusted.
- Reproduce the exact runtime symptom with a newly authored deterministic
  corpus.
- Vary legal component behavior, especially the bounded interpreter.
- Inject faults before and after every meaningful durable boundary.
- Compare complete normalized durable state, not only final text or exit code.
- Test subsets, reordered selections, invalidation, restart, and historical
  cutoffs.
- Keep a known-broken base so RED can be reproduced independently.

### Lower-value repeated strategy

Repeating a broad architecture review from scratch after every repair had poor
marginal economics. Once the authority boundary and prior controls were
verified, the better review was narrow: inspect the changed call path, rerun
the permanent suite, and add only the new adversarial permutation or legal
behavior that remained uncovered.

## What should be automated earlier next time?

1. **Release evidence ledger.** Record exact HEAD, branch, clean/dirty state,
   test counts, tool versions, and artifact hashes automatically at each gate.
2. **Fault-point inventory.** Generate the recovery matrix from the durable
   stage definitions so new stages cannot be added without a corresponding
   before/after injection point.
3. **Interpreter behavior contracts.** Include package-sensitive and
   previous-Baseline-sensitive interpreters in the first recovery suite.
4. **Permutation generators.** Generate oldest/middle/newest and reordered
   selected support cases instead of relying on one convenient recap fixture.
5. **Identity audit.** Require every persisted identity to declare whether it
   serves provenance, deduplication, support qualification, or physical
   addressing.
6. **Release boundary checks.** Automatically assert that a documentation or
   release commit changes no `src/lce/**` or `tests/**` paths unless explicitly
   authorized.

## Where LLM leverage was strongest

LLMs were most valuable where the search space was broad but the acceptance
criterion could be made explicit:

- scanning research artifacts for contradictions and predecessor relations;
- proposing independent probes against a written invariant;
- tracing a persisted identity through multiple runtime layers;
- exercising many recovery injection points;
- comparing source, report, and Git evidence without relying on one summary;
- turning accepted history into readable technical documentation.

They were less trustworthy when asked to infer authority boundaries from a
plausible architecture or to treat a passing reference path as universal.
Those tasks required explicit contracts and human review.

## Where human judgment remained indispensable

The key judgments were semantic and organizational:

- deciding what counts as evidence versus derived interpretation;
- deciding that a useful experiment was still not production authority;
- choosing to stop at bounded higher-order behavior;
- recognizing that the same support fingerprint can leak through multiple
  representations;
- refusing to call 74, 85, 93, or 135 green tests “closure” after independent
  rejects;
- deciding that MR integration was outside standalone V1 rather than using it
  to inflate the product claim.

## Final professional takeaway

The strongest portfolio signal is disciplined uncertainty management. The
project used LLMs heavily, but its difficult work was discovering the correct
problem boundary, constructing experiments that could falsify attractive ideas,
separating authority from derived structure, selecting invariants, and forcing
generated implementation to satisfy them under restart and adversarial review.

## Frozen result and limits

Final gates recorded for implementation HEAD `808b148...`:

```text
139 full-suite tests
14 closure invariants
32 recovery tests
30/30 normalized recovery matrix
21 retained regressions + E2E
mypy clean
Ruff clean
isolated exact-HEAD install/import/smoke passed
```

V1 does not claim AGI, personhood, autonomous truth judgment, production
semantic-model quality, unlimited recursive cognition, MR/Body integration, or
solved higher-order precision. Future work remains embedding/model quality,
threshold tuning, higher-order precision, future MR/Body integration, and
performance optimization.
