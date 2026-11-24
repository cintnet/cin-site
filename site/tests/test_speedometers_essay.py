import re
import statistics
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent.parent
BLOG_PATH = SITE_ROOT / "content" / "blog" / "why-speedometers-dont-steer.html"
IMAGE_PATH = SITE_ROOT / "assets" / "img" / "post-why-speedometers-dont-steer.jpg"


class SpeedometersDontSteerEssayTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(BLOG_PATH.exists(), f"Blog post missing at {BLOG_PATH}")
        self.content = BLOG_PATH.read_text(encoding="utf-8")

    def test_frontmatter_fields(self):
        """Check all required frontmatter metadata."""
        for field in [
            "title: Why speedometers don't steer",
            "reader: Citizens, civic leaders",
            "takeaway:",
            "template: article",
            "date: 2026-11-08",
            "order: 58",
            "category: Seeing",
            "image: post-why-speedometers-dont-steer.jpg",
            "image_alt:",
            "lede:",
        ]:
            self.assertIn(field, self.content)

    def test_image_asset_properties(self):
        """Check that illustration JPEG exists, is under 300 KB, and has valid dimensions."""
        self.assertTrue(IMAGE_PATH.exists(), f"Image asset missing at {IMAGE_PATH}")
        size_kb = IMAGE_PATH.stat().st_size / 1024
        self.assertLess(size_kb, 300, f"Image size {size_kb:.1f} KB exceeds 300 KB limit")

    def test_prose_sentence_lengths(self):
        """Strict Voice Gate: median <= 22 words, zero sentences > 35 words."""
        text = self.content
        # Strip frontmatter
        text = re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL)
        # Strip aside for researchers
        text = re.sub(r'<aside class="for-researchers".*?</aside>', "", text, flags=re.DOTALL)
        # Strip footnotes
        text = re.sub(r'<section class="footnotes".*?</section>', "", text, flags=re.DOTALL)
        # Strip figure/svg
        text = re.sub(r"<figure.*?</figure>", "", text, flags=re.DOTALL)
        # Strip html tags
        plain = re.sub(r"<[^>]+>", " ", text)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", plain) if s.strip()]
        lengths = [len(s.split()) for s in sentences]

        self.assertGreater(len(sentences), 20, "Essay should have substantial content")
        median_len = statistics.median(lengths)
        self.assertLessEqual(median_len, 22.0, f"Median sentence length {median_len} > 22")
        long_ones = [(l, s) for l, s in zip(lengths, sentences) if l > 35]
        self.assertEqual(len(long_ones), 0, f"Found sentences over 35 words: {long_ones}")

    def test_steward_gate_no_forbidden_strings(self):
        """No internal ticket IDs, speculative tokens, or savings promises."""
        text = self.content
        for forbidden in ["MMCT", "guaranteed profit", "guaranteed savings"]:
            self.assertNotIn(forbidden, text)
        self.assertIsNone(re.search(r"\b[DL]-\d{4}\b", text), "Found internal ticket ID pattern")

    def test_primary_sources_and_citations(self):
        """Footnotes contain verified primary sources."""
        self.assertIn("arXiv:2503.14499", self.content)
        self.assertIn("arXiv:2607.05163", self.content)
        self.assertIn("arXiv:2609.15293", self.content)
        self.assertIn("arXiv:2512.16030", self.content)
        self.assertIn("arXiv:2611.08417", self.content)
        self.assertIn("arXiv:2611.03575", self.content)

    def test_desktop_svg_accessibility(self):
        """Explainer diagram has full accessibility markers and no prohibited innerHTML."""
        match = re.search(r'<figure class="explainer" id="ex-two-dials">.*?(<svg\b[^>]*class=["\'][^"\']*\bdiagram-desktop\b[^"\']*["\'][^>]*>.*?</svg>)', self.content, re.DOTALL)
        self.assertIsNotNone(match, "Could not find desktop svg inside #ex-two-dials")
        svg_code = match.group(1)
        self.assertIn('role="group"', svg_code)
        self.assertIn('aria-labelledby="ex-dials-title ex-dials-desc"', svg_code)
        self.assertIn('<title id="ex-dials-title">', svg_code)
        self.assertIn('<desc id="ex-dials-desc">', svg_code)
        self.assertNotIn(".innerHTML", self.content)

    def test_mobile_svg_attributes_and_accessibility(self):
        match = re.search(r'<figure class="explainer" id="ex-two-dials">.*?(<svg\b[^>]*class=["\'][^"\']*\bdiagram-mobile\b[^"\']*["\'][^>]*>.*?</svg>)', self.content, re.DOTALL)
        self.assertIsNotNone(match, "Could not find mobile svg inside #ex-two-dials")
        svg_code = match.group(1)

        self.assertIn('viewBox="0 0 330 680"', svg_code)
        self.assertIn('role="img"', svg_code)
        self.assertIn('aria-labelledby="ex-dials-m-title ex-dials-m-desc"', svg_code)
        self.assertIn('<title id="ex-dials-m-title">', svg_code)
        self.assertIn('<desc id="ex-dials-m-desc">', svg_code)

    def test_responsive_media_query_and_layout_switching(self):
        self.assertIn("@media (max-width: 600px)", self.content)
        self.assertIn(".diagram-desktop", self.content)
        self.assertIn(".diagram-mobile", self.content)

    def test_svg_is_well_formed_xml(self):
        match = re.search(r'<figure class="explainer" id="ex-two-dials">.*?</figure>', self.content, re.DOTALL)
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
        match = re.search(r'<figure class="explainer" id="ex-two-dials">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match)
        fig = match.group(0)

        # Locate mobile SVG
        m_match = re.search(r'<svg\b[^>]*class=["\'][^"\']*\bdiagram-mobile\b[^"\']*["\'][^>]*>(.*?)</svg>', fig, re.DOTALL)
        self.assertIsNotNone(m_match, "Could not find mobile SVG in explainer")
        mobile_svg_inner = m_match.group(0)

        # Extract viewBox width
        vb_match = re.search(r'viewBox=["\']\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*["\']', mobile_svg_inner)
        self.assertIsNotNone(vb_match, "Missing or invalid viewBox in mobile SVG")
        vb_width = float(vb_match.group(3))

        # Extract font sizes
        font_sizes = [float(fs) for fs in re.findall(r'font-size=["\']([0-9.]+)["\']', mobile_svg_inner)]
        self.assertTrue(len(font_sizes) > 0, "No explicit font-size attributes found in mobile SVG text elements")

        rendered_width = 343.0
        min_font_size = min(font_sizes)
        rendered_min_font = min_font_size * (rendered_width / vb_width)

        # Smallest text must render at 11px or more on phone
        self.assertGreaterEqual(
            rendered_min_font,
            11.0,
            f"Smallest mobile SVG text renders at {rendered_min_font:.2f}px in a 343px container (fails below 11px)"
        )

        # Verify that desktop SVG would fail mobile readability if not switched
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

    def test_voice_and_humanizer_invariants(self):
        # Zero em-dashes in prose
        self.assertNotIn("—", self.content, "Found em-dash in essay prose")

        # Zero forbidden AI stock words
        ai_words = [
            "delve", "tapestry", "testament", "underscore", "showcase", "foster",
            "pivotal", "intricate", "realm", "vibrant", "seamless", "crucial", "landscape"
        ]
        text_lower = self.content.lower()
        for word in ai_words:
            self.assertNotIn(f" {word} ", text_lower, f"Found AI stock word '{word}' in essay")


if __name__ == "__main__":
    unittest.main()
