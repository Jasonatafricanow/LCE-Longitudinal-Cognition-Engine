from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from lce.core.projection import LceProjectionCore
from lce.reference_memory.composite import (
    ExternalSourceMutationError,
    ProjectionSubstrate,
)
from lce.reference_memory.projection_state import SqliteProjectionStateStore
from lce.reference_memory.sqlite import ReferenceMemoryStore
from tests.fixtures.longitudinal_corpus import longitudinal_corpus


def test_external_source_projection_keeps_canonical_rows_out_of_projection_db(
    tmp_path: Path,
) -> None:
    source = ReferenceMemoryStore(tmp_path / "canonical")
    materials = longitudinal_corpus()[:3]
    for material in materials:
        source.add_evidence(material)

    state = SqliteProjectionStateStore(tmp_path / "derived")
    substrate = ProjectionSubstrate(
        source,
        state,
        close_source=False,
        close_state=True,
    )
    core = LceProjectionCore(
        tmp_path / "lce",
        memory=substrate,
        lineage_id="external",
        close_memory=True,
    )
    results = core.run_batch(materials)
    assert len(results) == len(materials)
    core.close()

    stored = source.list_current_valid_evidence()
    assert tuple(item.evidence_id for item in stored) == tuple(
        item.evidence_id for item in materials
    )
    assert tuple(item.content for item in stored) == tuple(
        item.content for item in materials
    )
    with sqlite3.connect(
        tmp_path / "derived" / "projection_state.sqlite"
    ) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "raw_evidence" not in tables
    assert "semantic_blocks" in tables
    source.close()


def test_external_projection_validates_source_and_cannot_mutate_it(
    tmp_path: Path,
) -> None:
    source = ReferenceMemoryStore(tmp_path / "canonical")
    material = longitudinal_corpus()[0]
    source.add_evidence(material)
    state = SqliteProjectionStateStore(tmp_path / "derived")
    substrate = ProjectionSubstrate(source, state)

    validated = substrate.add_evidence(material)
    assert validated.evidence_id == material.evidence_id
    assert validated.content == material.content
    assert (
        validated.effective_ordering_key
        == material.effective_ordering_key
    )
    with pytest.raises(KeyError):
        substrate.add_evidence(
            material.__class__(
                evidence_id="missing",
                content=material.content,
                occurred_at=material.occurred_at,
                provenance=material.provenance,
            )
        )
    with pytest.raises(ExternalSourceMutationError):
        substrate.invalidate(material.evidence_id, reason="not LCE authority")
    with pytest.raises(ExternalSourceMutationError):
        substrate.supersede(material.evidence_id, "replacement")

    substrate.close()
    source.close()
