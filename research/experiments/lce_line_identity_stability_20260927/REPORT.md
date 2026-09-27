# LCE Line Identity Stability Experiment

Date: 2026-09-27
Branch: verification/lce-line-identity-stability-20260927
Base: 576f177a43334c2bbd8dc0364b89af15ca44aaf6

## Question

Can a mature Line keep one stable identity while growing many branches, participating in multiple Surfaces, and serving many consumer calls—without cloning itself into new persistent Lines or relation-view cognition objects?

## Result 1 — branch proliferation does not create Line proliferation

A single mature trading Line was given 24 branches. The registry remained:

    Lines:    1
    Branches: 24

Then 500 callable projections were materialized from those branches.

After 500 calls:

    Lines:    1
    Branches: 24
    persistent projection cognition nodes: 0

The Line Raw closure contained 76 Raw items, but identity stayed singular.

This supports:

    branch proliferation != Line proliferation
    projection materialization != cognition proliferation

## Result 2 — callable projection is a consumption view, not a new cognition identity

A callable projection retained:

    owner_line_id
    source_branch_id
    Raw provenance closure

but was not inserted into the cognition registry.

The first projection from branch_0 closed to the shared trunk plus branch_0 Raw evidence. Repeated materialization changed only a usage counter.

This corrects the prior experiment's overly permissive notion of persistent relation-view nodes.

## Result 3 — the same Line can participate in multiple Surfaces through real branches

One trading Line had two real internal branches:

    trade_timing
    trade_execution

Two Surfaces referenced those branches directly:

    surface_timing
      -> line_trading / trade_timing
      -> engineering / boundary
      -> writing / structure

    surface_execution
      -> line_trading / trade_execution
      -> risk / execution
      -> learning / execution

The trading Line identity count remained exactly 1.

No persistent trade_view_u / trade_view_f cognition objects were created.

## Result 4 — Surface provenance follows the participating branch only

surface_timing contained trade_timing Raw evidence and the shared trading trunk, but not trade_execution-only Raw evidence.

surface_execution contained trade_execution Raw evidence and the shared trading trunk, but not trade_timing-only Raw evidence.

So higher-order structure can be branch-specific without cloning the whole Line.

## Result 5 — one Surface cannot count several branches of one Line as independent directions

An attempted Surface containing three branches from line_trading was rejected.

This protects evidence independence:

    one owner Line
    -> many branches
    != many independent Lines

The same Line may participate in different Surfaces through different branches, but one Surface cannot use sibling branches to manufacture cross-Line support.

## Result 6 — split candidacy is delayed and non-mutating

An early branch with one unique Raw item did not become a split candidate.

A more independently evolved branch with five unique continuation Raw items and its own two child branches was allowed by the synthetic fixture oracle to become a split candidate.

Crucially:

    Line count before candidate: 1
    Line count after candidate:  1
    new Line created:            false

So even a mature branch that looks structurally independent only produces a review/candidate object. It does not automatically split or clone the parent Line.

The exact oracle used here is synthetic and is not production split policy.

## Verification

Code head before this report: 8b67a954940445c847d8149bb0b3aec7bd645ca0

- LCE Line Identity Stability run 36324266066: PASS
- focused invariants: 9 / 9 passed
- Public Verification run 36324266026: PASS

## Revised structural boundary

The current model is:

    Line
      |- stable identity / trunk
      |- Branch A
      |- Branch B
      |- Branch C
      `- ...

Consumers may receive ephemeral projections from any branch.

Surfaces may reference real branches directly.

A branch can later become a split candidate if independent evolution justifies review, but candidacy does not itself create a new Line.

Therefore:

    trunk growth        -> same Line
    branch growth       -> same Line
    callable projection -> same Line
    Surface membership  -> same Line
    split candidate     -> still same Line

Only a later explicit identity transition, under a separately justified rule, could create a new Line.

## What this does not prove

It does not decide the production rule for when a branch should truly become an independent Line.

It also does not yet test:

- branch merge/rejoin after long divergence;
- retroactive dual-time evidence that changes branch identity;
- noisy real SemanticBlock embeddings;
- persistence/caching policy for callable projections.

The main result is narrower: mature cognition can become structurally rich without becoming identity-rich by default.
