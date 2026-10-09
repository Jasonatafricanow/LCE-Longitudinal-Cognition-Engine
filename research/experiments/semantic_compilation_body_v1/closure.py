"""Deterministic Semantic Closure Compiler.

Fulfills §14 and §7 of the experiment specification:
- Compiles validated Semantic Points and dependencies into SemanticBlocks.
- Enforces Union-Find closure over 'cohabit' dependencies.
- Attaches 'context' dependencies to provenance/context_refs WITHOUT raw text concatenation.
- Excludes 'defer' / unresolved points from cognition space.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from research.experiments.semantic_compilation_body_v1.schema import (
    EpistemicStatus,
    Polarity,
    SemanticBlock,
    SemanticParseResultV1,
    SemanticPoint,
    SpeechAct,
    TemporalKind,
)


class UnionFind:
    def __init__(self, elements: Sequence[str]) -> None:
        self.parent = {elem: elem for elem in elements}

    def find(self, elem: str) -> str:
        root = elem
        while self.parent[root] != root:
            root = self.parent[root]
        curr = elem
        while self.parent[curr] != root:
            nxt = self.parent[curr]
            self.parent[curr] = root
            curr = nxt
        return root

    def union(self, elem1: str, elem2: str) -> None:
        r1, r2 = self.find(elem1), self.find(elem2)
        if r1 != r2:
            self.parent[r2] = r1


EPISTEMIC_PRIORITY = {
    "counterfactual": 6,
    "hypothetical": 5,
    "uncertain": 4,
    "planned": 3,
    "reported": 2,
    "unknown": 1,
    "asserted": 0,
}


def _aggregate_speech_act(points: list[SemanticPoint]) -> SpeechAct:
    acts = {p.speech_act for p in points}
    if "directive" in acts:
        return "directive"
    if "question" in acts:
        return "question"
    if "assertion" in acts:
        return "assertion"
    return "other"


def _aggregate_polarity(points: list[SemanticPoint]) -> Polarity:
    pols = {p.polarity for p in points}
    if "negative" in pols:
        return "negative"
    if "unknown" in pols and pols == {"unknown"}:
        return "unknown"
    return "positive"


def _aggregate_epistemic(points: list[SemanticPoint]) -> EpistemicStatus:
    return max(points, key=lambda p: EPISTEMIC_PRIORITY.get(p.epistemic_status, 0)).epistemic_status


def _aggregate_temporal(points: list[SemanticPoint]) -> TemporalKind:
    # Later/current event takes precedence in composite state
    temps = [p.temporal for p in points]
    if "current" in temps:
        return "current"
    if "future" in temps:
        return "future"
    if "past" in temps:
        return "past"
    if "atemporal" in temps:
        return "atemporal"
    return "unknown"


def compile_semantic_closure(
    parse_result: SemanticParseResultV1,
    case_id: str = "CASE",
) -> tuple[list[SemanticBlock], list[str]]:
    """Compile SemanticParseResultV1 into deterministic SemanticBlock partitions.
    
    Returns (compiled_blocks, deferred_point_ids).
    """
    deferred_set = set(parse_result.unresolved)
    point_map: dict[str, SemanticPoint] = {}

    for pt in parse_result.semantic_points:
        point_map[pt.local_id] = pt
        if pt.status == "defer" or pt.unresolved_refs:
            deferred_set.add(pt.local_id)

    # Filter out deferred points from active cognition
    resolved_ids = [pt.local_id for pt in parse_result.semantic_points if pt.local_id not in deferred_set]
    resolved_set = set(resolved_ids)

    if not resolved_ids:
        return [], sorted(deferred_set)

    # 1. Cohabit Union-Find
    uf = UnionFind(resolved_ids)
    for dep in parse_result.dependencies:
        if dep.boundary_policy == "cohabit":
            if dep.from_point in resolved_set and dep.to_point in resolved_set:
                uf.union(dep.from_point, dep.to_point)

    # Group components
    components: dict[str, list[str]] = defaultdict(list)
    for pid in resolved_ids:
        components[uf.find(pid)].append(pid)

    # Deterministic sorting of groups
    sorted_groups = sorted(
        (sorted(group) for group in components.values()),
        key=lambda grp: grp[0],
    )

    # Map point to group index
    group_for_point: dict[str, int] = {}
    for g_idx, grp in enumerate(sorted_groups):
        for pid in grp:
            group_for_point[pid] = g_idx

    # 2. Context attachment
    context_for_group: dict[int, set[str]] = defaultdict(set)
    for dep in parse_result.dependencies:
        if dep.boundary_policy == "context":
            src_group = group_for_point.get(dep.from_point)
            if src_group is not None:
                # If target is in a different group, attach as context support
                if dep.to_point not in sorted_groups[src_group]:
                    context_for_group[src_group].add(dep.to_point)

    # 3. Build SemanticBlocks
    blocks: list[SemanticBlock] = []
    for g_idx, member_ids in enumerate(sorted_groups):
        context_ids = sorted(context_for_group.get(g_idx, set()))
        member_points = [point_map[pid] for pid in member_ids]
        
        # Source refs gather from members + context provenance
        all_sources = set()
        for pid in member_ids:
            all_sources.update(point_map[pid].source_refs)
        for pid in context_ids:
            if pid in point_map:
                all_sources.update(point_map[pid].source_refs)

        # Build analysis_text cleanly (§7: no verbatim context string concatenation!)
        if len(member_points) == 1:
            analysis_text = member_points[0].meaning
        else:
            # Combine cohabited statements with semantic cohesion
            analysis_text = "；".join(p.meaning for p in member_points)

        block = SemanticBlock(
            block_id=f"{case_id}-SB{g_idx+1:02d}",
            member_point_ids=member_ids,
            context_point_ids=context_ids,
            source_refs=sorted(all_sources),
            analysis_text=analysis_text,
            speech_act=_aggregate_speech_act(member_points),
            polarity=_aggregate_polarity(member_points),
            epistemic_status=_aggregate_epistemic(member_points),
            temporal=_aggregate_temporal(member_points),
        )
        blocks.append(block)

    return blocks, sorted(deferred_set)
