"""Unified standalone batch/nearline LCE V1 runtime."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from lce.cognition.invalidation import DependencyInvalidator, InvalidationResult
from lce.cognition.promotion import (
    BoundedInterpretation,
    BoundedInterpretationPackage,
    BoundedInterpreter,
    ConservativePromotionPolicy,
    PromotionPolicy,
    RuleBasedBoundedInterpreter,
    UnderstandingPromoter,
)
from lce.cognition.worktree import CognitionWorktreeStore
from lce.contracts.consolidation import ConsolidationResult
from lce.read_api import AcceptedUnderstandingReadAPI, UnderstandingView
from lce.reference_memory.contracts import (
    AuthorizedSelectedSupport,
    RawEvidence,
    ReferenceMemorySubstratePort,
    SemanticBlock,
)
from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.semantic.compiler import CompilerResult, SemanticCompiler
from lce.semantic.contracts import SemanticDecisionProvider
from lce.store.sqlite_store import SqliteBaselineStore
from lce.structure.contracts import (
    HigherOrderCandidate,
    StructureConfig,
    StructureDiff,
    StructureSnapshot,
)
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
        memory: ReferenceMemorySubstratePort | None = None,
        interpreter: BoundedInterpreter | None = None,
    ) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.memory: ReferenceMemorySubstratePort = memory if memory is not None else ReferenceMemoryStore(self.root / "memory")
        self._owns_memory = memory is None
        self.baselines = SqliteBaselineStore(self.root / "baselines")
        self.worktrees = CognitionWorktreeStore(self.root / "worktrees")
        self.discovery = SnapshotStructureDiscovery(self.memory, self.root / "structures", config=structure_config)
        self.compiler = SemanticCompiler(self.memory, provider, lineage_id=lineage_id)
        self.policy = policy or ConservativePromotionPolicy()
        self.interpreter = interpreter or RuleBasedBoundedInterpreter()
        self.promoter = UnderstandingPromoter(
            memory=self.memory, baseline_store=self.baselines, worktree_store=self.worktrees, policy=self.policy
        )
        self.read_api = AcceptedUnderstandingReadAPI(memory=self.memory, baseline_store=self.baselines)

    def process(self, material: RawEvidence, *, mode: str = "nearline") -> ProcessResult:
        if mode not in {"batch", "nearline"}:
            raise ValueError("mode must be batch or nearline")
        compiler_result = self.compiler.process(material)
        stage = self.memory.get_pipeline_stage(material.evidence_id)
        if compiler_result.replayed and stage == "complete":
            return self._completed_replay_result(material, compiler_result)
        if stage not in {"vector-ready", "snapshot/discovery-evaluated", "worktree-support-evaluated", "promotion-evaluated", "complete"}:
            self.memory.rebuild_vector_index(deterministic_block_embedding, index_version="lce-vector-v1")
            self.memory.mark_pipeline_stage(material.evidence_id, "vector-ready", fingerprint="lce-vector-v1")
        previous = max(
            (snapshot for snapshot in self.discovery.snapshots.all_snapshots() if snapshot.cutoff < material.occurred_at),
            key=lambda snapshot: snapshot.cutoff,
            default=None,
        )
        snapshot = self.discovery.create_snapshot(material.occurred_at)
        diff = self.discovery.diff(previous, snapshot) if previous else None
        candidates = self.discovery.higher_order_candidates(snapshot)
        promotions: list[ConsolidationResult] = []
        self.memory.mark_pipeline_stage(material.evidence_id, "snapshot/discovery-evaluated", fingerprint=snapshot.snapshot_id)
        for candidate in candidates:
            result = self._evaluate_candidate(candidate, snapshot, diff)
            if result is not None:
                promotions.append(result)
        self.memory.mark_pipeline_stage(material.evidence_id, "worktree-support-evaluated", fingerprint=snapshot.snapshot_id)
        self.memory.mark_pipeline_stage(material.evidence_id, "promotion-evaluated", fingerprint=snapshot.snapshot_id)
        self.memory.mark_pipeline_stage(material.evidence_id, "complete", fingerprint=snapshot.snapshot_id)
        return ProcessResult(compiler_result, snapshot, diff, candidates, tuple(promotions))

    def _completed_replay_result(
        self, material: RawEvidence, compiler_result: CompilerResult
    ) -> ProcessResult:
        progress_reader = getattr(self.memory, "get_pipeline_progress", None)
        progress = progress_reader(material.evidence_id) if callable(progress_reader) else None
        snapshot: StructureSnapshot | None = None
        if progress is not None and progress[1] is not None:
            try:
                snapshot = self.discovery.snapshots.get(progress[1])
            except KeyError:
                snapshot = None
        if snapshot is None:
            matching = [
                item for item in self.discovery.snapshots.all_snapshots()
                if item.cutoff == material.occurred_at
            ]
            snapshot = max(matching, key=lambda item: item.snapshot_id, default=None)
        if snapshot is None:
            # Rebuilding a derived snapshot is safe, but no cognition stage is rerun.
            snapshot = self.discovery.create_snapshot(material.occurred_at)
        candidates = self.discovery.higher_order_candidates(snapshot)
        return ProcessResult(compiler_result, snapshot, None, candidates, ())

    def run_batch(self, materials: Sequence[RawEvidence]) -> tuple[ProcessResult, ...]:
        ordered = sorted(materials, key=lambda item: (item.effective_ordering_key, item.evidence_id))
        return tuple(self.process(material, mode="batch") for material in ordered)

    def _evaluate_candidate(
        self,
        candidate: HigherOrderCandidate,
        snapshot: StructureSnapshot,
        diff: StructureDiff | None,
    ) -> ConsolidationResult | None:
        region_id = "higher-order:" + ":".join(candidate.supporting_structure_ids)
        head = self.baselines.get_head(region_id)
        existing = self.worktrees.find_open_by_region(region_id)
        if existing is not None:
            reconciled = self.promoter.reconcile_committed(existing.worktree_id)
            if reconciled is not None:
                return reconciled
        structures = tuple(
            observation
            for observation in snapshot.structures
            if observation.structure_id in candidate.supporting_structure_ids
        )
        blocks_by_id = {block.block_id: block for block in snapshot.block_states}
        blocks = tuple(blocks_by_id[block_id] for block_id in candidate.supporting_block_ids if block_id in blocks_by_id)
        source_refs = tuple(sorted({source for block in blocks for source in block.raw_evidence_ids}))
        package = BoundedInterpretationPackage(
            candidate=candidate,
            structures=structures,
            semantic_blocks=blocks,
            authorized_source_refs=source_refs,
            previous_baseline=head,
        )
        interpretation = self.interpreter.interpret(package)
        if interpretation.status != "PROPOSED" or interpretation.content is None:
            return None
        content = interpretation.content
        authorized_blocks = set(candidate.supporting_block_ids)
        if not set(interpretation.supporting_block_ids).issubset(authorized_blocks):
            raise ValueError("bounded interpreter returned an unauthorized Semantic Block")
        selected_support = self._selected_support(interpretation, blocks)
        interpretation = replace(
            interpretation,
            supporting_block_ids=tuple(item.block_id for item in selected_support),
            selected_support=selected_support,
        )
        if head is not None and head.content.strip() == content.strip():
            return None
        support_identity = self._support_identity(candidate, snapshot, diff, selected_support)
        if existing is None:
            existing = self.worktrees.create(
                region_id=region_id,
                candidate_content=content,
                supporting_block_ids=candidate.supporting_block_ids,
                supporting_structure_ids=candidate.supporting_structure_ids,
                base_baseline=head,
                interpretation_trace=interpretation.model_trace,
                selected_support=selected_support,
            )
        else:
            self.worktrees.update_support(
                existing.worktree_id,
                remove_block_ids=tuple(set(existing.supporting_block_ids) - set(candidate.supporting_block_ids))
                if existing.needs_rebuild else (),
                remove_structure_ids=tuple(set(existing.supporting_structure_ids) - set(candidate.supporting_structure_ids))
                if existing.needs_rebuild else (),
                add_block_ids=candidate.supporting_block_ids,
                add_structure_ids=candidate.supporting_structure_ids,
                selected_support=selected_support,
            )
            if existing.candidate_content != content:
                self.worktrees.update_candidate(
                    existing.worktree_id,
                    candidate_content=content,
                    interpretation_trace=interpretation.model_trace,
                )
            if existing.needs_rebuild:
                self.worktrees.clear_needs_rebuild(existing.worktree_id)
        self.worktrees.record_support(
            existing.worktree_id,
            snapshot_id=snapshot.snapshot_id,
            support_identity=support_identity,
        )
        return self.promoter.evaluate(existing.worktree_id, interpretation=interpretation)

    @staticmethod
    def _selected_support(
        interpretation: BoundedInterpretation,
        blocks: tuple[SemanticBlock, ...],
    ) -> tuple[AuthorizedSelectedSupport, ...]:
        requested_ids = interpretation.supporting_block_ids
        authorized = {block.block_id: block for block in blocks}
        supplied = interpretation.selected_support
        if supplied:
            if tuple(item.block_id for item in supplied) != requested_ids:
                raise ValueError("bounded interpreter selected states out of alignment with block IDs")
            selected = supplied
        else:
            selected_list: list[AuthorizedSelectedSupport] = []
            for block_id in requested_ids:
                block = authorized.get(block_id)
                if block is None or block.state_id is None:
                    raise ValueError("bounded interpreter selected a block outside the authorized package")
                selected_list.append(AuthorizedSelectedSupport(block_id=block_id, state_id=block.state_id))
            selected = tuple(selected_list)
        for item in selected:
            authorized_block = authorized.get(item.block_id)
            if authorized_block is None or authorized_block.state_id != item.state_id:
                raise ValueError("bounded interpreter selected a state outside the authorized package")
        if not selected:
            raise ValueError("a proposed interpretation must select at least one authorized state")
        return selected

    @staticmethod
    def _support_identity(
        candidate: HigherOrderCandidate,
        snapshot: StructureSnapshot,
        _diff: StructureDiff | None,
        selected_support: tuple[AuthorizedSelectedSupport, ...] = (),
    ) -> str:
        structures = [
            {
                "id": item.structure_id,
                "members": tuple(sorted(item.member_block_ids)),
            }
            for item in snapshot.structures
            if item.structure_id in candidate.supporting_structure_ids
        ]
        payload = {
            "relation": candidate.relation_type,
            "structures": structures,
            "blocks": tuple(
                (item.block_id, item.state_id, next((block.content for block in snapshot.block_states if block.block_id == item.block_id), ""))
                for item in selected_support
            ),
        }
        return "support_" + hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:24]

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
        previous = max(
            (snapshot for snapshot in self.discovery.snapshots.all_snapshots() if snapshot.cutoff < latest),
            key=lambda snapshot: snapshot.cutoff,
            default=None,
        )
        corrected_snapshot = self.discovery.create_snapshot(latest)
        corrected_diff = self.discovery.diff(previous, corrected_snapshot) if previous else None
        for candidate in self.discovery.higher_order_candidates(corrected_snapshot):
            self._evaluate_candidate(candidate, corrected_snapshot, corrected_diff)
        return result

    def close(self) -> None:
        self.discovery.close()
        self.worktrees.close()
        self.baselines.close()
        self.memory.close()
