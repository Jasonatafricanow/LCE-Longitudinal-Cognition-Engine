"""Typed Schema and Contracts for One-Pass Body Turn Result (BodyTurnResultV1).

Ensures one-pass inference produces both:
  1. normal assistant conversational response
  2. semantic parsing sidecar (SemanticParseResultV1)

Guarantees fail-closed property:
  If the semantic sidecar fails validation or is malformed,
  the assistant response is preserved and returned cleanly.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal
from pydantic import BaseModel, Field

from research.experiments.semantic_compilation_body_v1.schema import SemanticParseResultV1
from research.experiments.semantic_compilation_body_v1.validator import validate_parse_result

_logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when an unrecoverable validation error occurs."""


class BodyTurnResultV1(BaseModel):
    """PUBLIC envelope returned by Body Host in one-pass inference."""

    assistant_response: str = Field(
        ...,
        min_length=1,
        description="Conversational response delivered to the user. Must be non-empty."
    )
    semantic_sidecar: SemanticParseResultV1 | None = Field(
        default=None,
        description="Structured semantic parse of the user's turn. None if failed validation."
    )
    sidecar_valid: bool = Field(
        default=False,
        description="True if semantic_sidecar successfully passed deterministic schema validation."
    )
    sidecar_error: str | None = Field(
        default=None,
        description="Detailed reason if semantic_sidecar failed validation or was degraded."
    )
    sidecar_diagnostics: list[str] = Field(
        default_factory=list,
        description="Sanitization or warning notes emitted by the validator."
    )
    status: Literal["ok", "degraded", "failed"] = Field(
        default="ok",
        description="'ok' if both response and sidecar valid; 'degraded' if response valid but sidecar invalid."
    )
    raw_sidecar: dict[str, Any] | None = Field(
        default=None,
        description="Raw sidecar dict as received before validation (for audit & diagnostics)."
    )
    latency_ms: float = Field(default=0.0, description="Round-trip inference latency in milliseconds.")
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)

    @property
    def has_valid_sidecar(self) -> bool:
        return self.sidecar_valid and self.semantic_sidecar is not None


def parse_and_validate_body_turn(raw_payload: str | dict[str, Any]) -> BodyTurnResultV1:
    """Parse raw model output and strictly validate with fail-closed semantics.

    Rules:
      1. assistant_response MUST be a valid non-empty string. If missing/empty, raises ValidationError.
      2. semantic_sidecar is parsed via `validate_parse_result`.
      3. If sidecar validation fails:
         - assistant_response is KEPT intact.
         - semantic_sidecar is set to None.
         - sidecar_valid = False, status = 'degraded', sidecar_error records the reason.
         - No exception is raised.
    """
    if isinstance(raw_payload, str):
        cleaned = raw_payload.strip()
        # Handle markdown fences if model wrapped the JSON
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            # Fail-closed rescue: attempt to recover assistant_response if JSON truncated during sidecar
            import re
            m = re.search(r'"assistant_response"\s*:\s*"((?:[^"\\]|\\.)*)"', cleaned)
            if m:
                rescued_resp = bytes(m.group(1), "utf-8").decode("unicode_escape", errors="replace")
                return BodyTurnResultV1(
                    assistant_response=rescued_resp.strip(),
                    semantic_sidecar=None,
                    sidecar_valid=False,
                    sidecar_error=f"Body JSON malformed/truncated: {exc}",
                    status="degraded",
                    raw_sidecar=None,
                )
            raise ValidationError(f"Body output is not valid JSON: {exc}") from exc
    elif isinstance(raw_payload, dict):
        data = raw_payload
    else:
        raise ValidationError(f"Expected str or dict, got {type(raw_payload).__name__}")

    # 1. Extract and validate assistant_response
    assistant_resp = data.get("assistant_response")
    if assistant_resp is None:
        # Fallback check: did model use alternative key?
        assistant_resp = data.get("response") or data.get("reply") or data.get("content")
    
    if not isinstance(assistant_resp, str) or not assistant_resp.strip():
        raise ValidationError("assistant_response is missing or empty in Body output")

    assistant_resp = assistant_resp.strip()

    # 2. Extract and validate semantic_sidecar
    raw_sidecar = data.get("semantic_sidecar")
    if raw_sidecar is None:
        return BodyTurnResultV1(
            assistant_response=assistant_resp,
            semantic_sidecar=None,
            sidecar_valid=False,
            sidecar_error="semantic_sidecar key missing from Body payload",
            status="degraded",
            raw_sidecar=None,
        )

    # Fail-closed validation
    try:
        validated_sidecar, diagnostics = validate_parse_result(raw_sidecar)
        return BodyTurnResultV1(
            assistant_response=assistant_resp,
            semantic_sidecar=validated_sidecar,
            sidecar_valid=True,
            sidecar_error=None,
            sidecar_diagnostics=diagnostics,
            status="ok",
            raw_sidecar=raw_sidecar if isinstance(raw_sidecar, dict) else None,
        )
    except Exception as exc:
        _logger.warning("Fail-closed: semantic_sidecar failed validation: %s", exc)
        return BodyTurnResultV1(
            assistant_response=assistant_resp,
            semantic_sidecar=None,
            sidecar_valid=False,
            sidecar_error=str(exc),
            sidecar_diagnostics=[],
            status="degraded",
            raw_sidecar=raw_sidecar if isinstance(raw_sidecar, dict) else None,
        )
