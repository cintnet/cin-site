"""Tests for Spec 05 mobile/dark-mode SVG parity, zero-contrast prose, and 16-term
five-primitive Base Thesis grounding across the six Labs workbenches and technical paper hubs."""

from pathlib import Path
import re
import statistics
import unittest
import xml.etree.ElementTree as ET


SITE_ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = SITE_ROOT / "content"

DUAL_SVG_PAGE_CASES = (
    ("labs/institutions.html", "ex-institutions-overview"),
    ("labs/lab-overlays.html", "ex-lab-overlays-topology"),
    ("labs/lab-papers/index.html", "ex-lp-hub-blueprint"),
    ("labs/sovereign-authorities.html", "ex-sovereign-authorities-topology"),
    ("labs/sovereign-papers/index.html", "ex-sp-hub-blueprint"),
)

ALL_LABS_PAGES = (
    "labs/institutions.html",
    "labs/lab-overlays.html",
    "labs/lab-papers/index.html",
    "labs/sovereign-authorities.html",
    "labs/sovereign-papers/index.html",
    "labs/simulations.html",
)

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

FORBIDDEN_HUMANIZER_WORDS = (
    "delve",
    "tapestry",
    "testament",
    "underscore",
    "showcase",
    "foster",
    "pivotal",
    "intricate",
    "realm",
    "vibrant",
    "seamless",
    "crucial",
    "landscape",
)


def _extract_visible_prose(raw_html: str) -> str:
    body = raw_html.split("---\n", 2)[2]
    body = re.sub(
        r"<(style|script|figure|svg|aside|table|nav|form)[^>]*>.*?</\1>",
        " ",
        body,
        flags=re.DOTALL | re.IGNORECASE,
    )
    body = re.sub(
        r'<section class="footnotes">.*?</section>',
        " ",
        body,
        flags=re.DOTALL | re.IGNORECASE,
    )
    body = re.sub(r"</(h[1-6]|p|li|div|button|span|output|label)>", ". ", body, flags=re.IGNORECASE)
    body = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", body).strip()


class SiteCriticLabsWorkbenchesAndHubsSpec05Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.texts = {
            rel_path: (CONTENT_DIR / rel_path).read_text(encoding="utf-8")
            for rel_path in ALL_LABS_PAGES
        }

    def test_spec05_unboxed_dark_mode_and_dual_responsive_svgs(self) -> None:
        """All five schematic overview figures must define prefers-color-scheme: dark and
        [data-theme='dark'] with #8FD4B6 and #F09D82 tokens, pair .diagram-desktop with
        .diagram-mobile SVGs, and keep all SVG text >= 11px and mobile text right-edge <= 310px,
        while simulations.html defines dark-mode parity and >= 11px text across both wind-tunnel charts."""
        for rel_path, fig_id in DUAL_SVG_PAGE_CASES:
            raw = self.texts[rel_path]
            fig_m = re.search(
                rf'<figure\b[^>]*\bid=["\']{re.escape(fig_id)}["\'][^>]*>(.*?)</figure>',
                raw,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(fig_m, f"Missing figure #{fig_id} in {rel_path}")
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
                self.assertIn(token, fig_html, f"{rel_path} (#{fig_id}) missing Spec 05 token: {token}")
            self.assertNotIn("prefers-color-scheme: dark", fig_html)

            svgs = re.findall(r"<svg\b[^>]*>.*?</svg>", fig_html, flags=re.DOTALL)
            self.assertEqual(len(svgs), 2, f"{rel_path} (#{fig_id}) must contain desktop + mobile SVGs")

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
                                f"{rel_path} has SVG <text> below 11px: {fs}",
                            )

            mobile_root = ET.fromstring(svgs[1])
            vb_parts = mobile_root.attrib.get("viewBox", "0 0 999 0").split()
            self.assertLessEqual(float(vb_parts[2]), 330.0, f"{rel_path} mobile viewBox width > 330")
            if rel_path != "labs/lab-papers/index.html":
                self.assertLessEqual(float(vb_parts[2]), 310.0, f"{rel_path} mobile viewBox width > 310")
                self.assertIn("<line", svgs[1], f"{rel_path} .diagram-mobile missing connector <line>")
                self.assertIn("<polygon", svgs[1], f"{rel_path} .diagram-mobile missing arrowhead <polygon>")
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
                    f"{rel_path} mobile SVG text '{content}' overflows 310px bound ({right_edge:.1f})",
                )

        sim_raw = self.texts["labs/simulations.html"]
        sim_takeaway = re.search(r"^takeaway:\s*(.+)$", sim_raw, flags=re.M)
        self.assertIsNotNone(sim_takeaway)
        sim_first_big = re.search(r'<p class="big">(.*?)</p>', sim_raw, flags=re.DOTALL)
        self.assertIsNotNone(sim_first_big)
        self.assertTrue(
            re.sub(r"<[^>]+>", "", sim_first_big.group(1)).strip().startswith(sim_takeaway.group(1).strip()[:45])
        )
        for token in (
            "Endel Tulving",
            "Joscha Bach",
            "Andy Clark",
            "David Chalmers",
            "Jack Balkin",
            "Karl Friston",
            "Jack B. Dennis",
            "Earl C. Van Horn",
            "Jacob Meluso",
            "James Stodder",
            "Rudolf Meidner",
            "Elinor Ostrom",
            "/labs/shared-horizon/",
        ):
            self.assertIn(token, sim_raw, f"labs/simulations.html researcher aside missing '{token}'")
        for token in (
            "background: transparent",
            "border-top: 1px solid",
            "border-bottom: 1px solid",
            '[data-theme="dark"]',
            "#8FD4B6",
            "#F09D82",
        ):
            self.assertIn(token, sim_raw, f"labs/simulations.html missing Spec 05 token: {token}")
        self.assertNotIn("prefers-color-scheme: dark", sim_raw)
        for svg_str in re.findall(r"<svg\b[^>]*>.*?</svg>", sim_raw, flags=re.DOTALL):
            root = ET.fromstring(svg_str)
            for elem in root.iter():
                if elem.tag.split("}")[-1] == "text":
                    fs = elem.attrib.get("font-size")
                    if fs is not None:
                        self.assertGreaterEqual(float(fs.replace("px", "")), 11.0)

    def test_base_thesis_sixteen_term_grounding_and_anti_leak_gate(self) -> None:
        """All six Labs pages must reference all canonical five-primitive Base Thesis terms
        inside <aside class='for-researchers'> while keeping body prose free of leaked internal terms."""
        for rel_path in ALL_LABS_PAGES:
            raw = self.texts[rel_path]
            asides = re.findall(
                r'<aside class="for-researchers">(.*?)</aside>',
                raw,
                flags=re.DOTALL,
            )
            self.assertGreaterEqual(len(asides), 1, f"{rel_path} missing <aside class='for-researchers'>")
            combined_asides = "\n".join(asides)
            for term in REQUIRED_BASE_THESIS_TERMS:
                self.assertIn(term, combined_asides, f"{rel_path} researcher aside missing '{term}'")

            if rel_path in (
                "labs/institutions.html",
                "labs/lab-overlays.html",
                "labs/sovereign-authorities.html",
                "labs/sovereign-papers/index.html",
                "labs/simulations.html",
            ):
                takeaway_m = re.search(r"^takeaway:\s*(.+)$", raw, flags=re.M)
                self.assertIsNotNone(takeaway_m, f"{rel_path} missing takeaway front matter")
                takeaway = takeaway_m.group(1).strip()
                body_after_fm = raw.split("---\n", 2)[2]
                first_p = re.search(r"<p(?:\s+[^>]*)?>(.*?)</p>", body_after_fm, flags=re.DOTALL)
                self.assertIsNotNone(first_p, f"{rel_path} missing opening <p>")
                first_p_plain = re.sub(r"<[^>]+>", "", first_p.group(1)).strip()
                self.assertTrue(
                    first_p_plain.startswith(takeaway[:45]),
                    f"{rel_path} does not open sentence 1 with its direct takeaway claim: {first_p_plain[:80]}",
                )
                for scholar in (
                    "Endel Tulving",
                    "Joscha Bach",
                    "Andy Clark",
                    "David Chalmers",
                    "Jack Balkin",
                    "Karl Friston",
                    "Dennis",
                    "Van Horn",
                    "Jacob Meluso",
                    "James Stodder",
                    "Rudolf Meidner",
                    "Elinor Ostrom",
                    "/labs/shared-horizon/",
                ):
                    self.assertIn(scholar, combined_asides, f"{rel_path} researcher aside missing '{scholar}'")

            body_only = raw.split("---\n", 2)[2]
            body_only = re.sub(
                r'<aside class="for-researchers">.*?</aside>',
                "",
                body_only,
                flags=re.DOTALL,
            )
            body_only = re.sub(
                r'<section class="footnotes">.*?</section>',
                "",
                body_only,
                flags=re.DOTALL,
            )
            body_only = re.sub(
                r"<script\b[^>]*>.*?</script>",
                "",
                body_only,
                flags=re.DOTALL,
            )
            for leak in FORBIDDEN_BODY_LEAKS:
                self.assertNotIn(leak, body_only, f"{rel_path} leaked '{leak}' into body prose")

    def test_zero_contrast_prose_and_sentence_length_invariants(self) -> None:
        """All six Labs pages must eliminate instead-of and rather-than contrast constructions
        in visible HTML and researcher asides, contain zero em-dashes or stock AI words,
        and maintain median <= 22w and max <= 35w."""
        contrast_re = re.compile(r"\b(?:instead of|rather than|not only|not merely)\b", re.IGNORECASE)
        for rel_path in ALL_LABS_PAGES:
            raw = self.texts[rel_path]
            html_without_json = re.sub(r"<script\b[^>]*>.*?</script>", "", raw, flags=re.DOTALL)
            self.assertIsNone(
                contrast_re.search(html_without_json),
                f"{rel_path} still contains negative contrast phrasing: {contrast_re.findall(html_without_json)}",
            )

            prose = _extract_visible_prose(raw)
            self.assertNotIn("—", prose, f"{rel_path} contains em-dash in body prose")
            lower = prose.lower()
            for word in FORBIDDEN_HUMANIZER_WORDS:
                self.assertIsNone(
                    re.search(rf"\b{word}\b", lower),
                    f"{rel_path} body prose contains forbidden humanizer word '{word}'",
                )

            sentences = [
                s.strip()
                for s in re.split(r'[.?!]["\u2019\u201d\')\]]*(?:\s+|$)', prose)
                if len(s.strip().split()) >= 4
            ]
            self.assertGreaterEqual(len(sentences), 8, f"{rel_path} has too few sentences")
            lengths = [len(s.split()) for s in sentences]
            self.assertLessEqual(
                statistics.median(lengths),
                22.0,
                f"{rel_path} median sentence length {statistics.median(lengths)} > 22.0 words",
            )
            self.assertLessEqual(
                max(lengths),
                35,
                f"{rel_path} max sentence length {max(lengths)} > 35 words",
            )


if __name__ == "__main__":
    unittest.main()
