from __future__ import annotations

from datetime import UTC, datetime

from lce.cognition.worktree import CognitionWorktreeStore
from lce.contracts.baseline import Baseline, compute_content_hash
from lce.store.sqlite_store import SqliteBaselineStore


def baseline(baseline_id: str, *, content: str = "accepted", revision: int = 1, previous: str | None = None) -> Baseline:
    return Baseline(
        baseline_id=baseline_id,
        region_id="region",
        revision_number=revision,
        content=content,
        content_hash=compute_content_hash(content),
        supporting_memory_ids=("SB1",),
        created_at=datetime(2026, 6, 1, tzinfo=UTC),
        previous_baseline_id=previous,
        model_trace={"model": "test"},
    )


def test_open_worktree_does_not_change_head_and_persists_support_growth_and_loss(tmp_path) -> None:
    baseline_store = SqliteBaselineStore(tmp_path / "baselines")
    baseline_store.save_revision(baseline("base-1"))
    worktrees = CognitionWorktreeStore(tmp_path / "worktrees")
    item = worktrees.create(
        region_id="region",
        candidate_content="candidate understanding",
        supporting_block_ids=("SB1",),
        supporting_structure_ids=("S1",),
        base_baseline=baseline_store.get_head("region"),
    )
    assert baseline_store.get_head("region").baseline_id == "base-1"
    worktrees.update_support(item.worktree_id, add_block_ids=("SB2",), add_structure_ids=("S2",))
    worktrees.update_support(item.worktree_id, remove_block_ids=("SB1",), remove_structure_ids=("S1",))
    worktrees.close()

    reopened = CognitionWorktreeStore(tmp_path / "worktrees")
    current = reopened.get(item.worktree_id)
    assert current.status == "OPEN"
    assert current.supporting_block_ids == ("SB2",)
    assert current.supporting_structure_ids == ("S2",)
    assert current.base_baseline_id == "base-1"
    assert current.base_revision == 1
    reopened.close()
    baseline_store.close()


def test_drop_changes_only_the_worktree(tmp_path) -> None:
    worktrees = CognitionWorktreeStore(tmp_path / "worktrees")
    item = worktrees.create(
        region_id="region",
        candidate_content="candidate",
        supporting_block_ids=("SB1",),
        supporting_structure_ids=("S1",),
        base_baseline=None,
    )
    dropped = worktrees.set_status(item.worktree_id, "DROPPED")
    assert dropped.status == "DROPPED"
    assert worktrees.get(item.worktree_id).status == "DROPPED"
    worktrees.close()
