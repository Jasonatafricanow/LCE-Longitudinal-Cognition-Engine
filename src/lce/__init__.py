"""LCE — Minimal Longitudinal Logical Understanding Core."""

from lce.contracts.baseline import (
    Baseline,
    BaselineHistory,
    compute_content_hash,
    normalize_content,
)
from lce.contracts.consolidation import (
    CandidateBaseline,
    ConsolidationResult,
    EmptyNeighborhoodError,
    LceError,
    SemanticConsolidatorPort,
    UnauthorizedSourceError,
)
from lce.contracts.external_memory import (
    MemoryItemView,
    MemorySubstratePort,
)
from lce.core.engine import LceCore
from lce.store.interface import BaselineStorePort
from lce.store.sqlite_store import SqliteBaselineStore, StorageIntegrityError

__all__ = [
    "Baseline",
    "BaselineHistory",
    "BaselineStorePort",
    "CandidateBaseline",
    "ConsolidationResult",
    "EmptyNeighborhoodError",
    "LceCore",
    "LceError",
    "MemoryItemView",
    "MemorySubstratePort",
    "SemanticConsolidatorPort",
    "SqliteBaselineStore",
    "StorageIntegrityError",
    "UnauthorizedSourceError",
    "compute_content_hash",
    "normalize_content",
]
