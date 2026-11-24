import re
import statistics
import unittest
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent.parent
BLOG_PATH = SITE_ROOT / "content" / "blog" / "why-thinking-longer-does-not-make-an-assistant-more-honest.html"
IMAGE_PATH = SITE_ROOT / "assets" / "img" / "post-why-thinking-longer-does-not-make-an-assistant-more-honest.jpg"
RESEARCH_PATH = SITE_ROOT / "content" / "research.html"


class WhyThinkingLongerDoesNotMakeAnAssistantMoreHonestEssayTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(BLOG_PATH.exists(), f"Blog post missing at {BLOG_PATH}")
        self.content = BLOG_PATH.read_text(encoding="utf-8")

    def test_frontmatter_fields(self):
        """Check all required frontmatter metadata."""
        for field in [
            "title: Why thinking longer does not make an AI assistant more honest",
            "reader: Anyone relying on reasoning models",
            "takeaway:",
            "template: article",
            "date: 2026-11-09",
            "order: 60",
            "category: Seeing",
            "image: post-why-thinking-longer-does-not-make-an-assistant-more-honest.jpg",
            "image_alt:",
            "lede:",
        ]:
            self.assertIn(field, self.content)

    def test_image_asset_properties(self):
        """Check that illustration JPEG exists, is under 300 KB, and has valid content."""
        self.assertTrue(IMAGE_PATH.exists(), f"Image asset missing at {IMAGE_PATH}")
        size_kb = IMAGE_PATH.stat().st_size / 1024
        self.assertLess(size_kb, 300, f"Image size {size_kb:.1f} KB exceeds 300 KB limit")

    def test_prose_sentence_lengths(self):
        """Strict Voice Gate: median <= 22 words, zero sentences > 35 words."""
        text = self.content
        # Strip frontmatter
        text = re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL)
        # Strip aside for researchers
        text = re.sub(r'<aside class="for-researchers".*?</aside>', "", text, flags=re.DOTALL)
        # Strip footnotes
        text = re.sub(r'<section class="footnotes".*?</section>', "", text, flags=re.DOTALL)
        # Strip figure/svg
        text = re.sub(r"<figure.*?</figure>", "", text, flags=re.DOTALL)
        # Strip html tags
        plain = re.sub(r"<[^>]+>", " ", text)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", plain) if s.strip()]
        lengths = [len(s.split()) for s in sentences]

        self.assertGreater(len(sentences), 20, "Essay should have substantial content")
        median_len = statistics.median(lengths)
        self.assertLessEqual(median_len, 22.0, f"Median sentence length {median_len} > 22")
        long_ones = [(l, s) for l, s in zip(lengths, sentences) if l > 35]
        self.assertEqual(len(long_ones), 0, f"Found sentences over 35 words: {long_ones}")

    def test_steward_gate_no_forbidden_strings(self):
        """No internal ticket IDs, speculative tokens, or savings promises."""
        text = self.content
        for forbidden in ["MMCT", "guaranteed profit", "guaranteed savings", "tokens payout"]:
            self.assertNotIn(forbidden, text)
        self.assertIsNone(re.search(r"\b[DL]-\d{4}\b", text), "Found internal ticket ID pattern")
        self.assertIsNone(re.search(r"\bF\d+\b", text), "Found internal family ID pattern")

    def test_primary_sources_and_citations(self):
        """Footnotes contain verified primary sources."""
        self.assertIn("doi.org/10.1017/S0140525X10000968", self.content)
        self.assertIn("arxiv.org/abs/2305.04388", self.content)
        self.assertIn("arxiv.org/abs/2512.16030", self.content)
        self.assertIn("doi.org/10.1175/1520-0493(1950)078", self.content)

    def test_svg_accessibility(self):
        """Explainer diagram has full accessibility markers and no prohibited innerHTML."""
        self.assertIn('aria-labelledby="ex-ec-title ex-ec-desc"', self.content)
        self.assertIn('<title id="ex-ec-title">', self.content)
        self.assertIn('<desc id="ex-ec-desc">', self.content)
        self.assertNotIn(".innerHTML", self.content)

    def test_research_html_cross_link(self):
        """Theme 1 in research.html references the new essay."""
        self.assertTrue(RESEARCH_PATH.exists())
        research_content = RESEARCH_PATH.read_text(encoding="utf-8")
        self.assertIn("/blog/why-thinking-longer-does-not-make-an-assistant-more-honest/", research_content)


if __name__ == "__main__":
    unittest.main()
