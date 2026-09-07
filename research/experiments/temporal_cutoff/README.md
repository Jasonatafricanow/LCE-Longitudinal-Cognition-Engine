# Temporal Cutoff / No-Future Control

## Research Question

Can a longitudinal evaluation enforce that a claim at cutoff `T2` only consumes evidence available
at or before `T2`?

## Hypothesis

A fail-closed cutoff filter can prevent later events from entering the visible set, while a
shuffled-time control changes ordering without changing membership or crossing the cutoff.

## Synthetic Setup

The fixture contains four ordered synthetic events: `T1`, `T2`, `T3`, and `T4`. The later two
events carry a distinct synthetic signal so accidental future access is observable.

## Method

The experiment splits events at the requested cutoff, rejects explicitly supplied future IDs,
computes a plain visible baseline, and shuffles only the visible events for the negative control.

## Expected Result

At `T2`, only `E01` and `E02` are visible. The shuffled control changes their order but cannot add
`E03` or `E04`.

## What This Does Not Prove

It does not prove that a trend exists, that a temporal signal is meaningful, or that a model can
interpret a longitudinal pattern. It only verifies the evidence-visibility boundary.

## LCE Design Consequence

Longitudinal evaluation must enforce no-future visibility before any discovery or interpretation
step. A result obtained with future evidence is not a valid longitudinal evaluation.

## How to Run

From the repository root:

```text
python research/experiments/temporal_cutoff/experiment.py
python -m pytest research/experiments/temporal_cutoff -q
```
