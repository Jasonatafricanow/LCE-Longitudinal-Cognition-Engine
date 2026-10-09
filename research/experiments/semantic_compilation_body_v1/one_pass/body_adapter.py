"""Body Adapter for One-Pass Inference with DeepSeek-V4-Flash.

Implements single LLM call producing both:
  1. normal conversational assistant response
  2. structured semantic parsing sidecar

Features:
  - Dual endpoint support: Volces Ark & AMD Radeon (both DeepSeek-V4-Flash)
  - Automatic fallback & retry on 500/timeout
  - Disk caching & latency/token tracking
  - Fail-closed validation preserving assistant response
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import dotenv
import requests
from openai import OpenAI

from research.experiments.semantic_compilation_body_v1.one_pass.body_turn_contract import (
    BodyTurnResultV1,
    parse_and_validate_body_turn,
)

_logger = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
EXPERIMENT_ROOT = HERE.parent
CACHE_DIR = EXPERIMENT_ROOT / ".cache" / "deepseek_v4_flash_one_pass"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Load secrets from model-gateway .env if available
ENV_PATHS = [
    EXPERIMENT_ROOT.parent.parent.parent / "model-gateway" / ".env",
    Path("C:/projects/model-gateway/.env"),
]
for p in ENV_PATHS:
    if p.exists():
        dotenv.load_dotenv(p)

SYSTEM_PROMPT_DEFAULT = (HERE / "prompt_one_pass.md").read_text(encoding="utf-8")


class BodyAdapter:
    """One-pass Body Host adapter wrapping DeepSeek-V4-Flash."""

    def __init__(
        self,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        enable_cache: bool = True,
    ) -> None:
        self.system_prompt = system_prompt or SYSTEM_PROMPT_DEFAULT
        self.temperature = temperature
        self.enable_cache = enable_cache

        # Endpoints serving DeepSeek-V4-Flash
        self.endpoints = [
            {
                "name": "volces_ark",
                "base_url": "https://ark.cn-beijing.volces.com/api/plan/v3",
                "api_key": os.environ.get("ARK_API_KEY", ""),
                "model": "deepseek-v4-flash",
            },
            {
                "name": "amd_radeon",
                "base_url": "https://developer.amd.com.cn/radeon/api/v1",
                "api_key": os.environ.get("AMD_API_KEY", ""),
                "model": "DeepSeek-V4-Flash",
            },
        ]

    def format_turn_prompt(
        self, dialogue: list[dict[str, Any]], bounded_context: str | None = None
    ) -> str:
        """Format dialogue history and bounded context into prompt payload."""
        lines = []
        if bounded_context:
            lines.append("MR CURRENT CONTEXT")
            lines.append(bounded_context.strip())
            lines.append("")

        lines.append("Conversation Window (Raw Evidence):")
        for turn in dialogue:
            speaker = turn.get("speaker", "user")
            eid = turn.get("evidence_id", "E")
            text = turn.get("text", "")
            lines.append(f"[{eid}] {speaker}: {text}")

        lines.append("")
        lines.append("Provide your normal assistant response and semantic sidecar in BodyTurnResultV1 format.")
        return "\n".join(lines)

    def _call_api(self, prompt: str, system_override: str | None = None) -> tuple[str, dict[str, Any], float]:
        """Execute single call with automatic endpoint failover."""
        sys_prompt = system_override or self.system_prompt
        last_exc = None

        for ep in self.endpoints:
            client = OpenAI(api_key=ep["api_key"], base_url=ep["base_url"], timeout=180.0, max_retries=0)
            for attempt in range(1):
                try:
                    t0 = time.perf_counter()
                    res = client.chat.completions.create(
                        model=ep["model"],
                        messages=[
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=self.temperature,
                        max_tokens=4096,
                        response_format={"type": "json_object"},
                    )
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    content = res.choices[0].message.content or "{}"
                    usage = {
                        "prompt_tokens": res.usage.prompt_tokens if res.usage else 0,
                        "completion_tokens": res.usage.completion_tokens if res.usage else 0,
                        "total_tokens": res.usage.total_tokens if res.usage else 0,
                    }
                    return content, usage, latency_ms
                except Exception as exc:
                    _logger.warning("Endpoint %s attempt %d failed: %s", ep["name"], attempt + 1, exc)
                    last_exc = exc
                    time.sleep(1.0)

        raise RuntimeError(f"All DeepSeek-V4-Flash endpoints failed. Last error: {last_exc}")

    def run_turn(
        self,
        dialogue: list[dict[str, Any]],
        bounded_context: str | None = None,
        system_override: str | None = None,
        case_id: str | None = None,
    ) -> BodyTurnResultV1:
        """Run one-pass turn inference and return validated BodyTurnResultV1."""
        prompt = self.format_turn_prompt(dialogue, bounded_context)
        sys_prompt = system_override or self.system_prompt

        cache_key = hashlib.sha256(
            f"deepseek-v4-flash:{self.temperature}:{sys_prompt}:{prompt}".encode("utf-8")
        ).hexdigest()
        cache_file = CACHE_DIR / f"{cache_key}.json"

        if self.enable_cache and cache_file.exists():
            try:
                cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
                raw_content = cached_data["raw_content"]
                usage = cached_data["usage"]
                latency_ms = cached_data["latency_ms"]
            except Exception as exc:
                _logger.warning("Cache read error, calling API: %s", exc)
                raw_content, usage, latency_ms = self._call_api(prompt, sys_prompt)
                cache_file.write_text(
                    json.dumps(
                        {"raw_content": raw_content, "usage": usage, "latency_ms": latency_ms},
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
        else:
            raw_content, usage, latency_ms = self._call_api(prompt, sys_prompt)
            if self.enable_cache:
                cache_file.write_text(
                    json.dumps(
                        {"raw_content": raw_content, "usage": usage, "latency_ms": latency_ms},
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )

        result = parse_and_validate_body_turn(raw_content)
        result.latency_ms = latency_ms
        result.prompt_tokens = usage.get("prompt_tokens", 0)
        result.completion_tokens = usage.get("completion_tokens", 0)
        result.total_tokens = usage.get("total_tokens", 0)
        return result

    def run_baseline_turn(
        self,
        dialogue: list[dict[str, Any]],
        case_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute standard conversational turn WITHOUT semantic sidecar."""
        baseline_sys = "You are a helpful and polite conversational assistant. Respond naturally to the user."

        lines = ["Conversation:"]
        for turn in dialogue:
            speaker = turn.get("speaker", "user")
            text = turn.get("text", "")
            lines.append(f"{speaker}: {text}")
        prompt = "\n".join(lines)

        cache_key = hashlib.sha256(
            f"baseline:deepseek-v4-flash:{prompt}".encode("utf-8")
        ).hexdigest()
        cache_file = CACHE_DIR / f"{cache_key}.json"

        if self.enable_cache and cache_file.exists():
            return json.loads(cache_file.read_text(encoding="utf-8"))

        ep = self.endpoints[0]
        client = OpenAI(api_key=ep["api_key"], base_url=ep["base_url"], timeout=30.0)

        t0 = time.perf_counter()
        res = client.chat.completions.create(
            model=ep["model"],
            messages=[
                {"role": "system", "content": baseline_sys},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            max_tokens=1000,
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0

        content = res.choices[0].message.content or ""
        usage = {
            "prompt_tokens": res.usage.prompt_tokens if res.usage else 0,
            "completion_tokens": res.usage.completion_tokens if res.usage else 0,
            "total_tokens": res.usage.total_tokens if res.usage else 0,
        }
        out = {
            "assistant_response": content,
            "usage": usage,
            "latency_ms": latency_ms,
        }
        if self.enable_cache:
            cache_file.write_text(
                json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        return out
