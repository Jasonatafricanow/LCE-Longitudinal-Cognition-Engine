"""Synthetic fixtures for GitHub Issue #12: Temporal Semantic Graph Representation.

Implements all five required fixtures:
- TG-01: Delayed bridge
- TG-02: Distant recurrence
- TG-03: Contradiction-shaped geometry without semantic labels
- TG-04: Multi-membership bridge
- TG-05: Density trap
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np

BASE_TIME = datetime(2026, 4, 1, 10, 0, 0, tzinfo=UTC)


@dataclass
class SyntheticItem:
    """A cutoff-visible Semantic Block representation."""
    item_id: str
    occurred_at: datetime
    cutoff: str
    vector: np.ndarray
    region: str
    context_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.item_id,
            "occurred_at": self.occurred_at.isoformat(),
            "cutoff": self.cutoff,
            "vector": self.vector.tolist(),
            "region": self.region,
            "context_key": self.context_key,
        }


@dataclass
class FixtureOracle:
    """Ground-truth structural expectation for a fixture."""
    fixture_id: str
    fixture_name: str
    target_event_type: str
    target_block_ids: tuple[str, ...]
    carrier_block_ids: tuple[str, ...]
    region_labels: dict[str, tuple[str, ...]]
    cutoffs: tuple[str, ...]
    expected_temporal_dependence: bool
    notes: str = ""


@dataclass
class FixtureData:
    fixture_id: str
    items: list[SyntheticItem]
    cutoffs: list[str]
    oracle: FixtureOracle


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm == 0:
        raise ValueError("Cannot normalize zero vector")
    return vec / norm


def sample_near(u: np.ndarray, target_cos: float, rng: np.random.Generator) -> np.ndarray:
    """Sample a unit vector having approximately target_cos similarity to u."""
    d = len(u)
    raw = rng.standard_normal(d)
    proj = np.dot(raw, u) * u
    ortho = raw - proj
    ortho_norm = np.linalg.norm(ortho)
    if ortho_norm < 1e-12:
        return u.copy()
    ortho_unit = ortho / ortho_norm
    sin_val = math.sqrt(max(0.0, 1.0 - target_cos**2))
    return _normalize(target_cos * u + sin_val * ortho_unit)


# ==============================================================================
# TG-01: Delayed Bridge
# ==============================================================================

def generate_tg01_delayed_bridge(dim: int = 128, seed: int = 42) -> FixtureData:
    """TG-01 Delayed bridge fixture.

    Before X (at T0):
      Region A: A1, A2, A3 (high intra-sim ~0.88)
      Region B: B1, B2, B3 (high intra-sim ~0.88)
      Inter-region sim(A, B) ~ 0.0 (clearly separated)

    At T1:
      X arrives. X has mediocre direct similarity to A3 (~0.715) and B1 (~0.715),
      which is below intra-cluster density (0.88), but forms the sole bridge.
    """
    rng = np.random.default_rng(seed)

    # Base directions
    u_a = _normalize(rng.standard_normal(dim))
    u_b = rng.standard_normal(dim)
    u_b = _normalize(u_b - np.dot(u_b, u_a) * u_a)  # Orthogonal to A

    # Cluster A around u_a
    items: list[SyntheticItem] = []
    a_ids = ["A1", "A2", "A3"]
    t0 = BASE_TIME
    a_vecs = [sample_near(u_a, 0.94, rng) for _ in range(3)]
    for idx, item_id in enumerate(a_ids):
        items.append(SyntheticItem(item_id, t0 + timedelta(hours=idx), "T0", a_vecs[idx], "REGION_A"))

    # Cluster B around u_b
    b_ids = ["B1", "B2", "B3"]
    b_vecs = [sample_near(u_b, 0.94, rng) for _ in range(3)]
    for idx, item_id in enumerate(b_ids):
        items.append(SyntheticItem(item_id, t0 + timedelta(hours=3 + idx), "T0", b_vecs[idx], "REGION_B"))

    # Bridge node X at T1: midpoint between A3 and B1 with direct cosine ~ 0.715 to each
    u_x = _normalize(a_vecs[2] + b_vecs[0])
    t1 = t0 + timedelta(days=1)
    items.append(SyntheticItem("X_bridge", t1, "T1", u_x, "BRIDGE"))

    oracle = FixtureOracle(
        fixture_id="TG-01",
        fixture_name="Delayed bridge",
        target_event_type="reconnection_bridge",
        target_block_ids=("X_bridge",),
        carrier_block_ids=("X_bridge",),
        region_labels={"REGION_A": tuple(a_ids), "REGION_B": tuple(b_ids)},
        cutoffs=("T0", "T1"),
        expected_temporal_dependence=True,
        notes="X_bridge connects A3 and B1 at T1 with direct similarity ~0.715, below cluster density 0.88.",
    )

    return FixtureData(fixture_id="TG-01", items=items, cutoffs=["T0", "T1"], oracle=oracle)


# ==============================================================================
# TG-02: Distant Recurrence
# ==============================================================================

def generate_tg02_distant_recurrence(dim: int = 128, seed: int = 43) -> FixtureData:
    """TG-02 Distant recurrence fixture.

    Episode 1 (T1): A1, A2, A3 (Topic A, sim ~0.88)
    Intervening noise (T2): D1, D2, D3 (Unrelated Topic D, orthogonal to A)
    Episode 2 (T3): A4, A5, A6 (Topic A recurs, highly similar to A1..A3 ~0.85)

    Question: Does the graph representation recover a recurrent longitudinal region
    without forcing all temporally adjacent noise into it?
    """
    rng = np.random.default_rng(seed)

    u_a = _normalize(rng.standard_normal(dim))
    u_d = rng.standard_normal(dim)
    u_d = _normalize(u_d - np.dot(u_d, u_a) * u_a)

    items: list[SyntheticItem] = []
    t_start = BASE_TIME

    # Early A (T1)
    a_early_ids = ["A1", "A2", "A3"]
    for idx, item_id in enumerate(a_early_ids):
        vec = sample_near(u_a, 0.94, rng)
        items.append(SyntheticItem(item_id, t_start + timedelta(days=idx), "T1", vec, "TOPIC_A"))

    # Noise D (T2)
    noise_ids = ["D1", "D2", "D3"]
    for idx, item_id in enumerate(noise_ids):
        vec = sample_near(u_d, 0.94, rng)
        items.append(SyntheticItem(item_id, t_start + timedelta(days=5 + idx), "T2", vec, "NOISE_D"))

    # Late A recurrence (T3)
    a_late_ids = ["A4", "A5", "A6"]
    for idx, item_id in enumerate(a_late_ids):
        vec = sample_near(u_a, 0.94, rng)
        items.append(SyntheticItem(item_id, t_start + timedelta(days=12 + idx), "T3", vec, "TOPIC_A"))

    oracle = FixtureOracle(
        fixture_id="TG-02",
        fixture_name="Distant recurrence",
        target_event_type="distant_recurrence",
        target_block_ids=tuple(a_early_ids + a_late_ids),
        carrier_block_ids=tuple(a_late_ids),
        region_labels={"TOPIC_A": tuple(a_early_ids + a_late_ids), "NOISE_D": tuple(noise_ids)},
        cutoffs=("T1", "T2", "T3"),
        expected_temporal_dependence=True,
        notes="TOPIC_A recurs at T3 after gap filled with NOISE_D.",
    )

    return FixtureData(fixture_id="TG-02", items=items, cutoffs=["T1", "T2", "T3"], oracle=oracle)


# ==============================================================================
# TG-03: Contradiction-Shaped Geometry Without Semantic Labels
# ==============================================================================

def generate_tg03_contradiction_geometry(dim: int = 128, seed: int = 44) -> FixtureData:
    """TG-03 Contradiction-shaped geometry without semantic labels.

    Region R1 (T1): Stance 1 points R1_1, R1_2, R1_3
    Region R2 (T2): Stance 2 points R2_1, R2_2, R2_3 (moderate overlap with R1 ~0.72)
    Point X (T3): geometrically closer to R2 (~0.88) and distant from R1 (~0.60).
    """
    rng = np.random.default_rng(seed)

    # Base direction for R1
    u_r1 = _normalize(rng.standard_normal(dim))
    # Base direction for R2 with controlled cosine ~ 0.72 to R1
    ortho = rng.standard_normal(dim)
    ortho = _normalize(ortho - np.dot(ortho, u_r1) * u_r1)
    cos_target = 0.72
    u_r2 = _normalize(cos_target * u_r1 + math.sqrt(1.0 - cos_target**2) * ortho)

    items: list[SyntheticItem] = []
    t_start = BASE_TIME

    # R1 items (T1)
    r1_ids = ["R1_1", "R1_2", "R1_3"]
    for idx, item_id in enumerate(r1_ids):
        vec = sample_near(u_r1, 0.94, rng)
        items.append(SyntheticItem(item_id, t_start + timedelta(days=idx), "T1", vec, "STANCE_1"))

    # R2 items (T2)
    r2_ids = ["R2_1", "R2_2", "R2_3"]
    for idx, item_id in enumerate(r2_ids):
        vec = sample_near(u_r2, 0.94, rng)
        items.append(SyntheticItem(item_id, t_start + timedelta(days=4 + idx), "T2", vec, "STANCE_2"))

    # X arrives at T3: strongly aligned with R2, divergent from R1
    u_x = sample_near(u_r2, 0.96, rng)
    items.append(SyntheticItem("X_revision", t_start + timedelta(days=10), "T3", u_x, "REVISION_CANDIDATE"))

    oracle = FixtureOracle(
        fixture_id="TG-03",
        fixture_name="Contradiction-shaped geometry without semantic labels",
        target_event_type="structural_revision",
        target_block_ids=("X_revision",),
        carrier_block_ids=("X_revision",),
        region_labels={"STANCE_1": tuple(r1_ids), "STANCE_2": tuple(r2_ids)},
        cutoffs=("T1", "T2", "T3"),
        expected_temporal_dependence=True,
        notes="X_revision is closer to newer stance R2 than older stance R1.",
    )

    return FixtureData(fixture_id="TG-03", items=items, cutoffs=["T1", "T2", "T3"], oracle=oracle)


# ==============================================================================
# TG-04: Multi-Membership Bridge
# ==============================================================================

def generate_tg04_multi_membership(dim: int = 128, seed: int = 45) -> FixtureData:
    """TG-04 Multi-membership bridge fixture.

    Structure A: A1, A2, A3, A4 (Cluster A)
    Structure B: B1, B2, B3, B4 (Cluster B)
    Node M: participates in both A and B (similarity ~0.74 to both).
    """
    rng = np.random.default_rng(seed)

    u_a = _normalize(rng.standard_normal(dim))
    u_b_ortho = rng.standard_normal(dim)
    u_b_ortho = _normalize(u_b_ortho - np.dot(u_b_ortho, u_a) * u_a)

    # cos(u_a, u_b) = 0.30 (distant clusters)
    u_b = _normalize(0.30 * u_a + math.sqrt(1.0 - 0.30**2) * u_b_ortho)

    # Multi-member direction: midpoint between u_a and u_b
    u_m = _normalize(u_a + u_b)

    items: list[SyntheticItem] = []
    t0 = BASE_TIME

    a_ids = [f"A{i}" for i in range(1, 5)]
    for idx, item_id in enumerate(a_ids):
        vec = sample_near(u_a, 0.94, rng)
        items.append(SyntheticItem(item_id, t0 + timedelta(hours=idx), "T0", vec, "CLUSTER_A"))

    b_ids = [f"B{i}" for i in range(1, 5)]
    for idx, item_id in enumerate(b_ids):
        vec = sample_near(u_b, 0.94, rng)
        items.append(SyntheticItem(item_id, t0 + timedelta(hours=4 + idx), "T0", vec, "CLUSTER_B"))

    # Multi-member M: aligned with u_m (has ~0.74 similarity to both A and B)
    vec_m = sample_near(u_m, 0.98, rng)
    items.append(SyntheticItem("M_multi", t0 + timedelta(hours=9), "T0", vec_m, "MULTI_MEMBER"))

    oracle = FixtureOracle(
        fixture_id="TG-04",
        fixture_name="Multi-membership bridge",
        target_event_type="multi_membership",
        target_block_ids=("M_multi",),
        carrier_block_ids=("M_multi",),
        region_labels={"CLUSTER_A": tuple(a_ids), "CLUSTER_B": tuple(b_ids)},
        cutoffs=("T0",),
        expected_temporal_dependence=False,
        notes="M_multi belongs to both CLUSTER_A and CLUSTER_B non-exclusively.",
    )

    return FixtureData(fixture_id="TG-04", items=items, cutoffs=["T0"], oracle=oracle)


# ==============================================================================
# TG-05: Density Trap
# ==============================================================================

def generate_tg05_density_trap(dim: int = 128, seed: int = 46) -> FixtureData:
    """TG-05 Density trap fixture.

    Dense irrelevant cluster D: 15 nodes, tight cosine (~0.90), but timestamps
    are scrambled / all at once with no temporal progression.
    Sparse temporally coherent chain C: 5 nodes C1 -> C2 -> C3 -> C4 -> C5,
    moderate cosine (~0.76), strictly ordered across time.
    """
    rng = np.random.default_rng(seed)

    u_d = _normalize(rng.standard_normal(dim))
    u_c_base = rng.standard_normal(dim)
    u_c_base = _normalize(u_c_base - np.dot(u_c_base, u_d) * u_d)

    items: list[SyntheticItem] = []
    t_start = BASE_TIME

    # Dense cluster D: 15 nodes, high density, tight cosine ~0.90
    d_ids = [f"D{i:02d}" for i in range(1, 16)]
    t_offsets = rng.uniform(0, 48, size=15)
    for idx, item_id in enumerate(d_ids):
        vec = sample_near(u_d, 0.95, rng)
        occurred_at = t_start + timedelta(hours=float(t_offsets[idx]))
        items.append(SyntheticItem(item_id, occurred_at, "T0", vec, "DENSE_CLUSTER"))

    # Sparse temporally coherent chain C: 5 nodes, strictly ordered along time
    progression_axis = rng.standard_normal(dim)
    progression_axis = _normalize(progression_axis - np.dot(progression_axis, u_d) * u_d - np.dot(progression_axis, u_c_base) * u_c_base)

    c_ids = [f"C{i}" for i in range(1, 6)]
    for idx, item_id in enumerate(c_ids):
        step = (idx / 4.0) * 0.40
        vec = sample_near(_normalize(u_c_base + step * progression_axis), 0.97, rng)
        occurred_at = t_start + timedelta(days=idx * 2)
        items.append(SyntheticItem(item_id, occurred_at, "T0", vec, "TEMPORAL_CHAIN"))

    oracle = FixtureOracle(
        fixture_id="TG-05",
        fixture_name="Density trap",
        target_event_type="temporal_coherent_chain",
        target_block_ids=tuple(c_ids),
        carrier_block_ids=tuple(c_ids),
        region_labels={"DENSE_CLUSTER": tuple(d_ids), "TEMPORAL_CHAIN": tuple(c_ids)},
        cutoffs=("T0",),
        expected_temporal_dependence=True,
        notes="TEMPORAL_CHAIN is sparse but temporally coherent; DENSE_CLUSTER is dense but temporally static.",
    )

    return FixtureData(fixture_id="TG-05", items=items, cutoffs=["T0"], oracle=oracle)


def load_all_fixtures() -> dict[str, FixtureData]:
    """Load and return all 5 required fixtures."""
    return {
        "TG-01": generate_tg01_delayed_bridge(),
        "TG-02": generate_tg02_distant_recurrence(),
        "TG-03": generate_tg03_contradiction_geometry(),
        "TG-04": generate_tg04_multi_membership(),
        "TG-05": generate_tg05_density_trap(),
    }
