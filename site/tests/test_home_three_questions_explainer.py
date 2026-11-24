#!/usr/bin/env python3
"""Tests for the home page responsive Three Questions editorial explainer.

Verifies that the home page presents Seeing, Owning, and Acting in plain,
jargon-free English at a big-picture altitude, with zero invented circuit/bench
terminology or fake receipt/timer UI.
"""

from pathlib import Path
import sys
import unittest

SITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE_ROOT))
import build


FORBIDDEN_HOMEPAGE_JARGON = [
    "SCHEMATIC WIRE",
    "RELAY TOPOLOGY",
    "ERRAND WIRE",
    "ACTION RECEIPT BENCH",
    "SCOPED VALET KEY",
    "AMBIENT MASTER KEY",
    "LEASE TTL",
    "STAMP OUT-OF-BAND APPROVAL",
    "zero-tool airlock",
    "Coalition Bench",
    "Wind Tunnel",
]


class HomePageThreeQuestionsExplainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home_path = SITE_ROOT / "content" / "index.html"
        assert cls.home_path.exists(), f"Missing index.html at {cls.home_path}"
        cls.home_html = cls.home_path.read_text(encoding="utf-8")

    def test_explainer_structure_and_build_checks(self):
        """Explainer must conform to build.check_explainers with title, desc, and figcaption."""
        self.assertIn('id="ex-three-questions"', self.home_html)
        self.assertIn('id="ex-questions-title"', self.home_html)
        self.assertIn('id="ex-questions-desc"', self.home_html)
        errs = build.check_explainers("index.html", self.home_html)
        self.assertEqual(errs, [], f"check_explainers failed on index.html: {errs}")

    def test_three_core_pillars_and_essay_links(self):
        """All three core questions (Seeing, Owning, Acting) must be visible in plain English with links."""
        self.assertIn("01 · Seeing", self.home_html)
        self.assertIn("02 · Owning", self.home_html)
        self.assertIn("03 · Acting", self.home_html)
        self.assertIn("Who is actually acting?", self.home_html)
        self.assertIn("Who owns the intelligence?", self.home_html)
        self.assertIn("What can one person do?", self.home_html)
        self.assertIn("/blog/who-is-actually-acting/", self.home_html)
        self.assertIn("/blog/who-should-own-intelligence/", self.home_html)
        self.assertIn("/get-involved/", self.home_html)

    def test_zero_invented_bench_or_schematic_jargon(self):
        """Front page must never contain invented schematic/bench/key terminology or fake TTL receipts."""
        low = self.home_html.lower()
        for phrase in FORBIDDEN_HOMEPAGE_JARGON:
            self.assertNotIn(phrase.lower(), low, f"Forbidden jargon {phrase!r} found in index.html")
        self.assertNotIn('data-stage="bench"', self.home_html)

    def test_responsive_mobile_stacking_css(self):
        """Explainer must use clean editorial 3-column layout that stacks to 1fr on mobile."""
        self.assertIn("st-editorial-figure", self.home_html)
        self.assertIn("st-question-grid", self.home_html)
        self.assertNotIn('class="q-card"', self.home_html)

        stages_css_path = SITE_ROOT / "assets" / "css" / "stages.css"
        self.assertTrue(stages_css_path.exists(), f"Missing stages.css at {stages_css_path}")
        stages_css = stages_css_path.read_text(encoding="utf-8")
        self.assertIn(".st-question-grid", stages_css)
        self.assertIn("@media (max-width: 860px)", stages_css)
        self.assertNotIn("@media (prefers-color-scheme: dark)", stages_css)
        self.assertIn("#FAF3EA", stages_css)
        self.assertIn("grid-template-columns: 1fr;", stages_css)

    def test_no_duplicate_stories_cards(self):
        """Explainer must replace the redundant .stories block to avoid duplicating cards."""
        self.assertNotIn('<div class="stories">', self.home_html)

    def test_home_built_page_contains_explainer(self):
        """Built dist/index.html must contain the three questions explainer and valid markup."""
        build.build()
        dest = SITE_ROOT / "dist" / "index.html"
        self.assertTrue(dest.exists(), f"Expected {dest} to exist")
        html = dest.read_text(encoding="utf-8")
        self.assertIn('id="ex-three-questions"', html)
        self.assertIn("01 · Seeing", html)
        self.assertIn("02 · Owning", html)
        self.assertIn("03 · Acting", html)
        self.assertNotIn("SCHEMATIC WIRE", html)


if __name__ == "__main__":
    unittest.main()
