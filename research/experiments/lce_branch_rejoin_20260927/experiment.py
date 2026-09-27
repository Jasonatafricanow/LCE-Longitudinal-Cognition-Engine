"""Branch merge / rejoin pressure test for one stable Line identity.

The experiment models Worktree as a DAG inside one Line:
- one trunk may fork into competing/parallel branches;
- later evidence may support a convergence node with multiple parents;
- rejoin does not erase historical divergence;
- rejoin does not create a new Line;
- invalidating the convergence evidence reopens the prior branches;
- late-known historical convergence obeys knowledge-time cutoff authority.

This is a structural experiment. It does not define production semantic
criteria for deciding that two branches have truly converged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace


OPEN = "OPEN"
REJOINED = "REJOINED"


@dataclass(frozen=True, slots=True)
class RawEvidence:
    raw_id: str
    known_at: int
    logical_at: int
    text: str
    valid: bool = True


@dataclass(frozen=True, slots=True)
class Node:
    node_id: str
    line_id: str
    kind: str
    raw_ids: tuple[str, ...]
    parent_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FrontierState:
    line_id: str
    cutoff: int
    active_node_ids: tuple[str, ...]
    state: str


class WorktreeDag:
    def __init__(self, *, line_id: str) -> None:
        self.line_id = line_id
        self.raw: dict[str, RawEvidence] = {}
        self.nodes: dict[str, Node] = {}

    def add_raw(self, evidence: RawEvidence) -> None:
        if evidence.raw_id in self.raw:
            raise ValueError(f"duplicate raw id: {evidence.raw_id}")
        self.raw[evidence.raw_id] = evidence

    def invalidate_raw(self, raw_id: str) -> None:
        self.raw[raw_id] = replace(self.raw[raw_id], valid=False)

    def add_node(self, node: Node) -> None:
        if node.node_id in self.nodes:
            raise ValueError(f"duplicate node id: {node.node_id}")
        if node.line_id != self.line_id:
            raise ValueError("node cannot switch Line identity")
        for raw_id in node.raw_ids:
            if raw_id not in self.raw:
                raise ValueError(f"unknown raw id: {raw_id}")
        for parent_id in node.parent_ids:
            parent = self.nodes.get(parent_id)
            if parent is None:
                raise ValueError(f"unknown parent node: {parent_id}")
            if parent.line_id != self.line_id:
                raise ValueError("all parents must belong to same Line")
        self.nodes[node.node_id] = node

    def raw_visible(self, raw_id: str, *, cutoff: int) -> bool:
        raw = self.raw[raw_id]
        return raw.valid and raw.known_at <= cutoff

    def node_visible(self, node_id: str, *, cutoff: int) -> bool:
        node = self.nodes[node_id]
        if not all(self.raw_visible(raw_id, cutoff=cutoff) for raw_id in node.raw_ids):
            return False
        return all(self.node_visible(parent_id, cutoff=cutoff) for parent_id in node.parent_ids)

    def node_raw_closure(self, node_id: str) -> frozenset[str]:
        node = self.nodes[node_id]
        closure = set(node.raw_ids)
        for parent_id in node.parent_ids:
            closure.update(self.node_raw_closure(parent_id))
        return frozenset(closure)

    def historical_nodes(self, *, cutoff: int) -> tuple[str, ...]:
        return tuple(
            sorted(
                node_id
                for node_id in self.nodes
                if self.node_visible(node_id, cutoff=cutoff)
            )
        )

    def frontier(self, *, cutoff: int) -> FrontierState:
        visible = {
            node_id
            for node_id in self.nodes
            if self.node_visible(node_id, cutoff=cutoff)
        }
        visible_parents = {
            parent_id
            for node_id in visible
            for parent_id in self.nodes[node_id].parent_ids
            if parent_id in visible
        }
        frontier = tuple(sorted(visible - visible_parents))

        # A visible rejoin node on the frontier means the current structural
        # state has converged. Historical fork nodes remain in the graph.
        state = (
            REJOINED
            if any(self.nodes[node_id].kind == "rejoin" for node_id in frontier)
            else OPEN
        )
        return FrontierState(
            line_id=self.line_id,
            cutoff=cutoff,
            active_node_ids=frontier,
            state=state,
        )


def build_standard_rejoin() -> WorktreeDag:
    tree = WorktreeDag(line_id="line_strategy")

    raws = (
        RawEvidence("t0", 2020, 2020, "shared trunk 0"),
        RawEvidence("t1", 2021, 2021, "shared trunk 1"),
        RawEvidence("a2", 2022, 2022, "branch A stage 1"),
        RawEvidence("a3", 2023, 2023, "branch A stage 2"),
        RawEvidence("b2", 2022, 2022, "branch B stage 1"),
        RawEvidence("b3", 2023, 2023, "branch B stage 2"),
        RawEvidence("r4", 2024, 2024, "evidence of convergence"),
        RawEvidence("r5", 2025, 2025, "continued support after convergence"),
    )
    for raw in raws:
        tree.add_raw(raw)

    tree.add_node(Node("trunk_0", tree.line_id, "trunk", ("t0",), ()))
    tree.add_node(Node("trunk_1", tree.line_id, "trunk", ("t1",), ("trunk_0",)))
    tree.add_node(Node("branch_a_2", tree.line_id, "branch", ("a2",), ("trunk_1",)))
    tree.add_node(Node("branch_a_3", tree.line_id, "branch", ("a3",), ("branch_a_2",)))
    tree.add_node(Node("branch_b_2", tree.line_id, "branch", ("b2",), ("trunk_1",)))
    tree.add_node(Node("branch_b_3", tree.line_id, "branch", ("b3",), ("branch_b_2",)))
    tree.add_node(
        Node(
            "rejoin_4",
            tree.line_id,
            "rejoin",
            ("r4",),
            ("branch_a_3", "branch_b_3"),
        )
    )
    tree.add_node(Node("post_5", tree.line_id, "post_rejoin", ("r5",), ("rejoin_4",)))
    return tree


def build_late_known_rejoin() -> WorktreeDag:
    tree = WorktreeDag(line_id="line_strategy")

    raws = (
        RawEvidence("t0", 2020, 2020, "shared trunk 0"),
        RawEvidence("t1", 2021, 2021, "shared trunk 1"),
        RawEvidence("a2", 2022, 2022, "branch A stage 1"),
        RawEvidence("a3", 2023, 2023, "branch A stage 2"),
        RawEvidence("b2", 2022, 2022, "branch B stage 1"),
        RawEvidence("b3", 2023, 2023, "branch B stage 2"),
        # Learned in 2026 but logically belongs to 2024.
        RawEvidence("retro_r4", 2026, 2024, "late-known 2024 convergence evidence"),
    )
    for raw in raws:
        tree.add_raw(raw)

    tree.add_node(Node("trunk_0", tree.line_id, "trunk", ("t0",), ()))
    tree.add_node(Node("trunk_1", tree.line_id, "trunk", ("t1",), ("trunk_0",)))
    tree.add_node(Node("branch_a_2", tree.line_id, "branch", ("a2",), ("trunk_1",)))
    tree.add_node(Node("branch_a_3", tree.line_id, "branch", ("a3",), ("branch_a_2",)))
    tree.add_node(Node("branch_b_2", tree.line_id, "branch", ("b2",), ("trunk_1",)))
    tree.add_node(Node("branch_b_3", tree.line_id, "branch", ("b3",), ("branch_b_2",)))
    tree.add_node(
        Node(
            "retro_rejoin_4",
            tree.line_id,
            "rejoin",
            ("retro_r4",),
            ("branch_a_3", "branch_b_3"),
        )
    )
    return tree


def standard_rejoin_scenario() -> dict[str, object]:
    tree = build_standard_rejoin()

    frontier_2023 = tree.frontier(cutoff=2023)
    frontier_2024 = tree.frontier(cutoff=2024)
    frontier_2025 = tree.frontier(cutoff=2025)

    return {
        "line_id": tree.line_id,
        "line_identity_count": 1,
        "frontier_2023": {
            "nodes": list(frontier_2023.active_node_ids),
            "state": frontier_2023.state,
        },
        "frontier_2024": {
            "nodes": list(frontier_2024.active_node_ids),
            "state": frontier_2024.state,
        },
        "frontier_2025": {
            "nodes": list(frontier_2025.active_node_ids),
            "state": frontier_2025.state,
        },
        "historical_nodes_2025": list(tree.historical_nodes(cutoff=2025)),
        "rejoin_raw_closure": sorted(tree.node_raw_closure("rejoin_4")),
        "post_rejoin_raw_closure": sorted(tree.node_raw_closure("post_5")),
        "rejoin_parents": list(tree.nodes["rejoin_4"].parent_ids),
    }


def invalidation_reopens_branches_scenario() -> dict[str, object]:
    tree = build_standard_rejoin()

    before = tree.frontier(cutoff=2025)
    historical_before = tree.historical_nodes(cutoff=2025)

    tree.invalidate_raw("r4")

    after = tree.frontier(cutoff=2025)
    historical_after = tree.historical_nodes(cutoff=2025)

    return {
        "before": {
            "nodes": list(before.active_node_ids),
            "state": before.state,
        },
        "after": {
            "nodes": list(after.active_node_ids),
            "state": after.state,
        },
        "historical_before": list(historical_before),
        "historical_after": list(historical_after),
        "branch_history_preserved": all(
            node_id in historical_after
            for node_id in ("branch_a_2", "branch_a_3", "branch_b_2", "branch_b_3")
        ),
        "rejoin_visible_after": "rejoin_4" in historical_after,
        "post_visible_after": "post_5" in historical_after,
        "line_identity_count": 1,
    }


def late_known_rejoin_scenario() -> dict[str, object]:
    tree = build_late_known_rejoin()

    frontier_2025 = tree.frontier(cutoff=2025)
    nodes_2025 = tree.historical_nodes(cutoff=2025)

    frontier_2026 = tree.frontier(cutoff=2026)
    nodes_2026 = tree.historical_nodes(cutoff=2026)

    retro = tree.raw["retro_r4"]

    return {
        "retro_raw": {
            "known_at": retro.known_at,
            "logical_at": retro.logical_at,
        },
        "cutoff_2025": {
            "frontier": list(frontier_2025.active_node_ids),
            "state": frontier_2025.state,
            "visible_nodes": list(nodes_2025),
        },
        "cutoff_2026": {
            "frontier": list(frontier_2026.active_node_ids),
            "state": frontier_2026.state,
            "visible_nodes": list(nodes_2026),
        },
        "retro_rejoin_raw_closure": sorted(tree.node_raw_closure("retro_rejoin_4")),
    }


def no_history_rewrite_scenario() -> dict[str, object]:
    tree = build_standard_rejoin()

    before_rejoin = set(tree.historical_nodes(cutoff=2023))
    after_rejoin = set(tree.historical_nodes(cutoff=2025))

    fork_nodes = {"branch_a_2", "branch_a_3", "branch_b_2", "branch_b_3"}

    return {
        "fork_nodes_visible_before": sorted(fork_nodes & before_rejoin),
        "fork_nodes_visible_after": sorted(fork_nodes & after_rejoin),
        "fork_history_erased": not fork_nodes <= after_rejoin,
        "current_frontier": list(tree.frontier(cutoff=2025).active_node_ids),
        "current_state": tree.frontier(cutoff=2025).state,
        "historical_divergence_preserved": fork_nodes <= after_rejoin,
        "current_convergence_present": tree.frontier(cutoff=2025).active_node_ids == ("post_5",),
    }


def report() -> dict[str, object]:
    return {
        "experiment": "lce-branch-rejoin",
        "standard_rejoin": standard_rejoin_scenario(),
        "invalidation_reopens_branches": invalidation_reopens_branches_scenario(),
        "late_known_rejoin": late_known_rejoin_scenario(),
        "no_history_rewrite": no_history_rewrite_scenario(),
        "non_claims": [
            "multi-parent rejoin node is a structural fixture, not production convergence semantics",
            "the experiment does not define the semantic threshold for declaring convergence",
            "Worktree remains the public concept even though the internal structure is DAG-like",
        ],
    }


def main() -> None:
    print(json.dumps(report(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
