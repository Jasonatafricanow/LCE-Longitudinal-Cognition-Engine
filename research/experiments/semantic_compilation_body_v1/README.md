# Semantic Compilation Body/AGY Experiment V1

**Status**: Research Verification Only (`research/experiments/semantic_compilation_body_v1/`).  
**Constraint**: Prohibits direct modification to MR/LCE/MR-Mem production mainline. No downstream Point Cloud, Thread, Retrieval, or Baseline code is touched.

---

## 1. Why This Experiment Exists

A critical architectural hypothesis in the LCE / Longitudinal Cognition Engine roadmap is:

> **Can the real host Body / AGY reliably parse raw conversational evidence into faithful Semantic Points and semantic dependencies, and compile them into context-complete SemanticBlocks without taking statements out of context?**

### Historical Progression

1. **Early Naive Approach (Wheat Field Partitioning)**:
   ```text
   Raw Evidence -> Topic / Region Segmentation -> SemanticBlock
   ```
   *Defect*: Merely chunks text without understanding semantic relations or dependency scopes.

2. **September Research Record**:
   ```text
   91 raw units -> 667 first-pass semantic artifacts -> 129 SemanticBlocks -> Embedding -> Point Cloud
   ```
   *Key finding*: 667 semantic artifacts were never 667 vector points. They underwent a second-pass compilation into 129 context-complete SemanticBlocks.

3. **V1 Negative Experiment (Proposition == Block)**:
   - Attempted treating one parsed atomic proposition as one SemanticBlock.
   - *Result*: Catastrophically fragmented conditions from consequences, negations from claims, and past completed plans from current states.

4. **V2 & V3 Mechanical Validation (Semantic Closure Invariants)**:
   - Proved on 12 adversarial cases and 1,000 synthetic random dependency graphs that **given correct points and dependencies, the Semantic Closure algorithm (Union-Find + context attachment) is 100% topologically invariant, idempotent, and context-safe**.
   - *The remaining missing link*: **Can a real LLM / Body reliably emit those semantic points and dependencies from uncurated, complex dialogue?**

---

## 2. Theoretical Model: Two Distinct Stages

### Stage A: Semantic Parsing (Body / Host LLM as Semantic Authority)
```text
Raw Evidence
    ↓
SemanticParseResultV1
{
    semantic_points[]
    dependencies[]
    unresolved[]
}
```

- **Semantic Point**: An open natural-language semantic constituent extracted from the utterance.
- **Universal Logical Attributes**: Typed enums for structural logic ONLY (`speech_act`, `polarity`, `epistemic_status`, `temporal`, `status`). No closed business ontology (no `USER_PREFERENCE`, `CODING_RULE`, etc.).

### Stage B: Deterministic Semantic Closure Compilation (LCE / Compiler)
```text
Semantic Points + Dependencies
    ↓
Semantic Closure Compiler (Union-Find)
    ↓
SemanticBlocks
```

- **`cohabit`**: Endpoints must enter the SAME SemanticBlock; splitting them distorts source meaning (condition scope, limitation scope, negation scope, contrast).
- **`context`**: Points have distinct longitudinal identities (superseded instruction vs current instruction), but newer block attaches older point as context reference.
- **`separate`**: Points are independently meaningful and form separate SemanticBlocks.
- **`DEFER`**: Ambiguous references without unique antecedent in window are withheld from active cognition.
- **Critical Production Constraint**: `SemanticBlock.analysis_text` embeds the context-complete current meaning without verbatim string concatenation of historical text, preventing outdated keywords (e.g. `top-k=100`) from regaining vector weight.

---

## 3. Experimental Structure

```text
research/experiments/semantic_compilation_body_v1/
├── README.md                                  # This document
├── schema.py / schema.json                    # Typed Pydantic & JSON schema
├── prompt.md                                  # Production-grade Body semantic parsing prompt
├── generate_cases.py                          # Deterministic 75-case corpus builder
├── cases/
│   ├── cases.json                             # 75 cases covering 25 difficult linguistic phenomena
│   └── ground_truth.json                      # Formal ground truth specifications
├── runner.py                                  # Multi-model execution runner with disk cache
├── validator.py                               # Deterministic parser & schema validator
├── closure.py                                 # Union-Find Semantic Closure Compiler
├── evaluate.py                                # 14 quantitative metrics + E1-E18 error taxonomy
├── run_experiment.py                          # Master experiment driver
├── results/                                   # Full JSONL traces and model comparison summaries
└── SEMANTIC_COMPILATION_BODY_EXPERIMENT_V1.md # Formal research report & GO/BLOCKED decision
```

---

## 4. Model Comparison Arms

1. **Arm A (Production Body Host)**: `DeepSeek-V4-Flash` via AMD Radeon Inference / ModelScope API (configured as Hermes default model).
2. **Arm B (AGY Capability Anchor)**: `gemini-3-flash-preview` via Google GenAI API (multi-key pool rotation).
3. **Arm C (Lower Bound Reference)**: `glm-4-flash` via Zhipu AI API.

---

## 5. How to Run

```powershell
# Set PYTHONPATH to project root
$env:PYTHONPATH="."

# Run Arm A (DeepSeek-V4-Flash)
python -X utf8 research/experiments/semantic_compilation_body_v1/run_experiment.py --model deepseek_v4_flash

# Run Arm B (Gemini-3-Flash)
python -X utf8 research/experiments/semantic_compilation_body_v1/run_experiment.py --model gemini_2_5_flash

# Run Arm C (GLM-4-Flash)
python -X utf8 research/experiments/semantic_compilation_body_v1/run_experiment.py --model glm_4_flash
```
