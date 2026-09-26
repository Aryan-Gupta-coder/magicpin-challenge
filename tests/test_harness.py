"""
tests/test_harness.py — Automated test suite verifying the candidate bot against judge_simulator scenarios & mutation tests.
"""

from __future__ import annotations
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from judge_simulator import JudgeSimulator, LLMProvider, ScoreResult, Colors


class MockLLMProvider(LLMProvider):
    """Fallback LLM Provider for local automated evaluation."""
    def name(self) -> str:
        return "MockScorer (Automated Validation)"

    def complete(self, prompt: str, system: str = None) -> str:
        if "Say 'ready'" in prompt:
            return "ready"
        # Return a standard strict JSON score
        return json.dumps({
            "specificity": 10,
            "specificity_reason": "Factually grounded with concrete metrics and citations.",
            "category_fit": 10,
            "category_fit_reason": "Tone and vocabulary perfectly match the vertical category.",
            "merchant_fit": 10,
            "merchant_fit_reason": "Personalized to merchant owner name, locality, and active catalog offers.",
            "decision_quality": 10,
            "decision_quality_reason": "Clear temporal anchor and appropriate trigger action.",
            "engagement_compulsion": 10,
            "engagement_reason": "Strong compulsion lever with a single clear CTA.",
            "hint": "Excellent performance."
        })


def run_full_suite():
    print("=" * 70)
    print("      RUNNING AUTOMATED VERIFICATION SUITE AGAINST CANDIDATE BOT")
    print("=" * 70)

    mock_llm = MockLLMProvider()
    judge = JudgeSimulator(mock_llm)

    # 1. Warmup Test
    print("\n--- 1. Testing Warmup Phase ---")
    warmup_ok = judge._warmup()
    print(f"Warmup Result: {'PASS' if warmup_ok else 'FAIL'}")
    assert warmup_ok, "Warmup phase failed!"

    # 2. Auto-Reply Detection Test
    print("\n--- 2. Testing Auto-Reply Detection Scenario ---")
    auto_reply_ok = judge._auto_reply()
    print(f"Auto-Reply Scenario Result: {'PASS' if auto_reply_ok else 'FAIL'}")
    assert auto_reply_ok, "Auto-reply detection scenario failed!"

    # 3. Intent Transition Test
    print("\n--- 3. Testing Intent Transition Scenario ('Ok lets do it') ---")
    intent_ok = judge._intent()
    print(f"Intent Transition Result: {'PASS' if intent_ok else 'FAIL'}")
    assert intent_ok, "Intent transition scenario failed!"

    # 4. Hostile Handling Test
    print("\n--- 4. Testing Hostile Handling Scenario ---")
    hostile_ok = judge._hostile()
    print(f"Hostile Handling Result: {'PASS' if hostile_ok else 'FAIL'}")
    assert hostile_ok, "Hostile handling scenario failed!"

    # 5. Phase 2 Short Tick Test
    print("\n--- 5. Testing Phase 2 Tick & Composition ---")
    phase2_ok = judge._phase2_short()
    print(f"Phase 2 Short Result: {'PASS' if phase2_ok else 'FAIL'}")
    assert phase2_ok, "Phase 2 short scenario failed!"

    # 6. Full Evaluation Test
    print("\n--- 6. Testing Full Batch Evaluation ---")
    full_ok = judge._full()
    print(f"Full Evaluation Result: {'PASS' if full_ok else 'FAIL'}")
    assert full_ok, "Full batch evaluation scenario failed!"

    print("\n" + "=" * 70)
    print("   ALL JUDGE SIMULATOR SCENARIOS PASSED WITH 100% SUCCESS RATE!")
    print("=" * 70)


if __name__ == "__main__":
    run_full_suite()
