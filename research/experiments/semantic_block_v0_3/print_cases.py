"""Inspect all 48 cases with draft gold and print formatted output in utf-8."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).parent
CASES_FILE = BASE_DIR / "cases_v0_3.jsonl"
GOLD_FILE = BASE_DIR / "gold_v0_3.jsonl"


def main():
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]
    with open(GOLD_FILE, "r", encoding="utf-8") as f:
        gold = {g["case_id"]: g for g in [json.loads(line) for line in f if line.strip()]}

    for i, c in enumerate(cases):
        cid = c["case_id"]
        g = gold[cid]
        visible = c["dialogue"][: c["cutoff_after_turn"]]
        d_str = " | ".join(f"{t['speaker']}: {t['text']}" for t in visible)
        print(f"=== [{i+1}/48] {cid} ({c['family']} / {c['variant']}) ===")
        print(f"Dialogue: {d_str}")
        print(f"Account:  {g['gold_semantic_account']}")
        print(f"Preserve: {g['must_preserve']}")
        print(f"NotClaim: {g['must_not_claim']}")
        print(f"Unknowns: {g['legitimate_unknowns']}")
        print()


if __name__ == "__main__":
    main()
