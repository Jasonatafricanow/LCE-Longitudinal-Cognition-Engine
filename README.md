# LCE V1 — Longitudinal Cognition Engine

LCE is a standalone, contract-first longitudinal cognition pipeline. Its V1
product boundary is:

```text
Raw Evidence -> Semantic Block -> vector space -> structures
-> cognition worktree -> accepted Baseline/HEAD -> Understanding read API
```

LCE does not require MR. Reference Memory is the included minimal local
substrate and can be replaced by injecting a backend that implements the
focused Reference Memory ports. Raw Evidence remains
canonical and auditable; Semantic Blocks are the cognition points used for
vector projection. Derived vectors, structures, higher-order candidates, and
worktrees never become Raw Evidence.

Semantic Block continuation creates immutable states. Structure snapshots bind
their visible blocks and vectors to a cutoff, and a bounded interpreter sees
only the exact candidate package resolved by LCE. Failed ordered inputs form a
durable barrier; compiler replay does not imply downstream pipeline
completion.

The existing Baseline/HEAD Core remains the accepted revision authority. An
OPEN cognition worktree is a proposal. Conservative promotion creates a new
immutable revision only when the Understanding changes; additional support for
the same text does not create noise revisions.

## Boundaries

LCE V1 stops at `query(current_context) -> accepted Understandings`. It does
not integrate MR, Body, C10, Persona, Agent identity, Intent, ActionPolicy,
RuntimeBinding, or current-turn reasoning. See
[`docs/architecture/LCE_V1_RUNTIME.md`](docs/architecture/LCE_V1_RUNTIME.md)
and [`docs/architecture/LCE_V1_BOUNDARIES.md`](docs/architecture/LCE_V1_BOUNDARIES.md).

## Development

```powershell
python -m pytest -q
```

The standalone setup and replaceable Reference Memory options are documented
in [`docs/standalone-quickstart.md`](docs/standalone-quickstart.md) and
[`docs/reference-memory.md`](docs/reference-memory.md).
