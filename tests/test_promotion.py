from __future__ import annotations

from datetime import UTC, datetime

from lce.cognition.promotion import ConservativePromotionPolicy, UnderstandingPromoter
from lce.cognition.worktree import CognitionWorktreeStore
from lce.reference_memory.contracts import RawEvidence, SemanticBlock
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


def test_same_understanding_does_not_create_a_revision_but_changed_text_does(tmp_path) -> None:
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
    unchanged = promoter.evaluate(second.worktree_id)
    assert unchanged.revised is False
    assert baselines.get_head("region").revision_number == 1

    third = worktrees.create(
        region_id="region", candidate_content="meaningfully changed", supporting_block_ids=("SB1", "SB2"),
        supporting_structure_ids=("S1", "S2"), base_baseline=baselines.get_head("region"),
    )
    worktrees.record_support(third.worktree_id, snapshot_id="snap-3")
    changed = promoter.evaluate(third.worktree_id)
    assert changed.revised is True
    assert baselines.get_head("region").revision_number == 2
    assert baselines.get_history("region").revisions[0].content == "meaningfully changed"
    memory.close()
    baselines.close()
    worktrees.close()
