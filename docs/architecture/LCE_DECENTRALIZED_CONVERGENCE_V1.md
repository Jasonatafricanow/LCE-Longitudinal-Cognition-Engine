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
