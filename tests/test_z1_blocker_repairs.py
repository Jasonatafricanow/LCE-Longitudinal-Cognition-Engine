from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lce.cognition.promotion import BoundedInterpretation, ConservativePromotionPolicy
from lce.reference_memory.contracts import AuthorizedSelectedSupport, RawEvidence
from lce.runtime import LceRuntime
from lce.structure.contracts import StructureConfig
from tests.fixtures.longitudinal_corpus import longitudinal_corpus


class SelectingInterpreter:
    def __init__(self, *, reordered: bool = False) -> None:
        self.reordered = reordered
        self.calls = 0
        self.packages = []

    def interpret(self, package):
        self.calls += 1
        self.packages.append(package)
        ids = package.candidate.supporting_block_ids
        selected_ids = tuple(reversed(ids[-2:])) if self.reordered and len(ids) >= 2 else (ids[-1],)
        selected = tuple(
            AuthorizedSelectedSupport(
                block_id=block_id,
                state_id=next(block.state_id for block in package.semantic_blocks if block.block_id == block_id),
            )
            for block_id in selected_ids
        )
        return BoundedInterpretation(
            content="selected: " + ",".join(selected_ids),
            supporting_block_ids=selected_ids,
            selected_support=selected,
            model_trace={"provider": "selection-test", "model": "v1"},
        )


def _single_cycle_policy() -> ConservativePromotionPolicy:
    return ConservativePromotionPolicy(min_blocks=1, min_structures=1, min_support_cycles=1)


def _revision_signature(runtime: LceRuntime) -> tuple[object, ...]:
    return tuple(
        (
            region,
            tuple(
                (
                    item.revision_number,
                    item.content,
                    item.supporting_memory_ids,
                    item.supporting_state_ids,
                    item.selected_support,
                    item.previous_baseline_id,
                )
                for item in runtime.baselines.get_history(region).revisions
            ),
        )
        for region in runtime.baselines.list_regions()
    )


def _worktree_signature(runtime: LceRuntime) -> tuple[object, ...]:
    return tuple(
        (
            item.region_id,
            item.candidate_content,
            item.supporting_block_ids,
            item.selected_support,
            item.status,
            item.merged_baseline_id == (runtime.baselines.get_head(item.region_id).baseline_id if item.status == "MERGED" else None),
            runtime.worktrees.support_cycle_count(item.worktree_id),
        )
        for item in runtime.worktrees.list()
    )


@pytest.mark.parametrize("reordered", [False, True])
def test_selected_subset_and_reordered_support_survives_restart(tmp_path, reordered: bool) -> None:
    interpreter = SelectingInterpreter(reordered=reordered)
    runtime = LceRuntime(
        tmp_path / "run",
        lineage_id="selection",
        interpreter=interpreter,
        policy=_single_cycle_policy(),
    )
    runtime.run_batch(longitudinal_corpus()[:4])
    assert runtime.baselines.list_regions()
    for region in runtime.baselines.list_regions():
        baseline = runtime.baselines.get_head(region)
        assert baseline is not None
        assert tuple(item.block_id for item in baseline.selected_support) == baseline.supporting_memory_ids
        assert tuple(item.state_id for item in baseline.selected_support) == baseline.supporting_state_ids
        for item in baseline.selected_support:
            assert runtime.memory.get_semantic_block_state(item.state_id).block_id == item.block_id
    expected = {
        region: runtime.baselines.get_head(region).selected_support
        for region in runtime.baselines.list_regions()
    }
    runtime.close()

    reopened = LceRuntime(tmp_path / "run", lineage_id="selection", policy=_single_cycle_policy())
    for region, selected in expected.items():
        assert reopened.baselines.get_head(region).selected_support == selected
    assert reopened.query(None)
    assert all(
        view.supporting_semantic_block_state_ids
        and len(view.supporting_semantic_block_ids) == len(view.supporting_semantic_block_state_ids)
        for view in reopened.query(None)
    )
    reopened.close()


def test_selected_and_unselected_source_invalidation_are_distinct(tmp_path) -> None:
    interpreter = SelectingInterpreter()
    runtime = LceRuntime(
        tmp_path / "selected",
        lineage_id="selection",
        interpreter=interpreter,
        policy=_single_cycle_policy(),
    )
    runtime.run_batch(longitudinal_corpus()[:4])
    region = runtime.baselines.list_regions()[0]
    baseline = runtime.baselines.get_head(region)
    assert baseline is not None
    selected_source = runtime.memory.get_semantic_block_state(baseline.selected_support[0].state_id).raw_evidence_ids[0]
    runtime.memory.invalidate(selected_source, reason="selected-source-test")
    assert all(view.region_id != region for view in runtime.query(None))
    runtime.close()

    unselected_runtime = LceRuntime(
        tmp_path / "unselected",
        lineage_id="selection",
        interpreter=SelectingInterpreter(),
        policy=_single_cycle_policy(),
    )
    unselected_runtime.run_batch(longitudinal_corpus()[:4])
    region = unselected_runtime.baselines.list_regions()[0]
    baseline = unselected_runtime.baselines.get_head(region)
    assert baseline is not None
    selected_sources = {
        source
        for item in baseline.selected_support
        for source in unselected_runtime.memory.get_semantic_block_state(item.state_id).raw_evidence_ids
    }
    unselected_source = next(
        evidence.evidence_id
        for evidence in unselected_runtime.memory.list_current_valid_evidence()
        if evidence.evidence_id not in selected_sources
    )
    unselected_runtime.memory.invalidate(unselected_source, reason="unselected-source-test")
    assert any(view.region_id == region for view in unselected_runtime.query(None))
    unselected_runtime.close()


def test_historical_selected_state_is_promoted_after_later_extension(tmp_path) -> None:
    runtime = LceRuntime(
        tmp_path / "run",
        lineage_id="history",
        policy=ConservativePromotionPolicy(min_blocks=99, min_structures=99, min_support_cycles=99),
    )
    corpus = longitudinal_corpus()
    runtime.run_batch(corpus[:4])
    t1 = max(runtime.discovery.snapshots.all_snapshots(), key=lambda item: item.cutoff)
    candidate = runtime.discovery.higher_order_candidates(t1)[0]
    t1_support = tuple(
        AuthorizedSelectedSupport(block_id=block.block_id, state_id=block.state_id or "")
        for block in t1.block_states
        if block.block_id in candidate.supporting_block_ids
    )
    runtime.process(corpus[4])
    worktree = runtime.worktrees.create(
        region_id="historical-test",
        candidate_content="historical understanding",
        supporting_block_ids=tuple(item.block_id for item in t1_support),
        supporting_structure_ids=candidate.supporting_structure_ids,
        base_baseline=None,
        selected_support=t1_support,
    )
    runtime.worktrees.record_support(worktree.worktree_id, snapshot_id=t1.snapshot_id)
    runtime.policy = _single_cycle_policy()
    runtime.promoter.policy = runtime.policy
    merged = runtime.promoter.evaluate(
        worktree.worktree_id,
        interpretation=BoundedInterpretation(
            content="historical understanding",
            supporting_block_ids=tuple(item.block_id for item in t1_support),
            selected_support=t1_support,
            model_trace={"provider": "history-test", "model": "v1"},
        ),
    )
    assert merged is not None
    assert merged.baseline.selected_support == t1_support
    assert all(
        source != "E5"
        for item in merged.baseline.selected_support
        for source in runtime.memory.get_semantic_block_state(item.state_id).raw_evidence_ids
    )
    runtime.close()


def test_post_commit_replay_reconciles_worktree_without_duplicate_revision(tmp_path) -> None:
    corpus = longitudinal_corpus()
    reference = LceRuntime(tmp_path / "reference", lineage_id="main")
    reference.run_batch(corpus[:5])
    expected_revisions = _revision_signature(reference)
    expected_worktrees = _worktree_signature(reference)
    reference.close()

    runtime = LceRuntime(tmp_path / "faulted", lineage_id="main")
    original = runtime.worktrees.set_status
    failed = False

    def fail_once(worktree_id: str, status: str, *, merged_baseline_id: str | None = None):
        nonlocal failed
        if status == "MERGED" and not failed:
            failed = True
            raise RuntimeError("post-commit worktree status fault")
        return original(worktree_id, status, merged_baseline_id=merged_baseline_id)

    runtime.worktrees.set_status = fail_once  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="post-commit worktree status fault"):
        runtime.run_batch(corpus[:5])
    runtime.close()

    reopened = LceRuntime(tmp_path / "faulted", lineage_id="main")
    reopened.run_batch(corpus[:5])
    assert _revision_signature(reopened) == expected_revisions
    assert _worktree_signature(reopened) == expected_worktrees
    assert all(item.status == "MERGED" for item in reopened.worktrees.list())
    reopened.close()


def test_completed_prefix_replay_is_cognitively_non_mutating(tmp_path) -> None:
    corpus = longitudinal_corpus()
    interpreter = SelectingInterpreter()
    runtime = LceRuntime(
        tmp_path / "run",
        lineage_id="replay",
        interpreter=interpreter,
        policy=_single_cycle_policy(),
    )
    runtime.run_batch(corpus[:5])
    before_revisions = _revision_signature(runtime)
    before_worktrees = _worktree_signature(runtime)
    before_calls = interpreter.calls
    runtime.close()

    replay_interpreter = SelectingInterpreter()
    reopened = LceRuntime(
        tmp_path / "run",
        lineage_id="replay",
        interpreter=replay_interpreter,
        policy=_single_cycle_policy(),
    )
    for material in corpus[:5]:
        reopened.process(material)
        assert _revision_signature(reopened) == before_revisions
        assert _worktree_signature(reopened) == before_worktrees
    reopened.run_batch(corpus[:5])
    assert _revision_signature(reopened) == before_revisions
    assert _worktree_signature(reopened) == before_worktrees
    assert replay_interpreter.calls == 0
    assert before_calls > 0
    reopened.close()


def test_pipeline_stage_does_not_regress_on_replay(tmp_path) -> None:
    runtime = LceRuntime(tmp_path / "run", lineage_id="stage")
    material = longitudinal_corpus()[0]
    runtime.process(material)
    assert runtime.memory.get_pipeline_progress(material.evidence_id) is not None
    assert runtime.memory.get_pipeline_progress(material.evidence_id)[0] == "complete"
    runtime.memory.mark_pipeline_stage(material.evidence_id, "compiled")
    assert runtime.memory.get_pipeline_progress(material.evidence_id)[0] == "complete"
    runtime.close()


def test_default_policy_local_correction_uses_valid_selected_state(tmp_path) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)

    def evidence(index: int, topic: str, vector: tuple[float, ...], *, recap: bool = False) -> RawEvidence:
        return RawEvidence(
            evidence_id=f"e{index}",
            content=f"observation {index}",
            occurred_at=base + timedelta(days=index),
            ordering_key=f"{index:04d}",
            provenance={
                "source": "z1-correction",
                "canonical": True,
                "topic": topic,
                "vector": vector,
                "recap": recap,
                **({"new_information": f"new relevant detail {index}"} if recap else {}),
            },
        )

    corpus = [
        evidence(1, "topic1", (1.0, 0.0, 0.0)),
        evidence(2, "topic2", (0.98, 0.12, 0.0)),
        evidence(3, "topic3", (0.99, 0.10, 0.0)),
        evidence(4, "topic4", (0.97, 0.20, 0.0)),
        evidence(5, "topic3", (0.99, 0.10, 0.0), recap=True),
        evidence(6, "topic3", (0.99, 0.10, 0.0), recap=True),
        evidence(7, "topic3", (0.99, 0.10, 0.0), recap=True),
    ]
    runtime = LceRuntime(
        tmp_path / "run",
        structure_config=StructureConfig(k_values=(2,), min_similarity=0.9),
    )
    runtime.run_batch(corpus[:4])
    for material in corpus[4:]:
        runtime.process(material)
    before = runtime.query(None)
    assert before
    old = before[0]
    assert old.revision_number == 2
    assert set(old.supporting_source_refs) == {f"e{index}" for index in range(1, 8)}
    old_baseline_id = old.baseline_id

    runtime.invalidate_and_rebuild("e7")
    assert all(view.baseline_id != old_baseline_id for view in runtime.query(None))
    assert any(item.status == "OPEN" and runtime.worktrees.support_cycle_count(item.worktree_id) == 1
               for item in runtime.worktrees.list())

    runtime.process(evidence(8, "topic2", (0.98, 0.12, 0.0), recap=True))
    corrected = next(view for view in runtime.query(None) if view.baseline_id != old_baseline_id)
    assert corrected.revision_number == 3
    assert "e7" not in corrected.supporting_source_refs
    assert "e8" in corrected.supporting_source_refs
    history = runtime.baselines.get_history(corrected.region_id)
    assert history.revisions[0].previous_baseline_id == old_baseline_id
    runtime.close()
