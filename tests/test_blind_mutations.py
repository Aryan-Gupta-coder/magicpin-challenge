"""
scratch/test_blind_mutations.py — Validation of unseen context mutations against Vera bot candidate package.
"""

from __future__ import annotations
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.store import store
from bot.decision_engine import DecisionEngine
from bot.claim_ledger import build_claim_ledger_from_contexts
from bot.realizer import MessageRealizer
from bot.safety_guard import SafetyGuard
from bot.models import MerchantIntentState


class TestBlindMutations(unittest.TestCase):

    def setUp(self):
        store.wipe()

    def test_unseen_digest_mutation(self):
        """Verify that injecting a completely new unseen digest item produces a message with the NEW facts."""
        category_payload = {
            "slug": "dentists",
            "digest": [
                {
                    "id": "item_2026_x",
                    "title": "New 2026 Pediatric Sealants Study",
                    "source": "Lancet Dental 2026, p.88",
                    "trial_n": 5400,
                    "finding": "cuts molar decay by 52%"
                }
            ],
            "voice": {"tone": "clinical_peer", "vocab_taboo": ["cheap", "guarantee"]}
        }
        merchant_payload = {
            "merchant_id": "m_dentist_new",
            "category_slug": "dentists",
            "identity": {"name": "Bright Smiles Clinic", "owner_first_name": "Ananya"},
            "offers": [{"title": "Teeth Whitening @ Rs 999", "status": "active"}]
        }
        trigger_payload = {
            "id": "trg_digest_new",
            "kind": "research_digest",
            "scope": "merchant",
            "merchant_id": "m_dentist_new",
            "payload": {"top_item_id": "item_2026_x"},
            "urgency": 4
        }

        store.push_context("category", "dentists", 1, category_payload)
        store.push_context("merchant", "m_dentist_new", 1, merchant_payload)
        store.push_context("trigger", "trg_digest_new", 1, trigger_payload)

        dec = DecisionEngine.evaluate_trigger(trigger_payload, merchant_payload, category_payload)
        self.assertIsNotNone(dec)

        ledger = build_claim_ledger_from_contexts(category_payload, merchant_payload, trigger_payload, None)
        body, rationale = MessageRealizer.realize_proactive(dec, category_payload, merchant_payload, trigger_payload, ledger=ledger)
        cleaned = SafetyGuard.sanitize_output(body)

        # Must contain the new facts!
        self.assertIn("Lancet Dental 2026", cleaned)
        self.assertIn("5,400", cleaned)
        self.assertIn("Dr. Ananya", cleaned)
        # Must NOT contain hardcoded old facts
        self.assertNotIn("JIDA Oct 2026", cleaned)
        self.assertNotIn("2,100", cleaned)

    def test_expired_offer_exclusion(self):
        """Verify that expired offers are NOT included in generated messages."""
        merchant_payload = {
            "merchant_id": "m_salon_expired",
            "category_slug": "salons",
            "identity": {"name": "Glamour Lounge", "owner_first_name": "Riya"},
            "offers": [
                {"title": "Bridal Package @ Rs 5000", "status": "expired"},
                {"title": "Hair Spa @ Rs 499", "status": "active"}
            ]
        }
        category_payload = {"slug": "salons"}
        trigger_payload = {
            "id": "trg_salon_curious",
            "kind": "curious_ask_due",
            "merchant_id": "m_salon_expired",
            "urgency": 3
        }

        dec = DecisionEngine.evaluate_trigger(trigger_payload, merchant_payload, category_payload)
        body, _ = MessageRealizer.realize_proactive(dec, category_payload, merchant_payload, trigger_payload)
        cleaned = SafetyGuard.sanitize_output(body)

        self.assertNotIn("Bridal Package", cleaned)
        self.assertNotIn("Rs 5000", cleaned)

    def test_dynamic_reply_execution(self):
        """Verify that explicit execution replies do not invent false external actions or fixed patient-ed text."""
        conv_rec = {"auto_reply_count": 0, "turns": []}
        merchant = {"identity": {"owner_first_name": "Vikram", "name": "Vikram's Gym"}}
        
        action, body, cta, _ = MessageRealizer.realize_reply(
            MerchantIntentState.EXPLICIT_EXECUTION,
            conv_rec,
            merchant,
            {"slug": "gyms"}
        )
        self.assertEqual(action, "send")
        self.assertIn("Vikram", body)
        self.assertNotIn("90-sec patient-ed", body)
        self.assertNotIn("Sending now", body)


if __name__ == "__main__":
    unittest.main()
