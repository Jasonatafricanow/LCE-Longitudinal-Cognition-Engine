from __future__ import annotations

from datetime import UTC, datetime, timedelta

from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.structure.discovery import SnapshotStructureDiscovery, StructureConfig


BASE = datetime(2026, 4, 1, tzinfo=UTC)


def populate(store: ReferenceMemoryStore, specs: list[tuple[str, int, tuple[float, ...]]]) -> None:
    vectors: dict[str, tuple[float, ...]] = {}
    for block_id, day, vector in specs:
        evidence_id = f"E-{block_id}"
        when = BASE + timedelta(days=day)
        store.add_evidence(
            RawEvidence(
                evidence_id=evidence_id,
                content=block_id,
                occurred_at=when,
                ordering_key=f"{day:04d}:{block_id}",
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
                metadata={"subject": block_id},
            )
        )
        vectors[block_id] = vector
    store.rebuild_vector_index(lambda block: vectors[block.block_id], index_version="test")


def test_snapshot_cutoff_is_stable_and_diff_sees_new_members_and_strength(tmp_path) -> None:
    store = ReferenceMemoryStore(tmp_path / "memory")
    populate(
        store,
        [
            ("A", 0, (1.0, 0.0)),
            ("B", 0, (0.95, 0.31)),
            ("C", 1, (0.99, 0.10)),
        ],
    )
    discovery = SnapshotStructureDiscovery(
        store,
        tmp_path / "structures",
        config=StructureConfig(k_values=(1,), min_similarity=0.8),
    )
    t1 = discovery.create_snapshot(BASE)
    t1_again = discovery.create_snapshot(BASE)
    t2 = discovery.create_snapshot(BASE + timedelta(days=1))
    assert t1.snapshot_id == t1_again.snapshot_id
    assert "C" not in t1.visible_block_ids
    assert "C" in t2.visible_block_ids
    diff = discovery.diff(t1, t2)
    assert diff.new_members
    assert diff.stronger_support
    store.close()


def test_points_can_participate_in_multiple_structures_and_reconnect(tmp_path) -> None:
    store = ReferenceMemoryStore(tmp_path / "memory")
    populate(
        store,
        [
            ("A", 0, (1.0, 0.0)),
            ("B", 0, (0.99, 0.1)),
            ("isolated", 0, (0.0, 1.0)),
            ("new-neighbour", 1, (0.0, 0.99)),
        ],
    )
    discovery = SnapshotStructureDiscovery(
        store,
        tmp_path / "structures",
        config=StructureConfig(k_values=(1,), min_similarity=0.95),
    )
    t1 = discovery.create_snapshot(BASE)
    t2 = discovery.create_snapshot(BASE + timedelta(days=1))
    observations = t1.structures
    assert sum("B" in observation.member_block_ids for observation in observations) >= 2
    assert any("isolated" in observation.member_block_ids and len(observation.member_block_ids) == 1 for observation in t1.structures)
    diff = discovery.diff(t1, t2)
    assert any(change.structure_id.endswith(":isolated:k1") for change in diff.reconnections)
    store.close()


def test_rebuild_from_blocks_and_vectors_is_equivalent(tmp_path) -> None:
    store = ReferenceMemoryStore(tmp_path / "memory")
    populate(store, [("A", 0, (1.0, 0.0)), ("B", 1, (0.99, 0.1))])
    discovery = SnapshotStructureDiscovery(store, tmp_path / "structures")
    original = discovery.create_snapshot(BASE + timedelta(days=1))
    discovery.delete_derived_snapshots()
    rebuilt = discovery.create_snapshot(BASE + timedelta(days=1))
    assert original == rebuilt
    store.close()
