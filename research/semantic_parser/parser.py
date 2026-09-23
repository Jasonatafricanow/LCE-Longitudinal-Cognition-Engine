"""SemanticParser class for AGY Semantic Parsing v0.1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research.semantic_annotation.schema import (
    FORBIDDEN_LABELS,
    FROZEN_PREDICATE_MAP,
    GRAPH_ADMISSIBLE_EVIDENCE_STATUSES,
    ROLE_VOCABULARY,
    ArgumentMention,
    AttributionMode,
    EpistemicHedge,
    EvidenceStatus,
    ModalityType,
    PolarityType,
    PredicateNormalizationRule,
    PredicateSpec,
    RelationProvenance,
    RelationType,
    SemanticAnnotationDocument,
    SemanticRelation,
    SemanticUnit,
    SourceSpan,
    TemporalAnchorType,
    TemporalAnchoring,
    UnitKind,
    UnitProvenance,
)
from research.semantic_parser.client import GeminiClient
from research.semantic_parser.prompts import (
    SYSTEM_INSTRUCTION,
    format_few_shot_block,
    format_user_prompt,
    load_dev_few_shots,
)


class SemanticParser:
    """AGY Semantic Parser converting raw evidence and blocks into SemanticAnnotationDocument."""

    def __init__(
        self,
        client: GeminiClient | None = None,
        dev_jsonl_path: Path | str | None = None,
        num_few_shots: int = 8,
    ) -> None:
        self.client = client or GeminiClient()
        self.dev_jsonl_path = dev_jsonl_path or Path("research/benchmarks/semantic_annotation_v0_1/dev.jsonl")
        
        # Load calibration few-shots from dev
        all_few_shots = load_dev_few_shots(self.dev_jsonl_path)
        # Select balanced subset of few-shots to keep prompt compact and focused
        representative_ids = [
            "gold_dev_01",  # asserted past event with relative anchor
            "gold_dev_07",  # negative polarity over state
            "gold_dev_09",  # SAME_ENTITY mention-level coreference
            "gold_dev_12",  # explicit CAUSE with 'therefore'
            "gold_dev_13",  # CONDITION with 'If'
            "gold_dev_15",  # longitudinal shift across years (BEFORE)
            "gold_dev_17",  # nested attitude (intended + think)
            "gold_dev_20",  # NO_RELATION control
        ]
        chosen = [ex for ex in all_few_shots if ex["case_id"] in representative_ids][:num_few_shots]
        self.few_shot_text = format_few_shot_block(chosen) if chosen else ""

    def sanitize_input(self, case_dict: dict[str, Any]) -> dict[str, Any]:
        """Strip all gold annotations, families, trap descriptions, and rationales."""
        return {
            "case_id": case_dict["case_id"],
            "raw_evidence": case_dict["raw_evidence"],
            "semantic_blocks": case_dict["semantic_blocks"],
            "cutoff_time": case_dict.get("cutoff_time", "2026-09-23T00:00:00Z"),
        }

    def _snap_span(self, full_text: str, target_text: str, search_start: int = 0, search_end: int | None = None) -> SourceSpan:
        """Find substring within text slice or full text and return SourceSpan."""
        if search_end is None:
            search_end = len(full_text)
        idx = full_text.find(target_text, search_start, search_end)
        if idx == -1:
            # Fallback to whole text
            idx = full_text.find(target_text)
            if idx == -1:
                # Approximate fallback
                return SourceSpan(char_start=search_start, char_end=min(search_start + len(target_text), len(full_text)), text=target_text)
        return SourceSpan(char_start=idx, char_end=idx + len(target_text), text=target_text)

    def parse_case(self, case_dict: dict[str, Any]) -> SemanticAnnotationDocument:
        """Parse a case input and return a validated SemanticAnnotationDocument."""
        sanitized = self.sanitize_input(case_dict)
        raw_ev = sanitized["raw_evidence"][0]
        raw_text = raw_ev["content"]
        raw_ev_id = raw_ev["evidence_id"]
        block_id = sanitized["semantic_blocks"][0]["block_id"]
        case_id = sanitized["case_id"]

        prompt = format_user_prompt(sanitized, self.few_shot_text)
        response_json = self.client.generate_json(prompt, system_instruction=SYSTEM_INSTRUCTION)

        # Post-process and construct Pydantic document
        units_raw = response_json.get("units", [])
        relations_raw = response_json.get("relations", [])

        units: list[SemanticUnit] = []
        mention_map: dict[str, ArgumentMention] = {}

        for u_idx, u in enumerate(units_raw, 1):
            uid = u.get("annotation_id", f"u{u_idx}")
            
            # Unit source span
            u_span_text = u.get("source_span", {}).get("text", raw_text)
            u_span = self._snap_span(raw_text, u_span_text)

            # Predicate
            p_dict = u.get("predicate", {})
            surf_pred = p_dict.get("surface_predicate", "act").strip()
            norm_pred = p_dict.get("normalized_predicate", surf_pred.lower()).strip()
            norm_rule = p_dict.get("normalization_rule", "exact_surface")
            
            # Cognition label guard
            if norm_pred.upper() in FORBIDDEN_LABELS:
                norm_pred = surf_pred.lower()

            try:
                rule_enum = PredicateNormalizationRule(norm_rule)
            except ValueError:
                rule_enum = PredicateNormalizationRule.EXACT_SURFACE

            # Strictly enforce rule mechanics to satisfy PredicateSpec model validator
            if rule_enum == PredicateNormalizationRule.EXACT_SURFACE:
                norm_pred = surf_pred.lower()
            elif rule_enum == PredicateNormalizationRule.COMPOUND_LOWER:
                norm_surface = norm_pred.replace("_", " ")
                if norm_surface in surf_pred.lower():
                    surf_pred = norm_surface
                norm_pred = surf_pred.lower().replace(" ", "_")
            elif rule_enum == PredicateNormalizationRule.FROZEN_MAP:
                if surf_pred.lower() in FROZEN_PREDICATE_MAP:
                    norm_pred = FROZEN_PREDICATE_MAP[surf_pred.lower()]
                else:
                    rule_enum = PredicateNormalizationRule.EXACT_SURFACE
                    norm_pred = surf_pred.lower()
            elif rule_enum == PredicateNormalizationRule.LEMMA:
                if not norm_pred:
                    norm_pred = surf_pred.lower()

            pred_spec = PredicateSpec(
                surface_predicate=surf_pred,
                normalized_predicate=norm_pred,
                normalization_rule=rule_enum,
            )

            # Kind
            try:
                kind_enum = UnitKind(u.get("kind", "event"))
            except ValueError:
                kind_enum = UnitKind.EVENT

            # Polarity
            try:
                pol_enum = PolarityType(u.get("polarity", "positive"))
            except ValueError:
                pol_enum = PolarityType.POSITIVE

            # Modality
            try:
                mod_enum = ModalityType(u.get("modality", "asserted"))
            except ValueError:
                mod_enum = ModalityType.ASSERTED

            # Epistemic Hedge
            try:
                hdg_enum = EpistemicHedge(u.get("epistemic_hedge", "none"))
            except ValueError:
                hdg_enum = EpistemicHedge.NONE

            # Attribution Mode
            try:
                att_enum = AttributionMode(u.get("attribution_mode", "direct_speaker"))
            except ValueError:
                att_enum = AttributionMode.DIRECT_SPEAKER

            # Evidence Status
            try:
                ev_enum = EvidenceStatus(u.get("evidence_status", "explicit"))
            except ValueError:
                ev_enum = EvidenceStatus.EXPLICIT

            # Temporal Anchoring
            t_dict = u.get("temporal_anchoring", {})
            try:
                t_anchor_enum = TemporalAnchorType(t_dict.get("anchor_type", "exact"))
            except ValueError:
                t_anchor_enum = TemporalAnchorType.EXACT

            temporal_anchoring = TemporalAnchoring(
                normalized_value=t_dict.get("normalized_value", "2026-09-23"),
                anchor_type=t_anchor_enum,
                source_expression=t_dict.get("source_expression"),
                reference_anchor=t_dict.get("reference_anchor"),
            )

            # Arguments
            args: dict[str, ArgumentMention] = {}
            for r_idx, (role, arg_data) in enumerate(u.get("arguments", {}).items(), 1):
                mid = arg_data.get("mention_id", f"m_{uid}_{r_idx}")
                m_text = arg_data.get("text", "")
                if not m_text:
                    continue

                role_clean = role.lower().strip()
                if role_clean not in ROLE_VOCABULARY:
                    if any(t in role_clean for t in ("time", "date")):
                        role_clean = "time"
                    elif any(a in role_clean for a in ("actor", "agent", "user")):
                        role_clean = "actor"
                    elif any(t in role_clean for t in ("target", "object")):
                        role_clean = "target"
                    elif any(r in role_clean for r in ("reason", "cause")):
                        role_clean = "reason"
                    elif any(r in role_clean for r in ("result", "outcome")):
                        role_clean = "result"
                    elif any(p in role_clean for p in ("place", "location")):
                        role_clean = "place"
                    elif "purpose" in role_clean:
                        role_clean = "purpose"
                    elif "experiencer" in role_clean:
                        role_clean = "experiencer"
                    elif "stimulus" in role_clean:
                        role_clean = "stimulus"
                    elif "topic" in role_clean:
                        role_clean = "topic"
                    else:
                        role_clean = "theme"

                # Snap mention span strictly inside unit span!
                m_span = self._snap_span(raw_text, m_text, u_span.char_start, u_span.char_end)
                mention = ArgumentMention(
                    mention_id=mid,
                    role=role_clean,
                    text=m_text,
                    source_span=m_span,
                    entity_ref=arg_data.get("entity_ref"),
                )
                args[role_clean] = mention
                mention_map[mid] = mention

            units.append(
                SemanticUnit(
                    annotation_id=uid,
                    provenance=UnitProvenance(raw_evidence_id=raw_ev_id, semantic_block_id=block_id),
                    source_span=u_span,
                    kind=kind_enum,
                    predicate=pred_spec,
                    arguments=args,
                    polarity=pol_enum,
                    modality=mod_enum,
                    epistemic_hedge=hdg_enum,
                    holder_ref=u.get("holder_ref", "user"),
                    attribution_mode=att_enum,
                    temporal_anchoring=temporal_anchoring,
                    evidence_status=ev_enum,
                    confidence=float(u.get("confidence", 1.0)),
                )
            )

        # Relations
        relations: list[SemanticRelation] = []
        u_ids = {u.annotation_id for u in units}

        for r_idx, r in enumerate(relations_raw, 1):
            rid = r.get("relation_id", f"rel_{r_idx:02d}")
            src_id = r.get("source_id", "")
            tgt_id = r.get("target_id", "")
            r_type_str = r.get("relation_type", "NO_RELATION")

            # Cognition label guard
            if r_type_str.upper() in FORBIDDEN_LABELS:
                r_type_str = "BEFORE"

            try:
                r_type_enum = RelationType(r_type_str)
            except ValueError:
                r_type_enum = RelationType.NO_RELATION

            # Evidence status
            try:
                rev_enum = EvidenceStatus(r.get("evidence_status", "explicit"))
            except ValueError:
                rev_enum = EvidenceStatus.EXPLICIT

            # Supporting spans
            s_spans = []
            for sp_data in r.get("supporting_spans", []):
                sp_text = sp_data.get("text", "")
                if sp_text and sp_text in raw_text:
                    s_spans.append(self._snap_span(raw_text, sp_text))

            # Validate endpoints based on relation type
            if r_type_enum == RelationType.SAME_ENTITY:
                if src_id not in mention_map or tgt_id not in mention_map:
                    continue  # drop invalid coreference endpoint
                src_m = mention_map[src_id]
                tgt_m = mention_map[tgt_id]
                # Reject reflexive self-loops
                if src_m.source_span and tgt_m.source_span:
                    if (src_m.source_span.char_start == tgt_m.source_span.char_start and
                        src_m.source_span.char_end == tgt_m.source_span.char_end):
                        continue
            else:
                if src_id not in u_ids or tgt_id not in u_ids:
                    continue

            relations.append(
                SemanticRelation(
                    relation_id=rid,
                    source_id=src_id,
                    target_id=tgt_id,
                    relation_type=r_type_enum,
                    evidence_status=rev_enum,
                    confidence=float(r.get("confidence", 1.0)),
                    provenance=RelationProvenance(raw_evidence_id=raw_ev_id, semantic_block_id=block_id),
                    supporting_spans=s_spans,
                )
            )

        return SemanticAnnotationDocument(
            document_id=f"pred_doc_{case_id}",
            cutoff_time=sanitized.get("cutoff_time", "2026-09-23T00:00:00Z"),
            units=units,
            relations=relations,
        )
