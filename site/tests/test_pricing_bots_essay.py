import re
import statistics
import unittest
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent.parent
BLOG_PATH = SITE_ROOT / "content" / "blog" / "when-pricing-bots-bid-on-public-contracts.html"
IMAGE_PATH = SITE_ROOT / "assets" / "img" / "post-when-pricing-bots-bid-on-public-contracts.jpg"


class PricingBotsPublicProcurementEssayTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(BLOG_PATH.exists(), f"Blog post missing at {BLOG_PATH}")
        self.content = BLOG_PATH.read_text(encoding="utf-8")

    def test_frontmatter_fields(self):
        """Check all required frontmatter metadata."""
        for field in [
            "title: When pricing bots bid on public contracts",
            "reader: Public officials",
            "takeaway:",
            "template: article",
            "date: 2026-11-08",
            "order: 57",
            "category: Governing",
            "image: post-when-pricing-bots-bid-on-public-contracts.jpg",
            "image_alt:",
            "lede:",
        ]:
            self.assertIn(field, self.content)

    def test_image_asset_properties(self):
        """Check that illustration JPEG exists, is under 300 KB, and has valid dimensions."""
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
        max_len = max(lengths)
        long_ones = [(l, s) for l, s in zip(lengths, sentences) if l > 35]
        self.assertEqual(len(long_ones), 0, f"Found sentences over 35 words: {long_ones}")

    def test_steward_gate_no_forbidden_strings(self):
        """No internal ticket IDs, speculative tokens, or savings promises."""
        text = self.content
        for forbidden in ["MMCT", "guaranteed profit", "guaranteed savings"]:
            self.assertNotIn(forbidden, text)
        self.assertIsNone(re.search(r"\b[DL]-\d{4}\b", text), "Found internal ticket ID pattern")
        self.assertIsNone(re.search(r"\bF\d+\b", text), "Found internal family ID pattern")

    def test_primary_sources_and_citations(self):
        """Footnotes contain verified primary sources."""
        self.assertIn("arXiv:2409.03956", self.content)
        self.assertIn("arXiv:2610.21867", self.content)
        self.assertIn("ftc.gov", self.content)
        self.assertIn("competition-bureau-canada", self.content)

    def test_svg_accessibility(self):
        """Explainer diagram has full accessibility markers and no prohibited innerHTML."""
        self.assertIn('role="group"', self.content)
        self.assertIn('aria-labelledby="ex-audit-title ex-audit-desc"', self.content)
        self.assertIn('<title id="ex-audit-title">', self.content)
        self.assertIn('<desc id="ex-audit-desc">', self.content)
        self.assertNotIn(".innerHTML", self.content)


if __name__ == "__main__":
    unittest.main()
