# Core / Runtime Boundary

The LCE repository now exposes two different composition levels.

```text
external canonical source / adapter
              |
              v
      LceProjectionCore
      |       |       |
 semantic   structure  cognition
 blocks     snapshots  drafts/baselines
              |
              v
       accepted cognition

Standalone convenience:
ReferenceMemoryStore -> LceRuntime -> LceProjectionCore
```

`LceProjectionCore` is the reusable projection pipeline. It does not construct
the bundled `ReferenceMemoryStore` and therefore does not decide where factual
source material lives. Its source/working substrate is injected by the
composition root.

`LceRuntime` is only the standalone research/demo wrapper. When no substrate is
supplied it creates the bundled `ReferenceMemoryStore` and delegates all
cognition work to `LceProjectionCore`.

This split preserves the existing standalone API while removing the concrete
source store from the reusable core. It also establishes the integration
direction required by MR's layered-memory authority:

```text
MR canonical Memory
       |
       | adapter / stable IDs
       v
LCE projection core
       |
       v
derived LCE artifacts only
```

## Authority

This refactor does not promote LCE artifacts into factual authority. Baselines,
Semantic Blocks, vectors, snapshots and drafts remain derived cognition or
rebuildable projection state.

The current `ReferenceMemorySubstratePort` still groups source-validity and
derived Semantic Block working operations for standalone V1 compatibility.
That compatibility protocol is not a requirement that an embedded deployment
copy canonical MR Memory into LCE. Splitting Path-B source reads from
LCE-owned derived writes is the next integration seam; this refactor makes that
change local to the injected substrate boundary rather than the runtime itself.
