# LCE Trajectory Runtime V1

Status: V1 production runtime.

Development branch: `feature/trajectory-runtime-v1-20260927`

This document records the production structure implemented after the 2026-09-27
Path-B / Line / Surface experiments and the subsequent production-hardening
audit. It distinguishes structural contracts that
are now implemented from scoring/operator choices that remain replaceable.

## 1. Evidence authority

Only Raw Evidence is an independent **factual** evidence authority.

Persisted Line membership and edges are nevertheless reusable **derived
structural authority** once admitted. Ordinary runtime consumers use that
compiled structure directly; they do not reopen historical Raw Evidence to
re-prove the same accepted relation on every read or nearline turn.

Raw Evidence remains authoritative for provenance, audit, explicit
invalidation/revision, contradiction handling, and derivation rebuild. Reusing
a persisted Line relation therefore does not turn the Line itself into new
factual evidence.

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

Each immutable SemanticBlock state also carries its own `derived_known_at`:
the knowledge time at which that particular interpretation/state revision was
materialized. State visibility at cutoff `T` therefore requires both
`derived_known_at <= T` and cutoff-valid source dependencies. Old Raw Evidence
does not backdate a later reinterpretation into history.

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

A branch is allowed to remain a branch indefinitely. Branch age, node count,
wall-clock duration, or geometric length do **not** create an obligation to
split it into a new Line. The consumer boundary is already local and bounded:
querying one part of a large Line does not mean serializing the whole Line into
context. Storage/index scale is therefore an indexing concern, not a cognitive
identity rule.

A new Line is justified only when discovery identifies an independently
supported logical structure. It is not a lifecycle promotion for an old branch.

The store rejects:

- cross-Line edges;
- cycles;
- redundant transitive shortcut edges.

## 5. Line identity admission

`LineAssembler` remains deliberately conservative, but persistent identity is
now gated by decentralized evidence convergence rather than by overlap count or
cosine score alone.

Bootstrap identity admission and ordinary nearline relation admission are
different questions.

For bootstrap identity, a trajectory can:

- seed a new Line only when the proposed path has enough **independent Raw
  Evidence components** to certify the seed;
- inherit one existing Line when its cutoff-valid shared support is the unique
  eligible Pareto-undominated candidate;
- remain unresolved when multiple *identity* candidates have incomparable/equal
  support.

There is no weighted confidence score and no "best similarity wins" fallback
for those exclusive identity decisions.

Once a Line relation has been admitted and persisted, ordinary nearline growth
does not run another identity election between matching Lines. Each candidate
Line is evaluated independently for a new local relation using bounded ordered
witnesses from the already-compiled Line structure. If the relation is valid
for two Lines, the SemanticBlock may participate in both.

`LineAssembler` still refuses to auto-merge Lines. Multi-membership is not a
Line merge and does not clone identity.

Historical nodes whose underlying Raw Evidence is not valid at the requested
knowledge cutoff remain auditable but do not contribute to Line identity
matching at that cutoff.

Branch growth therefore does not imply Line cloning, while overlapping Line
membership remains legal. A long-lived branch remains internal topology unless
a separate independently supported structure is actually discovered and
admitted as another Line.

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

Interrupted rebuild recovery is identity-preserving. The durable
`rebuild_in_progress` marker stores the exact failed rebuild cutoff. On
restart, LCE must restore that cutoff first so prior Line identity can be
inherited under the same membership-revision semantics, then reconcile forward
to current source state. Both phases complete before new ingestion is compiled.
The marker remains set across the whole recovery sequence, so another hard
failure cannot expose an intermediate generation as current.

This distinction also governs **derived-cognition correction**. Historical
visibility does not imply current validity. If an accepted Line relation or
interpretation is later explicitly rejected as a reasoning error, the current
derived graph must be able to retire that relation and rebuild/roll back to the
last still-supported structure while retaining the old revision for audit.
Raw Evidence is not deleted merely because the derived relation was wrong.

Source-driven invalidation/rebuild is implemented in V1. A dedicated
relation-level correction ledger that can persist an explicit negative
constraint ("do not regenerate this rejected relation from the same support")
is an architectural requirement for the correction path and remains a
post-V1 control-plane implementation item.

If a SemanticBlock keeps the same stable `block_id` but a later immutable
state invalidates one or more existing relations, LCE first retires/revalidates
that membership's incident relations locally. Unrelated Line topology and
nearline-only growth remain current. A broader Line/global rebuild is reserved
for cases that cannot be repaired locally or for derivation-generation changes.
Stable node identity does not freeze stale temporal edges.

## 7. Callable Line projection

`CallableLineProjector` materializes a bounded, ephemeral local view around the
Line node most relevant to the current SemanticBlock.

The view is graph-distance bounded and preserves exact state and Raw provenance.

Exact Raw provenance closure uses iterative traversal rather than recursive DFS,
so long-lived deep Lines are not constrained by Python recursion depth. The
closure has an explicit node safety ceiling, but the ceiling is fail-closed:
if the traversal cannot finish exactly, LCE raises
`LineTraversalLimitExceeded` instead of returning truncated provenance.

Root-to-frontier path enumeration follows the same rule. `max_nodes` and
`max_paths` are resource safety ceilings, not hidden semantic windows. If an
exact path or exact path set cannot fit inside those ceilings,
`paths_to_frontier` raises `LineTraversalLimitExceeded`; it never returns a
truncated suffix/subset as though it were the complete Line shape. Surface
discovery treats that failure as local to the affected Line: that Line is
skipped, its incomplete path is never scored, and other complete Lines may
still produce candidates. The public Surface result marks itself partial and
reports skipped Line IDs/reasons. When any Line is skipped, candidate-set and
ranking completeness are explicitly false because omitted Lines could have
changed maximal cliques or bounded candidate ordering.

It is not inserted as a persistent cognition node.

`LceProjectionCore.callable_line_projections(...)` exposes all bounded views
for stable Lines already touched by the current SemanticBlocks.

This consumption boundary is intentionally narrower than global semantic
recall. Structural proposal and consumer injection are separate concerns.

## 8. Proactive Inspiration Material

Stable Lines and unresolved local trajectory proposals can now feed an explicit
proactive-consumption product without exposing LCE internals downstream.

The public object is intentionally only:

```text
material_id
content
```

Internally V1 supports two inspiration paths:

```text
unresolved local trajectory
    -> possible-association material

stable Line prefix A -> B -> C
    -> bounded semantic interpreter
    -> speculative D?
    -> extension material
```

The extension path preserves the authority split explicitly: the Line prefix is
supported derived structure while `D` remains speculative. The deterministic
reference interpreter does not invent a concrete extension; a deployment may
inject a bounded semantic interpreter after structural discovery.

Inspiration discovery is explicit and is not run automatically on every
nearline input. It is intended for sleep/daydream/dream or another bounded
background scheduler.

See `LCE_INSPIRATION_MATERIAL_V1.md`.

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
It compares the current compiled block(s) with already-stable Line nodes,
proposes matching Lines, and performs independent bounded relation admission
against each matching Line. Existing Line authority is reused rather than
re-derived from Raw closures on every turn.

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
branch age/length != automatic Line split
state revision != new trajectory point
weak overlap != exclusive ownership
one SemanticBlock may support multiple Lines
Surface membership != independent support
rejoin != history rewrite
relation rebuild != history rewrite
history retention != current validity
derived correction != Raw Evidence deletion
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
- a durable relation-level correction/negative-constraint ledger so an
  explicitly rejected derived relation does not immediately regenerate from the
  same unchanged support;
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
