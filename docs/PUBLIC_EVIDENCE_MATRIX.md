# Public Evidence Matrix

Status: public-verifiability index

This matrix answers a narrower question than the research narrative:

> **For each LCE finding, what kind of evidence can an external reader inspect or rerun today?**

It deliberately separates evidence classes that should not be collapsed into one confidence label.

## Evidence classes

| Class | Meaning |
| --- | --- |
| `PRIVATE-HISTORICAL` | The project record documents an experiment or observation from a non-public historical corpus/lab artifact. Useful for provenance and design history, but not independently reproducible from this repository alone. |
| `PUBLIC-SYNTHETIC` | A small public synthetic/offline experiment can be rerun from this repository to test a selected boundary. It is not a replication of the original private corpus. |
| `PUBLIC-SEMANTIC-REPLICATION` | A public or sanitized longitudinal corpus has been rerun with a real semantic embedding/model and committed artifacts allow independent reproduction. |
| `RUNTIME-REGRESSION` | The claim is encoded as executable runtime/closure tests or deterministic implementation contracts in the public repository. |
| `EXTERNAL-ADVERSARIAL-AUDIT` | A reviewer that did not implement the change reran the frozen SHA, challenged the stated invariants, and committed a raw audit report under the external-audit protocol. This is still not independent scientific validation. |

`NOT YET ESTABLISHED` means exactly that. Another evidence class cannot silently substitute for it.

## Finding-by-finding matrix

| Finding | Private historical | Public synthetic | Public semantic replication | Runtime regression | External adversarial audit | Current public claim strength |
| --- | --- | --- | --- | --- | --- | --- |
| **F01 Similarity discovers relatedness, not cognition** | Yes — POINTCLOUD-01/01R history | Yes — `research/experiments/semantic_neighbourhood/` | **NOT YET ESTABLISHED** | Partial — authority boundaries prevent similarity from self-promoting | **NOT YET ESTABLISHED** | Publicly reproducible as a boundary, not yet replicated on a public real-embedding longitudinal corpus |
| **F02 Raw text is evidence, not the corrected cognition point** | Yes — SEMANTIC-CLOUD-02 history | No full segmentation replication | **NOT YET ESTABLISHED** | Yes — Raw Evidence and Semantic Block authority are separate contracts | **NOT YET ESTABLISHED** | Runtime ownership is public; historical segmentation gains are not publicly reproduced |
| **F03 Semantic continuity != arbitrary time bucket** | Yes — BLOCK-03 history | No full BLOCK-03 reproduction | **NOT YET ESTABLISHED** | Partial — compiler/runtime keep semantic identity and occurrence order separate | **NOT YET ESTABLISHED** | Frozen design boundary with private historical measurements; no public semantic replication yet |
| **F04 Longitudinal claims require no-future evaluation** | Yes — TREND-04 history | Yes — `research/experiments/temporal_cutoff/` | **NOT YET ESTABLISHED** | Yes — cutoff-bound snapshots/read support are executable | **NOT YET ESTABLISHED** | Strong public boundary evidence; trend-quality generalization remains open |
| **F05 Exclusive clustering loses legitimate multi-membership** | Yes — STRUCTURE-06R history | Partial — public region experiment preserves weak/isolated evidence but does not reproduce the 74/97 multi-membership result | **NOT YET ESTABLISHED** | Yes — runtime structures permit overlapping participation | **NOT YET ESTABLISHED** | Runtime abstraction is public; original empirical multi-membership result is not publicly replicated |
| **F06 Derived structures are observations, not factual authority** | Yes — STRUCTURE-06R history | Yes — public experiments emit candidates/observations rather than truth | **NOT YET ESTABLISHED** | Yes — vectors/structures/candidates/Worktrees/Baselines cannot write themselves into Raw Evidence | **NOT YET ESTABLISHED** | Strong public architecture/runtime evidence |
| **F07 Provenance identity != qualifying cognition-support identity** | Yes — Z1/Z2/R3 history | Not needed for the runtime invariant | Not applicable to semantic-quality replication | Yes — closure/regression tests preserve selected state and support identity separately | **NOT YET ESTABLISHED** | Strong public runtime invariant; independent adversarial rerun still pending |
| **F08 Replay/recap/repeated consumption must not manufacture support** | Yes — Z2/R3 history | Not needed for the runtime invariant | Not applicable to semantic-quality replication | Yes — replay/recap/order regressions are executable | **NOT YET ESTABLISHED** | Strong public runtime invariant; independent adversarial rerun still pending |
| **F09 Green suites are insufficient when the oracle is weak** | Yes — Z0–Z3 history | Not applicable | Not applicable | Yes — retained RED→GREEN and package-sensitive recovery tests document the stronger oracle | **NOT YET ESTABLISHED** | Public self-critique is executable, but the verification authority itself still needs external challenge |
| **F10 Interpretation should consume bounded evidence, not search freely for support** | Yes — TREND-04/INSPIRATION-05 history | Partial — public experiments preserve bounded candidate/evidence roles | **NOT YET ESTABLISHED** | Yes — bounded interpretation package and deterministic read path are public | **NOT YET ESTABLISHED** | Strong public authority boundary; semantic quality remains unreplicated publicly |
| **F11 Temporal ordering is part of longitudinal evidence** | Yes — TREND-04 and later retrospective boundary | Yes — temporal cutoff experiment demonstrates ordered/no-future visibility | **NOT YET ESTABLISHED** | Yes — occurrence time/cutoff ordering is first-class in runtime | **NOT YET ESTABLISHED** | Frozen boundary publicly inspectable; broad corpus replication remains open |
| **F12 Semantic UNKNOWN is a valid stopping point** | Yes — weak higher-order results in INSPIRATION-05/STRUCTURE-06R | No full higher-order replication | **NOT YET ESTABLISHED** | Yes — higher-order candidates remain derived proposals and interpretation can fail closed | **NOT YET ESTABLISHED** | Runtime stop boundary is public; empirical higher-order precision is not publicly replicated |

## What is currently missing

Two columns are intentionally sparse.

### Public semantic replication

The historical research record includes a frozen 3072-dimensional semantic-space replay, but the original private corpus/lab artifacts are not sufficient for an external reader to reproduce that result from this repository alone.

The public repository therefore must not describe the historical measurements as if they were already public replications.

The replication target is:

```text
public/sanitized longitudinal corpus
+ named embedding provider/model/version
+ committed input manifest / vector metadata
+ deterministic replay code
+ committed raw summary artifacts
+ explicit comparison with the historical finding
```

Until such a run exists, this column remains `NOT YET ESTABLISHED`.

### External adversarial audit

The repository contains internal audit and closure reports. Those are useful engineering records, but they are still part of the same project production process.

A protocol-compliant external adversarial audit must start from a frozen SHA, rerun the canonical public verification gate, construct its own adversarial probes, and preserve disagreements rather than accepting the repository's closure verdict.

Until such reports are committed, this column remains `NOT YET ESTABLISHED`.

## Reading rule

A finding can be architecturally justified without every evidence class being present. For example, an authority boundary may be strongly supported by executable runtime invariants even when semantic generalization is not established.

The reverse is also true: a compelling private historical result does not become publicly reproducible merely because the architecture built from it has tests.

Use this matrix together with:

- [`research/FINDINGS.md`](research/FINDINGS.md) — detailed claim/evidence/non-claim statements;
- [`VERIFICATION.md`](VERIFICATION.md) — canonical software verification command;
- [`ENGINEERING_CHALLENGES_AND_BOUNDARIES.md`](ENGINEERING_CHALLENGES_AND_BOUNDARIES.md) — current implementation/open-boundary status;
- [`audit/`](audit/) — external adversarial audit protocol and reports;
- [`../research/replication/`](../research/replication/) — public semantic replication surface.
