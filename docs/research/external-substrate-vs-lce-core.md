# External Substrate vs LCE Core

## Research Question

Which parts of a longitudinal cognition pipeline belong to external discovery research, and which
parts are currently owned by LCE Core?

## Hypothesis

Raw memory, embeddings, neighbourhood discovery, candidate regions, and model interpretations are
external inputs or proposals. LCE Core should receive authorized evidence references and enforce
deterministic consolidation, provenance, equivalence, and persistence boundaries.

## Method

The public research experiments isolate three discovery controls:

```text
raw memory              external input
embeddings              external representation
neighbourhoods          candidate discovery
regions                 inspectable candidate structure
LLM interpretations     bounded semantic proposal, when present
authorized memory IDs   input accepted by LCE Core
```

The synthetic experiments intentionally contain no model client and no Core integration so that the
boundary remains visible.

## Observed Failure Mode

It is easy to treat a similarity edge, a region, or an interpretation as if it were already a
canonical cognition. That would silently move authority from an external discovery layer into the
Core without an accepted contract.

## Observation

Candidate relations and candidate regions can be useful without becoming canonical state. The
temporal control likewise validates evidence visibility without making a longitudinal claim.

## Design Consequence

Research code should expose proposals and controls explicitly. LCE Core should continue to consume
authorized external memory IDs and apply deterministic consolidation and storage rules.

## Current LCE Boundary

Compiled Cognition is not claimed as implemented here. Full semantic clustering is not part of the
current Core. An LLM interpretation does not become canonical automatically.
