"""Isolated, privacy-trimmed proof-of-execution: cognition content only.
No manual targets are sent to the provider; no production imports. 
These are TECHNICAL EXCERPTS, not a full-context five-node reproduction.
"""
from __future__ import annotations
import json
import os
import urllib.request
from pathlib import Path

MODEL = "openai/gpt-4o"
URL = "https://models.github.ai/inference/chat/completions"
SYSTEM = """你是 SemanticBlock 内容编译器。只为最后一条【当前用户发言】编译一句完整、可长期独立引用的用户认知。不是话题摘要，也不回答问题。
按顺序在同次编译中：找本轮用户新增的认知动作；借前文恢复对象的功能角色及其关系；把本轮变化代入关系；保留提议/试探/纠正等立场；过滤仅属修辞、附带查询和不影响该认知的产品名/参数。
前文助手的说法可错；明确的用户纠正优先。不能使用当前轮之后信息，不得添加未经支持的既定事实。输出恰好一个 JSON 对象 {\"content\": \"...\"}，不输出推导过程。"""
# No outcome/gold carrier appears in these inputs.
CASES = [
  {
    "id": "399022-trimmed",
    "context": [
      "助手此前解释：Laya 是开源决策模型，提供 typed answers，不是通用生成式 LLM。",
      "助手介绍 Jev 为手机端聊天/交互框架，其中有独立的判断模型组件，也有生成回复组件。"
    ],
    "current": "我觉得不合理……我能不能用他这个框架去把jev换成laya……这么小的模型手机都塞得下"
  },
  {
    "id": "399051-trimmed",
    "context": [
      "用户此前提出：保留手机聊天框架，将原来的 Jev 决策组件替换成小型决策模型 Laya。",
      "用户纠正助手：Laya 和 Jev 一样是决策模型，而这类决策方案需要前置 LLM 做清洗。",
      "助手随后确认：正确的处理流程是前置语言模型进行清洗，再由 Laya 完成决策；曾考虑分设备运行。"
    ],
    "current": "主要是你知道edge Gallery 吗…可以本机跑gemma 4...然后laya又是个三百多m的小模型，好像也能塞进手机ram"
  }
]

def main():
    token = os.getenv("GH_MODELS_TOKEN", "")
    if not token:
        print("BLOCKED: GH_MODELS_TOKEN unavailable; no calls made")
        return 3
    print("MODEL_REQUESTED:", MODEL)
    results = []
    for case in CASES:
        payload = json.dumps({
            "model": MODEL, "temperature": 0.0, "top_p": 1.0,
            "messages": [
                {"role":"system","content": SYSTEM},
                {"role":"user","content":"历史上下文（按时间）:\\n" + "\\n".join(case["context"]) + "\\n当前用户发言:\\n" + case["current"]}
            ]
        }, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(URL, data=payload, headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28"
        }, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=75) as response:
                body = json.loads(response.read())
        except Exception as exc:
            # Never print token or full request headers.
            print(case["id"], "PROVIDER_ERROR", type(exc).__name__, getattr(exc,"code", None))
            return 4
        output = body["choices"][0]["message"]["content"]
        row = {"id": case["id"], "requested_model": MODEL,
               "returned_model": body.get("model"), "content_raw": output}
        results.append(row)
        print(json.dumps(row, ensure_ascii=False))
    Path("manual_block_probe_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2),encoding="utf-8")
    print("TWO_CASE_PROVIDER_RUN_COMPLETED; NOT FULL HISTORICAL REPRODUCTION")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
