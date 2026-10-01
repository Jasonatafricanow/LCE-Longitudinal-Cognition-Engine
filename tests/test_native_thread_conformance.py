"""Path A behavioral contract using the actual MR-Mem product service."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from mr_mem import (
    MemoryCore,
    Scope,
    ScopeDomain,
    SemanticAdmissionService,
    SemanticMemoryCandidate,
    SourceRef,
    ThreadAutoUpdateService,
)

from lce.cognition.block_adapter import SemanticBlockMemoryAdapter
from lce.cognition.external import PrecomputedDraftInput, PrecomputedDraftIntake
from lce.core.projection import LceProjectionCore
from lce.reference_memory.composite import ProjectionSubstrate
from lce.reference_memory.contracts import (
    AuthorizedSelectedSupport,
    RawEvidence,
    SemanticBlock,
)
from lce.reference_memory.projection_state import SqliteProjectionStateStore

OCCURRED = datetime(2026, 1, 1, tzinfo=UTC)
KNOWN = datetime(2026, 10, 2, tzinfo=UTC)
SCOPE = Scope(ScopeDomain.USER, user_id="fixture-owner")


class NativeHost:
    def __init__(self):
        self.refs = {}

    def current_ref(self, scope, ref):
        return self.refs.get(ref.source_key) if scope == SCOPE else None

    def get_evidence(self, source_id):
        ref = self.refs[source_id]
        return RawEvidence(
            source_id, "Native metadata view; no raw copy.", ref.occurred_at,
            {"source": "native-host", "canonical": True, "session_id": ref.session_id},
            known_at=KNOWN,
        )

    def list_current_valid_evidence(self):
        return tuple(self.get_evidence(source_id) for source_id in self.refs)


class Clock:
    def now(self):
        return KNOWN


class ThreadHandoff:
    def __init__(self, projection):
        self.projection = projection
        self.fail_after_commit = True
        self.calls = 0
        self.intake = PrecomputedDraftIntake(
            memory_substrate=SemanticBlockMemoryAdapter(projection.memory),
            semantic_substrate=projection.memory, baseline_store=projection.baselines,
            draft_store=projection.worktrees, rejection_store=projection.rejections,
        )

    def compile(self, thread):
        self.calls += 1
        blocks = tuple(self.projection.memory.get_semantic_block(mid) for mid in thread.handoff_memory_ids)
        selected = tuple(AuthorizedSelectedSupport(block.block_id, block.state_id) for block in blocks)
        draft = PrecomputedDraftInput(
            region_id="mr-thread:" + thread.thread_id, content=thread.working_summary,
            supporting_memory_ids=thread.handoff_memory_ids,
            processing_input_id="handoff:" + ",".join(thread.handoff_memory_ids),
            selected_support=selected,
        )
        result = self.intake.stage_and_promote(draft)
        assert result.baseline.content == thread.working_summary
        assert result.baseline.selected_support == selected
        if self.fail_after_commit:
            self.fail_after_commit = False
            raise RuntimeError("crash after Baseline commit before Thread retirement")
        return result.baseline.baseline_id


def test_payment_thread_handoff_preserves_semantic_states_and_recovers_retirement(tmp_path: Path):
    host = NativeHost()
    semantic = MemoryCore(tmp_path / "semantic.sqlite")
    state = SqliteProjectionStateStore(tmp_path / "projection-state")
    substrate = ProjectionSubstrate(host, state)
    projection = LceProjectionCore(tmp_path / "lce", memory=substrate)
    admission = SemanticAdmissionService(
        store=semantic.canonical, sources=host, clock=Clock(), origin_runtime_id="fixture-host",
    )
    service = ThreadAutoUpdateService(canonical=semantic.canonical, product=semantic.products)
    events = []
    opened_id = None
    for index, (content, summary) in enumerate((
        ("User plans to prepare the down payment.", "Down payment is being prepared."),
        ("User has paid the down payment.", "Down payment paid; financing remains open."),
        ("User's loan approval is pending.", "Down payment paid; loan approval remains pending."),
    )):
        ref = SourceRef("native", f"session-{index}", str(index), OCCURRED + timedelta(days=index))
        host.refs[ref.source_key] = ref
        previous_id = events[-1].memory_id if events else None
        event = admission.admit(SemanticMemoryCandidate(
            semantic_id=f"payment-{index}", scope=SCOPE, content=content, source_refs=(ref,),
            compiler_version="reviewed-host-v1",
            attributes=(("holder", "user"), ("temporal_scope", "source time"),
                        ("thread_action", "track"), ("thread_question", "Will the home financing complete?"),
                        ("thread_summary", summary)),
            supports_memory_ids=(previous_id,) if previous_id else (),
        ))
        # Use independent accepted progress without superseding current Thread support.
        # The paid state relates to its earlier plan; past intent remains valid history.
        if previous_id:
            assert event.supports_memory_ids == (previous_id,)
        events.append(event)
        substrate.put_semantic_block(SemanticBlock(
            block_id=event.memory_id, content=event.content,
            raw_evidence_ids=(ref.source_key,), occurred_start=ref.occurred_at,
            occurred_end=ref.occurred_at, compiler_version="reviewed-host-v1", lineage_id="host",
            derived_known_at=event.known_at,
            metadata={"attributes": dict(event.attributes), "supports": event.supports_memory_ids},
        ))
        changed = service.apply(scope=SCOPE, accepted_events=(event,), at=KNOWN)
        if opened_id is None:
            opened_id = changed[0].thread_id
        assert changed[0].thread_id == opened_id
        assert len(semantic.products.list_threads(SCOPE)) == 1
    thread = semantic.products.get_thread(opened_id)
    assert thread.mature
    assert thread.working_summary == "Down payment paid; loan approval remains pending."
    handoff = ThreadHandoff(projection)
    service = ThreadAutoUpdateService(
        canonical=semantic.canonical, product=semantic.products, projection_compiler=handoff,
    )
    with pytest.raises(RuntimeError, match="after Baseline commit"):
        service.apply(scope=SCOPE, accepted_events=(), at=KNOWN)
    assert semantic.products.get_thread(opened_id) is not None
    service.apply(scope=SCOPE, accepted_events=(), at=KNOWN)
    assert semantic.products.get_thread(opened_id) is None
    assert len(projection.query(None)) == 1
    history = projection.baselines.get_history("mr-thread:" + opened_id)
    assert len(history.revisions) == 1
    assert history.revisions[0].selected_support
    semantic.close()
    semantic = MemoryCore(tmp_path / "semantic.sqlite")
    service = ThreadAutoUpdateService(
        canonical=semantic.canonical, product=semantic.products, projection_compiler=handoff,
    )
    service.apply(scope=SCOPE, accepted_events=tuple(events), at=KNOWN)
    assert semantic.products.get_thread(opened_id) is None
    assert len(projection.baselines.get_history("mr-thread:" + opened_id).revisions) == 1
    semantic.close()
    projection.close()
    substrate.close()
