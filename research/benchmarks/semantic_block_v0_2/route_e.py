"""Route E: exact B proposal, fail-closed gates, and a selective linker."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from research.benchmarks.semantic_block_v0_1.adapters.arm_b_one_pass import SYSTEM_PROMPT
from research.benchmarks.semantic_block_v0_1.adapters.base import BaseCompilerAdapter
from research.benchmarks.semantic_block_v0_1.contracts import (
    PredictionRecord,
    PublicRelation,
    PublicSemanticBlock,
    SourceSpan,
    VisibleCaseInput,
    sha256_text,
)
from research.benchmarks.semantic_block_v0_1.llm_client import BenchmarkLLMClient


LINKER_SYSTEM_PROMPT = """You are Route E's bounded relation linker.
Return only links among the supplied screened candidate pairs. Do not add,
remove, or rewrite semantic blocks. Use only the supplied endpoint keys and
source cue. CAUSE requires a supported directed connective; a chain does not
authorize a direct shortcut. SAME_ENTITY requires the supplied authorized
registry basis or explicit co-reference cue. BEFORE is timing metadata and
must have traversal_allowed=false. Return strict JSON:
{"relations":[{"type":"CAUSE|SAME_ENTITY|BEFORE","source_state_key":"s1",
"target_state_key":"s2","basis":"explicit_connective|authorized_registry|explicit_temporal",
"cue_text":"exact supplied cue or null"}]}
"""

_ENUMS = {
    "kind": {"event", "state", "attitude", "proposition", "reported_proposition", "other", "UNKNOWN"},
    "attribution_mode": {"direct_speaker", "direct_quote", "indirect_report", "external_claim", "UNKNOWN"},
    "polarity": {"positive", "negative", "mixed", "UNKNOWN"},
    "modality": {"asserted", "possible", "intended", "desired", "required", "conditional", "counterfactual", "UNKNOWN"},
    "epistemic_hedge": {"none", "uncertain", "approximate", "reported", "UNKNOWN"},
    "time_precision": {"instant", "day", "month", "interval", "approximate", "season", "year", "UNKNOWN"},
    "entity_status": {"resolved", "unresolved", "conflicting", "UNKNOWN"},
}
_CUE_PATTERNS = {
    "CAUSE": re.compile(r"\b(?:because|as a result|therefore|consequently|caused|causes|causing|led to|leads to|resulted in|results in|which made|which caused)\b", re.I),
    "BEFORE": re.compile(r"\b(?:before|after|earlier than|later than|preceded|followed|later)\b", re.I),
    "SAME_ENTITY": re.compile(r"\b(?:also known as|the same (?:person|system|device)|formerly known as|that same)\b", re.I),
}
_NEG_CAUSE = re.compile(r"\b(?:not|did not|does not|no|never|without)\s+(?:cause|causes|caused|causing)\b|\bno cause\b", re.I)
_FORWARD_CAUSE = re.compile(r"\b(?:as a result|therefore|consequently|which made|which caused|caused|causes|causing|led to|leads to|resulted in|results in)\b", re.I)
_BACKWARD_CAUSE = re.compile(r"\b(?:because|due to|owing to)\b", re.I)
_MODAL_MARKERS = re.compile(r"\b(?:might|may|could|would|if|unless|must|required|plan(?:s|ned)? to|intend(?:s|ed)? to)\b", re.I)
_QUOTE_RE = re.compile(r'"[^"\n]+"|“[^”\n]+”')


@dataclass(slots=True)
class GateDecision:
    state_key: str
    admitted: bool
    reasons: list[str]


@dataclass(slots=True)
class RelationDecision:
    source_state_key: str
    target_state_key: str
    relation_type: str
    admitted: bool
    reason: str


@dataclass(slots=True)
class RouteETrace:
    first_pass_sha256: str
    first_pass_cached: bool
    gate_decisions: list[GateDecision]
    relation_decisions: list[RelationDecision]
    linker_called: bool
    linker_cached: bool
    linker_candidate_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _prompt(case_input: VisibleCaseInput) -> str:
    """Keep this byte-identical to ArmBOnePassAdapter.compile's user prompt."""
    return json.dumps({
        "case_id": case_input.case_id,
        "cutoff": case_input.cutoff,
        "visible_evidence": case_input.visible_evidence,
        "bounded_context": case_input.context_evidence,
        "entity_registry": case_input.entity_registry,
    }, indent=2, ensure_ascii=False)


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _exact_span(text: str, evidence_map: dict[str, dict[str, Any]]) -> SourceSpan | None:
    """Resolve text only when it has one exact occurrence in admitted input."""
    if not text:
        return None
    hits: list[tuple[str, int]] = []
    for evidence_id, evidence in evidence_map.items():
        content = evidence["content"]
        start = 0
        while True:
            index = content.find(text, start)
            if index < 0:
                break
            hits.append((evidence_id, index))
            start = index + 1
    if len(hits) != 1:
        return None
    evidence_id, start = hits[0]
    return SourceSpan(evidence_id, start, start + len(text), text)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _gate_blocks(
    raw_blocks: Any,
    case_input: VisibleCaseInput,
) -> tuple[list[PublicSemanticBlock], list[GateDecision], dict[str, dict[str, Any]]]:
    evidence_map = {e["evidence_id"]: e for e in [*case_input.context_evidence, *case_input.visible_evidence]}
    visible_map = evidence_map
    blocks: list[PublicSemanticBlock] = []
    decisions: list[GateDecision] = []
    seen_state: set[str] = set()
    seen_block: set[str] = set()

    if not isinstance(raw_blocks, list):
        return [], [GateDecision("UNKNOWN", False, ["blocks_not_a_list"])], evidence_map

    for raw in raw_blocks:
        if not isinstance(raw, dict):
            decisions.append(GateDecision("UNKNOWN", False, ["block_not_an_object"]))
            continue
        state_key = raw.get("state_key") if _nonempty(raw.get("state_key")) else "UNKNOWN"
        reasons: list[str] = []
        required = (
            "state_key", "block_key", "canonical_content", "predicate", "kind", "participants",
            "holder", "utterer", "attribution_mode", "polarity", "modality", "epistemic_hedge",
            "valid_time", "time_precision", "entity_status", "uncertainty", "source_spans",
        )
        for field in required:
            if field not in raw:
                reasons.append(f"missing_required_field:{field}")
        for field in ("state_key", "block_key", "canonical_content", "predicate", "holder", "utterer", "valid_time", "uncertainty"):
            if not _nonempty(raw.get(field)):
                reasons.append(f"empty_required_field:{field}")
        for field, allowed in _ENUMS.items():
            if raw.get(field) not in allowed:
                reasons.append(f"invalid_enum:{field}")
        participants = raw.get("participants")
        if not isinstance(participants, dict) or any(not _nonempty(k) or not _nonempty(v) for k, v in participants.items()):
            reasons.append("invalid_participants")
        if state_key in seen_state:
            reasons.append("duplicate_state_key")
        block_key = raw.get("block_key")
        if block_key in seen_block:
            reasons.append("duplicate_block_key")
        spans_in = raw.get("source_spans")
        if not isinstance(spans_in, list) or not spans_in:
            reasons.append("missing_source_spans")
            spans_in = []
        spans: list[SourceSpan] = []
        for source_span in spans_in:
            if not isinstance(source_span, dict) or not _nonempty(source_span.get("evidence_id")) or not _nonempty(source_span.get("text")):
                reasons.append("malformed_source_span")
                continue
            evidence_id = source_span["evidence_id"]
            text = source_span["text"]
            if evidence_id not in visible_map:
                reasons.append(f"source_not_cutoff_visible:{evidence_id}")
                continue
            if evidence_id not in evidence_map:
                reasons.append(f"source_access_unestablished:{evidence_id}")
                continue
            if _parse_time(evidence_map[evidence_id]["available_at"]) > _parse_time(case_input.cutoff):
                reasons.append(f"source_after_cutoff:{evidence_id}")
                continue
            resolved = _exact_span(text, {evidence_id: evidence_map[evidence_id]})
            if resolved is None:
                reasons.append(f"span_not_unique_exact_match:{evidence_id}")
                continue
            spans.append(resolved)
        if not spans:
            reasons.append("no_admitted_exact_support")
        if spans and raw.get("holder") in {"user", "user/narrator"} and raw.get("attribution_mode") == "direct_speaker":
            for source_span in spans:
                content = evidence_map[source_span.evidence_id]["content"]
                if any(
                    match.start() <= source_span.char_start and source_span.char_end <= match.end()
                    for match in _QUOTE_RE.finditer(content)
                ):
                    reasons.append("quoted_claim_attributed_to_narrator")
                    break
        if spans and raw.get("attribution_mode") in {"direct_quote", "indirect_report", "external_claim"}:
            holder = str(raw.get("holder", "UNKNOWN"))
            if holder != "UNKNOWN":
                cited_text = " ".join(evidence_map[s.evidence_id]["content"] for s in spans)
                if holder.casefold() not in cited_text.casefold():
                    reasons.append("reported_holder_not_anchored_in_cited_source")
        if raw.get("kind") == "UNKNOWN" or raw.get("predicate") == "UNKNOWN":
            # Explicit UNKNOWN is a legal abstention under the contract.
            pass
        if raw.get("modality") == "asserted" and _MODAL_MARKERS.search(str(raw.get("canonical_content", ""))):
            reasons.append("modal_or_conditional_marker_promoted_to_asserted")

        admitted = not reasons
        decisions.append(GateDecision(str(state_key), admitted, reasons))
        if not admitted:
            continue
        seen_state.add(state_key)
        seen_block.add(block_key)
        max_available = max(evidence_map[s.evidence_id]["available_at"] for s in spans)
        if max_available > case_input.cutoff:
            decisions[-1].admitted = False
            decisions[-1].reasons.append("evidence_after_cutoff")
            continue
        try:
            support_count = raw.get("independent_support_count", 1)
            if not isinstance(support_count, int) or support_count < 1 or support_count > 1:
                raise ValueError("invalid_support_count")
            block = PublicSemanticBlock(
                block_id=f"{case_input.case_id}_{block_key}",
                state_id=f"{case_input.case_id}_{state_key}",
                state_available_at=max_available,
                canonical_content=raw["canonical_content"],
                predicate=raw["predicate"],
                kind=raw["kind"],
                participants=dict(participants),
                holder=raw["holder"],
                utterer=raw["utterer"],
                attribution_mode=raw["attribution_mode"],
                polarity=raw["polarity"],
                modality=raw["modality"],
                epistemic_hedge=raw["epistemic_hedge"],
                valid_time=raw["valid_time"],
                time_precision=raw["time_precision"],
                entity_status=raw["entity_status"],
                uncertainty=raw["uncertainty"],
                independent_support_count=support_count,
                source_spans=spans,
                lineage_id=f"route-e-{case_input.case_id}-{block_key}",
                compiler_version="route-e-v0.2",
            )
        except (KeyError, TypeError, ValueError) as exc:
            decisions[-1].admitted = False
            decisions[-1].reasons.append(f"public_contract_conversion_failed:{type(exc).__name__}")
            continue
        blocks.append(block)
    return blocks, decisions, evidence_map


def _screen_relations(
    raw_relations: Any,
    raw_blocks: Any,
    admitted_blocks: list[PublicSemanticBlock],
    evidence_map: dict[str, dict[str, Any]],
    registry: dict[str, str],
) -> tuple[list[dict[str, Any]], list[RelationDecision]]:
    evidence_order = {evidence_id: index for index, evidence_id in enumerate(evidence_map)}
    admitted_keys = {b.state_id.rsplit("_", 1)[-1] for b in admitted_blocks}
    admitted_by_key = {b.state_id.rsplit("_", 1)[-1]: b for b in admitted_blocks}
    decisions: list[RelationDecision] = []

    if len(admitted_blocks) < 2:
        return [], decisions

    raw_candidates: list[dict[str, Any]] = []

    # 1. Deterministic candidate generation from admitted blocks + visible evidence + authorized registry
    ordered_blocks = sorted(
        admitted_blocks,
        key=lambda b: (
            min((evidence_order[s.evidence_id] for s in b.source_spans if s.evidence_id in evidence_order), default=0),
            min((s.char_start for s in b.source_spans if s.evidence_id in evidence_order), default=0),
        ),
    )

    for i in range(len(ordered_blocks)):
        for j in range(i + 1, len(ordered_blocks)):
            b1 = ordered_blocks[i]
            b2 = ordered_blocks[j]
            key1 = b1.state_id.rsplit("_", 1)[-1]
            key2 = b2.state_id.rsplit("_", 1)[-1]
            eids1 = {s.evidence_id for s in b1.source_spans if s.evidence_id in evidence_order}
            eids2 = {s.evidence_id for s in b2.source_spans if s.evidence_id in evidence_order}
            if not eids1 or not eids2:
                continue
            min_dist = min(abs(evidence_order[a] - evidence_order[b]) for a in eids1 for b in eids2)
            if min_dist > 1:
                continue

            scoped_eids = eids1 | eids2
            scoped_map = {eid: evidence_map[eid] for eid in scoped_eids if eid in evidence_map}

            # A. SAME_ENTITY via authorized registry
            src_values = set(map(str, b1.participants.values()))
            tgt_values = set(map(str, b2.participants.values()))
            mapped_src = {registry[val] for val in src_values if val in registry and _nonempty(registry[val])}
            mapped_tgt = {registry[val] for val in tgt_values if val in registry and _nonempty(registry[val])}
            if mapped_src & mapped_tgt:
                raw_candidates.append({
                    "type": "SAME_ENTITY",
                    "source_state_key": key1,
                    "target_state_key": key2,
                    "basis": "authorized_registry",
                    "cue_text": None,
                    "cue_span": None,
                })

            # B. SAME_ENTITY via explicit cue
            for eid in sorted(scoped_eids, key=lambda e: evidence_order[e]):
                content = evidence_map[eid]["content"]
                for m in _CUE_PATTERNS["SAME_ENTITY"].finditer(content):
                    cue_text = m.group(0)
                    cue_span = _exact_span(cue_text, scoped_map)
                    if cue_span:
                        raw_candidates.append({
                            "type": "SAME_ENTITY",
                            "source_state_key": key1,
                            "target_state_key": key2,
                            "basis": "explicit_connective",
                            "cue_text": cue_text,
                            "cue_span": cue_span.to_dict(),
                        })

            # C. CAUSE (Forward and Backward)
            # Forward: key1 -> key2
            for eid in sorted(eids2, key=lambda e: evidence_order[e]):
                content = evidence_map[eid]["content"]
                for m in _FORWARD_CAUSE.finditer(content):
                    start, end = m.span()
                    prefix = content[max(0, start - 20):start].lower()
                    surrounding = content[max(0, start - 15):min(len(content), end + 15)].lower()
                    if re.search(r"\b(?:not|did not|does not|no|never|without)\s+$", prefix) or "no cause" in surrounding or "did not cause" in surrounding:
                        continue
                    cue_text = m.group(0)
                    cue_span = _exact_span(cue_text, scoped_map)
                    if cue_span:
                        raw_candidates.append({
                            "type": "CAUSE",
                            "source_state_key": key1,
                            "target_state_key": key2,
                            "basis": "explicit_connective",
                            "cue_text": cue_text,
                            "cue_span": cue_span.to_dict(),
                        })

            # In same evidence item: also check forward cause between spans
            if eids1 & eids2:
                same_eid = next(iter(eids1 & eids2))
                content = evidence_map[same_eid]["content"]
                for m in _FORWARD_CAUSE.finditer(content):
                    start, end = m.span()
                    prefix = content[max(0, start - 20):start].lower()
                    surrounding = content[max(0, start - 15):min(len(content), end + 15)].lower()
                    if re.search(r"\b(?:not|did not|does not|no|never|without)\s+$", prefix) or "no cause" in surrounding or "did not cause" in surrounding:
                        continue
                    cue_text = m.group(0)
                    cue_span = _exact_span(cue_text, scoped_map)
                    if cue_span:
                        raw_candidates.append({
                            "type": "CAUSE",
                            "source_state_key": key1,
                            "target_state_key": key2,
                            "basis": "explicit_connective",
                            "cue_text": cue_text,
                            "cue_span": cue_span.to_dict(),
                        })

            # Backward cause: "because", "due to", "owing to" -> key2 (cause) -> key1 (effect)
            for eid in sorted(scoped_eids, key=lambda e: evidence_order[e]):
                content = evidence_map[eid]["content"]
                for m in _BACKWARD_CAUSE.finditer(content):
                    start, end = m.span()
                    prefix = content[max(0, start - 20):start].lower()
                    if re.search(r"\b(?:not|did not|does not|no|never|without)\s+$", prefix):
                        continue
                    cue_text = m.group(0)
                    cue_span = _exact_span(cue_text, scoped_map)
                    if cue_span:
                        raw_candidates.append({
                            "type": "CAUSE",
                            "source_state_key": key2,
                            "target_state_key": key1,
                            "basis": "explicit_connective",
                            "cue_text": cue_text,
                            "cue_span": cue_span.to_dict(),
                        })

            # D. BEFORE
            if eids1 & eids2:
                # Same evidence record: b1 before b2
                same_eid = next(iter(eids1 & eids2))
                content = evidence_map[same_eid]["content"]
                for m in _CUE_PATTERNS["BEFORE"].finditer(content):
                    cue_text = m.group(0)
                    cue_span = _exact_span(cue_text, scoped_map)
                    if cue_span:
                        raw_candidates.append({
                            "type": "BEFORE",
                            "source_state_key": key1,
                            "target_state_key": key2,
                            "basis": "explicit_temporal",
                            "cue_text": cue_text,
                            "cue_span": cue_span.to_dict(),
                        })
            else:
                # Separate records: temporal cue must be in later record eids2 (e.g. "later", "afterwards", "after")
                for eid in sorted(eids2, key=lambda e: evidence_order[e]):
                    content = evidence_map[eid]["content"]
                    for m in _CUE_PATTERNS["BEFORE"].finditer(content):
                        cue_text = m.group(0)
                        if cue_text.lower() in {"later", "afterwards", "after", "later than"}:
                            cue_span = _exact_span(cue_text, scoped_map)
                            if cue_span:
                                raw_candidates.append({
                                    "type": "BEFORE",
                                    "source_state_key": key1,
                                    "target_state_key": key2,
                                    "basis": "explicit_temporal",
                                    "cue_text": cue_text,
                                    "cue_span": cue_span.to_dict(),
                                })

    # 2. Screen B's first-pass proposals if provided
    allowed_bases = {
        "CAUSE": {"explicit_connective"},
        "BEFORE": {"explicit_temporal"},
        "SAME_ENTITY": {"authorized_registry", "explicit_connective"},
    }
    if isinstance(raw_relations, list):
        for relation in raw_relations:
            if not isinstance(relation, dict):
                decisions.append(RelationDecision("UNKNOWN", "UNKNOWN", "UNKNOWN", False, "relation_not_an_object"))
                continue
            rel_type = str(relation.get("type", "UNKNOWN"))
            src = str(relation.get("source_state_key", "UNKNOWN"))
            tgt = str(relation.get("target_state_key", "UNKNOWN"))
            basis = str(relation.get("basis", ""))
            cue_text = relation.get("cue_text")
            reason = ""
            if rel_type not in _CUE_PATTERNS:
                reason = "unsupported_relation_type"
            elif src == tgt or src not in admitted_keys or tgt not in admitted_keys:
                reason = "endpoint_not_admitted_or_self_link"
            elif basis not in allowed_bases.get(rel_type, set()):
                reason = "invalid_relation_basis"

            cue_span: SourceSpan | None = None
            if not reason and rel_type == "SAME_ENTITY" and basis == "authorized_registry":
                src_values = set(map(str, admitted_by_key[src].participants.values()))
                tgt_values = set(map(str, admitted_by_key[tgt].participants.values()))
                mapped_src = {registry[val] for val in src_values if val in registry and _nonempty(registry[val])}
                mapped_tgt = {registry[val] for val in tgt_values if val in registry and _nonempty(registry[val])}
                if not (mapped_src & mapped_tgt):
                    reason = "registry_does_not_authorize_identity"
            elif not reason:
                if not _nonempty(cue_text) or not _CUE_PATTERNS[rel_type].search(cue_text):
                    reason = "missing_or_wrong_type_relation_cue"
                else:
                    src_eids = {s.evidence_id for s in admitted_by_key[src].source_spans}
                    tgt_eids = {s.evidence_id for s in admitted_by_key[tgt].source_spans}
                    scoped = {eid: evidence_map[eid] for eid in (src_eids | tgt_eids) if eid in evidence_map}
                    cue_span = _exact_span(cue_text, scoped)
                    if cue_span is None:
                        reason = "relation_cue_not_unique_exact_source_match"
                    elif cue_span.evidence_id not in (src_eids | tgt_eids):
                        reason = "cue_not_on_endpoint_support"
                    elif not src_eids or not tgt_eids:
                        reason = "candidate_endpoint_has_no_source_records"
                    elif min(abs(evidence_order[a] - evidence_order[b]) for a in src_eids for b in tgt_eids) > 1:
                        reason = "candidate_endpoint_records_not_adjacent"
                    elif rel_type == "CAUSE":
                        content = evidence_map[cue_span.evidence_id]["content"]
                        prefix = content[max(0, cue_span.char_start - 20):cue_span.char_start].lower()
                        surrounding = content[max(0, cue_span.char_start - 15):min(len(content), cue_span.char_end + 15)].lower()
                        if re.search(r"\b(?:not|did not|does not|no|never|without)\s+$", prefix) or "no cause" in surrounding or "did not cause" in surrounding:
                            reason = "negated_causal_cue"

            if reason:
                decisions.append(RelationDecision(src, tgt, rel_type, False, reason))
            else:
                raw_candidates.append({
                    "type": rel_type,
                    "source_state_key": src,
                    "target_state_key": tgt,
                    "basis": basis,
                    "cue_text": cue_text,
                    "cue_span": cue_span.to_dict() if cue_span else None,
                })

    # 3. Deduplicate candidates by (type, source, target)
    seen_cand: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for c in raw_candidates:
        key = (c["type"], c["source_state_key"], c["target_state_key"])
        if key not in seen_cand:
            seen_cand.add(key)
            deduped.append(c)

    # 4. Transitive shortcut suppression for CAUSE (e.g. A->B and B->C forbids A->C)
    cause_pairs = {(c["source_state_key"], c["target_state_key"]) for c in deduped if c["type"] == "CAUSE"}
    pruned: list[dict[str, Any]] = []
    for c in deduped:
        if c["type"] == "CAUSE":
            src = c["source_state_key"]
            tgt = c["target_state_key"]
            has_intermediate = any(
                (src, inter) in cause_pairs and (inter, tgt) in cause_pairs
                for inter in admitted_keys
                if inter not in (src, tgt)
            )
            if has_intermediate:
                decisions.append(RelationDecision(src, tgt, "CAUSE", False, "transitive_shortcut_forbidden"))
                continue
        pruned.append(c)

    # 5. Cycle suppression and path > 2 hops check
    adjacency: dict[str, list[str]] = {}
    for candidate in pruned:
        if candidate["type"] == "CAUSE":
            adjacency.setdefault(candidate["source_state_key"], []).append(candidate["target_state_key"])
    for source in list(adjacency.keys()):
        frontier = [(source, 0, {source})]
        while frontier:
            node, depth, seen = frontier.pop()
            for target in adjacency.get(node, []):
                if target in seen or depth >= 2:
                    invalid = [c for c in pruned if c["source_state_key"] == node and c["target_state_key"] == target and c["type"] == "CAUSE"]
                    for _ in invalid:
                        decisions.append(RelationDecision(node, target, "CAUSE", False, "cycle_or_path_over_two_hops"))
                    pruned = [c for c in pruned if c not in invalid]
                else:
                    frontier.append((target, depth + 1, {*seen, target}))

    # 6. Candidate pair limit (cap at 8)
    candidates: list[dict[str, Any]] = []
    for idx, c in enumerate(pruned):
        if idx < 8:
            candidates.append(c)
            decisions.append(RelationDecision(c["source_state_key"], c["target_state_key"], c["type"], True, "screened_source_cued_candidate"))
        else:
            decisions.append(RelationDecision(c["source_state_key"], c["target_state_key"], c["type"], False, "candidate_pair_limit_exceeded"))

    return candidates, decisions


def _admit_linker_output(
    raw_relations: Any,
    candidates: list[dict[str, Any]],
    admitted_blocks: list[PublicSemanticBlock],
    case_id: str,
    decisions: list[RelationDecision],
) -> list[PublicRelation]:
    states = {b.state_id.rsplit("_", 1)[-1]: b for b in admitted_blocks}
    out: list[PublicRelation] = []
    if not isinstance(raw_relations, list):
        for candidate in candidates:
            decisions.append(RelationDecision(candidate["source_state_key"], candidate["target_state_key"], candidate["type"], False, "linker_output_not_a_list"))
        return out

    seen: set[tuple[str, str, str]] = set()
    for raw in raw_relations:
        if not isinstance(raw, dict):
            continue
        rel_type = str(raw.get("type", "UNKNOWN"))
        src = str(raw.get("source_state_key", "UNKNOWN"))
        tgt = str(raw.get("target_state_key", "UNKNOWN"))
        candidate = next((c for c in candidates if (c["type"], c["source_state_key"], c["target_state_key"]) == (rel_type, src, tgt)), None)
        if candidate is None or (rel_type, src, tgt) in seen:
            decisions.append(RelationDecision(str(src), str(tgt), str(rel_type), False, "linker_changed_or_added_candidate"))
            continue

        raw_cue = raw.get("cue_text")
        cand_cue = candidate.get("cue_text")
        if cand_cue and raw_cue and raw_cue != "null" and str(raw_cue).strip().lower() != str(cand_cue).strip().lower():
            decisions.append(RelationDecision(str(src), str(tgt), str(rel_type), False, "linker_changed_or_added_candidate"))
            continue

        if rel_type == "BEFORE" and raw.get("traversal_allowed", False):
            decisions.append(RelationDecision(src, tgt, rel_type, False, "before_traversal_forbidden"))
            continue

        basis = raw.get("basis")
        required_basis = {"CAUSE": {"explicit_connective"}, "BEFORE": {"explicit_temporal"}, "SAME_ENTITY": {"authorized_registry", "explicit_connective"}}[rel_type]
        candidate_basis = candidate["basis"]
        if basis not in required_basis or basis != candidate_basis:
            decisions.append(RelationDecision(src, tgt, rel_type, False, "invalid_relation_basis"))
            continue

        cue_obj = SourceSpan(**candidate["cue_span"]) if candidate["cue_span"] else None
        out.append(PublicRelation(
            type=rel_type,
            direction="directed",
            source_state_id=states[src].state_id,
            target_state_id=states[tgt].state_id,
            basis=basis,
            cue_span=cue_obj,
            traversal_allowed=rel_type in {"CAUSE", "SAME_ENTITY"},
        ))
        seen.add((rel_type, src, tgt))
        decisions.append(RelationDecision(src, tgt, rel_type, True, "admitted_screened_relation"))

    for candidate in candidates:
        key = (candidate["type"], candidate["source_state_key"], candidate["target_state_key"])
        if key not in seen:
            decisions.append(RelationDecision(key[1], key[2], key[0], False, "linker_abstained"))
    return out


class RouteEAdapter(BaseCompilerAdapter):
    """B-compatible one-pass compiler with fail-closed admission gates."""

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        super().__init__(arm_id="E")
        self.client = BenchmarkLLMClient(cache_dir=cache_dir)
        self.last_trace: RouteETrace | None = None

    def compile(self, case_input: VisibleCaseInput) -> PredictionRecord:
        prediction, _trace = self.compile_with_trace(case_input)
        self.last_trace = _trace
        return prediction

    def compile_with_trace(self, case_input: VisibleCaseInput) -> tuple[PredictionRecord, RouteETrace]:
        user_prompt = _prompt(case_input)
        first = self.client.generate_structured_json(prompt=user_prompt, system_instruction=SYSTEM_PROMPT)
        raw = first.content
        raw_blocks = raw.get("blocks", [])
        blocks, gate_decisions, evidence_map = _gate_blocks(raw_blocks, case_input)
        candidates, relation_decisions = _screen_relations(
            raw.get("relations", []), raw_blocks, blocks, evidence_map, case_input.entity_registry
        )

        linker_called = bool(candidates)
        linker_cached = False
        relations: list[PublicRelation] = []
        linker_prompt_tokens = linker_completion_tokens = linker_total_tokens = 0
        linker_latency = 0.0
        if candidates:
            summaries = [
                {"state_key": b.state_id.rsplit("_", 1)[-1], "canonical_content": b.canonical_content,
                 "predicate": b.predicate, "holder": b.holder, "valid_time": b.valid_time}
                for b in blocks
            ]
            prompt = json.dumps({
                "case_id": case_input.case_id,
                "cutoff": case_input.cutoff,
                "admitted_blocks": summaries,
                "screened_pairs": candidates,
            }, indent=2, ensure_ascii=False)
            linked = self.client.generate_structured_json(prompt=prompt, system_instruction=LINKER_SYSTEM_PROMPT)
            linker_cached = linked.cached
            linker_prompt_tokens = linked.prompt_tokens
            linker_completion_tokens = linked.completion_tokens
            linker_total_tokens = linked.total_tokens
            linker_latency = linked.latency_ms
            relations = _admit_linker_output(
                linked.content.get("relations", []), candidates, blocks, case_input.case_id, relation_decisions
            )

        manifest_material = f"{SYSTEM_PROMPT}\n{LINKER_SYSTEM_PROMPT}\n{user_prompt}"
        prediction = PredictionRecord(
            case_id=case_input.case_id,
            cutoff=case_input.cutoff,
            arm_id="E",
            manifest_id=hashlib.sha256(manifest_material.encode("utf-8")).hexdigest(),
            blocks=blocks,
            relations=relations,
            call_count=1 + int(linker_called),
            prompt_tokens=first.prompt_tokens + linker_prompt_tokens,
            completion_tokens=first.completion_tokens + linker_completion_tokens,
            total_tokens=first.total_tokens + linker_total_tokens,
            latency_ms=first.latency_ms + linker_latency,
        )
        trace = RouteETrace(
            first_pass_sha256=sha256_text(json.dumps(raw, ensure_ascii=False, sort_keys=True)),
            first_pass_cached=first.cached,
            gate_decisions=gate_decisions,
            relation_decisions=relation_decisions,
            linker_called=linker_called,
            linker_cached=linker_cached,
            linker_candidate_count=len(candidates),
        )
        return prediction, trace
