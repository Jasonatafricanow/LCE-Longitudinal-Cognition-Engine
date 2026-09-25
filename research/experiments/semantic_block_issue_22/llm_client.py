"""LLM Client for SemanticBlock Issue #22 Experiment.

Extends BenchmarkLLMClient with experiment-specific caching and thread-safe multi-key rotation.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.experiments.semantic_block_v0_3.llm_client import (
    BenchmarkLLMClient as BaseLLMClient,
    CallResult,
)

BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def cosine_sim(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


class ThreadSafeBenchmarkLLMClient(BaseLLMClient):
    def __init__(self, cache_dir: Path | str | None = None) -> None:
        super().__init__(cache_dir=cache_dir)
        self._lock = threading.Lock()

    def rotate_key(self) -> str:
        with self._lock:
            self.key_index += 1
            return self.get_current_key()


BenchmarkLLMClient = ThreadSafeBenchmarkLLMClient


def get_llm_client() -> ThreadSafeBenchmarkLLMClient:
    return ThreadSafeBenchmarkLLMClient(cache_dir=CACHE_DIR)


__all__ = ["BaseLLMClient", "ThreadSafeBenchmarkLLMClient", "BenchmarkLLMClient", "CallResult", "cosine_sim", "get_llm_client"]
