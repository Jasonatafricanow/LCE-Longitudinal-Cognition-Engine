# Implementation Plan: LCE-V0-01R — Contract-First LCE Core (Revised)

Implement a minimal, independent, contract-first LCE Core in `c:\projects\LCE` that formulates, updates, persists, and audits durable learned baselines over external memory point clouds without owning raw memory or vector infrastructure.

## Key Architectural Boundaries (Post-Review Revision)

1. **Substrate & Point-Cloud Discovery Decoupled**:
   - `MemorySubstratePort` exposes only `get_by_ids(memory_ids: tuple[str, ...]) -> tuple[MemoryItemView, ...]`.
   - Point-cloud/neighborhood discovery is external. `LceCore.consolidate(region_id: str, memory_ids: tuple[str, ...])` consumes already-identified Memory IDs.
   - `region_id` is strictly an opaque LCE baseline lineage identifier; it has no vector/cluster semantics.
2. **Deterministic Equivalence (No Heuristic Semantic Overlap)**:
   - Revision suppression is strictly: `normalize(candidate.content) == normalize(previous.content)`.
   - If candidate normalized content is identical, HEAD revision is not incremented.
   - If changed, a new revision is created and linked.
3. **Identity Separation**:
   - `baseline_id` is an independent UUID (`base_<uuid4().hex>`).
   - `content_hash` is SHA-256 of `normalize(content)`, used for deterministic comparison and audit digests.
4. **Single-Source-of-Truth SQLite Schema**:
   - `baseline_revisions`: Full immutable revision records with `UNIQUE(region_id, revision_number)`.
   - `baseline_memory_refs`: Junction table `(baseline_id, memory_id)` for provenance tracking.
   - `baselines_head`: Pointer table `(region_id PRIMARY KEY, baseline_id, updated_at)`.
   - HEAD read is performed via `JOIN`. Revision insertion, reference linking, and HEAD pointer update occur in a single atomic transaction.
5. **Lean Audit Model Trace**:
   - `model_trace` contains only bounded audit metadata (`provider`, `model`, `model_version`, `run_id`, `confidence`, `timestamp`). Full prompts or raw memory dumps are strictly forbidden.
6. **Storage-Root Isolation**:
   - Caller supplies the storage root directory. Verified via storage-root isolation tests (T10), leaving `RuntimeBinding` production integration to the future MR adapter ticket. Compatible with Python >= 3.12.

---

## Package Layout (`c:\projects\LCE`)

```text
c:\projects\LCE\
├── docs/
│   └── plans/
│       └── implementation_plan.md
├── pyproject.toml
├── src/
│   └── lce/
│       ├── __init__.py
│       ├── contracts/
│       │   ├── __init__.py
│       │   ├── external_memory.py      # MemoryItemView, MemorySubstratePort
│       │   ├── baseline.py             # Baseline, BaselineRevision, BaselineHistory
│       │   └── consolidation.py        # CandidateBaseline, ConsolidationResult, SemanticConsolidatorPort, UnauthorizedSourceError
│       ├── store/
│       │   ├── __init__.py
│       │   ├── interface.py            # BaselineStorePort
│       │   └── sqlite_store.py         # SqliteBaselineStore (atomic transaction, pointer HEAD)
│       ├── core/
│       │   ├── __init__.py
│       │   ├── equivalence.py          # normalize_content, evaluate_equivalence
│       │   └── engine.py               # LceCore (consolidate, get_current_baseline, get_history)
│       └── testing/
│           ├── __init__.py
│           ├── fake_substrate.py       # FakeMemorySubstrate
│           └── fake_consolidator.py    # Scriptable FakeSemanticConsolidator
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_contracts.py
    ├── test_store.py
    ├── test_fake_substrate.py
    └── test_lce_core.py                # T1 through T12 complete verification suite
```

---

## Verification Plan

Run full verification suite using pytest:
```powershell
python -m pytest tests -v
```
Run type-checking with mypy:
```powershell
python -m mypy src tests
```
Ensure 100% pass on T1 through T12:
- T1 — External-memory-only
- T2 — Initial Baseline
- T3 — Stable provenance
- T4 — Unknown source rejection (fail-closed)
- T5 — Duplicate stability (normalized content equivalence)
- T6 — Meaningful revision (revision link & increment)
- T7 — Current HEAD retrieval
- T8 — Revision history audit
- T9 — Restart stability
- T10 — Storage-root isolation
- T11 — No authority escalation (inspection of LCE public API)
- T12 — Vector independence (metadata changes don't affect provenance)
