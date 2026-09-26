from __future__ import annotations

from dataclasses import replace

from research.experiments.worktree_snake_replay_20260926 import experiment as exp


def _shape(run: exp.SimulationResult) -> tuple[object, ...]:
    return (
        tuple(
            (
                b.branch_id,
                b.worktree_id,
                tuple(b.support_ids),
                tuple(sorted(b.envelope)),
            )
            for b in run.branches
        ),
        tuple(
            (
                r.point_id,
                r.worktree_id,
                r.envelope_candidates,
                r.point_candidates,
                r.accepted_branches,
            )
            for r in run.records
        ),
        run.residual_ids,
    )


def test_gold_labels_are_evaluator_only(monkeypatch) -> None:
    original = exp.corpus()
    baseline_run = exp.simulate(0.40)

    scrambled = tuple(
        replace(point, gold_branches=frozenset({"FAKE"} if point.gold_branches else ()))
        for point in original
    )
    monkeypatch.setattr(exp, "corpus", lambda: scrambled)
    scrambled_run = exp.simulate(0.40)

    assert _shape(baseline_run) == _shape(scrambled_run)


def test_branch_envelope_grows_instead_of_replacing_old_semantics() -> None:
    branch = exp.BranchState("B", "WT", 0)
    allowed = frozenset({"application", "interview", "contract"})
    p1 = exp.SemanticPoint("p1", 1, "applied", frozenset({"application"}))
    p2 = exp.SemanticPoint("p2", 2, "interviewed", frozenset({"interview"}))
    p3 = exp.SemanticPoint("p3", 3, "contract", frozenset({"contract"}))

    branch.add(p1, scoring_features=allowed)
    assert branch.envelope == frozenset({"application"})
    branch.add(p2, scoring_features=allowed)
    branch.add(p3, scoring_features=allowed)

    assert branch.envelope == frozenset({"application", "interview", "contract"})


def test_one_point_can_match_multiple_live_branches() -> None:
    weights = {"offer": 1.0, "compensation": 1.0, "retention": 1.0}
    point = exp.SemanticPoint(
        "p",
        10,
        "matched offer",
        frozenset({"offer", "compensation", "retention"}),
    )
    leave = exp.BranchState("leave", "WT", 0)
    stay = exp.BranchState("stay", "WT", 0)
    leave.feature_counts.update({"offer": 1, "compensation": 1})
    stay.feature_counts.update({"compensation": 1, "retention": 1})

    assert exp._branch_envelope_score(leave, point, weights) >= 2 / 3
    assert exp._branch_envelope_score(stay, point, weights) >= 2 / 3


def test_time_is_ordering_not_a_hard_retrieval_cutoff() -> None:
    run = exp.simulate(0.30)
    records = {record.point_id: record for record in run.records}

    # j11 arrives 55+ days after the previous explicit external-offer evidence.
    # The algorithm still evaluates all live WT_JOB branches; there is no day-window rejection.
    j11 = records["j11"]
    assert j11.worktree_id == "WT_JOB"
    assert any(branch.worktree_id == "WT_JOB" and branch.created_step < j11.step for branch in run.branches)


def test_point_cloud_can_bootstrap_multiple_branches_under_one_worktree() -> None:
    run = exp.simulate(0.30)
    job_branches = [branch for branch in run.branches if branch.worktree_id == "WT_JOB"]

    assert len(job_branches) >= 2


def test_benchmark_reports_recall_without_asserting_success() -> None:
    report = exp.benchmark()

    assert report["corpus"]["gold_branches"] == 6
    assert len(report["runs"]) == 4
    for run in report["runs"]:
        assert 0.0 <= run["envelope_candidate_recall"] <= 1.0
        assert 0.0 <= run["point_candidate_recall"] <= 1.0
        assert 0.0 <= run["seed_coverage"] <= 1.0
        assert 0.0 <= run["false_candidate_fraction"] <= 1.0
