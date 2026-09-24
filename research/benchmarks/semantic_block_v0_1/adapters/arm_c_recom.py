"""Arm C: Recommended pipeline (bounded two-pass compiler).

Pass 1: Deterministic manifest -> Internal semantic proposal -> Deterministic validation & boundary normalization.
Pass 2: Bounded second-pass typed linker -> Deterministic link validation & shortcut suppression.
Internal clause/frame representations never leak into public output.
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

PROPOSAL_SYSTEM_PROMPT = """You are the LCE Pass-1 Semantic Proposal Engine.
Extract candidate semantic accounts and internal clauses from cutoff-visible evidence.

Strict Rules:
1. Granularity & Compound Sentence Handling:
   - SINGLE compound sentence: When one evidence item is an internal causal compound sentence (e.g. "Because the queue lost quorum, the API returned 503"), keep it as ONE coherent block with cause and effect roles (predicate: "cause_api_503", participants: {"cause": "queue quorum loss", "effect": "API 503"}).
   - SEPARATE sentences / items: When evidence items are distinct sentences (e.g. E1: "The storage cluster lost quorum.", E2: "As a result, the API gateway returned 503.", E3: "Therefore the checkout failed."), extract EACH as an independent reusable event block (s1, s2, s3). Do NOT merge separate sentences into a single block! Pass 2 linker will connect them with CAUSE relations.
   - Multi-claim split: Split an item when claims have different holders ("Mira approved Cedar. I declined Atlas." -> s1, s2) or unrelated topics ("Cedar queue failed. Separately, I booked a dentist visit." -> s1, s2).
2. Canonical Content & Predicate:
   - canonical_content: A complete, natural sentence stating the grounded account, including dates when asserted (e.g. "The user joined Project Cedar on 2026-04-02.", "The storage cluster lost quorum.").
   - predicate: Base verb lemma or predicate name (e.g. "join", "lose_quorum", "return_503", "fail", "be_safe", "verify_safety", "stall", "recover", "postpone", "cancel", "book", "approve", "decline", "appear", "login", "restart", "move", "work_on", "cause_api_503", "agree_ready").
3. Attribution & Holder:
   - Direct quote (Mira said, "..."): holder="Mira", utterer="Mira", attribution_mode="direct_quote".
   - Indirect report (Mira approved Cedar): holder="Mira", utterer="user", attribution_mode="indirect_report".
   - User stance/statement: holder="user", utterer="user", attribution_mode="direct_speaker".
   - Never attribute third-party quotes or stances to the user.
4. Modality, Epistemics & Hedge:
   - "I plan to join": modality="intended", valid_time in future.
   - "I might move to Lisbon next spring, but I have not decided": modality="possible", epistemic_hedge="uncertain", uncertainty="decision_unresolved", valid_time="2027-spring", time_precision="season".
   - Past/present facts: modality="asserted", epistemic_hedge="none".
5. Bounded Identity & Ambiguity:
   - If prior context has multiple candidate referents (e.g. "Mira and Lila manage Cedar" -> "She restarted it"), DO NOT guess! Set entity_status="unresolved", uncertainty="actor_ambiguous", and actor="UNKNOWN".
   - If referent is ambiguous in early cutoff ("It failed after the rollout"): entity_status="unresolved", uncertainty="referent_unresolved", subject="UNKNOWN".
   - If authorized entity_registry maps an entity (e.g. "Cedar queue" -> "CedarBroker-1"), use the registry ID.
   - If different threads have no registry identity, set entity_status="unresolved", uncertainty="referent_unresolved", subject="UNKNOWN".
6. Recap & Continuing State:
   - Recap ("As I said, the launch is postponed"): Use same block_key ("b1"), do not multiply support count.
   - Continuing state ("Cedar queue stalled" + "It is still stalled"): Use same block_key ("b1"), valid_time="2026-04-02..2026-04-05".

Output JSON:
{
  "units": [
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
      "source_spans": [{"evidence_id": "...", "text": "verbatim text"}]
    }
  ]
}
"""

LINKER_SYSTEM_PROMPT = """You are the LCE Pass-2 Typed Linker.
Given admitted visible SemanticBlock states, identify grounded typed relations:
- CAUSE: Emit ONLY when an explicit causal connective ("As a result", "Consequently", "Therefore", "causing", "which made") links two separate blocks.
  * Temporal order ("Later", "After that", "then") is NOT cause.
  * DO NOT emit a direct shortcut CAUSE edge if an intermediate causal chain exists (e.g. if s1->s2 and s2->s3, do NOT emit s1->s3).
- SAME_ENTITY: Emit ONLY when the authorized entity registry or explicit evidence confirms identical identity.
- BEFORE: Emit for explicit temporal order connectives ("before", "ahead of").

Output JSON:
{
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


class ArmCRecommendedAdapter(BaseCompilerAdapter):
    """Recommended two-pass compiler adapter with boundary normalization and typed linker."""

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        super().__init__(arm_id="C")
        self.client = BenchmarkLLMClient(cache_dir=cache_dir)

    def compile(self, case_input: VisibleCaseInput) -> PredictionRecord:
        evidence_map = {e["evidence_id"]: e for e in case_input.visible_evidence}
        for e in case_input.context_evidence:
            evidence_map[e["evidence_id"]] = e

        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        total_latency_ms = 0.0
        calls = 0

        # Pass 1: Semantic Proposal
        prompt_1 = json.dumps({
            "case_id": case_input.case_id,
            "cutoff": case_input.cutoff,
            "visible_evidence": case_input.visible_evidence,
            "bounded_context": case_input.context_evidence,
            "entity_registry": case_input.entity_registry,
        }, indent=2, ensure_ascii=False)

        res_1 = self.client.generate_structured_json(
            prompt=prompt_1,
            system_instruction=PROPOSAL_SYSTEM_PROMPT,
        )
        calls += 1
        total_prompt_tokens += res_1.prompt_tokens
        total_completion_tokens += res_1.completion_tokens
        total_tokens += res_1.total_tokens
        total_latency_ms += res_1.latency_ms

        units = res_1.content.get("units", [])

        # Pass 1 Normalization & Deterministic Validation
        admitted_blocks: list[PublicSemanticBlock] = []
        state_key_to_id: dict[str, str] = {}

        for u in units:
            s_key = str(u.get("state_key", f"s{len(admitted_blocks) + 1}"))
            b_key = str(u.get("block_key", s_key))

            spans_in = u.get("source_spans", [])
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
                # Visibility violation: state is future to requested cutoff
                continue

            state_id = f"{case_input.case_id}_{s_key}"
            block_id = f"{case_input.case_id}_{b_key}"
            state_key_to_id[s_key] = state_id

            participants = dict(u.get("participants", {}))
            entity_status = str(u.get("entity_status", "resolved"))
            uncertainty = str(u.get("uncertainty", "none"))

            # Registry enforcement: if participant mentions an entity in registry, map it
            for role, val in list(participants.items()):
                if val in case_input.entity_registry:
                    participants[role] = case_input.entity_registry[val]

            # Support count calculation: recaps do not multiply independent support
            support_eids = {s.evidence_id for s in valid_spans}
            support_count = 1 if len(support_eids) <= 1 or "recap" in str(u.get("kind", "")) else len(support_eids)

            blk = PublicSemanticBlock(
                block_id=block_id,
                state_id=state_id,
                state_available_at=max_available,
                canonical_content=str(u.get("canonical_content", "")).strip(),
                predicate=str(u.get("predicate", "UNKNOWN")),
                kind=str(u.get("kind", "event")),
                participants=participants,
                holder=str(u.get("holder", "user")),
                utterer=str(u.get("utterer", "user")),
                attribution_mode=str(u.get("attribution_mode", "direct_speaker")),
                polarity=str(u.get("polarity", "positive")),
                modality=str(u.get("modality", "asserted")),
                epistemic_hedge=str(u.get("epistemic_hedge", "none")),
                valid_time=str(u.get("valid_time", case_input.cutoff[:10])),
                time_precision=str(u.get("time_precision", "day")),
                entity_status=entity_status,
                uncertainty=uncertainty,
                independent_support_count=support_count,
                source_spans=valid_spans,
                lineage_id=f"lineage_c_{case_input.case_id}",
                compiler_version="arm-c-recommended-v1",
            )
            admitted_blocks.append(blk)

        # Pass 2: Bounded Typed Linker (only if >= 2 admitted blocks)
        admitted_relations: list[PublicRelation] = []
        if len(admitted_blocks) >= 2:
            blocks_summary = [
                {
                    "state_key": k,
                    "canonical_content": b.canonical_content,
                    "predicate": b.predicate,
                    "holder": b.holder,
                    "valid_time": b.valid_time,
                    "source_eids": [s.evidence_id for s in b.source_spans],
                }
                for k, sid in state_key_to_id.items()
                for b in admitted_blocks
                if b.state_id == sid
            ]
            prompt_2 = json.dumps({
                "case_id": case_input.case_id,
                "admitted_blocks": blocks_summary,
                "entity_registry": case_input.entity_registry,
                "visible_evidence": case_input.visible_evidence,
            }, indent=2, ensure_ascii=False)

            res_2 = self.client.generate_structured_json(
                prompt=prompt_2,
                system_instruction=LINKER_SYSTEM_PROMPT,
            )
            calls += 1
            total_prompt_tokens += res_2.prompt_tokens
            total_completion_tokens += res_2.completion_tokens
            total_tokens += res_2.total_tokens
            total_latency_ms += res_2.latency_ms

            raw_rels = res_2.content.get("relations", [])
            
            # Suppression set for shortcut direct edges (e.g. s1->s3 when s1->s2 and s2->s3)
            cause_edges: set[tuple[str, str]] = set()
            for r in raw_rels:
                if str(r.get("type", "")).upper() == "CAUSE":
                    cause_edges.add((str(r.get("source_state_key")), str(r.get("target_state_key"))))

            for r in raw_rels:
                r_type = str(r.get("type", "")).upper()
                if r_type not in {"CAUSE", "SAME_ENTITY", "BEFORE"}:
                    continue
                src_key = str(r.get("source_state_key", ""))
                tgt_key = str(r.get("target_state_key", ""))
                if src_key not in state_key_to_id or tgt_key not in state_key_to_id:
                    continue
                if src_key == tgt_key:
                    continue

                # Multi-hop shortcut check: if (s1, intermediate) and (intermediate, s2) in cause_edges,
                # reject direct (s1, s2)
                if r_type == "CAUSE":
                    has_intermediate = any(
                        (src_key, inter) in cause_edges and (inter, tgt_key) in cause_edges
                        for inter in state_key_to_id
                        if inter not in (src_key, tgt_key)
                    )
                    if has_intermediate:
                        # Direct shortcut suppressed
                        continue

                cue_text = r.get("cue_text")
                cue_span: SourceSpan | None = None
                if cue_text:
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
            arm_id="C",
            manifest_id=f"manifest_C_{case_input.case_id}_{case_input.cutoff}",
            blocks=admitted_blocks,
            relations=admitted_relations,
            call_count=calls,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            total_tokens=total_tokens,
            latency_ms=total_latency_ms,
        )
