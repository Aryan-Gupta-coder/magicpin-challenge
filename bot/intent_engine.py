"""
bot/intent_engine.py — Multi-tier intent classifier & similarity-based auto-reply detector.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple, Optional
from bot.models import MerchantIntentState


# =============================================================================
# CANNED PATTERNS & REGEXES
# =============================================================================

CANNED_AUTO_REPLY_REGEXES = [
    r'thank\s+you\s+for\s+contacting',
    r'our\s+team\s+will\s+respond',
    r'automated\s+assistant',
    r'aapki\s+jaankari\s+ke\s+liye\s+shukriya',
    r'main\s+ek\s+automated\s+assistant\s+hoon',
    r'humari\s+team\s+tak\s+pahuncha',
    r'we\s+have\s+received\s+your\s+message',
    r'thanks\s+for\s+reaching\s+out',
]

EXPLICIT_EXECUTION_PATTERNS = [
    r'\bkar\s*do\b',
    r'\bbhej\s*do\b',
    r'\byes\s+send\b',
    r'\blets\s+do\s+it\b',
    r'\blet\'s\s+do\s+it\b',
    r'\bdo\s+it\b',
    r'\bgo\s+ahead\b',
    r'\bproceed\b',
    r'\bconfirm\b',
    r'\bsend\s+the\s+abstract\b',
    r'\bdraft\s+the\s+patient\b',
    r'\bplease\s+send\b',
    r'\bha\s+bhej\s*do\b',
    r'\bha\s+kar\s*do\b',
]

OPT_OUT_HOSTILE_PATTERNS = [
    r'\bstop\s+messaging\b',
    r'\bstop\s+sending\b',
    r'\bdon\'t\s+message\b',
    r'\bdont\s+message\b',
    r'\buseless\s+spam\b',
    r'\bblock\b',
    r'\bstop\b',
    r'\bnot\s+interested\b',
    r'\bnahin\s+chahiye\b',
]

DEFER_LATER_PATTERNS = [
    r'\bmaybe\s+later\b',
    r'\bnext\s+week\b',
    r'\bbusy\s+today\b',
    r'\bphir\s+kabhi\b',
    r'\bbaad\s+me\b',
    r'\bbaad\s+mein\b',
]

QUESTION_OFF_TOPIC_PATTERNS = [
    r'\bgst\b',
    r'\btax\b',
    r'\bwhere\s+are\s+you\b',
    r'\bwho\s+are\s+you\b',
    r'\bhelp\s+me\s+with\b',
    r'\bcan\s+you\s+also\b',
]


def jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate token-based Jaccard similarity."""
    tokens1 = set(re.findall(r'\w+', text1.lower()))
    tokens2 = set(re.findall(r'\w+', text2.lower()))
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union)


def levenshtein_ratio(text1: str, text2: str) -> float:
    """Normalized Levenshtein similarity (0.0-1.0)."""
    if text1 == text2:
        return 1.0
    len1, len2 = len(text1), len(text2)
    if len1 == 0 or len2 == 0:
        return 0.0
    # DP matrix rows
    prev_row = list(range(len2 + 1))
    for i, c1 in enumerate(text1, 1):
        cur_row = [i] + [0] * len2
        for j, c2 in enumerate(text2, 1):
            cost = 0 if c1 == c2 else 1
            cur_row[j] = min(prev_row[j] + 1, cur_row[j - 1] + 1, prev_row[j - 1] + cost)
        prev_row = cur_row
    distance = prev_row[-1]
    ratio = 1.0 - distance / max(len1, len2)
    return ratio


class IntentEngine:
    """Classifies inbound turn messages into MerchantIntentState."""

    @staticmethod
    def classify_intent(message: str, past_turns: List[Dict[str, Any]] = None) -> Tuple[MerchantIntentState, float, str]:
        if not message:
            return MerchantIntentState.UNKNOWN, 0.0, "Empty message"

        msg_clean = message.strip().lower()

        # ---------------------------------------------------------------------
        # Tier 1: Check Opt-Out & Hostile
        # ---------------------------------------------------------------------
        for pat in OPT_OUT_HOSTILE_PATTERNS:
            if re.search(pat, msg_clean):
                return MerchantIntentState.OPT_OUT_HOSTILE, 0.95, f"Matched hostile pattern: {pat}"

        # ---------------------------------------------------------------------
        # Tier 2: Check Explicit Execution Intent
        # ---------------------------------------------------------------------
        for pat in EXPLICIT_EXECUTION_PATTERNS:
            if re.search(pat, msg_clean):
                return MerchantIntentState.EXPLICIT_EXECUTION, 0.95, f"Matched execution pattern: {pat}"
        if msg_clean in ["yes", "ok", "okay", "ha", "haan", "sure", "yep"]:
            return MerchantIntentState.EXPLICIT_EXECUTION, 0.90, "Single-word commitment"

        # ---------------------------------------------------------------------
        # Tier 3: Check Canned Auto-Reply Signatures
        # ---------------------------------------------------------------------
        for pat in CANNED_AUTO_REPLY_REGEXES:
            if re.search(pat, msg_clean):
                return MerchantIntentState.AUTO_REPLY_DETECTED, 0.95, f"Matched auto-reply canned pattern: {pat}"

        # ---------------------------------------------------------------------
        # Tier 3b: Similarity-based Auto-Reply Detection (using Jaccard + Levenshtein)
        # ---------------------------------------------------------------------
        if past_turns:
            merchant_msgs = [t["msg"] for t in past_turns if t.get("from") == "merchant"]
            if merchant_msgs:
                for prev_msg in merchant_msgs[-3:]:
                    jacc = jaccard_similarity(msg_clean, prev_msg)
                    lev = levenshtein_ratio(msg_clean, prev_msg)
                    s = 0.5 * jacc + 0.5 * lev
                    if s >= 0.85:
                        return MerchantIntentState.AUTO_REPLY_DETECTED, s, f"Combined similarity ({s:.2f}) with past merchant turn"

        # ---------------------------------------------------------------------
        # Tier 4: Check Defer / Later
        # ---------------------------------------------------------------------
        for pat in DEFER_LATER_PATTERNS:
            if re.search(pat, msg_clean):
                return MerchantIntentState.DEFER_LATER, 0.85, f"Matched defer pattern: {pat}"

        # ---------------------------------------------------------------------
        # Tier 5: Check Off-Topic Question
        # ---------------------------------------------------------------------
        for pat in QUESTION_OFF_TOPIC_PATTERNS:
            if re.search(pat, msg_clean):
                return MerchantIntentState.QUESTION_OFF_TOPIC, 0.85, f"Matched question pattern: {pat}"

        # ---------------------------------------------------------------------
        # Tier 6: Positive Acknowledgment Fallback
        # ---------------------------------------------------------------------
        positive_words = ["sounds good", "thanks", "thank you", "good", "nice", "accha", "sahi hai", "great"]
        if any(w in msg_clean for w in positive_words):
            return MerchantIntentState.POSITIVE_ACK, 0.75, "Matched positive acknowledgment phrasing"

        return MerchantIntentState.UNKNOWN, 0.5, "Default fallback classification"
