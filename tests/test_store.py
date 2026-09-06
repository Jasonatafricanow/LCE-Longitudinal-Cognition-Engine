"""Unit tests for SQLite baseline persistence and isolation."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from lce.contracts.baseline import Baseline, compute_content_hash
from lce.store.sqlite_store import SqliteBaselineStore, StorageIntegrityError


def _make_baseline(
    *,
    baseline_id: str,
    region_id: str,
    revision_number: int,
    content: str,
    supporting_memory_ids: tuple[str, ...],
    previous_baseline_id: str | None = None,
) -> Baseline:
    return Baseline(
        baseline_id=baseline_id,
        region_id=region_id,
        revision_number=revision_number,
        content=content,
        content_hash=compute_content_hash(content),
        supporting_memory_ids=supporting_memory_ids,
        created_at=datetime.now(UTC),
        previous_baseline_id=previous_baseline_id,
        model_trace={"model": "test-model", "confidence": 1.0},
    )


def test_schema_has_no_raw_memory_tables(tmp_path: Path) -> None:
    store = SqliteBaselineStore(tmp_path)
    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name ASC")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    store.close()

    # Verify strictly expected tables and NO raw memory table
    assert tables == ["baseline_memory_refs", "baseline_revisions", "baselines_head"]
    assert "memories" not in tables
    assert "memory_items" not in tables
    assert "evidence" not in tables


def test_save_and_get_head(tmp_path: Path) -> None:
    store = SqliteBaselineStore(tmp_path)
    assert store.get_head("reg-1") is None

    b1 = _make_baseline(
        baseline_id="base-1",
        region_id="reg-1",
        revision_number=1,
        content="User adopted an orange cat.",
        supporting_memory_ids=("mem-1", "mem-2"),
    )
    store.save_revision(b1)

    head = store.get_head("reg-1")
    assert head is not None
    assert head.baseline_id == "base-1"
    assert head.revision_number == 1
    assert head.content == "User adopted an orange cat."
    assert head.supporting_memory_ids == ("mem-1", "mem-2")
    assert head.previous_baseline_id is None

    # Advance to rev 2
    b2 = _make_baseline(
        baseline_id="base-2",
        region_id="reg-1",
        revision_number=2,
        content="User adopted an orange cat and bought kitten food.",
        supporting_memory_ids=("mem-1", "mem-2", "mem-3"),
        previous_baseline_id="base-1",
    )
    store.save_revision(b2)

    head2 = store.get_head("reg-1")
    assert head2 is not None
    assert head2.baseline_id == "base-2"
    assert head2.revision_number == 2
    assert head2.previous_baseline_id == "base-1"
    assert head2.supporting_memory_ids == ("mem-1", "mem-2", "mem-3")

    history = store.get_history("reg-1")
    assert len(history.revisions) == 2
    assert history.revisions[0].baseline_id == "base-2"
    assert history.revisions[1].baseline_id == "base-1"

    store.close()


def test_monotonic_revision_sequence_enforcement(tmp_path: Path) -> None:
    store = SqliteBaselineStore(tmp_path)

    # Cannot start with rev 2
    b_invalid_first = _make_baseline(
        baseline_id="base-x",
        region_id="reg-1",
        revision_number=2,
        content="Invalid first rev",
        supporting_memory_ids=("mem-1",),
        previous_baseline_id="base-old",
    )
    with pytest.raises(StorageIntegrityError, match="First revision"):
        store.save_revision(b_invalid_first)

    # Valid first
    b1 = _make_baseline(
        baseline_id="base-1",
        region_id="reg-1",
        revision_number=1,
        content="First rev",
        supporting_memory_ids=("mem-1",),
    )
    store.save_revision(b1)

    # Skipping rev (e.g. rev 3 instead of rev 2)
    b3 = _make_baseline(
        baseline_id="base-3",
        region_id="reg-1",
        revision_number=3,
        content="Skipping rev",
        supporting_memory_ids=("mem-1",),
        previous_baseline_id="base-1",
    )
    with pytest.raises(StorageIntegrityError, match="Expected revision_number=2"):
        store.save_revision(b3)

    # Wrong previous_baseline_id
    b2_wrong_prev = _make_baseline(
        baseline_id="base-2",
        region_id="reg-1",
        revision_number=2,
        content="Wrong prev",
        supporting_memory_ids=("mem-1",),
        previous_baseline_id="base-unknown",
    )
    with pytest.raises(StorageIntegrityError, match="Expected previous_baseline_id='base-1'"):
        store.save_revision(b2_wrong_prev)

    store.close()


def test_storage_root_isolation(tmp_path: Path) -> None:
    root_a = tmp_path / "ns_a"
    root_b = tmp_path / "ns_b"

    store_a = SqliteBaselineStore(root_a)
    store_b = SqliteBaselineStore(root_b)

    b1_a = _make_baseline(
        baseline_id="base-a1",
        region_id="reg-shared",
        revision_number=1,
        content="Namespace A understanding",
        supporting_memory_ids=("mem-a",),
    )
    store_a.save_revision(b1_a)

    assert store_a.get_head("reg-shared") is not None
    assert store_b.get_head("reg-shared") is None

    store_a.close()
    store_b.close()


def test_restart_stability(tmp_path: Path) -> None:
    root = tmp_path / "restart_test"
    store1 = SqliteBaselineStore(root)

    b1 = _make_baseline(
        baseline_id="base-r1",
        region_id="reg-1",
        revision_number=1,
        content="Durable understanding",
        supporting_memory_ids=("m-1", "m-2"),
    )
    store1.save_revision(b1)
    store1.close()

    # Reconnect from fresh instance
    store2 = SqliteBaselineStore(root)
    head = store2.get_head("reg-1")
    assert head is not None
    assert head.baseline_id == "base-r1"
    assert head.content == "Durable understanding"
    assert head.supporting_memory_ids == ("m-1", "m-2")

    store2.close()


def test_fk1_pragma_enabled(tmp_path: Path) -> None:
    """PRAGMA foreign_keys must be active (= 1) on SQLite connections."""
    store = SqliteBaselineStore(tmp_path)
    conn = store._get_connection()
    row = conn.execute("PRAGMA foreign_keys;").fetchone()
    assert row is not None
    assert row[0] == 1
    store.close()


def test_fk2_head_foreign_key_enforcement(tmp_path: Path) -> None:
    """Inserting head pointer referencing nonexistent baseline_id fails with foreign key error."""
    store = SqliteBaselineStore(tmp_path)
    conn = store._get_connection()
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        conn.execute(
            "INSERT INTO baselines_head (region_id, baseline_id, updated_at) VALUES (?, ?, ?)",
            ("reg-1", "nonexistent-base-id", datetime.now(UTC).isoformat()),
        )
    store.close()


def test_fk3_refs_foreign_key_enforcement(tmp_path: Path) -> None:
    """Inserting memory ref row referencing nonexistent baseline_id fails with foreign key error."""
    store = SqliteBaselineStore(tmp_path)
    conn = store._get_connection()
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        conn.execute(
            "INSERT INTO baseline_memory_refs (baseline_id, memory_id) VALUES (?, ?)",
            ("nonexistent-base-id", "mem-1"),
        )
    store.close()


def test_tx1_failure_before_refs_rolls_back(tmp_path: Path) -> None:
    """Simulated failure during memory refs insertion leaves revision uncommitted and head absent."""
    store = SqliteBaselineStore(tmp_path)
    b1 = _make_baseline(
        baseline_id="base-tx1",
        region_id="reg-tx1",
        revision_number=1,
        content="Tx test 1",
        supporting_memory_ids=("mem-1", "mem-2"),
    )

    conn = store._get_connection()
    conn.execute(
        "CREATE TRIGGER fail_refs BEFORE INSERT ON baseline_memory_refs "
        "BEGIN SELECT RAISE(ABORT, 'Simulated failure during memory refs insertion'); END;"
    )

    with pytest.raises(StorageIntegrityError, match="Simulated failure during memory refs insertion"):
        store.save_revision(b1)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM baseline_revisions")
    assert cursor.fetchone()[0] == 0
    cursor.execute("SELECT COUNT(*) FROM baseline_memory_refs")
    assert cursor.fetchone()[0] == 0
    cursor.execute("SELECT COUNT(*) FROM baselines_head")
    assert cursor.fetchone()[0] == 0
    assert store.get_head("reg-tx1") is None
    store.close()


def test_tx2_failure_before_head_rolls_back(tmp_path: Path) -> None:
    """Simulated failure during head pointer update leaves revision and refs uncommitted and head absent."""
    store = SqliteBaselineStore(tmp_path)
    b1 = _make_baseline(
        baseline_id="base-tx2",
        region_id="reg-tx2",
        revision_number=1,
        content="Tx test 2",
        supporting_memory_ids=("mem-1",),
    )

    conn = store._get_connection()
    conn.execute(
        "CREATE TRIGGER fail_head BEFORE INSERT ON baselines_head "
        "BEGIN SELECT RAISE(ABORT, 'Simulated failure during head update'); END;"
    )

    with pytest.raises(StorageIntegrityError, match="Simulated failure during head update"):
        store.save_revision(b1)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM baseline_revisions")
    assert cursor.fetchone()[0] == 0
    cursor.execute("SELECT COUNT(*) FROM baseline_memory_refs")
    assert cursor.fetchone()[0] == 0
    cursor.execute("SELECT COUNT(*) FROM baselines_head")
    assert cursor.fetchone()[0] == 0
    assert store.get_head("reg-tx2") is None
    store.close()


def test_tx3_retry_after_rollback_succeeds(tmp_path: Path) -> None:
    """Following a failed save_revision, a subsequent valid save succeeds cleanly."""
    store = SqliteBaselineStore(tmp_path)
    b1 = _make_baseline(
        baseline_id="base-tx3",
        region_id="reg-tx3",
        revision_number=1,
        content="Tx test 3 retry",
        supporting_memory_ids=("mem-1", "mem-2"),
    )

    conn = store._get_connection()
    conn.execute(
        "CREATE TRIGGER fail_transient BEFORE INSERT ON baseline_memory_refs "
        "BEGIN SELECT RAISE(ABORT, 'Transient DB write glitch'); END;"
    )

    with pytest.raises(StorageIntegrityError, match="Transient DB write glitch"):
        store.save_revision(b1)

    # Drop trigger to simulate transient failure resolved
    conn.execute("DROP TRIGGER fail_transient;")

    # Retry should succeed cleanly
    store.save_revision(b1)

    head = store.get_head("reg-tx3")
    assert head is not None
    assert head.baseline_id == "base-tx3"
    assert head.revision_number == 1
    assert head.supporting_memory_ids == ("mem-1", "mem-2")
    assert head.content == "Tx test 3 retry"

    history = store.get_history("reg-tx3")
    assert len(history.revisions) == 1
    assert history.revisions[0].baseline_id == "base-tx3"

    store.close()
