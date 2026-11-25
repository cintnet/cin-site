#!/usr/bin/env python3
"""Deterministic regression suite for Spec 05 desktop/mobile directional arrowhead parity,
claim-first openings, negative-contrast-free everyday prose, and 62-term / 9-citation / 8-URL
five-primitive Base Thesis grounding across the five governance, open-ledger, election-cycle,
King Lear, and safeguards essays on cintnet.org (D-2321):
- site/content/blog/beyond-the-dystopian-script-why-ai-labs-need-a-better-story-of-society.html (#ex-dystopian-offramp)
- site/content/blog/how-people-labs-governments-and-industry-can-win-on-an-open-ledger.html (#ex-open-ledger-transition)
- site/content/blog/one-election-cycle-for-the-industrial-revolution.html (#ex-election-cycle-clock)
- site/content/blog/the-king-lear-trap-why-flattery-is-not-loyalty.html (#ex-king-lear-leverage)
- site/content/blog/when-the-person-building-the-safeguards-tells-you-to-be-angry.html (#ex-safeguards-town-dam)
"""

from __future__ import annotations

import pathlib
import re
import statistics
import unittest
import xml.etree.ElementTree as ET


SITE_DIR = pathlib.Path(__file__).resolve().parents[1]
CONTENT_DIR = SITE_DIR / "content"

PAGE_CASES: tuple[tuple[str, str], ...] = (
    ("blog/beyond-the-dystopian-script-why-ai-labs-need-a-better-story-of-society.html", "ex-dystopian-offramp"),
    ("blog/how-people-labs-governments-and-industry-can-win-on-an-open-ledger.html", "ex-open-ledger-transition"),
    ("blog/one-election-cycle-for-the-industrial-revolution.html", "ex-election-cycle-clock"),
    ("blog/the-king-lear-trap-why-flattery-is-not-loyalty.html", "ex-king-lear-leverage"),
    ("blog/when-the-person-building-the-safeguards-tells-you-to-be-angry.html", "ex-safeguards-town-dam"),
)

REQUIRED_BASE_THESIS_TERMS: tuple[str, ...] = (
    "multimodal egocentric",
    "perceptual sensorium",
    "Device Time",
    "observation confidence",
    "PUF",
    "TCG DICE",
    "DMTF SPDM",
    "IETF RATS",
    "9334",
    "optical data diode",
    "IEC 61508",
    "dead-man",
    "C2PA",
    "Merkle",
    "episodic memory vault",
    "biological person",
    "personal cognitive model",
    "Tulving",
    "Endel Tulving",
    "Signed Is Not True",
    "analog hole",
    "Fu",
    "Xu",
    "1:1",
    "cybernetic exocortex",
    "Joscha Bach",
    "Extended Mind",
    "Andy Clark",
    "David Chalmers",
    "Good Regulator",
    "do(x)",
    "information fiduciary",
    "Jack Balkin",
    "unassisted competence",
    "Markov blanket",
    "Karl Friston",
    "Michael Levin",
    "cognitive light cone",
    "Private Autobiographical Ledger",
    "Public Attestation &amp; Escrow Ledger",
    "Public Attestation and Escrow Ledger",
    "zero-knowledge",
    "ZK",
    "IETF SCITT",
    "9943",
    "Object-Capability",
    "capability lease",
    "Dennis",
    "Van Horn",
    "3f + 1",
    "Byzantine",
    "Wide Network Ledger",
    "Universal Basic Services",
    "merit-bonded",
    "Jacob Meluso",
    "reciprocal mutual credit",
    "James Stodder",
    "Rudolf Meidner",
    "frontier-lab overlays",
    "Elinor Ostrom",
    "/labs/protocol-inspector/",
    "/labs/sensor-boundary/",
    "/labs/shared-horizon/",
)

REQUIRED_NINE_CITATIONS: tuple[str, ...] = (
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

REQUIRED_EIGHT_SOURCE_URLS: tuple[str, ...] = (
    "10.1145/3176402",
    "rfc9334",
    "c2pa.org/specifications/specifications/2.1/specs/C2PA_Specification.html",
    "information-fiduciaries-and-first-amendment",
    "10.1098/rsif.2013.0475",
    "10.1145/365230.365252",
    "rfc9943",
    "employeeinvestme0000meid",
)


class SitecriticFiveGovernanceLedgerSafeguardsEssaysSpec05Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.texts = {
            rel_path: (CONTENT_DIR / rel_path).read_text(encoding="utf-8")
            for rel_path, _ in PAGE_CASES
        }

    def test_claim_first_openings_and_zero_negative_contrasts(self) -> None:
        for rel_path, _ in PAGE_CASES:
            raw = self.texts[rel_path]
            _, fm, body = raw.split("---", 2)
            m_takeaway = re.search(r"^takeaway:\s*(.+)$", fm, flags=re.M)
            self.assertIsNotNone(m_takeaway, f"{rel_path} missing takeaway front-matter")
            takeaway = m_takeaway.group(1).strip()

            m_first_p = re.search(r"<p(?:\s+[^>]*)?>(.*?)</p>", body, flags=re.S)
            self.assertIsNotNone(m_first_p, f"{rel_path} missing opening <p>")
            first_p = re.sub(r"<[^>]+>", "", m_first_p.group(1)).strip()
            self.assertTrue(
                first_p.startswith(takeaway[:45]),
                f"{rel_path} opening paragraph must begin with takeaway claim",
            )

            everyday = re.sub(r'<aside class="for-researchers">.*?</aside>', " ", body, flags=re.S)
            everyday = re.sub(r'<section class="footnotes">.*?</section>', " ", everyday, flags=re.S)
            everyday = re.sub(r'<figure class="explainer"[^>]*>.*?</figure>', " ", everyday, flags=re.S)
            text_only = re.sub(r"<[^>]+>", " ", everyday)
            self.assertIsNone(
                re.search(r"\brather than\b", text_only, flags=re.I),
                f"{rel_path} everyday prose contains negative contrast 'rather than'",
            )
            self.assertIsNone(
                re.search(r"\binstead of\b", text_only, flags=re.I),
                f"{rel_path} everyday prose contains negative contrast 'instead of'",
            )

    def test_dual_svgs_satisfy_spec05_dark_mode_and_mobile_connector_bounds(self) -> None:
        for rel_path, fig_id in PAGE_CASES:
            raw = self.texts[rel_path]
            fig_m = re.search(
                rf'<figure\b[^>]*id=["\']{re.escape(fig_id)}["\'][^>]*>(.*?)</figure>',
                raw,
                flags=re.S,
            )
            self.assertIsNotNone(fig_m, f"{rel_path} missing figure #{fig_id}")
            fig_html = fig_m.group(1)

            for dark_token in ("background: transparent", "#8FD4B6", "#F09D82", "prefers-color-scheme: dark", 'data-theme="dark"'):
                self.assertIn(
                    dark_token,
                    fig_html,
                    f"{rel_path} #{fig_id} missing Spec 05 token {dark_token}",
                )

            for view_name, view_cls in (("desktop", "diagram-desktop"), ("mobile", "diagram-mobile")):
                svg_m = re.search(
                    rf'<svg\b[^>]*class=["\'][^"\']*\b{view_cls}\b[^"\']*["\'][^>]*>.*?</svg>',
                    fig_html,
                    flags=re.S,
                )
                self.assertIsNotNone(svg_m, f"{rel_path} #{fig_id} missing {view_cls} SVG")
                svg_str = svg_m.group(0)
                ET.fromstring(svg_str)

                lines = re.findall(r"<line\b", svg_str)
                polys = re.findall(r"<polygon\b", svg_str)
                self.assertGreaterEqual(
                    len(lines),
                    3,
                    f"{rel_path} #{fig_id} {view_name} SVG must have >= 3 <line> connectors",
                )
                self.assertGreaterEqual(
                    len(polys),
                    3,
                    f"{rel_path} #{fig_id} {view_name} SVG must have >= 3 directional <polygon> arrowheads",
                )
                for fs in re.findall(r'font-size=["\']([0-9.]+)["\']', svg_str):
                    self.assertGreaterEqual(
                        float(fs),
                        11.0,
                        f"{rel_path} #{fig_id} {view_name} SVG has font-size={fs} < 11px",
                    )

                if view_name == "mobile":
                    for m_rect in re.finditer(r"<rect\b([^>]*)/?>", svg_str):
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

    def test_62_term_base_thesis_and_eight_source_urls(self) -> None:
        for rel_path, _ in PAGE_CASES:
            raw = self.texts[rel_path]
            self.assertNotIn("base thesis", raw.lower(), f"{rel_path} contains internal 'Base Thesis' label")
            asides = re.findall(
                r'<aside\b[^>]*class=["\'][^"\']*for-researchers[^"\']*["\'][^>]*>(.*?)</aside>',
                raw,
                flags=re.S,
            )
            self.assertTrue(asides, f"{rel_path} missing <aside class='for-researchers'>")
            combined_asides = "\n".join(asides)

            for term in REQUIRED_BASE_THESIS_TERMS:
                self.assertIn(
                    term.lower(),
                    combined_asides.lower(),
                    f"{rel_path} researcher asides missing Base Thesis term {term!r}",
                )
            for cite in REQUIRED_NINE_CITATIONS:
                self.assertIn(
                    cite,
                    combined_asides,
                    f"{rel_path} researcher asides missing canonical citation {cite!r}",
                )

            footnotes_m = re.search(r'<section class="footnotes">(.*?)</section>', raw, flags=re.S)
            self.assertIsNotNone(footnotes_m, f"{rel_path} missing <section class='footnotes'>")
            footnotes_html = footnotes_m.group(1)
            for url_token in REQUIRED_EIGHT_SOURCE_URLS:
                self.assertIn(
                    url_token,
                    footnotes_html,
                    f"{rel_path} footnotes missing canonical Base Thesis source URL {url_token!r}",
                )

    def test_everyday_prose_sentence_bounds_and_anti_leak_invariants(self) -> None:
        for rel_path, _ in PAGE_CASES:
            raw = self.texts[rel_path]
            _, _, body = raw.split("---", 2)
            public_body = re.sub(r"<(style|script|figure|svg|aside)[^>]*>.*?</\1>", " ", body, flags=re.S)
            public_body = re.sub(r'<section class="footnotes">.*?</section>', " ", public_body, flags=re.S)
            plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", public_body)).strip()

            self.assertNotIn("—", plain, f"{rel_path} contains em-dash in public prose")
            for forbidden in ("Base Thesis", "Markov blanket", "Exocortex", "Private Autobiographical Ledger"):
                self.assertIsNone(
                    re.search(rf"\b{re.escape(forbidden)}\b", plain, flags=re.I),
                    f"{rel_path} public prose contains forbidden label {forbidden!r}",
                )

            paragraphs = re.findall(r"<p(?:\s+[^>]*)?>(.*?)</p>", public_body, flags=re.S)
            lengths = []
            for p in paragraphs:
                p_clean = re.sub(r"<sup>.*?</sup>", "", p, flags=re.S)
                p_clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", p_clean)).strip()
                for sent in re.split(r"(?<=[.!?])\s+", p_clean):
                    words = [w for w in sent.split() if w]
                    if len(words) >= 4:
                        lengths.append(len(words))
                        self.assertLessEqual(len(words), 35, f"{rel_path} sentence > 35 words: {sent}")
            self.assertLessEqual(statistics.median(lengths), 22.0, f"{rel_path} median sentence > 22 words")


if __name__ == "__main__":
    unittest.main()
