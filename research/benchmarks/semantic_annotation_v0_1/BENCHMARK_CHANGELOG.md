# LCE Semantic Parsing Gold Benchmark Changelog

## [v0.1.1] - 2026-09-23 (Issue #14 Revision Patch)

### Fixed
- **Scoped Substring Resolution (`make_span`):** Replaced naive document-wide `content.index(arg_text)` with strictly bounded search within the parent unit's `[source_span.char_start, source_span.char_end]`.
- **Cross-Sentence Argument Span Offsets (11 Cases / 17 Mentions):**
  - `gold_dev_09` (formerly `gold_dev_13`): Fixed `m3` (`"security team"`) in Unit 2 to span [36:49] inside Unit 2 instead of pointing to Sentence 1 [17:30].
  - `gold_dev_10` (formerly `gold_dev_15`): Fixed `m4` (`"We"`) and `m6` (`"on Monday"`) in Unit 2 to span [31:33] and [64:73] inside Unit 2 instead of Sentence 1 [0:2] and [20:29].
  - `gold_eval_22` (formerly `gold_dev_16`): Fixed `m4` (`"We"`) and `m5` (`"team sync"`) in Unit 2 to span [32:34] and [43:52] inside Unit 2.
  - `gold_eval_01`: Fixed `m4` (`"I"`) to [54:55] and `m5` (`"BigCorp"`) to [79:86] in Unit 2. Fixed relation `rel_02` (`SAME_ENTITY`) so it connects `m2` (Sentence 1 BigCorp [36:43]) to `m5` (Sentence 2 BigCorp [79:86]), eliminating self-referential mention loop.
  - `gold_eval_02`: Fixed `m4` (`"I"`) in Unit 2 to [41:42].
  - `gold_eval_03` (formerly `gold_eval_04`): Fixed `m4` (`"our team"`) in Unit 2 to [40:48].
  - `gold_eval_04` (formerly `gold_eval_05`): Fixed `m2` (`"staging server"`) in Unit 2 to [35:49].
  - `gold_dev_16` (formerly `gold_eval_06`): Fixed `m3` (`"I"`) in Unit 2 to [27:28].
  - `gold_eval_05` (formerly `gold_eval_07`): Fixed `m2` (`"database cluster"`) in Unit 2 to [41:57].
  - `gold_dev_13` (formerly `gold_eval_08`): Fixed `m2` (`"we"`) in Unit 2 to [22:24] inside main clause `"we will shard the database"`.
  - `gold_eval_06` (formerly `gold_eval_24`): Fixed `m4` (`"I"`) in Unit 2 to [48:49].
- **Unit Clause Boundary Truncation (`gold_eval_19`, formerly `gold_dev_08`):** Expanded `u1.source_span` from `"terminated the employment"` [8:33] to the full clause `"The CTO terminated the employment of the director"` [0:49], properly enclosing argument mentions `m1` (`"CTO"` [4:7]) and `m2` (`"director"` [41:49]).
- **Semantic Predicate Mislabeling (`gold_eval_16`, formerly `gold_dev_06`):** In `"the runway is four months"`, replaced incorrect nominal predicate `surface_pred="runway"` with copula verb `surface_pred="is"`, `norm_pred="is"`, `norm_rule="exact_surface"`.

### Changed / Rebalanced
- **Dev Split Rebalancing (Prompt Design Feasibility):**
  - Redistributed cases between Dev (20 cases) and Eval (40 cases) so that **every one of the 17 families is represented in Dev**.
  - Dev now includes:
    - Discourse relations (`CONDITION` with `"If"`, `CONCESSION` with `"Although"`)
    - Longitudinal shift (`BEFORE` temporal ordering across calendar years)
    - State compatibility (`EQUIVALENT` paraphrase)
    - Nested attitude (`modality: intended`, `epistemic_hedge: think`)
    - Relative temporal anchoring (anchored to `unit:u1`)
    - Ambiguous relations (`TEMPORAL_UNKNOWN`)
    - Negative control pairs (`NO_RELATION`)
    - Syntactic negation (`polarity: negative`)
  - Eval retains all 16 adversarial traps ($\ge 15$ required) and 24 held-out evaluation cases.

### Added
- **Validation Upgrades (`validator.py`):**
  - Programmatic enforcement that every argument mention's `source_span` is strictly contained within its parent unit's `source_span`.
  - Programmatic rejection of reflexive `SAME_ENTITY` relations where source and target mentions resolve to identical character offsets.
  - Programmatic verification that Dev split covers all 17 case families.
- **Automated Regression Tests (`tests/research/test_semantic_annotation_gold_benchmark.py`):**
  - `test_argument_spans_strictly_contained_in_unit_spans`
  - `test_same_entity_not_self_referential`
  - `test_dev_split_covers_all_17_case_families`
