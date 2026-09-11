# LCE Decision Evolution

## Reading rule

This document answers the architectural questions that accumulated during the
LCE research and productization sequence. Every answer keeps four layers
separate:

```text
problem → evidence → failed assumption → decision → consequence
```

Research support is not automatically production authority. A later V1
implementation is not attributed backward to Core V0. Statements that were
not found verbatim in the repository are marked as owner reconstruction rather
than presented as original dated decisions.

The detailed experiment and claim authorities remain in the preserved A0
documents:

- [`LCE_EXPERIMENT_CHRONOLOGY_VERIFIED.md`](../research/LCE_EXPERIMENT_CHRONOLOGY_VERIFIED.md)
- [`LCE_DECISION_HISTORY_VERIFIED.md`](../research/LCE_DECISION_HISTORY_VERIFIED.md)
- [`LCE_ARCHITECTURE_CLAIMS_MATRIX.md`](../research/LCE_ARCHITECTURE_CLAIMS_MATRIX.md)

## 1. Why did raw text stop being the cognition point?

**Problem.** The first instinct was to treat raw diary segments as points in a
vector space and recover cognition from their neighbourhoods.

**Evidence.** POINTCLOUD-01 used 91 raw units over 14 days. Similarities formed
a narrow cone around roughly `0.51..0.88`; raw label propagation collapsed all
91 points to one label. POINTCLOUD-01R still produced a 48-point giant
component at mutual-kNN `k=4`. R08 grouped five different investment objects,
and bounded interpretation rejected all five as one structure.

**Failed assumption.** High vector similarity means the items share one
cognition. It did not. It produced connectedness and relatedness, but not a
reliable unit of longitudinal understanding.

**Decision.** Raw text remains evidence, provenance, audit material, and
compiler input. It is not itself the corrected cognition point.

**Consequence.** The accepted research path became:

```text
Raw Evidence → semantic artifacts → Semantic Block → embedding
```

This is a research representation decision, later reinforced by the LCE
provenance contracts. It is not a claim that Core V0 owns raw Memory.

## 2. Why did Semantic Block become the boundary before embedding?

**Problem.** Raw units contained mixed matters, while embedding them directly
  forced the vector space to carry a semantic segmentation burden it could not
  reliably solve.

**Evidence.** Semantic Cloud-02 paid a first-pass semantic cost, producing 667
  artifacts and 129 Semantic Blocks from the same raw corpus. Blocks retained
  artifact and raw references. The report explicitly calls the block a
  `Semantic Block / cognition node` and says raw text was never directly
  embedded in the corrected pipeline.

**Failed assumption.** Vectorization can be the first semantic operation and
  segmentation can be inferred afterward without changing the cognition unit.

**Decision.** Semantic understanding precedes embedding. The Semantic Block is
  the research cognition point; no separate `SemanticPoint` ontology was
  introduced.

**Consequence.** Later vector, structure, and interpretation experiments all
  operate over Semantic Blocks or bounded derived objects. Core V0 still
  accepts externally selected Memory IDs; this research decision did not
  retroactively add a compiler to V0.

## 3. Why was time rejected as the primary segmentation rule?

**Problem.** Day-batch compilation was convenient, but a day can contain
  unrelated matters and one matter can cross day boundaries.

**Evidence.** BLOCK-03 changed day-batch compilation to semantic-stream
  cutting. SB0008, SB0044, and SB0129 split at semantic switches; SB0021,
  containing a long quantitative-research matter, stayed intact. The corpus
  changed from 129 to 179 blocks, mixed blocks fell from about 10 to 3–4, and
  false regions fell from `5/16` to `0/14`. Recap deduplication reduced an
  intermediate 210 blocks to 179 without removing new ratings, decisions, or
  tasks.

**Failed assumption.** Time/day boundaries are a safe proxy for semantic
  continuity.

**Decision.** A Semantic Block is a semantic unit, not a time unit:

```text
same semantic continuum → continue
semantic switch → split
multiple matters in one input → split
recap → attach/deduplicate, not a new cognition point
```

**Consequence.** Time remains important for no-future evaluation, cutoff
  snapshots, ordering, and longitudinal replay. It does not define the point
  identity or block boundary by itself.

## 4. Why did a longitudinal trend experiment come before vector-first structure discovery?

**Problem.** After the Semantic Block correction, the project needed to test
  whether an emerging direction could be detected before it became obvious,
  without allowing future evidence to leak into the judgment.

**Evidence.** TREND-04 used six independent cutoffs, physically excluded
  future blocks, and reverse-checked proposed directions. It ran 48 main calls;
  75% of judgments said the direction was not yet visible. Three directions
  appeared 2–6 days early, while shuffle controls did not show coherent
  progression and an SB0034-related T3 cutoff was a real miss.

**Failed assumption.** A model-led candidate loop can be both the discovery
  mechanism and the evaluator of its own longitudinal support.

**Decision.** No-future cutoffs, chronological replay, and negative controls
  became required evidence for longitudinal claims. TREND-04 remained an
  intermediate LLM-led experiment, not the final discovery architecture.

**Consequence.** INSPIRATION-05 moved structural replay before language
  interpretation and postponed the LLM to the bounded interpretation stage.

## 5. Why did the project move to vector-first structure discovery?

**Problem.** TREND-04 depended on an LLM to propose and judge candidate
  directions. That made it difficult to separate geometric evidence from
  interpretation and to control evidence selection.

**Evidence.** INSPIRATION-05 froze one 3072-dimensional space and replayed
  local structure over 14/30/41-day prefixes. Nodes grew 179→302→489, average
  degree grew 6.2→10.2→12.8, and three old isolated points later reconnected.
  At the same time, more than 40% of nodes entered one giant region and 263
  sustained triggers exposed a noise floor.

**Failed assumption.** More sustained binary similarity is equivalent to a
  meaningful longitudinal structure.

**Decision.** Structure and temporal change should produce a bounded candidate
  evidence set first; language interpretation comes later and cannot search
  for its own support.

**Consequence.** The project gained an LLM-last authority direction while
  keeping the giant-region and sustained-support failures visible as reasons
  to avoid a single binary graph.

## 6. Why did exclusive clustering fail?

**Problem.** A point that participates in several evolving local structures
  cannot be faithfully represented by one exclusive cluster or one category
  tree.

**Evidence.** STRUCTURE-06R Lens C observed multi-point local structure at
  several `k` scales. At `k=16`, 74 blocks participated in multiple of 97
  groups. The experiment retained overlapping local structures around the
  SB0034 chain and other cross-time themes. INSPIRATION-05 had already shown
  that a single giant component could be mostly noise.

**Failed assumption.** Every cognition point should be assigned to one stable
  category, and a single category tree can explain longitudinal structure.

**Decision.** Structures are overlapping, local, scale-dependent observations.
  Exclusive membership is not the final structural abstraction.

**Consequence.** A point may participate in multiple derived observations, but
  this does not create a production ontology in which every plausible
  category becomes truth. The final V1 detector remains bounded and derived.

## 7. Why are structures derived rather than canonical authority?

**Problem.** Similarity regions, cliques, persistence features, and structure
  pairs are observations over Memory-derived material. Treating them as truth
  would let an unstable detector rewrite factual authority.

**Evidence.** STRUCTURE-06R recorded 3578 of 5825 `new_overlap` events as
  noise-floor background; H1 had no useful semantic signal; structure↔structure
  review found two of six pairs worth attention, four weak analogies, and no
  clear common pattern. The MR/LCE authority audit also requires Baselines not
  to become Evidence, Observation, Memory, C10, Intent, Appraisal, or Action.

**Failed assumption.** A derived structure is a safe replacement for the
  source records that caused it to be observed.

**Decision.** Structures, snapshots, higher-order candidates, and
  interpretations remain derived, rebuildable, and bounded. They may propose
  a CandidateBaseline, but they do not become canonical Memory or evidence by
  self-reference.

**Consequence.** The V1 path is:

```text
derived observation → bounded candidate → authorized support check
→ Worktree → conservative promotion → Baseline revision
```

The accepted Baseline is still not factual Memory.

## 8. Why was higher-order cognition bounded to one extra level?

**Problem.** Structure can itself become an object of comparison, but recursive
  structure-of-structure cognition can quickly become a second uncontrolled
  authority system.

**Evidence.** STRUCTURE-06R found only partial structure↔structure support: two
  of six pairs were worth attention, four were weak analogies, and none was a
  clear common pattern. The report explicitly says recursive cognition was not
  done. MR ADR-0026 excludes STRUCTURE-06 and topology from the binding.

**Failed assumption.** A promising higher-order analogy is sufficient to
  authorize recursive cognition.

**Decision.** V1 may form a bounded higher-order candidate one level above
  local structure, with explicit source closure and bounded interpretation.
  It does not recursively reinsert derived cognition as new evidence.

**Consequence.** Higher-order precision and recursive cognition remain future
  work. The V1 product has a bounded candidate detector, not a solved
  higher-order ontology.

## 9. Why was Worktree kept separate from accepted Baseline?

**Problem.** A candidate understanding must be inspectable, supportable,
  retryable, and droppable before it becomes accepted longitudinal state.

**Evidence.** Core V0 already distinguished candidate consolidation from
  immutable Baseline revisions. V1 introduced derived cognition Worktrees with
  `OPEN → MERGED` or `DROPPED`, support observations, replay flags, and
  promotion through the existing LCE Core. Z0 found that the original runner
  did not preserve this separation correctly under invalidation and recovery.

**Failed assumption.** Candidate calculation and accepted revision can share a
  single immediate write without needing a durable intermediate boundary.

**Decision.** Worktree state is derived, durable, and isolated from accepted
  Baseline/HEAD state. Promotion remains conservative and uses the existing
  Core rather than a second accepted-cognition store.

**Consequence.** Z0–Z2 repairs had to preserve Worktree support, selected
  immutable states, and downstream stage progress across restart. The final
  product still has one accepted authority path.

## 10. Why must Memory remain truth authority?

**Problem.** Longitudinal understanding is useful only if its source material
  remains auditable and ownership is not split among vectors, providers,
  structures, and derived Baselines.

**Evidence.** Core V0's `MemorySubstratePort` accepts caller-selected Memory
  views and stores Baseline revisions with provenance; it does not own the
  Memory table or vector discovery. MR ADR-0026 states that Memory owns points,
  LCE owns Baseline revisions over caller-selected points, and Baselines never
  become Evidence, Observation, Memory, C10, Intent, Appraisal, or Action.

**Failed assumption.** A derived LCE conclusion can become a new fact simply
  because it was accepted by the LCE promotion path.

**Decision.** Memory remains canonical factual authority. LCE owns derived
  longitudinal Baseline revisions and their support/provenance, not factual
  admission.

**Consequence.** The read path may return accepted longitudinal understanding,
  but it cannot write Memory, promote from a query, or create canonical facts.
  Invalidation can suppress a derived result when selected source validity is
  lost without pretending that LCE itself is the truth judge.

## 11. Why does standalone V1 own a minimal Reference Memory substrate?

**Problem.** Core V0 deliberately depended on an external Memory port, but a
  standalone product pipeline needed a reproducible local substrate to run
  compilation, vectors, snapshots, worktrees, recovery, and accepted reads
  without requiring MR.

**Evidence.** A1 added the standalone Reference Memory substrate, while the V0
  documents continued to say that V0 did not own Memory or vectors. The V1
  product reports explicitly separate Reference Memory from the existing Core
  Baseline store and test an independently implemented replacement backend.

**Failed assumption.** Making standalone V1 runnable requires retroactively
  redefining Core V0 as the owner of Memory or vectors.

**Decision.** V1 owns a minimal, replaceable Reference Memory implementation
  for standalone execution. Core V0 keeps its external port and Baseline
  authority boundary. The Reference Memory is not MR's canonical Memory and is
  not evidence that LCE should own production Memory.

**Consequence.** The product can be installed and tested without MR while
  preserving the optional one-way MR binding. B8 explicitly required an
  independent backend through the actual V1 composition seam.

## 12. Why is read-time LLM reasoning forbidden?

**Problem.** If a read query invokes a model, it can silently invent support,
  mutate state, or make current-turn generation an LCE responsibility.

**Evidence.** LCE's public read path serves accepted/current-valid Baselines;
  it does not call an interpretation provider, mutate HEAD, promote an OPEN
  Worktree, or write Evidence. Core V0 exposes consolidation and history, not a
  current-turn planner. MR architecture leaves current-turn reasoning and
  final generation/execution to Body.

**Failed assumption.** A richer answer is always worth a model call at read
  time, even if the call cannot be audited as a durable cognition event.

**Decision.** Interpretation is bounded and occurs in the explicit processing/
  promotion path. Read is deterministic, model-free, and non-mutating.

**Consequence.** LCE supplies accepted longitudinal material to a consumer;
  it does not become a second current-turn agent, Body, Intent engine, or
  ActionPolicy.

## 13. Why did immutable selected support become first-class?

**Problem.** A cutoff-bound interpretation may select an earlier immutable
  state even when the live block later has a newer continuation or recap.

**Evidence.** Z1 reproduced accepted provenance corruption when promotion
  replaced the selected historical state with the latest state. A legal
  interpreter selecting a strict subset or reordered subset exposed positional
  mapping errors and invalidation leaks. Z2 required exact selected
  `(block_id, state_id)` ownership through package, Worktree, Baseline, read,
  restart, and snapshot rebuild.

**Failed assumption.** The current block state is an equivalent substitute for
  the state that was actually interpreted.

**Decision.** Authorized selected immutable support is a first-class value,
  carried with exact block/state ownership, ordering, cardinality, and source
  validity checks.

**Consequence.** Historical promotion remains cutoff-bound. Later CONTINUE/RECAP
  state cannot leak into an earlier accepted conclusion. The selected support
  value is provenance-bearing; it is not automatically the same as qualifying
  support identity.

## 14. Why did support identity split from provenance identity?

**Problem.** A pure recap can create a new immutable state because provenance
  grows, while the underlying cognition-supporting content and effective
  structure remain unchanged.

**Evidence.** Z2 reproduced B4: a provenance-only state change advanced support
  and caused false promotion. R3's `eff90b6` separated recap provenance from
  cognition support. The support fingerprint then used semantic content and
  effective structure membership while preserving exact `block_id + state_id`
  provenance.

**Failed assumption.** Every new state version is new cognition support.

**Decision.** Keep two identities explicit:

```text
provenance identity = the exact immutable state interpreted
qualifying support identity = semantic/structural change relevant to the candidate
```

**Consequence.** Pure recap, duplicate source, replay, unrelated cutoff churn,
  and duplicate local observations remain one support identity. Genuine
  candidate-relevant change can advance support and promotion.

## 15. Why did durable recovery semantics become necessary?

**Problem.** A process can fail after a cognition effect is durable but before
  later bookkeeping markers are written. Retrying the entire input can then
  invoke the interpreter again or create duplicate Worktrees/support/revisions.

**Evidence.** Z0 found compiler replay skipping downstream stages. Z1 found
  post-Baseline and completed-prefix replay defects. Z2's reference interpreter
  produced a passing `30/30`, but a legal package-sensitive interpreter exposed
  `24/30`: six cases created unintended `OPEN/1` effects after an already
  committed result.

**Failed assumption.** Compiler idempotency or a completed marker alone proves
  that the entire cognition pipeline completed. A reference interpreter that
  ignores previous accepted cognition is representative of every legal
  interpreter.

**Decision.** Recovery is effect-aware:

```text
before durable cognition effect → retry interpretation may be allowed
after durable cognition effect → reuse committed interpretation/support/result
missing downstream marker → resume bookkeeping, not cognition
```

`d22b330` persists the processing input identity and reuses durable cognition
effects. The package-sensitive recovery matrix became permanent test authority.

**Consequence.** Recovery correctness is judged against full durable state,
  support identities, selected immutable states, Worktree status, accepted
  history, and interpreter call records. “The reference interpreter passed” is
  not sufficient evidence.

## 16. Why was test design itself part of the final architecture?

**Problem.** Green ordinary tests repeatedly missed real runtime defects at
  semantic boundaries and durable fault points.

**Evidence.** Z0 rejected an implementation with ordinary tests green. Z1 and
  Z2 again found defects outside the focused green assertions. The permanent
  suite introduced deliberate RED cases for B4 and B7, then preserved their
  RED→GREEN history. Z3 still found that the permanent fixture always recapped
  the newest block, so it never permuted selected order.

**Failed assumption.** A passing suite with broad feature coverage necessarily
  explores the adversarial state permutations that matter.

**Decision.** Independent adversarial discoveries must become permanent,
  source-tracked regressions. Fixture design must vary selected ordering and
  interpreter behavior, not merely repeat the most convenient newest-block
  path.

**Consequence.** The final B4 test-first commit `516826c` added oldest/middle/
  newest ordering coverage. Its `3 RED / 1 passed` result preceded the final
  `808b148` repair. The closure authority is executable history, not a report
  that merely says a bug was fixed.

## 17. Why is the MR binding one-way and separate from standalone V1 closure?

**Problem.** MR owns canonical Memory and current runtime authority; LCE is a
  derived longitudinal understanding component. A convenience integration
  could accidentally make LCE a reverse authority or make standalone closure
  depend on MR.

**Evidence.** MR commit `930d7f06dc9b8fd4b99ac60bcb4985061ad00e4c` accepted ADR-0026:
  explicit stable Memory IDs flow from MR canonical Memory into the frozen LCE
  port; production invocation remains OFF by default; no reverse writeback or
  vector authority is introduced.

**Failed assumption.** The product is complete only if MR integration is
  enabled, or an LCE Baseline can write back into MR factual Memory.

**Decision.** MR binding is optional, one-way, and independently gated. It is
  not part of standalone LCE V1 closure.

**Consequence.** F1 can freeze standalone LCE V1 at implementation HEAD
  `808b148...` without claiming MR, Body, Hot Start, production activation, or
  current-turn cognition.

## 18. Corrections to owner reconstruction

The following are useful conceptual reconstructions but were **not found
verbatim** in the inspected repository and must not be backdated as original
decisions:

- “stateless Foundation Model repeatedly pays the same cognitive cost”;
- `biology → animal → human` analogy;
- a Hot Start / ongoing-use same-ontology decision.

The weaker evidence-backed claims are still valid: dense similarity can join
semantically non-identical items; the project needed a longitudinal boundary;
and no accepted Hot Start contract was found. This distinction is part of the
history, not a footnote to be removed.

## 19. Why must a new algorithm not automatically become a new architectural abstraction?

**Problem.** During the 2026-09-11 design discussion for possible structure-
discovery experiments, three mathematical families were raised as candidate
suppliers: persistent homology, Hodge-Laplacian analysis, and discrete Hodge
decomposition. The first LLM response incorrectly escalated the appearance of
new algorithms into a possible new topology subsystem, generic provider layer,
and new structural contract.

**Evidence.** The actual product chain had not changed:

```text
Semantic Blocks + vectors
  → structure discovery
  → StructureObservation / StructureSnapshot / StructureDiff
  → HigherOrderCandidate
  → bounded interpretation / re-verification
```

The current `SnapshotStructureDiscovery` is one supplier of the existing
`structure` stage. A different mathematical detector would still consume the
same upstream semantic/vector material and supply structural evidence to the
same downstream cognition path. No new product responsibility, authority
boundary, consumer, or lifecycle had been introduced by naming a new algorithm.

The correction happened before implementation: the owner rejected the proposed
architectural expansion and restated the intended abstraction as:

```text
Structure = stable product
algorithm = replaceable / complementary supplier
bounded interpreter = downstream consumer and semantic verifier
```

This discussion is design-process evidence, not evidence that any of the new
algorithms are useful. Their usefulness remains an experimental question.

**Failed assumption.** A new technical concept, algorithm, or mathematical
object deserves a corresponding software abstraction or architectural layer.

This is an especially plausible LLM failure mode because a model can produce a
locally coherent implementation for an unnecessary concept: module, interface,
configuration, state, persistence, tests, and documentation may all be
internally consistent while increasing total system complexity.

**Decision.** Treat a new algorithm first as a possible implementation of an
existing responsibility. Before proposing a new abstraction, ask:

```text
Did the product responsibility actually change?
Does the existing abstraction fail to express proven useful output?
Would a new abstraction reduce total system complexity rather than organize
an unnecessary expansion?
```

If the first answer is no, the default is to keep the new method inside the
existing capability boundary. If usefulness has not yet been demonstrated,
run the research before changing the architecture.

The design rule is:

> LLMs are strong expansion engines; architecture review must provide
> compression pressure.

This is not a claim that humans are categorically better architects than LLMs.
It records a narrower observed risk: LLM proposals can over-materialize new
concepts into software entities when the existing product abstraction is
already sufficient.

**Consequence.** Future LCE design review should distinguish three questions in
order:

```text
new idea
  → is this already an existing responsibility?
      → yes: keep it inside the existing responsibility
      → no / unknown: prove the mismatch before adding architecture
  → design and test the algorithm
  → only experimentally proven product-semantic mismatch may justify
    a contract or architecture change
```

The review target is therefore not only whether a proposed abstraction is
well-designed. The prior questions are more important:

> Why must this abstraction exist?
>
> Did an architectural change actually occur?

This warning mirrors an earlier LCE lesson at a different layer. STRUCTURE-06R
showed that a mathematically visible H1 signal did not automatically justify a
new cognition ontology. The 2026-09-11 design correction adds the software-side
analogue: a mathematically interesting algorithm does not automatically justify
a new software ontology.

## 20. Final decision boundary

The frozen V1 principle is:

```text
provenance ordering
≠
qualifying cognition-support canonical identity
```

The release implements that principle inside a bounded standalone pipeline,
with Memory/Source authority, explicit selected immutable support,
effect-aware recovery, non-mutating reads, and optional one-way MR binding.
Embedding quality, threshold tuning, higher-order precision, future MR/Body
integration, and performance optimization remain non-blocking future work.
