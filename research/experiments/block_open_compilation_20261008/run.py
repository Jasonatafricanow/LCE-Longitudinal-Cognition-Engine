"""Open SemanticBlock compilation: independent 0..N, multi-source, deferred.

Model inference is local Qwen2.5-3B Q4; no embedding/Path B scoring,
no production code, no private original conversation.  Gold is not in model input.
"""
import hashlib
import json
import os
import re
import time
from pathlib import Path
from huggingface_hub import hf_hub_download
from llama_cpp import Llama

REPO="bartowski/Qwen2.5-3B-Instruct-GGUF"
MODEL_FILE="Qwen2.5-3B-Instruct-Q4_K_M.gguf"
OUTPUT=Path("block_open_compilation_results.json")

CASES=[
    ("two_blocks_same_source", "open", [
        {"id":"culture-r1","text":"反叛作品首先要被看到才可能扩大影响，进入公共解释以后，作者也不再独占作品的意义，读者重新解释还能延续批判。另一个完全独立的意见：AI给文章提建议应该客观、建设性，不能虚构问题当靶子批判；输出前最好先检查论证是否自洽。"}
    ], "batch"),
    ("two_sources_one_cognition", "open", [
        {"id":"valuation-r1","text":"不能只看设备账面折旧推断算力租赁值不值得投资。应结合实际收费利用率、有效经济寿命、二手残值与运营成本评估整个生命周期的经济收益。"},
        {"id":"valuation-r2","text":"旧设备虽然难以承担前沿训练，仍可能继续提供推理服务与现金流，因此退出残值未必归零；这也是全周期回报测算的一部分。顺便记录一个新计划：下一步单独核验旧卡在推理市场的实际出租价格。"}
    ], "batch"),
    ("ab_to_acb", "open", [
        {"id":"bridge-r1","text":"日线回测如果拿突破当天的全天成交额决定开盘买不买，会发生未来数据泄漏。需要基于交易时已可观测的信号。"},
        {"id":"bridge-r2","text":"我准备独立做一个盘中微信提醒模块，不用等日线收盘。但这和刚才的回测筛选要怎么衔接，我现在还没想清楚；先别替我补出中间机制。"},
        {"id":"bridge-r3","text":"现在想到连接方法了：用开盘前30分钟的成交额与历史同期比较，作为盘中可观测的过滤信号。它既补上日线回测的未来函数缺口，也可以直接作为盘中提醒模块的触发依据。"},
        {"id":"bridge-r4","text":"嗯，刚才说的就这些，没有新的判断或计划。"}
    ], "stream"),
    ("two_blocks_same_source", "exclusive", [
        {"id":"culture-r1","text":"反叛作品首先要被看到才可能扩大影响，进入公共解释以后，作者也不再独占作品的意义，读者重新解释还能延续批判。另一个完全独立的意见：AI给文章提建议应该客观、建设性，不能虚构问题当靶子批判；输出前最好先检查论证是否自洽。"}
    ], "batch"),
    ("ab_to_acb", "exclusive", [
        {"id":"bridge-r4","text":"嗯，刚才说的就这些，没有新的判断或计划。"}
    ], "batch"),
]
SYSTEM_OPEN="""你是在真实证据上执行 SemanticBlock 编译，不是在做单句摘要或为预设图形做语义裁剪。
严格仅看提供的截止时点资料：已经能理解的每个独立认知都可以编译成一个自包含的 Block；同一证据允许支持多个不同 Block；不同证据也允许共同支持同一 Block；0个或多个都合法。
新的认知与已有认知相同就不要重复创造；不要为了凑够某个数量而拆、合、舍弃事实；遇到尚不明确的指代或关系，应原样保留在 deferred，绝不能自作主张补完。
所有新 Block 必须真实由所列来源支持；写清断言/计划/推测的认知状态，不得把计划写成完成。先前已保存的 Blocks 无须重复输出也不能改写。只给当前批次或本轮新增的 Block。
输出 JSON 对象，字段严格是 new_blocks（数组，对象字段content和source_ids数组）、deferred（数组，对象字段source_ids和unresolved_text）、resolved_deferred_ids（字符串ID数组）。不得输出额外解释。"""
SYSTEM_EXCLUSIVE="""实验的受限对照：每次只准形成恰好一个 SemanticBlock，即使证据包含互不关联的多种认知，或者根本没有新认知。尽量总结当前证据为一个独立段落；返回 JSON 对象，字段严格是 new_blocks（数组，内恰一个对象，含 content/source_ids）、deferred（空数组）、resolved_deferred_ids（空数组）。不得输出额外说明。"""

def parse(text):
    stripped=text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        m=re.search(r"\{[\s\S]*\}",stripped)
        if m:
            try: return json.loads(m.group(0))
            except json.JSONDecodeError:pass
    return {"_parse_error":True,"raw":text}

def invoke(llm,name,mode,context,batch,accepted,deferred):
    prompt={
        "task":name,
        "history_cutoff":context[-1]["id"] if context else "none",
        "prior_evidence":context,
        "accepted_blocks_unchanged":accepted,
        "still_unresolved":deferred,
        "new_evidence":batch,
    }
    st=time.monotonic()
    result=llm.create_chat_completion(
        messages=[{"role":"system","content":SYSTEM_OPEN if mode=="open" else SYSTEM_EXCLUSIVE},
                  {"role":"user","content":json.dumps(prompt,ensure_ascii=False)}],
        temperature=0.0,top_p=1.0,max_tokens=850,
        response_format={"type":"json_object"})
    raw=result["choices"][0]["message"]["content"]
    parsed=parse(raw)
    return {"raw":raw,"parsed":parsed,"duration_seconds":round(time.monotonic()-st,2),
            "usage":result.get("usage",{}),
            "input_sha256":hashlib.sha256(json.dumps(prompt,ensure_ascii=False,sort_keys=True).encode()).hexdigest()}

def main():
    start=time.monotonic()
    print("DOWNLOADING_MODEL",REPO,MODEL_FILE,flush=True)
    file=hf_hub_download(repo_id=REPO,filename=MODEL_FILE)
    print("MODEL_LOCAL_BYTES",Path(file).stat().st_size,flush=True)
    llm=Llama(model_path=file,n_ctx=4096,n_threads=2,n_batch=256,n_gpu_layers=0,verbose=False)
    report={
       "model":REPO+"/"+MODEL_FILE,
       "limitations":[
         "Corpus uses human-curated, privacy-sanitized paraphrases, not unmodified private originals.",
         "The open instruction is a semantic compiler prompt, not a proven production compiler.",
         "Exact 0..N results and explanations are model proposals; reference quality needs human adjudication.",
         "Bridge episode is a synthetic controlled scenario; not proof of authentic long-term cognition recovery.",
         "No embedding, Path B, Line materialization, or hidden gold fed to model.",
       ],
       "results":[]
    }
    for name,mode,rows,kind in CASES:
        accepted=[];deferred=[];history=[];recs=[]
        batches=[rows] if kind=="batch" else [[x] for x in rows]
        for batch in batches:
            output=invoke(llm,name,mode,history,batch,accepted,deferred)
            parsed=output["parsed"]
            found={r["id"] for r in history+batch}
            if "new_blocks" in parsed and isinstance(parsed["new_blocks"],list):
                for b in parsed["new_blocks"]:
                    if isinstance(b,dict) and isinstance(b.get("source_ids"),list):
                        b["valid_source_ids"]=all(s in found for s in b["source_ids"])
                        accepted.append({
                            "block_id":"B"+str(len(accepted)+1),
                            "content":b.get("content",""),
                            "source_ids":b.get("source_ids",[]),
                            "committed_after":batch[-1]["id"]})
            if "deferred" in parsed and isinstance(parsed["deferred"],list):
                # Preserve previous pending by default, only remove explicitly resolved IDs.
                resolved=set(parsed.get("resolved_deferred_ids",[]))
                deferred=[d for d in deferred if not (set(d.get("source_ids",[])) & resolved)]
                for d in parsed["deferred"]:
                    if isinstance(d,dict) and d not in deferred:deferred.append(d)
            recs.append({
                "current_ids":[x["id"] for x in batch],
                "result":output,"accepted_total":len(accepted),
                "deferred_after":deferred.copy(),
                "all_committed_blocks":accepted.copy(),
            })
            history.extend(batch)
            print("STEP",name,mode,batch[-1]["id"],
                  "NEW_BLOCKS",len(parsed.get("new_blocks",[])) if isinstance(parsed.get("new_blocks"),list) else "?",
                  "PENDING",len(deferred),"PARSE_ERROR",parsed.get("_parse_error",False),flush=True)
            print("TEXT",json.dumps(parsed,ensure_ascii=False)[:1500],flush=True)
            report["results"].append({"name":name,"mode":mode,"kind":kind,"steps":recs})
            OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2))
        # cumulative per-step receipts are duplicated in report intentionally to allow replay.
    print("FINISHED",round(time.monotonic()-start,1),"seconds",flush=True)

if __name__=="__main__":
    main()
