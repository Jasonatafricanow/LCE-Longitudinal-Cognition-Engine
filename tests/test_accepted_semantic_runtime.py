from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from lce.core.projection import LceProjectionCore
from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.reference_memory.sqlite import ReferenceMemoryStore

OCCURRED = datetime(2026, 1, 1, tzinfo=UTC)
KNOWN = datetime(2026, 10, 2, tzinfo=UTC)


def accepted(
    memory: ReferenceMemoryStore, index: int, *, event_id: str | None = None,
) -> SemanticBlock:
    source_id = event_id or f"native-event-{index}"
    when = OCCURRED + timedelta(days=index * 10)
    known = KNOWN + timedelta(seconds=index)
    if not any(e.evidence_id == source_id for e in memory.list_current_valid_evidence()):
        memory.add_evidence(RawEvidence(
            source_id, "Native source metadata; raw body stays at the host.",
            when, {"source": "native-host", "canonical": True, "session_id": f"session-{index}"},
            known_at=known,
        ))
    return memory.put_semantic_block(SemanticBlock(
        block_id=f"host-semantic-{index}", content=f"Accepted local meaning {index}.",
        raw_evidence_ids=(source_id,), occurred_start=when, occurred_end=when,
        compiler_version="host-cleaner-v1", lineage_id="host",
        metadata={"vector": (1.0, index / 100.0)},
        derived_known_at=known,
    ))


def embedding(block: SemanticBlock) -> tuple[float, ...]:
    vector = block.metadata["vector"]
    assert isinstance(vector, tuple)
    return tuple(float(value) for value in vector)


def test_accepted_semantics_enter_points_without_second_compilation_or_fake_baseline(
    tmp_path: Path,
) -> None:
    memory = ReferenceMemoryStore(tmp_path / "memory")
    block = accepted(memory, 1)
    core = LceProjectionCore(
        tmp_path / "projection", memory=memory, block_embedder=embedding,
        block_embedding_version="fixture-geometry-v1",
    )
    result = core.process_semantic(block.block_id)
    assert result.compiler_result.action == "ACCEPTED"
    assert result.snapshot.visible_block_ids == (block.block_id,)
    assert result.snapshot.cutoff == block.derived_known_at
    assert memory.get_semantic_block(block.block_id) == block
    assert core.query(None) == ()
    assert core.lines.list_lines() == ()
    assert memory.compiled_block_ids(block.raw_evidence_ids[0]) is None
    core.close()
    memory.close()


def test_accepted_path_requires_explicit_semantic_vectors(tmp_path: Path) -> None:
    memory = ReferenceMemoryStore(tmp_path / "memory")
    block = accepted(memory, 1)
    core = LceProjectionCore(tmp_path / "projection", memory=memory)
    with pytest.raises(ValueError, match="explicit.*embedder"):
        core.process_semantic(block.block_id)
    assert core.query(None) == ()
    core.close()
    memory.close()


@pytest.mark.parametrize("same_source", [False, True])
def test_similar_points_and_duplicate_source_do_not_manufacture_baseline(
    tmp_path: Path, same_source: bool,
) -> None:
    memory = ReferenceMemoryStore(tmp_path / "memory")
    core = LceProjectionCore(
        tmp_path / "projection", memory=memory, block_embedder=embedding,
        block_embedding_version="fixture-geometry-v1",
    )
    for index in range(4):
        block = accepted(memory, index, event_id="same-event" if same_source else None)
        core.process_semantic(block.block_id)
    core.bootstrap_trajectory(knowledge_cutoff=KNOWN + timedelta(seconds=4))
    assert core.query(None) == ()
    assert core.baselines.list_regions() == ()
    if same_source:
        assert core.lines.list_lines() == ()
    core.close()
    memory.close()


def test_cross_session_line_identity_and_support_survive_restart_replay(tmp_path: Path) -> None:
    path = tmp_path / "memory"
    memory = ReferenceMemoryStore(path)
    core = LceProjectionCore(
        tmp_path / "projection", memory=memory, block_embedder=embedding,
        block_embedding_version="fixture-geometry-v1",
    )
    blocks = []
    for index in range(4):
        block = accepted(memory, index)
        blocks.append(block)
        core.process_semantic(block.block_id)
    core.bootstrap_trajectory(knowledge_cutoff=KNOWN + timedelta(seconds=4))
    line_ids = tuple(line.line_id for line in core.lines.list_lines())
    assert line_ids
    node_count = core.lines.conn.execute("SELECT count(*) FROM line_nodes").fetchone()[0]
    core.close()
    memory.close()
    memory = ReferenceMemoryStore(path)
    core = LceProjectionCore(
        tmp_path / "projection", memory=memory, block_embedder=embedding,
        block_embedding_version="fixture-geometry-v1",
    )
    for block in blocks:
        assert core.process_semantic(block.block_id).compiler_result.replayed
    assert tuple(line.line_id for line in core.lines.list_lines()) == line_ids
    assert core.lines.conn.execute("SELECT count(*) FROM line_nodes").fetchone()[0] == node_count
    core.close()
    memory.close()
