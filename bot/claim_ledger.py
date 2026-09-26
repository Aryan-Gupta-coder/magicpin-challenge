"""
bot/claim_ledger.py — Claim Graph Engine and Grounding Verification.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Set, Tuple, Optional
from bot.models import ClaimNode
from bot.safety_guard import SafetyGuard


class ClaimLedger:
    def __init__(self):
        self.nodes: Dict[str, ClaimNode] = {}
        self.permitted_tokens: Set[str] = set()

    def add_claim(self, claim_id: str, source_context: str, version: int, claim_type: str, raw_value: Any):
        if raw_value is None:
            return

        transformations = set()
        raw_str = SafetyGuard.to_ascii_safe(str(raw_value)).strip()
        if not raw_str:
            return

        transformations.add(raw_str)

        # Build permitted transformations based on claim_type
        if claim_type == "count" and isinstance(raw_value, (int, float)):
            val = int(raw_value)
            transformations.add(f"{val:,}")
            if val >= 1000:
                k_val = round(val / 1000.0, 2)
                k_str = f"{k_val:g}k"
                transformations.add(k_str)
                transformations.add(f"~{k_str}")
                transformations.add(f"~{val}")

        elif claim_type == "percentage" and isinstance(raw_value, (int, float)):
            val = float(raw_value)
            pct_val = val * 100.0 if val <= 1.0 else val
            pct_str = f"{pct_val:g}%"
            transformations.add(pct_str)
            transformations.add(f"{round(pct_val)}%")
            transformations.add(f"{pct_val:g} percent")

        elif claim_type == "currency" and isinstance(raw_value, (int, float, str)):
            clean_val = str(raw_value).replace("₹", "").replace("Rs.", "").replace("Rs", "").replace(",", "").strip()
            if clean_val.isdigit():
                v = int(clean_val)
                transformations.add(f"Rs {v:,}")
                transformations.add(f"Rs {v}")
                transformations.add(f"Rs. {v}")
                transformations.add(f"₹{v}")
                transformations.add(f"₹{v:,}")

        elif claim_type == "date":
            # e.g., "2026-11-05" -> "5 Nov", "Nov 5", "Wednesday 5 Nov"
            transformations.add(raw_str)
            date_match = re.search(r'\d{4}-(\d{2})-(\d{2})', raw_str)
            if date_match:
                m, d = int(date_match.group(1)), int(date_match.group(2))
                months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                if 1 <= m <= 12:
                    month_str = months[m - 1]
                    transformations.add(f"{d} {month_str}")
                    transformations.add(f"{month_str} {d}")

        elif claim_type == "citation":
            transformations.add(raw_str)
            clean_cit = re.sub(r'[^\w\s]', '', raw_str)
            transformations.add(clean_cit)

        node = ClaimNode(
            claim_id=claim_id,
            source_context=source_context,
            context_version=version,
            claim_type=claim_type,
            raw_value=raw_value,
            permitted_transformations=transformations
        )
        self.nodes[claim_id] = node
        for t in transformations:
            self.permitted_tokens.add(t.lower())

    def verify_message_grounding(self, body: str) -> Tuple[bool, List[str]]:
        """
        Extract numeric claims and currency figures from body and check against permitted_tokens.
        Returns (is_grounded, ungrounded_claims)
        """
        if not body:
            return True, []

        ungrounded = []

        # 1. Extract monetary claims (e.g. Rs 299, Rs. 499, ₹299)
        currencies = re.findall(r'(?:₹|Rs\.?\s*)(\d+(?:,\d+)*(?:\.\d+)?)', body, re.IGNORECASE)
        for cur in currencies:
            raw_cur = cur.replace(",", "")
            formatted_rs = f"rs {raw_cur}"
            formatted_rupee = f"₹{raw_cur}"
            if not any(token in self.permitted_tokens for token in [formatted_rs, formatted_rupee, raw_cur]):
                # Exclude standard common low numbers if they match hours/days/slots
                if raw_cur not in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12", "24", "48"]:
                    ungrounded.append(f"Currency Rs {cur}")

        # 2. Extract percentages (e.g. 38%, 2.1%)
        percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', body)
        for pct in percentages:
            pct_str = f"{pct}%"
            if pct_str.lower() not in self.permitted_tokens and f"{float(pct):g}%".lower() not in self.permitted_tokens:
                ungrounded.append(f"Percentage {pct}%")

        # 3. Extract key source citations mentioned (JIDA, DCI, IDA, Practo, PubMed)
        citations = re.findall(r'\b(JIDA|DCI|IDA|Practo|PubMed)\b.*?(?=\.|\n|$|,)', body)
        for cit in citations:
            if not any(cit.lower() in token for token in self.permitted_tokens):
                ungrounded.append(f"Citation {cit}")

        return len(ungrounded) == 0, ungrounded


def build_claim_ledger_from_contexts(
    category: Optional[Dict[str, Any]],
    merchant: Optional[Dict[str, Any]],
    trigger: Optional[Dict[str, Any]],
    customer: Optional[Dict[str, Any]],
    cat_ver: int = 1, mer_ver: int = 1, trg_ver: int = 1, cust_ver: int = 1
) -> ClaimLedger:
    ledger = ClaimLedger()

    # Category Context Claims
    if category:
        for i, item in enumerate(category.get("digest", [])):
            cid = item.get("id", f"digest_{i}")
            if "source" in item:
                ledger.add_claim(f"{cid}_source", f"category.digest[{i}].source", cat_ver, "citation", item["source"])
            if "trial_n" in item:
                ledger.add_claim(f"{cid}_trial_n", f"category.digest[{i}].trial_n", cat_ver, "count", item["trial_n"])

        for i, offer in enumerate(category.get("offer_catalog", [])):
            if "value" in offer:
                ledger.add_claim(f"cat_offer_{i}_val", f"category.offer_catalog[{i}].value", cat_ver, "currency", offer["value"])

        stats = category.get("peer_stats", {})
        if "avg_ctr" in stats:
            ledger.add_claim("peer_avg_ctr", "category.peer_stats.avg_ctr", cat_ver, "percentage", stats["avg_ctr"])
        if "avg_rating" in stats:
            ledger.add_claim("peer_avg_rating", "category.peer_stats.avg_rating", cat_ver, "count", stats["avg_rating"])

    # Merchant Context Claims
    if merchant:
        perf = merchant.get("performance", {})
        for metric in ["views", "calls", "directions", "leads"]:
            if metric in perf:
                ledger.add_claim(f"merchant_{metric}", f"merchant.performance.{metric}", mer_ver, "count", perf[metric])
        if "ctr" in perf:
            ledger.add_claim("merchant_ctr", "merchant.performance.ctr", mer_ver, "percentage", perf["ctr"])

        for i, offer in enumerate(merchant.get("offers", [])):
            if offer.get("status") == "active":
                title = offer.get("title", "")
                price_match = re.search(r'(?:₹|Rs\.?\s*)(\d+(?:,\d+)?)', title, re.IGNORECASE)
                if price_match:
                    ledger.add_claim(f"merchant_offer_{i}_price", f"merchant.offers[{i}].title", mer_ver, "currency", price_match.group(1))

        agg = merchant.get("customer_aggregate", {})
        for k, v in agg.items():
            if isinstance(v, (int, float)):
                claim_type = "percentage" if "pct" in k or "retention" in k else "count"
                ledger.add_claim(f"cust_agg_{k}", f"merchant.customer_aggregate.{k}", mer_ver, claim_type, v)

    # Trigger Payload Claims
    if trigger:
        payload = trigger.get("payload", {})
        for k, v in payload.items():
            if isinstance(v, (int, float)):
                claim_type = "percentage" if "pct" in k or "delta" in k else "count"
                ledger.add_claim(f"trigger_payload_{k}", f"trigger.payload.{k}", trg_ver, claim_type, v)
            elif isinstance(v, str) and ("₹" in v or "Rs" in v or "price" in k or "cost" in k):
                ledger.add_claim(f"trigger_payload_{k}", f"trigger.payload.{k}", trg_ver, "currency", v)

    # Customer Context Claims
    if customer:
        rel = customer.get("relationship", {})
        if "visits_total" in rel:
            ledger.add_claim("cust_visits", "customer.relationship.visits_total", cust_ver, "count", rel["visits_total"])
        if "lifetime_value" in rel:
            ledger.add_claim("cust_ltv", "customer.relationship.lifetime_value", cust_ver, "currency", rel["lifetime_value"])

    return ledger
