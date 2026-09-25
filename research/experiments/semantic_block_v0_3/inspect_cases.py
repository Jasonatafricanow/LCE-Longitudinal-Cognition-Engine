"""Adjudication inspection and validation script for SemanticBlock v0.3."""

from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
CASES_FILE = BASE_DIR / "cases_v0_3.jsonl"
GOLD_FILE = BASE_DIR / "gold_v0_3.jsonl"
CONTRAST_FILE = BASE_DIR / "contrast_groups_v0_3.json"
FORKS_FILE = BASE_DIR / "temporal_forks_v0_3.jsonl"


def load_data():
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]
    with open(GOLD_FILE, "r", encoding="utf-8") as f:
        gold = [json.loads(line) for line in f if line.strip()]
    with open(CONTRAST_FILE, "r", encoding="utf-8") as f:
        contrast = json.load(f)
    with open(FORKS_FILE, "r", encoding="utf-8") as f:
        forks = [json.loads(line) for line in f if line.strip()]
    return cases, gold, contrast, forks


def summarize_cases():
    cases, gold, contrast, forks = load_data()
    gold_map = {g["case_id"]: g for g in gold}
    print(f"Total cases: {len(cases)}, gold records: {len(gold)}, forks: {len(forks)}")
    
    for i, c in enumerate(cases):
        cid = c["case_id"]
        g = gold_map[cid]
        visible = c["dialogue"][:c["cutoff_after_turn"]]
        d_str = " | ".join(f"{t['speaker']}: {t['text']}" for t in visible)
        print(f"[{i+1}/48] {cid} ({c['family']}/{c['variant']})")
        print(f"   Dialogue: {d_str}")
        print(f"   Account:  {g['gold_semantic_account']}")
        print(f"   Preserve: {g['must_preserve']}")
        print(f"   NotClaim: {g['must_not_claim']}")
        print(f"   Unknowns: {g['legitimate_unknowns']}")
        print()


if __name__ == "__main__":
    summarize_cases()
