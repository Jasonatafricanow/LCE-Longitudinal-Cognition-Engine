# LCE Inspiration Material V1

Status: production core feature  
Date: 2026-09-28

## Purpose

LCE has two different downstream products:

```text
accepted understanding
    -> passive historical-context consumption

inspiration material
    -> proactive conversation consumption
```

The second product exists so long-term memory can become a new conversation
starting point instead of only answering an incoming query.

The product boundary is deliberately narrow:

```python
InspirationMaterial(
    material_id: str,
    content: str,
)
```

A downstream consumer does not need to understand Line IDs, branches,
SemanticBlocks, Raw-Evidence closures, trajectory scores, convergence profiles,
candidate kinds or internal provenance.

`material_id` is an opaque handle. `content` is self-contained material that
already preserves the correct epistemic strength.

## Internal discovery types

V1 implements two internal inspiration sources.

### 1. Possible association

The trajectory layer may find a local relation candidate whose identity remains
unresolved.

```text
A     B     C
 \    |    /
  possible relation?
```

This is not promoted into factual or accepted cognition merely because local
geometry looks interesting.

Instead LCE may compile it into material such as:

```text
Possible connection to explore (not established): ...
Observed material:
- A
- B
- C
```

The downstream use is reflective: show the user a possible connection and let
the user confirm, reject, refine or simply think about it.

### 2. Speculative extension

A persistent Line may already contain a supported logical prefix:

```text
A -> B -> C
```

LCE may ask a bounded semantic interpreter for one possible next implication:

```text
A -> B -> C -> D ?
```

The supported prefix and the speculative extension are never collapsed into one
authority claim.

The material is rendered with an explicit boundary:

```text
Existing supported line: A -> B -> C
Possible next implication to explore (not established): D
```

The reference interpreter intentionally does **not** invent D. A specific
extension requires an injected bounded semantic interpreter. This keeps the
structure-first / model-afterward architecture:

```text
existing supported structure
    -> bounded semantic hypothesis
    -> epistemically framed material
```

## Public seam vs internal state

Internally LCE retains whatever it needs for audit and lifecycle:

```text
candidate kind
candidate/path identity
Line identity when applicable
selected SemanticBlock state IDs
Raw-Evidence closure
knowledge cutoff
interpreter trace
queue status
```

None of those fields are part of the downstream public material object.

This prevents every consumer from having to understand LCE's internal ontology
and keeps future discovery types replaceable.

For example, LCE may later add analogy, counterexample, latent contradiction or
other inspiration suppliers without requiring downstream code to add a switch
over internal discovery kinds.

All suppliers still compile to the same public object:

```text
material_id + content
```

## Lifecycle

Inspiration material is persisted in an LCE-owned derived store.

Current public operations are:

```text
discover_inspiration(...)
inspiration_materials(...)
consume_inspiration(material_id)
dismiss_inspiration(material_id)
```

Repeated discovery of the same unchanged candidate is idempotent. Once a
material is consumed or dismissed, the same candidate is not re-enqueued merely
because sleep/dream discovery replays it.

A changed support state or genuinely new candidate identity may produce new
material.

## Scheduling boundary

Inspiration discovery is explicit.

Normal nearline processing does not automatically create proactive material.
The intended MR composition is:

```text
online
    -> Thread / Path A for explicit logic

sleep / daydream / dream
    -> Path B / existing Lines
    -> inspiration discovery
    -> inspiration material queue
```

A separate downstream policy decides whether and when material becomes an
outbound proactive message.

LCE does not own:

- Persona-specific initiative thresholds;
- interruption policy;
- send frequency/cooldowns;
- ActionPolicy permission;
- final Body wording.

LCE owns only the material and its internal cognitive provenance.

## Authority boundary

Inspiration is not Evidence and is not automatically accepted cognition.

For association material:

```text
local structural proposal != established relation
```

For extension material:

```text
supported A -> B -> C
    !=
speculative D
```

The rendered content must keep that distinction visible so a downstream Body
does not need to reconstruct which part was supported and which part was
hypothetical.

User feedback may later feed the normal Evidence/correction paths. A separate
relation-correction ledger is responsible for preventing an explicitly rejected
derived relation from being regenerated from unchanged support.

## Core invariant

> LCE may be internally complex; downstream proactive consumers receive only
> self-contained inspiration material plus an opaque handle.
