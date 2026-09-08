from __future__ import annotations

from datetime import UTC, datetime, timedelta

from lce.reference_memory.contracts import RawEvidence


def longitudinal_corpus() -> tuple[RawEvidence, ...]:
    base = datetime(2026, 8, 1, tzinfo=UTC)
    specs = (
        ("E1", "alpha starts", "alpha", (1.0, 0.0, 0.0), False, None),
        ("E2", "beta starts", "beta", (0.98, 0.12, 0.0), False, None),
        ("E3", "alpha continues", "alpha", (0.99, 0.10, 0.0), False, None),
        ("E4", "beta continues", "beta", (0.97, 0.20, 0.0), False, None),
        ("E5", "alpha recap with new deadline", "alpha", (0.99, 0.11, 0.0), True, "deadline Friday"),
    )
    return tuple(
        RawEvidence(
            evidence_id=evidence_id,
            content=content,
            occurred_at=base + timedelta(days=index),
            ordering_key=f"{index:04d}:{evidence_id}",
            provenance={
                "source": "synthetic-longitudinal",
                "canonical": True,
                "topic": topic,
                "vector": vector,
                "recap": recap,
                **({"new_information": new_information} if new_information else {}),
            },
        )
        for index, (evidence_id, content, topic, vector, recap, new_information) in enumerate(specs)
    )
