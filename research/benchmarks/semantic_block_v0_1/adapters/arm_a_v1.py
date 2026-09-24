"""Arm A: Current V1 Compiler behavior in an isolated research adapter.

Implements exact V1 compilation without new semantic slots or linking.
All unmodeled semantic fields are explicitly marked UNKNOWN.
"""

from __future__ import annotations

import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SRC = Path(__file__).resolve().parents[4] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lce.reference_memory.contracts import RawEvidence
from lce.semantic.compiler import SemanticCompiler
from lce.semantic.providers import RuleBasedSemanticProvider
from lce.testing.reference_memory import InMemoryReferenceMemory
from research.benchmarks.semantic_block_v0_1.adapters.base import (
    BaseCompilerAdapter,
)
from research.benchmarks.semantic_block_v0_1.contracts import (
    PredictionRecord,
    PublicSemanticBlock,
    SourceSpan,
    VisibleCaseInput,
)


def _to_utc(iso_str: str) -> datetime:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt if dt.tzinfo == UTC else dt.astimezone(UTC)


class ArmAV1Adapter(BaseCompilerAdapter):
    """Adapter wrapping exact V1 reference memory stream compiler."""

    def __init__(self) -> None:
        super().__init__(arm_id="A")

    def compile(self, case_input: VisibleCaseInput) -> PredictionRecord:
        t0 = time.perf_counter()
        substrate = InMemoryReferenceMemory()
        lineage_id = f"lineage_v1_{case_input.case_id}"
        compiler = SemanticCompiler(
            store=substrate,
            provider=RuleBasedSemanticProvider(),
            lineage_id=lineage_id,
            compiler_version="lce-semantic-stream-v1",
        )

        evidence_map = {e["evidence_id"]: e for e in case_input.visible_evidence}
        # Also map context evidence
        for e in case_input.context_evidence:
            evidence_map[e["evidence_id"]] = e

        # Feed visible evidence in order
        all_materials = case_input.context_evidence + case_input.visible_evidence
        for item in all_materials:
            raw_ev = RawEvidence(
                evidence_id=item["evidence_id"],
                content=item["content"],
                occurred_at=_to_utc(item["occurred_at"]),
                provenance={
                    "source": item.get("source_id", "synthetic"),
                    "canonical": True,
                    "thread_id": item.get("thread_id", ""),
                    "speaker": item.get("speaker", "user"),
                },
                ordering_key=item["occurred_at"],
            )
            compiler.process(raw_ev)

        # Retrieve current valid blocks
        v1_blocks = substrate.list_semantic_blocks(current_valid_only=True)
        # Filter to only those blocks whose raw_evidence_ids overlap with visible_evidence
        visible_eids = {e["evidence_id"]: e for e in case_input.visible_evidence}

        public_blocks: list[PublicSemanticBlock] = []
        for blk in v1_blocks:
            # Check if this block contains any primary visible evidence
            overlap_eids = [eid for eid in blk.raw_evidence_ids if eid in visible_eids]
            if not overlap_eids and case_input.visible_evidence:
                continue

            max_available = max(evidence_map[eid]["available_at"] for eid in blk.raw_evidence_ids)

            spans: list[SourceSpan] = []
            for eid in blk.raw_evidence_ids:
                if eid in evidence_map:
                    ev_text = evidence_map[eid]["content"]
                    spans.append(SourceSpan(
                        evidence_id=eid,
                        char_start=0,
                        char_end=len(ev_text),
                        text=ev_text,
                    ))

            state_id = blk.state_id or f"{blk.block_id}:v{blk.state_version}"
            public_blocks.append(PublicSemanticBlock(
                block_id=blk.block_id,
                state_id=state_id,
                state_available_at=max_available,
                canonical_content=blk.content,
                predicate="UNKNOWN",
                kind="UNKNOWN",
                participants={"subject": "UNKNOWN"},
                holder="UNKNOWN",
                utterer="UNKNOWN",
                attribution_mode="UNKNOWN",
                polarity="UNKNOWN",
                modality="UNKNOWN",
                epistemic_hedge="UNKNOWN",
                valid_time="UNKNOWN",
                time_precision="UNKNOWN",
                entity_status="UNKNOWN",
                uncertainty="UNKNOWN",
                independent_support_count=len(blk.raw_evidence_ids),
                source_spans=spans,
                lineage_id=lineage_id,
                compiler_version=blk.compiler_version,
            ))

        latency_ms = (time.perf_counter() - t0) * 1000.0

        return PredictionRecord(
            case_id=case_input.case_id,
            cutoff=case_input.cutoff,
            arm_id="A",
            manifest_id=f"manifest_A_{case_input.case_id}_{case_input.cutoff}",
            blocks=public_blocks,
            relations=[],  # V1 has no relations
            call_count=0,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=latency_ms,
        )
