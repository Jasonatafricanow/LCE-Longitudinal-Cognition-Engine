"""Construction record for the Issue #19 frozen synthetic benchmark.

Research data only. Do not run this after the freeze to change the gold in place.
The final JSONL files and their hashes, not this script's current output, are the
execution inputs. Any correction requires a new benchmark version.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_OCCURRED = "2026-04-02T12:00:00Z"
DEFAULT_AVAILABLE = "2026-04-03T12:00:00Z"
DEFAULT_CUTOFF = "2026-04-20T00:00:00Z"
HELDOUT_NEGATIVE_FAMILIES = {
    "B03", "B04", "B05", "B07", "B08", "B11",
    "B13", "B14", "B15", "B16", "B17", "B18",
}
CASES: list[dict[str, object]] = []
GOLD: list[dict[str, object]] = []


def ev(
    text: str,
    *,
    occurred: str = DEFAULT_OCCURRED,
    available: str = DEFAULT_AVAILABLE,
    thread: str = "diary-cedar",
    speaker: str = "user",
    source: str = "synthetic-diary",
) -> dict[str, str]:
    return {
        "content": text,
        "occurred_at": occurred,
        "available_at": available,
        "thread_id": thread,
        "speaker": speaker,
        "source_id": source,
    }


def st(
    key: str,
    content: str,
    predicate: str,
    kind: str,
    roles: dict[str, str],
    *,
    sources: tuple[int, ...] = (0,),
    snippets: dict[int, str] | None = None,
    holder: str = "user",
    utterer: str = "user",
    attribution: str = "direct_speaker",
    polarity: str = "positive",
    modality: str = "asserted",
    hedge: str = "none",
    valid_time: str = "2026-04-02",
    time_precision: str = "day",
    entity_status: str = "resolved",
    uncertainty: str = "none",
    block_key: str | None = None,
    independent_support_count: int = 1,
) -> dict[str, object]:
    return {
        "state_key": key,
        "block_key": block_key or key,
        "canonical_content": content,
        "predicate": predicate,
        "kind": kind,
        "participants": roles,
        "sources": sources,
        "snippets": snippets or {},
        "holder": holder,
        "utterer": utterer,
        "attribution_mode": attribution,
        "polarity": polarity,
        "modality": modality,
        "epistemic_hedge": hedge,
        "valid_time": valid_time,
        "time_precision": time_precision,
        "entity_status": entity_status,
        "uncertainty": uncertainty,
        "independent_support_count": independent_support_count,
    }


def add(
    family: str,
    variant: str,
    evidence: list[dict[str, str]],
    states: list[dict[str, object]],
    *,
    relations: list[tuple[str, str, str, int | None, str | None, str]] | None = None,
    cutoffs: list[str] | None = None,
    context_indices: tuple[int, ...] = (),
    registry: dict[str, str] | None = None,
    forbidden: list[str] | None = None,
    rationale: str,
) -> None:
    code = {"canonical": "C", "paraphrase": "P", "negative": "N"}[variant]
    case_id = f"{family}-{code}"
    split = "heldout" if variant == "negative" and family in HELDOUT_NEGATIVE_FAMILIES else "dev"
    evidence = [{"evidence_id": f"{case_id}-E{i + 1}", **item} for i, item in enumerate(evidence)]
    case = {
        "case_id": case_id,
        "family": family,
        "variant": variant,
        "split": split,
        "raw_evidence": evidence,
        "requested_cutoffs": cutoffs or [DEFAULT_CUTOFF],
        "context_evidence_ids": [evidence[i]["evidence_id"] for i in context_indices],
        "entity_registry": registry or {},
    }
    out_states: list[dict[str, object]] = []
    for item in states:
        indices = item.pop("sources")
        snippets = item.pop("snippets")
        spans = []
        for idx in indices:
            raw = evidence[idx]
            snippet = snippets.get(idx, raw["content"])
            pos = raw["content"].find(snippet)
            if pos < 0 or not snippet:
                raise ValueError(f"{case_id} missing supporting span {snippet!r}")
            spans.append({
                "evidence_id": raw["evidence_id"],
                "char_start": pos,
                "char_end": pos + len(snippet),
                "text": snippet,
            })
        available_at = max(evidence[idx]["available_at"] for idx in indices)
        out_states.append({**item, "available_at": available_at, "source_spans": spans})
    out_relations = []
    for rel_type, source, target, idx, cue, basis in relations or []:
        cue_span = None
        if idx is not None and cue is not None:
            raw = evidence[idx]
            pos = raw["content"].find(cue)
            if pos < 0:
                raise ValueError(f"{case_id} missing relation cue {cue!r}")
            cue_span = {"evidence_id": raw["evidence_id"], "char_start": pos,
                        "char_end": pos + len(cue), "text": cue}
        out_relations.append({"type": rel_type, "source_state_key": source,
                              "target_state_key": target, "basis": basis,
                              "cue_span": cue_span, "traversal": rel_type in {"CAUSE", "SAME_ENTITY"}})
    visibility = []
    for cutoff in case["requested_cutoffs"]:
        latest: dict[str, str] = {}
        for state in out_states:
            if state["available_at"] <= cutoff:
                latest[str(state["block_key"])] = str(state["state_key"])
        visibility.append({"cutoff": cutoff, "visible_state_keys": list(latest.values())})
    gold = {
        "case_id": case_id,
        "states": out_states,
        "relations": out_relations,
        "visibility": visibility,
        "forbidden_case_outputs": forbidden or [],
        "rationale": rationale,
        "annotation_status": "single_author_frozen_unadjudicated",
    }
    CASES.append(case)
    GOLD.append(gold)


# B01 — asserted event versus intention.
add("B01", "canonical", [ev("On 2026-04-02 I joined Project Cedar.")],
    [st("s1", "The user joined Project Cedar on 2026-04-02.", "join", "event",
        {"actor": "user", "project": "Cedar"})], rationale="Single asserted event.")
add("B01", "paraphrase", [ev("I became a member of Project Cedar on April 2, 2026.")],
    [st("s1", "The user joined Project Cedar on 2026-04-02.", "join", "event",
        {"actor": "user", "project": "Cedar"})], rationale="Formatting/paraphrase preserves event meaning.")
add("B01", "negative", [ev("I plan to join Project Cedar on April 2, 2027.")],
    [st("s1", "The user plans to join Project Cedar on 2027-04-02.", "join", "event",
        {"actor": "user", "project": "Cedar"}, modality="intended", valid_time="2027-04-02")],
    forbidden=["joined_as_occurred"], rationale="Future intention is not an occurred join.")

# B02 — one internally causal account, versus post-hoc sequence.
add("B02", "canonical", [ev("Because the queue lost quorum, the API returned 503.")],
    [st("s1", "Queue quorum loss caused the API to return 503.", "cause_api_503", "event",
        {"cause": "queue quorum loss", "effect": "API 503"})],
    rationale="One account preserves its internal causal connective without duplicate child blocks.")
add("B02", "paraphrase", [ev("The API returned 503 because the queue had lost quorum.")],
    [st("s1", "Queue quorum loss caused the API to return 503.", "cause_api_503", "event",
        {"cause": "queue quorum loss", "effect": "API 503"})],
    rationale="Clause order changes but semantic account and direction do not.")
add("B02", "negative", [ev("The queue lost quorum. Later, the API returned 503.")],
    [st("s1", "The queue lost quorum.", "lose_quorum", "event", {"subject": "queue"},
        snippets={0: "The queue lost quorum."}),
     st("s2", "The API returned 503 later.", "return_503", "event", {"subject": "API"},
        snippets={0: "Later, the API returned 503."})],
    forbidden=["CAUSE"], rationale="Temporal order alone does not warrant a causal account.")

# B03 — independent cross-sentence events, linked only by grounded cues.
add("B03", "canonical", [ev("The storage cluster lost quorum."),
    ev("As a result, the API gateway returned 503."), ev("Therefore the checkout failed.")],
    [st("s1", "The storage cluster lost quorum.", "lose_quorum", "event", {"subject": "storage cluster"}),
     st("s2", "The API gateway returned 503.", "return_503", "event", {"subject": "API gateway"}, sources=(1,)),
     st("s3", "The checkout failed.", "fail", "event", {"subject": "checkout"}, sources=(2,))],
    relations=[("CAUSE", "s1", "s2", 1, "As a result", "explicit_connective"),
               ("CAUSE", "s2", "s3", 2, "Therefore", "explicit_connective")],
    forbidden=["CAUSE_s1_s3_direct"],
    rationale="Two cross-sentence CAUSE edges must compose as a path, not a new direct edge.")
add("B03", "paraphrase", [ev("The storage cluster no longer had quorum."),
    ev("Consequently, the API gateway answered with 503."), ev("For that reason, checkout failed.")],
    [st("s1", "The storage cluster lost quorum.", "lose_quorum", "event", {"subject": "storage cluster"}),
     st("s2", "The API gateway returned 503.", "return_503", "event", {"subject": "API gateway"}, sources=(1,)),
     st("s3", "The checkout failed.", "fail", "event", {"subject": "checkout"}, sources=(2,))],
    relations=[("CAUSE", "s1", "s2", 1, "Consequently", "explicit_connective"),
               ("CAUSE", "s2", "s3", 2, "For that reason", "explicit_connective")],
    forbidden=["CAUSE_s1_s3_direct"], rationale="Paraphrased cross-sentence causal path.")
add("B03", "negative", [ev("The storage cluster lost quorum."),
    ev("Later, the API gateway returned 503."), ev("After that, checkout failed.")],
    [st("s1", "The storage cluster lost quorum.", "lose_quorum", "event", {"subject": "storage cluster"}),
     st("s2", "The API gateway returned 503.", "return_503", "event", {"subject": "API gateway"}, sources=(1,)),
     st("s3", "The checkout failed.", "fail", "event", {"subject": "checkout"}, sources=(2,))],
    forbidden=["CAUSE"], rationale="Three ordered events are not a causal chain without causal support.")

# B04 — quotation is not user belief; explicit agreement changes the answer.
add("B04", "canonical", [ev('Mira said, "The migration is safe." I have not verified it.')],
    [st("s1", "Mira said the migration is safe.", "be_safe", "proposition",
        {"subject": "migration"}, snippets={0: 'Mira said, "The migration is safe."'},
        holder="Mira", utterer="Mira", attribution="direct_quote"),
     st("s2", "The user has not verified the migration's safety.", "verify_safety", "attitude",
        {"actor": "user", "subject": "migration"}, snippets={0: "I have not verified it."},
        polarity="negative")],
    forbidden=["user_believes_migration_safe"], rationale="Quoted claim and author stance have separate holders.")
add("B04", "paraphrase", [ev('According to Mira, "the migration is safe"; I cannot confirm that.')],
    [st("s1", "Mira said the migration is safe.", "be_safe", "proposition",
        {"subject": "migration"}, snippets={0: 'According to Mira, "the migration is safe"'},
        holder="Mira", utterer="Mira", attribution="direct_quote"),
     st("s2", "The user cannot confirm migration safety.", "confirm_safety", "attitude",
        {"actor": "user", "subject": "migration"}, snippets={0: "I cannot confirm that."}, polarity="negative")],
    forbidden=["user_believes_migration_safe"], rationale="Paraphrased attribution with unchanged holder split.")
add("B04", "negative", [ev('Mira said, "The migration is safe." I agree with her.')],
    [st("s1", "Mira said the migration is safe.", "be_safe", "proposition",
        {"subject": "migration"}, snippets={0: 'Mira said, "The migration is safe."'},
        holder="Mira", utterer="Mira", attribution="direct_quote"),
     st("s2", "The user agrees that the migration is safe.", "agree_safe", "attitude",
        {"holder": "user", "subject": "migration"}, snippets={0: "I agree with her."})],
    rationale="Explicit user agreement allows a separate user-held stance, not silent quote promotion.")

# B05 — possible versus occurred.
add("B05", "canonical", [ev("I might move to Lisbon next spring, but I have not decided.")],
    [st("s1", "The user might move to Lisbon next spring and has not decided.", "move", "event",
        {"actor": "user", "destination": "Lisbon"}, modality="possible", hedge="uncertain",
        valid_time="2027-spring", time_precision="season", uncertainty="decision_unresolved")],
    forbidden=["move_occurred"], rationale="Possibility and decision uncertainty remain distinct from occurrence.")
add("B05", "paraphrase", [ev("Perhaps I will relocate to Lisbon in spring 2027; no decision yet.")],
    [st("s1", "The user might move to Lisbon next spring and has not decided.", "move", "event",
        {"actor": "user", "destination": "Lisbon"}, modality="possible", hedge="uncertain",
        valid_time="2027-spring", time_precision="season", uncertainty="decision_unresolved")],
    forbidden=["move_occurred"], rationale="Paraphrase preserves possibility and lack of commitment.")
add("B05", "negative", [ev("I moved to Lisbon on 2026-04-02.")],
    [st("s1", "The user moved to Lisbon on 2026-04-02.", "move", "event",
        {"actor": "user", "destination": "Lisbon"})],
    rationale="Actual occurrence must not be flattened into possible future move.")

# B06 — distinct time-scoped states, no precompiled revision.
add("B06", "canonical", [ev("In January 2026 I worked on Atlas. In March 2026 I worked on Cedar.")],
    [st("s1", "The user worked on Atlas in January 2026.", "work_on", "state",
        {"actor": "user", "project": "Atlas"}, snippets={0: "In January 2026 I worked on Atlas."},
        valid_time="2026-01", time_precision="month"),
     st("s2", "The user worked on Cedar in March 2026.", "work_on", "state",
        {"actor": "user", "project": "Cedar"}, snippets={0: "In March 2026 I worked on Cedar."},
        valid_time="2026-03", time_precision="month")],
    forbidden=["REVISION", "INCOMPATIBLE"], rationale="Different times do not imply cognitive revision.")
add("B06", "paraphrase", [ev("My January 2026 work was Atlas; by March 2026 my work was Cedar.")],
    [st("s1", "The user worked on Atlas in January 2026.", "work_on", "state",
        {"actor": "user", "project": "Atlas"}, snippets={0: "My January 2026 work was Atlas"},
        valid_time="2026-01", time_precision="month"),
     st("s2", "The user worked on Cedar in March 2026.", "work_on", "state",
        {"actor": "user", "project": "Cedar"}, snippets={0: "by March 2026 my work was Cedar"},
        valid_time="2026-03", time_precision="month")],
    forbidden=["REVISION", "INCOMPATIBLE"], rationale="Paraphrase preserves separate temporal scopes.")
add("B06", "negative", [ev("In January 2026 I did not work on Atlas. In March 2026 I worked on Cedar.")],
    [st("s1", "The user did not work on Atlas in January 2026.", "work_on", "state",
        {"actor": "user", "project": "Atlas"}, snippets={0: "In January 2026 I did not work on Atlas."},
        polarity="negative", valid_time="2026-01", time_precision="month"),
     st("s2", "The user worked on Cedar in March 2026.", "work_on", "state",
        {"actor": "user", "project": "Cedar"}, snippets={0: "In March 2026 I worked on Cedar."},
        valid_time="2026-03", time_precision="month")],
    forbidden=["REVISION", "INCOMPATIBLE"], rationale="Negation and non-overlapping times remain local facts.")

# B07 — bounded pronoun resolution, with an ambiguous negative.
add("B07", "canonical", [ev("Mira owns Cedar.", occurred="2026-04-08T12:00:00Z", available="2026-04-08T13:00:00Z"),
    ev("She restarted it yesterday.", occurred="2026-04-10T12:00:00Z", available="2026-04-10T13:00:00Z")],
    [st("s1", "Mira owns Cedar.", "own", "state", {"owner": "Mira", "object": "Cedar"},
        valid_time="2026-04-08"),
     st("s2", "Mira restarted Cedar on 2026-04-09.", "restart", "event",
        {"actor": "Mira", "object": "Cedar"}, sources=(1,), valid_time="2026-04-09")],
    context_indices=(0,), rationale="Prior cutoff-visible identity and relative-time anchor resolve pronouns.")
add("B07", "paraphrase", [ev("Mira manages Cedar.", occurred="2026-04-08T12:00:00Z", available="2026-04-08T13:00:00Z"),
    ev("Yesterday she rebooted that project.", occurred="2026-04-10T12:00:00Z", available="2026-04-10T13:00:00Z")],
    [st("s1", "Mira manages Cedar.", "manage", "state", {"manager": "Mira", "object": "Cedar"},
        valid_time="2026-04-08"),
     st("s2", "Mira restarted Cedar on 2026-04-09.", "restart", "event",
        {"actor": "Mira", "object": "Cedar"}, sources=(1,), valid_time="2026-04-09")],
    context_indices=(0,), rationale="Paraphrase with same bounded coreference target.")
add("B07", "negative", [ev("Mira and Lila manage Cedar.", occurred="2026-04-08T12:00:00Z", available="2026-04-08T13:00:00Z"),
    ev("She restarted it yesterday.", occurred="2026-04-10T12:00:00Z", available="2026-04-10T13:00:00Z")],
    [st("s1", "Mira and Lila manage Cedar.", "manage", "state",
        {"managers": "Mira,Lila", "object": "Cedar"}, valid_time="2026-04-08"),
     st("s2", "An unresolved female referent restarted Cedar on 2026-04-09.", "restart", "event",
        {"actor": "UNKNOWN", "object": "Cedar"}, sources=(1,), valid_time="2026-04-09",
        entity_status="unresolved", uncertainty="actor_ambiguous")],
    context_indices=(0,), forbidden=["actor_Mira", "actor_Lila"],
    rationale="Two candidate women make 'she' unresolved; no guessed actor.")

# B08 — cross-context identity requires authorized registry, not text similarity.
add("B08", "canonical", [ev("The Cedar queue is stalled.", thread="ops-A"),
    ev("Our task broker for Cedar recovered.", thread="ops-B")],
    [st("s1", "Cedar task broker is stalled.", "stall", "state", {"subject": "CedarBroker-1"}),
     st("s2", "Cedar task broker recovered.", "recover", "event",
        {"subject": "CedarBroker-1"}, sources=(1,))],
    relations=[("SAME_ENTITY", "s1", "s2", None, None, "authorized_registry")],
    registry={"Cedar queue": "CedarBroker-1", "task broker for Cedar": "CedarBroker-1"},
    rationale="Authorized identity joins different wording across threads.")
add("B08", "paraphrase", [ev("Cedar's work queue stopped.", thread="ops-A"),
    ev("The Cedar job dispatcher resumed operation.", thread="ops-B")],
    [st("s1", "Cedar task broker is stalled.", "stall", "state", {"subject": "CedarBroker-1"}),
     st("s2", "Cedar task broker recovered.", "recover", "event",
        {"subject": "CedarBroker-1"}, sources=(1,))],
    relations=[("SAME_ENTITY", "s1", "s2", None, None, "authorized_registry")],
    registry={"Cedar work queue": "CedarBroker-1", "Cedar job dispatcher": "CedarBroker-1"},
    rationale="Paraphrase has low lexical overlap but explicit registry identity.")
add("B08", "negative", [ev("Cedar's email queue stopped.", thread="ops-A"),
    ev("Cedar's billing task broker recovered.", thread="ops-B")],
    [st("s1", "Cedar email queue stopped.", "stop", "state", {"subject": "CedarEmail-1"}),
     st("s2", "Cedar billing broker recovered.", "recover", "event",
        {"subject": "CedarBilling-1"}, sources=(1,))],
    registry={"Cedar email queue": "CedarEmail-1", "Cedar billing task broker": "CedarBilling-1"},
    forbidden=["SAME_ENTITY"], rationale="Similar project name but registry identifies distinct systems.")

# B09 — recap attaches provenance without multiplying independent support.
add("B09", "canonical", [ev("I postponed the launch.", occurred="2026-04-02T12:00:00Z", available="2026-04-02T13:00:00Z"),
    ev("As I said, the launch is postponed.", occurred="2026-04-05T12:00:00Z", available="2026-04-05T13:00:00Z")],
    [st("v1", "The user postponed the launch.", "postpone", "event", {"actor": "user", "object": "launch"},
        block_key="b1"),
     st("v2", "The user postponed the launch.", "postpone", "event", {"actor": "user", "object": "launch"},
        sources=(0, 1), block_key="b1", independent_support_count=1)],
    cutoffs=["2026-04-03T00:00:00Z", DEFAULT_CUTOFF],
    rationale="Recap can extend provenance but is not independent corroboration.")
add("B09", "paraphrase", [ev("I delayed the launch.", occurred="2026-04-02T12:00:00Z", available="2026-04-02T13:00:00Z"),
    ev("To repeat myself, launch is delayed.", occurred="2026-04-05T12:00:00Z", available="2026-04-05T13:00:00Z")],
    [st("v1", "The user postponed the launch.", "postpone", "event", {"actor": "user", "object": "launch"}, block_key="b1"),
     st("v2", "The user postponed the launch.", "postpone", "event", {"actor": "user", "object": "launch"},
        sources=(0, 1), block_key="b1", independent_support_count=1)],
    cutoffs=["2026-04-03T00:00:00Z", DEFAULT_CUTOFF], rationale="Paraphrased recap stays one account.")
add("B09", "negative", [ev("I postponed the launch.", occurred="2026-04-02T12:00:00Z", available="2026-04-02T13:00:00Z"),
    ev("As I said, the launch is postponed. I canceled the demo.", occurred="2026-04-05T12:00:00Z", available="2026-04-05T13:00:00Z")],
    [st("v1", "The user postponed the launch.", "postpone", "event", {"actor": "user", "object": "launch"}, block_key="b1"),
     st("v2", "The user postponed the launch.", "postpone", "event", {"actor": "user", "object": "launch"},
        sources=(0, 1), snippets={1: "As I said, the launch is postponed."}, block_key="b1"),
     st("s2", "The user canceled the demo.", "cancel", "event", {"actor": "user", "object": "demo"},
        sources=(1,), snippets={1: "I canceled the demo."})],
    cutoffs=["2026-04-03T00:00:00Z", DEFAULT_CUTOFF],
    rationale="A recap plus new independent event needs two final accounts.")

# B10 — unrelated topic shift versus one coordinated account.
add("B10", "canonical", [ev("Cedar's queue failed. Separately, I booked a dentist visit.")],
    [st("s1", "Cedar's queue failed.", "fail", "event", {"subject": "Cedar queue"},
        snippets={0: "Cedar's queue failed."}),
     st("s2", "The user booked a dentist visit.", "book", "event",
        {"actor": "user", "object": "dentist visit"}, snippets={0: "I booked a dentist visit."})],
    forbidden=["CAUSE", "SAME_ENTITY"], rationale="Independent topics split, without a link.")
add("B10", "paraphrase", [ev("The Cedar queue failed; on an unrelated note, I scheduled a dental appointment.")],
    [st("s1", "Cedar's queue failed.", "fail", "event", {"subject": "Cedar queue"},
        snippets={0: "The Cedar queue failed"}),
     st("s2", "The user booked a dentist visit.", "book", "event",
        {"actor": "user", "object": "dentist visit"},
        snippets={0: "I scheduled a dental appointment."})],
    forbidden=["CAUSE", "SAME_ENTITY"], rationale="Paraphrase keeps unrelated account boundary.")
add("B10", "negative", [ev("Cedar's queue and retry worker failed together.")],
    [st("s1", "Cedar's queue and retry worker failed together.", "fail_together", "event",
        {"subjects": "Cedar queue,retry worker"})],
    rationale="One coordinated incident should not be split solely for two participants.")

# B11 — two independent meanings in one evidence item versus a restatement.
add("B11", "canonical", [ev("Mira approved Cedar. I declined Atlas.")],
    [st("s1", "Mira approved Cedar.", "approve", "event",
        {"actor": "Mira", "project": "Cedar"}, snippets={0: "Mira approved Cedar."},
        holder="Mira", utterer="user", attribution="indirect_report"),
     st("s2", "The user declined Atlas.", "decline", "event",
        {"actor": "user", "project": "Atlas"}, snippets={0: "I declined Atlas."})],
    rationale="Different holders, predicates, and projects yield separate blocks.")
add("B11", "paraphrase", [ev("Cedar received Mira's approval. As for Atlas, I said no.")],
    [st("s1", "Mira approved Cedar.", "approve", "event",
        {"actor": "Mira", "project": "Cedar"}, snippets={0: "Cedar received Mira's approval."},
        holder="Mira", utterer="user", attribution="indirect_report"),
     st("s2", "The user declined Atlas.", "decline", "event",
        {"actor": "user", "project": "Atlas"}, snippets={0: "As for Atlas, I said no."})],
    rationale="Paraphrase keeps the two reusable accounts distinct.")
add("B11", "negative", [ev("Mira approved Cedar, granting it permission to proceed.")],
    [st("s1", "Mira approved Cedar to proceed.", "approve", "event",
        {"actor": "Mira", "project": "Cedar"}, holder="Mira", utterer="user",
        attribution="indirect_report")],
    rationale="Appositional restatement is one approval account, not two blocks.")

# B12 — same continuing state versus changed world state.
add("B12", "canonical", [ev("The Cedar queue stalled.", occurred="2026-04-02T12:00:00Z", available="2026-04-02T13:00:00Z"),
    ev("It is still stalled; no restart yet.", occurred="2026-04-05T12:00:00Z", available="2026-04-05T13:00:00Z")],
    [st("v1", "The Cedar queue is stalled.", "stall", "state", {"subject": "Cedar queue"}, block_key="b1"),
     st("v2", "The Cedar queue remains stalled through 2026-04-05.", "stall", "state",
        {"subject": "Cedar queue"}, sources=(0, 1), block_key="b1",
        valid_time="2026-04-02..2026-04-05")],
    cutoffs=["2026-04-03T00:00:00Z", DEFAULT_CUTOFF],
    rationale="A continuing state may update the same block with a new immutable state.")
add("B12", "paraphrase", [ev("Cedar's queue stopped processing.", occurred="2026-04-02T12:00:00Z", available="2026-04-02T13:00:00Z"),
    ev("That queue remains stopped as of today.", occurred="2026-04-05T12:00:00Z", available="2026-04-05T13:00:00Z")],
    [st("v1", "The Cedar queue is stalled.", "stall", "state", {"subject": "Cedar queue"}, block_key="b1"),
     st("v2", "The Cedar queue remains stalled through 2026-04-05.", "stall", "state",
        {"subject": "Cedar queue"}, sources=(0, 1), block_key="b1",
        valid_time="2026-04-02..2026-04-05")],
    cutoffs=["2026-04-03T00:00:00Z", DEFAULT_CUTOFF], rationale="Paraphrased continuation, same account.")
add("B12", "negative", [ev("The Cedar queue stalled.", occurred="2026-04-02T12:00:00Z", available="2026-04-02T13:00:00Z"),
    ev("The Cedar queue recovered.", occurred="2026-04-05T12:00:00Z", available="2026-04-05T13:00:00Z")],
    [st("s1", "The Cedar queue stalled on 2026-04-02.", "stall", "state",
        {"subject": "Cedar queue"}),
     st("s2", "The Cedar queue recovered on 2026-04-05.", "recover", "event",
        {"subject": "Cedar queue"}, sources=(1,), valid_time="2026-04-05")],
    cutoffs=["2026-04-03T00:00:00Z", DEFAULT_CUTOFF], forbidden=["REVISION"],
    rationale="A changed world state is a new block, not an interpretive revision.")

# B13 — lexical collision versus genuine same referent.
add("B13", "canonical", [ev("Cedar queue lost quorum."), ev("The cedar trees lost leaves.")],
    [st("s1", "Cedar queue lost quorum.", "lose_quorum", "event", {"subject": "Cedar queue"}),
     st("s2", "Cedar trees lost leaves.", "lose_leaves", "event",
        {"subject": "cedar trees"}, sources=(1,))],
    forbidden=["SAME_ENTITY"], rationale="Shared token Cedar does not make queue and trees identical.")
add("B13", "paraphrase", [ev("The Cedar message queue lost quorum."), ev("Several cedar trees shed foliage.")],
    [st("s1", "Cedar queue lost quorum.", "lose_quorum", "event", {"subject": "Cedar queue"}),
     st("s2", "Cedar trees lost leaves.", "lose_leaves", "event",
        {"subject": "cedar trees"}, sources=(1,))],
    forbidden=["SAME_ENTITY"], rationale="Paraphrase keeps lexical collision negative.")
add("B13", "negative", [ev("The Cedar queue lost quorum."), ev("The Cedar queue recovered.")],
    [st("s1", "The Cedar queue lost quorum.", "lose_quorum", "event", {"subject": "CedarBroker-1"}),
     st("s2", "The Cedar queue recovered.", "recover", "event",
        {"subject": "CedarBroker-1"}, sources=(1,))],
    relations=[("SAME_ENTITY", "s1", "s2", None, None, "authorized_registry")],
    registry={"Cedar queue": "CedarBroker-1"},
    rationale="Same lexical form plus authorized identity really is one referent, not one event.")

# B14 — low-similarity identity is supported only by bounded context.
add("B14", "canonical", [ev("The task broker for Cedar failed.", thread="ops-C"),
    ev("That scheduling service recovered.", thread="ops-C")],
    [st("s1", "Cedar task broker failed.", "fail", "event", {"subject": "CedarBroker-1"}),
     st("s2", "Cedar task broker recovered.", "recover", "event",
        {"subject": "CedarBroker-1"}, sources=(1,))],
    context_indices=(0,), relations=[("SAME_ENTITY", "s1", "s2", None, None, "authorized_registry")],
    registry={"task broker for Cedar": "CedarBroker-1", "scheduling service": "CedarBroker-1"},
    rationale="Registry plus bounded thread context resolves a low-overlap referent.")
add("B14", "paraphrase", [ev("Cedar's job dispatcher went down.", thread="ops-C"),
    ev("That scheduler came back online.", thread="ops-C")],
    [st("s1", "Cedar task broker failed.", "fail", "event", {"subject": "CedarBroker-1"}),
     st("s2", "Cedar task broker recovered.", "recover", "event",
        {"subject": "CedarBroker-1"}, sources=(1,))],
    context_indices=(0,), relations=[("SAME_ENTITY", "s1", "s2", None, None, "authorized_registry")],
    registry={"Cedar job dispatcher": "CedarBroker-1", "scheduler": "CedarBroker-1"},
    rationale="Paraphrased identity uses explicit registry evidence.")
add("B14", "negative", [ev("The task broker for Cedar failed.", thread="ops-C"),
    ev("A scheduling service recovered.", thread="ops-D")],
    [st("s1", "Cedar task broker failed.", "fail", "event", {"subject": "CedarBroker-1"}),
     st("s2", "An unidentified scheduling service recovered.", "recover", "event",
        {"subject": "UNKNOWN"}, sources=(1,), entity_status="unresolved",
        uncertainty="referent_unresolved")],
    registry={"task broker for Cedar": "CedarBroker-1"},
    forbidden=["SAME_ENTITY"], rationale="Different thread and no registry mapping leave identity unresolved.")

# B15 — quoted disagreement and explicit agreement.
add("B15", "canonical", [ev('Mira said, "Cedar is ready." I disagree; its checkout still fails.')],
    [st("s1", "Mira claims Cedar is ready.", "be_ready", "proposition",
        {"subject": "Cedar"}, snippets={0: 'Mira said, "Cedar is ready."'},
        holder="Mira", utterer="Mira", attribution="direct_quote"),
     st("s2", "The user says Cedar checkout still fails.", "fail", "state",
        {"subject": "Cedar checkout"}, snippets={0: "I disagree; its checkout still fails."})],
    forbidden=["user_believes_Cedar_ready", "REVISION"],
    rationale="Quote and explicit disagreement are different holder-scoped claims.")
add("B15", "paraphrase", [ev('Mira called Cedar ready. I do not agree because checkout still fails.')],
    [st("s1", "Mira claims Cedar is ready.", "be_ready", "proposition",
        {"subject": "Cedar"}, snippets={0: "Mira called Cedar ready."},
        holder="Mira", utterer="user", attribution="indirect_report"),
     st("s2", "The user says Cedar checkout still fails.", "fail", "state",
        {"subject": "Cedar checkout"}, snippets={0: "I do not agree because checkout still fails."})],
    forbidden=["user_believes_Cedar_ready", "REVISION"],
    rationale="Indirect report still cannot become user-held readiness claim.")
add("B15", "negative", [ev('Mira said, "Cedar is ready." I agree; checkout passes.')],
    [st("s1", "Mira claims Cedar is ready.", "be_ready", "proposition",
        {"subject": "Cedar"}, snippets={0: 'Mira said, "Cedar is ready."'},
        holder="Mira", utterer="Mira", attribution="direct_quote"),
     st("s2", "The user agrees Cedar is ready and says checkout passes.", "agree_ready", "attitude",
        {"holder": "user", "subject": "Cedar"}, snippets={0: "I agree; checkout passes."})],
    rationale="Explicit agreement supports a user-held stance, separate from the quotation.")

# B16 — later evidence changes interpretation of old evidence, not old visibility.
add("B16", "canonical", [ev("It failed after the rollout.", occurred="2026-01-10T12:00:00Z", available="2026-01-10T13:00:00Z"),
    ev("By it, I meant the Cedar queue, not checkout.", occurred="2026-03-10T12:00:00Z", available="2026-03-10T13:00:00Z")],
    [st("v1", "An unresolved referent failed after the rollout.", "fail", "event",
        {"subject": "UNKNOWN"}, block_key="b1", entity_status="unresolved",
        uncertainty="referent_unresolved", valid_time="2026-01-10"),
     st("v2", "The Cedar queue failed after the rollout.", "fail", "event",
        {"subject": "Cedar queue"}, sources=(0, 1), block_key="b1", valid_time="2026-01-10")],
    cutoffs=["2026-02-01T00:00:00Z", "2026-04-01T00:00:00Z"],
    rationale="March clarification creates a later state; February retains ambiguity.")
add("B16", "paraphrase", [ev("It broke following deployment.", occurred="2026-01-10T12:00:00Z", available="2026-01-10T13:00:00Z"),
    ev("I was referring to Cedar's queue, not its checkout.", occurred="2026-03-10T12:00:00Z", available="2026-03-10T13:00:00Z")],
    [st("v1", "An unresolved referent failed after deployment.", "fail", "event",
        {"subject": "UNKNOWN"}, block_key="b1", entity_status="unresolved",
        uncertainty="referent_unresolved", valid_time="2026-01-10"),
     st("v2", "The Cedar queue failed after deployment.", "fail", "event",
        {"subject": "Cedar queue"}, sources=(0, 1), block_key="b1", valid_time="2026-01-10")],
    cutoffs=["2026-02-01T00:00:00Z", "2026-04-01T00:00:00Z"],
    rationale="Paraphrase preserves early unknown and later clarified interpretation.")
add("B16", "negative", [ev("The Cedar queue failed.", occurred="2026-01-10T12:00:00Z", available="2026-01-10T13:00:00Z"),
    ev("The Cedar queue recovered.", occurred="2026-03-10T12:00:00Z", available="2026-03-10T13:00:00Z")],
    [st("s1", "The Cedar queue failed in January.", "fail", "event",
        {"subject": "Cedar queue"}, valid_time="2026-01-10"),
     st("s2", "The Cedar queue recovered in March.", "recover", "event",
        {"subject": "Cedar queue"}, sources=(1,), valid_time="2026-03-10")],
    cutoffs=["2026-02-01T00:00:00Z", "2026-04-01T00:00:00Z"],
    forbidden=["interpretation_revision"],
    rationale="A world-state change creates a new block, not a reinterpretation of January.")

# B17 — BEFORE metadata must not become generic structural bridge authority.
add("B17", "canonical", [ev("A logged in before B logged in."),
    ev("B logged in before C logged in."),
    ev("X failed, causing Y to stop."), ev("Y stopped, causing Z to stall.")],
    [st("s1", "A logged in.", "login", "event", {"actor": "A"}, snippets={0: "A logged in"}),
     st("s2", "B logged in.", "login", "event", {"actor": "B"},
        sources=(0, 1), snippets={0: "B logged in", 1: "B logged in"}),
     st("s3", "C logged in.", "login", "event", {"actor": "C"},
        sources=(1,), snippets={1: "C logged in"}),
     st("s4", "X failed.", "fail", "event", {"subject": "X"},
        sources=(2,), snippets={2: "X failed"}),
     st("s5", "Y stopped.", "stop", "event", {"subject": "Y"},
        sources=(2, 3), snippets={2: "Y to stop", 3: "Y stopped"}),
     st("s6", "Z stalled.", "stall", "event", {"subject": "Z"},
        sources=(3,), snippets={3: "Z to stall"})],
    relations=[("BEFORE", "s1", "s2", 0, "before", "explicit_temporal"),
               ("BEFORE", "s2", "s3", 1, "before", "explicit_temporal"),
               ("CAUSE", "s4", "s5", 2, "causing", "explicit_connective"),
               ("CAUSE", "s5", "s6", 3, "causing", "explicit_connective")],
    forbidden=["BEFORE_generic_bridge", "CAUSE_s4_s6_direct"],
    rationale="Temporal links are non-traversable; the two explicit CAUSE edges form a path, not a direct edge.")
add("B17", "paraphrase", [ev("A signed in ahead of B signing in."),
    ev("B signed in ahead of C signing in."),
    ev("X broke, which made Y stop."), ev("Y stopped, which made Z stall.")],
    [st("s1", "A logged in.", "login", "event", {"actor": "A"}, snippets={0: "A signed in"}),
     st("s2", "B logged in.", "login", "event", {"actor": "B"},
        sources=(0, 1), snippets={0: "B signing in", 1: "B signed in"}),
     st("s3", "C logged in.", "login", "event", {"actor": "C"},
        sources=(1,), snippets={1: "C signing in"}),
     st("s4", "X failed.", "fail", "event", {"subject": "X"},
        sources=(2,), snippets={2: "X broke"}),
     st("s5", "Y stopped.", "stop", "event", {"subject": "Y"},
        sources=(2, 3), snippets={2: "Y stop", 3: "Y stopped"}),
     st("s6", "Z stalled.", "stall", "event", {"subject": "Z"},
        sources=(3,), snippets={3: "Z stall"})],
    relations=[("BEFORE", "s1", "s2", 0, "ahead of", "explicit_temporal"),
               ("BEFORE", "s2", "s3", 1, "ahead of", "explicit_temporal"),
               ("CAUSE", "s4", "s5", 2, "which made", "explicit_connective"),
               ("CAUSE", "s5", "s6", 3, "which made", "explicit_connective")],
    forbidden=["BEFORE_generic_bridge", "CAUSE_s4_s6_direct"],
    rationale="Paraphrase preserves the two causal edges and excludes temporal bridge expansion.")
add("B17", "negative", [ev("A logged in before B logged in."),
    ev("B logged in before C logged in."),
    ev("X appeared before Y appeared."), ev("Y appeared before Z appeared.")],
    [st("s1", "A logged in.", "login", "event", {"actor": "A"}, snippets={0: "A logged in"}),
     st("s2", "B logged in.", "login", "event", {"actor": "B"},
        sources=(0, 1), snippets={0: "B logged in", 1: "B logged in"}),
     st("s3", "C logged in.", "login", "event", {"actor": "C"},
        sources=(1,), snippets={1: "C logged in"}),
     st("s4", "X appeared.", "appear", "event", {"subject": "X"}, snippets={2: "X appeared"}, sources=(2,)),
     st("s5", "Y appeared.", "appear", "event", {"subject": "Y"},
        sources=(2, 3), snippets={2: "Y appeared", 3: "Y appeared"}),
     st("s6", "Z appeared.", "appear", "event", {"subject": "Z"},
        sources=(3,), snippets={3: "Z appeared"})],
    relations=[("BEFORE", "s1", "s2", 0, "before", "explicit_temporal"),
               ("BEFORE", "s2", "s3", 1, "before", "explicit_temporal"),
               ("BEFORE", "s4", "s5", 2, "before", "explicit_temporal"),
               ("BEFORE", "s5", "s6", 3, "before", "explicit_temporal")],
    forbidden=["CAUSE", "BEFORE_generic_bridge"],
    rationale="Pure temporal ordering has no admitted causal path or generic graph bridge.")

# B18 — knowledge availability is independent of event time.
add("B18", "canonical", [ev("The Cedar queue failed on January 5.",
    occurred="2026-01-05T12:00:00Z", available="2026-03-05T12:00:00Z")],
    [st("s1", "The Cedar queue failed on 2026-01-05.", "fail", "event",
        {"subject": "Cedar queue"}, valid_time="2026-01-05")],
    cutoffs=["2026-02-01T00:00:00Z", "2026-04-01T00:00:00Z"],
    rationale="January event admitted in March is invisible at February knowledge cutoff.")
add("B18", "paraphrase", [ev("On January 5 Cedar's queue went down.",
    occurred="2026-01-05T12:00:00Z", available="2026-03-05T12:00:00Z")],
    [st("s1", "The Cedar queue failed on 2026-01-05.", "fail", "event",
        {"subject": "Cedar queue"}, valid_time="2026-01-05")],
    cutoffs=["2026-02-01T00:00:00Z", "2026-04-01T00:00:00Z"],
    rationale="Paraphrase preserves event and admission-time separation.")
add("B18", "negative", [ev("The Cedar queue failed on January 5.",
    occurred="2026-01-05T12:00:00Z", available="2026-01-05T13:00:00Z")],
    [st("s1", "The Cedar queue failed on 2026-01-05.", "fail", "event",
        {"subject": "Cedar queue"}, valid_time="2026-01-05")],
    cutoffs=["2026-02-01T00:00:00Z", "2026-04-01T00:00:00Z"],
    rationale="Same event admitted in January is already visible by February.")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                for row in rows), encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    if Counter(row["family"] for row in CASES) != {f"B{i:02d}": 3 for i in range(1, 19)}:
        raise AssertionError("every required family must have C/P/N variants")
    for split in ("dev", "heldout"):
        write_jsonl(ROOT / f"{split}_cases.jsonl", [row for row in CASES if row["split"] == split])
        ids = {row["case_id"] for row in CASES if row["split"] == split}
        write_jsonl(ROOT / f"{split}_gold.jsonl", [row for row in GOLD if row["case_id"] in ids])
    print(f"built {len(CASES)} cases: {sum(r['split'] == 'dev' for r in CASES)} dev, "
          f"{sum(r['split'] == 'heldout' for r in CASES)} heldout")
