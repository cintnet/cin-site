"""Tests for Shared Horizon and Labs hub synchronization (1,000+ verified moves, 43 AI Labs & 50 Safety Groups),
Spec 05 mobile/dark-mode SVG parity (#ex-horizon-phases and #ex-sandbox-safety), and five-primitive Base Thesis grounding."""

from __future__ import annotations

from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET


SITE_ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = SITE_ROOT / "content"

REQUIRED_BASE_THESIS_TERMS = (
    "Device Time",
    "PUF",
    "TCG DICE",
    "DMTF SPDM",
    "IETF RATS",
    "RFC 9334",
    "optical data diodes",
    "IEC 61508",
    "C2PA",
    "analog hole",
    "1:1",
    "information fiduciary",
    "Markov blanket",
    "Private Autobiographical Ledger",
    "Public Attestation &amp; Escrow Ledger",
    "IETF SCITT",
    "Wide Network Ledger",
    "Universal Basic Services",
    "Meidner",
    "Ostrom",
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
)


class ProductSharedHorizonAndLabsSpec05SyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sh_raw = (CONTENT_DIR / "labs" / "shared-horizon.html").read_text(encoding="utf-8")
        self.labs_raw = (CONTENT_DIR / "labs" / "index.html").read_text(encoding="utf-8")

    def test_synchronized_move_and_lab_counts_across_shared_horizon_and_labs_hub(self) -> None:
        self.assertIn("over 1,000 verified real-world moves and encounters", self.sh_raw)
        self.assertNotIn("over 750 verified real-world moves", self.sh_raw)
        self.assertIn("Compare 43 AI Labs &amp; 50 Safety Groups", self.sh_raw)
        self.assertNotIn("Compare 40 AI Labs", self.sh_raw)

        self.assertIn("1,000+ VERIFIED MOVES", self.labs_raw)
        self.assertNotIn("750+ VERIFIED MOVES", self.labs_raw)

    def test_spec05_dual_responsive_svgs_and_dark_mode_tokens(self) -> None:
        for rel_name, raw, fig_id in (
            ("labs/shared-horizon.html", self.sh_raw, "ex-horizon-phases"),
            ("labs/index.html", self.labs_raw, "ex-sandbox-safety"),
        ):
            fig_m = re.search(
                rf'<figure\b[^>]*\bid=["\']{re.escape(fig_id)}["\'][^>]*>(.*?)</figure>',
                raw,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(fig_m, f"Missing #{fig_id} in {rel_name}")
            fig_html = fig_m.group(0)
            for token in (
                "background: transparent",
                "border-top: 1px solid",
                "border-bottom: 1px solid",
                '[data-theme="dark"]',
                "diagram-desktop",
                "diagram-mobile",
                "#8FD4B6",
                "#F09D82",
            ):
                self.assertIn(token, fig_html, f"{rel_name} (#{fig_id}) missing Spec 05 token: {token}")
            self.assertNotIn("prefers-color-scheme: dark", fig_html)

            svgs = re.findall(r"<svg\b[^>]*>.*?</svg>", fig_html, flags=re.DOTALL)
            self.assertEqual(len(svgs), 2, f"{rel_name} (#{fig_id}) must pair desktop and mobile SVGs")

            for svg_str in svgs:
                root = ET.fromstring(svg_str)
                self.assertIn(root.attrib.get("role"), ("img", "group"))
                for elem in root.iter():
                    if elem.tag.split("}")[-1] == "text":
                        fs = elem.attrib.get("font-size")
                        if fs is not None:
                            self.assertGreaterEqual(
                                float(fs.replace("px", "")),
                                11.0,
                                f"{rel_name} SVG <text> below 11px: {fs}",
                            )

            mobile_root = ET.fromstring(svgs[1])
            vb_parts = mobile_root.attrib.get("viewBox", "0 0 999 0").split()
            self.assertLessEqual(float(vb_parts[2]), 310.0, f"{rel_name} mobile viewBox width > 310")
            self.assertIn("<line", svgs[1])
            self.assertIn("<polygon", svgs[1])
            for text_el in mobile_root.iter():
                if text_el.tag.split("}")[-1] != "text":
                    continue
                content = (text_el.text or "").strip()
                if not content:
                    continue
                x = float(text_el.attrib.get("x", "0"))
                fs = float(text_el.attrib.get("font-size", "11").replace("px", ""))
                anchor = text_el.attrib.get("text-anchor", "start")
                est_w = len(content) * (fs * 0.58)
                right_edge = (
                    x + (est_w / 2)
                    if anchor == "middle"
                    else (x if anchor == "end" else x + est_w)
                )
                self.assertLessEqual(
                    right_edge,
                    310.0,
                    f"{rel_name} mobile SVG text '{content}' overflows 310px ({right_edge:.1f})",
                )

    def test_base_thesis_grounding_nov2026_sources_and_anti_leak_gate(self) -> None:
        for needle in (
            "https://arxiv.org/abs/2611.17115",
            "https://arxiv.org/abs/2611.11506",
            "https://arxiv.org/abs/2611.19417",
            "https://arxiv.org/abs/2611.24135",
            "https://arxiv.org/abs/2611.26983",
            "https://arxiv.org/abs/2611.10403",
            "draft-stafordtituss-agentic-mandate-evidence-02",
            "https://www.youtube.com/watch?v=pqD0K9bjhBs",
        ):
            self.assertIn(needle, self.sh_raw)

        for rel_name, raw in (
            ("labs/shared-horizon.html", self.sh_raw),
            ("labs/index.html", self.labs_raw),
        ):
            asides = re.findall(r'<aside class="for-researchers">(.*?)</aside>', raw, flags=re.DOTALL)
            self.assertGreaterEqual(len(asides), 1)
            combined_asides = "\n".join(asides)
            for term in REQUIRED_BASE_THESIS_TERMS:
                self.assertIn(term, combined_asides, f"{rel_name} researcher aside missing '{term}'")

            body_only = raw.split("---\n", 2)[2]
            body_only = re.sub(r'<aside class="for-researchers">.*?</aside>', "", body_only, flags=re.DOTALL)
            body_only = re.sub(r'<section class="footnotes">.*?</section>', "", body_only, flags=re.DOTALL)
            for leak in FORBIDDEN_BODY_LEAKS:
                self.assertNotIn(leak, body_only, f"{rel_name} leaked '{leak}' into public prose")


if __name__ == "__main__":
    unittest.main()
