#!/usr/bin/env python3
"""Unit tests for Spec 05 mobile/dark-mode SVG parity, directional mobile stage connectors,
38-term five-primitive Base Thesis grounding, and zero-contrast everyday prose across all seven
Get Involved audience briefings (index.html, everyone.html, builders.html, researchers.html,
policy.html, labs.html, and civil-society.html) (D-2096)."""

from pathlib import Path
import re
import statistics
import unittest
import xml.etree.ElementTree as ET

TESTS_DIR = Path(__file__).resolve().parent
SITE_ROOT = TESTS_DIR.parent
CONTENT_DIR = SITE_ROOT / "content"

TARGET_PAGES = (
    ("get-involved/index.html", "ex-five-roles-cycle"),
    ("get-involved/everyone.html", "ex-everyday-checks"),
    ("get-involved/builders.html", "ex-builder-circuits"),
    ("get-involved/researchers.html", "ex-research-agenda"),
    ("get-involved/policy.html", "ex-policy-procurement-gates"),
    ("get-involved/labs.html", "ex-lab-safeguards"),
    ("get-involved/civil-society.html", "ex-civil-society-defense"),
)

REQUIRED_38_BASE_THESIS_TERMS = (
    "Device Time",
    "PUF",
    "TCG DICE",
    "DMTF SPDM",
    "IETF RATS",
    "RFC 9334",
    "optical data diodes",
    "IEC 61508",
    "C2PA",
    "Merkle",
    "Signed Is Not True",
    "analog hole",
    "Fu &amp; Xu",
    "1:1",
    "Bach",
    "Clark &amp; Chalmers",
    "information fiduciary",
    "Balkin",
    "Markov blanket",
    "Friston",
    "Private Autobiographical Ledger",
    "Public Attestation &amp; Escrow Ledger",
    "ZK",
    "IETF SCITT",
    "RFC 9943",
    "capability lease",
    "3f + 1",
    "Byzantine",
    "Wide Network Ledger",
    "Universal Basic Services",
    "mutual credit",
    "Meidner",
    "Ostrom",
    "Stodder",
    "Meluso",
    "/labs/protocol-inspector/",
    "/labs/sensor-boundary/",
    "/labs/shared-horizon/",
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


class CommsSevenGetInvolvedAudienceGuidesSpec05Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.texts = {}
        for rel_path, _ in TARGET_PAGES:
            path = CONTENT_DIR / rel_path
            assert path.is_file(), f"Missing target page: {path}"
            cls.texts[rel_path] = path.read_text(encoding="utf-8")

    def test_spec05_unboxed_dark_mode_and_dual_responsive_svgs_with_mobile_connectors(self) -> None:
        for rel_path, fig_id in TARGET_PAGES:
            text = self.texts[rel_path]
            fig_match = re.search(
                rf'<figure\b[^>]*\bid=["\']{re.escape(fig_id)}["\'][^>]*>(.*?)</figure>',
                text,
                re.DOTALL,
            )
            self.assertIsNotNone(fig_match, f"Missing figure #{fig_id} in {rel_path}")
            fig_content = fig_match.group(1)

            self.assertIn("@media (prefers-color-scheme: dark)", fig_content)
            self.assertIn('[data-theme="dark"]', fig_content)
            self.assertIn("#8FD4B6", fig_content)
            self.assertIn("#F09D82", fig_content)
            self.assertIn("background: transparent", fig_content)
            self.assertIn("text-align: left", fig_content)
            self.assertIn('class="diagram-desktop"', fig_content)
            self.assertIn('class="diagram-mobile"', fig_content)

            svgs = re.findall(r"<svg\b[^>]*>.*?</svg>", fig_content, re.DOTALL)
            self.assertEqual(len(svgs), 2, f"{rel_path} #{fig_id} must contain desktop and mobile SVGs")

            for svg_str in svgs:
                root = ET.fromstring(svg_str)
                self.assertEqual(root.attrib.get("role"), "img")
                self.assertNotIn("height", root.attrib, f"{rel_path} SVG must not carry height='auto' attribute")
                self.assertIsNotNone(root.find("title"))
                self.assertIsNotNone(root.find("desc"))
                text_nodes = [el for el in root.iter() if el.tag.split("}")[-1] == "text"]
                self.assertLess(len(text_nodes), 28, f"{rel_path} SVG exceeds 27 text nodes ({len(text_nodes)})")
                for fs in re.findall(r'font-size=["\']([0-9.]+)["\']', svg_str):
                    self.assertGreaterEqual(float(fs), 11.0, f"{rel_path} has SVG font-size={fs} < 11px")

            mobile_root = ET.fromstring(svgs[1])
            vb_parts = mobile_root.attrib.get("viewBox", "0 0 999 0").split()
            self.assertLessEqual(float(vb_parts[2]), 330.0, f"{rel_path} mobile viewBox width > 330")
            mobile_rects = [el for el in mobile_root.iter() if el.tag.split("}")[-1] == "rect"]
            self.assertEqual(mobile_rects[0].attrib.get("fill"), "#FAF3EA", f"{rel_path} mobile SVG missing #FAF3EA backdrop")
            mobile_lines = [el for el in mobile_root.iter() if el.tag.split("}")[-1] == "line"]
            mobile_polys = [el for el in mobile_root.iter() if el.tag.split("}")[-1] == "polygon"]
            self.assertGreaterEqual(len(mobile_lines), 3, f"{rel_path} mobile SVG missing stage connector lines")
            self.assertGreaterEqual(len(mobile_polys), 3, f"{rel_path} mobile SVG missing directional arrowheads")

            for text_el in [el for el in mobile_root.iter() if el.tag.split("}")[-1] == "text"]:
                content = (text_el.text or "").strip()
                if not content:
                    continue
                x = float(text_el.attrib.get("x", "0"))
                fs = float(text_el.attrib.get("font-size", "11"))
                anchor = text_el.attrib.get("text-anchor", "start")
                est_w = len(content) * (fs * 0.58)
                right_edge = x + (est_w / 2) if anchor == "middle" else (x if anchor == "end" else x + est_w)
                self.assertLessEqual(
                    right_edge,
                    310.0,
                    f"{rel_path} mobile SVG text '{content}' overflows 310px bound (right_edge={right_edge:.1f})",
                )

    def test_base_thesis_38_term_grounding_and_anti_leak_gate(self) -> None:
        for rel_path, _ in TARGET_PAGES:
            text = self.texts[rel_path]
            asides = re.findall(r'<aside[^>]*for-researchers[^>]*>(.*?)</aside>', text, re.DOTALL)
            self.assertGreaterEqual(len(asides), 1, f"{rel_path} must contain researcher aside")
            aside_combined = "\n".join(asides)
            for term in REQUIRED_38_BASE_THESIS_TERMS:
                self.assertIn(term, aside_combined, f"{rel_path} researcher aside missing '{term}'")

            body_only = text.split("---\n", 2)[2]
            body_only = re.sub(r"<figure\b.*?</figure>", "", body_only, flags=re.DOTALL)
            body_only = re.sub(r'<aside[^>]*for-researchers[^>]*>.*?</aside>', "", body_only, flags=re.DOTALL)
            body_only = re.sub(r'<section class="footnotes">.*?</section>', "", body_only, flags=re.DOTALL)
            for leak in FORBIDDEN_BODY_LEAKS:
                self.assertNotIn(leak, body_only, f"{rel_path} leaked '{leak}' into everyday body prose")

    def test_voice_and_humanizer_sentence_invariants(self) -> None:
        for rel_path, _ in TARGET_PAGES:
            text = self.texts[rel_path]
            body = text.split("---\n", 2)[2]
            body_no_aside = re.sub(r"<figure\b.*?</figure>", " ", body, flags=re.DOTALL)
            body_no_aside = re.sub(r'<aside[^>]*for-researchers[^>]*>.*?</aside>', " ", body_no_aside, flags=re.DOTALL)
            body_no_aside = re.sub(r'<section class="footnotes">.*?</section>', " ", body_no_aside, flags=re.DOTALL)
            self.assertNotIn("—", body_no_aside, f"{rel_path} contains em-dash in body prose")
            self.assertNotIn("rather than", body_no_aside.lower(), f"{rel_path} contains 'rather than'")
            self.assertNotIn("instead of", body_no_aside.lower(), f"{rel_path} contains 'instead of'")

            ps = re.findall(r"<(?:p|li)\b[^>]*>(.*?)</(?:p|li)>", body_no_aside, flags=re.DOTALL)
            sentences = []
            for p in ps:
                ct = re.sub(r"<sup[^>]*>.*?</sup>", "", p)
                ct = re.sub(r"<[^>]+>", " ", ct)
                ct = re.sub(r"\s+", " ", ct).strip()
                for s in re.split(r"(?<=[.!?])\s+", ct):
                    if len(s.split()) > 3:
                        sentences.append(s)
            counts = [len(s.split()) for s in sentences]
            self.assertLessEqual(statistics.median(counts), 20.0, f"{rel_path} median sentence > 20 ({statistics.median(counts)})")
            self.assertLessEqual(max(counts), 35, f"{rel_path} max sentence > 35 ({max(counts)})")


if __name__ == "__main__":
    unittest.main()
