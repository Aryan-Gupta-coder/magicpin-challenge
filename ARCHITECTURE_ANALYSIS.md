# ARCHITECTURE_ANALYSIS.md — magicpin "Build Vera Better" Challenge

**System & Judge Reverse-Engineering Analysis**
*Author: Lead AI & Systems Engineer*

---

## 1. System Overview & Challenge Intent

The magicpin **"Build Vera Better"** AI Challenge tasks participants with designing and deploying a competition-grade AI assistant for Indian local merchants (restaurants, salons, gyms, dentists, pharmacies). Vera operates over WhatsApp, driving business growth, Google Business Profile (GBP) optimization, customer recall campaigns, and instant customer service on behalf of local merchants.

Rather than building a basic LLM prompt wrapper, this architecture analysis reverse-engineers the **judge simulator contract**, **evaluation dimensions**, **operational penalties**, and **hidden failure modes** from `challenge-brief.md`, `challenge-testing-brief.md`, `judge_simulator.py`, `engagement-design.md`, and `engagement-research.md`.

---

## 2. Reverse-Engineered Judge Contract & Requirements

### 2.1 HTTP API Surface & Endpoints
The candidate bot must expose **5 HTTPS/HTTP JSON endpoints**:

1. `POST /v1/context`
   - **Purpose**: Ingestion of slow-changing (category, merchant, customer) or fast-changing (trigger) data.
   - **Contract**: Idempotent on `(context_id, version)`. Re-pushing an existing version returns HTTP `409 Conflict` (`{"accepted": false, "reason": "stale_version", "current_version": X}`). Higher versions replace prior versions atomically.
   - **Response**: HTTP 200 `{"accepted": true, "ack_id": "...", "stored_at": "..."}`.

2. `POST /v1/tick`
   - **Purpose**: Periodic wake-up signal from judge harness (default: every 5 simulated minutes).
   - **Input**: `{"now": "<ISO8601>", "available_triggers": ["trg_001", "trg_002"]}`.
   - **Contract**: Bot evaluates stored context and active triggers. Returns zero or more proactive send actions.
   - **Output**: `{"actions": [ { "conversation_id": "...", "merchant_id": "...", "customer_id": null, "send_as": "vera" | "merchant_on_behalf", "trigger_id": "...", "template_name": "...", "template_params": [...], "body": "...", "cta": "...", "suppression_key": "...", "rationale": "..." } ]}`.
   - **Restraint Rule**: Returning `{"actions": []}` is valid and rewarded when no trigger warrants messaging.

3. `POST /v1/reply`
   - **Purpose**: Receives simulated merchant or customer reply turn.
   - **Input**: `{"conversation_id": "...", "merchant_id": "...", "customer_id": "...", "from_role": "merchant" | "customer", "message": "...", "received_at": "...", "turn_number": int}`.
   - **Contract**: Bot responds within **30 seconds**.
   - **Output Options**:
     - `{"action": "send", "body": "...", "cta": "...", "rationale": "..."}`
     - `{"action": "wait", "wait_seconds": 1800, "rationale": "..."}`
     - `{"action": "end", "rationale": "..."}`

4. `GET /v1/healthz`
   - **Purpose**: Liveness probe polled every 60s.
   - **Output**: `{"status": "ok", "uptime_seconds": N, "contexts_loaded": {"category": 5, "merchant": 50, "customer": 200, "trigger": 100}}`.

5. `GET /v1/metadata`
   - **Purpose**: Bot & team identification probe.
   - **Output**: `{"team_name": "...", "team_members": [...], "model": "...", "approach": "...", "version": "..."}`.

---

## 3. Detailed Answers to 16 Core Judge Questions

### 1. Required Endpoints?
`POST /v1/context`, `POST /v1/tick`, `POST /v1/reply`, `GET /v1/healthz`, `GET /v1/metadata`.

### 2. Required Request/Response Schemas?
Strict JSON schemas matching `challenge-testing-brief.md` §2 and validated by `judge_simulator.py`. Missing keys (`conversation_id`, `send_as`, `trigger_id`, `cta`, `suppression_key`, `rationale`, `body`) cause action disqualification (score = 0).

### 3. How does `/v1/context` work?
Stateful ingestion of context objects across 4 scopes (`category`, `merchant`, `customer`, `trigger`). Stored in an atomic in-memory/database store keyed by `(scope, context_id)`.

### 4. How does versioning work?
Every context payload contains an integer `version`. If `pushed_version <= stored_version`, reject with HTTP 409 `stale_version`. If `pushed_version > stored_version`, atomically replace the payload and update context pointers.

### 5. How does `/v1/tick` work?
Judge passes current time and active `available_triggers`. Bot performs trigger filtering, suppression checks, and context composition. Must respond within **30 seconds** (budget limit).

### 6. How does `/v1/reply` work?
Delivers merchant/customer turn. Bot maintains multi-turn state machine. Bot decides to advance (`action: "send"`), back off (`action: "wait"`), or terminate (`action: "end"`).

### 7. How does conversation state work?
State is keyed by `conversation_id`. The candidate bot must maintain turn history, state machine status, auto-reply counters, and active intent stage. Reusing an existing `conversation_id` in `/v1/tick` is invalid.

### 8. What are the canonical test cases?
A set of **30 test pairs** (and 10 deep case studies) covering 5 vertical categories (dentists, salons, restaurants, gyms, pharmacies), external events (IPL, research digests, weather, regulatory changes), internal data spikes/dips, and customer-facing recall/refill triggers.

### 9. What are the scoring dimensions?
Scored 0–10 each (total 50 per composition) by an LLM Judge:
1. **Specificity**: Concrete, verifiable numbers, dates, source citations, catalog prices.
2. **Category Fit**: Tone, allowed vocabulary, taboos, register matching vertical (e.g. clinical peer for dentists vs. coach tone for gyms).
3. **Merchant Fit**: Personalization to owner first name, exact locality, metrics, offer availability, and language preference.
4. **Trigger Relevance / Decision Quality**: Clear reason for "why now", leveraging trigger payload data, selecting correct action.
5. **Engagement Compulsion**: Cialdini levers (loss aversion, curiosity, social proof, effort externalization, single binary CTA).

### 10. What causes penalties?
- **Data Fabrication**: -2 points per invented fact/number/citation/competitor.
- **Internal Jargon Exposure**: -1 point for leaking system keys or raw JSON terms.
- **URL in Message Body**: -3 points per URL (Meta template compliance violation).
- **Verbatim Message Repetition**: -2 points per duplicate message in a conversation.
- **Operational Failures**: -10 for 3x healthz failure, -1 per tick/reply timeout (>30s), -2 for malformed JSON or empty body.

### 11. How are adaptive scenarios injected?
During Phase 3, the judge injects mid-test context updates without warning:
- Version bumps on category digests (e.g. new DCI regulatory circulars).
- Performance metric shifts on merchant snapshots.
- New customer profiles and sudden recall triggers.
Bots that dynamically adapt compositions to new context score bonus points (+5/dim); bots sending stale context fail.

### 12. How can stale context hurt us?
If a bot caches merchant metrics or category digests statically without updating its atomic store on version bumps, it will generate messages citing outdated CTRs or expired offers, triggering heavy **Specificity** and **Merchant Fit** penalties.

### 13. How are repeated/auto-replies tested?
In Phase 4 Replay (`auto_reply_hell`), the judge sends identical WhatsApp Business auto-replies ("Thank you for contacting us...") 4 turns in a row.
- Turn 1 auto-reply: Bot can acknowledge politely.
- Turn 2 auto-reply: Bot must switch to `action: "wait"`.
- Turn 3+ auto-reply: Bot must issue `action: "end"` to preserve resources and avoid spam.

### 14. What does the judge expect regarding `actions=[]`?
When available triggers have low urgency, are suppressed, or lack merchant fit, returning `actions: []` is the **correct, rewarded engineering decision**. Restraint beats spam.

### 15. What behavior is explicitly rewarded?
- Direct service+price offers ("Haircut @ ₹99", "Dental Cleaning @ ₹299").
- Source citations with exact pages ("JIDA Oct 2026 p.14").
- Hindi-English (Hinglish) code-mixing matching merchant language preference (`languages: ["en", "hi"]`).
- Contrarian, data-backed advice (e.g., advising a restaurant NOT to run a promo during Saturday night IPL because dine-in drops 12%).
- Instant transition to action execution upon explicit merchant commitment ("YES", "do it", "kar do").

### 16. What behavior is explicitly penalized?
- Generic discount spam ("Flat 30% off", "Grow your business").
- Asking qualifying questions AFTER the merchant has already said "YES / let's do it".
- Continuing to message after merchant hostility or 3x auto-replies.
- Hallucinating non-existent paper titles, medical claims, or competitor names.

---

## 4. Operational & Performance Budgets

| Metric | Budget / Constraint | Risk Mitigation Strategy |
|---|---|---|
| Latency Per Call | Max 30 seconds | Parallelized LLM realization, deterministic routing pre-filter |
| Max Actions / Tick | 20 actions | Rank triggers by urgency × fit score |
| Payload Size Cap | 500 KB per `/v1/context` | In-memory JSON indexing, zero-copy pointer swaps |
| Rate Limits | 10 requests/sec from judge | Async FastAPI non-blocking event loop |
| Replay Depth | Up to 5 turns deep | Explicit deterministic FSM state transition table |

---

## 5. Architectural Failure Modes Summary

1. **Prompt Injection / Jailbreak via Merchant Replies**: Merchant sends malformed or abusive text; LLM leaks system instructions. (*Mitigation: Input sanitization + fallback guard*).
2. **Infinite Turn Loops**: Bot and simulated merchant exchange infinite polite acknowledgments. (*Mitigation: Turn counter cap at 5 turns max*).
3. **Language Mismatch**: Sending pure English to a `hi-en mix` merchant or native Hindi to an `en` only merchant. (*Mitigation: Deterministic language rule validator*).
4. **Offer Expiry Hallucination**: Promoting an offer whose status is `"expired"`. (*Mitigation: Active offer filter in data normalizer*).
