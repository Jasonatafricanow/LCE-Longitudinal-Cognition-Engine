# SemanticBlock Design Freeze — 2026-09-25

Status: **FROZEN**

This document is the authoritative design boundary for SemanticBlock until it is explicitly superseded. Downstream experiments, taxonomies, scoring schemes, graph designs, or implementation convenience MUST NOT silently expand the responsibility of SemanticBlock.

## 1. Core definition

A **SemanticBlock** is a time-local, context-grounded semantic point:

> the smallest unit that faithfully and completely preserves what was actually meant at that time, using as much surrounding dialogue context as is necessary to avoid distortion.

Its boundary is determined by semantic completeness, not by sentence boundaries, message boundaries, clauses, token count, or an annotation schema.

A SemanticBlock is finished when it has truthfully captured the meaning available at that point in time. It does not need to explain what happens later.

## 2. Semantic fidelity comes before structure

The first problem is not confidence, graph structure, time normalization, relation extraction, or retrieval.

The first problem is:

> Did we understand the real meaning correctly?

Example:

“我朋友说公司可能下个月裁员。”

A faithful SemanticBlock must preserve that the user is reporting a friend's uncertain claim.

It must not collapse this into:

- “公司下个月会裁员。”
- “用户认为公司下个月会裁员。”

A later turn may further qualify the same meaning:

“我不知道，他最近老吓唬我。”

The necessary dialogue context may therefore span multiple turns. If multiple turns are required to preserve the real meaning, they belong to the same semantic interpretation context.

Internal parsing tools may use speech acts, attribution, modality, propositions, roles, or other categories. Those are implementation aids. They do not define the public SemanticBlock and must not replace semantic fidelity with field completeness.

## 3. Unknown is a valid cognitive state

UNKNOWN is not a parser failure and not a temporary defect to be eliminated.

It is the correct output whenever the available evidence does not justify a stronger claim.

However, UNKNOWN is also not a lazy fallback. It must be localized to the part that is genuinely unknown.

The rule is:

> Preserve what is known. Keep what is genuinely unknown unknown. Do not spread uncertainty into known information, and do not fill uncertainty with unsupported guesses.

Example:

“我朋友说明天可能裁员。”

Known:
- the user reported what the friend said;
- the friend expressed a possibility of layoffs tomorrow.

Potentially unknown:
- whether the user personally believes the claim;
- whether layoffs will actually happen.

Do not reduce the whole block to “layoffs = unknown”. That would discard known meaning.

Likewise:

“我今天必须赶杭州到北京的飞机。”

Known now:
- there is a strong current requirement or plan to catch that flight.

Unknown now:
- whether the user will actually depart;
- whether the flight will operate;
- whether the user will arrive.

The uncertainty of the future must not weaken the truth of the present requirement.

## 4. Do not manufacture cognition

Unsupported guessing is cognitive pollution.

If the system guesses during an unknown state, later evidence creates avoidable repair work:

    t1: insufficient evidence
        -> system guesses B

    t2: new evidence
        -> system must repair the invented B

The preferred behavior is:

    t1: A is known
        B is unknown

    t2: new evidence arrives
        B becomes known

The second sequence adds cognition only when reality provides new evidence.

Therefore:

> No new evidence, no new cognition.

The system should not invent certainty merely to make a representation look complete.

## 5. Time is strong longitudinal authority

SemanticBlock is a **point**. LCE turns points into a **line**.

A later event does not automatically invalidate an earlier truthful SemanticBlock.

Example:

    09:00  用户今天必须赶杭州 -> 北京的飞机
    11:00  用户堵在去机场的路上
    12:30  用户没有赶上飞机

The 09:00 block was not wrong. It recorded the real state at 09:00: a strong requirement or plan existed.

The 12:30 block records a later outcome.

Both are true at their own time points.

This is the purpose of longitudinal structure:

> preserve time-local truths, then let later evidence form a trajectory.

Time should therefore provide deterministic longitudinal structure whenever timestamps or source metadata are available. SemanticBlock should not be forced to predict the eventual outcome of a still-unresolved event.

## 6. World change is not the same as correction

Two different processes must remain separate.

### A. The world changed

    t1: user did A
    t2: user later did B

Both blocks remain valid historical facts. The new block extends the trajectory.

### B. Earlier cognition was wrong or explicitly corrected

    t1: user says Tuesday
    t2: user says “I said it wrong; it was Wednesday”

This is a correction or retraction lineage problem, not ordinary world evolution.

Do not rewrite normal historical change as error correction, and do not treat an actual correction as merely another unrelated event.

## 7. SemanticBlock stops at the bag of flour

SemanticBlock is the raw material for later cognition.

Using the project metaphor:

> wheat is milled into flour, the flour is bagged, and the bag is stored as usable material.

SemanticBlock does not need to ask every downstream “chef” whether the bag will be used.

A block may never become important. That is acceptable.

SemanticBlock does not decide:

- whether the information will matter later;
- what eventual outcome it leads to;
- whether another block is related;
- whether it belongs in a trend;
- whether it should be traversed in a graph;
- what global conclusion should be drawn.

Those are downstream responsibilities.

## 8. Relations and graph are selective downstream operations

The system must not repeatedly ask an LLM whether every pair of SemanticBlocks is related.

That would recreate full-context reasoning at graph-construction time and defeat the purpose of sparse structure.

Preferred direction:

    Raw Evidence + necessary context
            |
            v
    SemanticBlock
    (time-local semantic point)
            |
            v
    stored with deterministic metadata
            |
            v
    cheap structural or retrieval signal finds a meaningful candidate
            |
            v
    optional bounded relation verification
            |
            v
    longitudinal or graph structure

Only when there is a meaningful structural reason to inspect a candidate should a more expensive relation step be considered.

Examples of structural reasons may include:
- the same entity or event identity;
- a shared plan, task, flight, order, or thread;
- explicit causal or continuation cues;
- repeated longitudinal structure;
- cross-document evidence that retrieval surfaces as plausibly connected.

Absence of a structural signal is not an invitation to speculate.

## 9. “Must go” and “did not make it” belong to the line, not one block

These should remain separate time-local points:

    t1: user must catch the Hangzhou -> Beijing flight
    t2: user encounters a blocking event
    t3: user does not catch the flight

A graph or longitudinal retrieval layer may later recover them together as a trajectory such as:

    strong requirement or plan
    -> attempted execution
    -> obstruction
    -> unrealized outcome

The trajectory is downstream synthesis.

SemanticBlock must not pre-compose the whole trajectory before those later facts exist.

## 10. Source weight and confidence are downstream from meaning

A simple confidence heuristic may assign relatively high evidential weight to direct user-authored information, especially about the user's own state, experience, preference, or intention.

But this heuristic comes **after** semantic interpretation.

The system must first determine what the user actually meant: direct assertion, report of another person's claim, question, hypothetical, joke, sarcasm, exaggeration, intention, desire, correction, or genuinely ambiguous expression.

Increasing the weight of a misread utterance only strengthens the error.

Therefore:

> semantic truth first; confidence and authority second.

## 11. Frozen responsibility boundary

### SemanticBlock owns

- recovering the real meaning from the necessary local dialogue context;
- preserving attribution and qualification insofar as they are necessary to keep that meaning true;
- preserving known information without overclaiming;
- honestly retaining localized unknowns;
- representing the semantic state that existed at that time.

### SemanticBlock does not own

- future prediction;
- eventual outcome;
- exhaustive uncertainty elimination;
- global truth adjudication;
- longitudinal trend synthesis;
- graph traversal;
- pairwise relation search;
- corpus-wide structure discovery;
- deciding future usefulness;
- rewriting prior true states because later reality changed.

## 12. Frozen acceptance tests

A candidate SemanticBlock should be rejected or reconsidered if any of the following are true:

1. **Context distortion** — removing the original dialogue causes the block to materially misrepresent what was meant.
2. **Overclaim** — the block asserts something stronger than the available evidence.
3. **Underclaim** — the block hides information that was actually known by replacing it with broad uncertainty.
4. **Misplaced unknown** — uncertainty is assigned to the wrong part of the meaning.
5. **Attribution drift** — another person's claim becomes the user's own claim, or vice versa.
6. **Temporal overreach** — a current plan, requirement, or belief is rewritten as a future outcome that has not yet occurred.
7. **Premature trajectory** — downstream relationships or future conclusions are inserted into a time-local block before the evidence exists.
8. **Schema substitution** — field completeness is treated as semantic correctness even when the combined meaning is wrong.

## 13. Change control

This design is frozen.

Future experiments may test better ways to produce SemanticBlocks, but they must treat this document as the target definition.

A future change to the definition must be explicit:

1. identify the current frozen rule being changed;
2. provide a concrete failure case that the current definition cannot represent faithfully;
3. explain why the problem cannot be solved downstream;
4. write a superseding design record rather than silently editing the meaning of SemanticBlock.

Until that happens:

> SemanticBlock is a truthful semantic point.  
> Time turns points into lines.  
> Unknown remains unknown until reality provides evidence.  
> Downstream structure must not reach backward and redefine the point.
