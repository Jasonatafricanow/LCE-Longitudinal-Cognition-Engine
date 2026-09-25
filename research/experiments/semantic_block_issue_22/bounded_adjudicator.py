"""Bounded Adjudicator for SemanticBlock Issue #22 Benchmark.

Enforces an identical consumer adjudication contract across all experimental arms:
- Receives bounded candidate package (budget K in [3, 5, 8])
- Adjudicates whether each candidate actually supports the requested cognition
- Identifies accepted true targets vs false accepted cognitions vs rejected non-targets
- Measures candidate token cost, latency, and adjudication burden
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from research.experiments.semantic_block_issue_22.llm_client import (
    BenchmarkLLMClient,
    CallResult,
)
from research.experiments.semantic_block_issue_22.retrieval_engine import (
    RetrievalCandidate,
)

ADJUDICATOR_SYSTEM_PROMPT = """你是一个严格的纵向认知判定裁决器（Cognition Adjudicator）。
你的任务是评估候选语义块（SemanticBlock Candidate Package）是否能够确切、忠实地支持给定的检索认知目标。

输入包含：
1. 认知目标（Cognition Request / Query）：需要验证或检索的具体事实、状态、态度、主体或约束。
2. 候选语义块列表（Candidate Blocks）：每个语义块包含规范语义核心（Semantic Core）、元数据及结构投影信息。

【判决准则】：
1. 仅当候选块客观且完全支持认知目标所要求的主体、态度（肯定/否定/怀疑）、语力（陈述/询问/假设）、时态与情态时，方可判定 accepted 为 true。
2. 伪相关拒绝（Strict Rejection of Hard Negatives）：
   - 表面词汇高度重合但主体角色相反（如通知发起方颠倒、出借人借入人颠倒）必须拒绝（accepted: false）；
   - 极性相反（如询问拒绝签署而候选为同意签署）必须拒绝；
   - 情态不符（如要求确定事实而候选为纯粹假设、或反之）必须拒绝；
   - 归属不符（如要求用户自身确信而候选为转述他人观点）必须拒绝。
3. 给出清晰明确的判决理由（reason）。

输出严格 JSON 格式：
{
  "decisions": [
    {
      "candidate_id": "候选语义块ID",
      "accepted": true 或 false,
      "relevance_score": 0.0 到 1.0,
      "reason": "支持或拒绝的判定理由"
    }
  ]
}"""


@dataclass
class CandidateDecision:
    candidate_id: str
    accepted: bool
    relevance_score: float
    reason: str
    is_true_target: bool
    is_hard_negative: bool


@dataclass
class QueryAdjudicationResult:
    query_id: str
    query_text: str
    arm_id: str
    retrieval_method: str
    budget_k: int
    candidate_count: int
    decisions: list[CandidateDecision]
    accepted_target_count: int
    false_accepted_count: int
    rejected_irrelevant_count: int
    final_accepted_target_recall: float
    false_accepted_cognition_rate: float
    adjudication_precision: float
    candidate_token_count: int
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    cached: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BoundedAdjudicator:
    def __init__(self, llm_client: BenchmarkLLMClient) -> None:
        self.client = llm_client

    def adjudicate_candidate_package(
        self,
        query: dict[str, Any],
        candidates: list[RetrievalCandidate],
        arm_id: str,
        retrieval_method: str,
        budget_k: int,
        fork_group_map: dict[str, str] | None = None,
    ) -> QueryAdjudicationResult:
        fg_map = fork_group_map or {}
        qid = query["query_id"]
        qtext = query["query_text"]

        target_ids = set(query.get("target_case_ids", []))
        for tfg in query.get("target_fork_group_ids", []):
            for iid, fg in fg_map.items():
                if fg == tfg:
                    target_ids.add(iid)

        hn_ids = set(query.get("hard_negative_case_ids", []))
        for hfg in query.get("hard_negative_fork_group_ids", []):
            for iid, fg in fg_map.items():
                if fg == hfg:
                    hn_ids.add(iid)

        # Build candidate package representation for LLM prompt
        cand_blocks_text = []
        total_candidate_tokens = 0
        for idx, cand in enumerate(candidates, 1):
            rep_text = cand.representation.representation_text
            total_candidate_tokens += len(rep_text) // 2  # Approximate token count for Chinese/ASCII
            block_str = f"--- [候选块 {idx} | ID: {cand.item_id}] ---\n{rep_text}"
            cand_blocks_text.append(block_str)

        prompt = (
            f"认知目标（Cognition Request）：\n{qtext}\n\n"
            f"候选语义块集合（共 {len(candidates)} 个候选）：\n\n"
            + "\n\n".join(cand_blocks_text)
            + "\n\n请严格对以上每个候选语义块进行客观裁决（JSON格式）。"
        )

        res: CallResult = self.client.generate_json(prompt, system_instruction=ADJUDICATOR_SYSTEM_PROMPT)
        content = res.content
        raw_decisions = content.get("decisions", []) if isinstance(content, dict) else []
        if isinstance(content, list):
            raw_decisions = content

        dec_map = {}
        for d in raw_decisions:
            if isinstance(d, dict) and "candidate_id" in d:
                dec_map[d["candidate_id"]] = d

        decisions: list[CandidateDecision] = []
        accepted_targets = 0
        false_accepts = 0
        rejected_irrelevant = 0

        for cand in candidates:
            cid = cand.item_id
            is_target = cid in target_ids
            is_hn = cid in hn_ids

            # Find adjudicator verdict
            d_info = dec_map.get(cid)
            if not d_info:
                # Fallback search by index or substring
                for k, v in dec_map.items():
                    if cid in k or k in cid:
                        d_info = v
                        break

            if d_info:
                accepted = bool(d_info.get("accepted", False))
                score = float(d_info.get("relevance_score", 1.0 if accepted else 0.0))
                reason = str(d_info.get("reason", ""))
            else:
                accepted = False
                score = 0.0
                reason = "No decision rendered by adjudicator; default rejected."

            if accepted:
                if is_target:
                    accepted_targets += 1
                else:
                    false_accepts += 1
            else:
                if not is_target:
                    rejected_irrelevant += 1

            decisions.append(
                CandidateDecision(
                    candidate_id=cid,
                    accepted=accepted,
                    relevance_score=score,
                    reason=reason,
                    is_true_target=is_target,
                    is_hard_negative=is_hn,
                )
            )

        num_targets = max(1, len(target_ids))
        target_recall = min(1.0, accepted_targets / num_targets)
        total_accepted = accepted_targets + false_accepts
        precision = accepted_targets / max(1, total_accepted)
        false_accept_rate = false_accepts / max(1, total_accepted)

        return QueryAdjudicationResult(
            query_id=qid,
            query_text=qtext,
            arm_id=arm_id,
            retrieval_method=retrieval_method,
            budget_k=budget_k,
            candidate_count=len(candidates),
            decisions=decisions,
            accepted_target_count=accepted_targets,
            false_accepted_count=false_accepts,
            rejected_irrelevant_count=rejected_irrelevant,
            final_accepted_target_recall=target_recall,
            false_accepted_cognition_rate=false_accept_rate,
            adjudication_precision=precision,
            candidate_token_count=total_candidate_tokens,
            prompt_tokens=res.prompt_tokens,
            completion_tokens=res.completion_tokens,
            latency_ms=res.latency_ms,
            cached=res.cached,
        )
