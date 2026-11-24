#!/usr/bin/env python3
"""Unit tests for research credit curation on Drex Foundation Decision Models (D-1545 / gemini-adopt)."""

from pathlib import Path
import re
import statistics
import unittest

SITE_ROOT = Path(__file__).resolve().parents[1]
OTHERS_FILE = SITE_ROOT / "content" / "about" / "others.html"


class TestDrexCredit(unittest.TestCase):
    def test_file_exists(self):
        self.assertTrue(OTHERS_FILE.exists(), "others.html must exist")

    def test_others_html_contains_grounded_provenance(self):
        content = OTHERS_FILE.read_text(encoding="utf-8")
        self.assertIn("Nischay Dhankhar", content)
        self.assertIn("Alisher Amantay", content)
        self.assertIn("2611.07854", content)
        self.assertIn("fn107", content)
        self.assertIn("foundation decision models", content.lower())

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
        self._check_rhythm_and_voice(OTHERS_FILE)

    def test_no_forbidden_promises(self):
        content = OTHERS_FILE.read_text(encoding="utf-8").lower()
        for phrase in ("guaranteed profit", "royalty", "tokenomics", "mmct", "investment return"):
            self.assertNotIn(phrase, content, f"Forbidden phrase '{phrase}' found in {OTHERS_FILE.name}")


if __name__ == "__main__":
    unittest.main()
