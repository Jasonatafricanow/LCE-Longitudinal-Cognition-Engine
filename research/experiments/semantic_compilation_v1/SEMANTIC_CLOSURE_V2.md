# Semantic Closure experiment — v2

This experiment corrects the first V1 branch experiment. The earlier candidate accidentally treated one parsed proposition as one SemanticBlock. That contradicts the original LCE motivation.

The intended layers are:

```text
Raw Evidence
    -> semantic parsing
    -> Semantic Points / first-pass semantic artifacts
    -> context-complete compilation
    -> SemanticBlock
    -> embedding / Point Cloud
```

A Semantic Point is not a cognition point. It is an ingredient extracted from the original meaning. A SemanticBlock is the smallest downstream-analysis unit that can stand on its own without changing the source meaning through lost condition, negation, modality, reference, temporal state, correction, or limitation context.

This matches the September research record:

```text
91 raw units
-> 667 first-pass semantic artifacts
-> 129 Semantic Blocks
-> embedding
```

The 667 artifacts were never supposed to become 667 cognition points.

## Three strategies compared

The harness compares the same frozen semantic parse under three block policies.

### 1. Semantic-point singletons

Every resolved Semantic Point becomes its own block.

This is the over-atomized failure mode. It tends to cut:

- plan from completion/current state;
- condition from its consequence;
- evidence limitation from the claim it limits.

### 2. Raw-evidence buckets

All points originating in one raw turn/chunk stay together.

This approximates the old “divide the wheat field into regions” failure mode. It avoids some local truncation, but it merges independent meanings such as:

- transient test result + durable instruction;
- unrelated facts that happen to share a turn.

It also cannot, by itself, carry cross-turn correction/reference context.

### 3. Semantic closure

The compiler operates on dependency policy rather than sentence, turn, topic, or point count.

- `cohabit`: splitting the endpoints would change the meaning, so they form one SemanticBlock.
- `context`: the newer point may remain a separate longitudinal cognition point, but the prior point must be carried as explicit context/provenance in its compiled block.
- unresolved/deferred points do not enter the cognition space.
- explicitly independent points remain separate even if they occur in the same raw message.

The current v2 harness covers:

- transient result + durable instruction;
- planned -> completed -> current state;
- uncertainty;
- conditional scope;
- cross-turn correction;
- unresolved reference;
- resolved pronoun/reference;
- longitudinal state update;
- nested stance/limitation;
- question vs fact.

## What this validates

The executable result can support only this claim:

> Given a correct first-pass semantic parse, a dependency-driven semantic-closure compiler can preserve minimum context completeness while avoiding both atomic fragmentation and raw-turn overmerging on the frozen cases.

It does **not** yet prove that Body/AGY can generate the first-pass semantic points/dependencies reliably. That is the next experiment.

The prior V1 files are intentionally kept on the research branch as negative-history evidence showing why proposition == SemanticBlock was rejected.
