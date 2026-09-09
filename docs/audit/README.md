# External Adversarial Audit

This directory is for reviews that challenge a frozen LCE commit without trusting the repository's existing closure verdicts.

Start with:

- [`EXTERNAL_ADVERSARIAL_AUDIT_PROTOCOL.md`](EXTERNAL_ADVERSARIAL_AUDIT_PROTOCOL.md)
- [`REPORT_TEMPLATE.md`](REPORT_TEMPLATE.md)

A model-generated review may be useful as an **external adversarial review**, but it is not independent scientific validation. Reports should identify the reviewer/model, exact commit SHA, toolchain, commands, and any custom fixtures so another reader can reproduce the disagreement.

No protocol-compliant external audit report is considered established merely because a conversational review exists outside the repository. Raw reports should be committed here only when their frozen target and reproduction steps are explicit.
