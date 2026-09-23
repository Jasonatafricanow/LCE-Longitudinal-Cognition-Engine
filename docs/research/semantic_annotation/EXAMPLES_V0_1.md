# LCE Semantic Annotation Examples v0.1

**Status:** Frozen Reference Examples (GitHub Issue #13, Post-Review Revision)  
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
    "provenance": {
      "raw_evidence_id": "ev_001",
      "semantic_block_id": "block_001"
    },
    "source_span": {
      "char_start": 0,
      "char_end": 46,
      "text": "I submitted my resignation to Acme Corp yesterday"
    },
    "kind": "event",
    "predicate": {
      "surface_predicate": "submitted my resignation",
      "normalized_predicate": "submit_resignation",
      "normalization_rule": "verb_lemma"
    },
    "arguments": {
      "actor": {
        "role": "actor",
        "text": "I",
        "entity_ref": "user"
      },
      "target": {
        "role": "target",
        "text": "Acme Corp",
        "entity_ref": "ent_acme"
      },
      "time": {
        "role": "time",
        "text": "yesterday"
      }
    },
    "polarity": "positive",
    "modality": "asserted",
    "holder_ref": "user",
    "attribution_mode": "direct_speaker",
    "temporal_anchoring": {
      "normalized_value": "2026-09-22",
      "anchor_type": "relative",
      "source_expression": "yesterday",
      "reference_anchor": "evidence:occurred_at"
    },
    "evidence_status": "explicit",
    "confidence": 1.0
  }
  ```
- **Negative Example:**  
  *Text:* `"I am an employee at Acme Corp."`  
  *Incorrect:* `kind: "event"` (Reason: Being employed is a continuous status, not a dynamic transition).  
  *Correct:* `kind: "state"`, `normalized_predicate: "employed_at"`.

---

### 1.2 `state`
- **Positive Example:**  
  *Text:* `"The database is currently running out of disk space."`  
  *Annotation:*
  ```json
  {
    "annotation_id": "u_state_pos_01",
    "provenance": {
      "raw_evidence_id": "ev_001",
      "semantic_block_id": "block_001"
    },
    "source_span": {
      "char_start": 0,
      "char_end": 51,
      "text": "The database is currently running out of disk space"
    },
    "kind": "state",
    "predicate": {
      "surface_predicate": "running out of disk space",
      "normalized_predicate": "low_disk_space",
      "normalization_rule": "standard_frame"
    },
    "arguments": {
      "theme": {
        "role": "theme",
        "text": "The database",
        "entity_ref": "ent_db"
      }
    },
    "polarity": "positive",
    "modality": "asserted",
    "holder_ref": "user",
    "attribution_mode": "direct_speaker",
    "temporal_anchoring": {
      "normalized_value": "2026-09-23",
      "anchor_type": "relative",
      "source_expression": "currently",
      "reference_anchor": "evidence:occurred_at"
    },
    "evidence_status": "explicit",
    "confidence": 1.0
  }
  ```
- **Negative Example:**  
  *Text:* `"The database crashed at 3 PM."`  
  *Incorrect:* `kind: "state"` (Reason: Crashing is an instantaneous change of state/event).  
  *Correct:* `kind: "event"`, `normalized_predicate: "crash"`.

---

### 1.3 `proposition`
- **Positive Example:**  
  *Text:* `"Immutable append-only logs prevent write-skew anomalies."`  
  *Annotation:*
  ```json
  {
    "annotation_id": "u_prop_pos_01",
    "provenance": {
      "raw_evidence_id": "ev_001",
      "semantic_block_id": "block_001"
    },
    "source_span": {
      "char_start": 0,
      "char_end": 57,
      "text": "Immutable append-only logs prevent write-skew anomalies"
    },
    "kind": "proposition",
    "predicate": {
      "surface_predicate": "prevent",
      "normalized_predicate": "prevent_anomaly",
      "normalization_rule": "standard_frame"
    },
    "arguments": {
      "theme": {
        "role": "theme",
        "text": "Immutable append-only logs"
      },
      "target": {
        "role": "target",
        "text": "write-skew anomalies"
      }
    },
    "polarity": "positive",
    "modality": "asserted",
    "holder_ref": "user",
    "attribution_mode": "direct_speaker",
    "temporal_anchoring": {
      "normalized_value": "unknown",
      "anchor_type": "unanchored",
      "source_expression": null,
      "reference_anchor": null
    },
    "evidence_status": "explicit",
    "confidence": 1.0
  }
  ```
- **Negative Example:**  
  *Text:* `"I configured an append-only log yesterday."`  
  *Incorrect:* `kind: "proposition"` (Reason: Specific action performed by an actor at a date).  
  *Correct:* `kind: "event"`, `normalized_predicate: "configure"`.

---

### 1.4 `attitude`
- **Positive Example:**  
  *Text:* `"I prefer writing Rust over Python for systems programming."`  
  *Annotation:*
  ```json
  {
    "annotation_id": "u_att_pos_01",
    "provenance": {
      "raw_evidence_id": "ev_001",
      "semantic_block_id": "block_001"
    },
    "source_span": {
      "char_start": 0,
      "char_end": 58,
      "text": "I prefer writing Rust over Python for systems programming"
    },
    "kind": "attitude",
    "predicate": {
      "surface_predicate": "prefer",
      "normalized_predicate": "prefer",
      "normalization_rule": "verb_lemma"
    },
    "arguments": {
      "experiencer": {
        "role": "experiencer",
        "text": "I",
        "entity_ref": "user"
      },
      "theme": {
        "role": "theme",
        "text": "writing Rust"
      },
      "target": {
        "role": "target",
        "text": "Python"
      },
      "topic": {
        "role": "topic",
        "text": "systems programming"
      }
    },
    "polarity": "positive",
    "modality": "asserted",
    "holder_ref": "user",
    "attribution_mode": "direct_speaker",
    "temporal_anchoring": {
      "normalized_value": "2026",
      "anchor_type": "bounded_range",
      "source_expression": null,
      "reference_anchor": "evidence:occurred_at"
    },
    "evidence_status": "explicit",
    "confidence": 1.0
  }
  ```
- **Negative Example:**  
  *Text:* `"I wrote a Rust compiler last month."`  
  *Incorrect:* `kind: "attitude"` (Reason: Concrete past action, not a mental valuation).  
  *Correct:* `kind: "event"`, `normalized_predicate: "write"`.

---

## 2. Special Policy Examples

### 2.1 Shallow Nested Attitude Example
- **Text:** `"I think I want to leave."`
  *Annotation:*
  ```json
  {
    "annotation_id": "u_nested_01",
    "provenance": {
      "raw_evidence_id": "ev_002",
      "semantic_block_id": "block_002"
    },
    "source_span": {
      "char_start": 0,
      "char_end": 24,
      "text": "I think I want to leave"
    },
    "kind": "attitude",
    "predicate": {
      "surface_predicate": "think I want to leave",
      "normalized_predicate": "leave",
      "normalization_rule": "shallow_nested_hedge"
    },
    "arguments": {
      "actor": {
        "role": "actor",
        "text": "I",
        "entity_ref": "user"
      }
    },
    "polarity": "positive",
    "modality": "uncertain",
    "holder_ref": "user",
    "attribution_mode": "direct_speaker",
    "temporal_anchoring": {
      "normalized_value": "unknown",
      "anchor_type": "unanchored"
    },
    "evidence_status": "explicit",
    "confidence": 0.70
  }
  ```
  *Negative Error:* Setting `modality: "desired"` without epistemic hedging. Silently converting belief-about-desire into unhedged desire is prohibited.

### 2.2 Removal of Manufactured Result States
- **Text:** `"I moved to London in 2021."`
  - *Correct Annotation:* A single unit:
    ```json
    {
      "annotation_id": "u_move_01",
      "kind": "event",
      "predicate": {
        "surface_predicate": "moved",
        "normalized_predicate": "move_to",
        "normalization_rule": "verb_lemma"
      },
      "arguments": {
        "actor": {"role": "actor", "text": "I", "entity_ref": "user"},
        "target": {"role": "target", "text": "London", "entity_ref": "loc_london"},
        "time": {"role": "time", "text": "in 2021"}
      },
      "temporal_anchoring": {
        "normalized_value": "2021",
        "anchor_type": "exact",
        "source_expression": "in 2021"
      },
      "evidence_status": "explicit",
      "confidence": 1.0
    }
    ```
  - *Prohibited Negative Error:* Manufacturing a second synthetic unit `kind: "state", predicate: "live_in", arguments: {place: "London"}` and drawing a `CAUSE` relation to it. Transition events must not invent continuous result states without explicit bounded evidence.

---

## 3. Holder Identity and Attribution Mode

- **Text:** `"The VP announced 'We will achieve profitability next quarter', but our director told me the runway is four months."`
  - *Unit 1 (VP Quote):*
    ```json
    {
      "annotation_id": "u_vp_01",
      "kind": "proposition",
      "predicate": {
        "surface_predicate": "achieve profitability",
        "normalized_predicate": "profitable",
        "normalization_rule": "standard_frame"
      },
      "arguments": {
        "theme": {"role": "theme", "text": "We", "entity_ref": "company"},
        "time": {"role": "time", "text": "next quarter"}
      },
      "holder_ref": "VP",
      "attribution_mode": "direct_quote"
    }
    ```
  - *Unit 2 (Director Report):*
    ```json
    {
      "annotation_id": "u_dir_01",
      "kind": "state",
      "predicate": {
        "surface_predicate": "runway is four months",
        "normalized_predicate": "runway_duration",
        "normalization_rule": "standard_frame"
      },
      "arguments": {
        "theme": {"role": "theme", "text": "runway"},
        "result": {"role": "result", "text": "four months"}
      },
      "holder_ref": "director",
      "attribution_mode": "indirect_report"
    }
    ```

---

## 4. Relations: Grounding, Control Gating, and Mention Endpoints

### 4.1 `SAME_ENTITY` Over Argument Mentions
- **Text:** `"Alice joined the security team in June. The security team welcomed her warmly."`
  - $U_1$: `join(Alice, security team)`
  - $U_2$: `welcome(security team, her)`
  - Relation:
    ```json
    {
      "relation_id": "rel_same_ent_01",
      "source_id": "u1:actor",
      "target_id": "u2:target",
      "relation_type": "SAME_ENTITY",
      "evidence_status": "explicit",
      "confidence": 1.0,
      "provenance": {
        "raw_evidence_id": "ev_001",
        "semantic_block_id": "block_001"
      }
    }
    ```
  *Negative Error:* Using `source_id: "u1", target_id: "u2"`. `SAME_ENTITY` must target argument mentions (`u1:actor`), not whole propositions.

### 4.2 `INCOMPATIBLE` Requires Overlapping Temporal Validity
- **Positive Example (Contemporaneous Conflict):**  
  *Text (Same meeting, 2026-09-10):* `"The server is fully operational. The server is completely offline."`
  - $U_1$: `operational(server)`, `time: 2026-09-10`
  - $U_2$: `offline(server)`, `time: 2026-09-10`
  - Relation: `u1 INCOMPATIBLE u2` (overlapping times, mutually exclusive states).
- **Negative Example (Cross-Time Shift):**  
  *Text 1 (2022):* `"I really want to work at BigCorp."`  
  *Text 2 (2026):* `"I will never work at BigCorp again."`  
  - $U_1$: `time: 2022`, `polarity: positive`, `modality: desired`.
  - $U_2$: `time: 2026`, `polarity: negative`, `modality: intended`.
  - *Correct Relations:*
    - `u1 BEFORE u2`
    - `u1:target SAME_ENTITY u2:target`
  - *Prohibited Negative Error:* Labeling `u1 INCOMPATIBLE u2` or `u1 REVISION u2`. Because the temporal anchors do not overlap, this is a chronological difference from which downstream LCE infers cognitive change.

### 4.3 Control Labels Gated from Graph Persistence
- For evaluation benchmarks, unlinked or indeterminate pairs emit:
  ```json
  {
    "relation_id": "rel_ctrl_01",
    "source_id": "u1",
    "target_id": "u2",
    "relation_type": "NO_RELATION",
    "evidence_status": "explicit",
    "confidence": 1.0,
    "provenance": {
      "raw_evidence_id": "ev_001",
      "semantic_block_id": "block_001"
    }
  }
  ```
  *Rule:* This relation is retained in annotation files for inter-annotator evaluation, but calling `to_graph_edge()` fails with an error: control outcomes are never persisted into the typed graph.

---

## 5. Complete Multi-Unit End-to-End Walkthrough

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
        "char_end": 35,
        "text": "In 2022, I loved working at BigCorp"
      },
      "kind": "attitude",
      "predicate": {
        "surface_predicate": "loved working",
        "normalized_predicate": "love",
        "normalization_rule": "verb_lemma"
      },
      "arguments": {
        "experiencer": {
          "role": "experiencer",
          "text": "I",
          "entity_ref": "user"
        },
        "theme": {
          "role": "theme",
          "text": "working at BigCorp"
        },
        "time": {
          "role": "time",
          "text": "In 2022"
        }
      },
      "polarity": "positive",
      "modality": "asserted",
      "holder_ref": "user",
      "attribution_mode": "direct_speaker",
      "temporal_anchoring": {
        "normalized_value": "2022",
        "anchor_type": "exact",
        "source_expression": "In 2022",
        "reference_anchor": null
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
        "char_start": 44,
        "char_end": 70,
        "text": "the scale was exhilarating"
      },
      "kind": "attitude",
      "predicate": {
        "surface_predicate": "exhilarating",
        "normalized_predicate": "exhilarating",
        "normalization_rule": "exact_match"
      },
      "arguments": {
        "stimulus": {
          "role": "stimulus",
          "text": "the scale"
        },
        "experiencer": {
          "role": "experiencer",
          "text": "I",
          "entity_ref": "user"
        }
      },
      "polarity": "positive",
      "modality": "asserted",
      "holder_ref": "user",
      "attribution_mode": "direct_speaker",
      "temporal_anchoring": {
        "normalized_value": "2022",
        "anchor_type": "relative",
        "source_expression": "In 2022",
        "reference_anchor": "u1"
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
        "char_start": 81,
        "char_end": 113,
        "text": "by 2025 I completely burned out"
      },
      "kind": "event",
      "predicate": {
        "surface_predicate": "burned out",
        "normalized_predicate": "burn_out",
        "normalization_rule": "verb_lemma"
      },
      "arguments": {
        "actor": {
          "role": "actor",
          "text": "I",
          "entity_ref": "user"
        },
        "time": {
          "role": "time",
          "text": "by 2025"
        }
      },
      "polarity": "positive",
      "modality": "asserted",
      "holder_ref": "user",
      "attribution_mode": "direct_speaker",
      "temporal_anchoring": {
        "normalized_value": "2025",
        "anchor_type": "exact",
        "source_expression": "by 2025",
        "reference_anchor": null
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
        "char_start": 126,
        "char_end": 173,
        "text": "I will never work for a giant corporation again"
      },
      "kind": "attitude",
      "predicate": {
        "surface_predicate": "work",
        "normalized_predicate": "work_at",
        "normalization_rule": "standard_frame"
      },
      "arguments": {
        "actor": {
          "role": "actor",
          "text": "I",
          "entity_ref": "user"
        },
        "target": {
          "role": "target",
          "text": "giant corporation",
          "entity_ref": "ent_corp"
        }
      },
      "polarity": "negative",
      "modality": "intended",
      "holder_ref": "user",
      "attribution_mode": "direct_speaker",
      "temporal_anchoring": {
        "normalized_value": "2025/..",
        "anchor_type": "bounded_range",
        "source_expression": "again",
        "reference_anchor": "u3"
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
        "char_start": 195,
        "char_end": 221,
        "text": "Small startups are riskier"
      },
      "kind": "proposition",
      "predicate": {
        "surface_predicate": "are riskier",
        "normalized_predicate": "risky",
        "normalization_rule": "standard_frame"
      },
      "arguments": {
        "theme": {
          "role": "theme",
          "text": "Small startups"
        }
      },
      "polarity": "positive",
      "modality": "asserted",
      "holder_ref": "mentor",
      "attribution_mode": "direct_quote",
      "temporal_anchoring": {
        "normalized_value": "unknown",
        "anchor_type": "unanchored",
        "source_expression": null,
        "reference_anchor": null
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
        "char_start": 231,
        "char_end": 270,
        "text": "I joined a five-person AI lab last week"
      },
      "kind": "event",
      "predicate": {
        "surface_predicate": "joined",
        "normalized_predicate": "join",
        "normalization_rule": "verb_lemma"
      },
      "arguments": {
        "actor": {
          "role": "actor",
          "text": "I",
          "entity_ref": "user"
        },
        "target": {
          "role": "target",
          "text": "five-person AI lab",
          "entity_ref": "ent_lab"
        },
        "time": {
          "role": "time",
          "text": "last week"
        }
      },
      "polarity": "positive",
      "modality": "asserted",
      "holder_ref": "user",
      "attribution_mode": "direct_speaker",
      "temporal_anchoring": {
        "normalized_value": "2026-09",
        "anchor_type": "relative",
        "source_expression": "last week",
        "reference_anchor": "evidence:occurred_at"
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
      "confidence": 0.95,
      "provenance": {
        "raw_evidence_id": "ev_2026_09_15_01",
        "semantic_block_id": "block_042"
      },
      "supporting_spans": [
        {
          "char_start": 36,
          "char_end": 43,
          "text": "because"
        }
      ]
    },
    {
      "relation_id": "rel_02",
      "source_id": "u1",
      "target_id": "u3",
      "relation_type": "BEFORE",
      "evidence_status": "explicit",
      "confidence": 1.0,
      "provenance": {
        "raw_evidence_id": "ev_2026_09_15_01",
        "semantic_block_id": "block_042"
      },
      "supporting_spans": []
    },
    {
      "relation_id": "rel_03",
      "source_id": "u3",
      "target_id": "u4",
      "relation_type": "CAUSE",
      "evidence_status": "explicit",
      "confidence": 0.9,
      "provenance": {
        "raw_evidence_id": "ev_2026_09_15_01",
        "semantic_block_id": "block_042"
      },
      "supporting_spans": [
        {
          "char_start": 114,
          "char_end": 125,
          "text": "and decided"
        }
      ]
    },
    {
      "relation_id": "rel_04",
      "source_id": "u5",
      "target_id": "u6",
      "relation_type": "CONCESSION",
      "evidence_status": "explicit",
      "confidence": 0.9,
      "provenance": {
        "raw_evidence_id": "ev_2026_09_15_01",
        "semantic_block_id": "block_042"
      },
      "supporting_spans": [
        {
          "char_start": 223,
          "char_end": 226,
          "text": "but"
        },
        {
          "char_start": 271,
          "char_end": 277,
          "text": "anyway"
        }
      ]
    },
    {
      "relation_id": "rel_05",
      "source_id": "u1:experiencer",
      "target_id": "u3:actor",
      "relation_type": "SAME_ENTITY",
      "evidence_status": "explicit",
      "confidence": 1.0,
      "provenance": {
        "raw_evidence_id": "ev_2026_09_15_01",
        "semantic_block_id": "block_042"
      },
      "supporting_spans": []
    }
  ]
}
```
