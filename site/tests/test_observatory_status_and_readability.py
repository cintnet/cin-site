"""Tests ensuring Observatory honest-status representation and responsive readability.

Verifies that landing cards and labs index cards consistently reflect the early
exploratory state of the Observatory without prematurely claiming 'Live · Scored'.
"""
from __future__ import annotations

import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"


class ObservatoryHonestStatusTests(unittest.TestCase):
    def test_home_page_observatory_card_status(self):
        index_html = (CONTENT / "index.html").read_text(encoding="utf-8")
        self.assertIn('/labs/observatory/', index_html)
        # Must not claim to be already live and scored
        self.assertNotIn('<span class="status">Live · Scored</span><h3>Observatory</h3>', index_html)
        # Must accurately reflect early in-development state
        self.assertIn('<span class="status">Early · In development</span><h3>Observatory</h3>', index_html)
        # Must describe scoring in the future tense
        self.assertIn('public forecasts we will score ourselves on', index_html)

    def test_labs_index_observatory_card_status(self):
        labs_index_html = (CONTENT / "labs" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="observatory"', labs_index_html)
        self.assertNotIn('<span class="status">Live · Scored</span><h3>Observatory</h3>', labs_index_html)
        self.assertIn('<span class="status">Early · In development</span><h3>Observatory</h3>', labs_index_html)
        self.assertIn('We will publish dated forecasts and grade ourselves on them', labs_index_html)

    def test_observatory_page_metadata_and_readability(self):
        obs_html = (CONTENT / "labs" / "observatory.html").read_text(encoding="utf-8")
        # Frontmatter eyebrow should be Labs · Early
        self.assertIn('eyebrow: Labs · Early', obs_html)
        # Explainer figure contract
        self.assertIn('id="ex-oversight-gap"', obs_html)
        self.assertIn('aria-labelledby="ex-oversight-gap-title ex-oversight-gap-desc"', obs_html)
        self.assertIn('<figcaption>', obs_html)
        # Responsive CSS for stages grid on mobile
        self.assertIn('@media (max-width: 440px)', obs_html)
        # Honest limits callout
        self.assertIn('Our public scoring dashboard is still early', obs_html)


class ObservatoryReadabilityVoiceTests(unittest.TestCase):
    def _check_sentences(self, path: Path):
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                text = parts[2]
        text = re.sub(r"(?s)<script.*?</script>", "", text)
        text = re.sub(r"(?s)<style.*?</style>", "", text)
        text = re.sub(r"(?s)<svg.*?</svg>", "", text)
        text = re.sub(r'(?s)<aside class="for-researchers".*?</aside>', "", text)
        text = re.sub(r'(?s)<section class="footnotes".*?</section>', "", text)
        text = re.sub(r'</?(?:div|p|h[1-6]|li|section|article|header|footer|figure|figcaption|table|tr|td|th)[^>]*>', '. ', text)
        text = re.sub(r'<[^>]+>', ' ', text)
        raw_sentences = [s.strip() for s in re.split(r"[.!?]+(?:\s+|$)", text) if len(s.strip()) > 0]
        sentences = [" ".join(s.split()) for s in raw_sentences]
        lengths = [len(s.split()) for s in sentences if len(s.split()) > 1]
        self.assertTrue(len(lengths) > 0, f"No sentences found in {path}")
        lengths.sort()
        median = lengths[len(lengths) // 2]
        self.assertLessEqual(median, 22, f"{path} median sentence length {median} > 22")
        too_long = [s for s in sentences if len(s.split()) > 35]
        self.assertEqual(len(too_long), 0, f"{path} has sentences > 35 words: {too_long}")

    def test_readability_on_key_pages(self):
        for rel in ["index.html", "labs/index.html", "labs/observatory.html"]:
            self._check_sentences(CONTENT / rel)


if __name__ == "__main__":
    unittest.main()
