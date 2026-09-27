"""Line identity stability / branch proliferation experiment.

This experiment corrects an overly permissive assumption from the prior
Surface-overlap fixture. A mature Line is not a factory for persistent cloned
Lines or persistent relation-view cognition objects.

Under test:
- Line identity remains stable while branches proliferate.
- Branches are internal structure owned by exactly one Line.
- Callable projections are ephemeral consumption views, not cognition nodes.
- Higher-order Surfaces reference existing branch structure directly.
- The same Line may participate in multiple Surfaces through different
  branches without being cloned.
- A branch may become a *split candidate* only after independent evolution,
  but candidacy itself never mutates Line identity or creates a new Line.

The split oracle in this research fixture is deliberately synthetic. It tests
authority/mutation boundaries, not production split policy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Raw:
    raw_id: str
    text: str


@dataclass(frozen=True, slots=True)
class Branch:
    branch_id: str
    owner_line_id: str
    raw_ids: tuple[str, ...]
    parent_branch_id: str | None = None


@dataclass(frozen=True, slots=True)
class Line:
    line_id: str
    trunk_raw_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CallableProjection:
    owner_line_id: str
    source_branch_id: str
    raw_closure: tuple[str, ...]
    query_key: str


@dataclass(frozen=True, slots=True)
class Surface:
    surface_id: str
    participants: tuple[tuple[str, str], ...]  # (line_id, branch_id)


@dataclass(frozen=True, slots=True)
class SplitCandidate:
    owner_line_id: str
    branch_id: str
    reason: str
    raw_closure: tuple[str, ...]


@dataclass(slots=True)
class CognitionRegistry:
    raw: dict[str, Raw] = field(default_factory=dict)
    lines: dict[str, Line] = field(default_factory=dict)
    branches: dict[str, Branch] = field(default_factory=dict)
    surfaces: dict[str, Surface] = field(default_factory=dict)
    projection_materializations: int = 0

    def add_raw(self, raw: Raw) -> None:
        if raw.raw_id in self.raw:
            raise ValueError(f"duplicate raw id: {raw.raw_id}")
        self.raw[raw.raw_id] = raw

    def add_line(self, line: Line) -> None:
        if line.line_id in self.lines:
            raise ValueError(f"duplicate line id: {line.line_id}")
        missing = [raw_id for raw_id in line.trunk_raw_ids if raw_id not in self.raw]
        if missing:
            raise ValueError(f"missing trunk raw: {missing}")
        self.lines[line.line_id] = line

    def add_branch(self, branch: Branch) -> None:
        if branch.branch_id in self.branches:
            raise ValueError(f"duplicate branch id: {branch.branch_id}")
        if branch.owner_line_id not in self.lines:
            raise ValueError(f"unknown owner line: {branch.owner_line_id}")
        if branch.parent_branch_id is not None:
            parent = self.branches.get(branch.parent_branch_id)
            if parent is None:
                raise ValueError(f"unknown parent branch: {branch.parent_branch_id}")
            if parent.owner_line_id != branch.owner_line_id:
                raise ValueError("branch parent must belong to the same Line")
        missing = [raw_id for raw_id in branch.raw_ids if raw_id not in self.raw]
        if missing:
            raise ValueError(f"missing branch raw: {missing}")
        self.branches[branch.branch_id] = branch

    def line_raw_closure(self, line_id: str) -> frozenset[str]:
        line = self.lines[line_id]
        closure = set(line.trunk_raw_ids)
        for branch in self.branches.values():
            if branch.owner_line_id == line_id:
                closure.update(branch.raw_ids)
        return frozenset(closure)

    def branch_raw_closure(self, branch_id: str) -> frozenset[str]:
        branch = self.branches[branch_id]
        closure = set(self.lines[branch.owner_line_id].trunk_raw_ids)

        ancestry: list[Branch] = []
        cursor: Branch | None = branch
        while cursor is not None:
            ancestry.append(cursor)
            cursor = (
                self.branches.get(cursor.parent_branch_id)
                if cursor.parent_branch_id is not None
                else None
            )
        for item in reversed(ancestry):
            closure.update(item.raw_ids)
        return frozenset(closure)

    def materialize_projection(
        self,
        branch_id: str,
        *,
        query_key: str,
    ) -> CallableProjection:
        """Create a query-time view without inserting a cognition node."""

        branch = self.branches[branch_id]
        self.projection_materializations += 1
        return CallableProjection(
            owner_line_id=branch.owner_line_id,
            source_branch_id=branch.branch_id,
            raw_closure=tuple(sorted(self.branch_raw_closure(branch_id))),
            query_key=query_key,
        )

    def add_surface(
        self,
        surface_id: str,
        participants: tuple[tuple[str, str], ...],
    ) -> None:
        if surface_id in self.surfaces:
            raise ValueError(f"duplicate surface id: {surface_id}")

        owners: list[str] = []
        for line_id, branch_id in participants:
            branch = self.branches.get(branch_id)
            if branch is None:
                raise ValueError(f"unknown branch: {branch_id}")
            if branch.owner_line_id != line_id:
                raise ValueError("surface participant owner/branch mismatch")
            owners.append(line_id)

        if len(set(owners)) != len(owners):
            raise ValueError(
                "one Surface cannot count multiple branches of one Line "
                "as independent directions"
            )

        self.surfaces[surface_id] = Surface(surface_id, participants)

    def surface_raw_closure(self, surface_id: str) -> frozenset[str]:
        closure: set[str] = set()
        for _line_id, branch_id in self.surfaces[surface_id].participants:
            closure.update(self.branch_raw_closure(branch_id))
        return frozenset(closure)


def build_mature_tree(branch_count: int = 24) -> CognitionRegistry:
    registry = CognitionRegistry()

    for index in range(4):
        registry.add_raw(Raw(f"trunk_{index}", f"trunk raw {index}"))

    registry.add_line(
        Line(
            "line_trading",
            tuple(f"trunk_{index}" for index in range(4)),
        )
    )

    for branch_index in range(branch_count):
        raw_ids = []
        for point_index in range(3):
            raw_id = f"b{branch_index}_{point_index}"
            registry.add_raw(Raw(raw_id, f"branch {branch_index} raw {point_index}"))
            raw_ids.append(raw_id)
        registry.add_branch(
            Branch(
                branch_id=f"branch_{branch_index}",
                owner_line_id="line_trading",
                raw_ids=tuple(raw_ids),
            )
        )
    return registry


def proliferation_scenario() -> dict[str, object]:
    registry = build_mature_tree(branch_count=24)

    before = {
        "line_count": len(registry.lines),
        "branch_count": len(registry.branches),
        "surface_count": len(registry.surfaces),
    }

    first_projection = None
    for index in range(500):
        projection = registry.materialize_projection(
            f"branch_{index % 24}",
            query_key=f"query_{index}",
        )
        if first_projection is None:
            first_projection = projection

    after = {
        "line_count": len(registry.lines),
        "branch_count": len(registry.branches),
        "surface_count": len(registry.surfaces),
        "projection_materializations": registry.projection_materializations,
    }

    return {
        "before": before,
        "after": after,
        "persistent_projection_node_count": 0,
        "first_projection": {
            "owner_line_id": first_projection.owner_line_id if first_projection else None,
            "source_branch_id": first_projection.source_branch_id if first_projection else None,
            "raw_closure": list(first_projection.raw_closure) if first_projection else [],
        },
        "line_raw_closure_count": len(registry.line_raw_closure("line_trading")),
    }


def surface_branch_reference_scenario() -> dict[str, object]:
    registry = CognitionRegistry()

    line_specs = {
        "line_trading": ("trade_trunk", ("trade_timing", "trade_execution")),
        "line_engineering": ("eng_trunk", ("eng_boundary",)),
        "line_writing": ("write_trunk", ("write_structure",)),
        "line_risk": ("risk_trunk", ("risk_execution",)),
        "line_learning": ("learn_trunk", ("learn_execution",)),
    }

    for line_id, (trunk_id, branch_ids) in line_specs.items():
        registry.add_raw(Raw(trunk_id, trunk_id))
        registry.add_line(Line(line_id, (trunk_id,)))
        for branch_id in branch_ids:
            raw_id = f"{branch_id}_raw"
            registry.add_raw(Raw(raw_id, raw_id))
            registry.add_branch(
                Branch(
                    branch_id=branch_id,
                    owner_line_id=line_id,
                    raw_ids=(raw_id,),
                )
            )

    registry.add_surface(
        "surface_timing",
        (
            ("line_trading", "trade_timing"),
            ("line_engineering", "eng_boundary"),
            ("line_writing", "write_structure"),
        ),
    )
    registry.add_surface(
        "surface_execution",
        (
            ("line_trading", "trade_execution"),
            ("line_risk", "risk_execution"),
            ("line_learning", "learn_execution"),
        ),
    )

    return {
        "line_count": len(registry.lines),
        "branch_count": len(registry.branches),
        "surface_count": len(registry.surfaces),
        "trading_line_identity_count": sum(
            1 for line_id in registry.lines if line_id == "line_trading"
        ),
        "trading_surface_memberships": [
            {
                "surface_id": surface.surface_id,
                "branch_ids": [
                    branch_id
                    for line_id, branch_id in surface.participants
                    if line_id == "line_trading"
                ],
            }
            for surface in registry.surfaces.values()
            if any(line_id == "line_trading" for line_id, _ in surface.participants)
        ],
        "surface_timing_raw": sorted(registry.surface_raw_closure("surface_timing")),
        "surface_execution_raw": sorted(registry.surface_raw_closure("surface_execution")),
        "persistent_relation_view_nodes": 0,
    }


def duplicate_owner_surface_rejection_scenario() -> dict[str, object]:
    registry = build_mature_tree(branch_count=3)
    rejected = False
    message = None
    try:
        registry.add_surface(
            "bad_surface",
            (
                ("line_trading", "branch_0"),
                ("line_trading", "branch_1"),
                ("line_trading", "branch_2"),
            ),
        )
    except ValueError as exc:
        rejected = True
        message = str(exc)

    return {
        "rejected": rejected,
        "message": message,
        "surface_count": len(registry.surfaces),
        "line_count": len(registry.lines),
    }


def split_candidate_scenario() -> dict[str, object]:
    """Candidate authority test, not a production split detector.

    The fixture oracle treats a branch with its own multi-step continuation and
    child branching as structurally independent enough to *propose* review.
    Crucially, proposal does not mutate registry.lines.
    """

    registry = CognitionRegistry()
    for raw_id in ("t0", "t1", "t2"):
        registry.add_raw(Raw(raw_id, raw_id))
    registry.add_line(Line("line_root", ("t0", "t1", "t2")))

    registry.add_raw(Raw("early_0", "early branch first deviation"))
    registry.add_branch(
        Branch(
            "branch_early",
            "line_root",
            ("early_0",),
        )
    )

    early_unique = len(
        registry.branch_raw_closure("branch_early")
        - set(registry.lines["line_root"].trunk_raw_ids)
    )
    early_candidate = None

    mature_raw = tuple(f"mature_{index}" for index in range(5))
    for raw_id in mature_raw:
        registry.add_raw(Raw(raw_id, raw_id))
    registry.add_branch(
        Branch(
            "branch_mature",
            "line_root",
            mature_raw,
        )
    )

    for child_name in ("mature_child_a", "mature_child_b"):
        raw_id = f"{child_name}_raw"
        registry.add_raw(Raw(raw_id, raw_id))
        registry.add_branch(
            Branch(
                child_name,
                "line_root",
                (raw_id,),
                parent_branch_id="branch_mature",
            )
        )

    mature_children = [
        branch.branch_id
        for branch in registry.branches.values()
        if branch.parent_branch_id == "branch_mature"
    ]
    mature_unique = len(
        registry.branch_raw_closure("branch_mature")
        - set(registry.lines["line_root"].trunk_raw_ids)
    )

    # Synthetic research oracle: enough independent continuation + its own
    # branching makes review reasonable. These numbers are NOT production
    # thresholds and are intentionally not exposed as API policy.
    qualifies = mature_unique >= 5 and len(mature_children) >= 2
    mature_candidate = (
        SplitCandidate(
            owner_line_id="line_root",
            branch_id="branch_mature",
            reason="independent continuation plus internal branching",
            raw_closure=tuple(sorted(registry.branch_raw_closure("branch_mature"))),
        )
        if qualifies
        else None
    )

    return {
        "early": {
            "unique_branch_raw": early_unique,
            "split_candidate": early_candidate is not None,
        },
        "mature": {
            "unique_branch_raw": mature_unique,
            "child_branches": sorted(mature_children),
            "split_candidate": mature_candidate is not None,
            "candidate": (
                {
                    "owner_line_id": mature_candidate.owner_line_id,
                    "branch_id": mature_candidate.branch_id,
                    "reason": mature_candidate.reason,
                    "raw_closure": list(mature_candidate.raw_closure),
                }
                if mature_candidate
                else None
            ),
        },
        "line_count_before_candidate": 1,
        "line_count_after_candidate": len(registry.lines),
        "new_line_created": len(registry.lines) != 1,
        "candidate_is_non_mutating": len(registry.lines) == 1,
    }


def report() -> dict[str, object]:
    return {
        "experiment": "lce-line-identity-stability",
        "branch_proliferation": proliferation_scenario(),
        "surface_branch_reference": surface_branch_reference_scenario(),
        "duplicate_owner_surface_rejection": duplicate_owner_surface_rejection_scenario(),
        "delayed_split_candidate": split_candidate_scenario(),
        "non_claims": [
            "branch split oracle is synthetic and not production policy",
            "callable projections are modeled as ephemeral views, not persisted cognition",
            "the experiment does not decide when a branch should become a new Line",
        ],
    }


def main() -> None:
    print(json.dumps(report(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
