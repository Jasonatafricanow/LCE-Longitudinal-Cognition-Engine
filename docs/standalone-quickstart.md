# Standalone Quickstart

LCE V1 runs without MR and has no runtime dependency outside Python's standard
library. Install the package in a clean environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --no-deps .
```

Create a runtime and feed ordered `RawEvidence` objects:

```python
from datetime import UTC, datetime
from lce.reference_memory import RawEvidence
from lce.runtime import LceRuntime

runtime = LceRuntime("./state", lineage_id="demo")
item = RawEvidence(
    evidence_id="E1",
    content="the project moved forward",
    occurred_at=datetime.now(UTC),
    ordering_key="0001:E1",
    provenance={"source": "demo", "canonical": True, "topic": "project"},
)
runtime.process(item, mode="nearline")
accepted = runtime.query("project")
runtime.close()
```

For historical data, pass the same material to `run_batch()`. The runner uses
the same `process(material)` path, persists checkpoints, and safely replays a
stable evidence ID after restart. `query()` only returns accepted/current-valid
Understandings; it does not call an LLM, change HEAD, or inspect OPEN
worktrees as accepted cognition.

To replace the local substrate, pass an implementation of the focused
Reference Memory substrate contract as `LceRuntime(..., memory=backend)`. The
backend must provide canonical evidence validity, immutable Semantic Block
states, vector projection, compiler progress, and stage/idempotency methods;
the included `InMemoryReferenceMemory` is a small independent contract test
double.
