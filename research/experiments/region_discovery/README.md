# Transparent Region Construction

## Research Question

Can overlapping k-neighbourhoods form a deterministic, inspectable candidate region while keeping
weak groups and isolated evidence visible instead of forcing every item into a cluster?

## Hypothesis

A transparent overlap graph can identify a stable synthetic region, preserve a weak group as
unassigned when it does not meet the minimum size, and keep an isolated item isolated.

## Synthetic Setup

The fixture contains a four-item stable group, a two-item weak group, and one isolated item. All
vectors, thresholds, IDs, and ordering rules are synthetic and fixed.

## Method

The experiment builds deterministic top-k neighbourhoods, computes Jaccard overlap between
neighbourhoods, joins pairs meeting the configured overlap threshold, and emits region membership,
support information, isolated IDs, and unassigned IDs.

## Expected Result

One region is formed from the stable group. The weak group remains unassigned because it is smaller
than the configured minimum region size. The isolated item remains in `isolated_ids`.

## What This Does Not Prove

It does not prove that a region is a cognition, a belief, or a canonical longitudinal structure.
It does not validate a clustering method on natural data or select production hyperparameters.

## LCE Design Consequence

Candidate structure should remain inspectable and preserve negative evidence. Any later semantic
interpretation needs a separate, authorized boundary.

## How to Run

From the repository root:

```text
python research/experiments/region_discovery/experiment.py
python -m pytest tests/research/test_region_discovery.py -q
```
