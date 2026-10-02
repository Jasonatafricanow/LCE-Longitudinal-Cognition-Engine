from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "closure_cases.json").read_text(encoding="utf-8"))


class UnionFind:
    def __init__(self, ids: list[str]) -> None:
        self.parent = {item: item for item in ids}

    def find(self, item: str) -> str:
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != item:
            parent = self.parent[item]
            self.parent[item] = root
            item = parent
        return root

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[b] = a


def _point_map(case: dict) -> dict[str, dict]:
    return {point["id"]: point for point in case["points"]}


def _build_blocks(case: dict, groups: list[list[str]], *, include_context: bool) -> list[dict]:
    points = _point_map(case)
    group_index = {
        point_id: index
        for index, group in enumerate(groups)
        for point_id in group
    }
    context_by_group: dict[int, set[str]] = defaultdict(set)
    if include_context:
        for dep in case["dependencies"]:
            if dep["policy"] != "context":
                continue
            source_group = group_index.get(dep["from"])
            if source_group is not None and dep["to"] not in groups[source_group]:
                context_by_group[source_group].add(dep["to"])

    blocks = []
    for index, group in enumerate(groups):
        context_ids = sorted(context_by_group.get(index, set()))
        source_refs = {
            ref
            for point_id in group + context_ids
            for ref in points[point_id]["source_refs"]
        }
        body = " ".join(points[point_id]["meaning"] for point_id in group)
        if context_ids:
            context = " ".join(points[point_id]["meaning"] for point_id in context_ids)
            body = body + " 必要上下文：" + context
        blocks.append(
            {
                "member_point_ids": sorted(group),
                "context_point_ids": context_ids,
                "source_refs": sorted(source_refs),
                "canonical_meaning": body,
            }
        )
    return blocks


def _singleton_strategy(case: dict) -> list[dict]:
    groups = [[point["id"]] for point in case["points"] if point["status"] == "resolved"]
    return _build_blocks(case, groups, include_context=False)


def _raw_bucket_strategy(case: dict) -> list[dict]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for point in case["points"]:
        if point["status"] == "resolved":
            buckets[point["origin"]].append(point["id"])
    groups = [buckets[key] for key in buckets]
    return _build_blocks(case, groups, include_context=False)


def _semantic_closure_strategy(case: dict) -> list[dict]:
    resolved = [point["id"] for point in case["points"] if point["status"] == "resolved"]
    uf = UnionFind(resolved)
    resolved_set = set(resolved)
    for dep in case["dependencies"]:
        if dep["policy"] == "cohabit" and dep["from"] in resolved_set and dep["to"] in resolved_set:
            uf.union(dep["from"], dep["to"])
    components: dict[str, list[str]] = defaultdict(list)
    for point_id in resolved:
        components[uf.find(point_id)].append(point_id)
    groups = sorted((sorted(group) for group in components.values()), key=lambda group: group[0])
    return _build_blocks(case, groups, include_context=True)


def _partition(blocks: list[dict]) -> set[frozenset[str]]:
    return {frozenset(block["member_point_ids"]) for block in blocks}


def _evaluate(case: dict, blocks: list[dict]) -> dict[str, object]:
    points = _point_map(case)
    block_for = {
        point_id: index
        for index, block in enumerate(blocks)
        for point_id in block["member_point_ids"]
    }

    cohabit_violations = []
    context_violations = []
    for dep in case["dependencies"]:
        left = block_for.get(dep["from"])
        right = block_for.get(dep["to"])
        if dep["policy"] == "cohabit":
            if left is None or right is None or left != right:
                cohabit_violations.append(dep)
        elif dep["policy"] == "context":
            if left is None:
                context_violations.append({**dep, "reason": "source point not compiled"})
                continue
            source_block = blocks[left]
            target_refs = set(points[dep["to"]]["source_refs"])
            if (
                dep["to"] not in source_block["member_point_ids"]
                and dep["to"] not in source_block["context_point_ids"]
            ):
                context_violations.append({**dep, "reason": "required context not carried"})
            elif not target_refs <= set(source_block["source_refs"]):
                context_violations.append({**dep, "reason": "context provenance not carried"})

    overmerge_violations = []
    for left, right in case["separate_pairs"]:
        if left in block_for and right in block_for and block_for[left] == block_for[right]:
            overmerge_violations.append([left, right])

    deferred_ids = {point["id"] for point in case["points"] if point["status"] == "defer"}
    compiled_ids = set(block_for)
    deferred_leakage = sorted(deferred_ids & compiled_ids)
    expected_partition = {frozenset(group) for group in case["expected_groups"]}
    partition_exact = _partition(blocks) == expected_partition
    expected_deferred = set(case["expected_deferred"])
    defer_exact = deferred_ids == expected_deferred

    safe = (
        not cohabit_violations
        and not context_violations
        and not overmerge_violations
        and not deferred_leakage
        and partition_exact
        and defer_exact
    )
    return {
        "safe": safe,
        "block_count": len(blocks),
        "partition_exact": partition_exact,
        "defer_exact": defer_exact,
        "cohabit_violations": cohabit_violations,
        "context_violations": context_violations,
        "overmerge_violations": overmerge_violations,
        "deferred_leakage": deferred_leakage,
        "blocks": blocks,
    }


def main() -> None:
    strategies = {
        "semantic_point_singletons": _singleton_strategy,
        "raw_evidence_buckets": _raw_bucket_strategy,
        "semantic_closure": _semantic_closure_strategy,
    }
    summary = {
        name: {
            "safe_cases": 0,
            "exact_partition_cases": 0,
            "cohabit_violations": 0,
            "context_violations": 0,
            "overmerge_violations": 0,
        }
        for name in strategies
    }
    details = []

    for case in MANIFEST["cases"]:
        case_result = {"case": case["id"], "strategies": {}}
        for name, strategy in strategies.items():
            blocks = strategy(case)
            result = _evaluate(case, blocks)
            case_result["strategies"][name] = result
            summary[name]["safe_cases"] += int(result["safe"])
            summary[name]["exact_partition_cases"] += int(result["partition_exact"])
            summary[name]["cohabit_violations"] += len(result["cohabit_violations"])
            summary[name]["context_violations"] += len(result["context_violations"])
            summary[name]["overmerge_violations"] += len(result["overmerge_violations"])
        details.append(case_result)

    report = {
        "schema_version": MANIFEST["schema_version"],
        "cases": len(MANIFEST["cases"]),
        "summary": summary,
        "details": details,
        "interpretation": {
            "semantic_point_singletons": "Tests the failure mode where parsed semantic points are treated directly as cognition/vector points.",
            "raw_evidence_buckets": "Approximates turn/chunk/region grouping: preserves nearby wording but overmerges independent semantics and cannot carry cross-turn context explicitly.",
            "semantic_closure": "Groups only meaning-dependent points, carries non-cohabiting required context/provenance, and withholds unresolved references from cognition-point output.",
            "claim_boundary": "This validates the block-closure mechanism over a frozen semantic parse. It does not yet validate an LLM/Body generating the semantic points correctly."
        },
    }

    if summary["semantic_closure"]["safe_cases"] != len(MANIFEST["cases"]):
        raise SystemExit(json.dumps(report, ensure_ascii=False, indent=2))

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
