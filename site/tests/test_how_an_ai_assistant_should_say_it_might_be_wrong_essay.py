#!/usr/bin/env python3
"""Unit tests verifying metadata, responsive SVGs, mobile legibility, citations, and voice rules
for how-an-ai-assistant-should-say-it-might-be-wrong.html.
"""

from pathlib import Path
import re
import statistics
import sys
import unittest
import xml.etree.ElementTree as ET

SITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE_ROOT))

BLOG_FILE = SITE_ROOT / "content" / "blog" / "how-an-ai-assistant-should-say-it-might-be-wrong.html"


class HowAnAiAssistantShouldSayItMightBeWrongEssayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assertTrue(BLOG_FILE.exists(), f"Essay file must exist at {BLOG_FILE}")
        cls.content = BLOG_FILE.read_text(encoding="utf-8")
        parts = cls.content.split("---\n", 2)
        cls.fm_text = parts[1] if len(parts) >= 3 else ""
        cls.body = parts[2] if len(parts) >= 3 else cls.content

    def test_frontmatter_metadata(self):
        self.assertIn("title: How an AI assistant should tell you when it might be wrong", self.fm_text)
        self.assertIn("template: article", self.fm_text)
        self.assertIn("category: Seeing", self.fm_text)
        self.assertIn("image: post-how-an-ai-assistant-should-say-it-might-be-wrong.jpg", self.fm_text)
        self.assertIn("reader:", self.fm_text)
        self.assertIn("takeaway:", self.fm_text)
        self.assertIn("lede:", self.fm_text)
        self.assertNotIn("isn't honesty", self.fm_text)

    def test_illustration_vignette_spec(self):
        img_match = re.search(r"image:\s*([^\n]+)", self.fm_text)
        self.assertIsNotNone(img_match, "Image field missing in frontmatter")
        img_name = img_match.group(1).strip()
        img_path = SITE_ROOT / "assets" / "img" / img_name
        self.assertTrue(img_path.exists(), f"Vignette image must exist at {img_path}")
        size = img_path.stat().st_size
        self.assertLess(size, 300000, f"Image size ({size} bytes) must be under 300 KB")

    def test_citations_present(self):
        """Must cite Brier (1950), Bach (2012), and recent calibration and sycophancy studies."""
        citations = [
            "1520-0493",
            "2401.06730",
            "2502.08177",
            "2310.13548",
            "2207.05221",
            "2608.26511",
            "10.1007/978-3-642-35506-6_2",
        ]
        for c in citations:
            self.assertIn(c, self.content, f"Missing citation {c}")
        self.assertIn("@media (prefers-color-scheme: dark)", self.content)
        self.assertNotIn('<div class="callout">', self.content)

    def test_shared_horizon_integration(self):
        self.assertIn("/labs/shared-horizon/", self.content)
        self.assertIn("calibrating anti-sycophancy training", self.content)

    def test_svg_explainer_dual_structure_and_accessibility(self):
        match = re.search(
            r'<figure\b[^>]*\bid=["\']ex-honest-uncertainty["\'][^>]*>(.*?)</figure>',
            self.content,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "Figure #ex-honest-uncertainty not found")
        fig_content = match.group(1)

        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', fig_content, re.DOTALL)
        self.assertEqual(len(svgs), 2, "Expected desktop and mobile SVGs in #ex-honest-uncertainty")

        # Desktop SVG
        root_desk = ET.fromstring(svgs[0])
        self.assertEqual(root_desk.attrib.get("role"), "group")
        self.assertIn("diagram-desktop", root_desk.attrib.get("class", ""))
        self.assertIsNotNone(root_desk.find("title"))
        self.assertIsNotNone(root_desk.find("desc"))

        # Mobile SVG
        root_mob = ET.fromstring(svgs[1])
        self.assertEqual(root_mob.attrib.get("role"), "img")
        self.assertIn("diagram-mobile", root_mob.attrib.get("class", ""))
        self.assertIsNotNone(root_mob.find("title"))
        self.assertIsNotNone(root_mob.find("desc"))

        # Mobile font legibility & boundary containment
        viewbox = root_mob.attrib.get("viewBox", "0 0 330 640")
        vb_w = float(viewbox.split()[2])
        self.assertLessEqual(vb_w, 330.0, "Mobile viewBox width must be <= 330")
        scale = 343.0 / vb_w

        for elem in root_mob.iter():
            if elem.tag.endswith("text"):
                font_size_str = elem.attrib.get("font-size", "11")
                font_size = float(font_size_str)
                computed_px = font_size * scale
                self.assertGreaterEqual(
                    computed_px,
                    11.0,
                    f"Text '{elem.text}' font size {computed_px:.1f}px below 11px on 343px mobile screen",
                )

                content = (elem.text or "").strip()
                if content:
                    x = float(elem.attrib.get("x", "0"))
                    anchor = elem.attrib.get("text-anchor", "start")
                    est_w = len(content) * (font_size * 0.58)
                    right = x + (est_w / 2) if anchor == "middle" else (x if anchor == "end" else x + est_w)
                    self.assertLessEqual(
                        right,
                        310.0,
                        f"Text '{content}' right edge ({right:.1f}px) overflows 310px card boundary",
                    )

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
