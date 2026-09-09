# LCE Master Timeline

## Archive status

**Historical reconstruction / project archive**

This record is written after the standalone LCE V1 release was frozen. It is
source-grounded and intentionally preserves failed hypotheses, audit rejects,
repair boundaries, and evidence limits. It does not rewrite the project so
that the final product appears inevitable.

The primary historical authorities are:

- the existing verified research records, which are preserved and not
  overwritten: [`LCE_EXPERIMENT_CHRONOLOGY_VERIFIED.md`](../research/LCE_EXPERIMENT_CHRONOLOGY_VERIFIED.md),
  [`LCE_DECISION_HISTORY_VERIFIED.md`](../research/LCE_DECISION_HISTORY_VERIFIED.md),
  and [`LCE_ARCHITECTURE_CLAIMS_MATRIX.md`](../research/LCE_ARCHITECTURE_CLAIMS_MATRIX.md);
- committed Git history in the LCE repository;
- the local lab artifacts under `lab/`, treated as reproducible artifact
  authority rather than committed Git authority;
- the preserved product/audit records at the exact LCE V1 worktree
  `C:\projects\w\lce-v1-close`;
- the accepted MR binding record at MR commit
  `930d7f06dc9b8fd4b99ac60bcb4985061ad00e4c`.

The local `lab/` tree and the close-worktree audit reports were not silently
promoted into the frozen release. They are cited as historical evidence with
their scope and status kept explicit.

## Timestamp model

Historical events have several different times. This archive records them
separately:

| Field | Meaning |
|---|---|
| **Observed / Proposed At** | When the problem, hypothesis, or result was stated in the evidence. |
| **Experimented At** | When the experiment or probe was run, if the source records it. |
| **Decision Frozen At** | When the rule or boundary became an explicit accepted/frozen decision. |
| **Implemented At** | When the relevant repository implementation was committed. |
| **Verified At** | When an independent audit or fresh gate verified or rejected the claim. |

Each field is followed by a confidence class:

- `GIT-EXACT` — taken from a commit timestamp or exact Git ancestry;
- `ARTIFACT-EXACT` — taken from a named artifact/report date or exact artifact
  identity;
- `DATE-CONFIRMED` — the source explicitly confirms the calendar date;
- `DEPENDENCY-ORDERED` — order is proven by predecessor/supersedes/data
  dependencies, but an exact date is not available;
- `OWNER-FREEZE` — the owner explicitly froze the decision in the task
  authority;
- `UNKNOWN` — the repository does not support a more precise claim.

No exact hour is inferred for lab experiments whose reports do not contain an
exact time. The many 2026-09-07 lab reports are ordered by their explicit
predecessor and reused-input relationships, not by invented intra-day times.

## Four-track reading key

- **Research** — experiments over raw evidence, semantic blocks, vectors,
  structures, and longitudinal change.
- **Architecture** — authority, representation, port, persistence, and
  boundary decisions.
- **Implementation** — committed LCE code and tests.
- **Audit / Productization** — independent rejection, repair, regression
  capture, release, and closure evidence.

The arrows in the timeline are causal claims supported by the named evidence,
not claims that every later implementation was already present in earlier
research.

## Chronology at a glance

```text
raw text point cloud
  → raw representation failure
  → Semantic Block before embedding
  → semantic-stream boundary correction
  → longitudinal trend experiment
  → vector-first structure discovery
  → multi-scale local structure
  → bounded interpretation / authority boundary
  → Core V0
  → optional one-way MR binding
  → standalone V1 productization
  → adversarial rejects and bounded repairs
  → permanent RED→GREEN closure suite
  → final canonical-order repair
  → frozen release
```

This is a dependency-ordered summary. The detailed entries below retain the
separate timestamp fields and the distinction between research capability,
production implementation, and audit disposition.

## Research track: from raw points to bounded structure

### 1. POINTCLOUD-01 — raw text as a first negative-control point cloud

**Artifact:** `LCE-DIARY-POINTCLOUD-01` / `lab/diary_pointcloud_01/`

- **Observed / Proposed At:** Corpus spans 2026-07-26 through 2026-08-08;
  `ARTIFACT-EXACT` for the corpus range. The earliest owner framing is not
  found verbatim; `UNKNOWN` for that wording.
- **Experimented At:** The artifact is the predecessor to 01R and the
  Semantic Cloud work; exact run time is not recorded, therefore
  `DEPENDENCY-ORDERED`.
- **Decision Frozen At:** The raw point was later frozen as a negative control,
  not as the accepted cognition point; exact freeze time is
  `DEPENDENCY-ORDERED`.
- **Implemented At:** Local lab scripts, not a committed LCE Core feature;
  `UNKNOWN`.
- **Verified At:** Re-read and cross-checked by the A0 research audit;
  `DATE-CONFIRMED` as an A0 audit result on 2026-09-09.

The experiment embedded 91 raw diary units over 14 days and ran raw top-k
similarity plus model interpretation. The original space formed a narrow
similarity cone, roughly `0.51..0.88`. Raw label propagation collapsed all 91
points to one label. The result was useful precisely because it failed:
similarity did not supply a satisfactory cognition unit.

**Causal transition:** raw similarity experiment → dense/overconnected space
→ raw text is retained as evidence and provenance, but not accepted as the
cognition point.

### 2. POINTCLOUD-01R — raw-region reconstruction attempt

**Artifact:** `LCE-DIARY-POINTCLOUD-01R` / `lab/diary_pointcloud_01R/`

- **Observed / Proposed At:** The report is dated 2026-09-07;
  `DATE-CONFIRMED`.
- **Experimented At:** After POINTCLOUD-01 and before Semantic Cloud-02;
  `DEPENDENCY-ORDERED`.
- **Decision Frozen At:** The negative-control status of raw regions is
  confirmed in the later research records; exact original freeze time is
  `UNKNOWN`.
- **Implemented At:** Local lab artifact; exact Git implementation date is
  `UNKNOWN`.
- **Verified At:** A0 research audit, 2026-09-09; `DATE-CONFIRMED`.

Mean-centering, weighted kNN, label propagation, region splitting, and
bounded interpretation produced eight candidate regions. R08 grouped five
different investment objects and the interpreter rejected all five as one
structure. The report explicitly says the raw region is not a Semantic Block.

**Causal transition:** raw-region interpretation failure → semantic
understanding must be paid before embedding → Semantic Block becomes the
research cognition unit.

### 3. SEMANTIC-CLOUD-02 — Semantic Block before embedding

**Artifact:** `LCE-DIARY-SEMANTIC-CLOUD-02` / `lab/diary_semantic_block_02/`

- **Observed / Proposed At:** 2026-09-06/07 report sequence;
  `DATE-CONFIRMED` at calendar-day precision.
- **Experimented At:** After 01/01R and before BLOCK-03;
  `DEPENDENCY-ORDERED`.
- **Decision Frozen At:** The config and report explicitly freeze
  `Raw text is evidence, NOT the cognition point` and the Semantic Block
  pipeline; `ARTIFACT-EXACT`.
- **Implemented At:** Local compiler/research artifact, not yet LCE Core;
  `ARTIFACT-EXACT` for the named files and `UNKNOWN` for an exact run time.
- **Verified At:** A0 research audit on 2026-09-09; `DATE-CONFIRMED`.

The corrected pipeline became:

```text
raw units → first-pass semantic artifacts → Semantic Block → embedding
```

91 raw units produced 667 first-pass artifacts and 129 Semantic Blocks. Every
block retained artifact and raw references. The report recorded 16 regions and
17 isolated points, with evidence strength counts of 8 strong, 6 moderate,
and 2 weak; false regions remained 5/16 and the Type B evaluation-change
trajectory was still unreliable.

This was a representation correction, not a production claim. The LCE Core
remained untouched and external-input based.

### 4. BLOCK-03 — semantic stream instead of day-batch compilation

**Artifact:** `LCE-DIARY-BLOCK-03` / `lab/diary_semantic_block_03/`

- **Observed / Proposed At:** 2026-09-07 report sequence; `DATE-CONFIRMED`.
- **Experimented At:** After Semantic Cloud-02 and before TREND-04;
  `DEPENDENCY-ORDERED`.
- **Decision Frozen At:** The report explicitly states that a Semantic Block
  is a semantic unit, not a time unit; `ARTIFACT-EXACT`.
- **Implemented At:** The semantic-stream and recap-dedup scripts are named
  artifacts; production implementation came later in A2, not here;
  `DEPENDENCY-ORDERED`.
- **Verified At:** A0 research audit on 2026-09-09; `DATE-CONFIRMED`.

The day-batch compiler was replaced by semantic-stream cutting:

```text
same semantic continuum → continue
semantic switch → close and open
one input contains distinct matters → split
recap / repetition → attach or deduplicate, not a new cognition point
```

The corpus changed from 129 to 179 blocks. Mixed blocks fell from about 10 to
3–4; false regions fell from `5/16` to `0/14`; recap processing reduced an
intermediate 210 blocks to 179. SB0008, SB0044, and SB0129 were split, while
the long multi-unit research block SB0021 remained intact.

**Causal transition:** temporal batching hid semantic switches and repetition
→ semantic-stream boundaries expose them → later V1 compiler work must retain
the boundary without turning the lab compiler into a retroactive Core V0
feature.

### 5. TREND-04 — longitudinal discovery under no-future cutoffs

**Artifact:** `LCE-DIARY-TREND-04` / `lab/diary_trend_04/`

- **Observed / Proposed At:** 2026-09-07; `DATE-CONFIRMED`.
- **Experimented At:** After BLOCK-03 and before INSPIRATION-05;
  `DEPENDENCY-ORDERED`.
- **Decision Frozen At:** No-future visibility, independent cutoffs, and
  reverse verification became mandatory evidence for longitudinal claims;
  `ARTIFACT-EXACT` for the experiment record.
- **Implemented At:** Local research experiment only; exact production
  implementation time `UNKNOWN`.
- **Verified At:** A0 research audit on 2026-09-09; `DATE-CONFIRMED`.

Six independent cutoffs physically excluded future blocks. The experiment made
48 main calls; 75% of judgments said the direction could not yet be seen.
Three directions appeared 2–6 days early, shuffle controls did not show
coherent cross-window progression, and one SB0034-related T3 cutoff was a real
miss. TREND-04 still used an LLM-led candidate loop, so it was an evaluation
experiment rather than the final vector-first architecture.

**Causal transition:** time-cutoff discovery can test longitudinal claims, but
LLM-led candidate search is too close to the evidence-selection authority
boundary → move structural discovery before interpretation.

### 6. INSPIRATION-05 — vector-first replay

**Artifact:** `LCE-DIARY-INSPIRATION-05` / `lab/diary_inspiration_05/`

- **Observed / Proposed At:** 2026-09-07; `DATE-CONFIRMED`.
- **Experimented At:** After TREND-04; `DEPENDENCY-ORDERED`.
- **Decision Frozen At:** Vector-first replay and LLM-last interpretation became
  the next research direction; `ARTIFACT-EXACT`.
- **Implemented At:** Local replay scripts and reports; exact intra-day time
  `UNKNOWN`.
- **Verified At:** A0 research audit on 2026-09-09; `DATE-CONFIRMED`.

The experiment froze one 3072-dimensional space and replayed local structure
over 14-day, 30-day, and 41-day prefixes:

| Prefix | Nodes | Edges | Average degree | Isolated | Components | Sustained |
|---|---:|---:|---:|---:|---:|---:|
| P1 14d | 179 | 555 | 6.2 | 10 (6%) | 13 | 42 |
| P2 30d | 302 | 1545 | 10.2 | 10 (3%) | 12 | 144 |
| P3 41d | 489 | 3121 | 12.8 | 9 (2%) | 11 | 263 |

Three old isolated points reconnected after 34, 31, and 29 days; SB0034
accumulated 15 credible edges across 12 dates. The approach also failed in
important ways: more than 40% of nodes entered one giant region and sustained
support showed a noise floor. These failures motivated multi-scale observation
instead of a single binary graph.

### 7. STRUCTURE-06R — multi-scale local structure

**Artifact:** `LCE-DIARY-STRUCTURE-06R` / `lab/diary_structure_06R/`

- **Observed / Proposed At:** 2026-09-07, explicitly recorded as the
  predecessor of later product decisions; `DATE-CONFIRMED`.
- **Experimented At:** After INSPIRATION-05 using the frozen 489-block,
  41-day space; `DEPENDENCY-ORDERED`.
- **Decision Frozen At:** Multi-scale local structure is the strongest research
  direction; H1 is not core ontology; `ARTIFACT-EXACT` for the report.
- **Implemented At:** Local lenses/replay/candidate packaging only; no Core
  production implementation; `DEPENDENCY-ORDERED`.
- **Verified At:** A0 research audit on 2026-09-09; `DATE-CONFIRMED`.

The experiment removed the unique binary graph as the final observation model
and added lenses for local stability, overlap, multi-point structure, and
temporal evolution. At `k=16`, 74 blocks participated in multiple of 97
groups. H1 counts were 129/264/544 for 14/30/41-day prefixes but had no useful
semantic signal. Replay produced 5825 structural candidates, including 3578
`new_overlap` noise-floor events and 304 `structure_grew` events. The
structure-to-structure review found two of six pairs worth attention, four
weak analogies, and zero clear common patterns. Recursive cognition was not
implemented.

**Causal transition:** binary edge/event abstraction over-compressed a dense
space → observe multiple scales and preserve overlap/reconnection → structures
remain derived candidate observations, not canonical authority.

## Architecture track: Core V0 and the MR boundary

### 8. Core V0 — minimal contract-first authority boundary

#### `fa492f9cee8f16e80ccb2faf1c3e36d605ade9fd`

- **Observed / Proposed At:** Research needed a durable boundary without
  owning Memory or vectors; `DEPENDENCY-ORDERED` from the research artifacts.
- **Experimented At:** Not a lab experiment; implementation starts here;
  `UNKNOWN`.
- **Decision Frozen At:** The contract-first Core boundary is encoded by the
  commit; `GIT-EXACT`, 2026-09-06 21:51:22 +08:00.
- **Implemented At:** `GIT-EXACT`, 2026-09-06 21:51:22 +08:00.
- **Verified At:** Fresh Core tests and later A0/A1 audit records;
  `DATE-CONFIRMED` for the audit date, with later V1 verification kept
  separate from V0.

V0 introduced `MemorySubstratePort`, `SemanticConsolidatorPort`, and
`BaselineStorePort`; immutable Baseline revisions; SQLite HEAD/history;
provenance; and normalized equivalence. It accepted caller-selected Memory
IDs and consolidated them into durable Baselines. It did **not** contain the
later V1 Reference Memory pipeline, point discovery, local vector ownership,
or a local Memory/vector backend.

#### `d1eb5f63b427f216df0e38bde48eaff639546391`

- **Observed / Proposed At:** V0 needed stronger audit, provenance, and
  transaction guarantees; `DEPENDENCY-ORDERED`.
- **Experimented At:** Implementation hardening, not a separate lab
  experiment; `UNKNOWN`.
- **Decision Frozen At:** Fail-closed model traces, duplicate-reference
  rejection, strict revision linkage, and atomic SQLite revision/HEAD updates;
  `GIT-EXACT`, 2026-09-06 22:09:19 +08:00.
- **Implemented At:** `GIT-EXACT`, 2026-09-06 22:09:19 +08:00.
- **Verified At:** Later Core and MR binding gates; `DATE-CONFIRMED` at the
  relevant audit dates.

V0 semantics remained a **linear** immutable revision chain with
`previous_baseline_id` and a HEAD pointer. Persistent parallel branches,
merge/drop worktrees, and explicit revert semantics were not implemented.

### 9. MR-LCE-BIND-1 — optional one-way binding

**Commit:** `930d7f06dc9b8fd4b99ac60bcb4985061ad00e4c`

- **Observed / Proposed At:** MR needed an optional read binding to frozen LCE
  while canonical Memory remained MR-owned; `DATE-CONFIRMED` by the accepted
  MR ADR.
- **Experimented At:** Binding acceptance tests and isolated composition;
  `GIT-EXACT`, 2026-09-07 22:50:01 +08:00.
- **Decision Frozen At:** ADR-0026 accepted for MR-LCE-BIND-1;
  `GIT-EXACT` at the same commit.
- **Implemented At:** `GIT-EXACT`, 2026-09-07 22:50:01 +08:00.
- **Verified At:** Real MR Memory → frozen LCE → durable Baseline path passed;
  production activation remained OFF; `DATE-CONFIRMED` by the MR binding
  report.

The authority direction is:

```text
MR canonical Memory
  → explicit stable IDs through MemorySubstratePort
  → LCE Baseline revisions
```

The adapter is one-way. Memory owns points; LCE owns Baseline revisions over
caller-selected points. Baselines never become Evidence, Observation, Memory,
C10, Intent, Appraisal, or Action. No reverse authority was added. Production
Memory admission, retrieval, and LCE invocation remain OFF by default. This
milestone is separate from standalone LCE V1 closure.

## Implementation track: from V0 contracts to standalone V1

The implementation track is deliberately separate from the research track.
Research produced hypotheses and bounded experiment artifacts; implementation
introduced only the contracts and pipeline stages authorized by the V1 freeze.

### Core V0 implementation

| Commit | Implemented boundary |
|---|---|
| `fa492f9cee8f16e80ccb2faf1c3e36d605ade9fd` | Contract-first `MemorySubstratePort`, `SemanticConsolidatorPort`, `BaselineStorePort`, immutable Baseline revisions, SQLite HEAD/history, provenance, and normalized equivalence. |
| `d1eb5f63b427f216df0e38bde48eaff639546391` | Fail-closed trace/reference checks, strict revision linkage, atomic SQLite updates, rollback checks, and audit hardening. |

The implementation at both commits is V0: external Memory/vector ownership and
linear revision semantics. It does not contain Reference Memory, point
discovery, snapshot structure, Worktree promotion, or higher-order V1 behavior.

### Standalone V1 implementation sequence

| Stage | Commit | Implemented surface |
|---|---|---|
| A1 | `b838283140de5ccd9f26eaa13c968e6ad0813665` | Replaceable standalone Reference Memory and immutable Semantic Block states. |
| A2 | `c227fdf3eeaebb8ba28b6e19df250877fc695088` | Semantic-stream compiler and recap-aware block formation. |
| A3 | `4cd631f089cc6e574446d5f189bcf76867fdf35d` | Rebuildable vectors, cutoff snapshots, multi-scale structure, and bounded higher-order candidates. |
| A4 | `d92c9891cd0f2e635c29ea45d494a283591947fc` | Derived cognition Worktrees and conservative promotion through existing Core. |
| A5 | `ac87d712035825c361b3139ddf8dd736d022674f` | Standalone pipeline composition, invalidation, accepted read, packaging, and product boundary documentation. |

Later implementation repairs were bounded to audit findings: Z0 repair commits
`087e5cb`, `da1ff50`, `f99d74a`, `a250788`; selected-state/replay repair
`12d1c6a`; R3 commits `eff90b6`, `d22b330`; and final canonical support-order
repair `808b148`. None introduced MR/Body integration, a second accepted store,
or recursive cognition.

## Audit / Productization track: research authority to V1 closure

### 10. LCE-RESEARCH-A0 — research authority

**Authority:** `LCE-RESEARCH-A0`, represented by
[`LCE_RESEARCH_A0_AUDIT_REPORT.md`](../../LCE_RESEARCH_A0_AUDIT_REPORT.md) and
the three preserved verified research documents.

- **Observed / Proposed At:** The A0 reconstruction and its corrections are
  recorded on 2026-09-09; `ARTIFACT-EXACT` at calendar-day precision.
- **Experimented At:** Repository/lab/MR evidence inspection; exact run time
  not needed and not asserted; `DATE-CONFIRMED` for the audit date.
- **Decision Frozen At:** Verdict `CONFIRMED WITH CORRECTIONS`;
  `OWNER-FREEZE` for the archive authority.
- **Implemented At:** Documentation/audit artifact, not runtime code;
  `ARTIFACT-EXACT`.
- **Verified At:** The report's fresh command and hash checks; `DATE-CONFIRMED`.

A0 confirmed the main research evolution but corrected several claims:

- the “stateless Foundation Model repeatedly pays the same cognitive cost”
  paragraph was not found verbatim;
- `biology → animal → human` was not found verbatim;
- Core V0 has replaceable ports and a local SQLite Baseline store, not a local
  Memory/vector backend;
- Git worktree language is an analogy to the implemented linear revision/HEAD
  chain, not implemented branch/merge/drop semantics;
- no accepted Hot Start decision sharing the same LCE ontology was found.

The corrected history is the authority used by this archive.

### 11. V1 architecture freeze and A1–A5

The 2026-09-09 productization sequence deliberately expanded the standalone
surface without rewriting V0 history. The frozen V1 chain was:

```text
Reference Memory
  → Semantic Block compiler
  → rebuildable vectors
  → snapshot structure discovery
  → bounded higher-order candidate
  → bounded interpretation
  → OPEN cognition Worktree
  → conservative promotion through existing Baseline/HEAD
  → accepted current-valid read
```

MR, Body, C10, Persona, Intent, ActionPolicy, current-turn reasoning, and
reverse authority were outside the standalone product boundary.

| Stage | Commit and Git time | Product meaning |
|---|---|---|
| A1 Reference Memory substrate | `b838283140de5ccd9f26eaa13c968e6ad0813665`, 2026-09-09 05:15:37 +08:00 (`GIT-EXACT`) | Added standalone Reference Memory, validity/provenance, immutable Semantic Block states, vectors, and rebuildable substrate seams. |
| A2 Semantic Block compiler | `c227fdf3eeaebb8ba28b6e19df250877fc695088`, 05:18:34 (`GIT-EXACT`) | Productionized semantic stream compilation and recap-aware block formation. |
| A3 Snapshot structure discovery | `4cd631f089cc6e574446d5f189bcf76867fdf35d`, 05:22:42 (`GIT-EXACT`) | Added cutoff snapshots, local multi-scale structure, diffs, and bounded higher-order candidates. |
| A4 cognition Worktree + promotion | `d92c9891cd0f2e635c29ea45d494a283591947fc`, 05:26:26 (`GIT-EXACT`) | Added OPEN/MERGED/DROPPED derived worktrees and conservative promotion through existing Core. |
| A5 product pipeline | `ac87d712035825c361b3139ddf8dd736d022674f`, 05:37:49 (`GIT-EXACT`) | Connected the standalone pipeline, read path, invalidation, packaging, and product documentation. |

The initial closure candidate was `16b014e1a1d3b4a225d4049d7df9615c93921dc4`
at 05:39:50. Its ordinary tests and install were green, but that was an
implementation candidate, not independent closure. The later Z0 audit
rejected it.

### 12. Z0 — first independent closure reject

**Audited HEAD:** `16b014e1a1d3b4a225d4049d7df9615c93921dc4`

- **Observed / Proposed At:** Product closure claim at the initial V1
  candidate; `GIT-EXACT`.
- **Experimented At:** Independent adversarial runtime probes on 2026-09-09;
  `DATE-CONFIRMED`.
- **Decision Frozen At:** Z0 verdict `REJECT — LCE V1 PRODUCT CLOSURE
  BLOCKED`; `ARTIFACT-EXACT` in the preserved audit report.
- **Implemented At:** The rejected candidate's A1–A5 commits;
  `GIT-EXACT`.
- **Verified At:** 2026-09-09 Z0 audit; `DATE-CONFIRMED`.

The eight blockers were:

1. **B1 invalidation copied the old conclusion** instead of establishing
   corrected support;
2. **B2 historical state was mutable**, allowing later continuation to alter
   an earlier accepted source closure;
3. **B3 fake higher-order aliasing** treated equivalent center/k observations
   as distinct cognition support;
4. **B4 unrelated support inflation** allowed global snapshot/provenance
   changes to count as new support;
5. **B5 bounded interpretation was missing** from the production path;
6. **B6 failed input was overtaken** by later input;
7. **B7 replay was not pipeline-complete**, because compiler replay could skip
   downstream durable effects;
8. **B8 the Reference Memory port was decorative**, because an independent
   backend could not run the actual V1 pipeline.

The audit also found **N2**, a linked-structure diff defect: unchanged
overlaps were reported as newly linked structures. Ordinary tests were green,
but the independent runtime probes found real semantic and recovery defects.

**Causal transition:** green ordinary suite → adversarial runtime rejects the
implementation → repairs must make the frozen boundaries real and recoverable,
without changing the research ontology or expanding into MR/Body.

### 13. R1 repair tranche and Z1

The first bounded repair tranche followed Z0:

| Repair commit | Repair boundary |
|---|---|
| `087e5cb37e3b96ed0d05e51b11a84eeba07535fe` | Preserve cutoff-bound cognition state. |
| `da1ff503fd4d1099c745f811a964f381fb181442` | Make structure support and bounded interpretation explicit. |
| `f99d74a39f55402ad9be35b7d05313989ec6a40c` | Complete recovery and substrate-replacement seams. |
| `a2507888d5615868510682f0e799f2a1faf6f014` | Expose recovery and replacement contracts. |

- **Observed / Proposed At:** Each repair was driven by a named Z0 blocker;
  `DEPENDENCY-ORDERED` within the repair tranche.
- **Experimented At:** Fresh tests and independent probes after the tranche;
  `DATE-CONFIRMED` as 2026-09-09.
- **Decision Frozen At:** The repair report said `Z0 BLOCKER REPAIR COMPLETE —
  READY FOR RE-AUDIT`, not product closure; `ARTIFACT-EXACT`.
- **Implemented At:** The four exact commits above; `GIT-EXACT`.
- **Verified At:** Z1 re-audit at `9ea947ab9f495b256644b2d022907678e747ea1c`;
  `GIT-EXACT` and `DATE-CONFIRMED`.

Z1 found a root-cause convergence rather than four unrelated failures:

- B3, B4, B6, B8, and N2 passed the specified controls;
- B1/B2/B5 shared a selected immutable block/state mapping defect;
- B7 remained a recovery/completed-replay defect.

The repair report recorded 85 green tests, but the independent Z1 verdict
remained:

```text
REJECT — LCE V1 PRODUCT CLOSURE BLOCKED
```

### 14. R2 selected-state/replay repair and Z2

**Implementation commit:** `12d1c6a97808ca81d6822fea4a2be97285c88012`
(`fix: preserve selected immutable support`). The accompanying repair record
was committed as `ecf41377224881b51e242222c185acf191b324da`.

- **Observed / Proposed At:** The remaining B1/B2/B5 mapping defect and B7
  replay defect from Z1; `DEPENDENCY-ORDERED`.
- **Experimented At:** Selected immutable support, historical promotion,
  invalidation, and recovery probes; `DATE-CONFIRMED`, 2026-09-09.
- **Decision Frozen At:** Exact selected `(block_id, state_id)` support became
  first-class through interpretation, Worktree, Baseline, and read;
  `ARTIFACT-EXACT`.
- **Implemented At:** `GIT-EXACT`, `12d1c6a` at 15:24:51 +08:00.
- **Verified At:** Z2 audit at `ecf4137`, `DATE-CONFIRMED`.

Z2 passed B1, B2, B3, B5, B6, B8, and N2 controls, but still rejected closure:

- **B4 REGRESSION:** provenance-only immutable state change was counted as
  new cognition support;
- **B7 NOT FIXED:** the reference interpreter made the recovery matrix look
  correct, while a legitimate package-sensitive interpreter exposed repeated
  cognition effects.

The distinction was explicit:

```text
reference interpreter: 30/30 equivalent
package-sensitive interpreter: 24/30 equivalent
```

The result was **93 tests green**, but the product verdict was still
`REJECT — LCE V1 PRODUCT CLOSURE BLOCKED`.

### 15. Permanent closure suite and oracle correction

**Test authority:** `69fe0bc05bbc232b371f123628a8054340b63f70`.

- **Observed / Proposed At:** Repeated independent audit cost and hidden
  defects required converting GPT-6 discoveries into permanent repository
  regressions; `OWNER-FREEZE`, 2026-09-09.
- **Experimented At:** The known-broken `ecf4137` base was tested before
  production repair; `ARTIFACT-EXACT`.
- **Decision Frozen At:** Permanent closure authority became the tracked
  RED→GREEN suite; `GIT-EXACT`, 16:24:34 +08:00.
- **Implemented At:** `69fe0bc`; `GIT-EXACT`.
- **Verified At:** RED evidence was recorded before the R3 production fixes;
  `DATE-CONFIRMED`.

The new permanent tests intentionally failed on the known-broken base:

- closure invariants: `6 passed, 4 failed`;
- recovery suite: `20 passed, 12 failed`, with the 30-case matrix at
  `20/30 equivalent, 10/30 RED` under the corrected durable-effect oracle;
- retained Z0/Z1/E2E controls: `21 passed`;
- full suite: `119 passed, 16 failed`.

The failures were not hidden with skips, xfails, fixture-ID branches, or a
promotion-threshold change. The correction commit
`f7ce0874c688b4654534f5a8ddd623cc62a23d95` aligned the recovery oracle with
durable cognition effects. The key semantic distinction was:

```text
pre-durable interpreter retry is allowed
post-durable cognition effect must be recovery-idempotent
```

### 16. R3 and Q1

The bounded R3 production repair was:

| Commit | Effect |
|---|---|
| `eff90b6431688effb599f3780ce9a4911a7c7e86` | Separate recap provenance from cognition support. |
| `d22b33047c6f1526d59d5c2c72f4e16333dae2da` | Reuse durable cognition effects during recovery. |

- **Observed / Proposed At:** B4/B7 permanent RED evidence;
  `DEPENDENCY-ORDERED`.
- **Experimented At:** Fresh repair gates and independent controls on
  2026-09-09; `DATE-CONFIRMED`.
- **Decision Frozen At:** Support identity was separated from provenance
  identity, and committed recovery effects became reusable;
  `OWNER-FREEZE` through the R3 repair report.
- **Implemented At:** `GIT-EXACT`, 21:39:45 and 21:45:27 +08:00.
- **Verified At:** Q1 audited HEAD `b89d6a333bc0f806c8964dbd09381d21868d8b10`;
  `GIT-EXACT`, 21:47:58 +08:00.

The Q1 audit independently reported:

```text
B4 independently passed
B7 independently passed
30/30 recovery matrix
135 tests
READY FOR FINAL GPT-6 CLOSURE AUDIT
```

This was a readiness verdict, not yet the final closure verdict.

### 17. Z3 — final blind spot

The final blind audit at Q1 HEAD did not omit its own embarrassment. It found
one last B4 permutation path:

```text
pure recap of oldest selected block
  → recency-selected order changes
  → order-sensitive support fingerprint changes
  → false promotion
```

Removing `state_id` from the support fingerprint was necessary but not
sufficient. The permanent fixture repeatedly recapped the newest block, so its
selected order never permuted and the test did not observe this path. The Z3
verdict remained:

```text
REJECT — LCE V1 PRODUCT CLOSURE BLOCKED
```

The audit showed 135 tests, 30/30 recovery, and clean install, but test
integrity failed because the permanent fixture did not cover oldest/middle
recap permutations. This was a test-design failure, not a reason to erase the
historical RED→GREEN record.

### 18. Final B4 repair and frozen release

**Test-first commit:** `516826c47631e8e5bc7bf0e1f00eef746f29d05b`
(`test: cover recap ordering without support inflation`). Its historical RED
was `3 RED / 1 passed`, exposing the oldest/middle/newest ordering cases.

**Final implementation commit:**
`808b148960f8ae5852cd78a7b8343611539631b2`
(`fix: canonicalize cognition support fingerprint order`). The repair
canonicalized ordering for qualifying support fingerprints while preserving
exact selected ordering for provenance.

- **Observed / Proposed At:** Z3 permutation blind spot; `GIT-EXACT` at the
  audited Q1 HEAD.
- **Experimented At:** Test-first RED at `516826c`; `GIT-EXACT`,
  2026-09-09 22:27:09 +08:00.
- **Decision Frozen At:** `provenance ordering != qualifying cognition-support
  canonical identity`; `OWNER-FREEZE` through the final closure gate.
- **Implemented At:** `GIT-EXACT`, 2026-09-09 22:28:39 +08:00.
- **Verified At:** Final F1 mechanical gates and exact-HEAD release audit;
  `DATE-CONFIRMED`, 2026-09-09.

Final gates:

```text
closure invariants: 14 passed
recovery suite: 32 passed
normalized recovery matrix: 30/30
retained regressions + E2E: 21 passed
full suite: 139 passed
mypy src/lce: clean
Ruff src tests: clean
isolated exact-HEAD install/import/smoke: passed
```

The release was frozen with:

- implementation HEAD `808b148960f8ae5852cd78a7b8343611539631b2`;
- canonical `master` fast-forwarded from `c84e528a...` to that implementation;
- release metadata commit `047cf4eb15d1ae36779769d7192e769f76654fdb`;
- annotated tag `v1.0.0` resolving to `047cf4e...`;
- release record [`LCE_V1_RELEASE_RECORD.md`](../../LCE_V1_RELEASE_RECORD.md).

The tag points to the metadata boundary; the record identifies `808b148...` as
the final verified implementation. MR integration is explicitly outside
standalone V1 closure.

## Cross-track causal index

| Research result or failure | Architecture correction | Implementation / audit consequence |
|---|---|---|
| Raw points formed giant/weak regions. | Raw Evidence is not the cognition point. | Semantic Block compiler and provenance-preserving evidence boundary. |
| Day batching mixed semantic matters and hid recap repetition. | Blocks are semantic units, not time units. | Semantic-stream compiler and recap handling. |
| TREND-04 used LLM-led candidate discovery. | No-future evaluation is required; discovery should precede bounded interpretation. | Vector-first replay and LLM-last direction. |
| INSPIRATION-05 produced giant regions/noise floors. | Do not make one binary graph canonical. | Multi-scale derived structure observations. |
| STRUCTURE-06R found partial structure↔structure signal. | Higher-order cognition remains bounded and non-authoritative. | One extra bounded candidate level, no recursive loop. |
| Core V0 needed durable authority without owning Memory. | Ports, immutable Baseline revisions, SQLite HEAD/history. | `fa492f9` and `d1eb5f6`; no V1 features attributed backward. |
| MR needed optional LCE consumption. | MR Memory remains canonical; adapter is one-way and default-off. | `930d7f0`; standalone V1 remains separate. |
| Z0–Z2 found runtime defects despite green suites. | Frozen seams must be independently adversarially exercised. | Permanent closure suite and RED evidence. |
| Z3 found order-sensitive support inflation. | Provenance order and qualifying support identity are different. | `516826c` RED → `808b148` repair → 139-test closure. |

## Final boundary

### Non-V1 future work

The following are explicitly non-blocking future work, not unfinished V1
requirements:

- embedding/model quality;
- threshold tuning;
- higher-order precision;
- future MR/Body integration;
- performance optimization.

This archive does not continue into speculative V2 architecture. It ends at
the frozen release identity.

## LCE V1 ENGINEERING CLOSED
