from __future__ import annotations

import importlib.metadata
import subprocess
import sys
from collections.abc import Sequence


TOOLS = ("pytest", "mypy", "ruff")
COMMANDS: tuple[tuple[str, ...], ...] = (
    (sys.executable, "-m", "pytest", "-q"),
    (sys.executable, "-m", "mypy", "src/lce"),
    (sys.executable, "-m", "ruff", "check", "src", "tests"),
)


def _version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "NOT INSTALLED"


def _display(command: Sequence[str]) -> str:
    return " ".join(command)


def main() -> int:
    print(f"Python: {sys.version.split()[0]}")
    for tool in TOOLS:
        print(f"{tool}: {_version(tool)}")

    for command in COMMANDS:
        print(f"\n$ {_display(command)}", flush=True)
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            print(f"\nFAILED ({result.returncode}): {_display(command)}", file=sys.stderr)
            return result.returncode

    print("\nPUBLIC VERIFICATION GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
