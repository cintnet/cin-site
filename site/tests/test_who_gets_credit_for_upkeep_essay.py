"""Unit tests for who-gets-credit-for-upkeep essay and its responsive mobile explainer."""

import os
import re
import unittest
import xml.etree.ElementTree as ET

SITE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARTICLE_PATH = os.path.join(SITE_DIR, "content", "blog", "who-gets-credit-for-upkeep.html")


class TestWhoGetsCreditForUpkeepEssay(unittest.TestCase):
    def setUp(self):
        self.assertTrue(os.path.exists(ARTICLE_PATH), f"Missing article: {ARTICLE_PATH}")
        with open(ARTICLE_PATH, "r", encoding="utf-8") as f:
            self.content = f.read()

    def test_explainer_figure_exists(self):
        self.assertIn('<figure class="explainer" id="ex-maintenance-receipts">', self.content)
        self.assertIn("</figure>", self.content)

    def test_researcher_disclosure_exists(self):
        self.assertIn('<aside class="for-researchers">', self.content)
        self.assertIn("IETF SCITT", self.content)
        self.assertIn("Ostrom, 1990", self.content)

    def test_no_redundant_nested_prose_wrapper(self):
        self.assertNotIn('<div class="prose wrap-narrow">', self.content)

    def test_desktop_svg_attributes_and_accessibility(self):
        match = re.search(
            r'<figure class="explainer" id="ex-maintenance-receipts">.*?(<svg\b[^>]*class=["\'][^"\']*\bdiagram-desktop\b[^"\']*["\'][^>]*>.*?</svg>)',
            self.content,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "Could not find desktop svg inside #ex-maintenance-receipts")
        svg_code = match.group(1)

        self.assertIn('viewBox="0 0 700 350"', svg_code)
        self.assertIn('role="img"', svg_code)
        self.assertIn('aria-labelledby="ex-maintenance-receipts-title ex-maintenance-receipts-desc"', svg_code)
        self.assertIn('<title id="ex-maintenance-receipts-title">', svg_code)
        self.assertIn('<desc id="ex-maintenance-receipts-desc">', svg_code)

    def test_mobile_svg_attributes_and_accessibility(self):
        match = re.search(
            r'<figure class="explainer" id="ex-maintenance-receipts">.*?(<svg\b[^>]*class=["\'][^"\']*\bdiagram-mobile\b[^"\']*["\'][^>]*>.*?</svg>)',
            self.content,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "Could not find mobile svg inside #ex-maintenance-receipts")
        svg_code = match.group(1)

        self.assertIn('viewBox="0 0 330 690"', svg_code)
        self.assertIn('role="img"', svg_code)
        self.assertIn('aria-labelledby="ex-maintenance-receipts-m-title ex-maintenance-receipts-m-desc"', svg_code)
        self.assertIn('<title id="ex-maintenance-receipts-m-title">', svg_code)
        self.assertIn('<desc id="ex-maintenance-receipts-m-desc">', svg_code)

    def test_responsive_media_query_and_layout_switching(self):
        self.assertIn("@media (max-width: 600px)", self.content)
        self.assertIn(".diagram-desktop", self.content)
        self.assertIn(".diagram-mobile", self.content)

    def test_svg_is_well_formed_xml(self):
        match = re.search(r'<figure class="explainer" id="ex-maintenance-receipts">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match)
        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', match.group(0), re.DOTALL)
        self.assertGreaterEqual(len(svgs), 2, "Expected both desktop and mobile SVGs in explainer")
        for svg_code in svgs:
            try:
                root = ET.fromstring(svg_code)
                self.assertEqual(root.tag, "svg")
            except ET.ParseError as e:
                self.fail(f"SVG is not valid XML: {e}")

    def test_mobile_font_size_readability_at_343px(self):
        match = re.search(r'<figure class="explainer" id="ex-maintenance-receipts">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match)
        fig = match.group(0)

        m_match = re.search(r'<svg\b[^>]*class=["\'][^"\']*\bdiagram-mobile\b[^"\']*["\'][^>]*>(.*?)</svg>', fig, re.DOTALL)
        self.assertIsNotNone(m_match, "Could not find mobile SVG in explainer")
        mobile_svg_inner = m_match.group(0)

        vb_match = re.search(r'viewBox=["\']\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*["\']', mobile_svg_inner)
        self.assertIsNotNone(vb_match, "Missing or invalid viewBox in mobile SVG")
        vb_width = float(vb_match.group(3))

        font_sizes = [float(fs) for fs in re.findall(r'font-size=["\']([0-9.]+)["\']', mobile_svg_inner)]
        self.assertTrue(len(font_sizes) > 0, "No explicit font-size attributes found in mobile SVG text elements")

        rendered_width = 343.0
        min_font_size = min(font_sizes)
        rendered_min_font = min_font_size * (rendered_width / vb_width)

        self.assertGreaterEqual(
            rendered_min_font,
            11.0,
            f"Smallest mobile SVG text renders at {rendered_min_font:.2f}px in a 343px container (fails below 11px)",
        )

    def test_voice_and_humanizer_invariants(self):
        # 0 em-dashes
        self.assertNotIn("—", self.content, "Prose or explainer contains forbidden em-dash")

        # 0 forbidden AI buzzwords
        forbidden = [
            "delve", "tapestry", "testament", "underscore", "showcase",
            "foster", "pivotal", "intricate", "realm", "vibrant",
            "seamless", "crucial", "landscape",
        ]
        lower_content = self.content.lower()
        for word in forbidden:
            self.assertNotIn(f" {word} ", lower_content, f"Prose contains forbidden AI vocabulary: '{word}'")


if __name__ == "__main__":
    unittest.main()
