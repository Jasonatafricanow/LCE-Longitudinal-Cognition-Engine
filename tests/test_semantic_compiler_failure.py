from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lce.reference_memory.contracts import RawEvidence
from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.semantic.compiler import PendingInputError, SemanticCompiler
from lce.semantic.contracts import SemanticDecision


def item(evidence_id: str, order: str) -> RawEvidence:
    return RawEvidence(
        evidence_id=evidence_id,
        content=evidence_id,
        occurred_at=datetime(2026, 3, 1, tzinfo=UTC),
        ordering_key=order,
        provenance={"source": "synthetic", "canonical": True},
    )


class FlakyProvider:
    def __init__(self) -> None:
        self.failed = False

    def decide(self, *, evidence, open_block, recent_blocks):
        if not self.failed:
            self.failed = True
            raise RuntimeError("provider unavailable")
        return SemanticDecision("NEW", "topic", evidence.content)


def test_provider_failure_does_not_advance_checkpoint_or_skip_material(tmp_path) -> None:
    store = ReferenceMemoryStore(tmp_path / "memory")
    provider = FlakyProvider()
    compiler = SemanticCompiler(store, provider, lineage_id="lineage")
    material = item("E1", "0001:E1")
    with pytest.raises(RuntimeError, match="provider unavailable"):
        compiler.process(material)
    pending = store.get_checkpoint("lineage")
    assert pending is not None
    assert pending.last_ordering_key is None
    assert pending.state["pending_evidence_id"] == "E1"
    assert store.compiled_block_ids("E1") is None

    with pytest.raises(PendingInputError):
        compiler.process(item("E2", "0002:E2"))

    store.close()
    store = ReferenceMemoryStore(tmp_path / "memory")
    compiler = SemanticCompiler(store, provider, lineage_id="lineage")
    with pytest.raises(PendingInputError):
        compiler.process(item("E2", "0002:E2"))

    result = compiler.process(material)
    assert result.block_ids
    assert store.get_checkpoint("lineage").last_ordering_key == "0001:E1"
    assert store.compiled_block_ids("E1") == result.block_ids
    store.close()
