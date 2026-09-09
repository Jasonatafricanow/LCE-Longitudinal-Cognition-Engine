# LCE Research Repository Presentation — Design

Date: 2026-09-10
Status: Proposed for implementation after owner review
Scope: Documentation and navigation only; no LCE runtime, schema, authority, or test-contract changes

## 1. Problem

The repository already contains substantial research evidence, decision history, experiments, closure reports, and portfolio material, but the public entry path does not expose that work.

The current root README leads with the V1 pipeline and product boundary. A first-time reader can understand what the implementation does, but not why LCE exists, which hypotheses failed, which experiments changed the architecture, or how the final authority boundaries were derived.

This creates a presentation failure rather than a research-record failure: the evidence is present, but the repository does not make the research story legible.

## 2. Goal

Turn the repository from a code-first presentation into a research-engineering presentation without rewriting or duplicating the historical record.

A reader should be able to answer, in order:

1. What problem is LCE trying to solve?
2. What is the central architectural claim?
3. What was tried before the current design?
4. Which experiments or failures changed the design?
5. What does V1 currently implement?
6. What does V1 explicitly not claim?
7. Where can the evidence, experiments, history, and implementation contracts be inspected?

## 3. Non-goals

This documentation pass will not:

- change LCE Core, V1 runtime behavior, schemas, stores, providers, or APIs;
- alter accepted Memory/LCE/Body authority boundaries;
- reinterpret derived structures as factual authority;
- claim statistical or scientific validation beyond the actual experiment evidence;
- rewrite historical documents to make old decisions appear cleaner in hindsight;
- duplicate the full contents of `LCE_DECISION_EVOLUTION.md`, `LCE_MASTER_TIMELINE.md`, or portfolio documents;
- add new experimental claims that are not supported by repository evidence.

## 4. Source-of-truth rule

The presentation layer must be downstream of existing evidence.

Narrative claims in the new README, `RESEARCH_OVERVIEW.md`, and `FINDINGS.md` must be traceable to one or more of:

- `docs/history/LCE_DECISION_EVOLUTION.md`;
- `docs/history/LCE_MASTER_TIMELINE.md`;
- verified research chronology / decision documents already in the repository;
- `research/experiments/*` and their tests;
- V1 closure / repair reports;
- accepted architecture and boundary documents;
- current implementation and test state.

If an interpretation is an owner reconstruction rather than a contemporaneous recorded decision, it must be labeled as such rather than silently promoted to history.

## 5. Recommended information architecture

The repository should use one public reading path rather than create a second research archive.

```text
README.md
│
├── docs/RESEARCH_OVERVIEW.md
│   ├── docs/research/research-map.md
│   ├── docs/research/FINDINGS.md
│   ├── docs/history/LCE_DECISION_EVOLUTION.md
│   └── research/README.md
│
├── docs/architecture/*
├── docs/history/*
├── docs/portfolio/*
└── research/experiments/*
```

Existing historical and technical documents remain in place. The new files are index and synthesis layers, not replacement authorities.

## 6. Root README design

The root README becomes the public research-engineering entry point.

### 6.1 Opening problem statement

Lead with the practical problem rather than the pipeline:

> Agent systems often recover historical context by handing old records back to a foundation model and asking it to reconstruct meaning again. LCE explores a different question: can durable longitudinal understanding be formed, inspected, falsified, and reused without turning model inference into factual authority?

The wording may be refined during implementation, but the semantic distinction must remain:

```text
Memory = what happened
LCE = what was learned longitudinally
current-turn model / Body = what reasons and acts now
```

### 6.2 Research thesis

State the current design thesis in compact form:

```text
Raw Evidence
  -> semantic segmentation
  -> Semantic Blocks
  -> vector / local structural observations
  -> bounded candidate interpretation
  -> durable Worktree
  -> conservative accepted Baseline revision
  -> deterministic Understanding read
```

Each arrow is a bounded transformation, not an automatic increase in authority.

### 6.3 Experiment-driven evolution table

Add a compact table showing that architecture followed evidence rather than preceding it.

Target rows:

- POINTCLOUD-01 / POINTCLOUD-01R;
- Semantic Cloud-02;
- BLOCK-03;
- TREND-04;
- INSPIRATION-05;
- STRUCTURE-06R;
- Z0–R3 closure / repair sequence.

Columns:

| Stage | Starting assumption | Observation | Architecture consequence |

The table must use actual recorded values only where the repository provides them. It must distinguish exploratory observations from product correctness tests.

### 6.4 Key findings

Surface 6–10 findings with links to `docs/research/FINDINGS.md` rather than explaining all of them inline.

The initial candidate set is:

1. Similarity discovers relatedness, not cognition.
2. Raw text is evidence, not the corrected cognition point.
3. Semantic continuity is not equivalent to arbitrary time buckets.
4. Longitudinal claims require no-future evaluation and negative controls.
5. Exclusive clustering loses legitimate multi-membership.
6. Derived structures are observations, not factual authority.
7. Provenance identity is not the same as qualifying cognition-support identity.
8. Replay, recap, and repeated consumption must not manufacture support.
9. Green unit/integration tests are insufficient if recovery semantics are tested only with a weak oracle.
10. Language interpretation should consume a bounded evidence package rather than search freely for evidence supporting its own interpretation.

### 6.5 What V1 is / is not

Preserve the existing V1 boundary prominently:

- standalone, contract-first longitudinal cognition pipeline;
- Reference Memory is a replaceable local substrate;
- accepted Baseline/HEAD remains the revision authority inside LCE;
- read path is deterministic and model-free;
- current-turn reasoning, action, Persona, Body, MR runtime behavior, and factual Memory authority are outside V1's standalone product boundary.

### 6.6 Evidence and reproducibility

Add links to:

- `research/README.md`;
- the three existing public synthetic experiment directories;
- `docs/research/research-map.md`;
- closure reports / test status;
- quickstart and architecture docs.

Do not present the synthetic public experiments as the complete historical research record. They are reproducible public boundary experiments; the deeper historical sequence is documented in history/research documents.

### 6.7 Current limitations and unresolved questions

Include a short section naming unsolved areas instead of implying a completed theory of cognition.

At minimum distinguish:

- validated engineering invariants;
- exploratory research observations;
- deliberately excluded capabilities;
- future research questions.

## 7. `docs/RESEARCH_OVERVIEW.md`

Create a 5–10 minute narrative overview between the README and the long historical record.

Required sections:

1. Research question.
2. Why retrieval/prompt reconstruction was not considered sufficient.
3. Early raw-point experiments and failure.
4. Semantic Block correction.
5. Temporal falsification and no-future evaluation.
6. Vector-first local structure and giant-region/noise failures.
7. Overlapping structure and bounded higher-order cognition.
8. Authority separation: evidence, candidates, Worktree, Baseline, read path.
9. Productization failures: support inflation, recap/provenance identity, restart recovery.
10. What V1 finally freezes.
11. What remains unresolved.
12. Reading guide to experiments, history, architecture, and code.

This file should synthesize; it should not copy long passages from existing history documents.

## 8. `docs/research/FINDINGS.md`

Create a durable findings index organized by claim rather than chronology.

Each finding uses the following schema:

```text
Finding
Evidence
What it supports
What it does not support
Architecture consequence
Primary references
Status: exploratory | engineering invariant | frozen boundary | open question
```

This prevents research observations from being flattened into slogans.

The initial findings set should cover the ten items listed in README §6.4, with evidence drawn from the repository.

Negative results must remain visible. In particular, giant components, noise-floor sustained triggers, weak H1/TDA or structure-to-structure results, real misses, recap support inflation, and recovery defects should not be omitted simply because later architecture solved around them.

## 9. Existing research surfaces

### 9.1 `docs/research/research-map.md`

Keep it as the conceptual map from similarity through longitudinal structure to the LCE Core authority boundary. Only make link/navigation edits if required.

### 9.2 `research/README.md`

Keep it as the reproducible experiment entry point. Add a clear distinction between:

- public synthetic reproducibility experiments; and
- the full historical research chronology documented elsewhere.

### 9.3 `docs/history/*`

Treat these as detailed historical evidence and decision reconstruction. Do not rewrite them into marketing copy.

### 9.4 `docs/portfolio/*`

Keep the portfolio package separate from canonical research documentation. The root README may link to it as an optional project/case-study view, but portfolio prose must not become research authority.

### 9.5 Root closure / repair reports

Retain existing files in this pass. The README may group them under an implementation verification section. Moving them is out of scope because file relocation would create unnecessary link churn.

## 10. Reader paths

The documentation should support four distinct readers.

### 10.1 30-second reader

Reads root README opening, core distinction, architecture sketch, and current status.

### 10.2 5–10 minute technical reader

Reads `docs/RESEARCH_OVERVIEW.md` and the experiment-evolution table.

### 10.3 Research reviewer

Follows `FINDINGS.md`, `research-map.md`, experiment READMEs/tests, and detailed history.

### 10.4 Implementation reviewer

Moves from README into architecture contracts, source, quickstart, closure reports, and tests.

No reader should need to discover the existence of the research history by manually browsing directories.

## 11. Presentation constraints

- Use precise, non-promotional language.
- Prefer falsifiable claims over feature adjectives.
- Separate empirical observation from interpretation.
- Separate exploratory experiments from product verification.
- Preserve explicit negative results.
- Avoid calling candidate regions, vectors, or Baselines "truth" or "memory".
- Do not imply MR production activation if the current repository says it remains disabled/out of scope.
- Do not imply that public synthetic experiments reproduce every historical result.
- Avoid README bloat: detailed evidence belongs in linked documents.

## 12. Files expected to change

Implementation should normally touch only:

```text
README.md                              # replace public entry narrative
docs/RESEARCH_OVERVIEW.md              # new synthesis document
docs/research/FINDINGS.md              # new claim-index document
research/README.md                      # small navigation/scope clarification
docs/research/research-map.md           # optional link/navigation-only edits
```

No `src/`, runtime schema, database, provider, or production test file is expected to change.

If implementation discovers that a factual claim requires correcting a historical document rather than merely linking it, stop and treat that as a separate evidence-correction task.

## 13. Validation

Because this is a documentation-only change, validation focuses on integrity and traceability.

### Required checks

1. Every new historical numeric claim is traceable to an existing repository source.
2. Every experiment name links to a real file or directory.
3. All relative Markdown links resolve.
4. README does not contradict `LCE_V1_BOUNDARIES.md` or runtime architecture docs.
5. `RESEARCH_OVERVIEW.md` does not promote exploratory observations into validated scientific conclusions.
6. `FINDINGS.md` labels the status of every finding.
7. Existing research tests remain untouched and pass if the local execution environment is available.
8. Documentation changes contain no placeholders such as TBD/TODO.

### Acceptance criteria

A new reader should be able to infer from the README alone that:

- LCE is a longitudinal cognition research-engineering project, not merely an agent-memory package;
- its architecture changed in response to experiments and negative results;
- Memory, LCE-derived understanding, and current-turn reasoning are intentionally separate authorities;
- the repository contains reproducible experiments and a deeper historical record;
- V1 has explicit limitations and does not claim a solved general cognition model.

## 14. Implementation sequence

After owner approval of this design:

1. create an evidence matrix mapping README/overview/findings claims to repository sources;
2. rewrite the root README;
3. add `docs/RESEARCH_OVERVIEW.md`;
4. add `docs/research/FINDINGS.md`;
5. clarify navigation in `research/README.md` and, if needed, `research-map.md`;
6. run link/claim/consistency review;
7. inspect the final Git diff specifically for accidental authority or scope drift.

Implementation planning will be written separately after this design is reviewed and approved.
