from __future__ import annotations

import random
from collections import defaultdict

SEED = 20261002
CASES = 1000


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


def compile_partition(
    resolved_ids: list[str],
    cohabit_edges: list[tuple[str, str]],
    context_edges: list[tuple[str, str]],
    source_refs: dict[str, tuple[str, ...]],
) -> tuple[set[frozenset[str]], dict[frozenset[str], frozenset[str]]]:
    uf = UnionFind(resolved_ids)
    resolved = set(resolved_ids)
    for left, right in cohabit_edges:
        if left in resolved and right in resolved:
            uf.union(left, right)

    components: dict[str, set[str]] = defaultdict(set)
    for point_id in resolved_ids:
        components[uf.find(point_id)].add(point_id)

    partition = {frozenset(group) for group in components.values()}
    group_for = {
        point_id: group
        for group in partition
        for point_id in group
    }

    context_refs: dict[frozenset[str], set[str]] = {
        group: set() for group in partition
    }
    for left, right in context_edges:
        group = group_for.get(left)
        if group is None or right not in resolved or right in group:
            continue
        context_refs[group].update(source_refs[right])

    return partition, {
        group: frozenset(refs)
        for group, refs in context_refs.items()
    }


def normalized(partition: set[frozenset[str]]) -> tuple[tuple[str, ...], ...]:
    return tuple(sorted(tuple(sorted(group)) for group in partition))


def main() -> None:
    rng = random.Random(SEED)
    counters = defaultdict(int)

    for case_index in range(CASES):
        n = rng.randint(3, 16)
        ids = [f"P{case_index:04d}_{i:02d}" for i in range(n)]
        sources = {point_id: (f"E{case_index:04d}_{i:02d}",) for i, point_id in enumerate(ids)}

        cohabit: list[tuple[str, str]] = []
        context: list[tuple[str, str]] = []
        for i in range(n - 1):
            roll = rng.random()
            if roll < 0.22:
                cohabit.append((ids[i], ids[i + 1]))
            elif roll < 0.36:
                context.append((ids[i + 1], ids[i]))

        base_partition, base_context = compile_partition(ids, cohabit, context, sources)

        shuffled = ids[:]
        rng.shuffle(shuffled)
        p2, c2 = compile_partition(shuffled, cohabit[:], context[:], sources)
        assert normalized(base_partition) == normalized(p2)
        assert base_context == c2
        counters["permutation_invariance"] += 1

        duplicated_cohabit = cohabit + cohabit[:]
        duplicated_context = context + context[:]
        p3, c3 = compile_partition(ids, duplicated_cohabit, duplicated_context, sources)
        assert normalized(base_partition) == normalized(p3)
        assert base_context == c3
        counters["duplicate_edge_idempotence"] += 1

        extra = f"P{case_index:04d}_independent"
        sources_extra = {**sources, extra: (f"E{case_index:04d}_independent",)}
        p4, _ = compile_partition(ids + [extra], cohabit, context, sources_extra)
        assert frozenset({extra}) in p4
        assert {
            group for group in p4 if extra not in group
        } == base_partition
        counters["independent_addition_locality"] += 1

        if n >= 3:
            left, middle, right = ids[0], ids[1], ids[2]
            p5, _ = compile_partition(
                ids,
                cohabit + [(left, middle), (middle, right)],
                context,
                sources,
            )
            containing = next(group for group in p5 if left in group)
            assert {left, middle, right} <= set(containing)
            counters["cohabit_transitive_closure"] += 1

        if n >= 2:
            left, right = ids[-1], ids[0]
            p6, c6 = compile_partition(ids, cohabit, context + [(left, right)], sources)
            assert normalized(base_partition) == normalized(p6)
            left_group = next(group for group in p6 if left in group)
            if right not in left_group:
                assert set(sources[right]) <= set(c6[left_group])
            counters["context_does_not_merge"] += 1

        deferred = ids[-1]
        kept = ids[:-1]
        p7, _ = compile_partition(
            kept,
            [(a, b) for a, b in cohabit if deferred not in {a, b}],
            [(a, b) for a, b in context if deferred not in {a, b}],
            sources,
        )
        assert all(deferred not in group for group in p7)
        counters["deferred_exclusion"] += 1

    print({
        "seed": SEED,
        "generated_cases": CASES,
        "invariants": dict(counters),
        "status": "PASS",
        "boundary": (
            "This stress run validates closure mechanics only. It does not validate "
            "the semantic parser assigning cohabit/context/defer correctly."
        ),
    })


if __name__ == "__main__":
    main()
