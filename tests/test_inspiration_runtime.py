from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path

from lce.cognition.inspiration import (
    InspirationInterpretation,
    InspirationKind,
    InspirationPackage,
    RuleBasedInspirationInterpreter,
)
from lce.cognition.line_graph import LineApplyResult
from lce.contracts.inspiration import InspirationMaterial
from lce.core.projection import LceProjectionCore
from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.structure.trajectory import TrajectoryPath, TrajectoryRuntimeResult
from lce.testing.reference_memory import InMemoryReferenceMemory

BASE = datetime(2026, 1, 1, tzinfo=UTC)


class _SemanticInspirationInterpreter:
    derivation_id = "test-inspiration-v1"

    def interpret(
        self,
        package: InspirationPackage,
    ) -> InspirationInterpretation:
        if package.kind is InspirationKind.ASSOCIATION:
            hypothesis = "the timing and direction may be related"
        else:
            hypothesis = "D may become possible if the existing direction continues"
        return InspirationInterpretation(
            hypothesis=hypothesis,
            model_trace={"model": self.derivation_id},
        )


def _admit(
    memory: InMemoryReferenceMemory,
    *,
    index: int,
    content: str,
) -> SemanticBlock:
    occurred = BASE + timedelta(days=index * 10)
    evidence_id = f"E-{index}"
    memory.add_evidence(
        RawEvidence(
            evidence_id=evidence_id,
            content=content,
            occurred_at=occurred,
            known_at=occurred,
            provenance={"source": "test", "canonical": True},
        )
    )
    return memory.put_semantic_block(
        SemanticBlock(
            block_id=f"B-{index}",
            content=content,
            raw_evidence_ids=(evidence_id,),
            occurred_start=occurred,
            occurred_end=occurred,
            compiler_version="test",
            lineage_id="main",
            metadata={},
            derived_known_at=occurred,
        )
    )


def _seed_line(
    core: LceProjectionCore,
    blocks: tuple[SemanticBlock, ...],
    *,
    cutoff: datetime,
) -> str:
    line = core.lines.create_line(
        tuple(block.block_id for block in blocks),
        created_at=cutoff,
    )
    nodes = []
    for block in blocks:
        node, _added_node, _added_state = core.lines.ensure_node(
            line.line_id,
            block,
            knowledge_at=cutoff,
        )
        nodes.append(node)
    for parent, child in pairwise(nodes):
        core.lines.add_edge(
            line.line_id,
            parent.node_id,
            child.node_id,
            knowledge_at=cutoff,
        )
    return line.line_id


def _unresolved_trajectory(
    blocks: tuple[SemanticBlock, ...],
    *,
    cutoff: datetime,
) -> TrajectoryRuntimeResult:
    state_ids = tuple(block.state_id or "" for block in blocks)
    assert all(state_ids)
    path = TrajectoryPath(
        path_id="candidate-path-1",
        block_ids=tuple(block.block_id for block in blocks),
        state_ids=state_ids,
        edge_similarities=tuple(0.8 for _ in range(len(blocks) - 1)),
    )
    return TrajectoryRuntimeResult(
        knowledge_cutoff_iso=cutoff.isoformat(),
        candidate_paths=(path,),
        line_updates=(
            LineApplyResult(
                line_id=None,
                created_line=False,
                added_node_ids=(),
                added_state_ids=(),
                added_edges=(),
                unresolved_reason="identity unresolved",
            ),
        ),
    )


def test_public_material_contract_is_only_id_and_content() -> None:
    assert [field.name for field in fields(InspirationMaterial)] == [
        "material_id",
        "content",
    ]


def test_discovery_compiles_association_and_extension_to_opaque_material(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(memory, index=index, content=content)
        for index, content in enumerate(("A happened", "B followed", "C followed"))
    )
    cutoff = BASE + timedelta(days=100)
    core = LceProjectionCore(
        tmp_path / "core",
        memory=memory,
        inspiration_interpreter=_SemanticInspirationInterpreter(),
    )
    line_id = _seed_line(core, blocks, cutoff=cutoff)
    assert line_id

    discovered = core.discover_inspiration(
        knowledge_cutoff=cutoff,
        trajectory_result=_unresolved_trajectory(
            blocks[:2],
            cutoff=cutoff,
        ),
    )
    pending = core.inspiration_materials()

    assert len(discovered) == 2
    assert pending == discovered
    assert all(isinstance(item, InspirationMaterial) for item in pending)
    assert any(
        "Possible connection to explore (not established)" in item.content
        and "A happened" in item.content
        and "B followed" in item.content
        for item in pending
    )
    assert any(
        "Existing supported line: A happened -> B followed -> C followed"
        in item.content
        and "Possible next implication to explore (not established)"
        in item.content
        and "D may become possible" in item.content
        for item in pending
    )
    core.close()


def test_reference_interpreter_does_not_invent_extension_d(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(memory, index=index, content=content)
        for index, content in enumerate(("A", "B", "C"))
    )
    cutoff = BASE + timedelta(days=100)
    core = LceProjectionCore(
        tmp_path / "core",
        memory=memory,
        inspiration_interpreter=RuleBasedInspirationInterpreter(),
    )
    _seed_line(core, blocks, cutoff=cutoff)

    discovered = core.discover_inspiration(
        knowledge_cutoff=cutoff,
        trajectory_result=_unresolved_trajectory(
            blocks[:2],
            cutoff=cutoff,
        ),
    )

    assert len(discovered) == 1
    assert "Possible connection to explore (not established)" in discovered[0].content
    assert "Existing supported line:" not in discovered[0].content
    core.close()


def test_consumed_material_is_not_resurrected_by_same_discovery(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    blocks = tuple(
        _admit(memory, index=index, content=content)
        for index, content in enumerate(("A", "B"))
    )
    cutoff = BASE + timedelta(days=100)
    core = LceProjectionCore(
        tmp_path / "core",
        memory=memory,
        inspiration_interpreter=_SemanticInspirationInterpreter(),
    )
    result = _unresolved_trajectory(blocks, cutoff=cutoff)

    first = core.discover_inspiration(
        knowledge_cutoff=cutoff,
        trajectory_result=result,
    )
    assert len(first) == 1
    core.consume_inspiration(first[0].material_id)
    assert core.inspiration_materials() == ()

    replay = core.discover_inspiration(
        knowledge_cutoff=cutoff,
        trajectory_result=result,
    )
    assert replay == ()
    assert core.inspiration_materials() == ()
    core.close()


def test_dismiss_unknown_material_fails_closed(tmp_path: Path) -> None:
    memory = InMemoryReferenceMemory()
    core = LceProjectionCore(tmp_path / "core", memory=memory)
    try:
        core.dismiss_inspiration("missing")
    except KeyError as exc:
        assert exc.args == ("missing",)
    else:
        raise AssertionError("unknown material must fail closed")
    core.close()
