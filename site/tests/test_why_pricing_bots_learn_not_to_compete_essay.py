#!/usr/bin/env python3
"""Deterministic verification suite for 'Why pricing bots learn not to compete' essay.

Verifies:
1. Essay metadata, citations, and frontmatter integrity.
2. Image asset properties (<300 KB, valid format and alt text).
3. Responsive dual-SVG explainer (#ex-pricing-loop) with role="img", <title>, and <desc>.
4. Phone-width mobile SVG boundary containment (zero overflow beyond 310px width in 330px viewBox).
5. Plain language voice rules: median sentence <= 22 words, zero > 35 words, zero em-dashes.
6. Primary sources and antitrust legal citations.
"""

from pathlib import Path
import re
import statistics
import unittest
import xml.etree.ElementTree as ET

SITE_ROOT = Path(__file__).resolve().parents[1]
BLOG_PATH = SITE_ROOT / "content" / "blog" / "why-pricing-bots-learn-not-to-compete.html"
IMAGE_PATH = SITE_ROOT / "assets" / "img" / "post-why-pricing-bots-learn-not-to-compete.jpg"


class WhyPricingBotsLearnNotToCompeteEssayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assertTrue(BLOG_PATH.exists(), f"Missing blog post: {BLOG_PATH}")
        cls.assertTrue(IMAGE_PATH.exists(), f"Missing image file: {IMAGE_PATH}")
        cls.html_text = BLOG_PATH.read_text(encoding="utf-8")

    def test_frontmatter_and_metadata(self):
        """Frontmatter must have required keys and sensible values."""
        self.assertTrue(self.html_text.startswith("---"))
        fm_match = re.match(r"^---\n(.*?)\n---", self.html_text, re.DOTALL)
        self.assertIsNotNone(fm_match, "Valid YAML frontmatter required")
        fm = fm_match.group(1)

        self.assertIn("title: Why pricing bots learn not to compete", fm)
        self.assertIn("template: article", fm)
        self.assertIn("category: Everyday", fm)
        self.assertIn("image: post-why-pricing-bots-learn-not-to-compete.jpg", fm)
        self.assertIn("takeaway:", fm)

    def test_image_asset_properties(self):
        """Image must exist, be under 300 KB, and have descriptive alt text."""
        size_kb = IMAGE_PATH.stat().st_size / 1024
        self.assertLess(size_kb, 300.0, f"Image {IMAGE_PATH.name} ({size_kb:.1f} KB) exceeds 300 KB limit")
        fm_match = re.search(r"image_alt:\s*([^\r\n]+)", self.html_text)
        self.assertIsNotNone(fm_match, "image_alt must be present")
        alt = fm_match.group(1).strip().strip("\"'")
        self.assertGreaterEqual(len(alt), 15, f"image_alt must be >= 15 chars: '{alt}'")

    def test_citations_valid(self):
        """Footnotes must reference Calvano AER 2020, Fish ACM EC '24, FTC, and DOJ."""
        self.assertIn('id="fn1"', self.html_text)
        self.assertIn('id="fn2"', self.html_text)
        self.assertIn('id="fn3"', self.html_text)
        self.assertIn('id="fn4"', self.html_text)
        self.assertIn("10.1257/aer.20190623", self.html_text)
        self.assertIn("arXiv:2404.00806", self.html_text)
        self.assertIn("ftc.gov", self.html_text)
        self.assertIn("justice.gov", self.html_text)

    def test_explainer_presence_and_structure(self):
        """Figure #ex-pricing-loop must contain both desktop and mobile SVGs with responsive CSS."""
        fig_match = re.search(r'<figure\b[^>]*\bid=["\']ex-pricing-loop["\'][^>]*>(.*?)</figure>', self.html_text, re.DOTALL)
        self.assertIsNotNone(fig_match, "Figure #ex-pricing-loop must be present")
        fig_content = fig_match.group(1)

        self.assertIn(".diagram-desktop {", fig_content)
        self.assertIn(".diagram-mobile {", fig_content)
        self.assertIn("@media (max-width: 640px)", fig_content)

        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', fig_content, re.DOTALL)
        self.assertEqual(len(svgs), 2, "Expected exactly two SVGs (desktop and mobile) inside #ex-pricing-loop")

    def test_svg_xml_and_accessibility(self):
        """Both desktop and mobile SVGs must be valid XML with role='img', title, and desc."""
        fig_match = re.search(r'<figure\b[^>]*\bid=["\']ex-pricing-loop["\'][^>]*>(.*?)</figure>', self.html_text, re.DOTALL)
        fig_content = fig_match.group(1)
        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', fig_content, re.DOTALL)

        for svg_str in svgs:
            root = ET.fromstring(svg_str)
            self.assertEqual(root.tag, "svg")
            self.assertEqual(root.attrib.get("role"), "img", "SVG missing role='img'")
            title = root.find("title")
            desc = root.find("desc")
            self.assertIsNotNone(title, "SVG missing <title>")
            self.assertIsNotNone(desc, "SVG missing <desc>")
            self.assertTrue(title.text and len(title.text.strip()) > 5)
            self.assertTrue(desc.text and len(desc.text.strip()) > 10)

    def test_mobile_svg_boundary_containment(self):
        """Mobile SVG text elements must not overflow 330px viewBox or 310px inner width."""
        fig_match = re.search(r'<figure\b[^>]*\bid=["\']ex-pricing-loop["\'][^>]*>(.*?)</figure>', self.html_text, re.DOTALL)
        fig_content = fig_match.group(1)
        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', fig_content, re.DOTALL)
        mobile_svg = svgs[1]

        root = ET.fromstring(mobile_svg)
        vb = root.attrib.get("viewBox", "")
        self.assertIn("330", vb)

        overflows = []
        for text_el in root.iter("text"):
            content = (text_el.text or "").strip()
            if not content:
                continue
            x = float(text_el.attrib.get("x", "0"))
            fs = float(text_el.attrib.get("font-size", "11"))
            anchor = text_el.attrib.get("text-anchor", "start")
            est_width = len(content) * (fs * 0.58)
            right_edge = x + (est_width / 2) if anchor == "middle" else (x if anchor == "end" else x + est_width)
            if right_edge > 310.0:
                overflows.append(f"'{content}' (len {len(content)}, right_edge={right_edge:.1f} > 310)")

        self.assertEqual(overflows, [], "Mobile SVG text elements overflow card boundaries:\n" + "\n".join(overflows))

    def test_prose_sentence_lengths_and_humanizer_invariants(self):
        """Prose must adhere to median <= 22 words, zero > 35 words, zero em-dashes."""
        body = re.sub(r"^---.*?---\s*", "", self.html_text, flags=re.DOTALL)
        clean = re.sub(r"<(style|script|figure|svg|aside|section)[^>]*>.*?</\1>", "", body, flags=re.DOTALL)
        clean_text = re.sub(r"<[^>]+>", " ", clean)

        sentences = [s.strip() for s in re.split(r"[.!?]+", clean_text) if s.strip()]
        words_per_sentence = [len(s.split()) for s in sentences if len(s.split()) > 3]

        median_len = statistics.median(words_per_sentence)
        max_len = max(words_per_sentence)

        self.assertLessEqual(median_len, 22, f"Median sentence length {median_len} > 22")
        self.assertLessEqual(max_len, 35, f"Max sentence length {max_len} > 35")
        self.assertNotIn("—", clean_text, "Found forbidden em-dash in body prose")


if __name__ == "__main__":
    unittest.main()
