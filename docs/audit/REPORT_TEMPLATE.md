# External Adversarial Audit Report

## Target

- Repository:
- Commit SHA:
- Audit date:
- Reviewer/model/provider/version:
- OS/platform:
- Python:
- Verification toolchain:

## Independence label

Choose one:

- `EXTERNAL ADVERSARIAL REVIEW`
- `INTERNAL AUDIT`
- `INDEPENDENT SCIENTIFIC VALIDATION` — use only when that stronger standard is actually satisfied

## Canonical gate reproduction

Commands:

```text
python -m pip install -e . -r requirements-verification.txt
python scripts/verify.py
```

Result:

- pytest:
- mypy `src/lce`:
- Ruff `src tests`:
- Raw CI/log reference:
- Deviations from canonical command/toolchain:

## Claim review

Repeat this block for each material claim.

### Claim: <exact claim or short identifier>

- Source file/section:
- Verdict: `SUPPORTED | PARTIALLY SUPPORTED | NOT REPRODUCED | CONTRADICTED | OUT OF SCOPE`
- Evidence inspected:
- Reproduction command/fixture:
- Observed result:
- Narrowest supported wording:
- Counterexample or disagreement, if any:

## Mandatory challenge surfaces

### Authority leakage

- Probe:
- Result:
- Verdict:

### Replay/support inflation

- Probe:
- Result:
- Verdict:

### Selected-state provenance

- Probe:
- Result:
- Verdict:

### Durable-effect recovery

- Probe:
- Result:
- Verdict:

### Temporal cutoff leakage

- Probe:
- Result:
- Verdict:

### Test-oracle weakness

- Legal fixture variation introduced:
- Result:
- Verdict:

## Research-evidence scope

- Which historical claims are only `PRIVATE-HISTORICAL`?
- Which boundaries have `PUBLIC-SYNTHETIC` support?
- Which claims have `PUBLIC-SEMANTIC-REPLICATION`?
- Did the audit identify wording broader than the public evidence class supports?

## Disagreements with repository claims

For every disagreement, preserve:

1. exact claim;
2. exact frozen SHA;
3. reproduction steps;
4. raw result;
5. classification: `implementation | documentation | environment/toolchain | oracle/fixture | research-evidence scope`.

Do not delete this section after a maintainer response. Add resolution notes separately.

## Overall conclusion

Do not replace the per-claim verdicts with one score. Summarize:

- strongest publicly reproduced properties;
- strongest contradiction or non-reproduction;
- evidence debts that remain;
- whether any repository Finding or boundary should be narrowed, revised, or revalidated.
