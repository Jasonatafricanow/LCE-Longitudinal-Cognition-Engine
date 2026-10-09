"""Unit tests for BodyTurnResultV1 contract and fail-closed validation."""

import pytest
from research.experiments.semantic_compilation_body_v1.one_pass.body_turn_contract import (
    parse_and_validate_body_turn,
    BodyTurnResultV1,
    ValidationError,
)


def test_happy_path():
    payload = {
        "assistant_response": "收到，我会在周三前提交报告。",
        "semantic_sidecar": {
            "schema_version": "semantic_parse_v1",
            "source_window_refs": ["E01"],
            "semantic_points": [
                {
                    "local_id": "P01",
                    "source_refs": ["E01"],
                    "meaning": "用户要求在周三前提交报告",
                    "status": "resolved",
                    "speech_act": "directive",
                    "polarity": "positive",
                    "epistemic_status": "asserted",
                    "temporal": "future",
                }
            ],
            "dependencies": [],
            "unresolved": [],
        },
    }
    result = parse_and_validate_body_turn(payload)
    assert result.status == "ok"
    assert result.has_valid_sidecar is True
    assert result.assistant_response == "收到，我会在周三前提交报告。"
    assert len(result.semantic_sidecar.semantic_points) == 1
    assert result.semantic_sidecar.semantic_points[0].local_id == "P01"


def test_fail_closed_on_corrupted_sidecar():
    """If sidecar is broken, assistant_response must be preserved and not thrown away."""
    payload = {
        "assistant_response": "好的，我知道了。",
        "semantic_sidecar": {
            "schema_version": "semantic_parse_v1",
            # completely invalid type for semantic_points
            "semantic_points": "not_a_list",
        },
    }
    result = parse_and_validate_body_turn(payload)
    assert result.status == "degraded"
    assert result.has_valid_sidecar is False
    assert result.semantic_sidecar is None
    assert result.assistant_response == "好的，我知道了。"
    assert result.sidecar_error is not None


def test_missing_assistant_response():
    """If assistant_response is completely absent or empty, that is a hard failure."""
    payload = {
        "semantic_sidecar": {
            "schema_version": "semantic_parse_v1",
            "semantic_points": [],
            "dependencies": [],
            "unresolved": [],
        }
    }
    with pytest.raises(ValidationError):
        parse_and_validate_body_turn(payload)


def test_markdown_fence_unwrapping():
    json_str = """```json
{
  "assistant_response": "没问题。",
  "semantic_sidecar": {
    "schema_version": "semantic_parse_v1",
    "source_window_refs": ["E01"],
    "semantic_points": [
      {
        "local_id": "P01",
        "source_refs": ["E01"],
        "meaning": "用户表示确认",
        "status": "resolved"
      }
    ],
    "dependencies": [],
    "unresolved": []
  }
}
```"""
    result = parse_and_validate_body_turn(json_str)
    assert result.status == "ok"
    assert result.assistant_response == "没问题。"
    assert result.has_valid_sidecar is True
