"""Probe F8: Vector-only vs Graph-backed retrieval on identical accepted C blocks (B17 sentinel).

Tests k=3 retrieval, 2 relation hops from seeds:
- Seed 1: A-login (s1)
- Seed 2: X-failure / appearance (s4)
Requires:
- Positive C/P: recovers s4->s5->s6 CAUSE path.
- Negative N: zero CAUSE path.
- BEFORE edges contribute ZERO generic bridge candidates (traversal_allowed=False).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from research.benchmarks.semantic_block_v0_1.contracts import (
    PredictionRecord,
    PublicRelation,
    PublicSemanticBlock,
)
from research.benchmarks.semantic_block_v0_1.llm_client import embed_texts


def _cosine_similarity(u: list[float], v: list[float]) -> float:
    dot = sum(a * b for a, b in zip(u, v))
    norm_u = math.sqrt(sum(a * a for a in u))
    norm_v = math.sqrt(sum(b * b for b in v))
    if norm_u == 0.0 or norm_v == 0.0:
        return 0.0
    return dot / (norm_u * norm_v)


@dataclass
class RetrievalTrace:
    seed_key: str
    method: str
    candidate_ids: list[str]
    candidate_count: int
    precision: float
    recall: float


@dataclass
class F8ProbeResult:
    case_id: str
    variant: str
    pass_gate: bool
    traces: list[RetrievalTrace]
    before_bridge_detected: bool
    cause_path_recovered_positive: bool
    negative_cause_absent: bool
    errors: list[str]


def evaluate_f8_probe(
    c_prediction: PredictionRecord,
    cache_dir: Path | str | None = None,
) -> F8ProbeResult:
    case_id = c_prediction.case_id
    variant = case_id.split("-")[1]

    blocks = c_prediction.blocks
    relations = c_prediction.relations

    # Find s1 and s4 blocks
    s1_blk = next((b for b in blocks if b.state_id.endswith("_s1") or b.state_id == "s1" or "A logged in" in b.canonical_content), None)
    s4_blk = next((b for b in blocks if b.state_id.endswith("_s4") or b.state_id == "s4" or "X fail" in b.canonical_content.lower()), None)

    if not s1_blk or not s4_blk:
        return F8ProbeResult(
            case_id=case_id,
            variant=variant,
            pass_gate=False,
            traces=[],
            before_bridge_detected=False,
            cause_path_recovered_positive=False,
            negative_cause_absent=False,
            errors=[f"B17 fixture missing s1 or s4 block in {case_id}"],
        )

    # Embed all block contents
    texts = [b.canonical_content for b in blocks]
    embeddings = embed_texts(texts, cache_dir=cache_dir)
    block_embs = {b.state_id: emb for b, emb in zip(blocks, embeddings)}

    errors: list[str] = []
    traces: list[RetrievalTrace] = []
    before_bridge_detected = False

    # Check relation traversal policy: BEFORE must have traversal_allowed=False
    for r in relations:
        if r.type == "BEFORE" and r.traversal_allowed:
            before_bridge_detected = True
            errors.append(f"BEFORE relation {r.source_state_id}->{r.target_state_id} has traversal_allowed=True!")

    # Target sets for seeds
    # In C/P: s4 cause chain targets are s4, s5, s6
    expected_s4_targets = {
        b.state_id for b in blocks
        if any(b.state_id.endswith(x) for x in ("_s4", "_s5", "_s6", "s4", "s5", "s6"))
        or any(k in b.canonical_content.lower() for k in ("fail", "stop", "stall"))
    }
    expected_s1_targets = {s1_blk.state_id}

    cause_path_recovered_pos = False
    negative_cause_absent = False

    for seed_name, seed_blk, expected_relevant in [("s1_login", s1_blk, expected_s1_targets), ("s4_incident", s4_blk, expected_s4_targets)]:
        seed_vec = block_embs[seed_blk.state_id]

        # 1. Vector-only (k=3)
        sims = [
            (b.state_id, _cosine_similarity(seed_vec, block_embs[b.state_id]))
            for b in blocks
        ]
        sims.sort(key=lambda x: -x[1])
        vec_candidates = [x[0] for x in sims[:3]]

        tp_vec = len(set(vec_candidates) & expected_relevant)
        p_vec = tp_vec / len(vec_candidates) if vec_candidates else 0.0
        r_vec = tp_vec / len(expected_relevant) if expected_relevant else 1.0

        traces.append(RetrievalTrace(
            seed_key=seed_name,
            method="vector_only",
            candidate_ids=vec_candidates,
            candidate_count=len(vec_candidates),
            precision=p_vec,
            recall=r_vec,
        ))

        # 2. Vector + Graph (2 relation hops along traversable edges)
        graph_candidates = list(vec_candidates)
        # Traverse from seed up to 2 hops
        traversable_adj: dict[str, list[str]] = {}
        for r in relations:
            if r.traversal_allowed:
                traversable_adj.setdefault(r.source_state_id, []).append(r.target_state_id)

        # 2 hops BFS
        curr_level = [seed_blk.state_id]
        visited = set(curr_level)
        for _ in range(2):
            next_level = []
            for node in curr_level:
                for neighbor in traversable_adj.get(node, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_level.append(neighbor)
                        if neighbor not in graph_candidates:
                            graph_candidates.append(neighbor)
            curr_level = next_level

        tp_graph = len(set(graph_candidates) & expected_relevant)
        p_graph = tp_graph / len(graph_candidates) if graph_candidates else 0.0
        r_graph = tp_graph / len(expected_relevant) if expected_relevant else 1.0

        traces.append(RetrievalTrace(
            seed_key=seed_name,
            method="vector_plus_graph",
            candidate_ids=graph_candidates,
            candidate_count=len(graph_candidates),
            precision=p_graph,
            recall=r_graph,
        ))

        if seed_name == "s4_incident":
            if variant in ("C", "P"):
                # Must recover all targets in expected_s4_targets
                all_targets_found = expected_s4_targets.issubset(set(graph_candidates))
                if all_targets_found:
                    cause_path_recovered_pos = True
                else:
                    errors.append(f"F8 positive causal path incomplete: missing {expected_s4_targets - set(graph_candidates)}")
            else:  # 'N'
                # Negative: no cause path should exist
                s5_s6_in_graph = [cid for cid in graph_candidates if cid in expected_s4_targets and cid not in vec_candidates and cid != seed_blk.state_id]
                if not s5_s6_in_graph:
                    negative_cause_absent = True
                else:
                    errors.append(f"F8 negative fixture expanded unwanted cause candidates: {s5_s6_in_graph}")

    if variant in ("C", "P"):
        pass_gate = cause_path_recovered_pos and not before_bridge_detected
    else:
        pass_gate = negative_cause_absent and not before_bridge_detected

    return F8ProbeResult(
        case_id=case_id,
        variant=variant,
        pass_gate=pass_gate,
        traces=traces,
        before_bridge_detected=before_bridge_detected,
        cause_path_recovered_positive=cause_path_recovered_pos,
        negative_cause_absent=negative_cause_absent,
        errors=errors,
    )
