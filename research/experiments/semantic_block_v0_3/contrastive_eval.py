"""Contrastive evaluation for SemanticBlock v0.3 Benchmark.

Tests:
1. Same meaning, different surface -> structurally compatible (Equivalence Groups)
2. Similar surface, different meaning -> structurally separable (Hard-Negative Groups)

Calculates:
- Mean equivalence pair cosine similarity
- Mean hard-negative pair cosine similarity
- Separation margin (EQ - HN)
- Nearest-neighbor recovery rate within equivalence groups
- Granularity collapse rate
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.experiments.semantic_block_v0_3.llm_client import BenchmarkLLMClient

BASE_DIR = Path(__file__).parent
CONTRAST_FILE = BASE_DIR / "contrast_groups_v0_3.json"


def cosine_sim(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


class ContrastiveEvaluator:
    def __init__(self, llm_client: BenchmarkLLMClient) -> None:
        self.client = llm_client
        with open(CONTRAST_FILE, "r", encoding="utf-8") as f:
            self.contrast_data = json.load(f)
        self.eq_groups = self.contrast_data.get("equivalence_groups", [])
        self.hn_groups = self.contrast_data.get("hard_negative_groups", [])

    def evaluate_contrastive(
        self,
        split: str,
        arm_id: str,
        compiled_representations: dict[str, str],  # case_id -> representation_text
    ) -> dict[str, Any]:
        """Evaluate contrastive structure for an arm on the specified split."""
        # Embed all representations
        case_ids = sorted(compiled_representations.keys())
        embeddings: dict[str, list[float]] = {}
        for cid in case_ids:
            text = compiled_representations[cid]
            embeddings[cid] = self.client.embed_text(text)

        # 1. Equivalence groups (same meaning, different surface)
        eq_sims: list[float] = []
        eq_nn_recalls: list[float] = []
        eq_details: list[dict[str, Any]] = []

        for grp in self.eq_groups:
            cids = grp["case_ids"]
            # Check if all members are present in this split
            if not all(cid in embeddings for cid in cids):
                continue

            # Compute pairwise similarities
            for i in range(len(cids)):
                for j in range(i + 1, len(cids)):
                    c1, c2 = cids[i], cids[j]
                    sim = cosine_sim(embeddings[c1], embeddings[c2])
                    eq_sims.append(sim)

                    # Nearest neighbor rank of c2 from c1
                    all_sims = [(other, cosine_sim(embeddings[c1], embeddings[other])) for other in case_ids if other != c1]
                    all_sims.sort(key=lambda x: x[1], reverse=True)
                    ranked_others = [x[0] for x in all_sims]
                    rank = ranked_others.index(c2) + 1 if c2 in ranked_others else -1
                    is_top1 = (rank == 1)
                    is_top3 = (rank <= 3 and rank > 0)
                    eq_nn_recalls.append(1.0 if is_top1 else 0.0)

                    eq_details.append({
                        "group_id": grp["group_id"],
                        "case_1": c1,
                        "case_2": c2,
                        "similarity": sim,
                        "rank_in_corpus": rank,
                        "top1_match": is_top1,
                        "top3_match": is_top3,
                    })

        # 2. Hard-negative groups (similar surface, different meaning)
        hn_sims: list[float] = []
        hn_details: list[dict[str, Any]] = []

        for grp in self.hn_groups:
            if grp.get("split") != split:
                continue
            cids = [cid for cid in grp["case_ids"] if cid in embeddings]
            if len(cids) < 2:
                continue

            for i in range(len(cids)):
                for j in range(i + 1, len(cids)):
                    c1, c2 = cids[i], cids[j]
                    sim = cosine_sim(embeddings[c1], embeddings[c2])
                    hn_sims.append(sim)
                    hn_details.append({
                        "group_id": grp["group_id"],
                        "case_1": c1,
                        "case_2": c2,
                        "similarity": sim,
                    })

        mean_eq_sim = float(np.mean(eq_sims)) if eq_sims else 0.0
        mean_hn_sim = float(np.mean(hn_sims)) if hn_sims else 0.0
        margin = mean_eq_sim - mean_hn_sim
        eq_top1_acc = float(np.mean(eq_nn_recalls)) if eq_nn_recalls else 0.0

        # Granularity collapse rate: fraction of hard negative pairs having similarity higher than mean equivalence similarity
        collapse_count = sum(1 for s in hn_sims if s > mean_eq_sim) if eq_sims else 0
        collapse_rate = collapse_count / len(hn_sims) if hn_sims else 0.0

        return {
            "split": split,
            "arm_id": arm_id,
            "mean_equivalence_similarity": mean_eq_sim,
            "mean_hard_negative_similarity": mean_hn_sim,
            "separation_margin": margin,
            "equivalence_nn_top1_accuracy": eq_top1_acc,
            "granularity_collapse_rate": collapse_rate,
            "num_equivalence_pairs": len(eq_sims),
            "num_hard_negative_pairs": len(hn_sims),
            "equivalence_details": eq_details,
            "hard_negative_details": hn_details,
        }
