"""Tests for zero-LLM AML Line expansion."""

from datetime import UTC, datetime, timedelta

import pytest

from research.experiments.aml_path_b_v0.line_expansion import (
    BenchmarkUnit,
    RankedHit,
    build_anchor_lines,
    evidence_recall_at_k,
    expand_from_ranked_hits,
)


T0 = datetime(2026, 1, 1, tzinfo=UTC)


def unit(
    unit_id: str,
    day: int,
    session: str,
    *anchors: str,
) -> BenchmarkUnit:
    return BenchmarkUnit(
        unit_id=unit_id,
        occurred_at=T0 + timedelta(days=day),
        session_id=session,
        anchor_terms=tuple(anchors),
    )


def test_line_requires_three_members_and_two_sessions_by_default():
    units = [
        unit("a", 0, "s1", "NIO"),
        unit("b", 1, "s1", "NIO"),
        unit("c", 2, "s2", "NIO"),
        unit("x", 0, "s1", "Tesla"),
        unit("y", 1, "s1", "Tesla"),
        unit("z", 2, "s1", "Tesla"),
    ]

    lines = build_anchor_lines(units)

    assert len(lines) == 1
    assert lines[0].anchor_term == "nio"
    assert lines[0].member_ids == ("a", "b", "c")


def test_line_has_no_fixed_time_window():
    units = [
        unit("a", 0, "s1", "project"),
        unit("b", 100, "s2", "project"),
        unit("c", 1000, "s3", "project"),
    ]

    lines = build_anchor_lines(units)

    assert lines[0].member_ids == ("a", "b", "c")


def test_expansion_recovers_adjacent_cross_session_evidence():
    lines = build_anchor_lines(
        [
            unit("a", 0, "s1", "project"),
            unit("b", 1, "s2", "project"),
            unit("c", 2, "s3", "project"),
            unit("d", 3, "s4", "project"),
        ]
    )

    expanded = expand_from_ranked_hits(
        [RankedHit(unit_id="b", rank=1)],
        lines,
        radius=1,
    )

    assert [candidate.unit_id for candidate in expanded] == ["a", "c"]
    assert all(candidate.distance == 1 for candidate in expanded)


def test_expansion_never_returns_seed_hits():
    lines = build_anchor_lines(
        [
            unit("a", 0, "s1", "project"),
            unit("b", 1, "s2", "project"),
            unit("c", 2, "s3", "project"),
        ]
    )

    expanded = expand_from_ranked_hits(
        [
            RankedHit(unit_id="a", rank=1),
            RankedHit(unit_id="b", rank=2),
        ],
        lines,
    )

    assert [candidate.unit_id for candidate in expanded] == ["c"]


def test_multiple_line_support_accumulates_without_duplicate_candidates():
    units = [
        unit("a", 0, "s1", "project", "nio"),
        unit("b", 1, "s2", "project", "nio"),
        unit("c", 2, "s3", "project", "nio"),
    ]
    lines = build_anchor_lines(units)

    expanded = expand_from_ranked_hits(
        [RankedHit(unit_id="b", rank=1)],
        lines,
    )

    by_id = {candidate.unit_id: candidate for candidate in expanded}
    assert set(by_id) == {"a", "c"}
    assert by_id["a"].source_line_ids == ("anchor:nio", "anchor:project")
    assert by_id["c"].source_line_ids == ("anchor:nio", "anchor:project")


def test_evidence_recall_at_k():
    recall = evidence_recall_at_k(["a", "x", "c"], {"a", "b", "c"}, k=3)
    assert recall == pytest.approx(2 / 3)


def test_invalid_radius_is_rejected():
    with pytest.raises(ValueError, match="radius"):
        expand_from_ranked_hits([], [], radius=0)
