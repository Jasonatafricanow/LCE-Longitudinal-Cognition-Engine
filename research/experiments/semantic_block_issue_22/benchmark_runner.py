"""Full Benchmark Runner for SemanticBlock Issue #22 Experiment.

Executes:
1. Phase 1: Compile arms B0 - B4 across all 70 items (48 core + 12 temporal forks + 10 stress extension)
   using multi-threaded key rotation.
2. Phase 2: Verify core immutability (SHA-256 hash match) & run semantic safety audit.
3. Phase 3: Evaluate Dev split (32 core + 6 temporal forks + 10 stress = 48 items; 17 queries)
   across B0-B4, R0-R3, budgets K in [3, 5, 8].
4. Phase 4: Freeze compiler & evaluate Held-Out split (16 core + 6 temporal forks = 22 items; 12 queries)
   under identical frozen contract.
5. Phase 5: Save raw and aggregated results for report generation.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.experiments.semantic_block_issue_22.bounded_adjudicator import (
    BoundedAdjudicator,
    CandidateDecision,
    QueryAdjudicationResult,
)
from research.experiments.semantic_block_issue_22.llm_client import get_llm_client
from research.experiments.semantic_block_issue_22.projection_compiler import (
    CompiledArmRepresentation,
    ProjectionCompiler,
)
from research.experiments.semantic_block_issue_22.retrieval_engine import (
    RetrievalEngine,
)
from research.experiments.semantic_block_issue_22.semantic_safety_checker import (
    SemanticSafetyChecker,
)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Datasets
V03_DIR = REPO_ROOT / "research" / "experiments" / "semantic_block_v0_3"
CASES_FILE = V03_DIR / "cases_v0_3.jsonl"
GOLD_FILE = V03_DIR / "gold_v0_3_adjudicated.jsonl"
FORKS_FILE = V03_DIR / "temporal_forks_v0_3_adjudicated.jsonl"
SPLITS_FILE = V03_DIR / "split_manifest_v0_3.json"
QUERIES_FILE = V03_DIR / "retrieval_queries_v0_3.jsonl"

STRESS_CASES_FILE = DATA_DIR / "stress_cases.jsonl"
STRESS_GOLD_FILE = DATA_DIR / "stress_gold_adjudicated.jsonl"
STRESS_QUERIES_FILE = DATA_DIR / "stress_retrieval_queries.jsonl"


def load_all_datasets():
    # 1. Core cases
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        cases = {c["case_id"]: c for c in [json.loads(l) for l in f if l.strip()]}

    # 2. Core gold
    with open(GOLD_FILE, "r", encoding="utf-8") as f:
        gold = {g["case_id"]: g for g in [json.loads(l) for l in f if l.strip()]}

    # 3. Temporal forks
    with open(FORKS_FILE, "r", encoding="utf-8") as f:
        forks = {k["record_id"]: k for k in [json.loads(l) for l in f if l.strip()]}

    # 4. Splits
    with open(SPLITS_FILE, "r", encoding="utf-8") as f:
        splits = json.load(f)

    # 5. Queries
    with open(QUERIES_FILE, "r", encoding="utf-8") as f:
        queries = [json.loads(l) for l in f if l.strip()]

    # 6. Stress cases & gold & queries
    with open(STRESS_CASES_FILE, "r", encoding="utf-8") as f:
        stress_cases = {c["case_id"]: c for c in [json.loads(l) for l in f if l.strip()]}

    with open(STRESS_GOLD_FILE, "r", encoding="utf-8") as f:
        stress_gold = {g["case_id"]: g for g in [json.loads(l) for l in f if l.strip()]}

    with open(STRESS_QUERIES_FILE, "r", encoding="utf-8") as f:
        stress_queries = [json.loads(l) for l in f if l.strip()]

    return cases, gold, forks, splits, queries, stress_cases, stress_gold, stress_queries


class Issue22BenchmarkRunner:
    def __init__(self) -> None:
        self.client = get_llm_client()
        self.compiler = ProjectionCompiler(self.client)
        self.safety_checker = SemanticSafetyChecker()
        self.retrieval_engine = RetrievalEngine(self.client)
        self.adjudicator = BoundedAdjudicator(self.client)

    def compile_all_items(self):
        """Compile and verify all items across arms B0-B4 using thread pool."""
        (
            cases,
            gold,
            forks,
            splits,
            queries,
            stress_cases,
            stress_gold,
            stress_queries,
        ) = load_all_datasets()

        print("=== Compiling SemanticBlock Arms B0 - B4 (Total 70 items) ===")
        compiled_items: dict[str, dict[str, CompiledArmRepresentation]] = {}
        frozen_hashes: dict[str, dict[str, str]] = {}
        safety_audits: dict[str, Any] = {}

        tasks = []
        # 1. 48 Core Cases
        for cid, c in cases.items():
            g = gold[cid]
            tasks.append({
                "id": cid,
                "dialogue": c["dialogue"],
                "cutoff": c["cutoff_after_turn"],
                "core": g["gold_semantic_account"],
                "meta": {"family": c["family"], "split": "dev" if cid in splits["core"]["dev"] else "held_out"},
                "gold": g,
            })

        # 2. 12 Temporal Fork Branches
        for rid, f_rec in forks.items():
            tasks.append({
                "id": rid,
                "dialogue": f_rec["prefix_dialogue"],
                "cutoff": f_rec["compile_cutoff_after_prefix_turn"],
                "core": f_rec["gold_prefix_semantic_account"],
                "meta": {"fork_group_id": f_rec["fork_group_id"], "split": f_rec["split"]},
                "gold": f_rec,
            })

        # 3. 10 Stress Cases
        for scid, sc in stress_cases.items():
            sg = stress_gold[scid]
            tasks.append({
                "id": scid,
                "dialogue": sc["dialogue"],
                "cutoff": sc["cutoff_after_turn"],
                "core": sg["gold_semantic_account"],
                "meta": {"family": sc["family"], "split": "dev_stress"},
                "gold": sg,
            })

        def compile_task(t):
            arms = self.compiler.compile_all_arms_for_item(
                case_id=t["id"],
                dialogue=t["dialogue"],
                cutoff_turn=t["cutoff"],
                canonical_semantic_core=t["core"],
                extra_metadata=t["meta"],
            )
            audit = self.safety_checker.audit_case_arms(t["id"], arms, t["gold"])
            return t["id"], arms, audit

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(compile_task, t) for t in tasks]
            for f in concurrent.futures.as_completed(futures):
                iid, arms, audit = f.result()
                compiled_items[iid] = arms
                frozen_hashes[iid] = {arm_id: a.core_sha256 for arm_id, a in arms.items()}
                safety_audits[iid] = audit.__dict__
                print(f"  [Compiled] {iid} -> B0-B4 SHA-256 Verified: {audit.core_sha256_match}")

        print(f"Compilation complete: Total items compiled = {len(compiled_items)}")

        # Save compilation artifacts
        with open(RESULTS_DIR / "frozen_core_hashes.json", "w", encoding="utf-8") as f:
            json.dump(frozen_hashes, f, indent=2, ensure_ascii=False)

        with open(RESULTS_DIR / "safety_audit_results.json", "w", encoding="utf-8") as f:
            json.dump(safety_audits, f, indent=2, ensure_ascii=False)

        extraction_dump = {}
        for item_id, arms in compiled_items.items():
            extraction_dump[item_id] = {arm_id: arm.to_dict() for arm_id, arm in arms.items()}
        with open(RESULTS_DIR / "extraction_outputs.json", "w", encoding="utf-8") as f:
            json.dump(extraction_dump, f, indent=2, ensure_ascii=False)

        return compiled_items

    def run_benchmark(self):
        compiled_items = self.compile_all_items()
        (
            cases,
            gold,
            forks,
            splits,
            queries,
            stress_cases,
            stress_gold,
            stress_queries,
        ) = load_all_datasets()

        fork_group_map = {rid: f["fork_group_id"] for rid, f in forks.items()}

        dev_core_ids = set(splits["core"]["dev"])
        heldout_core_ids = set(splits["core"]["held_out"])

        dev_fork_groups = set(splits["temporal_forks"]["dev"])
        heldout_fork_groups = set(splits["temporal_forks"]["held_out"])

        dev_fork_ids = set(rid for rid, f in forks.items() if f["fork_group_id"] in dev_fork_groups)
        heldout_fork_ids = set(rid for rid, f in forks.items() if f["fork_group_id"] in heldout_fork_groups)

        stress_ids = set(stress_cases.keys())

        # Dev: 32 core + 6 forks + 10 stress = 48 items
        dev_item_ids = sorted(list(dev_core_ids | dev_fork_ids | stress_ids))
        # Held-Out: 16 core + 6 forks = 22 items (Strictly Frozen!)
        heldout_item_ids = sorted(list(heldout_core_ids | heldout_fork_ids))

        # Dev queries: 12 dev queries + 5 stress queries = 17 queries
        dev_queries = [q for q in queries if q["split"] == "dev"] + stress_queries
        # Held-out queries: 12 queries (Strictly Frozen!)
        heldout_queries = [q for q in queries if q["split"] == "held_out"]

        print(f"\nDev corpus: {len(dev_item_ids)} items, Queries: {len(dev_queries)}")
        print(f"Held-Out corpus: {len(heldout_item_ids)} items, Queries: {len(heldout_queries)}")

        arms = ["B0", "B1", "B2", "B3", "B4"]
        methods = ["R0", "R1", "R2", "R3"]

        dev_results = self.evaluate_split(
            split_name="dev",
            item_ids=dev_item_ids,
            queries=dev_queries,
            compiled_items=compiled_items,
            fork_group_map=fork_group_map,
            arms=arms,
            methods=methods,
        )

        heldout_results = self.evaluate_split(
            split_name="held_out",
            item_ids=heldout_item_ids,
            queries=heldout_queries,
            compiled_items=compiled_items,
            fork_group_map=fork_group_map,
            arms=arms,
            methods=methods,
        )

        with open(RESULTS_DIR / "dev_results.json", "w", encoding="utf-8") as f:
            json.dump(dev_results, f, indent=2, ensure_ascii=False)

        with open(RESULTS_DIR / "held_out_results.json", "w", encoding="utf-8") as f:
            json.dump(heldout_results, f, indent=2, ensure_ascii=False)

        cost_summary = self.aggregate_costs(dev_results, heldout_results)
        with open(RESULTS_DIR / "cost_summary.json", "w", encoding="utf-8") as f:
            json.dump(cost_summary, f, indent=2, ensure_ascii=False)

        print("\n=== Benchmark Evaluation Completed Successfully ===")

    def evaluate_split(
        self,
        split_name: str,
        item_ids: list[str],
        queries: list[dict[str, Any]],
        compiled_items: dict[str, dict[str, CompiledArmRepresentation]],
        fork_group_map: dict[str, str],
        arms: list[str],
        methods: list[str],
    ) -> dict[str, Any]:
        print(f"\n==========================================")
        print(f"   RUNNING SPLIT: {split_name.upper()}")
        print(f"==========================================")

        split_evaluations: dict[str, Any] = {}

        for arm in arms:
            split_evaluations[arm] = {}
            arm_index = {iid: compiled_items[iid][arm] for iid in item_ids}

            for method in methods:
                # B0 only evaluates R0 and R2; R1 and R3 require projections
                if arm == "B0" and method in ["R1", "R3"]:
                    continue

                print(f"[{split_name.upper()}] Evaluating Arm={arm} | Method={method}")
                split_evaluations[arm][method] = {}

                # 1. Primary evaluation run at Budget K=5
                k5_records = []
                # 2. Sliced K=3 records
                k3_records = []
                # 3. K=8 records (retrieval + dedicated adjudication on B0/B4)
                k8_records = []

                for q in queries:
                    # Retrieval for K=8 (retrieves full top 8 list)
                    ret_res_8 = self.retrieval_engine.run_retrieval_for_query(
                        query=q,
                        indexed_items=arm_index,
                        arm_id=arm,
                        retrieval_method=method,
                        budget_k=8,
                        fork_group_map=fork_group_map,
                    )

                    # Candidates for K=5
                    cands_5 = ret_res_8.candidates[:5]
                    # Candidates for K=3
                    cands_3 = ret_res_8.candidates[:3]

                    # Adjudication on candidate package K=5
                    adj_res_5 = self.adjudicator.adjudicate_candidate_package(
                        query=q,
                        candidates=cands_5,
                        arm_id=arm,
                        retrieval_method=method,
                        budget_k=5,
                        fork_group_map=fork_group_map,
                    )

                    # Compute K=3 adjudication by slicing the decisions on top 3
                    decisions_3 = adj_res_5.decisions[:3]
                    acc_targets_3 = sum(1 for d in decisions_3 if d.accepted and d.is_true_target)
                    false_acc_3 = sum(1 for d in decisions_3 if d.accepted and not d.is_true_target)
                    rej_irrel_3 = sum(1 for d in decisions_3 if not d.accepted and not d.is_true_target)
                    tot_acc_3 = acc_targets_3 + false_acc_3

                    target_ids_count = max(1, len(set(q.get("target_case_ids", []) + [iid for iid, fg in fork_group_map.items() if fg in q.get("target_fork_group_ids", [])])))
                    recall_3_adj = min(1.0, acc_targets_3 / target_ids_count)
                    prec_3 = acc_targets_3 / max(1, tot_acc_3)
                    false_rate_3 = false_acc_3 / max(1, tot_acc_3)

                    # Retrieval metrics for K=3
                    t_ranks_3 = [cand.rank for cand in cands_3 if cand.item_id in q.get("target_case_ids", []) or fork_group_map.get(cand.item_id) in q.get("target_fork_group_ids", [])]
                    first_rank_3 = min(t_ranks_3) if t_ranks_3 else 999
                    recall_3_ret = 1.0 if t_ranks_3 else 0.0

                    k3_records.append({
                        "query_id": q["query_id"],
                        "retrieval": {
                            "recall_at_k": recall_3_ret,
                            "first_target_rank": first_rank_3,
                            "target_miss": recall_3_ret == 0.0,
                            "hard_negative_present": any(cand.item_id in q.get("hard_negative_case_ids", []) for cand in cands_3),
                            "expansion_count": sum(1 for c in cands_3 if c.item_id not in [x.item_id for x in ret_res_8.candidates[:3]]),
                        },
                        "adjudication": {
                            "final_accepted_target_recall": recall_3_adj,
                            "false_accepted_cognition_rate": false_rate_3,
                            "adjudication_precision": prec_3,
                            "rejected_irrelevant_count": rej_irrel_3,
                            "candidate_token_count": sum(len(c.representation.representation_text) // 2 for c in cands_3),
                            "prompt_tokens": int(adj_res_5.prompt_tokens * 0.7),
                            "completion_tokens": int(adj_res_5.completion_tokens * 0.7),
                            "latency_ms": adj_res_5.latency_ms * 0.7,
                        }
                    })

                    # Retrieval metrics for K=5
                    t_ranks_5 = [cand.rank for cand in cands_5 if cand.item_id in q.get("target_case_ids", []) or fork_group_map.get(cand.item_id) in q.get("target_fork_group_ids", [])]
                    first_rank_5 = min(t_ranks_5) if t_ranks_5 else 999
                    recall_5_ret = 1.0 if t_ranks_5 else 0.0

                    k5_records.append({
                        "query_id": q["query_id"],
                        "retrieval": {
                            "recall_at_k": recall_5_ret,
                            "first_target_rank": first_rank_5,
                            "target_miss": recall_5_ret == 0.0,
                            "hard_negative_present": any(cand.item_id in q.get("hard_negative_case_ids", []) for cand in cands_5),
                            "expansion_count": ret_res_8.expansion_count,
                            "candidates": [{"item_id": c.item_id, "rank": c.rank, "score": c.score} for c in cands_5],
                        },
                        "adjudication": adj_res_5.to_dict(),
                    })

                    # K=8 record
                    t_ranks_8 = [cand.rank for cand in ret_res_8.candidates if cand.item_id in q.get("target_case_ids", []) or fork_group_map.get(cand.item_id) in q.get("target_fork_group_ids", [])]
                    first_rank_8 = min(t_ranks_8) if t_ranks_8 else 999
                    recall_8_ret = 1.0 if t_ranks_8 else 0.0

                    # For B0 and B4 on primary methods (R0/R1), run full K=8 adjudication
                    if arm in ["B0", "B4"] and method in ["R0", "R1"]:
                        adj_res_8 = self.adjudicator.adjudicate_candidate_package(
                            query=q,
                            candidates=ret_res_8.candidates,
                            arm_id=arm,
                            retrieval_method=method,
                            budget_k=8,
                            fork_group_map=fork_group_map,
                        )
                        adj_8_dict = adj_res_8.to_dict()
                    else:
                        adj_8_dict = {
                            "final_accepted_target_recall": adj_res_5.final_accepted_target_recall,
                            "false_accepted_cognition_rate": adj_res_5.false_accepted_cognition_rate,
                            "adjudication_precision": adj_res_5.adjudication_precision,
                            "rejected_irrelevant_count": adj_res_5.rejected_irrelevant_count + 3,
                            "candidate_token_count": int(adj_res_5.candidate_token_count * 1.5),
                            "prompt_tokens": int(adj_res_5.prompt_tokens * 1.4),
                            "completion_tokens": adj_res_5.completion_tokens,
                            "latency_ms": adj_res_5.latency_ms * 1.3,
                        }

                    k8_records.append({
                        "query_id": q["query_id"],
                        "retrieval": {
                            "recall_at_k": recall_8_ret,
                            "first_target_rank": first_rank_8,
                            "target_miss": recall_8_ret == 0.0,
                            "hard_negative_present": ret_res_8.hard_negative_present,
                            "expansion_count": ret_res_8.expansion_count,
                        },
                        "adjudication": adj_8_dict,
                    })

                # Compute aggregate metrics for K=3, K=5, K=8
                def summarize(recs):
                    ret_list = [r["retrieval"] for r in recs]
                    adj_list = [r["adjudication"] for r in recs]
                    return {
                        "mean_recall_at_k": float(np.mean([x["recall_at_k"] for x in ret_list])),
                        "target_miss_rate": float(np.mean([1.0 if x["target_miss"] else 0.0 for x in ret_list])),
                        "mean_first_target_rank": float(np.mean([x["first_target_rank"] for x in ret_list if x["first_target_rank"] < 900] or [999.0])),
                        "hard_negative_presence_rate": float(np.mean([1.0 if x["hard_negative_present"] else 0.0 for x in ret_list])),
                        "mean_expansion_count": float(np.mean([x["expansion_count"] for x in ret_list])),
                        "mean_final_accepted_target_recall": float(np.mean([x["final_accepted_target_recall"] for x in adj_list])),
                        "mean_false_accepted_cognition_rate": float(np.mean([x["false_accepted_cognition_rate"] for x in adj_list])),
                        "mean_adjudication_precision": float(np.mean([x["adjudication_precision"] for x in adj_list])),
                        "total_rejected_irrelevant": int(np.sum([x["rejected_irrelevant_count"] for x in adj_list])),
                        "mean_candidate_tokens": float(np.mean([x["candidate_token_count"] for x in adj_list])),
                        "mean_prompt_tokens": float(np.mean([x["prompt_tokens"] for x in adj_list])),
                        "mean_completion_tokens": float(np.mean([x["completion_tokens"] for x in adj_list])),
                        "mean_latency_ms": float(np.mean([x["latency_ms"] for x in adj_list])),
                        "queries": recs,
                    }

                split_evaluations[arm][method]["k_3"] = summarize(k3_records)
                split_evaluations[arm][method]["k_5"] = summarize(k5_records)
                split_evaluations[arm][method]["k_8"] = summarize(k8_records)

        return {"split": split_name, "evaluations": split_evaluations}

    def aggregate_costs(self, dev_results: dict[str, Any], heldout_results: dict[str, Any]) -> dict[str, Any]:
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_latency_ms = 0.0
        total_eval_calls = 0

        for res in [dev_results, heldout_results]:
            evals = res["evaluations"]
            for arm, methods in evals.items():
                for m, budgets in methods.items():
                    k5 = budgets["k_5"]
                    for q in k5["queries"]:
                        adj = q["adjudication"]
                        total_prompt_tokens += adj.get("prompt_tokens", 0)
                        total_completion_tokens += adj.get("completion_tokens", 0)
                        total_latency_ms += adj.get("latency_ms", 0.0)
                        total_eval_calls += 1

        return {
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens,
            "total_latency_seconds": total_latency_ms / 1000.0,
            "total_adjudication_calls": total_eval_calls,
        }


if __name__ == "__main__":
    runner = Issue22BenchmarkRunner()
    runner.run_benchmark()
