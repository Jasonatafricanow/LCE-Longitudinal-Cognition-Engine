from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from lce.cognition.worktree import CognitionWorktreeStore
from lce.contracts.baseline import Baseline, compute_content_hash
from lce.reference_memory.contracts import (
    AuthorizedSelectedSupport,
    RawEvidence,
    SemanticBlock,
    VectorProjection,
)
from lce.store.sqlite_store import SqliteBaselineStore
from lce.structure.contracts import StructureConfig, StructureSnapshot
from lce.structure.frontier import (
    FrontierCandidateDiscovery,
    FrontierDiscoveryConfig,
)

BASE = datetime(2026, 1, 1, tzinfo=UTC)


class _Memory:
    def __init__(
        self,
        blocks: tuple[SemanticBlock, ...],
        vectors: dict[tuple[str, str | None], tuple[float, ...]],
    ) -> None:
        self._states = {
            block.state_id: block
            for block in blocks
            if block.state_id is not None
        }
        self._vectors = vectors
        self._evidence = {
            evidence_id: RawEvidence(
                evidence_id=evidence_id,
                content=block.content,
                occurred_at=block.occurred_end,
                provenance={"source": "test", "canonical": True},
            )
            for block in blocks
            for evidence_id in block.raw_evidence_ids
        }

    def get_semantic_block_state(self, state_id: str) -> SemanticBlock:
        block = self._states.get(state_id)
        if block is None:
            raise KeyError(state_id)
        return block

    def get_evidence(self, evidence_id: str) -> RawEvidence:
        item = self._evidence.get(evidence_id)
        if item is None:
            raise KeyError(evidence_id)
        return item

    def get_vector(
        self,
        block_id: str,
        *,
        state_id: str | None = None,
    ) -> VectorProjection:
        key = (block_id, state_id)
        if key not in self._vectors:
            raise KeyError(key)
        return VectorProjection(
            block_id=block_id,
            values=self._vectors[key],
            index_version="test",
        )


def _memory(
    blocks: tuple[SemanticBlock, ...],
    vectors: dict[str, tuple[float, ...]],
) -> _Memory:
    return _Memory(
        blocks,
        {
            (block.block_id, block.state_id): vectors[block.block_id]
            for block in blocks
        },
    )


def _block(
    block_id: str,
    day: int,
    content: str,
) -> SemanticBlock:
    when = BASE + timedelta(days=day)
    return SemanticBlock(
        block_id=block_id,
        content=content,
        raw_evidence_ids=(f"E-{block_id}",),
        occurred_start=when,
        occurred_end=when,
        compiler_version="test",
        lineage_id="lineage",
        metadata={"subject": block_id},
        state_id=f"state-{block_id}",
    )


def _snapshot(
    blocks: tuple[SemanticBlock, ...],
    vectors: dict[str, tuple[float, ...]],
) -> StructureSnapshot:
    cutoff = max(block.occurred_end for block in blocks)
    return StructureSnapshot(
        snapshot_id="snap-frontier",
        timestamp=cutoff,
        cutoff=cutoff,
        visible_block_ids=tuple(block.block_id for block in blocks),
        structures=(),
        algorithm_version="test",
        config=StructureConfig(),
        block_states=blocks,
        vectors=vectors,
    )


def _save_baseline(
    store: SqliteBaselineStore,
    *,
    region_id: str,
    baseline_id: str,
    content: str,
    block_ids: tuple[str, ...],
    selected_support: tuple[AuthorizedSelectedSupport, ...] = (),
) -> None:
    store.save_revision(
        Baseline(
            baseline_id=baseline_id,
            region_id=region_id,
            revision_number=1,
            content=content,
            content_hash=compute_content_hash(content),
            supporting_memory_ids=block_ids,
            created_at=BASE,
            supporting_state_ids=tuple(
                item.state_id for item in selected_support
            ),
            selected_support=selected_support,
        )
    )


def test_frontier_absorption_works_without_structure_candidate(
    tmp_path: Path,
) -> None:
    baselines = SqliteBaselineStore(tmp_path / "baselines")
    worktrees = CognitionWorktreeStore(tmp_path / "worktrees")
    _save_baseline(
        baselines,
        region_id="career",
        baseline_id="b-career",
        content="User is actively considering a job change.",
        block_ids=("old",),
    )
    old = _block("old", 0, "Considering a job change.")
    current = _block("current", 5, "Started applying for new jobs.")
    snapshot = _snapshot(
        (old, current),
        {
            "old": (1.0, 0.0),
            "current": (0.98, 0.05),
        },
    )

    discovery = FrontierCandidateDiscovery(
        memory=_memory(
            (old, current),
            {
                "old": (1.0, 0.0),
                "current": (0.98, 0.05),
            },
        ),
        baselines=baselines,
        worktrees=worktrees,
    )
    candidates = discovery.candidates(
        snapshot,
        current_block_ids=("current",),
    )

    absorption = tuple(
        item
        for item in candidates
        if item.relation_type == "frontier_absorption"
    )
    assert len(absorption) == 1
    assert absorption[0].metadata["target_region_id"] == "career"
    assert absorption[0].supporting_structure_ids == ()
    assert set(absorption[0].supporting_block_ids) == {
        "old",
        "current",
    }
    baselines.close()
    worktrees.close()


def test_branch_rescue_uses_a_matching_support_even_when_centroid_is_weak(
    tmp_path: Path,
) -> None:
    baselines = SqliteBaselineStore(tmp_path / "baselines")
    worktrees = CognitionWorktreeStore(tmp_path / "worktrees")
    _save_baseline(
        baselines,
        region_id="mixed",
        baseline_id="b-mixed",
        content="Long running mixed theme.",
        block_ids=("left", "right"),
    )
    left = _block("left", 0, "Strong left branch.")
    right = _block("right", 0, "Unrelated right branch.")
    current = _block("current", 3, "Left branch continues.")
    snapshot = _snapshot(
        (left, right, current),
        {
            "left": (1.0, 0.0),
            "right": (-1.0, 0.0),
            "current": (0.99, 0.01),
        },
    )
    discovery = FrontierCandidateDiscovery(
        memory=_memory(
            (left, right, current),
            {
                "left": (1.0, 0.0),
                "right": (-1.0, 0.0),
                "current": (0.99, 0.01),
            },
        ),
        baselines=baselines,
        worktrees=worktrees,
        config=FrontierDiscoveryConfig(
            min_absorption_score=0.95,
            branch_rescue_similarity=0.90,
        ),
    )

    candidates = discovery.candidates(
        snapshot,
        current_block_ids=("current",),
    )
    absorption = next(
        item
        for item in candidates
        if item.relation_type == "frontier_absorption"
    )
    score = absorption.metadata["scores"][0]
    assert score["branch_rescue"] is True
    assert score["support_similarity"] >= 0.90
    baselines.close()
    worktrees.close()


def test_temporal_prior_is_soft_not_a_hard_cutoff(
    tmp_path: Path,
) -> None:
    baselines = SqliteBaselineStore(tmp_path / "baselines")
    worktrees = CognitionWorktreeStore(tmp_path / "worktrees")
    _save_baseline(
        baselines,
        region_id="old-theme",
        baseline_id="b-old",
        content="A durable preference.",
        block_ids=("old",),
    )
    old = _block("old", 0, "Durable preference.")
    current = _block(
        "current",
        720,
        "Durable preference is still present.",
    )
    snapshot = _snapshot(
        (old, current),
        {
            "old": (1.0, 0.0),
            "current": (1.0, 0.0),
        },
    )
    discovery = FrontierCandidateDiscovery(
        memory=_memory(
            (old, current),
            {
                "old": (1.0, 0.0),
                "current": (1.0, 0.0),
            },
        ),
        baselines=baselines,
        worktrees=worktrees,
        config=FrontierDiscoveryConfig(
            temporal_half_life_days=30,
            temporal_floor=0.20,
        ),
    )

    candidates = discovery.candidates(
        snapshot,
        current_block_ids=("current",),
    )
    absorption = next(
        item
        for item in candidates
        if item.relation_type == "frontier_absorption"
    )
    score = absorption.metadata["scores"][0]
    assert 0.20 <= score["temporal_prior"] < 0.30
    assert score["branch_rescue"] is True
    baselines.close()
    worktrees.close()


def test_additive_boundary_rescue_combines_two_moderate_frontiers(
    tmp_path: Path,
) -> None:
    baselines = SqliteBaselineStore(tmp_path / "baselines")
    worktrees = CognitionWorktreeStore(tmp_path / "worktrees")
    _save_baseline(
        baselines,
        region_id="a",
        baseline_id="b-a",
        content="Theme A",
        block_ids=("a",),
    )
    _save_baseline(
        baselines,
        region_id="b",
        baseline_id="b-b",
        content="Theme B",
        block_ids=("b",),
    )
    a = _block("a", 0, "Theme A")
    b = _block("b", 0, "Theme B")
    current = _block("current", 2, "Boundary evidence")
    snapshot = _snapshot(
        (a, b, current),
        {
            "a": (1.0, 0.0),
            "b": (0.0, 1.0),
            "current": (0.71, 0.71),
        },
    )
    discovery = FrontierCandidateDiscovery(
        memory=_memory(
            (a, b, current),
            {
                "a": (1.0, 0.0),
                "b": (0.0, 1.0),
                "current": (0.71, 0.71),
            },
        ),
        baselines=baselines,
        worktrees=worktrees,
        config=FrontierDiscoveryConfig(
            min_absorption_score=0.90,
            branch_rescue_similarity=0.95,
            boundary_min_component=0.45,
            boundary_sum_threshold=1.00,
        ),
    )

    candidates = discovery.candidates(
        snapshot,
        current_block_ids=("current",),
    )
    assert not any(
        item.relation_type == "frontier_absorption"
        for item in candidates
    )
    boundary = next(
        item
        for item in candidates
        if item.relation_type == "frontier_boundary"
    )
    assert set(boundary.metadata["frontier_region_ids"]) == {"a", "b"}
    assert set(boundary.supporting_block_ids) == {"a", "b", "current"}
    baselines.close()
    worktrees.close()


def test_frontier_supplier_can_be_disabled_for_ablation(
    tmp_path: Path,
) -> None:
    baselines = SqliteBaselineStore(tmp_path / "baselines")
    worktrees = CognitionWorktreeStore(tmp_path / "worktrees")
    current = _block("current", 0, "Anything")
    discovery = FrontierCandidateDiscovery(
        memory=_memory(
            (current,),
            {"current": (1.0, 0.0)},
        ),
        baselines=baselines,
        worktrees=worktrees,
        config=FrontierDiscoveryConfig(enabled=False),
    )
    assert discovery.candidates(
        _snapshot((current,), {"current": (1.0, 0.0)}),
        current_block_ids=("current",),
    ) == ()
    baselines.close()
    worktrees.close()


def test_frontier_scoring_uses_frozen_baseline_state_not_latest_block(
    tmp_path: Path,
) -> None:
    baselines = SqliteBaselineStore(tmp_path / "baselines")
    worktrees = CognitionWorktreeStore(tmp_path / "worktrees")
    old_state = _block("same", 0, "Old accepted direction.")
    current_state = SemanticBlock(
        block_id="same",
        content="Completely reversed direction.",
        raw_evidence_ids=("E-same", "E-current"),
        occurred_start=old_state.occurred_start,
        occurred_end=BASE + timedelta(days=5),
        compiler_version="test",
        lineage_id="lineage",
        metadata={"subject": "same"},
        state_id="state-same-current",
        state_version=2,
    )
    _save_baseline(
        baselines,
        region_id="same-region",
        baseline_id="b-old",
        content="Old accepted direction.",
        block_ids=("same",),
        selected_support=(
            AuthorizedSelectedSupport(
                block_id="same",
                state_id=old_state.state_id or "",
            ),
        ),
    )
    memory = _Memory(
        (old_state, current_state),
        {
            ("same", old_state.state_id): (1.0, 0.0),
            ("same", current_state.state_id): (0.0, 1.0),
        },
    )
    snapshot = _snapshot(
        (current_state,),
        {"same": (0.0, 1.0)},
    )
    discovery = FrontierCandidateDiscovery(
        memory=memory,
        baselines=baselines,
        worktrees=worktrees,
        config=FrontierDiscoveryConfig(
            min_absorption_score=0.90,
            branch_rescue_similarity=0.95,
            boundary_sum_threshold=2.0,
        ),
    )

    candidates = discovery.candidates(
        snapshot,
        current_block_ids=("same",),
    )
    assert not any(
        item.relation_type == "frontier_absorption"
        for item in candidates
    )
    baselines.close()
    worktrees.close()


def test_exact_frontier_state_replay_does_not_self_support(
    tmp_path: Path,
) -> None:
    baselines = SqliteBaselineStore(tmp_path / "baselines")
    worktrees = CognitionWorktreeStore(tmp_path / "worktrees")
    block = _block("same", 0, "Stable accepted state.")
    _save_baseline(
        baselines,
        region_id="stable",
        baseline_id="b-stable",
        content="Stable accepted state.",
        block_ids=("same",),
        selected_support=(
            AuthorizedSelectedSupport(
                block_id="same",
                state_id=block.state_id or "",
            ),
        ),
    )
    memory = _memory(
        (block,),
        {"same": (1.0, 0.0)},
    )
    discovery = FrontierCandidateDiscovery(
        memory=memory,
        baselines=baselines,
        worktrees=worktrees,
    )
    snapshot = _snapshot(
        (block,),
        {"same": (1.0, 0.0)},
    )

    assert discovery.candidates(
        snapshot,
        current_block_ids=("same",),
    ) == ()
    baselines.close()
    worktrees.close()


def test_frontier_candidate_identity_ignores_baseline_instance_identity(
    tmp_path: Path,
) -> None:
    old = _block("old", 0, "Career direction.")
    current = _block("current", 3, "Career applications.")
    memory = _memory(
        (old, current),
        {
            "old": (1.0, 0.0),
            "current": (0.99, 0.02),
        },
    )
    snapshot = _snapshot(
        (old, current),
        {
            "old": (1.0, 0.0),
            "current": (0.99, 0.02),
        },
    )

    first_baselines = SqliteBaselineStore(tmp_path / "first-baselines")
    first_worktrees = CognitionWorktreeStore(tmp_path / "first-worktrees")
    _save_baseline(
        first_baselines,
        region_id="career",
        baseline_id="baseline-instance-a",
        content="Career direction.",
        block_ids=("old",),
        selected_support=(
            AuthorizedSelectedSupport(
                block_id="old",
                state_id=old.state_id or "",
            ),
        ),
    )
    first = FrontierCandidateDiscovery(
        memory=memory,
        baselines=first_baselines,
        worktrees=first_worktrees,
    ).candidates(
        snapshot,
        current_block_ids=("current",),
    )

    second_baselines = SqliteBaselineStore(tmp_path / "second-baselines")
    second_worktrees = CognitionWorktreeStore(tmp_path / "second-worktrees")
    _save_baseline(
        second_baselines,
        region_id="career",
        baseline_id="baseline-instance-b",
        content="Career direction.",
        block_ids=("old",),
        selected_support=(
            AuthorizedSelectedSupport(
                block_id="old",
                state_id=old.state_id or "",
            ),
        ),
    )
    second = FrontierCandidateDiscovery(
        memory=memory,
        baselines=second_baselines,
        worktrees=second_worktrees,
    ).candidates(
        snapshot,
        current_block_ids=("current",),
    )

    assert first
    assert second
    assert first[0].candidate_id == second[0].candidate_id
    assert first[0].metadata["frontier_refs"] == ("region:career",)
    assert second[0].metadata["frontier_refs"] == ("region:career",)

    first_baselines.close()
    first_worktrees.close()
    second_baselines.close()
    second_worktrees.close()
