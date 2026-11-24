import re
import statistics
import unittest
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent.parent
BLOG_PATH = SITE_ROOT / "content" / "blog" / "why-reading-an-ai-models-mind-is-harder-than-checking-its-receipts.html"
IMAGE_PATH = SITE_ROOT / "assets" / "img" / "post-why-reading-an-ai-models-mind-is-harder-than-checking-its-receipts.jpg"


class WhyReadingAnAIModelsMindEssayTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(BLOG_PATH.exists(), f"Blog post missing at {BLOG_PATH}")
        self.content = BLOG_PATH.read_text(encoding="utf-8")

    def test_frontmatter_fields(self):
        """Check all required frontmatter metadata."""
        for field in [
            "title: Why reading an AI model's mind is harder than checking its receipts",
            "reader:",
            "takeaway:",
            "template: article",
            "date: 2026-11-09",
            "order: 61",
            "category: Seeing",
            "image: post-why-reading-an-ai-models-mind-is-harder-than-checking-its-receipts.jpg",
            "image_alt:",
            "lede:",
        ]:
            self.assertIn(field, self.content)

    def test_image_asset_properties(self):
        """Check that illustration JPEG exists, is under 300 KB, and is present."""
        self.assertTrue(IMAGE_PATH.exists(), f"Image asset missing at {IMAGE_PATH}")
        size_kb = IMAGE_PATH.stat().st_size / 1024
        self.assertLess(size_kb, 300, f"Image size {size_kb:.1f} KB exceeds 300 KB limit")

    def test_prose_sentence_lengths(self):
        """Strict Voice Gate: median <= 22 words, zero sentences > 35 words."""
        text = self.content
        text = re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL)
        text = re.sub(r'<aside class="for-researchers".*?</aside>', "", text, flags=re.DOTALL)
        text = re.sub(r'<section class="footnotes".*?</section>', "", text, flags=re.DOTALL)
        text = re.sub(r"<figure.*?</figure>", "", text, flags=re.DOTALL)
        plain = re.sub(r"<[^>]+>", " ", text)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", plain) if s.strip()]
        lengths = [len(s.split()) for s in sentences]

        self.assertGreater(len(sentences), 20, "Essay should have substantial content")
        median_len = statistics.median(lengths)
        self.assertLessEqual(median_len, 22.0, f"Median sentence length {median_len} > 22")
        long_ones = [(l, s) for l, s in zip(lengths, sentences) if l > 35]
        self.assertEqual(len(long_ones), 0, f"Found sentences over 35 words: {long_ones}")

    def test_sequential_footnotes(self):
        """Footnotes in prose must be cited in strict sequential order (1, 2, 3, 4, 5)."""
        body = self.content.split('<section class="footnotes">')[0]
        refs = [int(m) for m in re.findall(r'href=[\"\']#fn([0-9]+)[\"\']', body)]
        self.assertEqual(refs, [1, 2, 3, 4, 5], f"Footnotes out of order: {refs}")

        # Check all footnote entries exist
        for idx in range(1, 6):
            self.assertIn(f'id="fn{idx}"', self.content)

    def test_epistemic_limits_and_failure_modes(self):
        """Sceptic Gate: essay must state honest epistemic boundaries and limits."""
        self.assertIn("Honesty through open records", self.content)
        self.assertIn("cannot accomplish", self.content)
        self.assertIn("A tamper-evident log cannot guarantee that an agency's underlying policies are wise or fair", self.content)
        self.assertIn("Internal mechanistic interpretability remains a vital scientific microscope", self.content)

    def test_primary_source_citations(self):
        """Check all primary academic sources are cited accurately."""
        expected_arxiv = [
            "2502.03714",  # Universal Sparse Autoencoders (USAEs)
            "2312.06942",  # AI Control
            "2501.17315",  # AI control safety case (Korbak)
            "2406.07358",  # AI Sandbagging
            "2510.09462",  # Adaptive Attacks on Trusted Monitors
        ]
        for aid in expected_arxiv:
            self.assertIn(f"arxiv.org/abs/{aid}", self.content)

    def test_explainer_svg_accessibility(self):
        """Check explainer diagram SVG has accessible labels and phone-friendly viewBox."""
        self.assertIn('id="ex-internal-probe-vs-boundary"', self.content)
        self.assertIn('viewBox="0 0 720 336"', self.content)
        self.assertIn('role="group"', self.content)
        self.assertIn('aria-labelledby="ex-pb-title ex-pb-desc"', self.content)


if __name__ == "__main__":
    unittest.main()
