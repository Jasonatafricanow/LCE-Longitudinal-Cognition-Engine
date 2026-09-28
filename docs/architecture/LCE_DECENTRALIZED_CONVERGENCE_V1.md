# Decentralized Evidence Convergence V1

Status: production cognition primitive.

This module implements the 2026-09-28 non-centralized authority experiment as a
reusable LCE primitive. "Authority" here does **not** mean that a derived
interpretation becomes factual truth. Raw Evidence remains the only independent
factual authority.

The problem is narrower:

> When several derived structural interpretations are possible, can LCE obtain a
> high-confidence structural result from distributed source support without
> asking one model/scorer to issue a final weighted confidence number?

## Core rule

The runtime keeps a vector of explicit support dimensions:

- independent Raw-Evidence support groups;
- reciprocal local-structure support;
- source-grounded context diversity when an upstream layer supplies it;
- derivation stability across algorithm/provider variants;
- contradiction pressure.

There is no weighted sum.

Admission uses small explicit floors. Competition uses Pareto dominance. A
candidate may win only when it is no worse on every positive dimension, no
worse on contradiction pressure, and strictly better on at least one dimension.

Cross-dimension tradeoffs remain `UNRESOLVED`.

## Runtime objects

The implementation deliberately keeps the authority surface small.

### AuthoritySignal

One signal says:

```text
for decision D,
candidate C
is supported/contradicted
by Raw closure R
under derivation variant V
at knowledge time K
```

It may also carry:

- `reciprocal=True` when the structural observation comes from reciprocal
  local geometry;
- an optional upstream-supplied `context_id`;
- `polarity = support | contradict`.

The signal does **not** carry a scalar confidence.

### Evidence component

Signals are grouped by Raw-Evidence overlap, not merely by identical closure.

Let each signal closure be a set of Raw IDs. Construct a graph where two
closures are connected when they share at least one Raw ID. Each connected
component is one independent evidence component.

Therefore:

```text
{E1,E2} --overlaps-- {E2,E3} --overlaps-- {E3,E4}
                  => one component
```

This is the unit used by `independent_support`.

### AuthorityProfile

For each candidate:

```text
profile(C) = (
  independent_support,
  reciprocal_support,
  context_support,
  derivation_stability,
  contradiction_pressure
)
```

The dimensions have intentionally different meanings:

| Dimension | Meaning | What does **not** increase it |
|---|---|---|
| `independent_support` | Number of independent Raw-evidence components supporting the candidate. | Replaying the same Raw closure, partially overlapping closures, more projections over the same Raw basis. |
| `reciprocal_support` | Independent support components that contain at least one reciprocal local-structure observation. | A higher cosine score by itself. |
| `context_support` | Number of distinct stable upstream context IDs represented by supporting components. | Inventing local time buckets or assigning conflicting contexts to the same Raw component. |
| `derivation_stability` | Number of derivation variants that independently reproduce support above the configured per-variant evidence floor. | Repeating one variant or running many variants over only one Raw component. |
| `contradiction_pressure` | Number of independent Raw-evidence components carrying contradiction signals. Lower is better. | Positive support does not numerically cancel it. |

## Decision algorithm

Evaluation is intentionally two-stage.

### 1. Eligibility

A candidate must satisfy every configured floor:

```text
independent_support >= min_independent_support
reciprocal_support >= min_reciprocal_support
context_support >= min_context_support
derivation_stability >= min_derivation_stability
```

A floor is an admission condition, not a weight.

### 2. Pareto competition

For two eligible candidates `A` and `B`, `A` dominates `B` only when:

```text
A.independent_support >= B.independent_support
A.reciprocal_support  >= B.reciprocal_support
A.context_support     >= B.context_support
A.derivation_stability >= B.derivation_stability
A.contradiction_pressure <= B.contradiction_pressure

and at least one comparison is strict.
```

The final rule is:

```text
exactly one eligible undominated candidate
    -> CONVERGED(candidate)

zero eligible candidates
    -> UNRESOLVED

two or more eligible undominated candidates
    -> UNRESOLVED
```

There is no secondary score-based tie-break.

## Why Pareto instead of a weighted confidence score

A scalar requires an exchange rate between unlike evidence dimensions.

For example:

```text
score = 0.4 * independent_support
      + 0.2 * derivation_stability
      - 0.4 * contradiction_pressure
```

looks convenient, but it silently asserts how much contradiction can be bought
off by more support and how much repeated algorithmic stability is worth
relative to independent factual evidence.

LCE does not currently have authority to make those semantic exchange-rate
claims. Pareto comparison is deliberately weaker: it resolves only cases where
one candidate is structurally no worse across the entire declared profile.

This means the system gives up some automatic decisions in exchange for making
the remaining decisions easier to audit.

## Path B integration logic

### Slow bootstrap

For a newly proposed trajectory path:

```text
mutual-kNN proposes path
    |
    v
existing Line overlap candidates?
    |
    +-- no --> candidate = deterministic new Line seed
    |           support = path SemanticBlocks -> Raw closures
    |
    +-- yes -> candidates = existing Lines with enough visible shared support
                support = cutoff-valid shared Line states -> Raw closures
    |
    v
decentralized convergence
    |
    +-- CONVERGED new seed --> materialize new Line
    +-- CONVERGED existing Line --> inherit that Line identity
    +-- UNRESOLVED --> no persistent identity change
```

The minimum independent-support floor is never weaker than the structural
support floor already required by the path/Line assembler.

### Nearline attachment

Nearline routing is intentionally different from bootstrap.

The runtime first uses vector similarity only as a retrieval/proposal filter:

```text
current block
  -> scan visible stable Lines
  -> keep every Line whose best visible node clears min_similarity
```

It does **not** use the best score or score margin as final authority.

For every surviving candidate Line, it then collects the full cutoff-visible
local neighbourhood whose states also clear `min_similarity` against the
current block. Those states close back to Raw Evidence and form that candidate's
authority support.

```text
candidate Line
  -> all locally qualifying visible states
  -> Raw closures
  -> evidence components
  -> AuthorityProfile
```

All threshold-qualified Lines compete through the same convergence operator.

This preserves the boundary:

```text
similarity = proposal / retrieval evidence
Raw-grounded convergence = persistence authority
```

## Knowledge-time semantics

The ledger is bitemporal-aware in the sense relevant to derived cognition.

For each signal:

- Raw Evidence has its own logical occurrence and source knowledge lifecycle;
- the authority signal has its own `known_at`, meaning when this derived
  structural observation became available.

A signal is visible at cutoff `T` only when:

```text
signal.known_at <= T
and
every Raw Evidence item in signal.raw_evidence_ids is valid at T
```

This prevents two different history errors:

1. **backdating:** evidence known long ago does not make a structure derived
   today appear known long ago;
2. **forward contamination:** a later invalidation cannot be ignored merely
   because the derived signal was once recorded.

Earlier cutoffs still replay the earlier epistemic state.

## Derivation identity

`derivation_variant_id` exists so robustness across genuinely different
derivations can be represented without pretending those derivations are new
facts.

In the production Path B binding, the variant fingerprint covers:

```text
embedding version
trajectory configuration
neighbour-provider identity/version
```

The Line graph derivation fingerprint additionally includes the authority policy
itself. Changing `AuthorityConfig` therefore makes the current graph stale and
requires an explicit rebuild before Line consumers may treat it as current.

## Context semantics

`context_id` is deliberately external.

The convergence layer does not define "conversation", "session", "week",
"project", "market regime", or any other universal context bucket. If an
upstream source-aware layer has an authorized context identity, it may attach
one.

Within one independent Raw component:

- exactly one context ID -> that context can contribute;
- conflicting context IDs -> the component contributes no context-diversity
  support;
- no context ID -> no context-diversity contribution.

Across independent components, repeated use of the same context ID counts once
toward context diversity.

## Contradiction semantics

The data model supports `polarity="contradict"`, but Path B does not currently
invent semantic contradiction from geometry.

This is intentional. Cosine distance is not contradiction.

A future contradiction supplier must have its own authorized semantic contract.
Once such signals exist, the convergence layer can consume them without
changing its comparison logic.

## Failure / UNKNOWN semantics

`UNRESOLVED` is not an exception path. It is a first-class result.

Typical reasons include:

- too little independent Raw support;
- several candidates with equal source-grounded support;
- cross-dimension tradeoffs that Pareto comparison cannot resolve;
- insufficient derivation stability under a stricter deployment policy;
- missing authorized context or contradiction evidence when a policy requires
  those dimensions.

No fallback converts these states into "pick the highest similarity".

## Pseudocode

```text
function evaluate(decision_key, signals, policy):
    visible = signals_for(decision_key, cutoff)
    visible = keep_only_cutoff_valid_raw_closures(visible)

    for candidate in candidates(visible):
        support_components =
            connected_components_by_raw_overlap(candidate.support_signals)

        contradiction_components =
            connected_components_by_raw_overlap(candidate.contradict_signals)

        profile[candidate] = dimensions(
            support_components,
            contradiction_components,
            reciprocal_flags,
            context_ids,
            derivation_variants,
        )

    eligible = [c for c if meets_all_floors(profile[c], policy)]

    undominated = [
        c for c in eligible
        if no_other_eligible_candidate_pareto_dominates(c)
    ]

    if len(undominated) == 1:
        return CONVERGED(undominated[0])

    return UNRESOLVED
```

The intentionally absent line is:

```text
return max(candidates, key=weighted_confidence)
```

## Anti-self-amplification rule

Derived cognition cannot create votes.

A signal carries the exact Raw-Evidence closure that supports it. Independence
is stricter than exact-closure de-duplication: closures that overlap transitively
are collapsed into one evidence component. For example, `{E1,E2}` and
`{E2,E3}` are one authority component, not two votes.

Replaying the same evidence through many projections or derivation variants can
increase *derivation stability* but cannot increase *independent support*. A
derivation variant counts as stable only when that variant is itself supported
by a configured minimum number of independent evidence components. One Raw item
replayed through many variants therefore cannot manufacture stability either.

## Bitemporal rule

Signals have `known_at`, which records when that *derived structural
observation* was materialized. It is not backdated to the Raw Evidence event
time. Evaluation at a knowledge cutoff includes only signals already materialized
by that cutoff and whose Raw Evidence was valid at that same cutoff.

A later correction can therefore remove a signal from the current convergence
decision without rewriting what an earlier epistemic replay was allowed to
believe. Conversely, old Raw Evidence cannot make a newly derived interpretation
appear to have existed before it was actually derived.

## Context rule

LCE does not invent context buckets.

A `context_id` is optional and must come from an upstream source-aware layer.
If the same Raw-Evidence group is presented with conflicting context IDs, that
group contributes no context-diversity support. This prevents derived
re-projections from manufacturing artificial context breadth.

## Relation to Path B

Path B uses local geometry to *propose* structure. This convergence layer
decides whether the source-grounded support for a proposed identity is
sufficiently stable to materialize or inherit persistent Line identity.

The separation is intentional:

```text
Raw Evidence
  -> SemanticBlock
  -> local mutual-kNN proposal
  -> decentralized evidence convergence
  -> persistent Line identity / UNKNOWN
```

Similarity remains a proposal mechanism, not factual authority. For nearline
Line routing, every Line above the proposal threshold competes. A larger cosine
score or the legacy score margin cannot certify the winner. Each candidate is
supported by its whole cutoff-visible local neighbourhood above threshold, not
by one "best" anchor node.

The derivation-variant identity includes embedding version, trajectory config,
and neighbour-provider identity/version. Surviving multiple genuinely different
derivations can therefore count as stability; rerunning the same derivation
cannot.

## What this V1 does not claim

- It does not prove that a converged interpretation is semantically true.
- It does not invent contradiction labels; an authorized semantic-relation layer
  may add contradiction signals later.
- It does not define a universal context ontology.
- It does not replace held-out real-data calibration.
- It does not turn Surface or Line reuse into independent evidence.

The key invariant is:

> high structural confidence can emerge from distributed evidence while factual
> authority remains at the Raw-Evidence layer.
