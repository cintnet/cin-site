#!/usr/bin/env python3
"""Deterministic verification suite for the zero-tracking reading boundary explainer on the privacy page (D-1419 / gemini-media)."""

from pathlib import Path
import re
import statistics
import unittest
from xml.etree import ElementTree as ET

SITE_ROOT = Path(__file__).resolve().parents[1]
PRIVACY_FILE = SITE_ROOT / "content" / "privacy.html"


class TestPrivacyPageExplainer(unittest.TestCase):
    def setUp(self):
        self.assertTrue(PRIVACY_FILE.exists(), f"Expected {PRIVACY_FILE} to exist")
        self.content = PRIVACY_FILE.read_text(encoding="utf-8")

    def test_explainer_presence_and_id(self):
        self.assertIn('<figure class="explainer" id="ex-privacy-boundary">', self.content)
        self.assertIn('</figure>', self.content)

    def test_explainer_svg_well_formed_xml(self):
        svg_m = re.search(r'(<svg\b[^>]*>.*?</svg>)', self.content, re.DOTALL)
        self.assertIsNotNone(svg_m, "No <svg> tag found inside privacy.html")
        svg_str = svg_m.group(1)

        # Must parse cleanly with standard xml.etree.ElementTree
        root = ET.fromstring(svg_str)
        self.assertEqual(root.tag.split("}")[-1], "svg")

    def test_explainer_accessibility_and_viewbox(self):
        self.assertIn('data-stage="switchyard"', self.content)
        self.assertIn('data-rail-option="edge"', self.content)
        self.assertIn('data-rail-option="tracked"', self.content)
        self.assertIn('viewBox="0 0 680 220"', self.content)
        self.assertIn('role="img"', self.content)
        self.assertIn('aria-labelledby="ex-privacy-boundary-title ex-privacy-boundary-desc"', self.content)
        self.assertIn('<title id="ex-privacy-boundary-title">', self.content)
        self.assertIn('<desc id="ex-privacy-boundary-desc">', self.content)
        self.assertIn('<figcaption>', self.content)

    def test_spec05_warm_literary_palette(self):
        # Warm cream in stages.css, terracotta warnings, deep forest green safe gating
        self.assertIn("#0B3F30", self.content)
        self.assertIn("#B85C38", self.content)
        self.assertIn("#131014", self.content)
        self.assertIn("#5E564B", self.content)
        self.assertIn("#E1D3C0", self.content)
        stages_css = (SITE_ROOT / "assets" / "css" / "stages.css").read_text(encoding="utf-8")
        self.assertIn("#FAF3EA", stages_css)

    def test_voice_rhythm_and_sentence_length(self):
        text = self.content
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                text = parts[2]
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
        text = re.sub(r"<(svg|script|style|aside)[^>]*>.*?</\1>", " ", text, flags=re.DOTALL)
        text = re.sub(r"</(h[1-6]|p|li|div|figcaption|tr|td|th)>", ". ", text)
        text = re.sub(r"<[^>]+>", " ", text)
        sentences = [s.strip() for s in re.split(r'[\.\?\!]["\u2019\u201d\')\]]*(?:\s+|$)', text) if s.strip()]
        lengths = [len(s.split()) for s in sentences if len(s.split()) > 2]
        self.assertTrue(lengths, "No sentences found in privacy.html")
        med = statistics.median(lengths)
        self.assertLessEqual(med, 22.0, f"privacy.html median sentence length {med:.1f} exceeds 22 words")
        over_35 = [s for s in sentences if len(s.split()) > 35]
        self.assertEqual(len(over_35), 0, f"privacy.html has sentences > 35 words: {over_35}")

    def test_no_forbidden_promises(self):
        lower = self.content.lower()
        for forbidden in ("guaranteed returns", "passive income", "mmct", "token sale"):
            self.assertNotIn(forbidden, lower)


if __name__ == "__main__":
    unittest.main()
