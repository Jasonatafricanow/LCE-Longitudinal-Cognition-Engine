# Public Semantic Replication Surface

Status: harness available; **PUBLIC-SEMANTIC-REPLICATION = NOT YET ESTABLISHED**

This directory provides a provider-agnostic replay surface for **precomputed semantic vectors**. It exists so public replication can use a real embedding model without adding an embedding SDK or network dependency to standalone LCE Core.

## What this harness does

Input is JSONL:

1. one metadata row naming the corpus and embedding provider/model/version/dimension;
2. one row per temporally placed block containing stable ID, timestamp, text, and a precomputed vector.

The harness validates dimensional consistency and timezone-aware ordering, sorts blocks chronologically, and replays cosine neighbourhoods at each prefix so future blocks cannot leak into earlier cutoffs.

Run the synthetic contract fixture:

```bash
python research/replication/semantic_replay.py \
  research/replication/example_blocks.jsonl \
  --k 2 \
  --output /tmp/lce-semantic-replay.json
```

The included `example_blocks.jsonl` is **not** a real semantic embedding experiment. Its vectors are hand-authored topology fixtures used to verify the replay contract.

## Input schema

Metadata row:

```json
{"type":"metadata","schema_version":1,"corpus_id":"...","embedding_provider":"...","embedding_model":"...","embedding_version":"...","vector_dimension":1536}
```

Block row:

```json
{"type":"block","block_id":"B001","occurred_at":"2026-01-01T12:00:00+00:00","text":"...","vector":[0.1,0.2]}
```

Requirements:

- `occurred_at` must be timezone-aware;
- every block vector must match `vector_dimension`;
- vectors must contain only finite numbers;
- block IDs must be unique;
- the metadata must name the provider/model/version that created the vectors.

## How to perform a real public semantic replication

A reviewer may use any embedding provider or local model. LCE does not require one vendor.

The replication procedure is:

```text
public or sanitized longitudinal corpus
-> define Semantic Blocks with inspectable source mapping
-> generate embeddings with a named provider/model/version
-> write the JSONL manifest with real vectors
-> run semantic_replay.py
-> commit the input manifest or a legally redistributable reconstruction recipe
-> commit raw replay summary artifacts
-> compare the observed behaviour against the historical finding being tested
```

A completed run should record at minimum:

- corpus identity/license and exact selection procedure;
- block-generation/segmentation procedure;
- embedding provider/model/version and vector dimension;
- generation date and relevant model parameters;
- exact harness commit SHA and CLI arguments;
- raw summary output;
- which historical Finding was tested;
- whether the observation replicated, weakened, contradicted, or remained inconclusive.

## What counts as `PUBLIC-SEMANTIC-REPLICATION`

The label is earned only after a real public/sanitized corpus and a real semantic embedding run are committed with enough metadata for independent reproduction.

These do **not** qualify:

- the 16-dimensional token-hash fallback in standalone runtime;
- hand-authored fixture vectors;
- the small synthetic boundary experiments elsewhere under `research/`;
- a prose claim that a private 3072-dimensional historical run existed;
- an embedding run whose model/version/input corpus cannot be reconstructed.

Until such a run is present, `docs/PUBLIC_EVIDENCE_MATRIX.md` must keep the corresponding column at `NOT YET ESTABLISHED`.

## Why this is outside Core

Standalone LCE keeps provider/model choice replaceable. Core authority semantics should not change because a reviewer swaps OpenAI, Gemini, Voyage, sentence-transformers, or another embedding implementation.

The replication surface therefore accepts vectors as experimental inputs and studies their longitudinal structural behaviour. It does not make the embedding model factual authority.

## Tests

```bash
python -m pytest tests/research/test_semantic_replication_harness.py -q
```

The canonical repository-wide gate remains:

```bash
python scripts/verify.py
```
