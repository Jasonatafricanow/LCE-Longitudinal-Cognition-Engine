"""Evaluation metrics for GitHub Issue #12.

Records all 10 required dimensions:
1. known_event_recovery
2. bridge_carrier_identification
3. false_candidate_count
4. candidate_volume
5. temporal_specificity under shuffled-order control
6. robustness under perturbation / dropout
7. source_locality (exact block IDs supporting each structure)
8. redundancy with baseline
9. incremental_candidate_yield
10. runtime / memory cost
"""
from __future__ import annotations

import time
import tracemalloc
from dataclasses import asdict, dataclass, field
from typing import Any

from research.experiments.temporal_graph_representation.baseline import (
    BaselineCandidate,
    BaselineResult,
)
from research.experiments.temporal_graph_representation.fixtures import (
    FixtureOracle,
    SyntheticItem,
)
from research.experiments.temporal_graph_representation.graph import (
    GraphCandidate,
    TemporalGraphResult,
)


@dataclass
class RepresentationMetrics:
    representation_name: str
    known_event_recovery: bool
    bridge_carrier_identification: bool
    false_candidate_count: int
    candidate_volume: int
    temporal_specificity: float  # degradation under shuffle: 1.0 = perfect degradation (fully temporal), 0.0 = no degradation
    robustness_perturbation_dropout: float  # Jaccard overlap under perturbation & dropout vs clean
    source_locality: list[list[str]]  # block IDs supporting each structure
    redundancy_with_baseline: float  # Jaccard overlap with baseline
    incremental_candidate_yield: int  # valid candidates found that the other arm missed
    runtime_ms: float
    memory_kb: float
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_jaccard(set_a: set[str], set_b: set[str]) -> float:
    union = set_a | set_b
    if not union:
        return 1.0
    return len(set_a & set_b) / len(union)


def evaluate_representation_metrics(
    *,
    representation_name: str,
    clean_candidates: list[Any],
    clean_carriers: list[str],
    shuffled_candidates: list[Any],
    perturbed_candidates: list[Any],
    dropout_candidates: list[Any],
    oracle: FixtureOracle,
    baseline_candidates: list[Any] | None = None,
    elapsed_ms: float = 0.0,
    peak_memory_kb: float = 0.0,
) -> RepresentationMetrics:
    """Compute the 10 required metrics for a given representation on a fixture."""
    # 1. Known event recovery: does any candidate match the oracle target_event_type and overlap target_block_ids?
    target_set = set(oracle.target_block_ids)
    target_event = oracle.target_event_type

    recovery = False
    matching_candidate: Any = None
    for cand in clean_candidates:
        cand_type = getattr(cand, "candidate_type", "")
        cand_blocks = set(getattr(cand, "block_ids", []))
        if cand_type == target_event or (cand_blocks & target_set):
            # Check meaningful overlap
            if len(cand_blocks & target_set) >= min(1, len(target_set)):
                recovery = True
                matching_candidate = cand
                break

    # 2. Bridge / carrier identification: were the oracle carrier_block_ids recovered?
    carrier_set = set(oracle.carrier_block_ids)
    carrier_recovered = False
    if carrier_set:
        carrier_recovered = any(carrier in clean_carriers for carrier in carrier_set)
        if not carrier_recovered and matching_candidate:
            carrier_recovered = any(c in getattr(matching_candidate, "carrier_ids", []) for c in carrier_set)

    # 3. False candidate count and candidate volume
    candidate_volume = len(clean_candidates)
    false_count = 0
    for cand in clean_candidates:
        cand_blocks = set(getattr(cand, "block_ids", []))
        cand_type = getattr(cand, "candidate_type", "")
        # If candidate has no overlap with target or region labels, or is spurious
        is_grounded = bool(cand_blocks & target_set)
        for reg_name, reg_members in oracle.region_labels.items():
            if cand_blocks & set(reg_members):
                is_grounded = True
                break
        if not is_grounded:
            false_count += 1

    # 4. Temporal specificity under shuffled-order control:
    # If expected_temporal_dependence is True, does the target event recovery or score drop under shuffle?
    shuffled_recovered = False
    for cand in shuffled_candidates:
        cand_type = getattr(cand, "candidate_type", "")
        cand_blocks = set(getattr(cand, "block_ids", []))
        if (cand_type == target_event or (cand_blocks & target_set)) and (cand_blocks & target_set):
            shuffled_recovered = True
            break

    if oracle.expected_temporal_dependence:
        # If it was recovered in clean, but lost or degraded in shuffled -> high specificity
        if recovery and not shuffled_recovered:
            temporal_specificity = 1.0
        elif recovery and shuffled_recovered:
            temporal_specificity = 0.0  # Failed temporal specificity: order shuffle didn't break it
        else:
            temporal_specificity = 0.0
    else:
        # Not temporally dependent (e.g. TG-04)
        temporal_specificity = 1.0 if recovery and shuffled_recovered else 0.5

    # 5. Robustness under perturbation / dropout:
    # Measure stability of candidate block sets
    clean_blocks_flat = set().union(*[set(getattr(c, "block_ids", [])) for c in clean_candidates]) if clean_candidates else set()
    pert_blocks_flat = set().union(*[set(getattr(c, "block_ids", [])) for c in perturbed_candidates]) if perturbed_candidates else set()
    drop_blocks_flat = set().union(*[set(getattr(c, "block_ids", [])) for c in dropout_candidates]) if dropout_candidates else set()

    jaccard_pert = compute_jaccard(clean_blocks_flat, pert_blocks_flat)
    jaccard_drop = compute_jaccard(clean_blocks_flat, drop_blocks_flat)
    robustness = round((jaccard_pert + jaccard_drop) / 2.0, 4)

    # 6. Source locality: exact block IDs supporting each structure
    source_locality = [sorted(getattr(c, "block_ids", [])) for c in clean_candidates]

    # 7. Redundancy with baseline:
    if baseline_candidates is not None:
        base_blocks_flat = set().union(*[set(getattr(c, "block_ids", [])) for c in baseline_candidates]) if baseline_candidates else set()
        redundancy = round(compute_jaccard(clean_blocks_flat, base_blocks_flat), 4)
    else:
        redundancy = 1.0  # Baseline with itself

    # 8. Incremental candidate yield:
    # Target recovered by this representation that baseline did not recover
    incremental_yield = 0
    if baseline_candidates is not None:
        base_recovered = False
        for c in baseline_candidates:
            c_blocks = set(getattr(c, "block_ids", []))
            c_type = getattr(c, "candidate_type", "")
            if (c_type == target_event or (c_blocks & target_set)) and (c_blocks & target_set):
                base_recovered = True
                break
        if recovery and not base_recovered:
            incremental_yield = 1
        elif not recovery and base_recovered:
            incremental_yield = -1

    return RepresentationMetrics(
        representation_name=representation_name,
        known_event_recovery=recovery,
        bridge_carrier_identification=carrier_recovered,
        false_candidate_count=false_count,
        candidate_volume=candidate_volume,
        temporal_specificity=temporal_specificity,
        robustness_perturbation_dropout=robustness,
        source_locality=source_locality,
        redundancy_with_baseline=redundancy,
        incremental_candidate_yield=incremental_yield,
        runtime_ms=round(elapsed_ms, 3),
        memory_kb=round(peak_memory_kb, 3),
        details={"oracle_target": target_event, "oracle_carriers": list(oracle.carrier_block_ids)},
    )
