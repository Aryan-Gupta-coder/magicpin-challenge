# PROPOSED_ARCHITECTURE_V2.md — magicpin "Build Vera Better" Challenge

**Revised Second-Pass System Architecture & Technical Specification**
*Author: Lead AI & Systems Engineer*

---

## 1. Executive Summary & V2 Architecture Vision

Following a rigorous second-pass audit against `challenge-brief.md`, `challenge-testing-brief.md`, `judge_simulator.py`, `api-call-examples.md`, `case-studies.md`, `engagement-design.md`, and `engagement-research.md`, we have completely revised the system architecture.

The V1 architecture suffered from potential brittleness: relying on simple numeric thresholds (`urgency >= 3`), monolithic state machines, exact regex fact matching, and over-reliance on LLMs for decision making.

**V2 Architectural Pivot**:
1. **Decouple Decision from Realization**: The **Decision Engine** deterministically evaluates context and trigger signals to output a strictly structured `DecisionObject`. The LLM's sole role in proactive sends is realizing an audited decision into natural language.
2. **Replace Static Urgency Thresholds with Multi-Factor Utility Scoring**: A mathematical utility function balances trigger freshness, commercial relevance, consent, evidence strength, and merchant/customer state.
3. **Upgrade Fact Ledger to a Graph of Permitted Transformations**: Legitimate value representations (e.g. `2580` -> `2.58k` -> `~2.6k` views; `0.021` -> `2.1% CTR`) are explicitly tracked in a Claim Graph.
4. **Decouple State Models**: We separate **Conversation State**, **Merchant Intent**, and **Trigger Lifecycle** into three independent orthogonal state entities.
5. **Multi-Mode Composition Policy**: Three specialized modes (Mode A: Deterministic Template, Mode B: Constrained LLM, Mode C: Conversational LLM) prevent wasteful LLM calls and reduce latency.
6. **Thread-Safe In-Memory Storage**: Eliminates external Redis dependencies to guarantee zero-latency operation and 100% `/v1/healthz` reliability.

---

## 2. System Topology & Component Map

```
┌────────────────────────────────────────────────────────────────────────┐
│                        HTTP Ingress (FastAPI)                          │
│     POST /v1/context   POST /v1/tick   POST /v1/reply   GET /v1/*       │
└───────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               In-Memory Atomic Store (RLock Protected)                 │
│      Stores (scope, context_id) -> {version, payload, timestamp}       │
└───────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              Decision Engine (DECISION_ENGINE_SPEC.md)                 │
│   Calculates Utility Score U(t, m, c) -> Produces DecisionObject       │
└───────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              Composition Engine (COMPOSITION_POLICY.md)                │
│    Routes to Mode A (Template), Mode B (Constrained), Mode C (Conv)    │
└───────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│            Claim Graph Validator (CLAIM_GRAPH_SPEC.md)                 │
│      Verifies extracted claims against Permitted Transformations       │
└───────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              URL & Safety Guard (COMPOSITION_POLICY.md)                │
│       Detects URLs -> Re-prompts / Reframes -> Enforces Single CTA      │
└───────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              Orthogonal State Store (INTENT_ENGINE_SPEC.md)            │
│   Persists (Conversation State x Merchant Intent x Trigger Lifecycle)  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. High-Level Decision Flow for `/v1/tick`

```
[ POST /v1/tick ]
       │
       ▼
1. Fetch available_triggers list from request body
       │
       ▼
2. Load matching TriggerContext, MerchantContext, CategoryContext, CustomerContext from Store
       │
       ▼
3. Filter expired triggers (now > trigger.expires_at) or suppressed keys
       │
       ▼
4. Evaluate Utility Function U(t, m, c) for each candidate trigger:
   U = (W_fresh * Freshness) + (W_rel * Relevance) + (W_ev * Evidence) + (W_comm * CommercialValue) - Penalty
       │
       ▼
5. Is max(U) >= Decision Threshold (0.65)?
   ├─► NO  : Return {"actions": []}  [Restraint rewarded, avoids spam]
   └─► YES : Select Top-1 Decision Candidate
       │
       ▼
6. Build immutable DecisionObject + Claim Graph
       │
       ▼
7. Dispatch to Composition Policy (Mode B: Constrained LLM)
       │
       ▼
8. Validate realized message via Claim Graph Engine & URL Safety Guard
       │
       ▼
9. Update Trigger Lifecycle to PROMOTED & record suppression key
       │
       ▼
10. Return {"actions": [ActionPayload]} to Judge
```

---

## 4. High-Level Decision Flow for `/v1/reply`

```
[ POST /v1/reply ]
       │
       ▼
1. Load ConversationState, MerchantIntentState, and TriggerLifecycle from Store
       │
       ▼
2. Pass message to Multi-Tier Intent Classifier (INTENT_ENGINE_SPEC.md):
   - Check similarity-based Auto-Reply detector (Jaccard + N-gram + turn repeats)
   - Classify Intent: EXPLICIT_EXECUTION ("kar do", "yes send"), POSITIVE_ACKNOWLEDGMENT,
     DEFER_LATER, REJECTION, HOSTILE, QUESTION, OFF_TOPIC
       │
       ▼
3. Update Orthogonal State Entities:
   - MerchantIntentState -> EXPLICIT_EXECUTION
   - ConversationState   -> READY_TO_ACT
       │
       ▼
4. Determine Routing Action:
   ├─► AUTO_REPLY >= 2 turns : action: "wait" (wait_seconds: 14400)
   ├─► AUTO_REPLY >= 3 turns : action: "end"
   ├─► HOSTILE / REJECTION   : action: "end" (Set 30-day merchant suppression)
   ├─► DEFER_LATER           : action: "wait" (wait_seconds: 86400)
   ├─► EXPLICIT_EXECUTION    : Mode B/C Composition -> Output Execution Asset (Draft)
   └─► QUESTION / OFF_TOPIC   : Mode C Composition -> Answer & Clean Redirection
       │
       ▼
5. Pass Realized Response through Claim Graph & URL Safety Guard
       │
       ▼
6. Update Conversation State & Return JSON to Judge
```

---

## 5. Performance & Operational Reliability Budget

| Metric | Target | Enforced Mechanism |
|---|---|---|
| `/v1/healthz` Latency | < 2 ms | In-memory atomic data structures, zero IO |
| `/v1/context` Ingestion | < 5 ms | `threading.RLock()` protected dictionary updates |
| `/v1/tick` Processing | < 2.5 s | Deterministic utility filtering before LLM call |
| `/v1/reply` Processing | < 3.0 s | Fast intent pre-classification + single LLM turn |
| Max Response Timeout | 30.0 s | 15.0 s timeout on LLM HTTP client with fallback |
| Memory Footprint | < 150 MB | Low-overhead Python dataclasses |

---

## 6. Code Module Structure Specification

```
bot/
├── main.py                        # FastAPI endpoints (/v1/context, /v1/tick, /v1/reply, etc.)
├── store/
│   ├── memory_store.py            # Thread-safe in-memory context store with RLock
│   └── models.py                  # Dataclasses for Category, Merchant, Trigger, Customer
├── engine/
│   ├── decision_engine.py         # Utility calculation & DecisionObject generator
│   ├── claim_graph.py             # Permitted transformations & claim verification engine
│   ├── intent_engine.py           # Multi-tier intent classifier & similarity auto-reply detector
│   └── state_machine.py           # Orthogonal states (Conversation, Intent, Trigger)
├── composition/
│   ├── policy_router.py           # Mode A, Mode B, Mode C composition router
│   ├── llm_client.py              # Unified LLM provider client (OpenAI, Gemini, Anthropic, Ollama)
│   ├── prompt_templates.py        # Category & intent prompts
│   └── safety_guard.py            # URL detector, re-prompter, & single CTA validator
└── tests/
    └── test_mutation_suite.py     # Local test runner verifying all 8 mutation suites
```
