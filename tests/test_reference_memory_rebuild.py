from __future__ import annotations

from datetime import UTC, datetime

from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.reference_memory.sqlite import ReferenceMemoryStore


def test_vector_index_is_derived_and_rebuildable(tmp_path) -> None:
    store = ReferenceMemoryStore(tmp_path / "memory")
    item = RawEvidence(
        evidence_id="E1",
        content="canonical evidence",
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        ordering_key="0001:E1",
        provenance={"source": "synthetic", "canonical": True},
    )
    store.add_evidence(item)
    store.put_semantic_block(
        SemanticBlock(
            block_id="SB1",
            content="semantic cognition point",
            raw_evidence_ids=("E1",),
            occurred_start=item.occurred_at,
            occurred_end=item.occurred_at,
            compiler_version="v1",
            lineage_id="lineage",
        )
    )
    store.rebuild_vector_index(lambda block: (1.0, 2.0, 3.0), index_version="test-vector-v1")
    assert store.vector_projection_ids() == ("SB1",)
    store.delete_vector_index()
    assert store.vector_projection_ids() == ()
    store.rebuild_vector_index(lambda block: (4.0, 5.0, 6.0), index_version="test-vector-v2")
    assert store.vector_projection_ids() == ("SB1",)
    assert store.get_vector("SB1").values == (4.0, 5.0, 6.0)
    assert store.get_evidence("E1").content == "canonical evidence"
    assert store.get_semantic_block("SB1").content == "semantic cognition point"
    store.close()
