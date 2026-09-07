"""Synthetic no-future evaluation and shuffled-time negative control."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


class FutureLeakageError(ValueError):
    """Raised when an evaluation includes an event after its cutoff."""


def load_fixture(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    events = data.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("fixture must contain a non-empty events list")
    ids = [event.get("id") for event in events]
    if any(not isinstance(event_id, str) for event_id in ids) or len(set(ids)) != len(ids):
        raise ValueError("event ids must be unique strings")
    if any(not isinstance(event.get("time"), str) for event in events):
        raise ValueError("event times must be strings")
    return data


def _ordered_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(events, key=lambda event: (event["time"], event["id"]))
    if len({event["time"] for event in ordered}) != len(ordered):
        raise ValueError("synthetic events must have unique time labels")
    return ordered


def _split_at_cutoff(
    events: list[dict[str, Any]], cutoff: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = _ordered_events(events)
    visible = [event for event in ordered if event["time"] <= cutoff]
    future = [event for event in ordered if event["time"] > cutoff]
    return visible, future


def _assert_no_future(
    visible: list[dict[str, Any]], future: list[dict[str, Any]], visible_ids: list[str]
) -> None:
    allowed = {event["id"] for event in visible}
    future_ids = {event["id"] for event in future}
    requested = set(visible_ids)
    if not requested <= allowed or requested & future_ids:
        raise FutureLeakageError("evaluation input contains evidence after the cutoff")


def evaluate_cutoff(
    events: list[dict[str, Any]], cutoff: str, visible_ids: list[str] | None = None
) -> dict[str, Any]:
    """Evaluate only events visible at ``cutoff`` and fail closed on leakage."""
    visible, future = _split_at_cutoff(events, cutoff)
    allowed_ids = [event["id"] for event in visible]
    requested_ids = allowed_ids if visible_ids is None else visible_ids
    _assert_no_future(visible, future, requested_ids)
    visible_by_id = {event["id"]: event for event in visible}
    ordered_visible = [visible_by_id[event_id] for event_id in requested_ids]
    topics = list(dict.fromkeys(event["topic"] for event in ordered_visible))
    return {
        "cutoff": cutoff,
        "visible_ids": allowed_ids,
        "future_ids": [event["id"] for event in future],
        "future_leakage": False,
        "baseline": {"input_ids": requested_ids, "visible_topics": topics},
    }


def shuffled_time_control(events: list[dict[str, Any]], cutoff: str, *, seed: int) -> dict[str, Any]:
    """Shuffle only visible events, retaining the future boundary."""
    visible, future = _split_at_cutoff(events, cutoff)
    original_order = [event["id"] for event in visible]
    shuffled = list(original_order)
    random.Random(seed).shuffle(shuffled)
    _assert_no_future(visible, future, shuffled)
    return {
        "cutoff": cutoff,
        "original_order": original_order,
        "shuffled_order": shuffled,
        "visible_ids": sorted(shuffled),
        "future_ids": [event["id"] for event in future],
        "future_leakage": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", nargs="?", default=Path(__file__).with_name("fixture.json"))
    args = parser.parse_args()
    fixture = load_fixture(args.fixture)
    result = {
        "plain": evaluate_cutoff(fixture["events"], "T2"),
        "shuffled": shuffled_time_control(fixture["events"], "T2", seed=fixture["seed"]),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
