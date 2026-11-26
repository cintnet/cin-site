#!/usr/bin/env python3
"""Regression suite for claim-first openings, Spec 05 <=310px mobile SVG bounds,
38+14-term five-primitive Base Thesis grounding, and November 2026 primary-source
reporting across the five civic Get-Involved guides (index.html, everyone.html,
civil-society.html, builders.html, and policy.html)."""
from __future__ import annotations

import re
import statistics
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = SITE_DIR / "content"

FIVE_CIVIC_GUIDES = (
    ("get-involved/index.html", "ex-five-roles-cycle"),
    ("get-involved/everyone.html", "ex-everyday-checks"),
    ("get-involved/civil-society.html", "ex-civil-society-defense"),
    ("get-involved/builders.html", "ex-builder-circuits"),
    ("get-involved/policy.html", "ex-policy-procurement-gates"),
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
    "/labs/sovereign-papers/",
)

REQUIRED_14_EXPANDED_BASE_THESIS_TERMS = (
    "observation confidence",
    "optical data diode",
    "dead-man",
    "episodic memory vault",
    "Endel Tulving",
    "Joscha Bach",
    "Andy Clark",
    "David Chalmers",
    "Jack Balkin",
    "unassisted competence",
    "Karl Friston",
    "Object-Capability",
    "Jacob Meluso",
    "James Stodder",
    "Rudolf Meidner",
    "Elinor Ostrom",
)

REQUIRED_PRIMITIVE_TERMS_AND_CITATIONS = (
    "egocentric",
    "sensorium",
    "transduction realism",
    "Extended Mind",
    "monogamous",
    "personal cognitive model",
    "exocortex",
    "Good Regulator",
    "do(x)",
    "zero-knowledge",
    "polycentric",
    "merit-bonded",
    "frontier-lab overlays",
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


class CommunityFiveGetInvolvedGuidesSpec05AndReportingTests(unittest.TestCase):
    def test_claim_first_openings_and_zero_negative_contrasts(self) -> None:
        for rel_path, _ in FIVE_CIVIC_GUIDES:
            raw = (CONTENT_DIR / rel_path).read_text(encoding="utf-8")
            _, fm, body = raw.split("---", 2)
            m_takeaway = re.search(r"^takeaway:\s*(.+)$", fm, flags=re.M)
            self.assertIsNotNone(m_takeaway, f"{rel_path} missing takeaway front-matter")
            takeaway = m_takeaway.group(1).strip()

            m_first_big = re.search(r'<p class="big">(.*?)</p>', body, flags=re.S)
            self.assertIsNotNone(m_first_big, f"{rel_path} missing opening <p class=\"big\">")
            first_big = re.sub(r"<[^>]+>", "", m_first_big.group(1)).strip()
            self.assertTrue(
                first_big.startswith(takeaway),
                f"{rel_path} opening <p class=\"big\"> must begin with exact takeaway claim",
            )

            everyday = re.sub(r'<aside\b[^>]*for-researchers[^>]*>.*?</aside>', "", body, flags=re.S)
            everyday = re.sub(r'<section class="footnotes">.*?</section>', "", everyday, flags=re.S)
            everyday = re.sub(r"<figure\b.*?</figure>", "", everyday, flags=re.S)
            text_only = re.sub(r"<[^>]+>", " ", everyday)
            self.assertNotIn("—", text_only, f"{rel_path} everyday prose contains em-dash")
            for forbidden in ("rather than", "instead of", "not just", "not only", "not merely"):
                self.assertIsNone(
                    re.search(rf"\b{re.escape(forbidden)}\b", text_only, flags=re.I),
                    f"{rel_path} everyday prose contains forbidden contrast {forbidden!r}",
                )
            self.assertIsNone(
                re.search(r"(?:^|[.!?]\s+)Instead,", text_only),
                f"{rel_path} everyday prose contains sentence-initial 'Instead,'",
            )

            ps = re.findall(r"<(?:p|li)\b[^>]*>(.*?)</(?:p|li)>", everyday, flags=re.S)
            sentences = []
            for p in ps:
                ct = re.sub(r"<sup[^>]*>.*?</sup>", "", p)
                ct = re.sub(r"<[^>]+>", " ", ct)
                ct = re.sub(r"\s+", " ", ct).strip()
                for s in re.split(r"(?<=[.!?])\s+", ct):
                    if len(s.split()) > 3:
                        sentences.append(s)
            counts = [len(s.split()) for s in sentences]
            self.assertLessEqual(statistics.median(counts), 20.0, f"{rel_path} median sentence > 20")
            self.assertLessEqual(max(counts), 34, f"{rel_path} max sentence > 34")

    def test_spec05_dark_mode_and_mobile_310px_bounds(self) -> None:
        for rel_path, fig_id in FIVE_CIVIC_GUIDES:
            raw = (CONTENT_DIR / rel_path).read_text(encoding="utf-8")
            m_fig = re.search(
                rf'<figure\b[^>]*\bid="{re.escape(fig_id)}"[^>]*>(.*?)</figure>',
                raw,
                flags=re.S,
            )
            self.assertIsNotNone(m_fig, f"{rel_path} missing figure#{fig_id}")
            fig = m_fig.group(1)

            self.assertIn("background: transparent", fig, rel_path)
            self.assertNotIn("prefers-color-scheme: dark", fig, rel_path)
            self.assertIn(f':root[data-theme="dark"] #{fig_id}', fig, rel_path)
            self.assertIn(f'[data-theme="dark"] #{fig_id}', fig, rel_path)
            self.assertIn("#8FD4B6", fig, rel_path)
            self.assertIn("#F09D82", fig, rel_path)

            svgs = re.findall(r"<svg\b[^>]*>.*?</svg>", fig, flags=re.S)
            self.assertEqual(len(svgs), 2, f"{rel_path} must contain desktop and mobile SVGs")

            mobile_root = ET.fromstring(svgs[1])
            mobile_rects = [el for el in mobile_root.iter() if el.tag.split("}")[-1] == "rect"]
            self.assertEqual(mobile_rects[0].attrib.get("fill"), "#FAF3EA", f"{rel_path} mobile SVG first rect must be #FAF3EA")

            for rect_el in mobile_rects:
                x = float(rect_el.attrib.get("x", "0"))
                w = float(rect_el.attrib.get("width", "0"))
                self.assertLessEqual(x + w, 310.0, f"{rel_path} mobile rect x+width={x+w} > 310")

            for text_el in [el for el in mobile_root.iter() if el.tag.split("}")[-1] == "text"]:
                content = (text_el.text or "").strip()
                if not content:
                    continue
                x = float(text_el.attrib.get("x", "0"))
                fs = float(text_el.attrib.get("font-size", "11"))
                anchor = text_el.attrib.get("text-anchor", "start")
                est_w = len(content) * (fs * 0.58)
                right_edge = x + (est_w / 2) if anchor == "middle" else (x if anchor == "end" else x + est_w)
                self.assertLessEqual(right_edge, 310.0, f"{rel_path} mobile text {content!r} right_edge={right_edge:.1f} > 310")

    def test_38_plus_14_base_thesis_and_nov2026_reporting_grounding(self) -> None:
        for rel_path, _ in FIVE_CIVIC_GUIDES:
            raw = (CONTENT_DIR / rel_path).read_text(encoding="utf-8")
            asides = re.findall(r'<aside\b[^>]*for-researchers[^>]*>(.*?)</aside>', raw, flags=re.S)
            self.assertTrue(asides, f"{rel_path} missing researcher aside")
            aside = "\n".join(asides)

            for term in REQUIRED_38_EXACT_BASE_THESIS_TERMS:
                self.assertIn(term, aside, f"{rel_path} researcher aside missing {term!r}")
            for term in REQUIRED_14_EXPANDED_BASE_THESIS_TERMS:
                self.assertIn(term.lower(), aside.lower(), f"{rel_path} researcher aside missing {term!r}")
            for term in REQUIRED_PRIMITIVE_TERMS_AND_CITATIONS:
                self.assertIn(term, aside, f"{rel_path} researcher aside missing {term!r}")

        everyone_raw = (CONTENT_DIR / "get-involved/everyone.html").read_text(encoding="utf-8")
        for cite in (
            "2611.07554",
            "2611.25821",
            "2611.20144",
            "2611.15729",
            "2610.11351",
            "2610.10620",
            "2610.05532",
            "2611.02527",
            "2611.03223",
            "2611.16492",
            "2611.25599",
            "2611.25945",
            "2611.25470",
            "2507.07955",
            "2611.22971",
            "2611.24025",
            "2611.09721",
            "2611.27095",
            "2610.37741",
            "2610.07510",
            "2611.32946",
            "ai-supply-chain-security-canary-tokens",
            "ghost-hunt-a-steering-approach-to-model-backdoors-1",
            "cohere-s-qwen-incident-giving-the-suspected-backdoor-a-way",
            "personal-intelligence-apps",
            "backblaze.com/company/privacy.html",
            "Kaiqu Liang",
            "Shengwei You",
            "Chirag Goel",
            "Chirag Ahuja",
            "Lucas Florin",
            "William Guey",
            "Shiva Pochampally",
            "Junwei Yao",
            "Yiwei Zha",
            "Haitao Cheng",
            "Meghana Aparna Sistla",
            "Qifan Wang",
            "Zihao Dan",
            "Sukjun Hwang",
            "Yuxuan Zhou",
            "Ziyuan Wang",
            "David H. Yang",
            "Sean Maxwell",
            "Xinyan Hu",
            "Qiusi Zhan",
            "Vincent Koc",
            "HD Moore",
            "Daria-Teodora Harabor",
            "Geoffrey Voyer",
            "2611.04086",
            "2611.22223",
            "2608.17148",
            "2610.03394",
            "51rbs_HA3m4",
            "Shravya Kanchi",
            "Chaklam Cheong",
            "Sibo Liu",
            "Yuhai Long",
            "2509.21712",
            "2611.25985",
            "2611.26966",
            "Bingcan Guo",
            "Natasha E Blycha",
            "Deepak Waghmare",
        ):
            self.assertIn(cite, everyone_raw, f"everyone.html missing primary-source citation {cite!r}")

        builders_raw = (CONTENT_DIR / "get-involved/builders.html").read_text(encoding="utf-8")
        for cite in (
            "2611.30848",
            "2507.09089",
            "2601.20789",
            "2611.26966",
            "Frederic Lemieux",
            "Joel Becker",
            "Ethan Shen",
            "Deepak Waghmare",
        ):
            self.assertIn(cite, builders_raw, f"builders.html missing primary-source citation {cite!r}")

        civil_raw = (CONTENT_DIR / "get-involved/civil-society.html").read_text(encoding="utf-8")
        for cite in (
            "2606.08919",
            "2606.21399",
            "2611.10884",
            "2611.12167",
            "2611.10620",
            "2611.03412",
            "2611.08456",
            "2611.08452",
            "2610.34777",
            "2611.20045",
            "2611.21832",
            "2608.00801",
            "2605.26079",
            "2611.24185",
            "2611.24491",
            "2611.23346",
            "2611.17460",
            "2611.08781",
            "2611.12604",
            "2611.23202",
            "2611.22223",
            "2611.04461",
            "2609.02690",
            "2611.04086",
            "rfc9901",
            "51rbs_HA3m4",
            "mirror-dimension-for-agents",
            "reportondemocracyatwork.org",
            "2026-11-20-q4-2026-capability-update",
            "software-world-model",
            "transparency.org.au",
            "Turan",
            "Zhang",
            "Sun",
            "Wei",
            "Mohsin",
            "Liu",
            "Storey",
            "Wang",
            "Niu",
            "Luo",
            "Shenoy",
            "Sokolov",
            "Joshi",
            "Transparency International Australia",
            "Ruan",
            "Lim",
            "Shah",
            "Lee",
            "Peng",
            "Kinniment",
            "Trask",
            "Selya",
            "Nguyen",
            "Ferreras",
            "Cheong",
            "Fujie",
            "Ding",
            "Kanchi",
            "2611.30848",
            "2507.09089",
            "2601.20789",
            "2611.25985",
            "2611.26966",
            "Lemieux",
            "Becker",
            "Shen",
            "Blycha",
            "Waghmare",
        ):
            self.assertIn(cite, civil_raw, f"civil-society.html missing primary-source citation {cite!r}")


if __name__ == "__main__":
    unittest.main()
