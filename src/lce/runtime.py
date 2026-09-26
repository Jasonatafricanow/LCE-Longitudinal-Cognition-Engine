"""Standalone LCE composition wrapper.

The cognition pipeline lives in :mod:`lce.core.projection`. This module keeps
the convenience runtime that composes the bundled ReferenceMemoryStore for
standalone demos and research runs.
"""

from __future__ import annotations

from pathlib import Path

from lce.cognition.promotion import BoundedInterpreter, PromotionPolicy
from lce.core.projection import (
    LceProjectionCore,
    ProcessResult,
    deterministic_block_embedding,
)
from lce.reference_memory.contracts import ReferenceMemorySubstratePort
from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.semantic.contracts import SemanticDecisionProvider
from lce.structure.contracts import StructureConfig


class LceRuntime(LceProjectionCore):
    """Convenience standalone composition over the bundled SQLite substrate."""

    def __init__(
        self,
        root: Path | str,
        *,
        provider: SemanticDecisionProvider | None = None,
        policy: PromotionPolicy | None = None,
        lineage_id: str = "default",
        structure_config: StructureConfig | None = None,
        memory: ReferenceMemorySubstratePort | None = None,
        interpreter: BoundedInterpreter | None = None,
    ) -> None:
        root_path = Path(root)
        substrate = (
            memory
            if memory is not None
            else ReferenceMemoryStore(root_path / "memory")
        )
        super().__init__(
            root_path,
            provider=provider,
            policy=policy,
            lineage_id=lineage_id,
            structure_config=structure_config,
            memory=substrate,
            interpreter=interpreter,
            close_memory=True,
        )


__all__ = [
    "LceRuntime",
    "ProcessResult",
    "deterministic_block_embedding",
]
