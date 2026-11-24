#!/usr/bin/env python3
"""Unit tests verifying the five proposals visual explainer on vision.html.

Ensures strict compliance with:
- Spec 05 Visual Direction & Explainer standards
- Accessible SVG titles, descriptions, and ARIA bindings
- XML well-formedness (valid under xml.etree.ElementTree)
- Plain language and steward voice constraints (<= 22 words median, zero > 35 words)
- Presence in built HTML distribution
"""

from pathlib import Path
import re
import statistics
import unittest
from xml.etree import ElementTree as ET

SITE_ROOT = Path(__file__).resolve().parents[1]
VISION_HTML = SITE_ROOT / "content" / "vision.html"
DIST_VISION_HTML = SITE_ROOT / "dist" / "vision" / "index.html"


class VisionExplainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_content = VISION_HTML.read_text(encoding="utf-8")
        cls.fig_match = re.search(
            r'<figure\b[^>]*id=["\']ex-five-proposals["\'][^>]*>(.*?)</figure>',
            cls.raw_content,
            re.DOTALL,
        )

    def test_explainer_figure_exists(self):
        """The vision page must contain the ex-five-proposals explainer figure."""
        self.assertIsNotNone(
            self.fig_match,
            "Missing <figure class='explainer' id='ex-five-proposals'> in site/content/vision.html",
        )

    def test_svg_xml_validity(self):
        """The SVG must be strictly valid XML parseable by xml.etree.ElementTree."""
        body = self.fig_match.group(1)
        svg_m = re.search(r"<svg\b[^>]*>.*?</svg>", body, re.DOTALL)
        self.assertIsNotNone(svg_m, "No <svg> block found inside explainer figure.")
        svg_xml = svg_m.group(0)

        # Ensure valid XML namespaces for standalone parsing
        if "xmlns=" not in svg_xml:
            svg_xml = svg_xml.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)

        try:
            root = ET.fromstring(svg_xml)
        except ET.ParseError as e:
            self.fail(f"SVG XML parsing failed: {e}")

        self.assertEqual(root.tag.split("}")[-1], "svg")
        self.assertIn("viewBox", root.attrib)
        self.assertEqual(root.attrib["viewBox"], "0 0 460 270")

    def test_accessibility_bindings(self):
        """SVG must provide role='img' or 'group' and match aria-labelledby to title and desc IDs."""
        body = self.fig_match.group(1)
        svg_m = re.search(r"<svg\b[^>]*>", body, re.DOTALL)
        tag = svg_m.group(0)

        self.assertTrue('role="img"' in tag or 'role="group"' in tag)
        self.assertIn('aria-labelledby="ex-five-proposals-title ex-five-proposals-desc"', tag)
        self.assertIn('<title id="ex-five-proposals-title">', body)
        self.assertIn('<desc id="ex-five-proposals-desc">', body)

    def test_spec_05_color_palette(self):
        """Diagram must use matrix stage structure with warm cream, terracotta, and forest green tokens."""
        body = self.fig_match.group(1)
        self.assertIn('data-stage="matrix"', body, "Missing planar matrix stage")
        self.assertIn("#B85C38", body, "Missing terracotta #B85C38 accent token")
        self.assertIn("#0B3F30", body, "Missing deep forest green #0B3F30 token")
        self.assertIn("#DFD1BE", body, "Missing hairline rule #DFD1BE token")
        stages_css = (SITE_ROOT / "assets" / "css" / "stages.css").read_text(encoding="utf-8")
        self.assertIn("#FAF3EA", stages_css, "Missing warm cream #FAF3EA token in stages.css")

    def test_five_pillars_represented(self):
        """All five core proposals must have numbered badges and distinct titles in the SVG."""
        body = self.fig_match.group(1)
        for num in ("01", "02", "03", "04", "05"):
            self.assertIn(f">{num}<", body, f"Missing badge {num} in explainer")
        self.assertIn("Action receipts", body)
        self.assertIn("Duty of loyalty", body)
        self.assertIn("Expiring leases", body)
        self.assertIn("The second road", body)
        self.assertIn("Public computing", body)

    def test_plain_language_voice_gates(self):
        """Figcaption text must obey <= 22 median sentence length and zero > 35 words."""
        cap_m = re.search(r"<figcaption>(.*?)</figcaption>", self.fig_match.group(1), re.DOTALL)
        self.assertIsNotNone(cap_m, "Explainer must have an accessible figcaption")
        cap_text = cap_m.group(1).strip()
        self.assertNotIn("—", cap_text, "Figcaption must not contain em-dashes")

        sentences = [s.strip() for s in re.split(r"[\.\?\!]\s+", cap_text) if s.strip()]
        for s in sentences:
            words = s.split()
            self.assertLessEqual(len(words), 35, f"Figcaption sentence too long ({len(words)}w): '{s}'")
        lens = [len(s.split()) for s in sentences]
        self.assertLessEqual(statistics.median(lens), 22, "Figcaption median sentence length exceeds 22 words")

    def test_explainer_in_dist_build(self):
        """When built, dist/vision/index.html must contain the explainer figure."""
        if DIST_VISION_HTML.exists():
            dist_text = DIST_VISION_HTML.read_text(encoding="utf-8")
            self.assertIn('id="ex-five-proposals"', dist_text)
            self.assertIn('id="ex-five-proposals-title"', dist_text)


if __name__ == "__main__":
    unittest.main()
