# COMPOSITION_POLICY.md — magicpin "Build Vera Better" Challenge

**Composition Modes, URL Safety Pipeline, & CTA Engine Specification**
*Author: Lead AI & Systems Engineer*

---

## 1. Executive Summary & Composition Architecture

To avoid calling LLMs indiscriminately—which causes latency spikes, cost waste, and risk of malformed output—we establish a **Three-Mode Composition Policy**:

- **Mode A: Deterministic Template Engine** (High speed, zero cost, fixed structured flows).
- **Mode B: Constrained LLM Realizer** (Proactive trigger-driven merchant/customer messages based on `DecisionObject`).
- **Mode C: Conversational LLM Realizer** (Multi-turn replies, complex merchant questions, out-of-scope redirection).

---

## 2. Three-Mode Composition Policy Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       COMPOSITION MODE MATRIX                               │
├─────────────────┬───────────────────────┬───────────────────────────────────┤
│ Mode            │ When Used             │ Implementation Mechanism          │
├─────────────────┼───────────────────────┼───────────────────────────────────┤
│ **Mode A:       │ • Initial WhatsApp 24h│ Python string template engine     │
│ Deterministic   │   template params     │ with Fact Ledger parameter lookup.│
│ Template**      │ • Fallback on LLM fail│ Zero LLM calls.                   │
├─────────────────┼───────────────────────┼───────────────────────────────────┤
│ **Mode B:       │ • All proactive tick  │ Structured LLM Realizer           │
│ Constrained LLM │   sends (`/v1/tick`)  │ Prompted strictly on DecisionObject│
│ Realizer**      │ • Execution drafts    │ + Claim Graph. Temp = 0.0.        │
├─────────────────┼───────────────────────┼───────────────────────────────────┤
│ **Mode C:       │ • Merchant replies    │ Conversational LLM Realizer       │
│ Conversational  │   (`/v1/reply`)       │ Incorporates past conversation    │
│ LLM Realizer**  │ • Off-topic questions │ turns + current IntentState.      │
└─────────────────┴───────────────────────┴───────────────────────────────────┘
```

---

## 3. URL Safety & Re-Prompting Pipeline

In `judge_simulator.py` and `api-call-examples.md` §F.4:
> *"HTTP URLs in message bodies are penalized -3 points per URL (Meta WhatsApp template violation)."*

To guarantee zero URL violations, all realized messages pass through a **4-step URL Safety Pipeline**:

```
Realized Message Body
          │
          ▼
1. URL Detector: Regex Scan for r'https?://\S+|www\.\S+'
          │
          ▼
2. Is URL detected in Message Body?
   ├─► NO  : Message Body Approved.
   └─► YES : URL SAFETY VIOLATION DETECTED!
          │
          ▼
3. Re-prompt LLM Realizer:
   "CRITICAL ERROR: Your message contained an HTTP URL ('<url>'). 
    Meta WhatsApp rules STRICTLY PROHIBIT URLs in body text. 
    Rewrite the message immediately, removing the URL while preserving 
    the exact factual claim and CTA."
          │
          ▼
4. Deterministic Clean Reframe (Fallback):
   If re-prompt still contains URL, strip URL string cleanly and append:
   "(Abstract available on request)" or "(Details on your dashboard)".
```

---

## 4. Comprehensive CTA Engine

The **CTA Engine** selects the exact Call-to-Action format based on `DecisionObject.cta_type` and `ConversationState`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CTA ENGINE TYPES                               │
├──────────────────────┬───────────────────────────────┬──────────────────────┤
│ CTA Type             │ Standard Formatting Pattern   │ Permitted Contexts   │
├──────────────────────┼───────────────────────────────┼──────────────────────┤
│ `none`               │ (No trailing question)        │ Pure information     │
│                      │                               │ alerts, opt-out notes│
├──────────────────────┼───────────────────────────────┼──────────────────────┤
│ `open_ended`         │ "What service was most        │ Curiosity asks,      │
│                      │  requested this week?"        │ research digests     │
├──────────────────────┼───────────────────────────────┼──────────────────────┤
│ `binary_yes_no`      │ "Want me to draft the post?   │ Action triggers,     │
│                      │  Reply YES / NO."             │ campaign proposals   │
├──────────────────────┼───────────────────────────────┼──────────────────────┤
│ `confirmation`       │ "Reply CONFIRM to dispatch    │ High-value execution │
│                      │  to 40 adult patients."       │ (bulk messages)      │
├──────────────────────┼───────────────────────────────┼──────────────────────┤
│ `slot_selection`     │ "Reply 1 for Wed 6pm,         │ Patient / customer   │
│                      │  2 for Thu 5pm."              │ appointment recalls  │
├──────────────────────┼───────────────────────────────┼──────────────────────┤
│ `constrained_choice` │ "Reply A for 10-pack,         │ B2B corporate menu   │
│                      │  B for 25-pack."              │ package choices      │
└──────────────────────┴───────────────────────────────┴──────────────────────┘
```

### Selection Rules:
1. **Action Triggers (`research_digest`, `perf_spike`)**: Default to `binary_yes_no` or `open_ended`.
2. **Customer Recall (`recall_due`)**: Default to `slot_selection` (2 options matching customer timing preference).
3. **Execution Intent ("kar do")**: Default to `confirmation` ("Reply CONFIRM to dispatch...").
4. **Safety Alerts (`supply_alert`)**: Default to `binary_yes_no` ("Want me to draft the patient note?").

---

## 5. Explicit Challenge Citations

- **`api-call-examples.md` §F.4**:
  *"URL in body: Read more: https://magicpin.com/blog -> Hard fail for that action — Meta would reject. Penalty: -3 per URL."*
- **`challenge-brief.md` §5 (Constraints)**:
  *"3. Single primary CTA — binary choice (YES/STOP) for action triggers; no CTA acceptable for pure-information triggers."*
