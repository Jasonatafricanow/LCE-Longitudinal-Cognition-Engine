# LCE Structure Discovery Algorithm Specification

**Date:** 2026-09-11  
**Status:** Research specification only — no implementation authorized  
**Depends on:** `docs/superpowers/specs/2026-09-11-structure-discovery-supplier-design.md`

## 1. Research question

The architecture is already fixed:

```text
Semantic Blocks + vectors
        -> structure discovery
        -> structure product
        -> HigherOrderCandidate
        -> bounded LLM interpretation / re-verification
```

This study asks only which algorithms are useful suppliers of the existing `structure discovery` stage.

The target is not to maximize the number of detected patterns. The target is to find reproducible structural information that:

1. is not merely an artifact of one arbitrary neighbourhood threshold;
2. adds useful information beyond the current cosine / k-neighbourhood supplier;
3. can be traced back to bounded Semantic Blocks and source evidence;
4. improves downstream bounded interpretation rather than only producing more candidates;
5. can be rejected with no architecture change if it adds no value.

The previous STRUCTURE-06R result remains binding negative evidence: raw H1 counts existed but showed no useful semantic signal. Therefore this study must not repeat `count loops -> call them cognition`.

## 2. Existing baseline

The current supplier computes local cosine neighbourhoods at configured `k` values and a minimum similarity threshold, then derives:

- support score;
- neighbourhood stability across snapshots;
- local overlap;
- multi-point participation;
- temporal dates;
- snapshot diffs including new members, loss/weakening, stronger support, reconnection, reorganization, and linked structures;
- bounded higher-order candidates from overlap and/or centroid similarity.

This is the baseline that every new method must beat or complement.

The current baseline is deliberately retained because a new mathematical method should not be credited for information that a simpler graph operation already exposes.

## 3. Strong simple control: multiscale connectivity / MST

Before testing topological methods, establish a stronger simple control than the current fixed-threshold neighbourhood detector.

### 3.1 Why this control is required

For a Vietoris-Rips filtration, zero-dimensional persistent homology is equivalent to single-linkage connectivity, and its finite death scales are determined by minimum-spanning-tree edges. Therefore, if the only useful result from persistent homology is `previously separate regions become connected at scale x`, then a full persistent-homology dependency is unnecessary.

### 3.2 Input

Use the same cutoff-bounded Semantic Block vectors as all other suppliers.

Normalize each non-zero vector and derive chord distance:

```text
d(u, v) = sqrt(2 * (1 - cosine(u, v)))
```

This preserves cosine-neighbour ordering while producing a proper Euclidean metric on normalized vectors. Do not mean-center, whiten, reduce dimension, or change the embedding model in the first comparison; those would confound representation changes with algorithm changes.

### 3.3 Output signal

Compute an MST / union-find merge sequence and derive only structural observations relevant to LCE:

- component merge scale;
- bridge edge(s) responsible for a merge;
- whether a newly visible block causes a merge that did not exist at the previous cutoff;
- merge-scale robustness under small input perturbation / dropout.

This is an algorithmic control, not a new product type.

### 3.4 Falsification criterion

If persistent-homology H0 contributes no useful downstream information beyond this control, retain the simpler MST/union-find supplier and discard PH-H0 as redundant.

## 4. Candidate A — Vietoris-Rips persistent homology

### 4.1 Product question

Can multiscale topology identify structural events that the current fixed-k/fixed-threshold supplier misses, especially:

- cross-scale stable separation / reconnection;
- closure or cycle-like organization;
- structural features that survive a meaningful range of distance scales rather than appearing at one threshold?

### 4.2 Input representation

At each historical cutoff:

1. take the exact current-valid Semantic Block states visible at that cutoff;
2. use the same frozen embedding identity as the baseline;
3. normalize vectors;
4. compute the chord-distance matrix above;
5. build a Vietoris-Rips filtration.

Initial experiment computes only H0 and H1. H2+ is excluded until H0/H1 demonstrate incremental value.

The first run should keep the filtration bounded to the distance range corresponding to the existing semantic-neighbourhood regime. With current `min_similarity = 0.75`, the equivalent chord-distance cap is:

```text
sqrt(2 * (1 - 0.75)) ~= 0.70710678
```

Features still alive at the cap are treated as censored rather than assigned an invented death scale.

### 4.3 H0 interpretation

H0 is not treated as a novel topological feature by default. It is compared directly against the MST / union-find control.

Useful H0 evidence would be limited to cases where multiscale component lineage produces downstream information that the simpler control does not already represent cleanly.

### 4.4 H1 interpretation

The previous failed experiment used the existence/count of H1 as if that alone might be informative. This study instead tests persistence and localization.

For every H1 interval:

```text
persistence = death - birth
```

Record:

- birth scale;
- death scale;
- persistence lifetime;
- whether the interval survives small vector perturbations / block dropout;
- representative cocycle support, when available;
- supporting Semantic Block IDs inferred from non-zero representative-cocycle edges;
- cutoff at which the feature first appears;
- whether a corresponding feature can be matched to the previous cutoff.

Representative cocycles are localization aids, not canonical identities. A cocycle representative is not automatically a unique or minimal semantic cycle.

### 4.5 Cross-cutoff comparison

Compute a persistence diagram independently for each cutoff. Compare consecutive diagrams with bottleneck matching/distance.

A temporal candidate is interesting only when diagram change can be associated with bounded supporting blocks, for example:

- a new persistent H1 feature appears after one or more new Semantic Blocks enter;
- a previous persistent feature disappears after invalidation/supersession;
- a feature changes lifetime materially while retaining substantial support overlap.

Do not introduce zigzag persistence in the first experiment. Snapshot comparison is already available and is sufficient to test whether ordinary PH adds value. Zigzag or other dynamic topology is considered only if deletions/invalidation create a demonstrated failure that independent snapshot matching cannot represent.

### 4.6 What would count as incremental value

PH is useful only if at least one of these is observed reproducibly:

- a semantically meaningful candidate missed by current kNN and MST controls;
- materially better rejection of threshold-specific noise;
- a stable cycle/closure structure whose downstream bounded interpretation is reproducibly useful;
- improved discrimination between a persistent structural event and background dense-space connectivity.

Producing more H1 bars or more candidate structures is not success.

## 5. Candidate B — Hodge Laplacian / simplicial spectral analysis

### 5.1 Product question

Can edge-space or simplicial spectral structure reveal coherent multi-point organization that node-neighbourhood statistics and persistent homology do not capture well?

### 5.2 Required distinction

The Hodge Laplacian is not itself the same thing as Hodge decomposition.

For a simplicial complex with boundary matrices `B_k`, the k-th combinatorial Hodge Laplacian is:

```text
L_k = B_k^T B_k + B_{k+1} B_{k+1}^T
```

For k=0 this reduces to the ordinary graph-Laplacian family. For k=1 it acts on edges and combines lower adjacency through vertices with upper adjacency through filled triangles.

The kernel dimension of `L_k` recovers the corresponding Betti number. Therefore, using only Hodge-Laplacian nullity would largely duplicate ordinary homology and is not sufficient justification for this candidate.

The only plausible incremental value is in the **non-zero spectrum and eigenvector localization**.

### 5.3 Complex construction

Hodge analysis requires a simplicial complex. LCE does not have independently observed multi-way relations; it has vectors and pairwise proximity.

Therefore every triangle/tetrahedron produced from a Vietoris-Rips or clique complex must be described as:

> higher-order geometry induced from pairwise proximity

not as independently observed higher-order semantic interaction.

For the first experiment, build only the 2-skeleton needed for `L_1` from the same proximity filtration / sparse graph used by the PH comparison. Do not infer a separate semantic hypergraph.

### 5.4 Signals to test

At a small pre-registered set of filtration scales, compute `L_1` and inspect:

- smallest non-zero eigenvalues;
- spectral gaps;
- localization of low-frequency edge eigenvectors;
- whether localized edge modes identify stable block sets not recovered by node-space neighbourhoods;
- stability of these modes across nearby scales and adjacent temporal cutoffs.

Any edge-mode candidate is converted back to a bounded set of participating Semantic Block IDs before the LLM consumer sees it.

### 5.5 Falsification criterion

Reject Hodge-Laplacian analysis if:

- useful information is limited to Betti/nullity values already available from PH;
- low-frequency modes are unstable across nearby scales;
- candidate localization mostly reflects graph density/hubs;
- downstream interpretation quality does not improve relative to simpler controls;
- computational cost is disproportionate to incremental signal.

### 5.6 Persistent Laplacian note

Persistent Laplacians combine filtration-scale topology with non-harmonic spectral information. They are mathematically relevant because their null spaces recover persistent topological invariants while non-zero spectra may contain additional geometry.

They are **not** a first-phase candidate. If ordinary Hodge-Laplacian spectral information proves useful but too threshold-sensitive, then persistent Laplacian becomes a justified follow-up. Do not add it merely because the method exists.

## 6. Candidate C — discrete Hodge decomposition

### 6.1 Product question

Can an observed directional relation signal be decomposed into globally consistent, locally cyclic, and globally cyclic components that help LCE distinguish trajectory-like structure from feedback-like structure?

### 6.2 Current blocker

Discrete Hodge decomposition does not operate on an unlabelled point cloud alone. It requires a meaningful **edge flow**: an antisymmetric scalar signal on oriented edges.

Current LCE structure discovery has:

- symmetric vector similarity;
- temporal ordering;
- local membership and overlap;
- snapshot change.

It does **not** currently have a naturally authoritative edge-flow quantity.

This matters. Inventing a flow merely to make the decomposition runnable would inject the desired interpretation into the input.

### 6.3 Rejected first-pass flow constructions

Do not use any of the following without independent justification:

- `older -> newer` with similarity as flow magnitude: this is likely dominated by the time potential and can collapse into a mostly trivial gradient component;
- arbitrary vector-coordinate projection as edge flow: basis-dependent and semantically ungrounded;
- an LLM-assigned causal/attribution score: this would move language interpretation before structure discovery and violate the LLM-last evidence boundary;
- algorithmic confidence differences treated as flow: this measures the detector, not the historical relation.

### 6.4 Status

Discrete Hodge decomposition is therefore **BLOCKED, not rejected**.

It should be re-opened only when LCE or an authorized upstream source contains a real directional edge observable, for example an independently recorded transition, preference comparison, influence measurement, or other non-LLM-derived antisymmetric relation.

At that point the decomposition can test whether the observed flow is predominantly:

```text
gradient  -> globally potential-like / order-consistent
curl      -> locally cyclic
harmonic  -> locally curl-free but globally cyclic
```

Until then, no experiment is authorized because the required input signal is missing.

## 7. Experimental controls

All active candidates must be tested against the same frozen data and controls.

### 7.1 Synthetic structural fixtures

Create small hand-checkable fixtures before touching the real corpus:

1. two separated groups joined by one new bridge point — MST/H0 should detect the merge;
2. open chain becoming a robust ring — H1 should appear;
3. three mutually close points forming a filled 2-simplex — graph cycle exists but H1 should be zero after triangle filling;
4. noisy short-lived loop — persistence should be low / unstable;
5. two overlapping local structures sharing one point — detector must not force exclusive membership.

These fixtures test mathematics, not semantics.

### 7.2 Historical corpus

Reuse the frozen LCE historical vectors/cutoffs where possible, including the known INSPIRATION-05 and STRUCTURE-06R cases:

- 14/30/41-day prefix replay;
- the three previously isolated points that later reconnected;
- known giant-region / noise-floor behaviour;
- prior H1 negative evidence.

The new methods must explain whether they add information to those already preserved results rather than overwriting the earlier interpretation.

### 7.3 Temporal negative control

Shuffle temporal placement while preserving the same vector set/cardinality profile. Re-run candidate emergence.

A method that produces equally coherent longitudinal emergence under shuffled order has weak evidence that it is measuring longitudinal structure rather than static geometry.

### 7.4 Perturbation robustness

For each candidate structure, test small controlled perturbations such as:

- low-rate block dropout;
- small bounded vector perturbation followed by renormalization;
- nearby scale choices.

A candidate that exists only at one exact numerical setting is weak structural evidence.

### 7.5 Blind downstream interpretation

For comparative evaluation, the bounded LLM interpreter should not be told which algorithm produced a candidate. Candidate order should be randomized.

Algorithm identity remains in audit metadata but is hidden from semantic judgment where possible. This reduces the chance that words such as `topological`, `persistent`, or `Hodge` bias the interpreter toward treating a mathematically sophisticated result as semantically important.

The interpreter remains bounded to the supplied Semantic Blocks/source closure and cannot search freely for support.

## 8. Evaluation metrics

Do not optimize one aggregate score. Record a compact evidence matrix:

- **known-event recovery** — does the supplier recover hand-checkable synthetic and historical structural events?;
- **incremental candidate yield** — candidates not already represented by the current kNN/MST controls;
- **bounded interpretation precision** — fraction of candidates judged semantically coherent/useful versus weak/rejected/UNKNOWN under the same blind interpreter;
- **candidate volume** — more output is a cost unless precision improves;
- **robustness** — survival under small perturbation, dropout, nearby scale, and adjacent cutoff;
- **temporal specificity** — degradation under shuffled-order control;
- **redundancy** — overlap with existing supplier outputs;
- **source locality** — ability to map a structural result back to bounded supporting block IDs;
- **runtime / memory cost** — measured separately, not hidden inside semantic quality.

A useful method should improve the information available to the downstream consumer, not merely increase mathematical descriptor count.

## 9. Priority order

The research order is intentionally conservative:

```text
P0 current kNN/cosine baseline
P1 multiscale MST / union-find control
P2 persistent homology H0/H1
P3 Hodge L1 spectral analysis, only if P2 leaves a real higher-order gap
P4 discrete Hodge decomposition, only after a meaningful edge-flow observable exists
```

The order matters because each later method must justify complexity that the earlier, simpler method could not supply.

## 10. Decision table

| Method | Current fit | Main possible value | Main risk | Initial status |
| --- | --- | --- | --- | --- |
| Current kNN/cosine | direct | local overlap/stability/reconnection baseline | threshold/k dependence, dense-space noise | baseline |
| MST / union-find | very direct | threshold-free merge/bridge scale control | single-linkage chaining, no H1 structure | test first |
| Persistent homology | strong | cross-scale H0/H1 persistence and cycle/closure evidence | complex explosion, density effects, hard feature localization | active candidate |
| Hodge Laplacian L1 | conditional | non-zero edge-space spectral modes / higher-order geometry | depends on inferred complex; may duplicate PH | second-line candidate |
| Discrete Hodge decomposition | currently weak | distinguish gradient/curl/harmonic edge-flow structure | no justified edge-flow signal today | blocked |
| Persistent Laplacian | conditional follow-up | multiscale spectral information beyond PH | additional complexity before need is proven | deferred |

## 11. External references inspected

- GUDHI Rips-complex and persistent-cohomology documentation: https://gudhi.github.io/ripscomplex/ and https://gudhi.github.io/introduction/
- Ripser / Ripser.py persistent homology and representative cocycles: https://arxiv.org/abs/1908.02518 and https://ripser.scikit-tda.org/en/latest/
- Jiang, Lim, Yao, Ye, `Statistical ranking and combinatorial Hodge theory`, Mathematical Programming 127 (2011): https://doi.org/10.1007/s10107-010-0419-x
- Schaub et al., `Random Walks on Simplicial Complexes and the Normalized Hodge 1-Laplacian`, SIAM Review 62 (2020): https://doi.org/10.1137/18M1201019
- Mémoli, Wan, Wang, `Persistent Laplacians: properties, algorithms and implications`, SIAM Journal on Mathematics of Data Science 4 (2022): https://doi.org/10.1137/21M1435471

## 12. Research boundary

The strongest current conclusion is not that all three proposed methods should be implemented.

It is:

- persistent homology is worth a controlled experiment, but H0 must beat the simpler MST control and H1 must improve on the already-failed raw-H1-count idea;
- Hodge-Laplacian spectral analysis is plausible only as a second-line test for edge-space structure not captured by PH or current neighbourhood statistics;
- discrete Hodge decomposition is not yet well-posed for current LCE inputs because there is no justified edge-flow signal;
- architecture remains unchanged regardless of these outcomes.

A negative experiment that deletes a candidate algorithm from the roadmap is a successful research result.