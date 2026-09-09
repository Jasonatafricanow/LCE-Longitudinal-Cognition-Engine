from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from lce.cognition.promotion import BoundedInterpretation, ConservativePromotionPolicy
from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.runtime import LceRuntime
from lce.semantic.compiler import SemanticCompiler
from lce.structure.discovery import SnapshotStructureDiscovery, StructureConfig
from lce.testing.reference_memory import InMemoryReferenceMemory
from tests.fixtures.longitudinal_corpus import longitudinal_corpus


def _evidence(evidence_id: str, when: datetime, *, vector: tuple[float, ...] | None = None) -> RawEvidence:
    provenance: dict[str, object] = {"source": "z0-test", "canonical": True}
    if vector is not None:
        provenance["vector"] = vector
    return RawEvidence(
        evidence_id=evidence_id,
        content=evidence_id,
        occurred_at=when,
        ordering_key=f"{when.isoformat()}:{evidence_id}",
        provenance=provenance,
    )


def _populate_pair_space(store: ReferenceMemoryStore, root_time: datetime) -> None:
    vectors = {
        "A": (1.0, 0.0),
        "B": (0.99, 0.05),
        "C": (0.98, 0.12),
        "D": (0.97, 0.2),
    }
    for index, (block_id, vector) in enumerate(vectors.items()):
        when = root_time + timedelta(days=index)
        evidence = _evidence(f"E-{block_id}", when)
        store.add_evidence(evidence)
        store.put_semantic_block(
            SemanticBlock(
                block_id=block_id,
                content=f"content {block_id}",
                raw_evidence_ids=(evidence.evidence_id,),
                occurred_start=when,
                occurred_end=when,
                compiler_version="z0-test",
                lineage_id="z0",
            )
        )
    store.rebuild_vector_index(lambda block: vectors[block.block_id], index_version="z0")


def test_historical_snapshot_rebuild_uses_immutable_block_state_and_vectors(tmp_path: Path) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    store = ReferenceMemoryStore(tmp_path / "memory")
    _populate_pair_space(store, base)
    discovery = SnapshotStructureDiscovery(
        store,
        tmp_path / "structures",
        config=StructureConfig(k_values=(2,), min_similarity=0.8, higher_order_similarity=0.8),
    )
    cutoff = base + timedelta(days=3)
    historical = discovery.create_snapshot(cutoff)
    candidates = discovery.higher_order_candidates(historical)
    assert candidates
    candidate = candidates[0]
    raw_before = discovery.expand_candidate_to_raw(candidate)
    state_before = historical.block_states

    later = base + timedelta(days=10)
    store.add_evidence(_evidence("E-later", later))
    store.extend_semantic_block("A", content="new continuation", evidence_id="E-later", occurred_at=later)
    store.rebuild_vector_index(lambda block: {"A": (1.0, 0.0), "B": (0.99, 0.05), "C": (0.98, 0.12), "D": (0.97, 0.2)}[block.block_id], index_version="z0")
    discovery.delete_derived_snapshots()
    rebuilt = discovery.create_snapshot(cutoff)
    assert rebuilt == historical
    assert all("E-later" not in block.raw_evidence_ids for block in rebuilt.block_states)
    assert discovery.expand_candidate_to_raw(candidate) == raw_before
    assert state_before == rebuilt.block_states
    store.close()


def test_accepted_baseline_provenance_keeps_the_promoted_block_state(tmp_path: Path) -> None:
    corpus = longitudinal_corpus()
    runtime = LceRuntime(
        tmp_path / "run",
        lineage_id="main",
        policy=ConservativePromotionPolicy(min_blocks=2, min_structures=2, min_support_cycles=1),
    )
    runtime.run_batch(corpus[:4])
    region = runtime.baselines.list_regions()[0]
    runtime.process(corpus[4])
    history = runtime.baselines.get_history(region)
    revision_one = next(revision for revision in history.revisions if revision.revision_number == 1)
    raw_refs = {
        source
        for state_id in revision_one.supporting_state_ids
        for source in runtime.memory.get_semantic_block_state(state_id).raw_evidence_ids
    }
    assert "E5" not in raw_refs
    runtime.close()


def test_invalidation_can_promote_only_a_new_valid_interpretation(tmp_path: Path) -> None:
    corpus = longitudinal_corpus()
    runtime = LceRuntime(
        tmp_path / "run",
        lineage_id="main",
        policy=ConservativePromotionPolicy(min_blocks=2, min_structures=2, min_support_cycles=1),
    )
    runtime.run_batch(corpus[:4])
    runtime.invalidate_and_rebuild("E2")
    assert runtime.query(None) == ()
    replacement = RawEvidence(
        evidence_id="E5",
        content="alpha new valid support",
        occurred_at=corpus[4].occurred_at,
        ordering_key="0004:E5",
        provenance={"source": "z0-test", "canonical": True, "topic": "alpha", "vector": (0.99, 0.11, 0.0)},
    )
    runtime.process(replacement)
    served = runtime.query(None)
    assert served
    assert all("E2" not in view.supporting_source_refs for view in served)
    assert all("corrected after invalidation" not in view.content for view in served)
    runtime.close()


def test_equivalent_local_observations_do_not_form_higher_order_candidate(tmp_path: Path) -> None:
    base = datetime(2026, 2, 1, tzinfo=UTC)
    store = ReferenceMemoryStore(tmp_path / "memory")
    for block_id in ("A", "B"):
        when = base
        evidence = _evidence("E-" + block_id, when)
        store.add_evidence(evidence)
        store.put_semantic_block(SemanticBlock(block_id, block_id, (evidence.evidence_id,), when, when, "z0", "z0"))
    store.rebuild_vector_index(lambda _block: (1.0, 0.0), index_version="z0")
    discovery = SnapshotStructureDiscovery(
        store, tmp_path / "structures", config=StructureConfig(k_values=(1, 2), min_similarity=0.9)
    )
    snapshot = discovery.create_snapshot(base)
    assert len([item for item in snapshot.structures if set(item.member_block_ids) == {"A", "B"}]) >= 2
    assert discovery.higher_order_candidates(snapshot) == ()
    store.close()


def test_candidate_support_ignores_unrelated_global_cutoff_but_accepts_new_relevant_state(tmp_path: Path) -> None:
    corpus = longitudinal_corpus()
    runtime = LceRuntime(
        tmp_path / "run",
        lineage_id="main",
        policy=ConservativePromotionPolicy(min_blocks=2, min_structures=2, min_support_cycles=3),
    )
    runtime.run_batch(corpus[:4])
    worktree = runtime.worktrees.list(status="OPEN")[0]
    support_before = runtime.worktrees.support_cycle_count(worktree.worktree_id)
    runtime.process(corpus[4])
    support_after_relevant = runtime.worktrees.support_cycle_count(worktree.worktree_id)
    assert support_after_relevant == support_before + 1
    assert runtime.worktrees.get(worktree.worktree_id).status == "OPEN"
    unrelated = RawEvidence(
        evidence_id="UNRELATED",
        content="unrelated",
        occurred_at=corpus[4].occurred_at + timedelta(days=1),
        ordering_key="0005~UNRELATED",
        provenance={"source": "z0-test", "canonical": True, "topic": "unrelated", "vector": (0.0, 0.0, 1.0)},
    )
    runtime.process(unrelated)
    assert runtime.worktrees.support_cycle_count(worktree.worktree_id) == support_after_relevant
    assert runtime.worktrees.get(worktree.worktree_id).status == "OPEN"
    runtime.close()


class RecordingInterpreter:
    def __init__(self, status: str = "PROPOSED", content: str | None = None) -> None:
        self.packages = []
        self.status = status
        self.content = content

    def interpret(self, package):
        self.packages.append(package)
        return BoundedInterpretation(
            content=self.content or "bounded: " + " | ".join(block.content for block in package.semantic_blocks),
            supporting_block_ids=package.candidate.supporting_block_ids,
            status=self.status,
            model_trace={"provider": "recording-test", "model": "v1"},
        )


def test_bounded_interpreter_receives_exact_package_and_read_never_calls_it(tmp_path: Path) -> None:
    interpreter = RecordingInterpreter()
    runtime = LceRuntime(tmp_path / "run", lineage_id="main", interpreter=interpreter)
    runtime.run_batch(longitudinal_corpus()[:4])
    assert interpreter.packages
    package = interpreter.packages[0]
    assert package.semantic_blocks
    assert package.authorized_source_refs == tuple(sorted({source for block in package.semantic_blocks for source in block.raw_evidence_ids}))
    calls = len(interpreter.packages)
    runtime.query(None)
    assert len(interpreter.packages) == calls
    runtime.close()


def test_unknown_interpretation_never_creates_worktree(tmp_path: Path) -> None:
    interpreter = RecordingInterpreter(status="UNKNOWN", content=None)
    runtime = LceRuntime(tmp_path / "run", lineage_id="main", interpreter=interpreter)
    runtime.run_batch(longitudinal_corpus()[:4])
    assert runtime.worktrees.list() == ()
    assert runtime.query(None) == ()
    runtime.close()


def test_independent_in_memory_substrate_runs_v1_pipeline(tmp_path: Path) -> None:
    memory = InMemoryReferenceMemory()
    runtime = LceRuntime(tmp_path / "run", memory=memory, lineage_id="main")
    runtime.run_batch(longitudinal_corpus()[:5])
    assert runtime.query(None)
    assert memory.vector_projection_ids()
    runtime.close()


def test_compiler_unit_failure_rolls_back_blocks_marker_and_checkpoint(tmp_path: Path) -> None:
    store = ReferenceMemoryStore(tmp_path / "memory")
    evidence = _evidence("E1", datetime(2026, 3, 1, tzinfo=UTC))
    compiler = SemanticCompiler(store, None, lineage_id="z0")
    original = store.commit_compilation

    def fail_once(**_kwargs: object) -> None:
        raise RuntimeError("commit fault")

    store.commit_compilation = fail_once  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="commit fault"):
        compiler.process(evidence)
    assert store.list_semantic_blocks(current_valid_only=False) == ()
    assert store.compiled_block_ids("E1") is None
    assert store.get_checkpoint("z0").last_ordering_key is None

    store.commit_compilation = original  # type: ignore[method-assign]
    result = compiler.process(evidence)
    assert result.block_ids
    assert store.get_pipeline_stage("E1") == "compiled"
    store.close()


def test_runtime_vector_failure_replays_downstream_without_duplicate_revision(tmp_path: Path) -> None:
    corpus = longitudinal_corpus()

    reference = LceRuntime(tmp_path / "reference", lineage_id="main")
    reference.run_batch(corpus[:5])
    expected = {
        region: tuple(
            (revision.revision_number, revision.content, revision.supporting_memory_ids, revision.previous_baseline_id)
            for revision in reference.baselines.get_history(region).revisions
        )
        for region in reference.baselines.list_regions()
    }
    reference.close()

    faulted = LceRuntime(tmp_path / "faulted", lineage_id="main")
    original = faulted.memory.rebuild_vector_index
    failed = False

    def fail_once(*args: object, **kwargs: object) -> None:
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("vector projection fault")
        original(*args, **kwargs)

    faulted.memory.rebuild_vector_index = fail_once  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="vector projection fault"):
        faulted.process(corpus[0])
    faulted.close()

    reopened = LceRuntime(tmp_path / "faulted", lineage_id="main")
    reopened.run_batch(corpus[:5])
    actual = {
        region: tuple(
            (revision.revision_number, revision.content, revision.supporting_memory_ids, revision.previous_baseline_id)
            for revision in reopened.baselines.get_history(region).revisions
        )
        for region in reopened.baselines.list_regions()
    }
    assert actual == expected
    assert reopened.memory.get_pipeline_stage("E1") == "complete"
    reopened.close()


def test_unchanged_snapshot_has_no_new_linked_structure_delta(tmp_path: Path) -> None:
    base = datetime(2026, 4, 1, tzinfo=UTC)
    store = ReferenceMemoryStore(tmp_path / "memory")
    _populate_pair_space(store, base)
    discovery = SnapshotStructureDiscovery(
        store, tmp_path / "structures", config=StructureConfig(k_values=(2,), min_similarity=0.8)
    )
    first = discovery.create_snapshot(base + timedelta(days=3))
    second = discovery.create_snapshot(base + timedelta(days=3))
    assert discovery.diff(first, second).linked_structures == ()
    store.close()
