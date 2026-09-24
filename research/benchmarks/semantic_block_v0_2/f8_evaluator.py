"""Gold-grounded, fixed-budget F8 evaluation for SemanticBlock v0.2.

The v0.2 probe file is input data and is deliberately left unchanged. This
evaluator consumes its gold state keys and scores extraction/path recovery
separately from vector-only versus graph-assisted retrieval.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from research.benchmarks.semantic_block_v0_1.contracts import PredictionRecord
from research.benchmarks.semantic_block_v0_1.scorer.alignment import align_states


@dataclass(slots=True)
class RetrievalTraceV02:
    seed_gold_state_id: str
    method: str
    candidate_ids: list[str]
    candidate_gold_state_ids: list[str | None]
    candidate_scores: dict[str, float]
    graph_proposed_ids: list[str]
    graph_proposal_paths: dict[str, list[str]]
    graph_proposal_relation_ids: dict[str, list[str]]
    candidate_count: int
    precision: float
    recall: float
    relevant_gold_count: int


@dataclass(slots=True)
class F8ProbeResultV02:
    probe_id: str
    case_id: str
    arm_id: str
    pass_gate: bool
    extraction_path_pass: bool
    retrieval_budget_pass: bool
    before_bridge_detected: bool
    alignment: dict[str, str]
    missing_gold_states: list[str]
    missing_required_edges: list[tuple[str, str]]
    wrong_direction_edges: list[tuple[str, str]]
    forbidden_direct_edges: list[tuple[str, str]]
    invalid_relation_endpoints: list[str]
    unmatched_to_gold_relation_endpoints: list[str]
    invalid_relation_cues: list[str]
    cause_paths: dict[str, list[str]]
    traces: list[RetrievalTraceV02]
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_l = math.sqrt(sum(a * a for a in left))
    norm_r = math.sqrt(sum(b * b for b in right))
    if norm_l == 0.0 or norm_r == 0.0:
        return 0.0
    return dot / (norm_l * norm_r)


def _reachable_path(
    adjacency: dict[str, list[tuple[str, str]]],
    source: str,
    target: str,
    max_hops: int = 2,
) -> list[str] | None:
    frontier: list[tuple[str, list[str]]] = [(source, [source])]
    while frontier:
        node, path = frontier.pop(0)
        if len(path) - 1 >= max_hops:
            continue
        for neighbor, _rel_id in adjacency.get(node, []):
            if neighbor in path:
                continue
            next_path = [*path, neighbor]
            if neighbor == target:
                return next_path
            frontier.append((neighbor, next_path))
    return None


def _visible_gold(gold_case: dict[str, Any], cutoff: str) -> list[dict[str, Any]]:
    entry = next((v for v in gold_case["visibility"] if v["cutoff"] == cutoff), None)
    if entry is None:
        raise ValueError(f"Gold has no visibility entry for {gold_case['case_id']} at {cutoff}")
    visible_ids = set(entry["visible_state_ids"])
    return [state for state in gold_case["states"] if state["state_id"] in visible_ids]


def evaluate_f8_probe_v02(
    prediction: PredictionRecord,
    gold_case: dict[str, Any],
    probe: dict[str, Any],
    embeddings: dict[str, list[float]],
    visible_evidence: Iterable[dict[str, Any]],
) -> F8ProbeResultV02:
    """Evaluate one arm against one unchanged v0.2 F8 probe.

    ``embeddings`` is keyed by predicted immutable state ID. Supplying vectors
    makes the function deterministic and keeps model/API work outside scoring.
    The candidate universe is always the arm's own admitted, cutoff-visible
    blocks; both retrieval methods return at most the probe's total budget.
    """
    if prediction.case_id != probe["case_id"] or gold_case["case_id"] != probe["case_id"]:
        raise ValueError("prediction, probe, and gold case IDs must match")
    if prediction.cutoff != probe["cutoff"]:
        raise ValueError("prediction cutoff does not match the fixed probe cutoff")

    errors: list[str] = []
    k = int(probe["k"])
    if k != 3:
        errors.append(f"unexpected_total_candidate_budget:{k}")
    visible_ev = {
        e["evidence_id"]: e
        for e in visible_evidence
        if e.get("available_at", "") <= prediction.cutoff
    }
    pred_blocks = [b for b in prediction.blocks if b.state_available_at <= prediction.cutoff]
    pred_by_id = {b.state_id: b for b in pred_blocks}
    gold_states = _visible_gold(gold_case, prediction.cutoff)
    gold_by_id = {state["state_id"]: state for state in gold_states}

    # The existing span aligner expects a v0.1 ``state_key`` alias. This is
    # an in-memory view only; the frozen v0.2 gold file is never rewritten.
    gold_for_alignment = [{**s, "state_key": s["state_id"]} for s in gold_states]
    alignment_result = align_states(pred_blocks, gold_for_alignment)
    pred_to_gold = alignment_result.pred_to_gold
    gold_to_pred = alignment_result.gold_to_pred
    missing_gold = list(alignment_result.unmatched_golds)

    invalid_endpoints: list[str] = []
    unmatched_to_gold: list[str] = []
    invalid_cues: list[str] = []
    mapped_causes: set[tuple[str, str]] = set()
    cause_adj: dict[str, list[tuple[str, str]]] = {}
    before_bridge_detected = False
    for index, relation in enumerate(prediction.relations):
        rel_id = f"{relation.type}:{relation.source_state_id}->{relation.target_state_id}:{index}"
        if relation.source_state_id not in pred_by_id or relation.target_state_id not in pred_by_id:
            invalid_endpoints.append(rel_id)
            continue
        cue = relation.cue_span
        if cue is not None:
            ev = visible_ev.get(cue.evidence_id)
            if (
                ev is None
                or not (0 <= cue.char_start < cue.char_end <= len(ev["content"]))
                or ev["content"][cue.char_start:cue.char_end] != cue.text
            ):
                invalid_cues.append(rel_id)
                continue
        elif relation.type in {"CAUSE", "BEFORE"} or relation.basis != "authorized_registry":
            invalid_cues.append(rel_id)
            continue

        if relation.type == "BEFORE" and relation.traversal_allowed:
            before_bridge_detected = True
            errors.append(f"before_traversal_enabled:{rel_id}")
        if relation.type != "CAUSE":
            continue
        source_gold = pred_to_gold.get(relation.source_state_id)
        target_gold = pred_to_gold.get(relation.target_state_id)
        if source_gold and target_gold:
            mapped_causes.add((source_gold, target_gold))
        else:
            unmatched_to_gold.append(rel_id)
        # F8 graph retrieval is specifically the directed CAUSE graph. BEFORE
        # is never inserted into the adjacency map, even if a route marked it
        # traversable; that policy violation is separately reported above.
        if relation.traversal_allowed:
            cause_adj.setdefault(relation.source_state_id, []).append((relation.target_state_id, rel_id))

    required = {tuple(edge) for edge in probe.get("required_directed_cause_edge_pairs", [])}
    forbidden = {tuple(edge) for edge in probe.get("forbidden_direct_shortcuts", [])}
    missing_edges = sorted(required - mapped_causes)
    wrong_direction = sorted(
        (src, tgt) for src, tgt in required if (tgt, src) in mapped_causes
    )
    forbidden_edges = sorted(forbidden & mapped_causes)
    if missing_gold:
        errors.append(f"missing_gold_states:{','.join(missing_gold)}")
    if missing_edges:
        errors.append(f"missing_required_cause_edges:{missing_edges}")
    if wrong_direction:
        errors.append(f"wrong_direction_cause_edges:{wrong_direction}")
    if forbidden_edges:
        errors.append(f"forbidden_direct_cause_edges:{forbidden_edges}")
    if invalid_endpoints:
        errors.append(f"invalid_relation_endpoints:{invalid_endpoints}")
    if invalid_cues:
        errors.append(f"invalid_relation_cues:{invalid_cues}")

    seed_gold = probe["gold_seed_state_key"]
    relevant_gold = set(probe["relevant_gold_endpoint_keys"])
    seed_pred = gold_to_pred.get(seed_gold)
    cause_paths: dict[str, list[str]] = {}
    if seed_pred is None:
        errors.append(f"seed_gold_state_missing:{seed_gold}")
    else:
        for gold_target in relevant_gold:
            target_pred = gold_to_pred.get(gold_target)
            if target_pred is not None:
                path = _reachable_path(cause_adj, seed_pred, target_pred)
                if path:
                    cause_paths[gold_target] = [pred_to_gold.get(pid, pid) for pid in path]

    required_probe_states = {seed_gold, *relevant_gold}
    missing_probe_states = required_probe_states - set(gold_to_pred)
    if missing_probe_states:
        errors.append(f"missing_probe_gold_states:{sorted(missing_probe_states)}")
    path_pass = (
        not missing_probe_states
        and not missing_edges
        and not wrong_direction
        and not forbidden_edges
        and not invalid_endpoints
        and not invalid_cues
        and not before_bridge_detected
    )
    if required:
        path_pass = path_pass and relevant_gold.issubset(cause_paths)
    else:
        # Negative-control lane: no prohibited directed cause edge and no
        # directed CAUSE path from its gold seed to a relevant endpoint.
        path_pass = path_pass and not cause_paths

    traces: list[RetrievalTraceV02] = []
    retrieval_budget_pass = True
    if seed_pred is not None and seed_pred in pred_by_id:
        missing_vectors = sorted(set(pred_by_id) - set(embeddings))
        if missing_vectors:
            errors.append(f"missing_embeddings:{missing_vectors}")
            retrieval_budget_pass = False
        else:
            seed_vector = embeddings[seed_pred]
            scores = {
                pid: _cosine(seed_vector, embeddings[pid])
                for pid in pred_by_id
            }
            vector_ranked = sorted(scores, key=lambda pid: (-scores[pid], pid))

            def fixed_budget(seed: str, ranked: list[str]) -> list[str]:
                # Count the seed consistently in both methods and within k.
                return [seed, *(pid for pid in ranked if pid != seed)][:k]

            vector_candidates = fixed_budget(seed_pred, vector_ranked)
            graph_paths: dict[str, list[str]] = {}
            graph_path_edges: dict[str, list[str]] = {}
            frontier = [(seed_pred, [seed_pred], [])]
            for _ in range(2):
                next_frontier: list[tuple[str, list[str], list[str]]] = []
                for node, path, edge_path in frontier:
                    for neighbor, rel_id in cause_adj.get(node, []):
                        if neighbor in path or neighbor not in pred_by_id:
                            continue
                        next_path = [*path, neighbor]
                        next_edge_path = [*edge_path, rel_id]
                        graph_paths.setdefault(neighbor, next_path)
                        graph_path_edges.setdefault(neighbor, next_edge_path)
                        next_frontier.append((neighbor, next_path, next_edge_path))
                frontier = next_frontier
            graph_ranked = sorted(
                graph_paths,
                key=lambda pid: (len(graph_paths[pid]), -scores.get(pid, 0.0), pid),
            )
            graph_candidates = fixed_budget(seed_pred, [*graph_ranked, *vector_ranked])

            for method, candidates, proposals, paths, edges in (
                ("vector_only", vector_candidates, [], {}, {}),
                ("vector_plus_cause_graph", graph_candidates, graph_ranked, graph_paths, graph_path_edges),
            ):
                candidate_gold = [pred_to_gold.get(pid) for pid in candidates]
                true_positives = sum(gid in relevant_gold for gid in candidate_gold)
                traces.append(RetrievalTraceV02(
                    seed_gold_state_id=seed_gold,
                    method=method,
                    candidate_ids=list(candidates),
                    candidate_gold_state_ids=candidate_gold,
                    candidate_scores={pid: scores[pid] for pid in candidates},
                    graph_proposed_ids=list(proposals),
                    graph_proposal_paths={pid: [pred_to_gold.get(node, node) for node in paths[pid]] for pid in proposals},
                    graph_proposal_relation_ids={pid: edges[pid] for pid in proposals},
                    candidate_count=len(candidates),
                    precision=true_positives / len(candidates) if candidates else 0.0,
                    recall=true_positives / len(relevant_gold) if relevant_gold else 1.0,
                    relevant_gold_count=len(relevant_gold),
                ))
                if len(candidates) > k:
                    retrieval_budget_pass = False
            before_graph_ids = {
                pid
                for trace in traces
                for pid, edge_ids in trace.graph_proposal_relation_ids.items()
                if any(rel.startswith("BEFORE:") for rel in edge_ids)
            }
            if before_graph_ids:
                before_bridge_detected = True
                errors.append(f"before_derived_graph_proposals:{sorted(before_graph_ids)}")
    else:
        retrieval_budget_pass = False

    if not retrieval_budget_pass:
        errors.append("retrieval_budget_or_vector_input_invalid")
    return F8ProbeResultV02(
        probe_id=probe["probe_id"],
        case_id=prediction.case_id,
        arm_id=prediction.arm_id,
        pass_gate=path_pass and retrieval_budget_pass,
        extraction_path_pass=path_pass,
        retrieval_budget_pass=retrieval_budget_pass,
        before_bridge_detected=before_bridge_detected,
        alignment=dict(pred_to_gold),
        missing_gold_states=missing_gold,
        missing_required_edges=missing_edges,
        wrong_direction_edges=wrong_direction,
        forbidden_direct_edges=forbidden_edges,
        invalid_relation_endpoints=invalid_endpoints,
        unmatched_to_gold_relation_endpoints=unmatched_to_gold,
        invalid_relation_cues=invalid_cues,
        cause_paths=cause_paths,
        traces=traces,
        errors=errors,
    )
