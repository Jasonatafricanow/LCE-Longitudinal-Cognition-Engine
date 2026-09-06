"""LCE testing package re-exports."""

from lce.testing.fake_consolidator import ScriptableFakeConsolidator
from lce.testing.fake_substrate import FakeMemorySubstrate

__all__ = [
    "FakeMemorySubstrate",
    "ScriptableFakeConsolidator",
]
