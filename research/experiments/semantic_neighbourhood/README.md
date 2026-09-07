# Semantic Neighbourhood Candidate Generation

## Research Question

Can deterministic vector similarity identify useful candidate relationships without asserting
that the related items share a belief, cognition, or canonical meaning?

## Hypothesis

Fixed-vector similarity can produce a ranked candidate set, but the result must remain explicitly
named `candidate_relation`.

## Synthetic Setup

The fixture contains five synthetic items and fixed three-dimensional vectors. Two pairs are near
each other and one item is intentionally isolated from the threshold.

## Method

The experiment computes cosine similarity, applies a threshold, keeps the top qualifying neighbour
for each item, de-duplicates pairs, and returns a deterministic result ordered by similarity and ID.

## Expected Result

The two near pairs are returned. The isolated item is not returned as a candidate relation.

## What This Does Not Prove

It does not prove shared cognition, shared belief, semantic truth, a canonical relation, or any
longitudinal claim. It also does not choose an embedding model or a production threshold.

## LCE Design Consequence

Similarity belongs to an external discovery layer. Its output can be inspected or passed forward
as a candidate, but it cannot bypass authorization or become LCE Core state by itself.

## How to Run

From the repository root:

```text
python research/experiments/semantic_neighbourhood/experiment.py
python -m pytest research/experiments/semantic_neighbourhood -q
```
