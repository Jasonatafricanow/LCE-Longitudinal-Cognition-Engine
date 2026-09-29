"""Durable suppression of explicitly rejected derived proposals.

A rejection is narrow: it suppresses only the same region + normalized proposal
content + exact authorized source closure. New source evidence changes the
support signature and therefore reopens evaluation automatically. An explicit
authorized reopen may also lift the suppression without deleting audit history.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from lce.contracts.baseline import compute_content_hash


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value.strip()


def support_signature(source_refs: tuple[str, ...]) -> str:
    if not isinstance(source_refs, tuple) or not source_refs:
        raise ValueError("source_refs must be a nonempty tuple")
    normalized = tuple(sorted({_require_text(item, "source_ref") for item in source_refs}))
    payload = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    return "support_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


@dataclass(frozen=True, slots=True)
class DerivedProposalRejection:
    rejection_id: str
    region_id: str
    content_hash: str
    support_signature: str
    rejected_content: str
    rejected_at: datetime
    authority_ref: str
    reason: str | None = None
    reopened_at: datetime | None = None
    reopening_authority_ref: str | None = None

    @property
    def active(self) -> bool:
        return self.reopened_at is None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS derived_proposal_rejections (
    rejection_id TEXT PRIMARY KEY,
    region_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    support_signature TEXT NOT NULL,
    rejected_content TEXT NOT NULL,
    rejected_at TEXT NOT NULL,
    authority_ref TEXT NOT NULL,
    reason TEXT,
    reopened_at TEXT,
    reopening_authority_ref TEXT
);
CREATE INDEX IF NOT EXISTS idx_derived_rejection_lookup
ON derived_proposal_rejections(region_id, content_hash, support_signature, reopened_at);
"""


class DerivedProposalRejectionStore:
    """Audit-preserving replay suppression for derived cognition."""

    DB_FILENAME = "derived_rejections.sqlite"

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / self.DB_FILENAME
        self._conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    @staticmethod
    def _row(row: tuple[object, ...]) -> DerivedProposalRejection:
        return DerivedProposalRejection(
            rejection_id=str(row[0]),
            region_id=str(row[1]),
            content_hash=str(row[2]),
            support_signature=str(row[3]),
            rejected_content=str(row[4]),
            rejected_at=datetime.fromisoformat(str(row[5])),
            authority_ref=str(row[6]),
            reason=str(row[7]) if row[7] is not None else None,
            reopened_at=(
                datetime.fromisoformat(str(row[8]))
                if row[8] is not None
                else None
            ),
            reopening_authority_ref=(
                str(row[9]) if row[9] is not None else None
            ),
        )

    def active_match(
        self,
        *,
        region_id: str,
        content: str,
        source_refs: tuple[str, ...],
    ) -> DerivedProposalRejection | None:
        region = _require_text(region_id, "region_id")
        content_hash = compute_content_hash(_require_text(content, "content"))
        signature = support_signature(source_refs)
        row = self._conn.execute(
            """
            SELECT rejection_id, region_id, content_hash, support_signature,
                   rejected_content, rejected_at, authority_ref, reason,
                   reopened_at, reopening_authority_ref
            FROM derived_proposal_rejections
            WHERE region_id=? AND content_hash=? AND support_signature=?
              AND reopened_at IS NULL
            ORDER BY rejected_at DESC, rejection_id DESC
            LIMIT 1
            """,
            (region, content_hash, signature),
        ).fetchone()
        return None if row is None else self._row(row)

    def reject(
        self,
        *,
        region_id: str,
        content: str,
        source_refs: tuple[str, ...],
        authority_ref: str,
        reason: str | None = None,
        rejected_at: datetime | None = None,
    ) -> DerivedProposalRejection:
        region = _require_text(region_id, "region_id")
        proposal = _require_text(content, "content")
        authority = _require_text(authority_ref, "authority_ref")
        if reason is not None:
            reason = _require_text(reason, "reason")
        at = rejected_at or datetime.now(UTC)
        if at.tzinfo != UTC:
            raise ValueError("rejected_at must be aware UTC")
        existing = self.active_match(
            region_id=region,
            content=proposal,
            source_refs=source_refs,
        )
        if existing is not None:
            return existing
        item = DerivedProposalRejection(
            rejection_id="reject_" + uuid.uuid4().hex,
            region_id=region,
            content_hash=compute_content_hash(proposal),
            support_signature=support_signature(source_refs),
            rejected_content=proposal,
            rejected_at=at,
            authority_ref=authority,
            reason=reason,
        )
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO derived_proposal_rejections(
                    rejection_id, region_id, content_hash, support_signature,
                    rejected_content, rejected_at, authority_ref, reason,
                    reopened_at, reopening_authority_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                """,
                (
                    item.rejection_id,
                    item.region_id,
                    item.content_hash,
                    item.support_signature,
                    item.rejected_content,
                    item.rejected_at.isoformat(),
                    item.authority_ref,
                    item.reason,
                ),
            )
        return item

    def reopen(
        self,
        rejection_id: str,
        *,
        authority_ref: str,
        reopened_at: datetime | None = None,
    ) -> DerivedProposalRejection:
        rejection = _require_text(rejection_id, "rejection_id")
        authority = _require_text(authority_ref, "authority_ref")
        at = reopened_at or datetime.now(UTC)
        if at.tzinfo != UTC:
            raise ValueError("reopened_at must be aware UTC")
        row = self._conn.execute(
            """
            SELECT rejection_id, region_id, content_hash, support_signature,
                   rejected_content, rejected_at, authority_ref, reason,
                   reopened_at, reopening_authority_ref
            FROM derived_proposal_rejections
            WHERE rejection_id=?
            """,
            (rejection,),
        ).fetchone()
        if row is None:
            raise KeyError(rejection)
        current = self._row(row)
        if current.reopened_at is None:
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE derived_proposal_rejections
                    SET reopened_at=?, reopening_authority_ref=?
                    WHERE rejection_id=?
                    """,
                    (at.isoformat(), authority, rejection),
                )
        row = self._conn.execute(
            """
            SELECT rejection_id, region_id, content_hash, support_signature,
                   rejected_content, rejected_at, authority_ref, reason,
                   reopened_at, reopening_authority_ref
            FROM derived_proposal_rejections
            WHERE rejection_id=?
            """,
            (rejection,),
        ).fetchone()
        assert row is not None
        return self._row(row)

    def list(
        self,
        *,
        region_id: str | None = None,
    ) -> tuple[DerivedProposalRejection, ...]:
        if region_id is None:
            rows = self._conn.execute(
                """
                SELECT rejection_id, region_id, content_hash, support_signature,
                       rejected_content, rejected_at, authority_ref, reason,
                       reopened_at, reopening_authority_ref
                FROM derived_proposal_rejections
                ORDER BY rejected_at, rejection_id
                """
            ).fetchall()
        else:
            region = _require_text(region_id, "region_id")
            rows = self._conn.execute(
                """
                SELECT rejection_id, region_id, content_hash, support_signature,
                       rejected_content, rejected_at, authority_ref, reason,
                       reopened_at, reopening_authority_ref
                FROM derived_proposal_rejections
                WHERE region_id=?
                ORDER BY rejected_at, rejection_id
                """,
                (region,),
            ).fetchall()
        return tuple(self._row(row) for row in rows)

    def close(self) -> None:
        self._conn.close()
