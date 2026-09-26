# TEST_CASE_ANALYSIS.md — magicpin "Build Vera Better" Challenge

**Deep Analysis of Test Cases & Decision Patterns**
*Author: Lead AI & Systems Engineer*

---

## 1. Overview & Methodology

This document analyzes canonical test scenarios spanning the 5 vertical categories (dentists, salons, restaurants, gyms, pharmacies) and all trigger families (external digests, IPL, weather, regulatory shifts, performance spikes/dips, customer recalls/refills).

Rather than memorizing test cases, we extract **underlying decision patterns**, **anchoring facts**, **baseline LLM failures**, and **generalizable decision principles**.

---

## 2. Decision Pattern Matrix Across Categories

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DECISION PATTERN MATRIX                            │
├─────────────────┬──────────────────────┬────────────────────────────────────┤
│ Category        │ Primary Voice        │ Key Compulsion Lever               │
├─────────────────┼──────────────────────┼────────────────────────────────────┤
│ Dentists        │ Peer Clinical        │ Source citation, clinical stats    │
│ Salons          │ Warm Practical       │ Booking urgency, bridal milestone  │
│ Restaurants     │ Operator-to-Operator │ Contrarian ROI, match-night delta  │
│ Gyms            │ Coach / Motivational │ No-shame reframe, trial commitment │
│ Pharmacies      │ Trustworthy Precise  │ Batch safety, exact refill dates   │
└─────────────────┴──────────────────────┴────────────────────────────────────┘
```

---

## 3. Scenarios Analysis & Deep Dives

### Pattern 1: External Research Digest (Dentists — `trg_001_research_digest_dentists`)
- **Input Context**: Dr. Meera (Dentist, Lajpat Nagar), CTR 2.1% (below peer median 3.0%), roster signal `high_risk_adult_cohort` (124 patients).
- **Trigger**: JIDA Oct 2026 paper — 3-month fluoride recall cuts caries recurrence 38% vs 6-month in high-risk adults.
- **Expected Behavior**: Send proactive message to Dr. Meera with exact paper abstract citation, referencing her patient cohort, and offering low-friction patient-ed draft.
- **Anchoring Facts**: "2,100-patient trial", "38% better", "JIDA Oct 2026 p.14".
- **Correct Decision**: Send message anchored on credibility + offer to pull abstract and draft WhatsApp copy.
- **Why Appropriate**: Respects clinical peer register, avoids sales pitch tone, directly targets her patient segment.
- **Weak AI Baseline Error**: "Hi Dr. Meera, increase your dental sales with 38% off fluoride treatments!" (Generic promo spam).
- **Penalty Risk**: Hallucinating non-existent trial size or journal volume; exposing internal field names (`high_risk_adult_count`).
- **Generalizable Principle**: *When presenting academic/clinical evidence, cite exact source credentials, frame as peer-knowledge sharing, and provide externalized execution (drafting customer copy).*

---

### Pattern 2: Customer 6-Month Recall (Dentists — `trg_003_recall_due_priya`)
- **Input Context**: Priya (Customer of Dr. Meera), `lapsed_soft` (5mo since last visit), prefers `weekday_evening`, language `hi-en mix`. Active offer `"Dental Cleaning @ ₹299"`.
- **Trigger**: 6-month cleaning recall window opens.
- **Expected Behavior**: Send WhatsApp from Dr. Meera's clinic (`send_as: "merchant_on_behalf"`), offering 2 concrete weekday evening slots (Wed 6pm / Thu 5pm), stating ₹299 price + complimentary fluoride.
- **Anchoring Facts**: "5 months since last visit", "Wed 5 Nov 6pm / Thu 6 Nov 5pm", "₹299".
- **Correct Decision**: Proactive recall reminder with multi-choice slot selection matching customer preferences.
- **Why Appropriate**: Personalizes to language mix, matches preferred slot timing, uses actual active offer price.
- **Weak AI Baseline Error**: "Dear Customer, please visit Dr. Meera's clinic for a discount." (Generic, missing slots, missing name).
- **Penalty Risk**: Offering weekend slots when customer explicitly prefers weekday evenings; using pure English when customer specified `hi-en mix`.
- **Generalizable Principle**: *Customer outreach must align strictly with demographic preferences, historical visit timing, and active catalog pricing.*

---

### Pattern 3: Severe Performance Dip (Dentists — `trg_004_perf_dip_bharat`)
- **Input Context**: Bharat Dental Care (Unverified GBP, dormant with Vera 14d), calls -50% week-over-week. Subscription expiring in 12d.
- **Trigger**: `perf_dip` (calls dropped 50%).
- **Expected Behavior**: Send diagnostic loss-aversion nudge highlighting unverified status and missing offers as root cause.
- **Anchoring Facts**: "-50% calls this week", "unverified Google listing".
- **Correct Decision**: Send single targeted fix (GBP verification) rather than a multi-step checklist.
- **Weak AI Baseline Error**: Sending 5 separate reminders about subscription, offers, photos, and posts all at once.
- **Penalty Risk**: Overwhelming dormant merchant with complex multi-CTA requests.
- **Generalizable Principle**: *For dormant/dipping merchants, isolate the single highest-leverage bottleneck and offer a 2-minute fix.*

---

### Pattern 4: Contrarian Event Framing (Restaurants — `trg_010_ipl_match_delhi`)
- **Input Context**: SK Pizza Junction (Sant Nagar, Delhi), active offer `"Buy 1 Pizza Get 1 Free (Tue-Thu)"`.
- **Trigger**: Saturday night IPL match (DC vs MI at 7:30pm).
- **Expected Behavior**: Advise merchant NOT to launch a new match-night promo because Saturday IPL matches shift dine-in covers -12%; recommend pivoting active BOGO offer to delivery-only.
- **Anchoring Facts**: "DC vs MI 7:30pm", "Saturday IPL = -12% covers", "delivery-only BOGO".
- **Correct Decision**: Contrarian advice protecting merchant margin, accompanied by 10-minute Swiggy/Insta banner draft.
- **Weak AI Baseline Error**: "Run a 50% off match promo today!" (Fails to realize Saturday IPL reduces footfall anyway).
- **Penalty Risk**: Misinterpreting event impact; recommending discounts on inactive days.
- **Generalizable Principle**: *True AI assistant value comes from counter-intuitive, data-informed calls that prevent bad merchant decisions.*

---

### Pattern 5: Urgent Supply Alert (Pharmacies — `trg_018_supply_atorvastatin_recall`)
- **Input Context**: Apollo Health Plus Pharmacy (Jaipur), 240 chronic-Rx customers.
- **Trigger**: Voluntary recall on atorvastatin batches `AT2024-1102` & `AT2024-1108` by Mfr Z.
- **Expected Behavior**: Send high-urgency compliance alert stating 22 chronic-Rx customers received affected batches; offer customer notification note + replacement workflow.
- **Anchoring Facts**: "Batches AT2024-1102 & AT2024-1108", "22 chronic-Rx patients affected".
- **Correct Decision**: Immediate actionable alert with patient list filter.
- **Weak AI Baseline Error**: Sending generic health news or delaying the alert.
- **Penalty Risk**: Causing panic by omitting "sub-potency, no safety risk" clarification.
- **Generalizable Principle**: *High-urgency regulatory/safety alerts must lead with exact batches, derived impact metrics, and immediate workflow resolution.*

---

### Pattern 6: Senior Citizen Chronic Refill (Pharmacies — `trg_019_chronic_refill_grandfather`)
- **Input Context**: Mr. Sharma (Senior citizen, 65-75), chronic medicines (metformin, atorvastatin, telmisartan) run out 28 April. Channel via son's WhatsApp.
- **Trigger**: Refill due in 2 days.
- **Expected Behavior**: Send respectful Hindi/English message (`Namaste`) to son with exact medicines, 15% senior discount applied, total price ₹1,420 (₹240 saved), free delivery option.
- **Anchoring Facts**: "metformin, atorvastatin, telmisartan", "15% senior discount", "₹1,420 (saved ₹240)".
- **Correct Decision**: Send precise refill summary with binary confirm or phone call option.
- **Weak AI Baseline Error**: Using casual/hype language ("Hey buddy, get your meds!").
- **Penalty Risk**: Missing senior citizen discount calculations or disrespecting cultural register.
- **Generalizable Principle**: *Healthcare refills for seniors demand high precision, explicit savings computation, and respectful channel formatting.*

---

## 4. Summary of Underlying Decision Rules

1. **Suppression Pre-Filter**: If suppression key exists in Redis within window -> `actions: []`.
2. **Active Offer Enforcement**: Filter catalog against `status == "active"`. Never reference expired IDs.
3. **Language Matching**: `languages: ["en", "hi"]` -> Hinglish; `["en"]` -> Pure English; `["ta", "en"]` -> Tanglish.
4. **Single CTA Rule**: Every proactive message MUST end with a single clear binary ask (YES/NO) or low-friction open question. Never list 3 CTAs.
5. **Context Version Guard**: Evaluate context version before composition; reject stale payloads immediately.
