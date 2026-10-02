"""Explicit canonical mode and crash-safe immutable projected identity."""

from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("mr_mem.memory.semantic_projection")

from mr_mem.memory.contracts import MemoryLifecycle

from lce.integrations.mr_mem_runtime import MrMemProjectionRuntime
from tests.test_mr_mem_mapping import canonical_view


class ForbiddenSemanticProvider:
    def decide(self, **kwargs: object) -> None:
        raise AssertionError("integrated path performed semantic compilation")


def test_canonical_replay_restart_and_no_raw_compiler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    view = canonical_view()

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("legacy compiler must not be constructed or called")

    monkeypatch.setattr("lce.core.projection.SemanticCompiler", forbidden)
    runtime = MrMemProjectionRuntime(tmp_path, scope=view.scope, provider=ForbiddenSemanticProvider())
    try:
        result = runtime.project_canonical_semantic_block(view)
        assert result.downstream is not None
        assert result.downstream.trajectory_result is not None
        assert runtime.compiler is None
        state_id = runtime.projected.get_semantic_block(view.memory_id).state_id
        lines = runtime.lines.list_lines()
        for _ in range(5):
            replay = runtime.project_canonical_semantic_block(view)
            assert replay.receipt.replayed
        assert runtime.lines.list_lines() == lines
        assert len(runtime.projected.list_semantic_blocks(current_valid_only=False)) == 1
        assert runtime.projected.vector_projection_ids() == (view.memory_id,)
        with pytest.raises(RuntimeError, match="Raw input is forbidden"):
            runtime.process_raw_evidence(object())  # type: ignore[arg-type]
    finally:
        runtime.close()
    restarted = MrMemProjectionRuntime(tmp_path, scope=view.scope, provider=ForbiddenSemanticProvider())
    try:
        assert restarted.project_canonical_semantic_block(view).receipt.replayed
        assert restarted.projected.get_semantic_block(view.memory_id).state_id == state_id
        assert restarted.lines.list_lines() == lines
    finally:
        restarted.close()


@pytest.mark.parametrize("lifecycle", [MemoryLifecycle.INVALIDATED, MemoryLifecycle.ARCHIVED])
def test_unknown_lifecycle_preserves_history_and_omits_dated_algorithms(
    tmp_path: Path, lifecycle: MemoryLifecycle,
) -> None:
    view = canonical_view()
    runtime = MrMemProjectionRuntime(tmp_path, scope=view.scope)
    try:
        runtime.project_canonical_semantic_block(view)
        original = runtime.projected.get_semantic_block(view.memory_id)
        lines = runtime.lines.list_lines()
        result = runtime.project_canonical_semantic_block(replace(view, lifecycle=lifecycle))
        assert result.historical_validity_unknown
        assert result.downstream is None
        assert runtime.projected.list_semantic_blocks() == ()
        assert runtime.projected.vector_projection_ids() == ()
        assert runtime.projected.get_semantic_block(view.memory_id) == original
        assert runtime.lines.list_lines() == lines
    finally:
        runtime.close()
