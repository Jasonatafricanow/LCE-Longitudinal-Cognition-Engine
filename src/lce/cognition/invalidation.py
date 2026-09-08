"""Targeted propagation of Memory validity changes into derived cognition."""

from __future__ import annotations

from dataclasses import dataclass

from lce.cognition.worktree import CognitionWorktreeStore
from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.store.interface import BaselineStorePort
from lce.structure.discovery import SnapshotStructureDiscovery


@dataclass(frozen=True, slots=True)
class InvalidationResult:
    evidence_id: str
    affected_block_ids: tuple[str, ...]
    affected_snapshot_ids: tuple[str, ...]
    affected_worktree_ids: tuple[str, ...]
    affected_baseline_ids: tuple[str, ...]


class DependencyInvalidator:
    def __init__(self, memory, discovery, worktrees, baselines: BaselineStorePort) -> None:
        self.memory: ReferenceMemoryStore = memory
        self.discovery: SnapshotStructureDiscovery = discovery
        self.worktrees: CognitionWorktreeStore = worktrees
        self.baselines = baselines

    def invalidate(self, evidence_id: str, *, reason: str = "source evidence changed") -> InvalidationResult:
        self.memory.invalidate(evidence_id, reason=reason)
        affected_blocks = tuple(
            block.block_id
            for block in self.memory.list_semantic_blocks(current_valid_only=False)
            if evidence_id in block.raw_evidence_ids
        )
        affected_set = set(affected_blocks)
        snapshot_ids = tuple(
            snapshot.snapshot_id
            for snapshot in self.discovery.snapshots.all_snapshots()
            if affected_set & set(snapshot.visible_block_ids)
        )
        worktree_ids = tuple(
            item.worktree_id
            for item in self.worktrees.list(status="OPEN")
            if affected_set & set(item.supporting_block_ids)
        )
        for worktree_id in worktree_ids:
            self.worktrees.mark_needs_rebuild(worktree_id)
        baseline_ids: list[str] = []
        list_regions = getattr(self.baselines, "list_regions", lambda: ())
        for region_id in list_regions():
            history = self.baselines.get_history(region_id)
            baseline_ids.extend(
                revision.baseline_id
                for revision in history.revisions
                if affected_set & set(revision.supporting_memory_ids)
            )
        return InvalidationResult(
            evidence_id=evidence_id,
            affected_block_ids=affected_blocks,
            affected_snapshot_ids=tuple(sorted(snapshot_ids)),
            affected_worktree_ids=worktree_ids,
            affected_baseline_ids=tuple(sorted(set(baseline_ids))),
        )
