from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from lce.cognition.promotion import (
    BoundedInterpretation,
    BoundedInterpretationPackage,
)
from lce.contracts.baseline import Baseline, compute_content_hash
from lce.core.projection import LceProjectionCore
from lce.reference_memory.contracts import (
    AuthorizedSelectedSupport,
    RawEvidence,
    SemanticBlock,
)
from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.semantic.contracts import SemanticDecision
from lce.structure.contracts import StructureRelationCandidate

BASE = datetime(2026, 2, 1, tzinfo=UTC)


class _NewBlockProvider:
    def decide(
        self,
        *,
        evidence: RawEvidence,
        open_block: SemanticBlock | None,
        recent_blocks: tuple[SemanticBlock, ...],
    ) -> SemanticDecision:
        del open_block, recent_blocks
        return SemanticDecision(
            action="NEW",
            subject=evidence.evidence_id,
            cognition=evidence.content,
            reason="test creates independent blocks",
        )


class _RecordingInterpreter:
    def __init__(self, *, frontier_status: str = "PROPOSED") -> None:
        self.frontier_status = frontier_status
        self.calls: list[str] = []
        self.contexts: list[dict[str, object]] = []

    def interpret(
        self,
        package: BoundedInterpretationPackage,
    ) -> BoundedInterpretation:
        relation = package.candidate.relation_type
        self.calls.append(relation)
        self.contexts.append(dict(package.context))
        if relation.startswith("frontier_"):
            if self.frontier_status != "PROPOSED":
                return BoundedInterpretation(
                    content=None,
                    supporting_block_ids=(),
                    status=self.frontier_status,
                )
            return BoundedInterpretation(
                content="Updated accepted longitudinal understanding.",
                supporting_block_ids=package.candidate.supporting_block_ids,
                model_trace={
                    "provider": "test",
                    "model": "frontier",
                },
            )
        return BoundedInterpretation(
            content="Legacy structure interpretation.",
            supporting_block_ids=package.candidate.supporting_block_ids,
            model_trace={
                "provider": "test",
                "model": "legacy",
            },
        )


def _evidence(evidence_id: str, day: int, content: str) -> RawEvidence:
    return RawEvidence(
        evidence_id=evidence_id,
        content=content,
        occurred_at=BASE + timedelta(days=day),
        ordering_key=f"{day:04d}:{evidence_id}",
        provenance={"source": "test", "canonical": True},
    )


def _embed(block: SemanticBlock) -> tuple[float, ...]:
    if "career" in block.content.casefold():
        return (1.0, 0.0)
    return (0.0, 1.0)


def _seed_baseline(
    core: LceProjectionCore,
    memory: ReferenceMemoryStore,
    block_id: str,
) -> None:
    block = memory.get_semantic_block(block_id)
    assert block.state_id is not None
    content = "User is considering a career change."
    core.baselines.save_revision(
        Baseline(
            baseline_id="baseline-career-1",
            region_id="career-region",
            revision_number=1,
            content=content,
            content_hash=compute_content_hash(content),
            supporting_memory_ids=(block_id,),
            supporting_state_ids=(block.state_id,),
            selected_support=(
                AuthorizedSelectedSupport(
                    block_id=block_id,
                    state_id=block.state_id,
                ),
            ),
            created_at=BASE,
        )
    )


def _legacy_candidate(
    snapshot_id: str,
    block_ids: tuple[str, ...],
) -> StructureRelationCandidate:
    return StructureRelationCandidate(
        candidate_id="legacy-candidate",
        snapshot_id=snapshot_id,
        supporting_structure_ids=("legacy-s1", "legacy-s2"),
        supporting_block_ids=block_ids,
        relation_type="structure_relation",
        strength=1.0,
    )


def test_frontier_handled_input_skips_legacy_candidate_evaluation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    memory = ReferenceMemoryStore(tmp_path / "memory")
    interpreter = _RecordingInterpreter()
    core = LceProjectionCore(
        tmp_path / "projection",
        memory=memory,
        provider=_NewBlockProvider(),
        interpreter=interpreter,
        block_embedder=_embed,
        block_embedding_version="test-embed-v1",
    )

    first = core.process(_evidence("E1", 0, "career change idea"))
    first_block = first.compiler_result.block_ids[0]
    _seed_baseline(core, memory, first_block)

    original = core.discovery.higher_order_candidates

    def fake_legacy(snapshot):
        current_ids = tuple(
            block.block_id for block in snapshot.block_states
        )
        return (_legacy_candidate(snapshot.snapshot_id, current_ids),)

    monkeypatch.setattr(
        core.discovery,
        "higher_order_candidates",
        fake_legacy,
    )
    second = core.process(
        _evidence("E2", 2, "career applications started")
    )

    assert any(
        item.relation_type == "frontier_absorption"
        for item in second.higher_order_candidates
    )
    assert interpreter.calls[-1] == "frontier_absorption"
    assert "structure_relation" not in interpreter.calls
    frontier_contexts = interpreter.contexts[-1]["frontier_contexts"]
    assert frontier_contexts == (
        {
            "region_id": "career-region",
            "kind": "baseline",
            "content": "User is considering a career change.",
        },
    )
    assert core.baselines.get_head("career-region").revision_number == 2

    monkeypatch.setattr(
        core.discovery,
        "higher_order_candidates",
        original,
    )
    core.close()
    memory.close()


def test_unknown_frontier_falls_back_to_legacy_structure_supplier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    memory = ReferenceMemoryStore(tmp_path / "memory")
    interpreter = _RecordingInterpreter(frontier_status="UNKNOWN")
    core = LceProjectionCore(
        tmp_path / "projection",
        memory=memory,
        provider=_NewBlockProvider(),
        interpreter=interpreter,
        block_embedder=_embed,
        block_embedding_version="test-embed-v1",
    )

    first = core.process(_evidence("E1", 0, "career change idea"))
    first_block = first.compiler_result.block_ids[0]
    _seed_baseline(core, memory, first_block)

    def fake_legacy(snapshot):
        block_ids = tuple(
            block.block_id for block in snapshot.block_states
        )
        return (_legacy_candidate(snapshot.snapshot_id, block_ids),)

    monkeypatch.setattr(
        core.discovery,
        "higher_order_candidates",
        fake_legacy,
    )
    core.process(_evidence("E2", 2, "career applications started"))

    assert "frontier_absorption" in interpreter.calls
    assert "structure_relation" in interpreter.calls
    core.close()
    memory.close()


def test_injected_block_embedder_is_used_for_vector_rebuild(
    tmp_path: Path,
) -> None:
    memory = ReferenceMemoryStore(tmp_path / "memory")
    calls: list[str] = []

    def embed(block: SemanticBlock) -> tuple[float, ...]:
        calls.append(block.content)
        return (1.0, 0.0)

    core = LceProjectionCore(
        tmp_path / "projection",
        memory=memory,
        provider=_NewBlockProvider(),
        block_embedder=embed,
        block_embedding_version="external-embed-v3",
    )
    result = core.process(_evidence("E1", 0, "one block"))

    assert calls == ["one block"]
    vector = memory.get_vector(
        result.compiler_result.block_ids[0]
    )
    assert vector.index_version == "external-embed-v3"
    core.close()
    memory.close()
