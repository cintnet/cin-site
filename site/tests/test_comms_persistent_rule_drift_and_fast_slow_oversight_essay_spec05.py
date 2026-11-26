#!/usr/bin/env python3
"""Unit tests for the long-running assistant rule-drift and fast-slow oversight essay,
Spec 05 pastel watercolor vignette, dual desktop/mobile dark-mode SVG explainer,
verified primary citations, and 52-term five-primitive Base Thesis grounding
on cintnet.org/blog/ (comms)."""

from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

TESTS_DIR = Path(__file__).resolve().parent
SITE_ROOT = TESTS_DIR.parent
CONTENT_DIR = SITE_ROOT / "content"
IMG_DIR = SITE_ROOT / "assets" / "img"

ESSAY_REL = "blog/why-long-running-ai-assistants-break-the-house-rules.html"
FIG_ID = "ex-fast-slow-oversight"
IMG_NAME = "post-why-long-running-ai-assistants-break-the-house-rules.jpg"

REQUIRED_BASE_THESIS_TERMS = (
    "Device Time",
    "PUF",
    "TCG DICE",
    "DMTF SPDM",
    "IETF RATS",
    "RFC 9334",
    "optical data diodes",
    "IEC 61508",
    "dead-man",
    "observation confidence",
    "C2PA",
    "Merkle",
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
    "Andy Clark &amp; David Chalmers",
    "Clark &amp; Chalmers",
    "information fiduciary",
    "Jack Balkin",
    "Balkin",
    "unassisted competence",
    "Markov blanket",
    "Karl Friston",
    "Friston",
    "Private Autobiographical Ledger",
    "Public Attestation &amp; Escrow Ledger",
    "ZK",
    "IETF SCITT",
    "RFC 9943",
    "Object-Capability",
    "capability lease",
    "3f + 1",
    "Byzantine",
    "Wide Network Ledger",
    "Universal Basic Services",
    "mutual credit",
    "Rudolf Meidner",
    "Meidner",
    "Elinor Ostrom",
    "Ostrom",
    "James Stodder",
    "Stodder",
    "Jacob Meluso",
    "Meluso",
    "/labs/protocol-inspector/",
    "/labs/sensor-boundary/",
    "/labs/shared-horizon/",
)

REQUIRED_CITATIONS = (
    "2611.17460",
    "2611.03223",
    "2611.08781",
    "2503.18813",
    "2611.27095",
    "metr.org/blog/2026-11-20-q4-2026-capability-update/",
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


class CommsPersistentRuleDriftFastSlowEssaySpec05Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.essay_path = CONTENT_DIR / ESSAY_REL
        assert cls.essay_path.is_file(), f"Missing essay: {cls.essay_path}"
        cls.text = cls.essay_path.read_text(encoding="utf-8")

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
        self.assertIn(f':root[data-theme="dark"] #{FIG_ID}', fig_content)
        self.assertIn("#8FD4B6", fig_content)
        self.assertIn("#F09D82", fig_content)
        self.assertIn("background: transparent", fig_content)
        self.assertIn('class="diagram-desktop"', fig_content)
        self.assertIn('class="diagram-mobile"', fig_content)

        svgs = re.findall(r"<svg\b[^>]*>.*?</svg>", fig_content, re.DOTALL)
        self.assertEqual(len(svgs), 2, "Expected paired desktop and mobile SVGs")

        for svg_raw in svgs:
            root = ET.fromstring(svg_raw)
            self.assertGreaterEqual(len(list(root.iter("line"))), 3)
            self.assertGreaterEqual(len(list(root.iter("polygon"))), 2)
            for t_el in root.iter("text"):
                fs = float(t_el.attrib.get("font-size", "11"))
                self.assertGreaterEqual(fs, 11.0, f"SVG text below 11px: {ET.tostring(t_el, encoding='unicode')}")

    def test_02_everyday_body_anti_leak_and_claim_first_lede(self) -> None:
        parts = self.text.split("---", 2)
        self.assertEqual(len(parts), 3)
        body_html = parts[2]
        everyday_html = re.sub(r'<aside\s+class="for-researchers">.*?</aside>', "", body_html, flags=re.DOTALL)
        everyday_html = re.sub(r'<section\s+class="footnotes">.*?</section>', "", everyday_html, flags=re.DOTALL)
        everyday_html = re.sub(r"<figure\b.*?</figure>", "", everyday_html, flags=re.DOTALL)

        for leak in FORBIDDEN_BODY_LEAKS:
            self.assertNotIn(leak, everyday_html, f"Internal label leaked into everyday body: {leak}")
        self.assertNotIn("—", self.text, "Em-dash forbidden in prose")

    def test_03_verified_citations_and_five_primitive_researcher_grounding(self) -> None:
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
