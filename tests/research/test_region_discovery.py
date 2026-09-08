from pathlib import Path

from research.experiments.region_discovery.experiment import (
    construct_regions,
    load_fixture,
)

FIXTURE = (
    Path(__file__).parents[2]
    / "research"
    / "experiments"
    / "region_discovery"
    / "fixture.json"
)


def test_stable_cluster_forms_a_region() -> None:
    fixture = load_fixture(FIXTURE)
    result = construct_regions(fixture["items"], **fixture["parameters"])
    assert result["regions"] == [
        {
            "region_id": "R01",
            "member_ids": ["P01", "P02", "P03", "P04"],
            "support": {"edge_count": 6, "minimum_neighbour_overlap": 0.5},
        }
    ]


def test_weak_group_is_not_forced_into_a_region() -> None:
    fixture = load_fixture(FIXTURE)
    result = construct_regions(fixture["items"], **fixture["parameters"])
    assert result["unassigned_ids"] == ["P05", "P06"]
    assert all(item not in result["regions"][0]["member_ids"] for item in ["P05", "P06"])


def test_isolated_point_remains_isolated() -> None:
    fixture = load_fixture(FIXTURE)
    result = construct_regions(fixture["items"], **fixture["parameters"])
    assert result["isolated_ids"] == ["P07"]
    assert "P07" not in result["unassigned_ids"]


def test_region_manifest_is_deterministic_and_ordered() -> None:
    fixture = load_fixture(FIXTURE)
    kwargs = fixture["parameters"]
    first = construct_regions(fixture["items"], **kwargs)
    second = construct_regions(list(reversed(fixture["items"])), **kwargs)
    assert first == second
    assert first["regions"][0]["member_ids"] == sorted(first["regions"][0]["member_ids"])
