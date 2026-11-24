"""Tests for researchers guide readability, responsive mobile SVG explainer, and citation grounding in researchers.html."""

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE_ROOT = HERE.parent
RESEARCHERS_HTML = SITE_ROOT / "content" / "get-involved" / "researchers.html"


class TestResearchersGuideReadabilityAndMobileSvg(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not RESEARCHERS_HTML.is_file():
            raise FileNotFoundError(f"Missing {RESEARCHERS_HTML}")
        cls.content = RESEARCHERS_HTML.read_text(encoding="utf-8")

    def test_researchers_guide_exists_and_loads(self):
        self.assertTrue(len(self.content) > 1000)
        self.assertIn("For researchers", self.content)
        self.assertIn("Seven open problems where help matters most", self.content)
        self.assertIn("Four ways to stress-test our designs", self.content)

    def test_matrix_stage_and_svg_accessibility(self):
        """Explainer must provide a Spec 05 dual desktop/mobile stage with accessible schematic SVGs."""
        match = re.search(r'<figure class="explainer" id="ex-research-agenda">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match, "Missing #ex-research-agenda explainer figure")
        fig = match.group(0)

        self.assertIn('class="diagram-desktop"', fig)
        self.assertIn('class="diagram-mobile"', fig)
        self.assertIn('viewBox="0 0 720 280"', fig)
        self.assertIn('viewBox="0 0 330 650"', fig)
        self.assertIn('role="img"', fig)
        self.assertIn('aria-labelledby="ex-research-title ex-research-desc"', fig)
        self.assertIn('<title id="ex-research-title">', fig)
        self.assertIn('<desc id="ex-research-desc">', fig)

    def test_svg_is_well_formed_xml(self):
        """Inline SVGs inside #ex-research-agenda must be valid XML with < 28 text nodes each."""
        match = re.search(r'<figure class="explainer" id="ex-research-agenda">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match)
        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', match.group(0), re.DOTALL)
        self.assertEqual(len(svgs), 2, "Expected desktop and mobile SVGs in #ex-research-agenda")
        for svg_code in svgs:
            try:
                root = ET.fromstring(svg_code)
                self.assertEqual(root.tag.split("}")[-1], "svg")
            except ET.ParseError as e:
                self.fail(f"SVG is not valid XML: {e}")
            text_nodes = [el for el in root.iter() if el.tag.split("}")[-1] == "text"]
            self.assertLess(len(text_nodes), 28)

    def test_responsive_stage_css_and_svg_legibility(self):
        """Explainer CSS handles mobile stacking and dark-mode parity while schematic text stays >= 11px."""
        match = re.search(r'<figure class="explainer" id="ex-research-agenda">.*?</figure>', self.content, re.DOTALL)
        fig = match.group(0)
        self.assertIn("@media (max-width: 600px)", fig)
        self.assertIn("@media (prefers-color-scheme: dark)", fig)
        self.assertIn('[data-theme="dark"]', fig)
        self.assertIn("#8FD4B6", fig)
        self.assertIn("#F09D82", fig)

        font_sizes = [float(fs) for fs in re.findall(r'font-size=["\']([0-9.]+)["\']', fig)]
        self.assertTrue(len(font_sizes) > 0)
        self.assertGreaterEqual(min(font_sizes), 11.0)

    def test_citations_and_researcher_grounding(self):
        """Primary sources and open problems must be properly referenced."""
        self.assertIn("draft-cin-agent-network-00", self.content)
        self.assertIn("Shared Horizon", self.content)
        self.assertIn("Observatory", self.content)

    def test_voice_and_sentence_length_bounds(self):
        """Body prose must respect sentence length rules: median <= 22 words, zero > 35 words."""
        body = self.content
        if body.startswith("---"):
            _, _, body = body.split("---", 2)
        body = re.sub(r'<(aside|section|style|svg|figcaption).*?</\1>', '', body, flags=re.DOTALL)
        body = re.sub(r'</(h\d|p|li|ol|ul|div|button)>', '. ', body)
        body = re.sub(r'<[^>]+>', ' ', body)

        sentences = [s.strip() for s in re.split(r'[\.!?]\s+', body) if len(s.strip()) > 3]
        self.assertTrue(len(sentences) > 0)
        word_counts = [len(s.split()) for s in sentences]
        sorted_counts = sorted(word_counts)
        median_len = sorted_counts[len(sorted_counts) // 2]
        max_len = max(word_counts)

        self.assertLessEqual(median_len, 22, f"Median sentence length {median_len} exceeds 22 words")
        self.assertLessEqual(max_len, 35, f"Maximum sentence length {max_len} exceeds 35 words")


if __name__ == "__main__":
    unittest.main()
