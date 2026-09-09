from __future__ import annotations

import json
from pathlib import Path

import pytest

from research.replication.semantic_replay import load_replication_jsonl, replay_prefixes


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _metadata(dimension: int = 3) -> dict[str, object]:
    return {
        "type": "metadata",
        "schema_version": 1,
        "corpus_id": "synthetic-contract-fixture",
        "embedding_provider": "fixture",
        "embedding_model": "fixture-vector",
        "embedding_version": "1",
        "vector_dimension": dimension,
    }


def test_load_and_replay_preserve_no_future_visibility(tmp_path: Path) -> None:
    path = tmp_path / "blocks.jsonl"
    _write(
        path,
        [
            _metadata(),
            {
                "type": "block",
                "block_id": "B2",
                "occurred_at": "2026-01-02T00:00:00+00:00",
                "text": "second",
                "vector": [0.9, 0.1, 0.0],
            },
            {
                "type": "block",
                "block_id": "B1",
                "occurred_at": "2026-01-01T00:00:00+00:00",
                "text": "first",
                "vector": [1.0, 0.0, 0.0],
            },
            {
                "type": "block",
                "block_id": "B3",
                "occurred_at": "2026-01-03T00:00:00+00:00",
                "text": "future",
                "vector": [0.0, 1.0, 0.0],
            },
        ],
    )

    metadata, blocks = load_replication_jsonl(path)
    assert metadata.vector_dimension == 3
    assert [block.block_id for block in blocks] == ["B1", "B2", "B3"]

    summary = replay_prefixes(metadata, blocks, k=1, min_similarity=0.0)
    assert [prefix["cutoff_block_id"] for prefix in summary["prefixes"]] == ["B1", "B2", "B3"]
    second_prefix = summary["prefixes"][1]
    assert second_prefix["visible_block_ids"] == ["B1", "B2"]
    assert "B3" not in json.dumps(second_prefix)
    assert second_prefix["neighbours"]["B2"][0]["block_id"] == "B1"


def test_loader_rejects_inconsistent_vector_dimensions(tmp_path: Path) -> None:
    path = tmp_path / "bad-dimension.jsonl"
    _write(
        path,
        [
            _metadata(3),
            {
                "type": "block",
                "block_id": "B1",
                "occurred_at": "2026-01-01T00:00:00+00:00",
                "text": "bad",
                "vector": [1.0, 0.0],
            },
        ],
    )

    with pytest.raises(ValueError, match="vector_dimension"):
        load_replication_jsonl(path)


def test_loader_rejects_naive_timestamps(tmp_path: Path) -> None:
    path = tmp_path / "bad-time.jsonl"
    _write(
        path,
        [
            _metadata(),
            {
                "type": "block",
                "block_id": "B1",
                "occurred_at": "2026-01-01T00:00:00",
                "text": "missing timezone",
                "vector": [1.0, 0.0, 0.0],
            },
        ],
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        load_replication_jsonl(path)
