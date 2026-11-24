#!/usr/bin/env python3
"""Unit tests for claim-first opening paragraphs, Spec 05 mobile/dark-mode SVG parity with
directional mobile stage connectors, and 38+14-term five-primitive Base Thesis grounding across
the Sovereign Governance Papers hub (/labs/sovereign-papers/) and seven flagship sovereign
governance papers: United States (SOV-01), China (SOV-02), European Union (SOV-03),
United Kingdom (SOV-04), Canada (SOV-05), Japan (SOV-06), and India (SOV-09)."""

from pathlib import Path
import re
import statistics
import unittest
import xml.etree.ElementTree as ET

TESTS_DIR = Path(__file__).resolve().parent
SITE_ROOT = TESTS_DIR.parent
SOV_PAPERS_DIR = SITE_ROOT / "content" / "labs" / "sovereign-papers"

PAPER_CASES = (
    ("united-states.html", "ex-sp-united-states", "SOV-01"),
    ("china.html", "ex-sp-china", "SOV-02"),
    ("european-union.html", "ex-sp-european-union", "SOV-03"),
    ("united-kingdom.html", "ex-sp-united-kingdom", "SOV-04"),
    ("canada.html", "ex-sp-canada", "SOV-05"),
    ("japan.html", "ex-sp-japan", "SOV-06"),
    ("india.html", "ex-sp-india", "SOV-09"),
)

ALL_SOVEREIGN_PAGE_CASES = (
    ("index.html", "ex-sp-hub-blueprint"),
    ("united-states.html", "ex-sp-united-states"),
    ("china.html", "ex-sp-china"),
    ("european-union.html", "ex-sp-european-union"),
    ("united-kingdom.html", "ex-sp-united-kingdom"),
    ("canada.html", "ex-sp-canada"),
    ("japan.html", "ex-sp-japan"),
    ("india.html", "ex-sp-india"),
)

REQUIRED_38_EXACT_BASE_THESIS_TERMS = (
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
    "Public Attestation and Escrow Ledger",
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

REQUIRED_38_AND_14_BASE_THESIS_TERMS = (
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
    "Tulving",
    "Endel Tulving",
    "Signed Is Not True",
    "analog hole",
    "Fu",
    "Xu",
    "1:1",
    "exocortex",
    "Bach",
    "Joscha Bach",
    "Clark",
    "Chalmers",
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
    "Public Attestation",
    "Escrow Ledger",
    "ZK",
    "IETF SCITT",
    "9943",
    "Object-Capability",
    "capability lease",
    "Dennis",
    "Van Horn",
    "3f + 1",
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
)


class SitecriticUsEuUkCanadaSovereignPapersSpec05Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.texts = {}
        for filename, _ in ALL_SOVEREIGN_PAGE_CASES:
            path = SOV_PAPERS_DIR / filename
            assert path.exists(), f"Missing sovereign governance page: {path}"
            cls.texts[filename] = path.read_text(encoding="utf-8")

    def test_spec05_unboxed_dark_mode_and_dual_responsive_svgs_with_mobile_connectors(self) -> None:
        for filename, fig_id in ALL_SOVEREIGN_PAGE_CASES:
            text = self.texts[filename]
            fig_match = re.search(
                rf'<figure\b[^>]*\bid=["\']{fig_id}["\'][^>]*>(.*?)</figure>',
                text,
                re.DOTALL,
            )
            self.assertIsNotNone(fig_match, f"Missing figure #{fig_id} in {filename}")
            fig_content = fig_match.group(1)

            self.assertIn(f':root[data-theme="dark"] #{fig_id}', fig_content)
            self.assertIn(f'[data-theme="dark"] #{fig_id}', fig_content)
            self.assertIn("#8FD4B6", fig_content)
            self.assertIn("#F09D82", fig_content)
            self.assertIn("background: transparent", fig_content)
            self.assertIn('class="diagram-desktop"', fig_content)
            self.assertIn('class="diagram-mobile"', fig_content)
            self.assertIn("@media (max-width: 640px)", fig_content)

            if filename != "index.html":
                self.assertIn("@media (prefers-color-scheme: dark)", fig_content)
                self.assertIn("text-align: left", fig_content)
                self.assertIn("@media (max-width: 600px)", fig_content)

            svgs = re.findall(r"<svg\b[^>]*>.*?</svg>", fig_content, re.DOTALL)
            self.assertEqual(len(svgs), 2, f"{filename} #{fig_id} must contain desktop and mobile SVGs")

            for svg_str in svgs:
                root = ET.fromstring(svg_str)
                self.assertEqual(root.attrib.get("role"), "img")
                self.assertIsNotNone(root.find("title"))
                self.assertIsNotNone(root.find("desc"))
                text_nodes = [el for el in root.iter() if el.tag.split("}")[-1] == "text"]
                self.assertLess(len(text_nodes), 28, f"{filename} SVG exceeds 27 text nodes")
                for fs in re.findall(r'font-size=["\']([0-9.]+)["\']', svg_str):
                    self.assertGreaterEqual(float(fs), 11.0, f"{filename} has SVG font-size={fs} < 11px")

            mobile_root = ET.fromstring(svgs[1])
            vb_parts = mobile_root.attrib.get("viewBox", "0 0 999 0").split()
            self.assertLessEqual(float(vb_parts[2]), 310.0, f"{filename} mobile viewBox width > 310")
            mobile_lines = [el for el in mobile_root.iter() if el.tag.split("}")[-1] == "line"]
            mobile_polys = [el for el in mobile_root.iter() if el.tag.split("}")[-1] == "polygon"]
            self.assertGreaterEqual(len(mobile_lines), 3, f"{filename} mobile SVG missing stage connector lines")
            self.assertGreaterEqual(len(mobile_polys), 3, f"{filename} mobile SVG missing directional arrowheads")

            for elem in mobile_root.iter():
                tag = elem.tag.split("}")[-1]
                if tag == "rect":
                    w = float(elem.attrib.get("width", "0"))
                    self.assertLessEqual(w, 310.0, f"{filename} mobile SVG rect width {w} > 310px")
                elif tag == "text":
                    content = (elem.text or "").strip()
                    if not content:
                        continue
                    x = float(elem.attrib.get("x", "0"))
                    fs = float(elem.attrib.get("font-size", "11"))
                    anchor = elem.attrib.get("text-anchor", "start")
                    est_w = len(content) * (fs * 0.58)
                    right_edge = x + (est_w / 2) if anchor == "middle" else (x if anchor == "end" else x + est_w)
                    self.assertLessEqual(
                        right_edge,
                        310.0,
                        f"{filename} mobile SVG text '{content}' overflows 310px bound (right_edge={right_edge:.1f})",
                    )

    def test_base_thesis_five_primitive_grounding_and_anti_leak_gate(self) -> None:
        canonical_sources = (
            "10.1145/3176402",
            "rfc9334",
            "c2pa.org/specifications/specifications/2.1/specs/C2PA_Specification.html",
            "information-fiduciaries-and-first-amendment",
            "10.1098/rsif.2013.0475",
            "10.1145/365230.365252",
            "rfc9943",
            "employeeinvestme0000meid",
        )
        forbidden_body_leaks = (
            "Base Thesis",
            "Markov Blanket",
            "Markov blanket",
            "Exocortex",
            "exocortex",
            "Private Autobiographical Ledger",
            "Public Attestation",
            "Wide Network Ledger",
            "Primitive 5",
        )
        for filename, _ in ALL_SOVEREIGN_PAGE_CASES:
            text = self.texts[filename]
            asides = re.findall(r'<aside class="for-researchers">(.*?)</aside>', text, re.DOTALL)
            if filename == "index.html":
                self.assertEqual(len(asides), 1, "index.html must have 1 researcher aside")
            else:
                self.assertEqual(len(asides), 5, f"{filename} must have 5 researcher asides")
            aside_combined = "\n".join(asides)
            for term in REQUIRED_38_EXACT_BASE_THESIS_TERMS:
                self.assertIn(term, aside_combined, f"{filename} researcher asides missing exact '{term}'")
            for term in REQUIRED_38_AND_14_BASE_THESIS_TERMS:
                self.assertIn(
                    term.lower(),
                    aside_combined.lower(),
                    f"{filename} researcher asides missing Base Thesis term '{term}'",
                )
            if filename != "index.html":
                for src in canonical_sources:
                    self.assertIn(src, text, f"{filename} footnotes missing canonical Base Thesis source '{src}'")

            body_only = re.split(r"---\r?\n", text, maxsplit=2)[2]
            body_only = re.sub(r"<figure\b.*?</figure>", "", body_only, flags=re.DOTALL)
            body_only = re.sub(r'<aside class="for-researchers">.*?</aside>', "", body_only, flags=re.DOTALL)
            body_only = re.sub(r'<section class="footnotes">.*?</section>', "", body_only, flags=re.DOTALL)
            for leak in forbidden_body_leaks:
                self.assertNotIn(leak, body_only, f"{filename} leaked '{leak}' into everyday body prose")

    def test_claim_first_opening_and_voice_humanizer_sentence_invariants(self) -> None:
        for filename, _ in ALL_SOVEREIGN_PAGE_CASES:
            text = self.texts[filename]
            takeaway_match = re.search(r"^takeaway:\s*(.+)$", text, flags=re.M)
            self.assertIsNotNone(takeaway_match, f"{filename} missing takeaway front matter")
            takeaway = takeaway_match.group(1).strip()

            body = re.split(r"---\r?\n", text, maxsplit=2)[2]
            body_no_aside = re.sub(r"<figure\b.*?</figure>", " ", body, flags=re.DOTALL)
            body_no_aside = re.sub(r'<aside class="for-researchers">.*?</aside>', " ", body_no_aside, flags=re.DOTALL)
            body_no_aside = re.sub(r'<section class="footnotes">.*?</section>', " ", body_no_aside, flags=re.DOTALL)

            first_big = re.search(r'<p class="big">(.*?)</p>', body_no_aside, flags=re.S)
            self.assertIsNotNone(first_big, f"{filename} missing opening <p class=\"big\">")
            first_big_plain = re.sub(r"<[^>]+>", "", first_big.group(1)).strip()
            self.assertTrue(
                first_big_plain.startswith(takeaway[:45]),
                f"{filename} does not open sentence 1 with its direct takeaway claim: {first_big_plain[:80]}",
            )

            self.assertNotIn("—", body_no_aside, f"{filename} contains em-dash in body prose")
            for forbidden in ("rather than", "instead of", "not just", "not only", "not merely"):
                self.assertNotIn(forbidden, body_no_aside.lower(), f"{filename} contains '{forbidden}'")

            ps = re.findall(r"<p\b[^>]*>(.*?)</p>", body_no_aside, flags=re.DOTALL)
            sentences = []
            for p in ps:
                if "lp-sec-kicker" in p:
                    continue
                ct = re.sub(r"<sup>.*?</sup>", "", p)
                ct = re.sub(r"<[^>]+>", " ", ct)
                ct = re.sub(r"\s+", " ", ct).strip()
                for s in re.split(r"(?<=[.!?])\s+", ct):
                    if len(s.split()) > 3:
                        sentences.append(s)
            counts = [len(s.split()) for s in sentences]
            self.assertLessEqual(statistics.median(counts), 20.0, f"{filename} median sentence > 20")
            self.assertLessEqual(max(counts), 35, f"{filename} max sentence > 35")


if __name__ == "__main__":
    unittest.main()
