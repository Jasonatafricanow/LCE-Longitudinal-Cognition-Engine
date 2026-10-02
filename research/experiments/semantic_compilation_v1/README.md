# Semantic Compilation V1 research experiment

Status: research-only branch experiment. No production LCE, MR, MR-Mem, Thread, Line, Baseline, threshold, or authority code is changed.

## Why this experiment exists

The September research record already established:

```text
raw units -> first-pass semantic artifacts -> Semantic Block -> embedding
```

SEMANTIC-CLOUD-02 recorded 91 raw units -> 667 first-pass semantic artifacts -> 129 Semantic Blocks. BLOCK-03 later improved semantic-stream boundaries, but the production-shaped compiler that survived into LCE V1 primarily owns ordering, split/continue/recap and restart safety. Its default reference provider uses input `topic` / `semantic_content` hints or the raw content itself; it is not a general semantic parser.

This experiment isolates the missing question:

> Can one source-grounded, proposition-centric compilation contract represent the semantic information that downstream MR-Mem / Thread / LCE need, without forcing an entity graph or a closed ontology?

## External routes re-checked

The experiment is informed by, but does not copy, these routes:

1. **AMR / meaning-representation research** — parse text into explicit predicate/argument meaning graphs. Useful evidence that a semantic representation should be downstream-consumable rather than just a chunk boundary.
2. **Semantic Role Labeling / PropBank / FrameNet** — represent eventualities and participants. Useful for proposition decomposition and role grounding, but too ontology-heavy to become MR's canonical meaning vocabulary.
3. **OpenIE** — domain-open proposition/triple extraction from unstructured text. Useful for open predicates and atomicity; insufficient alone for modality, correction, discourse state and source-relative uncertainty.
4. **Microsoft GraphRAG** — TextUnit -> LLM entity/relationship extraction, with optional claim extraction and later graph/community processing. Important ordering lesson: pay semantic extraction cost before structural analysis; its entity/graph ontology is not adopted as MR's SemanticBlock ontology.
5. **Zep / Graphiti** — raw episodes stay available while LLM extraction creates temporal facts/entities/relations with provenance and changing validity. Strong match for keeping Raw Evidence separate from compiled semantics and for bitemporal provenance.
6. **LangMem / Mem0** — LLM extraction can produce multiple semantic memories/facts from conversation and then update persistent memory. Useful extraction evidence, but MR should not let extraction directly own memory mutation.
7. **HippoRAG / HippoRAG 2** — primarily a downstream memory organization/retrieval route; it reinforces keeping structured semantic units separate from retrieval geometry, but is not used as the compiler schema.
8. **Stanford Generative Agents / CoALA** — useful cognitive/memory architecture comparisons; they do not solve this exact semantic-compilation contract and therefore are negative controls rather than schema templates.

References:
- https://aclanthology.org/2024.naacl-long.159/
- https://aclanthology.org/2024.findings-emnlp.560/
- https://microsoft.github.io/graphrag/index/default_dataflow/
- https://help.getzep.com/how-graph-creation-works
- https://langchain-ai.github.io/langmem/guides/extract_semantic_memories/
- https://docs.mem0.ai/open-source/features/graph-memory
- https://arxiv.org/abs/2502.14802
- https://arxiv.org/abs/2304.03442
- https://arxiv.org/abs/2309.02427

## Candidate contract tested

This is deliberately smaller than a universal semantic graph.

Each candidate Semantic Block carries:

```text
local_id
source_refs[]
canonical_meaning
speech_act
polarity
epistemic_status
temporal { kind, expression }
unresolved_refs[]
confidence
```

Relations are separate candidates:

```text
from
to
relation
source_refs[]
confidence
```

The contract deliberately does **not** decide Memory KEEP/DROP, Thread identity, LCE Line identity, Baseline acceptance, affect deltas, or truth authority.

## Adversarial cases

The frozen public/synthetic corpus covers:

- simple assertion;
- one message containing transient result + durable directive;
- plan -> completed -> ongoing state in one utterance;
- uncertainty;
- conditional architecture invariant;
- cross-turn correction/supersession;
- unresolved reference without enough context;
- reference resolution with bounded context;
- state change over time;
- nested stance / “does not prove X, only Y”;
- question vs factual assertion;
- coding result mixed with a durable testing rule.

The semantic candidate outputs in `cases.json` were authored as host semantic proposals for this experiment. They are not presented as production AGY output.

## What the executable comparison measures

`run.py` checks the candidate representation for:

- atomic decomposition count;
- source grounding;
- typed logical operators;
- speech-act preservation;
- epistemic/modality preservation;
- temporal preservation;
- explicit unresolved-reference discipline;
- required semantic relations;
- relation provenance.

It then feeds the same raw cases through the current LCE `SemanticCompiler` with the built-in `RuleBasedSemanticProvider` and records what the current production-shaped contract can express without pre-supplied semantic hints.

The comparison is intentionally about the missing compiler **contract**, not about downstream embedding quality.

## Non-claims

A passing run does not prove:

- production Body/AGY parsing quality;
- a specific LLM's accuracy;
- real BGE/embedding quality;
- Point Cloud / Path B / Line quality;
- memory retention policy quality.

Those are later experiments. This branch must remain research-only until the semantic contract itself is reviewed.
