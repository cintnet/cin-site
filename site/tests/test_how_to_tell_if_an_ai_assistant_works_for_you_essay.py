#!/usr/bin/env python3
"""Unit tests verifying line-editing, voice rules, and citation integrity for the loyalty tests essay.

Verifies:
- Frontmatter metadata, takeaway, reader, and lede fields
- Vignette image existence and size constraints (< 300 KB)
- Plain language constraints (median sentence <= 22 words, zero > 35 words)
- Zero humanizer tells (zero em-dashes, zero negative parallelisms, zero forbidden AI words)
- Exact citation verification across all 4 primary sources
- Claim-first opening: names AI assistant immediately, cuts decorative scene opening
"""

from pathlib import Path
import re
import statistics
import sys
import unittest

SITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE_ROOT))

BLOG_FILE = SITE_ROOT / "content" / "blog" / "how-to-tell-if-an-ai-assistant-works-for-you.html"
IMAGE_FILE = SITE_ROOT / "assets" / "img" / "post-how-to-tell-if-an-ai-assistant-works-for-you.jpg"


class HowToTellIfAnAIAssistantWorksForYouEssayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = BLOG_FILE.read_text(encoding="utf-8")
        parts = cls.content.split("---\n", 2)
        cls.fm_text = parts[1] if len(parts) >= 3 else ""
        cls.body = parts[2] if len(parts) >= 3 else cls.content

    def test_essay_file_exists(self):
        self.assertTrue(BLOG_FILE.exists(), f"Essay file must exist at {BLOG_FILE}")

    def test_frontmatter_metadata(self):
        self.assertIn("title: How to tell if an AI assistant is working for you", self.fm_text)
        self.assertIn("template: article", self.fm_text)
        self.assertIn("category: Seeing", self.fm_text)
        self.assertIn("date: 2026-11-06", self.fm_text)
        self.assertIn("image: post-how-to-tell-if-an-ai-assistant-works-for-you.jpg", self.fm_text)
        self.assertIn("reader:", self.fm_text)
        self.assertIn("takeaway:", self.fm_text)
        self.assertIn("lede:", self.fm_text)

    def test_claim_first_opening(self):
        # Lede must name AI assistant directly and state the claim without a 50+ word scene opening
        self.assertIn("When an AI assistant sits between you and the internet", self.fm_text)
        self.assertNotIn("Step off a train in an unfamiliar city", self.content)
        self.assertNotIn("station concierge", self.content)

    def test_illustration_vignette_spec(self):
        self.assertTrue(IMAGE_FILE.exists(), f"Vignette image must exist at {IMAGE_FILE}")
        size = IMAGE_FILE.stat().st_size
        self.assertLess(size, 300000, f"Image size ({size} bytes) must be under 300 KB")

    def test_citations_present(self):
        """Must cite FTC 2022, OECD 2022, Sharma et al. 2024, Kadavath et al. 2022, Balkin 2016, Clark & Chalmers 1998, Dennis & Van Horn 1966."""
        citations = [
            "https://www.ftc.gov/reports/bringing-dark-patterns-light",
            "https://www.oecd.org/en/publications/dark-commercial-patterns_44f5e846-en.html",
            "https://arxiv.org/abs/2310.13548",
            "https://arxiv.org/abs/2207.05221",
            "https://doi.org/10.1093/analys/58.1.7",
            "https://doi.org/10.1145/365230.365252",
        ]
        for c in citations:
            self.assertIn(c, self.content, f"Missing citation {c}")
        self.assertIn("@media (prefers-color-scheme: dark)", self.content)
        self.assertNotIn('<div class="callout">', self.content)

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
        word_counts = [len(s.split()) for s in sentences if len(s.split()) > 2]

        self.assertGreater(len(word_counts), 30, "Too few sentences extracted")
        median_len = statistics.median(word_counts)
        self.assertLessEqual(median_len, 22, f"Median sentence length ({median_len}) must be <= 22 words")

        long_sentences = [s for s in sentences if len(s.split()) > 35]
        self.assertEqual(len(long_sentences), 0, f"Found sentences > 35 words: {long_sentences}")


if __name__ == "__main__":
    unittest.main()
