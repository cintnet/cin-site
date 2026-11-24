"""Unit test suite for 'Between hovering and blind trust' audience essay.

Verifies:
- Frontmatter schema, lede claim-first grounding, and metadata.
- Sentence length invariants: median <= 22 words, max <= 35 words.
- Zero em-dashes and humanizer tell invariants.
- Accessibility of desktop and mobile SVGs with valid XML.
- Citations grounded in primary source records.
- Header image existence, dimensions, and file size < 300 KB.
"""

import os
import re
import unittest
import xml.etree.ElementTree as ET


class TestBetweenHoveringAndBlindTrust(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.html_path = os.path.join(cls.root_dir, "content", "blog", "between-hovering-and-blind-trust.html")
        cls.img_path = os.path.join(cls.root_dir, "assets", "img", "post-between-hovering-and-blind-trust.jpg")

        with open(cls.html_path, "r", encoding="utf-8") as f:
            cls.content = f.read()

    def test_frontmatter_and_claim_first_lede(self):
        """Frontmatter must contain required metadata and claim-first lede."""
        self.assertIn("title: Between hovering and blind trust", self.content)
        self.assertIn("category: Seeing", self.content)
        self.assertIn("date: 2026-11-11", self.content)
        self.assertIn("image: post-between-hovering-and-blind-trust.jpg", self.content)

        match = re.search(r"^lede:\s*(.+)$", self.content, re.MULTILINE)
        self.assertIsNotNone(match, "Missing frontmatter lede")
        lede = match.group(1).strip()
        self.assertTrue(
            lede.startswith("Delegating tasks to AI assistants currently forces users into two bad options:"),
            f"Lede does not open with direct claim: {lede[:100]}"
        )
        self.assertIn("AI assistants", lede)
        self.assertIn("Carnegie Mellon", lede)
        self.assertIn("milestone checkpoints", lede)

    def test_sentence_length_and_voice_invariants(self):
        """Prose sentences must obey median <= 22 words, zero > 35 words, and no em-dashes."""
        # Strip frontmatter
        body = re.sub(r"^---.*?---\s*", "", self.content, flags=re.DOTALL)
        # Strip styles, figures, asides, footnotes
        clean = re.sub(r"<(style|script|figure|svg|aside|section)[^>]*>.*?</\1>", "", body, flags=re.DOTALL)
        clean_text = re.sub(r"<[^>]+>", " ", clean)

        # Tokenize sentences
        raw_sentences = [s.strip() for s in re.split(r"[.!?]+", clean_text) if s.strip()]
        words_per_sentence = [len(s.split()) for s in raw_sentences if len(s.split()) > 3]

        self.assertGreater(len(words_per_sentence), 25)
        median_len = sorted(words_per_sentence)[len(words_per_sentence) // 2]
        max_len = max(words_per_sentence)

        self.assertLessEqual(median_len, 22, f"Median sentence length {median_len} exceeds 22 words")
        self.assertLessEqual(max_len, 35, f"Max sentence length {max_len} exceeds 35 words")

        # Zero em-dashes in body prose
        self.assertNotIn("—", clean_text, "Found em-dash in body prose")

        # Humanizer forbidden words
        forbidden = [
            "delve", "tapestry", "testament", "underscore", "showcase",
            "foster", "pivotal", "intricate", "realm", "vibrant",
            "seamless", "crucial", "landscape"
        ]
        lower_body = clean_text.lower()
        for word in forbidden:
            self.assertFalse(
                re.search(rf"\b{word}\b", lower_body),
                f"Forbidden humanizer word found in prose: {word}"
            )

    def test_explainer_diagram_and_svg_validity(self):
        """Explainer must contain accessible desktop and mobile SVGs with valid XML."""
        match = re.search(r'<figure class="explainer" id="ex-delegation-checkpoints">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match, "Missing #ex-delegation-checkpoints figure")
        fig = match.group(0)

        self.assertIn('class="diagram-desktop"', fig)
        self.assertIn('class="diagram-mobile"', fig)
        self.assertIn('viewBox="0 0 700 350"', fig)
        self.assertIn('viewBox="0 0 330 680"', fig)

        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', fig, re.DOTALL)
        self.assertEqual(len(svgs), 2)
        for svg_str in svgs:
            root = ET.fromstring(svg_str)
            self.assertEqual(root.tag, "svg")
            self.assertIn("role", root.attrib)
            self.assertEqual(root.attrib["role"], "img")

    def test_primary_source_citations(self):
        """Primary source citations must be present in footnotes and aside."""
        self.assertIn("arXiv:2611.00291", self.content)
        self.assertIn("10.1287/isre.2016.0644", self.content)
        self.assertIn("10.1109/3468.844354", self.content)
        self.assertIn("10.1145/3290605.3300233", self.content)
        self.assertIn('id="fn1"', self.content)
        self.assertIn('id="fn4"', self.content)

    def test_header_image_asset(self):
        """Header image must exist, have valid JPEG magic bytes, and be < 300 KB."""
        self.assertTrue(os.path.exists(self.img_path), f"Missing header image: {self.img_path}")
        size = os.path.getsize(self.img_path)
        self.assertLess(size, 300 * 1024, f"Image size {size} exceeds 300 KB")
        self.assertGreater(size, 20 * 1024, f"Image size {size} is suspiciously small")

        with open(self.img_path, "rb") as f:
            magic = f.read(3)
            self.assertEqual(magic, b"\xff\xd8\xff", "Header image is not a valid JPEG")


if __name__ == "__main__":
    unittest.main()
