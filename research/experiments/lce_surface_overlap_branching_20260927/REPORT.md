# LCE Surface Overlap / Branching Pressure Test

Date: 2026-09-27
Branch: verification/lce-surface-overlap-branching-20260927
Base: line-to-surface branch f221c776bda3e006a2cff988d5bd0f241de501e6

## Question

The previous Line -> Surface experiment showed that semantically distant Lines can form a higher-order Surface when their trajectory shapes match. This pressure test asks whether that idea survives three less tidy conditions:

1. the same trajectory is represented with different numbers of states;
2. only one branch of a multidimensional Worktree belongs to a Surface;
3. one Line legitimately participates in multiple Surfaces.

The experiment deliberately does not assign abstraction levels or exclusive cluster membership.

## Representation under test

The comparison unit is a reproducible RelationView:

    owner Line / Worktree
        -> derived branch or relation view
        -> higher-order comparison
        -> Surface

A RelationView is derived cognition, not Raw Evidence. Its authority still closes through the projection graph to the underlying Raw Evidence.

Within one Surface, two views owned by the same Line are not allowed to count as two independent directions. Across different Surfaces, however, the same Line may participate through different relation views.

## Result 1 — different-length Lines can express the same trajectory

The same piecewise-linear trajectory was represented with:

    4 states
    7 states
    13 states

After arc-length resampling, pairwise trajectory-shape similarities were effectively 1.0 and one Surface was discovered over all three Lines.

This supports a necessary invariance:

    number of stored states != semantic identity of the trajectory

A mature Line should not fail higher-order matching merely because one domain generated more intermediate SemanticBlocks than another.

Arc-length resampling is only an experimental operator. It is not frozen as production policy.

## Result 2 — only the matching Worktree branch enters the Surface

A synthetic Worktree had a shared trunk and two branches:

    trunk
      |- branch A
      `- branch B

Branch A matched the engineering and writing trajectories:

    similarity ~= 1.0

Branch B diverged:

    similarity ~= 0.8122

The emitted Surface contained:

    strategy_branch_a
    engineering_u
    writing_u

and did not contain strategy_branch_b.

Most importantly, the Surface Raw closure included the shared trunk Raw Evidence plus branch-A Raw Evidence, but none of the branch-B-only Raw Evidence.

This supports a stronger boundary than 'a Worktree belongs to a Surface':

    a specific reproducible branch/relation view participates in a Surface

The sibling branch remains available for other interpretations and higher-order relations.

## Result 3 — one Line can participate in two Surfaces

A single trading Line exposed two different reproducible relation views:

    trade_view_u
    trade_view_f

The two view shapes were intentionally different:

    cross-pattern similarity = 0.8996887

Two separate Surfaces emerged:

    Surface U:
      line_engineering
      line_trading via trade_view_u
      line_writing

    Surface F:
      line_learning
      line_product
      line_trading via trade_view_f

The trading Line therefore had Surface membership count = 2.

No exclusive assignment was required.

## Result 4 — overlap does not fabricate independent evidence

Both Surfaces ultimately depend on the same 13 Raw Evidence items from the trading Line.

The intersection of the two Surface Raw closures was exactly those 13 trading Raw IDs and nothing else.

So overlap is represented as shared dependency/provenance, not duplicated evidence.

This preserves the authority invariant:

    multiple higher-order uses of one Line
    != multiple independent evidence sources

## Result 5 — one Surface cannot count two views from the same Line as two directions

Surface discovery rejects candidate groups that would use two RelationViews from the same owner Line as separate members of one Surface.

This matters because multi-view representation increases expressive power, but must not create fake cross-direction support.

The current experimental rule is:

    same owner may participate in many Surfaces
    but at most once inside a single Surface candidate

This is a structural-independence constraint, not a semantic category.

## Verification

Final code head before this report: 1f3437a93e0ae1f77f764305eddb11e716575f2e

- LCE Surface Overlap Branching run 36322933472: PASS
- focused pressure tests: 8 / 8 passed
- Public Verification run 36322933565: PASS
- canonical repository test suite at this stage: 207 passed
- mypy: PASS
- ruff: PASS

Two intermediate CI failures were non-algorithmic: one list-order assertion and one malformed test import introduced while formatting the test file. Both were corrected without changing the experiment operator or measured results.

## What this supports

The combined Surface experiments now support the following structural interpretation:

    Raw Evidence
        -> SemanticBlocks / Point Cloud
        -> Line / Worktree
        -> reproducible branch or relation views
        -> overlapping higher-order Surface projections

This is different from hierarchical clustering.

A Worktree can expose multiple branches. A Line can expose multiple relation views. Those views may participate in zero, one, or several higher-order structures.

The resulting geometry is therefore naturally:

    local
    overlapping
    branch-aware
    provenance-preserving
    non-exclusive

rather than a partition of cognition into fixed categories.

## What this does not prove

It does not prove:

- that arc-length resampling is the correct production trajectory comparator;
- robustness to real SemanticBlock embedding noise;
- handling of missing or uncertain logical-time positions;
- natural discovery of which relation view should be projected from a mature Line;
- production handling of nonlinear branch merge/rejoin;
- how Surface projections should be rendered into natural-language callable cognition;
- how many independent Lines are sufficient for a Surface.

The synthetic shapes are falsification fixtures, not a proposed ontology.

## Next pressure tests

The next useful layer is no longer exclusive-vs-overlap. The remaining risks are:

1. irregular dual-time histories: late evidence inserted into the middle of a Line should be able to create, revise, or dissolve a Surface without future leakage;
2. noisy and partially missing trajectories: the relation should survive moderate missing states without turning every vaguely similar Line into a Surface;
3. branch merge/rejoin: two competing Worktree branches may later converge while preserving their historical provenance;
4. callable semantic projection: replace synthetic relation-shape tokens with an actual compiled semantic description and test whether Body retrieval remains precise.
