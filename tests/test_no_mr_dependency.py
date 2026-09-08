from __future__ import annotations

from pathlib import Path


def test_lce_source_has_no_mr_import_or_runtime_dependency() -> None:
    source_root = Path(__file__).parents[1] / "src" / "lce"
    forbidden = ("import mr", "from mr", "mind runtime", "mind_runtime")
    offenders = []
    for path in source_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8").casefold()
        if any(token in text for token in forbidden):
            offenders.append(str(path))
    assert offenders == []
