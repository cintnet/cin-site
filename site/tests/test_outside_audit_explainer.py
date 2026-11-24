"""Unit tests for the outside audit visual explainer on why-an-ai-agent-will-not-audit-itself."""

import os
import re
import unittest
import xml.etree.ElementTree as ET

SITE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARTICLE_PATH = os.path.join(SITE_DIR, "content", "blog", "why-an-ai-agent-will-not-audit-itself.html")


class TestOutsideAuditExplainer(unittest.TestCase):
    def setUp(self):
        self.assertTrue(os.path.exists(ARTICLE_PATH), f"Missing article: {ARTICLE_PATH}")
        with open(ARTICLE_PATH, "r", encoding="utf-8") as f:
            self.content = f.read()

    def test_explainer_figure_exists(self):
        self.assertIn('<figure class="explainer" id="ex-outside-audit">', self.content)
        self.assertIn("</figure>", self.content)

    def test_svg_attributes_and_accessibility(self):
        match = re.search(r'<figure class="explainer" id="ex-outside-audit">.*?(<svg[^>]*>.*?</svg>)', self.content, re.DOTALL)
        self.assertIsNotNone(match, "Could not find svg inside #ex-outside-audit")
        svg_code = match.group(1)

        self.assertIn('viewBox="0 0 720 330"', svg_code)
        self.assertIn('role="img"', svg_code)
        self.assertIn('aria-labelledby="ex-audit-title ex-audit-desc"', svg_code)
        self.assertIn('<title id="ex-audit-title">', svg_code)
        self.assertIn('<desc id="ex-audit-desc">', svg_code)

    def test_svg_is_well_formed_xml(self):
        match = re.search(r'<figure class="explainer" id="ex-outside-audit">.*?(<svg[^>]*>.*?</svg>)', self.content, re.DOTALL)
        self.assertIsNotNone(match)
        svg_code = match.group(1)
        try:
            root = ET.fromstring(svg_code)
            self.assertEqual(root.tag, "svg")
        except ET.ParseError as e:
            self.fail(f"SVG is not valid XML: {e}")

    def test_contrasting_sections_and_cognitive_load(self):
        match = re.search(r'<figure class="explainer" id="ex-outside-audit">.*?(<svg[^>]*>.*?</svg>)', self.content, re.DOTALL)
        svg_code = match.group(1)
        root = ET.fromstring(svg_code)

        # Ensure cognitive clarity: text elements should stay under 28 nodes
        texts = root.findall(".//text")
        self.assertLessEqual(len(texts), 28, f"Too many text nodes in diagram ({len(texts)} > 28)")
        self.assertGreaterEqual(len(texts), 12, "Diagram has too few text nodes")

        # Verify key architectural comparisons
        self.assertIn("SELF-REPORTING INSIDE AGENT", svg_code)
        self.assertIn("INDEPENDENT OUTSIDE CHECK", svg_code)
        self.assertIn("Mistakes hidden in 67% of multi-step task runs", svg_code)
        self.assertIn("Separated Verifier Pass", svg_code)
        self.assertIn("kernel-level egress escrow", svg_code.lower())

    def test_figcaption_and_no_banned_tells(self):
        match = re.search(r'<figure class="explainer" id="ex-outside-audit">.*?<figcaption>(.*?)</figcaption>', self.content, re.DOTALL)
        self.assertIsNotNone(match, "Missing figcaption in explainer")
        caption = match.group(1)
        self.assertNotIn("—", caption, "Found em-dash in caption")
        for tell in ["delve", "tapestry", "seamless", "crucial", "landscape", "pivotal", "foster"]:
            self.assertNotIn(tell, caption.lower(), f"Found AI tell in caption: {tell}")


if __name__ == "__main__":
    unittest.main()
