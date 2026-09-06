"""Unit tests for fake substrate."""

from lce.testing.fake_substrate import FakeMemorySubstrate


def test_fake_substrate_basic() -> None:
    substrate = FakeMemorySubstrate()
    substrate.add_memory("m1", "Content 1", ("ev1",), {"score": 0.8})
    substrate.add_memory("m2", "Content 2", ("ev2",))

    items = substrate.get_by_ids(("m1", "m2", "m_unknown"))
    assert len(items) == 2
    assert items[0].memory_id == "m1"
    assert items[1].memory_id == "m2"

    # Test metadata update without altering memory content
    substrate.update_metadata("m1", {"score": 0.99, "coord": [0.1, 0.2]})
    updated = substrate.get_by_ids(("m1",))[0]
    assert updated.memory_id == "m1"
    assert updated.content == "Content 1"
    assert updated.source_refs == ("ev1",)
    assert updated.retrieval_metadata["score"] == 0.99
