# Structure Discovery Failures, Boundaries, and Owner Hypotheses

**Date:** 2026-09-11  
**Status:** Research record — experimental failures and hypotheses; not production authority

## 1. Purpose

This document records what the 2026-09-11 structure-discovery experiments actually falsified, what remains plausible, and which new owner hypotheses were raised after reviewing the failures.

The main lesson is methodological:

> A mathematical algorithm can be correct while the representation supplied to it encodes the wrong object.

Future experiments must therefore distinguish algorithm capability, representation legality, and real-data signal availability.

## 2. Three-tier audit rule

All future mathematical suppliers for LCE should be evaluated through three separate tiers.

### Tier 1 — Operator capability

Question:

> Given a mathematically valid input containing the claimed structure, does the implementation recover that structure and its counterexamples correctly?

Use simple synthetic positive and negative controls.

This tier verifies the operator and its implementation. It does not establish LCE product value.

### Tier 2 — Representation legality

Question:

> Does the LCE path from historical text/events to the mathematical input preserve the structure the operator requires, without smuggling the desired result into graph, edge, face, cluster, or state construction?

Examples of illegal or suspect representation shortcuts include:

- treating pairwise similarity triangles as independently observed semantic 2-simplices;
- creating a canonical semantic-state ontology only to make a directional algorithm runnable;
- forcing Level-2 text to produce a desired geometric configuration;
- assuming one cross-domain synthesis must correspond to one Semantic Block.

### Tier 3 — Signal availability / temporal horizon

Question:

> If the operator is capable and the representation is legal, has the real longitudinal history accumulated enough support for the structure to be estimable?

A current lack of repeated support is not equivalent to algorithm failure. For longitudinal statistics, the corpus grows one way through time and may enter the operating region later.

## 3. kNN / cosine — failure boundary, not total rejection

### Experimental failure

Controlled bridge fixtures showed that fixed local kNN/cosine neighbourhoods are poor at cross-region bridge localization. Tight thresholds miss intermediate bridge points; loose thresholds can join large portions of the anisotropic embedding cone. kNN also lacks a natural critical-edge or responsible-arrival notion.

### What this does not prove

The experiment did not show that kNN is useless as a local supplier.

### Current capability placement

```text
kNN / cosine
    -> cheap local-proximity proposal
    -> local ego-neighbourhood / related-block retrieval
    -> NOT primary bridge/reconnection detector
```

The owner hypothesis is that kNN remains useful in narrow local contexts and should be evaluated against tasks it is structurally suited to, rather than judged by bridge performance alone.

## 4. Multi-Scale Stability — why early merging occurs

### Observed failure

Multi-scale threshold sweeps sometimes merged regions before the planted bridge event and lost bridge localization under distractors.

### Mechanism

As the allowed distance scale grows, any short path through intermediate points can join two components. Background points or hubs may therefore create an accidental chain before the intended bridge appears.

This is a percolation / chaining failure mode:

```text
A -- noise1 -- noise2 -- noise3 -- B
```

may become connected at an intermediate scale even when the intended bridge `C` is absent.

### Two-sided data-density hypothesis

The owner raised a second possibility: insufficient observations can also make structure unclear.

The current hypothesis is therefore two-sided:

```text
too sparse
    -> incomplete / unstable structure

too dense or noisy
    -> premature component percolation
```

Multi-scale stability may still be useful for answering whether a local group survives nearby scale choices. It should not be treated as a precise responsible-bridge detector.

## 5. MST — algorithmic capability survived, prevalence claim did not

### What survived

Controlled geometric and controlled-semantic fixtures established that MST / union-find can recover bridge/reconnection structure when the vector representation contains a usable bridge. R2 also corrected the oracle distinction between responsible arrivals, critical edges, critical paths, and articulation vertices.

### What failed

R1 inferred high real-corpus bridge prevalence from decreasing MST edge lengths as the corpus grew. R2 null controls showed this was largely ordinary point-cloud densification rather than evidence of unusually frequent chronological synthesis.

### Corrected interpretation

```text
MST capability = supported
real diary bridge prevalence = low under current representation
```

The latter does not yet establish that the underlying human cognition lacks bridge events.

## 6. Owner hypothesis — semantic segmentation may destroy bridge structure

The owner proposes that low real-corpus bridge prevalence may partly be an upstream representation failure.

### Hypothesis

Semantic segmentation may be hostile to cross-domain synthesis because a bridge often spans semantic domains by definition.

If a bridge is cut too finely:

- one part may be absorbed toward domain A;
- another part may be absorbed toward domain B;
- no independent bridge node remains.

If cut too coarsely:

- the bridge relation may be diluted by dominant local context.

A second, stronger hypothesis is that a real synthesis may not correspond to one node at all. It may be distributed across a short episode:

```text
A -- C1 -- C2 -- C3 -- B
```

where no single `Ci` is a complete semantic bridge.

### Consequence

The next representation experiment should be a segmentation / granularity ablation, not another bridge algorithm search.

Compare the same raw evidence under:

- sentence / utterance units;
- current Semantic Blocks;
- coarser semantic episodes;
- overlapping 2/3/4-block windows;
- temporary pooled local representations.

Freeze embedding and downstream supplier while varying segmentation.

The core question is:

> At what representation granularity does real cross-domain synthesis become recoverable?

## 7. Persistent Homology H0 — redundant with MST in the tested setting

For Vietoris-Rips filtration over the same metric space, H0 component merge/death information corresponds to single-linkage connectivity and MST merge scales.

The H0-vs-MST comparison therefore serves mainly as an implementation sanity check, not as evidence of two distinct product capabilities.

Current decision:

```text
PH-H0 = REDUNDANT for current LCE structure discovery
```

## 8. Persistent Homology H1 — semantic cycle and geometric hole are different objects

### Failure pair

R2 produced a useful positive/negative contrast:

1. a natural semantic feedback relation can have `H1 = 0` because all three pairwise proximity edges appear and the Vietoris-Rips complex immediately fills the triangle;
2. semantically unrelated high-dimensional points can produce a substantial H1 bar because their geometry leaves an unfilled void.

Therefore:

```text
semantic cycle
    !=
metric-space topological hole
```

### Why this is a representation mismatch

PH-H1 is correctly answering a geometric/topological question. LCE was asking it to stand in for a relational-semantic question.

The failure is not that PH mathematics is wrong. The current vector-to-Vietoris-Rips representation does not provide a stable mapping from cognitive feedback/circular relation to topological H1.

### Current decision

```text
PH-H1 = REJECT for current semantic-vector / Vietoris-Rips LCE use
```

This decision can be reopened only if the upstream representation changes in a way that supplies a justified relational complex rather than ordinary embedding proximity.

## 9. Predictive Directional Flow — temporal sparsity is an operating boundary, not a refutation

### Supported result

Controlled and Level-2 tests showed that non-LLM predictive asymmetry can recover repeated directional association under sufficient support while correctly returning UNKNOWN for many weak/symmetric cases.

The important output is an operating surface, not one fixed `N_min`:

```text
support
x effect size
x uncertainty
-> usable / UNKNOWN
```

### Owner hypothesis — one-way corpus growth increases future value

LCE history accumulates monotonically. A relation with insufficient support today may become estimable later.

This makes predictive flow qualitatively different from a static geometry detector: the capability can mature as the longitudinal corpus grows.

The owner hypothesis is that predictive directional statistics may become a foundation for later higher-order longitudinal structure, including:

- directional stability;
- repeated transition motifs;
- regime duration;
- direction reversal;
- change points;
- workflow or reasoning-state transitions after bounded semantic interpretation.

This remains a research hypothesis, not production authority.

## 10. Regime shift — near-zero global flow can itself contain structure

A global flow near zero is ambiguous.

It may mean true symmetric/null association:

```text
window 1 ~ 0
window 2 ~ 0
window 3 ~ 0
```

or cancellation of opposing regimes:

```text
window 1 > 0
window 2 > 0
window 3 < 0
window 4 < 0
```

Therefore:

```text
global flow ~ 0
```

must not automatically be interpreted as no signal.

A candidate regime shift should require evidence such as:

- sufficient windowed support;
- materially nonzero local flows;
- sign reversal;
- high temporal variance relative to an appropriate null;
- robustness to reasonable window choices.

Only downstream bounded interpretation may describe the semantic meaning as preference change, workflow reversal, model revision, or another process.

## 11. Discrete Hodge Decomposition — capability and input legality must be separated

### R2 finding

The same planted circulation changed dramatically depending on edge-window construction and whether graph triangles were filled as 2-simplices. A 4-cycle can appear harmonic in a graph-only complex and curl/coexact-dominant after lag-generated chords and clique completion.

Therefore DHD is not discovering a representation-independent property of historical text. It decomposes the edge flow on the supplied complex.

### Owner hypothesis — test capability with explicit counterexamples first

Before asking whether DHD is useful to LCE, establish its implementation boundary on mathematically clean inputs:

```text
pure potential flow
    -> gradient-dominant

filled triangle circulation
    -> coexact/curl-dominant

unfilled 4-cycle circulation
    -> harmonic-dominant

same edge flow + different face filling
    -> deliberately different decomposition
```

These tests prove operator capability and construction dependence separately.

### Representation legality blocker

LCE currently lacks an independent authority for deciding which triangles represent legitimate semantic 2-simplices.

A face does not become semantically real merely because three pairwise edges exist.

Possible future legitimate sources could include independently observed typed multi-way interaction, verified workflow closure, explicit relational schema, or another bounded non-self-confirming source. Causality is not required; independent justification is.

Current decision:

```text
DHD = DEFER at representation-legality boundary
```

## 12. Authored essays as higher-order ground truth

The owner proposed using recently written essays as a stronger benchmark corpus.

The essays often form a larger argument by connecting variables from apparently unrelated domains through repeated deeper logical relations. This directly targets the desired LCE ability better than simple proximity recovery.

The proposed benchmark is:

```text
pre-article historical fragments
    -> LCE candidate higher-order structure
    -> later completed article as held-out author logic
```

The completed article must be withheld from retrospective/prospective discovery and used only as evaluation authority.

The benchmark should distinguish:

- recovery from a finished article whose evidence is all present;
- retrospective discovery from pre-article history;
- prospective discovery before the author explicitly states the relation.

Detailed protocol is defined in:

`docs/research/LCE_AUTHOR_LOGIC_HELDOUT_BENCHMARK_PLAN_2026-09-11.md`.

## 13. Updated research order

The current research sequence is:

```text
1. verify operator capability and counterexamples
2. audit representation legality
3. audit segmentation / representation granularity
4. measure real signal prevalence / temporal horizon
5. compare bounded downstream value
6. only then consider production integration
```

For the immediate next phase:

```text
article oracle + segmentation ablation
    -> locate where known human higher-order structure is lost
    -> only then decide whether another representation or supplier is needed
```

No new structure-discovery algorithm is currently justified by the failures above.
