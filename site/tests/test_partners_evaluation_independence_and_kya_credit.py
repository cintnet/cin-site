#!/usr/bin/env python3
"""Unit tests for research credit curation on independent evaluation infrastructure, KYA identity tenets, and distributional conformance contracts (gemini-partners)."""

from pathlib import Path
import re
import statistics
import unittest

SITE_ROOT = Path(__file__).resolve().parents[1]
OTHERS_FILE = SITE_ROOT / "content" / "about" / "others.html"
RESEARCHERS_FILE = SITE_ROOT / "content" / "get-involved" / "researchers.html"


class TestPartnersEvaluationIndependenceAndKyaCredit(unittest.TestCase):
    def test_files_exist(self):
        self.assertTrue(OTHERS_FILE.exists(), "others.html must exist")
        self.assertTrue(RESEARCHERS_FILE.exists(), "researchers.html must exist")

    def test_others_html_contains_grounded_provenance(self):
        content = OTHERS_FILE.read_text(encoding="utf-8")
        # HKMA Project SAGE, NIST AIMS, DASMark
        self.assertIn("Project SAGE", content)
        self.assertIn("Design Tenets for Agent Identity Management Systems", content)
        self.assertIn("2610.24382", content)
        self.assertIn('href="#fn148"', content)
        self.assertIn('id="fn148"', content)

        # Distributional delegation contracts (arXiv:2610.33112)
        self.assertIn("2610.33112", content)
        self.assertIn('href="#fn149"', content)
        self.assertIn('id="fn149"', content)

        # Adan et al. (arXiv:2611.08134) and evaluation-based governance interviews (arXiv:2611.00465)
        self.assertIn("Sumaya Nur Adan", content)
        self.assertIn("2611.08134", content)
        self.assertIn("2611.00465", content)
        self.assertIn('href="#fn150"', content)
        self.assertIn('id="fn150"', content)

    def test_researchers_html_contains_grounded_provenance(self):
        content = RESEARCHERS_FILE.read_text(encoding="utf-8")
        self.assertIn("HKMA Project SAGE, 2026", content)
        self.assertIn("2610.24382", content)
        self.assertIn('href="#fn77"', content)
        self.assertIn('id="fn77"', content)

        self.assertIn("2610.33112", content)
        self.assertIn('href="#fn78"', content)
        self.assertIn('id="fn78"', content)

        self.assertIn("Adan et al., 2026", content)
        self.assertIn("2611.08134", content)
        self.assertIn("2611.00465", content)
        self.assertIn('href="#fn79"', content)
        self.assertIn('id="fn79"', content)

    def test_non_endorsement_and_no_forbidden_promises(self):
        others_text = OTHERS_FILE.read_text(encoding="utf-8").lower()
        self.assertIn("never imply endorsement", RESEARCHERS_FILE.read_text(encoding="utf-8").lower())
        self.assertIn("never claim that citing published research implies commercial endorsement", others_text)
        for path in [OTHERS_FILE, RESEARCHERS_FILE]:
            text = path.read_text(encoding="utf-8").lower()
            for forbidden in ["guaranteed return", "passive income", "mmct token", "token sale"]:
                self.assertNotIn(forbidden, text, f"{path.name} contains forbidden term: {forbidden}")

    def test_sentence_rhythm(self):
        for path in [OTHERS_FILE, RESEARCHERS_FILE]:
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


if __name__ == "__main__":
    unittest.main()
