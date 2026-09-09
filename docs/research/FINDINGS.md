# LCE Findings and Negative Results

This file indexes the claims that most directly shaped LCE architecture. It is organized by **finding**, not chronology.

Each entry separates:

```text
Finding
Evidence
What it supports
What it does not support
Architecture consequence
Status
Primary references
```

The status labels mean:

- `exploratory` — observed in research and useful for design, but not a general scientific claim;
- `engineering invariant` — runtime correctness behavior backed by closure/regression tests;
- `frozen boundary` — authority or architecture rule intentionally fixed for V1;
- `open question` — deliberately unresolved.

## F01 — Similarity discovers relatedness, not cognition

**Finding.** Vector similarity can identify candidate relatedness, but similarity alone does not authorize a claim that two items share one cognition, belief, or canonical meaning.

**Evidence.** POINTCLOUD-01 embedded 91 raw units over 14 days. Similarities formed a narrow cone around roughly `0.51..0.88`, and label propagation collapsed all 91 points to one label. POINTCLOUD-01R still produced a 48-point giant component at mutual-kNN `k=4`; one region grouped five different investment objects and bounded interpretation rejected them as one structure. The public synthetic semantic-neighbourhood experiment therefore emits `candidate_relation`, not cognition or truth.

**What it supports.** Similarity is useful as a discovery substrate for bounded candidate generation.

**What it does not support.** It does not prove that embeddings are useless, that all dense regions are noise, or that semantic relationships cannot be discovered geometrically. The narrower result is that **geometric proximity is insufficient authority for cognition identity**.

**Architecture consequence.** Similarity remains upstream and derived. Candidate geometry must pass through later semantic/authority boundaries before it can influence accepted longitudinal understanding.

**Status.** `frozen boundary`

**Primary references.** [`LCE_DECISION_EVOLUTION.md`](../history/LCE_DECISION_EVOLUTION.md), sections 1 and 5; [`semantic_neighbourhood`](../../research/experiments/semantic_neighbourhood/README.md).

## F02 — Raw text is evidence, not the corrected cognition point

**Finding.** Raw historical units are the evidence and provenance substrate, but they are too semantically mixed to serve directly as LCE's corrected cognition point.

**Evidence.** After the raw point-cloud failure, SEMANTIC-CLOUD-02 introduced a first semantic pass. The same raw corpus produced 667 semantic artifacts and 129 Semantic Blocks before embedding. Blocks retained links to artifacts and raw references.

**What it supports.** Semantic segmentation must happen before the vector/structure layer if the unit of comparison is meant to represent one bounded cognition matter.

**What it does not support.** It does not make Semantic Blocks factual Memory, nor does it claim that one specific semantic-block compiler is universally optimal.

**Architecture consequence.** The accepted representation path became:

```text
Raw Evidence → semantic artifacts → Semantic Block → embedding
```

Raw Evidence remains canonical and auditable; Semantic Blocks are downstream cognition units with source closure.

**Status.** `frozen boundary`

**Primary references.** [`LCE_DECISION_EVOLUTION.md`](../history/LCE_DECISION_EVOLUTION.md), sections 1–2; [`LCE_V1_BOUNDARIES.md`](../architecture/LCE_V1_BOUNDARIES.md).

## F03 — Semantic continuity is not equivalent to an arbitrary time bucket

**Finding.** Time is essential for ordering and longitudinal evaluation, but clock/day boundaries are not safe proxies for semantic identity.

**Evidence.** BLOCK-03 replaced day-batch compilation with semantic-stream cutting. The corpus changed from 129 to 179 blocks; mixed blocks fell from about 10 to 3–4; false regions fell from `5/16` to `0/14`; recap handling reduced an intermediate 210 blocks back to 179. Some units split at semantic switches while a long multi-unit research matter stayed intact.

**What it supports.** A cognition unit should follow semantic continuity rather than fixed temporal bins.

**What it does not support.** It does not reduce the importance of time. Cutoffs, ordering, occurrence time, replay, and historical visibility remain first-class longitudinal constraints.

**Architecture consequence.** LCE separates:

```text
semantic boundary → point identity
time boundary → ordering / visibility / replay / falsification
```

**Status.** `frozen boundary`

**Primary references.** [`LCE_DECISION_EVOLUTION.md`](../history/LCE_DECISION_EVOLUTION.md), section 3; [`LCE_V1_RUNTIME.md`](../architecture/LCE_V1_RUNTIME.md).

## F04 — Longitudinal claims require no-future evaluation and negative controls

**Finding.** A longitudinal result is not meaningful evidence of early discovery if the evaluator can see later events that were not available at the claimed cutoff.

**Evidence.** TREND-04 used six independent cutoffs, physically excluded future blocks, and ran 48 main calls. 75% of judgments said the direction was not yet visible; three directions appeared 2–6 days early; shuffle controls did not show coherent progression; one SB0034-related T3 cutoff was a real miss. The public temporal-cutoff experiment separately verifies fail-closed evidence visibility at a synthetic cutoff.

**What it supports.** No-future visibility, chronological replay, negative controls, and retained misses are necessary evaluation discipline for longitudinal claims.

**What it does not support.** It does not prove that any particular trend detector is accurate, that the three early directions generalize, or that the public synthetic cutoff experiment validates semantic trend detection.

**Architecture consequence.** Structure snapshots are cutoff-bound; future material is excluded from earlier state. Research evaluation is required to preserve misses rather than reinterpret them away.

**Status.** `engineering invariant`

**Primary references.** [`LCE_DECISION_EVOLUTION.md`](../history/LCE_DECISION_EVOLUTION.md), section 4; [`temporal_cutoff`](../../research/experiments/temporal_cutoff/README.md); [`LCE_V1_RUNTIME.md`](../architecture/LCE_V1_RUNTIME.md).

## F05 — Exclusive clustering loses legitimate multi-membership

**Finding.** A cognition point can legitimately participate in multiple local structures, so a single exclusive cluster/category assignment is an inadequate final structural abstraction.

**Evidence.** STRUCTURE-06R observed multi-point local structure at several scales. At `k=16`, 74 blocks participated in multiple of 97 groups. INSPIRATION-05 had already shown that a single giant component could absorb more than 40% of nodes.

**What it supports.** Local, overlapping, scale-dependent observations preserve information that an exclusive cluster can erase.

**What it does not support.** It does not prove that all clustering is invalid or that one specific `k` scale is universally correct.

**Architecture consequence.** V1 structures remain overlapping, local, derived observations. A point may participate in multiple observations, and higher-order reasoning must retain that source structure rather than forcing one taxonomy.

**Status.** `frozen boundary`

**Primary references.** [`LCE_DECISION_EVOLUTION.md`](../history/LCE_DECISION_EVOLUTION.md), section 6; [`LCE_V1_RUNTIME.md`](../architecture/LCE_V1_RUNTIME.md).

## F06 — Derived structures are observations, not factual authority

**Finding.** Regions, snapshots, persistence signals, higher-order candidates, Worktrees, and accepted Baselines are derived cognition artifacts; they cannot become new factual evidence by self-reference.

**Evidence.** STRUCTURE-06R recorded 3578 of 5825 `new_overlap` events as noise-floor background. H1 had no useful semantic signal. Structure-to-structure review found only 2 of 6 pairs worth attention, 4 weak analogies, and no clear common pattern. The V1 boundary explicitly prevents vectors, structures, candidates, Worktrees, or Baselines from writing themselves back as canonical Raw Evidence.

**What it supports.** Derived structure needs source closure and an explicit authority path. Attractive geometric or higher-order patterns remain proposals until bounded support/promotion rules accept them.

**What it does not support.** It does not say that accepted Baselines are meaningless. A Baseline is durable accepted LCE understanding; it is simply not factual Memory or objective truth.

**Architecture consequence.** The authority path is:

```text
derived observation
→ bounded candidate
→ authorized support
→ Worktree
→ conservative Baseline revision
```

Memory remains the factual authority outside that chain.

**Status.** `frozen boundary`

**Primary references.** [`LCE_DECISION_EVOLUTION.md`](../history/LCE_DECISION_EVOLUTION.md), sections 7–10; [`LCE_V1_BOUNDARIES.md`](../architecture/LCE_V1_BOUNDARIES.md).

## F07 — Provenance identity is not qualifying cognition-support identity

**Finding.** The exact immutable state that was interpreted and the semantic/structural change that qualifies as new cognition support are different identities and must be represented separately.

**Evidence.** Z1 reproduced provenance corruption when promotion substituted the latest block state for the historical state actually selected at a cutoff. Z2 then reproduced B4: a pure recap created a new immutable state and advanced support even though cognition-supporting content/effective structure had not meaningfully changed. R3 separated recap provenance from cognition support.

**What it supports.** Exact selected `(block_id, state_id)` provenance must survive package, Worktree, Baseline, read, restart, and rebuild, while support qualification must use candidate-relevant semantic/structural identity.

**What it does not support.** It does not mean provenance versioning should be removed. Provenance remains necessary for auditability; it simply cannot double as a support counter.

**Architecture consequence.** V1 keeps:

```text
provenance identity = exact immutable state interpreted
qualifying support identity = candidate-relevant semantic / structural change
```

**Status.** `engineering invariant`

**Primary references.** [`LCE_DECISION_EVOLUTION.md`](../history/LCE_DECISION_EVOLUTION.md), sections 13–14; [`LCE_V1_RELEASE_RECORD.md`](../../LCE_V1_RELEASE_RECORD.md).

## F08 — Replay, recap, and repeated consumption must not manufacture support

**Finding.** Reprocessing an existing cognition state, changing provenance order, or creating a recap/version must not automatically count as additional cognition support.

**Evidence.** Z2 showed that provenance-only state churn could falsely advance support. R3 changed the support fingerprint to semantic content and effective structure membership while retaining exact provenance separately. The final ordering regression added oldest/middle/newest recap permutations after earlier fixtures over-focused on the newest block path.

**What it supports.** Support must advance because of candidate-relevant semantic/structural change, not because the same evidence was replayed, re-ordered, recapped, or repeatedly consumed.

**What it does not support.** It does not prohibit legitimate new support from a later event. Genuine new candidate-relevant content can and should advance support.

**Architecture consequence.** Pure recap, duplicate source, replay, unrelated cutoff churn, duplicate local observations, and support-order permutations are normalized so they cannot create false promotion.

**Status.** `engineering invariant`

**Primary references.** [`LCE_DECISION_EVOLUTION.md`](../history/LCE_DECISION_EVOLUTION.md), sections 14 and 16; [`LCE_V1_RELEASE_RECORD.md`](../../LCE_V1_RELEASE_RECORD.md).

## F09 — Green suites are insufficient when the recovery oracle is too weak

**Finding.** A broad passing test suite does not establish recovery correctness if fixtures and interpreters do not exercise the legal state permutations that matter.

**Evidence.** Z0 rejected an implementation while ordinary tests were green. Z1/Z2 found additional defects outside focused green assertions. A reference interpreter produced a passing `30/30` recovery matrix, while a legal package-sensitive interpreter exposed `24/30`, with six unintended `OPEN/1` effects after committed results. Z3 later found that a permanent fixture always recapped the newest block and missed selected-order permutations. The final repair preserved explicit RED→GREEN history.

**What it supports.** Test design is part of the architecture when correctness depends on durable state, ordering, provenance, and legal provider behavior. Independent adversarial failures should become permanent regression authority.

**What it does not support.** It does not imply that tests are generally untrustworthy or that larger test counts are meaningless. The narrower lesson is that **coverage of semantic state space matters more than a green headline count**.

**Architecture consequence.** Recovery authority now includes package-sensitive interpreter behavior, durable state comparison, selected-state identity, Worktree status, accepted history, and varied selection ordering.

**Status.** `engineering invariant`

**Primary references.** [`LCE_DECISION_EVOLUTION.md`](../history/LCE_DECISION_EVOLUTION.md), sections 15–16; [`LCE_V1_RELEASE_RECORD.md`](../../LCE_V1_RELEASE_RECORD.md).

## F10 — Language interpretation should consume bounded evidence, not search freely for supporting evidence

**Finding.** When the same model both proposes an interpretation and searches unconstrained history for evidence that supports it, discovery, evidence selection, and interpretation authority become entangled.

**Evidence.** TREND-04 demonstrated the usefulness of model-led longitudinal probing but left the candidate model too close to evidence selection. INSPIRATION-05 therefore moved structural replay before language interpretation. The V1 runtime builds a bounded candidate package from derived structure and authorized source closure before interpretation. Read-time model reasoning is forbidden.

**What it supports.** Language models are useful inside an explicit bounded interpretation stage where the candidate package and source support are already resolved.

**What it does not support.** It does not claim that LLM reasoning should be removed from cognition systems or that models cannot discover useful hypotheses. The boundary concerns **authority and evidence selection**, not model usefulness.

**Architecture consequence.** LCE uses an LLM-last direction for durable interpretation and a deterministic, model-free read path. Current-turn free reasoning remains outside standalone LCE V1.

**Status.** `frozen boundary`

**Primary references.** [`LCE_DECISION_EVOLUTION.md`](../history/LCE_DECISION_EVOLUTION.md), sections 4–5 and 12; [`LCE_V1_RUNTIME.md`](../architecture/LCE_V1_RUNTIME.md).

# Negative-results index

LCE's development record is intentionally not cleaned into a success-only story.

| Negative result / miss | Why it mattered | What changed |
| --- | --- | --- |
| 91 raw points collapsed to one propagated label | similarity was too coarse to define cognition identity | semantic understanding before embedding |
| 48-point raw giant component | denser reconstruction did not solve the semantic-unit problem | Raw Evidence retained as evidence, not cognition point |
| 5/16 false regions after early Semantic Blocks | better segmentation did not prove downstream structure correctness | continue falsification instead of declaring success |
| real TREND-04 cutoff miss | early visibility was not guaranteed | preserve misses, no-future cutoffs, negative controls |
| >40% giant region in INSPIRATION-05 | one binary graph over-compressed dense structure | local multi-scale observations |
| 263 sustained triggers / large noise floor | persistence alone was too permissive | bounded candidate formation before interpretation |
| H1 had no useful semantic signal | mathematically attractive structure lacked cognition evidence | H1/TDA not promoted to core authority |
| only 2/6 structure pairs worth attention | higher-order analogy precision was weak | bound higher-order cognition to one level; no recursive promotion |
| recap support inflation | provenance churn looked like new cognition | split provenance identity from support identity |
| reference recovery `30/30` became package-sensitive `24/30` | test oracle did not cover legal interpreter behavior | effect-aware recovery + permanent adversarial matrix |
| newest-only recap fixture missed ordering bug | regression fixture encoded a hidden assumption | oldest/middle/newest selected-order coverage |

# Open questions

These findings constrain V1 but do not settle all research questions.

- embedding/model quality remains future work;
- production threshold tuning remains future work;
- higher-order candidate precision remains incomplete;
- cross-corpus generalization of local structural observations is not established here;
- future MR/Body integration is outside standalone V1 closure;
- performance optimization is non-blocking future work.

For the chronological architecture story, see [`docs/RESEARCH_OVERVIEW.md`](../RESEARCH_OVERVIEW.md). For the detailed decision record, see [`docs/history/LCE_DECISION_EVOLUTION.md`](../history/LCE_DECISION_EVOLUTION.md).
