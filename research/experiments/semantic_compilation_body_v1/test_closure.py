import json
from pathlib import Path
from research.experiments.semantic_compilation_body_v1.validator import validate_parse_result
from research.experiments.semantic_compilation_body_v1.closure import compile_semantic_closure

cases_file = Path("research/experiments/semantic_compilation_v1/closure_cases.json")
cases = json.loads(cases_file.read_text(encoding="utf-8"))["cases"]

for c in cases[:4]:
    cid = c["id"]
    raw = {
        "schema_version": "semantic_parse_v1",
        "source_window_refs": [r["evidence_id"] for r in c["raw"]],
        "semantic_points": [
            {
                "local_id": p["id"],
                "source_refs": p["source_refs"],
                "meaning": p["meaning"],
                "status": p["status"],
                "speech_act": p.get("speech_act", "assertion"),
                "epistemic_status": p.get("epistemic", "asserted"),
                "temporal": p.get("temporal", "current")
            }
            for p in c["points"]
        ],
        "dependencies": [
            {
                "from_point": d["from"],
                "to_point": d["to"],
                "relation": d.get("type", "rel"),
                "boundary_policy": d["policy"],
                "reason": "test"
            }
            for d in c["dependencies"]
        ]
    }
    parse_res, diags = validate_parse_result(raw)
    blocks, defs = compile_semantic_closure(parse_res, cid)
    print(f"Case {cid}:")
    print(f"  Points: {[p.local_id for p in parse_res.semantic_points]}")
    print(f"  Blocks ({len(blocks)}):")
    for b in blocks:
        print(f"    [{b.block_id}] members={b.member_point_ids} ctx={b.context_point_ids}")
        print(f"      analysis_text={b.analysis_text}")
    if defs:
        print(f"  Deferred: {defs}")
    print()
