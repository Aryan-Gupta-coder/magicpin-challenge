# INTENT_ENGINE_SPEC.md — magicpin "Build Vera Better" Challenge

**Multi-Tier Intent Engine, Similarity Auto-Reply Detector, & Decoupled State Specification**
*Author: Lead AI & Systems Engineer*

---

## 1. Executive Summary & Intent Hierarchy

In `judge_simulator.py` (Phase 4 Replay Scenarios), the AI Judge tests candidate bots on:
1. **Auto-Reply Hell** (Detecting repeated WhatsApp Business auto-replies).
2. **Intent Transition** (Switching to action mode immediately when merchant says "YES / let's do it").
3. **Hostile / Off-Topic Handling** (Handling abuse or out-of-scope GST filing questions gracefully).

V1 architecture combined conversation states, merchant intents, and trigger lifecycles into a single monolithic state machine. **V2 Architecture decouples these into 3 independent Orthogonal State Entities**.

---

## 2. Decoupled Orthogonal State Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ORTHOGONAL STATE MODEL (V2)                           │
├──────────────────────────┬──────────────────────────┬───────────────────────┤
│ Entity 1:                │ Entity 2:                │ Entity 3:             │
│ ConversationState        │ MerchantIntentState      │ TriggerLifecycleState │
├──────────────────────────┼──────────────────────────┼───────────────────────┤
│ • IDLE                   │ • UNKNOWN                │ • PENDING             │
│ • PROACTIVE_SENT         │ • POSITIVE_ACK           │ • PROMOTED            │
│ • AWAITING_RESPONSE      │ • EXPLICIT_EXECUTION     │ • ACKNOWLEDGED        │
│ • QUALIFYING             │ • CONDITIONAL_EXECUTION  │ • EXECUTING           │
│ • READY_TO_ACT           │ • DEFER_LATER            │ • COMPLETED           │
│ • EXECUTING              │ • REJECTION              │ • SUPPRESSED          │
│ • COMPLETED              │ • OPT_OUT_HOSTILE        │ • EXPIRED             │
│ • WAIT_BACKOFF           │ • AUTO_REPLY_DETECTED    │                       │
│ • ENDED                  │ • QUESTION_OFF_TOPIC     │                       │
└──────────────────────────┴──────────────────────────┴───────────────────────┘
```

---

## 3. Multi-Tier Intent Classification Engine

When a merchant or customer sends a reply message, the `IntentEngine` processes it through **3 classification tiers**:

```
Inbound Reply Message Text
           │
           ▼
[ Tier 1: Pattern & Keyword Pre-Filter ]
   - Check exact Hinglish & English execution phrases ("kar do", "bhej do", "yes send it")
   - Check explicit opt-out/hostile phrases ("stop messaging", "useless spam")
           │
           ▼
[ Tier 2: Similarity-Based Auto-Reply Detector ]
   - Jaccard Similarity & N-gram overlap against historical turns in this conversation
   - Canned phrase clustering ("Thank you for contacting...", "automated assistant")
           │
           ▼
[ Tier 3: Semantic Intent Resolver ]
   - Differentiates POSITIVE_ACK ("Sounds good") from EXPLICIT_EXECUTION ("Yes, do it now")
   - Differentiates DEFER_LATER ("Maybe next week") from REJECTION ("No thanks")
```

### 3.1 Intent Categorization & Execution Rules

| Classified Intent | Examples | FSM Action Target | Routing Response |
|---|---|---|---|
| **`EXPLICIT_EXECUTION`** | `"yes send it"`, `"kar do"`, `"bhej do"`, `"ok let's do it"` | `ConversationState` -> `READY_TO_ACT` -> `EXECUTING` | Output execution draft asset immediately. Do NOT ask qualification questions. |
| **`POSITIVE_ACK`** | `"Sounds good"`, `"Thanks for sharing"`, `"accha"` | `ConversationState` -> `QUALIFYING` | Low-friction follow-on suggestion. |
| **`DEFER_LATER`** | `"Maybe later"`, `"next week dekhange"`, `"busy today"` | `ConversationState` -> `WAIT_BACKOFF` | `action: "wait"` (`wait_seconds: 86400`). |
| **`REJECTION`** | `"No thanks"`, `"nahin chahiye"`, `"not interested"` | `ConversationState` -> `ENDED` | `action: "end"`. Set 7-day suppression key. |
| **`OPT_OUT_HOSTILE`** | `"Stop messaging me"`, `"don't spam"`, `"useless"` | `ConversationState` -> `ENDED` | `action: "end"`. Set 30-day merchant suppression key. |
| **`AUTO_REPLY_DETECTED`**| `"Thank you for contacting...", "automated assistant"` | `ConversationState` -> `AUTO_REPLY` | Turn 1: Note to owner. Turn 2: `wait`. Turn 3: `end`. |
| **`QUESTION_OFF_TOPIC`**| `"Can you help file GST?"`, `"What is your location?"` | `ConversationState` -> `QUALIFYING` | Decline out-of-scope ask politely; redirect cleanly. |

---

## 4. Advanced Similarity-Based Auto-Reply Detector

Rather than hardcoding a single fixed text string, the `AutoReplyDetector` calculates a similarity metric $S$ between the current turn $T_n$ and prior turns $\{T_1, \dots, T_{n-1}\}$:

$$S(T_n, T_{n-1}) = 0.5 \cdot \text{Jaccard}(T_n, T_{n-1}) + 0.5 \cdot \text{LevenshteinRatio}(T_n, T_{n-1})$$

### Auto-Reply Detection Rules:
1. **Verbatim / High Similarity ($S \ge 0.85$)**: Same canned auto-reply text sent again. Increment `auto_reply_turn_count`.
2. **Canned Cluster Pattern Match**: Matches regex signatures of common WhatsApp Business auto-responders:
   - `r'thank\s+you\s+for\s+contacting'`
   - `r'our\s+team\s+will\s+respond'`
   - `r'automated\s+assistant'`
   - `r'aapki\s+jaankari\s+ke\s+liye\s+shukriya'`
3. **Multi-Turn Backoff Thresholds**:
   - `auto_reply_turn_count == 1`: Respond with `action: "send"` ("Looks like an auto-reply 😊 When owner sees this, reply YES...").
   - `auto_reply_turn_count == 2`: Respond with `action: "wait"` (`wait_seconds: 14400`).
   - `auto_reply_turn_count >= 3`: Respond with `action: "end"` (Prevents turn waste & endless loops).

---

## 5. Explicit Challenge Citations

- **`judge_simulator.py` §7.3 (Auto-Reply Scenario)**:
  *"Turn 1: Sending auto-reply... Turn 3: Bot WAITING... Turn 4: Bot ENDED — detected auto-reply pattern!"*
- **`judge_simulator.py` §7.4 (Intent Transition Scenario)**:
  *"Merchant: 'Ok lets do it. Whats next?' ... Bot correctly switched to ACTION mode... Penalty: Bot is STILL QUALIFYING after commitment"*
- **`challenge-brief.md` §3 (Pain Points)**:
  *"1. Auto-reply pollution: 40-70% of merchant replies are WhatsApp Business canned auto-replies. Better detection + faster routing wins."*
