"""Unit tests for the line-edited stopping-the-race-to-the-bottom essay.

Verifies:
- Claim-first opening: names software agents and floor rules in the first two sentences.
- Sentence-length bounds: zero sentences > 35 words, median <= 22 words.
- Zero em-dashes in prose paragraphs and list items.
- Citation accuracy: Footnote 1 points to American Economic Review: Insights (DOI 10.1257/aeri.20180150).
- Explainer figure SVG XML validity and accessible aria bindings.
"""

from pathlib import Path
import re
import statistics
import unittest
from xml.etree import ElementTree as ET

SITE_ROOT = Path(__file__).resolve().parents[1]
ESSAY_PATH = SITE_ROOT / "content" / "blog" / "stopping-the-race-to-the-bottom.html"


class StoppingTheRaceToTheBottomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = ESSAY_PATH.read_text(encoding="utf-8")
        m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n(.*)", cls.raw, re.DOTALL)
        cls.frontmatter_raw = m.group(1) if m else ""
        cls.body_raw = m.group(2) if m else cls.raw

        cls.fm = {}
        for line in cls.frontmatter_raw.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                cls.fm[k.strip()] = v.strip()

    def test_frontmatter_presence(self):
        """Frontmatter must define required metadata."""
        self.assertEqual(self.fm.get("title"), "Stopping the algorithmic race to the bottom")
        self.assertIn("takeaway", self.fm)
        self.assertIn("lede", self.fm)
        self.assertIn("reader", self.fm)

    def test_claim_first_lede(self):
        """The lede must name software agents and floor rules in its opening sentences."""
        lede = self.fm.get("lede", "")
        self.assertIn("software agents", lede.lower())
        self.assertIn("guardrails", lede.lower())
        self.assertIn("floor rules", lede.lower())

    def test_sentence_length_bounds(self):
        """All body prose sentences must be <= 35 words, and median <= 22 words."""
        # Strip out figures, aside, script, style, footnotes
        prose = re.sub(r"<(style|script|svg|aside|figure)[^>]*>.*?</\1>", " ", self.body_raw, flags=re.DOTALL | re.IGNORECASE)
        prose = re.sub(r'<section class="footnotes".*?</section>', " ", prose, flags=re.DOTALL)
        # Turn block closing tags into periods so headings and paragraphs do not run together
        prose = re.sub(r"</(p|h\d|li|div|blockquote)>", ". ", prose, flags=re.IGNORECASE)
        prose = re.sub(r"<[^>]+>", " ", prose)

        sentences = [re.sub(r"\s+", " ", s).strip() for s in re.split(r"[\.\?\!]\s+", prose) if len(s.strip().split()) > 3]
        self.assertGreater(len(sentences), 40, "Expected at least 40 sentences in body prose")

        lengths = [len(s.split()) for s in sentences]
        max_len = max(lengths)
        median_len = statistics.median(lengths)

        self.assertLessEqual(max_len, 35, f"Found sentence exceeding 35 words ({max_len} words)")
        self.assertLessEqual(median_len, 22, f"Median sentence length ({median_len:.1f}) exceeds 22 words")

    def test_no_em_dashes_in_prose(self):
        """Prose body must contain zero em-dashes per Voice Guide Rule 16."""
        prose = re.sub(r"<(style|script|svg|aside|figure)[^>]*>.*?</\1>", " ", self.body_raw, flags=re.DOTALL | re.IGNORECASE)
        prose = re.sub(r'<section class="footnotes".*?</section>', " ", prose, flags=re.DOTALL)
        self.assertNotIn("—", prose, "Prose body must not contain literal em-dash")
        self.assertNotIn("&mdash;", prose, "Prose body must not contain &mdash;")

    def test_footnote_citation_accuracy(self):
        """Footnote 1 must cite American Economic Review: Insights (not Review of Economic Studies)."""
        self.assertIn("American Economic Review: Insights", self.raw)
        self.assertNotIn("Review of Economic Studies", self.raw)
        self.assertIn("https://doi.org/10.1257/aeri.20180150", self.raw)
        self.assertIn("https://doi.org/10.1257/aer.20190623", self.raw)

    def test_explainer_svg_validity(self):
        """The explainer figure must have valid XML and accessible labels."""
        fig_m = re.search(r'<figure\b[^>]*id=["\']ex-safety-floor["\'][^>]*>(.*?)</figure>', self.raw, re.DOTALL)
        self.assertIsNotNone(fig_m, "Missing <figure id='ex-safety-floor'>")
        svg_m = re.search(r"<svg\b[^>]*>.*?</svg>", fig_m.group(1), re.DOTALL)
        self.assertIsNotNone(svg_m, "Missing <svg> in explainer")
        svg_xml = svg_m.group(0)
        if "xmlns=" not in svg_xml:
            svg_xml = svg_xml.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)

        try:
            root = ET.fromstring(svg_xml)
        except ET.ParseError as e:
            self.fail(f"SVG XML parse error: {e}")

        self.assertEqual(root.tag.split("}")[-1], "svg")
        self.assertIn("viewBox", root.attrib)


if __name__ == "__main__":
    unittest.main()
