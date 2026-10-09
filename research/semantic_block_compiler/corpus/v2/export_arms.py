#!/usr/bin/env python3
"""Export V1 + V2 fixed-block corpus into three isolated local LCE input arms.

NO embeddings, candidate relations, or LLM judgments are generated.
Use id_map_ANALYST_ONLY.json for audit, NEVER feed it to an LLM consumer.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V1_PATH = ROOT.parent / "v1" / "fixed_blocks.json"
V2_PATH = ROOT / "challenge_blocks.json"
ARMS = ("baseline", "attribution", "state")
TRACKS = ("release", "jewelry", "venue", "scanners")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_id(block_id: str) -> str:
    return "W_" + hashlib.sha256(("fixed-blocks-v2::" + block_id).encode("utf-8")).hexdigest()[:12]


def load_and_check():
    old = json.loads(V1_PATH.read_text(encoding="utf-8"))
    add = json.loads(V2_PATH.read_text(encoding="utf-8"))
    assert old["synthetic_only"] is True and add["synthetic_only"] is True
    assert old["arms"] == add["arms"] == list(ARMS)
    assert len(old["cases"]) == len(add["cases"]) == 24
    blocks = old["cases"] + add["cases"]
    ids = [b["block_id"] for b in blocks]
    assert len(set(ids)) == 48
    assert set(public_id(x) for x in ids).__len__() == 48
    lookup = {b["block_id"]: b for b in blocks}
    assert Counter(b["track"] for b in blocks) == {t: 12 for t in TRACKS}
    for b in blocks:
        assert b.get("synthetic") is True
        assert all(b.get("compiled", {}).get(a, "").strip() for a in ARMS)
        assert b["source_turns"]
        assert {turn["role"] for turn in b["source_turns"]} <= {"assistant", "user"}
        assert len(set(t["turn_id"] for t in b["source_turns"])) == len(b["source_turns"])
        assert len(set(b["prior_context_ids"])) == len(b["prior_context_ids"])
        for ref in b["prior_context_ids"]:
            assert ref in lookup, (b["block_id"], ref)
            assert lookup[ref]["known_at"] < b["known_at"], (b["block_id"], ref, "future source")
    return blocks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("out/semanticblock-v2"))
    args = parser.parse_args()
    blocks = load_and_check()
    args.out.mkdir(parents=True, exist_ok=True)

    # This sidecar is for the experiment analyst only, not for the LCE vector
    # input or the subsequent LLM judge.
    mapping = {
        public_id(b["block_id"]): {
            "source_id": b["block_id"],
            "track": b["track"],
            "source_turn_ids": [t["turn_id"] for t in b["source_turns"]],
            "context_ids": b["prior_context_ids"],
            "origin": "v1" if int(b["block_id"][1:]) <= 6 else "v2",
        }
        for b in blocks
    }
    map_path = args.out / "id_map_ANALYST_ONLY.json"
    map_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    files = {}
    for arm in ARMS:
        path = args.out / (arm + ".jsonl")
        with path.open("w", encoding="utf-8", newline="\n") as f:
            for block in blocks:
                record = {
                    "id": public_id(block["block_id"]),
                    "text": block["compiled"][arm],
                    "known_at": block["known_at"],
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        files[arm] = {"file": path.name, "rows": len(blocks), "sha256": sha256(path)}

    receipt = {
        "dataset": "semanticblock-fixed-block-v2",
        "synthetic_only": True,
        "v1_sha256": sha256(V1_PATH),
        "v2_sha256": sha256(V2_PATH),
        "cases": len(blocks),
        "distinct_source_turns": sum(len(b["source_turns"]) for b in blocks),
        "arm_count": len(ARMS),
        "variants": len(blocks) * len(ARMS),
        "opaque_id_map_sha256": sha256(map_path),
        "arms": files,
        "lce_model_called": False,
        "llm_judge_called": False,
    }
    (args.out / "EXPORT_RECEIPT.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"PASS: {len(blocks)} unique fixed blocks, {len(blocks)*3} manual variants; independent arms")
    for arm, info in files.items():
        print(f"{arm}: {info['rows']} rows sha256={info['sha256']}")
    print(f"analyst-only ID map: {map_path}")
    print(f"receipt: {args.out / 'EXPORT_RECEIPT.json'}")


if __name__ == "__main__":
    main()
