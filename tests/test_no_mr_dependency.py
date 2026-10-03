from __future__ import annotations

import ast
import os
import subprocess
import sys
import textwrap
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


def test_standalone_runs_with_mr_imports_actively_blocked(tmp_path: Path) -> None:
    script = textwrap.dedent('''
        import importlib.abc
        import sys
        from datetime import UTC, datetime
        class BlockMr(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.startswith(("mr_mem", "mind_runtime")):
                    raise ImportError("standalone imported MR")
        sys.meta_path.insert(0, BlockMr())
        from lce.runtime import LceRuntime
        from lce.reference_memory.contracts import RawEvidence
        runtime = LceRuntime(sys.argv[1])
        result = runtime.process_raw_evidence(RawEvidence(
            "standalone-source", "real standalone evidence", datetime(2026, 1, 1, tzinfo=UTC),
            {"source": "standalone-test", "canonical": True},
        ))
        assert result.compiler_result.block_ids
        assert not any(name.startswith("mr_mem") for name in sys.modules)
        runtime.close()
    ''')
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path)], env=env,
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
