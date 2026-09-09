# LCE Research Map

LCE's public experiment surface is intentionally small, offline, and synthetic.
The three experiments linked below are **selected reproducibility surfaces**, not
the complete historical research sequence and not a hidden production
pipeline. Their purpose is to make several boundaries behind LCE design
decisions falsifiable and reviewable.

For the full architecture-evolution narrative, start with
[`docs/RESEARCH_OVERVIEW.md`](../RESEARCH_OVERVIEW.md). For claim-by-claim
evidence and negative results, see [`FINDINGS.md`](FINDINGS.md).

## From Similarity to Longitudinal Structure

```text
semantic similarity
        |
        v
candidate neighbourhood
        |
        v
region formation
        |
        v
temporal falsification
        |
        v
longitudinal structure
        |
        v
bounded interpretation / authority boundary
```

Each arrow is a research question, not an automatic authority escalation.

## 1. Semantic Neighbourhood

**Question:** Can similarity identify useful candidate relations without being
mistaken for meaning or truth?

**Evidence:** The [semantic neighbourhood experiment](../../research/experiments/semantic_neighbourhood/README.md)
uses fixed synthetic vectors and emits `candidate_relation` records. Its
contract deliberately stops before semantic or canonical claims.

**Architecture consequence:** Similarity is a discovery signal, not semantic or
factual authority. In standalone V1, vectors are rebuildable derived artifacts
over authorized Semantic Blocks; they cannot write themselves back as Raw
Evidence or accepted Understanding.

**Unresolved question:** Which discovery signals and thresholds remain useful
across different corpora without producing giant/noisy candidate regions?

## 2. Region Formation

**Question:** Can overlapping neighbourhoods form an inspectable candidate
region while preserving isolated or weakly supported evidence?

**Evidence:** The [region discovery experiment](../../research/experiments/region_discovery/README.md)
uses deterministic neighbourhood overlap, a minimum region size, and explicit
isolated/unassigned outputs. It does not force every item into a group.

**Architecture consequence:** Candidate regions should remain inspectable and
retain negative evidence. A region is a derived research object, not a belief,
factual Memory item, or accepted Baseline by itself. The later historical
research moved further toward overlapping local, multi-scale observations
rather than one exclusive cluster ontology.

**Unresolved question:** Which local structural observations provide useful
higher-order candidates without collapsing dense semantic space into a giant
region or noise floor?

## 3. Temporal Falsification

**Question:** Can a longitudinal evaluation prevent hindsight leakage?

**Evidence:** The [temporal cutoff experiment](../../research/experiments/temporal_cutoff/README.md)
restricts visibility to events at or before a cutoff, rejects future IDs, and
uses a shuffled-time negative control.

**Architecture consequence:** No-future visibility is an evaluation prerequisite
whenever a claim depends on temporal structure. V1 structure snapshots are
cutoff-bound so future block states cannot leak into an earlier snapshot.

**Unresolved question:** Which longitudinal signals remain stable under new
cutoffs, reordered observations, independent review, and different corpora?

## 4. Authority Boundary

The authority boundary evolved between the minimal Core V0 and standalone V1.
That evolution is intentional and should not be collapsed into one historical
claim.

**Core V0:** accepted caller-selected Memory IDs through external ports and
owned immutable Baseline revisions / HEAD. It did not own the later standalone
compiler, Reference Memory, or local vector/structure pipeline.

**Standalone V1:** adds a minimal replaceable Reference Memory substrate,
semantic-stream compilation, rebuildable vectors and cutoff-bounded structures,
bounded higher-order candidates, durable cognition Worktrees, conservative
promotion, and deterministic Understanding reads.

The V1 authority direction is:

```text
canonical Raw Evidence / source validity
        |
        v
Semantic Blocks
        |
        v
derived vectors / structures / candidates
        |
        v
bounded interpretation
        |
        v
OPEN cognition Worktree
        |
        v
conservative accepted Baseline revision
```

Derived cognition never writes itself back as canonical Raw Evidence. An
accepted Baseline is durable LCE understanding, not factual Memory or eternal
objective truth.

See [`LCE_V1_BOUNDARIES.md`](../architecture/LCE_V1_BOUNDARIES.md) and
[`LCE_V1_RUNTIME.md`](../architecture/LCE_V1_RUNTIME.md).

## Current Status

Standalone LCE V1 is frozen as a bounded product pipeline. The release record
reports 139 passing tests, closure/recovery gates, clean mypy/Ruff, and an
exact-HEAD install/import/smoke verification. Those are engineering release
gates, not scientific-validation claims.

MR-side binding is optional and one-way; production invocation is not part of
standalone V1 closure. Current-turn MR/Body reasoning, Persona, Intent,
ActionPolicy, recursive cognition, embedding-quality optimization, threshold
tuning, and higher-order precision remain outside or beyond the standalone V1
boundary.

The complete experiment-driven path and the distinction between exploratory
research, engineering invariants, frozen boundaries, and open questions are
covered in [`docs/RESEARCH_OVERVIEW.md`](../RESEARCH_OVERVIEW.md) and
[`FINDINGS.md`](FINDINGS.md).

Run the public research tests offline with:

```text
python -m pytest tests/research -q
```
