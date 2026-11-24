#!/usr/bin/env python3
"""Regression suite for Spec 05 diagram geometry, dark-mode contrast, claim-first openings,
and five-primitive Base Thesis grounding across the three core personal-assistant essays
and the labs/researchers get-involved guides."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = SITE_DIR / "content"

ESSAY_PAGES = (
    ("blog/an-assistant-that-works-only-for-you.html", "ex-skin-not-glass"),
    ("blog/how-an-ai-assistant-should-say-it-might-be-wrong.html", "ex-honest-uncertainty"),
    ("blog/how-to-tell-if-an-ai-assistant-works-for-you.html", "ex-loyalty-test"),
)

GUIDE_PAGES = (
    ("get-involved/labs.html", "ex-lab-safeguards"),
    ("get-involved/researchers.html", "ex-research-agenda"),
)

REQUIRED_PRIMITIVE_TERMS = (
    "egocentric",
    "sensorium",
    "Device Time",
    "observation confidence",
    "PUF",
    "TCG DICE",
    "DMTF SPDM",
    "IETF RATS",
    "data diode",
    "IEC 61508",
    "dead-man",
    "transduction realism",
    "analog hole",
    "C2PA",
    "Merkle",
    "episodic memory vault",
    "Extended Mind",
    "monogamous",
    "personal cognitive model",
    "exocortex",
    "information fiduciary",
    "Good Regulator",
    "do(x)",
    "Markov blanket",
    "Private Autobiographical Ledger",
    "Public Attestation &amp; Escrow Ledger",
    "zero-knowledge",
    "IETF SCITT",
    "Object-Capability",
    "Byzantine",
    "polycentric",
    "Wide Network Ledger",
    "Universal Basic Services",
    "merit-bonded",
    "mutual credit",
    "Meidner",
    "frontier-lab overlays",
    "Ostrom",
)

REQUIRED_CITATIONS = (
    "Balkin, 2016",
    "Friston, 2010",
    "Pearl, 2009",
    "Clark &amp; Chalmers, 1998",
    "Thompson, 1984",
    "Conant &amp; Ashby, 1970",
    "Dennis &amp; Van Horn, 1966",
    "Ostrom, 1990",
    "Bracale Syrnikov et al., 2026",
)


class SitecriticThreePersonalAssistantEssaysAndGuidesSpec05Tests(unittest.TestCase):
    def test_three_essays_claim_first_openings_and_zero_negative_contrasts(self) -> None:
        for rel_path, _ in ESSAY_PAGES:
            raw = (CONTENT_DIR / rel_path).read_text(encoding="utf-8")
            _, fm, body = raw.split("---", 2)
            m_takeaway = re.search(r"^takeaway:\s*(.+)$", fm, flags=re.M)
            self.assertIsNotNone(m_takeaway, f"{rel_path} missing takeaway front-matter")
            takeaway = m_takeaway.group(1).strip()

            m_first_p = re.search(r"<p>(.*?)</p>", body, flags=re.S)
            self.assertIsNotNone(m_first_p, f"{rel_path} missing opening <p>")
            first_p = re.sub(r"<[^>]+>", "", m_first_p.group(1)).strip()
            self.assertTrue(
                first_p.startswith(takeaway),
                f"{rel_path} opening paragraph must begin with exact takeaway claim",
            )

            everyday = re.sub(
                r'<aside class="for-researchers">.*?</aside>', "", body, flags=re.S
            )
            everyday = re.sub(
                r'<section class="footnotes">.*?</section>', "", everyday, flags=re.S
            )
            everyday = re.sub(
                r'<figure class="explainer"[^>]*>.*?</figure>', "", everyday, flags=re.S
            )
            text_only = re.sub(r"<[^>]+>", " ", everyday)
            self.assertIsNone(
                re.search(r"\brather than\b", text_only, flags=re.I),
                f"{rel_path} everyday prose contains negative contrast 'rather than'",
            )
            self.assertIsNone(
                re.search(r"\binstead of\b", text_only, flags=re.I),
                f"{rel_path} everyday prose contains negative contrast 'instead of'",
            )
            self.assertIsNone(
                re.search(r"(?:^|[.!?]\s+)Instead,", text_only),
                f"{rel_path} everyday prose contains sentence-initial 'Instead,'",
            )

    def test_all_five_explainers_satisfy_spec05_unboxed_dark_mode_and_mobile_bounds(self) -> None:
        for rel_path, fig_id in ESSAY_PAGES + GUIDE_PAGES:
            raw = (CONTENT_DIR / rel_path).read_text(encoding="utf-8")
            m_fig = re.search(
                rf'<figure class="explainer" id="{re.escape(fig_id)}">(.*?)</figure>',
                raw,
                flags=re.S,
            )
            self.assertIsNotNone(m_fig, f"{rel_path} missing figure#{fig_id}")
            fig = m_fig.group(1)

            self.assertIn("background: transparent", fig, rel_path)
            self.assertIn("prefers-color-scheme: dark", fig, rel_path)
            self.assertIn(':root[data-theme="dark"]', fig, rel_path)
            self.assertIn("#8FD4B6", fig, rel_path)
            self.assertIn("#F09D82", fig, rel_path)

            m_mobile = re.search(
                r'<svg class="diagram-mobile"[^>]*>(.*?)</svg>', fig, flags=re.S
            )
            self.assertIsNotNone(m_mobile, f"{rel_path} missing .diagram-mobile SVG")
            mobile_svg = m_mobile.group(1)

            for m_rect in re.finditer(r"<rect\b([^>]*)/?>", mobile_svg):
                attrs = m_rect.group(1)
                mx = re.search(r'\bx="([0-9.]+)"', attrs)
                mw = re.search(r'\bwidth="([0-9.]+)"', attrs)
                if mx and mw:
                    right_edge = float(mx.group(1)) + float(mw.group(1))
                    self.assertLessEqual(
                        right_edge,
                        310.0,
                        f"{rel_path} mobile rect right edge {right_edge} > 310",
                    )

            for fs in re.findall(r'font-size="([0-9.]+)"', fig):
                self.assertGreaterEqual(
                    float(fs), 11.0, f"{rel_path} has SVG font-size {fs} < 11px"
                )

        for rel_path, fig_id in ESSAY_PAGES:
            raw = (CONTENT_DIR / rel_path).read_text(encoding="utf-8")
            m_mobile = re.search(
                r'<svg class="diagram-mobile"[^>]*>(.*?)</svg>', raw, flags=re.S
            )
            mobile_svg = m_mobile.group(1)
            self.assertGreaterEqual(
                len(re.findall(r"<line\b", mobile_svg)),
                3,
                f"{rel_path} mobile diagram needs >= 3 directional connector lines",
            )
            self.assertGreaterEqual(
                len(re.findall(r"<polygon\b", mobile_svg)),
                3,
                f"{rel_path} mobile diagram needs >= 3 directional arrowheads",
            )

    def test_all_five_pages_anchor_five_primitives_and_canonical_sources(self) -> None:
        for rel_path, _ in ESSAY_PAGES + GUIDE_PAGES:
            raw = (CONTENT_DIR / rel_path).read_text(encoding="utf-8")
            asides = re.findall(
                r'<aside class="for-researchers">(.*?)</aside>', raw, flags=re.S
            )
            self.assertTrue(asides, f"{rel_path} missing researcher aside")
            aside = "\n".join(asides)
            for term in REQUIRED_PRIMITIVE_TERMS:
                self.assertIn(
                    term,
                    aside,
                    f"{rel_path} researcher aside missing primitive term {term!r}",
                )
            for cite in REQUIRED_CITATIONS:
                self.assertIn(
                    cite,
                    aside,
                    f"{rel_path} researcher aside missing citation {cite!r}",
                )


if __name__ == "__main__":
    unittest.main()
