"""Independent in-memory V1 Reference Memory substrate for replacement tests."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import datetime

from lce.reference_memory.contracts import (
    CompilerCheckpoint,
    RawEvidence,
    ReferenceMemorySubstratePort,
    SemanticBlock,
    VectorProjection,
)


class InMemoryReferenceMemory:
    """A complete V1 substrate that shares no implementation with SQLite."""

    def __init__(self) -> None:
        self._evidence: dict[str, RawEvidence] = {}
        self._current_blocks: dict[str, SemanticBlock] = {}
        self._states: dict[str, SemanticBlock] = {}
        self._vectors: dict[tuple[str, str], VectorProjection] = {}
        self._checkpoints: dict[str, CompilerCheckpoint] = {}
        self._compiled: dict[str, tuple[str, ...]] = {}
        self._stages: dict[str, tuple[str, str | None]] = {}

    @staticmethod
    def _state_id(block: SemanticBlock) -> str:
        payload = {
            "block_id": block.block_id,
            "state_version": block.state_version,
            "content": block.content,
            "raw_evidence_ids": block.raw_evidence_ids,
            "occurred_start": block.occurred_start.isoformat(),
            "occurred_end": block.occurred_end.isoformat(),
            "metadata": dict(block.metadata),
        }
        return "state_" + hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:24]

    @staticmethod
    def _check_provenance(item: RawEvidence) -> None:
        if not item.provenance.get("source") or item.provenance.get("canonical") is not True:
            raise ValueError("canonical source provenance is required")
        if item.provenance.get("derived") is True:
            raise ValueError("derived cognition cannot be written as evidence")

    def add_evidence(self, item: RawEvidence) -> RawEvidence:
        self._check_provenance(item)
        existing = self._evidence.get(item.evidence_id)
        if existing is not None:
            if (
                existing.content,
                existing.occurred_at,
                existing.effective_ordering_key,
                dict(existing.provenance),
            ) != (item.content, item.occurred_at, item.effective_ordering_key, dict(item.provenance)):
                raise ValueError(f"evidence_id '{item.evidence_id}' already has different immutable content")
            return existing
        self._evidence[item.evidence_id] = item
        return item

    def get_evidence(self, evidence_id: str) -> RawEvidence:
        try:
            return self._evidence[evidence_id]
        except KeyError:
            raise KeyError(evidence_id) from None

    def list_current_valid_evidence(self) -> tuple[RawEvidence, ...]:
        return tuple(
            sorted(
                (item for item in self._evidence.values() if item.current_valid),
                key=lambda item: (item.effective_ordering_key, item.evidence_id),
            )
        )

    def invalidate(self, evidence_id: str, *, reason: str) -> None:
        item = self.get_evidence(evidence_id)
        self._evidence[evidence_id] = replace(item, state="INVALID", superseded_by=None)

    def supersede(self, evidence_id: str, replacement_evidence_id: str) -> None:
        item = self.get_evidence(evidence_id)
        replacement = self.get_evidence(replacement_evidence_id)
        if not replacement.current_valid:
            raise ValueError("replacement evidence must be current-valid")
        self._evidence[evidence_id] = replace(item, state="SUPERSEDED", superseded_by=replacement_evidence_id)

    def put_semantic_block(self, block: SemanticBlock) -> SemanticBlock:
        for evidence_id in block.raw_evidence_ids:
            self.get_evidence(evidence_id)
        existing = self._current_blocks.get(block.block_id)
        if existing is not None:
            if replace(existing, state_id=None) != replace(block, state_id=None):
                raise ValueError(f"block_id '{block.block_id}' already has different immutable content")
            return existing
        return self._write_current(block)

    def _write_current(self, block: SemanticBlock) -> SemanticBlock:
        stored = replace(block, state_id=block.state_id or self._state_id(block))
        self._states[stored.state_id or ""] = stored
        self._current_blocks[stored.block_id] = stored
        return stored

    def extend_semantic_block(
        self, block_id: str, *, content: str | None, evidence_id: str, occurred_at: datetime
    ) -> SemanticBlock:
        current = self.get_semantic_block(block_id)
        self.get_evidence(evidence_id)
        evidence_ids = current.raw_evidence_ids if evidence_id in current.raw_evidence_ids else current.raw_evidence_ids + (evidence_id,)
        merged = current.content
        if content and content.strip() and content.strip() not in current.content:
            merged = f"{current.content}\n{content.strip()}"
        return self._write_current(
            replace(
                current,
                content=merged,
                raw_evidence_ids=evidence_ids,
                occurred_start=min(current.occurred_start, occurred_at),
                occurred_end=max(current.occurred_end, occurred_at),
                state_id=None,
                state_version=current.state_version + 1,
            )
        )

    def get_semantic_block(self, block_id: str) -> SemanticBlock:
        try:
            return self._current_blocks[block_id]
        except KeyError:
            raise KeyError(block_id) from None

    def get_semantic_block_state(self, state_id: str) -> SemanticBlock:
        try:
            return self._states[state_id]
        except KeyError:
            raise KeyError(state_id) from None

    def list_semantic_blocks(self, *, current_valid_only: bool = True) -> tuple[SemanticBlock, ...]:
        blocks = tuple(sorted(self._current_blocks.values(), key=lambda block: (block.occurred_start, block.block_id)))
        if not current_valid_only:
            return blocks
        return tuple(
            block for block in blocks
            if all(self.get_evidence(evidence_id).current_valid for evidence_id in block.raw_evidence_ids)
        )

    def list_semantic_block_states(self, *, current_valid_only: bool = True) -> tuple[SemanticBlock, ...]:
        states = tuple(sorted(self._states.values(), key=lambda block: (block.occurred_start, block.block_id, block.state_version)))
        if not current_valid_only:
            return states
        return tuple(
            block for block in states
            if all(self.get_evidence(evidence_id).current_valid for evidence_id in block.raw_evidence_ids)
        )

    def list_semantic_blocks_at_cutoff(
        self, cutoff: datetime, *, current_valid_only: bool = True
    ) -> tuple[SemanticBlock, ...]:
        latest: dict[str, SemanticBlock] = {}
        for block in self.list_semantic_block_states(current_valid_only=current_valid_only):
            if block.occurred_end <= cutoff and (
                block.block_id not in latest or block.state_version > latest[block.block_id].state_version
            ):
                latest[block.block_id] = block
        return tuple(sorted(latest.values(), key=lambda block: (block.occurred_start, block.block_id)))

    def rebuild_vector_index(
        self, embedder: Callable[[SemanticBlock], tuple[float, ...]], *, index_version: str
    ) -> None:
        self._vectors.clear()
        for block in self.list_semantic_block_states(current_valid_only=True):
            self._vectors[(block.block_id, block.state_id or "")] = VectorProjection(
                block.block_id, tuple(float(value) for value in embedder(block)), index_version
            )

    def delete_vector_index(self) -> None:
        self._vectors.clear()

    def vector_projection_ids(self) -> tuple[str, ...]:
        return tuple(sorted({block_id for block_id, state_id in self._vectors if self._current_blocks.get(block_id, None) and self._current_blocks[block_id].state_id == state_id}))

    def get_vector(self, block_id: str, *, state_id: str | None = None) -> VectorProjection:
        current = self.get_semantic_block(block_id)
        key = (block_id, state_id or current.state_id or "")
        try:
            return self._vectors[key]
        except KeyError:
            raise KeyError(block_id) from None

    def get_checkpoint(self, lineage_id: str) -> CompilerCheckpoint | None:
        return self._checkpoints.get(lineage_id)

    def save_checkpoint(self, checkpoint: CompilerCheckpoint) -> None:
        self._checkpoints[checkpoint.lineage_id] = checkpoint

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
        for block in block_states:
            self._write_current(block)
        self._compiled[evidence_id] = block_ids
        self._checkpoints[lineage_id] = checkpoint
        self.mark_pipeline_stage(evidence_id, "compiled")

    def compiled_block_ids(self, evidence_id: str) -> tuple[str, ...] | None:
        return self._compiled.get(evidence_id)

    def mark_pending_failure(self, lineage_id: str, *, evidence_id: str, ordering_key: str) -> None:
        current = self._checkpoints.get(lineage_id)
        state = dict(current.state) if current else {}
        state.update({"pending_evidence_id": evidence_id, "pending_ordering_key": ordering_key})
        self._checkpoints[lineage_id] = CompilerCheckpoint(
            lineage_id=lineage_id,
            last_ordering_key=current.last_ordering_key if current else None,
            open_block_id=current.open_block_id if current else None,
            compiler_version=current.compiler_version if current else "lce-semantic-stream-v1",
            state=state,
        )

    def get_pipeline_stage(self, evidence_id: str) -> str | None:
        return self._stages.get(evidence_id, (None, None))[0]

    def mark_pipeline_stage(self, evidence_id: str, stage: str, *, fingerprint: str | None = None) -> None:
        self._stages[evidence_id] = (stage, fingerprint)

    def close(self) -> None:
        return None


assert isinstance(InMemoryReferenceMemory(), ReferenceMemorySubstratePort)
