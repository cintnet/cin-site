#!/usr/bin/env python3
"""Deterministic verification test for the responsive protective skin explainer in
an-assistant-that-works-only-for-you.html.
"""

from pathlib import Path
import re
import statistics
import unittest
import xml.etree.ElementTree as ET

SITE_ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = SITE_ROOT / "content"
IMG_DIR = SITE_ROOT / "assets" / "img"


class AssistantWorksOnlyForYouExplainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html_path = CONTENT_DIR / "blog" / "an-assistant-that-works-only-for-you.html"
        cls.assertTrue(cls.html_path.exists(), f"Missing {cls.html_path}")
        cls.html_text = cls.html_path.read_text(encoding="utf-8")

    def test_image_and_frontmatter_invariants(self):
        """Header image exists, is under 300 KB, and has descriptive alt text."""
        fm_match = re.search(r"image:\s*([^\r\n]+)", self.html_text)
        self.assertIsNotNone(fm_match, "image must be present in frontmatter")
        img_name = fm_match.group(1).strip().strip("\"'")
        img_file = IMG_DIR / img_name
        self.assertTrue(img_file.exists(), f"Missing image file: {img_file}")
        sz = img_file.stat().st_size
        self.assertLessEqual(sz, 300 * 1024, f"Image size ({sz / 1024:.1f} KB) exceeds 300 KB limit")

        alt_match = re.search(r"image_alt:\s*([^\r\n]+)", self.html_text)
        self.assertIsNotNone(alt_match, "image_alt must be present")
        alt = alt_match.group(1).strip().strip("\"'")
        self.assertGreaterEqual(len(alt), 15, f"image_alt must be >= 15 chars: '{alt}'")

    def test_citations_valid(self):
        """Footnotes must reference Ross 1973, Margulis 1967, Friston 2013, Bagdasarian 2024, Hadfield-Menell 2017, Clark & Chalmers 1998, Tulving 2002, Balkin 2016, Bach 2012."""
        for fn_id in ("fn1", "fn2", "fn3", "fn4", "fn5", "fn6", "fn7"):
            self.assertIn(f'id="{fn_id}"', self.html_text)
        self.assertIn("1817064", self.html_text)
        self.assertIn("10.1016/0022-5193(67)90079-3", self.html_text)
        self.assertIn("10.1098/rsif.2013.0475", self.html_text)
        self.assertIn("2405.05175", self.html_text)
        self.assertIn("1611.08219", self.html_text)
        self.assertIn("10.1093/analys/58.1.7", self.html_text)
        self.assertIn("10.1146/annurev.psych.53.100901.135114", self.html_text)
        self.assertIn("Information Fiduciaries and the First Amendment", self.html_text)
        self.assertIn("10.1007/978-3-642-35506-6_2", self.html_text)

    def test_no_legacy_coined_labels_or_callout_boxes(self):
        """Researcher box and prose must not contain legacy coined internal labels or callout wrappers."""
        for legacy in ("Embodied Markov-Blanket Sensorium", "Mutualistic Neuro-Symbiont", "Isomorphic Predictive Co-Inference"):
            self.assertNotIn(legacy, self.html_text)
        self.assertNotIn('<div class="callout">', self.html_text)

    def test_explainer_presence_and_structure(self):
        """Figure #ex-skin-not-glass must contain both desktop and mobile SVGs with responsive and dark-mode CSS."""
        fig_match = re.search(r'<figure\b[^>]*\bid=["\']ex-skin-not-glass["\'][^>]*>(.*?)</figure>', self.html_text, re.DOTALL)
        self.assertIsNotNone(fig_match, "Figure #ex-skin-not-glass must be present")
        fig_content = fig_match.group(1)

        self.assertIn(".diagram-desktop {", fig_content)
        self.assertIn(".diagram-mobile {", fig_content)
        self.assertIn("@media (max-width: 640px)", fig_content)
        self.assertIn("@media (prefers-color-scheme: dark)", fig_content)

        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', fig_content, re.DOTALL)
        self.assertEqual(len(svgs), 2, "Expected exactly two SVGs (desktop and mobile) inside #ex-skin-not-glass")
        for svg_str in svgs:
            for fs in re.findall(r'font-size=["\']([0-9.]+)["\']', svg_str):
                self.assertGreaterEqual(float(fs), 11.0, f"Found SVG font-size={fs} < 11px in #ex-skin-not-glass")

    def test_svg_xml_and_accessibility(self):
        """Both desktop and mobile SVGs must be valid XML with role='img', title, and desc."""
        fig_match = re.search(r'<figure\b[^>]*\bid=["\']ex-skin-not-glass["\'][^>]*>(.*?)</figure>', self.html_text, re.DOTALL)
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
        fig_match = re.search(r'<figure\b[^>]*\bid=["\']ex-skin-not-glass["\'][^>]*>(.*?)</figure>', self.html_text, re.DOTALL)
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
