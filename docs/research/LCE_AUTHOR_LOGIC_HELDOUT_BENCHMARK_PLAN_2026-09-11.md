# LCE Author-Logic Held-Out Benchmark Plan

**Date:** 2026-09-11  
**Status:** Research plan only — no production integration authorized

## 1. Purpose

This benchmark tests the strongest current LCE research hypothesis:

> Given historical cognition fragments that appear locally unrelated at the time, can LCE recover structural relations that the human author later consolidates into a stable higher-order logic?

The benchmark uses the author's own completed essays as held-out human-authored targets rather than relying only on synthetic geometry or an LLM's post-hoc judgment.

The target is not summarization. The discovery run must not see the completed article whose logic is used as the oracle.

## 2. Why authored essays are useful research targets

The relevant essays are not simple single-topic summaries. Their final logic often emerges by connecting variables from apparently different domains because they instantiate a similar deeper relation or constraint.

This gives the benchmark three unusually strong evidence layers:

```text
pre-article historical material
    -> candidate latent structure
    -> later human-authored article
```

The final article is therefore evidence of which relations the author actually retained and organized into a stable argument. It is not proof that every relation in the article existed explicitly in earlier history; the benchmark must distinguish recovered prior structure from genuinely new reasoning introduced during writing.

## 3. Data inputs

### 3.1 Required

- complete final article text;
- article completion timestamp or best available time bound;
- the historical conversation / note corpus available before that time;
- message timestamps and session/conversation identifiers when available.

### 3.2 Preferred history source

Preferred source is a full ChatGPT account export or equivalent message-level archive that preserves:

```text
conversation/session identity
message tree / parent-child relation where available
raw original text
timestamps
```

If complete export remains unavailable, the first benchmark may use a bounded recent-history corpus, but the limitation must be recorded and prospective claims must be weakened accordingly.

## 4. Separation of discovery data and evaluation data

Create three logically separate corpora.

### Corpus 0 — Raw historical archive

The full available pre-article history. This is the source-of-truth evidence pool and must not be manually filtered to match the article.

### Corpus 1 — Discovery window

A realistic time-bounded prefix before the article, for example the previous N days or weeks. This is the corpus supplied to LCE in retrospective/prospective discovery experiments.

### Corpus 2 — Evaluation closure

Evidence recovered after the fact by tracing the final article's claims and relations back into the historical archive. Corpus 2 exists only for oracle construction, error analysis, and evidence verification.

Corpus 2 must never be supplied to the discovery run as a pre-filtered candidate set.

## 5. Human-authored oracle construction

Before evaluating LCE, decompose each completed article into a bounded structural oracle.

Record at minimum:

- final top-level thesis or theses;
- major intermediate reasoning chains;
- cross-domain connections;
- variables or examples that appear locally unrelated but are unified by the same deeper relation;
- relation type as described by the author's argument, without forcing a universal ontology;
- article paragraphs / spans supporting each relation;
- whether each relation can be traced to pre-article historical evidence;
- earliest known historical evidence for each constituent idea;
- first known explicit human formulation of the higher-order relation, if recoverable.

The oracle must distinguish:

```text
relation already latent in history
relation explicitly stated before article
relation first introduced during article writing
```

Only the first two are valid targets for pre-article discovery recall.

## 6. Benchmark levels

### Level 1 — Structure recovery from the finished article

Purpose: representation and segmentation audit.

Procedure:

1. remove article title, section labels, explicit outline cues, and other leakage where practical;
2. split the article under multiple representation policies;
3. shuffle or otherwise hide original section grouping where appropriate;
4. run structure discovery;
5. compare recovered structures to the author-logic oracle.

This asks whether LCE can recover a known logic when all required evidence is present.

It does not test longitudinal anticipation.

### Level 2 — Retrospective discovery from pre-article history

Purpose: test whether later article structure was discoverable from prior material.

Procedure:

```text
history before article completion
    -> LCE structure discovery
    -> candidate structures
    -> compare with held-out article oracle
```

The completed article is unavailable to LCE during discovery.

Measure which later-authorized relations were already recoverable and which candidates were false or never developed.

### Level 3 — Prospective cutoff discovery

Purpose: strongest longitudinal test.

Choose one or more cutoffs before the author's first explicit formulation of a final article relation.

At each cutoff:

```text
history available at cutoff only
    -> LCE candidates
    -> freeze output
    -> compare against later human-authored article
```

A candidate counts as prospective only if the source evidence existed before cutoff and the higher-order relation had not yet been explicitly stated by the author.

## 7. Segmentation ablation

The first representation question is not merely whether current Semantic Blocks are good or bad. The research question is:

> At what representation granularity does a real cross-domain synthesis become geometrically and structurally recoverable?

For the same frozen raw evidence, compare at least:

```text
A. sentence / utterance units
B. current Semantic Block segmentation
C. coarser semantic episode blocks
D. overlapping windows of 2 / 3 / 4 neighbouring blocks
E. current Semantic Block + temporary local pooled representation
```

Freeze the embedding model and downstream supplier during each ablation.

Interpretation rules:

```text
raw span / coarse episode recoverable, current SB not recoverable
    -> segmentation failure candidate

all segmentation variants fail, whole relevant span also fails geometrically
    -> embedding representation failure candidate

valid bridge / relation exists in vector representation but supplier misses it
    -> supplier failure

controlled representation succeeds but real history rarely contains target structure
    -> low signal prevalence / temporal horizon
```

Do not change segmentation and discovery algorithm simultaneously in the first ablation.

## 8. Structural targets

The benchmark must not assume that every higher-order relation is a single bridge node.

Test at least these shapes where the article oracle supports them:

### Single-node bridge

```text
A -- C -- B
```

### Distributed bridge / short synthesis episode

```text
A -- C1 -- C2 -- C3 -- B
```

where no individual `Ci` necessarily contains both domains strongly enough to be a canonical bridge.

### Repeated relational motif

Different semantic domains may instantiate the same deeper relation:

```text
A1 -> A2 -> A3
B1 -> B2 -> B3
C1 -> C2 -> C3
```

The desired higher-order discovery is the shared relational form, not lexical proximity between A/B/C nodes.

If current vector-distance suppliers cannot recover this case, record a possible relational-representation gap rather than inventing another proximity algorithm.

## 9. Metrics

Do not optimize one aggregate score. Record at least:

- oracle relation recovery;
- candidate precision against later human-authored structure;
- candidate volume;
- evidence-closure precision;
- temporal lead time for prospective candidates;
- segmentation sensitivity;
- paraphrase / perturbation robustness where applicable;
- false cross-domain connection rate;
- proportion of article relations unsupported by pre-article evidence;
- UNKNOWN / insufficient-evidence rate.

A simple retrospective precision may be reported as:

```text
later-authorized discovered candidates / all proposed candidates
```

A simple recall may be reported as:

```text
recoverable article relations discovered / recoverable article relations in oracle
```

These metrics are descriptive; they do not replace bounded qualitative review.

## 10. No-leakage rules

- discovery code cannot read the completed article in Level 2 or Level 3;
- article-derived keywords cannot be used to pre-filter Corpus 1;
- oracle construction output must be stored separately from discovery input;
- post-hoc evidence closure can be used only after candidate outputs are frozen;
- if the human author remembers a relation only after seeing algorithm output, record that as post-hoc interpretation, not ground truth;
- later article wording must not be inserted into Semantic Blocks used by the historical replay.

## 11. Failure taxonomy

Every miss should be assigned to the earliest defensible failing layer:

```text
SOURCE_MISSING
SEGMENTATION_FAILURE
EMBEDDING_REPRESENTATION_FAILURE
SUPPLIER_FAILURE
INSUFFICIENT_SIGNAL_OR_TEMPORAL_SUPPORT
ORACLE_NOT_PREEXISTING
UNKNOWN
```

The purpose is to locate where structure is lost, not merely to score algorithms.

## 12. Relationship to current structure-discovery research

This benchmark does not authorize a new architecture layer.

Current candidate methods retain narrow responsibilities:

```text
kNN / cosine
    -> cheap local proximity proposals

MST / union-find
    -> connectivity change / reconnection when bridge geometry exists

persistent homology
    -> rejected for current semantic-vector H1 use unless future representation changes justify reopening

predictive directional flow
    -> longitudinal directional association when repeated support accumulates

DHD
    -> capability-only until a defensible edge/face complex exists
```

The benchmark may reveal that the missing capability is not another structure-discovery algorithm but a better representation of distributed or relational structure.

## 13. Expected first experiment

Use one recent completed essay with known pre-writing discussion.

Run in this order:

```text
1. build article logic oracle
2. identify article completion cutoff
3. assemble all available pre-cutoff history without article-based filtering
4. run Level 1 segmentation ablation on article text
5. run Level 2 retrospective discovery
6. if timestamps permit, run one or more Level 3 prospective cutoffs
7. trace misses to segmentation / embedding / supplier / temporal support
```

Do not expand to multiple essays until the first benchmark is auditable end-to-end.

## 14. Success boundary

The strongest target capability is:

> Before the author explicitly consolidates a higher-order argument, LCE can surface bounded structural candidates linking historical cognition fragments that the author later independently organizes into the same stable logic.

Partial success is still informative:

- Level 1 success only -> representation can recover completed structure but longitudinal discovery remains unproven;
- Level 2 success -> prior history contained recoverable latent structure;
- Level 3 success -> prospective longitudinal structure discovery is demonstrated for that case;
- systematic failure at one representation level -> identifies the next research boundary.

A negative result that precisely locates the lost structure is a successful benchmark outcome.
