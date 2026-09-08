"""Unified standalone batch/nearline LCE V1 runtime."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from lce.cognition.invalidation import DependencyInvalidator, InvalidationResult
from lce.cognition.promotion import (
    ConservativePromotionPolicy,
    PromotionPolicy,
    UnderstandingPromoter,
)
from lce.cognition.worktree import CognitionWorktreeStore
from lce.contracts.consolidation import ConsolidationResult
from lce.core.equivalence import is_content_equivalent
from lce.read_api import AcceptedUnderstandingReadAPI, UnderstandingView
from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.semantic.compiler import CompilerResult, SemanticCompiler
from lce.semantic.contracts import SemanticDecisionProvider
from lce.store.sqlite_store import SqliteBaselineStore
from lce.structure.contracts import HigherOrderCandidate, StructureConfig, StructureDiff, StructureSnapshot
from lce.structure.discovery import SnapshotStructureDiscovery


def deterministic_block_embedding(block: SemanticBlock) -> tuple[float, ...]:
    configured = block.metadata.get("vector")
    if isinstance(configured, (list, tuple)) and configured:
        return tuple(float(value) for value in configured)
    values = [0.0] * 16
    for token in re.findall(r"\w+", block.content.casefold()):
        index = int(hashlib.sha256(token.encode()).hexdigest()[:8], 16) % len(values)
        values[index] += 1.0
    return tuple(values)


@dataclass(frozen=True, slots=True)
class ProcessResult:
    compiler_result: CompilerResult
    snapshot: StructureSnapshot
    diff: StructureDiff | None
    higher_order_candidates: tuple[HigherOrderCandidate, ...]
    promotions: tuple[ConsolidationResult, ...]


class LceRuntime:
    """Single cognition pipeline used by both historical and nearline modes."""

    def __init__(
        self,
        root: Path | str,
        *,
        provider: SemanticDecisionProvider | None = None,
        policy: PromotionPolicy | None = None,
        lineage_id: str = "default",
        structure_config: StructureConfig | None = None,
    ) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.memory = ReferenceMemoryStore(self.root / "memory")
        self.baselines = SqliteBaselineStore(self.root / "baselines")
        self.worktrees = CognitionWorktreeStore(self.root / "worktrees")
        self.discovery = SnapshotStructureDiscovery(self.memory, self.root / "structures", config=structure_config)
        self.compiler = SemanticCompiler(self.memory, provider, lineage_id=lineage_id)
        self.policy = policy or ConservativePromotionPolicy()
        self.promoter = UnderstandingPromoter(
            memory=self.memory, baseline_store=self.baselines, worktree_store=self.worktrees, policy=self.policy
        )
        self.read_api = AcceptedUnderstandingReadAPI(memory=self.memory, baseline_store=self.baselines)

    def process(self, material: RawEvidence, *, mode: str = "nearline") -> ProcessResult:
        if mode not in {"batch", "nearline"}:
            raise ValueError("mode must be batch or nearline")
        compiler_result = self.compiler.process(material)
        self.memory.rebuild_vector_index(deterministic_block_embedding, index_version="lce-vector-v1")
        previous = max(
            (snapshot for snapshot in self.discovery.snapshots.all_snapshots() if snapshot.cutoff < material.occurred_at),
            key=lambda snapshot: snapshot.cutoff,
            default=None,
        )
        snapshot = self.discovery.create_snapshot(material.occurred_at)
        diff = self.discovery.diff(previous, snapshot) if previous else None
        candidates = self.discovery.higher_order_candidates(snapshot)
        promotions: list[ConsolidationResult] = []
        if not compiler_result.replayed:
            for candidate in candidates:
                result = self._evaluate_candidate(candidate, snapshot)
                if result is not None:
                    promotions.append(result)
        return ProcessResult(compiler_result, snapshot, diff, candidates, tuple(promotions))

    def run_batch(self, materials: Sequence[RawEvidence]) -> tuple[ProcessResult, ...]:
        ordered = sorted(materials, key=lambda item: (item.effective_ordering_key, item.evidence_id))
        return tuple(self.process(material, mode="batch") for material in ordered)

    def _evaluate_candidate(self, candidate: HigherOrderCandidate, snapshot: StructureSnapshot) -> ConsolidationResult | None:
        region_id = "higher-order:" + ":".join(candidate.supporting_structure_ids)
        content = "Longitudinal relation between structures " + ", ".join(candidate.supporting_structure_ids)
        head = self.baselines.get_head(region_id)
        if head is not None and is_content_equivalent(head.content, content):
            return None
        existing = self.worktrees.find_open_by_region(region_id)
        if existing is None:
            existing = self.worktrees.create(
                region_id=region_id,
                candidate_content=content,
                supporting_block_ids=candidate.supporting_block_ids,
                supporting_structure_ids=candidate.supporting_structure_ids,
                base_baseline=head,
            )
        else:
            self.worktrees.update_support(
                existing.worktree_id,
                add_block_ids=candidate.supporting_block_ids,
                add_structure_ids=candidate.supporting_structure_ids,
            )
        self.worktrees.record_support(existing.worktree_id, snapshot_id=snapshot.snapshot_id)
        return self.promoter.evaluate(existing.worktree_id)

    def query(self, current_context: str | dict[str, object] | None) -> tuple[UnderstandingView, ...]:
        return self.read_api.query(current_context)

    def invalidate_and_rebuild(self, evidence_id: str, *, cutoff: datetime | None = None) -> InvalidationResult:
        invalidator = DependencyInvalidator(self.memory, self.discovery, self.worktrees, self.baselines)
        result = invalidator.invalidate(evidence_id)
        self.memory.rebuild_vector_index(deterministic_block_embedding, index_version="lce-vector-v1")
        latest = cutoff or max(
            (snapshot.cutoff for snapshot in self.discovery.snapshots.all_snapshots()),
            default=datetime.now(UTC),
        )
        corrected_snapshot = self.discovery.create_snapshot(latest)
        correction_policy = ConservativePromotionPolicy(min_blocks=1, min_structures=0, min_support_cycles=1)
        correction_promoter = UnderstandingPromoter(
            memory=self.memory, baseline_store=self.baselines, worktree_store=self.worktrees, policy=correction_policy
        )
        affected_blocks = set(result.affected_block_ids)
        current_blocks = {
            block.block_id for block in self.memory.list_semantic_blocks(current_valid_only=True)
        }
        for region_id in self.baselines.list_regions():
            head = self.baselines.get_head(region_id)
            if head is None or not affected_blocks.intersection(head.supporting_memory_ids):
                continue
            valid_blocks = tuple(block_id for block_id in head.supporting_memory_ids if block_id in current_blocks)
            if not valid_blocks:
                continue
            structure_ids = tuple(
                observation.structure_id
                for observation in corrected_snapshot.structures
                if set(observation.member_block_ids) & set(valid_blocks)
            )
            correction = self.worktrees.create(
                region_id=region_id,
                candidate_content=f"{head.content} [corrected after invalidation]",
                supporting_block_ids=valid_blocks,
                supporting_structure_ids=structure_ids,
                base_baseline=head,
            )
            self.worktrees.record_support(correction.worktree_id, snapshot_id=corrected_snapshot.snapshot_id)
            correction_promoter.evaluate(correction.worktree_id)
        return result

    def close(self) -> None:
        self.discovery.close()
        self.worktrees.close()
        self.baselines.close()
        self.memory.close()
