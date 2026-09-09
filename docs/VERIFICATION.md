# Public Verification

This document defines the **current public reproducibility gate** for LCE. It is intentionally separate from the historical V1 release record.

## Canonical command

Use Python 3.12 and run:

```bash
python -m pip install -e . -r requirements-verification.txt
python scripts/verify.py
```

`scripts/verify.py` prints the Python and tool versions it is using and then runs exactly these checks:

```text
python -m pytest -q
python -m mypy src/lce
python -m ruff check src tests
```

The same script is invoked by `.github/workflows/verification.yml`.

## Pinned toolchain

`requirements-verification.txt` is the public verification toolchain, currently pinned to exact versions:

```text
pytest 9.1.1
mypy 2.3.1
Ruff 0.16.6
```

A reviewer should not substitute a different mypy/Ruff/pytest version and then describe the result as the same gate without recording that difference.

This matters because the repository's `pyproject.toml` configures bare `mypy` over both `src` and `tests`, while the historical V1 release record explicitly reported the narrower release gate as:

```text
mypy (src/lce): clean
Ruff (src tests): clean
```

Therefore these are different claims:

```text
mypy
!=
mypy src/lce
```

A result from one surface must not be presented as a reproduction of the other.

## First public RED→GREEN record

The public verification workflow was used to establish the semantic-replication harness contract with an explicit RED→GREEN sequence.

### RED

Commit:

```text
9e00c67aa6b037183262f71c685b9d55ea79edf4
```

The new test `tests/research/test_semantic_replication_harness.py` was committed before the harness implementation existed.

GitHub Actions installed the pinned toolchain successfully, then failed during pytest collection with:

```text
ModuleNotFoundError: No module named 'research.replication'
```

The run collected the existing 139 tests plus the new contract test surface and stopped with one collection error. This was the expected RED state: the public contract existed before the implementation.

### GREEN

Commit:

```text
106f2b45d4cf7b016e5ccbddd7ac5bb93ec5e5ed
```

GitHub Actions ran the same canonical gate on Ubuntu 24.04 / Python 3.12.14 with the pinned toolchain and reported:

```text
142 passed in 10.01s
mypy src/lce -> Success: no issues found in 32 source files
ruff check src tests -> All checks passed!
PUBLIC VERIFICATION GATE: PASS
```

This record demonstrates two things narrowly:

1. the new replication-harness contract had a real failing state before implementation;
2. `mypy src/lce` is clean under mypy 2.3.1 on the recorded public CI environment.

It does **not** show that bare `mypy` over `src + tests` is clean, and it does not establish semantic-model quality.

## Historical release gate vs current public gate

`LCE_V1_RELEASE_RECORD.md` records the mechanical checks performed at the frozen implementation release HEAD. Those are historical release evidence.

The public verification workflow introduced later has a different purpose:

- make the command explicit;
- pin the tool versions;
- let a third party and GitHub Actions execute the same entry point;
- expose disagreements instead of relying on a prose statement that tools were clean.

A green current workflow does not retroactively prove every historical research claim. A historical release record does not replace a fresh public workflow result.

## Failure policy

If any command fails, the public verification gate is **not green**. The failure should be preserved with:

- commit SHA;
- Python version;
- pytest/mypy/Ruff versions;
- failing command;
- raw error output or linked CI log.

Do not downgrade or omit a failing check merely to recover a green badge. If a verification surface is intentionally changed, change the documented contract first and explain why.

## Scope

The canonical gate verifies software/runtime correctness surfaces currently encoded by the repository. It does not establish:

- semantic quality of an embedding model;
- general scientific validity of longitudinal cognition claims;
- cross-corpus generalization;
- production deployment reliability;
- independence of the test oracle.

Those require separate public replication and external adversarial audit evidence. See `docs/PUBLIC_EVIDENCE_MATRIX.md` and `docs/audit/`.
