# Current Body Turn Path Audit (Hermes / Mind Runtime Seam)

**Audit Date**: 2026-10-02  
**Target Architecture**: Hermes Agent Host + Mind Runtime (MR) Integration  
**Model in Scope**: DeepSeek-V4-Flash (primary Body host)  
**Location**: `research/experiments/semantic_compilation_body_v1/one_pass/CURRENT_BODY_TURN_PATH.md`

---

## 1. Executive Summary & Trace Overview

The current production turn pipeline connects the user messaging channel (Feishu, Telegram, Discord, CLI, Webhook) to the Body Host LLM (`DeepSeek-V4-Flash`) through Hermes and Mind Runtime (`mind_runtime`).

The interaction follows a 4-phase sequence:

```text
User Message (Channel)
        ↓
[Phase 1: Inbound Seam]
XiyueMRAdapter.begin_turn(HostTurnRequest)
        ↓
MindRuntimeHostAdapter.begin_turn()
        ↓
TurnOrchestrator.run() → Bounded Context (MR CURRENT CONTEXT)
        ↓
[Phase 2: LLM Invocation]
Hermes Agent Host compiles prompt:
System Prompt + Bounded Context + History + User Message
        ↓
Provider Call: DeepSeek-V4-Flash (via OpenAI-compatible API)
        ↓
[Phase 3: Outbound Response]
Assistant text extracted from completion
        ↓
Sent to user channel (streaming/non-streaming)
        ↓
[Phase 4: Commit / Abort Seam]
XiyueMRAdapter.commit_turn() / abort_turn()
        ↓
MindRuntimeHostAdapter.commit_turn() → Projection Promoted
```

---

## 2. Technical Audit of the 7 Key Dimensions

### 2.1 Body Request Object
* **Contract/Schema**: Hermes uses an OpenAI-compatible payload format sent to the LLM backend (Ark / DeepSeek / AMD Radeon endpoint).
* **Payload Structure**:
  ```json
  {
    "model": "deepseek-v4-flash",
    "messages": [
      {
        "role": "system",
        "content": "<base_system_prompt>\n\nMR CURRENT CONTEXT\nCurrent emotional/behavioral steering:\n- <intent_summary>\n- <emotional_state>\nRelevant current situation:\n- <situation_summary>"
      },
      {"role": "user", "content": "<turn_history_n_minus_1>"},
      {"role": "assistant", "content": "<turn_history_n_minus_1_response>"},
      {"role": "user", "content": "<current_user_message>"}
    ],
    "temperature": 0.2,
    "stream": false
  }
  ```
* **Seam Location**: As demonstrated in `tests/host/test_xiyue_adapter.py:220` (`test_a9_seam_injection`), `render_bounded_context(bounded)` appends the cognitive steering block directly to `agent.ephemeral_system_prompt`.

### 2.2 Body Response Object
* **Current Production Type**:
  Standard OpenAI chat completion response:
  ```json
  {
    "id": "chatcmpl-xxx",
    "choices": [
      {
        "index": 0,
        "message": {
          "role": "assistant",
          "content": "<conversational reply to user>"
        },
        "finish_reason": "stop"
      }
    ],
    "usage": { "prompt_tokens": 120, "completion_tokens": 45, "total_tokens": 165 }
  }
  ```
* **Current Limitation**: Only plain conversational text (`assistant_response`) is returned. There is no structured sidecar in production; semantic parsing is completely absent at the Body level.

### 2.3 Provider Adapter
* **Host Provider Layer**:
  - AutoClaw / Hermes gateway (`openclaw.mjs` / `gateway-bundle.mjs`) communicates via custom OpenAI-compatible endpoints configured in `~/.hermes/profiles/xiyue/config.yaml`.
  - Endpoint providers: Ark-DSF (`https://ark.cn-beijing.volces.com/api/plan/v3`) or AMD Radeon AI inference (`https://developer.amd.com.cn/radeon/api/v1`).
  - Python-side MR adapter: `mind_runtime.host.xiyue_adapter.XiyueMRAdapter`, which talks to `MindRuntimeHostPort` (`mind_runtime.host.runtime_adapter.MindRuntimeHostAdapter`).

### 2.4 Response Parser
* **Current Path**:
  The response parser in Hermes extracts `choice.message.content`, checks for tool calls if enabled, and strips trailing whitespace/markdown formatting (per `display.final_response_markdown: strip`).
* **Required One-Pass Seam**:
  The parser must be adapted to accept either:
  1. A composite JSON envelope (`BodyTurnResultV1`), OR
  2. A dual-part message format with delimited sections (e.g. ````json:semantic_sidecar ... ```` or JSON object containing `{ "assistant_response": "...", "semantic_sidecar": { ... } }`).
  A deterministic JSON envelope is cleanest and least prone to regex breakage.

### 2.5 Streaming vs. Non-Streaming Behavior
* **Profile Configuration**:
  In `~/.hermes/profiles/xiyue/config.yaml`:
  `streaming.enabled: false` (and platform streaming is disabled: `platforms.telegram.streaming: false`, `discord: false`).
* **One-Pass Implication**:
  - In non-streaming mode: One single response parses both `assistant_response` and `semantic_sidecar`.
  - In future streaming mode: `assistant_response` can be streamed immediately token-by-token (or emitted first in JSON streaming), while `semantic_sidecar` accumulates in the tail without delaying user perception.

### 2.6 JSON / Structured Output Capability of DeepSeek-V4-Flash
* **Model Capability**:
  DeepSeek-V4-Flash natively supports `response_format: {"type": "json_object"}`.
  In Phase 1 experiments (Arm A, 75 cases), DeepSeek-V4-Flash demonstrated 100% adherence to valid JSON when prompted for `SemanticParseResultV1`.
* **One-Pass Envelope Feasibility**:
  Combining `assistant_response` and `semantic_sidecar` into a single JSON schema:
  ```json
  {
    "assistant_response": "string",
    "semantic_sidecar": {
      "schema_version": "semantic_parse_v1",
      "semantic_points": [...],
      "dependencies": [...],
      "unresolved": [...]
    }
  }
  ```
  DeepSeek-V4-Flash can produce both in a single inference pass with negligible token overhead.

### 2.7 Current TurnOrchestrator / Host Seam
* **Pre-inference Seam**:
  ```python
  handle = adapter.begin_turn(
      message=user_msg, channel=channel, session_id=session_id, message_id=msg_id
  )
  # handle contains bounded_context
  ```
* **Host-side Evidence Ingestion**:
  Currently, `MindRuntimeHostAdapter.begin_turn` converts the `HostTurnRequest` into:
  ```python
  Evidence(
      payload={"text": request.user_message},  # RAW UNPARSED TEXT
      ...
  )
  ```
  And in `orchestrator.py:759`:
  `semantic_payload = (("fact.key", _raw_text),)`
  The orchestrator has NO real semantic parser. It relies on a fallback `RuleBasedSemanticProvider` which simply treats the entire raw message as a single unanalyzed blob.
* **Post-inference Seam**:
  ```python
  if final_response:
      adapter.commit_turn(handle)
  else:
      adapter.abort_turn(handle, reason="empty_response")
  ```
* **Where the Sidecar Fits Naturally**:
  The semantic sidecar is generated by the Body LLM during the main turn.
  The Host receives `BodyTurnResultV1`.
  - `assistant_response` is immediately returned to the user.
  - `semantic_sidecar` is fed into `SemanticClosureCompiler` to produce `SemanticBlock[]`.
  - The resulting `SemanticBlock[]` can either be attached to `adapter.commit_turn(...)` or passed into MR fact/cognition storage.
  - Fail-closed property: If `semantic_sidecar` fails validation, `assistant_response` is still sent to the user, and the turn commits with an empty/fallback sidecar (`sidecar = None`).

---

## 3. Comparison: Two-Pass (Shadow Call) vs. One-Pass (Production Target)

| Dimension | Two-Pass Shadow Architecture (Current/Flawed) | One-Pass Architecture (Target) |
| :--- | :--- | :--- |
| **Inference Calls** | 2 LLM calls per turn | **1 LLM call per turn** |
| **Latency** | ~2x Body latency (e.g. 1.2s + 1.1s = 2.3s) | **1x Body latency + ~100ms sidecar overhead** |
| **Cognitive Split** | Assistant understands in Call 1, Parser re-understands in Call 2 | **Single shared understanding generates both response & semantic graph** |
| **Cost** | 2x Input Token ingestion cost | **Zero extra input token cost** |
| **Failure Mode** | Inconsistency between reply & parsed memory | **Strict coherence between assistant intent and memory representation** |
