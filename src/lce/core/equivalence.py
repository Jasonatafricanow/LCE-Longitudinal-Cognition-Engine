"""Deterministic equivalence evaluator for LCE baseline contents."""

from __future__ import annotations

from lce.contracts.baseline import normalize_content
from lce.reference_memory.contracts import AuthorizedSelectedSupport


def is_content_equivalent(candidate_content: str, previous_content: str) -> bool:
    """Determine whether candidate understanding is semantically identical to previous.

    Rule:
      normalize(candidate.content) == normalize(previous.content)
      -> True (redundant, no new revision needed)
      -> False (meaningful change, new revision required)
    """
    return normalize_content(candidate_content) == normalize_content(previous_content)


def support_snapshot_identity(
    *,
    supporting_memory_ids: tuple[str, ...],
    supporting_state_ids: tuple[str, ...] = (),
    selected_support: tuple[AuthorizedSelectedSupport, ...] = (),
) -> tuple[
    frozenset[str],
    bool,
    frozenset[str],
    frozenset[tuple[str, str]],
]:
    """Return order-insensitive support authority while preserving state identity.

    Tuple order is a storage/alignment representation detail. Durable support
    identity is the set of supporting IDs plus immutable selected block/state
    pairs when present.
    """
    return (
        frozenset(supporting_memory_ids),
        bool(selected_support),
        frozenset(supporting_state_ids),
        frozenset(
            (item.block_id, item.state_id)
            for item in selected_support
        ),
    )


def is_support_equivalent(
    *,
    left_memory_ids: tuple[str, ...],
    right_memory_ids: tuple[str, ...],
    left_state_ids: tuple[str, ...] = (),
    right_state_ids: tuple[str, ...] = (),
    left_selected_support: tuple[AuthorizedSelectedSupport, ...] = (),
    right_selected_support: tuple[AuthorizedSelectedSupport, ...] = (),
) -> bool:
    """Compare support authority without treating tuple permutation as change."""
    return support_snapshot_identity(
        supporting_memory_ids=left_memory_ids,
        supporting_state_ids=left_state_ids,
        selected_support=left_selected_support,
    ) == support_snapshot_identity(
        supporting_memory_ids=right_memory_ids,
        supporting_state_ids=right_state_ids,
        selected_support=right_selected_support,
    )
