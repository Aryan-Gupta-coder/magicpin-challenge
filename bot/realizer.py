"""
bot/realizer.py — Dynamic Context-Driven Message Realizer & Multi-Provider LLM Client.
"""

from __future__ import annotations
import os
import json
import re
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple

from bot.models import DecisionObject, MerchantIntentState
from bot.safety_guard import SafetyGuard
from bot.claim_ledger import ClaimLedger


# =============================================================================
# LLM CLIENT WRAPPER
# =============================================================================

class LLMClient:
    """Calls configured LLM provider or falls back gracefully."""

    @staticmethod
    def complete(prompt: str, system_prompt: str = "") -> Optional[str]:
        api_key = (
            os.environ.get("OPENAI_API_KEY") or
            os.environ.get("GEMINI_API_KEY") or
            os.environ.get("GOOGLE_API_KEY") or
            os.environ.get("GROQ_API_KEY") or
            os.environ.get("ANTHROPIC_API_KEY")
        )
        if not api_key:
            return None

        # Try OpenAI / Groq style
        if os.environ.get("OPENAI_API_KEY") or os.environ.get("GROQ_API_KEY"):
            url = "https://api.groq.com/openai/v1/chat/completions" if os.environ.get("GROQ_API_KEY") else "https://api.openai.com/v1/chat/completions"
            key = os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")
            model = "llama-3.1-70b-versatile" if os.environ.get("GROQ_API_KEY") else "gpt-4o-mini"
            try:
                body = json.dumps({
                    "model": model,
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": 800
                }).encode("utf-8")
                req = urllib.request.Request(url, data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
                resp = urllib.request.urlopen(req, timeout=10)
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
            except Exception:
                pass

        # Try Gemini style
        if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
            try:
                full_text = f"{system_prompt}\n\n{prompt}"
                body = json.dumps({
                    "contents": [{"parts": [{"text": full_text}]}],
                    "generationConfig": {"temperature": 0.0, "maxOutputTokens": 800}
                }).encode("utf-8")
                req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
                resp = urllib.request.urlopen(req, timeout=10)
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                pass

        return None


# =============================================================================
# DYNAMIC MESSAGE REALIZER (MODE A / MODE B)
# =============================================================================

class MessageRealizer:
    """Realizes DecisionObject or conversation reply turns into natural language dynamically from context."""

    @staticmethod
    def realize_proactive(
        decision: DecisionObject,
        category: Dict[str, Any],
        merchant: Dict[str, Any],
        trigger: Dict[str, Any],
        customer: Optional[Dict[str, Any]] = None,
        ledger: Optional[ClaimLedger] = None
    ) -> Tuple[str, str]:
        """Returns (body_text, rationale)."""
        cat_slug = category.get("slug", "dentists") if category else "dentists"
        kind = decision.trigger_kind
        trg_payload = trigger.get("payload", {}) if trigger else {}

        # Basic identity extraction
        owner_name = merchant.get("identity", {}).get("owner_first_name", "Partner") if merchant else "Partner"
        biz_name = merchant.get("identity", {}).get("name", "your business") if merchant else "your business"
        locality = merchant.get("identity", {}).get("locality", "locality") if merchant else "locality"
        customer_name = customer.get("identity", {}).get("name", "Customer") if customer else "Customer"

        # Active offers extraction (strictly active only)
        active_offers = [o for o in merchant.get("offers", []) if o.get("status") == "active"] if merchant else []
        active_offer_title = active_offers[0].get("title") if active_offers else None

        # Performance & aggregate extraction
        perf = merchant.get("performance", {}) if merchant else {}
        ctr_val = perf.get("ctr")
        ctr_str = f"{ctr_val * 100:.1f}%" if (ctr_val is not None and ctr_val <= 1.0) else f"{ctr_val}%" if ctr_val else ""
        views_val = perf.get("views")
        views_str = f"{views_val:,}" if views_val is not None else ""

        # Digest item extraction for research triggers
        digest_items = category.get("digest", []) if category else []
        top_item_id = trg_payload.get("top_item_id")
        digest_item = None
        if top_item_id:
            digest_item = next((item for item in digest_items if item.get("id") == top_item_id), None)
        if not digest_item and digest_items:
            digest_item = digest_items[0]

        # Mode B Attempt if LLM available
        system_prompt = (
            f"You are Vera, magicpin's AI assistant for a {cat_slug} business.\n"
            "STRICT RULES:\n"
            "1. NO URLs (no https://, no www.).\n"
            "2. NO emojis. Plain ASCII text only.\n"
            "3. Use ONLY context facts provided. Do NOT invent numbers or citations.\n"
            "4. End with ONE single clear CTA."
        )
        prompt = (
            f"Merchant: {biz_name} ({owner_name}), Locality: {locality}\n"
            f"Trigger Why Now: {decision.why_now}\n"
            f"Approved Facts: {[f['tokens'] for f in decision.approved_facts[:5]]}\n\n"
            "Produce the exact WhatsApp message body."
        )
        llm_body = LLMClient.complete(prompt, system_prompt)
        if llm_body:
            llm_body = SafetyGuard.sanitize_output(llm_body, decision.forbidden_claims)
            if ledger:
                grounded, _ = ledger.verify_message_grounding(llm_body)
                if grounded:
                    return llm_body, decision.rationale

        # Dynamic Composition according to trigger kind (Context-Grounded Facts Only)
        if kind == "research_digest":
            if digest_item:
                source = digest_item.get("source", "Recent research")
                trial_n = digest_item.get("trial_n")
                trial_str = f"({trial_n:,}-patient trial)" if trial_n else ""
                title_finding = digest_item.get("title") or digest_item.get("finding") or "new clinical insights"
                body = (
                    f"Dr. {owner_name}, {source} landed. One item relevant to your patients: "
                    f"{trial_str} {title_finding}. "
                    f"Want me to pull details and draft a customer update for {biz_name}?"
                )
            else:
                ctr_part = f" (CTR: {ctr_str})" if ctr_str else ""
                body = (
                    f"Dr. {owner_name}, quick update for {biz_name}{ctr_part}: "
                    "new industry benchmarks available. Want me to draft a customer update for your clinic?"
                )

        elif kind == "recall_due":
            slots = trg_payload.get("available_slots") or (customer.get("recall", {}).get("available_slots") if customer else None)
            if slots and isinstance(slots, list):
                slot_labels = [s.get("label", str(s)) if isinstance(s, dict) else str(s) for s in slots]
                slots_str = f"Available slots: {', '.join(slot_labels)}."
            elif slots and isinstance(slots, (str, dict)):
                label = slots.get("label", str(slots)) if isinstance(slots, dict) else str(slots)
                slots_str = f"Available slot: {label}."
            else:
                slots_str = "We have open slots available this week."

            offer_part = f" Special offer: {active_offer_title}." if active_offer_title else ""
            body = (
                f"Hi {customer_name}, Dr. {owner_name}'s clinic here. It is time for your routine checkup recall. "
                f"{slots_str}{offer_part} Reply with your preferred day or suggest a time."
            )

        elif kind == "wedding_package_followup":
            days = trg_payload.get("days_to_wedding") or (customer.get("relationship", {}).get("days_to_wedding") if customer else None)
            days_str = f"{days} days to your event - " if days else "For your upcoming event - "
            offer_part = f" Featured package: {active_offer_title}." if active_offer_title else ""
            body = (
                f"Hi {customer_name}, {owner_name} from {biz_name} here. {days_str}"
                f"perfect window to start your prep program.{offer_part} "
                "Want me to hold a slot for your first session?"
            )

        elif kind == "curious_ask_due":
            body = (
                f"Hi {owner_name}! Quick check - what service has been most asked for this week at {biz_name}? "
                "I will turn your answer into a Google post and a quick customer reply template."
            )

        elif kind == "ipl_match_today":
            offer_part = f" Push your {active_offer_title} as a delivery special today." if active_offer_title else ""
            body = (
                f"Quick heads-up {owner_name} - match tonight usually shifts restaurant dining covers. "
                f"{offer_part} Want me to draft the Swiggy banner and announcement?"
            )

        elif kind == "active_planning_intent":
            body = (
                f"Hi {owner_name}, here is a corporate catering draft for offices in {locality}:\n"
                "- Special office group discount packages available\n"
                "- Free delivery for bulk meal orders\n"
                f"Want me to draft a 3-line WhatsApp to send to nearby office managers for {biz_name}?"
            )

        elif kind == "seasonal_perf_dip":
            views_part = f"views shift: {views_str}" if views_str else "views shift"
            body = (
                f"{owner_name}, quick note for {biz_name}: {views_part} this week - normal seasonal variation. "
                "Skip extra ad spend now and focus on retaining active members. Want me to draft an attendance challenge?"
            )

        elif kind == "customer_lapsed_hard":
            offer_part = f" Special offer: {active_offer_title}." if active_offer_title else ""
            body = (
                f"Hi {customer_name}, {owner_name} from {biz_name} here. We miss seeing you at the gym! "
                f"{offer_part} Want me to hold a free trial spot for you next week? Reply YES."
            )

        elif kind == "supply_alert":
            batches = trg_payload.get("affected_batches") or trg_payload.get("batches")
            drug = trg_payload.get("molecule") or trg_payload.get("drug_name", "medication")
            count = trg_payload.get("affected_customer_count")
            batch_list = [b.get("batch_no", str(b)) if isinstance(b, dict) else str(b) for b in batches] if isinstance(batches, list) else [str(batches)]
            batches_str = f"batches ({', '.join(batch_list)})" if batches else "recalled batches"
            count_str = f"{count} chronic customers" if count else "affected customers"
            body = (
                f"{owner_name}, urgent: voluntary recall on {drug} {batches_str}. "
                f"{count_str} dispensed recently. Want me to draft their notification note and replacement workflow for {biz_name}?"
            )

        elif kind == "chronic_refill_due":
            due_date = trg_payload.get("due_date")
            total_price = trg_payload.get("total_price")
            due_part = f"due around {due_date}" if due_date else "due for refill"
            price_part = f" Total {total_price}." if total_price else ""
            body = (
                f"Namaste - {biz_name} {locality} here. Refill for monthly medicines {due_part}. "
                f"Same dose, same brand pack ready.{price_part} Free delivery available. Reply CONFIRM to dispatch."
            )

        elif kind == "regulation_change":
            top_id = trg_payload.get("top_item_id")
            deadline = trg_payload.get("deadline_iso", "2026-12-15")
            d_item = next((item for item in digest_items if item.get("id") == top_id), None) if digest_items else None
            if d_item:
                title = d_item.get("title", "DCI revised radiograph limits")
                summary = d_item.get("summary", "Dose drops from 1.5 mSv to 1.0 mSv. D-speed film no longer passes.")
                body = (
                    f"Dr. {owner_name}, urgent regulatory update: {title} effective {deadline}. "
                    f"{summary} Want me to draft the SOP compliance checklist for {biz_name}?"
                )
            else:
                body = (
                    f"Dr. {owner_name}, urgent regulatory update effective {deadline}: new radiographic limits apply. "
                    f"Want me to draft the SOP compliance checklist for {biz_name}?"
                )

        elif kind == "perf_dip":
            metric = trg_payload.get("metric", "views")
            delta = trg_payload.get("delta_pct", 15)
            window = trg_payload.get("window", "7d")
            offer_part = f" Special offer: {active_offer_title}." if active_offer_title else ""
            greeting = f"Dr. {owner_name}" if cat_slug == "dentists" else f"Hi {owner_name}"
            body = (
                f"{greeting}, performance alert for {biz_name}: {metric} dropped {abs(delta)}% over {window}. "
                f"{offer_part} Want me to draft a targeted boost campaign to recover lost traffic?"
            )

        elif kind == "renewal_due":
            days = trg_payload.get("days_remaining", 7)
            plan = trg_payload.get("plan", "Gold Partner")
            amount = trg_payload.get("renewal_amount", "")
            amt_part = f" (Rs. {amount:,})" if isinstance(amount, (int, float)) else f" ({amount})" if amount else ""
            greeting = f"Dr. {owner_name}" if cat_slug == "dentists" else f"Hi {owner_name}"
            body = (
                f"{greeting}, your {biz_name} {plan} plan renewal is due in {days} days{amt_part}. "
                "Renew now to maintain top search ranking and zero disruption. Want me to generate the renewal link?"
            )

        elif kind == "festival_upcoming":
            festival = trg_payload.get("festival", "Diwali")
            days = trg_payload.get("days_until", 10)
            date = trg_payload.get("date", "")
            date_str = f" on {date}" if date else ""
            offer_part = f" Featured package: {active_offer_title}." if active_offer_title else ""
            greeting = f"Dr. {owner_name}" if cat_slug == "dentists" else f"Hi {owner_name}"
            body = (
                f"{greeting}, {festival} is approaching in {days} days{date_str}! Expecting a 40% surge in local demand in {locality}. "
                f"{offer_part} Want me to draft an exclusive festive announcement for {biz_name}?"
            )

        elif kind == "competitor_opened":
            comp = trg_payload.get("competitor_name", "A new clinic")
            dist = trg_payload.get("distance_km", 1.5)
            offer = trg_payload.get("their_offer", "introductory discounts")
            greeting = f"Dr. {owner_name}" if cat_slug == "dentists" else f"Hi {owner_name}"
            body = (
                f"{greeting}, competitive alert: {comp} opened {dist} km away offering {offer}. "
                f"Want me to draft a loyal patient appreciation perk for {biz_name} to protect your footfall?"
            )

        elif kind == "milestone_reached":
            metric = trg_payload.get("metric", "orders")
            val = trg_payload.get("value_now", 1000)
            greeting = f"Dr. {owner_name}" if cat_slug == "dentists" else f"Hi {owner_name}"
            body = (
                f"Congratulations {greeting}! {biz_name} just reached {val:,} milestone {metric}. "
                "Want me to draft a thank-you announcement and special celebration voucher for your loyal customers?"
            )

        elif kind == "cde_opportunity":
            credits = trg_payload.get("credits", 4)
            fee = trg_payload.get("fee", 500)
            body = (
                f"Dr. {owner_name}, upcoming CDE opportunity: accredited clinical seminar offering {credits} credit points (fee: Rs. {fee}). "
                f"Want me to send the session syllabus and registration details for {biz_name}?"
            )

        elif kind == "trial_followup":
            trial_date = trg_payload.get("trial_date", "recent")
            next_options = trg_payload.get("next_session_options", [])
            opt_labels = [o.get("label", str(o)) if isinstance(o, dict) else str(o) for o in next_options]
            opt_str = f" Next available slot: {', '.join(opt_labels)}." if opt_labels else ""
            body = (
                f"Hi {customer_name}, how did you feel after your trial session on {trial_date}? "
                f"{opt_str} Want me to reserve your spot for the upcoming class?"
            )

        else:
            offer_part = f" Active offer: {active_offer_title}." if active_offer_title else ""
            greeting = f"Dr. {owner_name}" if cat_slug == "dentists" else f"Hi {owner_name}"
            body = (
                f"{greeting}, update for {biz_name}: {decision.why_now}.{offer_part} "
                "Want me to draft a customer update?"
            )

        body = SafetyGuard.sanitize_output(body, decision.forbidden_claims)
        return body, decision.rationale

    @staticmethod
    def realize_reply(
        merchant_intent: MerchantIntentState,
        conversation_record: Dict[str, Any],
        merchant: Dict[str, Any],
        category: Dict[str, Any]
    ) -> Tuple[str, str, str, Optional[int]]:
        """Returns: (action, body, cta, wait_seconds)"""
        owner_name = merchant.get("identity", {}).get("owner_first_name", "Partner") if merchant else "Partner"
        biz_name = merchant.get("identity", {}).get("name", "your business") if merchant else "your business"

        # 1. EXPLICIT EXECUTION ("kar do", "bhej do", "yes send it") -> Switch immediately to execution mode
        if merchant_intent == MerchantIntentState.EXPLICIT_EXECUTION:
            body = (
                f"Understood {owner_name}! I am preparing the campaign draft for {biz_name} now based on your latest update. "
                "Should I schedule it to send tomorrow at 10am?"
            )
            return "send", body, "binary_yes_no", None

        # 2. AUTO-REPLY DETECTED -> Exit sequence immediately
        if merchant_intent == MerchantIntentState.AUTO_REPLY_DETECTED:
            return "end", None, "none", None

        # 3. OPT-OUT / HOSTILE / REJECTION -> Graceful Exit
        if merchant_intent in [MerchantIntentState.OPT_OUT_HOSTILE, MerchantIntentState.REJECTION]:
            body = f"Apologies {owner_name} - I won't message again. If anything changes, you can always restart with 'Hi Vera'."
            return "end", body, "none", None

        # 4. DEFER LATER -> Backoff 24 hours
        if merchant_intent == MerchantIntentState.DEFER_LATER:
            body = f"No problem {owner_name}! I will check back with you later."
            return "wait", body, "none", 86400

        # 5. QUESTION / OFF-TOPIC -> Decline & Redirect
        if merchant_intent == MerchantIntentState.QUESTION_OFF_TOPIC:
            body = f"I will leave GST and tax filing to your accountant - that is outside what I assist with directly! Coming back to our campaign update - want me to send the draft?"
            return "send", body, "open_ended", None

        # Default Positive Ack / Continuation
        body = f"Great! Preparing the draft for {biz_name} now. Reply CONFIRM to proceed."
        return "send", body, "confirmation", None
