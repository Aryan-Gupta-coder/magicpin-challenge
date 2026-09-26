"""
tests/test_mutations.py — Mutation unit tests verifying adaptive context shifts, claim graph verification, & safety bounds.
"""

from __future__ import annotations
import sys
import os
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.models import MerchantIntentState, DecisionObject
from bot.claim_ledger import build_claim_ledger_from_contexts, ClaimLedger
from bot.safety_guard import SafetyGuard
from bot.intent_engine import IntentEngine
from bot.decision_engine import DecisionEngine


class TestMutations(unittest.TestCase):

    def test_url_safety_stripping(self):
        """Verify HTTP URLs are stripped and reframed to prevent Meta penalties (-3 pts)."""
        body_with_url = "Read more at https://magicpin.com/blog or visit www.example.com for details."
        cleaned, had_url = SafetyGuard.strip_urls(body_with_url)
        self.assertTrue(had_url)
        self.assertNotIn("https://", cleaned)
        self.assertNotIn("www.", cleaned)

    def test_emoji_stripping(self):
        """Verify non-ASCII emojis are stripped cleanly to ensure ASCII safety across OS terminals."""
        body_with_emoji = "Hi Dr. Meera 🦷 Dr. Meera's clinic here 💍 welcome! 😊"
        cleaned = SafetyGuard.strip_emojis(body_with_emoji)
        self.assertNotIn("🦷", cleaned)
        self.assertNotIn("💍", cleaned)
        self.assertNotIn("😊", cleaned)

    def test_hinglish_intent_classification(self):
        """Verify 'kar do' and 'bhej do' are correctly classified as EXPLICIT_EXECUTION."""
        int1, _, _ = IntentEngine.classify_intent("kar do")
        self.assertEqual(int1, MerchantIntentState.EXPLICIT_EXECUTION)

        int2, _, _ = IntentEngine.classify_intent("bhej do draft")
        self.assertEqual(int2, MerchantIntentState.EXPLICIT_EXECUTION)

        int3, _, _ = IntentEngine.classify_intent("yes send it")
        self.assertEqual(int3, MerchantIntentState.EXPLICIT_EXECUTION)

    def test_auto_reply_detection(self):
        """Verify WhatsApp Business canned auto-replies are classified as AUTO_REPLY_DETECTED."""
        auto_msg = "Thank you for contacting us! Our team will respond shortly."
        intent, _, _ = IntentEngine.classify_intent(auto_msg)
        self.assertEqual(intent, MerchantIntentState.AUTO_REPLY_DETECTED)

    def test_claim_ledger_grounding(self):
        """Verify numeric transformations (e.g. 2410 -> 2,410, 0.021 -> 2.1%) are grounded."""
        category = {
            "digest": [{"id": "d1", "source": "JIDA Oct 2026, p.14", "trial_n": 2100}],
            "peer_stats": {"avg_ctr": 0.030}
        }
        merchant = {
            "performance": {"views": 2410, "ctr": 0.021},
            "offers": [{"title": "Dental Cleaning @ ₹299", "status": "active"}]
        }

        ledger = build_claim_ledger_from_contexts(category, merchant, None, None)
        
        # Grounded body
        good_body = "Your CTR is 2.1% (views: 2,410). 2,100-patient trial from JIDA Oct 2026, p.14. Price is ₹299."
        is_grounded, ungrounded = ledger.verify_message_grounding(good_body)
        self.assertTrue(is_grounded, f"Should be grounded, but found ungrounded: {ungrounded}")

        # Ungrounded / Fabricated body
        bad_body = "Your CTR is 45% (views: 99999). 5,000-patient trial from PubMed 2025. Price is ₹999."
        is_grounded_bad, ungrounded_bad = ledger.verify_message_grounding(bad_body)
        self.assertFalse(is_grounded_bad, "Fabricated numbers should NOT be grounded!")


if __name__ == "__main__":
    unittest.main()
