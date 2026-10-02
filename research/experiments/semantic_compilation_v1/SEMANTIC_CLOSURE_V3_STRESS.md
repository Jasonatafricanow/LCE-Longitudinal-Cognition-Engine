# Semantic Closure V3 — mechanical stress/falsification

V2 showed the intended partition on twelve hand-labelled semantic cases. That is not enough: the labels themselves encode substantial semantic judgment.

V3 therefore does **not** add more prose examples. It attacks the closure mechanism with topology-level invariants over 1,000 deterministic generated dependency graphs.

The tested invariants are:

1. **Permutation invariance** — point input order cannot change the SemanticBlock partition or carried context.
2. **Dependency idempotence** — duplicate dependency edges cannot create new cognition.
3. **Independent-addition locality** — adding an unrelated semantic point creates only its own block and cannot perturb existing blocks.
4. **Cohabit transitivity** — if A cannot be separated from B and B cannot be separated from C, the compiler must keep the whole closure together.
5. **Context does not merge** — a historical/reference dependency may enrich the new block's provenance without collapsing two longitudinal cognition points into one.
6. **Deferred exclusion** — unresolved points never enter cognition/vector output.

This is deliberately a mechanism falsification step, not semantic-quality evidence.

## Important correction to V2 rendering

V2 concatenated context text into a synthetic `canonical_meaning` purely so the run could make context visible. That is **not** a production recommendation.

For production, these must be separate:

```text
SemanticBlock.analysis_text
    = one context-complete meaning intended for embedding / downstream analysis

SemanticBlock.context_refs
    = evidence/semantic support needed to justify or reconstruct that meaning
```

A superseded historical instruction should therefore remain in provenance/context without necessarily being re-injected verbatim into the embedding text. Otherwise an old state such as `top-k=100` can receive fresh vector weight even though the actual current meaning is “100 was revoked; use 20/30/50/70”.

The remaining high-value unknown is upstream:

> Can Body/AGY reliably infer Semantic Points plus `cohabit/context/defer` dependencies from raw conversation?

Neither V2 nor V3 claims that result.
