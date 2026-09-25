import json
from pathlib import Path

BASE_V03 = Path("research/experiments/semantic_block_v0_3")
BASE_EXP = Path("research/experiments/semantic_block_issue_22")

with open(BASE_V03 / "retrieval_queries_v0_3.jsonl", "r", encoding="utf-8") as f:
    v03_q = [json.loads(l) for l in f if l.strip()]

with open(BASE_EXP / "data" / "stress_retrieval_queries.jsonl", "r", encoding="utf-8") as f:
    stress_q = [json.loads(l) for l in f if l.strip()]

all_q = {q["query_id"]: q for q in v03_q + stress_q}

with open(BASE_EXP / "results" / "held_out_results.json", "r", encoding="utf-8") as f:
    held_out = json.load(f)

with open(BASE_EXP / "results" / "dev_results.json", "r", encoding="utf-8") as f:
    dev = json.load(f)

# Group queries by type
types = {}
for qid, q in all_q.items():
    qt = q.get("query_type", "unknown")
    types.setdefault(qt, []).append(qid)

print("Query breakdown by type:")
for qt, qids in types.items():
    print(f"  {qt} ({len(qids)}): {qids}")

def evaluate_slice(split_data, qids, split_name):
    print(f"\n--- SLICE EVALUATION ON {split_name} for queries {qids} ---")
    evals = split_data["evaluations"]
    for arm in ["B0", "B1", "B2", "B3", "B4"]:
        for m in ["R0", "R1", "R2", "R3"]:
            if m in evals[arm]:
                qs = [q for q in evals[arm][m]["k_5"]["queries"] if q["query_id"] in qids]
                if not qs:
                    continue
                recalls = [q["adjudication"]["final_accepted_target_recall"] for q in qs]
                precs = [q["adjudication"]["adjudication_precision"] for q in qs]
                first_ranks = [q["retrieval"]["first_target_rank"] for q in qs if q["retrieval"]["first_target_rank"] < 900]
                mean_rec = sum(recalls) / len(recalls)
                mean_prec = sum(precs) / len(precs)
                mean_rank = sum(first_ranks) / len(first_ranks) if first_ranks else 999.0
                print(f"  {arm} {m}: n={len(qs)}, recall={mean_rec*100:.1f}%, prec={mean_prec*100:.1f}%, first_rank={mean_rank:.2f}")

for qt, qids in types.items():
    held_qids = [qid for qid in qids if qid in [q["query_id"] for q in held_out["evaluations"]["B0"]["R0"]["k_5"]["queries"]]]
    dev_qids = [qid for qid in qids if qid in [q["query_id"] for q in dev["evaluations"]["B0"]["R0"]["k_5"]["queries"]]]
    print(f"\n=======================================================")
    print(f"SLICE: {qt} (Held-out: {len(held_qids)}, Dev: {len(dev_qids)})")
    print(f"=======================================================")
    if held_qids:
        evaluate_slice(held_out, held_qids, "HELD-OUT")
    if dev_qids:
        evaluate_slice(dev, dev_qids, "DEV")
