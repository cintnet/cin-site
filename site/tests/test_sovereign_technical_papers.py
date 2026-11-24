#!/usr/bin/env python3
"""Deterministic verification suite for sovereign AI governance papers (/labs/sovereign-papers/ and knowledge/sovereign_papers/)."""

from __future__ import annotations

import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1]
if str(SITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SITE_ROOT))

import build  # noqa: E402

CONTENT_DIR = SITE_ROOT / "content"
SOV_PAPERS_HTML_DIR = CONTENT_DIR / "labs" / "sovereign-papers"
SOV_AUTH_HTML = CONTENT_DIR / "labs" / "sovereign-authorities.html"
CIN_SOV_PAPERS_MD_DIR = Path("knowledge/sovereign_papers")

EXPECTED_FLAGSHIP_SOVEREIGNS: tuple[tuple[str, str, str], ...] = (
    ("SOV-01", "united-states", "United States"),
    ("SOV-02", "china", "China"),
    ("SOV-03", "european-union", "European Union"),
    ("SOV-04", "united-kingdom", "United Kingdom"),
    ("SOV-05", "canada", "Canada"),
    ("SOV-06", "japan", "Japan"),
    ("SOV-09", "india", "India"),
    ("MUL-01", "un-multilateral", "United Nations"),
)


class TestSovereignTechnicalPapers(unittest.TestCase):
    def test_hub_and_all_8_flagship_sovereign_html_papers_exist_and_pass_build_checks(self) -> None:
        hub_path = SOV_PAPERS_HTML_DIR / "index.html"
        self.assertTrue(hub_path.is_file(), f"Missing hub page {hub_path}")

        all_files = [hub_path] + [SOV_PAPERS_HTML_DIR / f"{slug}.html" for _, slug, _ in EXPECTED_FLAGSHIP_SOVEREIGNS]
        seen_titles: set[str] = set()
        seen_descs: set[str] = set()

        build.WARNINGS.clear()
        for html_path in all_files:
            self.assertTrue(html_path.is_file(), f"Missing sovereign HTML paper {html_path}")
            meta = build.parse(html_path)
            doc = build.page_shell(meta, meta["body"])
            errs = build.check_page(meta, doc)
            self.assertEqual(errs, [], f"build.check_page errors in {html_path.name}: {errs}")

            norm_title = meta["title"].strip().casefold()
            norm_desc = meta["description"].strip().casefold()
            self.assertNotIn(norm_title, seen_titles, f"Duplicate title in {html_path.name}")
            self.assertNotIn(norm_desc, seen_descs, f"Duplicate description in {html_path.name}")
            seen_titles.add(norm_title)
            seen_descs.add(norm_desc)

        self.assertEqual(build.WARNINGS, [], f"Unexpected build warnings: {build.WARNINGS}")

    def test_each_sovereign_paper_has_5_sections_dossier_svg_researcher_aside_and_footnotes(self) -> None:
        for code, slug, name_sub in EXPECTED_FLAGSHIP_SOVEREIGNS:
            html_path = SOV_PAPERS_HTML_DIR / f"{slug}.html"
            raw = html_path.read_text(encoding="utf-8")
            self.assertIn(code, raw, f"Missing {code} in {slug}.html")
            self.assertIn(name_sub, raw, f"Missing {name_sub} in {slug}.html")
            self.assertIn('class="lp-dossier"', raw, f"Missing .lp-dossier in {slug}.html")
            for sec_n in range(1, 6):
                self.assertIn(f'id="sec-{sec_n}"', raw, f"Missing #sec-{sec_n} in {slug}.html")

            self.assertIn('<aside class="for-researchers">', raw, f"Missing researcher aside in {slug}.html")
            self.assertIn('<section class="footnotes">', raw, f"Missing footnotes section in {slug}.html")

            svg_m = re.search(r"<svg\b[^>]*>.*?</svg>", raw, flags=re.S)
            self.assertIsNotNone(svg_m, f"Missing inline <svg> diagram in {slug}.html")
            root = ET.fromstring(svg_m.group(0))
            text_nodes = [el for el in root.iter() if el.tag.split("}")[-1] == "text"]
            self.assertLess(len(text_nodes), 28, f"Too many <text> nodes in {slug}.html SVG")

    def test_canonical_markdown_sovereign_papers_in_cin_knowledge_exist_and_have_depth(self) -> None:
        if not CIN_SOV_PAPERS_MD_DIR.is_dir():
            self.skipTest("knowledge/sovereign_papers not mounted in this environment")

        readme = CIN_SOV_PAPERS_MD_DIR / "README.md"
        self.assertTrue(readme.is_file(), "Missing knowledge/sovereign_papers/README.md")
        readme_txt = readme.read_text(encoding="utf-8")
        self.assertIn("MUL-01", readme_txt)

        for code, slug, name_sub in EXPECTED_FLAGSHIP_SOVEREIGNS:
            md_path = CIN_SOV_PAPERS_MD_DIR / f"{code}-{slug}.md"
            self.assertTrue(md_path.is_file(), f"Missing canonical Markdown paper {md_path}")
            md_txt = md_path.read_text(encoding="utf-8")
            self.assertIn(name_sub, md_txt)
            self.assertIn("```mermaid", md_txt, f"Missing Mermaid diagram in {md_path.name}")
            self.assertGreaterEqual(
                len(md_txt.split()),
                1100,
                f"Expected >= 1100 words of technical specification in {md_path.name}",
            )

    def test_cross_links_across_observatory_policy_labs_and_sovereign_workbench(self) -> None:
        self.assertTrue(SOV_AUTH_HTML.is_file(), "Missing /labs/sovereign-authorities/ page")
        for rel in (
            "index.html",
            "labs/index.html",
            "labs/observatory.html",
            "labs/lab-overlays.html",
            "labs/lab-papers/index.html",
            "get-involved/policy.html",
            "research.html",
        ):
            txt = (CONTENT_DIR / rel).read_text(encoding="utf-8")
            self.assertIn("/labs/sovereign-papers/", txt, f"Missing /labs/sovereign-papers/ link in {rel}")


if __name__ == "__main__":
    unittest.main()
