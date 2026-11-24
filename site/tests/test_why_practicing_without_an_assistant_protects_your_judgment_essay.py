#!/usr/bin/env python3
"""Unit tests for 'Why practicing without an assistant protects your judgment' blog essay (Spec 03/05/09 / Lane comms)."""

import os
from pathlib import Path
import re
import sys
import unittest

SITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE_ROOT))
import build as site_build

BLOG_FILE = SITE_ROOT / "content" / "blog" / "why-practicing-without-an-assistant-protects-your-judgment.html"
IMAGE_FILE = SITE_ROOT / "assets" / "img" / "post-why-practicing-without-an-assistant-protects-your-judgment.jpg"


class WhyPracticingWithoutAnAssistantProtectsYourJudgmentEssayTests(unittest.TestCase):
    def test_essay_file_exists(self):
        self.assertTrue(BLOG_FILE.exists(), f"Essay file must exist at {BLOG_FILE}")

    def test_frontmatter_metadata(self):
        content = BLOG_FILE.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\n"), "File must start with YAML frontmatter")
        parts = content.split("---\n", 2)
        self.assertGreaterEqual(len(parts), 3, "Frontmatter must be enclosed by --- delimiters")
        fm_text = parts[1]

        self.assertIn("title: Why practicing without an assistant protects your judgment", fm_text)
        self.assertIn("template: article", fm_text)
        self.assertIn("category: Living", fm_text)
        self.assertIn("date: 2026-11-08", fm_text)
        self.assertIn("image: post-why-practicing-without-an-assistant-protects-your-judgment.jpg", fm_text)
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
            (r"\bF[0-9]{1,2}\b", "foundation ticket id"),
        ]
        for pattern, label in forbidden:
            match = re.search(pattern, body, re.IGNORECASE)
            self.assertIsNone(match, f"Found forbidden {label} '{match.group(0) if match else ''}' in body")

    def test_sentence_and_paragraph_length(self):
        content = BLOG_FILE.read_text(encoding="utf-8")
        body = content.split("---\n", 2)[2]
        # Ignore aside and footnotes for plain reading text
        plain_body = re.sub(r'<aside\b[^>]*>.*?</aside>', '', body, flags=re.DOTALL)
        plain_body = re.sub(r'<section\b[^>]*\bclass=["\']footnotes["\'][^>]*>.*?</section>', '', plain_body, flags=re.DOTALL)
        plain_body = re.sub(r'<figure\b[^>]*>.*?</figure>', '', plain_body, flags=re.DOTALL)

        paragraphs = re.findall(r'<p\b[^>]*>(.*?)</p>', plain_body, flags=re.DOTALL)
        self.assertGreater(len(paragraphs), 5, "Essay must have multiple paragraphs")

        for p in paragraphs:
            clean = re.sub(r'<[^>]+>', ' ', p).strip()
            words = clean.split()
            self.assertLessEqual(len(words), 95, f"Paragraph exceeds 95 words: '{clean[:60]}...'")

            sentences = [s.strip() for s in re.split(r'[.!?]+', clean) if s.strip()]
            for s in sentences:
                s_words = s.split()
                self.assertLessEqual(len(s_words), 34, f"Sentence exceeds 34 words ({len(s_words)} words): '{s}'")

    def test_interactive_explainer_accessibility(self):
        content = BLOG_FILE.read_text(encoding="utf-8")
        self.assertIn('figure class="explainer" id="ex-cognitive-autonomy"', content)
        self.assertIn('aria-labelledby="ex-autonomy-title ex-autonomy-desc"', content)
        self.assertIn('<title id="ex-autonomy-title">', content)
        self.assertIn('<desc id="ex-autonomy-desc">', content)
        self.assertIn('<figcaption>', content)

    def test_primary_source_citations(self):
        content = BLOG_FILE.read_text(encoding="utf-8")
        self.assertIn("https://www.theguardian.com/technology/2026/nov/06/ai-disruption-job-quitting", content)
        self.assertIn("https://arxiv.org/abs/2604.03501", content)
        self.assertIn("https://arxiv.org/abs/2610.38167", content)


if __name__ == "__main__":
    unittest.main()
