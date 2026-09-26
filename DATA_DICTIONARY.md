# DATA_DICTIONARY.md — magicpin "Build Vera Better" Challenge

**Complete Data Map, Schemas, & Field-Level Analysis**
*Author: Lead AI & Systems Engineer*

---

## 1. Context Relationship Map

The system operates across **4 primary context entities**. The diagram below demonstrates their structural hierarchy and relationship flow:

```
┌────────────────────────────────────────────────────────────────────────┐
│                            CategoryContext                             │
│  (Vertical Knowledge, Voice Rules, Catalog, Peer Stats, Digests)       │
└───────────────────┬────────────────────────────────────┘
                                    │
                                    ▼ 1:N
┌────────────────────────────────────────────────────────────────────────┐
│                            MerchantContext                             │
│  (Identity, Subscription, Performance, Offers, Signals, Roster Agg)    │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
          1:N Triggers                      1:N Roster
                    │                                │
                    ▼                                ▼
┌───────────────────────┐                ┌───────────────────────────────┐
│    TriggerContext     │                │        CustomerContext        │
│  (Scope, Kind, Payload)                │  (Identity, Relation, Consent)│
└───────────┬───────────┘                └───────────────┬───────────────┘
            │                                            │
            └───────────────────────┬────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │     Conversation      │
                        │ (FSM State, History)  │
                        └───────────────────────┘
```

---

## 2. CategoryContext Schema & Data Map

### 2.1 Entity Description
Slow-changing knowledge pack defining a vertical category (`dentists`, `salons`, `restaurants`, `gyms`, `pharmacies`). Shared across all merchants in the category.

| Field Name | Type | Mutable / Static | Expose to Merchant? | Decision & Composition Impact |
|---|---|---|---|---|
| `slug` | `string` | Static | No | Unique key for category lookup. Determines voice dispatch. |
| `display_name` | `string` | Static | Yes | Surface-level category label. |
| `voice.tone` | `string` | Static | No | Sets LLM persona register (e.g. `peer_clinical` vs `warm_practical`). |
| `voice.register` | `string` | Static | No | Dictates formality level (e.g., `respectful_collegial`). |
| `voice.code_mix` | `string` | Static | No | Sets default language mixing strategy (`hindi_english_natural`). |
| `voice.vocab_allowed` | `list[string]` | Static | Yes (naturally) | Clinical/domain terms allowed in message body (e.g. `caries`, `OPG`, `RVG`). |
| `voice.vocab_taboo` | `list[string]` | Static | **STRICT NO** | Words that trigger penalty if present (`guaranteed`, `100% cure`). |
| `voice.salutation_examples` | `list[string]` | Static | Yes | Formatting prefix for owner greetings (`Dr. {first_name}`). |
| `offer_catalog` | `list[Offer]` | Dynamic (weekly) | Yes | Canonical service+price patterns (e.g. `Dental Cleaning @ ₹299`). |
| `peer_stats` | `object` | Dynamic (monthly) | Yes | Comparative benchmarks (`avg_ctr: 0.030`, `avg_reviews: 62`). |
| `digest` | `list[DigestItem]` | **Dynamic (versioned)** | Yes | Weekly research, compliance, CDE, and trend items. Citation source. |
| `patient_content_library` | `list[Content]` | Dynamic | Yes | Content for `PRO_PATIENT_CONTENT` customer re-sharing. |
| `seasonal_beats` | `list[Beat]` | Static | Yes | Seasonal demand cues (e.g. `exam-stress bruxism Nov-Feb`). |
| `trend_signals` | `list[Signal]` | Dynamic | Yes | Search volume trends (e.g. `clear aligners +62% YoY`). |

---

## 3. MerchantContext Schema & Data Map

### 3.1 Entity Description
Fast-changing business snapshot representing a merchant's current commercial and operational state.

| Field Name | Type | Mutable / Static | Expose to Merchant? | Decision & Composition Impact |
|---|---|---|---|---|
| `merchant_id` | `string` | Static | No | Primary key (`m_001_drmeera_dentist_delhi`). |
| `category_slug` | `string` | Static | No | Foreign key linking to `CategoryContext`. |
| `identity.name` | `string` | Static | Yes | Merchant business title. Must match exactly. |
| `identity.city` | `string` | Static | Yes | Geographic city anchor. |
| `identity.locality` | `string` | Static | Yes | Hyper-local neighborhood anchor (e.g. `Lajpat Nagar`). |
| `identity.languages` | `list[string]` | Static | Yes | Preferred output language list (`["en", "hi"]` -> Hinglish). |
| `identity.owner_first_name` | `string` | Static | Yes | Personal greeting target (`Dr. Meera` or `Suresh`). |
| `subscription.status` | `string` | Dynamic | Yes | `active`, `trial`, `expired`. Determines commercial pitch. |
| `subscription.days_remaining` | `integer` | Dynamic | Yes | Triggers renewal urgency nudges. |
| `performance.views` | `integer` | Dynamic (30d) | Yes | 30-day GBP views metric. Used for loss-aversion framing. |
| `performance.calls` | `integer` | Dynamic (30d) | Yes | Call lead volume. |
| `performance.ctr` | `float` | Dynamic (30d) | Yes | Click-through rate. Evaluated against `peer_stats.avg_ctr`. |
| `performance.delta_7d` | `object` | Dynamic (7d) | Yes | 7-day velocity (`views_pct`, `calls_pct`). Drives spike/dip triggers. |
| `offers` | `list[Offer]` | **Dynamic** | Yes | Must check `status == "active"`. **NEVER promote expired offers**. |
| `signals` | `list[string]` | Dynamic | No | Derived system flags (`stale_posts:22d`, `ctr_below_peer_median`). |
| `customer_aggregate` | `object` | Dynamic | Partial | Roster stats (`high_risk_adult_count`, `lapsed_180d_plus`). |
| `review_themes` | `list[Theme]` | Dynamic | Yes | Sentiment clusters (`wait_time: neg`, `doctor_manner: pos`). |

---

## 4. TriggerContext Schema & Data Map

### 4.1 Entity Description
Event object that prompts message generation.

| Field Name | Type | Mutable / Static | Expose to Merchant? | Decision & Composition Impact |
|---|---|---|---|---|
| `id` | `string` | Static | No | Trigger unique identifier (`trg_001_...`). |
| `scope` | `string` | Static | No | `merchant` (Vera -> Merchant) or `customer` (Merchant -> Customer). |
| `kind` | `string` | Static | No | Event type (`research_digest`, `recall_due`, `ipl_match_today`). |
| `source` | `string` | Static | No | `external` (news/weather/CDE) or `internal` (perf dip/recall). |
| `merchant_id` | `string` | Static | No | Foreign key linking to target `MerchantContext`. |
| `customer_id` | `string | null` | Static | No | Foreign key linking to `CustomerContext` if `scope == "customer"`. |
| `payload` | `dict` | Static | Yes (selectively) | Kind-specific payload data (e.g. `top_item_id`, `match_name`). |
| `urgency` | `integer (1-5)` | Static | No | Ranks queued triggers. Urgency >= 3 prioritizes send. |
| `suppression_key` | `string` | Static | No | Deduplication key in Redis (`research:dentists:2026-W17`). |
| `expires_at` | `ISO8601` | Static | No | Expired triggers are discarded immediately. |

---

## 5. CustomerContext Schema & Data Map

### 5.1 Entity Description
Customer profile used when Vera sends a message *on behalf of the merchant* (`send_as: "merchant_on_behalf"`).

| Field Name | Type | Mutable / Static | Expose to Merchant? | Decision & Composition Impact |
|---|---|---|---|---|
| `customer_id` | `string` | Static | No | Unique customer identifier. |
| `merchant_id` | `string` | Static | No | Associated merchant. |
| `identity.name` | `string` | Static | Yes | Customer name personalization. |
| `identity.language_pref` | `string` | Static | Yes | `hi-en mix`, `english`, `ta-en mix`, `kn-en mix`. Strict language match. |
| `relationship.last_visit` | `ISO8601` | Dynamic | Yes | Computes exact lapse duration (e.g. `5 months since last visit`). |
| `relationship.services_received` | `list[string]` | Dynamic | Yes | Historical services received for targeted recommendations. |
| `state` | `string` | Dynamic | No | `new`, `active`, `lapsed_soft`, `lapsed_hard`, `churned`. |
| `preferences.preferred_slots` | `string` | Static | Yes | Honors time preference (e.g. `weekday_evening` -> offers 5pm/6pm slots). |
| `consent.scope` | `list[string]` | Dynamic | **STRICT NO** | Verify consent before sending (`recall_reminders`, `promotional_offers`). |

---

## 6. Flagged Data Uncertainties & Assumptions

1. **Customer Roster Source of Truth**: Customer profiles in real production live across clinic SaaS (Practo, Dentcubate) or CSV uploads. In the challenge, `customers_seed.json` is the sole authoritative context pushed via `POST /v1/context`.
2. **Offer Origin**: `MerchantContext.offers` contains both `active` and `expired` items. System must filter strictly on `status == "active"` to prevent illegal offer realization.
3. **Suppression Scope**: Suppression keys are scoped per trigger family and window (e.g., `research:dentists:2026-W17`). The system must enforce atomic Redis set-nx for 7-day suppression.
