# SemanticBlock: proposed semantic contract for Issue #18

Status: **RESEARCH PROPOSAL**, 2026-09-24. This document does not change the frozen V1 runtime or certify a compiler. Read it with [the recommendation](RECOMMENDATION.md), [benchmark](BENCHMARK_SPEC.md), and [migration analysis](MIGRATION_ANALYSIS.md).

## Canonical definition

A `SemanticBlock` is the smallest **coherent, independently reusable, source-grounded semantic account** that LCE's longitudinal components can consume without parsing its original natural-language evidence again for basic meaning. It is the final lower-level semantic consumption unit. Its text is a readable canonical rendering of structured meaning, with explicit speaker/holder, event or state, polarity, modality, time, uncertainty, and provenance where applicable. It can contain more than one clause or assertion when those clauses form one inseparable semantic account. A block can be linked to other blocks, but a link does not turn either block into a longitudinal conclusion.

It is **not** raw evidence, an arbitrary text chunk or topic segment, an embedding, a one-proposition-per-node mandate, a standalone event ontology, an accepted cognition result, or a longitudinal structure. An embedding and a graph index are rebuildable projections *of* blocks. Raw Evidence stays the audit and correction substrate. A block is a compiled interpretation with explicit provenance, not new independent testimony.

## Boundary and granularity rule

The unit boundary is **semantic reusability with context intact**. A candidate can stand alone only if a downstream reader can answer who says what, about whom, when, under which qualification, using the block alone. Apply these rules in order:

1. Keep a causal or conditional compound in one block when splitting would leave a clause dependent on the other or would destroy the asserted cause/condition. Preserve its internal connective. Do not create both a parent block and duplicate child blocks.
2. Split one Raw Evidence item when it makes independently reusable claims with different holders, incompatible time scopes, or unrelated topics, and each child remains intelligible with its own grounded spans. One input may yield multiple blocks.
3. Merge or extend across Raw Evidence only when the later item continues the *same* account with compatible holder, referent, time, modality, and polarity. A recap may add provenance without counting as independent corroboration. A newly changed state is a new block, even for the same subject.
4. Link distinct blocks when identity or an explicit relation crosses a genuine boundary. Do not merge merely for shared vocabulary, timestamp adjacency, or topic.
5. If a pronoun, time, holder, or clause boundary cannot be resolved from allowed context, retain an explicit unknown/ambiguous value or quarantine the candidate. Do not fill a mandatory semantic field by guessing.

This is a proposed operational rule. Whether it yields reliable boundaries is a benchmark question, not a result of Issues #13–#17.

## Minimum sufficient field contract

`REQUIRED` means present with a value **or an explicit unknown/ambiguous marker** when source evidence cannot decide. It never licenses a default assertion. The table describes a future contract, not fields already enforced by the Python dataclass.

| Information | Classification | Rule |
| --- | --- | --- |
| `block_id`, `state_id`, `state_version`, `lineage_id`, `compiler_version` | REQUIRED | Stable object handle, immutable state handle, lineage, and reproducible compiler identity. Existing V1 names should be retained. |
| Canonical semantic content | REQUIRED | Readable, source-bounded account; never a bare copied chunk or a longitudinal judgment. |
| Subject/participants and roles | REQUIRED | Include the participants needed to understand the account; unresolved referents stay explicit. Do not require an exhaustive entity inventory. |
| Predicate/action/state and kind | REQUIRED | Distinguish assertion about an event, state, attitude, or reported proposition where that distinction changes downstream meaning. A research-internal parse need not become a public class. |
| Polarity | REQUIRED | Preserve the scope of negation; absence of negation is not proof of a positive world fact when the holder is reporting or hypothesizing. |
| Modality | REQUIRED | Separate asserted, intended, desired, possible, conditional/hypothetical, and unknown as needed; do not conflate with confidence. |
| Epistemic status/hedge | REQUIRED | Preserve speaker commitment and uncertainty separately from compiler confidence. |
| Holder/source and attribution mode | REQUIRED | Distinguish author belief, quote, indirect report, external claim, and unknown. Source of words and holder of a claim may differ. |
| Valid/event time and precision | REQUIRED | Known instant/interval/relative anchor or explicit unresolved time. Keep source occurrence, claimed validity, and compiler visibility separate. |
| Raw Evidence IDs and source spans | REQUIRED | Exact source IDs; evidence-specific spans for every semantic assertion, and relation cues where applicable. IDs alone are insufficient for a multi-claim input. |
| Entity identity references | OPTIONAL | Admit an externally authorized ID or a justified, versioned resolution; otherwise preserve local mentions and ambiguity. No identity inferred from name alone. |
| Compiler confidence/uncertainty | REQUIRED | Calibrated or categorical uncertainty per critical decision, including unresolved fields; never convert model confidence into factual authority. |
| Relation references | OPTIONAL | Only validated, versioned links with stable endpoints and evidence; absence means unknown, not false. Internal clause links may remain inside block meaning. |
| Vector, topic key, display summary | DERIVED | Rebuild from the accepted block state; never use as the semantic source of truth. |
| Parse units, candidate spans, prompt traces, beam alternatives | INTERNAL-ONLY | Useful for validation and audit, not public architecture or downstream object types. |
| REVISION, RECURRENCE, TRAJECTORY, STABLE_PREFERENCE, COGNITIVE_SHIFT, accepted status | NOT PART OF SEMANTICBLOCK | Belong to longitudinal discovery, interpretation, and authority decisions. |

The fields above may initially live in a validated, versioned subdocument inside existing `metadata`; the benchmark must decide the minimal final schema. A string `content` plus free-form `metadata` does **not** satisfy this contract by itself.

## Falsifiable semantic completeness

A block is complete enough when a block-only consumer, with no Raw Evidence text, can correctly answer or explicitly abstain on: **what** was asserted; **who** holds it; participants and referents; negation scope; modality and epistemic hedge; applicable time; exact supporting source IDs/spans; and whether a proposed `CAUSE` or `SAME_ENTITY` link has grounded, stable endpoints. Raw Evidence may still be reopened to audit, correct, or recompile. A block that needs the raw sentence to answer any of those basic questions fails completeness. Exhaustive world modeling is not required.

## Hard invariants proposed for benchmark gating

1. **Grounded:** Every semantic assertion and admitted relation has exact source support; unsupported additions are rejected. Every block traces to Raw Evidence. A span validator checks coordinate integrity, while semantic grounding needs human evaluation too.
2. **Attribution and uncertainty safe:** Quoted/reported claims never silently become user beliefs or world facts; desire, possibility, negation, and unknown remain distinct.
3. **Temporal and cutoff safe:** A state is visible only if both its supporting evidence *and its interpretation* were available at the requested cutoff. Later clarification cannot rewrite a historical answer.
4. **Composable:** Link endpoints identify immutable block states (and local anchors when needed). A chain of `CAUSE` edges supports path retrieval; it does not automatically assert a new direct causal edge.
5. **Non-cognitive:** The compiler emits local meaning and grounded local relations, not recurrence, revision, trajectory, preference, or acceptance.
6. **Versioned and rebuildable:** Same evidence set, ordered context manifest, compiler/model/prompt/normalizer versions, and settings produce equivalent semantic output or an explicit nondeterminism record. Old states remain addressable.
7. **Non-amplifying:** A recap or repeated quotation cannot become independent support solely because it created another evidence ID or block state.

Any violation blocks canonical admission for the affected output. This is a proposed fail-closed rule, not a claim that current V1 enforces it.

## Decision record: representation shape

| Choice | Option | Evidence | Advantages | Failure modes | Decision | Confidence | Open question |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | Enriched text plus metadata and links | Current V1 stores `content`, times, IDs, and untyped `metadata` | Lowest migration cost and readable | Basic semantics stay implicit; F7 and holder errors are hard to validate | Reject as final contract; keep as baseline | Medium | Can a constrained text template narrow the gap? |
| B | Full structured semantic frame | #13–#15 annotations expose relevant dimensions | Strong field-level validation and symbolic querying | Parser brittleness, high migration/storage cost, pressure to make every proposition a node | Research comparator only | Medium | Does added structure improve block-level sufficiency enough to justify cost? |
| C | Readable canonical content plus minimal typed fields | #16–#17 show relation value but also parsing and topology failures; V1 already has a block object | Preserves LCE abstraction and readability while making critical meaning testable | Dual text/fields can disagree; requires cross-field consistency validation | **Recommend for benchmark** | Medium; untested end to end | Which fields can safely be omitted without raw rereading? |

The comparison for Issue #18's operational criteria is provisional:

| Criterion | A: enriched text | B: full frame | C: hybrid |
| --- | --- | --- | --- |
| Human readability | High | Low to medium | High |
| Parser reliability | Fewer output slots, but meaning remains implicit | Many dependent slots and endpoint checks | Critical slots only; text/field agreement must be checked |
| Schema brittleness | Low apparent brittleness, high semantic ambiguity | High | Moderate |
| V1 backward compatibility | Highest | Lowest | Moderate: retains `content` and block/state IDs |
| Vector embedding quality | Depends on noisy/coarse prose | Requires rendering frame to text | Canonical content can be embedded directly; unproven advantage |
| Graph relation quality | Links depend on rereading text | Precise if parsing succeeds | Typed endpoints plus internal anchors; benchmark needed |
| Storage size | Lowest | Highest | Intermediate; measure after serialization |
| Migration cost | Lowest | Highest | Intermediate, with versioned side-by-side states |

## Evidence status

- **FROZEN DECISION:** SemanticBlock remains LCE's public lower-level semantic unit; raw evidence is provenance and correction material. See [Issue #18](https://github.com/Jasonatafricanow/LCE-Longitudinal-Cognition-Engine/issues/18) and the current [`SemanticBlock` contract](../../../src/lce/reference_memory/contracts.py).
- **EXPERIMENTALLY SUPPORTED, narrow:** #16's eight synthetic fixtures show useful oracle `CAUSE` and `SAME_ENTITY` relations beyond its vector arm; #17's four qualified Oracle-win fixtures retain 77.4% pooled gain with the frozen parser, while F7 fails and candidate count grows 26 to 44. See [#16 report](../../../research/experiments/oracle_graph_value/ORACLE_GRAPH_EXPERIMENT_REPORT.md) and [#17 reconciliation](../../../research/experiments/agy_graph_vs_oracle/RECONCILIATION_AUDIT.md). These are not block-compiler or production validations.
- **WORKING HYPOTHESIS:** Shape C and the above granularity/field rules make a directly consumable block. They require the new benchmark.
- **FUTURE POSSIBILITY:** Graph-backed retrieval of already-composed longitudinal products, conditional on quality and authority gates; current V1 structure discovery is vector-based.

External work supports *what to test*, not the LCE result: [DocRED](https://aclanthology.org/P19-1074/) documents cross-sentence relation extraction difficulty; [Modality and Negation in Event Extraction](https://aclanthology.org/2021.case-1.6/) shows why an event mention need not assert occurrence; [GraphRAG](https://www.microsoft.com/en-us/research/publication/from-local-to-global-a-graph-rag-approach-to-query-focused-summarization/) demonstrates precomputed graph summaries for a different global retrieval task. None establishes the proposed LCE contract or its production performance.
