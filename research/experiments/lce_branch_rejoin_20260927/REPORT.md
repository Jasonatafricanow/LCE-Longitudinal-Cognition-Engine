# LCE Branch Merge / Rejoin Pressure Test

Date: 2026-09-27
Branch: verification/lce-branch-rejoin-20260927
Base: 8a0779b54060c11d379b4c8a65ffee4a27435454

## Question

Can one stable Line diverge into multiple branches and later converge again without either rewriting the historical fork or forcing the branches to remain permanently separate?

The experiment also checks two failure modes:

- invalidating the convergence evidence must reopen the prior branches;
- late-known historical convergence must obey knowledge-time cutoff and cannot leak backward.

## Internal shape under test

Worktree remains the public concept, but the structural substrate is allowed to be DAG-like:

    trunk
      |- branch A ----\
      |                -> rejoin -> later continuation
      `- branch B ----/

A rejoin node has multiple parents inside the same Line identity.

This is a structural fixture only. It does not define production semantic criteria for declaring that branches have actually converged.

## Result 1 — divergence and convergence can coexist in one Line

At cutoff 2023 the active frontier was:

    branch_a_3
    branch_b_3
    state = OPEN

At cutoff 2024, after convergence evidence:

    rejoin_4
    state = REJOINED

At cutoff 2025, the Line continued from the rejoin:

    post_5

The Line identity count remained exactly 1 throughout.

The historical graph at 2025 still contained both complete branch histories:

    branch_a_2
    branch_a_3
    branch_b_2
    branch_b_3

plus rejoin_4 and post_5.

Therefore current convergence does not rewrite historical divergence.

## Result 2 — rejoin provenance includes both histories

The Raw closure of rejoin_4 contained:

    shared trunk: t0, t1
    branch A:     a2, a3
    branch B:     b2, b3
    convergence:  r4

The later post_5 continuation strictly extended that closure with r5.

This keeps the convergence falsifiable: the rejoin is derived from the two branch histories plus new convergence evidence, not a replacement for those histories.

## Result 3 — invalidating convergence evidence reopens the fork

Before invalidation at cutoff 2025, the active frontier was post_5.

After invalidating Raw r4:

    rejoin_4 became invisible
    post_5 became invisible because it depends on rejoin_4
    branch_a_3 became active again
    branch_b_3 became active again

The fork history itself remained intact.

This is the desired rollback behavior:

    convergence is a compiled current interpretation
    not an irreversible history rewrite

## Result 4 — late-known historical convergence obeys dual time

A special fixture used convergence evidence with:

    logical_at = 2024
    known_at   = 2026

At cutoff 2025:

    retro_rejoin_4 was invisible
    frontier = branch_a_3 + branch_b_3
    state = OPEN

At cutoff 2026:

    retro_rejoin_4 became visible
    frontier = retro_rejoin_4
    state = REJOINED

So the current 2026 reconstruction can place the convergence logically in 2024 without pretending the system knew it in 2025.

This preserves:

    current corrected reconstruction
    != historical epistemic state

## Result 5 — current convergence and historical divergence remain queryable together

The final 2025 state has a single current continuation while all fork nodes remain historically visible.

Therefore the system can answer two different questions without contradiction:

    What is the current Line frontier?
      -> post-rejoin continuation

    Did the cognition previously diverge?
      -> yes, both historical branches remain in provenance

This is precisely why a strict tree is insufficient internally even though the public abstraction can remain Worktree.

## Verification

Code head before this report: 569288c3ef3e7dc5b3d1b71727157ef1482b4965

- LCE Branch Rejoin run 36324681188: PASS
- focused invariants: 9 / 9 passed
- Public Verification run 36324681113: PASS
- repository suite: 225 passed
- mypy: PASS
- ruff: PASS

## Structural boundary now supported by experiments

The research sequence now supports the following implementation shape:

    Raw Evidence
        -> SemanticBlock / Point Cloud
        -> local mutual-neighbour structure
        -> stable Line identity
        -> branch-aware Worktree
        -> branch divergence / rejoin inside the same Line
        -> callable branch/trunk projections
        -> overlapping higher-order Surface projections

with these authority constraints:

    Raw Evidence is the only independent evidence authority.
    Derived cognition never becomes self-evidence.
    UNKNOWN and WRONG remain legal results.
    Knowledge time controls visibility.
    Logical time controls placement.
    Branch growth does not clone Lines.
    Callable projections do not become cognition identities by default.
    Surface membership does not create independent evidence.
    Rejoin does not erase historical divergence.
    Rejoin invalidation can reopen prior branches.

## What remains experimental

The exact numerical/semantic operators remain research choices:

- production A4-R neighbour representation and thresholds;
- production trajectory continuity scoring;
- convergence detection criteria;
- branch-to-independent-Line transition policy;
- Surface trajectory comparator;
- natural-language compilation of callable higher-order projections.

Those should not be frozen merely because the synthetic fixtures passed.

## Conclusion

The structural uncertainty is now substantially lower than the operator uncertainty.

The experiments have attacked the major representation failures that would force a redesign later: exclusive clustering, hard temporal gates, one-timestamp authority, global cohesion, cognition self-evidence, projection proliferation, Line cloning, Surface exclusivity, and irreversible branch splitting.

At this point the next useful step is to stop adding synthetic structure variants and implement the validated architecture in the real LCE runtime behind explicit interfaces.

Implementation should preserve replaceable operators so that AML and later real-data pressure tests can challenge retrieval/scoring without reopening the structural model.
