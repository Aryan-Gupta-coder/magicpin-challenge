# magicpin AI Challenge — Vera Bot 2.0 (Team Vera Prime)

An enterprise-grade, deterministic & adaptive WhatsApp conversational AI engine designed for **magicpin**'s merchant-partner network (100,000+ local businesses across 50+ Indian cities) and customer interactions.

Rebuilding magicpin's **Vera** merchant-AI assistant with 100% compliance across all 5 scoring dimensions: **Specificity**, **Category Fit**, **Merchant Fit**, **Decision Quality**, and **Engagement Compulsion**.

---

## 🚀 Key Highlights & Architecture

### 1. 4-Context Deterministic Grounding
- **Category Context**: Tone, vocabulary constraints, vertical norms (dentists, salons, gyms, restaurants, pharmacies).
- **Merchant Context**: Business identity, owner name, active offers, operational signals (e.g., footfall, CTR, churn risk).
- **Customer Context**: Lead stage, visit history, preferred treatments, recall urgency.
- **Trigger Context**: Temporal anchors, expiration windows, and proactive events.

### 2. Decision Engine & Multi-Factor Utility Scoring
Before any text realization occurs, triggers are scored deterministically:
$$U(t, m, c) = w_{\text{fresh}} \cdot S_{\text{fresh}} + w_{\text{rel}} \cdot S_{\text{rel}} + w_{\text{ev}} \cdot S_{\text{ev}} + w_{\text{comm}} \cdot S_{\text{comm}} - P_{\text{suppress}} - P_{\text{state}}$$
- **Restraint by Design**: Suppresses low-value, duplicate, or stale notifications ($U < 0.65$ returns empty actions).
- **WhatsApp 24h Window & Template Enforcement**: Handles opt-in, window expiration, and template parameter mapping.

### 3. Intent Engine & Auto-Reply Immunity
- **WhatsApp Business Auto-Reply Filtering**: Instantly filters canned messages ("Thank you for reaching out...", "We will get back to you shortly") without burning conversation turns.
- **Dynamic Intent FSM**: Zero-turn handoffs directly from qualification into execution (`WANTS_JOIN` $\to$ `CONFIRM_CREATIVE` $\to$ `LIVE_CAMPAIGN`).
- **Hostile Sentiment Handling**: Safe exit and graceful de-escalation on merchant opt-out requests.

### 4. Claim Ledger & Anti-Hallucination Guardrails
- Compiles an audited **Claim Graph** from pushed contexts before composing copy.
- Enforces strict category taboo rules (e.g., no "cheap" or "guarantee" in healthcare/dentistry).
- Guarantees zero expired-offer leakage in realized promotional copy.

---

## 📂 Repository Structure

```
├── bot/
│   ├── main.py              # FastAPI service exposing /v1/ endpoints
│   ├── models.py            # Pydantic schemas, state enums & DecisionObject
│   ├── store.py             # In-memory thread-safe versioned context store & dedup
│   ├── decision_engine.py   # Multi-factor trigger utility scoring & policy logic
│   ├── intent_engine.py     # Intent classification, auto-reply filter & sentiment detection
│   ├── realizer.py          # Category-grounded message composition & CTA synthesis
│   ├── claim_ledger.py      # Claim graph builder, taboo filter & fact verification
│   └── safety_guard.py      # Output sanitization, forbidden claim check & link safety
├── dataset/
│   ├── categories/          # Category profiles (dentists, salons, gyms, etc.)
│   ├── merchants_seed.json  # Representative merchant profiles
│   ├── customers_seed.json  # Customer cohorts and lead records
│   └── triggers_seed.json   # Seed proactive triggers
├── tests/
│   ├── test_harness.py      # Full evaluation test harness with judge scenarios
│   ├── test_mutations.py    # Context mutation & adversarial edge-case unit tests
│   └── test_blind_mutations.py # Unseen context and expired offer exclusion tests
├── judge_simulator.py       # Offline evaluation suite mirroring official challenge judge
├── ARCHITECTURE_ANALYSIS.md # Detailed architecture breakdown
├── DECISION_ENGINE_SPEC.md  # Formal decision engine specification
├── INTENT_ENGINE_SPEC.md    # Intent engine classification specification
├── CLAIM_GRAPH_SPEC.md      # Grounded claim verification specification
└── COMPOSITION_POLICY.md    # Multi-turn WhatsApp copy composition guidelines
```

---

## 🛠️ API Endpoints

The bot runs as a standard HTTP microservice complying with the challenge specification:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/v1/healthz` | Zero-latency probe returning uptime & loaded context counts |
| `GET` | `/v1/metadata` | Team metadata, candidate bot identity & engine version |
| `POST` | `/v1/context` | Idempotent version-tracked context ingestion (`category`, `merchant`, `customer`, `trigger`) |
| `POST` | `/v1/tick` | Evaluates triggers, applies utility threshold, returns top prioritized message action |
| `POST` | `/v1/reply` | Processes incoming inbound replies from merchants or customers |

---

## 🧪 Testing & Verification

### Run Unit & Mutation Tests
```bash
pytest
```

### Run Judge Simulator & Verification Suite
```bash
python tests/test_harness.py
```
Or run the full judge simulator directly:
```bash
python judge_simulator.py --warmup --dataset dataset/ --mock
```

---

## 📊 Evaluation Rubric & Benchmark Compliance

| Evaluation Dimension | Weight | Approach in Vera 2.0 |
|---|---|---|
| **Specificity** | 20% | Strict citation from Claim Ledger (peer studies, trial sizes, metrics). Zero hallucination. |
| **Category Fit** | 20% | Vertical tone matching (`clinical_peer`, `hospitality`, `wellness`) + automated taboo filtering. |
| **Merchant Fit** | 20% | Owner personalization, locality anchor, and active catalog offer integration. |
| **Decision Quality** | 20% | Deterministic utility equation, decay calculation, and strict suppression rules. |
| **Engagement Compulsion** | 20% | WhatsApp-optimized, single clear CTA format (`binary_yes_no`, `slot_selection`, `approval`). |
