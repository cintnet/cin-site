"""Unit tests for governments-and-ai-agents essay and its responsive mobile explainer."""

import os
import re
import unittest
import xml.etree.ElementTree as ET

SITE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARTICLE_PATH = os.path.join(SITE_DIR, "content", "blog", "governments-and-ai-agents.html")


class TestGovernmentsAndAiAgentsEssay(unittest.TestCase):
    def setUp(self):
        self.assertTrue(os.path.exists(ARTICLE_PATH), f"Missing article: {ARTICLE_PATH}")
        with open(ARTICLE_PATH, "r", encoding="utf-8") as f:
            self.content = f.read()

    def test_explainer_figure_exists(self):
        self.assertIn('<figure class="explainer" id="ex-agent-gatekeeper">', self.content)
        self.assertIn("</figure>", self.content)

    def test_no_redundant_nested_prose_wrapper(self):
        self.assertNotIn('<div class="prose wrap-narrow">', self.content)

    def test_desktop_svg_attributes_and_accessibility(self):
        match = re.search(
            r'<figure class="explainer" id="ex-agent-gatekeeper">.*?(<svg\b[^>]*class=["\'][^"\']*\bdiagram-desktop\b[^"\']*["\'][^>]*>.*?</svg>)',
            self.content,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "Could not find desktop svg inside #ex-agent-gatekeeper")
        svg_code = match.group(1)

        self.assertIn('viewBox="0 0 700 340"', svg_code)
        self.assertIn('aria-labelledby="ex-agent-gatekeeper-title ex-agent-gatekeeper-desc"', svg_code)
        self.assertIn('<title id="ex-agent-gatekeeper-title">', svg_code)
        self.assertIn('<desc id="ex-agent-gatekeeper-desc">', svg_code)

    def test_mobile_svg_attributes_and_accessibility(self):
        match = re.search(
            r'<figure class="explainer" id="ex-agent-gatekeeper">.*?(<svg\b[^>]*class=["\'][^"\']*\bdiagram-mobile\b[^"\']*["\'][^>]*>.*?</svg>)',
            self.content,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "Could not find mobile svg inside #ex-agent-gatekeeper")
        svg_code = match.group(1)

        self.assertIn('viewBox="0 0 330 690"', svg_code)
        self.assertIn('role="img"', svg_code)
        self.assertIn('aria-labelledby="ex-agent-gatekeeper-m-title ex-agent-gatekeeper-m-desc"', svg_code)
        self.assertIn('<title id="ex-agent-gatekeeper-m-title">', svg_code)
        self.assertIn('<desc id="ex-agent-gatekeeper-m-desc">', svg_code)

    def test_responsive_media_query_and_layout_switching(self):
        self.assertIn("@media (max-width: 600px)", self.content)
        self.assertIn(".diagram-desktop", self.content)
        self.assertIn(".diagram-mobile", self.content)

    def test_svg_is_well_formed_xml(self):
        match = re.search(r'<figure class="explainer" id="ex-agent-gatekeeper">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match)
        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', match.group(0), re.DOTALL)
        self.assertGreaterEqual(len(svgs), 2, "Expected both desktop and mobile SVGs in explainer")
        for svg_code in svgs:
            try:
                root = ET.fromstring(svg_code)
                self.assertEqual(root.tag, "svg")
            except ET.ParseError as e:
                self.fail(f"SVG failed XML validation: {e}\n{svg_code[:200]}...")

    def test_mobile_font_readability_at_343px_width(self):
        match = re.search(r'<figure class="explainer" id="ex-agent-gatekeeper">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match)
        fig = match.group(0)

        m_match = re.search(r'<svg\b[^>]*class=["\'][^"\']*\bdiagram-mobile\b[^"\']*["\'][^>]*>(.*?)</svg>', fig, re.DOTALL)
        self.assertIsNotNone(m_match, "Could not find mobile SVG in explainer")
        mobile_svg_inner = m_match.group(0)

        vb_match = re.search(r'viewBox=["\']\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*["\']', mobile_svg_inner)
        self.assertIsNotNone(vb_match, "Mobile SVG missing viewBox")
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

        d_match = re.search(r'<svg\b[^>]*class=["\'][^"\']*\bdiagram-desktop\b[^"\']*["\'][^>]*>(.*?)</svg>', fig, re.DOTALL)
        self.assertIsNotNone(d_match, "Could not find desktop SVG in explainer")
        desktop_svg_inner = d_match.group(0)
        d_vb_match = re.search(r'viewBox=["\']\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*["\']', desktop_svg_inner)
        d_vb_width = float(d_vb_match.group(3))
        d_font_sizes = [float(fs) for fs in re.findall(r'font-size=["\']([0-9.]+)["\']', desktop_svg_inner)]
        desktop_rendered_min_font = min(d_font_sizes) * (rendered_width / d_vb_width)

        self.assertLess(
            desktop_rendered_min_font,
            11.0,
            f"Desktop SVG unexpectedly passed mobile threshold: {desktop_rendered_min_font:.2f}px",
        )

    def test_shared_horizon_link_present(self):
        self.assertIn('/labs/shared-horizon/', self.content, "Missing Shared Horizon link in essay")

    def test_voice_and_humanizer_invariants(self):
        self.assertNotIn("—", self.content, "Found em-dash in essay prose")

        ai_words = [
            "delve", "tapestry", "testament", "underscore", "showcase", "foster",
            "pivotal", "intricate", "realm", "vibrant", "seamless", "crucial", "landscape",
        ]
        text_lower = self.content.lower()
        for word in ai_words:
            self.assertNotIn(f" {word} ", text_lower, f"Found AI stock word '{word}' in essay")


if __name__ == "__main__":
    unittest.main()
