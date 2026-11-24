"""Unit tests for the capability lease visual explainer on power-on-loan-not-owned."""

import os
import re
import unittest
import xml.etree.ElementTree as ET

SITE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARTICLE_PATH = os.path.join(SITE_DIR, "content", "blog", "power-on-loan-not-owned.html")


class TestPowerOnLoanExplainer(unittest.TestCase):
    def setUp(self):
        self.assertTrue(os.path.exists(ARTICLE_PATH), f"Missing article: {ARTICLE_PATH}")
        with open(ARTICLE_PATH, "r", encoding="utf-8") as f:
            self.content = f.read()

    def test_explainer_figure_exists(self):
        self.assertIn('<figure class="explainer" id="ex-power-lease">', self.content)
        self.assertIn("</figure>", self.content)

    def test_no_redundant_nested_prose_wrapper(self):
        # Body should not contain redundant <div class="prose wrap-narrow"> wrappers
        self.assertNotIn('<div class="prose wrap-narrow">', self.content)

    def test_svg_attributes_and_accessibility(self):
        match = re.search(r'<figure class="explainer" id="ex-power-lease">.*?(<svg[^>]*>.*?</svg>)', self.content, re.DOTALL)
        self.assertIsNotNone(match, "Could not find svg inside #ex-power-lease")
        svg_code = match.group(1)

        self.assertIn('viewBox="0 0 760 320"', svg_code)
        self.assertIn('role="img"', svg_code)
        self.assertIn('aria-labelledby="ex-power-lease-title ex-power-lease-desc"', svg_code)
        self.assertIn('<title id="ex-power-lease-title">', svg_code)
        self.assertIn('<desc id="ex-power-lease-desc">', svg_code)

    def test_mobile_svg_attributes_and_accessibility(self):
        """Mobile stacked SVG must have valid viewBox, role, and accessibility tags."""
        match = re.search(r'<figure class="explainer" id="ex-power-lease">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match)
        fig = match.group(0)

        self.assertIn('class="diagram-mobile"', fig)
        self.assertTrue('viewBox="0 0 330 560"' in fig or 'viewBox="0 0 300 560"' in fig)
        self.assertIn('aria-labelledby="ex-power-lease-m-title ex-power-lease-m-desc"', fig)
        self.assertIn('<title id="ex-power-lease-m-title">', fig)
        self.assertIn('<desc id="ex-power-lease-m-desc">', fig)

    def test_responsive_media_query_and_layout_switching(self):
        """Explainer must define responsive media queries switching between desktop and mobile SVGs."""
        self.assertIn("@media (max-width: 600px)", self.content)
        self.assertIn(".diagram-desktop", self.content)
        self.assertIn(".diagram-mobile", self.content)

    def test_svg_is_well_formed_xml(self):
        """All inline SVGs inside #ex-power-lease must be valid XML."""
        match = re.search(r'<figure class="explainer" id="ex-power-lease">.*?</figure>', self.content, re.DOTALL)
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
        """At 375px screen width (343px rendered container), the active mobile SVG text
        must compute min(font-size) * (rendered width / viewBox width) >= 11px."""
        match = re.search(r'<figure class="explainer" id="ex-power-lease">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match)
        fig = match.group(0)

        # Locate the mobile SVG
        m_match = re.search(r'<svg\b[^>]*class=["\'][^"\']*\bdiagram-mobile\b[^"\']*["\'][^>]*>(.*?)</svg>', fig, re.DOTALL)
        self.assertIsNotNone(m_match, "Could not find mobile SVG in explainer")
        mobile_svg_inner = m_match.group(0)

        # Extract viewBox width
        vb_match = re.search(r'viewBox=["\']\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*["\']', mobile_svg_inner)
        self.assertIsNotNone(vb_match, "Missing or invalid viewBox in mobile SVG")
        vb_width = float(vb_match.group(3))

        # Extract font sizes declared on text elements
        font_sizes = [float(fs) for fs in re.findall(r'font-size=["\']([0-9.]+)["\']', mobile_svg_inner)]
        self.assertTrue(len(font_sizes) > 0, "No explicit font-size attributes found in mobile SVG text elements")

        rendered_width = 343.0
        min_font_size = min(font_sizes)
        rendered_min_font = min_font_size * (rendered_width / vb_width)

        # Must render at 11px or more at 375px screen width
        self.assertGreaterEqual(
            rendered_min_font,
            11.0,
            f"Smallest mobile SVG text renders at {rendered_min_font:.2f}px in a 343px container (fails below 11px)"
        )

        # Verify that desktop SVG would fail this phone readability test if not switched
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
            f"Desktop SVG unexpectedly passed mobile threshold: {desktop_rendered_min_font:.2f}px"
        )

    def test_contrasting_sections_and_cognitive_load(self):
        match = re.search(r'<figure class="explainer" id="ex-power-lease">.*?(<svg[^>]*>.*?</svg>)', self.content, re.DOTALL)
        svg_code = match.group(1)
        root = ET.fromstring(svg_code)

        # Ensure cognitive clarity: text elements should stay under 28 nodes
        texts = root.findall(".//text")
        self.assertLessEqual(len(texts), 28, f"Too many text nodes in diagram ({len(texts)} > 28)")
        self.assertGreaterEqual(len(texts), 12, "Diagram has too few text nodes")

        # Verify key architectural comparisons
        self.assertIn("Standing service account", svg_code)
        self.assertIn("Expiring capability lease", svg_code)
        self.assertIn("Broad ambient scope", svg_code)
        self.assertIn("Task-scoped valet pass", svg_code)
        self.assertIn("Automatic sunset clock", svg_code)
        self.assertIn("Monotonic narrowing at every hop", svg_code)

    def test_figcaption_and_no_banned_tells(self):
        match = re.search(r'<figure class="explainer" id="ex-power-lease">.*?<figcaption>(.*?)</figcaption>', self.content, re.DOTALL)
        self.assertIsNotNone(match, "Missing figcaption in explainer")
        caption = match.group(1)
        self.assertNotIn("—", caption, "Found em-dash in caption")
        for tell in ["delve", "tapestry", "seamless", "crucial", "landscape", "pivotal", "foster", "testament"]:
            self.assertNotIn(tell, caption.lower(), f"Found AI tell in caption: {tell}")


if __name__ == "__main__":
    unittest.main()
