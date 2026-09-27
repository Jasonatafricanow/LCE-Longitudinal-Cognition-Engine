"""Source-store-independent longitudinal projection pipeline.

Concrete standalone source storage is composed in lce.runtime. This module owns
LCE-derived projection state and consumes an injected source/working substrate.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Sequence
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
from lce.structure.frontier import (
    FrontierCandidateDiscovery,
    FrontierDiscoveryConfig,
)


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


@dataclass(frozen=True, slots=True)
class _CandidateEvaluation:
    handled: bool
    promotion: ConsolidationResult | None = None


class LceProjectionCore:
    """Source-store-independent cognition pipeline.

    The core never constructs a factual/source store. A caller must inject the
    substrate that supplies source validity plus rebuildable semantic-block and
    projection state. This keeps concrete standalone persistence outside the
    cognition engine and lets embedded runtimes provide their own adapter.
    """

    def __init__(
        self,
        root: Path | str,
        *,
        memory: ReferenceMemorySubstratePort,
        provider: SemanticDecisionProvider | None = None,
        policy: PromotionPolicy | None = None,
        lineage_id: str = "default",
        structure_config: StructureConfig | None = None,
        frontier_config: FrontierDiscoveryConfig | None = None,
        interpreter: BoundedInterpreter | None = None,
        block_embedder: Callable[
            [SemanticBlock], tuple[float, ...]
        ] | None = None,
        block_embedding_version: str = "lce-vector-v1",
        close_memory: bool = False,
    ) -> None:
        if type(close_memory) is not bool:
            raise TypeError("close_memory must be bool")
        if (
            not isinstance(block_embedding_version, str)
            or not block_embedding_version.strip()
        ):
            raise ValueError("block_embedding_version must be nonempty")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.memory = memory
        self._close_memory = close_memory
        self.baselines = SqliteBaselineStore(self.root / "baselines")
        self.worktrees = CognitionWorktreeStore(self.root / "worktrees")
        self.discovery = SnapshotStructureDiscovery(
            self.memory,
            self.root / "structures",
            config=structure_config,
        )
        self.frontier = FrontierCandidateDiscovery(
            baselines=self.baselines,
            worktrees=self.worktrees,
            config=frontier_config,
        )
        self.compiler = SemanticCompiler(
            self.memory,
            provider,
            lineage_id=lineage_id,
        )
        self.policy = policy or ConservativePromotionPolicy()
        self.interpreter = interpreter or RuleBasedBoundedInterpreter()
        self._block_embedder = (
            block_embedder or deterministic_block_embedding
        )
        self._block_embedding_version = block_embedding_version.strip()
        self.promoter = UnderstandingPromoter(
            memory=self.memory,
            baseline_store=self.baselines,
            worktree_store=self.worktrees,
            policy=self.policy,
        )
        self.read_api = AcceptedUnderstandingReadAPI(
            memory=self.memory,
            baseline_store=self.baselines,
        )

    def process(
        self, material: RawEvidence, *, mode: str = "nearline"
    ) -> ProcessResult:
        if mode not in {"batch", "nearline"}:
            raise ValueError("mode must be batch or nearline")
        compiler_result = self.compiler.process(material)
        stage = self.memory.get_pipeline_stage(material.evidence_id)
        if compiler_result.replayed and stage == "complete":
            return self._completed_replay_result(
                material,
                compiler_result,
            )
        if stage not in {
            "vector-ready",
            "snapshot/discovery-evaluated",
            "worktree-support-evaluated",
            "promotion-evaluated",
            "complete",
        }:
            self.memory.rebuild_vector_index(
                self._block_embedder,
                index_version=self._block_embedding_version,
            )
            self.memory.mark_pipeline_stage(
                material.evidence_id,
                "vector-ready",
                fingerprint=self._block_embedding_version,
            )
        previous = max(
            (
                snapshot
                for snapshot in self.discovery.snapshots.all_snapshots()
                if snapshot.cutoff < material.occurred_at
            ),
            key=lambda snapshot: snapshot.cutoff,
            default=None,
        )
        snapshot = self.discovery.create_snapshot(material.occurred_at)
        diff = (
            self.discovery.diff(previous, snapshot)
            if previous
            else None
        )

        frontier_candidates = self.frontier.candidates(
            snapshot,
            current_block_ids=compiler_result.block_ids,
        )
        structure_candidates = self.discovery.higher_order_candidates(
            snapshot
        )
        candidates = (*frontier_candidates, *structure_candidates)
        promotions: list[ConsolidationResult] = []

        self.memory.mark_pipeline_stage(
            material.evidence_id,
            "snapshot/discovery-evaluated",
            fingerprint=snapshot.snapshot_id,
        )

        frontier_handled = False
        for candidate in frontier_candidates:
            outcome = self._evaluate_candidate(
                candidate,
                snapshot,
                diff,
                replayed=compiler_result.replayed,
                processing_input_id=material.evidence_id,
            )
            frontier_handled = frontier_handled or outcome.handled
            if outcome.promotion is not None:
                promotions.append(outcome.promotion)

        # Frontier is the primary incremental path.  Legacy 06R remains the
        # discovery fallback when no existing cognition can absorb the input.
        if not frontier_handled:
            for candidate in structure_candidates:
                outcome = self._evaluate_candidate(
                    candidate,
                    snapshot,
                    diff,
                    replayed=compiler_result.replayed,
                    processing_input_id=material.evidence_id,
                )
                if outcome.promotion is not None:
                    promotions.append(outcome.promotion)

        self.memory.mark_pipeline_stage(
            material.evidence_id,
            "worktree-support-evaluated",
            fingerprint=snapshot.snapshot_id,
        )
        self.memory.mark_pipeline_stage(
            material.evidence_id,
            "promotion-evaluated",
            fingerprint=snapshot.snapshot_id,
        )
        self.memory.mark_pipeline_stage(
            material.evidence_id,
            "complete",
            fingerprint=snapshot.snapshot_id,
        )
        return ProcessResult(
            compiler_result,
            snapshot,
            diff,
            candidates,
            tuple(promotions),
        )

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

    @staticmethod
    def _frontier_refs(
        candidate: HigherOrderCandidate,
    ) -> tuple[str, ...]:
        raw = candidate.metadata.get("frontier_refs", ())
        if not isinstance(raw, (list, tuple)):
            return ()
        return tuple(
            dict.fromkeys(
                item
                for item in raw
                if isinstance(item, str) and item.strip()
            )
        )

    @classmethod
    def _candidate_region_id(
        cls,
        candidate: HigherOrderCandidate,
    ) -> str:
        if candidate.relation_type == "frontier_absorption":
            target = candidate.metadata.get("target_region_id")
            if not isinstance(target, str) or not target.strip():
                raise ValueError(
                    "frontier absorption requires target_region_id"
                )
            return target
        if candidate.relation_type == "frontier_boundary":
            regions = candidate.metadata.get(
                "frontier_region_ids",
                (),
            )
            if not isinstance(regions, (list, tuple)):
                raise ValueError(
                    "frontier boundary requires frontier_region_ids"
                )
            region_ids = tuple(
                sorted(
                    {
                        item
                        for item in regions
                        if isinstance(item, str) and item.strip()
                    }
                )
            )
            if len(region_ids) < 2:
                raise ValueError(
                    "frontier boundary requires at least two regions"
                )
            digest = hashlib.sha256(
                json.dumps(region_ids).encode()
            ).hexdigest()[:20]
            return f"frontier-boundary:{digest}"
        return "higher-order:" + ":".join(
            candidate.supporting_structure_ids
        )

    def _evaluate_candidate(
        self,
        candidate: HigherOrderCandidate,
        snapshot: StructureSnapshot,
        diff: StructureDiff | None,
        *,
        replayed: bool = False,
        processing_input_id: str | None = None,
    ) -> _CandidateEvaluation:
        region_id = self._candidate_region_id(candidate)
        head = self.baselines.get_head(region_id)
        frontier_refs = self._frontier_refs(candidate)
        frontier_candidate = candidate.relation_type.startswith(
            "frontier_"
        )

        # A replay after compilation may be resuming a partially completed
        # input. Once this input has a durable worktree effect, that persisted
        # effect is authoritative for recovery.
        if replayed and processing_input_id is not None:
            durable = self.worktrees.find_by_region_and_input(
                region_id,
                processing_input_id,
            )
            if durable is not None:
                if durable.status != "OPEN":
                    return _CandidateEvaluation(handled=True)
                reconciled = self.promoter.reconcile_committed(
                    durable.worktree_id
                )
                if reconciled is not None:
                    return _CandidateEvaluation(
                        handled=True,
                        promotion=reconciled,
                    )
                support_identity = self._support_identity(
                    candidate,
                    snapshot,
                    diff,
                    durable.selected_support,
                )
                self.worktrees.record_support(
                    durable.worktree_id,
                    snapshot_id=snapshot.snapshot_id,
                    support_identity=support_identity,
                    processing_input_id=processing_input_id,
                )
                return _CandidateEvaluation(
                    handled=True,
                    promotion=self.promoter.evaluate(
                        durable.worktree_id
                    ),
                )

        existing = self.worktrees.find_open_by_region(region_id)
        if existing is not None:
            reconciled = self.promoter.reconcile_committed(
                existing.worktree_id
            )
            if reconciled is not None:
                return _CandidateEvaluation(
                    handled=True,
                    promotion=reconciled,
                )

        structures = tuple(
            observation
            for observation in snapshot.structures
            if observation.structure_id
            in candidate.supporting_structure_ids
        )
        blocks_by_id = {
            block.block_id: block
            for block in snapshot.block_states
        }
        blocks = tuple(
            blocks_by_id[block_id]
            for block_id in candidate.supporting_block_ids
            if block_id in blocks_by_id
        )
        source_refs = tuple(
            sorted(
                {
                    source
                    for block in blocks
                    for source in block.raw_evidence_ids
                }
            )
        )
        package = BoundedInterpretationPackage(
            candidate=candidate,
            structures=structures,
            semantic_blocks=blocks,
            authorized_source_refs=source_refs,
            previous_baseline=head,
            context={
                "frontier_refs": frontier_refs,
                "supplier": candidate.metadata.get("supplier"),
            },
        )
        interpretation = self.interpreter.interpret(package)
        if (
            interpretation.status != "PROPOSED"
            or interpretation.content is None
        ):
            return _CandidateEvaluation(handled=False)

        content = interpretation.content
        authorized_blocks = set(candidate.supporting_block_ids)
        if not set(
            interpretation.supporting_block_ids
        ).issubset(authorized_blocks):
            raise ValueError(
                "bounded interpreter returned an unauthorized Semantic Block"
            )
        selected_support = self._selected_support(
            interpretation,
            blocks,
        )
        interpretation = replace(
            interpretation,
            supporting_block_ids=tuple(
                item.block_id for item in selected_support
            ),
            selected_support=selected_support,
        )

        if head is not None and head.content.strip() == content.strip():
            return _CandidateEvaluation(handled=True)

        support_identity = self._support_identity(
            candidate,
            snapshot,
            diff,
            selected_support,
        )
        if existing is None:
            existing = self.worktrees.create(
                region_id=region_id,
                candidate_content=content,
                supporting_block_ids=candidate.supporting_block_ids,
                supporting_structure_ids=(
                    candidate.supporting_structure_ids
                ),
                supporting_frontier_refs=frontier_refs,
                base_baseline=head,
                interpretation_trace=interpretation.model_trace,
                selected_support=selected_support,
                processing_input_id=processing_input_id,
                support_kind=(
                    "frontier"
                    if frontier_candidate
                    else "semantic_block"
                ),
            )
        else:
            self.worktrees.update_support(
                existing.worktree_id,
                remove_block_ids=(
                    tuple(
                        set(existing.supporting_block_ids)
                        - set(candidate.supporting_block_ids)
                    )
                    if existing.needs_rebuild
                    else ()
                ),
                remove_structure_ids=(
                    tuple(
                        set(existing.supporting_structure_ids)
                        - set(candidate.supporting_structure_ids)
                    )
                    if existing.needs_rebuild
                    else ()
                ),
                remove_frontier_refs=(
                    tuple(
                        set(existing.supporting_frontier_refs)
                        - set(frontier_refs)
                    )
                    if existing.needs_rebuild
                    else ()
                ),
                add_block_ids=candidate.supporting_block_ids,
                add_structure_ids=candidate.supporting_structure_ids,
                add_frontier_refs=frontier_refs,
                selected_support=selected_support,
                processing_input_id=processing_input_id,
            )
            if existing.candidate_content != content:
                self.worktrees.update_candidate(
                    existing.worktree_id,
                    candidate_content=content,
                    interpretation_trace=interpretation.model_trace,
                )
            if existing.needs_rebuild:
                self.worktrees.clear_needs_rebuild(
                    existing.worktree_id
                )

        self.worktrees.record_support(
            existing.worktree_id,
            snapshot_id=snapshot.snapshot_id,
            support_identity=support_identity,
            processing_input_id=processing_input_id,
        )
        return _CandidateEvaluation(
            handled=True,
            promotion=self.promoter.evaluate(
                existing.worktree_id,
                interpretation=interpretation,
            ),
        )

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
            # The reference interpreter supplies block IDs but no explicit
            # selection ordering.  Use newest-first for that derived order so
            # the selected support reflects the current longitudinal edge;
            # an interpreter that supplies explicit states/order remains
            # authoritative below.
            selected_list = []
            ordered_blocks = sorted(
                (authorized[block_id] for block_id in requested_ids if block_id in authorized),
                key=lambda block: (block.occurred_end, block.block_id),
                reverse=True,
            )
            for block in ordered_blocks:
                block_id = block.block_id
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

    def _support_identity(
        self,
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
            "frontier_refs": self._frontier_refs(candidate),
            "structures": structures,
            "blocks": tuple(sorted(
                # State IDs retain exact immutable provenance, but a newer
                # state with identical semantic/structural meaning is not
                # new cognition support (for example, a pure recap). Canonical
                # block order here must not change selected provenance order.
                (item.block_id, next((block.content for block in snapshot.block_states if block.block_id == item.block_id), ""))
                for item in selected_support
            )),
        }
        return "support_" + hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:24]

    def query(self, current_context: str | dict[str, object] | None) -> tuple[UnderstandingView, ...]:
        return self.read_api.query(current_context)

    def invalidate_and_rebuild(
        self, evidence_id: str, *, cutoff: datetime | None = None
    ) -> InvalidationResult:
        """Standalone path: mutate the owned source, then rebuild projections."""
        invalidator = DependencyInvalidator(
            self.memory, self.discovery, self.worktrees, self.baselines
        )
        result = invalidator.invalidate(evidence_id)
        self._rebuild_after_source_change(cutoff=cutoff)
        return result

    def source_changed_and_rebuild(
        self, evidence_id: str, *, cutoff: datetime | None = None
    ) -> InvalidationResult:
        """Embedded path: source owner already changed canonical lifecycle."""
        invalidator = DependencyInvalidator(
            self.memory, self.discovery, self.worktrees, self.baselines
        )
        result = invalidator.source_changed(evidence_id)
        self._rebuild_after_source_change(cutoff=cutoff)
        return result

    def _rebuild_after_source_change(
        self, *, cutoff: datetime | None
    ) -> None:
        self.memory.rebuild_vector_index(
            self._block_embedder,
            index_version=self._block_embedding_version,
        )
        latest = cutoff or max(
            (
                snapshot.cutoff
                for snapshot in self.discovery.snapshots.all_snapshots()
            ),
            default=datetime.now(UTC),
        )
        previous = max(
            (
                snapshot
                for snapshot in self.discovery.snapshots.all_snapshots()
                if snapshot.cutoff < latest
            ),
            key=lambda snapshot: snapshot.cutoff,
            default=None,
        )
        corrected_snapshot = self.discovery.create_snapshot(latest)
        corrected_diff = (
            self.discovery.diff(previous, corrected_snapshot)
            if previous
            else None
        )
        for candidate in self.discovery.higher_order_candidates(
            corrected_snapshot
        ):
            self._evaluate_candidate(
                candidate, corrected_snapshot, corrected_diff
            )

    def close(self) -> None:
        self.discovery.close()
        self.worktrees.close()
        self.baselines.close()
        if self._close_memory:
            self.memory.close()
