"""LLM Execution Runner for Semantic Compilation Body/AGY Experiment V1.

Implements multi-model execution and disk caching (§10, §15):
- Arm A: DeepSeek-V4-Flash (Production Body Host) via AMD / ModelScope API
- Arm B: Gemini-2.5-Flash (AGY High-Capability Anchor) with Google multi-key rotation
- Arm C: GLM-4-Flash (Lower Bound Reference) via Zhipu API

Enforces full provenance metadata recording:
- model identity, model version, prompt version, schema version, temperature, latency, timestamp.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import dotenv
import requests
from openai import OpenAI

from research.experiments.semantic_compilation_body_v1.schema import SemanticParseResultV1
from research.experiments.semantic_compilation_body_v1.validator import validate_parse_result

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Load secrets
ENV_PATHS = [
    HERE.parent.parent.parent / "model-gateway" / ".env",
    Path("C:/projects/model-gateway/.env"),
]
for p in ENV_PATHS:
    if p.exists():
        dotenv.load_dotenv(p)

SYSTEM_PROMPT = (HERE / "prompt.md").read_text(encoding="utf-8")
PROMPT_VERSION = "body_sidecar_v1.0"
SCHEMA_VERSION = "semantic_parse_v1"


def get_google_keys() -> list[str]:
    keys = []
    for k in ["GOOGLE_API_KEY_1", "GOOGLE_API_KEY_2", "GOOGLE_API_KEY_3", "GOOGLE_API_KEY_4", "GOOGLE_API_KEY_5", "GEMINI_API_KEY"]:
        val = os.environ.get(k)
        if val and val.strip() and val.strip() not in keys:
            keys.append(val.strip())
    return keys


class ModelRunner:
    def __init__(self, model_arm: str = "deepseek_v4_flash", temperature: float = 0.0) -> None:
        self.model_arm = model_arm
        self.temperature = temperature
        self.cache_dir = CACHE_DIR / model_arm
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.google_keys = get_google_keys()
        self.google_key_idx = 0

    def _next_google_key(self) -> str:
        if not self.google_keys:
            raise RuntimeError("No Google API keys available in environment.")
        key = self.google_keys[self.google_key_idx % len(self.google_keys)]
        self.google_key_idx += 1
        return key

    def format_user_prompt(self, case: dict[str, Any]) -> str:
        lines = [
            f"Please parse the following conversation window (Case ID: {case['case_id']}) into semantic points and dependencies:",
            ""
        ]
        for turn in case["dialogue"]:
            speaker = turn.get("speaker", "user")
            eid = turn.get("evidence_id", "E")
            text = turn.get("text", "")
            lines.append(f"[{eid}] {speaker}: {text}")
        lines.append("")
        lines.append("Output strictly valid JSON matching SemanticParseResultV1 schema.")
        return "\n".join(lines)

    def _call_deepseek_amd(self, user_content: str) -> tuple[str, dict[str, Any]]:
        api_key = os.environ.get("AMD_API_KEY")
        client = OpenAI(
            api_key=api_key,
            base_url="https://developer.amd.com.cn/radeon/api/v1",
        )
        res = client.chat.completions.create(
            model="DeepSeek-V4-Flash",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=self.temperature,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        raw_text = res.choices[0].message.content or ""
        usage = {
            "prompt_tokens": res.usage.prompt_tokens if res.usage else 0,
            "completion_tokens": res.usage.completion_tokens if res.usage else 0,
            "total_tokens": res.usage.total_tokens if res.usage else 0,
        }
        return raw_text, usage

    def _call_gemini(self, user_content: str) -> tuple[str, dict[str, Any]]:
        max_attempts = 4
        last_err = None
        for attempt in range(max_attempts):
            key = self._next_google_key()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={key}"
            payload = {
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": [{"parts": [{"text": user_content}]}],
                "generationConfig": {
                    "temperature": self.temperature,
                    "maxOutputTokens": 8192,
                    "responseMimeType": "application/json",
                    "thinkingConfig": {"thinkingBudget": 0},
                },
            }
            try:
                resp = requests.post(url, json=payload, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        raw_text = candidates[0]["content"]["parts"][0]["text"]
                        usage_meta = data.get("usageMetadata", {})
                        usage = {
                            "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                            "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
                            "total_tokens": usage_meta.get("totalTokenCount", 0),
                        }
                        return raw_text, usage
                elif resp.status_code in (429, 503):
                    time.sleep(1.0 + attempt)
                    continue
                else:
                    last_err = f"HTTP {resp.status_code}: {resp.text}"
            except Exception as e:
                last_err = str(e)
                time.sleep(1.0)
        raise RuntimeError(f"Gemini call failed after {max_attempts} attempts: {last_err}")

    def _call_glm(self, user_content: str) -> tuple[str, dict[str, Any]]:
        api_key = os.environ.get("GLM_API_KEY")
        client = OpenAI(
            api_key=api_key,
            base_url="https://open.bigmodel.cn/api/paas/v4/",
        )
        res = client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=self.temperature,
            max_tokens=2048,
        )
        raw_text = res.choices[0].message.content or ""
        usage = {
            "prompt_tokens": res.usage.prompt_tokens if res.usage else 0,
            "completion_tokens": res.usage.completion_tokens if res.usage else 0,
            "total_tokens": res.usage.total_tokens if res.usage else 0,
        }
        return raw_text, usage

    def run_case(self, case: dict[str, Any], use_cache: bool = True) -> dict[str, Any]:
        case_id = case["case_id"]
        cache_file = self.cache_dir / f"{case_id}.json"

        if use_cache and cache_file.exists():
            return json.loads(cache_file.read_text(encoding="utf-8"))

        user_content = self.format_user_prompt(case)
        source_refs = [t["evidence_id"] for t in case["dialogue"]]

        start_time = time.time()
        if self.model_arm == "deepseek_v4_flash":
            raw_text, usage = self._call_deepseek_amd(user_content)
            model_identity = "DeepSeek-V4-Flash"
            model_provider = "amd_radeon_inference"
        elif self.model_arm == "gemini_2_5_flash":
            raw_text, usage = self._call_gemini(user_content)
            model_identity = "gemini-3-flash-preview"
            model_provider = "google_genai"
        elif self.model_arm == "glm_4_flash":
            raw_text, usage = self._call_glm(user_content)
            model_identity = "glm-4-flash"
            model_provider = "zhipu_ai"
        else:
            raise ValueError(f"Unknown model arm: {self.model_arm}")

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Validate proposal
        parse_result, diagnostics = validate_parse_result(raw_text, source_refs)

        record = {
            "case_id": case_id,
            "model_arm": self.model_arm,
            "model_identity": model_identity,
            "model_provider": model_provider,
            "prompt_version": PROMPT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "temperature": self.temperature,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latency_ms": elapsed_ms,
            "usage": usage,
            "raw_output": raw_text,
            "diagnostics": diagnostics,
            "validated_parse": parse_result.model_dump(),
        }

        # Cache result
        cache_file.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        return record
