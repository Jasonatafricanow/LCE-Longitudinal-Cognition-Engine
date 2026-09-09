"""Restart-safe Semantic Block compiler using the BLOCK-03 stream boundary."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, replace

from lce.reference_memory.contracts import (
    CompilerCheckpoint,
    RawEvidence,
    ReferenceMemorySubstratePort,
    SemanticBlock,
)
from lce.semantic.contracts import SemanticDecision, SemanticDecisionProvider
from lce.semantic.providers import RuleBasedSemanticProvider


@dataclass(frozen=True, slots=True)
class CompilerResult:
    evidence_id: str
    block_ids: tuple[str, ...]
    action: str
    replayed: bool = False


class PendingInputError(RuntimeError):
    """Raised when a later input tries to cross an earlier failed input."""


class SemanticCompiler:
    """Compile ordered Raw Evidence without silently crossing failed input."""

    def __init__(
        self,
        store: ReferenceMemorySubstratePort,
        provider: SemanticDecisionProvider | None,
        *,
        lineage_id: str,
        compiler_version: str = "lce-semantic-stream-v1",
    ) -> None:
        self.store = store
        self.provider = provider or RuleBasedSemanticProvider()
        self.lineage_id = lineage_id
        self.compiler_version = compiler_version

    def process(self, material: RawEvidence) -> CompilerResult:
        self.store.add_evidence(material)
        existing = self.store.compiled_block_ids(material.evidence_id)
        if existing is not None:
            checkpoint = self.store.get_checkpoint(self.lineage_id)
            if checkpoint is not None and checkpoint.state.get("pending_evidence_id") == material.evidence_id:
                state = dict(checkpoint.state)
                state.pop("pending_evidence_id", None)
                state.pop("pending_ordering_key", None)
                self.store.save_checkpoint(replace(checkpoint, state=state))
            return CompilerResult(material.evidence_id, existing, "REPLAY", replayed=True)

        checkpoint = self.store.get_checkpoint(self.lineage_id)
        pending_id = str(checkpoint.state.get("pending_evidence_id", "")) if checkpoint else ""
        if pending_id and pending_id != material.evidence_id:
            raise PendingInputError(
                f"semantic stream is blocked by pending input '{pending_id}'"
            )
        last_order = (
            (checkpoint.last_ordering_key, str(checkpoint.state.get("last_evidence_id", "")))
            if checkpoint is not None and checkpoint.last_ordering_key is not None
            else None
        )
        current_order = (material.effective_ordering_key, material.evidence_id)
        if last_order is not None and current_order < last_order:
            raise ValueError("semantic stream input is out of order")
        open_block = self.store.get_semantic_block(checkpoint.open_block_id) if checkpoint and checkpoint.open_block_id else None
        recent_blocks = self.store.list_semantic_blocks(current_valid_only=False)

        try:
            decision = self.provider.decide(
                evidence=material,
                open_block=open_block,
                recent_blocks=recent_blocks,
            )
            block_ids, next_open, next_sequence, block_states = self._apply(
                material, decision, open_block, checkpoint
            )
        except Exception:
            self.store.mark_pending_failure(
                self.lineage_id,
                evidence_id=material.evidence_id,
                ordering_key=material.effective_ordering_key,
            )
            raise
        state = dict(checkpoint.state) if checkpoint is not None else {}
        state["next_block_sequence"] = next_sequence
        state["last_evidence_id"] = material.evidence_id
        state.pop("pending_evidence_id", None)
        state.pop("pending_ordering_key", None)
        next_checkpoint = CompilerCheckpoint(
            lineage_id=self.lineage_id,
            last_ordering_key=material.effective_ordering_key,
            open_block_id=next_open.block_id if next_open is not None else None,
            compiler_version=self.compiler_version,
            state=state,
        )
        try:
            self.store.commit_compilation(
                evidence_id=material.evidence_id,
                lineage_id=self.lineage_id,
                block_states=block_states,
                block_ids=block_ids,
                decision=decision.as_mapping(),
                checkpoint=next_checkpoint,
            )
        except Exception:
            self.store.mark_pending_failure(
                self.lineage_id,
                evidence_id=material.evidence_id,
                ordering_key=material.effective_ordering_key,
            )
            raise
        return CompilerResult(material.evidence_id, block_ids, decision.action)

    def process_batch(self, materials: Sequence[RawEvidence]) -> tuple[CompilerResult, ...]:
        return tuple(self.process(material) for material in materials)

    def _new_block(
        self,
        material: RawEvidence,
        subject: str,
        cognition: str,
        sequence: int,
    ) -> SemanticBlock:
        digest = hashlib.sha256(self.lineage_id.encode("utf-8")).hexdigest()[:10]
        block = SemanticBlock(
            block_id=f"sb_{digest}_{sequence:06d}",
            content=cognition,
            raw_evidence_ids=(material.evidence_id,),
            occurred_start=material.occurred_at,
            occurred_end=material.occurred_at,
            compiler_version=self.compiler_version,
            lineage_id=self.lineage_id,
            metadata={
                "subject": subject,
                **({"vector": material.provenance["vector"]} if "vector" in material.provenance else {}),
            },
        )
        return block

    def _apply(
        self,
        material: RawEvidence,
        decision: SemanticDecision,
        open_block: SemanticBlock | None,
        checkpoint: CompilerCheckpoint | None,
    ) -> tuple[tuple[str, ...], SemanticBlock | None, int, tuple[SemanticBlock, ...]]:
        state = dict(checkpoint.state) if checkpoint is not None else {}
        sequence = int(str(state.get("next_block_sequence", 0)))

        updates: dict[str, SemanticBlock] = {}

        def append(block: SemanticBlock, content: str | None) -> SemanticBlock:
            evidence_ids = (
                block.raw_evidence_ids
                if material.evidence_id in block.raw_evidence_ids
                else block.raw_evidence_ids + (material.evidence_id,)
            )
            merged_content = block.content
            if content and content.strip() and content.strip() not in block.content:
                merged_content = f"{block.content}\n{content.strip()}"
            updated = replace(
                block,
                content=merged_content,
                raw_evidence_ids=evidence_ids,
                occurred_start=min(block.occurred_start, material.occurred_at),
                occurred_end=max(block.occurred_end, material.occurred_at),
                state_id=None,
                state_version=block.state_version + 1,
            )
            updates[updated.block_id] = updated
            return updated

        def create(subject: str, cognition: str) -> SemanticBlock:
            nonlocal sequence
            sequence += 1
            created = self._new_block(material, subject, cognition, sequence)
            updates[created.block_id] = created
            return created

        if decision.action == "SPLIT":
            current = open_block
            result: list[str] = []
            for group in decision.groups:
                if current is not None and str(current.metadata.get("subject", "")) == group.subject:
                    current = append(current, group.cognition)
                else:
                    current = create(group.subject, group.cognition)
                result.append(current.block_id)
            return tuple(dict.fromkeys(result)), current, sequence, tuple(updates.values())

        if decision.action == "RECAP" and decision.recap_block_ids:
            result = []
            for block_id in decision.recap_block_ids:
                target = self.store.get_semantic_block(block_id)
                target = append(target, decision.new_information)
                result.append(target.block_id)
            return tuple(dict.fromkeys(result)), open_block, sequence, tuple(updates.values())

        if decision.action in {"CONTINUE", "MERGE", "AUXILIARY"} and open_block is not None:
            updated = append(open_block, decision.cognition)
            return (updated.block_id,), updated, sequence, tuple(updates.values())

        created = create(decision.subject, decision.cognition)
        updates[created.block_id] = created
        return (created.block_id,), created, sequence, tuple(updates.values())
