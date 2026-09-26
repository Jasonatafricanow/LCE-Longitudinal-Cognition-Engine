"""LCE — Minimal Longitudinal Logical Understanding Core."""

from lce.cognition.external import PrecomputedDraftInput, PrecomputedDraftIntake
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
from lce.core.projection import LceProjectionCore, ProcessResult
from lce.read_api import AcceptedUnderstandingReadAPI, UnderstandingView
from lce.runtime import LceRuntime
from lce.store.interface import BaselineStorePort
from lce.store.sqlite_store import SqliteBaselineStore, StorageIntegrityError

__all__ = [
    "AcceptedUnderstandingReadAPI",
    "Baseline",
    "BaselineHistory",
    "BaselineStorePort",
    "CandidateBaseline",
    "ConsolidationResult",
    "EmptyNeighborhoodError",
    "LceCore",
    "LceError",
    "LceProjectionCore",
    "LceRuntime",
    "MemoryItemView",
    "MemorySubstratePort",
    "PrecomputedDraftInput",
    "PrecomputedDraftIntake",
    "ProcessResult",
    "SemanticConsolidatorPort",
    "SqliteBaselineStore",
    "StorageIntegrityError",
    "UnauthorizedSourceError",
    "UnderstandingView",
    "compute_content_hash",
    "normalize_content",
]
