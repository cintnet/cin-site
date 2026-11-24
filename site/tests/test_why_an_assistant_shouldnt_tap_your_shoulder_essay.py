#!/usr/bin/env python3
"""Unit tests for 'Why an assistant shouldn't tap your shoulder for every small question' blog essay (Spec 03/05/09 / Lane sitecritic)."""

from pathlib import Path
import re
import sys
import unittest

SITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE_ROOT))
import build as site_build

BLOG_FILE = SITE_ROOT / "content" / "blog" / "why-an-assistant-shouldnt-tap-your-shoulder-for-every-small-question.html"
IMAGE_FILE = SITE_ROOT / "assets" / "img" / "post-why-an-assistant-shouldnt-tap-your-shoulder-for-every-small-question.jpg"


class WhyAnAssistantShouldntTapYourShoulderTests(unittest.TestCase):
    def test_essay_file_exists(self):
        self.assertTrue(BLOG_FILE.exists(), f"Essay file must exist at {BLOG_FILE}")

    def test_frontmatter_metadata(self):
        content = BLOG_FILE.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\n"), "File must start with YAML frontmatter")
        parts = content.split("---\n", 2)
        self.assertGreaterEqual(len(parts), 3, "Frontmatter must be enclosed by --- delimiters")
        fm_text = parts[1]

        self.assertIn("title: Why an assistant shouldn't tap your shoulder for every small question", fm_text)
        self.assertIn("template: article", fm_text)
        self.assertIn("category: Living", fm_text)
        self.assertIn("order: 55", fm_text)
        self.assertIn("date: 2026-11-08", fm_text)
        self.assertIn("image: post-why-an-assistant-shouldnt-tap-your-shoulder-for-every-small-question.jpg", fm_text)
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
            (r"\bL-[0-9]{4}\b", "ticket id"),
        ]
        for pattern, label in forbidden:
            match = re.search(pattern, body, re.IGNORECASE)
            self.assertIsNone(match, f"Found forbidden {label} in essay body: {match}")

        # Check sentence lengths in paragraphs outside aside/details/figure
        clean_body = re.sub(r"<aside class=\"for-researchers\">.*?</aside>", "", body, flags=re.DOTALL)
        clean_body = re.sub(r"<section class=\"footnotes\">.*?</section>", "", clean_body, flags=re.DOTALL)
        clean_body = re.sub(r"<figure.*?</figure>", "", clean_body, flags=re.DOTALL)
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
        self.assertIn('id="ex-attention-scheduling"', content)
        self.assertIn('role="group"', content)
        self.assertIn('<figcaption>', content)

    def test_citations_and_attribution(self):
        content = BLOG_FILE.read_text(encoding="utf-8")
        self.assertIn("arXiv:2610.41129", content)
        self.assertIn("Hanzhao Wang, Shengjie Liu and Zhengchao Wang", content)
        self.assertIn("Gloria Mark", content)
        self.assertIn("arXiv:2611.00291", content)

    def test_research_cross_link(self):
        research_file = SITE_ROOT / "content" / "research.html"
        self.assertTrue(research_file.exists())
        research_text = research_file.read_text(encoding="utf-8")
        self.assertIn("why-an-assistant-shouldnt-tap-your-shoulder-for-every-small-question", research_text)


if __name__ == "__main__":
    unittest.main()
