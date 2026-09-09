from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from lce.cognition.promotion import BoundedInterpretation, BoundedInterpretationPackage
from lce.cognition.worktree import CognitionWorktree
from lce.reference_memory.contracts import RawEvidence
from lce.runtime import LceRuntime
from lce.structure.contracts import StructureConfig

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
FOUR_BLOCK_CONFIG = StructureConfig(k_values=(2,), min_similarity=0.9)


def _evidence(
    evidence_id: str,
    index: int,
    topic: str,
    vector: tuple[float, ...],
    *,
    recap: bool = False,
    new_information: str | None = None,
    content: str | None = None,
) -> RawEvidence:
    provenance: dict[str, object] = {
        "source": "lce-v1-closure-tests",
        "canonical": True,
        "topic": topic,
        "vector": vector,
        "recap": recap,
    }
    if new_information is not None:
        provenance["new_information"] = new_information
    return RawEvidence(
        evidence_id=evidence_id,
        content=content or f"observation {index}",
        occurred_at=BASE_TIME + timedelta(days=index),
        ordering_key=f"{index:04d}:{evidence_id}",
        provenance=provenance,
    )


def _b4_corpus() -> tuple[RawEvidence, ...]:
    vectors = ((1.0, 0.0), (0.99, 0.05), (0.98, 0.12), (0.97, 0.2))
    originals = tuple(
        _evidence(f"E{index}", index, f"matter-{index}", vector)
        for index, vector in enumerate(vectors, start=1)
    )
    return originals + (
        _evidence("E5", 5, "matter-4", vectors[3], recap=True),
        _evidence("E6", 6, "matter-4", vectors[3], recap=True),
        _evidence("E7", 7, "matter-4", vectors[3], recap=True),
        _evidence(
            "E8",
            8,
            "matter-4",
            vectors[3],
            recap=True,
            new_information="genuinely new candidate-relevant measurement",
        ),
    )


def _single_worktree(runtime: LceRuntime) -> CognitionWorktree:
    worktrees = runtime.worktrees.list()
    assert len(worktrees) == 1
    return worktrees[0]


def test_b4_pure_recap_does_not_advance_support_but_relevant_change_does(tmp_path: Path) -> None:
    """A state-version/provenance change is not a new qualifying support cycle."""
    corpus = _b4_corpus()
    runtime = LceRuntime(tmp_path / "run", structure_config=FOUR_BLOCK_CONFIG)
    runtime.run_batch(corpus[:4])

    before = _single_worktree(runtime)
    assert runtime.worktrees.support_cycle_count(before.worktree_id) == 1
    assert before.status == "OPEN"
    assert runtime.baselines.list_regions() == ()
    original_state = before.selected_support[0].state_id
    original_state_count = len(runtime.memory.list_semantic_block_states(current_valid_only=False))

    runtime.close()
    runtime = LceRuntime(tmp_path / "run", structure_config=FOUR_BLOCK_CONFIG)
    for material in corpus[4:7]:
        runtime.process(material)
        current = _single_worktree(runtime)
        assert runtime.worktrees.support_cycle_count(current.worktree_id) == 1
        assert current.status == "OPEN"
        assert runtime.baselines.list_regions() == ()

    current = _single_worktree(runtime)
    assert len(runtime.memory.list_semantic_block_states(current_valid_only=False)) > original_state_count
    current_state = runtime.memory.get_semantic_block_state(current.selected_support[0].state_id)
    assert current_state.state_id != original_state
    assert current_state.raw_evidence_ids == ("E4", "E5", "E6", "E7")
    assert runtime.worktrees.support_identities(current.worktree_id)

    runtime.process(corpus[7])
    assert runtime.baselines.list_regions()
    region = runtime.baselines.list_regions()[0]
    head = runtime.baselines.get_head(region)
    assert head is not None
    assert head.revision_number == 1
    merged = runtime.worktrees.list(status="MERGED")
    assert len(merged) == 1
    assert runtime.worktrees.support_cycle_count(merged[0].worktree_id) == 2
    runtime.close()


@pytest.mark.parametrize(
    "event_kind",
    (
        "restart",
        "completed replay",
        "duplicate source",
        "unrelated point",
        "duplicate local-structure observation",
        "unchanged global snapshot",
        "pure recap",
        "multiple pure recaps",
    ),
)
def test_b4_retained_inflation_events_do_not_change_qualifying_support(
    tmp_path: Path, event_kind: str
) -> None:
    corpus = _b4_corpus()
    runtime = LceRuntime(tmp_path / "run", structure_config=FOUR_BLOCK_CONFIG)
    runtime.run_batch(corpus[:4])
    before = _single_worktree(runtime)
    before_support = runtime.worktrees.support_cycle_count(before.worktree_id)
    before_identities = runtime.worktrees.support_identities(before.worktree_id)
    before_head = tuple(runtime.baselines.get_history(region).revisions for region in runtime.baselines.list_regions())

    if event_kind == "restart":
        runtime.close()
        runtime = LceRuntime(tmp_path / "run", structure_config=FOUR_BLOCK_CONFIG)
    elif event_kind == "completed replay":
        runtime.run_batch(corpus[:4])
    elif event_kind == "duplicate source":
        runtime.process(corpus[3])
    elif event_kind == "unrelated point":
        runtime.process(_evidence("UNRELATED", 5, "unrelated", (0.0, 0.0)))
    elif event_kind == "duplicate local-structure observation":
        runtime.process(
            _evidence(
                "E-DUP-LOCAL",
                5,
                "matter-4",
                (0.97, 0.2),
                content="observation 4",
            )
        )
    elif event_kind == "unchanged global snapshot":
        runtime.process(_evidence("GLOBAL-CHURN", 5, "global-only", (0.0, 0.0)))
    elif event_kind == "pure recap":
        runtime.process(corpus[4])
    elif event_kind == "multiple pure recaps":
        runtime.run_batch(corpus[4:7])
    else:
        raise AssertionError(event_kind)

    after = _single_worktree(runtime)
    assert runtime.worktrees.support_cycle_count(after.worktree_id) == before_support
    assert runtime.worktrees.support_identities(after.worktree_id) == before_identities
    assert runtime.baselines.list_regions() == ()
    assert tuple(runtime.baselines.get_history(region).revisions for region in runtime.baselines.list_regions()) == before_head
    runtime.close()


def test_completed_replay_after_newer_cognition_is_non_mutating(tmp_path: Path) -> None:
    corpus = _b4_corpus()
    runtime = LceRuntime(tmp_path / "run", structure_config=FOUR_BLOCK_CONFIG)
    runtime.run_batch(corpus)
    expected = _durable_signature(runtime)
    runtime.close()

    replay_interpreter = _CountingReferenceInterpreter()
    reopened = LceRuntime(
        tmp_path / "run",
        structure_config=FOUR_BLOCK_CONFIG,
        interpreter=replay_interpreter,
    )
    for material in corpus:
        reopened.process(material)
    for prefix in range(1, len(corpus) + 1):
        reopened.run_batch(corpus[:prefix])
    reopened.run_batch(corpus)
    assert _durable_signature(reopened) == expected
    assert replay_interpreter.calls == 0
    reopened.close()


def _durable_signature(runtime: LceRuntime) -> tuple[object, ...]:
    histories: list[object] = []
    baseline_numbers: dict[str, tuple[str, int]] = {}
    for region in runtime.baselines.list_regions():
        for revision in runtime.baselines.get_history(region).revisions:
            baseline_numbers[revision.baseline_id] = (region, revision.revision_number)
    for region in runtime.baselines.list_regions():
        revisions = []
        for revision in sorted(runtime.baselines.get_history(region).revisions, key=lambda item: item.revision_number):
            previous = baseline_numbers.get(revision.previous_baseline_id or "")
            revisions.append(
                (
                    revision.revision_number,
                    revision.content,
                    revision.supporting_memory_ids,
                    revision.supporting_state_ids,
                    tuple((item.block_id, item.state_id) for item in revision.selected_support),
                    previous[1] if previous else None,
                )
            )
        histories.append((region, tuple(revisions)))

    worktrees = []
    for index, item in enumerate(
        sorted(runtime.worktrees.list(), key=lambda value: (value.region_id, value.created_at, value.worktree_id))
    ):
        merged = baseline_numbers.get(item.merged_baseline_id or "")
        worktrees.append(
            (
                f"worktree-{index}",
                item.region_id,
                item.candidate_content,
                item.supporting_block_ids,
                item.supporting_structure_ids,
                item.status,
                item.base_revision,
                merged[1] if merged else None,
                tuple((value.block_id, value.state_id) for value in item.selected_support),
                runtime.worktrees.support_identities(item.worktree_id),
            )
        )

    blocks = tuple(
        (
            item.block_id,
            item.content,
            item.raw_evidence_ids,
            item.state_id,
            item.state_version,
            item.occurred_start,
            item.occurred_end,
            tuple(sorted(item.metadata.items())),
        )
        for item in runtime.memory.list_semantic_block_states(current_valid_only=False)
    )
    vectors = tuple(
        (
            item.block_id,
            runtime.memory.get_vector(item.block_id, state_id=item.state_id).values,
            runtime.memory.get_vector(item.block_id, state_id=item.state_id).index_version,
        )
        for item in runtime.memory.list_semantic_blocks(current_valid_only=True)
    )
    snapshots = tuple(
        (
            snapshot.snapshot_id,
            snapshot.cutoff,
            snapshot.visible_block_ids,
            tuple(
                (
                    structure.structure_id,
                    structure.center_block_id,
                    structure.member_block_ids,
                    structure.k,
                )
                for structure in snapshot.structures
            ),
            tuple((block.block_id, block.state_id, block.raw_evidence_ids) for block in snapshot.block_states),
            tuple(sorted(snapshot.vectors.items())),
        )
        for snapshot in runtime.discovery.snapshots.all_snapshots()
    )
    candidates = tuple(
        (
            candidate.candidate_id,
            candidate.snapshot_id,
            candidate.supporting_structure_ids,
            candidate.supporting_block_ids,
            candidate.relation_type,
        )
        for snapshot in runtime.discovery.snapshots.all_snapshots()
        for candidate in runtime.discovery.higher_order_candidates(snapshot)
    )
    accepted = tuple(
        (
            view.region_id,
            view.content,
            view.revision_number,
            view.supporting_semantic_block_ids,
            view.supporting_semantic_block_state_ids,
            view.supporting_source_refs,
            view.status,
        )
        for view in runtime.query(None)
    )
    return (tuple(histories), tuple(worktrees), blocks, vectors, snapshots, candidates, accepted)


class _CountingReferenceInterpreter:
    def __init__(self) -> None:
        self.calls = 0
        self.packages: list[object] = []

    def interpret(self, package: BoundedInterpretationPackage) -> BoundedInterpretation:
        self.calls += 1
        self.packages.append(package)
        return BoundedInterpretation(
            content="reference interpretation",
            supporting_block_ids=package.candidate.supporting_block_ids,
            model_trace={"provider": "closure-test", "model": "deterministic"},
        )
