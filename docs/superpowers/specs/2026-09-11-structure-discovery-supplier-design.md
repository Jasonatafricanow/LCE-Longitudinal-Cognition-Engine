# Structure Discovery Supplier Design

**Date:** 2026-09-11  
**Status:** Design only — no algorithm or implementation change authorized  
**Scope:** LCE longitudinal structure discovery research

## 1. Problem

LCE already has a stable product chain:

```text
Raw Evidence
  -> Semantic Blocks
  -> vectors
  -> structure discovery
  -> StructureObservation / StructureSnapshot / StructureDiff
  -> HigherOrderCandidate
  -> bounded LLM interpretation / re-verification
  -> Worktree / Baseline
```

The current structure discovery implementation is only one way to supply the `structure` stage. It uses local cosine / k-neighbourhood observations, overlap, stability, multi-point participation, and temporal snapshot diffs.

New mathematical methods may discover structural information that the current supplier misses. Candidate families include persistent homology, Hodge-Laplacian analysis, and discrete Hodge decomposition.

The design question is **not** whether LCE needs a new topology subsystem. It is:

> Can additional structure-discovery algorithms act as alternative or complementary suppliers of the same existing LCE structure product, without changing the downstream cognition pipeline?

## 2. Core design decision

**The architecture does not change.**

The fixed abstraction remains:

```text
Semantic Blocks + vectors
          |
          v
  structure discovery
          |
          v
      structure
          |
          v
 HigherOrderCandidate
          |
          v
 bounded LLM verification
```

Structure is the product. A discovery algorithm is a supplier.

The consumer must not depend on whether a structure was discovered by the current kNN/cosine method, persistent homology, a graph/spectral method, a Hodge-family method, or a future method.

No new architectural layer is justified merely because a new algorithm exists.

## 3. Existing authority boundary remains frozen

All new supplier outputs remain **derived structural evidence**.

They do not become Raw Evidence, factual Memory, canonical truth, causal truth, or accepted cognition merely because a mathematical detector reports them.

A detected structure may support a bounded `HigherOrderCandidate`. The downstream interpreter must still inspect the authorized Semantic Blocks / source evidence and may return `UNKNOWN` when the semantic meaning is not justified.

The existing rules remain unchanged:

```text
geometry != semantics
structure != causality
persistence != truth
algorithmic confidence != promotion authority
```

## 4. What may vary

Only the internal discovery method may vary.

Conceptually:

```text
Structure discovery suppliers
  - current local kNN / cosine supplier
  - persistent-homology supplier candidate
  - Hodge-Laplacian supplier candidate
  - discrete-Hodge supplier candidate
  - future supplier candidates

                 |
                 v
        existing structure product
                 |
                 v
        existing downstream consumer
```

These names identify research candidates, not approved implementations.

No supplier receives its own cognition authority, persistence authority, interpretation path, or LLM.

## 5. Product-level structural questions

The research should stay centered on structural phenomena LCE already cares about rather than on mathematical novelty for its own sake.

Candidate suppliers are useful only if they improve observation of one or more of the following:

- **stable local membership** — a group remains structurally coherent across reasonable scales or cutoffs;
- **reconnection / bridge emergence** — a new or later Semantic Block changes previously separated local relations;
- **closure / cycle-like organization** — a relation pattern becomes structurally closed rather than remaining a simple chain;
- **overlapping participation** — one Semantic Block legitimately participates in several local structures;
- **higher-order co-structure** — a multi-point relation contains information not captured by independent pairwise similarity alone;
- **reorganization / disappearance** — an earlier structure weakens, splits, merges, disappears, or is reorganized as later evidence arrives;
- **cross-scale stability** — a structural observation survives a meaningful range of neighbourhood or scale choices instead of appearing only at one arbitrary threshold.

These are observations. Their meaning is not predefined.

## 6. Important prior negative evidence

LCE has already tested a limited H1/TDA signal during STRUCTURE-06R. H1 counts existed but showed no useful semantic signal. That negative result remains valid and must not be overwritten by the existence of more sophisticated topology terminology.

Therefore a future persistent-homology experiment must not merely repeat:

```text
count H1 loops -> assume cognition
```

If persistent homology is evaluated again, the new hypothesis must concern information not already falsified by the earlier H1-count experiment, such as cross-scale persistence, birth/death behaviour, temporal structural change, or comparative precision against the existing supplier.

Likewise, Hodge-family methods must earn their place by exposing useful structure unavailable from the current supplier. A mathematically elegant decomposition is not itself evidence of product value.

## 7. Supplier-output compatibility

The existing `StructureObservation` contract is currently shaped by the first kNN supplier and contains fields such as `center_block_id`, `k`, `neighbourhood_stability`, and `local_overlap`.

This design does **not** authorize changing that contract now.

The rule is:

> First determine experimentally whether a new supplier produces useful incremental structural evidence. Only then ask whether the current structure contract can represent it cleanly.

Possible outcomes after experiments are deliberately left open:

1. the new method maps cleanly into existing structure objects — no contract change;
2. a very small supplier-neutral extension is required — make the minimum change;
3. the method produces no useful incremental evidence — add nothing.

A new generic provider hierarchy, topology engine, persistence layer, or parallel cognition pipeline is specifically not justified at the design stage.

## 8. Algorithm-design phase boundary

The next phase, after this design is accepted, is an **algorithm specification**, not implementation.

That specification should define for each candidate method:

- exact input representation;
- what structural question it is supposed to answer;
- what output can be converted into existing LCE structure evidence;
- what information is genuinely new relative to the current kNN/cosine supplier;
- required assumptions and known failure modes;
- computational cost and scale limits;
- falsifiable acceptance criteria;
- negative controls and comparison baseline.

The algorithm specification must keep persistent homology, Hodge Laplacian, and discrete Hodge decomposition separate. They are not interchangeable algorithms and may require different input structures. In particular, discrete Hodge decomposition should not be treated as a drop-in point-cloud detector unless a meaningful graph/simplicial edge-flow quantity is first defined.

## 9. Experiment phase boundary

Only after the algorithm specification is accepted should experiments be implemented.

The experiment must compare candidate suppliers against the current structure-discovery baseline on the same frozen Semantic Blocks, vector space, temporal cutoffs, and evaluation corpus wherever possible.

The primary question is not whether the new algorithm finds *something*. It is:

> Does it provide reproducible structural information that is useful to the downstream bounded interpreter and is not already available from the current supplier?

Useful evidence may include improved precision, recovery of previously missed longitudinal structural events, stronger cross-scale stability, lower noise, or materially better downstream candidate verification.

A method that only creates more candidate structures without improving discrimination is a failure.

## 10. Architecture-change gate

No architecture change is permitted merely because an experiment uses a new library, mathematical object, or intermediate representation.

An architecture or public-contract change becomes discussable only if all of the following are true:

1. the candidate algorithm demonstrates reproducible incremental value;
2. the useful output cannot be represented cleanly through the existing structure product;
3. the missing information is needed by the existing downstream consumer;
4. the proposed change reduces total system complexity relative to ad hoc adaptation;
5. the smallest sufficient change has been identified.

This is a high bar by design.

## 11. Non-goals

This design does not authorize:

- a Topology Engine;
- a Hodge subsystem;
- a second structure pipeline;
- a new LLM judge;
- new cognition authority;
- causal inference from topology;
- recursive cognition;
- new canonical state;
- a new persistence layer;
- MR production integration changes;
- changing the current `StructureObservation` contract before experimental evidence requires it;
- treating mathematical elegance as evidence of semantic usefulness.

## 12. Design principle

The research should expand **algorithmic options**, not architectural surface area.

A good outcome may be one new algorithm implementation behind the existing structure stage. An equally good outcome may be a negative result and zero production code.

The default rule is:

> If a new method supplies an existing capability, keep it inside that capability. Create a new abstraction only when the existing abstraction is proven insufficient and the new abstraction makes the whole system simpler.

The desired architecture remains short, explicit, replaceable, and easy to reason about.
