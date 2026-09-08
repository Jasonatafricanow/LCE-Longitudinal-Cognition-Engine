"""Baseline storage port definition."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lce.contracts.baseline import Baseline, BaselineHistory


@runtime_checkable
class BaselineStorePort(Protocol):
    """Persistence port for LCE baseline states and audit histories."""

    def get_head(self, region_id: str) -> Baseline | None:
        """Fetch the current HEAD baseline for a given region."""
        ...

    def save_revision(self, baseline: Baseline) -> None:
        """Atomically persist a new baseline revision and advance the HEAD pointer."""
        ...

    def get_history(self, region_id: str, limit: int | None = None) -> BaselineHistory:
        """Fetch the revision history for a given region, ordered by revision descending."""
        ...

    def close(self) -> None:
        """Close the storage connection and release underlying resources."""
        ...

    def list_regions(self) -> tuple[str, ...]:
        """List persisted Baseline lineages for dependency-aware readers."""
        ...
