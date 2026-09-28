from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from lce.cognition.line_graph import (
    LineAssembler,
    LineAssemblerConfig,
    LineGraphStore,
)
from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.structure.trajectory import (
    NeighbourCandidateProvider,
    TrajectoryConfig,
    TrajectoryRuntime,
)
from lce.testing.reference_memory import InMemoryReferenceMemory


BASE = datetime(2026, 1, 1, tzinfo=UTC)


class _ChainProvider(NeighbourCandidateProvider):
    derivation_fingerprint = "authority-chain-v1"

    def candidates(
        self,
        blocks: tuple[SemanticBlock, ...],
        vectors: dict[str, tuple[float, ...]],
        *,
        k: int,
        min_similarity: float,
    ) -> dict[str, tuple[tuple[float, str], ...]]:
        del vectors, k, min_similarity
        ids = [block.block_id for block in blocks]
        output: dict[str, tuple[tuple[float, str], ...]] = {}
        for index, block_id in enumerate(ids):
            neighbours: list[tuple[float, str]] = []
            if index:
                neighbours.append((0.99, ids[index - 1]))
            if index + 1 < len(ids):
                neighbours.append((0.99, ids[index + 1]))
            output[block_id] = tuple(neighbours)
        return output


def _block(
    memory: InMemoryReferenceMemory,
    *,
    block_id: str,
    day: int,
    evidence_id: str,
) -> SemanticBlock:
    when = BASE + timedelta(days=day)
    try:
        memory.get_evidence(evidence_id)
    except KeyError:
        memory.add_evidence(
            RawEvidence(
                evidence_id=evidence_id,
                content=evidence_id,
                occurred_at=when,
                known_at=when,
                provenance={"source": "test", "canonical": True},
            )
        )
    return memory.put_semantic_block(
        SemanticBlock(
            block_id=block_id,
            content=block_id,
            raw_evidence_ids=(evidence_id,),
            occurred_start=when,
            occurred_end=when,
            compiler_version="test",
            lineage_id="main",
            metadata={"vector": (1.0, float(day) / 1000.0)},
        )
    )


def _rebuild(memory: InMemoryReferenceMemory) -> None:
    memory.rebuild_vector_index(
        lambda block: tuple(
            float(value) for value in block.metadata["vector"]
        ),
        index_version="authority-test-v1",
    )


def test_duplicate_raw_support_cannot_seed_persistent_line(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    tuple(
        _block(
            memory,
            block_id=f"B{index}",
            day=index * 10,
            evidence_id="RAW-SAME",
        )
        for index in range(3)
    )
    _rebuild(memory)
    store = LineGraphStore(tmp_path / "lines")
    runtime = TrajectoryRuntime(
        memory=memory,
        line_store=store,
        trajectory_config=TrajectoryConfig(
            k=2,
            min_similarity=0.5,
            min_support=3,
        ),
        neighbour_provider=_ChainProvider(),
    )

    result = runtime.bootstrap(
        knowledge_cutoff=BASE + timedelta(days=40)
    )

    assert result.candidate_paths
    assert result.authority_decisions
    assert all(
        decision.status == "UNRESOLVED"
        for decision in result.authority_decisions
    )
    assert store.list_lines() == ()
    runtime.close()
    store.close()


def test_independent_raw_support_certifies_seed_without_scalar_score(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    tuple(
        _block(
            memory,
            block_id=f"B{index}",
            day=index * 10,
            evidence_id=f"E{index}",
        )
        for index in range(3)
    )
    _rebuild(memory)
    store = LineGraphStore(tmp_path / "lines")
    runtime = TrajectoryRuntime(
        memory=memory,
        line_store=store,
        trajectory_config=TrajectoryConfig(
            k=2,
            min_similarity=0.5,
            min_support=3,
        ),
        neighbour_provider=_ChainProvider(),
    )

    result = runtime.bootstrap(
        knowledge_cutoff=BASE + timedelta(days=40)
    )

    assert len(store.list_lines()) == 1
    converged = tuple(
        decision
        for decision in result.authority_decisions
        if decision.status == "CONVERGED"
    )
    assert converged
    winner = converged[0]
    assert winner.winner_id == store.list_lines()[0].line_id
    profile = winner.profile_for(winner.winner_id)
    assert profile is not None
    assert profile.independent_support == 3
    assert profile.derivation_stability == 1
    runtime.close()
    store.close()


def test_competing_line_identity_resolves_by_independent_support_dominance(
    tmp_path: Path,
) -> None:
    memory = InMemoryReferenceMemory()
    a = _block(memory, block_id="A", day=0, evidence_id="EA")
    b = _block(memory, block_id="B", day=10, evidence_id="EB")
    c = _block(memory, block_id="C", day=20, evidence_id="EC")
    d = _block(memory, block_id="D", day=30, evidence_id="ED")
    x = _block(memory, block_id="X", day=40, evidence_id="EX")
    cutoff = BASE + timedelta(days=50)

    store = LineGraphStore(tmp_path / "lines")
    seeder = LineAssembler(
        memory=memory,
        store=store,
        config=LineAssemblerConfig(
            min_seed_support=3,
            min_shared_support=3,
        ),
    )
    first = seeder.apply_path((a, b, c), knowledge_cutoff=cutoff)
    second = seeder.apply_path((b, c, d), knowledge_cutoff=cutoff)
    assert first.line_id is not None
    assert second.line_id is not None
    assert first.line_id != second.line_id

    runtime = TrajectoryRuntime(
        memory=memory,
        line_store=store,
        assembler_config=LineAssemblerConfig(
            min_seed_support=3,
            min_shared_support=2,
        ),
        neighbour_provider=_ChainProvider(),
    )
    decision = runtime.converge_path_identity(
        (a, b, c, x),
        knowledge_cutoff=cutoff,
    )

    assert decision.status == "CONVERGED"
    assert decision.winner_id == first.line_id
    first_profile = decision.profile_for(first.line_id)
    second_profile = decision.profile_for(second.line_id)
    assert first_profile is not None
    assert second_profile is not None
    assert first_profile.independent_support == 3
    assert second_profile.independent_support == 2

    applied = runtime.assembler.apply_path(
        (a, b, c, x),
        knowledge_cutoff=cutoff,
        resolved_line_id=decision.winner_id,
    )
    assert applied.line_id == first.line_id
    assert set(store.lines_for_block("X")) == {first.line_id}
    runtime.close()
    store.close()
