"""Shared pytest fixtures for LCE test suite."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from lce.core.engine import LceCore
from lce.store.sqlite_store import SqliteBaselineStore
from lce.testing.fake_consolidator import ScriptableFakeConsolidator
from lce.testing.fake_substrate import FakeMemorySubstrate


@pytest.fixture
def fake_substrate() -> FakeMemorySubstrate:
    return FakeMemorySubstrate()


@pytest.fixture
def fake_consolidator() -> ScriptableFakeConsolidator:
    return ScriptableFakeConsolidator()


@pytest.fixture
def sqlite_store(tmp_path: Path) -> Iterator[SqliteBaselineStore]:
    store = SqliteBaselineStore(tmp_path)
    yield store
    store.close()


@pytest.fixture
def lce_core(
    fake_substrate: FakeMemorySubstrate,
    sqlite_store: SqliteBaselineStore,
    fake_consolidator: ScriptableFakeConsolidator,
) -> LceCore:
    return LceCore(
        memory_substrate=fake_substrate,
        baseline_store=sqlite_store,
        consolidator=fake_consolidator,
    )
