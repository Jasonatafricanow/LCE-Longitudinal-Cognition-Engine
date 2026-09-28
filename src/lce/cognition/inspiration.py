"""Derived inspiration discovery with a deliberately narrow public seam.

LCE may use rich internal structure to produce proactive conversation material,
but downstream consumers receive only InspirationMaterial(material_id, content).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from lce.cognition.line_graph import LineGraphStore, LineGraphView
from lce.contracts.inspiration import InspirationMaterial
from lce.reference_memory.contracts import (
    ReferenceMemorySubstratePort,
    SemanticBlock,
)
from lce.structure.trajectory import TrajectoryRuntimeResult


def _require_utc(value: datetime, name: str) -> None:
    if value.tzinfo != UTC:
        raise ValueError(f"{name} must be an aware UTC datetime")


def _nonempty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty")
    return value.strip()


def _evidence_valid_at(
    memory: ReferenceMemorySubstratePort,
    evidence_id: str,
    cutoff: datetime,
) -> bool:
    reader = getattr(memory, "evidence_valid_at", None)
    if callable(reader):
        return bool(reader(evidence_id, cutoff))
    item = memory.get_evidence(evidence_id)
    return item.effective_known_at <= cutoff and item.current_valid


class InspirationKind(StrEnum):
    """Internal discovery kinds. Not part of the downstream public contract."""

    ASSOCIATION = "association"
    EXTENSION = "extension"


@dataclass(frozen=True, slots=True)
class InspirationConfig:
    max_association_materials: int = 8
    max_extension_materials: int = 8
    max_extension_path_nodes: int = 6
    max_fragment_chars: int = 512

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class InspirationPackage:
    """Bounded internal package visible to an inspiration interpreter."""

    kind: InspirationKind
    candidate_id: str
    content_fragments: tuple[str, ...]
    block_ids: tuple[str, ...]
    state_ids: tuple[str, ...]
    raw_evidence_ids: tuple[str, ...]
    knowledge_cutoff: datetime
    line_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, InspirationKind):
            raise TypeError("kind must be InspirationKind")
        _nonempty(self.candidate_id, "candidate_id")
        if not self.content_fragments:
            raise ValueError("content_fragments must be nonempty")
        if len(self.block_ids) != len(self.state_ids):
            raise ValueError("block_ids and state_ids must align")
        if len(set(self.block_ids)) != len(self.block_ids):
            raise ValueError("block_ids must be unique")
        if len(set(self.state_ids)) != len(self.state_ids):
            raise ValueError("state_ids must be unique")
        if len(set(self.raw_evidence_ids)) != len(self.raw_evidence_ids):
            raise ValueError("raw_evidence_ids must be unique")
        _require_utc(self.knowledge_cutoff, "knowledge_cutoff")
        if self.line_id is not None:
            _nonempty(self.line_id, "line_id")


@dataclass(frozen=True, slots=True)
class InspirationInterpretation:
    """Interpreter output before LCE applies epistemic framing."""

    hypothesis: str | None
    status: str = "PROPOSED"
    model_trace: dict[str, object] | None = None

    def __post_init__(self) -> None:
        if self.status not in {"PROPOSED", "UNKNOWN", "REJECTED"}:
            raise ValueError(
                "inspiration interpretation status must be "
                "PROPOSED, UNKNOWN, or REJECTED"
            )
        if self.status == "PROPOSED":
            if self.hypothesis is None or not self.hypothesis.strip():
                raise ValueError("a proposed inspiration requires a hypothesis")
        elif self.hypothesis is not None and self.hypothesis.strip():
            raise ValueError(
                "UNKNOWN/REJECTED inspiration must not carry a hypothesis"
            )


@runtime_checkable
class InspirationInterpreter(Protocol):
    def interpret(
        self,
        package: InspirationPackage,
    ) -> InspirationInterpretation:
        """Generate only the speculative relation/extension for this package."""
        ...


class RuleBasedInspirationInterpreter:
    """Safe reference interpreter.

    Association material can be produced deterministically from discovered
    structure. A specific A->B->C->D extension needs semantic generation, so
    reference mode deliberately returns UNKNOWN for EXTENSION instead of
    inventing D.
    """

    derivation_id = "rule-based-inspiration-v1"

    def interpret(
        self,
        package: InspirationPackage,
    ) -> InspirationInterpretation:
        if package.kind is InspirationKind.ASSOCIATION:
            return InspirationInterpretation(
                hypothesis=(
                    "these observations may have a meaningful relationship "
                    "worth checking with the user"
                ),
                model_trace={
                    "provider": "reference-inspiration-interpreter",
                    "model": self.derivation_id,
                },
            )
        return InspirationInterpretation(
            hypothesis=None,
            status="UNKNOWN",
            model_trace={
                "provider": "reference-inspiration-interpreter",
                "model": self.derivation_id,
            },
        )


class InspirationStore:
    """Persistent internal queue with an opaque public read surface."""

    def __init__(self, root: Path | str) -> None:
        root_path = Path(root)
        root_path.mkdir(parents=True, exist_ok=True)
        self.db_path = root_path / "inspiration.sqlite"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inspiration_materials (
                material_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                kind TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                line_id TEXT,
                support_json TEXT NOT NULL,
                trace_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_inspiration_status_created
            ON inspiration_materials(status, created_at, material_id)
            """
        )
        self.conn.commit()

    def put(
        self,
        *,
        material_id: str,
        content: str,
        package: InspirationPackage,
        trace: dict[str, object],
    ) -> InspirationMaterial | None:
        material = InspirationMaterial(material_id, content)
        payload = {
            "block_ids": package.block_ids,
            "state_ids": package.state_ids,
            "raw_evidence_ids": package.raw_evidence_ids,
            "knowledge_cutoff": package.knowledge_cutoff.isoformat(),
        }
        self.conn.execute(
            """
            INSERT OR IGNORE INTO inspiration_materials(
                material_id, content, kind, candidate_id, line_id,
                support_json, trace_json, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
            """,
            (
                material.material_id,
                material.content,
                package.kind.value,
                package.candidate_id,
                package.line_id,
                json.dumps(payload, sort_keys=True),
                json.dumps(trace, sort_keys=True, default=str),
                datetime.now(UTC).isoformat(),
            ),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT status, content FROM inspiration_materials "
            "WHERE material_id = ?",
            (material.material_id,),
        ).fetchone()
        if row is None or str(row[0]) != "PENDING":
            return None
        return InspirationMaterial(material.material_id, str(row[1]))

    def pending(self, *, limit: int) -> tuple[InspirationMaterial, ...]:
        if type(limit) is not int or not 0 <= limit <= 100:
            raise ValueError("limit must be an integer in [0, 100]")
        if limit == 0:
            return ()
        rows = self.conn.execute(
            """
            SELECT material_id, content
            FROM inspiration_materials
            WHERE status = 'PENDING'
            ORDER BY created_at, material_id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return tuple(
            InspirationMaterial(str(row[0]), str(row[1]))
            for row in rows
        )

    def set_status(self, material_id: str, status: str) -> None:
        _nonempty(material_id, "material_id")
        if status not in {"CONSUMED", "DISMISSED"}:
            raise ValueError("status must be CONSUMED or DISMISSED")
        cursor = self.conn.execute(
            "UPDATE inspiration_materials SET status = ? "
            "WHERE material_id = ? AND status = 'PENDING'",
            (status, material_id),
        )
        self.conn.commit()
        if cursor.rowcount == 0:
            exists = self.conn.execute(
                "SELECT 1 FROM inspiration_materials WHERE material_id = ?",
                (material_id,),
            ).fetchone()
            if exists is None:
                raise KeyError(material_id)

    def status(self, material_id: str) -> str:
        row = self.conn.execute(
            "SELECT status FROM inspiration_materials WHERE material_id = ?",
            (material_id,),
        ).fetchone()
        if row is None:
            raise KeyError(material_id)
        return str(row[0])

    def close(self) -> None:
        self.conn.close()


class InspirationRuntime:
    """Compile rich LCE structure into opaque proactive-message material."""

    def __init__(
        self,
        *,
        memory: ReferenceMemorySubstratePort,
        line_store: LineGraphStore,
        root: Path | str,
        interpreter: InspirationInterpreter | None = None,
        config: InspirationConfig | None = None,
    ) -> None:
        self.memory = memory
        self.lines = line_store
        self.line_view = LineGraphView(memory=memory, store=line_store)
        self.interpreter = interpreter or RuleBasedInspirationInterpreter()
        self.config = config or InspirationConfig()
        self.store = InspirationStore(root)

    def discover(
        self,
        *,
        knowledge_cutoff: datetime,
        trajectory_result: TrajectoryRuntimeResult | None = None,
    ) -> tuple[InspirationMaterial, ...]:
        _require_utc(knowledge_cutoff, "knowledge_cutoff")
        materials: list[InspirationMaterial] = []
        if trajectory_result is not None:
            materials.extend(
                self._association_materials(
                    trajectory_result,
                    knowledge_cutoff=knowledge_cutoff,
                )
            )
        materials.extend(
            self._extension_materials(
                knowledge_cutoff=knowledge_cutoff,
            )
        )
        return tuple(materials)

    def pending_materials(
        self,
        *,
        limit: int = 20,
    ) -> tuple[InspirationMaterial, ...]:
        return self.store.pending(limit=limit)

    def consume(self, material_id: str) -> None:
        self.store.set_status(material_id, "CONSUMED")

    def dismiss(self, material_id: str) -> None:
        self.store.set_status(material_id, "DISMISSED")

    def _association_materials(
        self,
        result: TrajectoryRuntimeResult,
        *,
        knowledge_cutoff: datetime,
    ) -> tuple[InspirationMaterial, ...]:
        output: list[InspirationMaterial] = []
        for path, update in zip(
            result.candidate_paths,
            result.line_updates,
            strict=True,
        ):
            if len(output) >= self.config.max_association_materials:
                break
            # A converged path is already a durable structure. Association
            # inspiration is specifically for local structure that looks
            # related but has not obtained a single persistent identity.
            if update.line_id is not None:
                continue
            blocks = self._blocks_for_states(
                path.block_ids,
                path.state_ids,
                knowledge_cutoff=knowledge_cutoff,
            )
            if len(blocks) < 2:
                continue
            package = self._package(
                kind=InspirationKind.ASSOCIATION,
                candidate_id=path.path_id,
                blocks=blocks,
                knowledge_cutoff=knowledge_cutoff,
                line_id=None,
            )
            material = self._compile(package)
            if material is not None:
                output.append(material)
        return tuple(output)

    def _extension_materials(
        self,
        *,
        knowledge_cutoff: datetime,
    ) -> tuple[InspirationMaterial, ...]:
        output: list[InspirationMaterial] = []
        for line in self.lines.list_lines():
            if len(output) >= self.config.max_extension_materials:
                break
            paths = self.line_view.paths_to_frontier(
                line.line_id,
                knowledge_cutoff=knowledge_cutoff,
                max_paths=self.config.max_extension_materials * 4,
                max_nodes=max(
                    self.config.max_extension_path_nodes * 4,
                    self.config.max_extension_path_nodes,
                ),
            )
            for node_path in paths:
                if len(output) >= self.config.max_extension_materials:
                    break
                selected_nodes = node_path[
                    -self.config.max_extension_path_nodes:
                ]
                blocks: list[SemanticBlock] = []
                for node_id in selected_nodes:
                    block = self.line_view.state_for_node_at_cutoff(
                        node_id,
                        knowledge_cutoff=knowledge_cutoff,
                    )
                    if block is None:
                        blocks = []
                        break
                    blocks.append(block)
                if len(blocks) < 2:
                    continue
                state_ids = tuple(
                    block.state_id or "" for block in blocks
                )
                if any(not state_id for state_id in state_ids):
                    continue
                candidate_payload = json.dumps(
                    {
                        "line_id": line.line_id,
                        "state_ids": state_ids,
                    },
                    sort_keys=True,
                )
                candidate_id = "extension_" + hashlib.sha256(
                    candidate_payload.encode()
                ).hexdigest()[:24]
                package = self._package(
                    kind=InspirationKind.EXTENSION,
                    candidate_id=candidate_id,
                    blocks=tuple(blocks),
                    knowledge_cutoff=knowledge_cutoff,
                    line_id=line.line_id,
                )
                material = self._compile(package)
                if material is not None:
                    output.append(material)
        return tuple(output)

    def _blocks_for_states(
        self,
        block_ids: Sequence[str],
        state_ids: Sequence[str],
        *,
        knowledge_cutoff: datetime,
    ) -> tuple[SemanticBlock, ...]:
        if len(block_ids) != len(state_ids):
            return ()
        blocks: list[SemanticBlock] = []
        for block_id, state_id in zip(
            block_ids,
            state_ids,
            strict=True,
        ):
            try:
                block = self.memory.get_semantic_block_state(state_id)
            except KeyError:
                return ()
            if block.block_id != block_id:
                return ()
            if not all(
                _evidence_valid_at(
                    self.memory,
                    evidence_id,
                    knowledge_cutoff,
                )
                for evidence_id in block.raw_evidence_ids
            ):
                return ()
            blocks.append(block)
        return tuple(blocks)

    def _package(
        self,
        *,
        kind: InspirationKind,
        candidate_id: str,
        blocks: tuple[SemanticBlock, ...],
        knowledge_cutoff: datetime,
        line_id: str | None,
    ) -> InspirationPackage:
        return InspirationPackage(
            kind=kind,
            candidate_id=candidate_id,
            content_fragments=tuple(
                block.content.strip()[: self.config.max_fragment_chars]
                for block in blocks
            ),
            block_ids=tuple(block.block_id for block in blocks),
            state_ids=tuple(
                block.state_id or "" for block in blocks
            ),
            raw_evidence_ids=tuple(
                sorted(
                    {
                        evidence_id
                        for block in blocks
                        for evidence_id in block.raw_evidence_ids
                    }
                )
            ),
            knowledge_cutoff=knowledge_cutoff,
            line_id=line_id,
        )

    def _compile(
        self,
        package: InspirationPackage,
    ) -> InspirationMaterial | None:
        interpretation = self.interpreter.interpret(package)
        if (
            interpretation.status != "PROPOSED"
            or interpretation.hypothesis is None
        ):
            return None
        content = self._render(
            package,
            interpretation.hypothesis.strip(),
        )
        material_id = self._material_id(package)
        trace = dict(interpretation.model_trace or {})
        trace["kind"] = package.kind.value
        return self.store.put(
            material_id=material_id,
            content=content,
            package=package,
            trace=trace,
        )

    @staticmethod
    def _material_id(package: InspirationPackage) -> str:
        payload = {
            "kind": package.kind.value,
            "candidate_id": package.candidate_id,
            "line_id": package.line_id,
            "state_ids": package.state_ids,
        }
        return "insp_" + hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()[:24]

    @staticmethod
    def _render(
        package: InspirationPackage,
        hypothesis: str,
    ) -> str:
        if package.kind is InspirationKind.ASSOCIATION:
            observed = "\n".join(
                f"- {fragment}"
                for fragment in package.content_fragments
            )
            return (
                "Possible connection to explore (not established): "
                f"{hypothesis}\n"
                "Observed material:\n"
                f"{observed}"
            )

        supported = " -> ".join(package.content_fragments)
        return (
            "Existing supported line: "
            f"{supported}\n"
            "Possible next implication to explore (not established): "
            f"{hypothesis}"
        )

    def close(self) -> None:
        self.store.close()
