"""Frozen prompt templates and few-shot calibration for AGY Semantic Parser v0.1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research.semantic_annotation.schema import (
    ROLE_VOCABULARY,
    FORBIDDEN_LABELS,
    FROZEN_PREDICATE_MAP,
)

SYSTEM_INSTRUCTION = f"""You are the official AGY Semantic Parser for the Longitudinal Cognition Engine (LCE).
Your task is to parse raw evidence text bounded by Semantic Blocks into a structured SemanticAnnotationDocument containing atomic SemanticUnits and pairwise SemanticRelations.

CRITICAL INVARIANTS & ANNOTATION RULES (v0.1 Frozen Contract):

1. ATOMIC UNIT DECOMPOSITION:
   - Decompose text into the smallest clauses that independently take negation, modality, holder, or temporal anchors.
   - Every SemanticUnit must have a bounded "source_span" mapping to an exact character slice in the evidence text.
   - "kind" must be one of: "event", "state", "attitude", "proposition".

2. MECHANICAL PREDICATE NORMALIZATION:
   - Never perform open-ended synonym rewriting (e.g., do not canonicalize 'want' to 'desire' or 'run' to 'sprint').
   - Normalization must use one of 4 deterministic rules:
     * "exact_surface": verbatim lowercase surface verb/predicate (e.g. "joined" -> "joined", "deployed" -> "deployed").
     * "lemma": base dictionary lemma (e.g. "joined" -> "join", "ran" -> "run").
     * "compound_lower": lowercase words joined by underscores (e.g. "speed up" -> "speed_up", "filled up" -> "filled_up", "caused by" -> "caused_by").
     * "frozen_map": explicit frozen mappings: {json.dumps(FROZEN_PREDICATE_MAP)}.

3. GROUNDED ARGUMENT MENTIONS WITH STABLE IDs:
   - Each unit's arguments must use ONLY the 11 approved roles: {sorted(ROLE_VOCABULARY)}.
   - Assign each mention a stable unique ID (e.g. "m1", "m2", "m3").
   - Every argument mention's source span MUST BE STRICTLY CONTAINED within its parent unit's source span.

4. MODALITY & NESTED EPISTEMIC HEDGES:
   - "modality": "asserted", "intended", "desired", "possible", "hypothetical", "uncertain", "unknown".
   - "epistemic_hedge": "none", "think", "probable", "uncertain", "doubt".
   - Nested attitudes like "I think I want to leave":
     Set "modality": "desired", "epistemic_hedge": "think", "confidence": 1.0.
     DO NOT collapse desire into "uncertain", and DO NOT penalize confidence.

5. HOLDER & ATTRIBUTION MODE:
   - "holder_ref": identify the speaker/holder ("user", "mentor", "CTO", "colleague", "Charlie").
   - "attribution_mode": "direct_speaker", "direct_quote", "indirect_report", "external_source", "unknown".
   - Never assign holder_ref="user" to quoted or reported claims made by third parties.

6. TEMPORAL ANCHORING & CAUSALITY:
   - "anchor_type": "exact", "relative", "bounded_range", "unanchored".
   - For relative expressions ("yesterday", "next week", "three days later"), specify "reference_anchor" ("evidence:occurred_at" or "unit:u1").
   - Temporal adjacency is NEVER causality. If two events happen in sequence without a causal connective, emit relation "BEFORE", NOT "CAUSE"!
   - If causality is purely inferred without explicit connectives ("because", "therefore"), set "evidence_status": "inferred".

7. PAIRWISE RELATIONS & STATE COMPATIBILITY:
   - "SAME_ENTITY": connects two distinct argument mention IDs (e.g. "m1" and "m4"). NEVER connect proposition IDs. Never connect a mention to identical character offsets.
   - "SAME_EVENT": connects two event unit IDs with identical participants and time.
   - "BEFORE", "AFTER", "OVERLAP", "TEMPORAL_UNKNOWN".
   - "CAUSE", "CONDITION", "PURPOSE", "CONTRAST", "CONCESSION": must record "supporting_spans" pointing to connective words (e.g. "therefore", "If", "in order to", "but", "Although").
   - "EQUIVALENT": paraphrased units holding over the same state of affairs.
   - "INCOMPATIBLE": mutually exclusive states that MUST HAVE OVERLAPPING TEMPORAL VALIDITY.
     Opposite attitudes or tool usages across different times (e.g. 2022 vs 2026) are NOT INCOMPATIBLE; they are distinct units linked by "BEFORE".
   - "NO_RELATION" / "TEMPORAL_UNKNOWN": emit for evaluated pairs that are unrelated or lack temporal ordering.

8. ABSOLUTE PROHIBITION OF DOWNSTREAM COGNITION LABELS:
   - NEVER output any of these forbidden labels anywhere in predicates, kinds, or relations:
     {sorted(FORBIDDEN_LABELS)}.
   - You produce raw semantic building blocks, not longitudinal cognitive conclusions.

OUTPUT FORMAT:
Return a JSON object conforming exactly to this schema:
{{
  "units": [
    {{
      "annotation_id": "u1",
      "source_span": {{"char_start": 0, "char_end": 33, "text": "I joined the committee yesterday"}},
      "kind": "event",
      "predicate": {{
        "surface_predicate": "joined",
        "normalized_predicate": "joined",
        "normalization_rule": "exact_surface"
      }},
      "arguments": {{
        "actor": {{"mention_id": "m1", "text": "I", "source_span": {{"char_start": 0, "char_end": 1, "text": "I"}}, "entity_ref": "user"}},
        "target": {{"mention_id": "m2", "text": "committee", "source_span": {{"char_start": 13, "char_end": 22, "text": "committee"}}}},
        "time": {{"mention_id": "m3", "text": "yesterday", "source_span": {{"char_start": 23, "char_end": 32, "text": "yesterday"}}}}
      }},
      "polarity": "positive",
      "modality": "asserted",
      "epistemic_hedge": "none",
      "holder_ref": "user",
      "attribution_mode": "direct_speaker",
      "temporal_anchoring": {{
        "normalized_value": "2026-09-23",
        "anchor_type": "relative",
        "source_expression": "yesterday",
        "reference_anchor": "evidence:occurred_at"
      }},
      "evidence_status": "explicit",
      "confidence": 1.0
    }}
  ],
  "relations": [
    {{
      "relation_id": "rel_01",
      "source_id": "u1",
      "target_id": "u2",
      "relation_type": "BEFORE",
      "evidence_status": "explicit",
      "confidence": 1.0,
      "supporting_spans": []
    }}
  ]
}}
"""


def load_dev_few_shots(dev_jsonl_path: Path | str, case_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """Load calibration few-shot examples strictly from the Dev split."""
    dev_path = Path(dev_jsonl_path)
    if not dev_path.exists():
        return []

    # Diverse calibration cases covering core phenomena within token budget
    target_ids = case_ids or [
        "gold_dev_09",  # SAME_ENTITY mention-level coreference across sentences
        "gold_dev_12",  # explicit CAUSE with 'therefore' in supporting_spans
        "gold_dev_15",  # longitudinal shift across years (BEFORE, not REVISION)
        "gold_dev_17",  # nested attitude (intended + think, decoupled)
        "gold_dev_20",  # NO_RELATION control
    ]

    selected: list[dict[str, Any]] = []
    with open(dev_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            c = json.loads(line)
            if c["case_id"] in target_ids:
                selected.append({
                    "case_id": c["case_id"],
                    "raw_evidence": c["raw_evidence"],
                    "semantic_blocks": c["semantic_blocks"],
                    "cutoff_time": c["cutoff_time"],
                    "gold_output": {
                        "units": c["gold_document"]["units"],
                        "relations": c["gold_document"]["relations"],
                    },
                })
    return selected


def format_few_shot_block(few_shots: list[dict[str, Any]]) -> str:
    """Format few-shot examples for inclusion in model prompt using compact JSON."""
    blocks: list[str] = ["--- FEW-SHOT CALIBRATION EXAMPLES (FROM DEV SET) ---"]
    for idx, ex in enumerate(few_shots, 1):
        content = ex["raw_evidence"][0]["content"]
        blocks.append(f"\nExample {idx}:")
        blocks.append(f"INPUT EVIDENCE: \"{content}\"")
        blocks.append("OUTPUT PARSE:")
        blocks.append(json.dumps(ex["gold_output"], separators=(",", ":"), ensure_ascii=False))
    blocks.append("\n--- END OF FEW-SHOT EXAMPLES ---")
    return "\n".join(blocks)


def format_user_prompt(case_input: dict[str, Any], few_shot_text: str = "") -> str:
    """Format input case into user prompt, strictly sanitizing out gold annotations and metadata."""
    raw_ev = case_input["raw_evidence"]
    blocks = case_input["semantic_blocks"]
    cutoff = case_input.get("cutoff_time", "2026-09-23T00:00:00Z")

    content_lines = []
    for ev in raw_ev:
        content_lines.append(f"Evidence ID: {ev['evidence_id']} (Occurred at: {ev.get('occurred_at')})")
        content_lines.append(f"Text Content: \"{ev['content']}\"")

    prompt = f"""{few_shot_text}

--- TARGET INPUT TO PARSE ---
Cutoff Timestamp: {cutoff}
{chr(10).join(content_lines)}

Parse the above evidence into atomic SemanticUnits and pairwise SemanticRelations according to the v0.1 frozen ontology.
Ensure all source spans align to exact character slices in the text.
Ensure arguments are strictly contained inside their unit spans.
Do not emit any forbidden longitudinal cognition terms.
Return ONLY valid JSON.
"""
    return prompt
