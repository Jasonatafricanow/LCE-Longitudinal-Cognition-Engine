from __future__ import annotations

import ast
import hashlib
import importlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from lce.integrations.mr_mem import MRMemSemanticBlockAdapter, open_mr_mem_projection


class Sources:
    def __init__(self, ref: Any) -> None:
        self.ref = ref

    def current_ref(self, scope: object, ref: Any) -> Any:
        return self.ref if ref.source_key == self.ref.source_key else None

    def current_user_source(self, scope: object, interaction_id: str) -> Any:
        return self.ref if interaction_id == self.ref.record_id else None


class Clock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def admit(
    memory: Any, source: Sources, scope: Any, content: str, target: str | None = None
) -> Any:
    contracts = importlib.import_module("mr_mem.memory.semantic_store")
    service = memory.semantic_admission(
        sources=source, clock=Clock(), origin_runtime_id="fixture"
    )
    payload = {
        "schema_version": "semantic_delta_v1",
        "points": [
            {
                "point_id": "p1",
                "meaning": content,
                "status": "resolved",
                "speech_act": "directive",
                "polarity": "positive",
                "epistemic_status": "asserted",
                "temporal_scope": "current",
            }
        ],
        "dependencies": []
        if target is None
        else [
            {
                "from_point_id": "p1",
                "target_kind": "memory",
                "target_id": target,
                "relation": "correction",
                "boundary_policy": "context",
                "lifecycle_effect": "supersede",
            }
        ],
    }
    return service.admit_semantic_delta(
        payload,
        binding=contracts.SemanticSourceBinding(
            scope, source.ref.record_id, source.ref
        ),
        activated_memory_ids=() if target is None else (target,),
    )


def test_real_mr_mem_blocks_project_without_recompilation_and_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mr_mem = pytest.importorskip("mr_mem")
    core = importlib.import_module("mr_mem.memory.core")
    from lce.semantic.compiler import SemanticCompiler

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError(
            "integrated path invoked legacy semantic compiler/provider"
        )

    monkeypatch.setattr(SemanticCompiler, "__init__", forbidden)
    monkeypatch.setattr(SemanticCompiler, "process", forbidden)
    scope = mr_mem.Scope(mr_mem.ScopeDomain.USER, "owner")
    at = datetime(2020, 1, 1, tzinfo=UTC)
    sources = Sources(mr_mem.SourceRef("native", "s", "1", at, fingerprint="v1"))
    path = tmp_path / "canonical.sqlite"
    with core.MemoryCore(path) as memory:
        first = admit(memory, sources, scope, "top-k=100。")
        old_id = first.memory_ids[0]
        content = memory.get(old_id).content
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    projection_root = tmp_path / "derived"
    projection = open_mr_mem_projection(path, projection_root, scope=scope)
    try:
        assert projection.compiler is None
        source = projection.memory.source  # type: ignore[attr-defined]
        block = source.get_semantic_block(old_id)
        assert block.block_id == old_id and block.content == content
        assert block.metadata["source_refs"][0]["record_id"] == "1"
        result = projection.process_semantic_block(block)
        assert result.compiler_result.block_ids == (old_id,)
        assert result.trajectory_result is not None
        with pytest.raises(ValueError, match="differs"):
            projection.process_semantic_block(replace(block, content="rewritten"))
        with pytest.raises(ValueError, match="SemanticBlocks only"):
            projection.process(source.get_evidence(old_id))
    finally:
        projection.close()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    projection = open_mr_mem_projection(path, projection_root, scope=scope)
    try:
        source = projection.memory.source  # type: ignore[attr-defined]
        replay = projection.process_semantic_block(source.get_semantic_block(old_id))
        assert replay.compiler_result.replayed
        assert len(projection.memory.list_semantic_blocks()) == 1
        with core.MemoryCore(path) as memory:
            sources.ref = mr_mem.SourceRef(
                "native", "s", "2", at + timedelta(days=1), fingerprint="v2"
            )
            second = admit(memory, sources, scope, "top-k=20/30/50/70。", old_id)
        new_id = second.memory_ids[0]
        view = source.view(new_id)
        assert view.context_memory_ids == (old_id,) and view.relations
        projection.process_semantic_block(source.get_semantic_block(new_id))
        assert tuple(b.block_id for b in projection.memory.list_semantic_blocks()) == (
            new_id,
        )
        assert source.view(old_id).lifecycle == "superseded"
    finally:
        projection.close()


def test_adapter_rejects_write_capability_and_foreign_scope(tmp_path: Path) -> None:
    mr_mem = pytest.importorskip("mr_mem")
    core = importlib.import_module("mr_mem.memory.core")
    scope = mr_mem.Scope(mr_mem.ScopeDomain.USER, "owner")
    path = tmp_path / "canonical.sqlite"
    source = Sources(
        mr_mem.SourceRef(
            "native", "s", "1", datetime(2020, 1, 1, tzinfo=UTC), fingerprint="v1"
        )
    )
    with core.MemoryCore(path) as writer:
        receipt = admit(writer, source, scope, "test")
        with pytest.raises(ValueError, match="read-only"):
            MRMemSemanticBlockAdapter(writer, scope=scope)
    with core.MemoryCore(path, read_only=True) as reader:
        adapter = MRMemSemanticBlockAdapter(
            reader, scope=mr_mem.Scope(mr_mem.ScopeDomain.USER, "foreign")
        )
        with pytest.raises(KeyError):
            adapter.view(receipt.memory_ids[0])


def test_lce_integration_has_no_semantic_delta_or_agy_dependency() -> None:
    path = Path(__file__).resolve().parents[1] / "src/lce/integrations/mr_mem.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = {item.id for item in ast.walk(tree) if isinstance(item, ast.Name)}
    assert not names.intersection(
        {"DeltaSemanticPoint", "SemanticDeltaV1", "ExternalAGYAdapter"}
    )
    imports = {
        item.module for item in ast.walk(tree) if isinstance(item, ast.ImportFrom)
    }
    assert not any(
        name and name.startswith(("historical", "lce.semantic")) for name in imports
    )
