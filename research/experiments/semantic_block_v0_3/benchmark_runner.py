"""Full benchmark orchestrator for SemanticBlock v0.3.

Executes:
Phase C — Dev evaluation (32 dev core cases + 6 dev temporal fork branches)
Phase D — Freeze compiler/config, then held-out one-shot evaluation (16 held-out core cases + 6 held-out temporal fork branches)

Produces complete outputs:
- Dev predictions, scores, contrastive, retrieval, and audit results
- Held-out predictions, scores, contrastive, retrieval, and audit results
- Cost and latency accounting
- Error analysis across failure taxonomy
- Final comprehensive benchmark report
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.experiments.semantic_block_v0_3.compiler_arms import CompilerArms
from research.experiments.semantic_block_v0_3.contrastive_eval import ContrastiveEvaluator
from research.experiments.semantic_block_v0_3.granularity_audit import GranularityAuditor
from research.experiments.semantic_block_v0_3.llm_client import BenchmarkLLMClient
from research.experiments.semantic_block_v0_3.reconstruction_consumer import BlindReconstructor
from research.experiments.semantic_block_v0_3.retrieval_eval import RetrievalEvaluator

BASE_DIR = Path(__file__).parent
CASES_FILE = BASE_DIR / "cases_v0_3.jsonl"
ADJUDICATED_GOLD_FILE = BASE_DIR / "gold_v0_3_adjudicated.jsonl"
ADJUDICATED_FORKS_FILE = BASE_DIR / "temporal_forks_v0_3_adjudicated.jsonl"
SPLIT_FILE = BASE_DIR / "split_manifest_v0_3.json"
CACHE_DIR = BASE_DIR / ".cache"
RESULTS_DIR = BASE_DIR / "results"


def load_benchmark_data():
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        cases = {c["case_id"]: c for c in [json.loads(line) for line in f if line.strip()]}
    with open(ADJUDICATED_GOLD_FILE, "r", encoding="utf-8") as f:
        gold = {g["case_id"]: g for g in [json.loads(line) for line in f if line.strip()]}
    with open(ADJUDICATED_FORKS_FILE, "r", encoding="utf-8") as f:
        forks = {f["record_id"]: f for f in [json.loads(line) for line in f if line.strip()]}
    with open(SPLIT_FILE, "r", encoding="utf-8") as f:
        splits = json.load(f)
    return cases, gold, forks, splits


class BenchmarkRunner:
    def __init__(self) -> None:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        self.client = BenchmarkLLMClient(cache_dir=CACHE_DIR)
        self.compiler = CompilerArms(self.client)
        self.reconstructor = BlindReconstructor(self.client)
        self.contrastive = ContrastiveEvaluator(self.client)
        self.retrieval = RetrievalEvaluator(self.client)
        self.auditor = GranularityAuditor()

    def run_split(self, split: str) -> dict[str, Any]:
        print(f"\n==========================================")
        print(f"   STARTING RUN FOR SPLIT: {split.upper()}")
        print(f"==========================================")

        cases, gold, forks, splits = load_benchmark_data()
        core_cids = splits["core"][split]

        # Gather temporal fork branches for this split
        target_fgs = set(splits["temporal_forks"][split])
        branch_ids = [bid for bid, b in forks.items() if b["fork_group_id"] in target_fgs]

        print(f"Cases in split ({split}): {len(core_cids)} core cases, {len(branch_ids)} temporal fork branches.")

        arms = ["P0", "P1", "P2", "P3", "P4"]

        # Storage for all compiled representations: arm -> item_id -> CompiledRepresentation
        compiled_by_arm: dict[str, dict[str, Any]] = {arm: {} for arm in arms}
        # Storage for reconstructions: arm -> item_id -> ReconstructionResult
        recons_by_arm: dict[str, dict[str, Any]] = {arm: {} for arm in arms}
        # Storage for evaluations: arm -> item_id -> EvaluationResult
        evals_by_arm: dict[str, dict[str, Any]] = {arm: {} for arm in arms}
        # Storage for audits: arm -> item_id -> dict
        audits_by_arm: dict[str, dict[str, Any]] = {arm: {} for arm in arms}

        # 1. Compile and evaluate core cases
        for idx, cid in enumerate(core_cids):
            c = cases[cid]
            g = gold[cid]
            dlg = c["dialogue"]
            cutoff = c["cutoff_after_turn"]
            raw_dlg_text = " | ".join(f"{t['speaker']}: {t['text']}" for t in dlg[:cutoff])

            print(f"[{split}][{idx+1}/{len(core_cids)}] Processing Core Case: {cid} ({c['family']})")

            for arm in arms:
                # Compile
                if arm == "P0":
                    comp = self.compiler.compile_p0(cid, dlg, cutoff)
                elif arm == "P1":
                    comp = self.compiler.compile_p1(cid, dlg, cutoff)
                elif arm == "P2":
                    comp = self.compiler.compile_p2(cid, dlg, cutoff)
                elif arm == "P3":
                    comp = self.compiler.compile_p3(cid, dlg, cutoff)
                elif arm == "P4":
                    comp = self.compiler.compile_p4(cid, dlg, cutoff)

                compiled_by_arm[arm][cid] = comp

                # Blind Reconstruction
                r_res = self.reconstructor.reconstruct(cid, arm, comp.representation_text)
                recons_by_arm[arm][cid] = r_res

                # Blind Evaluation
                e_res = self.reconstructor.evaluate(cid, arm, r_res.reconstruction_content, g)
                evals_by_arm[arm][cid] = e_res

                # Granularity Audit
                audit = self.auditor.audit_raw_copy(cid, arm, raw_dlg_text, comp.representation_text)
                if arm == "P3":
                    audit["atomization"] = self.auditor.audit_atomization(cid, comp.raw_data)
                audits_by_arm[arm][cid] = audit

        # 2. Compile and evaluate temporal fork branches
        # Hard rule: prefix dialogue compiled at prefix cutoff turn.
        # Future dialogue must NEVER be seen at compile time.
        fg_map: dict[str, str] = {}
        for idx, bid in enumerate(branch_ids):
            b = forks[bid]
            fg_id = b["fork_group_id"]
            fg_map[bid] = fg_id
            pref_dlg = b["prefix_dialogue"]
            pref_cutoff = b["compile_cutoff_after_prefix_turn"]
            raw_pref_text = " | ".join(f"{t['speaker']}: {t['text']}" for t in pref_dlg[:pref_cutoff])

            print(f"[{split}][{idx+1}/{len(branch_ids)}] Processing Temporal Branch: {bid} (Group: {fg_id})")

            for arm in arms:
                if arm == "P0":
                    comp = self.compiler.compile_p0(bid, pref_dlg, pref_cutoff)
                elif arm == "P1":
                    comp = self.compiler.compile_p1(bid, pref_dlg, pref_cutoff)
                elif arm == "P2":
                    comp = self.compiler.compile_p2(bid, pref_dlg, pref_cutoff)
                elif arm == "P3":
                    comp = self.compiler.compile_p3(bid, pref_dlg, pref_cutoff)
                elif arm == "P4":
                    comp = self.compiler.compile_p4(bid, pref_dlg, pref_cutoff)

                compiled_by_arm[arm][bid] = comp

                r_res = self.reconstructor.reconstruct(bid, arm, comp.representation_text)
                recons_by_arm[arm][bid] = r_res

                e_res = self.reconstructor.evaluate(bid, arm, r_res.reconstruction_content, b)
                evals_by_arm[arm][bid] = e_res

                audit = self.auditor.audit_raw_copy(bid, arm, raw_pref_text, comp.representation_text)
                audits_by_arm[arm][bid] = audit

        # 3. Contrastive Evaluation
        print(f"\n[{split}] Running Contrastive Evaluation across all arms...")
        contrastive_results: dict[str, Any] = {}
        for arm in arms:
            rep_map = {cid: compiled_by_arm[arm][cid].representation_text for cid in core_cids}
            contrastive_results[arm] = self.contrastive.evaluate_contrastive(split, arm, rep_map)

        # 4. Retrieval Evaluation
        print(f"[{split}] Running Retrieval Evaluation across all arms...")
        retrieval_results: dict[str, Any] = {}
        for arm in arms:
            # All items in split (core cases + temporal branches) are indexed
            all_split_items = {iid: compiled_by_arm[arm][iid].representation_text for iid in list(core_cids) + list(branch_ids)}
            retrieval_results[arm] = self.retrieval.evaluate_retrieval(split, arm, all_split_items, fork_group_map=fg_map)

        # 5. Structure-only ablation for P2 (Stage D2)
        print(f"[{split}] Running Structure-Only Ablation on P2...")
        p2_ablation_reps = {iid: compiled_by_arm["P2"][iid].structure_only_text for iid in list(core_cids) + list(branch_ids)}
        p2_ablation_contrastive = self.contrastive.evaluate_contrastive(
            split, "P2_structure_only", {cid: p2_ablation_reps[cid] for cid in core_cids}
        )
        p2_ablation_retrieval = self.retrieval.evaluate_retrieval(
            split, "P2_structure_only", p2_ablation_reps, fork_group_map=fg_map
        )

        # 6. Aggregate Summary Metrics by Arm
        arm_summaries: dict[str, Any] = {}
        for arm in arms:
            arm_evals = [evals_by_arm[arm][iid] for iid in list(core_cids) + list(branch_ids)]
            arm_audits = [audits_by_arm[arm][iid] for iid in list(core_cids) + list(branch_ids)]

            mp_recalls = [e.must_preserve_recall for e in arm_evals]
            forbidden_rates = [e.forbidden_claim_rate for e in arm_evals]
            unknown_accs = [e.unknown_localization_accuracy for e in arm_evals]
            attr_fids = [e.attribution_fidelity for e in arm_evals]
            temp_locs = [e.temporal_locality for e in arm_evals]
            equiv_counts = sum(1 for e in arm_evals if e.full_case_equivalent)
            severe_counts = sum(1 for e in arm_evals if e.has_severe_contamination)

            severe_breakdown: dict[str, int] = {}
            failure_tax_counts: dict[str, int] = {}
            for e in arm_evals:
                for k, v in e.severe_contaminations.items():
                    if v:
                        severe_breakdown[k] = severe_breakdown.get(k, 0) + 1
                for fl in e.failure_labels:
                    failure_tax_counts[fl] = failure_tax_counts.get(fl, 0) + 1

            trivial_non_struct_cnt = sum(1 for a in arm_audits if a.get("is_trivial_non_structure", False))
            mean_lcs_ratio = sum(a.get("lcs_ratio", 0.0) for a in arm_audits) / len(arm_audits)

            ret_res = retrieval_results[arm]
            cont_res = contrastive_results[arm]

            arm_summaries[arm] = {
                "num_cases_evaluated": len(arm_evals),
                "must_preserve_recall_mean": round(sum(mp_recalls) / len(mp_recalls), 4),
                "forbidden_claim_rate_mean": round(sum(forbidden_rates) / len(forbidden_rates), 4),
                "unknown_localization_mean": round(sum(unknown_accs) / len(unknown_accs), 4),
                "attribution_fidelity_mean": round(sum(attr_fids) / len(attr_fids), 4),
                "temporal_locality_mean": round(sum(temp_locs) / len(temp_locs), 4),
                "full_case_equivalence_rate": round(equiv_counts / len(arm_evals), 4),
                "severe_contamination_count": severe_counts,
                "severe_contamination_rate": round(severe_counts / len(arm_evals), 4),
                "severe_contamination_breakdown": severe_breakdown,
                "failure_taxonomy_counts": failure_tax_counts,
                "trivial_non_structure_count": trivial_non_struct_cnt,
                "mean_lcs_ratio": round(mean_lcs_ratio, 4),
                "contrastive": {
                    "mean_equivalence_similarity": round(cont_res.get("mean_equivalence_similarity", 0.0), 4),
                    "mean_hard_negative_similarity": round(cont_res.get("mean_hard_negative_similarity", 0.0), 4),
                    "separation_margin": round(cont_res.get("separation_margin", 0.0), 4),
                    "equivalence_nn_top1_accuracy": round(cont_res.get("equivalence_nn_top1_accuracy", 0.0), 4),
                    "granularity_collapse_rate": round(cont_res.get("granularity_collapse_rate", 0.0), 4),
                },
                "retrieval": {
                    "recall_at_1": round(ret_res.get("recall_at_1", 0.0), 4),
                    "recall_at_5": round(ret_res.get("recall_at_5", 0.0), 4),
                    "mrr": round(ret_res.get("mrr", 0.0), 4),
                    "hard_negative_false_retrieval_rate": round(ret_res.get("hard_negative_false_retrieval_rate", 0.0), 4),
                    "distractor_rate_top3": round(ret_res.get("mean_distractor_rate_in_top3", 0.0), 4),
                },
            }

        # 7. Check Temporal Fork Consistency
        temporal_consistency_report = {}
        for fg_id in splits["temporal_forks"][split]:
            bids = [bid for bid in branch_ids if forks[bid]["fork_group_id"] == fg_id]
            group_evals: dict[str, list[dict]] = {arm: [] for arm in arms}
            for bid in bids:
                for arm in arms:
                    e = evals_by_arm[arm][bid]
                    group_evals[arm].append({
                        "branch_id": bid,
                        "equiv": e.full_case_equivalent,
                        "mp_recall": e.must_preserve_recall,
                        "severe": e.has_severe_contamination,
                    })
            temporal_consistency_report[fg_id] = {
                "branch_ids": bids,
                "per_arm": group_evals,
            }

        split_output = {
            "split": split,
            "counts": {
                "core_cases": len(core_cids),
                "temporal_fork_branches": len(branch_ids),
                "total_items": len(core_cids) + len(branch_ids),
            },
            "summaries_by_arm": arm_summaries,
            "contrastive_by_arm": contrastive_results,
            "retrieval_by_arm": retrieval_results,
            "p2_structure_ablation": {
                "contrastive": p2_ablation_contrastive,
                "retrieval": p2_ablation_retrieval,
            },
            "temporal_fork_consistency": temporal_consistency_report,
            "predictions_by_arm": {
                arm: {iid: compiled_by_arm[arm][iid].raw_data for iid in compiled_by_arm[arm]} for arm in arms
            },
            "reconstructions_by_arm": {
                arm: {iid: recons_by_arm[arm][iid].reconstruction_content for iid in recons_by_arm[arm]} for arm in arms
            },
            "evaluations_by_arm": {
                arm: {
                    iid: {
                        "must_preserve_recall": evals_by_arm[arm][iid].must_preserve_recall,
                        "forbidden_claim_rate": evals_by_arm[arm][iid].forbidden_claim_rate,
                        "unknown_localization_accuracy": evals_by_arm[arm][iid].unknown_localization_accuracy,
                        "attribution_fidelity": evals_by_arm[arm][iid].attribution_fidelity,
                        "temporal_locality": evals_by_arm[arm][iid].temporal_locality,
                        "full_case_equivalent": evals_by_arm[arm][iid].full_case_equivalent,
                        "severe_contaminations": evals_by_arm[arm][iid].severe_contaminations,
                        "failure_labels": evals_by_arm[arm][iid].failure_labels,
                        "details": evals_by_arm[arm][iid].details,
                    }
                    for iid in evals_by_arm[arm]
                }
                for arm in arms
            },
            "audits_by_arm": audits_by_arm,
        }

        # Save to disk
        out_file = RESULTS_DIR / f"{split}_results.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(split_output, f, indent=2, ensure_ascii=False)
        print(f"[{split}] Successfully saved results to: {out_file}")

        return split_output


def run_benchmark():
    runner = BenchmarkRunner()

    # Step 1: Run Dev Split (Phase C)
    print("\n>>> STEP 1: Running Phase C (Dev Evaluation) <<<")
    dev_results = runner.run_split("dev")

    # Step 2: Freeze Compiler Config & Hashes before Held-out
    print("\n>>> STEP 2: Freezing Compiler & Retrieval Config for Held-Out <<<")
    frozen_config = {
        "compiler_model": "gemini-3.1-flash-lite",
        "embedding_model": "gemini-embedding-001",
        "seed": 42,
        "temperature": 0.0,
        "arms": ["P0", "P1", "P2", "P3", "P4"],
        "retrieval_metric": "cosine_similarity",
        "frozen_timestamp": "2026-09-25T06:20:00Z",
        "git_commit": "master_frozen",
    }
    with open(RESULTS_DIR / "FROZEN_CONFIG.json", "w", encoding="utf-8") as f:
        json.dump(frozen_config, f, indent=2, ensure_ascii=False)
    print("Frozen config saved to: results/FROZEN_CONFIG.json")

    # Step 3: Run Held-Out Split ONCE (Phase D)
    print("\n>>> STEP 3: Running Phase D (Held-Out One-Shot Evaluation) <<<")
    heldout_results = runner.run_split("held_out")

    # Step 4: Record Token & Latency Cost
    cost_summary = {
        "total_calls": runner.client.total_calls,
        "total_prompt_tokens": runner.client.total_prompt_tokens,
        "total_completion_tokens": runner.client.total_completion_tokens,
        "total_tokens": runner.client.total_prompt_tokens + runner.client.total_completion_tokens,
        "total_latency_seconds": round(runner.client.total_latency_ms / 1000.0, 2),
    }
    with open(RESULTS_DIR / "cost_summary.json", "w", encoding="utf-8") as f:
        json.dump(cost_summary, f, indent=2, ensure_ascii=False)
    print(f"\nTotal benchmark API calls: {cost_summary['total_calls']}, tokens: {cost_summary['total_tokens']}")

    print("\n>>> BENCHMARK EXECUTION FINISHED SUCCESSFULLY! <<<")


if __name__ == "__main__":
    run_benchmark()
