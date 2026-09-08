# LCE Research

This directory contains small, reproducible experiments that support LCE design decisions.
They are deliberately independent from the LCE Core implementation and use only synthetic,
offline inputs.

The experiments record falsifiable boundaries rather than presenting a large collection of
historical runners:

- [Semantic neighbourhood](experiments/semantic_neighbourhood/README.md): similarity discovers candidates, not truth.
- [Region discovery](experiments/region_discovery/README.md): candidate structure should remain inspectable and preserve isolated evidence.
- [Temporal cutoff](experiments/temporal_cutoff/README.md): longitudinal evaluation must enforce no-future visibility.

These experiments do not define canonical cognition, replace LCE Core authority, or claim that
any interpretation is automatically canonical. Run them offline with:

```text
python -m pytest tests/research -q
```

Further design notes are collected in [`docs/research/`](../docs/research/).
