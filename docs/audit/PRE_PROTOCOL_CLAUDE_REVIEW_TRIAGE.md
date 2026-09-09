# Pre-Protocol Claude Review Triage

Status: **PRE-PROTOCOL EXTERNAL REVIEW — does not count as `EXTERNAL-ADVERSARIAL-AUDIT` evidence**

This document preserves the engineering issues raised by an external Claude review that cloned the public repository and reported local test/type/lint observations before the formal external-audit protocol existed.

The original review did not record enough metadata to satisfy the current audit protocol: in particular, the exact target commit SHA and complete raw command/log bundle were not preserved in-repository. It is therefore retained as review input, not promoted into the Public Evidence Matrix's external-audit column.

## Review claims and current disposition

| Review observation | Disposition after repository inspection/public gate work |
| --- | --- |
| The 139-test release claim reproduced locally | **Supported as historical release evidence.** The new public gate later expanded the suite to 142 tests after adding replication-harness contract tests. |
| `mypy 2.3.1` produced about 60 errors while the release record said mypy was clean | **Command-surface mismatch identified.** `pyproject.toml` makes bare `mypy` inspect `src + tests`; the release record explicitly claimed `mypy (src/lce): clean`. The new public gate pins mypy 2.3.1 and runs `mypy src/lce`; GitHub Actions reports no issues in 32 source files. Bare `mypy` is still a different, broader claim and is not silently relabelled as clean. |
| Ruff reported one unused variable while the release record said Ruff was clean | **Environment/target details were insufficiently recorded in the pre-protocol review.** The new public gate pins Ruff 0.16.6 and runs `ruff check src tests`; GitHub Actions reports all checks passed. This does not erase the older observation; it makes the current reproduction surface explicit. |
| `deterministic_block_embedding` is a 16-dimensional token-hash vector and therefore only a toy semantic representation | **Partly supported.** The standalone fallback is intentionally a deterministic 16-dimensional hash/count vector. Runtime can also consume supplied vectors, and `docs/reference-memory.md` describes the fallback as a topology/reference seam rather than semantic-model validation. |
| The historical structural findings therefore came from the same 16-dimensional toy space | **Not supported by the historical record, but the review exposed a real public-evidence gap.** Historical INSPIRATION-05 / STRUCTURE-06R records describe a frozen 3072-dimensional semantic space; however, the original private corpus/lab artifacts are not publicly reproducible from this repository. The correct public limitation is not 'history used the 16-d fallback'; it is 'the historical 3072-d claims lack a public semantic replication'. |
| The polished research narrative is retrospective and the original full lab sequence is not publicly reproducible | **Supported.** The repository already labels the narrative as retrospective synthesis and the public `research/` experiments as selected synthetic boundary tests rather than full historical replay. The new Public Evidence Matrix makes this evidence-class distinction explicit. |
| Closure reports are still part of the same project production process and therefore self-attested | **Supported as an external-verification limitation.** Internal adversarial testing is useful but does not create reviewer independence. The repository now defines a frozen-SHA external adversarial audit protocol and keeps the corresponding evidence class `NOT YET ESTABLISHED` until a compliant report exists. |
| A real semantic embedding replication and an external adversarial audit are the next high-value steps | **Accepted.** A provider-agnostic precomputed-vector replay harness and evidence matrix are now public. A real public/sanitized semantic run and protocol-compliant external audit remain explicit evidence debt. |

## Why this review mattered

The most important correction was not to defend the repository by adding more prose. It was to apply LCE Finding F09 to LCE's own verification authority:

```text
implementation
-> internal oracle
-> reproducible public gate
-> external adversarial challenge
-> disagreement investigation
```

The review also forced a stricter separation between:

```text
PRIVATE-HISTORICAL evidence
PUBLIC-SYNTHETIC evidence
PUBLIC-SEMANTIC-REPLICATION
RUNTIME-REGRESSION evidence
EXTERNAL-ADVERSARIAL-AUDIT evidence
```

A stronger class cannot be inferred merely because a weaker or different class exists.

## Current status

This review remains **pre-protocol** and must not be cited as a completed external audit. To upgrade the evidence class, a reviewer must target an exact frozen SHA and follow [`EXTERNAL_ADVERSARIAL_AUDIT_PROTOCOL.md`](EXTERNAL_ADVERSARIAL_AUDIT_PROTOCOL.md), preserving raw reproduction steps and disagreements.
