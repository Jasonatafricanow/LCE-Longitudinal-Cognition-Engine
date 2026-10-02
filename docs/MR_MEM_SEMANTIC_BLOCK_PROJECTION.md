# Integrated MR-Mem SemanticBlock projection

`lce.integrations.mr_mem.open_mr_mem_projection` opens MR-Mem with a read-only
MemoryCore and writes LCE derivations to a separate projection root. It accepts
an explicit MR-Mem Scope. The caller obtains committed Blocks through
`MRMemSemanticBlockAdapter.get_semantic_block(memory_id)` and passes them to
`LceProjectionCore.process_semantic_block` or `run_semantic_block_batch`.

`CanonicalSemanticBlockView` maps existing MR-Mem fields: memory ID, unchanged
content, source occurred range, canonical known_at, native SourceRefs, context
Memory IDs, outbound relations, compiler version and current lifecycle. Only
records with matching canonical SemanticBlock metadata are eligible. Legacy
factual records and foreign scopes are rejected. LCE assigns no cognition ID:
the projection Block ID remains the canonical Memory ID.

Integrated composition creates no SemanticCompiler or SemanticDecisionProvider.
It validates the exact mapped Block against the read-only canonical adapter,
stores a rebuildable projection cache and feeds the existing embedding,
snapshot, trajectory, line and baseline stages. It never splits, merges or
reinterprets a committed Block. Existing trajectory/discovery algorithms and
embedding defaults are unchanged.

The substrate's existing `RawEvidence` validity/ordering surface carries a
read-only canonical Block token keyed by Memory ID. It is never historical Raw
input, written to a source store or passed to a semantic compiler. SourceRefs
remain on the Block projection metadata. Current lifecycle is read afresh from
MR-Mem; missing historical lifecycle times are not invented.

For a successful commit:

```python
projection = open_mr_mem_projection(canonical_db, derived_root, scope=scope)
try:
    source = projection.memory.source
    block = source.get_semantic_block(memory_id)
    result = projection.process_semantic_block(block)
finally:
    projection.close()
```

Projection restart reuses canonical identity and pipeline progress. It never
requests a semantic proposal again. No online flag or production DB cutover is
performed by this tool.

## Legacy standalone boundary

`lce.semantic.compiler`, `contracts` and `providers` remain available for the
standalone `LceRuntime` and legacy Raw source callers. They are explicitly
LEGACY / STANDALONE. Loading the integrated adapter does not load those modules;
the old compiler is imported only when standalone composition is constructed.
Integrated composition rejects Raw ingestion and configured semantic providers.
No production canonical source passes through two semantic compilers.
