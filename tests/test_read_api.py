from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lce.contracts.baseline import Baseline, compute_content_hash
from lce.read_api import AcceptedUnderstandingReadAPI
from lce.reference_memory.contracts import (
    AuthorizedSelectedSupport,
    RawEvidence,
    SemanticBlock,
)
from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.runtime import LceRuntime
from lce.semantic.providers import RuleBasedSemanticProvider
from lce.store.sqlite_store import SqliteBaselineStore
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


def test_read_api_matches_short_cjk_query_inside_continuous_sentence(
    tmp_path: Path,
) -> None:
    when = datetime(2026, 9, 1, tzinfo=UTC)
    memory = ReferenceMemoryStore(tmp_path / "cjk-memory")
    memory.add_evidence(
        RawEvidence(
            evidence_id="E-cjk",
            content="用户喜欢喝咖啡",
            occurred_at=when,
            known_at=when,
            provenance={"source": "test", "canonical": True},
        )
    )
    block = memory.put_semantic_block(
        SemanticBlock(
            block_id="SB-cjk",
            content="用户喜欢喝咖啡",
            raw_evidence_ids=("E-cjk",),
            occurred_start=when,
            occurred_end=when,
            compiler_version="test",
            lineage_id="main",
            derived_known_at=when,
        )
    )
    assert block.state_id is not None

    baselines = SqliteBaselineStore(tmp_path / "cjk-baselines")
    support = AuthorizedSelectedSupport(
        block_id=block.block_id,
        state_id=block.state_id,
    )
    baselines.save_revision(
        Baseline(
            baseline_id="base-cjk",
            region_id="region-cjk",
            revision_number=1,
            content="用户喜欢喝咖啡",
            content_hash=compute_content_hash("用户喜欢喝咖啡"),
            supporting_memory_ids=(block.block_id,),
            supporting_state_ids=(block.state_id,),
            selected_support=(support,),
            created_at=when,
        )
    )

    reader = AcceptedUnderstandingReadAPI(
        memory=memory,
        baseline_store=baselines,
    )

    short = reader.query("咖啡")
    punctuated = reader.query("想问：咖啡？")
    mixed = reader.query("coffee 咖啡")

    assert tuple(view.baseline_id for view in short) == ("base-cjk",)
    assert tuple(view.baseline_id for view in punctuated) == ("base-cjk",)
    assert tuple(view.baseline_id for view in mixed) == ("base-cjk",)
    memory.close()
    baselines.close()


def test_read_api_skips_baseline_with_missing_evidence_instead_of_crashing(
    tmp_path: Path,
) -> None:
    when = datetime(2026, 9, 1, tzinfo=UTC)
    block = SemanticBlock(
        block_id="SB-missing-evidence",
        content="stable understanding",
        raw_evidence_ids=("missing-evidence",),
        occurred_start=when,
        occurred_end=when,
        compiler_version="test",
        lineage_id="main",
        state_id="state-missing-evidence",
        derived_known_at=when,
    )

    class MissingEvidenceMemory:
        def get_semantic_block_state(self, state_id: str) -> SemanticBlock:
            if state_id != block.state_id:
                raise KeyError(state_id)
            return block

        def get_semantic_block(self, block_id: str) -> SemanticBlock:
            if block_id != block.block_id:
                raise KeyError(block_id)
            return block

        def get_evidence(self, evidence_id: str) -> RawEvidence:
            raise KeyError(evidence_id)

    baselines = SqliteBaselineStore(tmp_path / "missing-evidence-baselines")
    support = AuthorizedSelectedSupport(
        block_id=block.block_id,
        state_id=block.state_id or "",
    )
    baselines.save_revision(
        Baseline(
            baseline_id="base-missing-evidence",
            region_id="region-missing-evidence",
            revision_number=1,
            content="stable understanding",
            content_hash=compute_content_hash("stable understanding"),
            supporting_memory_ids=(block.block_id,),
            supporting_state_ids=(block.state_id or "",),
            selected_support=(support,),
            created_at=when,
        )
    )
    reader = AcceptedUnderstandingReadAPI(
        memory=MissingEvidenceMemory(),  # type: ignore[arg-type]
        baseline_store=baselines,
    )

    assert reader.query("stable") == ()
    baselines.close()
