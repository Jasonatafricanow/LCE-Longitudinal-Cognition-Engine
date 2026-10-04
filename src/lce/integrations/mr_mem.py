"""MR-Mem committed Block mapping. No semantic inference or native Raw access."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from mr_mem.memory.contracts import MemoryLifecycle
from mr_mem.memory.semantic_projection import (
    CanonicalSemanticBlockView,
    CanonicalSemanticRelationView,
)

from lce.reference_memory.contracts import SemanticBlock

PROJECTION_TARGET = "lce-semantic-v1"


class LifecycleTimeUnknown(RuntimeError):
    """Exact historical validity requires an unavailable canonical transition time."""


@dataclass(frozen=True, slots=True)
class CanonicalBlockProjection:
    block: SemanticBlock
    lifecycle: MemoryLifecycle
    transition_known_at: datetime | None
    outgoing_relations: tuple[CanonicalSemanticRelationView, ...]
    incoming_relations: tuple[CanonicalSemanticRelationView, ...]

    @property
    def current_valid(self) -> bool:
        return self.lifecycle is MemoryLifecycle.ACTIVE

    def valid_at(self, cutoff: datetime) -> bool:
        known_at = self.block.derived_known_at
        assert known_at is not None
        if cutoff < known_at:
            return False
        if self.current_valid:
            return True
        if self.transition_known_at is None:
            raise LifecycleTimeUnknown(self.block.block_id)
        return cutoff < self.transition_known_at


def map_canonical_semantic_block(
    view: CanonicalSemanticBlockView, *, lineage_id: str,
) -> CanonicalBlockProjection:
    """Preserve identity and both clocks; source keys are provenance references.

    SemanticBlock's legacy raw_evidence_ids field carries native support IDs
    only. No RawEvidence is created. Mutable annotations are separate from the
    immutable derived Block state, so lifecycle updates cannot clone cognition.
    """
    if not isinstance(view, CanonicalSemanticBlockView):
        raise TypeError("CanonicalSemanticBlockView required")
    if not view.source_refs:
        raise ValueError("canonical native provenance required")
    return CanonicalBlockProjection(
        block=SemanticBlock(
            block_id=view.memory_id,
            content=view.content,
            raw_evidence_ids=tuple(ref.source_key for ref in view.source_refs),
            occurred_start=view.occurred_at,
            occurred_end=view.occurred_at,
            compiler_version=view.compiler_version,
            lineage_id=lineage_id,
            derived_known_at=view.known_at,
            metadata={
                "projection_target": PROJECTION_TARGET,
                "scope": asdict(view.scope),
                "schema_version": view.schema_version,
                "source_interaction_id": view.source_interaction_id,
                "context_memory_ids": view.context_memory_ids,
                "semantic_units": tuple(unit.wire() for unit in view.units),
                "unit_source_indices": view.unit_source_indices,
                "source_refs": tuple({
                    **asdict(ref), "occurred_at": ref.occurred_at.isoformat(),
                } for ref in view.source_refs),
            },
        ),
        lifecycle=view.lifecycle,
        transition_known_at=view.transition_known_at,
        outgoing_relations=view.outgoing_relations,
        incoming_relations=view.incoming_relations,
    )


class MRMemSemanticBlockAdapter:
    """Explicit post-compilation adapter mapping MR-Mem's CanonicalSemanticBlockView to LCE."""

    def __init__(self, *, lineage_id: str = "mr-mem") -> None:
        self.lineage_id = lineage_id

    def adapt(
        self,
        view: CanonicalSemanticBlockView,
        *,
        lineage_id: str | None = None,
    ) -> CanonicalBlockProjection:
        return map_canonical_semantic_block(
            view,
            lineage_id=lineage_id or self.lineage_id,
        )

    def __call__(
        self,
        view: CanonicalSemanticBlockView,
        *,
        lineage_id: str | None = None,
    ) -> CanonicalBlockProjection:
        return self.adapt(view, lineage_id=lineage_id)

