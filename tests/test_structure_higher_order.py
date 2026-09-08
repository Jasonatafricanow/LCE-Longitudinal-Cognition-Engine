from __future__ import annotations

from datetime import UTC, datetime, timedelta

from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.structure.discovery import SnapshotStructureDiscovery, StructureConfig


def test_structure_level_candidate_keeps_refs_and_expands_to_raw_evidence(tmp_path) -> None:
    store = ReferenceMemoryStore(tmp_path / "memory")
    base = datetime(2026, 5, 1, tzinfo=UTC)
    vectors = {
        "A1": (1.0, 0.0),
        "A2": (0.99, 0.05),
        "B1": (0.98, 0.18),
        "B2": (0.97, 0.24),
    }
    for index, block_id in enumerate(vectors):
        when = base + timedelta(days=index % 2)
        evidence_id = f"E-{block_id}"
        store.add_evidence(
            RawEvidence(
                evidence_id=evidence_id,
                content=block_id,
                occurred_at=when,
                ordering_key=f"{index:04d}:{block_id}",
                provenance={"source": "synthetic", "canonical": True},
            )
        )
        store.put_semantic_block(
            SemanticBlock(
                block_id=block_id,
                content=block_id,
                raw_evidence_ids=(evidence_id,),
                occurred_start=when,
                occurred_end=when,
                compiler_version="test",
                lineage_id="lineage",
                metadata={"subject": block_id[0]},
            )
        )
    store.rebuild_vector_index(lambda block: vectors[block.block_id], index_version="test")
    discovery = SnapshotStructureDiscovery(
        store,
        tmp_path / "structures",
        config=StructureConfig(k_values=(2,), min_similarity=0.8, higher_order_similarity=0.95),
    )
    snapshot = discovery.create_snapshot(base + timedelta(days=1))
    candidates = discovery.higher_order_candidates(snapshot)
    assert candidates
    candidate = candidates[0]
    assert len(candidate.supporting_structure_ids) >= 2
    assert set(candidate.supporting_block_ids).issubset(set(snapshot.visible_block_ids))
    assert set(discovery.expand_candidate_to_blocks(candidate)) == set(candidate.supporting_block_ids)
    assert set(discovery.expand_candidate_to_raw(candidate)) == {f"E-{block_id}" for block_id in candidate.supporting_block_ids}
    store.close()
