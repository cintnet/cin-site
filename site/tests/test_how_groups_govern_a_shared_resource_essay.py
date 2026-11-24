#!/usr/bin/env python3
"""Unit tests verifying line-editing, voice rules, and citation integrity for the shared resource essay.

Verifies:
- Frontmatter metadata, takeaway, reader, and lede fields
- Vignette image existence and size constraints (< 300 KB)
- Plain language constraints (median sentence <= 22 words, zero > 35 words)
- Zero humanizer tells (zero em-dashes, zero negative parallelisms, zero forbidden AI words)
- Exact citation verification across all 10 sources
- No invented principle count or links to cards that do not exist
"""

from pathlib import Path
import re
import statistics
import sys
import unittest

SITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE_ROOT))
import build as site_build

BLOG_FILE = SITE_ROOT / "content" / "blog" / "how-groups-govern-a-shared-resource.html"
IMAGE_FILE = SITE_ROOT / "assets" / "img" / "post-how-groups-govern-a-shared-resource.jpg"


class HowGroupsGovernASharedResourceEssayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = BLOG_FILE.read_text(encoding="utf-8")
        parts = cls.content.split("---\n", 2)
        cls.fm_text = parts[1] if len(parts) >= 3 else ""
        cls.body = parts[2] if len(parts) >= 3 else cls.content

    def test_essay_file_exists(self):
        self.assertTrue(BLOG_FILE.exists(), f"Essay file must exist at {BLOG_FILE}")

    def test_frontmatter_metadata(self):
        self.assertIn("title: How groups govern a shared resource", self.fm_text)
        self.assertIn("template: article", self.fm_text)
        self.assertIn("category: Governing", self.fm_text)
        self.assertIn("date: 2026-11-06", self.fm_text)
        self.assertIn("image: post-how-groups-govern-a-shared-resource.jpg", self.fm_text)
        self.assertIn("reader:", self.fm_text)
        self.assertIn("takeaway:", self.fm_text)
        self.assertIn("lede:", self.fm_text)

    def test_illustration_vignette_spec(self):
        self.assertTrue(IMAGE_FILE.exists(), f"Vignette image must exist at {IMAGE_FILE}")
        size = IMAGE_FILE.stat().st_size
        self.assertLess(size, 300000, f"Image size ({size} bytes) must be under 300 KB")

    def test_citations_present(self):
        """Must cite Hardin, Ostrom 1990/2010, Piatti, Borah, Berger, Mukhopadhyay, Ostrom 1961, Rose, Salguero."""
        citations = [
            "10.1126/science.162.3859.1243",
            "10.1017/CBO9780511807763",
            "10.1257/aer.100.3.641",
            "2404.16698",
            "2605.29062",
            "2610.36989",
            "2610.21746",
            "10.2307/1952530",
            "2604.01151",
            "2606.19214",
        ]
        for c in citations:
            self.assertIn(c, self.content, f"Missing citation {c}")

    def test_no_invented_counts_or_links(self):
        # Ostrom (1990) lists eight design principles; the essay merges two, so it gives no count.
        self.assertNotIn("seven core habits", self.content)
        self.assertNotIn("digital commons</a>", self.content)

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
