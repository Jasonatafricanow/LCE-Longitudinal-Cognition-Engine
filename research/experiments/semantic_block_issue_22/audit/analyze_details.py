import json
from pathlib import Path

BASE = Path("research/experiments/semantic_block_issue_22/audit")

with open(BASE / "ADJUDICATOR_INPUT_IDENTITY.json", "r", encoding="utf-8") as f:
    adj = json.load(f)

print("=== HELD-OUT QUERY ADJUDICATOR COMPARISON (B0 vs B4) ===")
for q in adj["held_out_queries"]:
    print(f"{q['query_id']}: candidates_match={q['candidates_match']}, decisions_match={q['decisions_match']}, divergent={q['divergent_candidates']}")
    if not q["decisions_match"]:
        print(f"   B0 decisions: {q['decisions_b0']}")
        print(f"   B4 decisions: {q['decisions_b4']}")

with open(BASE / "CANDIDATE_SET_OVERLAP.json", "r", encoding="utf-8") as f:
    overlap = json.load(f)

print("\n=== CANDIDATE OVERLAPS PER QUERY (HELD-OUT) ===")
for q in overlap["held_out"]["per_query_analysis"]:
    print(f"{q['query_id']}: B0_vs_B1={q['pairwise_jaccard']['B0_vs_B1']:.2f}, B1_vs_B4={q['pairwise_jaccard']['B1_vs_B4']:.2f}, B0==B1: {q['pairwise_rank_match']['B0_vs_B1']}, B1..B4 identical set: {q['b1_b2_b3_b4_candidate_set_identical']}")

print("\n=== DEV QUERY STATS ===")
for q in overlap["dev"]["per_query_analysis"]:
    print(f"{q['query_id']}: B0_vs_B1={q['pairwise_jaccard']['B0_vs_B1']:.2f}, B1_vs_B4={q['pairwise_jaccard']['B1_vs_B4']:.2f}, B1..B4 identical set: {q['b1_b2_b3_b4_candidate_set_identical']}")
