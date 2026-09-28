"""Narrow public contract for proactive inspiration consumption."""

from __future__ import annotations

from dataclasses import dataclass


def _require_nonempty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty")
    return value.strip()


@dataclass(frozen=True, slots=True)
class InspirationMaterial:
    """Opaque, self-contained material for a downstream proactive consumer.

    Downstream systems intentionally receive only an opaque identifier plus
    content. LCE-internal Line, branch, support, confidence, candidate type and
    provenance structures stay behind the cognition boundary.
    """

    material_id: str
    content: str

    def __post_init__(self) -> None:
        _require_nonempty(self.material_id, "material_id")
        _require_nonempty(self.content, "content")
