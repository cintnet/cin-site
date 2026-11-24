"""Tests for public guide readability, responsive mobile SVG explainer, and citation grounding in everyone.html."""

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE_ROOT = HERE.parent
EVERYONE_HTML = SITE_ROOT / "content" / "get-involved" / "everyone.html"


class TestEveryoneGuideReadabilityAndMobileSvg(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not EVERYONE_HTML.is_file():
            raise FileNotFoundError(f"Missing {EVERYONE_HTML}")
        cls.content = EVERYONE_HTML.read_text(encoding="utf-8")

    def test_everyone_guide_exists_and_loads(self):
        self.assertTrue(len(self.content) > 1000)
        self.assertIn("Six things one person or household can do this week", self.content)
        for idx in range(1, 7):
            self.assertIn(f"<strong>{idx}. ", self.content, f"Missing household habit #{idx} in everyone.html")

    def test_editorial_overview_and_svg_accessibility(self):
        """Explainer must provide a Spec 05 dual desktop/mobile household overview and accessible SVGs without fake bench jargon."""
        match = re.search(r'<figure class="explainer[^"]*" id="ex-everyday-checks">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match, "Missing #ex-everyday-checks explainer figure")
        fig = match.group(0)

        self.assertIn('class="diagram-desktop"', fig)
        self.assertIn('class="diagram-mobile"', fig)
        self.assertIn("1. Scoped Permissions", fig)
        self.assertIn("2. Dated Receipts", fig)
        self.assertIn("3. On-Device Privacy", fig)
        self.assertIn('viewBox="0 0 680 340"', fig)
        self.assertIn('viewBox="0 0 330 570"', fig)
        self.assertIn('role="img"', fig)
        self.assertIn('aria-labelledby="ex-everyday-checks-title ex-everyday-checks-desc"', fig)
        self.assertIn('<title id="ex-everyday-checks-title">', fig)
        self.assertIn('<desc id="ex-everyday-checks-desc">', fig)
        self.assertNotIn("LEASE TTL", fig)
        self.assertNotIn("HOUSEHOLD AGENCY BENCH", fig)
        self.assertNotIn('data-stage="bench"', fig)

    def test_svg_is_well_formed_xml(self):
        """Inline SVGs inside #ex-everyday-checks must be valid XML with < 28 text nodes each."""
        match = re.search(r'<figure class="explainer[^"]*" id="ex-everyday-checks">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match)
        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', match.group(0), re.DOTALL)
        self.assertEqual(len(svgs), 2)
        for svg_code in svgs:
            try:
                root = ET.fromstring(svg_code)
                self.assertEqual(root.tag.split("}")[-1], "svg")
            except ET.ParseError as e:
                self.fail(f"SVG is not valid XML: {e}")
            text_nodes = [el for el in root.iter() if el.tag.split("}")[-1] == "text"]
            self.assertLess(len(text_nodes), 28)

    def test_responsive_stage_css_and_svg_legibility(self):
        """Explainer CSS handles mobile stacking and dark-mode parity while text stays >= 11px."""
        match = re.search(r'<figure class="explainer[^"]*" id="ex-everyday-checks">.*?</figure>', self.content, re.DOTALL)
        fig = match.group(0)
        self.assertIn("@media (max-width: 600px)", fig)
        self.assertIn("@media (prefers-color-scheme: dark)", fig)
        self.assertIn('[data-theme="dark"]', fig)
        self.assertIn("#8FD4B6", fig)
        self.assertIn("#F09D82", fig)

        font_sizes = [float(fs) for fs in re.findall(r'font-size=["\']([0-9.]+)["\']', fig)]
        self.assertTrue(len(font_sizes) > 0)
        self.assertGreaterEqual(min(font_sizes), 11.0)

    def test_dialogue_and_memory_verification_citations_present(self):
        """Verified citations for Zheng et al. (2611.01087), Islam et al. (2609.22248), Zhu et al. (2609.05767), Chen et al. (2610.18684), and Cheng et al. (2610.02480) must be present."""
        self.assertIn("2611.01087", self.content)
        self.assertIn("2609.22248", self.content)
        self.assertIn("2609.05767", self.content)
        self.assertIn("2610.18684", self.content)
        self.assertIn("2610.02480", self.content)
        self.assertIn("Chengbo Zheng", self.content)
        self.assertIn("MD Aidul Islam", self.content)
        self.assertIn("Lichen Zhu", self.content)
        self.assertIn("Jiajun Chen", self.content)
        self.assertIn("Yu Cheng", self.content)


if __name__ == "__main__":
    unittest.main()
