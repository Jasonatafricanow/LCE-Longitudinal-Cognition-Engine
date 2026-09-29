from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from lce.contracts.baseline import Baseline, compute_content_hash
from lce.core.projection import LceProjectionCore
from lce.reference_memory.contracts import (
    AuthorizedSelectedSupport,
    RawEvidence,
    SemanticBlock,
)
from lce.reference_memory.sqlite import ReferenceMemoryStore

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _raw(evidence_id: str, day: int) -> RawEvidence:
    return RawEvidence(
        evidence_id=evidence_id,
        content=f"source {evidence_id}",
        occurred_at=BASE + timedelta(days=day),
        known_at=BASE + timedelta(days=day),
        provenance={"source": "test", "canonical": True},
    )


def _block(
    block_id: str,
    evidence_id: str,
    day: int,
) -> SemanticBlock:
    at = BASE + timedelta(days=day)
    return SemanticBlock(
        block_id=block_id,
        content=f"semantic {block_id}",
        raw_evidence_ids=(evidence_id,),
        occurred_start=at,
        occurred_end=at,
        compiler_version="test-v1",
        lineage_id="test",
        derived_known_at=at,
    )


def _put(
    memory: ReferenceMemoryStore,
    evidence_id: str,
    block_id: str,
    day: int,
) -> SemanticBlock:
    memory.add_evidence(_raw(evidence_id, day))
    return memory.put_semantic_block(
        _block(block_id, evidence_id, day)
    )


def _save(
    core: LceProjectionCore,
    *,
    revision: int,
    content: str,
    blocks: tuple[SemanticBlock, ...],
) -> Baseline:
    selected = tuple(
        AuthorizedSelectedSupport(
            block_id=block.block_id,
            state_id=block.state_id or "",
        )
        for block in blocks
    )
    previous = core.baselines.get_head("region-1")
    baseline = Baseline(
        baseline_id=f"base-{revision}",
        region_id="region-1",
        revision_number=revision,
        content=content,
        content_hash=compute_content_hash(content),
        supporting_memory_ids=tuple(
            block.block_id for block in blocks
        ),
        supporting_state_ids=tuple(
            item.state_id for item in selected
        ),
        selected_support=selected,
        created_at=BASE + timedelta(days=revision),
        previous_baseline_id=(
            previous.baseline_id if previous is not None else None
        ),
    )
    core.baselines.save_revision(baseline)
    return baseline


def test_rejection_hides_exact_current_understanding_but_keeps_history(
    tmp_path: Path,
) -> None:
    memory = ReferenceMemoryStore(tmp_path / "memory")
    block_a = _put(memory, "A", "block-a", 0)
    core = LceProjectionCore(
        tmp_path / "projection",
        memory=memory,
    )
    baseline = _save(
        core,
        revision=1,
        content="A and B may imply E.",
        blocks=(block_a,),
    )

    assert core.query(None)
    rejection = core.reject_current_understanding(
        "region-1",
        authority_ref="user-correction-1",
        reason="user rejected this derived relation",
        rejected_at=BASE + timedelta(days=2),
    )

    assert rejection.active is True
    assert core.query(None) == ()
    assert core.frontier._frontier(
        {block_a.block_id: block_a}
    ) == ()
    history = core.baselines.get_history("region-1")
    assert history.revisions[0].baseline_id == baseline.baseline_id

    core.close()
    memory.close()


def test_new_support_reopens_same_hypothesis_without_erasing_rejection(
    tmp_path: Path,
) -> None:
    memory = ReferenceMemoryStore(tmp_path / "memory")
    block_a = _put(memory, "A", "block-a", 0)
    block_c = _put(memory, "C", "block-c", 3)
    core = LceProjectionCore(
        tmp_path / "projection",
        memory=memory,
    )
    content = "A and B may imply E."
    _save(core, revision=1, content=content, blocks=(block_a,))
    rejection = core.reject_current_understanding(
        "region-1",
        authority_ref="user-correction-1",
    )
    assert core.query(None) == ()

    _save(
        core,
        revision=2,
        content=content,
        blocks=(block_a, block_c),
    )
    views = core.query(None)

    assert len(views) == 1
    assert views[0].content == content
    assert set(views[0].supporting_source_refs) == {"A", "C"}
    assert core.rejections.list()[0] == rejection
    assert core.rejections.list()[0].active is True

    core.close()
    memory.close()


def test_explicit_reopen_restores_same_support_proposal(
    tmp_path: Path,
) -> None:
    memory = ReferenceMemoryStore(tmp_path / "memory")
    block_a = _put(memory, "A", "block-a", 0)
    core = LceProjectionCore(
        tmp_path / "projection",
        memory=memory,
    )
    _save(
        core,
        revision=1,
        content="A and B may imply E.",
        blocks=(block_a,),
    )
    rejection = core.reject_current_understanding(
        "region-1",
        authority_ref="user-correction-1",
    )
    assert core.query(None) == ()

    reopened = core.reopen_rejected_understanding(
        rejection.rejection_id,
        authority_ref="user-reopened-hypothesis",
        reopened_at=BASE + timedelta(days=4),
    )

    assert reopened.active is False
    assert len(core.query(None)) == 1

    core.close()
    memory.close()
