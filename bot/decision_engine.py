"""
bot/decision_engine.py — Deterministic Decision Engine & Trigger Utility Scoring.
"""

from __future__ import annotations
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bot.models import DecisionObject, ConversationState
from bot.claim_ledger import build_claim_ledger_from_contexts
from bot.store import store


class DecisionEngine:
    """Evaluates candidate triggers and context snapshots to build an audited DecisionObject."""

    @staticmethod
    def evaluate_trigger(
        trigger: Dict[str, Any],
        merchant: Dict[str, Any],
        category: Dict[str, Any],
        customer: Optional[Dict[str, Any]] = None,
        cat_ver: int = 1, mer_ver: int = 1, trg_ver: int = 1, cust_ver: int = 1,
        now_str: Optional[str] = None
    ) -> Optional[DecisionObject]:

        trg_id = trigger.get("id", "")
        kind = trigger.get("kind", "")
        scope = trigger.get("scope", "merchant")
        merchant_id = merchant.get("merchant_id", "")
        customer_id = customer.get("customer_id") if customer else None
        suppression_key = trigger.get("suppression_key", f"{kind}:{merchant_id}")

        # Suppression penalty (P_suppress = 1.00 when active)
        p_suppress = 1.0 if store.is_suppressed(suppression_key) else 0.0

        # Parse request simulated timestamp
        now_dt = None
        if now_str:
            try:
                now_dt = datetime.fromisoformat(now_str.replace("Z", "+00:00"))
            except Exception:
                pass

        expires_at_str = trigger.get("expires_at")
        exp_dt = None
        if expires_at_str:
            try:
                exp_dt = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                comp_dt = now_dt if now_dt else datetime.now(exp_dt.tzinfo)
                if comp_dt >= exp_dt:
                    return None
            except Exception:
                pass

        # ---------------------------------------------------------------------
        # 2. Multi-Factor Utility Scoring
        # ---------------------------------------------------------------------
        urgency = trigger.get("urgency", 1)
        
        # Calculate Freshness according to specification: 1.0 - (now - delivered_at) / (expires_at - delivered_at)
        freshness_score = 1.0
        if exp_dt and now_dt:
            delivered_at_str = trigger.get("delivered_at") or trigger.get("created_at")
            if delivered_at_str:
                try:
                    delivered_dt = datetime.fromisoformat(delivered_at_str.replace("Z", "+00:00"))
                    total_window = (exp_dt - delivered_dt).total_seconds()
                    elapsed = (now_dt - delivered_dt).total_seconds()
                    if total_window > 0:
                        freshness_score = max(0.0, min(1.0, 1.0 - (elapsed / total_window)))
                except Exception:
                    pass

        relevance_score = 0.8
        evidence_score = 0.9 if trigger.get("source") == "external" else 0.7
        commercial_score = 0.8

        # Reward explicit signals match
        signals = merchant.get("signals", [])
        if "high_risk_adult_cohort" in signals and kind in ["research_digest", "recall_due"]:
            relevance_score = 1.0
        if "ctr_below_peer_median" in signals and kind in ["research_digest", "perf_dip"]:
            commercial_score = 1.0

        raw_utility_score = (
            0.20 * freshness_score +
            0.30 * relevance_score +
            0.25 * evidence_score +
            0.25 * commercial_score
        )

        # Apply state penalty (P_state = 0.50) only for awaiting response state
        p_state = 0.0
        conv_id = f"conv_{merchant_id}_{trg_id}"
        record = store.get_conversation_record(conv_id)
        if record and record.get("conv_state") == ConversationState.AWAITING_RESPONSE:
            p_state = 0.50

        # Apply suppression penalty (P_suppress = 1.00) when active (p_suppress already computed above)
        utility_score = max(0.0, raw_utility_score - p_state - p_suppress)

        # Enforce Minimum Utility Threshold (0.65 as specified in DECISION_ENGINE_SPEC.md)
        if utility_score < 0.65:
            return None

        # ---------------------------------------------------------------------
        # 3. Strategy & Signal Assembly
        # ---------------------------------------------------------------------
        primary_signal = signals[0] if signals else "standard_engagement"
        supporting_signals = signals[1:] if len(signals) > 1 else []
        why_now = f"Trigger '{kind}' activated for {merchant.get('identity', {}).get('name')}"

        send_as = "merchant_on_behalf" if scope == "customer" else "vera"

        # Determine CTA Format based on trigger kind & scope
        if scope == "customer":
            cta_type = "slot_selection" if kind == "recall_due" else "binary_yes_no"
        elif kind in ["research_digest", "curious_ask_due"]:
            cta_type = "open_ended"
        elif kind in ["active_planning_intent", "ipl_match_today", "supply_alert"]:
            cta_type = "binary_yes_no"
        else:
            cta_type = "binary_yes_no"

        # Strategy Dispatch
        cat_slug = category.get("slug", "default") if category else "default"
        recommended_strategy = f"{cat_slug}_{kind}_strategy"
        audience_segment = customer.get("identity", {}).get("name", "Merchant Owner") if customer else "Merchant Owner"

        # Template Params
        owner_name = merchant.get("identity", {}).get("owner_first_name", "Partner")
        biz_name = merchant.get("identity", {}).get("name", "your business")
        template_name = f"vera_{kind}_v1"
        template_params = [owner_name, biz_name, why_now]

        # Assemble Fact Ledger & Taboos
        ledger = build_claim_ledger_from_contexts(category, merchant, trigger, customer, cat_ver, mer_ver, trg_ver, cust_ver)
        approved_facts = [
            {"id": node.claim_id, "type": node.claim_type, "raw": node.raw_value, "tokens": list(node.permitted_transformations)}
            for node in ledger.nodes.values()
        ]

        forbidden_claims = category.get("voice", {}).get("vocab_taboo", []) if category else []

        decision = DecisionObject(
            action="send",
            why_now=why_now,
            trigger_id=trg_id,
            trigger_kind=kind,
            merchant_id=merchant_id,
            customer_id=customer_id,
            send_as=send_as,
            context_versions={"category": cat_ver, "merchant": mer_ver, "trigger": trg_ver, "customer": cust_ver},
            primary_signal=primary_signal,
            supporting_signals=supporting_signals,
            recommended_strategy=recommended_strategy,
            audience_segment=audience_segment,
            utility_score=utility_score,
            priority=urgency,
            cta_type=cta_type,
            template_name=template_name,
            template_params=template_params,
            suppression_key=suppression_key,
            approved_facts=approved_facts,
            forbidden_claims=forbidden_claims,
            confidence=0.92,
            rationale=f"Composed proactive action for trigger '{kind}' (utility={utility_score:.2f}) targeting {audience_segment}"
        )

        return decision
