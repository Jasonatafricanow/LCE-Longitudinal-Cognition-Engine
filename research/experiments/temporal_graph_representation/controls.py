"""Experimental controls and ablations for GitHub Issue #12.

Implements:
1. Temporal shuffle control (preserves vectors/cardinality, shuffles temporal placement)
2. Vector perturbation control (Gaussian jitter + renormalization)
3. Block dropout control (low-rate node deletion)
4. Edge ablations (semantic only, temporal only, semantic + temporal)
"""
from __future__ import annotations

import copy
import random
from typing import Literal

import numpy as np

from research.experiments.temporal_graph_representation.fixtures import (
    SyntheticItem,
    _normalize,
)

AblationMode = Literal["semantic_only", "temporal_only", "semantic_and_temporal"]


def temporal_shuffle_control(items: list[SyntheticItem], *, seed: int = 42) -> list[SyntheticItem]:
    """Permute timestamps/chronological order among items while keeping vectors and IDs fixed."""
    if len(items) <= 1:
        return [copy.deepcopy(it) for it in items]

    rng = random.Random(seed)
    shuffled = [copy.deepcopy(it) for it in items]
    timestamps = [it.occurred_at for it in shuffled]
    rng.shuffle(timestamps)

    for it, ts in zip(shuffled, timestamps):
        it.occurred_at = ts

    # Return items sorted by new occurred_at to reflect the shuffled arrival stream
    return sorted(shuffled, key=lambda it: (it.occurred_at, it.item_id))


def vector_perturbation_control(
    items: list[SyntheticItem], *, sigma: float = 0.03, seed: int = 42
) -> list[SyntheticItem]:
    """Apply bounded Gaussian perturbation to vectors and re-normalize."""
    rng = np.random.default_rng(seed)
    perturbed: list[SyntheticItem] = []

    for it in items:
        noise = rng.normal(0.0, sigma, size=it.vector.shape)
        new_vec = _normalize(it.vector + noise)
        perturbed.append(
            SyntheticItem(
                item_id=it.item_id,
                occurred_at=it.occurred_at,
                cutoff=it.cutoff,
                vector=new_vec,
                region=it.region,
                context_key=it.context_key,
            )
        )

    return perturbed


def block_dropout_control(
    items: list[SyntheticItem], *, dropout_rate: float = 0.15, seed: int = 42
) -> list[SyntheticItem]:
    """Randomly drop a fraction of non-target/random blocks to test structural robustness."""
    if len(items) <= 2:
        return [copy.deepcopy(it) for it in items]

    rng = random.Random(seed)
    retained: list[SyntheticItem] = []

    for it in items:
        if rng.random() >= dropout_rate:
            retained.append(copy.deepcopy(it))

    # Guard: never drop all items
    if not retained:
        retained = [copy.deepcopy(items[0])]

    return retained


def get_ablation_flags(ablation: AblationMode) -> tuple[bool, bool]:
    """Return (include_semantic, include_temporal) flags for a given ablation mode."""
    if ablation == "semantic_only":
        return True, False
    elif ablation == "temporal_only":
        return False, True
    elif ablation == "semantic_and_temporal":
        return True, True
    else:
        raise ValueError(f"Unknown ablation mode: {ablation}")
