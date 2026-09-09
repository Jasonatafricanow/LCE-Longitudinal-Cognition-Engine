# External Adversarial Audit Protocol

Status: current public-review protocol

The purpose of this protocol is not to obtain another friendly architecture summary. It is to challenge a frozen LCE implementation and its verification claims from outside the implementation loop.

## 1. Freeze the target

Record:

```text
repository
commit SHA
date of audit
reviewer identity or model/provider/version
operating system
Python version
```

Do not audit a moving branch name without also recording the exact resolved SHA.

## 2. Do not trust the closure verdict

The auditor may read architecture and boundary documentation to understand intended behavior, but must treat statements such as `closed`, `verified`, `30/30`, or `139 passed` as claims to reproduce rather than premises.

The recommended order is:

1. clone/checkout the frozen SHA;
2. read `docs/VERIFICATION.md`;
3. run the canonical public gate;
4. inspect implementation/tests;
5. only then compare findings with historical closure reports.

## 3. Reproduce the canonical software gate

Run:

```bash
python -m pip install -e . -r requirements-verification.txt
python scripts/verify.py
```

Preserve the complete output or CI link. Record any deviations in tool version or command.

A different command is useful evidence, but it must not be described as reproducing the canonical gate unless it actually matches it.

## 4. Mandatory challenge surfaces

The audit must attempt to break at least these boundaries.

### A. Authority leakage

Try to make a derived artifact become factual source authority through repeated use, retrieval, promotion, or rebuild.

Expected invariant:

```text
vector / structure / candidate / Worktree / Baseline
!= Raw Evidence authority
```

### B. Replay and support inflation

Try duplicate source, recap-only state growth, reordered selected support, repeated snapshot evaluation, and restart replay.

Expected invariant: repeated consumption or provenance-only change does not manufacture qualifying cognition support.

### C. Selected-state provenance

Construct a case where an older immutable Semantic Block state is the authorized cutoff selection while a newer state exists.

Expected invariant: package, Worktree, Baseline, read, restart, and rebuild retain the exact selected state rather than silently replacing it with latest state.

### D. Durable-effect recovery

Inject failures before and after durable Worktree/support/promotion effects.

Expected invariant:

```text
before durable cognition effect -> retry may be legal
after durable cognition effect  -> reuse committed effect
missing downstream marker       -> resume bookkeeping, not cognition
```

### E. Temporal cutoff leakage

Attempt to make evidence occurring after a cutoff affect an earlier snapshot or longitudinal claim.

Expected invariant: no future evidence enters the earlier visibility state.

### F. Test-oracle weakness

Do not assume existing fixtures span all legal provider/interpreter behaviors. Vary ordering, subset selection, package sensitivity, deterministic IDs where legal, and failure location. If a stronger legal fixture changes a green result, preserve that discrepancy.

## 5. Optional challenge surfaces

Reviewers are encouraged to probe:

- semantic-provider failure barriers;
- invalidation and correction after source supersession;
- content-equivalent candidate promotion;
- multi-membership/local-structure assumptions;
- read-time mutation or reasoning;
- unsupported higher-order interpretation;
- Temporal UNKNOWN handling and fabricated chronology;
- Semantic UNKNOWN handling and speculative meaning.

## 6. Verdict vocabulary

Each reviewed claim should use one of these verdicts:

- `SUPPORTED` — reproduced or directly supported by inspected public evidence;
- `PARTIALLY SUPPORTED` — a narrower form is supported but the repository wording is broader;
- `NOT REPRODUCED` — attempted reproduction did not establish the claim, without sufficient evidence to contradict it;
- `CONTRADICTED` — public evidence or an executable counterexample conflicts with the claim;
- `OUT OF SCOPE` — the claim is not part of the frozen target or cannot be evaluated from the available public surface.

Avoid a single overall score that hides disagreement across surfaces.

## 7. Preserve disagreement

If the audit disagrees with repository claims:

1. quote or identify the exact claim/file;
2. give reproduction commands;
3. give the smallest counterexample or failing fixture;
4. record raw output;
5. state whether the issue is implementation, documentation, environment/toolchain, test-oracle, or research-evidence scope;
6. do not rewrite the report after maintainers respond. Add a separate resolution note if needed.

The repository should be allowed to be wrong in public.

## 8. Independence labels

Use precise labels:

```text
INTERNAL AUDIT
  reviewer participated in the implementation/closure process

EXTERNAL ADVERSARIAL REVIEW
  reviewer did not implement the target change and attacks a frozen public SHA

INDEPENDENT SCIENTIFIC VALIDATION
  requires a stronger institutional/data/method independence standard and is not implied by using another AI model
```

A Claude/Gemini/GPT review performed under this protocol qualifies at most as `EXTERNAL ADVERSARIAL REVIEW` unless stronger independence actually exists.

## 9. Report storage

Commit completed reports under:

```text
docs/audit/reports/YYYY-MM-DD-<reviewer>-<short-sha>.md
```

Use [`REPORT_TEMPLATE.md`](REPORT_TEMPLATE.md). Supporting fixtures may be committed under `tests/audit/` or a report-specific subdirectory when they are safe and reproducible.

## 10. Why this protocol exists

LCE Finding F09 says a green suite is only as strong as its oracle and fixtures. That rule must apply to LCE's own closure evidence.

The next verification layer is therefore:

```text
implementation
-> internal oracle
-> reproducible public gate
-> external adversarial challenge
-> disagreement investigation
```

The external audit is not authority merely because it is external. Its value comes from frozen inputs, reproducible procedures, preserved counterexamples, and an oracle that was not designed solely to confirm the implementation being reviewed.
