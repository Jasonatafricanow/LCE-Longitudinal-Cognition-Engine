# Trajectory Candidate Convergence Experiment — 2026-09-28

Status: research-only branch experiment. No production runtime wiring.

Branch: feature/trajectory-runtime-v1-convergence-experiment-20260928
Base: feature/trajectory-runtime-v1-20260927 @ c349fce

## Question

Can ambiguous Line interpretations converge from repeated independent structural support without introducing a central semantic scorer or a weighted confidence number?

The production Path-B runtime already leaves multi-Line identity ambiguity unresolved. This experiment tests a possible next layer: preserve competing candidates, accumulate auditable support, and resolve only when one candidate structurally dominates the others.

## Authority boundary

Raw Evidence remains the only independent evidence authority. Derived projections must reuse the same support_group_id when they close over the same canonical support. Repetition of one derived interpretation therefore cannot create extra votes.

The experiment does not treat a candidate as factual merely because it wins. The result is still derived cognition.

## Profile dimensions

Each candidate is represented by an explicit vector rather than one confidence scalar:

- independent_support: unique canonical support groups;
- reciprocal_support: unique support groups participating in reciprocal local relations;
- context_support: distinct caller-supplied contexts carrying support;
- derivation_stability: distinct algorithm/parameter variants under which support survives;
- contradiction_pressure: unique canonical groups that contradict the candidate.

No weighted sum is computed.

## Decision rule

1. Apply only a small evidentiary admission floor.
2. Compare eligible candidates by Pareto dominance.
3. A candidate dominates another only if it is no worse on every positive dimension, no worse on contradiction pressure, and strictly better somewhere.
4. Converge only when exactly one eligible candidate is undominated.
5. Otherwise return UNRESOLVED.

This intentionally refuses to invent an exchange rate such as “three extra support points cancel one contradiction”. Cross-dimension tradeoffs remain ambiguous until new evidence changes the structure.

## Falsifiable expectations

The experiment should fail if any of these occur:

- repeating derived views of one Raw source increases independent support;
- two equally supported Lines are arbitrarily tie-broken;
- a weighted tradeoff is hidden inside the decision rule;
- later independent evidence cannot resolve an earlier ambiguity;
- parameter perturbation creates extra evidence authority rather than only a stability signal.

## Why this is separate from production

The current runtime has deliberately unfrozen policies for Line ambiguity and branch-to-independent-Line transition. This experiment should first be attacked with synthetic counterexamples and held-out real trajectories. Only then should a production integration be considered.
