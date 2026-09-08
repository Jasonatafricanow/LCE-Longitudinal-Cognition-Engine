from __future__ import annotations

from pathlib import Path

from lce.runtime import LceRuntime
from lce.semantic.providers import RuleBasedSemanticProvider
from tests.fixtures.longitudinal_corpus import longitudinal_corpus


class CountingProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.delegate = RuleBasedSemanticProvider()

    def decide(self, *, evidence, open_block, recent_blocks):
        self.calls += 1
        return self.delegate.decide(evidence=evidence, open_block=open_block, recent_blocks=recent_blocks)


def test_read_path_returns_only_accepted_current_valid_understanding_without_reasoning(tmp_path: Path) -> None:
    provider = CountingProvider()
    runtime = LceRuntime(tmp_path / "run", provider=provider, lineage_id="main")
    runtime.run_batch(longitudinal_corpus()[:4])
    calls_before = provider.calls
    views_before = runtime.query("alpha")
    views_after = runtime.query("alpha")
    assert provider.calls == calls_before
    assert views_after == views_before
    assert all(view.status == "ACCEPTED" for view in views_after)
    assert all(view.worktree_status is None for view in views_after)
    runtime.close()
