"""MR-Mem canonical SemanticBlock → LCE projection; no semantic compilation."""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from lce.core.projection import LceProjectionCore
from lce.reference_memory.composite import ProjectionSubstrate
from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.reference_memory.projection_state import SqliteProjectionStateStore

LINEAGE = "mr-mem-canonical-semantic-block"


class MRMemReader(Protocol):
    """Existing canonical read surface; no admission or mutation capability."""

    read_only: bool

    def get(self, memory_id: str) -> Any: ...
    def load_all(self) -> tuple[Any, ...]: ...
    def get_semantic_metadata(self, memory_id: str) -> Any: ...
    def semantic_relations(self, memory_id: str) -> tuple[tuple[str, ...], ...]: ...
    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class CanonicalSemanticBlockView:
    """Thin projection view of existing MR-Mem authority, not a new cognition."""

    memory_id: str
    content: str
    occurred_start: datetime
    occurred_end: datetime
    known_at: datetime
    source_refs: tuple[Mapping[str, str | None], ...]
    context_memory_ids: tuple[str, ...]
    relations: tuple[tuple[str, ...], ...]
    compiler_version: str
    lifecycle: str


class MRMemSemanticBlockAdapter:
    canonical_semantic_blocks = True

    def __init__(self, reader: MRMemReader, *, scope: object) -> None:
        if not reader.read_only:
            raise ValueError("LCE requires a read-only MR-Mem canonical reader")
        self.reader, self.scope = reader, scope

    def view(self, memory_id: str) -> CanonicalSemanticBlockView:
        memory = self.reader.get(memory_id)
        metadata = self.reader.get_semantic_metadata(memory_id)
        if memory is None or memory.scope != self.scope:
            raise KeyError(memory_id)
        if metadata is None or metadata.memory_id != memory_id:
            raise ValueError(
                "only MR-Mem canonical SemanticBlocks may enter integrated LCE"
            )
        refs = memory.provenance.source_refs
        if not refs or refs != metadata.source_refs:
            raise ValueError("canonical source-ref metadata mismatch")
        payloads = tuple(
            {
                "source_namespace": ref.source_namespace,
                "session_id": ref.session_id,
                "record_id": ref.record_id,
                "occurred_at": ref.occurred_at.isoformat(),
                "revision": ref.revision,
                "fingerprint": ref.fingerprint,
            }
            for ref in refs
        )
        return CanonicalSemanticBlockView(
            memory_id,
            memory.content,
            min(ref.occurred_at for ref in refs),
            max(ref.occurred_at for ref in refs),
            memory.known_at,
            payloads,
            metadata.context_memory_ids,
            self.reader.semantic_relations(memory_id),
            metadata.compiler_version,
            memory.lifecycle.value,
        )

    def get_semantic_block(self, memory_id: str) -> SemanticBlock:
        view = self.view(memory_id)
        return SemanticBlock(
            block_id=view.memory_id,
            content=view.content,
            raw_evidence_ids=(view.memory_id,),
            occurred_start=view.occurred_start,
            occurred_end=view.occurred_end,
            compiler_version=view.compiler_version,
            lineage_id=LINEAGE,
            metadata={
                "canonical_authority": "MR-Mem",
                "source_refs": view.source_refs,
                "context_memory_ids": view.context_memory_ids,
                "relations": view.relations,
            },
            derived_known_at=view.known_at,
        )

    def get_evidence(self, evidence_id: str) -> RawEvidence:
        """Compatibility validity token, read from the Block; never native Raw input.

        Existing downstream algorithms use this surface for validity/ordering.
        Nothing is written to a Raw store or sent to a semantic compiler.
        """
        view = self.view(evidence_id)
        state = {"active": "VALID", "superseded": "SUPERSEDED"}.get(
            view.lifecycle, "INVALID"
        )
        return RawEvidence(
            evidence_id=view.memory_id,
            content=view.content,
            occurred_at=view.occurred_start,
            known_at=view.known_at,
            state=state,
            ordering_key=view.known_at.isoformat() + ":" + view.memory_id,
            provenance={"canonical_authority": "MR-Mem", "memory_id": view.memory_id},
        )

    def list_current_valid_evidence(self) -> tuple[RawEvidence, ...]:
        return tuple(
            self.get_evidence(item.memory_id)
            for item in self.reader.load_all()
            if item.scope == self.scope
            and item.lifecycle.value == "active"
            and self.reader.get_semantic_metadata(item.memory_id) is not None
        )

    def close(self) -> None:
        self.reader.close()


def open_mr_mem_projection(
    canonical_db: Path | str,
    projection_root: Path | str,
    *,
    scope: object,
) -> LceProjectionCore:
    """Open integrated LCE with read-only MR-Mem and separate derived storage."""
    reader = importlib.import_module("mr_mem.memory.core").MemoryCore(
        canonical_db, read_only=True
    )
    source = MRMemSemanticBlockAdapter(reader, scope=scope)
    substrate = ProjectionSubstrate(
        source,
        SqliteProjectionStateStore(Path(projection_root) / "projection_state"),
        close_source=True,
        close_state=True,
    )
    try:
        return LceProjectionCore(
            projection_root,
            memory=substrate,
            lineage_id=LINEAGE,
            canonical_blocks=True,
            close_memory=True,
        )
    except BaseException:
        substrate.close()
        raise
