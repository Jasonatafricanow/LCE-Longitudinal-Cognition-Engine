# Issue #18: compiler, context, relation, and lifecycle recommendation

Status: **SPECIFICATION ONLY**, 2026-09-24. No production implementation is authorized by this document. [Definition and field contract](SEMANTIC_BLOCK_DEFINITION.md) is normative for this proposal; [benchmark](BENCHMARK_SPEC.md) determines whether to keep it.

## Decision summary

1. **Definition:** `SemanticBlock` is the smallest coherent, reusable, source-grounded semantic account directly consumed by longitudinal LCE; see [canonical definition](SEMANTIC_BLOCK_DEFINITION.md).
2. **Minimum contract:** readable meaning plus typed participants/predicate, polarity, modality/hedge, holder/attribution, time, uncertainty, exact spans, identity/version lineage; optional justified relation refs. Unknowns are explicit.
3. **Pipeline:** deterministic provenance and cutoff capture, bounded internal semantic proposal, deterministic validation, one public block output, then bounded cross-block linking.
4. **Internal only:** parse units, clause candidates, prompt traces, span matching, and linker search state; no new public ontology follows from research decomposition.
5. **Relations:** grounded CAUSE and SAME_ENTITY are candidate structural edges after validation; BEFORE is timing metadata and never a generic bridge; other families remain restricted pending tests.
6. **Context:** recorded, bounded, source-authorized, and cutoff-visible by both evidence and interpretation availability; no future or accepted cognition as source.
7. **Lifecycle:** immutable `state_id`s under a stable `block_id` only while the semantic account persists; new world states and changed boundaries get new block IDs; compiler changes get explicit lineages.
8. **Benchmark:** [Raw Evidence → block benchmark](BENCHMARK_SPEC.md) freezes block-only questions, 18 candidate families, held-out controls, graph ablations, hard safety gates, replay, and cost.
9. **Migration:** [read-only compatibility analysis](MIGRATION_ANALYSIS.md) recommends side-by-side versioned compilation only after the benchmark, preserving V1 selected support and correcting historical visibility.
10. **Rejected:** public atomic-unit hierarchy, topic/proposition-equals-block, in-place rewrite, lazy canonical read-time recompilation, chronology-as-causality, and unrestricted graph traversal.

[External-anchor comparison](EXTERNAL_ANCHORS_SYNTHESIS.md) evaluates Microsoft GraphRAG, AMR/UMR, PDTB, TimeML, and factuality/attribution research against LCE evidence without adopting their architectures.

## Recommended pipeline

```text
authorized Raw Evidence + versioned cutoff/context manifest
  -> deterministic source IDs, source-time, spans, and availability capture
  -> bounded semantic interpretation (internal parse and boundary candidates)
  -> deterministic validation: source alignment, attribution, time, duplicates,
     parent/child clause conflicts, required unknowns, stable endpoints
  -> one public SemanticBlock output per accepted semantic account
  -> bounded second-pass linker over admitted block states
  -> typed, evidence-backed relation references with separate traversal policy
  -> vector / structure projections; later bounded cognition remains downstream
```

The recommended research candidate combines Route 3's deterministic ownership of provenance and validation, Route 2's internal parse/normalize separation, and Route 5's bounded relation linker. It uses Route 4 only for *cutoff-visible* pronouns, continuations, and cross-entry identity/causality. It does not expose the internal parse as another public LCE layer. A one-pass arm remains in the benchmark as a cost/latency baseline. No route has yet been shown to produce a complete LCE block.

### Route decision record

| Option | Evidence | Advantages | Failure modes | Decision | Confidence | Open question |
| --- | --- | --- | --- | --- | --- | --- |
| 1. One structured LLM pass | #15 parser has strong span overlap but weaker argument-role fidelity; #17 F7 topology breaks | Simple, lower nominal latency and fewer calls | Source and semantic validation entangled; unstable replay; cross-sentence misses | Comparator, not default | Medium | Can a single pass match two-stage quality at materially lower cost? |
| 2. Internal parse then normalize/validate | #17 identifies over-segmentation and broken endpoints | Explicit checks; isolates model proposal from admission | Extra complexity and potentially latency | Keep as internal design | Medium | Which second-stage checks are actually useful? |
| 3. Deterministic provenance + LLM meaning + deterministic validation | Current V1 has source IDs/checkpoint and immutable states, but weak semantic fields | Authority split, auditability, replay manifest | Validator can prove span integrity, not truth of interpretation; silent semantic repair is unsafe | **Recommended baseline** | Medium | How much human review remains needed for critical semantics? |
| 4. Incremental context-aware compilation | #17 F7 and cross-domain identity need cross-sentence/context signals | Can resolve continuations and references | Future leakage, self-confirmation, cost growth | Bounded, cutoff-aware variant only | Medium | What context budget preserves quality? |
| 5. Block-first, deferred linker | #17 shows CAUSE severance and BEFORE bloat; #16 shows qualified relation value | Separate relation correctness from block boundary, supports re-linking | Delayed relation availability; second pass can mislink | **Recommended for cross-block relations** | Medium | When does same-pass relation extraction outperform deferred? |

All quality/cost claims above are hypotheses or narrow evidence, not production measurements. Record model, prompt, token counts, elapsed time, retry count, and output changes for every benchmark arm. A deterministic postprocessor must reject or flag invalid semantics; it must not turn `BEFORE` into `CAUSE` merely from adjacency or a connective token. A connective can trigger **review of a proposed relation** only when the scoped source spans and endpoints support it.

## Context and cutoff policy

For a compilation request, define a manifest with: requested cutoff, allowed source IDs and revisions, each source's occurrence time **and availability/admission time**, selected immutable prior block-state IDs, entity-ID namespace/version if available, compiler/model/prompt/normalizer versions, ordering key, and context-budget policy. Hash the ordered manifest for replay/audit. `occurred_at` alone cannot prove visibility: a late-arriving old diary entry or a new interpretation of old text must not appear at an earlier knowledge cutoff.

Allowed context, in order: (1) the current Raw Evidence including its own thread/session context; (2) a bounded, explicitly selected prior evidence window; (3) selected prior **source-grounded** block states visible at the cutoff; (4) authorized entity IDs if present. Every context item must satisfy both event-time relevance and availability-time cutoff, with a fixed selection algorithm and maximum count/token budget recorded in the manifest. The block's semantic assertions must still cite the current or explicit prior Raw Evidence spans; prior LCE derived cognition cannot serve as raw support. If an identity or causal interpretation requires unavailable future context, mark unresolved. Recompilation with later context is a new state/lineage event, never a silent change to an earlier snapshot.

The current `RawEvidence` contract has `occurred_at` and an ordering key but no explicit availability time. The current `list_semantic_blocks_at_cutoff()` chooses the latest state whose `occurred_end <= cutoff`; it does not filter by when that state was compiled. This is a concrete migration gate, not a reason to weaken the no-future rule. See [migration analysis](MIGRATION_ANALYSIS.md).

## Relation authority policy

Persisted does not mean eligible for graph traversal. Relation records need immutable endpoint state IDs, optional local anchors for clauses/mentions within a block, source spans, direction, qualification (explicit / warranted entailment / unresolved), confidence, compiler/linker version, and cutoff visibility. Open-world absence is `UNKNOWN`, never `NO_RELATION`. Invalid endpoint or unsupported cue means no admitted edge.

| Relation family | Persist? | Seed / one-hop retrieval | Multi-hop structure discovery | Direction and composition | Rationale / status |
| --- | --- | --- | --- | --- | --- |
| `CAUSE` | Yes, only grounded and validated | Yes, qualified | Yes, qualified causal-path traversal | Directed; a path is a chain, **not** automatic direct A→C causation | #16 F4/F7/F8 Oracle gain; #17 F7 missing cross-sentence edge. Highest value, highest parser risk. |
| `SAME_ENTITY` | Yes, with explicit or auditable identity resolution | Yes, scoped | Yes, scoped continuity traversal | Symmetric; transitive closure only inside consistent namespace/identity constraints; block meanings do not merge | #16 F6 gain; #17 false background links. |
| `BEFORE` / temporal ordering | Yes as timing metadata when grounded | Filter, sort, bounded one-hop context only | **No generic bridge traversal** | Directed partial order; temporal transitivity does not imply causation | #16 little incremental gain in tested fixtures; #17 accounts for most bloat. |
| `EQUIVALENT` / `SAME_EVENT` | Provisional, with strict identity evidence | Dedup/one-hop only pending tests | No until separately validated | Symmetry possible; transitivity requires matched holder, time, referent, event identity | #16 tested setting did not show incremental discovery; similar wording is insufficient. |
| `INCOMPATIBLE` | Only explicit local incompatibility with compatible scope/holder; otherwise higher-level candidate | One-hop explanation/negative control | No automatic multi-hop revision | Symmetric for same scope, not transitive | #16 F3 had no F1 gain; cross-time difference is not revision. |
| Discourse (`because`, `therefore`, `however`, quotation, elaboration) | Keep cue and scope as block/internal metadata | Supports relation validation | No generic traversal | Depends on cue; never infer world causation from connective alone | Useful for attribution and F7 repair but should not become equal graph authority. |
| Similarity/neighbour | Derived index only | Yes for candidate seeding | Existing vector discovery only | Symmetric score; no entailment | Retrieval utility is separate from semantic truth. |

Relation authority is conditional on the benchmark's per-family precision, endpoint stability, and downstream benefit. In particular, no unconditional CAUSE or SAME_ENTITY graph gate follows from #16/#17. Reject generic undirected expansion over all persisted relations; budget candidates per seed and log which edge family produced each candidate. A relation can be true yet not useful as an expansion bridge.

### F7/F8 handling rules

- **F7:** Preserve a cross-sentence causal account as one block when it cannot be separated without losing the causal connective; otherwise link distinct stable block states with exact cue spans. Check parent/child overlap and prohibit duplicate compound-plus-clause blocks. The linker must validate both endpoints after boundary decisions. `BEFORE` is not upgraded to `CAUSE` by chronology or a token-only heuristic. Fail closed or request review when the scope is ambiguous.
- **F8:** `BEFORE` can be stored and used for temporal filtering, but cannot enter generic undirected 2-hop bridge expansion. Cap per-seed candidate volume and measure recall and precision separately. False/low-salience SAME_ENTITY edges require provenance and relevance gates. The #17 audit attributes 14 of a net 18 extra candidates to topology amplification, but its category counts are overlapping/net-adjusted; do not treat them as an exact independently additive decomposition.

## Identity and lifecycle

- `block_id` identifies one continuing semantic account within a lineage; it is an opaque stable handle, not a hash of mutable wording. `state_id` identifies an immutable compiled state. A semantic fingerprint is for comparison/dedup, not identity or authority. The existing state chain is a starting point.
- A compatible continuation or genuinely new source detail may create a new state for the same block, retaining all source spans and the reason for change. A pure recap may add an audit attachment without creating independent qualifying support. A changed world state gets a **new block**, linked by shared entity/time only when grounded; the compiler does not emit `REVISION`.
- Later evidence clarifying old ambiguity creates a new interpretive state with its own availability time and `clarified_by` provenance. Historical cutoffs continue to select the old state. Compiler v2 re-reading old evidence creates a **new compiler lineage/version** and explicit mapping to old IDs/states; it does not overwrite them. A changed boundary/split/merge maps old block IDs to new IDs via a migration record, not reuse of one ID for a different account.
- Invalidation or supersession of Raw Evidence propagates to dependent states and derived indexes. Keep historical states for audit, but exclude invalid support from current valid reads. Rebuild projections from admitted states and recorded compiler manifest. Separately track semantic lineage and evidence authority: a compiled block never becomes independent evidence for another block.

### Decision record: lifecycle and retrieval

| Option | Evidence | Advantages | Failure modes | Decision | Confidence | Open question |
| --- | --- | --- | --- | --- | --- | --- |
| Mutable current block only | Existing current-block table is easy to read | Low operational cost | Retroactive truth and cutoff leakage; no audit | Reject | High | None for the new contract |
| Immutable states under stable block ID, new ID on boundary change | V1 already stores `state_id` and `state_version`; V1 release preserved immutable selected support | Replay, audit, bounded migration | Requires availability-time history and remapping | **Recommend** | Medium | How to expose historical selection without changing existing callers? |
| GraphRAG directly interprets Raw Evidence on every query | External GraphRAG has query-time synthesis, but Issue #18 seeks precomposed LCE products | Flexible novel queries | Repeated interpretation and authority confusion | Reject for this specific LCE objective | High | Novel-query fallback policy remains open |
| Graph index over admitted blocks and already-built structures | Issue #18 architecture; precomputed-index analogy from external GraphRAG | Recover structure and its support as a whole | Stale edges/indexes if state and cutoff are ignored | Research target, not V1 capability | Medium | Which query families benefit in LCE? |

The retrieval boundary is: **evidence retrieval** returns original source for audit; **block retrieval** returns compiled local meaning and provenance; **structure retrieval** returns a prebuilt longitudinal structure plus exact supporting block states; **cognition retrieval** returns an accepted, versioned higher-level result with its authority and support. The graph is a consumer/index, not the compiler and not an authority source. This is a target design; V1 does not currently provide the full graph path.

## Rejected alternatives and open questions

Reject a public AtomicSemanticUnit/PropositionStore/RelationOverlay hierarchy on current evidence: #13–#17 decomposed variables for experiments, not a demonstrated need for extra downstream product layers. Reject proposition-equals-block and topic-equals-block rules because both can break coherent causality or under-split independent meanings. Reject universal graph-edge traversal, chronology-as-causality, and embedding similarity as entity identity. Reject automatic `INCOMPATIBLE`→`REVISION` promotion and any accepted cognition inside the compiler.

Open questions to decide from the benchmark: exact granularity under compound clauses; whether a minimal structured field set passes block-only tasks; whether a second relation pass improves F7 without harmful latency/cost; safe entity resolution across contexts; calibrated abstention thresholds; how many prior blocks are needed for coreference; and whether graph-backed structure retrieval beats the existing vector/structure path under the same budget. All are **WORKING HYPOTHESES** until tested.

## Sources and scope of inference

Repository: [Issue #18](https://github.com/Jasonatafricanow/LCE-Longitudinal-Cognition-Engine/issues/18), [#16 report](../../../research/experiments/oracle_graph_value/ORACLE_GRAPH_EXPERIMENT_REPORT.md), [#17 report](../../../research/experiments/agy_graph_vs_oracle/AGY_GRAPH_VS_ORACLE_REPORT.md), [#17 frozen reconciliation](../../../research/experiments/agy_graph_vs_oracle/RECONCILIATION_AUDIT.md), [current compiler](../../../src/lce/semantic/compiler.py), and [current contracts](../../../src/lce/reference_memory/contracts.py). The #15 evaluation and integrity-audit reports disagree about `gold_eval_14` and relation scoring; this proposal uses their error categories and frozen predictions as leads, not their aggregate PASS label as a semantic-completeness proof.

External primary sources: [DocRED](https://aclanthology.org/P19-1074/) motivates cross-sentence relation evaluation; [cross-document event coreference evaluation](https://aclanthology.org/C16-1183/) motivates separate within/cross-context scoring; [GraphRAG paper](https://www.microsoft.com/en-us/research/publication/from-local-to-global-a-graph-rag-approach-to-query-focused-summarization/) shows the value of a precomputed graph index for its own question set. The policies here are LCE design inferences, not claims made by those papers.
