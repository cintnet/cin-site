#!/usr/bin/env python3
"""Regression tests for OPCP, AULA, and AI-delegated privacy researcher credits (gemini-adopt)."""

from pathlib import Path
import re
import statistics
import unittest

SITE_ROOT = Path(__file__).resolve().parents[1]
OTHERS_FILE = SITE_ROOT / "content" / "about" / "others.html"
RESEARCHERS_FILE = SITE_ROOT / "content" / "get-involved" / "researchers.html"


class TestAdoptOpcpAulaDelegatedPrivacyCredits(unittest.TestCase):
    def test_others_html_contains_grounded_credits(self) -> None:
        content = OTHERS_FILE.read_text(encoding="utf-8")
        for token in (
            "Deepak Waghmare",
            "Shaad Sufi",
            "2611.26966",
            "Natasha E. Blycha",
            "2611.25985",
            "Bingcan Guo",
            "2509.21712",
            'href="#fn151"',
            'id="fn151"',
            'href="#fn152"',
            'id="fn152"',
            'href="#fn153"',
            'id="fn153"',
        ):
            self.assertIn(token, content)

    def test_researchers_html_contains_grounded_credits(self) -> None:
        content = RESEARCHERS_FILE.read_text(encoding="utf-8")
        for token in (
            "Waghmare",
            "2611.26966",
            "Blycha et al.",
            "2611.25985",
            "Guo, Xu, Zhang",
            "2509.21712",
            'href="#fn80"',
            'id="fn80"',
            'href="#fn81"',
            'id="fn81"',
            'href="#fn82"',
            'id="fn82"',
        ):
            self.assertIn(token, content)

    def test_non_endorsement_and_no_forbidden_claims(self) -> None:
        others_text = OTHERS_FILE.read_text(encoding="utf-8").lower()
        res_text = RESEARCHERS_FILE.read_text(encoding="utf-8").lower()
        self.assertIn("never claim that citing published research implies commercial endorsement", others_text)
        self.assertIn("never imply endorsement", res_text)
        for text in (others_text, res_text):
            for forbidden in ("guaranteed return", "passive income", "mmct token", "token sale", "base thesis"):
                self.assertNotIn(forbidden, text)

    def test_sentence_rhythm(self) -> None:
        for path in (OTHERS_FILE, RESEARCHERS_FILE):
            text = path.read_text(encoding="utf-8")
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    text = parts[2]
            text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
            text = re.sub(r"<(svg|script|style|aside)[^>]*>.*?</\1>", " ", text, flags=re.DOTALL)
            text = re.sub(r'<section class="footnotes"[^>]*>.*?</section>', " ", text, flags=re.DOTALL)
            text = re.sub(r"</(h[1-6]|p|li|div|figcaption|tr|td|th)>", ". ", text)
            text = re.sub(r"<[^>]+>", " ", text)
            sentences = [s.strip() for s in re.split(r'[\.\?\!]["\u2019\u201d\')\]]*(?:\s+|$)', text) if s.strip()]
            lengths = [len(s.split()) for s in sentences if len(s.split()) > 2]
            self.assertLessEqual(statistics.median(lengths), 22.0)
            self.assertEqual([s for s in sentences if len(s.split()) > 35], [])


if __name__ == "__main__":
    unittest.main()
