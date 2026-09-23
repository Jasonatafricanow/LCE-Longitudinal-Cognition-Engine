"""Deterministic JSON serialization and hashing for Oracle Typed Graph."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from research.oracle_graph.models import OracleTypedGraph


def canonical_graph_json(graph: OracleTypedGraph) -> str:
    """Serialize an OracleTypedGraph to a canonical, deterministically sorted JSON string."""
    raw_dict = graph.model_dump()
    return json.dumps(raw_dict, indent=2, sort_keys=True)


def compute_graph_digest(graph: OracleTypedGraph) -> str:
    """Compute reproducible SHA-256 digest over the canonical graph JSON bytes."""
    canon_bytes = canonical_graph_json(graph).encode("utf-8")
    return hashlib.sha256(canon_bytes).hexdigest()
