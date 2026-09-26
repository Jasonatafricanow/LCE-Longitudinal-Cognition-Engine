"""Chronological replay experiment for Point Cloud -> Worktree -> Snake growth.

This is deliberately a research prototype, not production LCE code.

The experiment isolates the architectural question raised after Issues #25/#26:
whether an already-growing cognition branch is a better retrieval target than
pairwise old-point lookup, while allowing multiple simultaneous branches and
leaving unmatched points in a residual point cloud.

Gold branch labels exist only in the evaluator. The replay algorithm never reads
them when routing, retrieving, seeding, or assimilating points.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True, slots=True)
class SemanticPoint:
    point_id: str
    day: int
    text: str
    features: frozenset[str]
    gold_branches: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class WorktreeBaseline:
    worktree_id: str
    context_features: frozenset[str]


@dataclass(slots=True)
class BranchState:
    branch_id: str
    worktree_id: str
    created_step: int
    support_ids: list[str] = field(default_factory=list)
    feature_counts: Counter[str] = field(default_factory=Counter)

    def add(self, point: SemanticPoint, *, scoring_features: frozenset[str]) -> None:
        if point.point_id in self.support_ids:
            return
        self.support_ids.append(point.point_id)
        self.feature_counts.update(feature for feature in point.features if feature in scoring_features)

    @property
    def envelope(self) -> frozenset[str]:
        return frozenset(self.feature_counts)


@dataclass(frozen=True, slots=True)
class RetrievalRecord:
    step: int
    point_id: str
    day: int
    worktree_id: str | None
    gold_branches: frozenset[str]
    envelope_candidates: tuple[str, ...]
    point_candidates: tuple[str, ...]
    accepted_branches: tuple[str, ...]
    branch_sizes_before: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class SimulationResult:
    threshold: float
    branches: tuple[BranchState, ...]
    records: tuple[RetrievalRecord, ...]
    residual_ids: tuple[str, ...]
    branch_alignment: dict[str, str | None]
    summary: dict[str, object]


CONTEXT_FEATURES = frozenset(
    {
        "ctx_job",
        "ctx_home",
        "ctx_arch",
        "decision_open",
        "timeline_marker",
    }
)


def _p(
    point_id: str,
    day: int,
    text: str,
    features: Iterable[str],
    gold: Iterable[str] = (),
) -> SemanticPoint:
    return SemanticPoint(point_id, day, text, frozenset(features), frozenset(gold))


def corpus() -> tuple[SemanticPoint, ...]:
    """Fresh chronological corpus with three independent branching worktrees.

    The examples are intentionally varied in surface wording.  The structured
    feature sets stand in for semantic compilation / embedding output so this
    experiment measures stateful longitudinal retrieval rather than language
    model quality.
    """

    items = [
        # Job decision baseline and two simultaneously live futures.
        _p("j00", 0, "I am reassessing whether to stay in my current job.", ["ctx_job", "decision_open"]),
        _p("j01", 3, "Management friction made me start browsing other roles.", ["ctx_job", "management_conflict", "external_search", "browsing"], ["JOB_LEAVE"]),
        _p("j02", 9, "I updated my resume and sent applications.", ["ctx_job", "resume", "application", "external_search"], ["JOB_LEAVE"]),
        _p("j03", 12, "My manager raised the possibility of a promotion to retain me.", ["ctx_job", "promotion", "retention", "manager_support"], ["JOB_STAY"]),
        _p("j04", 18, "Finance approved a larger salary budget for my role.", ["ctx_job", "raise", "compensation", "retention"], ["JOB_STAY"]),
        _p("n01", 20, "I replaced the battery in my phone.", ["device", "battery"]),
        _p("j05", 27, "A recruiter booked a first interview.", ["ctx_job", "recruiter", "interview", "external_search"], ["JOB_LEAVE"]),
        _p("j06", 34, "The internal promotion now includes ownership of a new project.", ["ctx_job", "promotion", "internal_role", "career_growth"], ["JOB_STAY"]),
        _p("j07", 43, "The outside company asked for salary expectations after the technical round.", ["ctx_job", "interview", "external_compensation", "external_opportunity"], ["JOB_LEAVE"]),
        _p("j08", 51, "My current company confirmed the title change in writing.", ["ctx_job", "promotion", "internal_role", "retention"], ["JOB_STAY"]),
        _p("j09", 63, "I received an external offer but have not accepted it.", ["ctx_job", "external_offer", "external_opportunity", "uncertainty"], ["JOB_LEAVE"]),
        _p("j10", 66, "The company matched part of the offer, so I am reconsidering both paths.", ["ctx_job", "external_offer", "compensation", "retention", "uncertainty"], ["JOB_LEAVE", "JOB_STAY"]),
        _p("j11", 121, "I asked the new employer to revise the start date in the contract.", ["ctx_job", "external_offer", "contract", "start_date"], ["JOB_LEAVE"]),
        _p("j12", 128, "My boss offered a six-month leadership track if I stay.", ["ctx_job", "career_growth", "promotion", "retention"], ["JOB_STAY"]),
        _p("j13", 191, "I signed the external offer; resignation has not happened yet.", ["ctx_job", "external_offer", "contract", "commitment", "uncertainty"], ["JOB_LEAVE"]),
        _p("j14", 198, "HR confirmed the promotion remains available if I withdraw the resignation plan.", ["ctx_job", "promotion", "retention", "uncertainty"], ["JOB_STAY"]),
        _p("j15", 205, "I formally resigned after the notice discussion.", ["ctx_job", "resignation", "commitment", "management_conflict"], ["JOB_LEAVE"]),

        # Housing worktree: move vs stay/renew.
        _p("h00", 2, "The lease situation is open and I am deciding whether to move.", ["ctx_home", "decision_open"]),
        _p("h01", 7, "I started viewing apartments closer to work.", ["ctx_home", "viewing", "commute", "relocation"], ["HOME_MOVE"]),
        _p("h02", 14, "A second viewing made the new neighborhood look practical.", ["ctx_home", "viewing", "neighborhood", "relocation"], ["HOME_MOVE"]),
        _p("h03", 16, "The landlord offered a lower renewal rent.", ["ctx_home", "renewal", "rent_discount", "landlord_offer"], ["HOME_STAY"]),
        _p("h04", 24, "The landlord also agreed to repair the kitchen if I renew.", ["ctx_home", "renewal", "repair", "landlord_offer"], ["HOME_STAY"]),
        _p("n02", 31, "The football match was moved to Saturday.", ["sports", "schedule"]),
        _p("h05", 39, "I asked a moving company for a quote.", ["ctx_home", "moving_company", "relocation", "logistics"], ["HOME_MOVE"]),
        _p("h06", 48, "The repaired kitchen reduced one reason to leave.", ["ctx_home", "repair", "renewal", "uncertainty"], ["HOME_STAY"]),
        _p("h07", 72, "The new apartment sent me a draft lease.", ["ctx_home", "new_lease", "relocation", "contract"], ["HOME_MOVE"]),
        _p("h08", 75, "My landlord extended the renewal deadline while I compare both options.", ["ctx_home", "renewal", "landlord_offer", "uncertainty"], ["HOME_STAY", "HOME_MOVE"]),
        _p("h09", 137, "I paid the holding deposit on the new apartment.", ["ctx_home", "new_lease", "deposit", "commitment"], ["HOME_MOVE"]),
        _p("h10", 145, "The old landlord made one final rent discount offer.", ["ctx_home", "renewal", "rent_discount", "landlord_offer"], ["HOME_STAY"]),
        _p("h11", 211, "The movers collected the boxes and the new lease started.", ["ctx_home", "moving_company", "new_lease", "commitment"], ["HOME_MOVE"]),

        # Architecture worktree: rewrite/migrate vs incremental compatibility path.
        _p("a00", 1, "The service architecture needs a change but the direction is open.", ["ctx_arch", "decision_open"]),
        _p("a01", 6, "I prototyped the new stack behind an adapter.", ["ctx_arch", "prototype", "new_stack", "adapter"], ["ARCH_REWRITE"]),
        _p("a02", 11, "The prototype can read production-shaped fixtures.", ["ctx_arch", "prototype", "migration", "new_stack"], ["ARCH_REWRITE"]),
        _p("a03", 15, "A compatibility patch keeps the old service running.", ["ctx_arch", "compatibility", "patch", "maintenance"], ["ARCH_PATCH"]),
        _p("a04", 22, "We shipped another small adapter instead of replacing the service.", ["ctx_arch", "adapter", "incremental", "compatibility"], ["ARCH_PATCH"]),
        _p("a05", 29, "The new stack passed a partial migration replay.", ["ctx_arch", "migration", "replay", "new_stack"], ["ARCH_REWRITE"]),
        _p("n03", 33, "The office router firmware was upgraded.", ["network", "firmware"]),
        _p("a06", 42, "The compatibility release removed one blocker without changing storage.", ["ctx_arch", "compatibility", "release", "incremental"], ["ARCH_PATCH"]),
        _p("a07", 59, "A shadow cutover moved read traffic to the new stack.", ["ctx_arch", "cutover", "migration", "new_stack"], ["ARCH_REWRITE"]),
        _p("a08", 68, "The patch path remains useful for clients that cannot migrate yet.", ["ctx_arch", "compatibility", "maintenance", "client_constraint"], ["ARCH_PATCH"]),
        _p("a09", 116, "Write traffic is now mirrored into the migration target.", ["ctx_arch", "migration", "cutover", "replay"], ["ARCH_REWRITE"]),
        _p("a10", 124, "A legacy client forced one more compatibility release.", ["ctx_arch", "compatibility", "release", "client_constraint"], ["ARCH_PATCH"]),
        _p("a11", 184, "The migration target became authoritative for new writes.", ["ctx_arch", "cutover", "migration", "authority"], ["ARCH_REWRITE"]),
        _p("a12", 201, "The compatibility layer is still maintained for the remaining legacy client.", ["ctx_arch", "compatibility", "maintenance", "client_constraint"], ["ARCH_PATCH"]),
    ]
    return tuple(sorted(items, key=lambda p: (p.day, p.point_id)))


def baselines() -> tuple[WorktreeBaseline, ...]:
    return (
        WorktreeBaseline("WT_JOB", frozenset({"ctx_job"})),
        WorktreeBaseline("WT_HOME", frozenset({"ctx_home"})),
        WorktreeBaseline("WT_ARCH", frozenset({"ctx_arch"})),
    )


def _feature_weights(points: tuple[SemanticPoint, ...]) -> dict[str, float]:
    doc_freq: Counter[str] = Counter()
    for point in points:
        doc_freq.update(point.features)
    n = len(points)
    return {
        feature: math.log((n + 1) / (count + 1)) + 1.0
        for feature, count in doc_freq.items()
        if feature not in CONTEXT_FEATURES
    }


def _weighted_coverage(
    source_features: frozenset[str],
    target_features: frozenset[str],
    weights: dict[str, float],
) -> float:
    """How much of target meaning is already represented by source meaning."""

    target = [f for f in target_features if f in weights]
    if not target:
        return 0.0
    denom = sum(weights[f] for f in target)
    hit = sum(weights[f] for f in target if f in source_features)
    return hit / denom if denom else 0.0


def _weighted_jaccard(
    left: frozenset[str],
    right: frozenset[str],
    weights: dict[str, float],
) -> float:
    left = frozenset(f for f in left if f in weights)
    right = frozenset(f for f in right if f in weights)
    union = left | right
    if not union:
        return 0.0
    inter = left & right
    return sum(weights[f] for f in inter) / sum(weights[f] for f in union)


def _route_worktree(point: SemanticPoint, roots: tuple[WorktreeBaseline, ...]) -> str | None:
    scores = [
        (len(point.features & root.context_features), root.worktree_id)
        for root in roots
    ]
    score, worktree_id = max(scores)
    return worktree_id if score > 0 else None


def _branch_envelope_score(branch: BranchState, point: SemanticPoint, weights: dict[str, float]) -> float:
    return _weighted_coverage(branch.envelope, point.features, weights)


def _branch_point_score(
    branch: BranchState,
    point: SemanticPoint,
    points_by_id: dict[str, SemanticPoint],
    weights: dict[str, float],
) -> float:
    if not branch.support_ids:
        return 0.0
    return max(
        _weighted_coverage(points_by_id[support_id].features, point.features, weights)
        for support_id in branch.support_ids
    )


def _align_branches(
    branches: Iterable[BranchState],
    points_by_id: dict[str, SemanticPoint],
) -> dict[str, str | None]:
    alignment: dict[str, str | None] = {}
    for branch in branches:
        counts: Counter[str] = Counter()
        for point_id in branch.support_ids:
            counts.update(points_by_id[point_id].gold_branches)
        if not counts:
            alignment[branch.branch_id] = None
            continue
        best = counts.most_common()
        if len(best) > 1 and best[0][1] == best[1][1]:
            alignment[branch.branch_id] = None
        else:
            alignment[branch.branch_id] = best[0][0]
    return alignment


def _summarize(
    *,
    threshold: float,
    points: tuple[SemanticPoint, ...],
    branches: dict[str, BranchState],
    records: list[RetrievalRecord],
    alignment: dict[str, str | None],
    residual_ids: tuple[str, ...],
) -> dict[str, object]:
    points_by_id = {p.point_id: p for p in points}
    gold_labels = sorted({label for p in points for label in p.gold_branches})
    mapped_by_gold: dict[str, list[BranchState]] = defaultdict(list)
    for branch in branches.values():
        label = alignment.get(branch.branch_id)
        if label is not None:
            mapped_by_gold[label].append(branch)

    seeded = sum(bool(mapped_by_gold[label]) for label in gold_labels)
    opportunities = hits_envelope = hits_point = 0
    false_envelope = total_envelope = 0
    long_gap_opportunities = long_gap_hits = 0
    multi_memberships = multi_hits = 0
    multi_exact_opportunities = multi_exact_hits = 0
    maturity = {
        "young_1_2": [0, 0],
        "growing_3_4": [0, 0],
        "mature_5_plus": [0, 0],
    }

    records_by_point = {record.point_id: record for record in records}
    support_day_by_branch: dict[str, list[tuple[int, str]]] = {}
    for branch in branches.values():
        support_day_by_branch[branch.branch_id] = sorted(
            (points_by_id[pid].day, pid) for pid in branch.support_ids
        )

    for point in points:
        record = records_by_point[point.point_id]
        env_set = set(record.envelope_candidates)
        point_set = set(record.point_candidates)
        sizes = dict(record.branch_sizes_before)

        for candidate_id in env_set:
            total_envelope += 1
            label = alignment.get(candidate_id)
            if label is not None and label not in point.gold_branches:
                false_envelope += 1

        available_gold: list[str] = []
        for gold in point.gold_branches:
            prior_branches = [
                b for b in mapped_by_gold[gold]
                if b.created_step < record.step
            ]
            if not prior_branches:
                continue
            available_gold.append(gold)
            opportunities += 1
            env_hit_branches = [b for b in prior_branches if b.branch_id in env_set]
            point_hit_branches = [b for b in prior_branches if b.branch_id in point_set]
            if env_hit_branches:
                hits_envelope += 1
            if point_hit_branches:
                hits_point += 1

            prior_sizes = [sizes.get(b.branch_id, 0) for b in prior_branches]
            max_size = max(prior_sizes, default=0)
            bucket = "young_1_2" if max_size <= 2 else "growing_3_4" if max_size <= 4 else "mature_5_plus"
            maturity[bucket][1] += 1
            if env_hit_branches:
                maturity[bucket][0] += 1

            prior_support_days: list[int] = []
            for b in prior_branches:
                prior_support_days.extend(
                    day for day, _pid in support_day_by_branch[b.branch_id]
                    if day < point.day
                )
            if prior_support_days:
                gap = point.day - max(prior_support_days)
                if gap > 45:
                    long_gap_opportunities += 1
                    if env_hit_branches:
                        long_gap_hits += 1

        if len(point.gold_branches) > 1 and len(available_gold) == len(point.gold_branches):
            multi_exact_opportunities += 1
            per_gold = []
            for gold in point.gold_branches:
                hit = any(
                    b.branch_id in env_set and b.created_step < record.step
                    for b in mapped_by_gold[gold]
                )
                per_gold.append(hit)
                multi_memberships += 1
                multi_hits += int(hit)
            if all(per_gold):
                multi_exact_hits += 1

    branch_purities: list[float] = []
    for branch in branches.values():
        label = alignment.get(branch.branch_id)
        if label is None:
            branch_purities.append(0.0)
            continue
        supports = [points_by_id[pid] for pid in branch.support_ids]
        if supports:
            branch_purities.append(
                sum(label in p.gold_branches for p in supports) / len(supports)
            )

    return {
        "threshold": threshold,
        "gold_branch_count": len(gold_labels),
        "seeded_gold_branches": seeded,
        "seed_coverage": seeded / len(gold_labels) if gold_labels else 0.0,
        "candidate_membership_opportunities": opportunities,
        "envelope_candidate_hits": hits_envelope,
        "envelope_candidate_recall": hits_envelope / opportunities if opportunities else 0.0,
        "point_candidate_hits": hits_point,
        "point_candidate_recall": hits_point / opportunities if opportunities else 0.0,
        "envelope_recall_gain_vs_point": (
            (hits_envelope - hits_point) / opportunities if opportunities else 0.0
        ),
        "envelope_candidate_count": total_envelope,
        "false_envelope_candidates": false_envelope,
        "false_candidate_fraction": false_envelope / total_envelope if total_envelope else 0.0,
        "long_gap_gt45_opportunities": long_gap_opportunities,
        "long_gap_gt45_hits": long_gap_hits,
        "long_gap_gt45_recall": long_gap_hits / long_gap_opportunities if long_gap_opportunities else 0.0,
        "multi_branch_membership_opportunities": multi_memberships,
        "multi_branch_membership_hits": multi_hits,
        "multi_branch_membership_recall": multi_hits / multi_memberships if multi_memberships else 0.0,
        "multi_branch_exact_opportunities": multi_exact_opportunities,
        "multi_branch_exact_hits": multi_exact_hits,
        "multi_branch_exact_recall": multi_exact_hits / multi_exact_opportunities if multi_exact_opportunities else 0.0,
        "maturity_recall": {
            bucket: {
                "hits": value[0],
                "opportunities": value[1],
                "recall": value[0] / value[1] if value[1] else None,
            }
            for bucket, value in maturity.items()
        },
        "branch_count": len(branches),
        "mean_branch_purity": sum(branch_purities) / len(branch_purities) if branch_purities else 0.0,
        "residual_count": len(residual_ids),
        "residual_ids": list(residual_ids),
        "branch_alignment": alignment,
        "branch_supports": {
            branch.branch_id: {
                "worktree_id": branch.worktree_id,
                "gold_alignment": alignment.get(branch.branch_id),
                "created_step": branch.created_step,
                "support_ids": list(branch.support_ids),
                "envelope": sorted(branch.envelope),
            }
            for branch in branches.values()
        },
    }


def simulate(
    threshold: float,
    *,
    seed_threshold: float = 0.24,
    accept_margin: float = 0.08,
    top_k: int = 3,
) -> SimulationResult:
    points = corpus()
    roots = baselines()
    weights = _feature_weights(points)
    scoring_features = frozenset(weights)
    points_by_id = {p.point_id: p for p in points}

    branches: dict[str, BranchState] = {}
    residual_by_worktree: dict[str, list[str]] = defaultdict(list)
    records: list[RetrievalRecord] = []
    next_branch = 1

    for step, point in enumerate(points):
        worktree_id = _route_worktree(point, roots)
        branch_sizes_before = tuple(sorted((bid, len(branch.support_ids)) for bid, branch in branches.items()))

        if worktree_id is None:
            records.append(
                RetrievalRecord(step, point.point_id, point.day, None, point.gold_branches, (), (), (), branch_sizes_before)
            )
            continue

        eligible = [branch for branch in branches.values() if branch.worktree_id == worktree_id]
        envelope_ranked = sorted(
            (
                (_branch_envelope_score(branch, point, weights), branch.branch_id)
                for branch in eligible
            ),
            reverse=True,
        )
        point_ranked = sorted(
            (
                (_branch_point_score(branch, point, points_by_id, weights), branch.branch_id)
                for branch in eligible
            ),
            reverse=True,
        )
        envelope_candidates = tuple(
            branch_id for score, branch_id in envelope_ranked
            if score >= threshold
        )[:top_k]
        point_candidates = tuple(
            branch_id for score, branch_id in point_ranked
            if score >= threshold
        )[:top_k]

        accept_threshold = min(0.90, threshold + accept_margin)
        accepted = tuple(
            branch_id for score, branch_id in envelope_ranked
            if score >= accept_threshold
        )[:top_k]

        records.append(
            RetrievalRecord(
                step,
                point.point_id,
                point.day,
                worktree_id,
                point.gold_branches,
                envelope_candidates,
                point_candidates,
                accepted,
                branch_sizes_before,
            )
        )

        if accepted:
            for branch_id in accepted:
                branches[branch_id].add(point, scoring_features=scoring_features)
            continue

        # Unmatched points remain in the residual point cloud.  Only the
        # residual cloud is pair-compared, and only to bootstrap a branch.
        residuals = residual_by_worktree[worktree_id]
        best: tuple[float, str] | None = None
        for prior_id in residuals:
            prior = points_by_id[prior_id]
            similarity = _weighted_jaccard(prior.features, point.features, weights)
            if best is None or similarity > best[0]:
                best = (similarity, prior_id)

        residuals.append(point.point_id)
        if best is None or best[0] < seed_threshold:
            continue

        prior_id = best[1]
        branch_id = f"B{next_branch:02d}"
        next_branch += 1
        branch = BranchState(branch_id, worktree_id, step)
        branch.add(points_by_id[prior_id], scoring_features=scoring_features)
        branch.add(point, scoring_features=scoring_features)
        branches[branch_id] = branch
        residuals.remove(prior_id)
        residuals.remove(point.point_id)

    alignment = _align_branches(branches.values(), points_by_id)
    residual_ids = tuple(
        point_id
        for worktree_id in sorted(residual_by_worktree)
        for point_id in residual_by_worktree[worktree_id]
    )
    summary = _summarize(
        threshold=threshold,
        points=points,
        branches=branches,
        records=records,
        alignment=alignment,
        residual_ids=residual_ids,
    )
    return SimulationResult(
        threshold,
        tuple(branches.values()),
        tuple(records),
        residual_ids,
        alignment,
        summary,
    )


def benchmark() -> dict[str, object]:
    thresholds = (0.30, 0.40, 0.50, 0.60)
    runs = [simulate(threshold) for threshold in thresholds]
    return {
        "experiment": "worktree-snake-chronological-replay",
        "mechanism": {
            "point_cloud": "unmatched points remain residual; pair comparison is used only for branch bootstrap",
            "worktree": "multiple active branches may coexist under one frozen baseline context",
            "snake": "each branch incrementally accumulates semantic coverage from accepted points",
            "retrieval": "new point is matched against branch semantic envelope; no hard temporal cutoff",
            "multi_branch": "one point may be candidate/accepted by multiple live branches",
            "gold_usage": "gold labels are evaluator-only and are never read by replay logic",
        },
        "corpus": {
            "points": len(corpus()),
            "worktrees": len(baselines()),
            "gold_branches": len({g for p in corpus() for g in p.gold_branches}),
            "gold_memberships": sum(len(p.gold_branches) for p in corpus()),
            "max_day": max(p.day for p in corpus()),
        },
        "runs": [run.summary for run in runs],
    }


def main() -> None:
    print(json.dumps(benchmark(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
