from __future__ import annotations

from pathlib import Path

from lce.runtime import LceRuntime
from tests.fixtures.longitudinal_corpus import longitudinal_corpus


def test_standalone_batch_restart_nearline_merge_head_and_query(tmp_path: Path) -> None:
    corpus = longitudinal_corpus()
    runtime = LceRuntime(tmp_path / "run", lineage_id="main")
    batch_results = runtime.run_batch(corpus[:4])
    assert len(batch_results) == 4
    assert all(result.snapshot.visible_block_ids for result in batch_results)
    assert any(result.higher_order_candidates for result in batch_results)
    runtime.close()

    restarted = LceRuntime(tmp_path / "run", lineage_id="main")
    replay = restarted.process(corpus[3])
    assert replay.compiler_result.replayed is True
    continuation = restarted.process(corpus[4])
    assert continuation.snapshot.cutoff == corpus[4].occurred_at
    merged = restarted.worktrees.list(status="MERGED")
    assert merged
    views = restarted.query("alpha")
    assert views
    assert all(view.supporting_semantic_block_ids for view in views)
    assert all(view.supporting_source_refs for view in views)
    restarted.close()


def test_correction_path_localizes_invalidation_and_replaces_served_head(tmp_path: Path) -> None:
    runtime = LceRuntime(tmp_path / "run", lineage_id="main")
    corpus = longitudinal_corpus()
    runtime.run_batch(corpus[:4])
    runtime.process(corpus[4])
    before = runtime.query(None)
    assert before
    invalidated = runtime.invalidate_and_rebuild("E2")
    assert "E2" in invalidated.invalidated_evidence_id
    after = runtime.query(None)
    assert after
    assert all("E2" not in view.supporting_source_refs for view in after)
    assert any("corrected" in view.content for view in after)
    runtime.close()
