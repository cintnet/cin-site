#!/usr/bin/env python3
"""Unit tests for research credit curation on public sector benchmarks, institutional governance graphs, and everyday protocol cryptography (gemini-partners)."""

from pathlib import Path
import re
import statistics
import unittest

SITE_ROOT = Path(__file__).resolve().parents[1]
OTHERS_FILE = SITE_ROOT / "content" / "about" / "others.html"
RESEARCHERS_FILE = SITE_ROOT / "content" / "get-involved" / "researchers.html"


class TestPublicSectorAndInstitutionalGovernanceCredit(unittest.TestCase):
    def test_files_exist(self):
        self.assertTrue(OTHERS_FILE.exists(), "others.html must exist")
        self.assertTrue(RESEARCHERS_FILE.exists(), "researchers.html must exist")

    def test_others_html_contains_grounded_provenance(self):
        content = OTHERS_FILE.read_text(encoding="utf-8")
        # Marcantonio Bracale Syrnikov et al. (arXiv:2601.11369)
        self.assertIn("Marcantonio Bracale Syrnikov", content)
        self.assertIn("Federico Pierucci", content)
        self.assertIn("Public Governance Graphs", content)
        self.assertIn("2601.11369", content)
        self.assertIn('href="#fn118"', content)
        self.assertIn('id="fn118"', content)

        # Jonathan Rystrøm et al. (arXiv:2601.20617)
        self.assertTrue("Jonathan Rystr&oslash;m" in content or "Jonathan Rystrøm" in content)
        self.assertIn("Chris Schmitz", content)
        self.assertIn("2601.20617", content)
        self.assertIn('href="#fn119"', content)
        self.assertIn('id="fn119"', content)

        # Marco De Rossi (arXiv:2602.01304)
        self.assertIn("Marco De Rossi", content)
        self.assertIn("2602.01304", content)
        self.assertIn('href="#fn115"', content)
        self.assertIn('id="fn115"', content)

    def test_researchers_html_contains_grounded_provenance(self):
        content = RESEARCHERS_FILE.read_text(encoding="utf-8")
        # Marcantonio Bracale Syrnikov et al. (arXiv:2601.11369)
        self.assertIn("2601.11369", content)
        self.assertIn('href="#fn45"', content)
        self.assertIn('id="fn45"', content)
        self.assertIn("Bracale Syrnikov et al., 2026", content)

        # Marco De Rossi (arXiv:2602.01304)
        self.assertIn("2602.01304", content)
        self.assertIn('href="#fn46"', content)
        self.assertIn('id="fn46"', content)
        self.assertIn("De Rossi, 2026", content)

        # Jonathan Rystrøm et al. (arXiv:2601.20617)
        self.assertIn("2601.20617", content)
        self.assertIn('href="#fn47"', content)
        self.assertIn('id="fn47"', content)
        self.assertTrue("Rystr&oslash;m et al., 2026" in content or "Rystrøm et al., 2026" in content)

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
        for path in [OTHERS_FILE, RESEARCHERS_FILE]:
            text = path.read_text(encoding="utf-8").lower()
            for forbidden in ["guaranteed return", "passive income", "mmct token", "token sale"]:
                self.assertNotIn(forbidden, text, f"{path.name} contains forbidden term: {forbidden}")


if __name__ == "__main__":
    unittest.main()
