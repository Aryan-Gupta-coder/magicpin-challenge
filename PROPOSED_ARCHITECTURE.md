# PROPOSED_ARCHITECTURE.md — magicpin "Build Vera Better" Challenge

**Competition-Grade Hybrid System Architecture**
*Author: Lead AI & Systems Engineer*

---

## 1. Architectural Philosophy & Strategy

We reject the naive pattern of passing raw context JSON into a single monolithic prompt wrapper. Instead, we propose a **Hybrid Pipeline Architecture** that strictly separates:
- **Deterministic logic** (filtering, routing, suppression, catalog validation, state machine transitions, safety checks).
- **LLM Reasoning & Language Realization** (contextual synthesis, tone adaptation, Hinglish code-mixing, rationale generation).

This architecture guarantees sub-3 second latency, zero offer hallucinations, robust auto-reply handling, and maximum scores across all 5 judge dimensions.

---

## 2. End-to-End Processing Pipeline

The system consists of **10 distinct execution stages**:

```
[ HTTP Ingress / FastAPI Endpoint ]
              │
              ▼
Stage 1: Atomic Context Store & Version Manager
              │
              ▼
Stage 2: Context Normalizer & Active Offer Filter
              │
              ▼
Stage 3: Trigger Analyzer & Suppression Engine
              │
              ▼
Stage 4: Deterministic Decision & Action Router
              │
              ▼
Stage 5: Conversation State Machine (FSM) Transition
              │
              ▼
Stage 6: Fact & Claim Ledger Assembler
              │
              ▼
Stage 7: LLM Realizer & Prompt Composer
              │
              ▼
Stage 8: Grounding & Fact Verification Engine
              │
              ▼
Stage 9: Message, Language & URL Safety Validator
              │
              ▼
Stage 10: Final Response Realization & State Persistence
```

### Stage Details:
1. **Atomic Context Store**: Thread-safe in-memory store indexing `(scope, context_id)` -> `{version, payload}`. Handles version bumps and returns HTTP 409 on stale pushes.
2. **Context Normalizer**: Resolves active offers (`status == "active"`), computes customer lapse durations, formats owner greetings, and extracts peer benchmark deltas.
3. **Trigger Analyzer**: Filters expired triggers, evaluates urgency (1-5), and checks Redis suppression keys to avoid duplicate sends.
4. **Action Router**: Evaluates whether a trigger warrants messaging. Returns `actions: []` if suppression is active or urgency is insufficient.
5. **State Machine (FSM)**: Manages multi-turn conversation states (`IDLE`, `PROACTIVE_SENT`, `AWAITING_RESPONSE`, `QUALIFYING`, `READY_TO_ACT`, `EXECUTING`, `COMPLETED`, `AUTO_REPLY`, `ENDED`, `WAIT_BACKOFF`).
6. **Fact & Claim Ledger**: Assembles an immutable ledger of verifiable facts (exact CTRs, catalog prices, paper citations, slot times) that the LLM is permitted to reference.
7. **LLM Realizer**: Specialized category-scoped LLM prompt realization (using OpenAI / Anthropic / Gemini API with temperature=0).
8. **Grounding Validator**: Cross-checks realized message body against the Fact Ledger. If the LLM invents a non-ledger number or price, the validator strips or corrects it.
9. **Safety Validator**: Enforces Meta compliance: strips HTTP URLs (penalty avoidance), verifies length, checks taboo vocabulary, and ensures single CTA formatting.
10. **State Persistence**: Saves turn history, updates suppression keys, and returns JSON payload to the Judge.

---

## 3. Decision Boundary Matrix (LLM vs. Deterministic Logic)

| Concern / Decision | Implementation Layer | Rationale |
|---|---|---|
| Context Version Bump & Idempotency | **Deterministic Python** | Must be atomic, zero-latency, and HTTP 409 compliant. |
| Trigger Suppression & Expiration | **Deterministic Redis / Set-NX** | Prevents duplicate sends instantly without wasting LLM tokens. |
| Active Offer Selection | **Deterministic Filter** | Prevents recommending expired or inactive offers. |
| State Machine Transition (YES/NO/Auto-reply) | **Deterministic Intent Router** | Ensures instant switch to action mode; prevents intent handoff failure. |
| Claim Grounding Verification | **Deterministic Fact Matching** | Eliminates numeric hallucinations (-2 judge penalty). |
| URL & Taboo Vocabulary Stripping | **Deterministic Regex Guard** | Eliminates HTTP URL penalty (-3) and legal taboo leaks. |
| Copy Generation & Tone Adaptation | **LLM Realizer (Structured)** | Harnesses LLM creativity for natural peer voice and Hinglish code-mixing. |
| Rationale Explanation Generation | **LLM Realizer** | Produces clear, natural-language rationale for the judge scoring engine. |

---

## 4. Internal Fact & Claim Ledger Architecture

To guarantee **100% Grounding (Zero Hallucination)**, the system builds an immutable `FactLedger` prior to LLM realization:

```python
@dataclass
class ApprovedFact:
    fact_id: str          # e.g., "fact_ctr_meera"
    category: str         # "metric", "price", "citation", "slot", "date"
    raw_value: Any        # 0.021, "299", "JIDA Oct 2026 p.14", "Wed 5 Nov, 6pm"
    formatted_claim: str  # "2.1% CTR", "₹299 cleaning", "JIDA Oct 2026 p.14"
    source_context: str   # "merchant.performance", "category.digest[0]"
    version: int          # context version
```

### Verification Algorithm:
After the LLM Realizer returns a candidate message, the `GroundingValidator`:
1. Extracts all numbers, monetary figures (`₹...`), citations, and dates from the message body via Regex.
2. Cross-references every extracted token against the active `FactLedger`.
3. If an extracted number (e.g., `45% off`) does not exist in the `FactLedger`, the validator triggers an automatic fallback realization or replaces the hallucinated claim with the approved ledger fact.

---

## 5. Explicit Conversation Finite State Machine (FSM)

```
                       ┌──────────────┐
                       │     IDLE     │
                       └──────┬───────┘
                              │
                    Trigger Active / Tick
                              │
                              ▼
                       ┌──────────────┐
                       │PROACTIVE_SENT│
                       └──────┬───────┘
                              │
                       Merchant Reply
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
   Auto-Reply Match      Intent: "YES"     Intent: "STOP"
          │                   │                   │
          ▼                   ▼                   ▼
  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
  │  AUTO_REPLY   │   │ READY_TO_ACT  │   │   REJECTED    │
  └───────┬───────┘   └───────┬───────┘   └───────┬───────┘
          │                   │                   │
   Count >= 2?          Execute Action       Graceful Exit
          │                   │                   │
          ▼                   ▼                   ▼
  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
  │ WAIT_BACKOFF  │   │   EXECUTING   │   │     ENDED     │
  └───────┬───────┘   └───────┬───────┘   └───────────────┘
          │                   │
     Count >= 3          Action Done
          │                   │
          ▼                   ▼
  ┌───────────────┐   ┌───────────────┐
  │     ENDED     │   │   COMPLETED   │
  └───────────────┘   └───────────────┘
```

### Intent Handling Rules:
- **"YES" / "DO IT" / "GO AHEAD" / "kar do" / "bhej do"**: Instantly transitions state from `AWAITING_RESPONSE` -> `READY_TO_ACT` -> `EXECUTING`. Immediately outputs artifact (e.g. drafted post/patient text) without asking further qualifying questions.
- **Auto-Reply ("Thank you for contacting...")**: Increment auto-reply counter. Turn 1: Polite note to owner. Turn 2: Transition to `action: "wait"`. Turn 3: Transition to `action: "end"`.
- **"STOP" / "NO" / "Hostile"**: Immediately transition to `ENDED`. Return `action: "end"` and set 30-day merchant suppression.
