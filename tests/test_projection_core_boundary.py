from __future__ import annotations

from pathlib import Path

from lce.core.projection import LceProjectionCore
from lce.reference_memory.sqlite import ReferenceMemoryStore
from tests.fixtures.longitudinal_corpus import longitudinal_corpus


def test_projection_core_requires_injected_source_store_and_does_not_own_it(
    tmp_path: Path,
) -> None:
    memory = ReferenceMemoryStore(tmp_path / "source")
    core = LceProjectionCore(
        tmp_path / "projection",
        memory=memory,
        lineage_id="main",
    )

    results = core.run_batch(longitudinal_corpus()[:2])
    assert len(results) == 2
    core.close()

    # Core closes only LCE-owned projection stores by default. The injected
    # source/working substrate remains owned by its composition root.
    assert memory.list_current_valid_evidence()
    memory.close()


def test_forward_replay_repairs_historical_source_gap(tmp_path: Path) -> None:
    corpus = longitudinal_corpus()[:3]
    memory = ReferenceMemoryStore(tmp_path / "source")
    core = LceProjectionCore(
        tmp_path / "projection",
        memory=memory,
        lineage_id="main",
    )

    # Simulate a broken embedded consumer that projected a later source first.
    later = core.run_batch((corpus[1],))
    assert len(later) == 1
    assert memory.get_pipeline_stage(corpus[1].evidence_id) == "complete"

    rebuilt = core.replay_projection_from_sources(corpus)

    assert len(rebuilt) == len(corpus)
    assert {
        item.evidence_id
        for item in memory.list_current_valid_evidence()
    } == {
        item.evidence_id
        for item in corpus
    }
    assert all(
        memory.get_pipeline_stage(item.evidence_id) == "complete"
        for item in corpus
    )
    core.close()
    memory.close()


def test_projection_core_has_no_concrete_reference_store_dependency() -> None:
    source = (
        Path(__file__).parents[1] / "src" / "lce" / "core" / "projection.py"
    ).read_text(encoding="utf-8")
    assert "ReferenceMemoryStore" not in source
    assert "reference_memory.sqlite" not in source
