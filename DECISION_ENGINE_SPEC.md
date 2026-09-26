# DECISION_ENGINE_SPEC.md — magicpin "Build Vera Better" Challenge

**Decision Engine & Trigger Utility Scoring Specification**
*Author: Lead AI & Systems Engineer*

---

## 1. Overview & Architectural Intent

The **Decision Engine** is the central brain responsible for deciding **whether to send a message**, **what signal to anchor on**, **what CTA format to use**, and **what facts are approved for realization**.

Crucially, **the LLM is NOT permitted to make structural decisions independently**. Instead, the Decision Engine deterministically constructs an immutable `DecisionObject`. The LLM's role is strictly limited to realizing this `DecisionObject` into natural language.

---

## 2. Explicit `DecisionObject` Schema

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class DecisionObject:
    # 1. Action Decision
    action: str                        # "send" | "suppress" | "wait" | "end"
    why_now: str                       # Explains the temporal anchor (e.g. "JIDA Oct issue landed this week")
    
    # 2. Trigger & Target Context
    trigger_id: str
    trigger_kind: str
    merchant_id: str
    customer_id: Optional[str]
    send_as: str                       # "vera" | "merchant_on_behalf"
    
    # 3. Context Provenance & Version Tracking
    context_versions: Dict[str, int]   # {"category": 1, "merchant": 2, "trigger": 1, "customer": 1}
    
    # 4. Strategy & Target Audience
    primary_signal: str                # Key context signal (e.g. "high_risk_adult_cohort", "ctr_below_peer")
    supporting_signals: List[str]      # Secondary signals (e.g. "stale_posts:22d")
    recommended_strategy: str          # Realization strategy (e.g. "peer_clinical_digest_with_patient_ed")
    audience_segment: str              # Target audience description (e.g. "High-risk adult patients")
    
    # 5. Scoring & Urgency
    utility_score: float               # Calculated utility score (0.0 to 1.0)
    priority: int                      # Urgency ranking (1 to 5)
    
    # 6. CTA & Structural Formatting
    cta_type: str                      # "none" | "open_ended" | "binary_yes_no" | "confirmation" | "slot_selection" | "constrained_choice"
    template_name: Optional[str]       # WhatsApp 24h window template name
    template_params: List[str]         # Approved template parameters
    suppression_key: str               # Dedup key for Redis/in-memory store
    
    # 7. Fact Ledger & Safety Boundaries
    approved_facts: List[Dict[str, Any]] # Approved Claim Graph nodes
    forbidden_claims: List[str]        # Forbidden topics/words (from category taboos & expired offers)
    confidence: float                  # Decision confidence rating (0.0 to 1.0)
```

---

## 3. Multi-Factor Trigger Utility Scoring Engine

Rather than relying on naive thresholds like `urgency >= 3 = send`, the Decision Engine computes a normalized **Trigger Utility Score $U(t, m, c)$** across candidate triggers:

$$U(t, m, c) = w_{\text{fresh}} \cdot S_{\text{fresh}} + w_{\text{rel}} \cdot S_{\text{rel}} + w_{\text{ev}} \cdot S_{\text{ev}} + w_{\text{comm}} \cdot S_{\text{comm}} - P_{\text{suppress}} - P_{\text{state}}$$

### 3.1 Scoring Components & Weights

| Component | Weight ($w$) | Calculation Logic | Challenge File Citation |
|---|---|---|---|
| **Freshness ($S_{\text{fresh}}$)** | `0.20` | Decay function: $1.0 - \frac{\text{now} - \text{delivered\_at}}{\text{expires\_at} - \text{delivered\_at}}$. Drops to 0 at expiration. | `challenge-brief.md` §4.3 |
| **Relevance ($S_{\text{rel}}$)** | `0.30` | Match score between `trigger.payload` and `merchant.signals` / `customer.state`. | `engagement-design.md` §4 |
| **Evidence Strength ($S_{\text{ev}}$)** | `0.25` | 1.0 if source-cited paper/circular; 0.8 if metric spike/dip; 0.5 if generic beat. | `examples/case-studies.md` |
| **Commercial Value ($S_{\text{comm}}$)**| `0.25` | Estimated ROI or retention impact (e.g. high-risk patient recall = high value). | `challenge-brief.md` §3 |
| **Suppression Penalty ($P_{\text{suppress}}$)**| `1.00` | 1.0 if `suppression_key` is active in store (forces score to 0). | `challenge-testing-brief.md` §2.2 |
| **State Penalty ($P_{\text{state}}$)** | `0.50` | 0.5 if conversation is already `AWAITING_RESPONSE` (prevents double-tick messaging). | `judge_simulator.py` |

---

## 4. Decision Thresholds & Send vs. Suppress Rules

- **Send Threshold**: If $U(t, m, c) \ge 0.65$, trigger is approved for composition.
- **Top-1 Selection**: If multiple triggers exceed `0.65`, select the single trigger with the highest utility score $U$.
- **Restraint Rule**: If no candidate trigger achieves $U(t, m, c) \ge 0.65$, return `actions: []`.

> **Reference Citation (`challenge-testing-brief.md` FAQ §14)**:
> *"Q: Can my bot refuse to send when nothing's worth saying? A: Yes — return `{"actions": []}` from `/v1/tick`. Restraint is rewarded; spam is penalized."*
