"""Snapshot-based structure observation derived from Semantic Block vectors."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.structure.contracts import (
    HigherOrderCandidate,
    StructureChange,
    StructureConfig,
    StructureDiff,
    StructureObservation,
    StructureSnapshot,
)


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    a, b = set(left), set(right)
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


class SnapshotStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.root / "structure_snapshots.sqlite"))
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                snapshot_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def save(self, snapshot: StructureSnapshot) -> None:
        payload = {
            "snapshot_id": snapshot.snapshot_id,
            "timestamp": snapshot.timestamp.isoformat(),
            "cutoff": snapshot.cutoff.isoformat(),
            "visible_block_ids": list(snapshot.visible_block_ids),
            "algorithm_version": snapshot.algorithm_version,
            "config": {
                "k_values": list(snapshot.config.k_values),
                "min_similarity": snapshot.config.min_similarity,
                "higher_order_similarity": snapshot.config.higher_order_similarity,
                "algorithm_version": snapshot.config.algorithm_version,
            },
            "structures": [
                {
                    "structure_id": item.structure_id,
                    "center_block_id": item.center_block_id,
                    "member_block_ids": list(item.member_block_ids),
                    "k": item.k,
                    "support_score": item.support_score,
                    "neighbourhood_stability": item.neighbourhood_stability,
                    "local_overlap": item.local_overlap,
                    "multi_point_participation": item.multi_point_participation,
                    "temporal_dates": list(item.temporal_dates),
                }
                for item in snapshot.structures
            ],
        }
        self.conn.execute(
            "INSERT OR REPLACE INTO snapshots VALUES (?, ?)",
            (snapshot.snapshot_id, json.dumps(payload, sort_keys=True)),
        )
        self.conn.commit()

    @staticmethod
    def _decode(payload: str) -> StructureSnapshot:
        raw = json.loads(payload)
        config = StructureConfig(**raw["config"] | {"k_values": tuple(raw["config"]["k_values"])})
        structures = tuple(
            StructureObservation(
                structure_id=item["structure_id"],
                center_block_id=item["center_block_id"],
                member_block_ids=tuple(item["member_block_ids"]),
                k=item["k"],
                support_score=item["support_score"],
                neighbourhood_stability=item["neighbourhood_stability"],
                local_overlap=item["local_overlap"],
                multi_point_participation=item["multi_point_participation"],
                temporal_dates=tuple(item["temporal_dates"]),
            )
            for item in raw["structures"]
        )
        return StructureSnapshot(
            snapshot_id=raw["snapshot_id"],
            timestamp=datetime.fromisoformat(raw["timestamp"]),
            cutoff=datetime.fromisoformat(raw["cutoff"]),
            visible_block_ids=tuple(raw["visible_block_ids"]),
            structures=structures,
            algorithm_version=raw["algorithm_version"],
            config=config,
        )

    def latest_before(self, cutoff: datetime, *, exclude_id: str) -> StructureSnapshot | None:
        candidates = []
        for (payload,) in self.conn.execute("SELECT payload_json FROM snapshots"):
            snapshot = self._decode(payload)
            if snapshot.snapshot_id != exclude_id and snapshot.cutoff < cutoff:
                candidates.append(snapshot)
        return max(candidates, key=lambda item: item.cutoff, default=None)

    def all_snapshots(self) -> tuple[StructureSnapshot, ...]:
        snapshots = [self._decode(payload) for (payload,) in self.conn.execute("SELECT payload_json FROM snapshots")]
        return tuple(sorted(snapshots, key=lambda item: (item.cutoff, item.snapshot_id)))

    def delete_all(self) -> None:
        self.conn.execute("DELETE FROM snapshots")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()


class SnapshotStructureDiscovery:
    """Compute rebuildable observations over current-valid Semantic Blocks."""

    def __init__(
        self,
        memory: ReferenceMemoryStore,
        snapshot_root: Path | str,
        *,
        config: StructureConfig | None = None,
    ) -> None:
        self.memory = memory
        self.config = config or StructureConfig()
        self.snapshots = SnapshotStore(snapshot_root)

    def create_snapshot(self, cutoff: datetime) -> StructureSnapshot:
        if cutoff.tzinfo != UTC:
            raise ValueError("cutoff must be UTC")
        blocks = [
            block
            for block in self.memory.list_semantic_blocks(current_valid_only=True)
            if block.occurred_end <= cutoff
        ]
        blocks.sort(key=lambda block: (block.occurred_start, block.block_id))
        visible_ids = tuple(block.block_id for block in blocks)
        identity = {
            "cutoff": cutoff.isoformat(),
            "visible": visible_ids,
            "config": self.config.algorithm_version,
            "k": self.config.k_values,
            "min_similarity": self.config.min_similarity,
        }
        snapshot_id = "snap_" + hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]
        vectors = {block.block_id: self.memory.get_vector(block.block_id).values for block in blocks}
        block_by_id = {block.block_id: block for block in blocks}
        observations: list[StructureObservation] = []
        for k in self.config.k_values:
            for center in visible_ids:
                ranked = sorted(
                    (
                        (_cosine(vectors[center], vectors[other]), other)
                        for other in visible_ids
                        if other != center
                    ),
                    key=lambda item: (-item[0], item[1]),
                )
                neighbours = tuple(
                    other for similarity, other in ranked[:k] if similarity >= self.config.min_similarity
                )
                members = (center,) + neighbours
                similarities = [
                    _cosine(vectors[center], other_vector)
                    for other_id, other_vector in vectors.items()
                    if other_id in neighbours
                ]
                dates = tuple(sorted({block_by_id[item].occurred_start.date().isoformat() for item in members}))
                observations.append(
                    StructureObservation(
                        structure_id=f"{self.config.algorithm_version}:{center}:k{k}",
                        center_block_id=center,
                        member_block_ids=members,
                        k=k,
                        support_score=sum(similarities) / len(similarities) if similarities else 0.0,
                        neighbourhood_stability=0.0,
                        local_overlap=0.0,
                        multi_point_participation=0,
                        temporal_dates=dates,
                    )
                )

        previous = self._latest_other_snapshot(snapshot_id, cutoff)
        previous_by_id = {item.structure_id: item for item in previous.structures} if previous else {}
        participation: defaultdict[str, int] = defaultdict(int)
        for observation in observations:
            for member in observation.member_block_ids:
                participation[member] += 1
        enriched: list[StructureObservation] = []
        for observation in observations:
            previous_item = previous_by_id.get(observation.structure_id)
            overlap = max(
                (_jaccard(observation.member_block_ids, other.member_block_ids)
                 for other in observations if other.structure_id != observation.structure_id),
                default=0.0,
            )
            enriched.append(
                StructureObservation(
                    structure_id=observation.structure_id,
                    center_block_id=observation.center_block_id,
                    member_block_ids=observation.member_block_ids,
                    k=observation.k,
                    support_score=observation.support_score,
                    neighbourhood_stability=(
                        _jaccard(observation.member_block_ids, previous_item.member_block_ids)
                        if previous_item else 0.0
                    ),
                    local_overlap=overlap,
                    multi_point_participation=sum(
                        1 for item in observations if observation.center_block_id in item.member_block_ids
                    ),
                    temporal_dates=observation.temporal_dates,
                )
            )
        snapshot = StructureSnapshot(
            snapshot_id=snapshot_id,
            timestamp=cutoff,
            cutoff=cutoff,
            visible_block_ids=visible_ids,
            structures=tuple(enriched),
            algorithm_version=self.config.algorithm_version,
            config=self.config,
        )
        self.snapshots.save(snapshot)
        return snapshot

    def _latest_other_snapshot(self, current_id: str, cutoff: datetime) -> StructureSnapshot | None:
        return self.snapshots.latest_before(cutoff, exclude_id=current_id)

    def diff(self, previous: StructureSnapshot, current: StructureSnapshot) -> StructureDiff:
        old = {item.structure_id: item for item in previous.structures}
        new = {item.structure_id: item for item in current.structures}
        new_members: list[StructureChange] = []
        lost: list[StructureChange] = []
        stronger: list[StructureChange] = []
        reconnections: list[StructureChange] = []
        for structure_id, observation in new.items():
            previous_item = old.get(structure_id)
            if previous_item is None:
                new_members.append(StructureChange(structure_id, added_block_ids=observation.member_block_ids))
                continue
            added = tuple(item for item in observation.member_block_ids if item not in previous_item.member_block_ids)
            removed = tuple(item for item in previous_item.member_block_ids if item not in observation.member_block_ids)
            if added:
                new_members.append(StructureChange(structure_id, added_block_ids=added))
            if removed or observation.support_score < previous_item.support_score:
                lost.append(StructureChange(structure_id, removed_block_ids=removed))
            if observation.support_score > previous_item.support_score + 1e-9 or added:
                stronger.append(StructureChange(structure_id, added_block_ids=added))
            if len(previous_item.member_block_ids) == 1 and len(observation.member_block_ids) > 1:
                reconnections.append(StructureChange(structure_id, added_block_ids=added))

        reorganizations: list[StructureChange] = []
        for old_id, old_item in old.items():
            if old_id in new:
                continue
            related = tuple(
                item.structure_id for item in current.structures
                if _jaccard(old_item.member_block_ids, item.member_block_ids) > 0.0
            )
            if related:
                reorganizations.append(StructureChange(old_id, relation_ids=related))

        linked: list[StructureChange] = []
        ordered = list(current.structures)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1:]:
                if left.center_block_id == right.center_block_id:
                    continue
                overlap = _jaccard(left.member_block_ids, right.member_block_ids)
                if overlap > 0.0:
                    linked.append(StructureChange(left.structure_id, relation_ids=(right.structure_id,)))
        return StructureDiff(
            previous_snapshot_id=previous.snapshot_id,
            current_snapshot_id=current.snapshot_id,
            new_members=tuple(new_members),
            lost_or_weakened=tuple(lost),
            stronger_support=tuple(stronger),
            reconnections=tuple(reconnections),
            reorganizations=tuple(reorganizations),
            linked_structures=tuple(linked),
        )

    def higher_order_candidates(self, snapshot: StructureSnapshot) -> tuple[HigherOrderCandidate, ...]:
        candidates: list[HigherOrderCandidate] = []
        observations = [item for item in snapshot.structures if len(item.member_block_ids) >= 2]
        for index, left in enumerate(observations):
            for right in observations[index + 1:]:
                if left.center_block_id == right.center_block_id:
                    continue
                shared = set(left.member_block_ids) & set(right.member_block_ids)
                left_centroid = self._centroid(left.member_block_ids)
                right_centroid = self._centroid(right.member_block_ids)
                relation = _cosine(left_centroid, right_centroid)
                if not shared and relation < self.config.higher_order_similarity:
                    continue
                if not shared and (len(left.temporal_dates) < 2 or len(right.temporal_dates) < 2):
                    continue
                structure_ids = tuple(sorted((left.structure_id, right.structure_id)))
                block_ids = tuple(sorted(set(left.member_block_ids) | set(right.member_block_ids)))
                candidate_id = "hoc_" + hashlib.sha256(
                    f"{snapshot.snapshot_id}|{'|'.join(structure_ids)}".encode()
                ).hexdigest()[:20]
                candidates.append(
                    HigherOrderCandidate(
                        candidate_id=candidate_id,
                        snapshot_id=snapshot.snapshot_id,
                        supporting_structure_ids=structure_ids,
                        supporting_block_ids=block_ids,
                        relation_type="structure_relation",
                        strength=max(relation, 1.0 if shared else relation),
                        metadata={"shared_block_ids": sorted(shared)},
                    )
                )
        unique = {candidate.candidate_id: candidate for candidate in candidates}
        return tuple(unique[key] for key in sorted(unique))

    def _centroid(self, block_ids: Iterable[str]) -> tuple[float, ...]:
        vectors = [self.memory.get_vector(block_id).values for block_id in block_ids]
        return tuple(sum(vector[index] for vector in vectors) / len(vectors) for index in range(len(vectors[0])))

    def expand_candidate_to_blocks(self, candidate: HigherOrderCandidate) -> tuple[str, ...]:
        return candidate.supporting_block_ids

    def expand_candidate_to_raw(self, candidate: HigherOrderCandidate) -> tuple[str, ...]:
        raw: set[str] = set()
        for block_id in candidate.supporting_block_ids:
            raw.update(self.memory.get_semantic_block(block_id).raw_evidence_ids)
        return tuple(sorted(raw))

    def delete_derived_snapshots(self) -> None:
        self.snapshots.delete_all()

    def close(self) -> None:
        self.snapshots.close()
