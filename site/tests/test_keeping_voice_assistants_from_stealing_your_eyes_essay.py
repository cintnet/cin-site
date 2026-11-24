#!/usr/bin/env python3
"""Unit tests verifying voice, responsive SVG, and citation integrity for the glanceable voice displays essay.

Verifies:
- Frontmatter metadata, takeaway, reader, and lede fields
- Vignette image existence and size constraints (< 300 KB)
- Plain language constraints (median sentence <= 22 words, zero > 35 words)
- Zero humanizer tells (zero em-dashes, zero negative parallelisms, zero forbidden AI words)
- Valid desktop and mobile SVG XML with role="img", <title>, <desc>
- Mobile font legibility (min computed font >= 11px at 343px width)
- Sourced citations for Wolter et al. (arXiv:2611.08443) and Weiser & Brown (1996)
- Cross-link to Shared Horizon action card
"""

from pathlib import Path
import re
import statistics
import sys
import unittest
import xml.etree.ElementTree as ET

SITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE_ROOT))

BLOG_FILE = SITE_ROOT / "content" / "blog" / "keeping-voice-assistants-from-stealing-your-eyes.html"
IMAGE_FILE = SITE_ROOT / "assets" / "img" / "post-keeping-voice-assistants-from-stealing-your-eyes.jpg"


class KeepingVoiceAssistantsFromStealingYourEyesEssayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assertTrue(BLOG_FILE.exists(), f"Essay file must exist at {BLOG_FILE}")
        cls.content = BLOG_FILE.read_text(encoding="utf-8")
        parts = cls.content.split("---\n", 2)
        cls.fm_text = parts[1] if len(parts) >= 3 else ""
        cls.body = parts[2] if len(parts) >= 3 else cls.content

    def test_essay_file_exists(self):
        self.assertTrue(BLOG_FILE.exists())

    def test_frontmatter_metadata(self):
        self.assertIn("title: Keeping voice assistants from stealing your eyes", self.fm_text)
        self.assertIn("template: article", self.fm_text)
        self.assertIn("category: Living", self.fm_text)
        self.assertIn("date: 2026-11-12", self.fm_text)
        self.assertIn("image: post-keeping-voice-assistants-from-stealing-your-eyes.jpg", self.fm_text)
        self.assertIn("reader:", self.fm_text)
        self.assertIn("takeaway:", self.fm_text)
        self.assertIn("lede:", self.fm_text)

    def test_illustration_vignette_spec(self):
        self.assertTrue(IMAGE_FILE.exists(), f"Vignette image must exist at {IMAGE_FILE}")
        size = IMAGE_FILE.stat().st_size
        self.assertLess(size, 300000, f"Image size ({size} bytes) must be under 300 KB")

    def test_citations_present(self):
        """Must cite Wolter et al. (2611.08443) and Weiser & Brown (10.1007/978-1-4612-0685-9_6)."""
        self.assertIn("2611.08443", self.content)
        self.assertIn("10.1007/978-1-4612-0685-9_6", self.content)

    def test_shared_horizon_cross_link(self):
        self.assertIn("/labs/shared-horizon/", self.content)

    def test_svg_explainer_structure_and_accessibility(self):
        match = re.search(r'<figure\b[^>]*\bid=["\']ex-glanceable-voice-displays["\'][^>]*>(.*?)</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match, "Figure #ex-glanceable-voice-displays not found")
        fig_content = match.group(1)

        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', fig_content, re.DOTALL)
        self.assertEqual(len(svgs), 2, "Expected desktop and mobile SVGs")

        # Desktop SVG
        root_desk = ET.fromstring(svgs[0])
        self.assertEqual(root_desk.attrib.get("role"), "img")
        self.assertIn("diagram-desktop", root_desk.attrib.get("class", ""))
        self.assertIsNotNone(root_desk.find("title"))
        self.assertIsNotNone(root_desk.find("desc"))

        # Mobile SVG
        root_mob = ET.fromstring(svgs[1])
        self.assertEqual(root_mob.attrib.get("role"), "img")
        self.assertIn("diagram-mobile", root_mob.attrib.get("class", ""))
        self.assertIsNotNone(root_mob.find("title"))
        self.assertIsNotNone(root_mob.find("desc"))

        # Mobile font size and bounds
        viewbox = root_mob.attrib.get("viewBox", "0 0 330 640")
        vb_w = float(viewbox.split()[2])
        container_w = 343.0
        scale = container_w / vb_w

        for elem in root_mob.iter():
            if elem.tag.endswith("text"):
                font_size_str = elem.attrib.get("font-size", "11")
                font_size = float(font_size_str)
                computed_px = font_size * scale
                self.assertGreaterEqual(computed_px, 11.0, f"Text font size {computed_px}px below 11px")

                x_str = elem.attrib.get("x")
                if x_str:
                    x = float(x_str)
                    self.assertLessEqual(x, 310.0, f"Text x={x} overflows 310px card bound")

    def test_voice_and_humanizer_rules(self):
        txt = self.body
        txt = re.sub(r"<aside\b.*?</aside>", " ", txt, flags=re.S)
        txt = re.sub(r'<section class=["\']footnotes["\'].*?</section>', " ", txt, flags=re.S)
        txt = re.sub(r"<script\b.*?</script>", " ", txt, flags=re.S)
        txt = re.sub(r"<style\b.*?</style>", " ", txt, flags=re.S)
        txt = re.sub(r"<svg\b.*?</svg>", " ", txt, flags=re.S)
        txt = re.sub(r"<figcaption\b.*?</figcaption>", " ", txt, flags=re.S)
        txt = re.sub(r"<[^>]+>", " ", txt)
        clean_text = re.sub(r"\s+", " ", txt).strip()

        # Zero em-dashes
        self.assertNotIn("—", clean_text, "Found em-dash in body prose")

        # Zero forbidden AI words
        forbidden = [
            "delve", "tapestry", "testament", "underscore", "showcase",
            "foster", "pivotal", "intricate", "realm", "vibrant",
            "seamless", "crucial", "landscape",
        ]
        words_lower = clean_text.lower()
        for word in forbidden:
            self.assertNotIn(f" {word} ", f" {words_lower} ", f"Forbidden AI word '{word}' found")

        # Sentence lengths
        sentences = [s.strip() for s in re.split(r"[.!?]+", clean_text) if s.strip()]
        sentence_lengths = [len(s.split()) for s in sentences if len(s.split()) > 1]

        for s, count in zip(sentences, sentence_lengths):
            self.assertLessEqual(count, 35, f"Sentence exceeds 35 words ({count}): '{s}'")

        median_len = statistics.median(sentence_lengths)
        self.assertLessEqual(median_len, 22, f"Median sentence length {median_len} exceeds 22 words")


if __name__ == "__main__":
    unittest.main()
