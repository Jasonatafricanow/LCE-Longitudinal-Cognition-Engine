"""Unit tests for LCE contracts."""

from datetime import UTC, datetime

import pytest

from lce.contracts.baseline import (
    Baseline,
    BaselineHistory,
    compute_content_hash,
    normalize_content,
)
from lce.contracts.external_memory import MemoryItemView


def test_memory_item_view_valid() -> None:
    view = MemoryItemView(
        memory_id="mem-1",
        content="User likes cats",
        source_refs=("ev-101",),
        retrieval_metadata={"score": 0.95, "vector_dim": 1536},
    )
    assert view.memory_id == "mem-1"
    assert view.content == "User likes cats"
    assert view.source_refs == ("ev-101",)
    assert view.retrieval_metadata["score"] == 0.95

    with pytest.raises(ValueError, match="memory_id"):
        MemoryItemView(memory_id="", content="text", source_refs=("ev-1",))
    with pytest.raises(ValueError, match="content"):
        MemoryItemView(memory_id="mem-1", content="  ", source_refs=("ev-1",))
    with pytest.raises(ValueError, match="source_refs"):
        MemoryItemView(memory_id="mem-1", content="text", source_refs=())


def test_baseline_creation_and_immutability() -> None:
    now = datetime.now(UTC)
    content = "User has a stray orange cat."
    h = compute_content_hash(content)

    b1 = Baseline(
        baseline_id="base-001",
        region_id="region-cats",
        revision_number=1,
        content=content,
        content_hash=h,
        supporting_memory_ids=("mem-1", "mem-2"),
        created_at=now,
        previous_baseline_id=None,
        model_trace={"model": "glm-4", "confidence": 0.9},
    )
    assert b1.revision_number == 1
    assert b1.previous_baseline_id is None

    # Rev 1 with previous_baseline_id must fail
    with pytest.raises(ValueError, match="revision 1 must have previous_baseline_id=None"):
        Baseline(
            baseline_id="base-001",
            region_id="region-cats",
            revision_number=1,
            content=content,
            content_hash=h,
            supporting_memory_ids=("mem-1",),
            created_at=now,
            previous_baseline_id="base-old",
        )

    # Rev 2 without previous_baseline_id must fail
    with pytest.raises(ValueError, match="revision > 1 must have a non-empty previous_baseline_id"):
        Baseline(
            baseline_id="base-002",
            region_id="region-cats",
            revision_number=2,
            content=content,
            content_hash=h,
            supporting_memory_ids=("mem-1",),
            created_at=now,
            previous_baseline_id=None,
        )

    # Naive datetime must fail
    with pytest.raises(ValueError, match="aware UTC"):
        Baseline(
            baseline_id="base-001",
            region_id="region-cats",
            revision_number=1,
            content=content,
            content_hash=h,
            supporting_memory_ids=("mem-1",),
            created_at=datetime.now(),  # naive  # noqa: DTZ005
            previous_baseline_id=None,
        )


def test_baseline_forbids_raw_memories_in_audit_trace() -> None:
    now = datetime.now(UTC)
    content = "Summary"
    h = compute_content_hash(content)

    with pytest.raises(ValueError, match="forbidden raw memory/prompt audit keys"):
        Baseline(
            baseline_id="base-001",
            region_id="region-cats",
            revision_number=1,
            content=content,
            content_hash=h,
            supporting_memory_ids=("mem-1",),
            created_at=now,
            previous_baseline_id=None,
            model_trace={"raw_memories": ["mem 1 text", "mem 2 text"]},
        )


def test_normalize_content_and_hash() -> None:
    text1 = "  User   adopted  a cat. \n\n"
    text2 = "User adopted a cat."
    assert normalize_content(text1) == text2
    assert compute_content_hash(text1) == compute_content_hash(text2)


def test_baseline_history() -> None:
    now = datetime.now(UTC)
    b1 = Baseline(
        baseline_id="b1",
        region_id="reg-1",
        revision_number=1,
        content="C1",
        content_hash=compute_content_hash("C1"),
        supporting_memory_ids=("m1",),
        created_at=now,
        previous_baseline_id=None,
    )
    b2 = Baseline(
        baseline_id="b2",
        region_id="reg-1",
        revision_number=2,
        content="C2",
        content_hash=compute_content_hash("C2"),
        supporting_memory_ids=("m1", "m2"),
        created_at=now,
        previous_baseline_id="b1",
    )
    history = BaselineHistory(region_id="reg-1", revisions=(b2, b1))
    assert len(history.revisions) == 2

    # Mismatch region must fail
    b_other = Baseline(
        baseline_id="b3",
        region_id="reg-other",
        revision_number=1,
        content="C3",
        content_hash=compute_content_hash("C3"),
        supporting_memory_ids=("m3",),
        created_at=now,
        previous_baseline_id=None,
    )
    with pytest.raises(ValueError, match="does not match history region_id"):
        BaselineHistory(region_id="reg-1", revisions=(b_other,))
