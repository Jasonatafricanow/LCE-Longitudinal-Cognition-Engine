# LCE V1 Boundaries

## Ownership

Reference Memory owns:

- canonical Raw Evidence content and stable IDs;
- source/provenance metadata;
- validity, invalidation, and supersede history;
- the current-valid evidence view;
- the anti-pollution boundary between canonical evidence and derived cognition.

LCE owns:

- Semantic Blocks compiled from authorized evidence;
- derived vectors, local structures, snapshots, and diffs;
- higher-order candidates and their provenance expansion;
- OPEN/MERGED/DROPPED cognition worktrees;
- accepted Understanding Baseline revisions and the read API.

The runtime consumes these capabilities through focused Reference Memory
ports. `ReferenceMemoryStore` is only the default standalone implementation;
an injected backend may own the same canonical validity state elsewhere. LCE
does not reinterpret invalidation as a truth decision.

## Explicit non-goals

LCE V1 does not implement MR integration, Body integration, C10, Persona,
Agent identity, Intent, ActionPolicy, RuntimeBinding, MR Scope, current-turn
reasoning, or action execution. The consumer decides how accepted
Understandings are used.

LCE V1 does not make an exclusive cluster ontology, a complex knowledge graph,
TDA/H1 authority, an embedding leaderboard, or recursive cognition beyond
`structure -> higher-order candidate`.

LCE V1 also does not claim to reconstruct the correct reasoning order from
arbitrary unordered evidence. Removing temporal order and asking the system to
infer the hidden logic is a broader general-reasoning problem, not a required
proof of longitudinal cognition.

## Authority and provenance

Raw Evidence is not a cognition point. Only canonical Semantic Blocks enter the
vector projection. A derived vector, structure, candidate, worktree, or
Baseline revision cannot write itself back as canonical evidence. Every
higher-order candidate can expand through supporting structures to Semantic
Blocks and then to source evidence IDs.

An accepted Baseline is a current LCE revision, not an eternal objective truth.
Its history remains immutable; its HEAD is filtered out by the read API when a
supporting source is no longer current-valid.

## Temporal evidence sufficiency

Time does not define Semantic Block identity, but temporal ordering is part of
the evidence used for longitudinal claims.

The distinction is:

```text
semantic continuity -> cognition-unit boundary
temporal ordering   -> sequence / visibility / replay / change / falsification
```

A reliable source timestamp, version order, explicit before/after relation, or
other inspectable ordering evidence may establish temporal placement. If a
source has no explicit timestamp but its relative position can be recovered
reliably, that recovery belongs in the inspectable ingestion/provenance path.

If temporal placement remains underdetermined, LCE must not manufacture a
reasoning trajectory merely because one plausible ordering can be imagined.
The evidence may remain useful as ordinary source material, but it cannot
support claims about emergence, transition, supersession order, or longitudinal
trajectory until temporal placement is sufficiently established.

This is the **Temporal UNKNOWN** boundary:

```text
temporal position UNKNOWN
  -> no longitudinal trajectory / evolution claim
```

Standalone V1 does not claim a universal automatic temporal-reconstruction
engine. Missing-time handling can be an import/integration policy, but the
longitudinal authority rule remains fail-closed.

## Semantic UNKNOWN and higher-order stopping

A different UNKNOWN state exists after temporal placement is already adequate.
LCE may observe cutoff-bound structural change such as stability, reconnection,
growth, loss, overlap, or reorganization without having sufficient evidence to
name the higher-order cognition that the change represents.

In that case:

```text
observed temporal / structural pattern
  -> bounded higher-order candidate
  -> UNKNOWN derived proposal
```

`UNKNOWN` is a valid stopping point. A persistent pattern may justify attention
without authorizing semantic certainty.

This is the **Semantic UNKNOWN** boundary. It must not be conflated with
Temporal UNKNOWN:

- **Temporal UNKNOWN** — the system cannot place the evidence reliably enough
  to construct a longitudinal trajectory;
- **Semantic UNKNOWN** — the system can observe an ordered pattern but cannot
  justify what higher-order meaning it has.

The first forbids a trajectory claim. The second preserves the trajectory/
structure observation while forbidding an unsupported meaning claim.

## Scope-control rule

A product constraint should not be removed merely to force LCE to demonstrate a
more general intelligence capability. Long-running interactions, events,
decisions, versions, and memory records are normally ordered inputs. Their time
structure is legitimate domain information.

Testing whether a model can recover a plausible logic from deliberately
unordered evidence is valuable as a separate reasoning research program, but
crossing that boundary changes the question from longitudinal cognition to
open-ended causal/logical reconstruction.

See [`../ENGINEERING_CHALLENGES_AND_BOUNDARIES.md`](../ENGINEERING_CHALLENGES_AND_BOUNDARIES.md)
for the broader engineering challenge matrix and the two UNKNOWN boundaries.
