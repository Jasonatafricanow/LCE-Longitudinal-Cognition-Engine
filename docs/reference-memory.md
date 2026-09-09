# Reference Memory

Reference Memory is the small standalone substrate shipped with LCE V1. It is
an implementation option, not an LCE requirement.

It provides stable Raw Evidence IDs, immutable source content, UTC occurrence
ordering, provenance, validity/invalidation, supersede links, an audit event
history, canonical Semantic Block storage, and a rebuildable vector projection.
Semantic Block continuation creates a new immutable block state; cutoff-bound
snapshots and accepted Baselines can therefore retain the state they actually
observed. Raw Evidence and derived vectors use separate SQLite tables.
Removing the vector projection does not remove Evidence, Semantic Blocks, or
their historical states.

## Three supported uses

1. Use Reference Memory directly with `ReferenceMemoryStore` for a standalone
   LCE installation.
2. Implement the focused Reference Memory ports and replace the local backend
   with your own Memory implementation. The V1 runner accepts an injected
   substrate; LCE Core consumes explicit ports and does not import MR or a
   concrete MR backend. `lce.testing.InMemoryReferenceMemory` is an independent
   contract example, not a production database.
3. Reuse or adapt the Reference Memory provenance, validity, supersede, and
   anti-pollution minimum in another Memory system while keeping that system's
   own canonical authority.

The third option does not transfer ownership to LCE. An unknown or non-
canonical source is rejected rather than silently admitted. Derived cognition
cannot be written as Raw Evidence.

```python
from lce.reference_memory import ReferenceMemoryStore

memory = ReferenceMemoryStore("./state/memory")
# add RawEvidence, compile Semantic Blocks, and rebuild vectors as needed
```

MR integration is deliberately outside this package and outside LCE V1
product closure.

## Deterministic fallback and supplied vectors

`RuleBasedSemanticProvider` is a deterministic standalone fallback. It relies
on caller-supplied semantic hints/metadata such as `topic`, `topics`, recap
flags, and explicit new-information fields; it does not claim to infer all
semantic boundaries from ordinary prose. A real semantic/model provider should
implement the existing replaceable semantic provider port.

The reference embedding fallback hashes Semantic Block text. A fixture may
also supply a `vector` in Raw Evidence provenance; that vector is copied into
the Semantic Block state only as deterministic topology-fixture metadata. It
is not evidence of semantic/model accuracy. Each immutable block state keeps
the vector metadata it was compiled with; later continuation does not rewrite
an earlier state's vector. Production semantic/model embeddings should use the
existing vector/embedder seam and provide their own lifecycle and versioning.

LCE itself does not require Reference Memory. A backend may either use this
implementation directly, implement the focused Memory Port, or reuse only its
provenance, validity, supersede, and anti-pollution minimum in its own canonical
Memory system.
