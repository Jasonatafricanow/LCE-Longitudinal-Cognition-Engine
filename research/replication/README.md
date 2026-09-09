# Public Semantic Replication Surface

Status: harness available; **BUNDLED PUBLIC REAL-CORPUS REPLICATION: NOT PROVIDED**

This directory provides a provider-agnostic replay surface for **precomputed semantic vectors**. It exists so interested reviewers or users can test LCE with a real embedding model without adding an embedding SDK or network dependency to standalone LCE Core.

## Evidence responsibility boundary

The historical LCE research used private longitudinal material. That original source material is not required to be published in order for the implementation, method, and replication procedure to be open.

> **Public reproducibility requires a reproducible method, not disclosure of private longitudinal evidence.**

This harness is therefore an **available replication interface**, not a promise that the maintainer will publish the original corpus or manufacture a substitute dataset merely to populate an evidence matrix.

A third-party or maintainer-run public replication may be added later if someone has a suitable public or appropriately sanitized corpus. Such a run would be additional empirical evidence, not a V1 authority prerequisite.

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

## How an interested reviewer can perform a public semantic replication

A reviewer may use any embedding provider or local model. LCE does not require one vendor.

A suitable replication procedure is:

```text
public or appropriately sanitized longitudinal corpus
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

## What counts as a public semantic replication

The label applies only after a real public/sanitized corpus and a real semantic embedding run are committed with enough metadata for independent reproduction.

These do **not** qualify:

- the 16-dimensional token-hash fallback in standalone runtime;
- hand-authored fixture vectors;
- the small synthetic boundary experiments elsewhere under `research/`;
- a prose claim that a private 3072-dimensional historical run existed;
- an embedding run whose model/version/input corpus cannot be reconstructed.

Until such a contribution exists, `docs/PUBLIC_EVIDENCE_MATRIX.md` records the public-semantic-replication column as `NOT BUNDLED`. That status is descriptive, not a statement that LCE V1 is unfinished.

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
