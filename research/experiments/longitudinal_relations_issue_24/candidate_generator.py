"""Candidate Formation Generators (L0, L1, L2) for Issue #24.

Levels:
- L0: Time Only (Chronological forward ordering within temporal window)
- L1: Time + Semantic Core dense embedding cosine similarity
- L2: Time + Cognitive Boundary Projections (sparse structural matching)
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from lce.cognition.longitudinal_relation import LongitudinalCandidate
from research.experiments.longitudinal_relations_issue_24.contracts import CorpusBlockRecord
from research.experiments.longitudinal_relations_issue_24.llm_client import (
    cosine_sim,
    get_llm_client,
)

REVISION_CHANGE_KEYWORDS = {"改到", "顺延", "推迟", "延期", "调到", "变更", "变动", "新安排"}
REVISION_CORRECTION_KEYWORDS = {"说错了", "记错了", "看错了", "笔误", "搞错了", "不是", "其实是", "纠正", "更正"}
PERSISTENCE_KEYWORDS = {"还在", "依然", "仍然", "暂未", "维持", "压了", "待审批", "没变"}


class CandidateGenerator:
    """Manages multi-tier candidate generation."""

    def __init__(
        self,
        temporal_window_hours: float = 720.0,
        l1_cosine_threshold: float = 0.65,
    ) -> None:
        self.temporal_window = timedelta(hours=temporal_window_hours)
        self.l1_cosine_threshold = l1_cosine_threshold
        self.llm_client = get_llm_client()
        self._embedding_cache: dict[str, list[float]] = {}

    def get_block_embedding(self, block: CorpusBlockRecord) -> list[float]:
        if block.block_id not in self._embedding_cache:
            self._embedding_cache[block.block_id] = self.llm_client.embed_text(block.content)
        return self._embedding_cache[block.block_id]

    # -------------------------------------------------------------------------
    # L0: Time Only
    # -------------------------------------------------------------------------
    def generate_l0(self, blocks: list[CorpusBlockRecord]) -> list[LongitudinalCandidate]:
        """Generate all forward pairs respecting deterministic chronological authority."""
        candidates = []
        n = len(blocks)
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                t1 = blocks[i]
                t2 = blocks[j]
                # Deterministic authority: t1 must precede t2
                if t1.occurred_end <= t2.occurred_start:
                    delta = t2.occurred_start - t1.occurred_end
                    if delta <= self.temporal_window:
                        candidate_id = f"cand_L0_{t1.block_id}_{t2.block_id}"
                        candidates.append(
                            LongitudinalCandidate(
                                candidate_id=candidate_id,
                                predecessor_block_id=t1.block_id,
                                successor_block_id=t2.block_id,
                                predecessor_time=t1.occurred_end,
                                successor_time=t2.occurred_start,
                                signals=("temporal_precedence",),
                                filter_level="L0",
                                score=1.0,
                            )
                        )
        return candidates

    # -------------------------------------------------------------------------
    # L1: Time + Core Embedding Cosine Similarity
    # -------------------------------------------------------------------------
    def generate_l1(
        self,
        blocks: list[CorpusBlockRecord],
        l0_candidates: list[LongitudinalCandidate] | None = None,
    ) -> list[LongitudinalCandidate]:
        """Filter candidates using Semantic Core dense embedding similarity."""
        if l0_candidates is None:
            l0_candidates = self.generate_l0(blocks)

        block_map = {b.block_id: b for b in blocks}
        candidates = []

        for cand in l0_candidates:
            t1 = block_map[cand.predecessor_block_id]
            t2 = block_map[cand.successor_block_id]

            emb1 = self.get_block_embedding(t1)
            emb2 = self.get_block_embedding(t2)
            sim = cosine_sim(emb1, emb2)

            if sim >= self.l1_cosine_threshold:
                candidates.append(
                    LongitudinalCandidate(
                        candidate_id=f"cand_L1_{t1.block_id}_{t2.block_id}",
                        predecessor_block_id=t1.block_id,
                        successor_block_id=t2.block_id,
                        predecessor_time=t1.occurred_end,
                        successor_time=t2.occurred_start,
                        signals=("temporal_precedence", f"core_cosine_sim_{sim:.3f}"),
                        filter_level="L1",
                        score=float(sim),
                    )
                )

        return candidates

    # -------------------------------------------------------------------------
    # L2: Time + Cognitive Boundary Projections
    # -------------------------------------------------------------------------
    def generate_l2(
        self,
        blocks: list[CorpusBlockRecord],
        l0_candidates: list[LongitudinalCandidate] | None = None,
    ) -> list[LongitudinalCandidate]:
        """Filter candidates using cheap deterministic cognitive boundary projections."""
        if l0_candidates is None:
            l0_candidates = self.generate_l0(blocks)

        block_map = {b.block_id: b for b in blocks}
        candidates = []

        for cand in l0_candidates:
            t1 = block_map[cand.predecessor_block_id]
            t2 = block_map[cand.successor_block_id]

            # 1. Domain/thread check (if same thread or domain)
            same_domain = t1.domain == t2.domain
            same_thread = t1.thread_id == t2.thread_id

            if not same_domain:
                # Fast rejection for cross-domain unrelated noise
                continue

            signals = ["temporal_precedence"]
            score = 0.0

            # 2. Entity Anchor Overlap
            p1_anchors = t1.projections.get("entity_role_anchors", {})
            p2_anchors = t2.projections.get("entity_role_anchors", {})

            e1 = set(p1_anchors.get("key_entities", []) + p1_anchors.get("affected_object", []) + p1_anchors.get("destination_or_location", []))
            e2 = set(p2_anchors.get("key_entities", []) + p2_anchors.get("affected_object", []) + p2_anchors.get("destination_or_location", []))
            anchor_overlap = e1.intersection(e2)

            if anchor_overlap:
                signals.append(f"entity_anchors:{','.join(sorted(anchor_overlap))}")
                score += 0.35

            # 3. Cognitive Tension / Localized Unknowns Match
            t1_unknowns = t1.projections.get("localized_unknowns", [])
            if t1_unknowns:
                # Check if t2 addresses the tension
                t2_content = t2.content
                t2_action = t2.projections.get("action_or_state", {}).get("summary", "")
                tension_addressed = False
                for u in t1_unknowns:
                    # check semantic keyword matching
                    u_words = [w for w in ["按时", "登机", "起飞", "提交", "召开", "批准", "抽血", "割接", "续租", "签字", "开会"] if w in u]
                    if any(w in t2_content or w in t2_action for w in u_words):
                        tension_addressed = True
                        break
                if tension_addressed:
                    signals.append("unresolved_dimension_match")
                    score += 0.40

            # 4. Action/State Transition Cue
            s1 = t1.projections.get("action_or_state", {}).get("status")
            s2 = t2.projections.get("action_or_state", {}).get("status")
            if s1 in {"current_requirement_obligation", "intention_plan"} and s2 in {"completed_past", "cancelled_retracted", "state_observation"}:
                signals.append(f"state_transition:{s1}->{s2}")
                score += 0.30

            # 5. Explicit Revision or Correction Cues
            p2_rev = t2.projections.get("revision_retraction", {})
            p2_comm = t2.projections.get("communicative_act")
            if p2_rev.get("is_revision") or p2_comm == "correction_retraction":
                nature = p2_rev.get("correction_nature", "revision")
                signals.append(f"explicit_revision:{nature}")
                score += 0.45

            # Keyword lexical confirmation
            has_corr_cue = any(kw in t2.content for kw in REVISION_CORRECTION_KEYWORDS)
            has_change_cue = any(kw in t2.content for kw in REVISION_CHANGE_KEYWORDS)
            has_persist_cue = any(kw in t2.content for kw in PERSISTENCE_KEYWORDS)

            if has_corr_cue:
                signals.append("lexical_correction_cue")
                score += 0.30
            if has_change_cue:
                signals.append("lexical_state_change_cue")
                score += 0.30
            if has_persist_cue:
                signals.append("lexical_persistence_cue")
                score += 0.30

            # If same thread and has at least one nontrivial signal
            if same_thread:
                score += 0.20

            # Acceptance threshold for L2
            # Needs at least one structural signal beyond temporal precedence
            if len(signals) > 1 and score >= 0.30:
                candidates.append(
                    LongitudinalCandidate(
                        candidate_id=f"cand_L2_{t1.block_id}_{t2.block_id}",
                        predecessor_block_id=t1.block_id,
                        successor_block_id=t2.block_id,
                        predecessor_time=t1.occurred_end,
                        successor_time=t2.occurred_start,
                        signals=tuple(signals),
                        filter_level="L2",
                        score=min(1.0, float(score)),
                    )
                )

        return candidates
