"""
bot/safety_guard.py — Safety guard: ASCII sanitization, URL stripping, taboo word verification, and CTA formatting.
"""

from __future__ import annotations
import re
from typing import List, Tuple, Optional


class SafetyGuard:
    """Validates and cleans realized message outputs before sending to the judge."""

    @staticmethod
    def to_ascii_safe(text: str) -> str:
        """
        Guarantees 100% ASCII compliance across all OS terminal encodings (CP1252, UTF-8, etc.).
        Maps known symbols (Rupee, smart quotes, dashes) to ASCII equivalents and drops emojis.
        """
        if not text:
            return ""

        replacements = {
            "₹": "Rs ",
            "—": "-",
            "–": "-",
            "“": '"',
            "”": '"',
            "‘": "'",
            "’": "'",
            "\xa0": " ",
            "\u200b": "",
        }
        for k, v in replacements.items():
            text = text.replace(k, v)

        # Encode to ASCII, dropping any remaining non-ASCII Unicode characters (emojis, etc.)
        ascii_text = text.encode("ascii", "ignore").decode("ascii")
        # Clean up multi-space artifacts
        return re.sub(r'[ \t]{2,}', ' ', ascii_text).strip()

    @staticmethod
    def strip_emojis(body: str) -> str:
        """Safely remove non-ASCII emoji/symbol characters from message text without corrupting normal ASCII content."""
        if not body:
            return ""
        return SafetyGuard.to_ascii_safe(body)

    @staticmethod
    def strip_urls(body: str) -> Tuple[str, bool]:
        """Detect and cleanly strip HTTP/HTTPS URLs to prevent Meta WhatsApp violations (-3 penalty)."""
        if not body:
            return body, False

        url_pattern = r'https?://\S+|www\.\S+'
        has_url = bool(re.search(url_pattern, body))

        if not has_url:
            return body, False

        # Cleanly replace URL occurrences with non-URL explanatory text
        cleaned = re.sub(url_pattern, '(details on your dashboard)', body)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned, True

    @staticmethod
    def check_taboo_words(body: str, taboo_list: List[str]) -> Tuple[bool, List[str]]:
        """Check if message contains prohibited taboo words from CategoryContext.voice.vocab_taboo."""
        if not body or not taboo_list:
            return True, []

        found = []
        body_lower = body.lower()
        for taboo in taboo_list:
            clean_taboo = taboo.split('(')[0].strip().lower()
            if clean_taboo and clean_taboo in body_lower:
                found.append(taboo)

        return len(found) == 0, found

    @staticmethod
    def sanitize_output(body: str, taboo_list: List[str] = None) -> str:
        """Run full safety pass: strip URLs, convert to ASCII-safe text, remove taboos, and clean spacing."""
        if not body:
            return ""

        # 1. Strip URLs
        cleaned, _ = SafetyGuard.strip_urls(body)

        # 2. Convert to 100% ASCII-safe text (strips non-CP1252 emojis, converts Rupee sign to Rs)
        cleaned = SafetyGuard.to_ascii_safe(cleaned)

        # 3. Check & remove taboo words if found
        if taboo_list:
            for taboo in taboo_list:
                clean_taboo = taboo.split('(')[0].strip()
                if clean_taboo and clean_taboo.lower() in cleaned.lower():
                    pattern = re.compile(re.escape(clean_taboo), re.IGNORECASE)
                    cleaned = pattern.sub('', cleaned)

        # 4. Clean up formatting
        cleaned = re.sub(r'[\r\n]{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned).strip()

        return cleaned
