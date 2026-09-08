from __future__ import annotations

from datetime import UTC, datetime

from lce.cognition.invalidation import DependencyInvalidator
from lce.cognition.worktree import CognitionWorktreeStore
from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.store.sqlite_store import SqliteBaselineStore
from lce.structure.discovery import SnapshotStructureDiscovery


def test_invalidating_one_source_finds_only_affected_dependencies(tmp_path) -> None:
    memory = ReferenceMemoryStore(tmp_path / "memory")
    for evidence_id, block_id in (("E1", "SB1"), ("E2", "SB2")):
        when = datetime(2026, 7, 1, tzinfo=UTC)
        memory.add_evidence(
            RawEvidence(
                evidence_id=evidence_id, content=block_id, occurred_at=when,
                ordering_key=evidence_id, provenance={"source": "synthetic", "canonical": True},
            )
        )
        memory.put_semantic_block(
            SemanticBlock(
                block_id=block_id, content=block_id, raw_evidence_ids=(evidence_id,),
                occurred_start=when, occurred_end=when, compiler_version="test", lineage_id="lineage",
            )
        )
    memory.rebuild_vector_index(lambda block: (1.0, 0.0) if block.block_id == "SB1" else (0.0, 1.0), index_version="test")
    discovery = SnapshotStructureDiscovery(memory, tmp_path / "structures")
    snapshot = discovery.create_snapshot(datetime(2026, 7, 2, tzinfo=UTC))
    worktrees = CognitionWorktreeStore(tmp_path / "worktrees")
    affected_worktree = worktrees.create(
        region_id="region", candidate_content="candidate", supporting_block_ids=("SB1",),
        supporting_structure_ids=tuple(item.structure_id for item in snapshot.structures if "SB1" in item.member_block_ids),
        base_baseline=None,
    )
    unaffected_worktree = worktrees.create(
        region_id="other", candidate_content="other", supporting_block_ids=("SB2",),
        supporting_structure_ids=(), base_baseline=None,
    )
    baselines = SqliteBaselineStore(tmp_path / "baselines")
    result = DependencyInvalidator(memory, discovery, worktrees, baselines).invalidate("E1")
    assert result.affected_block_ids == ("SB1",)
    assert result.affected_worktree_ids == (affected_worktree.worktree_id,)
    assert unaffected_worktree.worktree_id not in result.affected_worktree_ids
    assert result.affected_snapshot_ids == (snapshot.snapshot_id,)
    assert worktrees.get(affected_worktree.worktree_id).needs_rebuild is True
    memory.close()
    baselines.close()
    worktrees.close()
    discovery.close()
