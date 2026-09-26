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


def test_projection_core_has_no_concrete_reference_store_dependency() -> None:
    source = (
        Path(__file__).parents[1] / "src" / "lce" / "core" / "projection.py"
    ).read_text(encoding="utf-8")
    assert "ReferenceMemoryStore" not in source
    assert "reference_memory.sqlite" not in source
