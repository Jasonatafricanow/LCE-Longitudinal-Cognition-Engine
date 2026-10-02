"""Contract mapping without invoking any compiler or provider."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip("mr_mem.memory.semantic_projection")

from mr_mem.contracts import Scope, ScopeDomain
from mr_mem.memory.contracts import MemoryLifecycle
from mr_mem.memory.semantic_projection import CanonicalSemanticBlockView
from mr_mem.memory.source import SourceRef

from lce.integrations.mr_mem import LifecycleTimeUnknown, map_canonical_semantic_block


def canonical_view(memory_id: str = "canonical-1") -> CanonicalSemanticBlockView:
    occurred = datetime(2026, 1, 1, tzinfo=UTC)
    known = occurred + timedelta(days=10)
    return CanonicalSemanticBlockView(
        memory_id, Scope(ScopeDomain.USER, user_id="u1"), "top-k=100", occurred, known,
        MemoryLifecycle.ACTIVE, "semantic_delta_v1", "mr-compiler-v1",
        (SourceRef("native", "s1", memory_id, occurred, revision="r1"),), (), (), (),
    )


def test_mapping_preserves_canonical_identity_time_and_native_provenance() -> None:
    view = canonical_view()
    projected = map_canonical_semantic_block(view, lineage_id="tenant-1")
    block = projected.block
    assert block.block_id == view.memory_id
    assert block.content == view.content
    assert block.occurred_start == block.occurred_end == view.occurred_at
    assert block.derived_known_at == view.known_at != view.occurred_at
    assert block.raw_evidence_ids == (view.source_refs[0].source_key,)
    assert projected.current_valid
    assert not projected.valid_at(view.occurred_at)
    assert projected.valid_at(view.known_at)


@pytest.mark.parametrize("lifecycle", [MemoryLifecycle.INVALIDATED, MemoryLifecycle.ARCHIVED,
                                      MemoryLifecycle.SUPERSEDED])
def test_unknown_transition_is_not_sync_time(lifecycle: MemoryLifecycle) -> None:
    view = replace(canonical_view(), lifecycle=lifecycle)
    projected = map_canonical_semantic_block(view, lineage_id="tenant-1")
    assert not projected.current_valid
    assert projected.transition_known_at is None
    with pytest.raises(LifecycleTimeUnknown):
        projected.valid_at(view.known_at)

def test_mrmem_semantic_block_adapter() -> None:
    from lce.integrations.mr_mem import MRMemSemanticBlockAdapter

    adapter = MRMemSemanticBlockAdapter(lineage_id="tenant-adapter")
    view = canonical_view("canonical-adapter-1")
    projected = adapter.adapt(view)
    assert projected.block.block_id == "canonical-adapter-1"
    assert projected.block.lineage_id == "tenant-adapter"

    projected2 = adapter(view, lineage_id="override-lineage")
    assert projected2.block.lineage_id == "override-lineage"
