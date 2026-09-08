# LCE Core — Minimal Longitudinal Logical Understanding Core

`lce-core` is a lightweight, contract-first Python engine that consolidates externally supplied related memory items into durable, highly compressed long-term logical baselines (`Baseline`).

## Core Architecture & Boundaries

1. **Memory owns the points**: LCE does not own raw memory items or vector coordinates. It consumes external memory views via the read-only `MemorySubstratePort` dependency contract.
2. **Shared vector substrate**: Point cloud and semantic neighborhood discovery belong to the external vector substrate. `LceCore.consolidate(region_id, memory_ids)` consumes already-identified Memory IDs.
3. **Stable Identity Provenance**: Baselines reference immutable external `memory_id`s, entirely decoupled from transient vector coordinates or similarity scores.
4. **Deterministic Equivalence**: Duplicate or redundant memories with unchanged learned understanding do not produce meaningless revision increments (`normalize_content(candidate) == normalize_content(previous)`).
5. **Fail-Closed Validation**: The semantic consolidator produces candidate baselines that are strictly verified against authorized input memory IDs before commit. Any unknown memory reference fails closed with `UnauthorizedSourceError`.
6. **Single-Source-of-Truth Storage**: SQLite storage persists immutable `baseline_revisions`, junction `baseline_memory_refs`, and a pointer-only `baselines_head` table in an atomic transaction. Zero raw memory tables exist in LCE.
7. **Storage-Root Isolation**: Callers supply the storage root directory, ensuring independent runtimes or namespaces have strictly isolated baseline states.

## Package Layout

```text
src/lce/
├── contracts/
│   ├── external_memory.py      # MemoryItemView, MemorySubstratePort
│   ├── baseline.py             # Baseline, BaselineHistory, normalize_content
│   └── consolidation.py        # CandidateBaseline, ConsolidationResult, SemanticConsolidatorPort
├── store/
│   ├── interface.py            # BaselineStorePort
│   └── sqlite_store.py         # SqliteBaselineStore
├── core/
│   ├── equivalence.py          # is_content_equivalent
│   └── engine.py               # LceCore
└── testing/
    ├── fake_substrate.py       # FakeMemorySubstrate
    └── fake_consolidator.py    # ScriptableFakeConsolidator
```

## Production Status

```text
PRODUCTION STATUS:
MR-SIDE BINDING EXISTS
PRODUCTION ACTIVATION DISABLED
AUTOMATIC LONGITUDINAL COMPILATION OUT OF SCOPE
```
LCE Core operates contract-first against `MemorySubstratePort`. The MR-side
adapter exists as an optional integration boundary, but production activation
remains disabled and LCE Core does not own MR Memory, vectors, or current-turn
reasoning. Automatic longitudinal compilation remains research work.

## Research

The [reproducible research surface](research/README.md) contains small, offline, synthetic
experiments that document the evidence boundaries behind LCE design decisions. Additional design
notes are collected in [`docs/research/`](docs/research/).

The [research map](docs/research/research-map.md) connects each experiment to
the architectural consequence it supports and the question that remains open.
