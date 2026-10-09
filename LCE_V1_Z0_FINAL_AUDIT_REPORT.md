# LCE-V1-CLOSE-Z0 — Independent Final Product Closure Audit

**REJECT — LCE V1 PRODUCT CLOSURE BLOCKED**

Audited HEAD: `16b014e1a1d3b4a225d4049d7df9615c93921dc4`.

The implementation installs and its existing tests pass. Independent runtime probes nevertheless reproduce failures in invalidation, historical provenance, higher-order separation, promotion support, ordered recovery, and substrate replacement. The runner also omits the frozen bounded-interpretation step. These are implementation failures against the V1 freeze, not objections to the research status or demands for better embedding quality.

## Actual blockers

All source paths below are relative to `C:/projects/w/lce-v1-close`; line numbers refer to the exact audited HEAD. No fixes were made.

### B1 — BLOCKER: invalidation re-accepts the old relation without establishing corrected support

- **Files/lines:** `src/lce/runtime.py:137`, `:149-165`; `src/lce/cognition/promotion.py:44-55`.
- **Observed runtime consequence:** a relation supported by `e1` and `e2` is accepted. After a later recap adds `e4` to the second block, invalidating `e1` produces a new accepted revision containing the exact old relation plus ` [corrected after invalidation]`, now citing only `e2/e4`. The relation still names the removed structure. The rebuilt space no longer supports the original two-sided relation.
- **Cause:** the correction path trims invalid block IDs, copies the old text, and uses an unconditional relaxed policy of one block, zero required structures, and one cycle. It never evaluates whether the remaining structure supports that cognition. The read API sees the trimmed current-valid IDs and serves the copied conclusion.
- **Violated frozen requirement:** invalid cognition must stop being served; localized correction may create a revision only when a genuinely changed, supported cognition warrants it. Removing an invalid source from the citation list is not correction of the understanding.
- **Minimal fix:** keep the affected understanding unavailable until the affected rebuilt support and bounded interpretation justify a replacement. If the relation no longer exists, leave it unavailable or drop its correction candidate. Do not authorize a copied conclusion through a suffix and a reduced threshold. Preserve unrelated HEADs and historical revisions.
- **Required regression:** invalidate one of the sole two supporting sides; assert that neither the old relation nor the same relation with a correction suffix is served. Assert unrelated HEAD/content/revision is unchanged. Separately demonstrate a warranted changed understanding with correct revision ancestry and valid support.

### B2 — BLOCKER: historical snapshots and accepted provenance resolve mutable future block state

- **Files/lines:** `src/lce/reference_memory/sqlite.py:284-313`; `src/lce/structure/discovery.py:157-174`, `:318-319`, `:351-355`; `src/lce/read_api.py:44-56`.
- **Observed runtime consequence:** at cutoff t2, a candidate expands to `(e1,e2)` and the snapshot contains two blocks. After a t4 recap extends one block, the *same old candidate* expands to `(e1,e2,e4)`. Recreating t2 now contains only one block because the other block's mutable `occurred_end` is t4. The accepted Baseline ID remains unchanged while its read-time source expansion also grows to include e4.
- **Cause:** continued blocks overwrite content/end time and append source references in place. Historical discovery filters the final block by `occurred_end`; candidate expansion and centroid calculation read live blocks/vectors instead of the candidate's snapshot state. Snapshot identity also lacks a block/vector revision digest.
- **Violated frozen requirement:** snapshot t represents cognition space observable at its cutoff; deleted derived observations must be reconstructible; historical candidate provenance must not acquire unsupported future sources. Immutable Baseline rows alone do not preserve an immutable expanded audit chain.
- **Minimal fix:** retain enough block/content/source/vector version information, or recorded-decision reconstruction, to resolve the exact state at a cutoff. Resolve historical candidates through that snapshot-bound state. Include the relevant input/config versions in reproducible identity. This does not require canonical Structure authority.
- **Required regression:** capture t1 snapshot, candidate expansion, and accepted support; perform CONTINUE and RECAP with new information at t2; delete/rebuild derived snapshots in chronological order; assert t1 content, visible points, vectors, structure descriptors and source closure remain equivalent and contain no t2 source. Verify the historical audit chain after invalidation as well.

### B3 — BLOCKER: duplicate observations of one local structure become a higher-order candidate

- **Files/lines:** `src/lce/structure/discovery.py:176-209`, `:312-339`.
- **Observed runtime consequence:** two points with identical vectors, `k_values=(1,)` and `min_similarity=0.9`, produce two center-indexed observations whose complete member sets are both `{A,B}`. The detector treats these as two structures and emits one higher-order candidate with strength 1. No relation between distinct existing structures has appeared.
- **Cause:** the detector excludes only pairs with the same center. Different centers and scales can describe the same local support. Shared membership immediately permits a candidate, so alternate views of one local pair supply the second apparent structure.
- **Violated frozen requirement:** more points/stronger existing structure must remain distinguishable from multiple existing structures forming a higher-order relation. This is not a request to prohibit overlapping structures: the reproduced observations have *identical full membership*, not merely legitimate overlap.
- **Minimal fix:** distinguish equivalent observations of the same local structure from independently formed structures before higher-order generation. Require a relation across the latter. Preserve overlapping/multi-membership observations in the local layer.
- **Required regression:** a local pair, additional support for that one structure, and duplicate center/k views must not alone create higher-order cognition. A separate positive case with genuinely distinct, potentially overlapping structures must still produce a bounded candidate with exact source expansion.

### B4 — BLOCKER: unrelated input promotes unchanged candidate support

- **Files/lines:** `src/lce/runtime.py:117-123`; `src/lce/cognition/worktree.py:179-186`; `src/lce/cognition/promotion.py:31-36`.
- **Observed runtime consequence:** a candidate is OPEN with one recorded support cycle. Close/reopen the runtime, then ingest an orthogonal unrelated point. Its supporting blocks and sources remain exactly the original two, but the new global snapshot ID raises support count to two and the default policy marks it MERGED. The unrelated source is not even in the accepted support set.
- **Cause:** support is keyed only by `(worktree_id, snapshot_id)`. A different cutoff/global visible set counts as new support even when candidate-relevant structure has not gained independent evidence. Exact same-snapshot insertion is idempotent, but that does not make the counted support independent.
- **Violated frozen requirement:** promotion must use genuinely distinct structural/temporal support; repeated emission of the same structure, recap, and multi-membership must not inflate acceptance. Raising a tuning threshold merely delays the reproduced failure.
- **Minimal fix:** persist candidate-relevant support identity/deltas and deduplicate equivalent observations and underlying support. Only a qualifying independent structural/temporal observation may advance the policy. A global cutoff change alone is insufficient.
- **Required regression:** after restart, replay, pure recap, duplicate source and unrelated new inputs must leave support count/HEAD unchanged. Genuine later relevant support must advance the worktree and permit promotion under the same conservative policy. Exercise this independently of B3's duplicate-structure case.

### B5 — BLOCKER: bounded interpretation is absent from the delivered runner

- **Files/lines:** `src/lce/runtime.py:54-74`, `:101-111`; `src/lce/cognition/promotion.py:39-55`, `:78-82`.
- **Observed runtime consequence:** accepted content is manufactured as `Longitudinal relation between structures <structure IDs>`. `_CandidateConsolidator` returns the stored string and IDs without using the resolved memories, previous understanding or context; it nevertheless records `provider=lce-bounded-interpreter` and `model=bounded-v1`. The runtime has no interpretation-provider injection. Its `provider` parameter controls Raw Evidence semantic compilation, not structure interpretation.
- **Violated frozen requirement:** Master A4 explicitly requires `structure / higher-order candidate → bounded interpretation → OPEN cognition worktree`, with model interpretation separated from policy acceptance. An ID label is a structural record, not implementation of this missing step. This finding is about an absent capability, not the quality of an allowed deterministic semantic/embedding fallback.
- **Minimal fix:** connect a replaceable bounded interpretation implementation through the existing consolidation boundary, supplying only the authorized structure/block/source package and recording truthful trace metadata. Feed its proposed understanding into the existing worktree/policy/Core path. Keep all interpretation off the read path and disallow self-retrieval or source expansion.
- **Required regression:** a recording interpreter must receive only the bounded support and have its proposed text reach OPEN before policy acceptance. Test reject/unknown behavior, unsupported-source rejection, meaningful changed interpretation producing one revision, equivalent interpretation producing none, and zero interpreter calls during query.

### B6 — BLOCKER: a failed input can be overtaken and become permanently unprocessable

- **Files/lines:** `src/lce/semantic/compiler.py:39-65`.
- **Observed runtime consequence:** provider failure on E1 leaves its evidence admitted. Processing E2 succeeds and advances checkpoint to `0002`. Retrying E1 then raises `ValueError: semantic stream input is out of order`. The evidence exists but has no Semantic Block and cannot be recovered through normal ordered processing.
- **Cause:** the compiler has a completed checkpoint but no durable pending/failed-input barrier. Checking that the failing call itself did not advance the checkpoint is insufficient; the next call can cross it.
- **Violated frozen requirement:** checkpoint must not pass failed material; retries must preserve ordering and no evidence may be silently lost from cognition processing.
- **Minimal fix:** preserve the earliest pending unit per lineage and fail closed on later processing until that unit completes, or otherwise recover it in the original ordered stream. Use a stable total ordering including tie handling.
- **Required regression:** fail E1, attempt E2 both before and after restart, then allow E1 to succeed; assert checkpoint never passed E1 while pending and E1/E2 eventually compile exactly once in order.

### B7 — BLOCKER: compilation and downstream runtime completion are not restart-atomic

- **Files/lines:** `src/lce/semantic/compiler.py:54-67`; `src/lce/reference_memory/sqlite.py:264`, `:300`, `:377-417`; `src/lce/runtime.py:79-94`.
- **Observed compiler consequence:** inject a failure immediately before `save_checkpoint`, after the compiled-evidence record commits. Restart and retry E1: replay is true, but checkpoint is `None`. E2 then attempts sequence 1 and raises `ValueError: block_id 'sb_f8e8e742b8_000001' already has different immutable content`.
- **Observed runner consequence:** inject one snapshot failure after E2 compilation commits. Restart/retry E2: one higher-order candidate is calculated but zero worktrees are created because `compiler_result.replayed` skips downstream evaluation. After the same next input, the faulted run remains OPEN with no accepted result while the fault-free identical corpus is MERGED. This divergence is additional to the promotion defect in B4.
- **Cause:** block writes, compiled-evidence records, and checkpoint writes commit separately. Compiler idempotency is then incorrectly used as proof that the whole cognition pipeline completed.
- **Violated frozen requirement:** restart/retry/checkpoint recovery must not lose worktree state, processing progress or accepted outcomes; the same ordered input must recover without lost work or duplicate revisions.
- **Minimal fix:** atomically commit one compilation unit, its processed marker and checkpoint through the substrate contract. Track/resume downstream completion separately with idempotent snapshot, support and promotion operations. Do not treat compiler replay as a completed runner transaction.
- **Required regression:** inject failure at every durable boundary, including split-block writes, compiled marker/checkpoint, snapshot generation, worktree support and Baseline commit; close/reopen and replay the identical corpus. Compare block identities/provenance, worktree support/status, accepted content/lineage/revisions against the fault-free run; require no missing work and no duplicate revisions.

### B8 — BLOCKER: the advertised Memory Port cannot replace the Reference backend in V1 processing

- **Files/lines:** `src/lce/reference_memory/contracts.py:130-138`; `src/lce/semantic/compiler.py:27-28`, `:40-49`; `src/lce/runtime.py:54-74`; `tests/test_reference_memory.py:21-36`.
- **Observed runtime consequence:** an independent in-memory object implementing every declared `ReferenceMemoryPort` method passes `isinstance(..., ReferenceMemoryPort)`. Passing it to the compiler fails immediately with `AttributeError: 'Replacement' object has no attribute 'compiled_block_ids'`. `LceRuntime` provides no memory injection and constructs `ReferenceMemoryStore` directly; all downstream components retain that instance.
- **Cause:** the declared port contains only evidence admission and current-valid listing, while the pipeline requires block, vector, checkpoint, validity and recovery operations from the concrete store. The replacement test exercises only admission on the double, not LCE processing. Monkeypatching several concrete instances is not the documented replacement path.
- **Violated frozen requirement:** standalone Reference Memory is optional/replaceable through an explicit contract, including a working alternate substrate/test double. **Core V0 itself still correctly uses `MemorySubstratePort`; the failure is the new V1 pipeline boundary, not the unchanged Core.**
- **Minimal fix:** expose the actual minimal consumed substrate operations and transaction/recovery semantics through explicit port(s), and permit composition with an injected backend. Use those ports in the compiler/discovery/promotion/read components; retain the reference implementation as a default.
- **Required regression:** a backend independent of `ReferenceMemoryStore` must run compile → vector projection → discovery → worktree → accepted read, including validity propagation and the backend's restart/recovery contract. Merely satisfying a runtime-checkable protocol or inheriting the concrete SQLite implementation is insufficient.

## Identity, independence and scope

- Worktree: `C:/projects/w/lce-v1-close`.
- Branch: `w/lce-v1-close`.
- Base: `c84e528a55446e33f1ac077d0df7711d09302d4b`.
- Final audited HEAD: `16b014e1a1d3b4a225d4049d7df9615c93921dc4`.
- Initial working tree: clean. Full range: **42 files, 3337 insertions, 45 deletions**.
- Reviewed all six commits in the range, not only the final report commit:

| Stage | Commit |
|---|---|
| A1 | `b838283140de5ccd9f26eaa13c968e6ad0813665` |
| A2 | `c227fdf3eeaebb8ba28b6e19df250877fc695088` |
| A3 | `4cd631f089cc6e574446d5f189bcf76867fdf35d` |
| A4 | `d92c9891cd0f2e635c29ea45d494a283591947fc` |
| A5 implementation | `ac87d712035825c361b3139ddf8dd736d022674f` |
| Closure material | `16b014e1a1d3b4a225d4049d7df9615c93921dc4` |

A fresh reviewer was explicitly started with `gpt-6-astra`, reasoning effort `high`, without implementation-agent history. It independently read source/full-range changes and ran adversarial probes. The parent auditor separately verified repository identity, background, source paths, packaging, commands, compiler fault probes and replacement behavior, then read and reran the reviewer's structural/recovery probe script. Both assessments reject closure. Implementation-agent verdicts were not used as proof.

Audit date: 2026-09-09, Asia/Shanghai. Production code, tests, dependencies, research files and Git history were not edited. Only this audit report is an intentional repository deliverable; test/cache activity and temporary verification environments are not implementation changes. No commit, merge, tag or release action was performed.

## Mandatory background and authority reconciliation

Read and reconciled:

1. This worktree's `LCE_V1_PRODUCT_CLOSURE_REPORT.md` as implementer evidence, not authority.
2. Core V0 `docs/plans/implementation_plan.md`, contracts, engine and SQLite store.
3. `C:/projects/LCE/LCE_RESEARCH_A0_AUDIT_REPORT.md` and `docs/research/LCE_DECISION_HISTORY_VERIFIED.md`.
4. BLOCK-03 report and actual `03_stream_compile.py` / `03c_dedup_recap.py`.
5. INSPIRATION-05 report, including dense pairwise/sustained-support failure surfaces.
6. STRUCTURE-06R report and source for local lenses, temporal replay, candidate packaging and structure-pair comparison; H1 remains non-authoritative.
7. A0 Product Closure audit from task `01a082ba-e517-7233-99e8-c5416c7932fc`, including its final audit response.
8. Owner-corrected freeze and complete A1–A5 Master Execution **user message** from task `01a082d6-b856-73f3-981e-8ebc591ee46f`, headed `ACCEPTED WITH OWNER CORRECTIONS`, together with the present Z0 instructions.

The owner-corrected Master and current Z0 instructions override A0 recommendations that would otherwise require Body output or heavy persistent structural lineage. No Body work is requested. Reference Memory, snapshot observation, minimal worktrees and bounded higher-order capability are intentional 2026-09-09 V1 decisions, even though historically absent from Core V0. Their historical absence is **not** a finding against V1.

Historical status is preserved: BLOCK-03 semantic boundary supported/frozen; STRUCTURE-06R local multi-scale direction supported; structure↔structure experimental quality **PARTIALLY SUPPORTED**; Core V0 linear revision/HEAD historically implemented. No runtime smoke test in this audit upgrades experimental quality to proven higher-order understanding.

## Commands and results actually obtained

Working-directory commands ran in the audited worktree unless stated otherwise.

| Command/check | Actual result |
|---|---|
| `git rev-parse HEAD`, `git branch --show-current`, `git status --short`, `git worktree list --porcelain` | Exact identity above; initial clean state |
| `git log --format='%H %s' c84e528..16b014` | All A1–A5 and report commits present in the audited range |
| `git diff --stat c84e528..16b014` | 42 files / 3337 insertions / 45 deletions |
| `git diff --check c84e528..16b014` | No whitespace errors |
| `python -m pytest -q` | **74 passed in 20.47s** |
| `python -m pytest tests/test_runtime_e2e.py -q` | **2 passed in 12.01s** |
| `python -m mypy src/lce` | **Success: no issues found in 31 source files** |
| `python -m ruff --version` | **ruff 0.16.5**, available in this audit environment |
| `python -m ruff check src tests` | **10 findings**: 7 I001, 1 RUF022, 1 F401, 1 F841; not fixed |
| AST scan of production imports against interpreter stdlib names | No undeclared third-party import roots |
| Production leakage and internal Evidence-write searches | Findings described below; no named experiment-answer decision logic or automatic cognition→Evidence path found |
| Parent compiler/replacement fault probes | B6, B7 compiler case and B8 reproduced |
| Fresh reviewer probe, independently rerun by parent | B1–B4 and B7 runner case reproduced; positive mechanisms also exercised |

Interpreter actually used: **`C:/Python314/python.exe`, Python 3.14.5**, pytest 9.0.3. The `py` launcher discrepancy in the implementer report is not a blocker and is not substituted for the verified executable.

### Fresh clean-install verification

To keep package building out of the audited checkout, exported exact HEAD with `git archive`, extracted it into a newly generated temporary directory, and created a fresh venv there. Ran normal `pip install <exported-source>` using PEP 517 build isolation. Installation built `lce_core-0.1.0-py3-none-any.whl` and succeeded.

Fresh environment root:

`C:/Users/Temp/AppData/Local/Temp/lce-z0-audit-9f4228da13624f02890a536f518a009d`

The venv interpreter ran the smoke script with **`-I`**, from outside the repository. Verified import location was `venv/Lib/site-packages/lce/__init__.py`, not the source tree. Installed distributions were only `lce-core` and `pip`; setuptools was confined to the isolated build environment. Import, one raw input, Semantic Block creation and process/close succeeded without MR.

The installed package also processed the same supplied deterministic fixture in batch and incrementally, closing/reopening after **every** nearline item. The ordered `(region_id, content, revision_number, source_refs)` results matched and were nonempty: **54 accepted entries** in each. Random Baseline UUIDs and wall-clock timestamps were excluded from semantic equivalence. This proves fault-free pipeline equivalence, not cognition quality or recovery equivalence; B7 supplies the failing recovery comparison.

Temporary reproducibility scripts retained outside the repo:

- `<fresh-environment-root>/clean_smoke.py` — installed-package import/process and nonempty batch/nearline comparison.
- `<fresh-environment-root>/parent_probes.py` — failed-input overtaking, compiler commit/checkpoint interruption, declared-port replacement.
- `C:/Users/Temp/AppData/Local/Temp/lce-z0-independent-probes.py` — structural alias, promotion inflation, historical expansion/cutoff, invalidation, downstream interruption and positive mechanism checks. These probes assert the *observed defects*, not passing frozen-contract behavior; their exit 0 is evidence of reproduction.

## Architecture fidelity and independently exercised coverage

| Area | Evidence and disposition |
|---|---|
| Raw Evidence identity, provenance, validity, supersede | Existing tests freshly passed for stable IDs across reopen, current-valid filtering, supersede link/events and retained audit history. The concrete store is a real minimal SQLite substrate. Replacement is blocked by B8. |
| Internal anti-self-pollution | Production evidence admission is from caller-supplied material in `SemanticCompiler.process`; no Baseline/worktree/HOC/structure interpretation is automatically passed back to it. Derived and noncanonical provenance rejection is present. No impossible malicious-caller intent detector is demanded. |
| Semantic compiler | Scripted-provider tests exercise continuation, semantic switch/new matter, same-unit SPLIT, RECAP without a new point, preserved new information and ordinary restart/idempotent replay. Blocks retain raw IDs. Durable failure behavior is blocked by B6/B7, not judged from model quality. |
| Vector rebuild | Independently deleted/rebuilt projections and compared exact Raw Evidence/Block objects before/after: unchanged. Fallback normally hashes block content; the fixture-vector override has the limitation noted below. |
| Point multi-membership and overlap | Exercised directly: a point appears in multiple local observations. No connected-component/exclusive-cluster assignment is the final ontology. |
| Snapshot diff, strengthening, old-point reconnection | Direct synthetic probes showed new-member/stronger-support changes and a previously isolated old point gaining a neighbor. Static snapshot deletion/rebuild test passed. Historical mutable-block cases fail B2. |
| Real structure-level operation | The detector consumes formed observations, member overlap and **structure centroids**, with a temporal-date guard for disjoint pairs. It is not simply another individual point-pair threshold renamed. A positive control with two disjoint two-member structures generated cross-structure candidates. Its alias handling still fails B3. |
| Higher-order source expansion | Current-time expansion reaches existing blocks and raw IDs; candidates are derived `UNKNOWN`, not Evidence, and there is no recursive reinsertion. Snapshot-bound historical expansion fails B2. |
| Worktree persistence and isolation | OPEN survived reopen; support grow/remove storage tests passed. Explicit DROPPED state survived restart, did not alter Main and could not be promoted/read. Default repeated-support behavior fails B4. Automatic loss/drop scheduling is not established by the manual setter tests. |
| Core reuse and same-text suppression | Promotion uses existing `CandidateBaseline`, `LceCore`, Baseline revision/previous/HEAD and SQLite atomic history. Existing tests prove equivalent text does not create a revision, while changed text does. This authority was not rebuilt as a second accepted store. B5 blocks meaningful runner-generated interpretation. |
| Invalidation dependencies | The invalidator finds affected blocks, snapshots, OPEN worktrees and historical Baseline IDs; direct invalid source filtering works. Correction is semantically unsafe under B1. It does not independently judge Evidence truth. |
| Batch/nearline | Both call the same `process` body; fault-free nonempty installed-package comparison passed. No second cognition implementation was found. Ordering and recovery fail B6/B7. |
| Accepted read API | Reads HEADs, resolves current source validity, filters OPEN/DROPPED and lexical relevance. No reasoning provider call, HEAD mutation, promotion or Evidence write is in query. The stale copied correction from B1 can nevertheless pass these checks. |
| Alternate substrate | Historical Core fake-substrate tests pass; the actual declared V1 Reference port fails processing under B8. These are distinct claims. |
| Standalone packaging | Fresh isolated install/import/process passed; production imports are stdlib plus `lce`. No `examples/` directory exists at this HEAD; examples are in quickstart docs and the synthetic test fixture, both inspected. |
| YAGNI/ownership | Four stores correspond to evidence/compiler state, disposable snapshots, candidate worktrees and existing accepted Baselines. No full MR copy, second factual truth judge, heavy canonical Structure ontology, recursive cognition engine, Body/current-turn planner, Intent/ActionPolicy or RuntimeBinding was found. Problems are missing/unsafe connections, not grounds for a broad redesign. |

## Non-blocking findings and evidence limits

### N1 — IMPORTANT NON-BLOCKING: fallback/demo assumptions are underdocumented

`src/lce/semantic/providers.py:34-65` uses caller provenance fields such as `topic`, `topics`, `semantic_content`, `recap` and `new_information`. It does not infer all those decisions from ordinary prose. `runtime.py:32-34` accepts `block.metadata['vector']`, copied from raw provenance by `semantic/compiler.py:90`; this bypasses content hashing. The E2E fixture supplies both semantic hints and predetermined vectors. Extending that block does not update this supplied vector.

The provider port is real and supports scripted/model-backed semantic decisions, and the store accepts a block embedder callable. The reference fallback is not advertised as state of the art. Consequently this audit does **not** reject the product because the fallback is simple or because synthetic vectors are used. Document the exact hints and supplied-vector lifecycle, keep deterministic fixture topology distinct from semantic accuracy evidence, and verify a content-sensitive embedder when addressing the existing composition/recovery seams. These are reference implementation limits, not proof of research-quality understanding. The absent later structure interpreter is separately B5.

### N2 — IMPORTANT NON-BLOCKING: linked-structure diff reports existing links as changes

`src/lce/structure/discovery.py:291-299` populates `linked_structures` from current overlaps without comparing the prior snapshot's links. An unchanged overlap can therefore appear in a field used to describe newly linked structures. Other diff fields do compare prior/current membership, so the entire diff API is not functionally fake. Correct the delta semantics and add an unchanged-snapshot regression when revisiting A3; do not infer new support from this field as presently implemented.

### N3 — MINOR: lint findings

Ruff is available now and reports the 10 issues listed above. They are import/export ordering and unused import/assignment issues. No fix command was run. They do not independently prevent product closure.

### Leakage checks

Explicit searches covered `SB0034`, diary-style IDs, NAS/Tailscale, known region/candidate identifiers including R11/R07, G017/G032/G057/G066, POS-SB and EMG-K/K0084, synthetic/fixture/pytest branches and MR/Body/Intent/ActionPolicy terminology. No production decision logic keyed to the lab's known answers was found. Synthetic names in tests and the explicitly named `lce.testing` helpers are allowed fixtures, not evidence of production leakage. The metadata-vector bypass is disclosed in N1 rather than falsely called a hidden diary-answer whitelist.

No algorithm leaderboard, threshold optimum, Chinese semantic quality, TDA/H1, cross-domain precision, recursive cognition beyond one level, MR/Hot Start/Body integration or performance benchmark was required for this verdict. Historical lab model experiments were read, not rerun with new models/data.

## Exact re-audit scope after fixes

Retain this audited HEAD as the comparison base. Re-audit the complete repair diff plus affected original call paths; do not limit review to new tests or the newest commit.

1. **A1/A2:** real substrate injection and consumed contracts; atomic compilation and failed-input barrier; ordering, retries and restart fault matrix. Run an independent non-Reference backend through the pipeline.
2. **A3:** cutoff-specific input/provenance reconstruction, chronological deletion/rebuild, identity/version behavior; equivalent-observation negative controls and distinct-structure positive controls; multi-membership/reconnection/strengthening retained.
3. **A4:** candidate-relevant distinct support, bounded interpreter invocation/source limits, conservative OPEN→MERGED/DROPPED behavior, unchanged-text suppression and meaningful revisions. Verify historical support is auditable.
4. **Invalidation/read:** loss of a sole supporting side must suppress the old conclusion; any replacement must be justified by valid rebuilt support; unrelated HEADs remain usable and unchanged; query remains read-only and model-free.
5. **A5/recovery:** inject failures before/after each persistent stage, restart and replay; compare nonempty batch and incremental outcomes against a fault-free reference, including support counts and revision histories.
6. Rerun `python -m pytest -q`, `python -m pytest tests/test_runtime_e2e.py -q`, `python -m mypy src/lce`, available Ruff, production leakage/import checks, and a fresh isolated package install/import/process from the repaired exact HEAD.

No new architecture research or MR/Body integration is requested. The minimal work is to make the frozen V1 boundaries real and recoverable. Until those regressions pass under independent review, the verdict remains **REJECT — LCE V1 PRODUCT CLOSURE BLOCKED**.
