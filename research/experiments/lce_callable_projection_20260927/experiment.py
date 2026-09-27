"""Callable projection and falsifiable compiled-cognition experiment.

The experiment tests a narrow engineering hypothesis:

* LCE projections may be consumed and may themselves be inputs to higher derived
  projections.
* Only Raw Evidence is independent evidence authority.
* Every derived projection closes back to Raw Evidence.
* Repeated consumption or recursive projection use cannot manufacture support.
* Raw invalidation/correction can move a compiled result back to UNKNOWN or
  WRONG without rewriting Raw Evidence.
* Retrieval happens over naturally formed projections; there is no manually
  assigned abstraction-level taxonomy.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, replace
from typing import Iterable, Mapping


SUPPORTED = "SUPPORTED"
UNKNOWN = "UNKNOWN"
WRONG = "WRONG"


@dataclass(frozen=True, slots=True)
class RawEvidence:
    evidence_id: str
    features: frozenset[str]
    text: str
    valid: bool = True


@dataclass(frozen=True, slots=True)
class Projection:
    projection_id: str
    features: frozenset[str]
    sources: tuple[str, ...]
    text: str


@dataclass(frozen=True, slots=True)
class Consumption:
    projection_id: str
    text: str
    raw_support: frozenset[str]


class ProjectionGraph:
    """Two-authority graph: Raw Evidence and rebuildable derived projections."""

    def __init__(self) -> None:
        self.raw: dict[str, RawEvidence] = {}
        self.projections: dict[str, Projection] = {}
        self.usage_count: Counter[str] = Counter()

    def add_raw(self, evidence: RawEvidence) -> None:
        if evidence.evidence_id in self.raw or evidence.evidence_id in self.projections:
            raise ValueError(f"duplicate node id: {evidence.evidence_id}")
        self.raw[evidence.evidence_id] = evidence

    def add_projection(self, projection: Projection) -> None:
        if projection.projection_id in self.raw or projection.projection_id in self.projections:
            raise ValueError(f"duplicate node id: {projection.projection_id}")
        for source_id in projection.sources:
            if source_id not in self.raw and source_id not in self.projections:
                raise ValueError(
                    f"projection {projection.projection_id} has unknown source {source_id}"
                )
        self.projections[projection.projection_id] = projection

    def invalidate_raw(self, evidence_id: str) -> None:
        evidence = self.raw[evidence_id]
        self.raw[evidence_id] = replace(evidence, valid=False)

    def raw_closure(self, node_id: str) -> frozenset[str]:
        """Return unique Raw Evidence support; derived nodes never count as evidence."""

        return self._raw_closure(node_id, visiting=frozenset())

    def _raw_closure(
        self,
        node_id: str,
        *,
        visiting: frozenset[str],
    ) -> frozenset[str]:
        if node_id in self.raw:
            return frozenset({node_id})
        if node_id not in self.projections:
            raise KeyError(node_id)
        if node_id in visiting:
            raise ValueError(f"projection cycle detected at {node_id}")
        next_visiting = visiting | {node_id}
        closure: set[str] = set()
        for source_id in self.projections[node_id].sources:
            closure.update(
                self._raw_closure(
                    source_id,
                    visiting=next_visiting,
                )
            )
        return frozenset(closure)

    def valid_raw_closure(self, node_id: str) -> frozenset[str]:
        return frozenset(
            evidence_id
            for evidence_id in self.raw_closure(node_id)
            if self.raw[evidence_id].valid
        )

    def dependency_depth(self, node_id: str) -> int:
        """Audit-only graph depth. It is not an abstraction class or retrieval gate."""

        if node_id in self.raw:
            return 0
        projection = self.projections[node_id]
        return 1 + max(
            (self.dependency_depth(source_id) for source_id in projection.sources),
            default=0,
        )

    def consume(self, projection_id: str) -> Consumption:
        projection = self.projections[projection_id]
        self.usage_count[projection_id] += 1
        return Consumption(
            projection_id=projection_id,
            text=projection.text,
            raw_support=self.valid_raw_closure(projection_id),
        )

    def affected_projections(self, evidence_id: str) -> tuple[str, ...]:
        if evidence_id not in self.raw:
            raise KeyError(evidence_id)
        return tuple(
            sorted(
                projection_id
                for projection_id in self.projections
                if evidence_id in self.raw_closure(projection_id)
            )
        )


def jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def rank_callable_projections(
    graph: ProjectionGraph,
    query_features: frozenset[str],
    *,
    candidate_ids: Iterable[str] | None = None,
) -> tuple[tuple[str, float], ...]:
    """Rank already-compiled callable views directly, without scanning Raw Evidence."""

    ids = tuple(candidate_ids) if candidate_ids is not None else tuple(graph.projections)
    scored = [
        (
            projection_id,
            jaccard(
                query_features,
                graph.projections[projection_id].features,
            ),
        )
        for projection_id in ids
    ]
    return tuple(sorted(scored, key=lambda item: (item[1], item[0]), reverse=True))


def evaluate_compiled_claim(
    graph: ProjectionGraph,
    projection_id: str,
    *,
    raw_signal: Mapping[str, float],
    min_independent_support: int = 2,
    supported_threshold: float = 0.25,
    wrong_threshold: float = -0.25,
) -> dict[str, object]:
    """Synthetic falsification oracle.

    Signals are fixture-only evidence about one specific claim. They are not a
    production semantic ontology. The experiment only tests authority and
    rollback mechanics.
    """

    support = graph.valid_raw_closure(projection_id)
    values = [raw_signal[evidence_id] for evidence_id in support if evidence_id in raw_signal]

    if len(values) < min_independent_support:
        status = UNKNOWN
        mean_signal = None if not values else sum(values) / len(values)
    else:
        mean_signal = sum(values) / len(values)
        if mean_signal >= supported_threshold:
            status = SUPPORTED
        elif mean_signal <= wrong_threshold:
            status = WRONG
        else:
            status = UNKNOWN

    return {
        "status": status,
        "valid_raw_support": sorted(support),
        "independent_support_count": len(support),
        "mean_fixture_signal": mean_signal,
        "usage_count": graph.usage_count[projection_id],
    }


def build_trading_projection_graph() -> ProjectionGraph:
    graph = ProjectionGraph()

    raws = (
        RawEvidence(
            "r_exec_1",
            frozenset({"trading", "execution", "breakout", "entry", "weak_followthrough"}),
            "A breakout entry failed to follow through.",
        ),
        RawEvidence(
            "r_exec_2",
            frozenset({"trading", "execution", "breakout", "sector", "followthrough"}),
            "Breakout quality depends on sector strength and follow-through.",
        ),
        RawEvidence(
            "r_exec_3",
            frozenset({"trading", "execution", "entry", "slippage", "stop"}),
            "Entry quality and slippage changed the realized trade.",
        ),
        RawEvidence(
            "r_timing_1",
            frozenset({"trading", "timing", "sector", "breadth", "rotation"}),
            "Timing improved when sector breadth and rotation aligned.",
        ),
        RawEvidence(
            "r_timing_2",
            frozenset({"trading", "timing", "macro", "sentiment", "liquidity"}),
            "Macro liquidity and sentiment changed the timing regime.",
        ),
        RawEvidence(
            "r_phil_1",
            frozenset({"trading", "certainty", "optionality", "valuation", "expectation"}),
            "High apparent certainty can already be priced.",
        ),
    )
    for evidence in raws:
        graph.add_raw(evidence)

    graph.add_projection(
        Projection(
            "p_execution",
            frozenset(
                {
                    "trading",
                    "execution",
                    "breakout",
                    "entry",
                    "weak_followthrough",
                    "slippage",
                }
            ),
            ("r_exec_1", "r_exec_2", "r_exec_3"),
            "Execution currently treats breakout shape as insufficient without entry quality, follow-through, and context.",
        )
    )
    graph.add_projection(
        Projection(
            "p_timing",
            frozenset({"trading", "timing", "sector", "breadth", "macro", "liquidity"}),
            ("r_timing_1", "r_timing_2"),
            "Timing depends on sector breadth plus the broader liquidity/sentiment regime.",
        )
    )
    graph.add_projection(
        Projection(
            "p_philosophy",
            frozenset({"trading", "certainty", "optionality", "valuation", "expectation"}),
            ("r_phil_1",),
            "The current philosophy treats apparent certainty as something that may already be priced.",
        )
    )

    graph.add_projection(
        Projection(
            "p_trading_line",
            frozenset(
                {
                    "trading",
                    "execution",
                    "breakout",
                    "entry",
                    "weak_followthrough",
                    "slippage",
                    "timing",
                    "sector",
                    "breadth",
                    "macro",
                    "liquidity",
                    "certainty",
                    "optionality",
                    "valuation",
                    "expectation",
                }
            ),
            ("p_execution", "p_timing", "p_philosophy"),
            "A long compiled trading line spanning execution, timing, and philosophy.",
        )
    )

    # Higher derived object deliberately reuses a branch source. Raw closure
    # must deduplicate it rather than treating projection reuse as new evidence.
    graph.add_projection(
        Projection(
            "p_reused_higher",
            frozenset({"trading", "execution", "timing", "certainty"}),
            ("p_execution", "p_timing", "p_execution"),
            "A higher derived view built from already compiled branches.",
        )
    )
    return graph


def callable_projection_scenario() -> dict[str, object]:
    graph = build_trading_projection_graph()
    query = frozenset(
        {"trading", "execution", "breakout", "entry", "weak_followthrough"}
    )
    candidates = ("p_execution", "p_timing", "p_philosophy", "p_trading_line")
    ranked = rank_callable_projections(graph, query, candidate_ids=candidates)
    selected_id, selected_score = ranked[0]
    payload = graph.consume(selected_id)

    full_line_features = len(graph.projections["p_trading_line"].features)
    selected_features = len(graph.projections[selected_id].features)

    graph.add_raw(
        RawEvidence(
            "r_exec_4",
            frozenset(
                {"trading", "execution", "breakout", "entry", "weak_followthrough"}
            ),
            "I bought a breakout today and it underperformed immediately.",
        )
    )

    reroute = rank_callable_projections(
        graph,
        graph.raw["r_exec_4"].features,
        candidate_ids=candidates,
    )
    graph.add_projection(
        Projection(
            "p_execution_v2",
            graph.projections["p_execution"].features
            | frozenset({"underperformance"}),
            ("p_execution", "r_exec_4"),
            "Execution branch after a new underperforming breakout observation.",
        )
    )

    return {
        "query_ranking": [
            {"projection_id": projection_id, "score": score}
            for projection_id, score in ranked
        ],
        "selected_projection": selected_id,
        "selected_score": selected_score,
        "consumer_raw_support": sorted(payload.raw_support),
        "consumer_context_feature_count": selected_features,
        "full_line_feature_count": full_line_features,
        "context_reduction_fraction": 1.0 - selected_features / full_line_features,
        "new_raw_routed_to": reroute[0][0],
        "old_execution_raw_closure": sorted(graph.raw_closure("p_execution")),
        "extended_execution_raw_closure": sorted(
            graph.raw_closure("p_execution_v2")
        ),
        "reused_higher_raw_closure": sorted(
            graph.raw_closure("p_reused_higher")
        ),
        "reused_higher_dependency_depth": graph.dependency_depth("p_reused_higher"),
    }


def no_self_evidence_scenario(consumptions: int = 100) -> dict[str, object]:
    graph = ProjectionGraph()
    for evidence_id in ("a", "b", "c"):
        graph.add_raw(
            RawEvidence(
                evidence_id,
                frozenset({"same_compiled_claim", evidence_id}),
                f"raw evidence {evidence_id}",
            )
        )

    graph.add_projection(
        Projection(
            "p",
            frozenset({"same_compiled_claim"}),
            ("a", "b", "c"),
            "compiled claim",
        )
    )
    graph.add_projection(
        Projection(
            "q",
            frozenset({"same_compiled_claim", "higher"}),
            ("p", "p", "a"),
            "higher projection reusing p",
        )
    )

    before = graph.raw_closure("q")
    for _ in range(consumptions):
        graph.consume("p")
        graph.consume("q")
    after = graph.raw_closure("q")

    return {
        "raw_nodes": sorted(graph.raw),
        "projection_nodes": sorted(graph.projections),
        "q_raw_closure_before_usage": sorted(before),
        "q_raw_closure_after_usage": sorted(after),
        "p_usage_count": graph.usage_count["p"],
        "q_usage_count": graph.usage_count["q"],
        "independent_support_count": len(after),
    }


def rollback_scenario() -> dict[str, object]:
    graph = ProjectionGraph()
    for evidence in (
        RawEvidence("a", frozenset({"claim", "early"}), "early support A"),
        RawEvidence("b", frozenset({"claim", "early"}), "early support B"),
        RawEvidence("c", frozenset({"claim", "early"}), "early support C"),
    ):
        graph.add_raw(evidence)

    graph.add_projection(
        Projection(
            "p_initial",
            frozenset({"claim"}),
            ("a", "b", "c"),
            "current compiled claim",
        )
    )

    signal = {"a": 1.0, "b": 0.8, "c": 0.6}
    initial = evaluate_compiled_claim(
        graph,
        "p_initial",
        raw_signal=signal,
    )

    # Usage is deliberately large; it must not change evidence authority.
    for _ in range(250):
        graph.consume("p_initial")
    after_usage = evaluate_compiled_claim(
        graph,
        "p_initial",
        raw_signal=signal,
    )

    # Two raw sources are later invalidated/corrected. The projection remains an
    # auditable historical derived object, but current valid support collapses.
    graph.invalidate_raw("b")
    graph.invalidate_raw("c")
    after_invalidation = evaluate_compiled_claim(
        graph,
        "p_initial",
        raw_signal=signal,
    )

    # New raw evidence is genuinely independent evidence. It can falsify the
    # old compiled claim. The old projection is an input/provenance carrier, not
    # a vote.
    graph.add_raw(
        RawEvidence("d", frozenset({"claim", "correction"}), "new correction D")
    )
    graph.add_raw(
        RawEvidence("e", frozenset({"claim", "correction"}), "new correction E")
    )
    signal.update({"d": -1.0, "e": -1.0})

    graph.add_projection(
        Projection(
            "p_recompiled",
            frozenset({"claim", "rechecked"}),
            ("p_initial", "d", "e"),
            "claim recompiled after corrections",
        )
    )
    recompiled = evaluate_compiled_claim(
        graph,
        "p_recompiled",
        raw_signal=signal,
    )

    # If the corrective raw evidence itself is later invalidated, the system is
    # allowed to return to UNKNOWN rather than preserving WRONG as dogma.
    graph.invalidate_raw("d")
    graph.invalidate_raw("e")
    after_correction_invalidation = evaluate_compiled_claim(
        graph,
        "p_recompiled",
        raw_signal=signal,
    )

    return {
        "initial": initial,
        "after_250_consumptions": after_usage,
        "after_source_invalidation": after_invalidation,
        "recompiled_with_new_raw_corrections": recompiled,
        "after_correction_invalidation": after_correction_invalidation,
        "affected_by_b": list(graph.affected_projections("b")),
        "p_initial_raw_closure": sorted(graph.raw_closure("p_initial")),
        "p_recompiled_raw_closure": sorted(graph.raw_closure("p_recompiled")),
        "raw_authority_nodes": sorted(graph.raw),
        "derived_nodes": sorted(graph.projections),
    }


def report() -> dict[str, object]:
    return {
        "experiment": "lce-callable-projection-falsifiability",
        "authority_contract": {
            "raw_evidence": "only independent evidence authority",
            "projection": (
                "derived/rebuildable cognition; callable and recursively usable "
                "without becoming independent evidence"
            ),
            "unknown": "legal current compiled result when valid support is insufficient",
            "wrong": "legal current compiled result when valid raw evidence falsifies a claim",
            "abstraction_levels": "not assigned; dependency structure emerges from projections",
        },
        "callable_projection": callable_projection_scenario(),
        "no_self_evidence": no_self_evidence_scenario(),
        "rollback": rollback_scenario(),
    }


def main() -> None:
    print(json.dumps(report(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
