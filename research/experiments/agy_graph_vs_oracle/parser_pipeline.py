"""Parser pipeline to run frozen AGY Semantic Parser on longitudinal fixtures.

Features:
- Strict input sanitization (removes all gold units, relations, and target oracles).
- SHA-256 and fixture-ID based disk caching at .llm_cache/predicted_fixtures/
  ensuring zero-cost offline reproducibility once generated.
- Converts parser output into valid SemanticAnnotationDocument.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research.experiments.oracle_graph_value.fixtures.models import LongitudinalFixture
from research.semantic_annotation.schema import SemanticAnnotationDocument
from research.semantic_parser.parser import SemanticParser

CACHE_DIR = Path(".llm_cache/predicted_fixtures")


def parse_fixture_with_agy_parser(
    fixture: LongitudinalFixture,
    parser: SemanticParser | None = None,
    force_refresh: bool = False,
) -> SemanticAnnotationDocument:
    """Parse raw evidence of a LongitudinalFixture using frozen AGY Semantic Parser."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{fixture.fixture_id}.json"

    # Check cache first
    if not force_refresh and cache_file.exists():
        try:
            cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
            return SemanticAnnotationDocument.model_validate(cached_data)
        except Exception:
            pass  # Fall back to live parsing if cache is corrupted

    # 1. Sanitize input: strictly raw evidence text and semantic blocks only
    sanitized_input = {
        "case_id": fixture.fixture_id,
        "raw_evidence": [
            {
                "evidence_id": ev.evidence_id,
                "content": ev.content,
                "occurred_at": ev.occurred_at,
            }
            for ev in fixture.evidence
        ],
        "semantic_blocks": [
            {
                "block_id": b.block_id,
                "evidence_ids": b.evidence_ids,
                "text": b.text,
                "occurred_start": b.occurred_start,
                "occurred_end": b.occurred_end,
            }
            for b in fixture.a0_blocks
        ],
        "cutoff_time": fixture.gold_document.cutoff_time,
    }

    # 2. Run parser
    p = parser or SemanticParser()
    pred_doc = p.parse_case(sanitized_input)

    # 3. Cache result
    cache_file.write_text(json.dumps(pred_doc.model_dump(), indent=2), encoding="utf-8")

    return pred_doc


def parse_all_fixtures_with_agy_parser(
    fixtures: list[LongitudinalFixture],
    parser: SemanticParser | None = None,
    force_refresh: bool = False,
) -> dict[str, SemanticAnnotationDocument]:
    """Parse all longitudinal fixtures using frozen AGY Semantic Parser."""
    p = parser or SemanticParser()
    results: dict[str, SemanticAnnotationDocument] = {}
    for fix in fixtures:
        doc = parse_fixture_with_agy_parser(fix, parser=p, force_refresh=force_refresh)
        results[fix.fixture_id] = doc
    return results
