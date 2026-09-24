# v0.2 route execution entry point

`runner.py` provides one shared input and one shared adjudicated gold path for
B, C, and E. Its `--dry-run` validates case IDs, cutoff lists, probe state keys,
visibility, and the in-memory field-name view required by the unchanged
legacy scorer. It makes no LLM or embedding calls.

From the repository root, check compatibility with:

```powershell
python -m research.benchmarks.semantic_block_v0_2.runner --dry-run --gold C:\projects\semantic_block_v0_2_adjudication\gold_v0_2.jsonl
```

The normal runner mode is an experiment: it calls the B/C/E adapters, scores
their predictions against that same gold file, and runs the fixed v0.2 F8
probes. It was not run for this implementation task.

`route_e.py` imports B's exact semantic system prompt and uses the same
cutoff-visible user-prompt serialization. E applies deterministic admission
gates, then invokes a bounded linker only for source-cued, admitted candidate
pairs. `f8_evaluator.py` consumes the existing `F8_PROBES.jsonl` unchanged,
requires gold-aligned directed path edges, distinguishes missing predicted
endpoints from unmatched gold alignment, and clips both retrieval lanes to
the probe's total candidate budget.
