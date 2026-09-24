# SemanticBlock benchmark v0.2: pre-execution protocol

Status: **annotation preparation only**. The 24 case inputs and two blank packets exist; independent annotations, adjudicated gold, Route E implementation, and B/C/E runs do **not**. The [v0.1 audit](V01_BC_F8_AUDIT.md) identifies measurement defects; [Route E design](ROUTE_E_DESIGN.md) is a hypothesis. No production compiler change is authorized by this package.

## Scenario split and blinding

All 24 v0.2 cases form **12 unseen scenario families** (`U01`–`U12`, two contrasts each). None is copied from v0.1 B01–B18 or used as a Route E prompt example. The operator-only `operator_scenario_map.jsonl` records family/contrast assignments; annotator packets contain opaque `V2-###` IDs and Raw Evidence only. Route E development and thresholds may use v0.1 development cases and published failure analysis, but **no v0.2 case content**. B/C/E code, prompts, scorer, model revision, budgets and seed must be hashed and sealed before the route implementer receives v0.2 cases. Mere storage in the same repo is not a security boundary: the operator must deliver inputs to isolated environments and retain access records. If a route developer sees v0.2 content before sealing, the affected family is contaminated and cannot be counted as unseen; preserve the incident rather than silently substituting cases.

Two independently completed files and a third-person decision log are prerequisites to gold freeze, as specified in [adjudication protocol](ADJUDICATION_PROTOCOL.md). Until then the benchmark state is `WAITING_FOR_ANNOTATION`; no gold hash, scored B/C/E comparison, or readiness verdict may be reported.

## Comparison once gold is frozen

- **B:** exact one-pass semantic proposal and deterministic validator, source/prompt hashes pinned. Preserve its v0.1 identity or version any necessary interface adaptation separately.
- **C:** exact two-stage proposal/normalizer/linker, source/prompt hashes pinned. Preserve the raw Pass-1 proposal and final state for causal attribution.
- **E:** byte-identical B first-pass semantic proposal, then the [hard gates and selective linker](ROUTE_E_DESIGN.md). Record a paired `B + gates only`/`E without linker` ablation from the same cached B proposal. Do not silently add semantic normalization to E.

For all three use the same model revision, evidence order, cutoff, authorized context, seed/temperature when available, total input/output token ceiling, no semantic retry in the primary quality pass, and separate transient API retry accounting. Route artifacts must record model output bytes and admission decisions. An API failure counts as a failure, with a separately labeled retry sensitivity analysis if needed. Do not use v0.1 held-out or v0.2 unseen families for tuning.

The public output contract is the Issue #18 SemanticBlock state and typed relation refs. A raw-hidden consumer runs in a **separate process/container** whose only mounted inputs are public block/edge JSON and query IDs; deny filesystem and API access to Raw Evidence, annotation packets, and gold. The scorer opens gold only after predictions and access logs are sealed. Include independent human semantic-grounding review for disputed canonical claims; exact text overlap is not entailment. Match states via predeclared maximum-weight bipartite span/account assignment, log all ties and boundary disputes, and count unmatched gold states as missing rather than shrinking denominators. Distinguish runtime nonexistent endpoint from a valid predicted endpoint that fails gold alignment.

Report per family and cutoff: exact boundaries, account match, each semantic field, justified abstention, unsupported assertions, holder/utterer flips, source-span integrity and entailment, availability/cutoff, relation TP/FP/FN with direction and grounding, F7/F8 probes, replay with live-call and cache-hit modes separated, calls/tokens/latency/storage, and all hard-gate failures. Give denominators and confidence/uncertainty; no single aggregate score can override a safety gate.

## Corrected F8 measurement

The adjudicator defines `F8_PROBES.jsonl` **from case inputs and adjudicated gold, before route predictions are opened**. At minimum include v0.2 U03's positive causal sequence and negative temporal sequence, plus a regression lane on v0.1 B17 reported separately from unseen-family results. Each probe stores a gold seed state key, relevant gold endpoint keys, required directed CAUSE edge pairs, forbidden direct shortcuts, temporal distractor keys, cutoff, and `k=3`. Do not derive seeds/relevant targets from predicted suffixes or generated text. If the seed or a relevant gold state is missing from an arm's blocks, score it as missing and fail path recovery; do not remove it from the denominator.

Score two different quantities:

1. **Extraction/path gate:** map predicted states to gold, then require every specified directed CAUSE edge and the full path; forbid unsupported direct shortcuts and BEFORE→CAUSE substitution. Check every relation endpoint exists among **admitted cutoff-visible predicted states**. Report missing block, missing edge, wrong direction, and invalid cue separately. Negative probe passes only with no prohibited causal edge or path.
2. **Retrieval gate:** for each arm's own accepted blocks, compare vector-only and vector+admitted-relations over the **same candidate universe**, query/embedding model, seed, and final **total candidate budget `k=3`**. The graph may propose and rerank but may not append a fourth result. Count seed inclusion consistently in both arms. Map final candidates to gold and compute precision, recall, and candidate volume with the fixed gold relevant set. Log ranked IDs, scores, edge provenance, graph-proposed IDs, accepted IDs, and per-family deltas. BEFORE edges have no generic bridge traversal; verify zero BEFORE-derived proposals, not merely a false traversal flag. Also run a BEFORE-enabled diagnostic ablation without treating it as an authorized route.

A graph retrieval gain is valid only if the extraction/path gate and fixed-budget retrieval gate both pass. Compare B/C/E separately. Never call the v0.1 F8 `PASS` or 33.3%→100% claim verified by this new protocol.

## Freeze and stop sequence

1. Receive and hash A and B independent completed files; validate spans/cutoffs/completeness.
2. Adjudicator resolves disagreements and signs the decision log; freeze new gold and scorer/probe manifests together.
3. Confirm B/C/E route hashes were sealed before v0.2 access; run each once and preserve first-run artifacts.
4. Publish per-family comparison and raw-hidden/F8 evidence; give an evidence-bounded verdict. No production code, migration, or GraphRAG integration under this benchmark task.

The current handoff stops **before step 1**. No v0.2 gold should be generated from this case-authoring script or from v0.1 gold.
