"""Stage 1: Latent candidate discovery for Issue #25.

Three baselines:
  B0 — deterministic time ordering only
  B1 — time + Semantic Core embedding similarity
  B2 — time + Core + cognitive-boundary signals (from SemanticBlock representation)

Key constraint: NO oracle fields (thread_id, domain, correction_nature, gold relation).
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta

from research.experiments.path_b_production_issue_25.contracts import (
    DiscoveredCandidate,
    ProductionMemoryView,
)


# ---------------------------------------------------------------------------
# Embedding infrastructure (production-shaped: sentence-level cosine)
# ---------------------------------------------------------------------------

def _simple_token_overlap_vector(text: str) -> dict[str, float]:
    """Character bigram bag for deterministic pseudo-embedding.

    In production this would be a real embedding model. Here we use
    character bigrams to give a deterministic reproducible similarity
    signal without requiring an external model.
    """
    # Extract Chinese characters and latin words
    chars = re.findall(r'[\u4e00-\u9fff]', text)
    words = re.findall(r'[a-zA-Z]+', text.lower())
    bigrams: dict[str, float] = {}
    for i in range(len(chars) - 1):
        bg = chars[i] + chars[i + 1]
        bigrams[bg] = bigrams.get(bg, 0) + 1.0
    for w in words:
        bigrams[f"w:{w}"] = bigrams.get(f"w:{w}", 0) + 1.0
    # Normalize
    norm = math.sqrt(sum(v * v for v in bigrams.values())) or 1.0
    return {k: v / norm for k, v in bigrams.items()}


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity between two sparse vectors."""
    keys = set(a) & set(b)
    if not keys:
        return 0.0
    dot = sum(a[k] * b[k] for k in keys)
    return dot  # both already normalized


# ---------------------------------------------------------------------------
# Cognitive boundary signal extractors (production-available, no oracle)
# ---------------------------------------------------------------------------

# Lexical cues extracted from content alone (no projection taxonomy expansion)
_PLAN_FUTURE_CUES = re.compile(
    r'计划|打算|准备|约了|下[周个]|明[天年]|将来|以后|预定|需要订|预约'
)
_OUTCOME_CUES = re.compile(
    r'已经|完成|结束|到了|出来了|通过|成功|失败|没过|取消|不行|办好|拿到|收到'
)
_CORRECTION_CUES = re.compile(
    r'说错了|更正|纠正|其实|原来|不是.*而是|搞错|弄错|之前说错'
)
_PERSISTENCE_CUES = re.compile(
    r'还在|仍然|继续|还没|依然|一直|没变|照旧|还是'
)
_UNCERTAINTY_CUES = re.compile(
    r'不知道|可能|也许|大概|待定|不确定|等.*结果|审批中|还没.*通知|暗示'
)
_RESOLUTION_CUES = re.compile(
    r'确定|正式|结果|通知|批准|决定|明确|确认'
)


def _extract_boundary_signals(
    predecessor: ProductionMemoryView,
    successor: ProductionMemoryView,
) -> tuple[list[str], float]:
    """Extract cognitive-boundary signals from content and temporal coordinates.

    Returns (signal_list, additive_score).
    Uses ONLY production-available information:
      - content text
      - temporal coordinates (both axes)
      - provenance (source_type, channel — no oracle fields)
    """
    signals: list[str] = []
    score = 0.0

    p_content = predecessor.content
    s_content = successor.content

    # 1. Semantic continuity: shared Chinese character overlap (entity proxy)
    p_chars = set(re.findall(r'[\u4e00-\u9fff]{2,}', p_content))
    s_chars = set(re.findall(r'[\u4e00-\u9fff]{2,}', s_content))
    # Extract multi-char tokens (2+ chars) as entity proxies
    p_tokens = set()
    s_tokens = set()
    for c in p_chars:
        for i in range(len(c) - 1):
            p_tokens.add(c[i:i+2])
    for c in s_chars:
        for i in range(len(c) - 1):
            s_tokens.add(c[i:i+2])
    common_tokens = p_tokens & s_tokens
    if len(common_tokens) >= 2:
        signals.append(f"entity_overlap:{len(common_tokens)}")
        score += min(0.35, len(common_tokens) * 0.05)

    # 2. Plan-outcome arc detection
    if _PLAN_FUTURE_CUES.search(p_content) and _OUTCOME_CUES.search(s_content):
        signals.append("plan_outcome_arc")
        score += 0.3

    # 3. Correction detection
    if _CORRECTION_CUES.search(s_content):
        signals.append("correction_cue")
        score += 0.4

    # 4. Persistence detection
    if _PERSISTENCE_CUES.search(s_content) and len(common_tokens) >= 2:
        signals.append("persistence_cue")
        score += 0.25

    # 5. Uncertainty → resolution arc
    if _UNCERTAINTY_CUES.search(p_content) and _RESOLUTION_CUES.search(s_content):
        signals.append("uncertainty_resolution_arc")
        score += 0.35

    # 6. Axis B (proposition validity) overlap
    p_sem = predecessor.temporal.semantic_time
    s_sem = successor.temporal.semantic_time
    if p_sem is not None and s_sem is not None:
        sem_delta = abs((p_sem - s_sem).total_seconds())
        if sem_delta < 86400 * 14:  # within 2 weeks of each other semantically
            signals.append("semantic_time_proximity")
            score += 0.15

    # 7. Axis B validity window overlap
    p_vs, p_ve = predecessor.temporal.valid_start, predecessor.temporal.valid_end
    s_vs, s_ve = successor.temporal.valid_start, successor.temporal.valid_end
    if p_vs and p_ve and s_vs and s_ve:
        if p_vs <= s_ve and s_vs <= p_ve:
            signals.append("validity_window_overlap")
            score += 0.2

    return signals, score


# ---------------------------------------------------------------------------
# Candidate Generator
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CandidateGeneratorConfig:
    temporal_window_days: int = 45
    b1_cosine_threshold: float = 0.08
    b2_min_score: float = 0.25
    b2_min_signals: int = 1


class CandidateGenerator:
    """Stage 1 latent candidate discovery.

    Generates candidates at three baseline levels:
      B0 — time only
      B1 — time + embedding
      B2 — time + embedding + cognitive boundary signals
    """

    def __init__(self, config: CandidateGeneratorConfig | None = None) -> None:
        self.config = config or CandidateGeneratorConfig()
        self._embedding_cache: dict[str, dict[str, float]] = {}

    def _get_embedding(self, view: ProductionMemoryView) -> dict[str, float]:
        if view.memory_id not in self._embedding_cache:
            self._embedding_cache[view.memory_id] = _simple_token_overlap_vector(
                view.content
            )
        return self._embedding_cache[view.memory_id]

    # ----- B0: Time only -----

    def generate_b0(
        self, views: Sequence[ProductionMemoryView]
    ) -> list[DiscoveredCandidate]:
        """Deterministic temporal ordering/proximity only."""
        window = timedelta(days=self.config.temporal_window_days)
        candidates = []
        sorted_views = sorted(views, key=lambda v: v.temporal.received_at)

        for i, pred in enumerate(sorted_views):
            for j in range(i + 1, len(sorted_views)):
                succ = sorted_views[j]
                delta = succ.temporal.received_at - pred.temporal.received_at
                if delta > window:
                    break  # sorted, so all further are beyond window
                candidates.append(
                    DiscoveredCandidate(
                        candidate_id=f"B0_{pred.memory_id}__{succ.memory_id}",
                        predecessor_id=pred.memory_id,
                        successor_id=succ.memory_id,
                        predecessor_time=pred.temporal.received_at,
                        successor_time=succ.temporal.received_at,
                        signals=("temporal_precedence",),
                        baseline_level="B0",
                        score=1.0 - (delta.total_seconds() / window.total_seconds()),
                    )
                )

        return candidates

    # ----- B1: Time + Semantic Core embedding -----

    def generate_b1(
        self,
        views: Sequence[ProductionMemoryView],
        b0_candidates: list[DiscoveredCandidate] | None = None,
    ) -> list[DiscoveredCandidate]:
        """Filter B0 candidates using semantic embedding similarity."""
        if b0_candidates is None:
            b0_candidates = self.generate_b0(views)

        view_map = {v.memory_id: v for v in views}
        candidates = []

        for cand in b0_candidates:
            pred = view_map[cand.predecessor_id]
            succ = view_map[cand.successor_id]
            emb_p = self._get_embedding(pred)
            emb_s = self._get_embedding(succ)
            sim = _cosine_similarity(emb_p, emb_s)

            if sim >= self.config.b1_cosine_threshold:
                candidates.append(
                    DiscoveredCandidate(
                        candidate_id=f"B1_{pred.memory_id}__{succ.memory_id}",
                        predecessor_id=pred.memory_id,
                        successor_id=succ.memory_id,
                        predecessor_time=pred.temporal.received_at,
                        successor_time=succ.temporal.received_at,
                        signals=("temporal_precedence", f"cosine_sim_{sim:.3f}"),
                        baseline_level="B1",
                        score=sim,
                    )
                )

        return candidates

    # ----- B2: Time + Core + cognitive-boundary signals -----

    def generate_b2(
        self,
        views: Sequence[ProductionMemoryView],
        b0_candidates: list[DiscoveredCandidate] | None = None,
    ) -> list[DiscoveredCandidate]:
        """Filter using cognitive boundary signals from content + temporal axes."""
        if b0_candidates is None:
            b0_candidates = self.generate_b0(views)

        view_map = {v.memory_id: v for v in views}
        candidates = []

        for cand in b0_candidates:
            pred = view_map[cand.predecessor_id]
            succ = view_map[cand.successor_id]

            # Embedding similarity
            emb_p = self._get_embedding(pred)
            emb_s = self._get_embedding(succ)
            sim = _cosine_similarity(emb_p, emb_s)

            # Cognitive boundary signals
            boundary_signals, boundary_score = _extract_boundary_signals(pred, succ)

            # Combined signals
            all_signals = ["temporal_precedence"]
            combined_score = 0.0

            if sim >= self.config.b1_cosine_threshold:
                all_signals.append(f"cosine_sim_{sim:.3f}")
                combined_score += sim * 0.3

            all_signals.extend(boundary_signals)
            combined_score += boundary_score

            # Accept if has enough signals above threshold
            non_temporal_signals = len(all_signals) - 1  # minus temporal_precedence
            if (
                non_temporal_signals >= self.config.b2_min_signals
                and combined_score >= self.config.b2_min_score
            ):
                candidates.append(
                    DiscoveredCandidate(
                        candidate_id=f"B2_{pred.memory_id}__{succ.memory_id}",
                        predecessor_id=pred.memory_id,
                        successor_id=succ.memory_id,
                        predecessor_time=pred.temporal.received_at,
                        successor_time=succ.temporal.received_at,
                        signals=tuple(all_signals),
                        baseline_level="B2",
                        score=min(1.0, combined_score),
                    )
                )

        return candidates
