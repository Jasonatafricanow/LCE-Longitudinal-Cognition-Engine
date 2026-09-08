# LCE Research Map

LCE's public research surface is intentionally small, offline, and synthetic.
The experiments are not a hidden production pipeline and they do not promote
candidate structure into canonical cognition. Their purpose is to make the
boundaries behind LCE design decisions falsifiable and reviewable.

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
LCE Core authority boundary
```

Each arrow is a research question, not an automatic authority escalation.

## 1. Semantic Neighbourhood

**Question:** Can similarity identify useful candidate relations without being
mistaken for meaning or truth?

**Evidence:** The [semantic neighbourhood experiment](../../research/experiments/semantic_neighbourhood/README.md)
uses fixed synthetic vectors and emits `candidate_relation` records. Its
contract deliberately stops before semantic or canonical claims.

**Architecture consequence:** Vector similarity belongs to an external
discovery substrate. It may propose IDs or relations, but LCE Core must
receive authorized memory references rather than silently owning a vector
index.

**Unresolved question:** Which additional evidence and review rules are needed
before a candidate relation can support a longitudinal interpretation?

## 2. Region Formation

**Question:** Can overlapping neighbourhoods form an inspectable candidate
region while preserving isolated or weakly supported evidence?

**Evidence:** The [region discovery experiment](../../research/experiments/region_discovery/README.md)
uses deterministic neighbourhood overlap, a minimum region size, and explicit
isolated/unassigned outputs. It does not force every item into a group.

**Architecture consequence:** Candidate regions should remain inspectable and
retain support information. A region is a useful research object, not a belief
or a canonical baseline by itself.

**Unresolved question:** How should a later semantic process justify a durable
longitudinal structure without erasing negative evidence or weak membership?

## 3. Temporal Falsification

**Question:** Can a longitudinal evaluation prevent hindsight leakage?

**Evidence:** The [temporal cutoff experiment](../../research/experiments/temporal_cutoff/README.md)
restricts visibility to events at or before a cutoff, rejects future IDs, and
uses a shuffled-time negative control.

**Architecture consequence:** No-future visibility is an evaluation prerequisite
whenever a claim depends on temporal structure. A result that sees later events
is not evidence that the structure was discoverable earlier.

**Unresolved question:** Which longitudinal signals remain stable under new
cutoffs, reordered observations, and independent review?

## 4. LCE Core Authority Boundary

**Question:** What should LCE Core own once external research has identified
candidate inputs?

**Evidence:** The [external substrate boundary](external-substrate-vs-lce-core.md),
Core contracts, and SQLite store make the boundary explicit:

```text
raw memory / embeddings / neighbourhoods / regions
  -> external inputs or candidate discovery

authorized memory IDs
  -> LCE Core consolidation
  -> immutable baseline revisions and explicit head pointer
```

Unknown memory references fail closed. Equivalent content does not create
meaningless revision increments. Storage is rooted by the caller so separate
runtimes remain isolated.

**Architecture consequence:** LCE Core is a deterministic consolidation and
lineage boundary, not a general vector database, raw-memory owner, or current
turn reasoning engine.

**Unresolved question:** How should a future longitudinal compiler be evaluated
without collapsing research candidates into current runtime authority?

## Current Status

MR-side binding exists, but production activation remains disabled. Automatic
longitudinal compilation is out of scope for the current Core. The public
experiments therefore remain proposal-and-control surfaces until a later
contract explicitly promotes a capability.

Run the research tests offline with:

```text
python -m pytest tests/research -q
```
