"""Isolated semantic-relation ablation: actual LCE Path B supplier, two embeddings.

Data are privacy-reduced paraphrases of a previously frozen 13-Block three-topic
experiment, NOT the untouched historical user text. No model has access to gold
trajectory labels or downstream results during embedding.
"""
from __future__ import annotations
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from lce.reference_memory.contracts import RawEvidence, SemanticBlock
from lce.structure.trajectory import (
    ExactCosineNeighbourProvider,
    MutualKnnTrajectorySupplier,
    TrajectoryConfig,
)
from lce.testing.reference_memory import InMemoryReferenceMemory

CORPUS = [
  ("C1","compute","2026-07-27T12:04:00+00:00","研究者质疑仅凭设备折旧速度就否定算力租赁价值，认为实际回本能力及二手设备残值仍需结合市场条件判断。"),
  ("C2","compute","2026-08-02T12:02:00+00:00","研究者认为算力租赁的短期高收益来自供需约束形成的阶段性窗口，其盈利能力取决于付费利用率、购置成本与价差收敛，而不能只看静态回本期。"),
  ("C3","compute","2026-08-02T12:03:00+00:00","研究者推断如果云服务商在需求紧缺期扩容获利，新增需求会向加速卡和供应链传导；产能响应滞后可能进一步推升设备价格。"),
  ("C4","compute","2026-08-02T12:04:00+00:00","研究者提出按全生命周期经济收益评价算力设备，综合计入付费利用率、有效经济寿命、退出残值以及运维成本，而不是只看账面折旧。"),
  ("T1","trading","2026-07-27T12:08:00+00:00","研究者认为仅用日线数据无法可靠模拟盘中卖出与真实成交，价格和滑点误差可能改变回测盈利，因此需要更细粒度的交易数据。"),
  ("T2","trading","2026-07-27T12:09:00+00:00","研究者发现用买入当日收盘成交额筛选股票会引入未来信息，因此计划只采用交易当时已可观察的开盘半小时成交额与历史同期对照。"),
  ("T3","trading","2026-08-06T12:10:00+00:00","研究者怀疑回测收益来自人工预选股票而非交易信号本身，因此暂不把该表现归因为可重复的策略超额收益。"),
  ("T4","trading","2026-08-08T12:03:00+00:00","研究者计划固定回测样本截止日，将既有历史成绩与之后每日更新的模拟实盘结果分别跟踪，以核对策略信号与人工交易。"),
  ("T5","trading","2026-08-08T12:04:00+00:00","研究者计划将日内选股独立为实时信号系统，经分钟级K线核对后分别发送提醒与模拟交易执行，而不额外等待日线信号。"),
  ("P1","culture","2026-08-03T12:04:00+00:00","研究者用文化工业批判解释流行音乐的标准化和规避风险倾向，并认为商业机制可能吸纳和包装反叛艺术。"),
  ("P2","culture","2026-08-03T12:05:00+00:00","研究者认为地下音乐进入主流商业传播渠道可能削弱批判性，形成保留地下身份就难以扩大影响、进入大众市场又可能被收编的两难。"),
  ("P3","culture","2026-08-03T12:06:00+00:00","研究者认为作品需先被看见才会扩大影响，而进入公共解释后作者无法垄断其意义；读者的再解释可能延续作品的批判作用。"),
  ("N1","unrelated","2026-08-03T12:06:00+00:00","研究者要求人工智能审稿保持建设性与客观性，避免断章取义或稻草人论证，并在输出之前自检逻辑。"),
]
# Each intervention removes an expressed LOGICAL RELATION, not just a keyword.
# Crucially the original corpus is unchanged in the control condition.
FLATTEN = {
  "C1":"研究者讨论算力租赁业务、设备折旧、回本期和二手设备残值等经济信息。",
  "C2":"研究者讨论算力租赁的利用率、设备采购、供求水平、阶段利润和回本速度。",
  "C3":"研究者讨论云服务商、加速卡供应链、设备扩容和市场涨价等议题。",
  "C4":"研究者讨论算力设备经济寿命、运营成本、折旧和退出残值等指标。",
  "T1":"研究者讨论日线回测中的成交价格、滑点及分钟数据的使用。",
  "T2":"研究者讨论买入日成交额、开盘半小时成交额与历史数据的比较。",
  "T3":"研究者讨论策略表现、人工选股、交易信号以及超额收益评价。",
  "T4":"研究者讨论历史回测成绩、模拟实盘与实际交易记录的持续对比。",
  "T5":"研究者讨论日内选股、分钟K线、消息提醒和模拟交易系统。",
  "P1":"研究者讨论文化工业、商业流行音乐与反叛艺术的市场包装。",
  "P2":"研究者讨论地下音乐、商业传播、社会批判和大众市场。",
  "P3":"研究者讨论作品、传播渠道、作者、读者和公共解释。",
}
MODELS = [
  "BAAI/bge-small-zh-v1.5",
  "intfloat/multilingual-e5-small",
]
EXPECTED_ORDER_PAIRS = [
 ("C1","C2"),("C2","C3"),("C3","C4"),
 ("T1","T2"),("T2","T3"),("T3","T4"),("T4","T5"),
 ("P1","P2"),("P2","P3"),
]

def build_blocks(corpus):
    memory = InMemoryReferenceMemory()
    blocks=[]
    for bid,topic,stamp,sentence in corpus:
        dt=datetime.fromisoformat(stamp)
        memory.add_evidence(RawEvidence(
          evidence_id="e_"+bid,content=sentence,occurred_at=dt,known_at=dt,
          provenance={"source":"anonymized-conceptual-probe"}))
        block=memory.put_semantic_block(SemanticBlock(
          block_id=bid,content=sentence,raw_evidence_ids=("e_"+bid,),
          occurred_start=dt,occurred_end=dt,compiler_version="human-redacted-v1",
          lineage_id="concept-probe",metadata={"topic_control":topic},
          derived_known_at=dt,
        ))
        blocks.append(block)
    return memory,tuple(blocks)

def analysis(corpus,vectors,model_name):
    memory,blocks=build_blocks(corpus)
    memory.rebuild_vector_index(
       lambda b:tuple(float(i) for i in vectors[b.content]),
       index_version="experiment-"+model_name.replace("/","-"))
    selected={b.block_id: b for b in blocks}
    output={"model":model_name,"variants":{}}
    for threshold in (0.55,0.70):
        supplier=MutualKnnTrajectorySupplier(memory=memory,config=TrajectoryConfig(
          k=4,min_similarity=threshold,min_support=3))
        ordered=tuple(sorted(blocks,key=lambda b:(b.occurred_start,b.block_id)))
        emb={b.block_id: memory.get_vector(b.block_id,state_id=b.state_id).values for b in ordered}
        mutual=supplier._mutual_edges(ordered,emb)
        outgoing,scores=supplier._directed_graph(ordered,mutual)
        paths=supplier.propose(ordered)
        direct={(a,b) for a,child in outgoing.items() for b in child}
        outpairs=[f"{a}->{b}" for a,b in EXPECTED_ORDER_PAIRS if (a,b) in direct]
        contamination=[f"{a}<->{b}" for (a,b),score in mutual.items()
          if selected[a].metadata["topic_control"]!=selected[b].metadata["topic_control"]]
        output["variants"][str(threshold)]={
           "mutual_edges":len(mutual),"directed_edges":len(direct),
           "expected_directed_pairs":outpairs,
           "expected_directed_pair_count":len(outpairs),
           "cross_topic_mutual_pairs":contamination,
           "unrelated_N1_mutual_pairs":[f"{a}<->{b}" for a,b in mutual if "N1" in (a,b)],
           "candidate_paths":[list(x.block_ids) for x in paths],
           "mutual_edges_scored":[[a,b,round(score,5)] for (a,b),score in sorted(mutual.items())],
        }
    return output

def main():
    from sentence_transformers import SentenceTransformer
    src=Path(__file__).resolve()
    full_text="\n".join(x[3] for x in CORPUS)
    result={
      "limitations":[
        "Inputs are privacy-reduced paraphrases, not byte-identical original 13 manual Blocks.",
        "Timestamps are source-day plus synthetic ordinal order; these do not establish actual second-level historical order.",
        "Ablations shorten some text; differences do not isolate relation removal from word-count/style changes.",
        "Candidate paths are the production Path B supplier output, not confirmed persistent Lines or user cognition truth.",
        "No claim about an automatic semantic compiler follows from this experiment."
      ],
      "corpus_sha256":hashlib.sha256(full_text.encode()).hexdigest(),
      "case_count":len(CORPUS),"models":{}
    }
    texts=set(b[3] for b in CORPUS)|set(FLATTEN.values())
    controls={x[0] for x in CORPUS}
    assert len(controls)==13 and set(FLATTEN).issubset(controls)
    for model_name in MODELS:
        print("LOAD_MODEL:",model_name,flush=True)
        model=SentenceTransformer(model_name,device="cpu",trust_remote_code=False)
        terms=sorted(texts)
        prefix="passage: " if "multilingual-e5" in model_name else ""
        emb=model.encode([prefix+t for t in terms],batch_size=8,
                         normalize_embeddings=True,show_progress_bar=False)
        vectors={t:tuple(float(v) for v in emb[i]) for i,t in enumerate(terms)}
        variants={
          "full":CORPUS,
          "all_relation_flattened":[(i,tp,ts,FLATTEN.get(i,c)) for i,tp,ts,c in CORPUS],
        }
        for target in sorted(FLATTEN):
            variants["drop_"+target]=[(i,tp,ts,FLATTEN[i] if i==target else c) for i,tp,ts,c in CORPUS]
        report={"vector_dimensions":len(next(iter(vectors.values()))),"variants":{}}
        for label,corpus in variants.items():
            summary=analysis(corpus,vectors,model_name)
            report["variants"][label]=summary["variants"]
            high=summary["variants"]["0.55"]
            print("RESULT",model_name,label,"mutual",high["mutual_edges"],"expected",high["expected_directed_pair_count"],"paths",high["candidate_paths"],"neg",high["unrelated_N1_mutual_pairs"],flush=True)
        result["models"][model_name]=report
        Path("relation_ablation_results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("COMPLETED_MODELS",list(result["models"]),flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
