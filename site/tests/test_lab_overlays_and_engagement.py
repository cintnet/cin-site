#!/usr/bin/env python3
"""Deterministic verification suite for /labs/lab-overlays/ and active AI-lab & safety engagement."""

from __future__ import annotations

import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = SITE_ROOT / "content"
OVERLAYS_HTML = CONTENT_DIR / "labs" / "lab-overlays.html"
OVERLAYS_JS = SITE_ROOT / "assets" / "js" / "lab-overlays.js"


class TestLabOverlaysAndEngagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = OVERLAYS_HTML.read_text(encoding="utf-8")
        cls.js = OVERLAYS_JS.read_text(encoding="utf-8")
        m = re.search(
            r'<script type="application/json" id="lab-overlays-data">(.*?)</script>',
            cls.html,
            flags=re.S,
        )
        assert m is not None, "Missing #lab-overlays-data JSON payload in lab-overlays.html"
        cls.bundle = json.loads(m.group(1))

    def test_93_entities_43_labs_and_50_safety_groups(self) -> None:
        entities = self.bundle.get("entities", [])
        self.assertEqual(len(entities), 93)
        labs = [e for e in entities if e.get("cohort") == "main_ai_lab"]
        safety = [e for e in entities if e.get("cohort") == "safety_lab_researcher"]
        self.assertEqual(len(labs), 43)
        self.assertEqual(len(safety), 50)

        codes = [e.get("code") for e in entities]
        self.assertEqual(codes[:43], [f"LAB-{i:02d}" for i in range(1, 44)])
        self.assertEqual(codes[43:], [f"SAF-{i:02d}" for i in range(1, 51)])

        paper_urls = [e.get("technical_paper_url") for e in labs if e.get("technical_paper_url")]
        self.assertEqual(len(paper_urls), 12)
        self.assertIn("lo-paper-btn", self.js)

        names_blob = " | ".join(e.get("name", "") for e in entities)
        for required_name in (
            "Anthropic",
            "Google DeepMind",
            "OpenAI",
            "Cohere",
            "Mistral",
            "DeepSeek",
            "World Labs",
            "AMI Labs",
            "VERSES AI",
            "UK AI",
            "METR",
            "Redwood Research",
            "Apollo Research",
            "LawZero",
            "Cooperative AI Foundation",
        ):
            self.assertIn(required_name, names_blob)

    def test_six_scenarios_and_six_societal_ledger_domains(self) -> None:
        scenarios = self.bundle.get("scenarios", [])
        domains = self.bundle.get("ledger_societal_domains", [])
        self.assertEqual(len(scenarios), 6)
        self.assertEqual(len(domains), 6)

        domain_ids = [d.get("id") for d in domains]
        self.assertEqual(
            domain_ids,
            ["legal", "corporate", "humanitarian", "political", "economic", "diplomatic"],
        )
        for d in domains:
            for key in (
                "today_failure",
                "ledger_principle",
                "individual_effect",
                "institutional_effect",
                "open_hard_problem",
            ):
                self.assertTrue(len(d.get(key, "").strip()) > 25, f"Missing {key} in {d.get('id')}")

        scen_ids = [s.get("id") for s in scenarios]
        for entity in self.bundle["entities"]:
            self.assertTrue(entity.get("specialized_agent_id", "").startswith("cin.liaison."))
            self.assertEqual(len(entity.get("where_they_converge", [])), 2)
            self.assertEqual(len(entity.get("where_they_deviate", [])), 2)
            self.assertTrue(len(entity.get("engagement_brief", "")) > 25)
            overlays = entity.get("scenario_overlays", {})
            self.assertEqual(set(overlays.keys()), set(scen_ids))
            for sid in scen_ids:
                cell = overlays[sid]
                self.assertIn(cell.get("readiness"), (1, 2, 3, 4, 5))
                self.assertTrue(len(cell.get("individual_impact", "")) > 25)
                self.assertTrue(len(cell.get("organization_impact", "")) > 25)

    def test_svg_topology_and_planar_mount_ids(self) -> None:
        fig_m = re.search(
            r'<figure class="explainer" id="ex-lab-overlays-topology">.*?</figure>',
            self.html,
            flags=re.S,
        )
        self.assertIsNotNone(fig_m)
        svg_m = re.search(r"<svg\b[^>]*>.*?</svg>", fig_m.group(0), flags=re.S)
        self.assertIsNotNone(svg_m)
        root = ET.fromstring(svg_m.group(0))
        text_nodes = [el for el in root.iter() if el.tag.split("}")[-1] == "text"]
        self.assertLess(len(text_nodes), 28)

        font_sizes = [float(fs) for fs in re.findall(r'font-size=["\']([0-9.]+)["\']', svg_m.group(0))]
        self.assertGreaterEqual(min(font_sizes), 10.0)

        for dom_id in (
            "lo-domain-rail",
            "lo-domain-stage",
            "lo-domain-status",
            "lo-scenario-bar",
            "lo-scenario-banner",
            "lo-wb-status",
            "lo-select-a",
            "lo-select-b",
            "lo-swap-btn",
            "lo-pair-stage",
            "lo-cohort-bar",
            "lo-search",
            "lo-region",
            "lo-sort",
            "lo-reset",
            "lo-count-status",
            "lo-rows",
            "lo-more-wrap",
            "lo-more-btn",
        ):
            self.assertIn(f'id="{dom_id}"', self.html)

    def test_client_js_uses_pure_dom_without_innerhtml_or_fetch(self) -> None:
        self.assertNotIn("innerHTML", self.js)
        self.assertNotIn("outerHTML", self.js)
        self.assertNotIn("fetch(", self.js)

    def test_voice_and_sentence_bounds_on_overlays_prose(self) -> None:
        _, _, body = self.html.split("---", 2)
        prose = re.sub(
            r"<(aside|section class=\"footnotes\"|style|svg|figcaption|script).*?</(?:aside|section|style|svg|figcaption|script)>",
            " ",
            body,
            flags=re.S,
        )
        prose = re.sub(r"</(h\d|p|li|ol|ul|div|button)>", ". ", prose)
        prose = re.sub(r"<[^>]+>", " ", prose)
        self.assertNotIn("\u2014", prose)

        sentences = [s.strip() for s in re.split(r"[.!?]\s+", prose) if len(s.strip().split()) >= 4]
        lengths = sorted(len(s.split()) for s in sentences)
        median_len = lengths[len(lengths) // 2]
        max_len = max(lengths)
        self.assertLessEqual(median_len, 22)
        self.assertLessEqual(max_len, 34)

    def test_site_wide_cross_links_and_no_isolationist_lab_disclaimers(self) -> None:
        for rel in (
            "labs/index.html",
            "labs/institutions.html",
            "get-involved/labs.html",
            "get-involved/researchers.html",
            "about/governance.html",
            "about/others.html",
            "vision.html",
        ):
            content = (CONTENT_DIR / rel).read_text(encoding="utf-8")
            self.assertIn("/labs/lab-overlays/", content, f"Missing cross-link in {rel}")

        banned_phrases = (
            "do not partner with large ai labs",
            "don't work with large ai labs",
            "do not work with large ai labs",
            "refuse to engage with ai labs",
        )
        for html_file in CONTENT_DIR.rglob("*.html"):
            lower = html_file.read_text(encoding="utf-8").lower()
            for phrase in banned_phrases:
                self.assertNotIn(phrase, lower, f"Isolationist phrase '{phrase}' found in {html_file}")


if __name__ == "__main__":
    unittest.main()
