"""Synthetic candidate discovery over fixed vectors.

Similarity is used only to propose candidate relations.  It does not create
semantic, cognitive, or canonical authority.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def load_fixture(path: str | Path) -> dict[str, Any]:
    """Load and minimally validate a synthetic fixture."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("fixture must contain a non-empty items list")
    ids = [item.get("id") for item in items]
    if any(not isinstance(item_id, str) for item_id in ids) or len(set(ids)) != len(ids):
        raise ValueError("fixture item ids must be unique strings")
    return data


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Return deterministic cosine similarity without external dependencies."""
    if len(left) != len(right) or not left:
        raise ValueError("vectors must be non-empty and have equal dimensions")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        raise ValueError("zero vectors are not valid candidate inputs")
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def discover_candidate_relations(
    items: list[dict[str, Any]], *, threshold: float, top_k: int | None = None
) -> list[dict[str, Any]]:
    """Return only vector-similarity candidate relations.

    Items are sorted by synthetic id before ranking so input order cannot
    change the result.  A pair is emitted once when it is among the top-k
    qualifying neighbours of either endpoint.
    """
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    if top_k is not None and top_k < 1:
        raise ValueError("top_k must be positive when provided")

    ordered = sorted(items, key=lambda item: item["id"])
    ranked: dict[str, list[tuple[float, str]]] = {}
    by_id = {item["id"]: item for item in ordered}
    for item in ordered:
        neighbours: list[tuple[float, str]] = []
        for other in ordered:
            if item["id"] == other["id"]:
                continue
            similarity = cosine_similarity(item["vector"], other["vector"])
            if similarity >= threshold:
                neighbours.append((similarity, other["id"]))
        ranked[item["id"]] = sorted(neighbours, key=lambda pair: (-pair[0], pair[1]))

    selected: dict[tuple[str, str], float] = {}
    for left_id, neighbours in ranked.items():
        for similarity, right_id in neighbours[:top_k]:
            pair = tuple(sorted((left_id, right_id)))
            selected[pair] = max(similarity, selected.get(pair, -1.0))

    return [
        {
            "relation_type": "candidate_relation",
            "left_id": left_id,
            "right_id": right_id,
            "similarity": round(similarity, 6),
        }
        for (left_id, right_id), similarity in sorted(
            selected.items(), key=lambda entry: (-entry[1], entry[0])
        )
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", nargs="?", default=Path(__file__).with_name("fixture.json"))
    args = parser.parse_args()
    fixture = load_fixture(args.fixture)
    result = discover_candidate_relations(
        fixture["items"], threshold=fixture["threshold"], top_k=fixture.get("top_k")
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
