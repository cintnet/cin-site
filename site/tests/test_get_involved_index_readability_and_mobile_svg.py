"""Tests for get-involved hub page readability, responsive mobile SVG explainer, and voice compliance."""

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE_ROOT = HERE.parent
INDEX_HTML = SITE_ROOT / "content" / "get-involved" / "index.html"


class TestGetInvolvedIndexReadabilityAndMobileSvg(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not INDEX_HTML.is_file():
            raise FileNotFoundError(f"Missing {INDEX_HTML}")
        cls.content = INDEX_HTML.read_text(encoding="utf-8")

    def test_get_involved_index_exists_and_loads(self):
        self.assertTrue(len(self.content) > 1000)
        self.assertIn("Find your part.", self.content)
        self.assertIn("How the five roles reinforce each other", self.content)
        self.assertIn("/get-involved/policy/", self.content)
        self.assertIn("/get-involved/researchers/", self.content)
        self.assertIn("/get-involved/labs/", self.content)
        self.assertIn("/get-involved/builders/", self.content)
        self.assertIn("/get-involved/civil-society/", self.content)
        self.assertIn("/get-involved/everyone/", self.content)

    def test_zero_card_planar_stage_and_svg_accessibility(self):
        """Explainer must provide a Spec 05 dual desktop/mobile reinforcement cycle stage with accessible SVGs."""
        match = re.search(r'<figure class="explainer" id="ex-five-roles-cycle">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match, "Missing #ex-five-roles-cycle explainer figure")
        fig = match.group(0)

        self.assertIn('class="diagram-desktop"', fig)
        self.assertIn('class="diagram-mobile"', fig)
        self.assertIn('viewBox="0 0 720 440"', fig)
        self.assertIn('viewBox="0 0 330 760"', fig)
        self.assertIn('role="img"', fig)
        self.assertIn('aria-labelledby="ex-five-roles-title ex-five-roles-desc"', fig)
        self.assertIn('<title id="ex-five-roles-title">', fig)
        self.assertIn('<desc id="ex-five-roles-desc">', fig)

    def test_svg_is_well_formed_xml(self):
        """Inline SVGs inside #ex-five-roles-cycle must be valid XML with < 28 text nodes each."""
        match = re.search(r'<figure class="explainer" id="ex-five-roles-cycle">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match)
        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', match.group(0), re.DOTALL)
        self.assertEqual(len(svgs), 2, "Expected desktop and mobile SVGs in #ex-five-roles-cycle")
        for svg_code in svgs:
            try:
                root = ET.fromstring(svg_code)
                self.assertEqual(root.tag.split("}")[-1], "svg")
            except ET.ParseError as e:
                self.fail(f"SVG is not valid XML: {e}")
            text_nodes = [el for el in root.iter() if el.tag.split("}")[-1] == "text"]
            self.assertLess(len(text_nodes), 28, "SVG must stay below 28 text nodes")

    def test_responsive_media_query_and_mobile_reflow(self):
        """Explainer CSS provides mobile <=600px stacking and dark-mode parity, with >= 11px SVG labels."""
        match = re.search(r'<figure class="explainer" id="ex-five-roles-cycle">.*?</figure>', self.content, re.DOTALL)
        fig = match.group(0)
        self.assertIn("@media (max-width: 600px)", fig)
        self.assertIn("@media (prefers-color-scheme: dark)", fig)
        self.assertIn('[data-theme="dark"]', fig)
        self.assertIn("#8FD4B6", fig)
        self.assertIn("#F09D82", fig)

        font_sizes = [float(fs) for fs in re.findall(r'font-size=["\']([0-9.]+)["\']', fig)]
        self.assertTrue(len(font_sizes) > 0, "No explicit font-size attributes found in SVG text elements")
        self.assertGreaterEqual(min(font_sizes), 11.0)

    def test_five_roles_and_cycle_content(self):
        """Verifies that all roles and the reinforcement cycle are present in the stage."""
        match = re.search(r'<figure class="explainer" id="ex-five-roles-cycle">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match)
        fig = match.group(0)

        for role_label in ["BUILDERS", "RESEARCHERS", "LAB TEAMS", "POLICY MAKERS", "CIVIL SOCIETY", "CITIZENS"]:
            self.assertIn(role_label, fig, f"Missing role label {role_label} in figure")

        self.assertIn("THE REINFORCEMENT CYCLE", fig)

    def test_voice_and_sentence_length_bounds(self):
        """Body prose must respect sentence length rules: median <= 22 words, zero > 35 words."""
        body = self.content
        if body.startswith("---"):
            _, _, body = body.split("---", 2)
        body = re.sub(r'<section\b[^>]*class=["\'][^"\']*footnotes[^"\']*["\'][^>]*>.*?</section>', '', body, flags=re.DOTALL)
        body = re.sub(r'<(aside|style|svg|figcaption).*?</\1>', '', body, flags=re.DOTALL)
        body = re.sub(r'</(h\d|p|li|div|button)>', '. ', body)
        body = re.sub(r'<[^>]+>', ' ', body)

        sentences = [s.strip() for s in re.split(r'[\.!?]\s+', body) if len(s.strip().split()) > 2]
        self.assertTrue(len(sentences) > 0)
        word_counts = [len(s.split()) for s in sentences]
        sorted_counts = sorted(word_counts)
        median_len = sorted_counts[len(sorted_counts) // 2]
        max_len = max(word_counts)

        self.assertLessEqual(median_len, 22, f"Median sentence length {median_len} exceeds 22 words")
        self.assertLessEqual(max_len, 35, f"Maximum sentence length {max_len} exceeds 35 words")


if __name__ == "__main__":
    unittest.main()
