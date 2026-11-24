#!/usr/bin/env python3
"""Deterministic verification suite for /labs/sovereign-authorities/ (30 Sovereign & Global AI Authorities)."""

from __future__ import annotations

import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = SITE_ROOT / "content"
SOVEREIGN_HTML = CONTENT_DIR / "labs" / "sovereign-authorities.html"
SOVEREIGN_JS = SITE_ROOT / "assets" / "js" / "sovereign-authorities.js"
UPSTREAM_JSON = Path("research/institutions/sovereign_overlays_30.json")

if str(SITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SITE_ROOT))

import build  # noqa: E402


class TestSovereignAuthoritiesWorkbench(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = SOVEREIGN_HTML.read_text(encoding="utf-8")
        cls.js = SOVEREIGN_JS.read_text(encoding="utf-8")
        m = re.search(
            r'<script type="application/json" id="sovereign-authorities-data">(.*?)</script>',
            cls.html,
            flags=re.S,
        )
        assert m is not None, "Missing #sovereign-authorities-data JSON payload in sovereign-authorities.html"
        cls.bundle = json.loads(m.group(1))

    def test_frontmatter_route_and_companion_hub_links(self) -> None:
        meta = build.parse(SOVEREIGN_HTML)
        self.assertEqual(meta["route"], "/labs/sovereign-authorities/")
        self.assertEqual(meta.get("template"), "page")
        self.assertEqual(meta.get("layout"), "wide")
        self.assertEqual(meta.get("section"), "labs")
        self.assertEqual(meta.get("script"), "sovereign-authorities.js")

        self.assertIn('href="/labs/sovereign-papers/"', self.html)
        self.assertIn('href="/labs/lab-overlays/"', self.html)

    def test_30_authorities_cohorts_codes_and_8_flagship_papers(self) -> None:
        entities = self.bundle.get("entities", [])
        self.assertEqual(len(entities), 30)
        nats = [e for e in entities if e.get("cohort") == "national_authority"]
        muls = [e for e in entities if e.get("cohort") == "multilateral_authority"]
        self.assertEqual(len(nats), 20)
        self.assertEqual(len(muls), 10)

        codes = [e.get("code") for e in entities]
        self.assertEqual(codes[:20], [f"SOV-{i:02d}" for i in range(1, 21)])
        self.assertEqual(codes[20:], [f"MUL-{i:02d}" for i in range(1, 11)])

        paper_map = {e["id"]: e["sovereign_paper_url"] for e in entities if e.get("sovereign_paper_url")}
        self.assertEqual(
            paper_map,
            {
                "united_states": "/labs/sovereign-papers/united-states/",
                "china": "/labs/sovereign-papers/china/",
                "european_union": "/labs/sovereign-papers/european-union/",
                "united_kingdom": "/labs/sovereign-papers/united-kingdom/",
                "canada": "/labs/sovereign-papers/canada/",
                "japan": "/labs/sovereign-papers/japan/",
                "india": "/labs/sovereign-papers/india/",
                "un_multilateral": "/labs/sovereign-papers/un-multilateral/",
            },
        )

        if UPSTREAM_JSON.exists():
            upstream = json.loads(UPSTREAM_JSON.read_text(encoding="utf-8"))
            self.assertEqual(self.bundle, upstream)

    def test_five_axes_and_150_unique_bespoke_cells(self) -> None:
        axes = self.bundle.get("axes", [])
        self.assertEqual(len(axes), 5)
        axis_ids = [a.get("id") for a in axes]
        self.assertEqual(
            axis_ids,
            [
                "a1_frontier_safety_teeth",
                "a2_public_over_private_capture",
                "a3_citizen_vault_vs_surveillance",
                "a4_public_compute_and_shared_economy",
                "a5_treaty_verification_and_second_road",
            ],
        )
        self.assertEqual([a.get("code") for a in axes], [f"AX-{i:02d}" for i in range(1, 6)])

        citizen_cells: list[str] = []
        state_cells: list[str] = []
        for entity in self.bundle["entities"]:
            self.assertTrue(entity.get("specialized_agent_id", "").startswith("cin.sovereign."))
            self.assertEqual(len(entity.get("where_they_converge", [])), 2)
            self.assertEqual(len(entity.get("where_they_deviate", [])), 2)
            self.assertGreater(len(entity.get("statutory_and_treaty_step", "")), 30)
            overlays = entity.get("axis_overlays", {})
            self.assertEqual(set(overlays.keys()), set(axis_ids))
            for aid in axis_ids:
                cell = overlays[aid]
                self.assertIn(cell.get("score"), (1, 2, 3, 4, 5))
                cit = cell.get("citizen_impact", "").strip()
                st = cell.get("state_and_lab_impact", "").strip()
                self.assertGreater(len(cit), 30)
                self.assertGreater(len(st), 30)
                citizen_cells.append(cit.lower())
                state_cells.append(st.lower())

        self.assertEqual(len(citizen_cells), 150)
        self.assertEqual(len(set(citizen_cells)), 150)
        self.assertEqual(len(state_cells), 150)
        self.assertEqual(len(set(state_cells)), 150)

    def test_svg_topology_accessibility_and_mount_ids(self) -> None:
        fig_m = re.search(
            r'<figure class="explainer" id="ex-sovereign-authorities-topology">.*?</figure>',
            self.html,
            flags=re.S,
        )
        self.assertIsNotNone(fig_m)
        svg_m = re.search(r"<svg\b[^>]*>.*?</svg>", fig_m.group(0), flags=re.S)
        self.assertIsNotNone(svg_m)
        root = ET.fromstring(svg_m.group(0))
        text_nodes = [el for el in root.iter() if el.tag.split("}")[-1] == "text"]
        self.assertLess(len(text_nodes), 24)

        font_sizes = [float(fs) for fs in re.findall(r'font-size=["\']([0-9.]+)["\']', svg_m.group(0))]
        self.assertTrue(font_sizes)
        self.assertGreaterEqual(min(font_sizes), 10.5)

        for dom_id in (
            "sa-axis-bar",
            "sa-axis-banner",
            "sa-wb-status",
            "sa-select-a",
            "sa-select-b",
            "sa-swap-btn",
            "sa-pair-stage",
            "sa-cohort-bar",
            "sa-search",
            "sa-region",
            "sa-sort",
            "sa-reset",
            "sa-count-status",
            "sa-rows",
            "sa-more-wrap",
            "sa-more-btn",
        ):
            self.assertIn(f'id="{dom_id}"', self.html)

        self.assertIn('value="united_states"', self.html)
        self.assertIn('value="china"', self.html)

    def test_pure_dom_js_and_comparator_labels(self) -> None:
        for forbidden_js in (
            "innerHTML",
            "outerHTML",
            "insertAdjacentHTML",
            "document.write(",
            "eval(",
            "new Function(",
            "fetch(",
            "XMLHttpRequest",
        ):
            self.assertNotIn(forbidden_js, self.js)

        for required_token in (
            '"united_states"',
            '"china"',
            "Read Sovereign Paper ↗",
            "Sovereign Paper ↗",
            "sa-paper-btn",
            "WHERE PUBLIC-INTEREST POLICY CONVERGES WITH CIN",
            "WHERE PRIVATE CAPTURE OR STATE OVERREACH DEVIATES TODAY",
            "EFFECT ON CITIZENS & WORKERS",
            "EFFECT ON DOMESTIC LABS & AGENCIES",
            "PROPOSED STATUTORY & TREATY STEP",
        ):
            self.assertIn(required_token, self.js)

    def test_six_verified_footnotes(self) -> None:
        fn_m = re.search(r'<section class="footnotes">(.*?)</section>', self.html, flags=re.S)
        self.assertIsNotNone(fn_m)
        fn_block = fn_m.group(1)
        for fn_id in ("fn1", "fn2", "fn3", "fn4", "fn5", "fn6"):
            self.assertIn(f'id="{fn_id}"', fn_block)
        for expected_ref in (
            "https://arxiv.org/abs/2402.08797",
            "https://arxiv.org/abs/2602.09678",
            "https://arxiv.org/abs/2411.15149",
            "https://arxiv.org/abs/2501.07913",
            "https://doi.org/10.1257/aer.100.3.641",
            "https://doi.org/10.3386/w24174",
        ):
            self.assertIn(expected_ref, fn_block)

    def test_strict_voice_sentence_bounds_and_read_only_build_check(self) -> None:
        _, _, body = self.html.split("---", 2)
        prose = re.sub(
            r"<(aside|section class=\"footnotes\"|style|svg|script).*?</(?:aside|section|style|svg|script)>",
            " ",
            body,
            flags=re.S,
        )
        prose = re.sub(r"</(h\d|p|li|ol|ul|div|button|figcaption)>", ". ", prose)
        prose = re.sub(r"<[^>]+>", " ", prose)
        self.assertNotIn("\u2014", prose)
        self.assertNotIn("\u2013", prose)
        self.assertIsNone(re.search(r"\brather\s+than\b", prose, re.I))

        sentences = [s.strip() for s in re.split(r"[.!?]\s+", prose) if len(s.strip().split()) >= 4]
        lengths = sorted(len(s.split()) for s in sentences)
        median_len = lengths[len(lengths) // 2]
        max_len = max(lengths)
        self.assertLessEqual(median_len, 22)
        self.assertLessEqual(max_len, 28)

        build.WARNINGS.clear()
        meta = build.parse(SOVEREIGN_HTML)
        rendered_main = build.inject_img_dimensions(
            build.enrich_collapsible_disclosures(build.render_page(meta))
        )
        doc = build.page_shell(meta, rendered_main)
        errs = (
            build.check_page(meta, doc)
            + build.check_citations_and_prose([meta])
            + build.check_js()
            + build.check_viewport_zoom_scalability(meta["route"], doc)
            + build.check_html_lang_and_charset(meta["route"], doc)
        )
        self.assertEqual(errs, [])
        self.assertEqual(build.WARNINGS, [])


if __name__ == "__main__":
    unittest.main()
