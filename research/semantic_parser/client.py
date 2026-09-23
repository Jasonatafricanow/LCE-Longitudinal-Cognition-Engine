"""LLM client for AGY Semantic Parser with caching, retries, and offline support."""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "gemini-3.5-flash"
DEFAULT_TEMPERATURE = 0.1
MAX_RETRIES = 8
BASE_RETRY_DELAY = 4.0


def load_gemini_api_key() -> str | None:
    """Find and return Gemini API key from environment or local credential files."""
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    search_paths = [
        Path(r"C:\projects\model-gateway\.env"),
        Path(os.environ.get("USERPROFILE", r"C:\Users\Temp")) / ".hermes" / "profiles" / "xiyue" / ".env",
    ]
    for p in search_paths:
        if p.exists():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
            except Exception:
                pass
    return None


def clean_json_response(text: str) -> str:
    """Strip markdown code block fences and return raw JSON string."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


class GeminiClient:
    """Client for generating structured JSON via Google Gemini API with disk caching."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        fallback_models: list[str] | None = None,
        temperature: float = DEFAULT_TEMPERATURE,
        cache_dir: Path | str | None = None,
        mock_mode: bool = False,
    ) -> None:
        self.api_key = api_key or load_gemini_api_key()
        self.model = model
        self.fallback_models = fallback_models or ["gemini-3.5-flash-lite"]
        self.temperature = temperature
        self.mock_mode = mock_mode
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, prompt: str, system_instruction: str) -> str:
        h = hashlib.sha256()
        h.update(self.model.encode("utf-8"))
        h.update(str(self.temperature).encode("utf-8"))
        h.update(system_instruction.encode("utf-8"))
        h.update(prompt.encode("utf-8"))
        return h.hexdigest()

    def generate_json(self, prompt: str, *, system_instruction: str = "") -> dict[str, Any]:
        """Generate a JSON object from Gemini, utilizing cache if available."""
        # 1. Check disk cache
        if self.cache_dir:
            ckey = self._cache_key(prompt, system_instruction)
            cache_file = self.cache_dir / f"{ckey}.json"
            if cache_file.exists():
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass

        # 2. Check mock mode
        if self.mock_mode or not self.api_key:
            if not self.api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is not set and no cached response was found. "
                    "Cannot execute live parser call."
                )
            return {"units": [], "relations": []}

        # 3. Live call with retries and fallback models
        combined_prompt = f"SYSTEM INSTRUCTIONS:\n{system_instruction}\n\nUSER PROMPT:\n{prompt}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": combined_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": 8192,
                "responseMimeType": "application/json",
            },
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        model_candidates = [self.model] + [m for m in self.fallback_models if m != self.model]
        last_error = None
        for attempt in range(MAX_RETRIES):
            current_model = model_candidates[attempt % len(model_candidates)]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={self.api_key}"
            try:
                req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=90) as resp:
                    resp_json = json.loads(resp.read().decode("utf-8"))

                candidate = resp_json["candidates"][0]
                content_part = candidate["content"]["parts"][0]["text"]
                cleaned_text = clean_json_response(content_part)
                parsed = json.loads(cleaned_text)

                # Save to cache if successful
                if self.cache_dir:
                    ckey = self._cache_key(prompt, system_instruction)
                    cache_file = self.cache_dir / f"{ckey}.json"
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(parsed, f, ensure_ascii=False, indent=2)

                return parsed

            except urllib.error.HTTPError as e:
                last_error = e
                err_msg = e.read().decode("utf-8", errors="replace")
                # Rate limit (429) or transient server error (500, 503)
                if e.code in (429, 500, 503):
                    delay = min(20.0, BASE_RETRY_DELAY * (1.3 ** attempt))
                    print(f"[GeminiClient] HTTP {e.code} on model '{current_model}' (attempt {attempt+1}/{MAX_RETRIES}). Backing off {delay:.1f}s... Info: {err_msg[:80]}")
                    time.sleep(delay)
                else:
                    raise RuntimeError(f"Gemini API error (HTTP {e.code}): {err_msg}") from e
            except Exception as e:
                last_error = e
                delay = min(20.0, BASE_RETRY_DELAY * (1.3 ** attempt))
                print(f"[GeminiClient] Error on model '{current_model}' (attempt {attempt+1}/{MAX_RETRIES}): {e}. Backing off {delay:.1f}s...")
                time.sleep(delay)

        raise RuntimeError(f"Failed to generate JSON from Gemini after {MAX_RETRIES} attempts: {last_error}")
