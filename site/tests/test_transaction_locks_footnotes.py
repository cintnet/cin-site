import re
import unittest
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent.parent
BLOG_PATH = SITE_ROOT / "content" / "blog" / "why-parallel-agents-need-transaction-locks.html"


class TransactionLocksFootnotesTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(BLOG_PATH.exists(), f"Blog post missing at {BLOG_PATH}")
        self.content = BLOG_PATH.read_text(encoding="utf-8")

    def test_forbidden_terms_removed(self):
        """Assert the page does not contain removed or misleading phrases."""
        self.assertNotIn("nist.gov/blogs/cybersecurity-insights/design-tenets", self.content)
        self.assertNotIn("guaranteeing", self.content)
        self.assertNotIn("read-uncommitted", self.content)

    def test_footnote_numbering_and_sources(self):
        """Verify footnote numbering matches sources list exactly."""
        self.assertIn('href="#fn1">1</a>', self.content)
        self.assertIn('href="#fn2">2</a>', self.content)
        self.assertIn('href="#fn3">3</a>', self.content)
        self.assertNotIn('href="#fn4"', self.content)
        self.assertNotIn('id="fn4"', self.content)

        # Ensure correct sources in footnotes
        self.assertIn('id="fn1">1. Hal Berenson', self.content)
        self.assertIn('id="fn2">2. Yuxiang Peng and Xiaodi Wu', self.content)
        self.assertIn('id="fn3">3. Council of Europe', self.content)

    def test_stale_authorization_sentence(self):
        """Verify stale authorization sentence is accurately phrased and footnoted."""
        expected = "Researchers studying agent governance call this stale authorization: the approval was correct when given and wrong by the time the money moved.<sup><a href=\"#fn2\">2</a></sup>"
        self.assertIn(expected, self.content)

    def test_council_of_europe_sentence(self):
        """Verify Council of Europe sentence is accurately phrased and footnoted."""
        expected = "The Council of Europe's AI convention already asks states to keep AI systems accountable and open to oversight; these commitments are one practical way to do that.<sup><a href=\"#fn3\">3</a></sup>"
        self.assertIn(expected, self.content)


if __name__ == "__main__":
    unittest.main()
