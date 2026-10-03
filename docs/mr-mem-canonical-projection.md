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
