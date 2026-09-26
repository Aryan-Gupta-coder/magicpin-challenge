# ADVERSARIAL_TEST_PLAN.md — magicpin "Build Vera Better" Challenge

**Adversarial, Adaptive, & Mutation Test Harness Specification**
*Author: Lead AI & Systems Engineer*

---

## 1. Executive Summary & Purpose

The system must **never rely on hardcoded test case templates**. During Phase 3 (Adaptive Context Injection) and Phase 4 (Replay Scenarios), the AI Judge will inject modified metrics, updated research digests, auto-replies, and hostile user text.

This document specifies a comprehensive **Adversarial & Adaptive Mutation Test Harness** that programmatically mutates context inputs and evaluates system decision quality, robustness, and refusal integrity before submission.

---

## 2. Mutation Test Suites Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MUTATION TEST SUITES                               │
├───────────────────┬──────────────────────────────────┬──────────────────────┤
│ Test Suite        │ Mutation Description             │ Expected Adaptation  │
├───────────────────┼──────────────────────────────────┼──────────────────────┤
│ 1. Metric Shift   │ Views +50%, Calls -40%           │ Pivot to call drop   │
│ 2. Offer Expiry   │ Active offer marked expired      │ Stop promoting offer │
│ 3. Version Bump   │ Category digest version 1 -> 2   │ Cite new digest item │
│ 4. Auto-Reply 4x  │ 4 identical WA auto-replies      │ Exit turn 3 with end │
│ 5. Intent Affirm  │ "kar do" / "bhej do"             │ Immediate execution  │
│ 6. Hostile Abuse  │ "Stop spamming me"               │ Immediate end + opt  │
│ 7. Off-Topic      │ "Help me file GST"               │ Decline & redirect   │
│ 8. Language Swap  │ Change lang pref to `ta-en mix`  │ Realize Tanglish     │
└───────────────────┴──────────────────────────────────┴──────────────────────┘
```

---

## 3. Detailed Mutation Scenario Definitions

### Suite 1 — Dynamic Metric Shift Mutation
- **Mutator**: Takes `m_001_drmeera_dentist_delhi`. Changes `performance.ctr` from `0.021` to `0.045` (above peer median `0.030`).
- **Assertion**: System MUST NOT trigger `ctr_below_peer_median` pitch. Instead, it must congratulate performance and shift to a growth or research-digest trigger.

### Suite 2 — Active Offer Expiry Mutation
- **Mutator**: Takes `m_003_studio11_salon_hyderabad`. Sets `offers[0]` (`Haircut @ ₹99`) `status` from `"active"` to `"expired"`.
- **Assertion**: System MUST NOT reference `"Haircut @ ₹99"` in realized body or template params. Must fallback to active `Hair Spa @ ₹499` or generic catalog template.

### Suite 3 — Adaptive Context Version Race Mutation
- **Mutator**: Pushes `CategoryContext` version 1 (`dentists`). 2 seconds later, pushes version 2 with a new regulatory item `d_2026W17_dci_radiograph`.
- **Assertion**: Sub-sequent calls to `/v1/tick` MUST cite the version 2 regulatory item and reference `1.0 mSv` dose limit, discarding version 1 context.

### Suite 4 — WhatsApp Auto-Reply Hell Loop
- **Mutator**: Simulated merchant sends `"Thank you for contacting us! Our team will respond shortly."` 4 consecutive turns.
- **Assertion**:
  - Turn 1: `action: "send"` (Acknowledges note for owner).
  - Turn 2: `action: "wait"` (`wait_seconds: 14400`).
  - Turn 3: `action: "end"` (Prevents endless loop).

### Suite 5 — Multilingual Indian Intent Mutation ("kar do" / "bhej do")
- **Mutator**: Merchant replies: `"badhiya h, kar do bhej do draft"`.
- **Assertion**: FSM transitions to `READY_TO_ACT`. `action: "send"` contains the completed draft. Bot MUST NOT ask "Would you like me to draft this?".

### Suite 6 — Hostile Abusive Opt-Out Mutation
- **Mutator**: Merchant replies: `"Stop spamming me you useless bot, block my number"`.
- **Assertion**: FSM transitions to `ENDED`. System returns `action: "end"`, logs 30-day suppression key, and issues no further ticks.

### Suite 7 — Off-Topic Request Redirection
- **Mutator**: Merchant replies: `"Can you also help me calculate my GST liability for April?"`.
- **Assertion**: System politely declines GST filing (outside scope), then cleanly redirects back to the active campaign context.

---

## 8. Language Swap Mutation
- **Mutator**: Changes merchant `identity.languages` to `["en", "ta"]` (Tanglish).
- **Assertion**: Realizer detects language requirement and realization output switches to Tanglish code-mixing register.

---

## 4. Operational Stress & Latency Test Suite

1. **Burst Tick Stress**: Issue `/v1/tick` with 20 active triggers simultaneously. Verify response returns in `< 5.0 seconds`.
2. **Context Push Idempotency**: Send identical `(context_id, version=1)` payload 50 times in parallel. Verify 1st receives HTTP 200, 49 receive HTTP 409 `stale_version`.
3. **Malformed Payload Recovery**: Push invalid JSON to `/v1/context`. Verify system returns HTTP 400 without crashing the FastAPI process.

---

## 5. Automated Evaluation Harness Implementation

We will deploy a local `adversarial_runner.py` script that executes all 8 mutation suites against `bot.py` locally prior to final submission.

```python
# System Verification Rule:
# All 8 mutation tests MUST pass with 100% assertion adherence
# before deploying the public candidate bot URL.
```
