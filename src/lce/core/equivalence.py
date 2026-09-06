"""Deterministic equivalence evaluator for LCE baseline contents."""

from __future__ import annotations

from lce.contracts.baseline import normalize_content


def is_content_equivalent(candidate_content: str, previous_content: str) -> bool:
    """Determine whether candidate understanding is semantically identical to previous.

    Rule:
      normalize(candidate.content) == normalize(previous.content)
      -> True (redundant, no new revision needed)
      -> False (meaningful change, new revision required)
    """
    return normalize_content(candidate_content) == normalize_content(previous_content)
