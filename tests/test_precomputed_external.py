from __future__ import annotations

import sqlite3

import pytest

from lce.cognition.external import PrecomputedDraftInput, PrecomputedDraftIntake
from lce.cognition.worktree import DraftRevisionStore
from lce.store.sqlite_store import SqliteBaselineStore
from lce.testing.fake_substrate import FakeMemorySubstrate


def setup_intake(tmp_path):
    memory = FakeMemorySubstrate()
    memory.add_memory("m1", "wanted replacement", ("e1",))
    memory.add_memory("m2", "price delayed purchase", ("e2",))
    baselines = SqliteBaselineStore(tmp_path / "baselines")
    drafts = DraftRevisionStore(tmp_path / "drafts")
    intake = PrecomputedDraftIntake(
        memory_substrate=memory,
        baseline_store=baselines,
        draft_store=drafts,
    )
    return memory, baselines, drafts, intake


def draft(*, content="Price delayed the replacement.", input_id="thread:t1:v1"):
    return PrecomputedDraftInput(
        region_id="mr-thread:t1",
        content=content,
        supporting_memory_ids=("m1", "m2"),
        processing_input_id=input_id,
        context={"source": "mr-thread"},
    )


def test_precomputed_external_input_is_staged_before_baseline_promotion(tmp_path):
    _, baselines, drafts, intake = setup_intake(tmp_path)

    result = intake.stage_and_promote(draft())

    assert result.revised
    assert result.baseline.content == "Price delayed the replacement."
    assert result.baseline.supporting_memory_ids == ("m1", "m2")

    items = drafts.list()
    assert len(items) == 1
    assert items[0].support_kind == "external_memory"
    assert items[0].supporting_block_ids == ("m1", "m2")
    assert items[0].status == "MERGED"
    assert items[0].merged_baseline_id == result.baseline.baseline_id

    drafts.close()
    baselines.close()


def test_precomputed_external_replay_reuses_merged_draft_and_baseline(tmp_path):
    _, baselines, drafts, intake = setup_intake(tmp_path)

    first = intake.stage_and_promote(draft())
    replay = intake.stage_and_promote(draft())

    assert not replay.revised
    assert replay.reason == "PRECOMPUTED_DRAFT_RECONCILED"
    assert replay.baseline.baseline_id == first.baseline.baseline_id
    assert len(drafts.list()) == 1
    assert len(baselines.get_history("mr-thread:t1").revisions) == 1

    drafts.close()
    baselines.close()


def test_precomputed_external_rejects_conflicting_replay_identity(tmp_path):
    _, baselines, drafts, intake = setup_intake(tmp_path)
    intake.stage_and_promote(draft())

    with pytest.raises(ValueError, match="conflicting draft"):
        intake.stage_and_promote(draft(content="Different interpretation."))

    drafts.close()
    baselines.close()


def test_precomputed_external_rejects_missing_support_before_persisting_draft(tmp_path):
    _, baselines, drafts, intake = setup_intake(tmp_path)
    invalid = PrecomputedDraftInput(
        region_id="mr-thread:t1",
        content="candidate",
        supporting_memory_ids=("m1", "missing"),
        processing_input_id="thread:t1:bad",
    )

    with pytest.raises(ValueError, match="incomplete or unauthorized"):
        intake.stage_and_promote(invalid)

    assert drafts.list() == ()
    assert baselines.get_current_baseline("mr-thread:t1") is None if hasattr(
        baselines, "get_current_baseline"
    ) else baselines.get_head("mr-thread:t1") is None

    drafts.close()
    baselines.close()


def test_precomputed_external_recovers_commit_before_draft_status(tmp_path):
    memory, baselines, drafts, intake = setup_intake(tmp_path)
    value = draft()
    item = drafts.create(
        region_id=value.region_id,
        candidate_content=value.content,
        supporting_block_ids=value.supporting_memory_ids,
        supporting_structure_ids=(),
        base_baseline=None,
        processing_input_id=value.processing_input_id,
        support_kind="external_memory",
    )

    # Simulate a crash after LCE Core committed the Baseline but before the
    # external draft status was marked MERGED.
    from lce.contracts.consolidation import CandidateBaseline
    from lce.core.engine import LceCore

    class Consolidator:
        def consolidate(self, *, memories, previous_baseline, context=None):
            return CandidateBaseline(
                content=value.content,
                supporting_memory_ids=value.supporting_memory_ids,
            )

    LceCore(
        memory_substrate=memory,
        baseline_store=baselines,
        consolidator=Consolidator(),
    ).consolidate(value.region_id, value.supporting_memory_ids)
    assert drafts.get(item.worktree_id).status == "OPEN"

    recovered = intake.stage_and_promote(value)
    assert not recovered.revised
    assert recovered.reason == "PRECOMPUTED_DRAFT_RECONCILED"
    assert drafts.get(item.worktree_id).status == "MERGED"

    drafts.close()
    baselines.close()


def test_support_kind_schema_migrates_existing_worktree_database(tmp_path):
    root = tmp_path / "drafts"
    root.mkdir()
    db = root / "cognition_worktrees.sqlite"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE worktrees (
                worktree_id TEXT PRIMARY KEY,
                region_id TEXT NOT NULL,
                base_baseline_id TEXT,
                base_revision INTEGER,
                candidate_content TEXT NOT NULL,
                supporting_block_ids_json TEXT NOT NULL,
                supporting_structure_ids_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL,
                needs_rebuild INTEGER NOT NULL DEFAULT 0,
                merged_baseline_id TEXT,
                applicability TEXT,
                unresolved TEXT,
                interpretation_trace_json TEXT NOT NULL DEFAULT '{}',
                selected_support_json TEXT NOT NULL DEFAULT '[]',
                processing_input_id TEXT
            );
            CREATE TABLE support_cycles (
                worktree_id TEXT NOT NULL,
                snapshot_id TEXT NOT NULL,
                PRIMARY KEY(worktree_id, snapshot_id)
            );
            CREATE TABLE support_observations (
                worktree_id TEXT NOT NULL,
                support_identity TEXT NOT NULL,
                PRIMARY KEY(worktree_id, support_identity)
            );
            """
        )

    store = DraftRevisionStore(root)
    columns = {
        str(row[1])
        for row in store.conn.execute("PRAGMA table_info(worktrees)").fetchall()
    }
    assert "support_kind" in columns
    store.close()
