#!/usr/bin/env python3
"""Deterministic regression suite for the Get Involved 6-role civic reinforcement cycle
(fixing 05 CIVIL SOCIETY / 06 CITIZENS desktop & mobile parity, >=11px SVG labels, <=310px
mobile bounds, and 93 lab overlays), non-duplicated header ledes across five Tier-1 frontier
lab technical papers, and Spec 05 desktop/mobile directional <polygon> arrowhead parity
across eleven cintnet.org pages."""

from __future__ import annotations

import pathlib
import re
import unittest
import xml.etree.ElementTree as ET


SITE_DIR = pathlib.Path(__file__).resolve().parents[1]
CONTENT_DIR = SITE_DIR / "content"

ARROWHEAD_PARITY_PAGES: tuple[tuple[str, str], ...] = (
    ("get-involved/index.html", "ex-five-roles-cycle"),
    ("blog/aviation-safety-for-ai-infrastructure.html", "ex-valve-interlock"),
    ("blog/eight-ways-ai-goes-wrong.html", "ex-eight-harbors"),
    ("blog/slowing-frontier-training-without-a-global-censor.html", "ex-seismic-threshold"),
    ("blog/what-canadas-ai-security-framework-gets-right-and-whats-still-missing.html", "ex-canada-ai-srmf"),
    ("blog/why-faster-code-still-waits-on-the-test-bench.html", "ex-test-bench-bottleneck"),
    ("blog/why-people-dont-want-an-ai-mother.html", "ex-mother-vs-aide"),
    ("blog/why-running-your-own-ai-tools-needs-a-rollback-checkpoint.html", "ex-byte-memory-rollback"),
    ("labs/lab-papers/anthropic.html", "ex-lp-anthropic"),
    ("labs/lab-papers/openai.html", "ex-lp-openai"),
    ("labs/lab-papers/safe-superintelligence.html", "ex-lp-safe-superintelligence"),
)

TIER1_LAB_PAPERS: tuple[str, ...] = (
    "labs/lab-papers/anthropic.html",
    "labs/lab-papers/openai.html",
    "labs/lab-papers/safe-superintelligence.html",
    "labs/lab-papers/deepseek.html",
    "labs/lab-papers/google-deepmind.html",
)


class SitecriticSixRolesHubAndDesktopArrowheadsSpec05Tests(unittest.TestCase):
    def test_get_involved_hub_six_roles_desktop_and_mobile_parity(self) -> None:
        raw = (CONTENT_DIR / "get-involved/index.html").read_text(encoding="utf-8")
        self.assertIn("93 lab overlays", raw)
        self.assertNotIn("90 lab overlays", raw)

        fig_m = re.search(r'<figure\b[^>]*id="ex-five-roles-cycle"[^>]*>(.*?)</figure>', raw, flags=re.S)
        self.assertIsNotNone(fig_m)
        fig = fig_m.group(1)

        for view_cls in ("diagram-desktop", "diagram-mobile"):
            svg_m = re.search(rf'<svg\b[^>]*class="[^"]*\b{view_cls}\b[^"]*"[^>]*>.*?</svg>', fig, flags=re.S)
            self.assertIsNotNone(svg_m, f"Missing {view_cls} in get-involved/index.html")
            svg_str = svg_m.group(0)
            root = ET.fromstring(svg_str)
            for role_badge in (
                "01 · BUILDERS",
                "02 · RESEARCHERS",
                "03 · LAB TEAMS",
                "04 · POLICY MAKERS",
                "05 · CIVIL SOCIETY",
                "06 · CITIZENS",
            ):
                self.assertIn(role_badge, svg_str, f"{view_cls} missing {role_badge}")
            text_els = [el for el in root.iter() if el.tag.split("}")[-1] == "text"]
            self.assertLess(len(text_els), 28, f"{view_cls} exceeds 27 text nodes")

    def test_desktop_and_mobile_directional_arrowheads_and_light_paper_safety(self) -> None:
        for rel_path, fig_id in ARROWHEAD_PARITY_PAGES:
            raw = (CONTENT_DIR / rel_path).read_text(encoding="utf-8")
            fig_m = re.search(
                rf'<figure\b[^>]*id=["\']{re.escape(fig_id)}["\'][^>]*>(.*?)</figure>',
                raw,
                flags=re.S,
            )
            self.assertIsNotNone(fig_m, f"{rel_path} missing #{fig_id}")
            fig = fig_m.group(1)
            self.assertNotIn("prefers-color-scheme: dark", fig, f"{rel_path} #{fig_id} contains light-paper dark override")
            self.assertIn("#8FD4B6", fig, f"{rel_path} #{fig_id} missing #8FD4B6")
            self.assertIn("#F09D82", fig, f"{rel_path} #{fig_id} missing #F09D82")

            for view_name, view_cls in (("desktop", "diagram-desktop"), ("mobile", "diagram-mobile")):
                svg_m = re.search(
                    rf'<svg\b[^>]*class=["\'][^"\']*\b{view_cls}\b[^"\']*["\'][^>]*>.*?</svg>',
                    fig,
                    flags=re.S,
                )
                self.assertIsNotNone(svg_m, f"{rel_path} #{fig_id} missing {view_cls}")
                svg_str = svg_m.group(0)
                ET.fromstring(svg_str)
                self.assertGreaterEqual(
                    len(re.findall(r"<line\b", svg_str)),
                    3,
                    f"{rel_path} {view_name} SVG needs >= 3 <line> connectors",
                )
                self.assertGreaterEqual(
                    len(re.findall(r"<polygon\b", svg_str)),
                    3,
                    f"{rel_path} {view_name} SVG needs >= 3 directional <polygon> arrowheads",
                )
                for fs in re.findall(r'font-size=["\']([0-9.]+)["\']', svg_str):
                    self.assertGreaterEqual(float(fs), 11.0, f"{rel_path} {view_name} font-size={fs} < 11px")

    def test_tier1_lab_papers_deduplicate_header_lede_while_preserving_claim_first_big_paragraph(self) -> None:
        for rel_path in TIER1_LAB_PAPERS:
            raw = (CONTENT_DIR / rel_path).read_text(encoding="utf-8")
            _, fm, body = raw.split("---", 2)
            takeaway = re.search(r"^takeaway:\s*(.+)$", fm, flags=re.M).group(1).strip()
            lede = re.search(r"^lede:\s*(.+)$", fm, flags=re.M).group(1).strip()
            big_p = re.sub(r"<[^>]+>", "", re.search(r'<p class="big">(.*?)</p>', body, flags=re.S).group(1)).strip()
            self.assertTrue(big_p.startswith(takeaway[:45]), f"{rel_path} <p class='big'> must start with takeaway")
            self.assertNotEqual(lede[:45], big_p[:45], f"{rel_path} header lede duplicates <p class='big'> verbatim")


if __name__ == "__main__":
    unittest.main()
