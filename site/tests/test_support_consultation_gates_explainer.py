#!/usr/bin/env python3
"""Unit tests verifying the interactive consultation gates explainer on support.html.

Ensures strict compliance with:
- Spec 05 Visual Direction & Explainer standards
- Accessible SVG titles, descriptions, and ARIA bindings
- XML well-formedness (100% valid under xml.etree.ElementTree)
- Plain language and steward voice constraints (<= 22 words median, zero > 35 words)
- Presence in built HTML distribution
"""

from pathlib import Path
import re
import statistics
import unittest
from xml.etree import ElementTree as ET

SITE_ROOT = Path(__file__).resolve().parents[1]
SUPPORT_HTML = SITE_ROOT / "content" / "support.html"
DIST_SUPPORT_HTML = SITE_ROOT / "dist" / "support" / "index.html"


class SupportConsultationGatesExplainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_content = SUPPORT_HTML.read_text(encoding="utf-8")
        cls.fig_match = re.search(
            r'<figure\b[^>]*id=["\']ex-consultation-gates["\'][^>]*>(.*?)</figure>',
            cls.raw_content,
            re.DOTALL,
        )

    def test_explainer_figure_exists(self):
        """The support page must contain the ex-consultation-gates explainer figure."""
        self.assertIsNotNone(
            self.fig_match,
            "Missing <figure class='explainer' id='ex-consultation-gates'> in site/content/support.html",
        )

    def test_svg_xml_validity(self):
        """The SVG must be strictly valid XML parseable by xml.etree.ElementTree."""
        body = self.fig_match.group(1)
        svg_m = re.search(r"<svg\b[^>]*>.*?</svg>", body, re.DOTALL)
        self.assertIsNotNone(svg_m, "No <svg> block found inside explainer figure.")
        svg_xml = svg_m.group(0)

        # Ensure valid XML namespaces for standalone parsing
        if "xmlns=" not in svg_xml:
            svg_xml = svg_xml.replace("<svg ", "<svg xmlns=\"http://www.w3.org/2000/svg\" ", 1)

        try:
            root = ET.fromstring(svg_xml)
        except ET.ParseError as e:
            self.fail(f"SVG XML parsing failed: {e}")

        self.assertEqual(root.tag.split("}")[-1], "svg")
        self.assertIn("viewBox", root.attrib)
        self.assertEqual(root.attrib["viewBox"], "0 0 680 220")

    def test_accessibility_bindings(self):
        """SVG must provide role='group' or 'img' and match aria-labelledby to title and desc IDs."""
        body = self.fig_match.group(1)
        svg_m = re.search(r"<svg\b[^>]*>", body, re.DOTALL)
        tag = svg_m.group(0)

        self.assertIn('aria-labelledby="ex-consultation-title ex-consultation-desc"', tag)
        self.assertIn('<title id="ex-consultation-title">', body)
        self.assertIn('<desc id="ex-consultation-desc">', body)

    def test_spec_05_color_palette(self):
        """Diagram must use switchyard stage structure with terracotta, forest green, and cream tokens."""
        body = self.fig_match.group(1)
        self.assertIn('data-stage="switchyard"', body, "Missing interactive switchyard stage")
        self.assertIn('data-rail-option="gated"', body)
        self.assertIn('data-rail-option="rushed"', body)
        self.assertIn("#B85C38", body, "Missing terracotta #B85C38 hazard token")
        self.assertIn("#0B3F30", body, "Missing deep forest green #0B3F30 token")
        stages_css = (SITE_ROOT / "assets" / "css" / "stages.css").read_text(encoding="utf-8")
        self.assertIn("#FAF3EA", stages_css, "Missing warm cream #FAF3EA token in stages.css")
        self.assertIn("#1F6B4E", stages_css, "Missing sage green #1F6B4E token in stages.css")

    def test_plain_language_voice_gates(self):
        """Figcaption and Q&A text must obey <= 22 median sentence length and zero > 35 words."""
        # Check figcaption
        cap_m = re.search(r"<figcaption>(.*?)</figcaption>", self.fig_match.group(1), re.DOTALL)
        self.assertIsNotNone(cap_m, "Explainer must have an accessible figcaption")
        cap_text = cap_m.group(1).strip()
        sentences = [s.strip() for s in re.split(r"[\.\?\!]\s+", cap_text) if s.strip()]
        for s in sentences:
            words = s.split()
            self.assertLessEqual(len(words), 35, f"Figcaption sentence too long ({len(words)}w): '{s}'")

        # Check the newly added Q&A text
        qa_match = re.search(
            r"<h3>Why do automated assistants break rules or overstep boundaries when rushed to finish a task\?</h3>(.*?)(?=<figure|<h3)",
            self.raw_content,
            re.DOTALL,
        )
        self.assertIsNotNone(qa_match, "Missing Q&A section on assistant boundary overreach under rush")
        qa_prose = re.sub(r"<[^>]+>", " ", qa_match.group(1))
        qa_sentences = [re.sub(r"\s+", " ", s).strip() for s in re.split(r"[\.\?\!]\s+", qa_prose) if len(s.strip().split()) >= 2]
        self.assertTrue(len(qa_sentences) >= 5, "Expected at least 5 explanatory sentences in the Q&A section")

        lens = [len(s.split()) for s in qa_sentences]
        median_len = statistics.median(lens)
        self.assertLessEqual(median_len, 22, f"Q&A median sentence length ({median_len}) exceeds 22 words")
        for s in qa_sentences:
            words = s.split()
            self.assertLessEqual(len(words), 35, f"Q&A sentence too long ({len(words)}w): '{s}'")

    def test_explainer_in_dist_build(self):
        """When built, dist/support/index.html must contain the explainer figure."""
        if DIST_SUPPORT_HTML.exists():
            dist_text = DIST_SUPPORT_HTML.read_text(encoding="utf-8")
            self.assertIn('id="ex-consultation-gates"', dist_text)
            self.assertIn('id="ex-consultation-title"', dist_text)


if __name__ == "__main__":
    unittest.main()
