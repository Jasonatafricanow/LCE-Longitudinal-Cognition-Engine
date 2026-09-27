from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from lce.cognition.worktree import CognitionWorktreeStore
from lce.contracts.baseline import Baseline, compute_content_hash
from lce.reference_memory.contracts import SemanticBlock
from lce.store.sqlite_store import SqliteBaselineStore
from lce.structure.contracts import StructureConfig, StructureSnapshot
from lce.structure.frontier import (
    FrontierCandidateDiscovery,
    FrontierDiscoveryConfig,
)

BASE = datetime(2026, 1, 1, tzinfo=UTC)


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
    discovery = FrontierCandidateDiscovery(
        baselines=baselines,
        worktrees=worktrees,
        config=FrontierDiscoveryConfig(enabled=False),
    )
    current = _block("current", 0, "Anything")
    assert discovery.candidates(
        _snapshot((current,), {"current": (1.0, 0.0)}),
        current_block_ids=("current",),
    ) == ()
    baselines.close()
    worktrees.close()
