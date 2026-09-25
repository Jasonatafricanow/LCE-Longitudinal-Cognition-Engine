import json
from pathlib import Path

BASE = Path("research/experiments/semantic_block_issue_22")
RESULTS_DIR = BASE / "results"

with open(RESULTS_DIR / "held_out_results.json", "r", encoding="utf-8") as f:
    held_out = json.load(f)

print("--- HELD OUT EVALUATION OVERVIEW ---")
evals = held_out["evaluations"]
for arm in ["B0", "B1", "B2", "B3", "B4"]:
    for m in ["R0", "R1", "R2", "R3"]:
        if m in evals[arm]:
            k5 = evals[arm][m]["k_5"]
            print(f"Arm {arm} Method {m}:")
            print(f"  mean_final_accepted_target_recall: {k5['mean_final_accepted_target_recall']}")
            print(f"  mean_recall_at_k: {k5['mean_recall_at_k']}")
            print(f"  hard_negative_presence_rate: {k5['hard_negative_presence_rate']}")
            print(f"  mean_adjudication_precision: {k5['mean_adjudication_precision']}")
            print(f"  mean_first_target_rank: {k5['mean_first_target_rank']}")
            print(f"  mean_candidate_tokens: {k5['mean_candidate_tokens']}")

# Check per-query breakdown for B1 R1 and B4 R1
print("\n--- QUERY DETAILS FOR B1 R1 (K=5) ---")
b1_r1_queries = evals["B1"]["R1"]["k_5"]["queries"]
for i, q in enumerate(b1_r1_queries):
    qid = q["query_id"]
    ret = q["retrieval"]
    adj = q["adjudication"]
    print(f"Query {qid}: recall_at_k={ret['recall_at_k']}, final_acc_recall={adj['final_accepted_target_recall']}, acc_target_cnt={adj['accepted_target_count']}, false_acc_cnt={adj['false_accepted_count']}, hn_present={ret['hard_negative_present']}")

print("\n--- QUERY DETAILS FOR B4 R1 (K=5) ---")
b4_r1_queries = evals["B4"]["R1"]["k_5"]["queries"]
for i, q in enumerate(b4_r1_queries):
    qid = q["query_id"]
    ret = q["retrieval"]
    adj = q["adjudication"]
    print(f"Query {qid}: recall_at_k={ret['recall_at_k']}, final_acc_recall={adj['final_accepted_target_recall']}, acc_target_cnt={adj['accepted_target_count']}, false_acc_cnt={adj['false_accepted_count']}, hn_present={ret['hard_negative_present']}")

# Check candidates across arms for all queries
print("\n--- CANDIDATE COMPARISON ACROSS ARMS (K=5) ---")
for i in range(len(b1_r1_queries)):
    qid = b1_r1_queries[i]["query_id"]
    cand_b0 = [c["item_id"] for c in evals["B0"]["R0"]["k_5"]["queries"][i]["retrieval"]["candidates"]]
    cand_b1 = [c["item_id"] for c in evals["B1"]["R1"]["k_5"]["queries"][i]["retrieval"]["candidates"]]
    cand_b2 = [c["item_id"] for c in evals["B2"]["R1"]["k_5"]["queries"][i]["retrieval"]["candidates"]]
    cand_b3 = [c["item_id"] for c in evals["B3"]["R1"]["k_5"]["queries"][i]["retrieval"]["candidates"]]
    cand_b4 = [c["item_id"] for c in evals["B4"]["R1"]["k_5"]["queries"][i]["retrieval"]["candidates"]]
    print(f"Query {qid}:")
    print(f"  B0: {cand_b0}")
    print(f"  B1: {cand_b1}")
    print(f"  B2: {cand_b2}")
    print(f"  B3: {cand_b3}")
    print(f"  B4: {cand_b4}")
print("\n--- DETAILED INVESTIGATION FOR RQ-H05 ---")
for arm in ["B0", "B1", "B2", "B3", "B4"]:
    for m in ["R0", "R1", "R2", "R3"]:
        if m in evals[arm]:
            q5 = [q for q in evals[arm][m]["k_5"]["queries"] if q["query_id"] == "RQ-H05"][0]
            cands = [c["item_id"] for c in q5["retrieval"]["candidates"]]
            adj = q5["adjudication"]
            decisions = [(d["candidate_id"], d["accepted"], d["is_true_target"], d["reason"][:40]) for d in adj["decisions"]]
            print(f"{arm} {m} RQ-H05: cands={cands}, acc_cnt={adj['accepted_target_count']}, recall={adj['final_accepted_target_recall']}, dec={decisions}")

