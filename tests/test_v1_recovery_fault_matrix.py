from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from lce.cognition.promotion import BoundedInterpretation, BoundedInterpretationPackage
from lce.reference_memory.contracts import RawEvidence
from lce.runtime import LceRuntime
from lce.structure.contracts import StructureConfig

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
FAULT_CONFIG = StructureConfig(k_values=(2,), min_similarity=0.8, higher_order_similarity=0.8)


class PackageSensitiveInterpreter:
    """Deterministic contract fixture; it has no access to Memory or a model API."""

    def __init__(self) -> None:
        self.calls = 0
        self.packages: list[BoundedInterpretationPackage] = []

    def interpret(self, package: BoundedInterpretationPackage) -> BoundedInterpretation:
        self.calls += 1
        self.packages.append(package)
        prefix = (
            "reference interpretation"
            if package.previous_baseline is None
            else "comparison against previous understanding"
        )
        content = prefix + ": " + " | ".join(block.content for block in package.semantic_blocks)
        return BoundedInterpretation(
            content=content,
            supporting_block_ids=package.candidate.supporting_block_ids,
            model_trace={"provider": "closure-package-fixture", "model": "deterministic-v1"},
        )


def _fault_corpus() -> tuple[RawEvidence, ...]:
    vectors = ((1.0, 0.0), (0.99, 0.05), (0.98, 0.12), (0.97, 0.2))
    originals = tuple(
        RawEvidence(
            evidence_id=f"Z{index}",
            content=f"matter-{index} original observation",
            occurred_at=BASE_TIME + timedelta(days=index),
            ordering_key=f"{index:04d}",
            provenance={
                "source": "lce-v1-fault-matrix",
                "canonical": True,
                "topic": f"matter-{index}",
                "vector": vector,
            },
        )
        for index, vector in enumerate(vectors, start=1)
    )
    informative = RawEvidence(
        evidence_id="Z5",
        content="matter-1 substantial additional information",
        occurred_at=BASE_TIME + timedelta(days=5),
        ordering_key="0005",
        provenance={
            "source": "lce-v1-fault-matrix",
            "canonical": True,
            "topic": "matter-1",
            "recap": True,
            "new_information": "additional relevant measurement",
            "vector": vectors[0],
        },
    )
    return originals + (informative,)


INJECTION_CASES = tuple(
    (method + "-" + when, target, method, index, when, None)
    for method, target, index in (
        ("_write_current_state", "memory", 0),
        ("_save_checkpoint", "memory", 0),
        ("commit_compilation", "memory", 0),
        ("rebuild_vector_index", "memory", 0),
        ("create_snapshot", "discovery", 3),
        ("save", "snapshot_store", 3),
        ("create", "worktrees", 3),
        ("record_support", "worktrees", 4),
        ("save_revision", "baselines", 4),
        ("set_status", "worktrees", 4),
    )
    for when in ("before", "after")
) + tuple(
    (stage + "-" + when, "memory", "mark_pipeline_stage", 4, when, stage)
    for stage in (
        "vector-ready",
        "snapshot/discovery-evaluated",
        "worktree-support-evaluated",
        "promotion-evaluated",
        "complete",
    )
    for when in ("before", "after")
)


def _install_fault(runtime: LceRuntime, target: str, method: str, when: str, stage: str | None, name: str) -> dict[str, bool]:
    target_object: Any = {
        "memory": runtime.memory,
        "discovery": runtime.discovery,
        "snapshot_store": runtime.discovery.snapshots,
        "worktrees": runtime.worktrees,
        "baselines": runtime.baselines,
    }[target]
    original = getattr(target_object, method)
    fired = {"value": False}

    def wrapper(*args: object, **kwargs: object) -> object:
        matches = stage is None or (len(args) > 1 and args[1] == stage)
        if not fired["value"] and matches:
            fired["value"] = True
            if when == "after":
                original(*args, **kwargs)
            raise RuntimeError(f"injected closure fault: {name}")
        return original(*args, **kwargs)

    setattr(target_object, method, wrapper)
    return fired


def _durable_signature(
    runtime: LceRuntime,
    interpreter: PackageSensitiveInterpreter,
    prior_interpreter: PackageSensitiveInterpreter | None = None,
) -> tuple[object, ...]:
    baseline_numbers: dict[str, tuple[str, int]] = {}
    for region in runtime.baselines.list_regions():
        for revision in runtime.baselines.get_history(region).revisions:
            baseline_numbers[revision.baseline_id] = (region, revision.revision_number)

    histories = []
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
    for ordinal, item in enumerate(
        sorted(runtime.worktrees.list(), key=lambda value: (value.region_id, value.created_at, value.worktree_id))
    ):
        merged = baseline_numbers.get(item.merged_baseline_id or "")
        worktrees.append(
            (
                f"worktree-{ordinal}",
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

    states = tuple(
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
                (structure.structure_id, structure.center_block_id, structure.member_block_ids, structure.k)
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
    prior_packages = prior_interpreter.packages if prior_interpreter is not None else ()
    calls = tuple(
        (
            package.candidate.candidate_id,
            package.previous_baseline.revision_number if package.previous_baseline else None,
        )
        for package in (*prior_packages, *interpreter.packages)
    )
    return (
        tuple(histories),
        tuple(worktrees),
        states,
        vectors,
        snapshots,
        candidates,
        accepted,
        (prior_interpreter.calls if prior_interpreter is not None else 0) + interpreter.calls,
        calls,
    )


def _run_reference(corpus: tuple[RawEvidence, ...], root: Path) -> tuple[tuple[object, ...], int]:
    interpreter = PackageSensitiveInterpreter()
    runtime = LceRuntime(root, structure_config=FAULT_CONFIG, interpreter=interpreter)
    runtime.run_batch(corpus)
    signature = _durable_signature(runtime, interpreter)
    calls = interpreter.calls
    runtime.close()
    return signature, calls


@pytest.mark.parametrize(
    "name,target,method,index,when,stage",
    INJECTION_CASES,
    ids=[case[0] for case in INJECTION_CASES],
)
def test_b7_fault_matrix_recovery_is_durably_equivalent(
    tmp_path: Path,
    name: str,
    target: str,
    method: str,
    index: int,
    when: str,
    stage: str | None,
) -> None:
    corpus = _fault_corpus()
    expected, expected_calls = _run_reference(corpus, tmp_path / "reference")
    interpreter = PackageSensitiveInterpreter()
    runtime = LceRuntime(tmp_path / "faulted", structure_config=FAULT_CONFIG, interpreter=interpreter)
    for material in corpus[:index]:
        runtime.process(material)
    fired = _install_fault(runtime, target, method, when, stage, name)
    with pytest.raises(RuntimeError, match="injected closure fault"):
        runtime.process(corpus[index])
    assert fired["value"] is True
    runtime.close()

    recovered_interpreter = PackageSensitiveInterpreter()
    reopened = LceRuntime(
        tmp_path / "faulted",
        structure_config=FAULT_CONFIG,
        interpreter=recovered_interpreter,
    )
    reopened.run_batch(corpus[index:])
    actual = _durable_signature(reopened, recovered_interpreter, interpreter)
    assert actual == expected
    assert actual[-2] == expected_calls
    reopened.close()


def _recover_named_case(tmp_path: Path, stage: str) -> tuple[tuple[object, ...], tuple[object, ...], PackageSensitiveInterpreter, LceRuntime]:
    corpus = _fault_corpus()
    reference_interpreter = PackageSensitiveInterpreter()
    reference = LceRuntime(tmp_path / "reference", structure_config=FAULT_CONFIG, interpreter=reference_interpreter)
    reference.run_batch(corpus)
    expected = _durable_signature(reference, reference_interpreter)
    reference.close()

    fault_interpreter = PackageSensitiveInterpreter()
    faulted = LceRuntime(tmp_path / "faulted", structure_config=FAULT_CONFIG, interpreter=fault_interpreter)
    faulted.run_batch(corpus[:4])
    _install_fault(faulted, "worktrees" if stage == "merged" else "memory", "set_status" if stage == "merged" else "mark_pipeline_stage", "after", stage if stage != "merged" else None, stage)
    with pytest.raises(RuntimeError, match="injected closure fault"):
        faulted.process(corpus[4])
    faulted.close()
    recovered_interpreter = PackageSensitiveInterpreter()
    reopened = LceRuntime(tmp_path / "faulted", structure_config=FAULT_CONFIG, interpreter=recovered_interpreter)
    reopened.process(corpus[4])
    return expected, _durable_signature(reopened, recovered_interpreter, fault_interpreter), recovered_interpreter, reopened


def test_b7_already_merged_recovery_finishes_without_reinterpretation(tmp_path: Path) -> None:
    expected, actual, interpreter, runtime = _recover_named_case(tmp_path, "merged")
    assert actual == expected
    assert interpreter.calls == 0
    assert runtime.memory.get_pipeline_stage("Z5") == "complete"
    assert not runtime.worktrees.list(status="OPEN")
    assert all(item.status == "MERGED" for item in runtime.worktrees.list())
    runtime.close()


def test_b7_promotion_evaluated_recovery_finishes_without_reinterpretation(tmp_path: Path) -> None:
    expected, actual, interpreter, runtime = _recover_named_case(tmp_path, "promotion-evaluated")
    assert actual == expected
    assert interpreter.calls == 0
    assert runtime.memory.get_pipeline_stage("Z5") == "complete"
    assert not runtime.worktrees.list(status="OPEN")
    assert all(item.status == "MERGED" for item in runtime.worktrees.list())
    runtime.close()
