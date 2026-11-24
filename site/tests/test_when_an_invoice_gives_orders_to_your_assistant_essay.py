#!/usr/bin/env python3
"""Unit tests for 'When an invoice gives orders to your assistant' blog essay (Spec 03/05/09 / Lane comms)."""

from pathlib import Path
import re
import sys
import unittest

SITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE_ROOT))
import build as site_build

BLOG_FILE = SITE_ROOT / "content" / "blog" / "when-an-invoice-gives-orders-to-your-assistant.html"
IMAGE_FILE = SITE_ROOT / "assets" / "img" / "post-when-an-invoice-gives-orders-to-your-assistant.jpg"


class WhenAnInvoiceGivesOrdersToYourAssistantEssayTests(unittest.TestCase):
    def test_essay_file_exists(self):
        self.assertTrue(BLOG_FILE.exists(), f"Essay file must exist at {BLOG_FILE}")

    def test_frontmatter_metadata(self):
        content = BLOG_FILE.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\n"), "File must start with YAML frontmatter")
        parts = content.split("---\n", 2)
        self.assertGreaterEqual(len(parts), 3, "Frontmatter must be enclosed by --- delimiters")
        fm_text = parts[1]

        self.assertIn("title: When an invoice gives orders to your assistant", fm_text)
        self.assertIn("template: article", fm_text)
        self.assertIn("category: Protecting", fm_text)
        self.assertIn("date: 2026-11-09", fm_text)
        self.assertIn("image: post-when-an-invoice-gives-orders-to-your-assistant.jpg", fm_text)
        self.assertIn("reader:", fm_text)
        self.assertIn("takeaway:", fm_text)
        self.assertIn("lede:", fm_text)

    def test_illustration_vignette_spec(self):
        self.assertTrue(IMAGE_FILE.exists(), f"Vignette image must exist at {IMAGE_FILE}")
        size = IMAGE_FILE.stat().st_size
        self.assertLess(size, 300000, f"Image size ({size} bytes) must be under 300 KB")
        self.assertGreater(size, 10000, f"Image size ({size} bytes) must be substantial")

        dims = site_build.image_dimensions(IMAGE_FILE)
        self.assertIsNotNone(dims, "Image dimensions must be extractable")
        w, h = dims
        self.assertGreaterEqual(w, 1200, "Width should be at least 1200px")
        self.assertGreaterEqual(h, 700, "Height should be at least 700px")

    def test_voice_rules_and_forbidden_terms(self):
        content = BLOG_FILE.read_text(encoding="utf-8")
        body = content.split("---\n", 2)[2]

        forbidden = [
            (r"\bContribution\s+Tokens?\b", "token framing"),
            (r"\bMMCT\b", "token ticker"),
            (r"\$\s?[0-9][0-9,]*(\.[0-9]+)?\s*(k|K|/|per)\s*(yr|year|month)?", "dollar figure"),
            (r"\broyalt(y|ies)\b", "royalty claim"),
            (r"\bD-[0-9]{4}\b", "ticket id"),
        ]

        for pattern, label in forbidden:
            match = re.search(pattern, body, re.IGNORECASE)
            self.assertIsNone(match, f"Found forbidden {label} in essay body: {match}")

        # Check sentence lengths in paragraphs outside aside/details/figure
        clean_body = re.sub(r"<aside class=\"for-researchers\">.*?</aside>", "", body, flags=re.DOTALL)
        clean_body = re.sub(r"<section class=\"footnotes\">.*?</section>", "", clean_body, flags=re.DOTALL)
        clean_body = re.sub(r"<figure.*?</figure>", "", clean_body, flags=re.DOTALL)
        clean_body = re.sub(r"<style.*?</style>", "", clean_body, flags=re.DOTALL)
        clean_body = re.sub(r"<[^>]+>", " ", clean_body)

        sentences = [s.strip() for s in re.split(r"[.!?]+", clean_body) if s.strip()]
        lengths = [len(s.split()) for s in sentences if len(s.split()) > 0]
        self.assertTrue(lengths, "Must contain sentences")
        lengths.sort()
        median = lengths[len(lengths) // 2]
        self.assertLessEqual(median, 22, f"Median sentence length {median} exceeds 22 words")
        for s in sentences:
            w_count = len(s.split())
            self.assertLessEqual(w_count, 35, f"Sentence exceeds 35 words ({w_count}w): {s}")

    def test_explainer_diagram_and_accessibility(self):
        content = BLOG_FILE.read_text(encoding="utf-8")
        self.assertIn('id="ex-invoice-boundary"', content)
        self.assertIn('role="img"', content)
        self.assertIn('<figcaption>', content)
        self.assertIn('<title id="ex-invoice-title">', content)
        self.assertIn('<desc id="ex-invoice-desc">', content)

    def test_research_page_link_presence(self):
        research_file = SITE_ROOT / "content" / "research.html"
        self.assertIn("when-an-invoice-gives-orders-to-your-assistant", research_file.read_text(encoding="utf-8"))

    def test_shared_horizon_cross_references(self):
        content = BLOG_FILE.read_text(encoding="utf-8")
        self.assertIn("Shared Horizon action library", content)
        self.assertIn("Shared Horizon", content)
        self.assertIn("2611.08281", content)
        self.assertIn("2610.35835", content)


if __name__ == "__main__":
    unittest.main()
