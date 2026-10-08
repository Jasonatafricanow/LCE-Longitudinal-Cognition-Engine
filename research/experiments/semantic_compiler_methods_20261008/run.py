"""Isolated semantic compilation METHOD comparison on fixed source evidence.

Compare:
  direct       : one-pass Body-like Block extraction (prior experiment baseline)
  closure      : Hindsight-inspired context/role/unknown reconstruction followed
                 by A-MEM-inspired independent self-contained notes
  closure_audit: identical closure proposal plus source/uncertainty/repetition
                 verification before admission.
Gold in fixtures.json["check"] is NEVER sent to a model call.
Experiment NEVER invokes embeddings or Path B.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from huggingface_hub import hf_hub_download
from llama_cpp import Llama

ROOT=Path(__file__).resolve().parent
FIXTURES=json.loads((ROOT/"fixtures.json").read_text(encoding="utf-8"))["cases"]
OUTPUT=Path("semantic_compiler_method_results.json")
MODEL_REPO="bartowski/Qwen2.5-3B-Instruct-GGUF"
MODEL_FILE="Qwen2.5-3B-Instruct-Q4_K_M.gguf"
METHODS=("direct","closure","closure_audit")

DIRECT_SYS="""执行语义编译，不是为预设Graph写摘要。基于截止时点的全部上下文，写已经可以确认的独立、完整、可自我理解的认知。一个来源允许形成多个不同Block；多个来源也可支持同一Block；可以零产出；不用争夺排他边界。若指代、关系尚不清楚，保留未决而不猜想。不要重复已有Block，不要把猜测写成既成事实。每条Block引用真正支持该内容的全部必要来源ID。只输出JSON：new_blocks:[{content,source_ids}],deferred:[{unresolved_text,source_ids}],resolved_deferred_ids:[id]。"""
CLOSURE_SYS="""执行上下文重建，不负责决定下游Graph的边，也不要将对话强行分割为几个主题。逐项恢复已明确的对象、参与者、角色、条件、否定、指代、理由、认知状态及语义关系；一来源允许支持多个认知，多来源允许支持同一认知；不要为了数量筛掉旁支。每一项必须引用足够的真实来源ID。遇到证据不足的对象和未决关系要明确留下，不得提前用未来轮次解释过去。根据当前输入的完整截止上下文提取，不得借助未来知识。JSON仅返回：understood:[{meaning,source_ids,epistemic}],unresolved:[{unresolved_text,source_ids}],clarifications:[{meaning,source_ids}]。"""
NOTES_SYS="""你收到的是已经按实际截止时点重建的语义清单。请按A-MEM式自包含认知Note原则生成可脱离原文独立理解的SemanticBlock：0到任意多个均可，同源多Block、多源同Block均可，只有语义完整性决定边界；不要固定数量，不要为了预设长链删除其他独立认知。参照已有已承认Block，只输出新增的认知（纠正/追加可新增但不覆盖已有的时间历史）；没新认知时严格返回空数组。时间未明确的关系放到deferred，后来资料能够明确时才提供解决的deferred ID；必须保持原来的历史已知范围。新Block必须标所有必要的来源ID而不仅仅标存在的ID。JSON仅返回：new_blocks:[{content,source_ids}],deferred:[{unresolved_text,source_ids}],resolved_deferred_ids:[id]。"""
AUDIT_SYS="""你是独立来源与时态审查器，不负责发明新事实、增加新的Block或追求下游Line。逐个审查candidate_blocks：
(1) 断言是否确实受到列出的证据支持，引用是否遗漏必要的来源、误把别的来源算作证据；
(2) 与已经承认的Block是否语义重复（仅改写不算新Block）；
(3) 是否把不确定/未决关系提前编译为事实；
(4) 是否把同一来源的无关认知强行合并。
allow仅在全部通过时；sources_wrong但其他方面有效时 action="fix_sources"，返回确切必要的证据ID，不能凭空改变content；其他情况 reject 或 defer，说明理由。先前已接受的Block保持不动。
另审查 propose_resolved_deferred_ids 是否已有新证据支持化解；别仅因对话又提到相关话题就自动结案。
严格JSON：decisions:[{index,action,source_ids,reason}],valid_resolved_deferred_ids:[id]。action仅 allow/fix_sources/defer/reject。"""

def encode(value):return json.dumps(value,ensure_ascii=False,sort_keys=True)
def norm(value):return re.sub(r"[\s，。；;、.!?！？]+","",str(value)).strip()
def parse(raw):
    try:return json.loads(raw.strip())
    except (ValueError,TypeError):
        matched=re.search(r"\{[\s\S]*\}",raw)
        if matched:
            try:return json.loads(matched.group(0))
            except ValueError:pass
        return {"_parse_error":True,"raw":raw}

def call(llm,system,payload,max_tokens=650):
    start=time.monotonic()
    resp=llm.create_chat_completion(
      messages=[{"role":"system","content":system},
                {"role":"user","content":encode(payload)}],
      response_format={"type":"json_object"},temperature=0.,top_p=1.,
      max_tokens=max_tokens)
    msg=resp["choices"][0]["message"]["content"]
    return {
      "parsed":parse(msg),"raw":msg,"seconds":round(time.monotonic()-start,2),
      "usage":resp.get("usage",{}),
      "prompt_sha256":hashlib.sha256((system+encode(payload)).encode()).hexdigest()
    }

def compact_blocks(blocks):
    return [{k:b[k] for k in ("id","content","source_ids","committed_at")} for b in blocks]

def add_deferred(pending,candidates,valid_refs,turn_id):
    inserted=[]
    for p in candidates if isinstance(candidates,list) else []:
        if not isinstance(p,dict):continue
        meaning=p.get("unresolved_text")
        if not isinstance(meaning,str) or not meaning.strip():continue
        ids=p.get("source_ids",[])
        if not isinstance(ids,list) or not ids or any(x not in valid_refs for x in ids):continue
        if any(norm(d["unresolved_text"])==norm(meaning) and d["status"]=="open" for d in pending):continue
        d={"id":f"D{len(pending)+1}","unresolved_text":meaning,
           "source_ids":ids,"opened_at":turn_id,"status":"open","closed_at":None}
        pending.append(d);inserted.append(d["id"])
    return inserted

def evaluate_step(llm,method,episode,turn,history,accepted,pending):
    now=history+[turn]
    ids={x["id"] for x in now}
    current_pending=[d.copy() for d in pending if d["status"]=="open"]
    base={"history_cutoff":turn["id"],"evidence_up_to_cutoff":now,
          "new_source_ids":[turn["id"]],"existing_blocks":compact_blocks(accepted),
          "pending_unresolved":current_pending}
    stages={}
    if method=="direct":
        stages["extract"]=call(llm,DIRECT_SYS,base)
        draft=stages["extract"]["parsed"]
        reconstructed=None
    else:
        stages["reconstruct"]=call(llm,CLOSURE_SYS,base,750)
        reconstructed=stages["reconstruct"]["parsed"]
        stages["notes"]=call(llm,NOTES_SYS,{**base,"reconstructed_meaning":reconstructed},800)
        draft=stages["notes"]["parsed"]
    proposal=draft.get("new_blocks",[]) if isinstance(draft,dict) else []
    proposed_deferred=draft.get("deferred",[]) if isinstance(draft,dict) else []
    resolution=draft.get("resolved_deferred_ids",[]) if isinstance(draft,dict) else []
    if not isinstance(proposal,list):proposal=[]
    if not isinstance(proposed_deferred,list):proposed_deferred=[]
    if not isinstance(resolution,list):resolution=[]
    if reconstructed and isinstance(reconstructed,dict):
        # Reconstruction and Note extraction are separate; preserve questions that
        # extraction forgot to repeat, not forced via case-specific expectations.
        u=reconstructed.get("unresolved",[])
        if isinstance(u,list):proposed_deferred=proposed_deferred+u
    if method=="closure_audit":
        review_input={**base,"candidate_blocks":proposal,
             "propose_resolved_deferred_ids":resolution,"proposed_unresolved":proposed_deferred}
        stages["audit"]=call(llm,AUDIT_SYS,review_input,750)
        review=stages["audit"]["parsed"]
        decisions=review.get("decisions",[]) if isinstance(review,dict) else []
        if not isinstance(decisions,list):decisions=[]
        verdicts={d.get("index"):d for d in decisions if isinstance(d,dict)}
        resolution=review.get("valid_resolved_deferred_ids",[]) if isinstance(review,dict) else []
        if not isinstance(resolution,list):resolution=[]
    else:verdicts={}
    new_accepted=[]
    rejected=[]
    for i,b in enumerate(proposal):
        if not isinstance(b,dict):
            rejected.append({"index":i,"why":"non-object"});continue
        content=b.get("content")
        source_ids=b.get("source_ids")
        if not isinstance(content,str) or not content.strip() or not isinstance(source_ids,list) or not source_ids or any(k not in ids for k in source_ids):
            rejected.append({"index":i,"why":"invalid data/unknown or future citation"});continue
        check=verdicts.get(i,{}) if method=="closure_audit" else {}
        action=check.get("action","reject") if method=="closure_audit" else "allow"
        if action=="fix_sources":
            revised=check.get("source_ids")
            if not isinstance(revised,list) or not revised or any(k not in ids for k in revised):
                rejected.append({"index":i,"why":"invalid corrected provenance"});continue
            source_ids=revised
        elif action!="allow":
            rejected.append({"index":i,"why":action,"review":check.get("reason","")})
            if action=="defer":
                proposed_deferred.append({"unresolved_text":content,"source_ids":source_ids})
            continue
        if any(norm(x["content"])==norm(content) for x in accepted+new_accepted):
            rejected.append({"index":i,"why":"exact normalized semantic duplicate"});continue
        block={"id":f"B{len(accepted)+len(new_accepted)+1}","content":content,
               "source_ids":source_ids,"committed_at":turn["id"]}
        new_accepted.append(block)
    accepted.extend(new_accepted)
    inserted=add_deferred(pending,proposed_deferred,ids,turn["id"])
    closed=[]
    for ref in resolution:
        for d in pending:
            if ref==d["id"] and d["status"]=="open":
                d["status"]="resolved";d["closed_at"]=turn["id"];closed.append(ref)
    return {
       "episode":episode,"method":method,"cutoff":turn["id"],
       "raw_stages":stages,"draft_blocks":proposal,"new_accepted":new_accepted,
       "rejected":rejected,"deferred_added":inserted,
       "deferred_resolved":closed,
       "unresolved_remaining":[d["id"] for d in pending if d["status"]=="open"],
       "cumulative_accepted":compact_blocks(accepted),
       "cumulative_deferred":[d.copy() for d in pending],
    }

def main():
    start=time.monotonic()
    print("MODEL",MODEL_REPO+"/"+MODEL_FILE,flush=True)
    file=hf_hub_download(repo_id=MODEL_REPO,filename=MODEL_FILE)
    print("MODEL_BYTES",Path(file).stat().st_size,flush=True)
    llm=Llama(model_path=file,n_ctx=6144,n_threads=2,n_batch=256,
              n_gpu_layers=0,verbose=False)
    report={
        "model":MODEL_REPO+"/"+MODEL_FILE,"methods":METHODS,
        "fixture_sha256":hashlib.sha256((ROOT/"fixtures.json").read_bytes()).hexdigest(),
        "limitations":[
          "Corpus is privacy-reduced adaptations plus controlled synthetic cases, not raw private dialogues.",
          "Gold is prewritten but single-author, unadjudicated, and is never sent to the model.",
          "Methods differ in calls and total tokens; interpret as method/cost comparison not equal-compute ablation.",
          "The 3B quantized model is a diagnostic tool, not proof about the Body LLM's competence.",
          "The independent semantic auditor is fallible, not an authoritative ground-truth oracle.",
          "No Embedding, Path B, production data changes or Line tuning."
        ],
        "steps":[],"runtime_seconds":None}
    for method in METHODS:
        for case in FIXTURES:
            accepted=[];pending=[];history=[]
            for turn in case["turns"]:
                step=evaluate_step(llm,method,case["id"],turn,history,accepted,pending)
                report["steps"].append(step)
                history.append(turn)
                report["runtime_seconds"]=round(time.monotonic()-start,1)
                OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
                print("STEP",method,case["id"],turn["id"],
                      "draft",len(step["draft_blocks"]),
                      "admitted",len(step["new_accepted"]),
                      "rejected",len(step["rejected"]),
                      "pending",step["unresolved_remaining"],
                      "closed",step["deferred_resolved"],flush=True)
                for item in step["new_accepted"]:
                    print("ADMITTED",encode(item)[:1100],flush=True)
                if step["rejected"]:
                    print("REJECTED",encode(step["rejected"])[:900],flush=True)
    print("DONE",report["runtime_seconds"],"seconds","steps",len(report["steps"]),flush=True)

if __name__=="__main__":main()
