# Pairwise vs Region

## Research Question

When vector similarity produces related-item pairs, what additional evidence is needed before a
stable candidate structure can be inspected?

## Hypothesis

Pairwise similarity is useful for candidate generation, but it is not equivalent to a stable
longitudinal structure. Neighbourhood overlap can make the structural assumptions explicit and
keep isolated evidence visible.

## Method

The synthetic research surface compares two bounded steps:

```text
pairwise candidate relation
→ transparent region candidate
→ separately authorized interpretation
```

The first step uses fixed-vector cosine similarity. The second uses deterministic k-neighbourhood
overlap, minimum region size, and explicit isolated/unassigned outputs.

## Observed Failure Mode

A high-similarity pair can be a local coincidence, and a clustering routine can hide uncertainty by
forcing every item into a group. A region manifest without support information also makes later
review difficult.

## Observation

The public synthetic experiment keeps candidate relation, region membership, overlap support,
unassigned items, and isolated items as separate observable fields.

## Design Consequence

The discovery layer should report inspectable candidates rather than silently promote similarity
into semantic authority.

## Current LCE Boundary

The current LCE Core does not own vectors or neighbourhood discovery. It consumes externally supplied,
authorized memory IDs and performs deterministic consolidation and persistence.
