# Public Verification Track Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make LCE's public evidence and verification surface independently reproducible, clearly scoped, and suitable for adversarial external review.

**Architecture:** Keep standalone LCE Core unchanged. Add a pinned public verification toolchain and one canonical verification command; expose claim-by-claim public evidence status; define an external audit protocol that does not trust existing closure reports; add a provider-agnostic semantic-replication surface that consumes precomputed real embeddings without binding an embedding vendor into Core.

**Tech Stack:** Python 3.12, pytest, mypy, Ruff, GitHub Actions, Markdown, JSONL for replication fixtures.

**Spec:** `docs/ENGINEERING_CHALLENGES_AND_BOUNDARIES.md` and `docs/ARCHITECTURE_REVALIDATION.md`

## Global Constraints

- Do not change LCE authority semantics, runtime state transitions, schemas, or promotion behavior.
- Keep the installable LCE package dependency-free; verification/research dependencies remain development-only.
- Historical private-corpus evidence, public synthetic reproduction, public semantic replication, runtime invariants, and external audit evidence must remain distinct.
- Do not claim a public semantic replication until an executable run with real semantic vectors has completed and its artifacts are committed.
- Do not treat an AI audit as independent scientific validation; label it adversarial external review.
- Verification claims must name the exact command and pinned toolchain used.

---

### Task 1: Canonical public verification command and CI

**Files:**
- Create: `requirements-verification.txt`
- Create: `scripts/verify.py`
- Create: `.github/workflows/verification.yml`
- Create: `docs/VERIFICATION.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: existing `tests/`, `src/lce/`, `pyproject.toml`.
- Produces: `python scripts/verify.py` as the canonical local/CI verification entry point.

- [ ] Pin pytest, mypy, and Ruff in `requirements-verification.txt`.
- [ ] Implement `scripts/verify.py` to run, in order: full pytest suite, `mypy src/lce`, and `ruff check src tests`; stop on first non-zero exit and print exact command.
- [ ] Add a GitHub Actions workflow on push/PR using Python 3.12, installing only the package plus `requirements-verification.txt`, then invoking `python scripts/verify.py`.
- [ ] Document the distinction between the historical release gate and the new public reproducibility gate, including why bare `mypy` is not the same surface as `mypy src/lce`.
- [ ] Link the canonical verification entry point from README.
- [ ] Verify the workflow result on the branch before claiming the public gate is green.

### Task 2: Public Evidence Matrix

**Files:**
- Create: `docs/PUBLIC_EVIDENCE_MATRIX.md`
- Modify: `docs/research/FINDINGS.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: F01-F12, release record, public synthetic experiments, historical research records.
- Produces: one claim-by-claim table with evidence classes and explicit public-verifiability status.

- [ ] Define evidence classes: `PRIVATE-HISTORICAL`, `PUBLIC-SYNTHETIC`, `PUBLIC-SEMANTIC-REPLICATION`, `RUNTIME-REGRESSION`, `EXTERNAL-ADVERSARIAL-AUDIT`.
- [ ] Map each F01-F12 finding to the evidence classes currently available.
- [ ] Mark missing public semantic replication and external audit as `NOT YET ESTABLISHED`, never inferred from private history.
- [ ] Link each row to the exact public file/report that exists.
- [ ] Add README and Findings links to the matrix.

### Task 3: External adversarial audit protocol

**Files:**
- Create: `docs/audit/EXTERNAL_ADVERSARIAL_AUDIT_PROTOCOL.md`
- Create: `docs/audit/REPORT_TEMPLATE.md`
- Create: `docs/audit/README.md`

**Interfaces:**
- Consumes: a frozen commit SHA and the canonical verification command.
- Produces: a repeatable review procedure and raw-report format for reviewers that did not implement the code.

- [ ] Require auditor to begin from a frozen SHA and not trust existing closure verdicts.
- [ ] Require independent rerun of canonical verification and recording of tool/platform metadata.
- [ ] Require challenge areas: authority leakage, replay/support inflation, selected-state provenance, recovery after durable effects, temporal cutoff leakage, and test-oracle weakness.
- [ ] Require disagreements with repository claims to be preserved verbatim with reproduction steps.
- [ ] Label model-based reviews as adversarial external reviews, not independent scientific validation.
- [ ] Add a raw report template with verdicts `SUPPORTED`, `PARTIALLY SUPPORTED`, `NOT REPRODUCED`, `CONTRADICTED`, `OUT OF SCOPE`.

### Task 4: Provider-agnostic semantic replication surface

**Files:**
- Create: `research/replication/README.md`
- Create: `research/replication/semantic_replay.py`
- Create: `research/replication/example_blocks.jsonl`
- Create: `tests/research/test_semantic_replication_harness.py`
- Modify: `research/README.md`

**Interfaces:**
- Consumes: JSONL rows containing stable block ID, occurrence time, text, and a precomputed numeric semantic vector.
- Produces: deterministic local-neighbourhood and cutoff summaries from externally generated semantic vectors, without importing an embedding SDK into `src/lce`.

- [ ] Write a failing test for loading valid precomputed-vector JSONL and rejecting inconsistent dimensions / invalid timestamps.
- [ ] Implement a small research-only loader and cosine-neighbourhood replay that preserves chronology and emits JSON summary artifacts.
- [ ] Add an example fixture explicitly labelled topology/example data, not semantic validation.
- [ ] Document how a reviewer can generate embeddings with any provider/model and then feed the vectors into the harness; require provider/model/version metadata in the JSONL header or sidecar.
- [ ] Explicitly state `PUBLIC-SEMANTIC-REPLICATION = NOT YET ESTABLISHED` until a real public corpus + real embedding run is committed.
- [ ] Run the focused research test and canonical verification before any completion claim.

### Task 5: Final verification and review surface

**Files:**
- Modify only if verification exposes documentation or command mismatches.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: branch diff and evidence-backed readiness statement.

- [ ] Run/observe the GitHub Actions public verification workflow for the branch.
- [ ] Compare branch against `master` and confirm Core/runtime semantics were not changed except research-only harness files.
- [ ] Check all README/document links to new verification, evidence, audit, and replication surfaces.
- [ ] Report any failed gate or unexecuted semantic replication as open evidence debt rather than calling the track complete.
