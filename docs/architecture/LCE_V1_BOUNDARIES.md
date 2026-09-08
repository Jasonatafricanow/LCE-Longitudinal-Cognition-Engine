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

## Explicit non-goals

LCE V1 does not implement MR integration, Body integration, C10, Persona,
Agent identity, Intent, ActionPolicy, RuntimeBinding, MR Scope, current-turn
reasoning, or action execution. The consumer decides how accepted
Understandings are used.

LCE V1 does not make an exclusive cluster ontology, a complex knowledge graph,
TDA/H1 authority, an embedding leaderboard, or recursive cognition beyond
`structure -> higher-order candidate`.

## Authority and provenance

Raw Evidence is not a cognition point. Only canonical Semantic Blocks enter the
vector projection. A derived vector, structure, candidate, worktree, or
Baseline revision cannot write itself back as canonical evidence. Every
higher-order candidate can expand through supporting structures to Semantic
Blocks and then to source evidence IDs.

An accepted Baseline is a current LCE revision, not an eternal objective truth.
Its history remains immutable; its HEAD is filtered out by the read API when a
supporting source is no longer current-valid.
