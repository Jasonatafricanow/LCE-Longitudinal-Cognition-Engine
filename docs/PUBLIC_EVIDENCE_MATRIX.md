# Public Evidence Matrix

Status: public-verifiability index

This matrix answers a narrower question than the research narrative:

> **For each LCE finding, what kind of evidence can an external reader inspect or rerun today?**

It deliberately separates evidence classes that should not be collapsed into one confidence label. It is **not** a completion checklist that requires every column to be filled before LCE V1 is legitimate or complete.

## Evidence responsibility boundary

Historical empirical observations were produced from private longitudinal material. That original source material may remain private.

> **Public reproducibility requires a reproducible method, not disclosure of private longitudinal evidence.**

The maintainer responsibility is to make public claims accurately scoped and to expose inspectable code, protocols, verification commands, fixtures, and replication interfaces where appropriate. It is not to disclose sensitive/private longitudinal records or fabricate a pseudo-real replacement corpus merely to make every evidence column non-empty.

Likewise:

> **Third-party replication and external audit are additional evidence, not authority prerequisites for LCE V1.**

Interested reviewers/users can add those evidence classes using the published surfaces. Their absence means only that the repository does not currently bundle or record that additional evidence.

## Evidence classes

| Class | Meaning |
| --- | --- |
| `PRIVATE-HISTORICAL` | The project record documents an experiment or observation from a non-public historical corpus/lab artifact. Useful for provenance and design history, but not independently reproducible from this repository alone. The source corpus is not required to be disclosed. |
| `PUBLIC-SYNTHETIC` | A small public synthetic/offline experiment can be rerun from this repository to test a selected mechanism or boundary. It is not a replication of the original private corpus. |
| `PUBLIC-SEMANTIC-REPLICATION` | A public or appropriately sanitized longitudinal corpus has been rerun with a real semantic embedding/model and committed artifacts allow independent reproduction. This is an optional additional evidence class, not a V1 release gate. |
| `RUNTIME-REGRESSION` | The claim is encoded as executable runtime/closure tests or deterministic implementation contracts in the public repository. |
| `EXTERNAL-ADVERSARIAL-AUDIT` | A reviewer that did not implement the change reran a frozen SHA, challenged the stated invariants, and committed a raw audit report under the external-audit protocol. This is additional review evidence, not independent scientific validation or a V1 authority prerequisite. |

Status vocabulary:

- `NOT BUNDLED` — this repository does not include a protocol-compliant public real-corpus replication for that finding;
- `NO THIRD-PARTY AUDIT RECORDED` — no protocol-compliant external audit report is currently committed for that finding;
- `NOT APPLICABLE` — that evidence class is not needed to evaluate the stated engineering invariant.

None of these labels means “unfinished V1.” Another evidence class also cannot silently substitute for one that is explicitly absent.

## Finding-by-finding matrix

| Finding | Private historical | Public synthetic | Public semantic replication | Runtime regression | External adversarial audit | Current public claim strength |
| --- | --- | --- | --- | --- | --- | --- |
| **F01 Similarity discovers relatedness, not cognition** | Yes — POINTCLOUD-01/01R history | Yes — `research/experiments/semantic_neighbourhood/` | **NOT BUNDLED** | Partial — authority boundaries prevent similarity from self-promoting | **NO THIRD-PARTY AUDIT RECORDED** | Publicly reproducible as a boundary; historical real-embedding observations remain private-corpus evidence |
| **F02 Raw text is evidence, not the corrected cognition point** | Yes — SEMANTIC-CLOUD-02 history | No full segmentation replication | **NOT BUNDLED** | Yes — Raw Evidence and Semantic Block authority are separate contracts | **NO THIRD-PARTY AUDIT RECORDED** | Runtime ownership is public; historical segmentation measurements remain private-corpus evidence |
| **F03 Semantic continuity != arbitrary time bucket** | Yes — BLOCK-03 history | No full BLOCK-03 reproduction | **NOT BUNDLED** | Partial — compiler/runtime keep semantic identity and occurrence order separate | **NO THIRD-PARTY AUDIT RECORDED** | Frozen design boundary with private historical measurements; public replication surface is available |
| **F04 Longitudinal claims require no-future evaluation** | Yes — TREND-04 history | Yes — `research/experiments/temporal_cutoff/` | **NOT BUNDLED** | Yes — cutoff-bound snapshots/read support are executable | **NO THIRD-PARTY AUDIT RECORDED** | Strong public boundary evidence; trend-quality generalization is not claimed |
| **F05 Exclusive clustering loses legitimate multi-membership** | Yes — STRUCTURE-06R history | Partial — public region experiment preserves weak/isolated evidence but does not reproduce the 74/97 multi-membership result | **NOT BUNDLED** | Yes — runtime structures permit overlapping participation | **NO THIRD-PARTY AUDIT RECORDED** | Runtime abstraction is public; original empirical multi-membership result remains private-corpus evidence |
| **F06 Derived structures are observations, not factual authority** | Yes — STRUCTURE-06R history | Yes — public experiments emit candidates/observations rather than truth | **NOT BUNDLED** | Yes — vectors/structures/candidates/Worktrees/Baselines cannot write themselves into Raw Evidence | **NO THIRD-PARTY AUDIT RECORDED** | Strong public architecture/runtime evidence |
| **F07 Provenance identity != qualifying cognition-support identity** | Yes — Z1/Z2/R3 history | Not needed for the runtime invariant | **NOT APPLICABLE** | Yes — closure/regression tests preserve selected state and support identity separately | **NO THIRD-PARTY AUDIT RECORDED** | Strong public runtime invariant; third-party challenge is optional additional evidence |
| **F08 Replay/recap/repeated consumption must not manufacture support** | Yes — Z2/R3 history | Not needed for the runtime invariant | **NOT APPLICABLE** | Yes — replay/recap/order regressions are executable | **NO THIRD-PARTY AUDIT RECORDED** | Strong public runtime invariant; third-party challenge is optional additional evidence |
| **F09 Green suites are insufficient when the oracle is weak** | Yes — Z0–Z3 history | **NOT APPLICABLE** | **NOT APPLICABLE** | Yes — retained RED→GREEN and package-sensitive recovery tests document the stronger oracle | **NO THIRD-PARTY AUDIT RECORDED** | Public self-critique is executable; an external challenge would add evidence but is not a completion condition |
| **F10 Interpretation should consume bounded evidence, not search freely for support** | Yes — TREND-04/INSPIRATION-05 history | Partial — public experiments preserve bounded candidate/evidence roles | **NOT BUNDLED** | Yes — bounded interpretation package and deterministic read path are public | **NO THIRD-PARTY AUDIT RECORDED** | Strong public authority boundary; semantic-quality generalization is not claimed |
| **F11 Temporal ordering is part of longitudinal evidence** | Yes — TREND-04 and later retrospective boundary | Yes — temporal cutoff experiment demonstrates ordered/no-future visibility | **NOT BUNDLED** | Yes — occurrence time/cutoff ordering is first-class in runtime | **NO THIRD-PARTY AUDIT RECORDED** | Frozen boundary publicly inspectable; broader empirical replication is optional additional evidence |
| **F12 Semantic UNKNOWN is a valid stopping point** | Yes — weak higher-order results in INSPIRATION-05/STRUCTURE-06R | No full higher-order replication | **NOT BUNDLED** | Yes — higher-order candidates remain derived proposals and interpretation can fail closed | **NO THIRD-PARTY AUDIT RECORDED** | Runtime stop boundary is public; original higher-order precision observations remain private-corpus evidence |

## Optional additional evidence surfaces

Two columns are intentionally sparse because they represent evidence that may be contributed by interested reviewers/users rather than release obligations on the maintainer.

### Public semantic replication

The historical research record includes a frozen 3072-dimensional semantic-space replay, but the original private corpus/lab artifacts are not published and are not required to be published.

The public repository therefore does not describe those historical measurements as public replications. Instead it exposes a provider-agnostic replication surface so an interested party can test the method with a public or appropriately sanitized corpus and a real embedding model.

A protocol-compliant contribution would normally include:

```text
public/sanitized longitudinal corpus
+ named embedding provider/model/version
+ committed input manifest / vector metadata
+ deterministic replay code
+ committed raw summary artifacts
+ explicit comparison with the historical finding
```

Until somebody contributes such a run, the matrix says `NOT BUNDLED`. That label records the evidence surface accurately; it is not an outstanding V1 requirement.

### External adversarial audit

The repository contains internal audit and closure reports. Those are useful engineering records, but they are still part of the same project production process.

If an external reviewer chooses to perform a protocol-compliant adversarial audit, the public protocol asks them to freeze a SHA, rerun the canonical public verification gate, construct their own adversarial probes, and preserve disagreements rather than accepting the repository's closure verdict.

Until such a report is committed, the matrix says `NO THIRD-PARTY AUDIT RECORDED`. Again, this is a descriptive evidence label, not a requirement that the maintainer obtain an external certification.

## Reading rule

A finding can be architecturally justified without every evidence class being present. For example, an authority boundary may be strongly supported by executable runtime invariants even when no public real-corpus semantic replication or third-party audit is bundled.

The reverse is also true: a compelling private historical result does not become publicly reproducible merely because the architecture built from it has tests.

The matrix therefore answers **what evidence exists**, not **whether an external authority has granted permission for the project to count as complete**.

Use this matrix together with:

- [`research/FINDINGS.md`](research/FINDINGS.md) — detailed claim/evidence/non-claim statements;
- [`VERIFICATION.md`](VERIFICATION.md) — canonical software verification command;
- [`ENGINEERING_CHALLENGES_AND_BOUNDARIES.md`](ENGINEERING_CHALLENGES_AND_BOUNDARIES.md) — current implementation/open-boundary status;
- [`audit/`](audit/) — external adversarial audit protocol and any reports that may later be contributed;
- [`../research/replication/`](../research/replication/) — public semantic replication surface.
