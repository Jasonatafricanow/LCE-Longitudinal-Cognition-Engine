"""Lightweight snapshot-based multi-structure discovery."""

from lce.structure.contracts import (
    HigherOrderCandidate,
    StructureConfig,
    StructureDiff,
    StructureObservation,
    StructureRelationCandidate,
    StructureSnapshot,
)
from lce.structure.discovery import SnapshotStructureDiscovery
from lce.structure.frontier import (
    FrontierCandidateDiscovery,
    FrontierDiscoveryConfig,
)
from lce.structure.surface import (
    LinePathView,
    SurfaceCandidate,
    SurfaceDiscoveryResult,
    SurfaceSkippedLine,
    SurfaceConfig,
    SurfaceRuntime,
    SurfaceSearchLimitExceeded,
)
from lce.structure.trajectory import (
    ExactCosineNeighbourProvider,
    MutualKnnTrajectorySupplier,
    NeighbourCandidateProvider,
    TrajectoryConfig,
    TrajectoryPath,
    TrajectoryRuntime,
    TrajectoryRuntimeResult,
)

__all__ = [
    "ExactCosineNeighbourProvider",
    "FrontierCandidateDiscovery",
    "FrontierDiscoveryConfig",
    "HigherOrderCandidate",
    "LinePathView",
    "MutualKnnTrajectorySupplier",
    "NeighbourCandidateProvider",
    "SnapshotStructureDiscovery",
    "StructureConfig",
    "StructureDiff",
    "StructureObservation",
    "StructureRelationCandidate",
    "StructureSnapshot",
    "SurfaceCandidate",
    "SurfaceDiscoveryResult",
    "SurfaceSkippedLine",
    "SurfaceConfig",
    "SurfaceRuntime",
    "SurfaceSearchLimitExceeded",
    "TrajectoryConfig",
    "TrajectoryPath",
    "TrajectoryRuntime",
    "TrajectoryRuntimeResult",
]
