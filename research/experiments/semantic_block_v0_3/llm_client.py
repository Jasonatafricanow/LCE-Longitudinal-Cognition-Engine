"""LLM and Embedding Client for SemanticBlock v0.3 Benchmark.

Enforces:
- Locked model: gemini-3.1-flash-lite
- Locked embedding: gemini-embedding-001
- Seed: 42, Temperature: 0.0
- Deterministic disk caching
- Multi-key rotation across available Google API keys
- Automatic local proxy (127.0.0.1:7890) support
- Token accounting and latency tracking
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

MODEL_NAME = "gemini-3.1-flash-lite"
EMBEDDING_MODEL = "gemini-embedding-001"
DEFAULT_SEED = 42
DEFAULT_TEMP = 0.0
MAX_RETRIES = 25
BASE_BACKOFF = 2.0


def setup_proxy():
    """Configure urllib proxy if local proxy is active."""
    proxy_urls = ["http://127.0.0.1:7890", "http://localhost:7890"]
    for p_url in proxy_urls:
        try:
            proxy_handler = urllib.request.ProxyHandler({"http": p_url, "https": p_url})
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)
            break
        except Exception:
            pass


setup_proxy()


def load_all_keys() -> list[str]:
    """Load all distinct Google API keys from environment and secret files."""
    keys = []
    # 1. Check environment
    for k in ["GEMINI_API_KEY", "GOOGLE_API_KEY_1", "GOOGLE_API_KEY_2", "GOOGLE_API_KEY_3", "GOOGLE_API_KEY_4", "GOOGLE_API_KEY_5"]:
        val = os.environ.get(k)
        if val and val.strip() and val.strip() not in keys:
            keys.append(val.strip())

    # 2. Check local secret paths
    search_paths = [
        Path(r"C:\projects\model-gateway\.env"),
        Path(os.environ.get("USERPROFILE", r"C:\Users\Temp")) / ".hermes" / "profiles" / "xiyue" / ".env",
    ]
    for p in search_paths:
        if p.exists():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("GOOGLE_API_KEY_") or line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and val not in keys:
                            keys.append(val)
            except Exception:
                pass

    if not keys:
        raise RuntimeError("No Google API keys found in environment or credential files.")
    return keys


@dataclass
class CallResult:
    content: dict[str, Any]
    raw_text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    model_version: str
    cached: bool


class BenchmarkLLMClient:
    """Client for generating JSON and embeddings with multi-key rotation and caching."""

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        self.keys = load_all_keys()
        self.key_index = 0
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_calls = 0
        self.total_latency_ms = 0.0

    def get_current_key(self) -> str:
        return self.keys[self.key_index % len(self.keys)]

    def rotate_key(self) -> str:
        self.key_index += 1
        return self.get_current_key()

    def _cache_key(self, prompt: str, system_instruction: str, seed: int, temp: float) -> str:
        h = hashlib.sha256()
        h.update(MODEL_NAME.encode("utf-8"))
        h.update(str(seed).encode("utf-8"))
        h.update(str(temp).encode("utf-8"))
        h.update(system_instruction.encode("utf-8"))
        h.update(prompt.encode("utf-8"))
        return h.hexdigest()

    def generate_json(
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
                    res = CallResult(
                        content=data["content"],
                        raw_text=data.get("raw_text", ""),
                        prompt_tokens=data.get("prompt_tokens", 0),
                        completion_tokens=data.get("completion_tokens", 0),
                        total_tokens=data.get("total_tokens", 0),
                        latency_ms=data.get("latency_ms", 0.0),
                        model_version=data.get("model_version", MODEL_NAME),
                        cached=True,
                    )
                    self.total_calls += 1
                    return res
                except Exception:
                    pass

        parts = []
        if system_instruction:
            parts.append({"text": f"SYSTEM INSTRUCTIONS:\n{system_instruction}\n\nUSER PROMPT:\n{prompt}"})
        else:
            parts.append({"text": prompt})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "seed": seed,
                "responseMimeType": "application/json",
            },
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        last_error = None
        t0 = time.perf_counter()

        for attempt in range(MAX_RETRIES):
            key = self.get_current_key()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={key}"
            try:
                req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_json = json.loads(resp.read().decode("utf-8"))
                latency_ms = (time.perf_counter() - t0) * 1000.0

                candidate = resp_json.get("candidates", [{}])[0]
                text_content = candidate.get("content", {}).get("parts", [{}])[0].get("text", "{}")

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

                self.total_calls += 1
                self.total_prompt_tokens += prompt_tokens
                self.total_completion_tokens += completion_tokens
                self.total_latency_ms += latency_ms

                res = CallResult(
                    content=parsed,
                    raw_text=text_content,
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
                            "raw_text": text_content,
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens,
                            "latency_ms": latency_ms,
                            "model_version": model_ver,
                        }, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                # Rotate key politely for next call
                self.rotate_key()
                time.sleep(0.3)
                return res

            except urllib.error.HTTPError as e:
                last_error = e
                # Rotate key immediately on 429
                self.rotate_key()
                wait_time = BASE_BACKOFF * (1.2 ** attempt)
                if e.code == 429:
                    wait_time = min(15.0, wait_time + 2.0)
                time.sleep(wait_time)
            except Exception as e:
                last_error = e
                self.rotate_key()
                time.sleep(BASE_BACKOFF * (1.2 ** attempt))

        raise RuntimeError(f"Exceeded max retries in generate_json: {last_error}")

    def embed_text(self, text: str) -> list[float]:
        """Embed text using gemini-embedding-001 with disk caching and key rotation."""
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if self.cache_dir:
            cpath = self.cache_dir / f"embed_{h}.json"
            if cpath.exists():
                try:
                    return json.loads(cpath.read_text(encoding="utf-8"))
                except Exception:
                    pass

        payload = {"content": {"parts": [{"text": text}]}}
        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        last_error = None
        for attempt in range(MAX_RETRIES):
            key = self.get_current_key()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent?key={key}"
            try:
                req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                vec = data["embedding"]["values"]
                if self.cache_dir:
                    cpath = self.cache_dir / f"embed_{h}.json"
                    cpath.write_text(json.dumps(vec), encoding="utf-8")
                self.rotate_key()
                time.sleep(0.15)
                return vec
            except urllib.error.HTTPError as e:
                last_error = e
                self.rotate_key()
                wait_time = min(10.0, 1.5 * (1.2 ** attempt))
                time.sleep(wait_time)
            except Exception as e:
                last_error = e
                self.rotate_key()
                time.sleep(min(10.0, 1.5 * (1.2 ** attempt)))

        raise RuntimeError(f"Exceeded max retries in embed_text: {last_error}")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]
