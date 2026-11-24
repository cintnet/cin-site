"""Tests for AI labs guide readability, analogies, responsive mobile safeguards explainer, and accessibility in labs.html."""

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE_ROOT = HERE.parent
LABS_HTML = SITE_ROOT / "content" / "get-involved" / "labs.html"


class TestLabsGuideSafeguardsDiagram(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not LABS_HTML.is_file():
            raise FileNotFoundError(f"Missing {LABS_HTML}")
        cls.content = LABS_HTML.read_text(encoding="utf-8")

    def test_labs_guide_exists_and_loads(self):
        self.assertTrue(len(self.content) > 1000)
        self.assertIn("For people at AI labs", self.content)
        self.assertIn("Six practical steps a lab team can ship now", self.content)
        self.assertIn("How your organisation is evaluated in Shared Horizon", self.content)
        self.assertIn("What we can offer your team", self.content)

    def test_analogy_paragraphs_preserved(self):
        """All core grounding analogies must remain present in the guide."""
        self.assertIn("In the early days of aviation, every aircraft maker built its own cockpit gauges", self.content)
        self.assertIn("When every ship paints the same load line on its hull", self.content)
        self.assertIn("Put a licence plate and a receipt on every outward agent action", self.content)
        self.assertIn("Treat incoming text like mail arriving at a quarantine desk", self.content)
        self.assertIn("Like a country doctor who orders a lab swab before prescribing", self.content)
        self.assertIn("every kitchen smells its own cooking differently than a health inspector does", self.content)
        self.assertIn("like taking your own medical chart when you change clinics", self.content)

    def test_matrix_stage_and_svg_accessibility(self):
        """Explainer must provide a Spec 05 dual desktop/mobile stage with accessible schematic SVGs."""
        match = re.search(r'<figure class="explainer" id="ex-lab-safeguards">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match, "Missing #ex-lab-safeguards explainer figure")
        fig = match.group(0)

        self.assertIn('class="diagram-desktop"', fig)
        self.assertIn('class="diagram-mobile"', fig)
        self.assertIn('viewBox="0 0 720 440"', fig)
        self.assertIn('viewBox="0 0 330 830"', fig)
        self.assertIn('role="img"', fig)
        self.assertIn('aria-labelledby="ex-lab-safeguards-title ex-lab-safeguards-desc"', fig)
        self.assertIn('<title id="ex-lab-safeguards-title">', fig)
        self.assertIn('<desc id="ex-lab-safeguards-desc">', fig)

    def test_no_inline_style_attributes_inside_figure(self):
        """No style='...' attributes may appear inside the figure."""
        match = re.search(r'<figure class="explainer" id="ex-lab-safeguards">(.*?)</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match)
        fig_inner = match.group(1)

        fig_without_style_tag = re.sub(r'<style>.*?</style>', '', fig_inner, flags=re.DOTALL)
        inline_styles = re.findall(r'\bstyle\s*=\s*["\'][^"\']*["\']', fig_without_style_tag, re.IGNORECASE)
        self.assertEqual(inline_styles, [], f"Found inline style attributes in figure: {inline_styles}")

    def test_no_forbidden_jargon_in_figure(self):
        """Diagram must use plain language and avoid internal buzzwords and overclaiming words."""
        match = re.search(r'<figure class="explainer" id="ex-lab-safeguards">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match)
        fig = match.group(0)

        forbidden = [
            "epistemic",
            "control-data separation",
            "attested",
            "zero ambient",
            "guarantee",
            "prevent",
            "tamper-proof",
        ]
        for word in forbidden:
            self.assertNotIn(word.lower(), fig.lower(), f"Forbidden word '{word}' found in #ex-lab-safeguards")

    def test_svg_is_well_formed_xml(self):
        """Inline SVGs inside #ex-lab-safeguards must be valid XML with < 28 text nodes each."""
        match = re.search(r'<figure class="explainer" id="ex-lab-safeguards">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match)
        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', match.group(0), re.DOTALL)
        self.assertEqual(len(svgs), 2, "Expected desktop and mobile SVGs in #ex-lab-safeguards")
        for svg_code in svgs:
            try:
                root = ET.fromstring(svg_code)
                self.assertTrue(root.tag.endswith("svg"))
            except ET.ParseError as e:
                self.fail(f"SVG is not valid XML: {e}")
            text_nodes = [el for el in root.iter() if el.tag.split("}")[-1] == "text"]
            self.assertLess(len(text_nodes), 28)

    def test_responsive_stage_css_and_svg_legibility(self):
        """Explainer CSS handles mobile stacking and dark-mode parity while schematic text stays >= 11px."""
        match = re.search(r'<figure class="explainer" id="ex-lab-safeguards">.*?</figure>', self.content, re.DOTALL)
        fig = match.group(0)
        self.assertIn("@media (max-width: 600px)", fig)
        self.assertIn("@media (prefers-color-scheme: dark)", fig)
        self.assertIn('[data-theme="dark"]', fig)
        self.assertIn("#8FD4B6", fig)
        self.assertIn("#F09D82", fig)

        font_sizes = [float(fs) for fs in re.findall(r'font-size=["\']([0-9.]+)["\']', fig)]
        self.assertTrue(len(font_sizes) > 0)
        self.assertGreaterEqual(min(font_sizes), 11.0)

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
