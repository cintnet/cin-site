#!/usr/bin/env python3
"""Deterministic regression suite for the claim-first formal-proof translation-gap essay
('Why a checked proof can still solve the wrong problem'), Spec 05 desktop/mobile directional
arrowhead parity, deduplicated researcher disclosures, 62-term (38+14 Base Thesis + Michael
Levin cognitive light cone + Endel Tulving episodic memory) and 9-citation Base Thesis
foundations, 8-source Base Thesis URL provenance, and 14 watched YouTube podcast concern
reflections across 8 blog, frontier-lab, and workbench pages on cintnet.org (D-2285):
- site/content/blog/why-a-checked-proof-can-still-solve-the-wrong-problem.html (#ex-proof-translation-gap)
- site/content/blog/why-shared-ai-servers-leak-across-tenants.html (#ex-shared-server-isolation)
- site/content/labs/lab-overlays.html (#ex-lab-overlays-topology)
- site/content/labs/lab-papers/anthropic.html (#ex-lp-anthropic)
- site/content/labs/lab-papers/deepseek.html (#ex-lp-deepseek)
- site/content/labs/lab-papers/google-deepmind.html (#ex-lp-google-deepmind)
- site/content/labs/lab-papers/openai.html (#ex-lp-openai)
- site/content/labs/lab-papers/safe-superintelligence.html (#ex-lp-safe-superintelligence)
"""

from __future__ import annotations

import pathlib
import re
import statistics
import unittest
import xml.etree.ElementTree as ET


SITE_DIR = pathlib.Path(__file__).resolve().parents[1]
CONTENT_DIR = SITE_DIR / "content"
IMG_DIR = SITE_DIR / "assets" / "img"

PAGE_CASES: tuple[tuple[str, str], ...] = (
    ("blog/why-a-checked-proof-can-still-solve-the-wrong-problem.html", "ex-proof-translation-gap"),
    ("blog/why-shared-ai-servers-leak-across-tenants.html", "ex-shared-server-isolation"),
    ("labs/lab-overlays.html", "ex-lab-overlays-topology"),
    ("labs/lab-papers/anthropic.html", "ex-lp-anthropic"),
    ("labs/lab-papers/deepseek.html", "ex-lp-deepseek"),
    ("labs/lab-papers/google-deepmind.html", "ex-lp-google-deepmind"),
    ("labs/lab-papers/openai.html", "ex-lp-openai"),
    ("labs/lab-papers/safe-superintelligence.html", "ex-lp-safe-superintelligence"),
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


class PublisherCheckedProofAndEightPagesSpec05Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.texts = {
            rel_path: (CONTENT_DIR / rel_path).read_text(encoding="utf-8")
            for rel_path, _ in PAGE_CASES
        }

    def test_checked_proof_essay_artwork_primary_sources_and_podcast_reflections(self) -> None:
        """The new formal-proof translation-gap essay and updated shared-server essay must
        carry verified primary citations, custom < 300 KB Spec 05 watercolor vignette JPEG,
        and timestamped YouTube podcast reflections."""
        proof_img = IMG_DIR / "post-why-a-checked-proof-can-still-solve-the-wrong-problem.jpg"
        self.assertTrue(proof_img.is_file(), "Missing Spec 05 watercolor vignette JPEG")
        self.assertLess(proof_img.stat().st_size, 300_000, "Vignette JPEG exceeds 300 KB")

        proof_html = self.texts["blog/why-a-checked-proof-can-still-solve-the-wrong-problem.html"]
        for expected in (
            "arXiv:2610.08144",
            "arXiv:2610.35596",
            "arXiv:2611.02849",
            "arXiv:2611.05168",
            "youtube.com/watch?v=MkeKXJzJo98",
            "youtube.com/watch?v=n5mJ6RUIwUc",
            "youtube.com/watch?v=IRJDwtAreB4",
            "youtube.com/watch?v=KVYdy65dt0s",
            "youtube.com/watch?v=KGA7B_c_S4s",
            "youtube.com/watch?v=Ahi52SdK588",
            "youtube.com/watch?v=FiSr_OXXTTY",
            "41.6",
            "67.2",
            "44.3",
            "31.37",
            "11.64",
        ):
            self.assertIn(expected, proof_html, f"Checked-proof essay missing {expected!r}")

        shared_html = self.texts["blog/why-shared-ai-servers-leak-across-tenants.html"]
        for expected in (
            "youtube.com/watch?v=jKez48toV3U",
            "youtube.com/watch?v=3ZkDiDrxDeY",
            "youtube.com/watch?v=mg4yo5HUMuQ",
            "youtube.com/watch?v=H7Daly20npA",
            "youtube.com/watch?v=I0Fasi1-teQ",
            "youtube.com/watch?v=MAngqVza390",
        ):
            self.assertIn(expected, shared_html, f"Shared-servers essay missing {expected!r}")

    def test_all_eight_explainers_satisfy_spec05_desktop_mobile_arrowheads_and_dark_mode(self) -> None:
        """Every explainer across all 8 pages must provide dual diagram-desktop and diagram-mobile
        SVGs that parse cleanly as XML, expose dark-mode CSS variables (#8FD4B6 / #F09D82),
        maintain >= 11px font sizes, and render >= 3 explicit <line> connectors and >= 3
        directional <polygon> arrowheads in both desktop and mobile views."""
        for rel_path, fig_id in PAGE_CASES:
            raw = self.texts[rel_path]
            fig_m = re.search(
                rf'<figure\b[^>]*id=["\']{re.escape(fig_id)}["\'][^>]*>(.*?)</figure>',
                raw,
                flags=re.S,
            )
            self.assertIsNotNone(fig_m, f"{rel_path} missing figure #{fig_id}")
            fig_html = fig_m.group(1)

            for dark_token in ("#8FD4B6", "#F09D82", "prefers-color-scheme: dark", 'data-theme="dark"'):
                self.assertIn(
                    dark_token,
                    raw,
                    f"{rel_path} #{fig_id} missing dark-mode CSS token {dark_token}",
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
                    f"{rel_path} #{fig_id} {view_name} SVG must have >= 3 <line> connectors (found {len(lines)})",
                )
                self.assertGreaterEqual(
                    len(polys),
                    3,
                    f"{rel_path} #{fig_id} {view_name} SVG must have >= 3 directional <polygon> arrowheads (found {len(polys)})",
                )
                for fs in re.findall(r'font-size=["\']([0-9.]+)["\']', svg_str):
                    self.assertGreaterEqual(
                        float(fs),
                        11.0,
                        f"{rel_path} #{fig_id} {view_name} SVG has font-size={fs} < 11px",
                    )

    def test_deduplicated_researcher_asides_and_full_base_thesis_grounding(self) -> None:
        """All 8 pages must have zero duplicate paragraphs inside <aside class='for-researchers'>,
        zero leaked 'Base Thesis' labels anywhere in the HTML, all 62 Base Thesis terms and
        9 canonical citations in researcher asides, and all 8 canonical Base Thesis primary source
        URLs in <section class='footnotes'>."""
        for rel_path, _ in PAGE_CASES:
            raw = self.texts[rel_path]
            self.assertNotIn(
                "base thesis",
                raw.lower(),
                f"{rel_path} contains internal 'Base Thesis' label",
            )
            asides = re.findall(
                r'<aside\b[^>]*class=["\'][^"\']*for-researchers[^"\']*["\'][^>]*>(.*?)</aside>',
                raw,
                flags=re.S,
            )
            self.assertTrue(asides, f"{rel_path} missing <aside class='for-researchers'>")

            for aside_idx, aside_block in enumerate(asides, 1):
                paras = [
                    re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", p)).strip()
                    for p in re.findall(r"<p\b[^>]*>(.*?)</p>", aside_block, flags=re.S)
                ]
                self.assertEqual(
                    len(paras),
                    len(set(paras)),
                    f"{rel_path} aside #{aside_idx} contains duplicated paragraph text",
                )

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

            footnotes_m = re.search(
                r'<section class="footnotes">(.*?)</section>', raw, flags=re.S
            )
            self.assertIsNotNone(footnotes_m, f"{rel_path} missing <section class='footnotes'>")
            footnotes_html = footnotes_m.group(1)
            for url_token in REQUIRED_EIGHT_SOURCE_URLS:
                self.assertIn(
                    url_token,
                    footnotes_html,
                    f"{rel_path} footnotes missing canonical Base Thesis source URL {url_token!r}",
                )

    def test_everyday_prose_and_anti_leak_invariants(self) -> None:
        """All 8 pages must keep everyday prose free of em-dashes and leaked internal labels,
        and obey <= 22-word median and <= 35-word maximum sentence lengths."""
        for rel_path, _ in PAGE_CASES:
            raw = self.texts[rel_path]
            _, _, body = raw.split("---", 2)
            public_body = re.sub(r"<(style|script|figure|svg|aside)[^>]*>.*?</\1>", " ", body, flags=re.S)
            public_body = re.sub(r'<section class="footnotes">.*?</section>', " ", public_body, flags=re.S)
            public_body = re.sub(r'<div id="[a-z-]+-data"[^>]*>.*?</div>', " ", public_body, flags=re.S)
            plain = re.sub(r"<[^>]+>", " ", public_body)
            plain = re.sub(r"\s+", " ", plain).strip()

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
