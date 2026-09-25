"""Retrieval utility evaluator for SemanticBlock v0.3 Benchmark.

Evaluates Stage C Recall Utility against retrieval_queries_v0_3.jsonl:
- Recall@1
- Recall@5
- Mean Reciprocal Rank (MRR)
- Hard-Negative False Retrieval Rate
- Distractor Rate
- Candidate Volume / Rank analysis
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
QUERIES_FILE = BASE_DIR / "retrieval_queries_v0_3.jsonl"


def cosine_sim(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


class RetrievalEvaluator:
    def __init__(self, llm_client: BenchmarkLLMClient) -> None:
        self.client = llm_client
        with open(QUERIES_FILE, "r", encoding="utf-8") as f:
            self.queries = [json.loads(line) for line in f if line.strip()]

    def evaluate_retrieval(
        self,
        split: str,
        arm_id: str,
        indexed_items: dict[str, str],  # item_id (case_id or branch_id) -> compiled representation_text
        fork_group_map: dict[str, str] | None = None,  # branch_id -> fork_group_id
    ) -> dict[str, Any]:
        """Run retrieval evaluation for the given split and compiled arm index."""
        fg_map = fork_group_map or {}

        # 1. Embed all indexed representations
        item_ids = sorted(indexed_items.keys())
        index_embeddings: dict[str, list[float]] = {}
        for iid in item_ids:
            index_embeddings[iid] = self.client.embed_text(indexed_items[iid])

        # 2. Filter queries for this split
        split_queries = [q for q in self.queries if q.get("split") == split]
        if not split_queries:
            return {"split": split, "arm_id": arm_id, "num_queries": 0}

        r1_list: list[float] = []
        r5_list: list[float] = []
        mrr_list: list[float] = []
        hn_false_list: list[float] = []
        distractor_rate_list: list[float] = []
        query_results: list[dict[str, Any]] = []

        for q in split_queries:
            qid = q["query_id"]
            qtext = q["query_text"]
            qvec = self.client.embed_text(qtext)

            # Determine target item IDs
            target_ids = set(q.get("target_case_ids", []))
            target_fg = set(q.get("target_fork_group_ids", []))
            for iid, fg in fg_map.items():
                if fg in target_fg:
                    target_ids.add(iid)

            # Determine hard-negative item IDs
            hn_ids = set(q.get("hard_negative_case_ids", []))
            hn_fg = set(q.get("hard_negative_fork_group_ids", []))
            for iid, fg in fg_map.items():
                if fg in hn_fg:
                    hn_ids.add(iid)

            # Compute similarities against all indexed items
            scores = [(iid, cosine_sim(qvec, index_embeddings[iid])) for iid in item_ids]
            scores.sort(key=lambda x: x[1], reverse=True)
            ranked_ids = [s[0] for s in scores]

            # Find ranks of targets
            target_ranks = [ranked_ids.index(t) + 1 for t in target_ids if t in ranked_ids]
            first_target_rank = min(target_ranks) if target_ranks else 999

            r1 = 1.0 if first_target_rank == 1 else 0.0
            r5 = 1.0 if first_target_rank <= 5 else 0.0
            mrr = 1.0 / first_target_rank if target_ranks else 0.0

            # Check if any hard negative ranked above the first target
            hn_above_target = False
            for hn in hn_ids:
                if hn in ranked_ids:
                    hn_rank = ranked_ids.index(hn) + 1
                    if hn_rank < first_target_rank:
                        hn_above_target = True
                        break

            # Distractor count in top 3 before target
            top3 = ranked_ids[:3]
            distractors_in_top3 = sum(1 for item in top3 if item not in target_ids and item not in hn_ids)
            distractor_rate = distractors_in_top3 / min(3, len(top3))

            r1_list.append(r1)
            r5_list.append(r5)
            mrr_list.append(mrr)
            hn_false_list.append(1.0 if hn_above_target else 0.0)
            distractor_rate_list.append(distractor_rate)

            query_results.append({
                "query_id": qid,
                "query_type": q.get("query_type"),
                "query_text": qtext,
                "first_target_rank": first_target_rank,
                "recall_at_1": r1,
                "recall_at_5": r5,
                "mrr": mrr,
                "hard_negative_false_retrieval": hn_above_target,
                "top_retrieved": scores[:5],
            })

        return {
            "split": split,
            "arm_id": arm_id,
            "num_queries": len(split_queries),
            "recall_at_1": float(np.mean(r1_list)),
            "recall_at_5": float(np.mean(r5_list)),
            "mrr": float(np.mean(mrr_list)),
            "hard_negative_false_retrieval_rate": float(np.mean(hn_false_list)),
            "mean_distractor_rate_in_top3": float(np.mean(distractor_rate_list)),
            "query_details": query_results,
        }
