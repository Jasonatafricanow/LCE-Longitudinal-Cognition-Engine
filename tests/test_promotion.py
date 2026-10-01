from __future__ import annotations

from datetime import UTC, datetime

from lce.cognition.promotion import ConservativePromotionPolicy, UnderstandingPromoter
from lce.cognition.worktree import CognitionWorktreeStore
from lce.contracts.baseline import Baseline, compute_content_hash
from lce.reference_memory.contracts import (
    AuthorizedSelectedSupport,
    RawEvidence,
    SemanticBlock,
)
from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.store.sqlite_store import SqliteBaselineStore


def setup_memory(tmp_path) -> ReferenceMemoryStore:
    store = ReferenceMemoryStore(tmp_path / "memory")
    for index in (1, 2):
        evidence_id = f"E{index}"
        block_id = f"SB{index}"
        when = datetime(2026, 6, index, tzinfo=UTC)
        store.add_evidence(
            RawEvidence(
                evidence_id=evidence_id,
                content=f"evidence {index}",
                occurred_at=when,
                ordering_key=f"{index:04d}:{evidence_id}",
                provenance={"source": "synthetic", "canonical": True},
            )
        )
        store.put_semantic_block(
            SemanticBlock(
                block_id=block_id,
                content=f"block {index}",
                raw_evidence_ids=(evidence_id,),
                occurred_start=when,
                occurred_end=when,
                compiler_version="test",
                lineage_id="lineage",
                metadata={"subject": "theme"},
                derived_known_at=when,
            )
        )
    return store


def test_conservative_policy_requires_repeated_multi_structure_support(tmp_path) -> None:
    memory = setup_memory(tmp_path)
    baselines = SqliteBaselineStore(tmp_path / "baselines")
    worktrees = CognitionWorktreeStore(tmp_path / "worktrees")
    promoter = UnderstandingPromoter(
        memory=memory,
        baseline_store=baselines,
        worktree_store=worktrees,
        policy=ConservativePromotionPolicy(min_blocks=2, min_structures=2, min_support_cycles=2),
    )
    item = worktrees.create(
        region_id="region",
        candidate_content="theme understanding",
        supporting_block_ids=("SB1", "SB2"),
        supporting_structure_ids=("S1", "S2"),
        base_baseline=None,
    )
    worktrees.record_support(item.worktree_id, snapshot_id="snap-1")
    assert promoter.evaluate(item.worktree_id) is None
    worktrees.record_support(item.worktree_id, snapshot_id="snap-2")
    merged = promoter.evaluate(item.worktree_id)
    assert merged is not None
    assert merged.revised is True
    assert baselines.get_head("region").content == "theme understanding"
    assert worktrees.get(item.worktree_id).status == "MERGED"
    memory.close()
    baselines.close()
    worktrees.close()


def test_multiple_blocks_from_one_source_cannot_satisfy_baseline_maturity(tmp_path) -> None:
    memory = setup_memory(tmp_path)
    original = memory.get_semantic_block("SB1")
    memory.put_semantic_block(SemanticBlock(
        block_id="SB-duplicate", content="another fragment of the same event",
        raw_evidence_ids=original.raw_evidence_ids,
        occurred_start=original.occurred_start, occurred_end=original.occurred_end,
        compiler_version="test", lineage_id="lineage", metadata={},
        derived_known_at=original.derived_known_at,
    ))
    baselines = SqliteBaselineStore(tmp_path / "baselines")
    worktrees = CognitionWorktreeStore(tmp_path / "worktrees")
    promoter = UnderstandingPromoter(
        memory=memory, baseline_store=baselines, worktree_store=worktrees,
        policy=ConservativePromotionPolicy(),
    )
    draft = worktrees.create(
        region_id="duplicate", candidate_content="must remain immature",
        supporting_block_ids=("SB1", "SB-duplicate"),
        supporting_structure_ids=("S1", "S2"), base_baseline=None,
    )
    for snapshot_id in ("snap-1", "snap-2", "snap-3"):
        worktrees.record_support(draft.worktree_id, snapshot_id=snapshot_id)
    assert promoter.evaluate(draft.worktree_id) is None
    assert baselines.list_regions() == ()
    assert worktrees.get(draft.worktree_id).status == "OPEN"
    memory.close()
    baselines.close()
    worktrees.close()


def test_same_understanding_revises_when_support_changes_and_text_change_revises_again(tmp_path) -> None:
    memory = setup_memory(tmp_path)
    baselines = SqliteBaselineStore(tmp_path / "baselines")
    worktrees = CognitionWorktreeStore(tmp_path / "worktrees")
    policy = ConservativePromotionPolicy(min_blocks=1, min_structures=1, min_support_cycles=1)
    promoter = UnderstandingPromoter(memory=memory, baseline_store=baselines, worktree_store=worktrees, policy=policy)

    first = worktrees.create(
        region_id="region", candidate_content="same", supporting_block_ids=("SB1",),
        supporting_structure_ids=("S1",), base_baseline=None,
    )
    worktrees.record_support(first.worktree_id, snapshot_id="snap-1")
    promoter.evaluate(first.worktree_id)
    second = worktrees.create(
        region_id="region", candidate_content="same", supporting_block_ids=("SB1", "SB2"),
        supporting_structure_ids=("S1", "S2"), base_baseline=baselines.get_head("region"),
    )
    worktrees.record_support(second.worktree_id, snapshot_id="snap-2")
    support_updated = promoter.evaluate(second.worktree_id)
    assert support_updated.revised is True
    assert support_updated.reason == "SUPPORT_UPDATE"
    assert baselines.get_head("region").revision_number == 2
    assert baselines.get_head("region").supporting_memory_ids == (
        "SB1",
        "SB2",
    )

    third = worktrees.create(
        region_id="region", candidate_content="meaningfully changed", supporting_block_ids=("SB1", "SB2"),
        supporting_structure_ids=("S1", "S2"), base_baseline=baselines.get_head("region"),
    )
    worktrees.record_support(third.worktree_id, snapshot_id="snap-3")
    changed = promoter.evaluate(third.worktree_id)
    assert changed.revised is True
    assert baselines.get_head("region").revision_number == 3
    assert baselines.get_history("region").revisions[0].content == "meaningfully changed"
    memory.close()
    baselines.close()
    worktrees.close()


def test_frontier_promotion_distinguishes_revision_from_new_boundary(
    tmp_path,
) -> None:
    baselines = SqliteBaselineStore(tmp_path / "baselines")
    baselines.save_revision(
        Baseline(
            baseline_id="base-frontier",
            region_id="existing",
            revision_number=1,
            content="old",
            content_hash=compute_content_hash("old"),
            supporting_memory_ids=("SB1",),
            created_at=datetime(2026, 6, 1, tzinfo=UTC),
        )
    )
    worktrees = CognitionWorktreeStore(tmp_path / "worktrees")
    policy = ConservativePromotionPolicy()

    revision = worktrees.create(
        region_id="existing",
        candidate_content="updated",
        supporting_block_ids=("SB1",),
        supporting_structure_ids=(),
        supporting_frontier_refs=("baseline:base-frontier",),
        base_baseline=baselines.get_head("existing"),
        support_kind="frontier",
    )
    assert policy.should_promote(revision, 1) is True

    boundary = worktrees.create(
        region_id="boundary",
        candidate_content="cross-frontier relation",
        supporting_block_ids=("SB1", "SB2"),
        supporting_structure_ids=(),
        supporting_frontier_refs=("baseline:a", "baseline:b"),
        base_baseline=None,
        support_kind="frontier",
    )
    assert policy.should_promote(boundary, 1) is False
    assert policy.should_promote(boundary, 2) is True

    worktrees.close()
    baselines.close()


def test_reconcile_committed_ignores_selected_support_tuple_order(
    tmp_path,
) -> None:
    memory = setup_memory(tmp_path)
    baselines = SqliteBaselineStore(tmp_path / "baselines")
    worktrees = CognitionWorktreeStore(tmp_path / "worktrees")
    promoter = UnderstandingPromoter(
        memory=memory,
        baseline_store=baselines,
        worktree_store=worktrees,
        policy=ConservativePromotionPolicy(
            min_blocks=1,
            min_structures=1,
            min_support_cycles=1,
        ),
    )
    sb1 = memory.get_semantic_block("SB1")
    sb2 = memory.get_semantic_block("SB2")
    assert sb1.state_id is not None
    assert sb2.state_id is not None
    support_1 = AuthorizedSelectedSupport(
        block_id="SB1",
        state_id=sb1.state_id,
    )
    support_2 = AuthorizedSelectedSupport(
        block_id="SB2",
        state_id=sb2.state_id,
    )
    baselines.save_revision(
        Baseline(
            baseline_id="base-order",
            region_id="region-order",
            revision_number=1,
            content="same",
            content_hash=compute_content_hash("same"),
            supporting_memory_ids=("SB1", "SB2"),
            supporting_state_ids=(sb1.state_id, sb2.state_id),
            selected_support=(support_1, support_2),
            created_at=datetime(2026, 6, 3, tzinfo=UTC),
        )
    )
    draft = worktrees.create(
        region_id="region-order",
        candidate_content="same",
        supporting_block_ids=("SB2", "SB1"),
        supporting_structure_ids=("S1",),
        base_baseline=baselines.get_head("region-order"),
        selected_support=(support_2, support_1),
    )

    reconciled = promoter.reconcile_committed(draft.worktree_id)

    assert reconciled is not None
    assert reconciled.revised is False
    assert reconciled.reason == "POST_COMMIT_RECONCILED"
    assert reconciled.baseline.baseline_id == "base-order"
    assert worktrees.get(draft.worktree_id).status == "MERGED"

    memory.close()
    baselines.close()
    worktrees.close()
