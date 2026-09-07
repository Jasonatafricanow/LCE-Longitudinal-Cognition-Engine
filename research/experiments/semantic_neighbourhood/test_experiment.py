import json
from pathlib import Path

import pytest

from research.experiments.semantic_neighbourhood.experiment import (
    discover_candidate_relations,
    load_fixture,
)


FIXTURE = Path(__file__).with_name("fixture.json")


def test_near_vectors_create_candidate_relations() -> None:
    fixture = load_fixture(FIXTURE)
    relations = discover_candidate_relations(
        fixture["items"], threshold=fixture["threshold"], top_k=fixture["top_k"]
    )

    pairs = {(row["left_id"], row["right_id"]) for row in relations}
    assert pairs == {("P01", "P02"), ("P03", "P04")}
    assert all(row["relation_type"] == "candidate_relation" for row in relations)


def test_low_similarity_items_do_not_become_candidates() -> None:
    fixture = load_fixture(FIXTURE)
    relations = discover_candidate_relations(
        fixture["items"], threshold=fixture["threshold"], top_k=fixture["top_k"]
    )

    assert all("P05" not in (row["left_id"], row["right_id"]) for row in relations)


def test_candidate_relations_are_deterministic() -> None:
    fixture = load_fixture(FIXTURE)
    kwargs = {"threshold": fixture["threshold"], "top_k": fixture["top_k"]}

    assert discover_candidate_relations(fixture["items"], **kwargs) == discover_candidate_relations(
        list(reversed(fixture["items"])), **kwargs
    )


def test_result_schema_does_not_claim_cognitive_authority() -> None:
    fixture = load_fixture(FIXTURE)
    relations = discover_candidate_relations(
        fixture["items"], threshold=fixture["threshold"], top_k=fixture["top_k"]
    )
    forbidden = {"same_belief", "same_cognition", "canonical_relation", "confirmed_structure"}

    assert relations
    assert not forbidden.intersection(relations[0])


def test_fixture_is_json_and_has_only_synthetic_ids() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert [item["id"] for item in raw["items"]] == ["P01", "P02", "P03", "P04", "P05"]
    assert all(item["id"].startswith("P") for item in raw["items"])
