# Worktree + Snake chronological replay experiment

This experiment replaces the pair-retrieval framing used in Issues #25/#26 with a stateful chronological replay.

It tests a narrower architectural hypothesis:

1. unmatched SemanticBlocks remain in a residual point cloud;
2. local coherence in the residual cloud can bootstrap a cognition branch;
3. several branches can remain active under one frozen Worktree/Baseline context;
4. each branch grows incrementally ("Snake") by accumulating semantic coverage;
5. a new block is retrieved against live branch state rather than only against isolated historical points;
6. one block may match multiple branches;
7. time orders evidence but does not impose a hard temporal cutoff.

The corpus contains three open decisions with two simultaneously valid directions each:

- job: leave vs stay;
- housing: move vs renew/stay;
- architecture: migrate/rewrite vs compatibility/patch.

Gold branch labels are evaluation-only. A test reruns the replay after replacing every gold label and requires the entire retrieval/growth trace to remain identical.

## What is measured

The benchmark sweeps candidate thresholds 0.30 / 0.40 / 0.50 / 0.60 and reports:

- branch bootstrap coverage;
- candidate membership recall using the accumulated branch semantic envelope;
- candidate membership recall using the strongest isolated support point as a point-to-point baseline;
- recall gain/loss from branch-state retrieval;
- false candidate fraction;
- >45 day recall;
- multi-branch membership recall and exact multi-branch recall;
- recall by branch maturity (1-2, 3-4, 5+ supports);
- branch purity and residual point-cloud size.

No success threshold is encoded in pytest. The workflow prints raw results; tests only enforce mechanism invariants. This avoids turning an expected result into a self-fulfilling test.
