#!/usr/bin/env python3
"""Deterministic verification suite for Spec 05 mobile/dark-mode SVG parity, directional
mobile stage connectors, claim-first line editing, zero rather-than/instead-of contrasts,
and 38+14-term five-primitive Base Thesis grounding across four cintnet.org audience essays:
- site/content/blog/open-problems-we-would-love-help-with.html (#ex-open-problems-map)
- site/content/blog/teaching-an-assistant-step-by-step.html (#ex-step-dpo)
- site/content/blog/testing-an-assistant-on-unfamiliar-roads.html (#ex-clean-room-testing)
- site/content/blog/why-code-still-needs-a-mentor.html (#ex-mentorship-budget)
"""

import pathlib
import re
import statistics
import unittest
import xml.etree.ElementTree as ET


CONTENT_DIR = pathlib.Path(__file__).resolve().parents[1] / "content"

PAGE_CASES = (
    ("blog/open-problems-we-would-love-help-with.html", "ex-open-problems-map"),
    ("blog/teaching-an-assistant-step-by-step.html", "ex-step-dpo"),
    ("blog/testing-an-assistant-on-unfamiliar-roads.html", "ex-clean-room-testing"),
    ("blog/why-code-still-needs-a-mentor.html", "ex-mentorship-budget"),
)

REQUIRED_RESEARCHER_TERMS = (
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
    "Tulving",
    "Endel Tulving",
    "Signed Is Not True",
    "analog hole",
    "Fu &amp; Xu",
    "Kevin Fu",
    "Wenyuan Xu",
    "1:1",
    "exocortex",
    "Bach",
    "Joscha Bach",
    "Clark &amp; Chalmers",
    "Andy Clark",
    "David Chalmers",
    "information fiduciary",
    "Balkin",
    "Jack Balkin",
    "unassisted competence",
    "Markov blanket",
    "Friston",
    "Karl Friston",
    "Private Autobiographical Ledger",
    "Public Attestation and Escrow Ledger",
    "Public Attestation &amp; Escrow Ledger",
    "ZK",
    "IETF SCITT",
    "RFC 9943",
    "Object-Capability",
    "capability lease",
    "Dennis",
    "Van Horn",
    "3f + 1",
    "Byzantine",
    "Wide Network Ledger",
    "Universal Basic Services",
    "Meluso",
    "Jacob Meluso",
    "reciprocal mutual credit",
    "Stodder",
    "James Stodder",
    "Meidner",
    "Rudolf Meidner",
    "Ostrom",
    "Elinor Ostrom",
    "Levin",
    "Michael Levin",
    "/labs/protocol-inspector/",
    "/labs/sensor-boundary/",
    "/labs/shared-horizon/",
)

CANONICAL_SOURCES = (
    "10.1145/3176402",
    "rfc9334",
    "c2pa.org/specifications/specifications/2.1/specs/C2PA_Specification.html",
    "information-fiduciaries-and-first-amendment",
    "10.1098/rsif.2013.0475",
    "10.1145/365230.365252",
    "rfc9943",
    "employeeinvestme0000meid",
    "CBO9780511807763",
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
    "MMCT",
)


class CommsOpenProblemsStepDpoCleanRoomMentorshipSpec05Tests(unittest.TestCase):
    """Verify Spec 05 mobile/dark-mode SVG parity, directional mobile stage connectors,
    claim-first openings, zero negative contrasts, and 38+14-term five-primitive Base Thesis
    grounding across all four audience essays."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.texts = {
            rel_path: (CONTENT_DIR / rel_path).read_text(encoding="utf-8")
            for rel_path, _ in PAGE_CASES
        }

    def test_spec05_unboxed_dark_mode_and_dual_responsive_svgs_with_connectors(self) -> None:
        for rel_path, fig_id in PAGE_CASES:
            text = self.texts[rel_path]
            fig_m = re.search(
                rf'<figure\b[^>]*id="{re.escape(fig_id)}"[^>]*>.*?</figure>',
                text,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(fig_m, f"Missing #{fig_id} in {rel_path}")
            fig_html = fig_m.group(0)

            self.assertIn("background: transparent", fig_html, f"{rel_path} explainer must be unboxed")
            self.assertIn("@media (prefers-color-scheme: dark)", fig_html)
            self.assertIn('[data-theme="dark"]', fig_html)
            self.assertIn("#8FD4B6", fig_html)
            self.assertIn("#F09D82", fig_html)
            self.assertIn("diagram-desktop", fig_html)
            self.assertIn("diagram-mobile", fig_html)
            self.assertIn("@media (max-width: 640px)", fig_html)
            self.assertIn("@media (max-width: 600px)", fig_html)

            svg_blocks = re.findall(r"<svg\b[^>]*>.*?</svg>", fig_html, re.DOTALL)
            self.assertEqual(len(svg_blocks), 2, f"{rel_path} must have desktop + mobile SVGs")

            for svg_raw in svg_blocks:
                root = ET.fromstring(svg_raw)
                self.assertEqual(root.attrib.get("role"), "img", f"{rel_path} SVG must have role='img'")
                self.assertNotIn("height", root.attrib, f"{rel_path} SVG must not carry height attribute")
                self.assertIsNotNone(root.find("title"))
                self.assertIsNotNone(root.find("desc"))
                text_nodes = [el for el in root.iter() if el.tag.split("}")[-1] == "text"]
                self.assertLess(len(text_nodes), 28, f"{rel_path} SVG exceeds 27 text nodes ({len(text_nodes)})")
                for elem in text_nodes:
                    fs = elem.attrib.get("font-size")
                    if fs is not None:
                        self.assertGreaterEqual(
                            float(fs.replace("px", "")),
                            11.0,
                            f"{rel_path} has SVG <text> below 11px: {fs}",
                        )

            mobile_root = ET.fromstring(svg_blocks[1])
            vb_parts = mobile_root.attrib.get("viewBox", "0 0 999 0").split()
            self.assertLessEqual(float(vb_parts[2]), 330.0, f"{rel_path} mobile viewBox width > 330")
            mobile_lines = [el for el in mobile_root.iter() if el.tag.split("}")[-1] == "line"]
            mobile_polys = [el for el in mobile_root.iter() if el.tag.split("}")[-1] == "polygon"]
            self.assertGreaterEqual(len(mobile_lines), 3, f"{rel_path} .diagram-mobile missing connector <line>")
            self.assertGreaterEqual(len(mobile_polys), 3, f"{rel_path} .diagram-mobile missing arrowhead <polygon>")

            for elem in mobile_root.iter():
                tag = elem.tag.split("}")[-1]
                if tag == "rect":
                    w = float(elem.attrib.get("width", "0"))
                    self.assertLessEqual(w, 310.0, f"{rel_path} mobile SVG rect width {w} > 310px")
                elif tag == "text":
                    content = (elem.text or "").strip()
                    if not content:
                        continue
                    x = float(elem.attrib.get("x", "0"))
                    fs = float(elem.attrib.get("font-size", "11").replace("px", ""))
                    anchor = elem.attrib.get("text-anchor", "start")
                    est_w = len(content) * (fs * 0.58)
                    right_edge = x + (est_w / 2) if anchor == "middle" else (x if anchor == "end" else x + est_w)
                    self.assertLessEqual(
                        right_edge,
                        310.0,
                        f"{rel_path} mobile SVG text '{content}' overflows 310px bound (right_edge={right_edge:.1f})",
                    )

    def test_base_thesis_38_plus_14_term_grounding_and_canonical_sources(self) -> None:
        for rel_path, _ in PAGE_CASES:
            text = self.texts[rel_path]
            aside_match = re.search(
                r'<aside class="for-researchers">(.*?)</aside>', text, re.DOTALL
            )
            self.assertIsNotNone(aside_match, f"{rel_path} missing <aside class='for-researchers'>")
            aside_text = aside_match.group(1)
            for term in REQUIRED_RESEARCHER_TERMS:
                self.assertIn(term, aside_text, f"{rel_path} researcher aside missing '{term}'")
            for src in CANONICAL_SOURCES:
                self.assertIn(src, text, f"{rel_path} footnotes missing canonical Base Thesis source '{src}'")

            body_only = text.split("---\n", 2)[2]
            body_only = re.sub(r'<aside class="for-researchers">.*?</aside>', "", body_only, flags=re.DOTALL)
            body_only = re.sub(r'<section class="footnotes">.*?</section>', "", body_only, flags=re.DOTALL)
            for leak in FORBIDDEN_BODY_LEAKS:
                self.assertNotIn(leak, body_only, f"{rel_path} leaked '{leak}' into everyday body prose")

    def test_claim_first_voice_and_humanizer_sentence_invariants(self) -> None:
        for rel_path, _ in PAGE_CASES:
            text = self.texts[rel_path]
            self.assertNotIn('<div class="callout">', text)
            takeaway_m = re.search(r"^takeaway:\s*(.+)$", text, flags=re.M)
            self.assertIsNotNone(takeaway_m, f"{rel_path} missing takeaway front matter")
            takeaway = takeaway_m.group(1).strip()
            body = re.split(r"---\r?\n", text, maxsplit=2)[2]
            first_p = re.search(r"<p(?:\s+[^>]*)?>(.*?)</p>", body, flags=re.DOTALL)
            self.assertIsNotNone(first_p, f"{rel_path} missing opening <p>")
            first_p_plain = re.sub(r"<[^>]+>", "", first_p.group(1)).strip()
            self.assertTrue(
                first_p_plain.startswith(takeaway[:45]),
                f"{rel_path} does not open sentence 1 with its direct takeaway claim: {first_p_plain[:80]}",
            )
            clean = re.sub(
                r"<(style|script|figure|svg|aside|section)[^>]*>.*?</\1>",
                " ",
                body,
                flags=re.DOTALL,
            )
            clean = re.sub(r"</(h[1-6]|p|li|div|figcaption|blockquote)>", ". ", clean, flags=re.IGNORECASE)
            clean_text = re.sub(r"<[^>]+>", " ", clean)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()
            self.assertNotIn("—", clean_text, f"{rel_path} contains em-dash in body prose")
            self.assertIsNone(
                re.search(r"\brather than\b", clean_text, re.I),
                f"{rel_path} still contains 'rather than' contrast in everyday prose",
            )
            self.assertIsNone(
                re.search(r"\binstead of\b", clean_text, re.I),
                f"{rel_path} still contains 'instead of' contrast in everyday prose",
            )
            sentences = [s.strip() for s in re.split(r"[.!?]+", clean_text) if len(s.strip().split()) > 3]
            counts = [len(s.split()) for s in sentences]
            self.assertLessEqual(statistics.median(counts), 20.0, f"{rel_path} median sentence > 20")
            self.assertLessEqual(max(counts), 35, f"{rel_path} max sentence > 35")


if __name__ == "__main__":
    unittest.main()
