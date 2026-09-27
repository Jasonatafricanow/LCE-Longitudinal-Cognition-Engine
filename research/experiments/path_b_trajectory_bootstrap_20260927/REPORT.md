# Path B A4-R Trajectory Bootstrap Experiment

**Date:** 2026-09-27  
**Branch:** `verification/path-b-trajectory-bootstrap-20260927`  
**Base experiment:** `verification/path-b-point-cloud-bootstrap-20260927` / `1b121bf1042491adbfb09753b3456b0354522790`

## Why this revision exists

The previous A4 experiment established a useful result:

> reciprocal local semantic neighbourhoods can reveal latent point-cloud structure with surprisingly little relevant evidence.

However, three pieces of the first A4 experiment were experiment scaffolding rather than durable LCE semantics:

1. fixed chronological span / fixed time buckets as hard admission gates;
2. a single timestamp doing both evidence visibility and logical placement;
3. treating one connected component as one exclusive cognition boundary.

Those assumptions conflict with already-frozen LCE boundaries: semantic continuity is not an arbitrary time bucket, temporal ordering remains first-class, and one point may participate in multiple local structures.

This experiment therefore keeps the A4 core and changes the observation model rather than discarding A4.

## A4-R experimental contract

Kept:

```text
mutual semantic neighbourhood
+
local point-cloud structure
```

Removed as hard gates:

```text
minimum chronological span
fixed time buckets
global connected-component == one cognition
```

Time is split into two axes:

```text
known_at
= when LCE is allowed to know/use the evidence
= cutoff / no-future authority

logical_at
= where the evidence belongs in the reconstructed cognition trajectory
= trajectory ordering
```

A4-R then looks for overlapping logical-time paths through reciprocal local
neighbourhoods. Same-logical-time neighbours are not forced into an artificial
before/after sequence.

This is still a synthetic operator experiment. Gold line labels are used only
for evaluation and do not participate in candidate construction.

---

## Result 1 — sparse long-horizon structure survives a large irrelevant history

Fixture:

```text
5,004 total SemanticBlock-like points
4 relevant points
~2,900 logical-day span
5,000 irrelevant points
```

A4-R recovered:

```text
sparse_0
→ sparse_1
→ sparse_2
→ sparse_3
```

Measured:

| Metric | Result |
|---|---:|
| relevant coverage | 100% |
| candidate purity | 100% |
| support | 4 |
| mean local transition similarity | 0.5902 |
| logical span | 2900 |
| independent knowledge events | 4 |

The important point is not the synthetic 100%. It is that no maximum gap,
minimum span, or fixed time bucket was needed to keep the four-point line
recoverable inside a much larger history.

This supports the intended sparse-history behaviour:

```text
very large history
+
very sparse relevant evidence
→ structure may still be recoverable
```

It does not establish production recall on real embeddings.

---

## Result 2 — local trajectory continuity succeeds where global cohesion fails

A six-point line was constructed so that each neighbouring state changes
gradually:

```text
A → B → C → D → E → F
```

Adjacent states remain related, but early and late states are deliberately far
apart.

Measured global all-pairs cohesion:

```text
0.127967
```

The previous A4-style global cohesion gate was `0.15`, so an A4-like
connected-component implementation emitted no candidate.

A4-R recovered the complete six-point trajectory:

| Metric | Result |
|---|---:|
| coverage | 100% |
| purity | 100% |
| support | 6 |
| mean local transition similarity | 0.2874 |
| global pairwise cohesion | 0.1280 |

This is a direct falsification of the assumption:

```text
one mature cognition line
⇒ all historical points should remain mutually cohesive
```

The supported shape is instead:

```text
local continuity can remain strong
while global all-pairs similarity falls
```

That matches a dynamically changing person better than a static cluster model.

---

## Result 3 — knowledge time and logical time cannot be one timestamp

Fixture:

```text
logical state: 2021
first told to LCE: 2026
```

At cutoff 2025 the visible states were:

```text
2020
2022
2023
```

The 2021 state was absent, so there was no future leakage.

At cutoff 2026 the newly known historical state became visible and was placed
by logical time:

```text
2020
→ 2021
→ 2022
→ 2023
```

This demonstrates the required distinction:

```text
visibility is governed by knowledge time
placement is governed by logical time
```

A later statement can therefore revise the current reconstruction of an older
trajectory without pretending that LCE knew the fact at an earlier cutoff.

Current fixture uses integer logical positions only. Production logical time
will need to allow exact times, intervals, partial order, relative order, and
UNKNOWN rather than forcing a fabricated date.

---

## Result 4 — one trunk can retain two overlapping continuations

Fixture:

```text
trunk_0
  ↓
trunk_1
  ├─ a_2 → a_3 → a_4
  └─ b_2 → b_3 → b_4
```

A4-R produced two maximal trajectories:

```text
trunk_0 → trunk_1 → a_2 → a_3 → a_4
trunk_0 → trunk_1 → b_2 → b_3 → b_4
```

Both retained 100% synthetic line coverage/purity.

The two states at the branch boundary share the same logical position. A4-R
does not sequence them one after another merely because they are semantic
neighbours.

This is the key structural difference from exclusive connected components:

```text
shared support is legal
+
branches may coexist
+
same-time alternatives need not collapse
```

The experiment does not yet model a full multidimensional Worktree relation
algebra (support, contradiction, exclusivity, compatibility, merge, etc.). It
only demonstrates that the point-cloud supplier no longer destroys branching
before Worktree interpretation gets a chance to represent it.

---

## Result 5 — time distinguishes evidence shape without deciding structure existence

Two fixtures were given the same local semantic geometry.

### Short burst

```text
4 points
logical span = 3
knowledge span = 3
independent knowledge events = 1
```

### Sparse recurrence

```text
4 points
logical span = 2900
knowledge span = 2900
independent knowledge events = 4
```

A4-R detected both local structures.

That is intentional.

The experiment no longer says:

```text
short span
→ structure does not exist
```

Instead it preserves separate longitudinal evidence:

```text
semantic/local structure
logical span
knowledge span
independent knowledge events
```

The burst and the sparse recurrence therefore remain distinguishable without
using an arbitrary 42-day / 45-day-bucket admission rule.

This leaves a real downstream research question:

> how should Worktree interpretation weigh longitudinal independence and
> recurrence without turning time back into a hard expiry/window rule?

That question is intentionally not answered by this experiment.

---

## Result 6 — mature multi-anchor structure gives a larger retrieval surface

A minimal lower-bound check compared one early historical point with the whole
six-point drift line.

For a late-stage query:

```text
single earliest anchor similarity = 0.0
max mature-line anchor similarity = 1.0
```

For an unrelated query:

```text
max mature-line anchor similarity = 0.0
```

This does **not** yet prove the full mature-abstraction hypothesis. It only
establishes the simplest lower bound: a mature line can expose multiple
legitimate retrieval anchors instead of being compressed into one centroid.

The intended production direction remains stronger:

```text
maturity
→ more support anchors
→ more branch structure
→ higher-level abstractions
→ broader but structured retrieval surface
```

not:

```text
maturity
→ lower one global similarity threshold
→ attraction black hole
```

---

## Verification

Initial implementation commit:

`57e4b7989f9ba8847aa1c9667160fa879a2b678d`

GitHub Actions:

- Path B A4-R Trajectory Bootstrap — run `36318317604`: **PASS**
- Public Verification — run `36318317542`: **PASS**

Focused invariants:

```text
7 passed
```

They verify:

- gold labels do not affect structural output;
- sparse four-point longitudinal structure survives large irrelevant history;
- local continuity recovers drift rejected by global cohesion;
- dual-time visibility prevents future leakage and permits retrospective placement;
- overlapping branches survive without exclusive-component collapse;
- short burst and sparse recurrence are both structurally visible but retain different longitudinal diagnostics;
- multi-anchor mature retrieval expands a lower-bound recall surface without absorbing an unrelated query.

---

## What this experiment supports

The evidence supports keeping A4's core idea, but narrowing its responsibility:

```text
Point Cloud
    ↓
reciprocal local semantic structure
    ↓
overlapping trajectory observations
    ↓
Worktree hypotheses / branches
```

It also supports replacing the first A4 formulation:

```text
persistent connected component
+ fixed temporal gates
+ global cohesion
```

with a trajectory-oriented formulation:

```text
local continuity
+ overlap
+ logical ordering
+ separate knowledge-time authority
```

Time remains first-class evidence. It is no longer the admission window.

---

## What this experiment does not prove

It does not yet prove:

- production behaviour on real SemanticBlock embeddings;
- robustness to anisotropic embedding density / hubness;
- correct inference of contradiction, support, exclusivity, or contextual compatibility;
- full multidimensional Worktree semantics;
- the Point → Line → Surface higher-order transition;
- learned abstraction that raises recall above the multi-anchor lower bound;
- the final production threshold for creating an OPEN Worktree;
- production logical-time extraction from natural language.

The beam-path supplier is an experimental operator, not a production algorithm.

---

## Next algorithmic questions

The next research layer is no longer whether point-cloud trend structure exists.
The useful questions are:

1. Can the trajectory supplier survive real SemanticBlock vector noise and
   density imbalance while keeping sparse lines?
2. How should a mature line expose hierarchical retrieval surfaces without
   collapsing into one centroid or an attraction black hole?
3. How should Worktree preserve multidimensional relations among overlapping
   lines, including mutually exclusive unresolved branches?
4. Once lines are stable enough, can repeated **trajectory shapes** across
   different semantic directions form the intended Line → Surface structure?
5. How should uncertain logical time be represented as intervals / partial
   orders / UNKNOWN while preserving knowledge-time cutoff authority?

## Current conclusion

**A4 remains valuable. A4-R changes what A4 is allowed to mean.**

The original experiment showed that very small amounts of relevant evidence can
already create visible structure in a point cloud.

This revision adds evidence that the useful structure should be interpreted as
an evolving, overlapping trajectory substrate rather than a time-windowed
exclusive cluster.

The strongest results are:

```text
4 relevant points / 5,004 total
→ sparse line still recovered

global cohesion 0.128 (< old 0.15 gate)
→ six-state dynamic line still recovered through local continuity

2026 knowledge of a 2021 state
→ invisible before 2026
→ correctly inserted into the 2021 logical position after it becomes known

shared trunk
→ two branches remain simultaneously representable
```

Those results are consistent with the intended LCE model:

```text
Point
→ Line
→ multidimensional Worktree
→ later Line-to-Surface abstraction
```

rather than a static semantic clustering system.
