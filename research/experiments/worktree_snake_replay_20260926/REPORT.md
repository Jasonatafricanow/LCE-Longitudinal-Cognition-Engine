# Worktree + Snake chronological replay — first direct GitHub run

Evaluated implementation SHA: `18fd21b1117588c22f4ede0d6d4c4af2f7e47574`

GitHub Actions:
- Worktree Snake Replay Experiment: run 36232395015 — PASS
- Public Verification: run 36232395023 — PASS

## Scope

This is a mechanism experiment, not a production-quality semantic-model benchmark.

It separates two questions that Issues #25/#26 mixed together:

1. **Bootstrap / point cloud:** can unclaimed points form live branches early enough?
2. **Established cognition:** once a branch has accumulated a coherent semantic envelope, how well does it recall later evidence compared with matching the same new point against isolated historical points?

Gold labels are evaluator-only. Replacing all gold labels leaves the retrieval/growth trace unchanged.

## End-to-end chronological replay

44 points, 3 Worktrees, 6 latent branches, 40 gold memberships, timeline out to day 211.

| candidate threshold | seed coverage | branch-envelope recall | isolated-point recall | false candidate fraction | >45d recall | exact multi-branch recall |
|---:|---:|---:|---:|---:|---:|---:|
| 0.30 | 83.3% | 66.7% | 66.7% | 11.8% | 70.0% | 0% |
| 0.40 | 100% | 57.9% | 57.9% | 6.7% | 63.6% | 0% |
| 0.50 | 100% | 57.9% | 57.9% | 0% | 63.6% | 0% |
| 0.60 | 100% | 57.9% | 57.9% | 0% | 66.7% | 0% |

The aggregate replay is bottlenecked by early branch formation / fragmentation rather than by mature branch matching.

### Recall by branch maturity

At thresholds 0.30–0.50:

- young branches (1–2 supports): 33–45% recall;
- growing branches (3–4 supports): 100% recall;
- mature branches (5+ supports): 100% recall in the available replay opportunities.

The sample for mature 5+ is still small, so the 100% figure is directional, not a final production estimate.

## Controlled established-branch probes

To isolate the user's "more complete cognition matches more future points" hypothesis, six branches were frozen with three earlier supports each, then evaluated on 30 fresh probes / 30 gold memberships. The new probes deliberately combine semantics distributed across multiple earlier supports so no single old point necessarily represents the whole later observation.

| threshold | compiled branch-envelope recall | isolated-point recall | recall gain | false candidate fraction | exact multi-branch recall |
|---:|---:|---:|---:|---:|---:|
| 0.30 | 100% | 93.3% | +6.7 pp | 0% | 100% |
| 0.40 | 96.7% | 86.7% | +10.0 pp | 0% | 66.7% |
| 0.50 | 83.3% | 16.7% | +66.7 pp | 0% | 0% |
| 0.60 | 80.0% | 16.7% | +63.3 pp | 0% | 0% |

## Interpretation

The first direct run supports the architectural distinction:

- **Once cognition exists and has accumulated several supports, matching the new point against the compiled branch state is substantially more robust than requiring one old point to resemble the new point.**
- The end-to-end weakness is currently the transition from residual point cloud to stable parallel branches. A branch can be seeded late or fragmented into several small branches, which destroys recall before the Snake has enough history to gain semantic inertia.
- Multi-direction cognition works in the controlled established-branch condition (100% exact multi-branch recall at the permissive threshold), but the end-to-end replay fails it because both required branches are not reliably alive and mature at the same time.
- Removing the 45-day hard cutoff fixes the categorical temporal failure, but long-gap recall is still only ~64–70% end-to-end because a live semantic branch must still exist and match.

## Current conclusion

**The Worktree + Snake hypothesis is supported at the established-cognition layer. The unresolved mechanism is point-cloud bootstrap / branch formation, not mature longitudinal recall.**

Do not translate the controlled 96.7–100% figure into a production recall claim: semantic features are structured research fixtures standing in for a real semantic compiler/embedding. The next meaningful experiment should keep established-branch retrieval frozen and test better point-cloud-to-branch formation without using gold branch IDs.
