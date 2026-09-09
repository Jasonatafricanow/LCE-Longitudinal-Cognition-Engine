# LCE Research Repository Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reframe the LCE repository so a first-time technical reader can see the owner's architecture-design process: problem framing, experiment-driven pivots, negative results, correction mechanisms, authority boundaries, and the final V1 implementation.

**Architecture:** Keep the existing research/history/portfolio records as evidence authorities and add a thin public narrative layer above them. The root README becomes the 30-second entry point; `docs/RESEARCH_OVERVIEW.md` becomes the 5–10 minute research narrative; `docs/research/FINDINGS.md` becomes the claim-oriented evidence index; existing experiment/history documents remain the deep evidence layer. No runtime, schema, store, provider, or production-test behavior changes.

**Tech Stack:** Markdown documentation, existing Python/pytest research tests, Git/GitHub relative links.

**Spec:** `docs/superpowers/specs/2026-09-10-lce-research-repository-presentation-design.md`

## Global Constraints

- Documentation and navigation only; no LCE runtime, schema, authority, or test-contract changes.
- Do not change accepted Memory/LCE/Body authority boundaries.
- Derived vectors, regions, structures, Worktrees, and Baselines must not be described as factual Memory or truth.
- Historical numeric claims must be traceable to existing repository evidence.
- Owner reconstruction must be labeled rather than presented as contemporaneous historical fact.
- Exploratory research observations, engineering invariants, frozen boundaries, and open questions must remain explicitly distinguishable.
- Negative results and real misses must remain visible.
- Do not imply MR production activation when current repository evidence says the binding is disabled/out of scope.
- Do not imply that the public synthetic experiments reproduce the entire historical research sequence.
- Avoid promotional language; prefer falsifiable claims and architecture consequences.
- No `src/`, runtime schema, database, provider, or production test changes are expected.

---

## File Structure

### Files to create

- `docs/RESEARCH_OVERVIEW.md` — 5–10 minute narrative of how LCE evolved and why each major architectural turn happened.
- `docs/research/FINDINGS.md` — claim-oriented research/engineering findings index, with evidence, limits, status, and architecture consequence.

### Files to modify

- `README.md` — public research-engineering entry point and shortest reader path.
- `research/README.md` — distinguish public synthetic reproducibility experiments from the deeper historical research record and link upward to the overview/findings/history.
- `docs/research/research-map.md` — navigation-only edits if required after the new overview/findings files exist.

### Existing evidence authorities to consume, not rewrite

- `docs/history/LCE_DECISION_EVOLUTION.md`
- `docs/history/LCE_MASTER_TIMELINE.md`
- `docs/history/LCE_V1_CLOSURE_HISTORY.md`
- verified research chronology/decision/claims documents already linked from history
- `research/experiments/semantic_neighbourhood/README.md`
- `research/experiments/region_discovery/README.md`
- `research/experiments/temporal_cutoff/README.md`
- root V1 closure/repair/release reports
- `docs/architecture/LCE_V1_RUNTIME.md`
- `docs/architecture/LCE_V1_BOUNDARIES.md`
- `docs/portfolio/LCE_PROJECT_SUMMARY.md` as an optional portfolio view, not research authority

---

## Evidence Matrix to Use During Writing

The implementation must preserve these evidence-to-claim relationships. Verify exact values against source files before writing them into public prose.

| Narrative claim | Primary evidence | Required framing |
|---|---|---|
| Raw text was a poor cognition point | POINTCLOUD-01 / POINTCLOUD-01R in `LCE_DECISION_EVOLUTION.md` | Experimental failure; similarity/connectivity did not justify cognition identity |
| Semantic understanding moved before embedding | Semantic Cloud-02 | Research representation decision, not a claim that V0 Core owned the compiler |
| Semantic boundaries replaced day/time buckets | BLOCK-03 | Architecture pivot caused by mixed-block / false-region behavior |
| Longitudinal claims require no-future evaluation | TREND-04 + temporal cutoff experiment | Falsification/evaluation requirement; retain real miss and negative controls |
| Discovery moved toward vector-first local structure with LLM-last interpretation | INSPIRATION-05 | Response to model-led discovery/evaluation entanglement and giant-region/noise behavior |
| Exclusive clustering was rejected | STRUCTURE-06R | Overlapping multi-membership is legitimate; region/structure still derived, not authority |
| Higher-order cognition remained bounded | STRUCTURE-06R + authority docs | Weak evidence prevented recursive promotion |
| Worktree must remain separate from accepted Baseline | V1 productization + Z0/Z1 | Durable proposal/accepted-state separation |
| Provenance identity differs from qualifying cognition support | Z1/Z2/R3 repair history | Engineering invariant derived from recap/support inflation bugs |
| Replay/recovery needs durable effect semantics | Z0–Z2/R3 closure history | Green tests with a weak oracle were insufficient; richer legal interpreters exposed defects |
| Read-time model reasoning is forbidden | V1 runtime/boundary docs | Deterministic non-mutating read path |
| Final V1 is a bounded standalone product, not solved general cognition | V1 boundaries/release reports | Product boundary and explicit limitations |

---

### Task 1: Rewrite the Root README Around Architecture-Design Reasoning

**Files:**
- Modify: `README.md`
- Read: `docs/history/LCE_DECISION_EVOLUTION.md`
- Read: `docs/architecture/LCE_V1_BOUNDARIES.md`
- Read: `docs/portfolio/LCE_PROJECT_SUMMARY.md`
- Read: root closure/release reports

**Interfaces:**
- Consumes: evidence authorities listed in the evidence matrix.
- Produces: the canonical public entry path used by later documents; links to `docs/RESEARCH_OVERVIEW.md`, `docs/research/FINDINGS.md`, `research/README.md`, history, architecture, quickstart, and verification reports.

- [ ] **Step 1: Capture the current README before editing**

Run:

```bash
git show HEAD:README.md > /tmp/lce-readme-before.md
```

Expected: `/tmp/lce-readme-before.md` contains the existing V1 pipeline/boundary README so no useful product-boundary wording is accidentally lost.

- [ ] **Step 2: Verify the core architecture distinction against existing sources**

Read the relevant sections and confirm that this public shorthand remains consistent with repository authority:

```text
Memory = what happened
LCE = what was learned longitudinally
current-turn model / Body = what reasons and acts now
```

Do not proceed with wording that would make LCE a factual-memory owner or current-turn reasoning engine.

- [ ] **Step 3: Replace the opening with the research problem and current thesis**

The README opening must explicitly answer these two questions before setup instructions:

```markdown
# LCE V1 — Longitudinal Cognition Engine

LCE investigates a practical weakness in long-running agent systems: historical records are often retrieved and handed back to a foundation model, which must reconstruct longitudinal meaning again at each use.

The project asks a narrower question: can durable longitudinal understanding be formed, inspected, falsified, revised, and reused without turning model inference or geometric similarity into factual authority?
```

Then retain the three-way authority distinction and a compact final V1 pipeline.

- [ ] **Step 4: Add an experiment-driven evolution table**

Add a compact table with these rows, after verifying exact values/wording in the history source:

```markdown
| Stage | Starting assumption | What the experiment exposed | Architecture consequence |
| --- | --- | --- | --- |
| POINTCLOUD-01 / 01R | Raw text points plus similarity could recover cognition | Similarity produced connectedness/giant structure without a reliable cognition unit | Raw evidence remains evidence; semantic understanding must precede the corrected cognition point |
| Semantic Cloud-02 | Vectorization could carry the segmentation burden | Mixed raw units were semantically entangled | Introduce Semantic Blocks before embedding |
| BLOCK-03 | Time/day boundaries were an acceptable block boundary | Semantic switches crossed time buckets and mixed matters inside a day | Block identity follows semantic continuity, not clock boundaries |
| TREND-04 | A model-led loop could discover and judge emerging trends | Cutoff evaluation exposed delayed visibility, real misses, and hindsight risk | Require no-future cutoffs, chronological replay, and negative controls |
| INSPIRATION-05 | Sustained binary similarity would reveal longitudinal structure | Giant regions and a large noise floor appeared | Separate structural discovery from bounded language interpretation; move toward LLM-last |
| STRUCTURE-06R | One exclusive cluster could represent a cognition point | Many points legitimately participated in multiple local structures | Use overlapping, local, scale-dependent derived structure |
| Z0–R3 | Passing normal test suites was enough to establish product correctness | Recap/support inflation, provenance leakage, and recovery defects survived earlier green suites | Freeze support identity, immutable selected provenance, and durable recovery semantics as explicit contracts |
```

Where exact numeric evidence is added, cite/link the source document in the table or immediately below it.

- [ ] **Step 5: Add a concise “What the research changed” findings section**

Surface only 6–10 claims, each as a one-line finding linked to `docs/research/FINDINGS.md`. Include negative findings, not only successes.

Required themes:

```text
similarity != cognition
raw evidence != cognition point
semantic continuity != time bucket
no-future evaluation
multi-membership over exclusive clustering
derived structure != authority
provenance identity != cognition-support identity
replay/recap/repeated use must not manufacture support
bounded interpretation rather than evidence-seeking interpretation
```

- [ ] **Step 6: Preserve and sharpen the V1 boundary section**

The README must state, in plain language:

```text
V1 owns a bounded standalone cognition pipeline and accepted LCE Baseline revisions.
It does not own production factual Memory, MR/Body current-turn reasoning, Persona, Intent, ActionPolicy, or general cognition.
Read-time Understanding access is deterministic and model-free.
```

Link to `docs/architecture/LCE_V1_RUNTIME.md` and `docs/architecture/LCE_V1_BOUNDARIES.md`.

- [ ] **Step 7: Add reader paths and evidence links**

Add a compact section such as:

```markdown
## Read by depth

- 5–10 minute research narrative: [`docs/RESEARCH_OVERVIEW.md`](docs/RESEARCH_OVERVIEW.md)
- Claim-by-claim findings and limits: [`docs/research/FINDINGS.md`](docs/research/FINDINGS.md)
- Reproducible synthetic boundary experiments: [`research/README.md`](research/README.md)
- Full decision evolution: [`docs/history/LCE_DECISION_EVOLUTION.md`](docs/history/LCE_DECISION_EVOLUTION.md)
- Runtime and product boundaries: [`docs/architecture/LCE_V1_RUNTIME.md`](docs/architecture/LCE_V1_RUNTIME.md), [`docs/architecture/LCE_V1_BOUNDARIES.md`](docs/architecture/LCE_V1_BOUNDARIES.md)
```

- [ ] **Step 8: Review README for architecture-design signal**

A reader should be able to answer all five questions from README alone:

```text
What was the original problem?
What failed?
Why did the architecture pivot?
How were mistakes converted into explicit contracts?
What is the final V1 boundary?
```

If the README mostly reads like a feature list or API description, revise it before committing.

- [ ] **Step 9: Commit the README rewrite**

```bash
git add README.md
git commit -m "docs: expose LCE experiment-driven architecture story"
```

---

### Task 2: Create the Research Overview as the Main Architecture Narrative

**Files:**
- Create: `docs/RESEARCH_OVERVIEW.md`
- Read: `docs/history/LCE_DECISION_EVOLUTION.md`
- Read: `docs/history/LCE_MASTER_TIMELINE.md`
- Read: `docs/research/research-map.md`
- Read: root closure/repair reports

**Interfaces:**
- Consumes: historical experiments, negative results, repair sequence, and current V1 boundaries.
- Produces: the main 5–10 minute explanation of the owner's architecture-design process; README links here for depth.

- [ ] **Step 1: Create the file with a strict narrative skeleton**

Use these section headings exactly or with semantically equivalent wording:

```markdown
# LCE Research Overview

## 1. The problem LCE was trying to solve
## 2. Why retrieval plus prompt reconstruction was not enough
## 3. First failure: raw text was the wrong cognition point
## 4. First major correction: Semantic Blocks before embedding
## 5. Second correction: semantic continuity over time buckets
## 6. Falsifying longitudinal claims: no-future cutoffs
## 7. Moving discovery before interpretation: vector-first, LLM-last
## 8. Rejecting giant regions and exclusive clustering
## 9. Bounded higher-order cognition and authority separation
## 10. Productization exposed a different class of errors
## 11. How the correction loop changed the runtime contracts
## 12. What V1 finally freezes
## 13. What remains unresolved
## 14. Where to inspect the evidence
```

- [ ] **Step 2: Write each major pivot in the same five-part pattern**

For every major transition, use this reasoning shape:

```text
Problem
→ Initial assumption
→ Experiment / adversarial observation
→ Why the assumption failed
→ Architecture consequence
```

This pattern is the primary vehicle for demonstrating architecture-design ability. Avoid chronology that merely says “then we implemented X.”

- [ ] **Step 3: Make the early research pivots concrete**

Cover at minimum:

```text
POINTCLOUD-01 / 01R
Semantic Cloud-02
BLOCK-03
TREND-04
INSPIRATION-05
STRUCTURE-06R
```

For each, include at least one concrete observation when a verified number is available, but never turn exploratory measurements into statistical validation claims.

- [ ] **Step 4: Make negative results first-class**

Explicitly preserve examples including:

```text
giant component / giant region behavior
noise-floor sustained triggers
real trend miss under cutoff evaluation
weak or non-promoted H1/TDA evidence
weak structure-to-structure analogies
multi-membership that invalidated exclusive clustering
```

The prose should explain how each negative result constrained the architecture.

- [ ] **Step 5: Separate research correction from product correctness correction**

Introduce a clear transition:

```text
The early failures changed the representation and discovery architecture.
The V1 closure failures changed the correctness model of the runtime itself.
```

Then explain Z0–R3 around:

```text
selected immutable support
provenance identity vs qualifying cognition-support identity
recap/support inflation
durable effect recovery
package-sensitive legal interpreters
why green suites were insufficient when the oracle was too weak
```

- [ ] **Step 6: Explain the owner's correction methodology explicitly**

Include a section that describes the recurring engineering loop without exaggeration:

```text
1. Form a narrow architectural hypothesis.
2. Construct a bounded experiment or adversarial test.
3. Preserve misses and negative results instead of tuning them away.
4. Ask whether the failure is algorithmic, representational, or authority-related.
5. Change the smallest abstraction that explains the failure.
6. Convert discovered failure modes into explicit invariants/regression tests.
7. Keep derived cognition from becoming its own evidence.
```

This is not a claim of a formal universal methodology; present it as the process visible in this repository.

- [ ] **Step 7: End with a precise frozen/current/open boundary table**

Use four categories:

```markdown
| Category | Meaning in this repository |
| --- | --- |
| Frozen boundary | Architecture/authority rule intentionally fixed in V1 |
| Engineering invariant | Runtime correctness behavior backed by regression/closure tests |
| Exploratory result | Research evidence that influenced design but is not a general scientific claim |
| Open question | Deliberately unresolved capability or evaluation problem |
```

Populate it with real examples from the source documents.

- [ ] **Step 8: Add deep links to evidence**

Every named experiment family and correction sequence should link to the closest existing repository authority rather than only to another summary document.

- [ ] **Step 9: Commit the overview**

```bash
git add docs/RESEARCH_OVERVIEW.md
git commit -m "docs: add LCE research and architecture evolution overview"
```

---

### Task 3: Create the Findings Index Around Claims, Limits, and Consequences

**Files:**
- Create: `docs/research/FINDINGS.md`
- Read: `docs/history/LCE_DECISION_EVOLUTION.md`
- Read: `docs/research/research-map.md`
- Read: experiment READMEs and closure/repair reports

**Interfaces:**
- Consumes: individual supported claims from research/history/product verification.
- Produces: stable claim-oriented reference used by README and research overview.

- [ ] **Step 1: Create the findings schema at the top of the file**

Use this template for every finding:

```markdown
## F01 — <short claim>

**Finding.** <one falsifiable sentence>

**Evidence.** <what was actually observed or tested>

**What it supports.** <bounded inference>

**What it does not support.** <explicit non-claim>

**Architecture consequence.** <what changed or froze>

**Status.** `exploratory` | `engineering invariant` | `frozen boundary` | `open question`

**Primary references.** <direct repository links>
```

- [ ] **Step 2: Add the ten required findings**

Use these IDs and concepts so README links remain stable:

```text
F01 Similarity discovers relatedness, not cognition.
F02 Raw text is evidence, not the corrected cognition point.
F03 Semantic continuity is not equivalent to arbitrary time buckets.
F04 Longitudinal claims require no-future evaluation and negative controls.
F05 Exclusive clustering loses legitimate multi-membership.
F06 Derived structures are observations, not factual authority.
F07 Provenance identity is not qualifying cognition-support identity.
F08 Replay, recap, and repeated consumption must not manufacture support.
F09 Green suites are insufficient when recovery semantics are tested with a weak oracle.
F10 Language interpretation should consume bounded evidence rather than search freely for supporting evidence.
```

- [ ] **Step 3: Attach concrete evidence and explicit limits to each finding**

For example, F01 should not stop at a slogan. It should record the actual point-cloud failure and then explicitly say that the result does not prove similarity is useless; it proves similarity alone is insufficient authority for cognition identity.

Similarly, F09 should record that later adversarial/legal-interpreter probes exposed defects after earlier test suites were green, but should not imply “tests are unreliable” in general. The architecture consequence is stronger oracles and explicit recovery invariants.

- [ ] **Step 4: Add a negative-results index**

At the end, add a compact table:

```markdown
| Negative result / miss | Why it mattered | What changed |
| --- | --- | --- |
| giant component / region | connectivity was too permissive | local/overlapping bounded structures |
| real cutoff miss | longitudinal visibility was not guaranteed | falsification and no-future evaluation |
| weak H1/TDA signal | attractive abstraction lacked enough evidence | not promoted to core authority |
| recap support inflation | state/provenance churn looked like new support | split provenance identity from support identity |
| package-sensitive recovery failure | durable effect existed before completion markers | explicit recovery semantics |
```

- [ ] **Step 5: Cross-check every finding status**

No finding may be labeled `engineering invariant` or `frozen boundary` unless the repository has implementation/contract/test evidence for that status. Otherwise use `exploratory` or `open question`.

- [ ] **Step 6: Commit the findings index**

```bash
git add docs/research/FINDINGS.md
git commit -m "docs: index LCE findings and negative results"
```

---

### Task 4: Repair Research Navigation Without Duplicating the Archive

**Files:**
- Modify: `research/README.md`
- Modify if needed: `docs/research/research-map.md`
- Read: `docs/RESEARCH_OVERVIEW.md`
- Read: `docs/research/FINDINGS.md`

**Interfaces:**
- Consumes: new overview and findings documents.
- Produces: explicit navigation between reproducible synthetic experiments and historical research evidence.

- [ ] **Step 1: Update `research/README.md` opening scope statement**

Preserve the current message that the directory contains small, reproducible, offline synthetic experiments, then add a sentence equivalent to:

```markdown
These experiments are the public reproducibility surface for selected design boundaries; they are not the full historical research sequence that led to LCE V1. For that sequence, start with [`docs/RESEARCH_OVERVIEW.md`](../docs/RESEARCH_OVERVIEW.md) and [`docs/history/LCE_DECISION_EVOLUTION.md`](../docs/history/LCE_DECISION_EVOLUTION.md).
```

- [ ] **Step 2: Add upward links to findings and research map**

Add:

```markdown
- Claim-by-claim findings and limits: [`docs/research/FINDINGS.md`](../docs/research/FINDINGS.md)
- Conceptual research map: [`docs/research/research-map.md`](../docs/research/research-map.md)
```

Do not expand this README into a second research overview.

- [ ] **Step 3: Review `docs/research/research-map.md` for stale status/navigation**

Only edit if necessary. Permitted edits:

```text
add link to RESEARCH_OVERVIEW.md
add link to FINDINGS.md
clarify that the three public experiments are a selected reproducibility surface
correct a stale current-status sentence if repository authority has changed
```

Do not rewrite its conceptual sequence or promote new authority claims.

- [ ] **Step 4: Commit navigation updates**

```bash
git add research/README.md docs/research/research-map.md
git commit -m "docs: connect LCE research evidence and reproducibility paths"
```

If `research-map.md` required no change, omit it from `git add`.

---

### Task 5: Validate Traceability, Scope, Links, and Architecture Signal

**Files:**
- Verify: `README.md`
- Verify: `docs/RESEARCH_OVERVIEW.md`
- Verify: `docs/research/FINDINGS.md`
- Verify: `research/README.md`
- Verify if changed: `docs/research/research-map.md`
- Test: existing `tests/research/`

**Interfaces:**
- Consumes: all documentation changes from Tasks 1–4.
- Produces: reviewed documentation package with no authority drift, broken links, unsupported numeric claims, or hidden negative results.

- [ ] **Step 1: Scan for placeholders and prohibited overclaims**

Run:

```bash
grep -RniE 'TBD|TODO|to be filled|solved cognition|proves cognition|LCE owns Memory|Baseline is truth' \
  README.md docs/RESEARCH_OVERVIEW.md docs/research/FINDINGS.md research/README.md docs/research/research-map.md || true
```

Expected: no placeholders; any semantic hits are reviewed and either removed or clearly negated/contextualized.

- [ ] **Step 2: Check local Markdown links in the changed files**

Run this one-off validation command from repository root:

```bash
python - <<'PY'
from pathlib import Path
import re

files = [
    Path('README.md'),
    Path('docs/RESEARCH_OVERVIEW.md'),
    Path('docs/research/FINDINGS.md'),
    Path('research/README.md'),
    Path('docs/research/research-map.md'),
]
pat = re.compile(r'\[[^\]]+\]\(([^)]+)\)')
missing = []
for md in files:
    if not md.exists():
        continue
    for target in pat.findall(md.read_text(encoding='utf-8')):
        if target.startswith(('http://', 'https://', '#', 'mailto:')):
            continue
        path_part = target.split('#', 1)[0]
        if not path_part:
            continue
        resolved = (md.parent / path_part).resolve()
        if not resolved.exists():
            missing.append((str(md), target))
if missing:
    for item in missing:
        print('MISSING', *item)
    raise SystemExit(1)
print('all local markdown links resolve')
PY
```

Expected: `all local markdown links resolve`.

- [ ] **Step 3: Run the existing research tests**

Run:

```bash
python -m pytest tests/research -q
```

Expected: PASS with no test modifications.

- [ ] **Step 4: Run the normal project test suite if the repository environment supports it**

Run:

```bash
python -m pytest -q
```

Expected: PASS. If environment/dependency setup prevents execution, record the exact environment failure; do not alter runtime code to make a documentation change pass.

- [ ] **Step 5: Perform a source-trace audit of every number in the new public docs**

Run:

```bash
grep -nE '[0-9]+' README.md docs/RESEARCH_OVERVIEW.md docs/research/FINDINGS.md
```

For each historical experiment/test count or measured value, open the cited source and verify the exact value. Ordinary dates, V1 labels, section numbers, and list numbering do not need evidence mapping.

- [ ] **Step 6: Perform an authority-boundary review**

Compare the changed prose against:

```text
docs/architecture/LCE_V1_BOUNDARIES.md
docs/architecture/LCE_V1_RUNTIME.md
docs/history/LCE_DECISION_EVOLUTION.md
```

Confirm all of the following:

```text
Memory remains factual authority.
LCE Baseline is derived longitudinal understanding, not factual Memory.
Read-time path is model-free/non-mutating.
Current-turn Body/reasoning stays outside standalone LCE V1.
Public synthetic experiments are not represented as the complete historical corpus.
```

- [ ] **Step 7: Perform the architecture-design signal review**

Read the README and overview once without looking at code. Score each question pass/fail:

```text
Can I identify the original design problem?
Can I identify at least three failed assumptions?
Can I explain why each major architectural pivot occurred?
Can I see how negative results were retained rather than hidden?
Can I see how runtime bugs became explicit invariants/contracts?
Can I distinguish exploratory research from verified product correctness?
Can I state the final V1 authority boundary?
```

All seven must pass before completion.

- [ ] **Step 8: Inspect the final diff for scope drift**

Run:

```bash
git diff HEAD~4 -- README.md docs/RESEARCH_OVERVIEW.md docs/research/FINDINGS.md research/README.md docs/research/research-map.md

git status --short
```

Expected: only documentation/navigation files are changed by this effort; no `src/`, schema, provider, database, or production test files appear.

- [ ] **Step 9: Commit any final documentation-only corrections**

If validation required edits:

```bash
git add README.md docs/RESEARCH_OVERVIEW.md docs/research/FINDINGS.md research/README.md docs/research/research-map.md
git commit -m "docs: tighten LCE research traceability and boundaries"
```

If validation required no edits, do not create an empty commit.

- [ ] **Step 10: Prepare the implementation handoff summary**

Report:

```text
files created/modified
major research pivots surfaced
negative results surfaced
correction methodology surfaced
validation commands and results
any evidence gaps deliberately left unresolved
final commit range
```

Do not claim completion unless link checks, evidence review, scope review, and available tests have actually been run.
