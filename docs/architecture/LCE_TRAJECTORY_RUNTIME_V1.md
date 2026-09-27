# LCE Trajectory Runtime V1

Status: implementation branch, not merged to master.

Branch: `feature/trajectory-runtime-v1-20260927`

This document records the production structure implemented after the 2026-09-27
Path-B / Line / Surface experiments. It distinguishes structural contracts that
are now implemented from scoring/operator choices that remain replaceable.

## 1. Evidence authority

Only Raw Evidence is an independent evidence authority.

Derived structures may be reused as computation and retrieval objects, but they
never become new factual support merely because they are recalled, nested, or
consumed.

The authority chain remains:

```text
Raw Evidence
    -> SemanticBlock state
    -> Line node / Worktree structure
    -> callable projection
    -> optional Surface candidate
```

Every consumer-facing projection retains exact immutable SemanticBlock state
references and Raw Evidence provenance.

## 2. Bitemporal input

`RawEvidence` now carries two distinct times:

- `known_at`: when LCE is allowed to use the evidence;
- `occurred_at`: where the evidence belongs in longitudinal history.

If `known_at` is omitted, it falls back to `occurred_at` for backward
compatibility.

Default ingestion ordering uses `effective_known_at`, while explicit
`ordering_key` remains authoritative.

The new knowledge-cutoff API makes late-known historical evidence invisible
before it is known, then allows it to be placed at its original logical time in
later reconstruction.

The older snapshot/06R compatibility path still uses logical
`occurred_at` cutoffs. It has not been silently redefined as bitemporal.

## 3. Local trajectory proposal

`MutualKnnTrajectorySupplier` is the production counterpart of the A4-R
research direction.

It currently uses:

- local vector cosine similarity;
- top-k neighbours;
- reciprocal/mutual neighbour edges;
- strict logical partial ordering for edge orientation;
- bounded overlapping path enumeration.

It explicitly does not use:

- a global pairwise-cohesion requirement;
- fixed minimum longitudinal span;
- fixed time buckets;
- maximum-age expiry;
- exclusive connected-component ownership.

Same-time or overlapping logical states are left unordered rather than forced
into a synthetic sequence.

The default numerical parameters are operational defaults, not cognitive
authority. They are replaceable and should later be calibrated on held-out real
data.

## 4. Stable Line identity

A Line has one persistent identity.

The persistence model is:

```text
Line
  -> stable SemanticBlock node
      -> immutable state revision(s)
  -> DAG edges
```

A Line node is keyed by stable `block_id`, not by `state_id`. Extending or
recompiling a SemanticBlock therefore creates another immutable node state
revision rather than a fake new trajectory point.

A node may have:

- multiple children: branch/divergence;
- multiple parents: merge/rejoin.

In V1, multiple parents have one narrow meaning: **conjunctive rejoin**.
A multi-parent child remains visible only while every parent ancestry remains
visible. Multiple parent edges do not mean "A OR B" and must not be used for
alternative hypotheses, fallback routes, or mutually exclusive interpretations.

Those unresolved/alternative semantics remain outside the current Line-edge
contract until a distinct relation representation is introduced. This boundary
is intentional: changing the visibility rule from `all(parents)` to
`any(parents)` would silently change rejoin authority.

The public concept remains Worktree/Line even though the internal graph is
DAG-like.

The store rejects:

- cross-Line edges;
- cycles;
- redundant transitive shortcut edges.

## 5. Line identity admission

`LineAssembler` is deliberately conservative.

A trajectory can:

- seed a new Line when it has no overlap with an existing Line;
- extend one existing Line when it has sufficient current-valid shared support;
- remain unresolved when overlap is weak;
- remain unresolved when it overlaps multiple stable Lines.

It does not auto-merge Lines.

Historical nodes whose underlying Raw Evidence is no longer valid remain
auditable but do not contribute to current Line identity matching.

Branch growth therefore does not imply Line cloning.

## 6. Knowledge-cutoff Line view

`LineGraphView` selects the latest immutable SemanticBlock state that is both:

- known by the requested knowledge cutoff; and
- still supported by current-valid Raw Evidence.

Visibility propagates through graph ancestry using conjunctive parent
dependency for multi-parent rejoin nodes.

Consequences:

- invalidating a rejoin source hides the rejoin and its descendants;
- prior branch frontiers become current again automatically;
- historical graph rows are preserved for audit;
- a late-known historical state does not leak into an earlier knowledge cutoff.

## 7. Callable Line projection

`CallableLineProjector` materializes a bounded, ephemeral local view around the
Line node most relevant to the current SemanticBlock.

The view is graph-distance bounded and preserves exact state and Raw provenance.

Exact Raw provenance closure uses iterative traversal rather than recursive DFS,
so long-lived deep Lines are not constrained by Python recursion depth. The
closure has an explicit node safety ceiling, but the ceiling is fail-closed:
if the traversal cannot finish exactly, LCE raises
`LineTraversalLimitExceeded` instead of returning truncated provenance.

It is not inserted as a persistent cognition node.

`LceProjectionCore.callable_line_projections(...)` exposes all bounded views
for stable Lines already touched by the current SemanticBlocks.

This consumption boundary is intentionally narrower than global semantic
recall. Structural proposal and consumer injection are separate concerns.

## 8. Optional Surface discovery

`SurfaceRuntime` is implemented as an opt-in derived operator.

It:

1. enumerates real root-to-frontier branch paths from stable Line DAGs;
2. does not create persistent relation-view cognition nodes;
3. derives a translation-invariant, arc-length-resampled path-shape signature;
4. compares paths only across different owner Lines;
5. permits one Line to participate in different Surface candidates through
   different real branch paths;
6. never counts two branches of one Line as two independent members of one
   Surface;
7. returns the union Raw closure of member paths.

Surface discovery is disabled unless a `SurfaceConfig` is explicitly supplied.

The structural constraints are implemented. The current shape comparator and
threshold are not treated as proven production semantics and remain replaceable.

## 9. Runtime integration

The Point-Cloud bootstrap and nearline growth paths are intentionally separate.

Nearline `process()` does **not** rescan the whole SemanticBlock history.
It only compares the current compiled block(s) with already-stable Line nodes
and either:

- attaches to one unambiguous Line;
- creates a branch/rejoin inside that Line;
- or stops unresolved when Line identity is ambiguous.

```text
new Raw Evidence
    -> Semantic compiler
    -> vector projection
    -> current block vs existing Line retrieval surface
    -> conservative Line growth / UNKNOWN
```

Full mutual-kNN Point-Cloud discovery is a slow path:

```text
accumulated SemanticBlocks
    -> explicit bootstrap_trajectory()
       or one bootstrap at the end of run_batch()
    -> overlapping trajectory proposals
    -> stable Line seeds / branch structure
```

This separation prevents a five- or ten-year Raw/Semantic history from being
rescanned on every conversation turn.

The current nearline router is linear in the number of visible persisted Line
nodes for each current block. It is already substantially cheaper than
all-pairs Point-Cloud discovery, but a future ANN/multi-anchor Line index may
replace that scan without changing the Line/Worktree contracts.

The slow bootstrap neighbour source is already abstracted behind
`NeighbourCandidateProvider`. The zero-dependency
`ExactCosineNeighbourProvider` is the reference O(N²) backend; an ANN/HNSW or
external vector-store adapter can replace it without changing mutual-neighbour
confirmation, trajectory formation, or Line identity rules.

Optional Surface discovery remains disabled unless a `SurfaceConfig` is
explicitly supplied.

The pre-existing V1 path remains intact in parallel:

```text
logical snapshot
    -> Frontier / 06R compatibility discovery
    -> legacy Worktree
    -> Baseline promotion
```

This is intentional. The new trajectory runtime can be pressure-tested without
silently changing accepted Baseline semantics.

Completed pipeline replay does not rerun cognition stages. Partial replay is
idempotent because Line nodes, node-state revisions, and edges have stable
identities.

A nearline system that starts with no Lines is expected to accumulate evidence
until an explicit/periodic bootstrap is run. Nearline traffic alone does not
silently promote a Point Cloud into a new Line.

## 10. Implemented failure boundaries

The implementation currently preserves these invariants:

```text
usage != evidence
projection != fact
branch != new Line
state revision != new trajectory point
Surface membership != independent support
rejoin != history rewrite
invalid historical node != current identity support
known_at controls visibility
occurred_at controls logical placement
```

UNKNOWN remains a legal outcome whenever identity or structure is
underdetermined.

## 11. Still unresolved / replaceable

The following are intentionally not frozen:

- embedding-specific k and similarity thresholds;
- an ANN/multi-anchor index for sub-linear existing-Line routing at very large scale;
- the final production local-continuity score;
- a semantic criterion for declaring branch convergence;
- the branch-to-independent-Line transition policy;
- real-data calibration of Surface shape comparison;
- richer logical-time representation for intervals, relative order, partial
  order, and UNKNOWN;
- whether/when optional Surface candidates should be compiled into natural
  language consumer projections;
- retirement of the legacy 06R/Frontier compatibility path.

These should be challenged with held-out real data before authority is expanded.

## 12. Verification

The branch has focused production tests for:

- knowledge-time visibility and late historical evidence;
- stable Line identity under immutable state revision;
- branch/rejoin and rollback after Raw invalidation;
- cycle and transitive-edge rejection;
- bounded non-persistent callable projections;
- local-drift trajectory recovery;
- no forced ordering for same-time states;
- current-turn relevance filtering;
- different-length cross-Line Surface discovery;
- Surface Raw closure and invalidation rollback.

The canonical repository verification gate is run on every commit to the feature
branch through `.github/workflows/trajectory-runtime-v1.yml`.
