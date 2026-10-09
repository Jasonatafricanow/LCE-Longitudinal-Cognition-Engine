import json
from pathlib import Path

p_patch = Path(r"c:\projects\LCE\research\experiments\semantic_compilation_body_v1\one_pass\results\one_pass_multiturn_patched.jsonl")
patch_lines = [json.loads(l) for l in p_patch.read_text(encoding="utf-8").splitlines() if l.strip()]

for r in patch_lines:
    if not r["passed"]:
        cid = r["case_id"]
        print(f"=== {cid} ===")
        print("Errors:", r["errors"])
        if r.get("e19_details"):
            for d in r["e19_details"]:
                print("  E19 Detail:", d)
        print("Assistant resp:", r.get("assistant_response_preview", "")[:120])
        print()
