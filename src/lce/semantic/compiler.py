"""Restart-safe Semantic Block compiler using the BLOCK-03 stream boundary."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from collections.abc import Sequence

from lce.reference_memory.contracts import CompilerCheckpoint, RawEvidence, SemanticBlock
from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.semantic.contracts import SemanticDecision, SemanticDecisionProvider, SemanticGroup
from lce.semantic.providers import RuleBasedSemanticProvider


@dataclass(frozen=True, slots=True)
class CompilerResult:
    evidence_id: str
    block_ids: tuple[str, ...]
    action: str
    replayed: bool = False


class SemanticCompiler:
    """Compile ordered Raw Evidence without silently crossing failed input."""

    def __init__(
        self,
        store: ReferenceMemoryStore,
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
            return CompilerResult(material.evidence_id, existing, "REPLAY", replayed=True)

        checkpoint = self.store.get_checkpoint(self.lineage_id)
        if checkpoint is not None and material.effective_ordering_key < (checkpoint.last_ordering_key or ""):
            raise ValueError("semantic stream input is out of order")
        open_block = self.store.get_semantic_block(checkpoint.open_block_id) if checkpoint and checkpoint.open_block_id else None
        recent_blocks = self.store.list_semantic_blocks(current_valid_only=False)

        # Provider failure intentionally occurs before any block/checkpoint write.
        decision = self.provider.decide(
            evidence=material,
            open_block=open_block,
            recent_blocks=recent_blocks,
        )
        block_ids, next_open, next_sequence = self._apply(material, decision, open_block, checkpoint)
        state = dict(checkpoint.state) if checkpoint is not None else {}
        state["next_block_sequence"] = next_sequence
        self.store.record_compiled_evidence(material.evidence_id, self.lineage_id, block_ids, decision.as_mapping())
        self.store.save_checkpoint(
            CompilerCheckpoint(
                lineage_id=self.lineage_id,
                last_ordering_key=material.effective_ordering_key,
                open_block_id=next_open.block_id if next_open is not None else None,
                compiler_version=self.compiler_version,
                state=state,
            )
        )
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
        self.store.put_semantic_block(block)
        return block

    def _apply(
        self,
        material: RawEvidence,
        decision: SemanticDecision,
        open_block: SemanticBlock | None,
        checkpoint: CompilerCheckpoint | None,
    ) -> tuple[tuple[str, ...], SemanticBlock | None, int]:
        state = dict(checkpoint.state) if checkpoint is not None else {}
        sequence = int(str(state.get("next_block_sequence", 0)))

        def append(block: SemanticBlock, content: str | None) -> SemanticBlock:
            return self.store.extend_semantic_block(
                block.block_id,
                content=content,
                evidence_id=material.evidence_id,
                occurred_at=material.occurred_at,
            )

        def create(subject: str, cognition: str) -> SemanticBlock:
            nonlocal sequence
            sequence += 1
            return self._new_block(material, subject, cognition, sequence)

        if decision.action == "SPLIT":
            current = open_block
            result: list[str] = []
            for group in decision.groups:
                if current is not None and str(current.metadata.get("subject", "")) == group.subject:
                    current = append(current, group.cognition)
                else:
                    current = create(group.subject, group.cognition)
                result.append(current.block_id)
            return tuple(dict.fromkeys(result)), current, sequence

        if decision.action == "RECAP" and decision.recap_block_ids:
            result = []
            for block_id in decision.recap_block_ids:
                target = self.store.get_semantic_block(block_id)
                target = append(target, decision.new_information)
                result.append(target.block_id)
            return tuple(dict.fromkeys(result)), open_block, sequence

        if decision.action in {"CONTINUE", "MERGE", "AUXILIARY"} and open_block is not None:
            updated = append(open_block, decision.cognition)
            return (updated.block_id,), updated, sequence

        created = create(decision.subject, decision.cognition)
        return (created.block_id,), created, sequence
