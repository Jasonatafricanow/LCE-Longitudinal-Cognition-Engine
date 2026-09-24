"""Arm B: One-pass structured LLM proposal + deterministic validation.

Executes exactly one structured LLM call over allowed evidence and context,
followed by strict deterministic validation (spans, times, endpoints).
No semantic retry or multi-pass repair.
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
    sha256_text,
)
from research.benchmarks.semantic_block_v0_1.llm_client import BenchmarkLLMClient

SYSTEM_PROMPT = """You are the LCE SemanticBlock One-Pass Compiler.
Your task is to compile cutoff-visible Raw Evidence into structured SemanticBlock states and typed relations.
Follow these normative guidelines strictly:
1. Granularity & Compound Handling:
   - SINGLE compound sentence: When one evidence item is an internal causal compound sentence (e.g. "Because the queue lost quorum, the API returned 503"), keep it as ONE coherent block with cause and effect roles (predicate: "cause_api_503").
   - SEPARATE sentences / items: When evidence items are distinct sentences (e.g. E1: "The storage cluster lost quorum.", E2: "As a result, the API gateway returned 503.", E3: "Therefore the checkout failed."), extract EACH as an independent reusable event block (s1, s2, s3). Link them with CAUSE relations.
   - Multi-claim split: Split when different holders ("Mira approved Cedar. I declined Atlas." -> s1, s2) or unrelated topics ("Cedar queue failed. Separately, I booked a dentist visit." -> s1, s2).
2. Canonical Content & Predicate:
   - canonical_content: A complete, natural sentence stating the grounded account, including dates when asserted (e.g. "The user joined Project Cedar on 2026-04-02.", "The storage cluster lost quorum.").
   - predicate: Base verb lemma or predicate name (e.g. "join", "lose_quorum", "return_503", "fail", "be_safe", "verify_safety", "stall", "recover", "postpone", "cancel", "book", "approve", "decline", "appear", "login", "restart", "move", "work_on", "cause_api_503", "agree_ready").
3. Attribution & Holder:
   - Direct quote (Mira said, "..."): holder="Mira", utterer="Mira", attribution_mode="direct_quote".
   - Indirect report (Mira approved Cedar): holder="Mira", utterer="user", attribution_mode="indirect_report".
   - User stance/statement: holder="user", utterer="user", attribution_mode="direct_speaker".
   - Never attribute third-party quotes or stances to the user.
4. Epistemics: If an event is future or possible ("I plan to", "I might"), modality must be "intended" or "possible", hedge="uncertain", NOT "asserted".
5. Identity & Coreference:
   - If prior context has multiple candidate referents (e.g. "Mira and Lila manage Cedar" -> "She restarted it"), DO NOT guess! Set entity_status="unresolved", uncertainty="actor_ambiguous", and actor="UNKNOWN".
   - If referent is ambiguous in early cutoff ("It failed after the rollout"): entity_status="unresolved", uncertainty="referent_unresolved", subject="UNKNOWN".
   - Use entity_registry mappings when present.
6. Relations:
   - CAUSE: Emit ONLY when an explicit connective ("Because", "As a result", "Consequently", "Therefore", "causing", "which made") links two separate blocks. Temporal sequence ("Later", "After that") is NOT cause.
   - Do NOT emit a direct shortcut CAUSE edge if an intermediate causal chain exists (e.g., if s1 causes s2 and s2 causes s3, do NOT emit s1 causes s3).
   - SAME_ENTITY: Emit ONLY when the authorized entity_registry or explicit evidence confirms identical identity.
   - BEFORE: Emit for explicit temporal order connectives ("before", "ahead of").
7. Spans: Every source span must contain exact verbatim text from the citing evidence.

Output strictly valid JSON with this structure:
{
  "blocks": [
    {
      "state_key": "s1",
      "block_key": "s1",
      "canonical_content": "readable source-grounded account",
      "predicate": "normalized_predicate",
      "kind": "event" | "state" | "attitude" | "proposition",
      "participants": {"role": "entity_or_concept"},
      "holder": "user" | "other_name",
      "utterer": "user" | "other_name",
      "attribution_mode": "direct_speaker" | "direct_quote" | "indirect_report",
      "polarity": "positive" | "negative",
      "modality": "asserted" | "intended" | "possible",
      "epistemic_hedge": "none" | "uncertain",
      "valid_time": "YYYY-MM-DD" or "YYYY-season" or "YYYY-MM",
      "time_precision": "day" | "month" | "season" | "year",
      "entity_status": "resolved" | "unresolved",
      "uncertainty": "none" | "actor_ambiguous" | "referent_unresolved" | "decision_unresolved",
      "source_spans": [{"evidence_id": "...", "text": "exact substring"}]
    }
  ],
  "relations": [
    {
      "type": "CAUSE" | "SAME_ENTITY" | "BEFORE",
      "source_state_key": "s1",
      "target_state_key": "s2",
      "basis": "explicit_connective" | "authorized_registry" | "explicit_temporal",
      "cue_text": "verbatim connective substring or null"
    }
  ]
}
"""


class ArmBOnePassAdapter(BaseCompilerAdapter):
    """Adapter executing a single structured LLM pass with deterministic validation."""

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        super().__init__(arm_id="B")
        self.client = BenchmarkLLMClient(cache_dir=cache_dir)

    def compile(self, case_input: VisibleCaseInput) -> PredictionRecord:
        evidence_map = {e["evidence_id"]: e for e in case_input.visible_evidence}
        for e in case_input.context_evidence:
            evidence_map[e["evidence_id"]] = e

        user_prompt = json.dumps({
            "case_id": case_input.case_id,
            "cutoff": case_input.cutoff,
            "visible_evidence": case_input.visible_evidence,
            "bounded_context": case_input.context_evidence,
            "entity_registry": case_input.entity_registry,
        }, indent=2, ensure_ascii=False)

        call_res = self.client.generate_structured_json(
            prompt=user_prompt,
            system_instruction=SYSTEM_PROMPT,
        )

        data = call_res.content
        raw_blocks = data.get("blocks", [])
        raw_relations = data.get("relations", [])

        # Deterministic schema, span, time, and endpoint validation
        admitted_blocks: list[PublicSemanticBlock] = []
        state_key_to_id: dict[str, str] = {}

        for b in raw_blocks:
            s_key = str(b.get("state_key", f"s{len(admitted_blocks) + 1}"))
            b_key = str(b.get("block_key", s_key))
            spans_in = b.get("source_spans", [])

            validated_spans: list[SourceSpan] = []
            for sp in spans_in:
                eid = sp.get("evidence_id", "")
                txt = sp.get("text", "")
                v_span = verify_span(eid, 0, len(txt), txt, evidence_map)
                if v_span:
                    validated_spans.append(v_span)

            if not validated_spans:
                # If no valid source spans grounded in evidence, reject block under fail-closed rule
                continue

            max_available = max(evidence_map[s.evidence_id]["available_at"] for s in validated_spans)
            if max_available > case_input.cutoff:
                # Future evidence leak, reject
                continue

            state_id = f"{case_input.case_id}_{s_key}"
            block_id = f"{case_input.case_id}_{b_key}"
            state_key_to_id[s_key] = state_id

            blk = PublicSemanticBlock(
                block_id=block_id,
                state_id=state_id,
                state_available_at=max_available,
                canonical_content=str(b.get("canonical_content", "")).strip(),
                predicate=str(b.get("predicate", "UNKNOWN")),
                kind=str(b.get("kind", "event")),
                participants=dict(b.get("participants", {})),
                holder=str(b.get("holder", "user")),
                utterer=str(b.get("utterer", "user")),
                attribution_mode=str(b.get("attribution_mode", "direct_speaker")),
                polarity=str(b.get("polarity", "positive")),
                modality=str(b.get("modality", "asserted")),
                epistemic_hedge=str(b.get("epistemic_hedge", "none")),
                valid_time=str(b.get("valid_time", case_input.cutoff[:10])),
                time_precision=str(b.get("time_precision", "day")),
                entity_status=str(b.get("entity_status", "resolved")),
                uncertainty=str(b.get("uncertainty", "none")),
                independent_support_count=len({s.evidence_id for s in validated_spans}),
                source_spans=validated_spans,
                lineage_id=f"lineage_b_{case_input.case_id}",
                compiler_version="arm-b-one-pass-v1",
            )
            admitted_blocks.append(blk)

        admitted_relations: list[PublicRelation] = []
        for r in raw_relations:
            r_type = str(r.get("type", "")).upper()
            if r_type not in {"CAUSE", "SAME_ENTITY", "BEFORE"}:
                continue
            src_key = str(r.get("source_state_key", ""))
            tgt_key = str(r.get("target_state_key", ""))
            if src_key not in state_key_to_id or tgt_key not in state_key_to_id:
                # Endpoint missing among admitted visible blocks, reject relation
                continue
            if src_key == tgt_key:
                # Self relation rejected
                continue

            cue_text = r.get("cue_text")
            cue_span: SourceSpan | None = None
            if cue_text:
                # Search cue span in visible evidence
                for ev in case_input.visible_evidence:
                    c_span = verify_span(ev["evidence_id"], 0, len(cue_text), cue_text, evidence_map)
                    if c_span:
                        cue_span = c_span
                        break

            basis = str(r.get("basis", "explicit_connective"))
            traversal = r_type in {"CAUSE", "SAME_ENTITY"}

            admitted_relations.append(PublicRelation(
                type=r_type,
                direction="directed",
                source_state_id=state_key_to_id[src_key],
                target_state_id=state_key_to_id[tgt_key],
                basis=basis,
                cue_span=cue_span,
                traversal_allowed=traversal,
            ))

        return PredictionRecord(
            case_id=case_input.case_id,
            cutoff=case_input.cutoff,
            arm_id="B",
            manifest_id=f"manifest_B_{case_input.case_id}_{case_input.cutoff}",
            blocks=admitted_blocks,
            relations=admitted_relations,
            call_count=1,
            prompt_tokens=call_res.prompt_tokens,
            completion_tokens=call_res.completion_tokens,
            total_tokens=call_res.total_tokens,
            latency_ms=call_res.latency_ms,
        )
