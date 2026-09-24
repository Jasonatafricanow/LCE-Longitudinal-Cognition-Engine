"""Arm D: Full-frame comparator adapter.

Extracts a rich internal semantic frame (frame name, core elements, epistemic layers),
then deterministically projects it onto the identical public SemanticBlock shape.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research.benchmarks.semantic_block_v0_1.adapters.base import (
    BaseCompilerAdapter,
    verify_span,
)
from research.benchmarks.semantic_block_v0_1.contracts import (
    PredictionRecord,
    PublicRelation,
    PublicSemanticBlock,
    SourceSpan,
    VisibleCaseInput,
)
from research.benchmarks.semantic_block_v0_1.llm_client import BenchmarkLLMClient

FRAME_SYSTEM_PROMPT = """You are the LCE Rich Internal Semantic Frame Parser.
Parse cutoff-visible evidence into structured event/state frames.
Each internal frame captures:
- frame_id, frame_name (e.g. Joining, Causation, Quoting, Stalling, Failing)
- core_elements: dict of semantic arguments (Agent, Theme, Cause, Effect, etc.)
- canonical_content: readable source-grounded account
- predicate: normalized lemma
- kind: event | state | attitude | proposition
- holder, utterer, attribution_mode (direct_speaker | direct_quote | indirect_report)
- polarity, modality (asserted | intended | possible), epistemic_hedge (none | uncertain)
- valid_time, time_precision
- entity_status (resolved | unresolved), uncertainty (none | actor_ambiguous | referent_unresolved | decision_unresolved)
- source_spans: [{"evidence_id": ..., "text": ...}]
- relations: [{"type": "CAUSE" | "SAME_ENTITY" | "BEFORE", "target_frame_id": ..., "cue_text": ...}]

Rules:
1. Reusability: Keep causal compound in one frame ("Because queue lost quorum, API returned 503").
2. Quoted statements belong to quote speaker, not author.
3. Possibility/Intention are not asserted events.
4. Ambiguous pronouns/referents without registry are unresolved.
5. No direct shortcut CAUSE edges if multi-hop chain exists.

Output JSON:
{
  "frames": [
    {
      "frame_id": "f1",
      "frame_name": "...",
      "canonical_content": "...",
      "predicate": "...",
      "kind": "event" | "state" | "attitude" | "proposition",
      "core_elements": {"...": "..."},
      "holder": "user" | "...",
      "utterer": "user" | "...",
      "attribution_mode": "direct_speaker" | "direct_quote" | "indirect_report",
      "polarity": "positive" | "negative",
      "modality": "asserted" | "intended" | "possible",
      "epistemic_hedge": "none" | "uncertain",
      "valid_time": "...",
      "time_precision": "day" | "month" | "season" | "year",
      "entity_status": "resolved" | "unresolved",
      "uncertainty": "none" | "actor_ambiguous" | "referent_unresolved" | "decision_unresolved",
      "source_spans": [{"evidence_id": "...", "text": "..."}],
      "relations": [{"type": "...", "target_frame_id": "...", "cue_text": "..."}]
    }
  ]
}
"""


class ArmDFullFrameAdapter(BaseCompilerAdapter):
    """Full-frame comparator adapter projecting internal frames to public blocks."""

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        super().__init__(arm_id="D")
        self.client = BenchmarkLLMClient(cache_dir=cache_dir)

    def compile(self, case_input: VisibleCaseInput) -> PredictionRecord:
        evidence_map = {e["evidence_id"]: e for e in case_input.visible_evidence}
        for e in case_input.context_evidence:
            evidence_map[e["evidence_id"]] = e

        prompt = json.dumps({
            "case_id": case_input.case_id,
            "cutoff": case_input.cutoff,
            "visible_evidence": case_input.visible_evidence,
            "bounded_context": case_input.context_evidence,
            "entity_registry": case_input.entity_registry,
        }, indent=2, ensure_ascii=False)

        res = self.client.generate_structured_json(
            prompt=prompt,
            system_instruction=FRAME_SYSTEM_PROMPT,
        )

        frames = res.content.get("frames", [])

        # Project internal frames to public blocks
        admitted_blocks: list[PublicSemanticBlock] = []
        frame_id_to_state_id: dict[str, str] = {}

        for idx, f in enumerate(frames, start=1):
            fid = str(f.get("frame_id", f"f{idx}"))
            spans_in = f.get("source_spans", [])

            valid_spans: list[SourceSpan] = []
            for sp in spans_in:
                eid = sp.get("evidence_id", "")
                txt = sp.get("text", "")
                v_span = verify_span(eid, 0, len(txt), txt, evidence_map)
                if v_span:
                    valid_spans.append(v_span)

            if not valid_spans:
                continue

            max_available = max(evidence_map[s.evidence_id]["available_at"] for s in valid_spans)
            if max_available > case_input.cutoff:
                continue

            s_key = f"s{len(admitted_blocks) + 1}"
            state_id = f"{case_input.case_id}_{s_key}"
            block_id = f"{case_input.case_id}_{s_key}"
            frame_id_to_state_id[fid] = state_id

            elements = dict(f.get("core_elements", {}))
            for role, val in list(elements.items()):
                if val in case_input.entity_registry:
                    elements[role] = case_input.entity_registry[val]

            support_eids = {s.evidence_id for s in valid_spans}

            blk = PublicSemanticBlock(
                block_id=block_id,
                state_id=state_id,
                state_available_at=max_available,
                canonical_content=str(f.get("canonical_content", "")).strip(),
                predicate=str(f.get("predicate", "UNKNOWN")),
                kind=str(f.get("kind", "event")),
                participants=elements,
                holder=str(f.get("holder", "user")),
                utterer=str(f.get("utterer", "user")),
                attribution_mode=str(f.get("attribution_mode", "direct_speaker")),
                polarity=str(f.get("polarity", "positive")),
                modality=str(f.get("modality", "asserted")),
                epistemic_hedge=str(f.get("epistemic_hedge", "none")),
                valid_time=str(f.get("valid_time", case_input.cutoff[:10])),
                time_precision=str(f.get("time_precision", "day")),
                entity_status=str(f.get("entity_status", "resolved")),
                uncertainty=str(f.get("uncertainty", "none")),
                independent_support_count=len(support_eids),
                source_spans=valid_spans,
                lineage_id=f"lineage_d_{case_input.case_id}",
                compiler_version="arm-d-full-frame-v1",
            )
            admitted_blocks.append(blk)

        admitted_relations: list[PublicRelation] = []
        for f in frames:
            src_fid = str(f.get("frame_id", ""))
            if src_fid not in frame_id_to_state_id:
                continue
            src_state = frame_id_to_state_id[src_fid]

            for r in f.get("relations", []):
                r_type = str(r.get("type", "")).upper()
                if r_type not in {"CAUSE", "SAME_ENTITY", "BEFORE"}:
                    continue
                tgt_fid = str(r.get("target_frame_id", ""))
                if tgt_fid not in frame_id_to_state_id:
                    continue
                tgt_state = frame_id_to_state_id[tgt_fid]
                if src_state == tgt_state:
                    continue

                cue_text = r.get("cue_text")
                cue_span: SourceSpan | None = None
                if cue_text:
                    for ev in case_input.visible_evidence:
                        c_span = verify_span(ev["evidence_id"], 0, len(cue_text), cue_text, evidence_map)
                        if c_span:
                            cue_span = c_span
                            break

                basis = "explicit_connective" if cue_span else "authorized_registry"
                traversal = r_type in {"CAUSE", "SAME_ENTITY"}

                admitted_relations.append(PublicRelation(
                    type=r_type,
                    direction="directed",
                    source_state_id=src_state,
                    target_state_id=tgt_state,
                    basis=basis,
                    cue_span=cue_span,
                    traversal_allowed=traversal,
                ))

        return PredictionRecord(
            case_id=case_input.case_id,
            cutoff=case_input.cutoff,
            arm_id="D",
            manifest_id=f"manifest_D_{case_input.case_id}_{case_input.cutoff}",
            blocks=admitted_blocks,
            relations=admitted_relations,
            call_count=1,
            prompt_tokens=res.prompt_tokens,
            completion_tokens=res.completion_tokens,
            total_tokens=res.total_tokens,
            latency_ms=res.latency_ms,
        )
