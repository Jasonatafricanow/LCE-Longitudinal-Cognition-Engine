# LCE Structure Discovery Capability-Coverage Experiment Design

**Date:** 2026-09-11  
**Status:** Experiment design only — no implementation authorized  
**Depends on:** `STRUCTURE_DISCOVERY_ALGORITHM_SPEC_2026-09-11.md`

## 1. Purpose

This experiment does **not** re-validate the mathematics of MST, persistent homology, Hodge Laplacians, or discrete Hodge decomposition. Those methods already have established mathematical definitions and known implementations.

The experiment asks four narrower LCE questions:

1. **Representation compatibility** — when LCE presents a structure through Semantic Blocks, embeddings, time, or a derived directional signal, does the required mathematical structure survive the representation step?
2. **Capability boundary** — under what noise, sparsity, density, paraphrase, timing, and dropout conditions does the LCE+algorithm combination stop recovering the intended structure reliably?
3. **Incremental product value** — does a more complex supplier expose useful structure that a simpler supplier does not already provide?
4. **Real-data prevalence** — after capability is established under controlled coverage, does the real longitudinal corpus contain enough of that signal to justify keeping the supplier?

A real-corpus miss is therefore not automatically an algorithm failure. It may mean the corpus does not contain enough of the required signal.

## 2. Evaluation order

The order is fixed:

```text
controlled capability fixture
  -> LCE representation layer
  -> supplier comparison
  -> stress / failure-boundary sweep
  -> blind downstream verification
  -> real longitudinal corpus
```

The controlled fixture exists to cover a target LCE capability, not to prove a theorem or test whether a mature library can perform its documented mathematics.

## 3. Two fixture levels

Each active capability should be tested at two representation levels.

### 3.1 Embedding-calibrated fixtures

Construct synthetic vectors whose distance distribution, anisotropy, local density, and dimensionality are calibrated to the frozen LCE embedding corpus, then plant the target structural pattern inside that background.

Purpose:

- test the supplier under embedding-like geometry rather than clean 2D toy geometry;
- isolate structure-discovery failure from language/embedding failure;
- permit controlled variation of signal strength and noise.

This level does not claim semantic validity. It tests whether the detector can recover a known structure when the vector representation actually contains it.

### 3.2 Controlled semantic fixtures

Construct bounded Semantic Blocks with known intended relations, send them through the real LCE semantic-block and embedding path, then run the same detector.

Purpose:

- test whether the representation layer preserves enough of the intended relation for the algorithm to see it;
- distinguish `representation failure` from `structure-discovery failure`;
- test paraphrase, topic overlap, distractors, and semantic ambiguity.

A fixture may succeed at the embedding-calibrated level and fail at the semantic level. That is a valid result: it means the algorithm has the capability but the current representation does not reliably expose the required signal.

## 4. Capability family A — bridge and reconnection

### 4.1 Target question

Can LCE detect that later evidence changes the connectivity of previously separate semantic regions?

This is the cleanest use case for the current kNN supplier and the MST / H0 control.

### 4.2 Required fixture variants

**A1 — geometric bridge.** Two coherent regions `A*` and `B*` are initially separated. A later block `C` is designed to be locally related to both sides and should reduce the merge scale or create a new cross-region connection.

**A2 — chained bridge.** `A` and `B` are not directly close, but later intermediate blocks create a path of short local relations. This tests the single-linkage/MST ability to represent broader connectivity through local steps.

**A3 — semantic explanatory bridge.** `C` explains a relation between `A` and `B` at the meaning level, but is not intentionally written as a lexical or topical midpoint. This is a representation-boundary test. If the embedding does not place `C` as a bridge, vector geometry cannot be expected to recover the semantic explanation.

**A4 — decoy bridge.** Add a block `D` that is superficially related to both sides but should not support the intended bounded interpretation. This measures chaining false positives and downstream rejection.

### 4.3 What success means

The supplier should localize the changed connection and identify the participating block set. For temporal fixtures, the structural change must appear only after the relevant later block becomes visible.

MST/H0 is retained only if this information is useful beyond the existing fixed-k/fixed-threshold detector.

## 5. Capability family B — cross-scale robustness and persistent topology

### 5.1 Target question

Does cross-scale persistence improve LCE's ability to distinguish robust structural candidates from threshold-specific or density-driven noise?

This is the primary product hypothesis for persistent homology.

### 5.2 Required fixture variants

**B1 — threshold-fragile candidate.** A structure exists only in a narrow distance range. It should receive low persistence / low robustness priority.

**B2 — broad-scale candidate.** A planted structural feature survives a substantially wider scale range. It should rank as more robust than B1.

**B3 — density artifact.** Increase local sampling density without adding new semantic organization. The method should not interpret density alone as stronger cognition evidence.

**B4 — temporal birth/death.** Later Semantic Blocks cause a persistent feature to appear, disappear, or materially change lifetime at a known cutoff.

**B5 — prior-H1 negative analogue.** Construct examples where H1 exists mathematically but carries no useful semantic distinction. This guards against repeating the earlier `H1 exists -> cognition` failure.

### 5.3 Product criterion

Persistent homology is useful only if persistence/localization improves candidate discrimination or downstream bounded interpretation compared with current kNN and MST controls.

If H0 is redundant with MST and H1 adds no semantic precision or useful robustness signal, persistent homology should be removed from the roadmap.

## 6. Capability family C — edge-space organization for Hodge Laplacian

### 6.1 Target question

Can non-zero Hodge-Laplacian spectrum/localization distinguish useful relation organization that node-neighbourhood statistics and persistent homology treat as equivalent or nearly equivalent?

### 6.2 Critical comparison design

Create paired fixtures with similar coarse topology but different edge organization.

Examples:

- two contractible/densely connected structures with similar H0/H1 summaries, one containing a coherent localized relation motif and the other containing randomized cross-links;
- two structures with comparable Betti numbers/persistence but different overlap organization;
- a stable localized edge mode versus a hub-dominated artifact.

The point is not to show that `L1` has eigenvalues. The point is to test whether the non-zero spectrum identifies a product-relevant distinction that PH and node-space statistics miss.

### 6.3 Product criterion

Retain Hodge-Laplacian analysis only if it recovers stable block-localized modes that:

- survive nearby scale choices and modest perturbation;
- are not explained by degree/hub density alone;
- produce useful downstream distinctions beyond PH and current neighbourhood statistics.

Otherwise it is redundant complexity.

## 7. Capability family D — directional flow and discrete Hodge decomposition

### 7.1 Why DHD needs a separate input study

Discrete Hodge decomposition requires an antisymmetric edge flow. Current LCE similarity is symmetric and therefore not a sufficient input.

The research target is not to invent a direction from timestamps. It is to determine whether LCE can derive a repeatable **predictive asymmetry** from longitudinal data without using an LLM to pre-interpret causality.

### 7.2 First candidate flow

For repeated semantic states or controlled semantic labels `u` and `v`, define a bounded future window `Delta` and estimate a predictive gain:

```text
g_Delta(u -> v)
  = P(v occurs in the future window | u is present in the conditioning history)
    - P(v occurs in the future window | matched baseline context)
```

Then form an antisymmetric flow:

```text
f_uv = g_Delta(u -> v) - g_Delta(v -> u)
f_vu = -f_uv
```

The first experiment should use the simplest auditable estimator that supports minimum-count filtering and uncertainty intervals. More flexible predictive models are deferred until the simple estimator's behavior is understood.

This quantity means **predictive asymmetry**, not causality.

### 7.3 Controlled longitudinal fixtures

Because reliable flow estimation requires repeated observations, the DHD fixtures must contain repeated semantic-state occurrences rather than one-off individual blocks.

Required families:

**D1 — predominantly gradient-like progression.** Repeated sequences mostly follow `A -> B -> C` with low reverse transition rate.

**D2 — local feedback cycle.** Repeated sequences support `A -> B`, `B -> C`, and `C -> A`.

**D3 — larger global cycle.** A cycle of four or more states with no filled local triangle analogue, intended to separate local curl-like and harmonic/global-cycle behavior where the chosen complex supports that distinction.

**D4 — mixed flow.** Combine a dominant progression with a weaker cycle.

**D5 — common-context confounder.** A hidden/observed context `X` raises both `A` and `B` without a true planted directional dependence between them. Predictive-asymmetry estimation should be checked for spurious flow.

**D6 — non-stationary drift.** Change the transition regime over time to determine when a single aggregated flow becomes misleading.

### 7.4 DHD capability gate

DHD remains blocked for production use until both conditions hold:

1. predictive asymmetry can be estimated with acceptable uncertainty at realistic support levels;
2. the resulting gradient/curl/harmonic decomposition recovers the planted longitudinal distinctions under controlled semantic fixtures and remains interpretable under perturbation.

Even if those tests pass, the output remains directional association structure. It does not become causal authority.

## 8. Stress dimensions and capability boundary

For each capability family, vary one factor at a time before testing interactions:

- Semantic Block count / observation density;
- unrelated distractor count;
- embedding noise magnitude;
- paraphrase variation;
- hubness / anisotropy;
- cluster density imbalance;
- block dropout / missing observations;
- timing jitter and lag spread;
- event-frequency imbalance;
- invalidation / supersession where relevant;
- for DHD, minimum repeated-state support and context imbalance.

Report a response curve rather than one magic threshold whenever possible.

The desired result is a capability boundary of the form:

```text
under conditions X/Y/Z -> reliable enough for candidate generation
near boundary B -> unstable / UNKNOWN
beyond boundary C -> do not use
```

## 9. Failure attribution

Every controlled miss must be classified before changing any algorithm:

```text
fixture does not encode the intended relation
  -> fixture failure

semantic text encodes it, embedding does not preserve it
  -> representation failure

embedding contains the structure, supplier misses it
  -> algorithm/application failure

supplier finds it, downstream bounded interpretation rejects it
  -> product-value failure

controlled tests pass, real corpus lacks sufficient occurrences
  -> prevalence / data-density limitation
```

Do not tune the algorithm to compensate for a representation failure without first proving that such compensation is legitimate.

## 10. Incremental-value ladder

Every candidate must beat the simplest sufficient predecessor on the exact same frozen fixture set:

```text
current kNN/cosine
  -> MST / union-find
  -> persistent homology
  -> Hodge-Laplacian spectrum
```

DHD is evaluated on the separate directional-flow fixture family because its input contract differs.

Complexity is justified only by incremental information useful to the existing structure consumer.

## 11. Blind semantic verification

When a supplier emits a bounded structure candidate, downstream verification should hide algorithm identity and mathematical prestige language where possible.

The interpreter receives:

- supporting Semantic Blocks;
- authorized source closure;
- neutral structural facts needed for judgment;
- temporal placement where relevant.

It should not be primed with labels such as `persistent homology`, `Hodge`, `topological`, or `spectral` during comparative semantic scoring.

This tests product value rather than model deference to sophisticated terminology.

## 12. Real-corpus phase

Only suppliers that pass controlled capability and stress-boundary tests proceed to the preserved LCE corpus.

The real-corpus phase asks:

- does this structural signal actually occur often enough to matter?;
- does it recover known historical events without inflating candidate volume?;
- does it add useful candidates to the existing kNN/cosine supplier?;
- does blind bounded interpretation precision improve?;
- is the runtime/memory cost justified by observed prevalence and value?

Absence of a signal in the real corpus does not invalidate the algorithm. It may simply mean the capability is not relevant enough to this product/data distribution to justify production code.

## 13. Stop rules

- **MST/H0:** keep only if merge-scale/bridge information improves on the current neighbourhood detector.
- **PH:** keep only if cross-scale persistence/localization improves robustness or semantic candidate precision beyond MST/kNN.
- **Hodge Laplacian:** keep only if non-zero edge-space spectral structure distinguishes useful cases that PH and node statistics miss.
- **DHD:** do not proceed beyond controlled research unless a justified repeated directional observable can be estimated with adequate support and uncertainty.

A negative result is a successful outcome when it removes an unnecessary supplier.

## 14. Architecture boundary

No fixture, detector, or result in this study creates a new architectural layer.

The product chain remains:

```text
Semantic Blocks / authorized longitudinal inputs
  -> structure discovery supplier
  -> existing structure product
  -> HigherOrderCandidate
  -> bounded LLM verification
```

The experiment determines which suppliers deserve to exist. It does not pre-authorize new abstractions.