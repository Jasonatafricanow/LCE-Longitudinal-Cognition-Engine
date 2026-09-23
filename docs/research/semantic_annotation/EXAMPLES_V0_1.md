# LCE Semantic Annotation Examples v0.1

**Status:** Frozen Reference Examples (GitHub Issue #13, Final Patch)  
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
      "normalized_predicate": "submitted_my_resignation",
      "normalization_rule": "compound_lower"
    },
    "arguments": {
      "actor": {
        "mention_id": "m_u1_act",
        "role": "actor",
        "text": "I",
        "entity_ref": "user"
      },
      "target": {
        "mention_id": "m_u1_tgt",
        "role": "target",
        "text": "Acme Corp",
        "entity_ref": "ent_acme"
      },
      "time": {
        "mention_id": "m_u1_time",
        "role": "time",
        "text": "yesterday"
      }
    },
    "polarity": "positive",
    "modality": "asserted",
    "epistemic_hedge": "none",
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
      "normalization_rule": "frozen_map"
    },
    "arguments": {
      "theme": {
        "mention_id": "m_db_1",
        "role": "theme",
        "text": "The database",
        "entity_ref": "ent_db"
      }
    },
    "polarity": "positive",
    "modality": "asserted",
    "epistemic_hedge": "none",
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

---

### 1.3 `attitude` and Nested Epistemic Hedging
- **Positive Example (Nested Attitude):**  
  *Text:* `"I think I want to leave."`  
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
      "surface_predicate": "leave",
      "normalized_predicate": "leave",
      "normalization_rule": "exact_surface"
    },
    "arguments": {
      "actor": {
        "mention_id": "m_user_leave",
        "role": "actor",
        "text": "I",
        "entity_ref": "user"
      }
    },
    "polarity": "positive",
    "modality": "desired",
    "epistemic_hedge": "think",
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
  *Analysis:*
  - `modality` is preserved as `desired` (capturing the desire stance).
  - `epistemic_hedge` explicitly preserves the outer hedging (`think`).
  - `confidence` is `1.0` (annotation accuracy is high; no arbitrary confidence reduction).

---

## 2. Relations: Mention-Based `SAME_ENTITY` and Graph Admission

### 2.1 `SAME_ENTITY` Connecting Stable Mention IDs
- **Text:** `"Alice joined the security team in June. The security team welcomed her warmly."`
  - $U_1$: `join` with argument `actor` (mention `m_alice_1`).
  - $U_2$: `welcome` with argument `target` (mention `m_alice_2`).
  - Relation:
    ```json
    {
      "relation_id": "rel_same_ent_01",
      "source_id": "m_alice_1",
      "target_id": "m_alice_2",
      "relation_type": "SAME_ENTITY",
      "evidence_status": "explicit",
      "confidence": 1.0,
      "provenance": {
        "raw_evidence_id": "ev_001",
        "semantic_block_id": "block_001"
      }
    }
    ```
  *Negative Error:* Using `source_id: "u1:actor", target_id: "u2:target"`. Pseudo-identifiers with colons are rejected. Mention IDs must be stable and explicit.

### 2.2 Frozen Graph Admission (Inferred is Audit-Only)
- **Example:**  
  *Text:* `"The database server rebooted. All connections were terminated."`
  - Relation:
    ```json
    {
      "relation_id": "rel_inferred_cause",
      "source_id": "u1",
      "target_id": "u2",
      "relation_type": "CAUSE",
      "evidence_status": "inferred",
      "confidence": 0.85,
      "provenance": {
        "raw_evidence_id": "ev_001",
        "semantic_block_id": "block_001"
      }
    }
    ```
  *Graph Policy:* This relation is retained in the benchmark record for annotator audit. Calling `to_graph_edge()` fails with an error: inferred relations **MUST NOT** be admitted into positive graphs in v0.1/#16/#17. Only `explicit` and `entailed` relations are admitted.

---

## 3. Complete Multi-Unit End-to-End Walkthrough

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
        "normalization_rule": "frozen_map"
      },
      "arguments": {
        "experiencer": {
          "mention_id": "m1_user_exp",
          "role": "experiencer",
          "text": "I",
          "entity_ref": "user"
        },
        "theme": {
          "mention_id": "m1_theme",
          "role": "theme",
          "text": "working at BigCorp"
        },
        "time": {
          "mention_id": "m1_time",
          "role": "time",
          "text": "In 2022"
        }
      },
      "polarity": "positive",
      "modality": "asserted",
      "epistemic_hedge": "none",
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
        "normalization_rule": "exact_surface"
      },
      "arguments": {
        "stimulus": {
          "mention_id": "m2_stimulus",
          "role": "stimulus",
          "text": "the scale"
        },
        "experiencer": {
          "mention_id": "m2_user_exp",
          "role": "experiencer",
          "text": "I",
          "entity_ref": "user"
        }
      },
      "polarity": "positive",
      "modality": "asserted",
      "epistemic_hedge": "none",
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
        "normalization_rule": "frozen_map"
      },
      "arguments": {
        "actor": {
          "mention_id": "m3_user_act",
          "role": "actor",
          "text": "I",
          "entity_ref": "user"
        },
        "time": {
          "mention_id": "m3_time",
          "role": "time",
          "text": "by 2025"
        }
      },
      "polarity": "positive",
      "modality": "asserted",
      "epistemic_hedge": "none",
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
        "normalized_predicate": "work",
        "normalization_rule": "exact_surface"
      },
      "arguments": {
        "actor": {
          "mention_id": "m4_user_act",
          "role": "actor",
          "text": "I",
          "entity_ref": "user"
        },
        "target": {
          "mention_id": "m4_target",
          "role": "target",
          "text": "giant corporation",
          "entity_ref": "ent_corp"
        }
      },
      "polarity": "negative",
      "modality": "intended",
      "epistemic_hedge": "none",
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
        "normalization_rule": "frozen_map"
      },
      "arguments": {
        "theme": {
          "mention_id": "m5_startups",
          "role": "theme",
          "text": "Small startups"
        }
      },
      "polarity": "positive",
      "modality": "asserted",
      "epistemic_hedge": "none",
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
        "normalized_predicate": "joined",
        "normalization_rule": "exact_surface"
      },
      "arguments": {
        "actor": {
          "mention_id": "m6_user_act",
          "role": "actor",
          "text": "I",
          "entity_ref": "user"
        },
        "target": {
          "mention_id": "m6_target",
          "role": "target",
          "text": "five-person AI lab",
          "entity_ref": "ent_lab"
        },
        "time": {
          "mention_id": "m6_time",
          "role": "time",
          "text": "last week"
        }
      },
      "polarity": "positive",
      "modality": "asserted",
      "epistemic_hedge": "none",
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
      "source_id": "m1_user_exp",
      "target_id": "m3_user_act",
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
