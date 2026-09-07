"""Synthetic, inspectable region construction over fixed vectors."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def load_fixture(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("fixture must contain a non-empty items list")
    ids = [item.get("id") for item in items]
    if any(not isinstance(item_id, str) for item_id in ids) or len(set(ids)) != len(ids):
        raise ValueError("fixture item ids must be unique strings")
    return data


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("vectors must be non-empty and have equal dimensions")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        raise ValueError("zero vectors are not valid region inputs")
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def _neighbour_sets(
    items: list[dict[str, Any]], neighbour_count: int, minimum_similarity: float
) -> dict[str, set[str]]:
    ordered = sorted(items, key=lambda item: item["id"])
    result: dict[str, set[str]] = {}
    for item in ordered:
        ranked = []
        for other in ordered:
            if item["id"] == other["id"]:
                continue
            similarity = _cosine(item["vector"], other["vector"])
            if similarity >= minimum_similarity:
                ranked.append((similarity, other["id"]))
        ranked.sort(key=lambda pair: (-pair[0], pair[1]))
        result[item["id"]] = {other_id for _, other_id in ranked[:neighbour_count]}
    return result


def _overlap(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def construct_regions(
    items: list[dict[str, Any]],
    *,
    neighbour_count: int,
    minimum_similarity: float,
    minimum_overlap: float,
    minimum_region_size: int,
) -> dict[str, Any]:
    """Construct deterministic regions from overlapping kNN neighbourhoods."""
    if neighbour_count < 1 or minimum_region_size < 1:
        raise ValueError("neighbour_count and minimum_region_size must be positive")
    if not 0 <= minimum_similarity <= 1 or not 0 <= minimum_overlap <= 1:
        raise ValueError("similarity and overlap thresholds must be between 0 and 1")

    neighbours = _neighbour_sets(items, neighbour_count, minimum_similarity)
    ids = sorted(neighbours)
    parent = {item_id: item_id for item_id in ids}

    def find(item_id: str) -> str:
        while parent[item_id] != item_id:
            parent[item_id] = parent[parent[item_id]]
            item_id = parent[item_id]
        return item_id

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    edge_overlaps: dict[tuple[str, str], float] = {}
    for index, left in enumerate(ids):
        for right in ids[index + 1 :]:
            score = _overlap(neighbours[left], neighbours[right])
            if score >= minimum_overlap:
                union(left, right)
                edge_overlaps[(left, right)] = score

    components: dict[str, list[str]] = {}
    for item_id in ids:
        components.setdefault(find(item_id), []).append(item_id)

    regions = []
    region_members = set()
    for member_ids in sorted(components.values(), key=lambda group: tuple(group)):
        member_ids = sorted(member_ids)
        if len(member_ids) < minimum_region_size:
            continue
        member_set = set(member_ids)
        scores = [
            score
            for (left, right), score in edge_overlaps.items()
            if left in member_set and right in member_set
        ]
        regions.append(
            {
                "region_id": f"R{len(regions) + 1:02d}",
                "member_ids": member_ids,
                "support": {
                    "edge_count": len(scores),
                    "minimum_neighbour_overlap": round(min(scores), 6) if scores else 0.0,
                },
            }
        )
        region_members.update(member_ids)

    isolated_ids = sorted(item_id for item_id, values in neighbours.items() if not values)
    unassigned_ids = sorted(
        item_id for item_id, values in neighbours.items() if values and item_id not in region_members
    )
    return {
        "regions": regions,
        "isolated_ids": isolated_ids,
        "unassigned_ids": unassigned_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", nargs="?", default=Path(__file__).with_name("fixture.json"))
    args = parser.parse_args()
    fixture = load_fixture(args.fixture)
    print(json.dumps(construct_regions(fixture["items"], **fixture["parameters"]), indent=2))


if __name__ == "__main__":
    main()
