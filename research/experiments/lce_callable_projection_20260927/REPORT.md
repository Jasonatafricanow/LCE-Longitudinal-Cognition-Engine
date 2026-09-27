# LCE Callable Projection / Falsifiability Experiment

Date: 2026-09-27
Branch: verification/lce-callable-projection-20260927
Base: A4-R trajectory branch e18f2c5ed2fea6dab348d96319f3a77af2a783e8

## Question

Can a compiled LCE logic structure become a reusable/callable derived object without silently becoming new independent evidence?

Required authority boundary:

    Raw Evidence = only independent evidence authority
    Projection = derived / rebuildable cognition
    usage != evidence
    projection != fact
    UNKNOWN = legal result
    WRONG = legal result

No manually assigned abstraction-level taxonomy is used.

## Experiment model

Two node classes are used: RawEvidence and Projection.

A Projection may consume Raw Evidence or other Projections. Every Projection recursively closes back to a set of unique Raw Evidence IDs. Reuse, nesting, recall, and consumption do not add evidence votes.

Projection dependency depth is audit-only. It is not an abstraction class or retrieval gate.

## Result 1 — branch projection beats the full mature line for a local query

A mature synthetic trading line contains execution, timing, and philosophy. For a concrete execution/breakout query, callable retrieval ranked:

| Projection | Score |
|---|---:|
| execution branch | 0.8333 |
| full trading line | 0.3333 |
| philosophy branch | 0.1111 |
| timing branch | 0.1000 |

The selected execution projection contained 6 semantic features versus 15 in the full line: a 60% smaller consumer context surface.

The important result is structural: a consumer can directly retrieve a naturally formed branch rather than ingest the whole mature line. No predefined execution/strategy/philosophy level was needed.

## Result 2 — consumer-side Raw Evidence can route back through the projection

A new Raw Evidence item describing another underperforming breakout routed to p_execution. The branch Raw closure changed from r_exec_1/r_exec_2/r_exec_3 to r_exec_1/r_exec_2/r_exec_3/r_exec_4 after recompilation.

The projection helped route the new observation, but only the genuinely new Raw item increased independent support.

## Result 3 — recursive projection preserves unique Raw support closure

A higher derived projection reused the execution projection twice plus the timing projection. Its evidence closure remained exactly the unique underlying Raw set: r_exec_1, r_exec_2, r_exec_3, r_timing_1, r_timing_2.

Derived cognition can therefore be reused as a computation/input object while its evidence authority remains the unique Raw Evidence closure underneath it.

## Result 4 — repeated consumption cannot make a projection more true

A projection with Raw support {a,b,c} was consumed repeatedly and then reused by another projection. After 100 uses, independent support was still exactly 3.

A second rollback fixture consumed an accepted projection 250 times. Its support was still the original three Raw items.

Recall count, usage count, consumer count, and projection nesting therefore do not become qualifying evidence.

## Result 5 — Raw invalidation can downgrade SUPPORTED to UNKNOWN

Initial synthetic fixture state: three valid Raw supports, mean fixture signal +0.8, status SUPPORTED.

After 250 consumptions: still three independent supports and SUPPORTED.

Then Raw b and c were invalidated. Current valid support immediately collapsed to {a}, and the compiled result became UNKNOWN.

The historical projection remained auditable, but current support no longer justified the old compiled conclusion.

## Result 6 — new corrective Raw Evidence can make the old claim WRONG

Two genuinely new Raw items d and e contradicted the old synthetic claim. A recompiled projection closed to current-valid support {a,d,e} and evaluated to mean fixture signal -0.3333, status WRONG.

The old projection was present only as provenance/derived input. It did not cast a positive vote for itself.

## Result 7 — WRONG is not irreversible

After d and e were also invalidated, valid support again became only {a}. The result returned from WRONG to UNKNOWN.

The experiment therefore permits:

    SUPPORTED -> UNKNOWN -> WRONG -> UNKNOWN

as Raw Evidence validity changes. WRONG is not a terminal dogma state.

## Result 8 — provenance impact is traceable through nested projections

Invalidating Raw b identified both dependent projections: p_initial and p_recompiled.

Historical closure stayed inspectable:

    p_initial -> {a,b,c}
    p_recompiled -> {a,b,c,d,e}

while current-valid support was evaluated separately. Historical provenance is therefore distinct from current qualifying support.

## Verification

Implementation/workflow head before this report: 035dc770ca700f858fea4635230e47f4654e9f1f

- LCE Callable Projection Falsifiability run 36320328909: PASS
- Focused research invariants: 9 passed
- Pure experiment code commit c919ade33beef6dd6b99883cd4466c0b6123e262 passed Public Verification.
- The final report commit is re-verified separately.

## What this supports

The experiment supports a layered projection graph:

    Raw Evidence
        -> Semantic/local cognition
        -> Line / branch / Worktree
        -> callable projection
        -> higher derived projection

with one authority invariant:

    all qualifying evidence support closes to unique Raw Evidence

A Projection may be consumed, compared with new SemanticBlocks, used as input to another Projection, cached, indexed, rebuilt, and invalidated through source changes without becoming a new independent factual source.

## What this does not prove

It does not prove production semantic projection quality, automatic branch/projection boundary discovery, real embedding retrieval precision, final line-to-surface representation, natural-language contradiction detection, or production thresholds for SUPPORTED/UNKNOWN/WRONG.

The numeric signal in the rollback fixture is only a falsification oracle for testing authority mechanics. It is not a proposed finite semantic ontology.

## Current interpretation

A mature LCE object should behave like a compiled dependency graph with multiple callable views, not a giant memory summary.

Consumers retrieve the structurally relevant view. Higher cognition may use lower compiled cognition as input. But every derived object remains falsifiable because its support can always be expanded back to Raw Evidence.

The useful asymmetry is:

    compiled cognition can become easier to use
    without becoming harder to disprove
