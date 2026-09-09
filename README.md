# LCE V1 — Longitudinal Cognition Engine

LCE is a research-engineering project about **durable longitudinal understanding**.

Long-running agent systems often recover history by retrieving old records and handing them back to a foundation model, which must reconstruct what changed, what persisted, and what matters again at each use. LCE explores a narrower alternative:

> Can longitudinal understanding be formed, inspected, falsified, revised, and reused without turning model inference, vector similarity, or derived structure into factual authority?

The architecture that exists today was not designed in one pass. It emerged through a sequence of failed assumptions, bounded experiments, negative results, adversarial audits, and runtime repairs.

A useful shorthand is:

```text
Memory = what happened
LCE = what was learned longitudinally
current-turn model / Body = what reasons and acts now
```

Those are intentionally different authorities.

## Current V1 pipeline

```text
Raw Evidence
  -> Reference Memory validity / provenance
  -> semantic-stream Semantic Blocks
  -> rebuildable vectors
  -> cutoff-bounded local structure snapshots
  -> bounded higher-order candidate
  -> bounded interpretation in an OPEN cognition Worktree
  -> conservative Baseline / HEAD promotion
  -> deterministic accepted Understanding read
```

Each arrow is a transformation boundary, not an automatic increase in authority. Raw Evidence remains canonical evidence. Vectors, structures, candidates, Worktrees, and accepted Baselines remain derived cognition artifacts and cannot write themselves back as factual Memory.

## Why the architecture changed

The research record is useful because several attractive ideas failed under inspection.

| Stage | Starting assumption | What the experiment exposed | Architecture consequence |
| --- | --- | --- | --- |
| **POINTCLOUD-01 / 01R** | Raw text points plus similarity could recover cognition | 91 raw units collapsed into one propagated label; a reconstruction still produced a 48-point giant component, and one region mixed five different investment objects | Raw text remains evidence, not the corrected cognition point |
| **SEMANTIC-CLOUD-02** | Vectorization could carry the segmentation burden | The same corpus produced 667 semantic artifacts and 129 Semantic Blocks before embedding | Pay semantic understanding before vector projection |
| **BLOCK-03** | Day/time batches were a safe proxy for cognition boundaries | Semantic-stream cutting moved 129 blocks to 179; mixed blocks fell from about 10 to 3–4 and false regions from `5/16` to `0/14` | Semantic continuity, not clock boundaries, defines the block |
| **TREND-04** | A model-led loop could both discover and judge longitudinal directions | Six no-future cutoffs produced 48 main calls; one cutoff was a real miss and shuffle controls did not produce coherent progression | Longitudinal claims require cutoff discipline, replay, and negative controls |
| **INSPIRATION-05** | Sustained binary similarity would reveal meaningful long-term structure | In a frozen 3072-dimensional replay, more than 40% of nodes entered one giant region and 263 sustained triggers exposed a noise floor | Structural discovery moves before language interpretation; interpretation becomes bounded and LLM-last |
| **STRUCTURE-06R** | One exclusive cluster could represent each cognition point | At `k=16`, 74 blocks participated in multiple of 97 local groups; H1 showed no useful semantic signal; only 2 of 6 structure pairs were worth attention | Use overlapping, local, scale-dependent derived structures; do not promote attractive higher-order signals without evidence |
| **Z0–R3 product closure** | Broad green test suites were enough to establish runtime correctness | Recap/support inflation, selected-state provenance leaks, and recovery faults survived earlier green suites; a legal package-sensitive interpreter turned a reference `30/30` recovery result into `24/30` | Make selected immutable support, support identity, effect-aware recovery, and adversarial regression fixtures explicit runtime contracts |

The detailed evidence and decision reasoning are preserved in [`docs/history/LCE_DECISION_EVOLUTION.md`](docs/history/LCE_DECISION_EVOLUTION.md) and [`docs/history/LCE_MASTER_TIMELINE.md`](docs/history/LCE_MASTER_TIMELINE.md).

## What the research changed

The main findings are not feature claims. They are constraints learned from experiments and failures:

1. **Similarity discovers relatedness, not cognition.** Dense neighbourhoods are useful candidate evidence, but they are not semantic or factual authority.
2. **Raw text is evidence, not the corrected cognition point.** Semantic segmentation must happen before embedding.
3. **Semantic continuity is not equivalent to a time bucket.** Time remains essential for ordering and falsification, but not for point identity.
4. **Longitudinal claims require no-future evaluation.** A result that sees later evidence is not evidence that the structure was discoverable earlier.
5. **Exclusive clustering loses legitimate multi-membership.** Longitudinal structure is local, overlapping, and scale-dependent.
6. **Derived structure is observation, not truth.** Regions, snapshots, higher-order candidates, and Baselines never become their own evidence.
7. **Provenance identity is not qualifying cognition-support identity.** A new immutable state may record new provenance without contributing new cognition support.
8. **Replay, recap, and repeated consumption must not manufacture support.** Durable state changes need semantic relevance, not merely a new version or ordering.
9. **A green suite is only as strong as its oracle and fixtures.** Independent adversarial failures became permanent RED→GREEN regressions.
10. **Language interpretation should consume bounded evidence, not search for evidence supporting its own interpretation.**

See [`docs/research/FINDINGS.md`](docs/research/FINDINGS.md) for evidence, non-claims, architecture consequences, and status for each finding.

## Two different kinds of correction

LCE went through two qualitatively different correction loops.

**Research corrections changed the representation and discovery architecture.** Raw points, time buckets, one giant graph, exclusive clustering, H1/TDA signals, and recursive higher-order interpretation were all tested or considered and then constrained or rejected when the evidence was insufficient.

**Productization corrections changed the runtime correctness model.** Z0–R3 showed that even after the conceptual architecture looked coherent, provenance, support qualification, restart semantics, and test-oracle design could still violate the intended authority boundaries. Those failures were not patched as isolated bugs; they became explicit contracts and permanent regression cases.

The recurring process was:

```text
narrow architectural hypothesis
  -> bounded experiment / adversarial probe
  -> preserve misses and negative results
  -> classify the failure: algorithm, representation, or authority
  -> change the smallest abstraction that explains the failure
  -> encode the discovered boundary as a contract / regression
  -> prevent derived cognition from becoming its own evidence
```

This process is described in more detail in [`docs/RESEARCH_OVERVIEW.md`](docs/RESEARCH_OVERVIEW.md).

## What V1 is

LCE V1 is a **standalone, contract-first longitudinal cognition pipeline**.

It owns:

- Semantic Blocks compiled from authorized evidence;
- derived vectors, local structures, snapshots, and diffs;
- bounded higher-order candidates;
- durable `OPEN / MERGED / DROPPED` cognition Worktrees;
- accepted Understanding Baseline revisions and HEAD;
- a deterministic Understanding read API.

`ReferenceMemoryStore` is the included minimal standalone evidence substrate and is replaceable through focused ports. The standalone product does not require MR.

The V1 release record reports mechanical closure at implementation HEAD `808b148...`: **139 tests passed**, **14 closure invariants passed**, **32 recovery fault tests passed**, a normalized **30/30** recovery matrix, clean mypy/Ruff, and an isolated exact-HEAD install/import/smoke check. These are engineering release gates, not claims of scientific validation or production deployment. See [`LCE_V1_RELEASE_RECORD.md`](LCE_V1_RELEASE_RECORD.md).

## What V1 is not

LCE V1 does **not** claim a solved general cognition model.

It does not implement MR or Body integration, C10, Persona, Agent identity, Intent, ActionPolicy, RuntimeBinding, current-turn reasoning, or action execution. It does not make exclusive clustering, a complex knowledge graph, TDA/H1, recursive cognition, or embedding quality into canonical authority.

Read-time access is deterministic, model-free, and non-mutating. A query cannot promote a Worktree, write Memory, or manufacture factual support.

See [`docs/architecture/LCE_V1_RUNTIME.md`](docs/architecture/LCE_V1_RUNTIME.md) and [`docs/architecture/LCE_V1_BOUNDARIES.md`](docs/architecture/LCE_V1_BOUNDARIES.md).

## Research evidence and reproducibility

The repository contains two complementary evidence surfaces:

- [`research/`](research/) contains small, synthetic, reproducible boundary experiments for semantic neighbourhoods, transparent region construction, and temporal cutoff / no-future control.
- [`docs/history/`](docs/history/) preserves the broader research and productization sequence, including failed hypotheses, experimental pivots, audit rejects, repair logic, and release closure.

The public synthetic experiments are **not** a replay of the complete historical research corpus. They are deliberately small reproducibility surfaces for selected design boundaries.

Useful entry points:

- Research narrative: [`docs/RESEARCH_OVERVIEW.md`](docs/RESEARCH_OVERVIEW.md)
- Findings and negative results: [`docs/research/FINDINGS.md`](docs/research/FINDINGS.md)
- Conceptual research map: [`docs/research/research-map.md`](docs/research/research-map.md)
- Full decision evolution: [`docs/history/LCE_DECISION_EVOLUTION.md`](docs/history/LCE_DECISION_EVOLUTION.md)
- Full reconstructed timeline: [`docs/history/LCE_MASTER_TIMELINE.md`](docs/history/LCE_MASTER_TIMELINE.md)
- Reproducible experiments: [`research/README.md`](research/README.md)
- Portfolio-oriented case study: [`docs/portfolio/LCE_CASE_STUDY.md`](docs/portfolio/LCE_CASE_STUDY.md)

## Current limits and open work

The repository deliberately keeps these categories separate:

- **Exploratory research observations:** point-cloud failures, trend visibility, local structure behavior, multi-membership, higher-order signal quality.
- **Engineering invariants:** source validity, selected immutable support, support qualification, idempotency, effect-aware recovery, non-mutating reads.
- **Frozen V1 boundaries:** factual Memory authority stays outside derived LCE cognition; interpretation is bounded; recursive cognition and current-turn reasoning remain outside standalone V1.
- **Future work:** embedding/model quality, threshold tuning, higher-order precision, future MR/Body integration, and performance optimization.

## Development

```powershell
python -m pytest -q
```

Standalone setup and the replaceable Reference Memory seam are documented in [`docs/standalone-quickstart.md`](docs/standalone-quickstart.md) and [`docs/reference-memory.md`](docs/reference-memory.md).
