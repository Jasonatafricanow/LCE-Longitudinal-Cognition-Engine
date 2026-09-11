# LCE Decision Evolution Addendum — Structure Discovery Capability Audit

**Date:** 2026-09-11  
**Scope:** Addendum to `LCE_DECISION_EVOLUTION.md`; research evolution only, not a new production authority

## A1. Why did algorithm evaluation become a representation audit?

**Problem.** Early structure-discovery evaluation risked interpreting any algorithmic miss as evidence that the mathematical method was unsuitable for LCE.

**Evidence.** The 2026-09-11 capability experiments produced different failure types:

- kNN failed controlled bridge localization while remaining plausible as a local-neighbour supplier;
- MST recovered planted bridge structure when the representation contained it, while the real diary showed low chronological bridge prevalence after null controls;
- PH-H1 correctly detected metric-space holes that did not correspond reliably to semantic cycles;
- predictive flow worked under repeated support but current diary data often remained below its support boundary;
- DHD output changed materially when edge and 2-simplex construction changed.

**Failed assumption.** If an algorithm is mathematically sound and returns a structure, the returned structure has the product meaning we hoped for; conversely, if real data does not trigger the method today, the algorithm itself lacks the capability.

**Decision.** Separate future evaluation into three tiers:

```text
Tier 1 — Operator capability
Does the mathematical implementation recover known positive and negative cases?

Tier 2 — Representation legality
Does LCE actually supply the mathematical object the operator requires without smuggling interpretation into the input?

Tier 3 — Signal availability / temporal horizon
Has the real longitudinal corpus accumulated enough support for the capability to become observable?
```

**Consequence.** Future claims must identify the earliest failing tier. `algorithm failure`, `representation failure`, and `insufficient longitudinal support` are not interchangeable conclusions.

## A2. Why was low real MST bridge prevalence not accepted as proof that cognition lacks bridge events?

**Problem.** R2 null controls showed that chronological diary arrivals did not produce unusually large MST bottleneck improvements relative to random densification.

**Evidence.** Controlled semantic fixtures still showed that bridge geometry, when present in Semantic Block embeddings, was recoverable by MST. The real-corpus prevalence result therefore sits downstream of semantic segmentation and embedding.

**Failed assumption.** The current Semantic Block representation necessarily preserves every cross-domain synthesis as one recoverable bridge node.

**Owner hypothesis.** Segmentation may destroy bridge structure. A synthesis may be split into fragments pulled toward different domains, diluted inside a coarse block, or distributed across a short sequence rather than represented by one node.

**Decision.** Before searching for another bridge algorithm, run segmentation / representation-granularity ablations over frozen raw evidence:

```text
sentence / utterance
current Semantic Block
coarser semantic episode
overlapping local windows
temporary pooled local representation
```

Freeze embedding and supplier while varying the representation.

**Consequence.** MST becomes useful not only as a candidate detector but as a diagnostic for upstream representational fidelity: if a known bridge exists in raw evidence but appears only under some segmentation policies, the failure belongs upstream of MST.

## A3. Why was PH-H1 rejected for the current vector-Vietoris-Rips route?

**Problem.** LCE wanted a detector for cognitive circular/feedback structure and tested whether topological H1 over embedding proximity could serve that role.

**Evidence.** A natural semantic feedback relation can become a filled triangle in a Vietoris-Rips complex and therefore have `H1 = 0`, while semantically unrelated high-dimensional points can form an unfilled geometric void with substantial H1 persistence.

**Failed assumption.** A semantic cycle is represented as a topological hole in ordinary embedding proximity geometry.

**Decision.** Reject PH-H1 for the current semantic-vector / Vietoris-Rips structure-discovery path. This is a representation-product mismatch, not a claim that persistent homology is mathematically invalid.

**Consequence.** PH-H1 may be reconsidered only if a future upstream representation provides a justified relational complex where the topological object corresponds to the relation being queried.

## A4. Why did predictive flow remain interesting despite sparse current data?

**Problem.** The diary corpus often lacked enough repeated transitions to estimate stable directional asymmetry.

**Evidence.** Controlled and Level-2 experiments showed an operating surface in which stronger directional effects become recoverable with modest repeated support, while weak/symmetric cases can remain UNKNOWN.

**Failed assumption.** A current support shortage implies the method is irrelevant to the future system.

**Owner hypothesis.** Longitudinal history grows monotonically. Predictive directional structure can therefore mature over time and may later support direction stability, reversal, change points, and repeated relational motifs.

**Decision.** Keep predictive flow as a research candidate whose output is gated by support and uncertainty rather than by one universal `N_min`.

**Consequence.** `global flow ~ 0` must remain ambiguous until windowed behaviour is examined. Stable near-zero windows and sign-cancelling regime shifts are different structural cases.

## A5. Why was DHD frozen at the representation-legality boundary?

**Problem.** Discrete Hodge decomposition requires an edge flow over a graph/simplicial complex, but LCE does not yet possess independent semantic authority for all edges and especially for 2-simplices.

**Evidence.** The same planted circulation changed from harmonic-dominant to coexact/curl-dominant when lag-window edges and triangle filling changed.

**Failed assumption.** Clique completion of pairwise semantic proximity is a neutral preprocessing step.

**Decision.** First verify DHD on mathematically explicit capability counterexamples:

```text
pure potential flow -> gradient-dominant
filled triangle circulation -> coexact/curl-dominant
unfilled 4-cycle circulation -> harmonic-dominant
same edge flow + changed face policy -> changed decomposition
```

Then separately ask whether LCE can supply a defensible complex. Pairwise closeness alone does not authorize a semantic face.

**Consequence.** DHD remains deferred. Its blocker is not operator mathematics but representation legality.

## A6. Why did authored essays become the next benchmark target?

**Problem.** Synthetic fixtures establish capability boundaries but do not fully test the desired LCE behaviour: recovering a larger logic that later unifies apparently unrelated variables through repeated deeper relations.

**Owner observation.** Recent authored essays provide a natural human-generated target. Their final arguments often connect locally distinct examples or variables because the author recognizes a shared logical structure.

**Decision.** Use completed essays as held-out author logic while withholding them from discovery. Compare LCE candidates generated from pre-article history against the relations the author later independently retained in the article.

Three benchmark strengths are distinguished:

```text
Level 1 — recover structure from a de-cued / resegmented completed article
Level 2 — retrospectively recover later article structure from pre-article history
Level 3 — prospectively surface the relation before the author first states it explicitly
```

Detailed protocol:

`docs/research/LCE_AUTHOR_LOGIC_HELDOUT_BENCHMARK_PLAN_2026-09-11.md`

**Consequence.** The next research question is no longer “which more advanced algorithm should be added?” It is:

> At which stage does known human higher-order structure disappear: source availability, segmentation, embedding representation, supplier capability, or temporal support?

## A7. Current research order

```text
operator capability / counterexamples
    -> representation legality
    -> segmentation and granularity ablation
    -> temporal support / prevalence
    -> bounded downstream value
    -> only then production integration
```

This addendum does not alter the frozen V1 production authority or the rule that new algorithms remain suppliers of the existing structure-discovery responsibility unless a proven product-semantic mismatch requires otherwise.
