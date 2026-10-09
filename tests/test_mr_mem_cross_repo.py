"""Real MR-Mem admission -> public views -> existing queue -> LCE downstream.

Small frozen producer fixtures exercise the actual MR-Mem validator/closure.
Those imports are test-only; the LCE production integration sees only views.
"""

from __future__ import annotations

import ast
import json
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

pytest.importorskip("mr_mem.memory.semantic_projection")

from mr_mem import MemoryCore, MemoryLifecycle, Scope, ScopeDomain, SourceRef
from mr_mem.memory.projection import ProjectionWorker
from mr_mem.memory.semantic_projection import SqliteCanonicalSemanticBlockReader
from mr_mem.memory.semantic_store import SemanticSourceBinding

from lce.integrations.mr_mem import PROJECTION_TARGET, LifecycleTimeUnknown
from lce.integrations.mr_mem_runtime import (
    MrMemProjectionRuntime,
    MrMemProjectionWriter,
)
from tests.test_mr_mem_runtime import ForbiddenSemanticProvider

OCCURRED = datetime(2026, 1, 1, tzinfo=UTC)
KNOWN = datetime(2026, 2, 1, tzinfo=UTC)
SCOPE = Scope(ScopeDomain.USER, user_id="fixture-user")


class NativeSources:
    def __init__(self) -> None:
        self.refs: dict[str, SourceRef] = {}

    def bind(self, name: str, ordinal: int) -> SemanticSourceBinding:
        ref = SourceRef("frozen-native", "session", name, OCCURRED + timedelta(days=ordinal),
                        revision="1")
        self.refs[name] = ref
        return SemanticSourceBinding(SCOPE, name, ref)

    def current_ref(self, scope: Scope, ref: SourceRef) -> SourceRef | None:
        return self.refs.get(ref.record_id) if scope == SCOPE else None

    def current_user_source(self, scope: Scope, interaction_id: str) -> SourceRef | None:
        return self.refs.get(interaction_id) if scope == SCOPE else None


class FrozenClock:
    def __init__(self, ordinal: int) -> None:
        self.ordinal = ordinal

    def now(self) -> datetime:
        return KNOWN + timedelta(days=self.ordinal)


def point(pid: str, content: str) -> dict[str, str]:
    return {"point_id": pid, "meaning": content, "status": "resolved", "speech_act": "directive",
                "polarity": "positive", "epistemic_status": "asserted", "temporal_scope": "future"}


def admit(core: MemoryCore, sources: NativeSources, name: str, ordinal: int,
          points: list[dict[str, str]], dependencies: list[dict[str, str]] | None = None,
          activated: tuple[str, ...] = ()) -> tuple[str, ...]:
    admission = core.semantic_admission(sources=sources, clock=FrozenClock(ordinal),
                                        origin_runtime_id="frozen-host")
    return tuple(admission.admit_semantic_delta(
        {"schema_version": "semantic_delta_v1", "points": points, "dependencies": dependencies or []},
        binding=sources.bind(name, ordinal), activated_memory_ids=activated,
    ).memory_ids)


def dependency(from_id: str, target: str, *, kind: str = "memory", policy: str = "context",
               effect: str = "none", relation: str = "supports") -> dict[str, str]:
    return {"from_point_id": from_id, "target_kind": kind, "target_id": target,
                "relation": relation, "boundary_policy": policy, "lifecycle_effect": effect}


def assert_no_raw_or_compilation(runtime: MrMemProjectionRuntime) -> None:
    with sqlite3.connect(runtime.projected.db_path) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "raw_evidence" not in tables
        assert db.execute("SELECT count(*) FROM compiled_evidence").fetchone() == (0,)
        assert db.execute("SELECT count(*) FROM compiler_checkpoints").fetchone() == (0,)


def test_cases_a_b_c_d_f_h_backfill_incremental_and_no_points(tmp_path: Path) -> None:
    sources = NativeSources()
    path = tmp_path / "mr-mem.sqlite"
    with MemoryCore(path) as core:
        first = admit(core, sources, "first", 1, [point("p1", "trajectory alpha supports user plan")])[0]
        queue = core.canonical.projection_queue()
        assert queue.register_projection_target(PROJECTION_TARGET) == 1  # Backfill A.
        reader = SqliteCanonicalSemanticBlockReader(path)
        runtime = MrMemProjectionRuntime(tmp_path / "lce", scope=SCOPE,
                                         provider=ForbiddenSemanticProvider())
        try:
            worker = ProjectionWorker(queue, MrMemProjectionWriter(reader, runtime), target=PROJECTION_TARGET)
            assert worker.run_once() == (1, 0)
            assert len(runtime.projected.list_semantic_blocks()) == 1
            independent = admit(core, sources, "second", 2,
                                [point("p1", "trajectory alpha supports user followup")])[0]
            assert worker.run_once() == (1, 0)
            assert {b.block_id for b in runtime.projected.list_semantic_blocks()} == {first, independent}
            cohabit = admit(core, sources, "cohabit", 3,
                            [point("p1", "如果网络恢复。"), point("p2", "此时保留数据库。")],
                            [dependency("p2", "p1", kind="point", policy="cohabit")])
            assert len(cohabit) == 1
            assert worker.run_once() == (1, 0)
            view = reader.get_semantic_block_view(cohabit[0])
            assert view is not None
            public = asdict(view)
            assert "member_point_ids" not in json.dumps(public, default=str)
            assert not hasattr(view, "points") and not hasattr(view, "dependencies")
            assert runtime.projected.get_semantic_block(cohabit[0]).content == "如果网络恢复。\n此时保留数据库。"
            context = admit(core, sources, "context", 4, [point("p1", "trajectory alpha supports user context")],
                            [dependency("p1", first)], activated=(first,))[0]
            assert worker.run_once() == (2, 0)  # Both relation endpoints are requeued.
            projected = runtime.projected.canonical_projection(context)
            assert projected.outgoing_relations[0].to_memory_id == first
            assert projected.outgoing_relations[0].relation == "supports"
            assert len(runtime.projected.list_semantic_blocks()) == 4
            for mid in (first, independent, cohabit[0], context):
                block = runtime.projected.get_semantic_block(mid)
                canonical = core.get(mid)
                assert block.occurred_start == canonical.occurred_at
                assert block.derived_known_at == canonical.known_at
                assert block.derived_known_at != block.occurred_start
            before = runtime.projected.list_semantic_blocks(current_valid_only=False)
            # Nearline growth consumes already bootstrapped Lines. Bootstrap is
            # the existing explicit slow-path seed operation, with default policy.
            runtime.bootstrap_trajectory(knowledge_cutoff=KNOWN + timedelta(days=4))
            lines = runtime.lines.list_lines()
            assert lines  # Replay checks cover actual derived Line identities.
            assert all(line.line_id not in {b.block_id for b in before} for line in lines)
            for _ in range(3):
                assert queue.rebuild(target=PROJECTION_TARGET, reset=True) == 4
                assert worker.run_once() == (4, 0)
            assert runtime.projected.list_semantic_blocks(current_valid_only=False) == before
            assert runtime.lines.list_lines() == lines
            assert len(runtime.projected.vector_projection_ids()) == 4
            assert_no_raw_or_compilation(runtime)
        finally:
            runtime.close()
            reader.close()


def test_case_e_supersede_keeps_historical_cognition_relation_and_time(tmp_path: Path) -> None:
    sources = NativeSources()
    path = tmp_path / "mr-mem.sqlite"
    with MemoryCore(path) as core:
        m1 = admit(core, sources, "old", 1, [point("p1", "top-k=100")])[0]
        queue = core.canonical.projection_queue()
        queue.register_projection_target(PROJECTION_TARGET)
        reader = SqliteCanonicalSemanticBlockReader(path)
        runtime = MrMemProjectionRuntime(tmp_path / "lce", scope=SCOPE, provider=ForbiddenSemanticProvider())
        try:
            worker = ProjectionWorker(queue, MrMemProjectionWriter(reader, runtime), target=PROJECTION_TARGET)
            assert worker.run_once() == (1, 0)
            original = runtime.projected.get_semantic_block(m1)
            m2 = admit(core, sources, "new", 2, [point("p1", "top-k=20/30/50/70")],
                       [dependency("p1", m1, effect="supersede", relation="supersedes")], (m1,))[0]
            assert worker.run_once() == (2, 0)
            old = runtime.projected.canonical_projection(m1)
            new = runtime.projected.canonical_projection(m2)
            assert core.get(m1).lifecycle is MemoryLifecycle.SUPERSEDED
            assert core.get(m2).lifecycle is MemoryLifecycle.ACTIVE
            assert not old.current_valid and new.current_valid
            assert runtime.projected.get_semantic_block(m1) == original
            assert old.transition_known_at == core.get(m2).known_at
            assert old.valid_at(core.get(m1).known_at)
            assert not old.valid_at(core.get(m2).known_at)
            assert old.incoming_relations == new.outgoing_relations
            assert {b.block_id for b in runtime.projected.list_semantic_blocks(current_valid_only=False)} == {m1, m2}
            assert runtime.projected.vector_projection_ids() == (m2,)
        finally:
            runtime.close()
            reader.close()


@pytest.mark.parametrize("crash_boundary", ["before_projection", "after_state", "after_downstream"])
def test_case_g_pending_resume_never_reparses_or_duplicates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, crash_boundary: str,
) -> None:
    path = tmp_path / "mr-mem.sqlite"
    root = tmp_path / "lce"
    with MemoryCore(path) as core:
        mid = admit(core, NativeSources(), "committed", 1, [point("p1", "canonical committed cognition")])[0]
        core.canonical.projection_queue().register_projection_target(PROJECTION_TARGET)
        reader = SqliteCanonicalSemanticBlockReader(path)
        runtime = MrMemProjectionRuntime(root, scope=SCOPE, provider=ForbiddenSemanticProvider())
        writer = MrMemProjectionWriter(reader, runtime)

        class CrashingWriter:
            def upsert(self, memory: object, *, intent: object) -> str:
                if crash_boundary == "after_state":
                    view = reader.get_semantic_block_view(mid)
                    assert view is not None
                    from lce.integrations.mr_mem import map_canonical_semantic_block
                    runtime.projected.put_canonical_projection(
                        map_canonical_semantic_block(view, lineage_id=runtime.lineage_id))
                if crash_boundary == "after_downstream":
                    writer.upsert(memory, intent=intent)
                raise SystemExit("worker crash before acknowledgement")

        try:
            with pytest.raises(SystemExit):
                ProjectionWorker(core.canonical.projection_queue(), CrashingWriter(), target=PROJECTION_TARGET).run_once()
            assert len(core.canonical.projection_queue().pending(10, target=PROJECTION_TARGET)) == 1
        finally:
            runtime.close()
            reader.close()

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("restart invoked semantic parsing/closure")

    monkeypatch.setattr("mr_mem.memory.semantic_admission.validate_semantic_delta", forbidden)
    monkeypatch.setattr("mr_mem.memory.semantic_admission.compile_semantic_delta", forbidden)
    monkeypatch.setattr("lce.semantic.compiler.SemanticCompiler.process", forbidden)
    with MemoryCore(path) as core:
        reader = SqliteCanonicalSemanticBlockReader(path)
        runtime = MrMemProjectionRuntime(root, scope=SCOPE, provider=ForbiddenSemanticProvider())
        try:
            queue = core.canonical.projection_queue()
            worker = ProjectionWorker(queue, MrMemProjectionWriter(reader, runtime), target=PROJECTION_TARGET)
            assert worker.run_once() == (1, 0)
            assert worker.run_once() == (0, 0)
            assert len(runtime.projected.list_semantic_blocks(current_valid_only=False)) == 1
            assert runtime.projected.vector_projection_ids() == (mid,)
            assert core.get(mid).memory_id == mid
            assert_no_raw_or_compilation(runtime)
        finally:
            runtime.close()
            reader.close()


def test_case_i_invalidated_current_false_history_retained(tmp_path: Path) -> None:
    path = tmp_path / "mr-mem.sqlite"
    sources = NativeSources()
    with MemoryCore(path) as core:
        mid = admit(core, sources, "first", 1, [point("p1", "canonical cognition")])[0]
        queue = core.canonical.projection_queue()
        queue.register_projection_target(PROJECTION_TARGET)
        reader = SqliteCanonicalSemanticBlockReader(path)
        runtime = MrMemProjectionRuntime(tmp_path / "lce", scope=SCOPE)
        try:
            worker = ProjectionWorker(queue, MrMemProjectionWriter(reader, runtime), target=PROJECTION_TARGET)
            assert worker.run_once() == (1, 0)
            original = runtime.projected.get_semantic_block(mid)
            invalidated_at = KNOWN + timedelta(days=5)
            assert core.canonical.invalidate_source(
                SCOPE, sources.refs["first"], deleted=True, at=invalidated_at
            ) == (mid,)
            assert worker.run_once() == (1, 0)
            projected = runtime.projected.canonical_projection(mid)
            assert not projected.current_valid
            assert projected.transition_known_at == invalidated_at
            assert runtime.projected.get_semantic_block(mid) == original
            assert runtime.projected.list_semantic_blocks() == ()
            # as-of replay: visible before the invalidation became known, hidden after
            assert projected.valid_at(KNOWN + timedelta(days=2))
            assert not projected.valid_at(invalidated_at)
            assert not projected.valid_at(KNOWN + timedelta(days=9))
        finally:
            runtime.close()
            reader.close()


def test_case_i_unrecorded_invalidation_time_stays_fail_closed(tmp_path: Path) -> None:
    """Rows invalidated before MR-Mem recorded times have no transition time: stay unknown."""
    path = tmp_path / "mr-mem.sqlite"
    sources = NativeSources()
    with MemoryCore(path) as core:
        mid = admit(core, sources, "first", 1, [point("p1", "canonical cognition")])[0]
        queue = core.canonical.projection_queue()
        queue.register_projection_target(PROJECTION_TARGET)
        reader = SqliteCanonicalSemanticBlockReader(path)
        runtime = MrMemProjectionRuntime(tmp_path / "lce", scope=SCOPE)
        try:
            worker = ProjectionWorker(queue, MrMemProjectionWriter(reader, runtime), target=PROJECTION_TARGET)
            assert worker.run_once() == (1, 0)
            with core.canonical._transaction():  # legacy path: lifecycle change without a time
                core.canonical._set_lifecycle(core.get(mid), MemoryLifecycle.INVALIDATED)
            assert worker.run_once() == (1, 0)
            projected = runtime.projected.canonical_projection(mid)
            assert projected.transition_known_at is None
            with pytest.raises(LifecycleTimeUnknown):
                projected.valid_at(KNOWN + timedelta(days=2))
        finally:
            runtime.close()
            reader.close()


def test_case_i_asof_history_reproducible_after_later_invalidation(tmp_path: Path) -> None:
    path = tmp_path / "mr-mem.sqlite"
    sources = NativeSources()
    with MemoryCore(path) as core:
        ids = [
            admit(core, sources, n, i, [point("p1", f"cognition point {n}")])[0]
            for i, n in enumerate(("a", "b", "c"), start=1)
        ]
        queue = core.canonical.projection_queue()
        queue.register_projection_target(PROJECTION_TARGET)
        reader = SqliteCanonicalSemanticBlockReader(path)
        runtime = MrMemProjectionRuntime(tmp_path / "lce", scope=SCOPE, provider=ForbiddenSemanticProvider())
        try:
            worker = ProjectionWorker(queue, MrMemProjectionWriter(reader, runtime), target=PROJECTION_TARGET)
            worker.run_once()
            cutoff = KNOWN + timedelta(days=10)

            def visible() -> list[str]:
                return sorted(b.block_id for b in runtime.projected.list_semantic_blocks_at_knowledge_cutoff(cutoff))

            before = visible()
            assert set(before) == set(ids)
            core.canonical.invalidate_source(SCOPE, sources.refs["b"], deleted=True)  # now > cutoff
            worker.run_once()
            assert visible() == before  # same cutoff, same history
            assert {b.block_id for b in runtime.projected.list_semantic_blocks()} == {ids[0], ids[2]}
        finally:
            runtime.close()
            reader.close()


def test_production_integration_has_no_producer_imports_or_raw_fabrication() -> None:
    root = Path(__file__).parents[1] / "src/lce/integrations"
    forbidden = {"SemanticDeltaV1", "DeltaSemanticPoint", "DeltaSemanticDependency",
                 "semantic_validator", "semantic_closure", "semantic_contracts", "RawEvidence",
                 "SemanticDecisionProvider", "SemanticCompiler"}
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imported = {alias.name.split(".")[-1] for alias in node.names}
                if isinstance(node, ast.ImportFrom):
                    imported.update((node.module or "").split("."))
                assert not imported & forbidden, (path, imported & forbidden)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden, (path, node.func.id)
