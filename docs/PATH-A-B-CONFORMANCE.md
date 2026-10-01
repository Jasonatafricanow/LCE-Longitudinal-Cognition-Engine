# Path A / Path B conformance (#49)

Authority: MR-Mem ADR-0001 at `fbf96dd`; accepted semantics precede LCE.
Public baseline: `cc72a21`, 290 tests passed before changes.

## Reproduced failures and fixes

- There was no accepted-SemanticBlock entry point. `process_semantic` now reads
  immutable accepted states from the injected substrate and never calls the raw
  SemanticCompiler. Its projection receipt is not a canonical Raw Evidence row.
  Historical snapshots use derived known_at while trajectory orientation retains
  occurred_at. The old raw compiler remains a standalone/reference adapter.
- Two fragments of one source plus repeated snapshots promoted a Baseline.
  Conservative promotion now checks independent sources of selected immutable
  states against its existing support floor. Frontier updates retain their
  existing policy; a new frontier boundary cannot bypass source independence.
- An OPEN Path A draft with new support was reconciled to an older, text-identical
  Baseline. Recovery now requires both content and support equivalence, including
  selected immutable states. A superseded merged receipt fails closed instead of
  rewriting the current HEAD from an old replay.
- External intake had no rejection check. Composition can now supply the durable
  rejection store. Unchanged closure stays rejected, including after restart;
  new source closure can produce an actual support revision without erasing the
  earlier rejection. Semantic handoff requires exact current state selection and
  validates content/source closure against the semantic substrate.
- Path A audit also reproduced MR-Mem Thread recreation after retirement and
  keyword-based merging of different questions. Companion fixes in MR-Mem PR #6
  retain handoff receipts and use the accepted canonical question identity.

## Behavioral coverage

| Attack | Evidence |
| --- | --- |
| Isolated accepted block | `test_accepted_semantic_runtime`: visible point, no compiler receipt, no Baseline |
| Similar unrelated points | same suite: proximity cannot promote without an explicit bounded interpreter |
| Prepare down payment -> paid -> loan pending | `test_native_thread_conformance`: one actual MR-Mem Thread with explicit accepted question identity |
| Mature Thread -> accepted equivalent understanding | same suite: exact block/state IDs, source times and relationships retained; Thread retires only after acceptance |
| Crash after Baseline commit | same suite: retry reconciles one revision; post-retirement replay cannot recreate Thread |
| Rejection -> restart -> new source | `test_precomputed_external`: actual intake/consolidation, new support revision, rejection history retained |
| Duplicate source fragments | `test_promotion` and `test_trajectory_authority_runtime`: cannot mature Baseline or seed Line |
| Cross-session identity/replay | `test_accepted_semantic_runtime`: explicit bootstrap seeds Line, IDs/node count survive restart/replay |
| DAG branches/rejoin/revision/invalidation | existing `test_line_graph_runtime`, run fresh as part of the complete gate |
| DROP/noise exclusion | host Cleaner #51 tests: no canonical semantics and no downstream consumer call; LCE accepted entry reads existing canonical IDs only |

## Limits and composition requirements

The accepted entry requires an explicitly supplied semantic embedder. It does not
silently use token-hash geometry. Fixture vectors exercise structural behavior;
they are not evidence of a configured production embedding model. Without an
explicit bounded interpreter, geometry produces structural candidates only,
never a fabricated understanding. The reference interpreter is retained solely
for the legacy raw/reference path.

Nearline trajectory processing attaches to existing Lines. Historical seeding
uses explicit bootstrap; similarity alone neither seeds independent authority nor
matures a Baseline. Thread identity must be stable in the accepted upstream
semantic output; paraphrase resolution is not replaced by keyword overlap.

Canonical accepted semantics still belong to the host/MR-Mem. The host adapter,
incremental source edit/delete synchronization, normal-turn invocation and next-
turn context assembly are Mind-Runtime #49, not a second LCE source database.
Broader production semantic quality and held-out vector behavior remain unproven.

## Validation

`python scripts/verify.py`: 299 passed; mypy clean in 44 source files; Ruff clean.
MR-Mem companion gate: 34 passed and Ruff clean. Verification installs its exact
MR-Mem commit as a test dependency; LCE runtime has no MR-Mem import dependency.
No default branch merge, release tag, private transcript or production DB write.
