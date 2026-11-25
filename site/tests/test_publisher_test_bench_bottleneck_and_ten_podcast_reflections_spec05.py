#!/usr/bin/env python3
"""Unit tests for the test-bench bottleneck essay on recursive self-improvement,
Spec 05 pastel watercolor illustration and dual desktop/mobile SVG explainer,
62-term Base Thesis grounding, and ten timestamped podcast concern reflections
across cintnet.org/blog/ (D-2332)."""

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
    ("blog/why-faster-code-still-waits-on-the-test-bench.html", "ex-test-bench-bottleneck"),
    ("blog/when-the-cider-press-runs-itself.html", "ex-coop-press-loop"),
    ("blog/no-one-should-command-a-swarm.html", "ex-swarm-locks"),
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


class PublisherTestBenchBottleneckAndTenPodcastReflectionsSpec05Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.texts = {}
        for rel_path, _ in TARGET_PAGES:
            path = CONTENT_DIR / rel_path
            assert path.is_file(), f"Missing target page: {path}"
            cls.texts[rel_path] = path.read_text(encoding="utf-8")

    def test_new_essay_spec05_watercolor_asset_and_dual_svg_explainer(self) -> None:
        img_path = IMG_DIR / "post-why-faster-code-still-waits-on-the-test-bench.jpg"
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

    def test_base_thesis_grounding_arxiv_citations_and_ten_podcast_reflections(self) -> None:
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

        tb_text = self.texts["blog/why-faster-code-still-waits-on-the-test-bench.html"]
        self.assertIn("/labs/shared-horizon/", tb_text)
        for arxiv_id in (
            "arXiv:2411.15114",
            "arXiv:2609.34262",
            "arXiv:2603.00520",
            "arXiv:2610.28679",
            "arXiv:2611.08417",
            "arXiv:2511.02997",
        ):
            self.assertIn(arxiv_id, tb_text)
        for vid in ("Em6tbhj9o6A", "HbgZFwWj4vY", "vNxdVCgyH78"):
            self.assertIn(f"https://www.youtube.com/watch?v={vid}", tb_text)

        cp_text = self.texts["blog/when-the-cider-press-runs-itself.html"]
        for vid in ("N6kzEOdzSus", "RZ4BBkSZ3io", "s5WNy6X_2FI", "M_Fzx5KzBwY", "53uYYeNC6Ek"):
            self.assertIn(f"https://www.youtube.com/watch?v={vid}", cp_text)

        sw_text = self.texts["blog/no-one-should-command-a-swarm.html"]
        for vid in ("n4nY3U0SOAw", "H43e72-2aAs", "2hJkprFnzhY"):
            self.assertIn(f"https://www.youtube.com/watch?v={vid}", sw_text)

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
