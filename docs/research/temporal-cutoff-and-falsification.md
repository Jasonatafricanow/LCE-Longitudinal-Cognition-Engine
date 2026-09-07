# Temporal Cutoff and Falsification

## Research Question

How can a longitudinal evaluation avoid mistaking hindsight for predictive or emergent structure?

## Hypothesis

Every evaluation cutoff must restrict its visible evidence to events at or before that cutoff. A
plain baseline and a shuffled-time negative control make leakage and temporal dependence testable.

## Method

The synthetic experiment evaluates `T2` over an ordered `T1`–`T4` sequence. It reports visible and
future IDs, rejects an explicitly supplied future ID, and shuffles only the visible events with a
fixed seed.

## Observed Failure Mode

If `T3` or `T4` enters a `T2` evaluation, a later pattern can appear to have been discoverable
earlier. This is hindsight leakage, not evidence of longitudinal discovery.

## Observation

The cutoff result remains fail-closed and deterministic. The shuffled-time control changes temporal
ordering while preserving the visible membership set and excluding future events.

## Design Consequence

No-future visibility is an evaluation prerequisite, not an optional reporting detail. Negative
controls should be part of the research design whenever temporal claims are made.

## Current LCE Boundary

This control concerns an external research/discovery layer. It does not implement trend discovery,
semantic interpretation, or canonical cognition inside LCE Core.
