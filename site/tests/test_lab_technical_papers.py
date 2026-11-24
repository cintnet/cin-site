#!/usr/bin/env python3
"""Deterministic verification suite for per-lab technical papers (/labs/lab-papers/ and knowledge/lab_papers/)."""

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
LAB_PAPERS_HTML_DIR = CONTENT_DIR / "labs" / "lab-papers"
CIN_LAB_PAPERS_MD_DIR = Path("knowledge/lab_papers")

EXPECTED_FLAGSHIP_PAPERS: tuple[tuple[str, str, str], ...] = (
    ("LAB-01", "anthropic", "Anthropic"),
    ("LAB-02", "google-deepmind", "Google DeepMind"),
    ("LAB-03", "openai", "OpenAI"),
    ("LAB-05", "meta-ai", "Meta AI"),
    ("LAB-06", "mistral-ai", "Mistral"),
    ("LAB-08", "safe-superintelligence", "Safe Superintelligence"),
    ("LAB-14", "deepseek", "DeepSeek"),
    ("LAB-15", "alibaba-qwen", "Qwen"),
    ("LAB-27", "physical-intelligence", "Physical Intelligence"),
    ("LAB-41", "world-labs", "World Labs"),
    ("LAB-42", "ami-labs", "AMI Labs"),
    ("LAB-43", "verses-ai", "VERSES AI"),
)


class TestLabTechnicalPapers(unittest.TestCase):
    def test_hub_and_all_12_flagship_html_papers_exist_and_pass_build_checks(self) -> None:
        hub_path = LAB_PAPERS_HTML_DIR / "index.html"
        self.assertTrue(hub_path.is_file(), f"Missing hub page {hub_path}")

        all_files = [hub_path] + [LAB_PAPERS_HTML_DIR / f"{slug}.html" for _, slug, _ in EXPECTED_FLAGSHIP_PAPERS]
        seen_titles: set[str] = set()
        seen_descs: set[str] = set()

        build.WARNINGS.clear()
        for html_path in all_files:
            self.assertTrue(html_path.is_file(), f"Missing HTML technical paper {html_path}")
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

    def test_each_flagship_paper_has_5_sections_dossier_svg_researcher_aside_and_footnotes(self) -> None:
        for code, slug, name_sub in EXPECTED_FLAGSHIP_PAPERS:
            html_path = LAB_PAPERS_HTML_DIR / f"{slug}.html"
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

    def test_canonical_markdown_papers_in_cin_knowledge_exist_and_have_depth(self) -> None:
        if not CIN_LAB_PAPERS_MD_DIR.is_dir():
            self.skipTest("knowledge/lab_papers not mounted in this environment")

        readme = CIN_LAB_PAPERS_MD_DIR / "README.md"
        self.assertTrue(readme.is_file(), "Missing knowledge/lab_papers/README.md")
        readme_txt = readme.read_text(encoding="utf-8")
        self.assertIn("LAB-43", readme_txt)

        for code, slug, name_sub in EXPECTED_FLAGSHIP_PAPERS:
            md_path = CIN_LAB_PAPERS_MD_DIR / f"{code}-{slug}.md"
            self.assertTrue(md_path.is_file(), f"Missing canonical Markdown paper {md_path}")
            md_txt = md_path.read_text(encoding="utf-8")
            self.assertIn(name_sub, md_txt)
            self.assertIn("```mermaid", md_txt, f"Missing Mermaid diagram in {md_path.name}")
            self.assertGreaterEqual(
                len(md_txt.split()),
                1100,
                f"Expected >= 1100 words of technical specification in {md_path.name}",
            )

    def test_cross_links_between_overlays_research_labs_and_technical_papers(self) -> None:
        overlays_html = (CONTENT_DIR / "labs" / "lab-overlays.html").read_text(encoding="utf-8")
        m = re.search(
            r'<script type="application/json" id="lab-overlays-data">(.*?)</script>',
            overlays_html,
            flags=re.S,
        )
        assert m is not None
        bundle = json.loads(m.group(1))
        linked_urls = [
            e["technical_paper_url"]
            for e in bundle["entities"]
            if e.get("technical_paper_url")
        ]
        self.assertEqual(len(linked_urls), 12)
        for url in linked_urls:
            slug = url.strip("/").split("/")[-1]
            self.assertTrue(
                (LAB_PAPERS_HTML_DIR / f"{slug}.html").is_file(),
                f"technical_paper_url {url} missing matching HTML file",
            )

        for rel in ("labs/index.html", "labs/lab-overlays.html", "research.html", "get-involved/labs.html"):
            txt = (CONTENT_DIR / rel).read_text(encoding="utf-8")
            self.assertIn("/labs/lab-papers/", txt, f"Missing /labs/lab-papers/ cross-link in {rel}")


if __name__ == "__main__":
    unittest.main()
