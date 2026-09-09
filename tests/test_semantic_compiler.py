from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from lce.reference_memory.contracts import RawEvidence
from lce.reference_memory.sqlite import ReferenceMemoryStore
from lce.semantic.compiler import SemanticCompiler
from lce.semantic.contracts import SemanticDecision, SemanticGroup

BASE_TIME = datetime(2026, 2, 1, tzinfo=UTC)


def raw(evidence_id: str, content: str, day: int, **metadata: object) -> RawEvidence:
    return RawEvidence(
        evidence_id=evidence_id,
        content=content,
        occurred_at=BASE_TIME + timedelta(days=day),
        ordering_key=f"{day:04d}:{evidence_id}",
        provenance={"source": "synthetic", "canonical": True, **metadata},
    )


@dataclass
class ScriptedProvider:
    decisions: dict[str, SemanticDecision]

    def decide(self, *, evidence, open_block, recent_blocks):
        return self.decisions[evidence.evidence_id]


def test_same_raw_unit_can_split_distinct_topics(tmp_path) -> None:
    item = raw("E1", "network broke; dinner was good", 0)
    provider = ScriptedProvider(
        {
            "E1": SemanticDecision(
                action="SPLIT",
                subject="network",
                cognition="network failure",
                groups=(
                    SemanticGroup("network", "network failure"),
                    SemanticGroup("dinner", "dinner experience"),
                ),
            )
        }
    )
    store = ReferenceMemoryStore(tmp_path / "memory")
    result = SemanticCompiler(store, provider, lineage_id="lineage").process(item)
    assert len(result.block_ids) == 2
    blocks = store.list_semantic_blocks(current_valid_only=False)
    assert [block.content for block in blocks] == ["network failure", "dinner experience"]
    assert all(block.raw_evidence_ids == ("E1",) for block in blocks)
    store.close()


def test_semantic_continuity_across_raw_units_keeps_one_block(tmp_path) -> None:
    provider = ScriptedProvider(
        {
            "E1": SemanticDecision("NEW", "research", "research started"),
            "E2": SemanticDecision("CONTINUE", "research", "research progressed"),
        }
    )
    store = ReferenceMemoryStore(tmp_path / "memory")
    compiler = SemanticCompiler(store, provider, lineage_id="lineage")
    compiler.process(raw("E1", "start", 0))
    compiler.process(raw("E2", "continue", 1))
    blocks = store.list_semantic_blocks(current_valid_only=False)
    assert len(blocks) == 1
    assert blocks[0].raw_evidence_ids == ("E1", "E2")
    assert "research progressed" in blocks[0].content
    store.close()


def test_recap_deduplicates_without_losing_new_information(tmp_path) -> None:
    provider = ScriptedProvider(
        {
            "E1": SemanticDecision("NEW", "project", "project decision"),
            "E2": SemanticDecision(
                "RECAP", "project", "project decision; new deadline Friday",
                recap_block_ids=("TARGET",), new_information="new deadline Friday",
            ),
        }
    )
    store = ReferenceMemoryStore(tmp_path / "memory")
    compiler = SemanticCompiler(store, provider, lineage_id="lineage")
    first = compiler.process(raw("E1", "decision", 0))
    provider.decisions["E2"] = SemanticDecision(
        "RECAP", "project", "project decision; new deadline Friday",
        recap_block_ids=first.block_ids, new_information="new deadline Friday",
    )
    compiler.process(raw("E2", "recap", 1, recap=True))
    blocks = store.list_semantic_blocks(current_valid_only=False)
    assert len(blocks) == 1
    assert blocks[0].raw_evidence_ids == ("E1", "E2")
    assert "new deadline Friday" in blocks[0].content
    store.close()


def test_restart_continues_same_semantic_stream_and_retry_is_idempotent(tmp_path) -> None:
    store = ReferenceMemoryStore(tmp_path / "memory")
    provider = ScriptedProvider(
        {
            "E1": SemanticDecision("NEW", "theme", "first"),
            "E2": SemanticDecision("CONTINUE", "theme", "second"),
        }
    )
    first = SemanticCompiler(store, provider, lineage_id="lineage")
    first.process(raw("E1", "first", 0))
    store.close()

    reopened = ReferenceMemoryStore(tmp_path / "memory")
    second = SemanticCompiler(reopened, provider, lineage_id="lineage")
    result = second.process(raw("E2", "second", 1))
    duplicate = second.process(raw("E2", "second", 1))
    assert result.block_ids == duplicate.block_ids
    assert len(reopened.list_semantic_blocks(current_valid_only=False)) == 1
    assert reopened.get_checkpoint("lineage").open_block_id == result.block_ids[0]
    reopened.close()


def test_rule_provider_uses_input_semantics_not_experimental_ids(tmp_path) -> None:
    store = ReferenceMemoryStore(tmp_path / "memory")
    compiler = SemanticCompiler(store, provider=None, lineage_id="lineage")
    first = compiler.process(raw("arbitrary-id", "network discussion", 0, topic="network"))
    second = compiler.process(raw("another-id", "meal reflection", 1, topic="food", recap=True))
    assert first.block_ids != second.block_ids
    assert {block.content for block in store.list_semantic_blocks(current_valid_only=False)}
    store.close()
