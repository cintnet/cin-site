#!/usr/bin/env python3
"""Unit tests for the self-hosted AI tools rollback-checkpoint essay, Spec 05 pastel watercolor
illustration and dual desktop/mobile SVG explainer, 38+14-term Base Thesis grounding,
and eight timestamped podcast concern reflections across cintnet.org/blog/ (P-0531)."""

from pathlib import Path
import re
import statistics
import unittest
import xml.etree.ElementTree as ET

TESTS_DIR = Path(__file__).resolve().parent
SITE_ROOT = TESTS_DIR.parent
CONTENT_DIR = SITE_ROOT / "content"
IMG_DIR = SITE_ROOT / "assets" / "img"

TARGET_PAGES = (
    ("blog/why-running-your-own-ai-tools-needs-a-rollback-checkpoint.html", "ex-byte-memory-rollback"),
    ("blog/slowing-frontier-training-without-a-global-censor.html", "ex-seismic-threshold"),
    ("blog/eight-ways-ai-goes-wrong.html", "ex-eight-harbors"),
    ("blog/aviation-safety-for-ai-infrastructure.html", "ex-valve-interlock"),
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
    "dead-man",
    "C2PA",
    "Merkle",
    "Tulving",
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
    "Object-Capability",
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

REQUIRED_14_FULL_NAME_TERMS = (
    "observation confidence",
    "biological person",
    "personal cognitive model",
    "cybernetic exocortex",
    "Joscha Bach",
    "Jack Balkin",
    "unassisted competence",
    "Karl Friston",
    "Endel Tulving",
    "Elinor Ostrom",
    "Rudolf Meidner",
    "James Stodder",
    "Jacob Meluso",
    "Andy Clark &amp; David Chalmers",
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


class PublisherByteChunkingRollbackAndPodcastReflectionsSpec05Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.texts = {}
        for rel_path, _ in TARGET_PAGES:
            path = CONTENT_DIR / rel_path
            assert path.is_file(), f"Missing target page: {path}"
            cls.texts[rel_path] = path.read_text(encoding="utf-8")

    def test_new_essay_spec05_watercolor_asset_and_dual_svg_explainer(self) -> None:
        img_path = IMG_DIR / "post-why-running-your-own-ai-tools-needs-a-rollback-checkpoint.jpg"
        self.assertTrue(img_path.is_file(), f"Missing illustration asset: {img_path}")
        size_bytes = img_path.stat().st_size
        self.assertGreater(size_bytes, 10_000)
        self.assertLess(size_bytes, 300_000, f"Illustration exceeds 300 KB: {size_bytes}")

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
            self.assertIn(f':root[data-theme="dark"] #{fig_id}', fig_content)
            self.assertIn("#8FD4B6", fig_content)
            self.assertIn("#F09D82", fig_content)
            self.assertIn("background: transparent", fig_content)
            self.assertIn('class="diagram-desktop"', fig_content)
            self.assertIn('class="diagram-mobile"', fig_content)

            svgs = re.findall(r"<svg\b[^>]*>.*?</svg>", fig_content, re.DOTALL)
            self.assertEqual(len(svgs), 2, f"{rel_path} #{fig_id} must contain desktop and mobile SVGs")

            mobile_root = ET.fromstring(svgs[1])
            mobile_lines = list(mobile_root.iter("line"))
            mobile_polys = list(mobile_root.iter("polygon"))
            self.assertGreaterEqual(len(mobile_lines), 3, f"{rel_path} mobile SVG missing stage connector lines")
            self.assertGreaterEqual(len(mobile_polys), 3, f"{rel_path} mobile SVG missing directional arrowheads")

            mobile_texts = list(mobile_root.iter("text"))
            self.assertLess(len(mobile_texts), 28, f"{rel_path} mobile SVG exceeds 27 text nodes")
            for text_el in mobile_texts:
                content = (text_el.text or "").strip()
                if not content:
                    continue
                x = float(text_el.attrib.get("x", "0"))
                fs = float(text_el.attrib.get("font-size", "11"))
                self.assertGreaterEqual(fs, 11.0, f"{rel_path} mobile SVG text below 11px")
                anchor = text_el.attrib.get("text-anchor", "start")
                est_w = len(content) * (fs * 0.58)
                right_edge = x + (est_w / 2) if anchor == "middle" else (x if anchor == "end" else x + est_w)
                self.assertLessEqual(
                    right_edge,
                    310.0,
                    f"{rel_path} mobile SVG text '{content}' overflows 310px bound (right_edge={right_edge:.1f})",
                )

    def test_base_thesis_grounding_arxiv_citations_and_eight_podcast_reflections(self) -> None:
        for rel_path, _ in TARGET_PAGES:
            text = self.texts[rel_path]
            asides = re.findall(r'<aside class="for-researchers">(.*?)</aside>', text, re.DOTALL)
            self.assertGreaterEqual(len(asides), 1, f"{rel_path} must contain researcher aside")
            aside_combined = "\n".join(asides)
            for term in REQUIRED_38_BASE_THESIS_TERMS:
                self.assertIn(term, aside_combined, f"{rel_path} researcher aside missing '{term}'")
            for extra in REQUIRED_14_FULL_NAME_TERMS:
                self.assertIn(extra, aside_combined, f"{rel_path} researcher aside missing full-name term '{extra}'")

            body_only = text.split("---\n", 2)[2]
            body_only = re.sub(r"<figure\b.*?</figure>", "", body_only, flags=re.DOTALL)
            body_only = re.sub(r'<aside class="for-researchers">.*?</aside>', "", body_only, flags=re.DOTALL)
            body_only = re.sub(r'<section class="footnotes">.*?</section>', "", body_only, flags=re.DOTALL)
            for leak in FORBIDDEN_BODY_LEAKS:
                self.assertNotIn(leak, body_only, f"{rel_path} leaked '{leak}' into everyday body prose")

        rb_text = self.texts["blog/why-running-your-own-ai-tools-needs-a-rollback-checkpoint.html"]
        self.assertIn("/labs/shared-horizon/", rb_text)
        for arxiv_id in ("arXiv:2608.02613", "arXiv:2611.15729", "arXiv:2611.20144", "arXiv:2611.07554", "arXiv:2512.15688", "arXiv:2503.18813"):
            self.assertIn(arxiv_id, rb_text)
        for vid in ("AxQE_ash8b8", "TtOoLanFzGw", "6RYD6yZVcUY", "5eON_8rgKzk"):
            self.assertIn(f"https://www.youtube.com/watch?v={vid}", rb_text)

        self.assertIn("https://www.youtube.com/watch?v=7n3cZzR0tVE", self.texts["blog/slowing-frontier-training-without-a-global-censor.html"])
        self.assertIn("https://www.youtube.com/watch?v=6RYD6yZVcUY", self.texts["blog/slowing-frontier-training-without-a-global-censor.html"])
        self.assertIn("https://www.youtube.com/watch?v=gDW9An30_c0", self.texts["blog/eight-ways-ai-goes-wrong.html"])
        self.assertIn("https://www.youtube.com/watch?v=5eON_8rgKzk", self.texts["blog/eight-ways-ai-goes-wrong.html"])
        self.assertIn("https://www.youtube.com/watch?v=AxQE_ash8b8", self.texts["blog/eight-ways-ai-goes-wrong.html"])
        self.assertIn("https://www.youtube.com/watch?v=xjX3jESpZqs", self.texts["blog/aviation-safety-for-ai-infrastructure.html"])
        self.assertIn("https://www.youtube.com/watch?v=rCZFomL5WBg", self.texts["blog/aviation-safety-for-ai-infrastructure.html"])
        self.assertIn("https://www.youtube.com/watch?v=gDW9An30_c0", self.texts["blog/aviation-safety-for-ai-infrastructure.html"])

    def test_voice_and_humanizer_sentence_invariants(self) -> None:
        for rel_path, _ in TARGET_PAGES:
            text = self.texts[rel_path]
            takeaway_m = re.search(r"^takeaway:\s*(.+)$", text, flags=re.M)
            self.assertIsNotNone(takeaway_m, f"{rel_path} missing takeaway front matter")
            takeaway = takeaway_m.group(1).strip()

            body = text.split("---\n", 2)[2]
            body_no_aside = re.sub(r"<figure\b.*?</figure>", " ", body, flags=re.DOTALL)
            body_no_aside = re.sub(r'<aside class="for-researchers">.*?</aside>', " ", body_no_aside, flags=re.DOTALL)
            body_no_aside = re.sub(r'<section class="footnotes">.*?</section>', " ", body_no_aside, flags=re.DOTALL)
            self.assertNotIn("—", body_no_aside, f"{rel_path} contains em-dash in body prose")
            self.assertNotIn("rather than", body_no_aside.lower(), f"{rel_path} contains 'rather than'")
            self.assertNotIn("instead of", body_no_aside.lower(), f"{rel_path} contains 'instead of'")

            first_p = re.search(r"<p>(.*?)</p>", body_no_aside, flags=re.S)
            self.assertIsNotNone(first_p, f"{rel_path} missing opening paragraph")
            first_p_plain = re.sub(r"<[^>]+>", "", first_p.group(1)).strip()
            self.assertTrue(
                first_p_plain.startswith(takeaway[:45]),
                f"{rel_path} does not open sentence 1 with its direct takeaway claim",
            )

            ps = re.findall(r"<(?:p|li)\b[^>]*>(.*?)</(?:p|li)>", body_no_aside, flags=re.DOTALL)
            word_counts = []
            for p_html in ps:
                plain = re.sub(r"<sup\b[^>]*>.*?</sup>", "", p_html, flags=re.DOTALL)
                plain = re.sub(r"<[^>]+>", " ", plain)
                plain = re.sub(r"\s+", " ", plain).strip()
                for sent in re.split(r"(?<=[.!?])\s+", plain):
                    words = [w for w in sent.split() if w]
                    if len(words) >= 3:
                        word_counts.append(len(words))
                        self.assertLessEqual(len(words), 35, f"{rel_path} sentence exceeds 35 words: {sent}")
            self.assertLessEqual(statistics.median(word_counts), 20.0, f"{rel_path} median sentence length > 20.0")


if __name__ == "__main__":
    unittest.main()
