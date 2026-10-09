"""An interrupted replay_projection_from_sources() must fail closed on restart.

Replay destroys the derived generation (memory projection, snapshots,
worktrees, Line graph) and then re-derives it source by source. A process kill
in that window used to leave an empty/partial Line graph carrying a valid
fingerprint and no rebuild marker, which a restart served as current.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from lce.cognition.line_graph import LineGraphStore
from lce.core.projection import LceProjectionCore, StaleLineGraphError
from lce.reference_memory.sqlite import ReferenceMemoryStore
from tests.fixtures.longitudinal_corpus import longitudinal_corpus

MARKER = "replay_in_progress"


class SimulatedKill(BaseException):
    """BaseException so no ``except Exception`` in the code under test absorbs it."""


def _open(root: Path) -> tuple[ReferenceMemoryStore, LceProjectionCore]:
    memory = ReferenceMemoryStore(root / "source")
    core = LceProjectionCore(root / "projection", memory=memory, lineage_id="main")
    return memory, core


def _line_ids(core: LceProjectionCore) -> frozenset[str]:
    return frozenset(line.line_id for line in core.lines.list_lines())


def _control_line_ids(root: Path) -> frozenset[str]:
    corpus = longitudinal_corpus()
    memory, core = _open(root)
    core.run_batch(corpus)
    core.replay_projection_from_sources(corpus)
    ids = _line_ids(core)
    core.close()
    memory.close()
    return ids


def _kill_during_third_process(core: LceProjectionCore, monkeypatch: pytest.MonkeyPatch) -> None:
    real = core.process
    calls = {"n": 0}

    def dying(*args: object, **kwargs: object) -> object:
        calls["n"] += 1
        if calls["n"] == 3:
            raise SimulatedKill
        return real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(core, "process", dying)


def _kill_before_first_source(core: LceProjectionCore, monkeypatch: pytest.MonkeyPatch) -> None:
    def dying(*args: object, **kwargs: object) -> object:
        raise SimulatedKill

    # Runs after every destructive reset, before any source is re-derived.
    monkeypatch.setattr(core, "run_batch", dying)


def _kill_before_any_reset(core: LceProjectionCore, monkeypatch: pytest.MonkeyPatch) -> None:
    def dying(*args: object, **kwargs: object) -> object:
        raise SimulatedKill

    monkeypatch.setattr(core.memory, "reset_derived_projection", dying)


KILL_POINTS: dict[str, Callable[[LceProjectionCore, pytest.MonkeyPatch], None]] = {
    "before_any_reset": _kill_before_any_reset,
    "after_resets_before_first_source": _kill_before_first_source,
    "mid_replay": _kill_during_third_process,
}


@pytest.mark.parametrize("kill_point", sorted(KILL_POINTS))
def test_interrupted_replay_fails_closed_then_rerun_matches_uninterrupted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kill_point: str
) -> None:
    corpus = longitudinal_corpus()
    expected = _control_line_ids(tmp_path / "control")
    assert expected, "fixture must produce at least one Line for this test to mean anything"

    root = tmp_path / "crashed"
    memory, core = _open(root)
    core.run_batch(corpus)
    assert _line_ids(core) == expected

    KILL_POINTS[kill_point](core, monkeypatch)
    with pytest.raises(SimulatedKill):
        core.replay_projection_from_sources(corpus)
    core.close()
    memory.close()
    monkeypatch.undo()

    # "Restart": brand-new objects over the same on-disk state.
    memory, core = _open(root)
    try:
        assert core.lines.get_metadata(MARKER), "interruption marker must survive the reset"
        with pytest.raises(StaleLineGraphError, match="replay_projection_from_sources"):
            core._require_line_graph_current()
        with pytest.raises(StaleLineGraphError):
            core.ensure_current_projection()
        with pytest.raises(StaleLineGraphError):
            core.process(corpus[-1])  # no ingestion on top of a partial generation
        with pytest.raises(StaleLineGraphError):
            core.run_batch((corpus[-1],))

        core.replay_projection_from_sources(corpus)

        assert not core.lines.get_metadata(MARKER)
        core._require_line_graph_current()
        assert _line_ids(core) == expected
        assert all(
            memory.get_pipeline_stage(item.evidence_id) == "complete" for item in corpus
        )
    finally:
        core.close()
        memory.close()


def test_failed_replay_marker_survives_plain_exceptions_too(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    corpus = longitudinal_corpus()
    memory, core = _open(tmp_path / "p")
    core.run_batch(corpus)

    def boom(*args: object, **kwargs: object) -> object:
        raise RuntimeError("provider failed")

    monkeypatch.setattr(core, "run_batch", boom)
    with pytest.raises(RuntimeError, match="provider failed"):
        core.replay_projection_from_sources(corpus)
    # Same process, no restart: still refuses until a replay completes.
    with pytest.raises(StaleLineGraphError):
        core._require_line_graph_current()
    monkeypatch.undo()
    core.replay_projection_from_sources(corpus)
    core._require_line_graph_current()
    core.close()
    memory.close()


def test_completed_and_empty_replays_leave_no_marker(tmp_path: Path) -> None:
    corpus = longitudinal_corpus()
    memory, core = _open(tmp_path / "p")
    core.replay_projection_from_sources(corpus)
    assert not core.lines.get_metadata(MARKER)
    core.replay_projection_from_sources(())
    assert not core.lines.get_metadata(MARKER)
    core._require_line_graph_current()
    core.close()
    memory.close()


def test_line_store_reset_preserves_only_named_metadata(tmp_path: Path) -> None:
    store = LineGraphStore(tmp_path / "lines")
    store.set_metadata("keep", "1")
    store.set_metadata("drop", "2")
    store.reset_derived(preserve_metadata=("keep",))
    assert store.get_metadata("keep") == "1"
    assert store.get_metadata("drop") is None
    store.reset_derived()
    assert store.get_metadata("keep") is None
    store.close()
