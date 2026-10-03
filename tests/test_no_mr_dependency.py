from __future__ import annotations

import ast
import tomllib
from pathlib import Path


def test_only_optional_integration_imports_mr_mem() -> None:
    source_root = Path(__file__).parents[1] / "src" / "lce"
    forbidden = ("mind runtime", "mind_runtime")
    offenders = []
    for path in source_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8").casefold()
        if any(token in text for token in forbidden):
            offenders.append(str(path))
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.ImportFrom):
                modules = (node.module or "",)
            elif isinstance(node, ast.Import):
                modules = tuple(alias.name for alias in node.names)
            else:
                continue
            for module in modules:
                if module.split(".")[0].startswith("mr") and (
                    path.parent != source_root / "integrations" or not module.startswith("mr_mem")
                ):
                    offenders.append(str(path))
    assert offenders == []
    project = tomllib.loads((source_root.parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert not any(dep.startswith("mr") for dep in project["project"]["dependencies"])
