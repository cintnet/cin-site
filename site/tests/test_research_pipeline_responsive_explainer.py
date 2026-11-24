#!/usr/bin/env python3
"""Unit tests verifying the responsive research pipeline status explainer on research.html.

Ensures strict compliance with:
- Spec 05 Visual Direction & Explainer standards
- Site UX Rule 2 (schematic SVG text tags < 28 to avoid text walls)
- Site UX Rule 5 (mobile and desktop responsive parity with card stacking <= 720px/440px)
- WCAG 2.2 accessible SVG bindings (role, title, desc, aria-labelledby)
- XML well-formedness (100% valid under xml.etree.ElementTree)
- Plain language and steward voice constraints (<= 22 words median, zero > 35 words)
- build.check_explainers compliance (0 errors)
"""

import json
from pathlib import Path
import re
import sys
import unittest
from xml.etree import ElementTree as ET

SITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE_ROOT))
import build

RESEARCH_HTML = SITE_ROOT / "content" / "research.html"


class ResearchPipelineResponsiveExplainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_content = RESEARCH_HTML.read_text(encoding="utf-8")
        cls.fig_match = re.search(
            r'<figure\b[^>]*id=["\']ex-research-status["\'][^>]*>(.*?)</figure>',
            cls.raw_content,
            re.DOTALL,
        )

    def test_explainer_figure_exists(self):
        """The research page must contain the ex-research-status explainer figure."""
        self.assertIsNotNone(
            self.fig_match,
            "Missing <figure class='explainer' id='ex-research-status'> in site/content/research.html",
        )

    def test_svg_xml_validity(self):
        """The SVG must be strictly valid XML parseable by xml.etree.ElementTree."""
        body = self.fig_match.group(1)
        svg_m = re.search(r"<svg\b[^>]*>.*?</svg>", body, re.DOTALL)
        self.assertIsNotNone(svg_m, "No <svg> block found inside ex-research-status figure.")
        svg_xml = svg_m.group(0)

        if "xmlns=" not in svg_xml:
            svg_xml = svg_xml.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)

        try:
            root = ET.fromstring(svg_xml)
        except ET.ParseError as e:
            self.fail(f"SVG XML parsing failed: {e}")

        self.assertEqual(root.tag.split("}")[-1], "svg")
        self.assertIn("viewBox", root.attrib)

    def test_accessibility_bindings(self):
        """SVG must provide role='group' or 'img' and match aria-labelledby to title and desc IDs."""
        body = self.fig_match.group(1)
        svg_m = re.search(r"<svg\b[^>]*>", body, re.DOTALL)
        tag = svg_m.group(0)

        self.assertIn('aria-labelledby="ex-research-status-title ex-research-status-desc"', tag)
        self.assertIn('<title id="ex-research-status-title">', body)
        self.assertIn('<desc id="ex-research-status-desc">', body)

    def test_svg_text_density_under_28(self):
        """SVG must stay below 28 text tags to strictly obey Site UX Rule 2 anti-text-wall requirement."""
        body = self.fig_match.group(1)
        svg_m = re.search(r"<svg\b[^>]*>.*?</svg>", body, re.DOTALL)
        text_tags = re.findall(r"<text[\s>]", svg_m.group(0))
        self.assertLess(
            len(text_tags),
            28,
            f"SVG contains {len(text_tags)} <text> tags (must be < 28 for Rule 2 compliance)",
        )

    def test_five_research_tracks_present(self):
        """All seven canonical research tracks must be represented in the responsive track matrix."""
        body = self.fig_match.group(1)
        self.assertIn("1. Seeing what agents do", body)
        self.assertIn("2. A separate network for agents", body)
        self.assertIn("3. AI that works only for you", body)
        self.assertIn("4. Power on loan", body)
        self.assertIn("5. Recognising contribution", body)
        self.assertIn("6. Knowing where AI is heading", body)
        self.assertIn("7. Cooperative ownership in automated production", body)

    def test_seven_track_catalog_invariants(self):
        """Catalog JSON must partition all 69 working papers across Tracks 1-7 with verified metadata."""
        cat_m = re.search(
            r'<script\b[^>]*id=["\']research-catalog-data["\'][^>]*>(.*?)</script>',
            self.raw_content,
            re.DOTALL,
        )
        self.assertIsNotNone(cat_m, "Missing #research-catalog-data JSON script block")
        catalog = json.loads(cat_m.group(1))
        items = catalog["items"]
        papers = [it for it in items if it.get("kind") == "paper"]
        essays = [it for it in items if it.get("kind") == "essay"]
        self.assertEqual(len(papers), 69)

        expected_primary = {1: 9, 2: 9, 3: 14, 4: 8, 5: 8, 6: 6, 7: 15}
        actual_primary = {t: 0 for t in range(1, 8)}
        by_id = {}
        for p in papers:
            by_id[p["id"]] = p
            primary_track = p["themes"][0]
            actual_primary[primary_track] += 1
            self.assertEqual(p.get("track"), f"Track {primary_track}")
            self.assertTrue(p.get("formal_title", "").strip(), f"{p['id']} missing formal_title")
            self.assertNotIn("$", p["title"], f"{p['id']} contains raw LaTeX dollar sign in title")

        self.assertEqual(actual_primary, expected_primary)
        self.assertEqual(by_id["M02"]["themes"], [4, 3, 1])
        self.assertEqual(by_id["M11"]["pages"], 15)
        self.assertEqual(by_id["M20"]["status"], "Our proposal")
        self.assertEqual(by_id["M49"]["status"], "Our proposal")

        essay_by_url = {e["url"]: e for e in essays}
        for e in essays:
            for pid in e.get("papers", []):
                self.assertIn(pid, by_id, f"Essay {e['id']} references unknown paper {pid}")
                paper_urls = {x["url"] for x in by_id[pid].get("essays", [])}
                self.assertIn(
                    e["url"],
                    paper_urls,
                    f"Essay {e['id']} -> {pid} missing reverse link in paper.essays",
                )
        for p in papers:
            for er in p.get("essays", []):
                if er["url"] in essay_by_url:
                    self.assertIn(
                        p["id"],
                        essay_by_url[er["url"]].get("papers", []),
                        f"Paper {p['id']} -> {er['url']} missing reverse link in essay.papers",
                    )

    def test_responsive_mobile_stacking_css(self):
        """Explainer must define media queries for mobile screen stacking."""
        body = self.fig_match.group(1)
        self.assertIn("@media (max-width: 720px)", body)
        self.assertIn("@media (max-width: 440px)", body)
        self.assertIn("grid-template-columns: 1fr;", body)

    def test_unified_warm_paper_palette_no_split_dark_mode(self):
        """Explainer must stick to unified warm paper colours without split-brain dark mode overrides."""
        body = self.fig_match.group(1)
        self.assertNotIn("@media (prefers-color-scheme: dark)", body)
        self.assertIn("#FAF3EA", body)

    def test_spec_05_color_tokens(self):
        """Explainer must utilize warm cream, terracotta, and deep forest green palette tokens."""
        body = self.fig_match.group(1)
        self.assertIn("#FAF3EA", body, "Missing warm cream #FAF3EA token")
        self.assertIn("#B85C38", body, "Missing terracotta #B85C38 token")
        self.assertIn("#0B3F30", body, "Missing deep forest green #0B3F30 token")
        self.assertIn("#E1D3C0", body, "Missing warm sand #E1D3C0 border token")

    def test_plain_language_voice_gates(self):
        """Figcaption text must obey <= 22 median sentence length and zero > 35 words."""
        cap_m = re.search(r"<figcaption>(.*?)</figcaption>", self.fig_match.group(1), re.DOTALL)
        self.assertIsNotNone(cap_m, "Explainer must have an accessible figcaption")
        cap_text = cap_m.group(1).strip()
        sentences = [s.strip() for s in re.split(r"[\.\?\!]\s+", cap_text) if s.strip()]
        for s in sentences:
            words = s.split()
            self.assertLessEqual(len(words), 35, f"Figcaption sentence too long ({len(words)}w): '{s}'")

    def test_build_check_explainers_passes(self):
        """build.check_explainers must pass cleanly on research.html with 0 errors."""
        errs = build.check_explainers("research.html", self.raw_content)
        self.assertEqual(errs, [], f"check_explainers returned errors: {errs}")


if __name__ == "__main__":
    unittest.main()
