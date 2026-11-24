#!/usr/bin/env python3
"""Unit tests for editorial polish of research and related-work pages (D-1416 / gemini-editor)."""

from pathlib import Path
import re
import statistics
import unittest

SITE_ROOT = Path(__file__).resolve().parents[1]
RESEARCH_FILE = SITE_ROOT / "content" / "research.html"
OTHERS_FILE = SITE_ROOT / "content" / "about" / "others.html"


class TestEditorialResearchAndScrutableStatePolish(unittest.TestCase):
    def test_files_exist(self):
        self.assertTrue(RESEARCH_FILE.exists(), "research.html must exist")
        self.assertTrue(OTHERS_FILE.exists(), "others.html must exist")

    def test_research_html_contains_grounded_provenance(self):
        content = RESEARCH_FILE.read_text(encoding="utf-8")
        self.assertIn("Scrutable State", content)
        self.assertIn("Vendster", content)
        self.assertIn("2602.09678", content)
        self.assertIn("2610.38292", content)
        self.assertIn("2610.39139", content)
        self.assertIn("/blog/why-a-public-decision-cannot-hide-in-a-black-box/", content)
        self.assertIn("/blog/why-your-shopping-assistant-needs-a-bargaining-shield/", content)

    def test_others_html_contains_grounded_provenance(self):
        content = OTHERS_FILE.read_text(encoding="utf-8")
        self.assertIn("Vendster", content)
        self.assertIn("Bergemann", content)
        self.assertIn("Cuéllar", content)
        self.assertIn("fn92", content)
        self.assertIn("fn93", content)
        self.assertIn("fn94", content)
        self.assertIn("2602.09678", content)
        self.assertIn("2610.38292", content)
        self.assertIn("2610.39139", content)

    def _check_rhythm_and_voice(self, path: Path):
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
        self.assertTrue(lengths, f"No sentences found in {path}")
        med = statistics.median(lengths)
        self.assertLessEqual(med, 22.0, f"{path.name} median sentence length {med:.1f} exceeds 22 words")
        over_35 = [s for s in sentences if len(s.split()) > 35]
        self.assertEqual(len(over_35), 0, f"{path.name} has {len(over_35)} sentences > 35 words: {over_35[:2]}")

    def test_sentence_rhythm(self):
        self._check_rhythm_and_voice(RESEARCH_FILE)
        self._check_rhythm_and_voice(OTHERS_FILE)

    def test_no_forbidden_promises(self):
        for path in (RESEARCH_FILE, OTHERS_FILE):
            content = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("guaranteed returns", content)
            self.assertNotIn("passive income", content)


if __name__ == "__main__":
    unittest.main()
