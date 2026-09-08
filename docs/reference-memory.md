# Reference Memory

Reference Memory is the small standalone substrate shipped with LCE V1. It is
an implementation option, not an LCE requirement.

It provides stable Raw Evidence IDs, immutable source content, UTC occurrence
ordering, provenance, validity/invalidation, supersede links, an audit event
history, canonical Semantic Block storage, and a rebuildable vector projection.
Raw Evidence and derived vectors use separate SQLite tables. Removing the
vector projection does not remove Evidence or Semantic Blocks.

## Three supported uses

1. Use Reference Memory directly with `ReferenceMemoryStore` for a standalone
   LCE installation.
2. Implement the Memory Port and replace the local backend with your own
   Memory implementation. LCE Core consumes explicit ports and does not import
   MR or a concrete MR backend.
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
