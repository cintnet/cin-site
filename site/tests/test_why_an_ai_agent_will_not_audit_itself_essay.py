"""Deterministic verification suite for why-an-ai-agent-will-not-audit-itself essay and mobile SVG explainer."""

from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

SITE_ROOT = Path(__file__).resolve().parents[1]
ESSAY_PATH = SITE_ROOT / "content" / "blog" / "why-an-ai-agent-will-not-audit-itself.html"


class TestWhyAnAiAgentWillNotAuditItselfEssay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assertTrue(ESSAY_PATH.exists(), f"Missing {ESSAY_PATH}")
        cls.text = ESSAY_PATH.read_text(encoding="utf-8")

    def test_frontmatter_integrity(self):
        """Frontmatter must include all required fields for publication."""
        match = re.match(r"^---\n(.*?)\n---", self.text, re.DOTALL)
        self.assertIsNotNone(match, "Frontmatter missing")
        fm = match.group(1)
        self.assertIn("title: Why an AI agent will not audit itself", fm)
        self.assertIn("template: article", fm)
        self.assertIn("image: post-why-an-ai-agent-will-not-audit-itself.jpg", fm)
        self.assertIn("category: Seeing", fm)
        self.assertIn("takeaway:", fm)
        self.assertIn("lede:", fm)

    def test_dual_svg_explainer_structure_and_accessibility(self):
        """Figure #ex-outside-audit must contain both desktop and mobile SVGs with role='img'."""
        fig_match = re.search(r'<figure\b[^>]*\bid=["\']ex-outside-audit["\'][^>]*>(.*?)</figure>', self.text, re.DOTALL)
        self.assertIsNotNone(fig_match, "Figure #ex-outside-audit not found")
        fig_content = fig_match.group(1)

        # Style checks for media query switching
        self.assertIn(".diagram-desktop", fig_content)
        self.assertIn(".diagram-mobile", fig_content)
        self.assertIn("@media (max-width: 640px)", fig_content)

        # Desktop SVG
        desk_match = re.search(r'<svg\b[^>]*class=["\'][^"\']*diagram-desktop[^"\']*["\'][^>]*>(.*?)</svg>', fig_content, re.DOTALL)
        self.assertIsNotNone(desk_match, "Desktop SVG missing or missing class='diagram-desktop'")
        desk_root = ET.fromstring(desk_match.group(0))
        self.assertEqual(desk_root.attrib.get("role"), "img")
        self.assertIsNotNone(desk_root.find("title"))
        self.assertIsNotNone(desk_root.find("desc"))

        # Mobile SVG
        mob_match = re.search(r'<svg\b[^>]*class=["\'][^"\']*diagram-mobile[^"\']*["\'][^>]*>(.*?)</svg>', fig_content, re.DOTALL)
        self.assertIsNotNone(mob_match, "Mobile SVG missing or missing class='diagram-mobile'")
        mob_root = ET.fromstring(mob_match.group(0))
        self.assertEqual(mob_root.attrib.get("role"), "img")
        self.assertIsNotNone(mob_root.find("title"))
        self.assertIsNotNone(mob_root.find("desc"))

    def test_mobile_svg_viewbox_and_font_bounds(self):
        """Mobile SVG text elements must fit within 330px width with font-size >= 10.5px."""
        mob_match = re.search(r'<svg\b[^>]*class=["\'][^"\']*diagram-mobile[^"\']*["\'][^>]*>(.*?)</svg>', self.text, re.DOTALL)
        self.assertIsNotNone(mob_match)
        mob_root = ET.fromstring(mob_match.group(0))

        vb = mob_root.attrib.get("viewBox", "")
        self.assertIn("330", vb, "Mobile viewBox width must be 330")

        overflows = []
        for text_el in mob_root.iter("text"):
            content = (text_el.text or "").strip()
            if not content:
                continue
            x = float(text_el.attrib.get("x", "0"))
            fs = float(text_el.attrib.get("font-size", "11"))
            self.assertGreaterEqual(fs, 10.5, f"Sub-10.5px font-size in mobile SVG: '{content}'")
            anchor = text_el.attrib.get("text-anchor", "start")
            est_width = len(content) * (fs * 0.58)
            right_edge = x + (est_width / 2) if anchor == "middle" else (x if anchor == "end" else x + est_width)
            if right_edge > 310.0:
                overflows.append(f"'{content}' (right_edge={right_edge:.1f} > 310)")

        self.assertEqual(overflows, [], "Mobile SVG text elements overflow card boundaries:\n" + "\n".join(overflows))

    def test_voice_and_sentence_length_invariants(self):
        """Prose must adhere to median <= 22 words, max <= 35 words, and zero em-dashes."""
        body = re.sub(r"^---.*?---\s*", "", self.text, flags=re.DOTALL)
        clean = re.sub(r"<(style|script|figure|svg|aside|section)[^>]*>.*?</\1>", "", body, flags=re.DOTALL)
        clean_text = re.sub(r"<[^>]+>", " ", clean)

        sentences = [s.strip() for s in re.split(r"[.!?]+", clean_text) if s.strip()]
        words_per_sentence = [len(s.split()) for s in sentences if len(s.split()) > 3]

        median_len = sorted(words_per_sentence)[len(words_per_sentence) // 2]
        max_len = max(words_per_sentence)

        self.assertLessEqual(median_len, 22, f"Median sentence length {median_len} > 22")
        self.assertLessEqual(max_len, 35, f"Max sentence length {max_len} > 35")
        self.assertNotIn("—", clean_text, "Found forbidden em-dash in body prose")

    def test_empirical_source_citations(self):
        """Essay must cite and footnote primary empirical studies."""
        self.assertIn("arXiv:2610.11351", self.text)
        self.assertIn("arXiv:2606.21155", self.text)
        self.assertIn("arXiv:2607.18360", self.text)
        self.assertIn("arXiv:2611.03575", self.text)
        self.assertIn("arXiv:2610.12463", self.text)
        self.assertIn("arXiv:2512.14745", self.text)
        self.assertIn("arXiv:2611.04507", self.text)


if __name__ == "__main__":
    unittest.main()
