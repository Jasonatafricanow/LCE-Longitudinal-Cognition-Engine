"""Comprehensive acceptance tests for LCE Core (T1 - T12).

Verifies the frozen contracts, boundaries, and behaviors specified in
LCE-V0-01 and LCE-V0-01R.
"""

import ast
import sqlite3
from pathlib import Path

import pytest

from lce.contracts.consolidation import (
    CandidateBaseline,
    UnauthorizedSourceError,
)
from lce.core.engine import LceCore
from lce.store.sqlite_store import SqliteBaselineStore
from lce.testing.fake_consolidator import ScriptableFakeConsolidator
from lce.testing.fake_substrate import FakeMemorySubstrate


# ---------------------------------------------------------------------------
# T1 — External-memory-only
# ---------------------------------------------------------------------------
def test_t1_external_memory_only(
    lce_core: LceCore,
    sqlite_store: SqliteBaselineStore,
    fake_substrate: FakeMemorySubstrate,
    fake_consolidator: ScriptableFakeConsolidator,
) -> None:
    """Prove LCE receives Memory through dependency contract and stores NO raw memory table or raw content."""
    sentinel = "RAW_MEMORY_SENTINEL_DO_NOT_PERSIST_93A7"
    fake_substrate.add_memory(
        "mem-sentinel-1",
        f"Sensitive raw memory content containing {sentinel}.",
        ("ev-1",),
    )
    fake_consolidator.queue_response(
        CandidateBaseline(
            content="User has notes.",
            supporting_memory_ids=("mem-sentinel-1",),
        )
    )
    lce_core.consolidate("region-sentinel", ("mem-sentinel-1",))

    # Verify tables: strictly LCE internal tables and NO raw memory tables
    conn = sqlite3.connect(sqlite_store.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name ASC")
    tables = [row[0] for row in cursor.fetchall()]

    assert set(tables) == {"baseline_revisions", "baselines_head", "baseline_memory_refs"}
    for forbidden in ("memories", "memory_items", "evidence", "observations", "propositions"):
        assert forbidden not in tables

    # Verify sentinel text does not appear in any row of any table
    for tbl in tables:
        cursor.execute(f"SELECT * FROM {tbl}")
        for row in cursor.fetchall():
            for cell in row:
                if isinstance(cell, str):
                    assert sentinel not in cell, f"Raw memory sentinel leaked into table {tbl} cell: {cell}"

    conn.close()

    # Verify sentinel does not appear anywhere in the persisted SQLite binary file
    db_bytes = sqlite_store.db_path.read_bytes()
    assert sentinel.encode("utf-8") not in db_bytes, "Raw memory sentinel found in SQLite database bytes"


# ---------------------------------------------------------------------------
# T2 — Initial Baseline creation
# ---------------------------------------------------------------------------
def test_t2_initial_baseline_creation(
    lce_core: LceCore,
    fake_substrate: FakeMemorySubstrate,
    fake_consolidator: ScriptableFakeConsolidator,
) -> None:
    """A related set of memories produces one initial persisted Baseline (B1)."""
    fake_substrate.add_memory("m1", "User adopted an orange kitten.", ("ev-1",))
    fake_substrate.add_memory("m2", "User named the kitten Mikan.", ("ev-2",))

    fake_consolidator.queue_response(
        CandidateBaseline(
            content="User adopted an orange kitten named Mikan.",
            supporting_memory_ids=("m1", "m2"),
            model_trace={"provider": "glm", "model": "glm-4", "run_id": "run-001"},
        )
    )

    res = lce_core.consolidate(
        region_id="region-cats",
        memory_ids=("m1", "m2"),
    )

    assert res.revised is True
    assert res.reason == "INITIAL_CREATION"
    b1 = res.baseline
    assert b1.region_id == "region-cats"
    assert b1.revision_number == 1
    assert b1.previous_baseline_id is None
    assert b1.content == "User adopted an orange kitten named Mikan."
    assert b1.supporting_memory_ids == ("m1", "m2")


# ---------------------------------------------------------------------------
# T3 — Stable provenance
# ---------------------------------------------------------------------------
def test_t3_stable_provenance(
    lce_core: LceCore,
    fake_substrate: FakeMemorySubstrate,
    fake_consolidator: ScriptableFakeConsolidator,
) -> None:
    """Baseline support points to stable external Memory IDs, not vector coordinates."""
    fake_substrate.add_memory(
        "mem-uuid-101",
        "User enjoys black coffee in the morning.",
        ("ev-coffee-1",),
        retrieval_metadata={"similarity_rank": 1, "vector_pos": 42},
    )

    fake_consolidator.queue_response(
        CandidateBaseline(
            content="User prefers black coffee in the morning.",
            supporting_memory_ids=("mem-uuid-101",),
            model_trace={"model": "estimator-v1"},
        )
    )

    res = lce_core.consolidate("region-coffee", ("mem-uuid-101",))
    b = res.baseline

    # Provenance matches the stable ID
    assert b.supporting_memory_ids == ("mem-uuid-101",)
    # Memory content or coordinates are not the identifier
    assert "similarity_rank" not in b.supporting_memory_ids
    assert "vector_pos" not in b.supporting_memory_ids


# ---------------------------------------------------------------------------
# T4 — Unknown source rejection (Fail Closed)
# ---------------------------------------------------------------------------
def test_t4_unknown_source_rejection(
    lce_core: LceCore,
    fake_substrate: FakeMemorySubstrate,
    fake_consolidator: ScriptableFakeConsolidator,
) -> None:
    """Candidate consolidation referencing unauthorized memory ID fails closed."""
    fake_substrate.add_memory("m1", "Authorized memory.", ("ev-1",))
    fake_substrate.add_memory("m2", "Authorized memory 2.", ("ev-2",))

    # Candidate hallucinates/references m99 which is not in the supplied set
    fake_consolidator.queue_response(
        CandidateBaseline(
            content="Hallucinated understanding.",
            supporting_memory_ids=("m1", "unauthorized-m99"),
        )
    )

    with pytest.raises(UnauthorizedSourceError, match="unauthorized-m99"):
        lce_core.consolidate("reg-secure", ("m1", "m2"))

    # Assert HEAD was never written or updated
    assert lce_core.get_current_baseline("reg-secure") is None


# ---------------------------------------------------------------------------
# T5 — Duplicate stability
# ---------------------------------------------------------------------------
def test_t5_duplicate_stability(
    lce_core: LceCore,
    fake_substrate: FakeMemorySubstrate,
    fake_consolidator: ScriptableFakeConsolidator,
) -> None:
    """Redundant memory with unchanged learned understanding creates NO new revision."""
    fake_substrate.add_memory("m1", "User has one cat.", ("ev-1",))

    # Initial consolidation
    fake_consolidator.queue_response(
        CandidateBaseline(
            content="User has one cat.",
            supporting_memory_ids=("m1",),
        )
    )
    res1 = lce_core.consolidate("reg-cat", ("m1",))
    assert res1.revised is True
    b1_id = res1.baseline.baseline_id

    # User repeats information: new redundant memory added
    fake_substrate.add_memory("m2", "User says again they have a cat.", ("ev-2",))

    # Consolidator extracts identical understanding (with minor whitespace differences)
    fake_consolidator.queue_response(
        CandidateBaseline(
            content="  User  has   one cat. \n",
            supporting_memory_ids=("m1", "m2"),
        )
    )
    res2 = lce_core.consolidate("reg-cat", ("m1", "m2"))

    assert res2.revised is False
    assert res2.reason == "NO_SEMANTIC_CHANGE"
    assert res2.baseline.baseline_id == b1_id
    assert res2.baseline.revision_number == 1

    # HEAD in store remains B1
    current = lce_core.get_current_baseline("reg-cat")
    assert current is not None
    assert current.baseline_id == b1_id
    assert current.revision_number == 1


# ---------------------------------------------------------------------------
# T6 — Meaningful revision
# ---------------------------------------------------------------------------
def test_t6_meaningful_revision(
    lce_core: LceCore,
    fake_substrate: FakeMemorySubstrate,
    fake_consolidator: ScriptableFakeConsolidator,
) -> None:
    """Meaningful new information produces a new revision linked to previous."""
    fake_substrate.add_memory("m1", "User adopted a cat.", ("ev-1",))
    fake_consolidator.queue_response(
        CandidateBaseline(
            content="User has a cat.",
            supporting_memory_ids=("m1",),
        )
    )
    res1 = lce_core.consolidate("reg-cat", ("m1",))
    b1 = res1.baseline

    # New memory arrives: adopted a second cat
    fake_substrate.add_memory("m2", "User adopted a second stray cat.", ("ev-2",))
    fake_consolidator.queue_response(
        CandidateBaseline(
            content="User now has two cats.",
            supporting_memory_ids=("m1", "m2"),
        )
    )
    res2 = lce_core.consolidate("reg-cat", ("m1", "m2"))
    b2 = res2.baseline

    assert res2.revised is True
    assert res2.reason == "MEANINGFUL_UPDATE"
    assert b2.revision_number == 2
    assert b2.previous_baseline_id == b1.baseline_id
    assert b2.content == "User now has two cats."
    assert b2.supporting_memory_ids == ("m1", "m2")


# ---------------------------------------------------------------------------
# T7 — Current HEAD
# ---------------------------------------------------------------------------
def test_t7_current_head(
    lce_core: LceCore,
    fake_substrate: FakeMemorySubstrate,
    fake_consolidator: ScriptableFakeConsolidator,
) -> None:
    """get_current_baseline returns the latest revision."""
    fake_substrate.add_memory("m1", "Point 1", ("ev-1",))
    fake_substrate.add_memory("m2", "Point 2", ("ev-2",))

    fake_consolidator.queue_response(CandidateBaseline("Understanding 1", ("m1",)))
    lce_core.consolidate("reg-x", ("m1",))

    fake_consolidator.queue_response(CandidateBaseline("Understanding 2", ("m1", "m2")))
    lce_core.consolidate("reg-x", ("m1", "m2"))

    head = lce_core.get_current_baseline("reg-x")
    assert head is not None
    assert head.revision_number == 2
    assert head.content == "Understanding 2"


# ---------------------------------------------------------------------------
# T8 — Revision history audit
# ---------------------------------------------------------------------------
def test_t8_revision_history_audit(
    lce_core: LceCore,
    fake_substrate: FakeMemorySubstrate,
    fake_consolidator: ScriptableFakeConsolidator,
) -> None:
    """Audit API returns prior revisions and supporting Memory refs in order."""
    fake_substrate.add_memory("m1", "P1", ("ev-1",))
    fake_substrate.add_memory("m2", "P2", ("ev-2",))
    fake_substrate.add_memory("m3", "P3", ("ev-3",))

    fake_consolidator.queue_response(CandidateBaseline("V1", ("m1",)))
    lce_core.consolidate("reg-hist", ("m1",))

    fake_consolidator.queue_response(CandidateBaseline("V2", ("m1", "m2")))
    lce_core.consolidate("reg-hist", ("m1", "m2"))

    fake_consolidator.queue_response(CandidateBaseline("V3", ("m1", "m2", "m3")))
    lce_core.consolidate("reg-hist", ("m1", "m2", "m3"))

    history = lce_core.get_history("reg-hist")
    assert len(history.revisions) == 3
    # Ordered descending: V3 -> V2 -> V1
    revs = history.revisions
    assert revs[0].revision_number == 3
    assert revs[0].content == "V3"
    assert revs[0].supporting_memory_ids == ("m1", "m2", "m3")

    assert revs[1].revision_number == 2
    assert revs[1].content == "V2"
    assert revs[1].previous_baseline_id == revs[2].baseline_id

    assert revs[2].revision_number == 1
    assert revs[2].content == "V1"
    assert revs[2].previous_baseline_id is None


# ---------------------------------------------------------------------------
# T9 — Restart stability
# ---------------------------------------------------------------------------
def test_t9_restart_stability(
    tmp_path: Path,
    fake_substrate: FakeMemorySubstrate,
    fake_consolidator: ScriptableFakeConsolidator,
) -> None:
    """Recreating LCE against the same storage root restores the exact HEAD and full revision chain."""
    store1 = SqliteBaselineStore(tmp_path)
    core1 = LceCore(
        memory_substrate=fake_substrate,
        baseline_store=store1,
        consolidator=fake_consolidator,
    )

    fake_substrate.add_memory("m1", "Point 1", ("ev-1",))
    fake_substrate.add_memory("m2", "Point 2", ("ev-2",))
    fake_substrate.add_memory("m3", "Point 3", ("ev-3",))

    # B1 (rev 1)
    fake_consolidator.queue_response(CandidateBaseline("Understanding B1", ("m1",)))
    res1 = core1.consolidate("reg-restart", ("m1",))
    b1_id = res1.baseline.baseline_id

    # B2 (rev 2)
    fake_consolidator.queue_response(CandidateBaseline("Understanding B2", ("m1", "m2")))
    res2 = core1.consolidate("reg-restart", ("m1", "m2"))
    b2_id = res2.baseline.baseline_id

    # B3 (rev 3)
    fake_consolidator.queue_response(CandidateBaseline("Understanding B3", ("m1", "m2", "m3")))
    res3 = core1.consolidate("reg-restart", ("m1", "m2", "m3"))
    b3_id = res3.baseline.baseline_id

    assert res3.baseline.revision_number == 3
    store1.close()

    # Reconstruct LCE process against existing database
    store2 = SqliteBaselineStore(tmp_path)
    core2 = LceCore(
        memory_substrate=fake_substrate,
        baseline_store=store2,
        consolidator=fake_consolidator,
    )

    restored_head = core2.get_current_baseline("reg-restart")
    assert restored_head is not None
    assert restored_head.baseline_id == b3_id
    assert restored_head.revision_number == 3
    assert restored_head.previous_baseline_id == b2_id
    assert restored_head.content == "Understanding B3"
    assert restored_head.supporting_memory_ids == ("m1", "m2", "m3")

    history = core2.get_history("reg-restart")
    assert len(history.revisions) == 3
    revs = history.revisions
    assert revs[0].baseline_id == b3_id
    assert revs[0].revision_number == 3
    assert revs[0].previous_baseline_id == b2_id
    assert revs[0].supporting_memory_ids == ("m1", "m2", "m3")

    assert revs[1].baseline_id == b2_id
    assert revs[1].revision_number == 2
    assert revs[1].previous_baseline_id == b1_id
    assert revs[1].supporting_memory_ids == ("m1", "m2")

    assert revs[2].baseline_id == b1_id
    assert revs[2].revision_number == 1
    assert revs[2].previous_baseline_id is None
    assert revs[2].supporting_memory_ids == ("m1",)

    store2.close()


# ---------------------------------------------------------------------------
# T10 — Storage-root isolation
# ---------------------------------------------------------------------------
def test_t10_storage_root_isolation(
    tmp_path: Path,
    fake_substrate: FakeMemorySubstrate,
    fake_consolidator: ScriptableFakeConsolidator,
) -> None:
    """Two caller storage roots cannot read or mutate each other's Baselines."""
    dir_a = tmp_path / "storage_a"
    dir_b = tmp_path / "storage_b"

    store_a = SqliteBaselineStore(dir_a)
    store_b = SqliteBaselineStore(dir_b)

    core_a = LceCore(
        memory_substrate=fake_substrate,
        baseline_store=store_a,
        consolidator=fake_consolidator,
    )
    core_b = LceCore(
        memory_substrate=fake_substrate,
        baseline_store=store_b,
        consolidator=fake_consolidator,
    )

    fake_substrate.add_memory("m1", "Memory A", ("ev-a",))
    fake_consolidator.queue_response(CandidateBaseline("Understanding A", ("m1",)))
    core_a.consolidate("shared-region", ("m1",))

    assert core_a.get_current_baseline("shared-region") is not None
    assert core_b.get_current_baseline("shared-region") is None

    store_a.close()
    store_b.close()


# ---------------------------------------------------------------------------
# T11 — No MR authority escalation
# ---------------------------------------------------------------------------
def test_t11_no_authority_escalation(lce_core: LceCore) -> None:
    """LCE Core exposes no write API and codebase imports zero Body/Intent/Appraisal/C10 runtime modules."""
    forbidden_terms = (
        "write_evidence",
        "admit_evidence",
        "write_fact",
        "canonical_fact",
        "c10",
        "write_intent",
        "set_intent",
        "action_policy",
        "write_policy",
        "appraisal",
    )

    public_methods = [
        attr for attr in dir(lce_core) if not attr.startswith("_") and callable(getattr(lce_core, attr))
    ]

    for method in public_methods:
        for term in forbidden_terms:
            assert term not in method.lower(), f"Forbidden authority escalation method detected: {method}"

    # LceCore only provides consolidate, get_current_baseline, get_history
    assert set(public_methods) == {"consolidate", "get_current_baseline", "get_history"}

    # Inspect all python files under src/lce to ensure ZERO imports of forbidden runtime authority
    src_dir = Path(__file__).resolve().parent.parent / "src" / "lce"
    forbidden_modules = {"mind_runtime", "c10", "intent", "action_policy", "appraisal", "body"}

    for py_file in src_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split(".")[0].lower()
                    assert root_mod not in forbidden_modules, (
                        f"Forbidden module imported in {py_file.name}: {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                root_mod = node.module.split(".")[0].lower()
                assert root_mod not in forbidden_modules, (
                    f"Forbidden module imported in {py_file.name}: {node.module}"
                )


# ---------------------------------------------------------------------------
# T12 — Vector independence
# ---------------------------------------------------------------------------
def test_t12_vector_independence(
    lce_core: LceCore,
    fake_substrate: FakeMemorySubstrate,
    fake_consolidator: ScriptableFakeConsolidator,
) -> None:
    """Mutating retrieval metadata (vector coordinates, similarity rank) does NOT alter provenance."""
    fake_substrate.add_memory(
        "m1",
        "Memory item with vector coords",
        ("ev-1",),
        retrieval_metadata={"vector": [0.12, 0.34, 0.56], "rank": 1},
    )

    fake_consolidator.queue_response(
        CandidateBaseline("Understanding from point", ("m1",))
    )
    res = lce_core.consolidate("reg-vec", ("m1",))
    b1 = res.baseline
    assert b1.supporting_memory_ids == ("m1",)

    # Substrate changes vector index row, re-indexes, or modifies similarity metadata
    fake_substrate.update_metadata(
        "m1",
        {"vector": [0.99, 0.88, 0.77], "rank": 99, "reindexed": True},
    )

    # Provenance lookup still reliably resolves to stable memory_id "m1"
    fetched = fake_substrate.get_by_ids(b1.supporting_memory_ids)
    assert len(fetched) == 1
    assert fetched[0].memory_id == "m1"
    assert fetched[0].content == "Memory item with vector coords"
    assert fetched[0].source_refs == ("ev-1",)
    assert fetched[0].retrieval_metadata["reindexed"] is True

    # Baseline HEAD in store remains completely unchanged
    current = lce_core.get_current_baseline("reg-vec")
    assert current is not None
    assert current.baseline_id == b1.baseline_id
    assert current.supporting_memory_ids == ("m1",)


def test_candidate_with_duplicate_memory_ids_rejected(
    lce_core: LceCore,
    fake_substrate: FakeMemorySubstrate,
) -> None:
    """A candidate baseline with duplicate memory IDs fails at the contract boundary and leaves store untouched."""
    fake_substrate.add_memory("m1", "Content", ("ev-1",))
    with pytest.raises(ValueError, match="duplicate memory IDs"):
        CandidateBaseline(
            content="Understanding",
            supporting_memory_ids=("m1", "m1"),
        )
    assert lce_core.get_current_baseline("reg-dup") is None
