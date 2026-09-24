from __future__ import annotations

from research.benchmarks.semantic_block_v0_1.contracts import (
    PredictionRecord,
    PublicRelation,
    PublicSemanticBlock,
    SourceSpan,
    VisibleCaseInput,
)
from research.benchmarks.semantic_block_v0_2.f8_evaluator import evaluate_f8_probe_v02
from research.benchmarks.semantic_block_v0_2.route_e import (
    _admit_linker_output,
    _gate_blocks,
    _screen_relations,
)


def _state(state_id: str, evidence_id: str, text: str) -> dict:
    return {
        "state_id": state_id,
        "predicate": "event",
        "source_spans": [{"evidence_id": evidence_id, "char_start": 0, "char_end": len(text), "text": text}],
    }


def _block(case_id: str, state_id: str, evidence_id: str, text: str, participants: dict[str, str] | None = None) -> PublicSemanticBlock:
    return PublicSemanticBlock(
        block_id=f"{case_id}_{state_id}",
        state_id=f"{case_id}_{state_id}",
        state_available_at="2026-05-02T12:00:00Z",
        canonical_content=text,
        predicate="event",
        kind="event",
        participants=participants or {},
        holder="user",
        utterer="user",
        attribution_mode="direct_speaker",
        polarity="positive",
        modality="asserted",
        epistemic_hedge="none",
        valid_time="UNKNOWN",
        time_precision="UNKNOWN",
        entity_status="unresolved",
        uncertainty="none",
        independent_support_count=1,
        source_spans=[SourceSpan(evidence_id, 0, len(text), text)],
        lineage_id=f"lineage-{state_id}",
        compiler_version="test",
    )


def _gold(case_id: str, states: list[dict], cutoff: str) -> dict:
    return {
        "case_id": case_id,
        "visibility": [{"cutoff": cutoff, "visible_state_ids": [s["state_id"] for s in states]}],
        "states": states,
    }


def test_f8_positive_uses_gold_edges_and_clips_graph_to_total_k() -> None:
    case_id = "V2-005"
    cutoff = "2026-05-20T00:00:00Z"
    texts = {
        "s1": ("V2-005-E1", "certificate expiry"),
        "s2": ("V2-005-E2", "routing loop saturated gateway"),
        "s3": ("V2-005-E3", "As a result API timed out"),
        "s4": ("V2-005-E4", "timeout caused checkout retries to fail"),
        "s5": ("V2-005-E5", "technician signed in before drill"),
    }
    blocks = [_block(case_id, key, eid, text) for key, (eid, text) in texts.items()]
    relations = [
        PublicRelation("CAUSE", "directed", f"{case_id}_s2", f"{case_id}_s3", "explicit_connective", SourceSpan("V2-005-E3", 0, 11, "As a result"), True),
        PublicRelation("CAUSE", "directed", f"{case_id}_s3", f"{case_id}_s4", "explicit_connective", SourceSpan("V2-005-E4", 8, 14, "caused"), True),
    ]
    prediction = PredictionRecord(case_id, cutoff, "E", "test", blocks, relations)
    states = [_state(key, eid, text) for key, (eid, text) in texts.items()]
    gold = _gold(case_id, states, cutoff)
    probe = {
        "probe_id": "positive",
        "case_id": case_id,
        "cutoff": cutoff,
        "k": 3,
        "gold_seed_state_key": "s2",
        "relevant_gold_endpoint_keys": ["s3", "s4"],
        "required_directed_cause_edge_pairs": [["s2", "s3"], ["s3", "s4"]],
        "forbidden_direct_shortcuts": [["s2", "s4"]],
    }
    evidence = [
        {"evidence_id": eid, "available_at": "2026-05-02T12:00:00Z", "content": text}
        for eid, text in texts.values()
    ]
    vectors = {block.state_id: [float(i == n) for i in range(5)] for n, block in enumerate(blocks)}

    result = evaluate_f8_probe_v02(prediction, gold, probe, vectors, evidence)

    assert result.extraction_path_pass
    assert result.retrieval_budget_pass
    graph_trace = next(trace for trace in result.traces if trace.method == "vector_plus_cause_graph")
    assert graph_trace.candidate_count == 3
    assert len(graph_trace.candidate_ids) == 3
    assert {"V2-005_s3", "V2-005_s4"} <= set(graph_trace.graph_proposed_ids)


def test_f8_negative_before_relation_never_becomes_a_graph_bridge() -> None:
    case_id = "V2-006"
    cutoff = "2026-05-20T00:00:00Z"
    texts = {
        "s1": ("V2-006-E1", "certificate expired before outage"),
        "s2": ("V2-006-E2", "API timed out after outage"),
        "s3": ("V2-006-E3", "Checkout retries failed later"),
        "s4": ("V2-006-E4", "technician signed in before drill"),
    }
    blocks = [_block(case_id, key, eid, text) for key, (eid, text) in texts.items()]
    before = PublicRelation(
        "BEFORE", "directed", f"{case_id}_s2", f"{case_id}_s3", "explicit_temporal",
        SourceSpan("V2-006-E3", 24, 29, "later"), False,
    )
    prediction = PredictionRecord(case_id, cutoff, "B", "test", blocks, [before])
    states = [_state(key, eid, text) for key, (eid, text) in texts.items()]
    gold = _gold(case_id, states, cutoff)
    probe = {
        "probe_id": "negative",
        "case_id": case_id,
        "cutoff": cutoff,
        "k": 3,
        "gold_seed_state_key": "s1",
        "relevant_gold_endpoint_keys": ["s2", "s3"],
        "required_directed_cause_edge_pairs": [],
        "forbidden_direct_shortcuts": [["s1", "s2"], ["s1", "s3"], ["s2", "s3"]],
    }
    evidence = [
        {"evidence_id": eid, "available_at": "2026-05-02T12:00:00Z", "content": text}
        for eid, text in texts.values()
    ]
    vectors = {block.state_id: [1.0, float(index)] for index, block in enumerate(blocks)}

    result = evaluate_f8_probe_v02(prediction, gold, probe, vectors, evidence)

    assert result.extraction_path_pass
    assert not result.before_bridge_detected
    assert not result.cause_paths
    graph_trace = next(trace for trace in result.traces if trace.method == "vector_plus_cause_graph")
    assert graph_trace.graph_proposed_ids == []
    assert graph_trace.candidate_count <= 3


def test_route_e_gates_preserve_semantic_fields_and_reject_missing_fields() -> None:
    content = "The API timed out."
    evidence = {
        "evidence_id": "E1",
        "content": content,
        "available_at": "2026-05-02T00:00:00Z",
        "occurred_at": "2026-05-01T00:00:00Z",
    }
    case_input = VisibleCaseInput(
        case_id="V2-X",
        family="V02",
        variant="single",
        split="v0.2",
        cutoff="2026-05-20T00:00:00Z",
        visible_evidence=[evidence],
        context_evidence=[],
        entity_registry={},
    )
    proposal = {
        "state_key": "s1",
        "block_key": "b1",
        "canonical_content": "The API timed out.",
        "predicate": "time_out",
        "kind": "event",
        "participants": {"system": "API"},
        "holder": "user",
        "utterer": "user",
        "attribution_mode": "direct_speaker",
        "polarity": "positive",
        "modality": "asserted",
        "epistemic_hedge": "none",
        "valid_time": "2026-05-01",
        "time_precision": "day",
        "entity_status": "unresolved",
        "uncertainty": "none",
        "source_spans": [{"evidence_id": "E1", "text": content}],
    }

    admitted, decisions, _ = _gate_blocks([proposal], case_input)
    rejected, bad_decisions, _ = _gate_blocks([{k: v for k, v in proposal.items() if k != "holder"}], case_input)

    assert len(admitted) == 1
    assert admitted[0].canonical_content == proposal["canonical_content"]
    assert admitted[0].predicate == proposal["predicate"]
    assert decisions[0].admitted
    assert not rejected
    assert "missing_required_field:holder" in bad_decisions[0].reasons


def test_route_e_candidate_generation_recovers_relation_omitted_by_b_first_pass() -> None:
    case_id = "V2-005"
    e1_text = "A routing loop saturated the gateway."
    e2_text = "As a result, the API timed out."
    evidence_map = {
        "V2-005-E2": {"evidence_id": "V2-005-E2", "content": e1_text, "available_at": "2026-05-02T12:00:00Z"},
        "V2-005-E3": {"evidence_id": "V2-005-E3", "content": e2_text, "available_at": "2026-05-02T12:00:00Z"},
    }
    s2 = _block(case_id, "s2", "V2-005-E2", e1_text)
    s3 = _block(case_id, "s3", "V2-005-E3", e2_text)

    # First pass emitted no relations (B omitted it)
    raw_relations: list[dict] = []
    candidates, decisions = _screen_relations(raw_relations, [], [s2, s3], evidence_map, {})

    assert len(candidates) == 1
    assert candidates[0]["type"] == "CAUSE"
    assert candidates[0]["source_state_key"] == "s2"
    assert candidates[0]["target_state_key"] == "s3"
    assert candidates[0]["basis"] == "explicit_connective"
    assert candidates[0]["cue_text"] == "As a result"
    assert candidates[0]["cue_span"]["evidence_id"] == "V2-005-E3"
    assert candidates[0]["cue_span"]["char_start"] == 0
    assert candidates[0]["cue_span"]["char_end"] == 11
    assert any(d.source_state_key == "s2" and d.target_state_key == "s3" and d.admitted for d in decisions)


def test_route_e_unsupported_pairs_not_generated() -> None:
    case_id = "V2-005"
    evidence_map = {
        "V2-005-E1": {"evidence_id": "V2-005-E1", "content": "The certificate expired before the outage, but the expiry did not cause it.", "available_at": "2026-05-02T12:00:00Z"},
        "V2-005-E2": {"evidence_id": "V2-005-E2", "content": "A technician had lunch.", "available_at": "2026-05-02T12:00:00Z"},
        "V2-005-E5": {"evidence_id": "V2-005-E5", "content": "The weather was sunny.", "available_at": "2026-05-02T12:00:00Z"},
    }
    s1 = _block(case_id, "s1", "V2-005-E1", "The certificate expired")
    s2 = _block(case_id, "s2", "V2-005-E2", "A technician had lunch")
    s5 = _block(case_id, "s5", "V2-005-E5", "The weather was sunny")

    # Negated cause in E1 ("did not cause it"), no connective between E1/E2 or E2/E5
    candidates, _decisions = _screen_relations([], [], [s1, s2, s5], evidence_map, {})
    assert candidates == []


def test_route_e_dangling_endpoints_impossible() -> None:
    case_id = "V2-X"
    evidence_map = {
        "E1": {"evidence_id": "E1", "content": "A routing loop saturated the gateway.", "available_at": "2026-05-02T12:00:00Z"},
        "E2": {"evidence_id": "E2", "content": "As a result, the API timed out.", "available_at": "2026-05-02T12:00:00Z"},
    }
    s1 = _block(case_id, "s1", "E1", "routing loop")
    s2 = _block(case_id, "s2", "E2", "API timed out")

    # Attempt raw proposal with non-admitted endpoint s99
    bad_proposal = {
        "type": "CAUSE",
        "source_state_key": "s1",
        "target_state_key": "s99",
        "basis": "explicit_connective",
        "cue_text": "As a result",
    }
    self_proposal = {
        "type": "CAUSE",
        "source_state_key": "s1",
        "target_state_key": "s1",
        "basis": "explicit_connective",
        "cue_text": "As a result",
    }
    candidates, decisions = _screen_relations([bad_proposal, self_proposal], [], [s1, s2], evidence_map, {})

    # s99 and s1->s1 are rejected
    assert not any(c["target_state_key"] == "s99" or c["source_state_key"] == "s99" for c in candidates)
    assert not any(c["source_state_key"] == c["target_state_key"] for c in candidates)
    assert any(d.source_state_key == "s1" and d.target_state_key == "s99" and not d.admitted and d.reason == "endpoint_not_admitted_or_self_link" for d in decisions)
    assert any(d.source_state_key == "s1" and d.target_state_key == "s1" and not d.admitted and d.reason == "endpoint_not_admitted_or_self_link" for d in decisions)

    # In linker admission, attempt to inject unadmitted endpoint s99
    admit_decisions: list = []
    admitted_rels = _admit_linker_output(
        [{"type": "CAUSE", "source_state_key": "s1", "target_state_key": "s99", "basis": "explicit_connective", "cue_text": "As a result"}],
        candidates,
        [s1, s2],
        case_id,
        admit_decisions,
    )
    assert admitted_rels == []
    assert any(d.target_state_key == "s99" and not d.admitted and d.reason == "linker_changed_or_added_candidate" for d in admit_decisions)


def test_route_e_before_never_enters_cause_traversal() -> None:
    case_id = "V2-006"
    evidence_map = {
        "E2": {"evidence_id": "E2", "content": "The API timed out after outage.", "available_at": "2026-05-02T12:00:00Z"},
        "E3": {"evidence_id": "E3", "content": "Checkout retries failed later.", "available_at": "2026-05-02T12:00:00Z"},
    }
    s2 = _block(case_id, "s2", "E2", "The API timed out")
    s3 = _block(case_id, "s3", "E3", "Checkout retries failed")

    candidates, _ = _screen_relations([], [], [s2, s3], evidence_map, {})
    assert any(c["type"] == "BEFORE" and c["source_state_key"] == "s2" and c["target_state_key"] == "s3" for c in candidates)

    before_cand = next(c for c in candidates if c["type"] == "BEFORE")
    decisions: list = []

    # Valid BEFORE admission must have traversal_allowed=False
    rels = _admit_linker_output(
        [{"type": "BEFORE", "source_state_key": "s2", "target_state_key": "s3", "basis": "explicit_temporal", "cue_text": before_cand["cue_text"]}],
        candidates,
        [s2, s3],
        case_id,
        decisions,
    )
    assert len(rels) == 1
    assert rels[0].type == "BEFORE"
    assert rels[0].traversal_allowed is False

    # Attempt to pass traversal_allowed=True on BEFORE must be rejected fail-closed
    bad_decisions: list = []
    bad_rels = _admit_linker_output(
        [{"type": "BEFORE", "source_state_key": "s2", "target_state_key": "s3", "basis": "explicit_temporal", "cue_text": before_cand["cue_text"], "traversal_allowed": True}],
        candidates,
        [s2, s3],
        case_id,
        bad_decisions,
    )
    assert bad_rels == []
    assert any(d.reason == "before_traversal_forbidden" for d in bad_decisions)


def test_route_e_no_direct_cause_shortcut_generated_from_chain() -> None:
    case_id = "V2-005"
    content = "A routing loop saturated the gateway. As a result, the API timed out. The timeout caused checkout retries to fail."
    evidence_map = {
        "E1": {"evidence_id": "E1", "content": content, "available_at": "2026-05-02T12:00:00Z"},
    }
    s2 = _block(case_id, "s2", "E1", "A routing loop saturated the gateway")
    s3 = _block(case_id, "s3", "E1", "the API timed out")
    s4 = _block(case_id, "s4", "E1", "checkout retries to fail")

    # Propose chain s2->s3 and s3->s4, PLUS direct shortcut s2->s4
    raw_relations = [
        {"type": "CAUSE", "source_state_key": "s2", "target_state_key": "s3", "basis": "explicit_connective", "cue_text": "As a result"},
        {"type": "CAUSE", "source_state_key": "s3", "target_state_key": "s4", "basis": "explicit_connective", "cue_text": "caused"},
        {"type": "CAUSE", "source_state_key": "s2", "target_state_key": "s4", "basis": "explicit_connective", "cue_text": "caused"},
    ]
    candidates, decisions = _screen_relations(raw_relations, [], [s2, s3, s4], evidence_map, {})

    cand_pairs = {(c["source_state_key"], c["target_state_key"]) for c in candidates if c["type"] == "CAUSE"}
    assert ("s2", "s3") in cand_pairs
    assert ("s3", "s4") in cand_pairs
    assert ("s2", "s4") not in cand_pairs
    assert any(d.source_state_key == "s2" and d.target_state_key == "s4" and d.reason == "transitive_shortcut_forbidden" for d in decisions)


def test_route_e_candidate_cap_enforced() -> None:
    case_id = "V2-CAP"
    evidence_map = {
        f"E{i}": {"evidence_id": f"E{i}", "content": f"Event {i} occurred.", "available_at": "2026-05-02T12:00:00Z"}
        for i in range(12)
    }
    blocks = [
        _block(case_id, f"s{i}", f"E{i}", f"Event {i}", participants={"entity": f"Event {i}"})
        for i in range(12)
    ]

    # Use registry to authorize SAME_ENTITY for 11 adjacent pairs
    registry = {f"Event {i}": "COMMON_ENTITY" for i in range(12)}
    candidates, decisions = _screen_relations([], [], blocks, evidence_map, registry)

    assert len(candidates) == 8
    assert any(d.reason == "candidate_pair_limit_exceeded" and not d.admitted for d in decisions)

