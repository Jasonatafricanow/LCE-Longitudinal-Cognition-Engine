# LCE Research Overview

This document explains how LCE arrived at its current architecture. It is not a feature list and it does not present the final V1 design as inevitable.

The useful unit of analysis is:

```text
problem
→ initial assumption
→ experiment / adversarial observation
→ why the assumption failed
→ architecture consequence
```

That pattern appears repeatedly across both the research phase and the V1 productization phase.

## 1. The problem LCE was trying to solve

A long-running agent can store enormous amounts of history and still fail to accumulate useful longitudinal understanding.

The common fallback is retrieval: find relevant old material, put it back into a prompt, and ask a foundation model to reconstruct what it means now. Retrieval is useful, but it leaves a deeper question unresolved:

> Which understandings have already been earned over time, and how can they remain inspectable, revisable, and reusable without being recomputed as free-form model inference on every turn?

LCE was built around that problem.

The project therefore separates three responsibilities:

```text
Memory = what happened
LCE = what was learned longitudinally
current-turn model / Body = what reasons and acts now
```

The separation is not cosmetic. It prevents a derived conclusion from quietly becoming a new fact, and prevents the longitudinal layer from turning into a second unrestricted current-turn agent.

## 2. Why retrieval plus prompt reconstruction was not enough

The problem was not simply storage capacity. A richer vector store or larger context window still leaves the model responsible for repeatedly deciding:

- which historical items belong together;
- which apparent pattern is stable rather than accidental;
- which evidence was actually available at the time a conclusion supposedly emerged;
- whether a later recap is new support or only new provenance;
- whether a derived interpretation is allowed to become durable state;
- whether a later read may mutate or reinforce that state.

If all of those decisions remain implicit inside a current prompt, the system can be hard to audit and can repeatedly pay the same interpretation cost. LCE instead tries to make the intermediate transformations explicit and bounded.

The final V1 pipeline is:

```text
Raw Evidence
  -> semantic-stream Semantic Blocks
  -> rebuildable vector observations
  -> cutoff-bounded local structures
  -> bounded higher-order candidate
  -> bounded interpretation
  -> durable cognition Worktree
  -> conservative Baseline / HEAD promotion
  -> deterministic Understanding read
```

That pipeline was reached only after several earlier abstractions failed.

## 3. First failure: raw text was the wrong cognition point

### Problem

The initial instinct was simple: treat raw diary/history units as points in vector space and recover cognition from their neighbourhoods.

### Initial assumption

If two historical units are sufficiently close in embedding space, the local region around them may correspond to one meaningful cognition or theme.

### Experiment / observation

POINTCLOUD-01 embedded **91 raw units over 14 days**. Similarities formed a relatively narrow cone around roughly `0.51..0.88`, and raw label propagation collapsed all **91 points into one label**.

POINTCLOUD-01R tried to repair the idea with mean-centering, weighted kNN, label propagation, region splitting, and bounded interpretation. It still produced a **48-point giant component at mutual-kNN `k=4`**. One reconstructed region grouped **five different investment objects**, and the bounded interpreter rejected the five as one structure.

### Why the assumption failed

Embedding similarity reliably expressed relatedness and connectedness, but not a sufficiently precise cognition boundary. The vector space was being asked to solve a semantic segmentation problem that had not yet been paid for.

### Architecture consequence

Raw text remained valuable, but its role changed:

```text
Raw Evidence = provenance / audit / compiler input
Raw Evidence != corrected cognition point
```

The research path became:

```text
Raw Evidence → semantic artifacts → Semantic Block → embedding
```

This was the first major architecture correction: **do not let geometry invent the unit of cognition that semantics should define first**.

Primary evidence: [`docs/history/LCE_DECISION_EVOLUTION.md`](history/LCE_DECISION_EVOLUTION.md), sections 1–2.

## 4. First major correction: Semantic Blocks before embedding

### Problem

Raw units often contained more than one matter. If a mixed unit is embedded as one point, every later geometric operation inherits that ambiguity.

### Initial assumption

Vectorization could be the first semantic operation, with segmentation recovered later from neighbourhood structure.

### Experiment / observation

SEMANTIC-CLOUD-02 paid a first semantic pass before embedding. The same raw corpus produced **667 first-pass semantic artifacts and 129 Semantic Blocks**. Blocks retained links back to the source artifacts and raw units.

The correction improved the unit of analysis, but it did not magically solve the whole problem. The report still recorded **16 regions**, **17 isolated points**, and **5/16 false regions**. That negative result mattered: Semantic Blocks were a better cognition point, not proof that the downstream structure detector was already correct.

### Why the assumption failed

Segmentation and vectorization were doing different jobs. A vector space can compare semantic units, but it should not be responsible for creating those units out of mixed raw text.

### Architecture consequence

Semantic understanding moved before embedding:

```text
raw units
→ first-pass semantic artifacts
→ Semantic Block
→ embedding
```

No separate `SemanticPoint` ontology was needed. The Semantic Block itself became the research cognition node while preserving source closure.

Primary evidence: [`docs/history/LCE_MASTER_TIMELINE.md`](history/LCE_MASTER_TIMELINE.md), SEMANTIC-CLOUD-02; [`docs/history/LCE_DECISION_EVOLUTION.md`](history/LCE_DECISION_EVOLUTION.md), section 2.

## 5. Second correction: semantic continuity over time buckets

### Problem

Even after introducing Semantic Blocks, the first compiler still used day-batch boundaries because they were operationally convenient.

### Initial assumption

A day or other fixed temporal window was a reasonable proxy for semantic continuity.

### Experiment / observation

BLOCK-03 changed the compiler from day-batch processing to semantic-stream cutting.

The rules became:

```text
same semantic continuum → continue
semantic switch → split
multiple distinct matters in one input → split
recap / repetition → attach or deduplicate, not a new cognition point
```

The corpus changed from **129 to 179 blocks**. Mixed blocks fell from about **10 to 3–4**, false regions fell from **5/16 to 0/14**, and recap processing reduced an intermediate **210 blocks back to 179** without deleting new ratings, decisions, or tasks.

Several previously mixed blocks split at semantic switches, while a long multi-unit research matter remained intact.

### Why the assumption failed

Time is essential for longitudinal reasoning, but time does not define semantic identity. One matter can cross a day boundary and several unrelated matters can occur inside the same day.

### Architecture consequence

LCE separated two concepts that are easy to conflate:

```text
semantic boundary → defines the cognition unit
time boundary → defines ordering, cutoff visibility, replay, and evaluation
```

This separation later became important for both no-future evaluation and immutable selected support.

Primary evidence: [`docs/history/LCE_DECISION_EVOLUTION.md`](history/LCE_DECISION_EVOLUTION.md), section 3.

## 6. Falsifying longitudinal claims: no-future cutoffs

### Problem

Once Semantic Blocks existed, the next question was whether the system could detect an emerging direction before hindsight made it obvious.

### Initial assumption

A model-led loop could propose candidate longitudinal directions and judge whether the evidence supported them.

### Experiment / observation

TREND-04 used **six independent cutoffs** that physically excluded future blocks. It ran **48 main calls**. **75%** of judgments said the direction was not yet visible. Three directions appeared **2–6 days early**, shuffle controls did not produce coherent cross-window progression, and one SB0034-related T3 cutoff was a **real miss**.

The miss was retained rather than explained away.

### Why the assumption failed

The experiment showed that longitudinal evaluation could be made falsifiable, but it also exposed an authority problem: if the same model proposes a direction and searches for evidence that supports it, discovery and evaluation are too entangled.

### Architecture consequence

Three evaluation requirements became durable research constraints:

```text
no-future visibility
chronological replay
negative controls / reverse checking
```

TREND-04 remained an intermediate LLM-led experiment. The next architecture moved structural discovery before language interpretation.

A small public version of the visibility rule is preserved in [`research/experiments/temporal_cutoff/`](../research/experiments/temporal_cutoff/).

Primary evidence: [`docs/history/LCE_DECISION_EVOLUTION.md`](history/LCE_DECISION_EVOLUTION.md), section 4.

## 7. Moving discovery before interpretation: vector-first, LLM-last

### Problem

TREND-04 still relied on a model to propose and judge candidate directions. That made it difficult to distinguish geometric evidence from linguistic interpretation and made evidence selection harder to bound.

### Initial assumption

A frozen vector space plus sustained binary similarity should expose meaningful longitudinal structure before interpretation.

### Experiment / observation

INSPIRATION-05 froze one **3072-dimensional** space and replayed local structure across **14-day, 30-day, and 41-day** prefixes.

The space evolved as follows:

| Prefix | Nodes | Average degree | Isolated | Sustained triggers |
| --- | ---: | ---: | ---: | ---: |
| 14d | 179 | 6.2 | 10 | 42 |
| 30d | 302 | 10.2 | 10 | 144 |
| 41d | 489 | 12.8 | 9 | 263 |

Three old isolated points later reconnected after 34, 31, and 29 days. That was useful evidence that local neighbourhood meaning can change longitudinally.

But the experiment also failed in an important way: **more than 40% of nodes entered one giant region**, and **263 sustained triggers** exposed a large noise floor.

### Why the assumption failed

“Persisting similarity” was still too weak a concept. A dense semantic space can produce long-lived connectivity without producing one meaningful structure.

### Architecture consequence

Two decisions followed:

1. **Structural observations should produce a bounded candidate evidence set before interpretation.**
2. **The language model should interpret that package; it should not search freely for its own support.**

This is the origin of the LLM-last direction in the current design.

Primary evidence: [`docs/history/LCE_MASTER_TIMELINE.md`](history/LCE_MASTER_TIMELINE.md), INSPIRATION-05; [`docs/history/LCE_DECISION_EVOLUTION.md`](history/LCE_DECISION_EVOLUTION.md), section 5.

## 8. Rejecting giant regions and exclusive clustering

### Problem

A single binary graph over a dense space produced giant connected regions and lost the fact that one cognition point can participate in several meaningful local structures at once.

### Initial assumption

A point could ultimately be assigned to one stable cluster or category tree.

### Experiment / observation

STRUCTURE-06R replaced the unique binary graph with multiple local lenses: neighbourhood stability, overlap, multi-point structure, and temporal evolution.

At `k=16`, **74 blocks participated in multiple of 97 groups**. That directly contradicted the exclusive-membership assumption.

The experiment also preserved several negative higher-order results:

- **3578 of 5825** `new_overlap` events looked like noise-floor background;
- H1 counts existed but had **no useful semantic signal**;
- structure-to-structure review found only **2 of 6 pairs worth attention**, **4 weak analogies**, and **0 clear common patterns**;
- recursive cognition was not implemented.

### Why the assumption failed

A point can legitimately participate in several local structures, and a visually attractive higher-order signal is not sufficient evidence for a new ontology.

### Architecture consequence

The research boundary became:

```text
local
+ overlapping
+ scale-dependent
+ derived
```

Structures can propose candidates. They do not become factual Memory or canonical truth.

Higher-order cognition was deliberately bounded to one additional level instead of recursively reinserting structure-derived cognition as new evidence.

Primary evidence: [`docs/history/LCE_DECISION_EVOLUTION.md`](history/LCE_DECISION_EVOLUTION.md), sections 6–8.

## 9. Bounded higher-order cognition and authority separation

The structural experiments created a new problem: once a detector can produce interesting regions, snapshots, and higher-order candidates, what authority should those objects have?

The answer was intentionally conservative.

```text
derived observation
→ bounded candidate
→ authorized support check
→ Worktree
→ conservative promotion
→ Baseline revision
```

An accepted Baseline is durable LCE understanding, but it is still **not factual Memory**.

The authority split is:

- **Reference Memory / external Memory authority** owns canonical Raw Evidence, stable IDs, provenance, validity, invalidation, and supersession;
- **LCE** owns Semantic Blocks, derived vector/structure artifacts, Worktrees, and accepted longitudinal Baseline revisions;
- **current-turn reasoning / action** remains outside standalone LCE V1.

This prevents self-pollution: a derived conclusion cannot cite its own repeated use as new evidence.

See [`docs/architecture/LCE_V1_BOUNDARIES.md`](architecture/LCE_V1_BOUNDARIES.md).

## 10. Productization exposed a different class of errors

The early research failures changed **what the system represented and how it discovered candidates**.

The V1 closure failures changed **what correctness meant for a durable runtime**.

That distinction is important.

Once the pipeline acquired immutable Semantic Block states, Worktrees, accepted Baselines, restart behavior, invalidation, replay, and bounded interpretation, new bugs appeared that were not visible in the earlier research prototypes.

### Selected-state provenance corruption

A cutoff-bound interpretation may legally select an older immutable block state even if the live block later has a continuation or recap.

Z1 reproduced cases where promotion replaced the state actually interpreted with the latest state. Strict subsets and reordered subsets exposed positional-mapping and invalidation problems.

The correction was to make exact selected `(block_id, state_id)` ownership first-class through package, Worktree, Baseline, read, restart, and rebuild.

### Recap/support inflation

A recap can create a new immutable state because provenance grows while the cognition-supporting content remains unchanged.

Z2 reproduced a case where this provenance-only state change advanced support and caused false promotion.

The architecture had to split two identities:

```text
provenance identity = exact immutable state interpreted
qualifying support identity = semantic / structural change relevant to the candidate
```

This is a deeper correction than “deduplicate recaps.” It states that **new version identity is not automatically new cognition support**.

### Recovery after durable cognition effects

A process can fail after an interpretation/support effect is already durable but before later stage markers are written.

If restart simply reruns cognition, it can create duplicate support, Worktrees, or revisions.

Z2's reference interpreter passed a `30/30` recovery matrix, but a legal package-sensitive interpreter exposed `24/30`: six cases produced unintended `OPEN/1` effects after a result had already committed.

The correction became effect-aware recovery:

```text
before durable cognition effect → interpretation may be retried
after durable cognition effect → reuse the committed cognition effect
missing downstream marker → resume bookkeeping, not cognition
```

Primary evidence: [`docs/history/LCE_DECISION_EVOLUTION.md`](history/LCE_DECISION_EVOLUTION.md), sections 13–16.

## 11. How the correction loop changed the runtime contracts

The recurring correction process visible in this repository is:

```text
1. Form a narrow architectural hypothesis.
2. Build a bounded experiment, replay, or adversarial fixture.
3. Preserve misses and negative results instead of tuning them away.
4. Ask what kind of failure occurred:
   - algorithmic?
   - representational?
   - temporal?
   - provenance / authority?
   - recovery / durability?
5. Change the smallest abstraction that explains the failure.
6. Turn the discovered failure mode into an explicit invariant or regression case.
7. Keep derived cognition from becoming its own evidence.
```

Examples:

| Failure | Classification | Architectural correction |
| --- | --- | --- |
| giant raw point region | representation | Semantic Block before embedding |
| mixed day-batch blocks | segmentation | semantic-stream boundaries |
| future visibility risk | evaluation | cutoff-bound no-future replay |
| giant binary region | structural abstraction | overlapping local multi-scale observations |
| weak H1 / structure-pair evidence | epistemic authority | do not promote unsupported higher-order ontology |
| recap creates false support | support semantics | split provenance identity from support identity |
| package-sensitive restart duplicates cognition | recovery | effect-aware durable recovery |
| green suite misses ordering bug | test authority | preserve adversarial RED→GREEN fixtures and vary selection order |

The important pattern is not “the design kept changing.” It is that each change attempted to make the next failure class **less implicit**.

## 12. What V1 finally freezes

The frozen V1 release combines the research boundaries with runtime invariants.

### Frozen authority boundaries

- Raw Evidence remains canonical factual evidence.
- Semantic Blocks are cognition points for the LCE vector/structure pipeline, but they retain source closure.
- Derived vectors, structures, candidates, Worktrees, and Baselines cannot write themselves back as Raw Evidence.
- An accepted Baseline is a durable LCE revision, not objective truth.
- Read-time access is deterministic, model-free, and non-mutating.
- Current-turn reasoning and action stay outside standalone LCE V1.
- Recursive cognition is not authorized.

### Engineering invariants

- selected immutable support must remain exact and cutoff-bound;
- provenance identity and qualifying cognition-support identity remain distinct;
- recap, duplicate source, replay, unrelated cutoff churn, and repeated local observations cannot manufacture new support by version/order alone;
- recovery must be aware of already-durable cognition effects;
- provider/input barriers and stage progress must survive restart;
- adversarial failures discovered during closure remain executable regression authority.

### Mechanical release gates

The V1 release record reports:

- **139 passed** in the full suite;
- **14 passed** closure invariants;
- **32 passed** recovery fault tests;
- normalized **30/30** recovery matrix;
- clean mypy for `src/lce`;
- clean Ruff for `src tests`;
- exact-HEAD isolated install/import/smoke passed.

These are engineering release gates. They do not claim production deployment or general scientific validation.

See [`LCE_V1_RELEASE_RECORD.md`](../LCE_V1_RELEASE_RECORD.md).

## 13. What remains unresolved

LCE V1 deliberately stops before several questions are solved.

### Exploratory research questions

- Which embedding/model choices improve the quality of candidate local structure?
- Which thresholds remain stable across corpora and domains?
- How should higher-order candidates be evaluated with stronger precision evidence?
- Which longitudinal patterns remain stable across longer time ranges, different users, and different observation densities?

### Product/integration questions

- Future MR/Body integration remains outside standalone V1 closure.
- Production invocation of the optional one-way MR binding is not part of this release boundary.
- Performance optimization is non-blocking future work.

### Deliberately rejected shortcuts

V1 does not promote:

- similarity into truth;
- one cluster into a universal cognition ontology;
- H1/TDA into authority;
- recursive structure-derived cognition into new evidence;
- model confidence into merge authority;
- read-time generation into durable cognition.

## 14. Where to inspect the evidence

Different documents answer different questions.

### Start here

- [`README.md`](../README.md) — 30-second project framing and experiment-driven evolution table.
- [`docs/research/FINDINGS.md`](research/FINDINGS.md) — claim-by-claim findings, limits, status, and architecture consequences.

### Research and experiment surface

- [`research/README.md`](../research/README.md) — public synthetic reproducibility experiments.
- [`docs/research/research-map.md`](research/research-map.md) — conceptual path from similarity to longitudinal structure and Core authority.
- [`research/experiments/semantic_neighbourhood/`](../research/experiments/semantic_neighbourhood/) — candidate relatedness without semantic/canonical escalation.
- [`research/experiments/region_discovery/`](../research/experiments/region_discovery/) — transparent region construction with isolated/weak evidence preserved.
- [`research/experiments/temporal_cutoff/`](../research/experiments/temporal_cutoff/) — no-future evidence visibility control.

### Full historical reasoning

- [`docs/history/LCE_DECISION_EVOLUTION.md`](history/LCE_DECISION_EVOLUTION.md) — problem → evidence → failed assumption → decision → consequence.
- [`docs/history/LCE_MASTER_TIMELINE.md`](history/LCE_MASTER_TIMELINE.md) — reconstructed research / architecture / implementation / audit timeline.
- [`docs/history/LCE_V1_CLOSURE_HISTORY.md`](history/LCE_V1_CLOSURE_HISTORY.md) — product closure and repair history.

### Current implementation boundaries

- [`docs/architecture/LCE_V1_RUNTIME.md`](architecture/LCE_V1_RUNTIME.md)
- [`docs/architecture/LCE_V1_BOUNDARIES.md`](architecture/LCE_V1_BOUNDARIES.md)
- [`LCE_V1_RELEASE_RECORD.md`](../LCE_V1_RELEASE_RECORD.md)

## Status legend

| Category | Meaning in this repository | Example |
| --- | --- | --- |
| **Frozen boundary** | Architecture or authority rule intentionally fixed for V1 | Memory remains factual authority; read-time path is non-mutating |
| **Engineering invariant** | Runtime correctness behavior backed by closure/regression tests | support identity is distinct from provenance identity |
| **Exploratory result** | Research observation that influenced design but is not a general scientific claim | multi-membership and giant-region behavior in the studied corpus |
| **Open question** | Capability or evaluation problem deliberately left unresolved | embedding quality, threshold tuning, higher-order precision |
