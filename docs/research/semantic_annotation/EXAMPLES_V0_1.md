# LCE Semantic Annotation Examples v0.1

**Status:** Frozen Reference Examples (GitHub Issue #13)  
**Scope:** Research Only — Pairs with [`ONTOLOGY_V0_1.md`](file:///c:/projects/LCE/docs/research/semantic_annotation/ONTOLOGY_V0_1.md) and [`ANNOTATION_GUIDELINE_V0_1.md`](file:///c:/projects/LCE/docs/research/semantic_annotation/ANNOTATION_GUIDELINE_V0_1.md).

---

## 1. Unit Kind Examples

### 1.1 `event`
- **Positive Example:**  
  *Text:* `"I submitted my resignation to Acme Corp yesterday."`  
  *Annotation:*
  ```json
  {
    "annotation_id": "u_event_pos_01",
    "kind": "event",
    "predicate": "submit_resignation",
    "arguments": {
      "actor": "I",
      "target": "Acme Corp",
      "time": "yesterday"
    },
    "polarity": "positive",
    "modality": "asserted",
    "holder": "user"
  }
  ```
- **Negative Example:**  
  *Text:* `"I am an employee at Acme Corp."`  
  *Incorrect:* `kind: "event"` (Reason: Being employed is a continuous status, not a dynamic occurrence).  
  *Correct:* `kind: "state"`, `predicate: "employed_at"`.

---

### 1.2 `state`
- **Positive Example:**  
  *Text:* `"The database is currently running out of disk space."`  
  *Annotation:*
  ```json
  {
    "annotation_id": "u_state_pos_01",
    "kind": "state",
    "predicate": "low_disk_space",
    "arguments": {
      "theme": "The database"
    },
    "polarity": "positive",
    "modality": "asserted",
    "holder": "user"
  }
  ```
- **Negative Example:**  
  *Text:* `"The database crashed at 3 PM."`  
  *Incorrect:* `kind: "state"` (Reason: Crashing is an instantaneous change of state/event).  
  *Correct:* `kind: "event"`, `predicate: "crash"`.

---

### 1.3 `proposition`
- **Positive Example:**  
  *Text:* `"Immutable append-only logs prevent write-skew anomalies."`  
  *Annotation:*
  ```json
  {
    "annotation_id": "u_prop_pos_01",
    "kind": "proposition",
    "predicate": "prevent_anomaly",
    "arguments": {
      "theme": "Immutable append-only logs",
      "target": "write-skew anomalies"
    },
    "polarity": "positive",
    "modality": "asserted",
    "holder": "user"
  }
  ```
- **Negative Example:**  
  *Text:* `"I am setting up an immutable append-only log."`  
  *Incorrect:* `kind: "proposition"` (Reason: This is a specific action undertaken by an actor).  
  *Correct:* `kind: "event"`, `predicate: "set_up"`.

---

### 1.4 `attitude`
- **Positive Example:**  
  *Text:* `"I prefer writing Rust over Python for systems programming."`  
  *Annotation:*
  ```json
  {
    "annotation_id": "u_att_pos_01",
    "kind": "attitude",
    "predicate": "prefer",
    "arguments": {
      "experiencer": "I",
      "theme": "writing Rust",
      "target": "Python",
      "topic": "systems programming"
    },
    "polarity": "positive",
    "modality": "asserted",
    "holder": "user"
  }
  ```
- **Negative Example:**  
  *Text:* `"I wrote a Rust compiler last month."`  
  *Incorrect:* `kind: "attitude"` (Reason: Writing a compiler is a concrete past action, not a mental stance or preference).  
  *Correct:* `kind: "event"`, `predicate: "write"`.

---

## 2. Argument Roles Examples

### 2.1 `actor` vs `experiencer` vs `theme`
- **Text:** `"Alice felt anxious when Bob dropped the production database."`
  - *Clause 1:* `"Alice felt anxious"`
    ```json
    {
      "annotation_id": "u_role_exp_01",
      "kind": "attitude",
      "predicate": "feel_anxious",
      "arguments": {
        "experiencer": "Alice"
      }
    }
    ```
    *Negative:* Do not label Alice as `actor` (she does not volitionally perform anxiety; she experiences it).
  - *Clause 2:* `"Bob dropped the production database"`
    ```json
    {
      "annotation_id": "u_role_act_01",
      "kind": "event",
      "predicate": "drop_database",
      "arguments": {
        "actor": "Bob",
        "theme": "production database"
      }
    }
    ```
    *Negative:* Do not label `production database` as `target` or `actor` (it undergoes the drop without volition $\implies$ `theme`).

### 2.2 `reason` vs `purpose` vs `result`
- **Text:** `"I refactored the auth module to improve latency, which reduced p99 times to 15ms because caching was enabled."`
  - `actor`: `"I"`
  - `theme`: `"auth module"`
  - `purpose`: `"to improve latency"` (intended goal)
  - `result`: `"reduced p99 times to 15ms"` (actual outcome)
  - `reason`: `"because caching was enabled"` (underlying explanation)
  - *Negative:* Do not label `"to improve latency"` as `result` (it was the aim, not the observed post-facto metric).

---

## 3. Polarity and Modality Examples

### 3.1 Polarity (`positive`, `negative`, `unknown`)
- **Positive:** `"We have enabled dual-factor authentication."` $\implies$ `polarity: positive`.
- **Negative:** `"We do not support legacy RSA keys."` $\implies$ `polarity: negative`.
- **Unknown:** `"Whether we retain the old cluster remains open."` $\implies$ `polarity: unknown`.
- *Negative Example:*  
  *Text:* `"I refused to sign the agreement."`  
  *Incorrect:* `polarity: negative` (Reason: The action of refusing affirmatively occurred).  
  *Correct:* `polarity: positive`, `predicate: "refuse_to_sign"`. (Alternatively, if predicate is `sign_agreement`, `polarity: negative`).

### 3.2 Modality (`asserted`, `possible`, `hypothetical`, `intended`, `desired`, `uncertain`, `unknown`)
- **Asserted:** `"The server restarted at midnight."` $\implies$ `modality: asserted`.
- **Possible:** `"The outage might be caused by DNS misconfiguration."` $\implies$ `modality: possible`.
- **Hypothetical:** `"If we migrate to Kubernetes, we would need three more SREs."` $\implies$ `modality: hypothetical`.
- **Intended:** `"I will publish the RFC next Monday."` $\implies$ `modality: intended`.
- **Desired:** `"I hope we can deprecate the v1 endpoints soon."` $\implies$ `modality: desired`.
- **Uncertain:** `"I am not sure if the migration script finished."` $\implies$ `modality: uncertain`.
- *Negative Example:*  
  *Text:* `"I plan to leave the company."`  
  *Incorrect:* `modality: desired` (Reason: Planning expresses a concrete intention/commitment, not merely a passive wish).  
  *Correct:* `modality: intended`.

---

## 4. Holder / Source Examples

### 4.1 `user` vs `quoted` vs `reported`
- **Text:** `"The VP claimed 'We will be profitable next quarter', but our team lead told me the runway is only four months."`
  - *Unit 1 (Quoted):*
    ```json
    {
      "annotation_id": "u_holder_quote_01",
      "kind": "proposition",
      "predicate": "profitable",
      "arguments": {"theme": "company", "time": "next quarter"},
      "modality": "asserted",
      "holder": "quoted"
    }
    ```
  - *Unit 2 (Reported):*
    ```json
    {
      "annotation_id": "u_holder_rep_01",
      "kind": "state",
      "predicate": "runway_duration",
      "arguments": {"theme": "runway", "result": "four months"},
      "modality": "asserted",
      "holder": "reported"
    }
    ```
  - *Negative Example:*  
    *Incorrect:* Labeling Unit 1 with `holder: user` (Reason: The user is citing the VP, not asserting personal conviction of profitability).

---

## 5. Evidence Status Examples

### 5.1 `explicit` vs `entailed` vs `inferred`
- **Text:** `"The CTO fired the director of infrastructure."`
  - *Unit 1 (`explicit`):*
    - Predicate: `fire`, Actor: `CTO`, Target: `director of infrastructure`. `evidence_status: explicit`.
  - *Unit 2 (`entailed`):*
    - Predicate: `terminate_employment`, Actor: `CTO`, Target: `director of infrastructure`. `evidence_status: entailed` (Strict logical consequence of being fired).
  - *Unit 3 (`inferred`):*
    - Predicate: `dissatisfied_with_performance`, Experiencer: `CTO`, Target: `director of infrastructure`. `evidence_status: inferred` (Plausible reason, but not stated).
  - *Negative Example:*  
    *Incorrect:* Labeling Unit 3 as `explicit` or `entailed`. (Inference must remain non-authoritative).

---

## 6. Relation Ontology Examples

### 6.1 `SAME_ENTITY` and `SAME_EVENT`
- **Text:** `"Alice joined the security team in June. The security team welcomed her warmly."`
  - $U_1$: `join(Alice, security team)`
  - $U_2$: `welcome(security team, Alice)`
  - Relation: `SAME_ENTITY(U1.arguments.actor, U2.arguments.target)` (`Alice` $\equiv$ `her`).
  - *Negative Example:*  
    *Text:* `"We had our weekly sync on Monday. We had our weekly sync on Wednesday."`  
    *Incorrect:* `U1 SAME_EVENT U2` (Reason: Distinct meeting tokens occurring on different days).  
    *Correct:* `U1 NO_RELATION U2` (or `BEFORE(U1, U2)`).

### 6.2 `BEFORE`, `AFTER`, `OVERLAP`, `TEMPORAL_UNKNOWN`
- **Text:** `"I worked at Google from 2018 to 2021. Then I joined DeepMind."`
  - $U_1$: `work_at(I, Google)` [2018–2021]
  - $U_2$: `join(I, DeepMind)` [2021]
  - Relation: `U1 BEFORE U2`
- **Text:** `"While living in London, I wrote my first book."`
  - $U_1$: `live_in(I, London)`
  - $U_2$: `write(I, first book)`
  - Relation: `U1 OVERLAP U2`
- **Text:** `"Alice finished her report. Bob deployed the patch."` (No dates/order given)
  - Relation: `U1 TEMPORAL_UNKNOWN U2`

### 6.3 `CAUSE`, `CONDITION`, `PURPOSE`, `CONTRAST`, `CONCESSION`
- **`CAUSE`:** `"The disk filled up, causing the node to crash."`  
  - $U_1$: `fill_up(disk)` $\xrightarrow{\text{CAUSE}}$ $U_2$: `crash(node)`.  
  *Negative Example:* `"The disk filled up. Later the node crashed."` $\implies$ Annotate `BEFORE`, NOT `CAUSE` (unless connective is present).
- **`CONDITION`:** `"If we exceed 10k QPS, we must shard the database."`  
  - $U_1$: `exceed_qps(10k)` $\xrightarrow{\text{CONDITION}}$ $U_2$: `shard(database)`.
- **`PURPOSE`:** `"We added indexes in order to speed up user lookup."`  
  - $U_1$: `add_indexes(we)` $\xrightarrow{\text{PURPOSE}}$ $U_2$: `speed_up(user lookup)`.
- **`CONTRAST`:** `"I enjoy backend systems, but frontend work drains me."`  
  - $U_1$: `enjoy(backend)` $\xleftrightarrow{\text{CONTRAST}}$ $U_2$: `drain(frontend)`.
- **`CONCESSION`:** `"Although the benchmark had flaws, we accepted the results."`  
  - $U_1$: `have_flaws(benchmark)` $\xrightarrow{\text{CONCESSION}}$ $U_2$: `accept(results)`.

### 6.4 `EQUIVALENT` vs `INCOMPATIBLE`
- **`EQUIVALENT`:**  
  *Text:* `"I started my own company."` vs (later span) `"I founded a startup."`  
  - $U_1$: `start(user, company)` $\xleftrightarrow{\text{EQUIVALENT}}$ $U_2$: `found(user, startup)`.
- **`INCOMPATIBLE`:**  
  *Text 1 (2022):* `"I really want to work at a big tech firm."`  
  *Text 2 (2026):* `"I will never work at a big tech firm again."`  
  - $U_1$: `want(user, big_tech_work)`, `polarity: positive`, `time: 2022`
  - $U_2$: `work_at(user, big_tech_firm)`, `polarity: negative`, `time: 2026`
  - Relations: `U1 BEFORE U2`, `U1 INCOMPATIBLE U2`.

---

## 7. Negative Invariants: Prohibited Downstream Cognition Labels

Annotators and parsers must **never** output high-level longitudinal interpretations.

| Attempted Incorrect Annotation | Why It Is Forbidden | Mandatory v0.1 Decomposition |
| :--- | :--- | :--- |
| `U1 REVISION U2` | "Revision" is a cognitive judgment of belief replacement across time. | `U1 BEFORE U2` and `U1 INCOMPATIBLE U2` with distinct temporal anchors. |
| `U1 RECURRENCE U2` | "Recurrence" is a multi-session trajectory pattern. | `U1 BEFORE U2` and `U1 EQUIVALENT U2` with distinct temporal anchors. |
| `user HAS_TRAJECTORY T` | "Trajectory" is a topological path in the structure graph. | Individual dated units linked with `BEFORE` / `CAUSE`. |
| `U1 COGNITIVE_SHIFT U2`| "Cognitive shift" is an engine-level psychological thesis. | `U1 INCOMPATIBLE U2` (or `CONTRAST`) across time horizons. |
| `P1 STABLE_PREFERENCE` | Stability requires longitudinal hypothesis evaluation. | Atomic unit with `kind: attitude`, `modality: desired`. |

---

## 8. Complete Multi-Unit End-to-End Walkthrough

### Raw Evidence Input
```text
Evidence ID: ev_2026_09_15_01
Semantic Block ID: block_042
Occurred: 2026-09-15T10:00:00Z
Content:
"In 2022, I loved working at BigCorp because the scale was exhilarating.
However, by 2025 I completely burned out and decided I will never work
for a giant corporation again. My mentor told me 'Small startups are
riskier', but I joined a five-person AI lab last week anyway."
```

### Complete Ground-Truth Annotation Document
```json
{
  "document_id": "doc_walkthrough_01",
  "cutoff_time": "2026-09-23T00:00:00Z",
  "units": [
    {
      "annotation_id": "u1",
      "provenance": {
        "raw_evidence_id": "ev_2026_09_15_01",
        "semantic_block_id": "block_042"
      },
      "source_span": {
        "char_start": 0,
        "char_end": 37,
        "text": "In 2022, I loved working at BigCorp"
      },
      "kind": "attitude",
      "predicate": "love",
      "arguments": {
        "experiencer": "I",
        "theme": "working at BigCorp",
        "time": "2022"
      },
      "polarity": "positive",
      "modality": "asserted",
      "holder": "user",
      "temporal_anchoring": {
        "value": "2022",
        "anchor_type": "exact",
        "source_expression": "In 2022"
      },
      "evidence_status": "explicit",
      "confidence": 1.0
    },
    {
      "annotation_id": "u2",
      "provenance": {
        "raw_evidence_id": "ev_2026_09_15_01",
        "semantic_block_id": "block_042"
      },
      "source_span": {
        "char_start": 46,
        "char_end": 74,
        "text": "the scale was exhilarating"
      },
      "kind": "attitude",
      "predicate": "exhilarating",
      "arguments": {
        "stimulus": "the scale",
        "experiencer": "I"
      },
      "polarity": "positive",
      "modality": "asserted",
      "holder": "user",
      "temporal_anchoring": {
        "value": "2022",
        "anchor_type": "relative",
        "source_expression": "In 2022"
      },
      "evidence_status": "explicit",
      "confidence": 0.95
    },
    {
      "annotation_id": "u3",
      "provenance": {
        "raw_evidence_id": "ev_2026_09_15_01",
        "semantic_block_id": "block_042"
      },
      "source_span": {
        "char_start": 89,
        "char_end": 125,
        "text": "by 2025 I completely burned out"
      },
      "kind": "event",
      "predicate": "burn_out",
      "arguments": {
        "actor": "I",
        "time": "by 2025"
      },
      "polarity": "positive",
      "modality": "asserted",
      "holder": "user",
      "temporal_anchoring": {
        "value": "2025",
        "anchor_type": "exact",
        "source_expression": "by 2025"
      },
      "evidence_status": "explicit",
      "confidence": 1.0
    },
    {
      "annotation_id": "u4",
      "provenance": {
        "raw_evidence_id": "ev_2026_09_15_01",
        "semantic_block_id": "block_042"
      },
      "source_span": {
        "char_start": 140,
        "char_end": 194,
        "text": "I will never work for a giant corporation again"
      },
      "kind": "attitude",
      "predicate": "work_at",
      "arguments": {
        "actor": "I",
        "target": "giant corporation"
      },
      "polarity": "negative",
      "modality": "intended",
      "holder": "user",
      "temporal_anchoring": {
        "value": "2025/..",
        "anchor_type": "bounded_range",
        "source_expression": "again"
      },
      "evidence_status": "explicit",
      "confidence": 1.0
    },
    {
      "annotation_id": "u5",
      "provenance": {
        "raw_evidence_id": "ev_2026_09_15_01",
        "semantic_block_id": "block_042"
      },
      "source_span": {
        "char_start": 218,
        "char_end": 244,
        "text": "Small startups are riskier"
      },
      "kind": "proposition",
      "predicate": "risky",
      "arguments": {
        "theme": "Small startups"
      },
      "polarity": "positive",
      "modality": "asserted",
      "holder": "quoted",
      "temporal_anchoring": {
        "value": "unknown",
        "anchor_type": "unanchored",
        "source_expression": null
      },
      "evidence_status": "explicit",
      "confidence": 1.0
    },
    {
      "annotation_id": "u6",
      "provenance": {
        "raw_evidence_id": "ev_2026_09_15_01",
        "semantic_block_id": "block_042"
      },
      "source_span": {
        "char_start": 254,
        "char_end": 302,
        "text": "I joined a five-person AI lab last week"
      },
      "kind": "event",
      "predicate": "join",
      "arguments": {
        "actor": "I",
        "target": "five-person AI lab",
        "time": "last week"
      },
      "polarity": "positive",
      "modality": "asserted",
      "holder": "user",
      "temporal_anchoring": {
        "value": "2026-09",
        "anchor_type": "relative",
        "source_expression": "last week"
      },
      "evidence_status": "explicit",
      "confidence": 1.0
    }
  ],
  "relations": [
    {
      "relation_id": "rel_01",
      "source_id": "u2",
      "target_id": "u1",
      "relation_type": "CAUSE",
      "evidence_status": "explicit",
      "confidence": 0.95
    },
    {
      "relation_id": "rel_02",
      "source_id": "u1",
      "target_id": "u3",
      "relation_type": "BEFORE",
      "evidence_status": "explicit",
      "confidence": 1.0
    },
    {
      "relation_id": "rel_03",
      "source_id": "u1",
      "target_id": "u4",
      "relation_type": "INCOMPATIBLE",
      "evidence_status": "entailed",
      "confidence": 0.95
    },
    {
      "relation_id": "rel_04",
      "source_id": "u3",
      "target_id": "u4",
      "relation_type": "CAUSE",
      "evidence_status": "explicit",
      "confidence": 0.9
    },
    {
      "relation_id": "rel_05",
      "source_id": "u5",
      "target_id": "u6",
      "relation_type": "CONCESSION",
      "evidence_status": "explicit",
      "confidence": 0.9
    }
  ]
}
```
