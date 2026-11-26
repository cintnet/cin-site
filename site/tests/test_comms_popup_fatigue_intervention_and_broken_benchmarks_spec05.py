#!/usr/bin/env python3
"""Unit tests for the confirmation pop-up fatigue, intervention-value triage,
and broken-benchmark auditing audience essay, Spec 05 pastel watercolor vignette,
dual desktop/mobile light/dark-mode SVG explainer, verified primary citations,
and 62-term five-primitive Base Thesis grounding on cintnet.org/blog/ (comms)."""

from __future__ import annotations

import html
from pathlib import Path
import re
import statistics
import unittest
import xml.etree.ElementTree as ET

TESTS_DIR = Path(__file__).resolve().parent
SITE_ROOT = TESTS_DIR.parent
CONTENT_DIR = SITE_ROOT / "content"
IMG_DIR = SITE_ROOT / "assets" / "img"

ESSAY_REL = "blog/why-more-pop-up-warnings-catch-fewer-ai-mistakes.html"
SIBLING_REL = "blog/why-long-running-ai-assistants-break-the-house-rules.html"
FIG_ID = "ex-popup-fatigue-vs-intervention-triage"
IMG_NAME = "post-why-more-pop-up-warnings-catch-fewer-ai-mistakes.jpg"

REQUIRED_BASE_THESIS_TERMS = (
    "multimodal egocentric",
    "perceptual sensorium",
    "Device Time",
    "observation confidence",
    "PUF",
    "TCG DICE",
    "DMTF SPDM",
    "IETF RATS",
    "RFC 9334",
    "optical data diode",
    "optical data diodes",
    "IEC 61508",
    "dead-man",
    "C2PA",
    "Merkle",
    "episodic memory vault",
    "Endel Tulving",
    "Tulving",
    "Signed Is Not True",
    "analog hole",
    "Fu &amp; Xu",
    "1:1",
    "biological person",
    "personal cognitive model",
    "cybernetic exocortex",
    "Joscha Bach",
    "Bach",
    "Extended Mind",
    "Andy Clark &amp; David Chalmers",
    "Clark &amp; Chalmers",
    "Good Regulator",
    "do(x)",
    "information fiduciary",
    "Jack Balkin",
    "Balkin",
    "unassisted competence",
    "Markov blanket",
    "Karl Friston",
    "Friston",
    "Michael Levin",
    "cognitive light cone",
    "Private Autobiographical Ledger",
    "Public Attestation &amp; Escrow Ledger",
    "Public Attestation and Escrow Ledger",
    "zero-knowledge",
    "ZK",
    "IETF SCITT",
    "RFC 9943",
    "Object-Capability",
    "capability lease",
    "Dennis &amp; Van Horn",
    "3f + 1",
    "Byzantine",
    "Wide Network Ledger",
    "Universal Basic Services",
    "merit-bonded",
    "Jacob Meluso",
    "Meluso",
    "reciprocal mutual credit",
    "mutual credit",
    "James Stodder",
    "Stodder",
    "Rudolf Meidner",
    "Meidner",
    "frontier-lab overlays",
    "Elinor Ostrom",
    "Ostrom",
    "/labs/protocol-inspector/",
    "/labs/sensor-boundary/",
    "/labs/shared-horizon/",
)

REQUIRED_CITATIONS = (
    "2606.08919",
    "2605.26079",
    "2606.21399",
    "2610.28539",
    "10.1145/3176402",
    "rfc9334",
    "c2pa.org/specifications/specifications/2.1/specs/C2PA_Specification.html",
    "information-fiduciaries-and-first-amendment",
    "10.1098/rsif.2013.0475",
    "10.1145/365230.365252",
    "rfc9943",
    "employeeinvestme0000meid",
)

FORBIDDEN_BODY_LEAKS = (
    "Base Thesis",
    "Markov Blanket",
    "Markov blanket",
    "Exocortex",
    "exocortex",
    "Private Autobiographical Ledger",
    "Public Attestation",
    "Wide Network Ledger",
    "Primitive 5",
    "SCITT",
    "IEC 61508",
)


class CommsPopupFatigueInterventionBrokenBenchmarksSpec05Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.essay_path = CONTENT_DIR / ESSAY_REL
        assert cls.essay_path.is_file(), f"Missing essay: {cls.essay_path}"
        cls.text = cls.essay_path.read_text(encoding="utf-8")
        cls.sibling_text = (CONTENT_DIR / SIBLING_REL).read_text(encoding="utf-8")

    def test_01_watercolor_vignette_and_spec05_dual_svg_explainer(self) -> None:
        img_path = IMG_DIR / IMG_NAME
        self.assertTrue(img_path.is_file(), f"Missing vignette image: {img_path}")
        size_bytes = img_path.stat().st_size
        self.assertGreater(size_bytes, 10_000)
        self.assertLess(size_bytes, 300_000, f"Vignette exceeds 300 KB: {size_bytes}")

        fig_match = re.search(
            rf'<figure\b[^>]*\bid=["\']{re.escape(FIG_ID)}["\'][^>]*>(.*?)</figure>',
            self.text,
            re.DOTALL,
        )
        self.assertIsNotNone(fig_match, f"Missing figure #{FIG_ID}")
        fig_content = fig_match.group(1)

        self.assertNotIn("@media (prefers-color-scheme: dark)", fig_content)
        for token in (
            f':root[data-theme="dark"] #{FIG_ID}',
            f':root[data-theme="light"] #{FIG_ID}',
            "#8FD4B6",
            "#F09D82",
            "background: transparent",
            'class="diagram-desktop"',
            'class="diagram-mobile"',
        ):
            self.assertIn(token, fig_content, f"Missing Spec 05 token: {token}")

        svgs = re.findall(r"<svg\b[^>]*>.*?</svg>", fig_content, re.DOTALL)
        self.assertEqual(len(svgs), 2, "Expected paired desktop and mobile SVGs")

        for view_name, svg_raw in (("desktop", svgs[0]), ("mobile", svgs[1])):
            self.assertNotIn("->", svg_raw)
            self.assertNotIn("-&gt;", svg_raw)
            root = ET.fromstring(svg_raw)
            self.assertGreaterEqual(len(list(root.iter("line"))), 3)
            self.assertGreaterEqual(len(list(root.iter("polygon"))), 2)
            for t_el in root.iter("text"):
                fs = float(t_el.attrib.get("font-size", "11"))
                self.assertGreaterEqual(fs, 11.0, f"SVG text below 11px: {ET.tostring(t_el, encoding='unicode')}")
            if view_name == "mobile":
                vb = root.attrib.get("viewBox", "0 0 999 0").split()
                self.assertLessEqual(float(vb[2]), 310.0)

    def test_02_everyday_body_anti_leak_claim_first_and_sentence_bounds(self) -> None:
        _, fm, body_html = self.text.split("---", 2)
        m_takeaway = re.search(r"^takeaway:\s*(.+)$", fm, flags=re.M)
        self.assertIsNotNone(m_takeaway)
        takeaway = m_takeaway.group(1).strip()

        m_first_p = re.search(r"<p(?:\s+[^>]*)?>(.*?)</p>", body_html, flags=re.S)
        self.assertIsNotNone(m_first_p)
        first_p = re.sub(r"<[^>]+>", "", m_first_p.group(1)).strip()
        self.assertTrue(first_p.startswith(takeaway[:45]))

        everyday_html = re.sub(r'<aside\s+class="for-researchers">.*?</aside>', "", body_html, flags=re.DOTALL)
        everyday_html = re.sub(r'<section\s+class="footnotes">.*?</section>', "", everyday_html, flags=re.DOTALL)
        everyday_html = re.sub(r"<figure\b.*?</figure>", "", everyday_html, flags=re.DOTALL)

        for leak in FORBIDDEN_BODY_LEAKS:
            self.assertNotIn(leak, everyday_html, f"Internal label leaked into everyday body: {leak}")
        self.assertNotIn("—", self.text, "Em-dash forbidden in prose")

        contrast_re = re.compile(r"\b(?:not\s+(?:just|only|merely)\b|rather\s+than\b|instead\s+of\b)", flags=re.I)
        self.assertIsNone(contrast_re.search(everyday_html))

        sentences: list[str] = []
        for m in re.finditer(r"<(?:p|li)(?:\s+[^>]*)?>(.*?)</(?:p|li)>", everyday_html, flags=re.S):
            inner = re.sub(r"<sup\b[^>]*>.*?</sup>", "", m.group(1), flags=re.S)
            txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", inner))).strip()
            for s in re.split(r'[.?!]["\u2019\u201d\')\]]*(?:\s+|$)', txt):
                if len(s.strip().split()) > 3:
                    sentences.append(s.strip())
        lengths = [len(s.split()) for s in sentences]
        self.assertLessEqual(statistics.median(lengths), 20.0)
        self.assertLessEqual(max(lengths), 34)

    def test_03_verified_citations_inbound_link_and_five_primitive_grounding(self) -> None:
        self.assertIn("/blog/why-more-pop-up-warnings-catch-fewer-ai-mistakes/", self.sibling_text)
        aside_match = re.search(
            r'<aside\s+class="for-researchers">(.*?)</aside>',
            self.text,
            re.DOTALL,
        )
        self.assertIsNotNone(aside_match, "Missing for-researchers aside")
        aside_html = aside_match.group(1)

        for term in REQUIRED_BASE_THESIS_TERMS:
            self.assertIn(term, aside_html, f"Missing Base Thesis term in researcher box: {term}")
        for cite in REQUIRED_CITATIONS:
            self.assertIn(cite, self.text, f"Missing primary citation: {cite}")


if __name__ == "__main__":
    unittest.main()
