# Research Report: Temporal Semantic Graph Representation (GitHub Issue #12)

**Result: NOT SUPPORTED**

## Executive Summary

- Candidate volume rose sharply from 8 in baseline to 40 in graph (3.5x inflation) due to combinatorial sub-clique and chain fragmentation without improved precision.
- Bridge carrier recovery in TG-01 is structurally equivalent to existing MST minimax cut-edge tracking already evaluated in LCE, offering zero incremental signal beyond what the simpler MST baseline provides.
- Without LLM-generated semantic labels (e.g. 'contradicts', 'causes'), structural revision candidates (TG-03) cannot be reliably distinguished from ordinary cluster extension or temporal drift.
- In dense clusters (TG-05), overlapping clique decomposition triggers severe hubness/density artifacts, spawning 8 spurious multi-membership candidates from a single static cluster.
- Longitudinal recurrence (TG-02) is identical to what the simpler frozen vector / cosine neighbourhood baseline already discovers, with temporal edges adding no discriminative filtering.

---

## Required Fields

**Question:** Does representing the same cutoff-bounded Semantic Blocks as a temporal semantic graph expose longitudinal structure that the current raw embedding / k-neighbourhood representation misses?

**Baseline:** Current LCE structure-discovery baseline unchanged (frozen vectors -> cosine / k-neighbourhood / multi-scale stability / exclusive cluster partition).

**Graph representation:** Minimal deterministic temporal semantic graph: nodes = cutoff-visible Semantic Blocks; allowed edges = `semantic_neighbour` (with score & threshold provenance), `temporal_next` (successive chronological order), and `same_context_key` (explicit identifiers only). Strictly zero LLM semantic relation labels, GNNs, or GraphRAG.

**Fixtures:** All 5 required fixtures implemented: TG-01 (Delayed bridge), TG-02 (Distant recurrence), TG-03 (Contradiction-shaped geometry), TG-04 (Multi-membership bridge), TG-05 (Density trap).

**Ablations:** Evaluated semantic_only, temporal_only, and semantic_and_temporal across all fixtures to isolate relation contributions.

**Metrics:** Recorded known-event recovery, bridge carrier identification, false candidate count, candidate volume, temporal specificity under shuffled control, robustness under perturbation/dropout, source locality, redundancy with baseline, incremental candidate yield, and runtime/memory cost.

**Observed operating region:** Deterministic topological operations (Tarjan cut-vertices, overlapping cliques, temporal-semantic path traversal) can detect bridge nodes and path progressions in clean synthetic graphs, but only in isolated, low-density settings without hubness.

**Observed failure boundary:** In realistic vector spaces with dense clusters or hubness, the minimal graph suffers combinatorial clique explosion (TG-05); without LLM semantic labels, it cannot distinguish structural revision from drift (TG-03); and its bridge carrier signal is entirely redundant with simpler MST cut-edge tracking (TG-01).

**Increment over baseline:** 0x stable increment. All valid longitudinal signals recovered by the graph are either already captured by the simpler vector-neighbourhood baseline / MST or drowned out by candidate inflation (40 graph candidates vs 8 baseline candidates).

**Known misses:** Fails to distinguish revision candidates from sequential drift without semantic labels; fails to isolate dense noise clusters without spurious clique generation.

**Complexity cost:** Overhead is higher without corresponding benefit: baseline total runtime = 11.61 ms; graph total runtime = 18.18 ms (~1.6x baseline). Memory overhead < 50 KB.

**Recommendation:** reject


---

## Compact Comparison Table


| Fixture | Baseline Detection | Graph Detection | Shuffle Result | Perturbation Result | Incremental Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TG-01** (Delayed bridge) | Recovered | Carrier Recovered (AP) | Failed to Degrade | Robust (0.93) | Redundant |
| **TG-02** (Distant recurrence) | Recovered | Recovered | Failed to Degrade | Robust (0.89) | Redundant |
| **TG-03** (Contradiction-shaped geometry without semantic labels) | Recovered | Recovered | Failed to Degrade | Robust (0.93) | Redundant |
| **TG-04** (Multi-membership bridge) | Recovered | Recovered | Degraded (Temporal) | Robust (0.89) | Redundant |
| **TG-05** (Density trap) | Recovered | Recovered | Failed to Degrade | Robust (0.64) | Redundant |

---

## Detailed Fixture & Ablation Breakdown


### TG-01: Delayed bridge

- **Oracle Target Event:** `reconnection_bridge`
- **Target Blocks:** `('X_bridge',)`
- **Carrier Blocks:** `('X_bridge',)`
- **Baseline Candidates (1):** ['base_clust_1']
- **Graph Candidates (5):** ['graph_bridge_A3', 'graph_bridge_B1', 'graph_bridge_X_bridge', 'graph_chain_A1', 'graph_chain_B1']
- **Ablation (Semantic Only) Recovery:** True
- **Ablation (Temporal Only) Recovery:** False
- **Source Locality (Graph):** [['A1', 'A3', 'B1'], ['A1', 'B1', 'B2'], ['A1', 'B1', 'X_bridge'], ['A1', 'A2', 'A3'], ['B1', 'B2', 'B3']]
- **Runtime / Memory:** Baseline: 1.89ms / 17.1KB; Graph: 2.42ms / 18.4KB

### TG-02: Distant recurrence

- **Oracle Target Event:** `distant_recurrence`
- **Target Blocks:** `('A1', 'A2', 'A3', 'A4', 'A5', 'A6')`
- **Carrier Blocks:** `('A4', 'A5', 'A6')`
- **Baseline Candidates (2):** ['base_clust_1', 'base_clust_2']
- **Graph Candidates (11):** ['graph_recurrence_1', 'graph_revision_A6', 'graph_multi_A5', 'graph_multi_A1', 'graph_multi_A2', 'graph_multi_A6', 'graph_multi_A4', 'graph_multi_A3', 'graph_chain_A1', 'graph_chain_D1', 'graph_chain_A4']
- **Ablation (Semantic Only) Recovery:** True
- **Ablation (Temporal Only) Recovery:** False
- **Source Locality (Graph):** [['A1', 'A2', 'A3', 'A4', 'A5', 'A6'], ['A4', 'A6', 'D1', 'D2'], ['A5'], ['A1'], ['A2'], ['A6'], ['A4'], ['A3'], ['A1', 'A2', 'A3'], ['D1', 'D2', 'D3'], ['A4', 'A5', 'A6']]
- **Runtime / Memory:** Baseline: 1.57ms / 23.0KB; Graph: 2.34ms / 16.3KB

### TG-03: Contradiction-shaped geometry without semantic labels

- **Oracle Target Event:** `structural_revision`
- **Target Blocks:** `('X_revision',)`
- **Carrier Blocks:** `('X_revision',)`
- **Baseline Candidates (2):** ['base_clust_1', 'base_clust_2']
- **Graph Candidates (4):** ['graph_revision_X_revision', 'graph_chain_R1_1', 'graph_chain_R2_1', 'graph_chain_R2_2']
- **Ablation (Semantic Only) Recovery:** False
- **Ablation (Temporal Only) Recovery:** False
- **Source Locality (Graph):** [['R1_1', 'R1_2', 'R2_1', 'X_revision'], ['R1_1', 'R1_2', 'R1_3'], ['R2_1', 'R2_2', 'R2_3', 'X_revision'], ['R2_2', 'R2_3', 'X_revision']]
- **Runtime / Memory:** Baseline: 0.82ms / 14.0KB; Graph: 1.49ms / 14.7KB

### TG-04: Multi-membership bridge

- **Oracle Target Event:** `multi_membership`
- **Target Blocks:** `('M_multi',)`
- **Carrier Blocks:** `('M_multi',)`
- **Baseline Candidates (1):** ['base_clust_1']
- **Graph Candidates (7):** ['graph_bridge_M_multi', 'graph_multi_M_multi', 'graph_chain_A1', 'graph_chain_A2', 'graph_chain_B1', 'graph_chain_B2', 'graph_chain_B3']
- **Ablation (Semantic Only) Recovery:** True
- **Ablation (Temporal Only) Recovery:** False
- **Source Locality (Graph):** [['A1', 'B1', 'M_multi'], ['M_multi'], ['A1', 'A2', 'A3', 'A4'], ['A2', 'A3', 'A4'], ['B1', 'B2', 'B3', 'B4', 'M_multi'], ['B2', 'B3', 'B4', 'M_multi'], ['B3', 'B4', 'M_multi']]
- **Runtime / Memory:** Baseline: 0.95ms / 18.3KB; Graph: 2.47ms / 18.7KB

### TG-05: Density trap

- **Oracle Target Event:** `temporal_coherent_chain`
- **Target Blocks:** `('C1', 'C2', 'C3', 'C4', 'C5')`
- **Carrier Blocks:** `('C1', 'C2', 'C3', 'C4', 'C5')`
- **Baseline Candidates (2):** ['base_clust_1', 'base_clust_2']
- **Graph Candidates (13):** ['graph_recurrence_1', 'graph_revision_C5', 'graph_multi_D08', 'graph_multi_D03', 'graph_multi_D13', 'graph_multi_D10', 'graph_multi_D15', 'graph_multi_D14', 'graph_multi_D06', 'graph_multi_D12', 'graph_multi_D09', 'graph_chain_C2', 'graph_chain_C3']
- **Ablation (Semantic Only) Recovery:** False
- **Ablation (Temporal Only) Recovery:** False
- **Source Locality (Graph):** [['C1', 'C2', 'C3', 'C4', 'C5'], ['C2', 'C5', 'D01', 'D02'], ['D08'], ['D03'], ['D13'], ['D10'], ['D15'], ['D14'], ['D06'], ['D12'], ['D09'], ['C2', 'C3', 'C4', 'C5'], ['C3', 'C4', 'C5']]
- **Runtime / Memory:** Baseline: 6.38ms / 76.8KB; Graph: 9.45ms / 33.4KB
