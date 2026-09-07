from pathlib import Path

import pytest

from research.experiments.temporal_cutoff.experiment import (
    FutureLeakageError,
    evaluate_cutoff,
    load_fixture,
    shuffled_time_control,
)


FIXTURE = Path(__file__).with_name("fixture.json")


def test_cutoff_t2_cannot_see_t3_or_t4() -> None:
    fixture = load_fixture(FIXTURE)
    result = evaluate_cutoff(fixture["events"], "T2")

    assert result["visible_ids"] == ["E01", "E02"]
    assert result["future_ids"] == ["E03", "E04"]
    assert result["future_leakage"] is False


def test_plain_baseline_uses_only_visible_evidence() -> None:
    fixture = load_fixture(FIXTURE)
    result = evaluate_cutoff(fixture["events"], "T2")

    assert result["baseline"]["input_ids"] == ["E01", "E02"]
    assert result["baseline"]["visible_topics"] == ["synthetic_alpha"]


def test_shuffled_time_control_changes_order_but_not_membership() -> None:
    fixture = load_fixture(FIXTURE)
    result = shuffled_time_control(fixture["events"], "T2", seed=fixture["seed"])

    assert set(result["shuffled_order"]) == {"E01", "E02"}
    assert result["shuffled_order"] != result["original_order"]
    assert result["future_ids"] == ["E03", "E04"]


def test_future_leakage_fails_closed() -> None:
    fixture = load_fixture(FIXTURE)
    with pytest.raises(FutureLeakageError):
        evaluate_cutoff(fixture["events"], "T2", visible_ids=["E01", "E02", "E03"])


def test_cutoff_results_are_deterministic() -> None:
    fixture = load_fixture(FIXTURE)

    assert shuffled_time_control(fixture["events"], "T2", seed=7) == shuffled_time_control(
        fixture["events"], "T2", seed=7
    )
