# CASE_STUDY_ANALYSIS.md — magicpin "Build Vera Better" Challenge

**Detailed Analysis of 10 Benchmark Case Studies**
*Author: Lead AI & Systems Engineer*

---

## 1. Executive Summary

This document evaluates the 10 reference case studies provided in `examples/case-studies.md`. These represent the gold standard for composition quality, earning scores of 44 to 50 out of 50.

We extract the **underlying reasoning patterns**, **CTA mechanisms**, **category-specific registers**, and **anti-patterns** that must NOT be blindly hardcoded or literally copied.

---

## 2. Case-by-Case Analytical Breakdown

### Case 1 — Dentists / Research Digest (`m_001_drmeera_dentist_delhi`)
- **Scope**: Merchant-facing (`send_as: "vera"`).
- **Trigger**: `research_digest` (JIDA Oct 2026 3-mo fluoride trial).
- **Context Signals**: 2.1% CTR (below peer), 124 high-risk adult patients.
- **Decision Pattern**: Share high-authority clinical trial abstract relevant to her specific patient cohort; offer to pull paper + draft patient-ed WhatsApp post.
- **Personalization**: Anchored on her high-risk adult patient count from `customer_aggregate`.
- **Engagement Mechanism**: Source citation (`JIDA Oct 2026 p.14`) + Reciprocity ("I'll pull it for you").
- **CTA Pattern**: Open-ended ("Want me to pull it + draft a patient-ed WhatsApp?").
- **Score**: 50/50.
- **What NOT to Copy**: Do not copy "JIDA Oct 2026 p.14" verbatim for other triggers; citation MUST dynamically match the actual `digest` item.

---

### Case 2 — Dentists / Recall Reminder (`c_001_priya_for_m001`)
- **Scope**: Customer-facing (`send_as: "merchant_on_behalf"`).
- **Trigger**: `recall_due` (6-month cleaning recall).
- **Context Signals**: Lapsed 5mo, prefers `weekday_evening`, language `hi-en mix`. Active offer `"Dental Cleaning @ ₹299"`.
- **Decision Pattern**: Friendly, non-preachy recall notice from clinic; offer 2 specific weekday evening slots + complimentary fluoride add-on.
- **Personalization**: Name, exact lapse time (5mo), language code-mix, slot timing matching preference.
- **Engagement Mechanism**: Convenience + Service+Price value anchor (`₹299 cleaning + complimentary fluoride`).
- **CTA Pattern**: Multi-choice slot selection ("Reply 1 for Wed, 2 for Thu, or tell us a time that works").
- **Score**: 49/50.
- **What NOT to Copy**: Do not offer 6pm/5pm slots if customer prefers `saturday_morning`.

---

### Case 3 — Salons / Bridal Followup (`c_005_kavya_for_m003`)
- **Scope**: Customer-facing (`send_as: "merchant_on_behalf"`).
- **Trigger**: `wedding_package_followup` (Bridal trial completed 5 weeks ago).
- **Context Signals**: Wedding date 2026-11-08 (196 days away), preferred Saturday slot.
- **Decision Pattern**: Congratulate & cue 30-day skin-prep program before peak season; offer preferred Saturday 4pm slot block.
- **Personalization**: Exact days-to-wedding count (196 days), owner first name (`Lakshmi`), trial history reference.
- **Engagement Mechanism**: Urgency/window framing + effort externalization ("block your preferred slot").
- **CTA Pattern**: Single binary slot confirmation ask ("Want me to block your preferred Saturday 4pm slot?").
- **Score**: 47/50.

---

### Case 4 — Salons / Curious Ask (`m_003_studio11_salon_hyderabad`)
- **Scope**: Merchant-facing (`send_as: "vera"`).
- **Trigger**: `curious_ask_due` (Weekly curiosity cadence).
- **Context Signals**: Last touch 3 days ago, high growth.
- **Decision Pattern**: Ask merchant what service was most requested this week; promise to convert answer into Google post + customer WhatsApp reply template.
- **Personalization**: Owner first name (`Lakshmi`), Studio11 salon name.
- **Engagement Mechanism**: Asking-the-merchant lever (Cialdini advice lever) + Upfront reciprocity offer.
- **CTA Pattern**: Low-friction open question ("what service has been most asked-for this week?").
- **Score**: 44/50.

---

### Case 5 — Restaurants / IPL Match Day (`m_005_pizzajunction_restaurant_delhi`)
- **Scope**: Merchant-facing (`send_as: "vera"`).
- **Trigger**: `ipl_match_today` (DC vs MI at 7:30pm today - Saturday).
- **Context Signals**: Trial tier, active BOGO pizza offer.
- **Decision Pattern**: Warn owner that Saturday night IPL matches reduce dine-in covers by 12%; advise pivoting active BOGO offer to delivery-only on Swiggy/Insta.
- **Personalization**: Owner name (`Suresh`), active BOGO offer reference.
- **Engagement Mechanism**: Loss aversion (-12% covers) + Contrarian data-backed coaching.
- **CTA Pattern**: Binary action proposal ("Want me to draft the Swiggy banner + Insta story? Live in 10 min.").
- **Score**: 50/50.

---

### Case 6 — Restaurants / Active Planning Intent (`m_006_southindiancafe_restaurant_bangalore`)
- **Scope**: Merchant-facing (`send_as: "vera"`).
- **Trigger**: `active_planning_intent` (Merchant asked about corporate thali package).
- **Context Signals**: High volume, 18 thali orders/day avg, Indiranagar locality.
- **Decision Pattern**: Deliver a complete tiered B2B corporate thali menu draft with pricing, volume discounts, and named local office tech parks; offer to draft outreach text for facility managers.
- **Personalization**: Indiranagar locality, named tech parks (Embassy Tech, RMZ Eco, Sigma Soft), South Indian menu items (filter coffee, dosa platter).
- **Engagement Mechanism**: Complete artifact delivery (zero effort required from merchant).
- **CTA Pattern**: Single binary execution ask ("Want me to draft a 3-line WhatsApp to send their facilities managers?").
- **Score**: 49/50.

---

### Case 7 — Gyms / Seasonal Dip Reframe (`m_007_powerhouse_gym_bangalore`)
- **Scope**: Merchant-facing (`send_as: "vera"`).
- **Trigger**: `seasonal_perf_dip` (April views down 30%).
- **Context Signals**: 245 active members, HSR Layout locality.
- **Decision Pattern**: Reframe 30% view drop as normal April-June acquisition lull (-25 to -35% industry benchmark); advise saving ad spend for Sept-Oct resolution season; suggest internal retention challenge for 245 members.
- **Personalization**: Exact view drop (-30%), exact active member count (245 members), HSR Layout benchmark.
- **Engagement Mechanism**: Anxiety pre-emption + Benchmark social proof + Budget protection.
- **CTA Pattern**: Binary offer ("Want me to draft a 'summer attendance challenge' to keep them through the dip?").
- **Score**: 48/50.

---

### Case 8 — Gyms / Customer Lapse Winback (`c_010_rashmi_for_m007`)
- **Scope**: Customer-facing (`send_as: "merchant_on_behalf"`).
- **Trigger**: `customer_lapsed_hard` (57 days since last visit).
- **Context Signals**: Previous training focus was weight loss, 5-month member history.
- **Decision Pattern**: Send warm, no-shame winback message highlighting a new Tue/Thu 6:30pm HIIT class aligned with weight loss; offer free trial spot next Tuesday.
- **Personalization**: Owner name (`Karthik`), weight loss goal match, exact lapse time (8 weeks).
- **Engagement Mechanism**: No-shame empathy ("happens to most members, no judgment") + Risk-free commitment ("no auto-charge").
- **CTA Pattern**: Single binary trial reservation ask ("Want me to hold a free trial spot for you next Tue, 30 Apr? Reply YES").
- **Score**: 50/50.

---

### Case 9 — Pharmacies / Compliance Alert (`m_009_apollo_pharmacy_jaipur`)
- **Scope**: Merchant-facing (`send_as: "vera"`).
- **Trigger**: `supply_alert` (Voluntary recall on 2 atorvastatin batches by Mfr Z).
- **Context Signals**: 240 chronic-Rx customers, Malviya Nagar Jaipur.
- **Decision Pattern**: Issue urgent compliance warning regarding recalled batches AT2024-1102 & AT2024-1108; report that 22 of his chronic patients received these batches; offer customer note + replacement workflow draft.
- **Personalization**: Owner name (`Ramesh`), exact derived patient impact (22 of 240 chronic-Rx customers).
- **Engagement Mechanism**: Operational urgency + Risk mitigation + Instant workflow solution.
- **CTA Pattern**: Binary workflow ask ("Want me to draft their WhatsApp note + the replacement-pickup workflow?").
- **Score**: 50/50.

---

### Case 10 — Pharmacies / Chronic Refill Reminder (`c_013_grandfather_for_m009`)
- **Scope**: Customer-facing (`send_as: "merchant_on_behalf"`).
- **Trigger**: `chronic_refill_due` (Metformin/atorvastatin/telmisartan run out April 28).
- **Context Signals**: Senior citizen (65-75), channel via son's WhatsApp, senior discount 15% active.
- **Decision Pattern**: Send respectful `Namaste` notification to son detailing 3 medicines, 15% senior discount applied (₹1,420 total, ₹240 saved), free home delivery tomorrow by 5pm.
- **Personalization**: Molecule names, senior discount calculations, locality (`Malviya Nagar`), respectful cultural salutation.
- **Engagement Mechanism**: Trust + Calculated financial savings + Frictionless re-order.
- **CTA Pattern**: Multi-path simple ask ("Reply CONFIRM to dispatch, or call 9876543210 if any change in dosage.").
- **Score**: 49/50.

---

## 3. Generalizable CTA & Compulsion Principles

1. **Binary Choice Primacy**: For action triggers, prefer binary commitment asks (`Reply YES / NO` or `Reply CONFIRM`).
2. **Multi-Choice for Slots/Refills Only**: Booking flows allow 2 explicit options (`Reply 1 for Wed, 2 for Thu`).
3. **Effort Externalization**: Always combine an ask with an pre-drafted asset ("I've drafted X — want me to send?").
4. **No-Shame Framing for Lapsed Customers**: Normalize lapses in gyms/salons ("happens to most members, no judgment").
5. **Exact Metric Anchoring**: Always cite 1-2 exact figures from the context (`2,100-patient trial`, `22 of 240 patients`, `196 days to wedding`).
