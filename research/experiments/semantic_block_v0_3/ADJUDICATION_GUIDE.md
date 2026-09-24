# SemanticBlock v0.3 Adjudication Guide

**Status:** draft adjudication protocol  
**Purpose:** convert the single-author draft gold into an independently reviewed benchmark without changing the frozen SemanticBlock definition.

## 1. Adjudicator task

For each case, judge the meaning available **at the stated cutoff only**.

The adjudicator must answer:

1. What is actually established by the visible dialogue?
2. What is not established and must remain UNKNOWN?
3. What stronger claims would be semantic overreach?
4. Does the draft gold preserve the original meaning without adding or removing commitment?
5. Would a downstream consumer reconstruct the same meaning from the proposed gold account?

The task is not to optimize a schema.

## 2. Authority

Use:

- `docs/architecture/SEMANTIC_BLOCK_DESIGN_FREEZE_2026-09-25.md`

Do not redefine SemanticBlock during adjudication.

If a case exposes a genuine failure of the frozen definition, mark it `DEFINITION_CHALLENGE` and explain why. Do not silently patch the definition.

## 3. Blindness requirements

The adjudicator may see:

- visible dialogue up to cutoff;
- draft gold semantic account;
- draft `must_preserve`;
- draft `must_not_claim`;
- draft `legitimate_unknowns`.

The adjudicator must not see:

- compiler outputs;
- retrieval rankings;
- model prompts/configuration;
- future dialogue after cutoff;
- dev/held-out label if avoidable;
- equivalence/hard-negative group labels if avoidable.

## 4. Decision labels

For every case:

- `ACCEPT` — draft gold is semantically faithful.
- `REVISE` — the case is usable but gold wording/boundary should change.
- `AMBIGUOUS` — more than one reading is genuinely defensible from the visible evidence.
- `INVALID_CASE` — the case cannot support a stable gold target.
- `DEFINITION_CHALLENGE` — the frozen SemanticBlock definition itself appears insufficient.

For every individual gold claim:

- `SUPPORTED`
- `UNSUPPORTED`
- `TOO_STRONG`
- `TOO_WEAK`
- `UNKNOWN_SHOULD_REMAIN`
- `UNKNOWN_TOO_BROAD`

## 5. Meaning-first checklist

### A. Attribution

Check who owns each claim.

Examples of unacceptable collapse:

- “朋友说 P” → “用户认为 P”
- “老王说 HR 提过 P” → “HR 宣布 P”
- assistant question mentioning P → user asserted P

### B. Communicative function

Do not treat every proposition mentioned in text as asserted.

Distinguish where necessary:

- assertion;
- question;
- request;
- suggestion;
- correction/retraction;
- hypothetical/counterfactual.

These labels are adjudication aids, not mandatory production fields.

### C. Commitment strength

Preserve the difference between:

- asserted/certain;
- probable;
- possible;
- unknown/uncommitted;
- negated.

Do not infer objective world truth from speaker commitment.

### D. Desire, intention, obligation, and outcome

Keep these separate:

- wants X;
- plans X;
- must do X;
- did X.

A current obligation or intention is already a real present semantic fact even if the future outcome remains unknown.

### E. UNKNOWN

UNKNOWN is correct when evidence genuinely stops there.

But do not allow broad UNKNOWN to erase supported detail.

Example:

> “我朋友说公司可能下个月裁员。”

Accept:
- friend expressed possible layoffs next month;
- user endorsement = UNKNOWN.

Reject:
- “everything about layoffs is UNKNOWN.”

### F. Temporal locality

Judge only what was available at cutoff.

A later success/failure must not alter the earlier point.

For temporal forks, all branches sharing one prefix must receive equivalent prefix gold.

### G. Nonliteral language

For sarcasm, hyperbole, metaphor, idiom, or ambiguous phrasing:

- preserve the nonliteral meaning when context strongly supports it;
- do not force a literal reading;
- do not force one hidden intention when the language is genuinely ambiguous.

Case V3-045 is intentionally designed to test honest ambiguity. Do not convert ambiguity into a definite literal plan.

## 6. Reconstructability criterion

Imagine Raw Evidence is removed.

A downstream consumer receives only the gold semantic account.

Ask:

> Could the consumer recover the important original meaning without inventing missing glue?

If no, revise the gold.

But also reject a gold account that simply copies the whole raw dialogue and avoids meaningful semantic compression.

## 7. Contrastive review

After case-level adjudication, review designated pairs/groups separately.

### Same meaning, different surface

The gold accounts should remain materially equivalent when wording differs but meaning does not.

### Similar surface, different meaning

The gold accounts must preserve distinctions even when words/topics overlap heavily.

Do not make two gold accounts artificially different just because they belong to a hard-negative pair; differences must come from the source semantics.

## 8. Temporal fork review

For every fork group:

1. inspect prefix only;
2. freeze the prefix meaning;
3. only afterward inspect future branches to verify they do not require changing the earlier semantic point.

If future outcomes tempt the adjudicator to rewrite the prefix, record that as a temporal-overreach risk.

## 9. Required output

Produce `adjudication_v0_3.jsonl` with one record per core case:

```json
{
  "case_id": "V3-001",
  "decision": "ACCEPT | REVISE | AMBIGUOUS | INVALID_CASE | DEFINITION_CHALLENGE",
  "gold_semantic_account": "...",
  "must_preserve": ["..."],
  "must_not_claim": ["..."],
  "legitimate_unknowns": ["..."],
  "notes": "...",
  "severity": "none | minor | material"
}
```

Produce `temporal_fork_adjudication_v0_3.jsonl` with one record per fork group.

Any unresolved disagreement must remain explicit. Do not manufacture consensus.
