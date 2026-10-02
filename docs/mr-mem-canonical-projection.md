# MR-Mem canonical cognition integration

The explicit mapping boundary is `lce.integrations.mr_mem`. It accepts only
MR-Mem's public `CanonicalSemanticBlockView`. MR-Mem owns cognition identity,
content, source metadata, occurrence time, knowledge time, relations and
lifecycle. LCE owns derived vectors and longitudinal structure. Install an
MR-Mem build containing the public projection contract before using this optional
integration; standalone LCE retains no MR-Mem runtime dependency.

The existing `SemanticBlock.raw_evidence_ids` field is a legacy storage name for
support references. In this integration it contains native SourceRef identity
keys only. There are no RawEvidence objects, transcripts or fake factual rows.
Lifecycle and relation annotations are separate from immutable Block states.
Unknown transition times must fail closed in exact historical validity queries.

This module does not activate a production path or change semantic, embedding,
trajectory, discovery or promotion algorithms.

`MrMemProjectionRuntime(root, scope=..., lineage_id=...)` binds one derived
lineage to an explicit MR-Mem scope. Call `project_canonical_semantic_block(view)`;
Raw entrypoints raise in this mode and the legacy compiler is not constructed.
The existing runtime's `process_raw_evidence` and compatibility `process` retain
standalone compilation. Both paths share the same post-compilation downstream.

Downstream previously relied on compiler side effects: persisted Block/state
identity, native support identity/validity, both clocks, vectors, and durable
pipeline progress. The canonical substrate now supplies those capabilities
explicitly. Support reads use metadata only; per-Block lifecycle gates prevent
shared source references from merging cognition or coupling lifecycle. Algorithm
predicates now read these capabilities; scoring, traversal, mutual-kNN, Line
assembly, Frontier policy and embedding parameters are unchanged.

`MrMemProjectionWriter(reader, runtime)` composes with MR-Mem's existing
`ProjectionWorker(queue, writer, target="lce-semantic-v1")`. Register that target
on the existing queue before draining. No second queue exists. The writer reads
only the public committed view and never parses producer input. Multiple scopes
require the caller to route views to separately bound runtimes.

Lifecycle/relations are rebuildable annotations, separate from immutable
projected cognition. Unknown non-active transition time updates current vectors
and validity, then skips timestamp-dependent downstream work. Historical Block
and Line rows remain. Exact historical validity raises `LifecycleTimeUnknown`;
algorithm validity predicates conservatively omit unknown support.
