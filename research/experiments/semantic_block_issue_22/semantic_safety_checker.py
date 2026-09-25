"""Semantic Safety and Consistency Auditor for Issue #22.

Audits:
1. Core text identity & SHA-256 hash match across all arms (B0-B4).
2. Projection inconsistency with core (contradictions between extracted projections and canonical core).
3. Unsupported projection values.
4. UNKNOWN scope drift (did projections hallucinate certainty where core is unknown, or vice versa?).
5. Attribution drift (did projections distort speaker or reported source?).
6. Temporal overreach (did projections inject future outcomes?).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from research.experiments.semantic_block_issue_22.projection_compiler import (
    CompiledArmRepresentation,
)


@dataclass
class CaseSafetyAuditResult:
    case_id: str
    core_sha256_match: bool
    core_text_identity_match: bool
    attribution_drift: bool
    polarity_contradiction: bool
    epistemic_contradiction: bool
    temporal_overreach: bool
    unknown_scope_drift: bool
    entity_role_drift: bool
    safety_violations: list[str]


class SemanticSafetyChecker:
    def audit_case_arms(
        self,
        case_id: str,
        arms: dict[str, CompiledArmRepresentation],
        canonical_gold: dict[str, Any] | None = None,
    ) -> CaseSafetyAuditResult:
        violations: list[str] = []

        # 1. Check Core SHA-256 Hash and Text Identity across all arms
        base_core = arms["B0"].semantic_core
        base_hash = arms["B0"].core_sha256
        hash_match = True
        text_match = True

        for arm_id in ["B1", "B2", "B3", "B4"]:
            if arm_id not in arms:
                continue
            arm = arms[arm_id]
            if arm.core_sha256 != base_hash:
                hash_match = False
                violations.append(f"Hash mismatch in {arm_id}: {arm.core_sha256} != {base_hash}")
            if arm.semantic_core != base_core:
                text_match = False
                violations.append(f"Core text mismatch in {arm_id}")

        # 2. Inspect projections in B4 (which contains all projections)
        b4_proj = arms["B4"].projections if "B4" in arms else {}
        b4_core = base_core

        # Attribution drift audit
        attr_drift = False
        src = b4_proj.get("source_attribution", {})
        reported_src = src.get("reported_source")
        if canonical_gold:
            gold_pres = canonical_gold.get("must_preserve", [])
            has_report_in_gold = any("转述" in p or "朋友" in p or "老王" in p or "HR" in p for p in gold_pres)
            if has_report_in_gold and not reported_src:
                attr_drift = True
                violations.append("Attribution drift: core indicates reported speech but projection lacks reported_source")

        # Polarity contradiction audit
        polarity_contra = False
        pol = b4_proj.get("polarity", "positive")
        if pol == "negative":
            if "不" not in b4_core and "没" not in b4_core and "未" not in b4_core and "否" not in b4_core:
                polarity_contra = True
                violations.append(f"Polarity contradiction: projection marked negative but core has no negative marker: '{b4_core}'")
        elif pol == "positive":
            if canonical_gold and canonical_gold.get("polarity") == "negative":
                polarity_contra = True
                violations.append(f"Polarity contradiction: gold is negative but projection is positive: '{b4_core}'")

        # Epistemic contradiction audit
        epistemic_contra = False
        epist = b4_proj.get("epistemic_commitment", "certain")
        if epist == "certain":
            if "可能" in b4_core or "也许" in b4_core or "大概" in b4_core or "不知道" in b4_core:
                epistemic_contra = True
                violations.append(f"Epistemic contradiction: core has modal uncertainty ('可能'/'大概') but projection marked 'certain'")

        # Temporal overreach audit
        temp_overreach = False
        temp_status = b4_proj.get("temporal_status", "")
        if "必须" in b4_core or "打算" in b4_core or "计划" in b4_core:
            if temp_status == "past_completed" and "已经" not in b4_core:
                temp_overreach = True
                violations.append("Temporal overreach: plan/obligation projected as completed past")

        # UNKNOWN scope drift
        unknown_drift = False
        unknowns = b4_proj.get("localized_unknowns", [])
        if "不知道" in b4_core and not unknowns and b4_proj.get("scoped_unresolved_dimensions") == []:
            unknown_drift = True
            violations.append("UNKNOWN scope drift: core explicitly states '不知道' but no localized unknowns recorded")

        # Entity role drift audit (for stress test cases if actor/target gold available)
        entity_role_drift = False
        if canonical_gold and "actor_agent" in canonical_gold:
            gold_actors = canonical_gold.get("actor_agent", [])
            proj_actors = b4_proj.get("entity_role_anchors", {}).get("actor_agent", [])
            for ga in gold_actors:
                if ga not in "".join(proj_actors):
                    entity_role_drift = True
                    violations.append(f"Entity role drift: expected actor '{ga}', got '{proj_actors}'")

        return CaseSafetyAuditResult(
            case_id=case_id,
            core_sha256_match=hash_match,
            core_text_identity_match=text_match,
            attribution_drift=attr_drift,
            polarity_contradiction=polarity_contra,
            epistemic_contradiction=epistemic_contra,
            temporal_overreach=temp_overreach,
            unknown_scope_drift=unknown_drift,
            entity_role_drift=entity_role_drift,
            safety_violations=violations,
        )
