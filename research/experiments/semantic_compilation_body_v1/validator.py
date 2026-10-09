"""Deterministic Validator for SemanticParseResultV1 proposals.

Ensures that model proposals strictly adhere to typed structural constraints
before being consumed by the Semantic Closure Compiler (§14).
"""

from __future__ import annotations

import json
import re
from typing import Any
from research.experiments.semantic_compilation_body_v1.schema import (
    BoundaryPolicy,
    EpistemicStatus,
    Polarity,
    SemanticDependency,
    SemanticParseResultV1,
    SemanticPoint,
    SpeechAct,
    TemporalKind,
)

VALID_SPEECH_ACTS: set[SpeechAct] = {"assertion", "question", "directive", "other"}
VALID_POLARITIES: set[Polarity] = {"positive", "negative", "unknown"}
VALID_EPISTEMICS: set[EpistemicStatus] = {
    "asserted",
    "uncertain",
    "hypothetical",
    "counterfactual",
    "planned",
    "reported",
    "unknown",
}
VALID_TEMPORALS: set[TemporalKind] = {"past", "current", "future", "atemporal", "unknown"}
VALID_POLICIES: set[BoundaryPolicy] = {"cohabit", "context", "separate"}


def extract_json(raw_text: str) -> dict[str, Any]:
    """Extract and parse JSON object from raw LLM output."""
    raw_text = raw_text.strip()
    # Check for markdown code blocks
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    
    # Check for raw JSON object
    match2 = re.search(r"(\{.*\})", raw_text, re.DOTALL)
    if match2:
        return json.loads(match2.group(1))
    
    return json.loads(raw_text)


def validate_parse_result(
    raw_output: str | dict[str, Any],
    source_refs: list[str] | None = None,
) -> tuple[SemanticParseResultV1, list[str]]:
    """Validate and sanitize a raw model proposal into SemanticParseResultV1.
    
    Returns (validated_result, list_of_warning_or_repair_messages).
    """
    diagnostics: list[str] = []
    
    if isinstance(raw_output, str):
        data = extract_json(raw_output)
    else:
        data = raw_output

    if not isinstance(data, dict):
        raise ValueError("Model output root must be a JSON object dictionary.")

    schema_version = data.get("schema_version", "semantic_parse_v1")
    src_refs = data.get("source_window_refs", source_refs or [])

    points: list[SemanticPoint] = []
    point_ids: set[str] = set()

    for idx, raw_pt in enumerate(data.get("semantic_points", [])):
        pid = str(raw_pt.get("local_id") or f"P{idx+1:02d}").strip()
        meaning = str(raw_pt.get("meaning", "")).strip()
        if not meaning:
            diagnostics.append(f"Point {pid} had empty meaning; omitted.")
            continue

        pt_sources = raw_pt.get("source_refs", [])
        if not pt_sources and source_refs:
            pt_sources = list(source_refs)

        # Normalize status
        status = raw_pt.get("status", "resolved")
        if status not in ("resolved", "defer"):
            status = "defer" if "defer" in str(status).lower() else "resolved"

        # Normalize speech_act
        sa = str(raw_pt.get("speech_act", "assertion")).lower()
        if sa not in VALID_SPEECH_ACTS:
            diagnostics.append(f"Point {pid} invalid speech_act '{sa}', normalized to 'assertion'")
            sa = "assertion"

        # Normalize polarity
        pol = str(raw_pt.get("polarity", "positive")).lower()
        if pol not in VALID_POLARITIES:
            pol = "positive"

        # Normalize epistemic
        ep = str(raw_pt.get("epistemic_status") or raw_pt.get("epistemic", "asserted")).lower()
        if ep not in VALID_EPISTEMICS:
            diagnostics.append(f"Point {pid} invalid epistemic '{ep}', normalized to 'asserted'")
            ep = "asserted"

        # Normalize temporal
        temp = str(raw_pt.get("temporal", "current")).lower()
        if temp not in VALID_TEMPORALS:
            temp = "current"

        unresolved_refs = raw_pt.get("unresolved_refs", [])
        conf = float(raw_pt.get("confidence", 1.0))
        conf = max(0.0, min(1.0, conf))

        point = SemanticPoint(
            local_id=pid,
            source_refs=pt_sources,
            meaning=meaning,
            status=status,
            speech_act=sa,
            polarity=pol,
            epistemic_status=ep,
            temporal=temp,
            unresolved_refs=unresolved_refs,
            confidence=conf,
        )
        points.append(point)
        point_ids.add(pid)

    dependencies: list[SemanticDependency] = []
    for dep in data.get("dependencies", []):
        f_pt = str(dep.get("from_point") or dep.get("from", "")).strip()
        t_pt = str(dep.get("to_point") or dep.get("to", "")).strip()
        if f_pt not in point_ids or t_pt not in point_ids:
            diagnostics.append(f"Dependency {f_pt}->{t_pt} dropped: endpoints not in points.")
            continue
        if f_pt == t_pt:
            diagnostics.append(f"Self-loop dependency on {f_pt} dropped.")
            continue

        policy = str(dep.get("boundary_policy") or dep.get("policy", "separate")).lower()
        if policy not in VALID_POLICIES:
            diagnostics.append(f"Invalid policy '{policy}' for {f_pt}->{t_pt}; normalized to 'separate'")
            policy = "separate"

        rel = str(dep.get("relation") or dep.get("type", "related_to")).strip()
        reason = str(dep.get("reason", "")).strip()
        conf = float(dep.get("confidence", 1.0))
        conf = max(0.0, min(1.0, conf))

        dependencies.append(
            SemanticDependency(
                from_point=f_pt,
                to_point=t_pt,
                relation=rel,
                boundary_policy=policy,
                reason=reason,
                confidence=conf,
            )
        )

    # Reconcile unresolved list
    unresolved: list[str] = []
    for item in data.get("unresolved", []):
        if isinstance(item, dict):
            val = str(item.get("point_id") or item.get("local_id") or item.get("id") or "").strip()
            if val:
                unresolved.append(val)
        elif item is not None:
            unresolved.append(str(item).strip())

    for p in points:
        if p.status == "defer" and p.local_id not in unresolved:
            unresolved.append(p.local_id)
        if p.unresolved_refs and p.local_id not in unresolved:
            unresolved.append(p.local_id)

    return (
        SemanticParseResultV1(
            schema_version=schema_version,
            source_window_refs=src_refs,
            semantic_points=points,
            dependencies=dependencies,
            unresolved=unresolved,
        ),
        diagnostics,
    )
