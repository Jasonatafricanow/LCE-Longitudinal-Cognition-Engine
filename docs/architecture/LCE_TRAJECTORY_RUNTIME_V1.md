# LCE Trajectory Runtime V1

Status: V1 production runtime.

Development branch: `feature/trajectory-runtime-v1-20260927`

This document records the production structure implemented after the 2026-09-27
Path-B / Line / Surface experiments and the subsequent production-hardening
audit. It distinguishes structural contracts that
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

The knowledge-cutoff API makes late-known historical evidence invisible before
it is known, then allows it to be placed at its original logical time in later
reconstruction. Standalone persistence also replays Raw Evidence lifecycle
events as of the requested knowledge cutoff: evidence invalidated in 2026 may
still appear in a 2023 epistemic replay if it was known and not yet invalidated
in 2023. "Known later to be wrong" therefore does not rewrite what was knowable
earlier.

Immutable SemanticBlock-state vectors are retained across later source
invalidation so historical replay remains rebuildable. Current default vector
lookup still excludes currently invalid blocks.

An external canonical source may optionally provide the same historical
`evidence_valid_at` capability. If it exposes only current lifecycle state,
LCE falls back conservatively to current validity and does not pretend to offer
exact historical lifecycle replay.

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
- bounded overlapping path enumeration;
- overlapping continuation segments when one trajectory exceeds the configured
  per-path node bound, so the bound does not silently discard the tail.

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

Because that is a strong semantic commitment, automatic Line growth does not
infer a second parent from vector similarity alone. Conjunctive rejoin is
disabled by default and must be explicitly authorized through the assembler
configuration until a real semantic rejoin criterion exists.

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

`LineAssembler` remains deliberately conservative, but persistent identity is
now gated by decentralized evidence convergence rather than by overlap count or
cosine score alone.

A trajectory can:

- seed a new Line only when the proposed path has enough **independent Raw
  Evidence components** to certify the seed;
- inherit one existing Line when its cutoff-valid shared support is the unique
  eligible Pareto-undominated candidate;
- remain unresolved when multiple stable Lines have incomparable/equal support.

There is no weighted confidence score and no "best similarity wins" fallback.
Cross-dimension tradeoffs stay `UNKNOWN`. Repeated derived projections and
transitively overlapping Raw closures cannot manufacture additional independent
support.

`LineAssembler` still refuses to auto-merge Lines. A convergence result may
authorize which existing identity a path inherits, but it cannot merge two Line
identities. Weak overlap is not exclusive ownership: one SemanticBlock may
legitimately participate in multiple local Lines.

Historical nodes whose underlying Raw Evidence is not valid at the requested
knowledge cutoff remain auditable but do not contribute to Line identity
matching at that cutoff.

Branch growth therefore does not imply Line cloning, while overlapping Line
membership remains legal.

## 6. Knowledge-cutoff Line view

`LineGraphView` selects the latest immutable SemanticBlock state that is both:

- known by the requested knowledge cutoff; and
- supported by Raw Evidence that was valid at that same knowledge cutoff when
  the source substrate can replay historical lifecycle state.

Visibility propagates through graph ancestry using conjunctive parent
dependency for multi-parent rejoin nodes. Visibility evaluation and provenance
closure are iterative, so deep long-lived Lines do not depend on Python
recursion depth.

Consequences:

- a later invalidation does not erase what was visible before that invalidation;
- current reconstruction can retire prior Line membership/edge revisions and
  compile replacement relations without deleting historical revisions;
- invalidating a rejoin source hides the rejoin and its descendants in the
  current reconstruction;
- prior branch frontiers become current again automatically;
- a late-known historical state does not leak into an earlier knowledge cutoff.

Line membership and Line edges are themselves knowledge-time revisioned. A
relation has a `known_at -> retired_at` lifetime. Rebuild therefore means
"retire the current derived relation and compile another revision", not "rewrite
the old graph in place".

If a SemanticBlock keeps the same stable `block_id` but a later immutable state
changes its logical interval enough to invalidate existing ordering, the current
Line graph is rebuilt. Stable node identity does not freeze stale temporal
edges.

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

Surface discovery is disabled unless a `SurfaceConfig` is explicitly
supplied, and it is not part of the per-turn nearline path.

A branch path is used only as the geometric view. Its evidence authority closes
over the endpoint's complete conjunctive Raw ancestry, so a single displayed
root-to-frontier route cannot omit another parent required by an AND-rejoin.

The structural constraints are implemented. The current shape comparator and
threshold are not treated as proven production semantics and remain replaceable.

## 9. Runtime integration

The Point-Cloud bootstrap and nearline growth paths are intentionally separate.

Nearline `process()` does **not** rescan the whole SemanticBlock history.
It compares the current compiled block(s) with already-stable Line nodes to
propose candidate Lines, then evaluates source-grounded local support.

Every Line above the semantic proposal threshold competes. The highest cosine
score does not become the identity authority. Each candidate is represented by
the cutoff-visible local Line states that also clear the proposal threshold.
The runtime then either:

- attaches to one uniquely converged Line;
- creates a branch/rejoin inside that Line;
- or stops unresolved when source-grounded identity remains ambiguous.

```text
new Raw Evidence
    -> Semantic compiler
    -> vector projection
    -> current block vs existing Line retrieval surface
    -> all threshold-qualified Line candidates
    -> decentralized Raw-Evidence convergence
    -> conservative Line growth / UNKNOWN
```

Full mutual-kNN Point-Cloud discovery is a slow path:

```text
accumulated SemanticBlocks
    -> explicit bootstrap_trajectory()
       or one bootstrap at the end of run_batch()
    -> overlapping trajectory proposals
    -> decentralized Raw-Evidence convergence
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

A custom neighbour provider whose internal behavior can change independently of
its Python class should expose a stable `derivation_fingerprint`. That value
participates in the persisted Line derivation fingerprint, so changing the
provider implementation/version cannot silently reuse graph revisions compiled
under older neighbour semantics.

Surface discovery is a higher-order slow-path operation. Supplying a
`SurfaceConfig` makes the operator available but does not make every nearline
turn rescan all Lines. Batch processing may run Surface discovery after the
trajectory bootstrap; callers can otherwise invoke the Surface runtime
explicitly.

Surface candidate enumeration uses maximal cross-Line cliques only and has
fail-closed view/search/candidate safety bounds. Hitting a bound raises rather
than returning an apparently complete partial candidate set.

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
idempotent because Line nodes, immutable block states, membership revisions, and
edge revisions have stable identities.

Every current membership/edge revision records a Line derivation fingerprint
covering the embedding version, trajectory config, assembler policy, and
neighbour-provider identity/version. If that fingerprint changes, LCE rebuilds
vectors and compiles a new current graph revision instead of silently treating
an old graph as if it came from the new algorithm. Historical revisions retain
their old fingerprint.

Before that explicit rebuild completes, Line consumer reads fail closed with
`StaleLineGraphError`. Read APIs do not silently rebuild or mutate the graph.
Restarting with the same derivation fingerprint reuses the existing current
revision without manufacturing a new one.

Bitemporal-divergent input (`known_at != occurred_at`) is compiled into the new
trajectory path but is not sent through legacy Frontier/06R cognition
evaluation. Once any source in a compiler lineage becomes bitemporal-divergent,
the legacy cognition path remains closed for that lineage, including later
ordinary inputs and source-rebuild flows. Re-enabling that path requires a
future explicit forward replay of all affected legacy snapshots; a later
ordinary input is not enough.

This avoids inserting a new logical-history snapshot into the old Baseline path
and then accidentally treating the retroactive evidence as a newly emerged
structure at some later cutoff.

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
weak overlap != exclusive ownership
one SemanticBlock may support multiple Lines
Surface membership != independent support
rejoin != history rewrite
relation rebuild != history rewrite
invalid historical node != cutoff-valid identity support
derivation fingerprint mismatch != reusable current graph
stale Line graph != readable Line graph
legacy lineage after retroactive evidence != safe legacy replay
known_at controls visibility
occurred_at controls logical placement
similarity proposes != similarity authorizes
derived replay != independent evidence
overlapping Raw closure != independent vote
cross-dimension tradeoff != scalar tie-break
```

UNKNOWN remains a legal outcome whenever identity or structure is
underdetermined.

## 11. Post-V1 replaceable operators / research

The following are intentionally not frozen:

- embedding-specific k and similarity thresholds;
- an ANN/multi-anchor index for sub-linear existing-Line routing at very large scale;
- the final production local-continuity proposal operator;
- a semantic relation supplier for explicit support/contradiction signals;
- a semantic criterion for declaring branch convergence; until then,
  conjunctive rejoin requires explicit authorization and is off by default;
- the branch-to-independent-Line transition policy;
- real-data calibration of Surface shape comparison and search bounds;
- richer logical-time representation for intervals, relative order, partial
  order, and UNKNOWN;
- whether/when optional Surface candidates should be compiled into natural
  language consumer projections;
- retirement of the legacy 06R/Frontier compatibility path.

These are deliberately outside the V1 structural authority boundary. They can be
replaced or calibrated without changing Raw-Evidence authority, stable Line identity,
knowledge-cutoff replay, or the branch/provenance invariants above. They should be
challenged with held-out real data before any of them is promoted into stronger
automatic authority.

## 12. Verification

The branch has focused production tests for:

- knowledge-time visibility and late historical evidence;
- stable Line identity under immutable state revision;
- overlapping Line membership without clone-by-default behavior;
- branch/rejoin and rollback after Raw invalidation;
- current Line relation rebuild while preserving historical relation replay;
- logical-time state revision invalidating stale ordering edges;
- same-cutoff rebuild retry after partial relation retirement;
- derivation-fingerprint rebuild across embedding/config/provider changes;
- same-fingerprint restart without spurious Line revision;
- stale Line read rejection before explicit rebuild;
- lineage-level legacy shutdown after retroactive evidence;
- cycle and transitive-edge rejection;
- bounded non-persistent callable projections;
- local-drift trajectory recovery;
- no forced ordering for same-time states;
- current-turn relevance filtering;
- different-length cross-Line Surface discovery;
- Surface Raw closure and invalidation rollback.

The canonical repository verification gate plus focused bitemporal, Line-graph,
trajectory, and Surface tests are required for this runtime. The focused
`.github/workflows/trajectory-runtime-v1.yml` workflow remains available for
trajectory-runtime branches.
