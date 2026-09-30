"""Composition adapter for external canonical Memory plus LCE-owned projections."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime

from lce.reference_memory.contracts import (
    CanonicalEvidenceSourcePort,
    CompilerCheckpoint,
    DerivedProjectionStatePort,
    RawEvidence,
    SemanticBlock,
    VectorProjection,
)


class ExternalSourceMutationError(RuntimeError):
    """LCE cannot mutate an externally owned canonical source."""


class ProjectionSubstrate:
    """Implement the legacy V1 substrate surface without duplicating source rows.

    Raw Evidence reads are delegated to the external canonical source. Semantic
    Blocks, vectors, compiler progress and pipeline progress are written only to
    the LCE-owned projection state store.
    """

    def __init__(
        self,
        source: CanonicalEvidenceSourcePort,
        state: DerivedProjectionStatePort,
        *,
        close_source: bool = False,
        close_state: bool = True,
    ) -> None:
        if type(close_source) is not bool or type(close_state) is not bool:
            raise TypeError("close_source and close_state must be bool")
        self.source = source
        self.state = state
        self._close_source = close_source
        self._close_state = close_state
        self._closed = False
        backfill = getattr(
            self.state,
            "backfill_legacy_derived_known_at",
            None,
        )
        if callable(backfill):
            backfill(self._resolve_legacy_derived_known_at)

    def _resolve_legacy_derived_known_at(
        self,
        raw_evidence_ids: tuple[str, ...],
    ) -> datetime:
        if not raw_evidence_ids:
            raise RuntimeError(
                "legacy semantic state has no Raw dependencies"
            )
        return max(
            self.source.get_evidence(evidence_id).effective_known_at
            for evidence_id in raw_evidence_ids
        )

    @staticmethod
    def _same_source(left: RawEvidence, right: RawEvidence) -> bool:
        return (
            left.evidence_id == right.evidence_id
            and left.content == right.content
            and left.occurred_at == right.occurred_at
            and left.effective_known_at == right.effective_known_at
            and left.effective_ordering_key == right.effective_ordering_key
            and json.dumps(
                dict(left.provenance),
                sort_keys=True,
                separators=(",", ":"),
            )
            == json.dumps(
                dict(right.provenance),
                sort_keys=True,
                separators=(",", ":"),
            )
            and left.state == right.state
            and left.superseded_by == right.superseded_by
        )

    def reset_derived_projection(self) -> None:
        reset = getattr(self.state, "reset_derived_projection", None)
        if not callable(reset):
            raise RuntimeError(
                "projection state store does not support derived reset"
            )
        reset()

    def add_evidence(self, item: RawEvidence) -> RawEvidence:
        """Validate that input already exists in canonical source; never copy it."""
        authoritative = self.source.get_evidence(item.evidence_id)
        if not self._same_source(authoritative, item):
            raise ValueError(
                "projection input differs from externally authoritative source"
            )
        return authoritative

    def get_evidence(self, evidence_id: str) -> RawEvidence:
        return self.source.get_evidence(evidence_id)

    def list_current_valid_evidence(self) -> tuple[RawEvidence, ...]:
        return self.source.list_current_valid_evidence()

    def evidence_valid_at(
        self,
        evidence_id: str,
        cutoff: datetime,
    ) -> bool:
        if cutoff.tzinfo != UTC:
            raise ValueError("cutoff must be UTC")
        item = self.source.get_evidence(evidence_id)
        if item.effective_known_at > cutoff:
            return False
        reader = getattr(self.source, "evidence_valid_at", None)
        if callable(reader):
            return bool(reader(evidence_id, cutoff))
        # External sources that expose only current lifecycle state cannot
        # reconstruct past validity exactly. Fall back conservatively to the
        # current authoritative state rather than fabricating history.
        return item.current_valid

    def invalidate(self, evidence_id: str, *, reason: str) -> None:
        del evidence_id, reason
        raise ExternalSourceMutationError(
            "external canonical source lifecycle must be changed by its owner"
        )

    def supersede(
        self, evidence_id: str, replacement_evidence_id: str
    ) -> None:
        del evidence_id, replacement_evidence_id
        raise ExternalSourceMutationError(
            "external canonical source lifecycle must be changed by its owner"
        )

    @staticmethod
    def _block_is_current(
        source: CanonicalEvidenceSourcePort, block: SemanticBlock
    ) -> bool:
        try:
            return all(
                source.get_evidence(evidence_id).current_valid
                for evidence_id in block.raw_evidence_ids
            )
        except KeyError:
            return False

    def _validate_source_refs(self, block: SemanticBlock) -> None:
        for evidence_id in block.raw_evidence_ids:
            self.source.get_evidence(evidence_id)

    @staticmethod
    def _with_derived_known_at(
        block: SemanticBlock,
    ) -> SemanticBlock:
        if block.derived_known_at is None:
            raise ValueError(
                "derived_known_at must be supplied by the state producer"
            )
        return block

    def put_semantic_block(self, block: SemanticBlock) -> SemanticBlock:
        self._validate_source_refs(block)
        return self.state.put_semantic_block(
            self._with_derived_known_at(block)
        )

    def get_semantic_block(self, block_id: str) -> SemanticBlock:
        return self.state.get_semantic_block(block_id)

    def get_semantic_block_state(self, state_id: str) -> SemanticBlock:
        return self.state.get_semantic_block_state(state_id)

    def list_semantic_blocks(
        self, *, current_valid_only: bool = True
    ) -> tuple[SemanticBlock, ...]:
        blocks = self.state.list_semantic_blocks()
        if not current_valid_only:
            return blocks
        return tuple(
            block
            for block in blocks
            if self._block_is_current(self.source, block)
        )

    def list_semantic_block_states(
        self, *, current_valid_only: bool = True
    ) -> tuple[SemanticBlock, ...]:
        states = self.state.list_semantic_block_states()
        if not current_valid_only:
            return states
        return tuple(
            block
            for block in states
            if self._block_is_current(self.source, block)
        )

    def list_semantic_blocks_at_cutoff(
        self, cutoff: datetime, *, current_valid_only: bool = True
    ) -> tuple[SemanticBlock, ...]:
        blocks = self.state.list_semantic_blocks_at_cutoff(cutoff)
        if not current_valid_only:
            return blocks
        return tuple(
            block
            for block in blocks
            if self._block_is_current(self.source, block)
        )

    def list_semantic_blocks_at_knowledge_cutoff(
        self, cutoff: datetime, *, current_valid_only: bool = True
    ) -> tuple[SemanticBlock, ...]:
        if cutoff.tzinfo != UTC:
            raise ValueError("cutoff must be UTC")
        latest: dict[str, SemanticBlock] = {}
        for block in self.state.list_semantic_block_states():
            try:
                visible = all(
                    (
                        self.evidence_valid_at(evidence_id, cutoff)
                        if current_valid_only
                        else self.source.get_evidence(
                            evidence_id
                        ).effective_known_at <= cutoff
                    )
                    for evidence_id in block.raw_evidence_ids
                )
            except KeyError:
                visible = False
            if (
                not visible
                or block.derived_known_at is None
                or block.derived_known_at > cutoff
            ):
                continue
            prior = latest.get(block.block_id)
            if prior is None or block.state_version > prior.state_version:
                latest[block.block_id] = block
        return tuple(
            sorted(
                latest.values(),
                key=lambda block: (block.occurred_start, block.block_id),
            )
        )

    def extend_semantic_block(
        self,
        block_id: str,
        *,
        content: str | None,
        evidence_id: str,
        occurred_at: datetime,
        derived_known_at: datetime,
    ) -> SemanticBlock:
        self.source.get_evidence(evidence_id)
        return self.state.extend_semantic_block(
            block_id,
            content=content,
            evidence_id=evidence_id,
            occurred_at=occurred_at,
            derived_known_at=derived_known_at,
        )

    def rebuild_vector_index(
        self,
        embedder: Callable[[SemanticBlock], tuple[float, ...]],
        *,
        index_version: str,
    ) -> None:
        self.state.replace_vector_index(
            self.list_semantic_block_states(current_valid_only=False),
            embedder,
            index_version=index_version,
        )

    def delete_vector_index(self) -> None:
        self.state.delete_vector_index()

    def get_vector(
        self, block_id: str, *, state_id: str | None = None
    ) -> VectorProjection:
        if state_id is None:
            block = self.state.get_semantic_block(block_id)
            if not self._block_is_current(self.source, block):
                raise KeyError(block_id)
        return self.state.get_vector(block_id, state_id=state_id)

    def vector_projection_ids(self) -> tuple[str, ...]:
        return tuple(
            block_id
            for block_id in self.state.vector_projection_ids()
            if self._block_is_current(
                self.source,
                self.state.get_semantic_block(block_id),
            )
        )

    def get_checkpoint(
        self, lineage_id: str
    ) -> CompilerCheckpoint | None:
        return self.state.get_checkpoint(lineage_id)

    def save_checkpoint(self, checkpoint: CompilerCheckpoint) -> None:
        self.state.save_checkpoint(checkpoint)

    def commit_compilation(
        self,
        *,
        evidence_id: str,
        lineage_id: str,
        block_states: tuple[SemanticBlock, ...],
        block_ids: tuple[str, ...],
        decision: Mapping[str, object],
        checkpoint: CompilerCheckpoint,
    ) -> None:
        self.source.get_evidence(evidence_id)
        normalized_states = []
        for block in block_states:
            self._validate_source_refs(block)
            normalized_states.append(
                self._with_derived_known_at(block)
            )
        self.state.commit_compilation(
            evidence_id=evidence_id,
            lineage_id=lineage_id,
            block_states=tuple(normalized_states),
            block_ids=block_ids,
            decision=decision,
            checkpoint=checkpoint,
        )

    def compiled_block_ids(
        self, evidence_id: str
    ) -> tuple[str, ...] | None:
        return self.state.compiled_block_ids(evidence_id)

    def mark_pending_failure(
        self, lineage_id: str, *, evidence_id: str, ordering_key: str
    ) -> None:
        self.state.mark_pending_failure(
            lineage_id,
            evidence_id=evidence_id,
            ordering_key=ordering_key,
        )

    def get_pipeline_stage(self, evidence_id: str) -> str | None:
        return self.state.get_pipeline_stage(evidence_id)

    def get_pipeline_progress(
        self, evidence_id: str
    ) -> tuple[str, str | None] | None:
        reader = getattr(self.state, "get_pipeline_progress", None)
        if not callable(reader):
            return None
        result = reader(evidence_id)
        return result if isinstance(result, tuple) else None

    def mark_pipeline_stage(
        self,
        evidence_id: str,
        stage: str,
        *,
        fingerprint: str | None = None,
    ) -> None:
        self.state.mark_pipeline_stage(
            evidence_id, stage, fingerprint=fingerprint
        )

    def close(self) -> None:
        if self._closed:
            return
        if self._close_state:
            self.state.close()
        if self._close_source:
            close = getattr(self.source, "close", None)
            if callable(close):
                close()
        self._closed = True
