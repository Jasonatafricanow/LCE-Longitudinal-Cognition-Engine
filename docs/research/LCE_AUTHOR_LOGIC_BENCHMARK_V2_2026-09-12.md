# LCE Author-Logic Benchmark V2 — 2026-09-12

**Status:** Research design — supersedes the previous author-logic benchmark as the primary system benchmark  
**Scope:** Controlled reconstruction of authored higher-order logic  
**Production integration:** Not authorized

## 1. Benchmark target

The completed article is treated as a **gold high-order cognitive structure**.

The task is not to test whether its original paragraphs are geometrically adjacent. The task is to reverse the article into less-organized semantic material and test whether LCE can reconstruct an approximation of the article's reasoning structure.

Primary target article:

```text
C:\知识库\用户\个人创作\当抽象开始跑在现实前面.md
```

The benchmark should recover structure, not wording.

Desired outputs include:

- major parallel reasoning chains;
- progression inside each chain;
- cross-chain convergence;
- higher-order common relations;
- bounded semantic interpretation close to the article's final abstraction.

Exact paragraph order or verbatim prose reconstruction is not required.

## 2. Main comparison

The natural baseline is the strongest practical general capability available without LCE-specific structural patches.

At every benchmark stage, compare:

```text
GENERAL BASELINE
same source evidence
+ standard Gemini / general-model capability
+ ordinary embedding / retrieval tools as appropriate

vs

LCE
same underlying model(s)
+ same source evidence
+ LCE longitudinal / structural machinery
```

Do not replace this with a large synthetic control matrix by default.

Ablations are added only when needed to explain where incremental value came from or why a result may be misleading.

The main value metric is the incremental capability gain attributable to LCE under the same underlying model.

## 3. Difficulty ladder

The benchmark proceeds through four stages.

```text
T0   article decomposition + artificial time/depth scaffold
T1   article decomposition + no time scaffold
T1.5 expanded evidence-like material + artificial time/depth scaffold
T2   expanded evidence-like material + no time scaffold
```

The ordering is intentional.

Artificial time is a **difficulty-reduction scaffold**, not a realism requirement.

### T0 — Decomposed article + artificial time scaffold

Purpose:

> Establish the minimum system capability. Can LCE reconstruct the major authored structure when reasoning depth is provided as an alpha dimension?

Procedure:

1. decompose the article into atomic or semi-atomic semantic cognition units;
2. derive several parallel reasoning chains from the finished article;
3. assign each unit a hidden gold chain identity for evaluation only;
4. assign a reasoning-depth layer that simulates longitudinal time;
5. shuffle units inside each time/depth layer;
6. remove original paragraph order, section identity, chain labels, and explicit final-structure cues from discovery input;
7. feed batches chronologically by artificial time layer into the actual LCE pipeline;
8. allow cheap structural state to accumulate across layers;
9. do not invoke the LLM for every point;
10. after sufficient structure has accumulated, interpret mature candidates in batch;
11. compare reconstruction against the authored gold structure.

Example hidden gold structure:

```text
A0 -> A1 -> A2 -> A3
B0 -> B1 -> B2 -> B3
C0 -> C1 -> C2 -> C3
D0 -> D1 -> D2 -> D3
```

Discovery input:

```text
Time 0: shuffle(A0, B0, C0, D0)
Time 1: shuffle(A1, B1, C1, D1)
Time 2: shuffle(A2, B2, C2, D2)
Time 3: shuffle(A3, B3, C3, D3)
```

The system is not told A/B/C/D identities.

T0 success means the time scaffold materially helps LCE reconstruct the parallel trajectories and/or their common higher-order structure.

### T1 — Decomposed article without time scaffold

Purpose:

> Test whether LCE can reconstruct the authored structure from the same compressed cognition units without artificial reasoning-depth assistance.

Procedure:

- reuse the same semantic units as T0;
- remove artificial time/depth labels;
- globally shuffle the units;
- retain no original article ordering information;
- run the same LCE system and general baseline;
- compare reconstruction against the same gold structure.

T1 is harder than T0 because LCE must infer organization without the temporal scaffold.

### T1.5 — Expanded evidence-like material with time scaffold

T1.5 is a fallback / diagnostic stage used when T2 fails, or may be run before T2 if engineering risk warrants it.

Purpose:

> Determine whether evidence expansion remains representable when time/depth assistance is preserved.

Start from the compact cognition units and expand them into more natural evidence-like material.

Example:

```text
compact cognition:
"A model can write 100k lines of code, but that is different from knowing 70k lines should not exist."
```

may become evidence such as:

```text
a project rapidly accumulated generated modules
fallbacks increased after multiple revisions
each abstraction had a locally defensible reason
maintenance burden nevertheless increased
later discussion questioned whether local coding competence implies architectural judgment
```

Then:

- retain artificial time/depth groups;
- shuffle inside each group;
- feed evidence through the actual LCE representation / compilation path;
- evaluate whether cognition trajectories and higher-order structure can still be reconstructed.

Interpretation:

```text
T1 succeeds
T1.5 fails
→ evidence-to-cognition representation / compilation is likely the bottleneck
```

### T2 — Expanded evidence-like material without time scaffold

Purpose:

> Strongest controlled benchmark: can LCE reconstruct high-order authored logic from evidence-like material without being given reasoning-depth organization?

Procedure:

- use the same expanded evidence corpus as T1.5;
- remove artificial time/depth grouping;
- globally shuffle;
- run the actual LCE pipeline;
- compare against the authored gold structure.

Interpretation example:

```text
T1 succeeds
T1.5 succeeds
T2 fails
→ evidence remains representable, but search / longitudinal organization without time scaffold is insufficient
```

If T2 succeeds with meaningful improvement over the general baseline, this is the strongest near-term benchmark outcome.

## 4. T0 is the immediate next experiment

Do not proceed directly to T1/T1.5/T2.

T0 should be completed and audited end-to-end first.

The initial T0 dataset should remain small enough to inspect manually.

Recommended first scale:

```text
3–4 parallel reasoning chains
× 3–4 reasoning depths
≈ 12–16 core cognition units
+ a small number of distractors only if needed
```

Do not inflate the corpus merely to make the experiment look realistic.

The first question is whether the system can recover the known structure under intentionally favorable conditions.

## 5. Gold structure construction

The completed article is evaluation authority.

Construct a hidden gold representation containing at minimum:

- cognition-unit IDs;
- gold chain membership;
- gold depth/time layer for T0/T1.5;
- within-chain predecessor/successor relations where defensible;
- cross-chain higher-order relation(s);
- final authored synthesis supported by the article;
- source spans from which each unit was derived.

Do not expose gold chain labels or final synthesis text to the discovery path.

Gold structure is allowed to be partial where the article does not justify a unique decomposition.

Use `UNKNOWN` rather than inventing certainty.

## 6. Real LCE pipeline requirement

The previous static benchmark mostly exercised:

```text
experimental segmentation
→ gemini-embedding-001
→ custom distance / kNN / MSS / MST analysis
→ post-hoc oracle evaluation
```

That should not be treated as the system benchmark.

T0 must explicitly audit and use the real LCE path as far as current implementation permits.

Expected shape:

```text
input cognition/evidence
    ↓
actual LCE semantic representation / compiler path
    ↓
actual embedding / retrieval capability
    ↓
existing LCE structural state / snapshots / diffs / candidates
    ↓
structural maturation
    ↓
bounded LLM semantic interpretation of mature candidates
    ↓
benchmark comparison
```

If a production/reference step is not currently wired, report the missing binding rather than silently replacing it with an experiment-local imitation.

Experiment-local code may orchestrate the benchmark but should not recreate the entire LCE pipeline in parallel.

## 7. LLM timing rule

The benchmark must not invoke the LLM after every block arrival.

T0 default:

```text
Time 0 batch → update structure
Time 1 batch → update structure
Time 2 batch → update structure
Time 3 batch → update structure
        ↓
freeze structural outputs / mature candidates
        ↓
LLM batch interpretation
```

Early interpretation is allowed only if an explicit structural-maturity trigger fires and the benchmark records why.

This prevents the general LLM from continuously reconstructing the answer during ingestion and obscuring the contribution of LCE structure discovery.

The LLM should interpret mature structure, not perform high-frequency pairwise recall.

## 8. General capability baseline

The baseline should represent a realistic user's available general capability, not an intentionally weak straw man.

At minimum include one clear market-facing baseline such as:

```text
Gemini Standard Reconstruction
same benchmark inputs
→ strong general model instructed to reconstruct the latent reasoning structure
```

Where useful, an engineering baseline may use:

```text
same embedding model
+ standard retrieval / nearest-neighbour capability
+ same bounded LLM
```

But this is optional unless needed to localize the source of improvement.

The primary external claim should remain understandable:

```text
"Under the same source material, LCE recovered X% more of the authored structure than the standard general-model capability."
```

Do not claim an improvement percentage until the metric is frozen before scoring.

## 9. T0 evaluation dimensions

Avoid a single opaque score.

Record at minimum:

### 9.1 Chain recovery

Can the system group cognition units into the major parallel trajectories represented in the article?

Possible measures:

- pairwise same-chain precision / recall;
- chain purity;
- chain coverage;
- ordering recovery inside each chain where applicable.

### 9.2 Cross-chain higher-order recovery

Can the system surface that multiple semantically different chains instantiate a shared higher-order structure?

Record:

- whether a candidate was produced;
- evidence supporting it;
- whether semantic interpretation matches the article's authored abstraction;
- unsupported or invented links.

### 9.3 Structural compression

Can the system reduce many cognition units into a smaller useful structural description without merely repeating all inputs?

### 9.4 False structure burden

How many strong candidate structures are not supported by the authored gold structure?

### 9.5 LLM semantic quality

After candidate maturation, does bounded interpretation identify a realistic semantic relation close to the article's actual reasoning?

Distinguish:

```text
structure present, interpretation poor
vs
structure never surfaced
```

### 9.6 Incremental value over general baseline

Report the frozen metric delta:

```text
LCE score - general baseline score
```

This is the primary algorithmic-value signal.

## 10. Failure localization

If T0 fails, assign the earliest defensible failure layer:

```text
DECOMPOSITION_INVALID
SEMANTIC_REPRESENTATION_FAILURE
EMBEDDING_OR_RETRIEVAL_GAP
TEMPORAL_STRUCTURE_FAILURE
HIGHER_ORDER_DISCOVERY_FAILURE
MATURATION_TRIGGER_FAILURE
LLM_INTERPRETATION_FAILURE
PIPELINE_BINDING_MISSING
UNKNOWN
```

Do not automatically respond to failure by introducing a new algorithm.

First ask whether the strongest existing general capability was actually consumed correctly.

Only add an LCE-specific patch after a stable gap is demonstrated.

## 11. What previous static experiments now mean

Retain previous artifacts and negative findings.

Reclassify them as side evidence:

```text
STATIC AUTHOR-ARTICLE GEOMETRY ABLATION
```

Useful retained observations include:

- simple point proximity did not recover the strongest cross-domain relational motif;
- overlapping windows can manufacture geometric continuity;
- candidate-volume effects can create misleading apparent recovery;
- static MST/kNN/MSS results should not be promoted into system-level LCE capability claims.

These results inform T0 design but do not decide T0 outcome.

## 12. Minimal T0 execution order

```text
1. freeze final article and gold-evaluation authority
2. decompose into ~12–16 compact cognition units
3. define 3–4 hidden parallel chains
4. assign artificial reasoning-depth/time groups
5. shuffle each group independently
6. freeze T0 discovery input
7. run general baseline
8. run actual LCE pipeline batch-by-batch
9. do cheap structural updates without per-point LLM calls
10. freeze mature structural candidates
11. run bounded LLM interpretation on those candidates
12. score both systems against the same gold structure
13. report incremental LCE value and failure layer
```

Do not start T1 until T0 is understandable end-to-end.

## 13. Success boundary

T0 is successful if, under the artificial time/depth scaffold, LCE reconstructs a meaningful approximation of the article's major reasoning structure and demonstrates measurable incremental value over the general baseline.

The strongest desired result is not exact prose recovery. It is evidence that LCE can turn shuffled, semantically heterogeneous cognition units into:

```text
parallel longitudinal trajectories
    + higher-order structural relation
    + bounded semantic interpretation
```

that materially resembles the structure the human author eventually produced.

If T0 succeeds, proceed to T1. If T1 succeeds, expand the compact cognition units into evidence-like material and attempt T2, using T1.5 as the time-scaffold fallback when needed.
