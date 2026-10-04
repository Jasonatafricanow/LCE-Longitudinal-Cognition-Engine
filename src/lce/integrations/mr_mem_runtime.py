"""Explicit committed-cognition runtime and existing MR-Mem queue worker bridge."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from mr_mem.contracts import Scope
from mr_mem.memory.semantic_projection import (
    CanonicalSemanticBlockReader,
    CanonicalSemanticBlockView,
)

from lce.core.projection import (
    CanonicalProjectionReceipt,
    LceProjectionCore,
    ProcessResult,
)
from lce.integrations.mr_mem import PROJECTION_TARGET, map_canonical_semantic_block
from lce.integrations.mr_mem_state import MrMemDerivedSubstrate
from lce.reference_memory.contracts import ReferenceMemorySubstratePort


@dataclass(frozen=True, slots=True)
class CanonicalProjectionResult:
    receipt: CanonicalProjectionReceipt
    downstream: ProcessResult | None
    historical_validity_unknown: bool = False


class MrMemProjectionRuntime(LceProjectionCore):
    def __init__(
        self, root: Path | str, *, scope: Scope, lineage_id: str = "mr-mem", **kwargs: object,
    ) -> None:
        self.scope = scope
        self.projected = MrMemDerivedSubstrate(Path(root) / "canonical-projection")
        try:
            self.projected.initialize_annotations(scope, lineage_id)
        except BaseException:
            self.projected.close()
            raise
        # Existing algorithms retain the standalone protocol annotation. The
        # integrated substrate supplies only downstream capabilities; explicit
        # mode disables construction of the legacy compiler and all Raw inputs.
        super().__init__(root, memory=cast(ReferenceMemorySubstratePort, self.projected),
                         lineage_id=lineage_id, semantic_mode="canonical", close_memory=True,
                         **kwargs)  # type: ignore[arg-type]

    def project_canonical_semantic_block(
        self, view: CanonicalSemanticBlockView,
    ) -> CanonicalProjectionResult:
        if not isinstance(view, CanonicalSemanticBlockView):
            raise TypeError("CanonicalSemanticBlockView required; Point is not an LCE input")
        if view.scope != self.scope:
            raise ValueError("canonical projection scope mismatch")
        projection = map_canonical_semantic_block(view, lineage_id=self.lineage_id)
        input_id, replayed = self.projected.put_canonical_projection(projection)
        receipt = CanonicalProjectionReceipt(input_id, (view.memory_id,), replayed)
        if not projection.current_valid and projection.transition_known_at is None:
            # Current validity is known, but a dated historical mutation cannot
            # be reconstructed. Update only current derived vectors and omit
            # timestamp-dependent algorithms without changing historical state.
            self.projected.rebuild_vector_index(self._block_embedder,
                                               index_version=self._block_embedding_version)
            return CanonicalProjectionResult(receipt, None, True)
        cutoff = max((view.known_at, *(r.known_at for r in (
            *view.incoming_relations, *view.outgoing_relations,
        ))))
        downstream = self._process_post_compiled(
            input_id, view.occurred_at, cutoff, receipt,
        )
        return CanonicalProjectionResult(receipt, downstream)


class MrMemProjectionWriter:
    """ProjectionWorker bridge: resolve only committed public Block views."""

    def __init__(self, reader: CanonicalSemanticBlockReader, runtime: MrMemProjectionRuntime) -> None:
        self.reader, self.runtime = reader, runtime

    def upsert(self, memory: object, *, intent: object) -> str:
        target = getattr(intent, "target", None)
        memory_id = getattr(intent, "memory_id", None)
        if target != PROJECTION_TARGET or not isinstance(memory_id, str):
            raise ValueError("explicit lce-semantic-v1 intent required")
        view = self.reader.get_semantic_block_view(memory_id)
        if view is None:
            raise ValueError("canonical native SemanticBlock view unavailable")
        self.runtime.project_canonical_semantic_block(view)
        return memory_id
