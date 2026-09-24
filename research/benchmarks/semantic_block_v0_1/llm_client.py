"""Isolated LLM and embedding client for Issue #19 research benchmark.

Enforces:
- Locked model family and revision: gemini-2.5-flash
- Seed: 42, Temperature: 0.0
- Token accounting and latency tracking
- Per-request and total budget limits (<=8192 input, <=2048 output tokens)
- Disk caching for deterministic reproducible replay
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from research.semantic_parser.client import load_gemini_api_key

MODEL_NAME = "gemini-3.1-flash-lite"
EMBEDDING_MODEL = "gemini-embedding-001"
DEFAULT_SEED = 42
DEFAULT_TEMP = 0.0
MAX_INPUT_TOKENS = 8192
MAX_OUTPUT_TOKENS = 2048


@dataclass
class CallResult:
    content: dict[str, Any]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    model_version: str
    cached: bool


class BenchmarkLLMClient:
    """LLM client for benchmark arm execution."""

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        self.api_key = load_gemini_api_key()
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY required for benchmark execution.")
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, prompt: str, system_instruction: str, seed: int, temp: float) -> str:
        h = hashlib.sha256()
        h.update(MODEL_NAME.encode("utf-8"))
        h.update(str(seed).encode("utf-8"))
        h.update(str(temp).encode("utf-8"))
        h.update(system_instruction.encode("utf-8"))
        h.update(prompt.encode("utf-8"))
        return h.hexdigest()

    def generate_structured_json(
        self,
        prompt: str,
        *,
        system_instruction: str = "",
        seed: int = DEFAULT_SEED,
        temperature: float = DEFAULT_TEMP,
    ) -> CallResult:
        ckey = self._cache_key(prompt, system_instruction, seed, temperature)
        if self.cache_dir:
            cpath = self.cache_dir / f"{ckey}.json"
            if cpath.exists():
                try:
                    data = json.loads(cpath.read_text(encoding="utf-8"))
                    return CallResult(
                        content=data["content"],
                        prompt_tokens=data.get("prompt_tokens", 0),
                        completion_tokens=data.get("completion_tokens", 0),
                        total_tokens=data.get("total_tokens", 0),
                        latency_ms=data.get("latency_ms", 0.0),
                        model_version=data.get("model_version", MODEL_NAME),
                        cached=True,
                    )
                except Exception:
                    pass

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={self.api_key}"
        combined = f"SYSTEM INSTRUCTIONS:\n{system_instruction}\n\nUSER PROMPT:\n{prompt}"
        payload = {
            "contents": [{"parts": [{"text": combined}]}],
            "generationConfig": {
                "temperature": temperature,
                "seed": seed,
                "maxOutputTokens": MAX_OUTPUT_TOKENS,
                "responseMimeType": "application/json",
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        max_retries = 20
        base_delay = 2.0
        last_error = None

        t0 = time.perf_counter()
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=60) as resp:
                    resp_json = json.loads(resp.read().decode("utf-8"))
                latency_ms = (time.perf_counter() - t0) * 1000.0

                candidate = resp_json.get("candidates", [{}])[0]
                text_content = candidate.get("content", {}).get("parts", [{}])[0].get("text", "{}")
                # Strip any accidental markdown formatting
                t_clean = text_content.strip()
                if t_clean.startswith("```json"):
                    t_clean = t_clean[7:]
                elif t_clean.startswith("```"):
                    t_clean = t_clean[3:]
                if t_clean.endswith("```"):
                    t_clean = t_clean[:-3]
                parsed = json.loads(t_clean.strip())

                usage = resp_json.get("usageMetadata", {})
                prompt_tokens = usage.get("promptTokenCount", 0)
                completion_tokens = usage.get("candidatesTokenCount", 0)
                total_tokens = usage.get("totalTokenCount", prompt_tokens + completion_tokens)
                model_ver = resp_json.get("modelVersion", MODEL_NAME)

                result = CallResult(
                    content=parsed,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    model_version=model_ver,
                    cached=False,
                )

                if self.cache_dir:
                    cpath = self.cache_dir / f"{ckey}.json"
                    cpath.write_text(
                        json.dumps({
                            "content": parsed,
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens,
                            "latency_ms": latency_ms,
                            "model_version": model_ver,
                        }, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                # Polite pacing between live calls
                time.sleep(1.5)
                return result

            except urllib.error.HTTPError as e:
                last_error = e
                if e.code in (429, 500, 503):
                    wait_time = 5.0 + 3.0 * attempt if e.code in (500, 503) else 25.0 + 10.0 * attempt
                    try:
                        err_body = e.read().decode("utf-8")
                        err_json = json.loads(err_body)
                        for d in err_json.get("error", {}).get("details", []):
                            if "retryDelay" in d:
                                wait_time = float(d["retryDelay"].rstrip("s")) + 2.5
                                break
                    except Exception:
                        pass
                    print(f"Transient HTTP error ({e.code}), waiting {wait_time:.1f}s before retry (attempt {attempt+1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                err_body = e.read().decode("utf-8") if hasattr(e, "read") else ""
                raise RuntimeError(f"HTTPError {e.code}: {err_body}") from e
            except Exception as e:
                last_error = e
                delay = min(25.0, 3.0 * (1.25 ** attempt))
                print(f"Transient exception ({type(e).__name__}: {e}), waiting {delay:.1f}s before retry (attempt {attempt+1}/{max_retries})...")
                time.sleep(delay)

        raise RuntimeError(f"Exceeded max retries: {last_error}")


def embed_texts(texts: list[str], cache_dir: Path | str | None = None) -> list[list[float]]:
    """Generate normalized embeddings via gemini-embedding-001 with disk caching."""
    api_key = load_gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY required for embeddings.")
    
    cdir = Path(cache_dir) if cache_dir else None
    if cdir:
        cdir.mkdir(parents=True, exist_ok=True)

    results: list[list[float]] = []
    for text in texts:
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if cdir:
            cpath = cdir / f"embed_{h}.json"
            if cpath.exists():
                try:
                    results.append(json.loads(cpath.read_text(encoding="utf-8")))
                    continue
                except Exception:
                    pass

        max_retries = 20
        last_error = None
        vec = None
        for attempt in range(max_retries):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent?key={api_key}"
                payload = {"content": {"parts": [{"text": text}]}}
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                vec = data["embedding"]["values"]
                time.sleep(0.5)
                break
            except urllib.error.HTTPError as e:
                last_error = e
                if e.code in (429, 500, 503):
                    wait_time = 5.0 + 3.0 * attempt if e.code in (500, 503) else 20.0 + 10.0 * attempt
                    print(f"Transient embedding HTTP error ({e.code}), waiting {wait_time:.1f}s before retry (attempt {attempt+1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                err_body = e.read().decode("utf-8") if hasattr(e, "read") else ""
                raise RuntimeError(f"HTTPError {e.code}: {err_body}") from e
            except Exception as e:
                last_error = e
                delay = min(25.0, 3.0 * (1.25 ** attempt))
                print(f"Transient embedding exception ({type(e).__name__}: {e}), waiting {delay:.1f}s before retry (attempt {attempt+1}/{max_retries})...")
                time.sleep(delay)

        if vec is None:
            raise RuntimeError(f"Exceeded max retries for embedding: {last_error}")

        results.append(vec)
        if cdir:
            cpath = cdir / f"embed_{h}.json"
            cpath.write_text(json.dumps(vec), encoding="utf-8")

    return results
