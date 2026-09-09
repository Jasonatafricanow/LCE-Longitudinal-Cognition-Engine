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

from lce.reference_memory.contracts import ReferenceMemorySubstratePort, SemanticBlock
from lce.structure.contracts import (
    HigherOrderCandidate,
    StructureChange,
    StructureConfig,
    StructureDiff,
    StructureObservation,
    StructureSnapshot,
)

__all__ = ["SnapshotStructureDiscovery", "StructureConfig"]


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
            "block_states": [
                {
                    "block_id": block.block_id,
                    "content": block.content,
                    "raw_evidence_ids": list(block.raw_evidence_ids),
                    "occurred_start": block.occurred_start.isoformat(),
                    "occurred_end": block.occurred_end.isoformat(),
                    "compiler_version": block.compiler_version,
                    "lineage_id": block.lineage_id,
                    "metadata": dict(block.metadata),
                    "state_id": block.state_id,
                    "state_version": block.state_version,
                }
                for block in snapshot.block_states
            ],
            "vectors": {key: list(value) for key, value in snapshot.vectors.items()},
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
        block_states = tuple(
            SemanticBlock(
                block_id=item["block_id"],
                content=item["content"],
                raw_evidence_ids=tuple(item["raw_evidence_ids"]),
                occurred_start=datetime.fromisoformat(item["occurred_start"]),
                occurred_end=datetime.fromisoformat(item["occurred_end"]),
                compiler_version=item["compiler_version"],
                lineage_id=item["lineage_id"],
                metadata=item["metadata"],
                state_id=item.get("state_id"),
                state_version=int(item.get("state_version", 1)),
            )
            for item in raw.get("block_states", [])
        )
        return StructureSnapshot(
            snapshot_id=raw["snapshot_id"],
            timestamp=datetime.fromisoformat(raw["timestamp"]),
            cutoff=datetime.fromisoformat(raw["cutoff"]),
            visible_block_ids=tuple(raw["visible_block_ids"]),
            structures=structures,
            algorithm_version=raw["algorithm_version"],
            config=config,
            block_states=block_states,
            vectors={key: tuple(float(value) for value in values) for key, values in raw.get("vectors", {}).items()},
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

    def get(self, snapshot_id: str) -> StructureSnapshot:
        row = self.conn.execute("SELECT payload_json FROM snapshots WHERE snapshot_id = ?", (snapshot_id,)).fetchone()
        if row is None:
            raise KeyError(snapshot_id)
        return self._decode(row[0])

    def delete_all(self) -> None:
        self.conn.execute("DELETE FROM snapshots")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()


class SnapshotStructureDiscovery:
    """Compute rebuildable observations over current-valid Semantic Blocks."""

    def __init__(
        self,
        memory: ReferenceMemorySubstratePort,
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
        blocks = list(self.memory.list_semantic_blocks_at_cutoff(cutoff, current_valid_only=True))
        blocks.sort(key=lambda block: (block.occurred_start, block.block_id))
        visible_ids = tuple(block.block_id for block in blocks)
        identity = {
            "cutoff": cutoff.isoformat(),
            "visible": visible_ids,
            "config": self.config.algorithm_version,
            "k": self.config.k_values,
            "min_similarity": self.config.min_similarity,
            "higher_order_similarity": self.config.higher_order_similarity,
            "states": tuple(block.state_id for block in blocks),
            "vectors": tuple(
                (
                    block.block_id,
                    self.memory.get_vector(block.block_id, state_id=block.state_id).values,
                    self.memory.get_vector(block.block_id, state_id=block.state_id).index_version,
                )
                for block in blocks
            ),
        }
        snapshot_id = "snap_" + hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]
        vectors = {
            block.block_id: self.memory.get_vector(block.block_id, state_id=block.state_id).values
            for block in blocks
        }
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
            block_states=tuple(blocks),
            vectors=vectors,
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
        current_groups = self._effective_groups(current)
        previous_groups = self._effective_groups(previous)
        previous_pairs = {
            tuple(sorted((left_key, right_key)))
            for index, (left_key, left) in enumerate(previous_groups)
            for right_key, right in previous_groups[index + 1:]
            if _jaccard(left.member_block_ids, right.member_block_ids) > 0.0
        }
        for index, (left_key, left) in enumerate(current_groups):
            for right_key, right in current_groups[index + 1:]:
                if _jaccard(left.member_block_ids, right.member_block_ids) <= 0.0:
                    continue
                if tuple(sorted((left_key, right_key))) in previous_pairs:
                    continue
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
        groups = self._effective_groups(snapshot)
        for index, (_left_key, left) in enumerate(groups):
            for right_key, right in groups[index + 1:]:
                shared = set(left.member_block_ids) & set(right.member_block_ids)
                left_centroid = self._centroid(snapshot, left.member_block_ids)
                right_centroid = self._centroid(snapshot, right.member_block_ids)
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

    @staticmethod
    def _effective_key(observation: StructureObservation) -> str:
        return "support:" + hashlib.sha256(
            "|".join(sorted(set(observation.member_block_ids))).encode()
        ).hexdigest()[:20]

    def _effective_groups(self, snapshot: StructureSnapshot) -> list[tuple[str, StructureObservation]]:
        grouped: dict[str, list[StructureObservation]] = defaultdict(list)
        for observation in snapshot.structures:
            if len(observation.member_block_ids) >= 2:
                grouped[self._effective_key(observation)].append(observation)
        return [
            (key, min(items, key=lambda item: (-item.support_score, item.structure_id)))
            for key, items in sorted(grouped.items())
        ]

    def _centroid(self, snapshot: StructureSnapshot, block_ids: Iterable[str]) -> tuple[float, ...]:
        vectors = []
        for block_id in block_ids:
            if block_id in snapshot.vectors:
                vectors.append(snapshot.vectors[block_id])
            else:
                vectors.append(self.memory.get_vector(block_id).values)
        return tuple(sum(vector[index] for vector in vectors) / len(vectors) for index in range(len(vectors[0])))

    def expand_candidate_to_blocks(self, candidate: HigherOrderCandidate) -> tuple[str, ...]:
        return candidate.supporting_block_ids

    def expand_candidate_to_raw(self, candidate: HigherOrderCandidate) -> tuple[str, ...]:
        raw: set[str] = set()
        snapshot = self.snapshots.get(candidate.snapshot_id)
        state_by_id = {block.block_id: block for block in snapshot.block_states}
        for block_id in candidate.supporting_block_ids:
            block = state_by_id.get(block_id) or self.memory.get_semantic_block(block_id)
            raw.update(block.raw_evidence_ids)
        return tuple(sorted(raw))

    def delete_derived_snapshots(self) -> None:
        self.snapshots.delete_all()

    def close(self) -> None:
        self.snapshots.close()
