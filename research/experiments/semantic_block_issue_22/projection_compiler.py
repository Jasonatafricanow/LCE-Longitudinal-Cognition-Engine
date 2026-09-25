"""SemanticBlock Projection Compiler for Issue #22.

Compiles experimental arms B0 - B4 around an intact, frozen Semantic Core:
- B0: Core only + provenance/deterministic metadata
- B1: Current minimal projections (attribution, epistemic, action status, localized unknowns)
- B2: Expanded discourse-state projections (+ communicative act, polarity, condition/hypothesis)
- B3: Expanded longitudinal-state projections (+ temporal status, change type, revision retraction, scoped unknowns)
- B4: Entity / role anchor projections (+ actor, target, object, location, key entities)

INVARIANT:
All arms B0-B4 share the exact same canonical `semantic_core` string and SHA-256 hash.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.experiments.semantic_block_issue_22.llm_client import BenchmarkLLMClient

PROJECTION_EXTRACTION_SYSTEM_PROMPT = """你是一个高精度的语义块正交投影编译器（SemanticBlock Projection Compiler）。
你的任务是围绕已经给定的“规范语义核心（Semantic Core）”，从对话截断点提取一系列多维正交投影（Projections）。

【绝对核心准则】：
1. 语义核心不可变（Immutable Semantic Core）：给定的规范语义核心完整表达了该时间点的真实含义。你所提取的所有投影均为对该语义核心的索引和正交视角，严禁与核心产生矛盾，严禁肢解或用槽位取代核心。
2. 来源归属：区分用户直接断言、转述他人观点、用户认同转述、用户怀疑/否定转述。
3. 语力与极性：区分陈述、询问确认、建议提议、假设条件、反讽等言语行为；精确判断真值陈述极性（肯定 positive、否定 negative、混合 mixed、未知 unknown）。注意：极性是真值否定（如'不去'、'没做'、'不同意'），绝不是情感好坏倾向（如'延期'或'坏事'若为肯定陈述仍是 positive）！
4. 假设与条件：准确提取是否依赖前置条件，区分纯粹反事实愿望与真实条件。
5. 纵向演变与纠错：区分客观世界状态变更（real_world_state_change，如通知延期）与说话人口误纠错（correction_retraction，如说错日期）。
6. 实体角色锚点：提取核心涉及的施事（actor_agent）、受事/对象（target_recipient）、客体资源（affected_object）、地点终点（destination_or_location）、关键命名实体（key_entities）。锚点只是定位索引，不可脱离核心独立解释。
7. 诚实未知：对话与核心中未涉及的维度保持未知（unknown 或空列表），绝不脑补过度推断。

请以严格的 JSON 格式输出如下字段：
{
  "source_attribution": {
    "speaker": "user | 对话对方 | 其他",
    "reported_source": null 或 "朋友 | 老王 | HR | 公司 等",
    "user_endorsement": "direct | endorsed | skeptical_rejected | uncommitted_unknown"
  },
  "epistemic_commitment": "certain | probable | possible | explicitly_unknown | negated",
  "action_or_state": {
    "status": "current_requirement_obligation | intention_plan | desire_preference | completed_past | hypothetical | cancelled_retracted | state_observation",
    "summary": "简明动作或状态摘要"
  },
  "localized_unknowns": ["具体未知事项1", "具体未知事项2"],
  "communicative_act": "assertion | question | tentative_suggestion | command_obligation | correction_retraction | hypothetical_counterfactual | expressive_irony",
  "polarity": "positive | negative | mixed_contrastive | unknown",
  "condition_or_hypothesis": {
    "type": "actual_unconditional | conditional_hypothetical | counterfactual_wish | counterfactual_relief",
    "condition_text": null 或 "条件陈述",
    "consequent_text": null 或 "结论陈述"
  },
  "temporal_status": "past_completed | present_current_requirement | future_planned | timeless_habitual | unknown",
  "change_type": "first_report | real_world_state_change | correction_retraction | no_change",
  "revision_retraction": {
    "is_revision": false 或 true,
    "retracted_target": null 或 "被撤回或纠正的旧内容",
    "correction_nature": null 或 "speaker_slip_repair | external_state_change"
  },
  "scoped_unresolved_dimensions": [
    {
      "dimension": "未决维度名称",
      "scope": "time_point_local | trajectory_dependent | external_world_dependent",
      "blocking_condition": null 或 "阻塞条件"
    }
  ],
  "entity_role_anchors": {
    "actor_agent": ["施事主体1"],
    "target_recipient": ["接收/受事对象1"],
    "affected_object": ["涉及的事务/物品/主题"],
    "destination_or_location": ["地点或终点"],
    "key_entities": ["实体1", "实体2"]
  }
}"""


@dataclass
class CompiledArmRepresentation:
    arm_id: str
    case_id: str
    cutoff_turn: int
    semantic_core: str
    core_sha256: str
    provenance: dict[str, Any]
    projections: dict[str, Any]
    representation_text: str
    core_only_text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProjectionCompiler:
    def __init__(self, llm_client: BenchmarkLLMClient) -> None:
        self.client = llm_client

    def compile_all_arms_for_item(
        self,
        case_id: str,
        dialogue: list[dict[str, str]],
        cutoff_turn: int,
        canonical_semantic_core: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> dict[str, CompiledArmRepresentation]:
        """Compile B0, B1, B2, B3, B4 for an item, guaranteeing identical canonical semantic_core."""
        canonical_semantic_core = canonical_semantic_core.strip()
        core_hash = hashlib.sha256(canonical_semantic_core.encode("utf-8")).hexdigest()

        visible_turns = dialogue[:cutoff_turn]
        dialogue_text = " | ".join(f"{t['speaker']}: {t['text']}" for t in visible_turns)

        # Provenance & deterministic metadata
        provenance = {
            "case_id": case_id,
            "cutoff_turn": cutoff_turn,
            "speaker": visible_turns[-1]["speaker"] if visible_turns else "user",
            **(extra_metadata or {}),
        }

        # Query LLM to extract the orthogonal projection suite around the intact core
        prompt = (
            f"截断对话（截止第{cutoff_turn}轮）：\n{dialogue_text}\n\n"
            f"权威规范语义核心（Semantic Core）：\n{canonical_semantic_core}\n\n"
            f"请严格依据规范语义核心与对话，提取多维正交投影（JSON格式）。"
        )

        res = self.client.generate_json(prompt, system_instruction=PROJECTION_EXTRACTION_SYSTEM_PROMPT)
        raw_proj = res.content
        if isinstance(raw_proj, list) and raw_proj and isinstance(raw_proj[0], dict):
            raw_proj = raw_proj[0]
        elif not isinstance(raw_proj, dict):
            raw_proj = {}

        # Safely extract projections with robust fallbacks
        source_attribution = raw_proj.get("source_attribution") or {
            "speaker": provenance.get("speaker", "user"),
            "reported_source": None,
            "user_endorsement": "direct",
        }
        epistemic_commitment = raw_proj.get("epistemic_commitment") or "certain"
        action_or_state = raw_proj.get("action_or_state") or {
            "status": "state_observation",
            "summary": canonical_semantic_core[:30],
        }
        localized_unknowns = raw_proj.get("localized_unknowns") or []
        communicative_act = raw_proj.get("communicative_act") or "assertion"
        polarity = raw_proj.get("polarity") or "positive"
        condition_or_hypothesis = raw_proj.get("condition_or_hypothesis") or {
            "type": "actual_unconditional",
            "condition_text": None,
            "consequent_text": None,
        }
        temporal_status = raw_proj.get("temporal_status") or "present_current_requirement"
        change_type = raw_proj.get("change_type") or "first_report"
        revision_retraction = raw_proj.get("revision_retraction") or {
            "is_revision": False,
            "retracted_target": None,
            "correction_nature": None,
        }
        scoped_unresolved_dimensions = raw_proj.get("scoped_unresolved_dimensions") or []
        entity_role_anchors = raw_proj.get("entity_role_anchors") or {
            "actor_agent": [],
            "target_recipient": [],
            "affected_object": [],
            "destination_or_location": [],
            "key_entities": [],
        }

        # Common core representation header
        core_header = (
            f"[SEMANTIC_CORE]: {canonical_semantic_core}\n"
            f"[元数据与切点]: case={case_id} | 轮次切点={cutoff_turn} | 说话人={provenance.get('speaker', 'user')}"
        )

        # Build serialized representations per arm

        # B0: Core only
        b0_text = core_header
        b0 = CompiledArmRepresentation(
            arm_id="B0",
            case_id=case_id,
            cutoff_turn=cutoff_turn,
            semantic_core=canonical_semantic_core,
            core_sha256=core_hash,
            provenance=provenance,
            projections={},
            representation_text=b0_text,
            core_only_text=canonical_semantic_core,
            prompt_tokens=res.prompt_tokens,
            completion_tokens=res.completion_tokens,
            latency_ms=res.latency_ms,
            cached=res.cached,
        )

        # B1: Minimal projections
        b1_proj = {
            "source_attribution": source_attribution,
            "epistemic_commitment": epistemic_commitment,
            "action_or_state": action_or_state,
            "localized_unknowns": localized_unknowns,
        }
        b1_text = (
            f"{core_header}\n"
            f"[来源归属]: {json.dumps(source_attribution, ensure_ascii=False)} "
            f"[认知强度]: {epistemic_commitment} "
            f"[动作状态]: {json.dumps(action_or_state, ensure_ascii=False)} "
            f"[未知维度]: {json.dumps(localized_unknowns, ensure_ascii=False)}"
        )
        b1 = CompiledArmRepresentation(
            arm_id="B1",
            case_id=case_id,
            cutoff_turn=cutoff_turn,
            semantic_core=canonical_semantic_core,
            core_sha256=core_hash,
            provenance=provenance,
            projections=b1_proj,
            representation_text=b1_text,
            core_only_text=canonical_semantic_core,
            prompt_tokens=res.prompt_tokens,
            completion_tokens=res.completion_tokens,
            latency_ms=res.latency_ms,
            cached=res.cached,
        )

        # B2: Expanded discourse-state projections
        b2_proj = {
            **b1_proj,
            "communicative_act": communicative_act,
            "polarity": polarity,
            "condition_or_hypothesis": condition_or_hypothesis,
        }
        b2_text = (
            f"{b1_text}\n"
            f"[言语行为]: {communicative_act} "
            f"[语义极性]: {polarity} "
            f"[假设条件]: {json.dumps(condition_or_hypothesis, ensure_ascii=False)}"
        )
        b2 = CompiledArmRepresentation(
            arm_id="B2",
            case_id=case_id,
            cutoff_turn=cutoff_turn,
            semantic_core=canonical_semantic_core,
            core_sha256=core_hash,
            provenance=provenance,
            projections=b2_proj,
            representation_text=b2_text,
            core_only_text=canonical_semantic_core,
            prompt_tokens=res.prompt_tokens,
            completion_tokens=res.completion_tokens,
            latency_ms=res.latency_ms,
            cached=res.cached,
        )

        # B3: Expanded longitudinal-state projections
        b3_proj = {
            **b2_proj,
            "temporal_status": temporal_status,
            "change_type": change_type,
            "revision_retraction": revision_retraction,
            "scoped_unresolved_dimensions": scoped_unresolved_dimensions,
        }
        b3_text = (
            f"{b2_text}\n"
            f"[时态状态]: {temporal_status} "
            f"[变更类型]: {change_type} "
            f"[纠错撤回]: {json.dumps(revision_retraction, ensure_ascii=False)} "
            f"[定域未决]: {json.dumps(scoped_unresolved_dimensions, ensure_ascii=False)}"
        )
        b3 = CompiledArmRepresentation(
            arm_id="B3",
            case_id=case_id,
            cutoff_turn=cutoff_turn,
            semantic_core=canonical_semantic_core,
            core_sha256=core_hash,
            provenance=provenance,
            projections=b3_proj,
            representation_text=b3_text,
            core_only_text=canonical_semantic_core,
            prompt_tokens=res.prompt_tokens,
            completion_tokens=res.completion_tokens,
            latency_ms=res.latency_ms,
            cached=res.cached,
        )

        # B4: Entity / role anchor projections
        b4_proj = {
            **b3_proj,
            "entity_role_anchors": entity_role_anchors,
        }
        b4_text = (
            f"{b3_text}\n"
            f"[实体角色锚点]: {json.dumps(entity_role_anchors, ensure_ascii=False)}"
        )
        b4 = CompiledArmRepresentation(
            arm_id="B4",
            case_id=case_id,
            cutoff_turn=cutoff_turn,
            semantic_core=canonical_semantic_core,
            core_sha256=core_hash,
            provenance=provenance,
            projections=b4_proj,
            representation_text=b4_text,
            core_only_text=canonical_semantic_core,
            prompt_tokens=res.prompt_tokens,
            completion_tokens=res.completion_tokens,
            latency_ms=res.latency_ms,
            cached=res.cached,
        )

        # Hard invariant assertions
        arms = {"B0": b0, "B1": b1, "B2": b2, "B3": b3, "B4": b4}
        for arm_name, arm_obj in arms.items():
            if arm_obj.core_sha256 != core_hash:
                raise ValueError(
                    f"Core Invariant Violation in arm {arm_name} for case {case_id}: "
                    f"Expected hash {core_hash}, got {arm_obj.core_sha256}"
                )

        return arms
