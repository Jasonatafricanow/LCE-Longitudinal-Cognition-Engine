# SemanticBlock v0.3 Corpus Package

Status: **DRAFT_SINGLE_AUTHOR_UNADJUDICATED**

Authority:
- `docs/architecture/SEMANTIC_BLOCK_DESIGN_FREEZE_2026-09-25.md`
- `docs/research/SEMANTIC_BLOCK_V03_FIDELITY_GRANULARITY_EXPERIMENT.md`

This package is the first concrete corpus for testing SemanticBlock semantic fidelity, reconstructability, useful granularity, and recall utility.

It is intentionally **not** a production benchmark yet. The cases and gold were authored in one pass and have not received independent blind adjudication. Do not report held-out performance as external or independent validation until the adjudication state changes.

## Files

- `cases_v0_3.jsonl` — 48 core dialogue cases.
- `gold_v0_3.jsonl` — gold semantic accounts and explicit known/unknown/forbidden boundaries.
- `contrast_groups_v0_3.json` — same-meaning/different-surface and similar-surface/different-meaning groups.
- `temporal_forks_v0_3.jsonl` — 4 identical-prefix scenarios, each with 3 different futures (12 branch records).
- `retrieval_queries_v0_3.jsonl` — semantic recall queries with targets and hard negatives.
- `split_manifest_v0_3.json` — 32 dev / 16 held-out core split plus temporal fork split.
- `ADJUDICATION_GUIDE.md` — blind review instructions.

## Core design rule

A SemanticBlock must support both:

1. **reconstructability** — a downstream consumer can recover the original time-local meaning without Raw Evidence;
2. **useful granularity** — the representation exposes enough semantic structure for selective recall and contrastive discrimination.

The trivial solution `SemanticBlock = raw dialogue` is a control, not a valid preferred design.

## Gold philosophy

Gold records separate:

- `must_preserve` — information that is actually established at the cutoff;
- `must_not_claim` — stronger or different claims the evidence does not support;
- `legitimate_unknowns` — uncertainty that must remain unresolved unless later evidence appears.

UNKNOWN is valid only where reality is genuinely underdetermined. It is not permission to erase already-known information.

## Split discipline

Equivalent/paraphrase siblings are kept in the same split. Held-out families are not disjoint from dev, so this package must **not** be described as unseen-family evaluation.

## Next required step before execution

Run independent blind annotation/adjudication against `gold_v0_3.jsonl`.

The adjudicator should receive:
- case dialogue up to cutoff;
- draft gold semantic account;
- must-preserve / must-not-claim / legitimate-unknown candidates.

The adjudicator should not receive:
- implementation outputs;
- model prompts;
- retrieval scores;
- future branches when judging a prefix cutoff.

After adjudication:
1. write adjudicated gold to a new file;
2. record disagreement and unresolved points;
3. freeze file hashes;
4. only then run P0-P4.
