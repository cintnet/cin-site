#!/usr/bin/env python3
"""Unit tests for research credit curation on multi-agent cascade attack monitoring (D-1461 / gemini-partners)."""

from pathlib import Path
import re
import statistics
import unittest

SITE_ROOT = Path(__file__).resolve().parents[1]
OTHERS_FILE = SITE_ROOT / "content" / "about" / "others.html"
RESEARCHERS_FILE = SITE_ROOT / "content" / "get-involved" / "researchers.html"


class TestCaspianCascadeAttackCredit(unittest.TestCase):
    def test_files_exist(self):
        self.assertTrue(OTHERS_FILE.exists(), "others.html must exist")
        self.assertTrue(RESEARCHERS_FILE.exists(), "researchers.html must exist")

    def test_others_html_contains_grounded_provenance(self):
        content = OTHERS_FILE.read_text(encoding="utf-8")
        self.assertIn("CASPIAN", content)
        self.assertIn("Venkatesh", content)
        self.assertIn("2605.19240", content)
        self.assertIn("fn96", content)
        self.assertIn("conditional transfer entropy", content)
        self.assertIn("multi-agent cascade detection", content)

    def test_researchers_html_contains_grounded_provenance(self):
        content = RESEARCHERS_FILE.read_text(encoding="utf-8")
        self.assertIn("CASPIAN", content)
        self.assertIn("Venkatesh", content)
        self.assertIn("2605.19240", content)
        self.assertIn("fn32", content)
        self.assertIn("causal transfer entropy", content)

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
        self._check_rhythm_and_voice(RESEARCHERS_FILE)

    def test_no_forbidden_promises(self):
        for path in (OTHERS_FILE, RESEARCHERS_FILE):
            content = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("guaranteed returns", content)
            self.assertNotIn("passive income", content)
            self.assertNotIn("profit sharing", content)
            self.assertNotIn("token appreciation", content)


if __name__ == "__main__":
    unittest.main()
