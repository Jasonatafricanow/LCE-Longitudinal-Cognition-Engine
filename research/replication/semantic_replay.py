from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ReplicationMetadata:
    schema_version: int
    corpus_id: str
    embedding_provider: str
    embedding_model: str
    embedding_version: str
    vector_dimension: int


@dataclass(frozen=True, slots=True)
class VectorBlock:
    block_id: str
    occurred_at: datetime
    text: str
    vector: tuple[float, ...]


def _require_string(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("occurred_at must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("occurred_at must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("occurred_at must be timezone-aware")
    return parsed.astimezone(UTC)


def _parse_vector(value: object, *, expected_dimension: int) -> tuple[float, ...]:
    if not isinstance(value, list):
        raise ValueError("vector must be a JSON array")
    if len(value) != expected_dimension:
        raise ValueError(
            f"vector length {len(value)} does not match metadata vector_dimension {expected_dimension}"
        )
    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError("vector values must be finite numbers")
        number = float(item)
        if not math.isfinite(number):
            raise ValueError("vector values must be finite numbers")
        result.append(number)
    return tuple(result)


def load_replication_jsonl(path: Path | str) -> tuple[ReplicationMetadata, tuple[VectorBlock, ...]]:
    source = Path(path)
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            parsed = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number} is not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"line {line_number} must be a JSON object")
        rows.append(parsed)

    if not rows or rows[0].get("type") != "metadata":
        raise ValueError("first non-empty row must be type=metadata")

    meta_row = rows[0]
    schema_version = meta_row.get("schema_version")
    vector_dimension = meta_row.get("vector_dimension")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool) or schema_version != 1:
        raise ValueError("schema_version must be integer 1")
    if not isinstance(vector_dimension, int) or isinstance(vector_dimension, bool) or vector_dimension < 1:
        raise ValueError("vector_dimension must be an integer >= 1")

    metadata = ReplicationMetadata(
        schema_version=schema_version,
        corpus_id=_require_string(meta_row, "corpus_id"),
        embedding_provider=_require_string(meta_row, "embedding_provider"),
        embedding_model=_require_string(meta_row, "embedding_model"),
        embedding_version=_require_string(meta_row, "embedding_version"),
        vector_dimension=vector_dimension,
    )

    blocks: list[VectorBlock] = []
    seen_ids: set[str] = set()
    for row_number, row in enumerate(rows[1:], start=2):
        if row.get("type") != "block":
            raise ValueError(f"row {row_number} must be type=block")
        block_id = _require_string(row, "block_id")
        if block_id in seen_ids:
            raise ValueError(f"duplicate block_id: {block_id}")
        seen_ids.add(block_id)
        text = _require_string(row, "text")
        blocks.append(
            VectorBlock(
                block_id=block_id,
                occurred_at=_parse_timestamp(row.get("occurred_at")),
                text=text,
                vector=_parse_vector(row.get("vector"), expected_dimension=vector_dimension),
            )
        )

    if not blocks:
        raise ValueError("replication input requires at least one block")

    blocks.sort(key=lambda block: (block.occurred_at, block.block_id))
    return metadata, tuple(blocks)


def cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        raise ValueError("cosine vectors must have the same dimension")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


def replay_prefixes(
    metadata: ReplicationMetadata,
    blocks: tuple[VectorBlock, ...],
    *,
    k: int = 3,
    min_similarity: float = -1.0,
) -> dict[str, Any]:
    if k < 1:
        raise ValueError("k must be >= 1")
    if not -1.0 <= min_similarity <= 1.0:
        raise ValueError("min_similarity must be between -1 and 1")

    prefixes: list[dict[str, Any]] = []
    for cutoff_index, cutoff_block in enumerate(blocks):
        visible = blocks[: cutoff_index + 1]
        neighbours: dict[str, list[dict[str, object]]] = {}
        for source in visible:
            scored: list[tuple[float, VectorBlock]] = []
            for target in visible:
                if source.block_id == target.block_id:
                    continue
                similarity = cosine_similarity(source.vector, target.vector)
                if similarity >= min_similarity:
                    scored.append((similarity, target))
            scored.sort(key=lambda item: (-item[0], item[1].occurred_at, item[1].block_id))
            neighbours[source.block_id] = [
                {"block_id": target.block_id, "similarity": round(similarity, 12)}
                for similarity, target in scored[:k]
            ]

        prefixes.append(
            {
                "cutoff_block_id": cutoff_block.block_id,
                "cutoff": cutoff_block.occurred_at.isoformat(),
                "visible_block_ids": [block.block_id for block in visible],
                "neighbours": neighbours,
            }
        )

    return {
        "metadata": asdict(metadata),
        "parameters": {"k": k, "min_similarity": min_similarity},
        "prefixes": prefixes,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replay chronological neighbourhoods from precomputed semantic vectors."
    )
    parser.add_argument("input", type=Path, help="JSONL replication input")
    parser.add_argument("--output", type=Path, help="Write JSON summary to this path")
    parser.add_argument("--k", type=int, default=3, help="Maximum neighbours per visible block")
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=-1.0,
        help="Minimum cosine similarity to retain (-1 to 1)",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    metadata, blocks = load_replication_jsonl(args.input)
    summary = replay_prefixes(metadata, blocks, k=args.k, min_similarity=args.min_similarity)
    rendered = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
