"""Retrieval Engine for SemanticBlock Issue #22 Benchmark.

Implements the 4 retrieval strategies under comparison:
- R0: Core-vector only (broad recall baseline)
- R1: Core-vector + projection rerank (broad top-N -> projection compatibility rerank, no hard rejects)
- R2: Mixed representation embedding (diagnostic: core + serialized projections in dense vector)
- R3: Projection-aware soft expansion (broad recall + structured promotion into fixed candidate budget K)

Evaluates:
- Recall@K for K in [3, 5, 8]
- Target miss rate
- First target rank
- Hard-negative presence rate
- Mean Reciprocal Rank (MRR)
- Candidate expansion count
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import numpy as np

from research.experiments.semantic_block_issue_22.llm_client import (
    BenchmarkLLMClient,
    cosine_sim,
)
from research.experiments.semantic_block_issue_22.projection_compiler import (
    CompiledArmRepresentation,
)

QUERY_ANALYSIS_PROMPT = """你是一个语义检索查询分析器（Retrieval Query Analyzer）。
请分析给定的认知检索查询（Query），提取查询所要求的核心事实与正交结构约束。

输出严格 JSON 格式：
{
  "target_polarity": "positive | negative | mixed_contrastive | any",
  "target_communicative_act": "assertion | question | tentative_suggestion | command_obligation | correction_retraction | hypothetical_counterfactual | any",
  "target_epistemic_commitment": "certain | probable | possible | explicitly_unknown | negated | any",
  "target_attribution": {
    "speaker": "user | other | any",
    "must_be_reported": true | false | null,
    "user_endorsement": "direct | endorsed | skeptical_rejected | uncommitted_unknown | any"
  },
  "target_condition_type": "actual_unconditional | conditional_hypothetical | counterfactual_wish | any",
  "target_change_type": "first_report | real_world_state_change | correction_retraction | any",
  "target_roles": {
    "actor_agent": "特定要求的发起人或施事者（如'李主管'，若无则null）",
    "target_recipient": "特定要求的接收人或受事者（如'张经理'，若无则null）"
  },
  "rationale": "简短分析"
}"""


@dataclass
class RetrievalCandidate:
    item_id: str
    arm_id: str
    rank: int
    score: float
    raw_vector_score: float
    projection_bonus: float
    representation: CompiledArmRepresentation


@dataclass
class QueryRetrievalResult:
    query_id: str
    query_text: str
    split: str
    arm_id: str
    retrieval_method: str
    budget_k: int
    first_target_rank: int
    recall_at_k: float
    target_miss: bool
    hard_negative_present: bool
    expansion_count: int
    candidates: list[RetrievalCandidate]


class RetrievalEngine:
    def __init__(self, llm_client: BenchmarkLLMClient) -> None:
        self.client = llm_client
        self._query_profile_cache: dict[str, dict[str, Any]] = {}

    def analyze_query_profile(self, query_id: str, query_text: str) -> dict[str, Any]:
        if query_id in self._query_profile_cache:
            return self._query_profile_cache[query_id]

        prompt = f"认知检索查询：\n{query_text}\n\n请提取该查询的结构意图与约束（JSON格式）。"
        res = self.client.generate_json(prompt, system_instruction=QUERY_ANALYSIS_PROMPT)
        profile = res.content
        if isinstance(profile, list) and profile and isinstance(profile[0], dict):
            profile = profile[0]
        elif not isinstance(profile, dict):
            profile = {}

        self._query_profile_cache[query_id] = profile
        return profile

    def compute_projection_alignment(
        self,
        arm_id: str,
        projections: dict[str, Any],
        query_profile: dict[str, Any],
    ) -> float:
        """Compute soft projection compatibility score between query and block projections."""
        if not projections or arm_id == "B0":
            return 0.0

        bonus = 0.0

        # B1 Level: Attribution, Epistemic, Action Status
        src = projections.get("source_attribution", {})
        q_attr = query_profile.get("target_attribution", {})
        if q_attr:
            if q_attr.get("must_be_reported") is True:
                if src.get("reported_source"):
                    bonus += 0.06
                else:
                    bonus -= 0.04
            elif q_attr.get("must_be_reported") is False:
                if src.get("reported_source") is None:
                    bonus += 0.04
                else:
                    bonus -= 0.03

            q_endorse = q_attr.get("user_endorsement")
            if q_endorse and q_endorse != "any":
                if src.get("user_endorsement") == q_endorse:
                    bonus += 0.07
                elif src.get("user_endorsement") in ["skeptical_rejected", "direct"] and q_endorse != src.get("user_endorsement"):
                    bonus -= 0.05

        q_epist = query_profile.get("target_epistemic_commitment")
        if q_epist and q_epist != "any":
            c_epist = projections.get("epistemic_commitment")
            if c_epist == q_epist:
                bonus += 0.05
            elif (q_epist == "certain" and c_epist in ["possible", "explicitly_unknown"]) or (q_epist == "possible" and c_epist == "certain"):
                bonus -= 0.04

        # B2 Level: Communicative act, Polarity, Condition
        if arm_id in ["B2", "B3", "B4"]:
            q_act = query_profile.get("target_communicative_act")
            if q_act and q_act != "any":
                c_act = projections.get("communicative_act")
                if c_act == q_act:
                    bonus += 0.06
                elif (q_act == "question" and c_act == "assertion") or (q_act == "assertion" and c_act == "question"):
                    bonus -= 0.05

            q_pol = query_profile.get("target_polarity")
            if q_pol and q_pol != "any":
                c_pol = projections.get("polarity")
                if c_pol == q_pol:
                    bonus += 0.08
                elif (q_pol == "negative" and c_pol == "positive") or (q_pol == "positive" and c_pol == "negative"):
                    bonus -= 0.09

            q_cond = query_profile.get("target_condition_type")
            if q_cond and q_cond != "any":
                c_cond = projections.get("condition_or_hypothesis", {}).get("type")
                if c_cond == q_cond:
                    bonus += 0.07
                elif q_cond == "conditional_hypothetical" and c_cond == "actual_unconditional":
                    bonus -= 0.06

        # B3 Level: Longitudinal state, Change type, Revision
        if arm_id in ["B3", "B4"]:
            q_change = query_profile.get("target_change_type")
            if q_change and q_change != "any":
                c_change = projections.get("change_type")
                if c_change == q_change:
                    bonus += 0.08
                elif q_change == "correction_retraction" and c_change == "real_world_state_change":
                    bonus -= 0.06
                elif q_change == "real_world_state_change" and c_change == "correction_retraction":
                    bonus -= 0.06

        # B4 Level: Entity / role anchors
        if arm_id == "B4":
            q_roles = query_profile.get("target_roles", {})
            q_actor = q_roles.get("actor_agent")
            q_target = q_roles.get("target_recipient")

            anchors = projections.get("entity_role_anchors", {})
            c_actors = anchors.get("actor_agent", [])
            c_targets = anchors.get("target_recipient", [])

            if q_actor:
                if any(q_actor in a for a in c_actors):
                    bonus += 0.12
                elif any(q_actor in t for t in c_targets):
                    # Query actor matched candidate target: entity role reversal!
                    bonus -= 0.12

            if q_target:
                if any(q_target in t for t in c_targets):
                    bonus += 0.12
                elif any(q_target in a for a in c_actors):
                    # Query target matched candidate actor: entity role reversal!
                    bonus -= 0.12

        return bonus

    def run_retrieval_for_query(
        self,
        query: dict[str, Any],
        indexed_items: dict[str, CompiledArmRepresentation],  # item_id -> arm representation
        arm_id: str,
        retrieval_method: str,  # R0, R1, R2, R3
        budget_k: int = 5,
        fork_group_map: dict[str, str] | None = None,
    ) -> QueryRetrievalResult:
        fg_map = fork_group_map or {}
        qid = query["query_id"]
        qtext = query["query_text"]
        split = query.get("split", "dev")

        # Resolve ground truth targets and hard negatives
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

        item_ids = sorted(indexed_items.keys())
        query_profile = self.analyze_query_profile(qid, qtext)

        # 1. Embeddings depending on retrieval method
        if retrieval_method == "R2":
            # Mixed representation dense embedding (diagnostic)
            q_vec = self.client.embed_text(qtext)
            scores_with_ids = []
            for iid in item_ids:
                rep_text = indexed_items[iid].representation_text
                doc_vec = self.client.embed_text(rep_text)
                sim = cosine_sim(q_vec, doc_vec)
                scores_with_ids.append((iid, sim, sim, 0.0))
            scores_with_ids.sort(key=lambda x: x[1], reverse=True)
            candidate_tuples = scores_with_ids[:budget_k]
            expansion_count = 0

        elif retrieval_method == "R0":
            # Core-vector only (broad baseline)
            q_vec = self.client.embed_text(qtext)
            scores_with_ids = []
            for iid in item_ids:
                core_text = indexed_items[iid].core_only_text
                doc_vec = self.client.embed_text(core_text)
                sim = cosine_sim(q_vec, doc_vec)
                scores_with_ids.append((iid, sim, sim, 0.0))
            scores_with_ids.sort(key=lambda x: x[1], reverse=True)
            candidate_tuples = scores_with_ids[:budget_k]
            expansion_count = 0

        elif retrieval_method == "R1":
            # Core-vector + projection rerank (broad top-N -> projection soft adjustment)
            q_vec = self.client.embed_text(qtext)
            broad_n = min(len(item_ids), max(15, budget_k * 2))
            base_scores = []
            for iid in item_ids:
                core_text = indexed_items[iid].core_only_text
                doc_vec = self.client.embed_text(core_text)
                sim = cosine_sim(q_vec, doc_vec)
                base_scores.append((iid, sim))
            base_scores.sort(key=lambda x: x[1], reverse=True)

            # Take broad top-N and apply soft projection rerank
            broad_pool = base_scores[:broad_n]
            reranked = []
            for iid, sim in broad_pool:
                bonus = self.compute_projection_alignment(
                    arm_id=arm_id,
                    projections=indexed_items[iid].projections,
                    query_profile=query_profile,
                )
                final_score = sim + bonus
                reranked.append((iid, final_score, sim, bonus))
            reranked.sort(key=lambda x: x[1], reverse=True)

            candidate_tuples = reranked[:budget_k]
            expansion_count = 0

        elif retrieval_method == "R3":
            # Projection-aware soft expansion:
            # Broad core-vector retrieval + promote high projection matches outside top-K into budget K
            q_vec = self.client.embed_text(qtext)
            broad_n = min(len(item_ids), max(20, budget_k * 3))
            base_scores = []
            for iid in item_ids:
                core_text = indexed_items[iid].core_only_text
                doc_vec = self.client.embed_text(core_text)
                sim = cosine_sim(q_vec, doc_vec)
                base_scores.append((iid, sim))
            base_scores.sort(key=lambda x: x[1], reverse=True)

            # Rerank broad pool
            broad_pool = base_scores[:broad_n]
            reranked = []
            for iid, sim in broad_pool:
                bonus = self.compute_projection_alignment(
                    arm_id=arm_id,
                    projections=indexed_items[iid].projections,
                    query_profile=query_profile,
                )
                reranked.append((iid, sim + bonus, sim, bonus))
            reranked.sort(key=lambda x: x[1], reverse=True)

            initial_top_k_ids = set([x[0] for x in base_scores[:budget_k]])
            reranked_top_k = reranked[:budget_k]
            expansion_count = sum(1 for c in reranked_top_k if c[0] not in initial_top_k_ids)
            candidate_tuples = reranked_top_k

        else:
            raise ValueError(f"Unknown retrieval method: {retrieval_method}")

        # Assemble candidates
        candidates: list[RetrievalCandidate] = []
        for rank, (iid, final_s, raw_s, bonus) in enumerate(candidate_tuples, 1):
            candidates.append(
                RetrievalCandidate(
                    item_id=iid,
                    arm_id=arm_id,
                    rank=rank,
                    score=final_s,
                    raw_vector_score=raw_s,
                    projection_bonus=bonus,
                    representation=indexed_items[iid],
                )
            )

        # Calculate metrics for this query
        candidate_ids = [c.item_id for c in candidates]
        target_ranks = [candidate_ids.index(t) + 1 for t in target_ids if t in candidate_ids]
        first_target_rank = min(target_ranks) if target_ranks else 999
        recall_at_k = 1.0 if any(t in candidate_ids for t in target_ids) else 0.0
        target_miss = recall_at_k == 0.0
        hn_present = any(hn in candidate_ids for hn in hn_ids)

        return QueryRetrievalResult(
            query_id=qid,
            query_text=qtext,
            split=split,
            arm_id=arm_id,
            retrieval_method=retrieval_method,
            budget_k=budget_k,
            first_target_rank=first_target_rank,
            recall_at_k=recall_at_k,
            target_miss=target_miss,
            hard_negative_present=hn_present,
            expansion_count=expansion_count,
            candidates=candidates,
        )
