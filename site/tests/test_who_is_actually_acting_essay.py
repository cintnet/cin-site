#!/usr/bin/env python3
"""Deterministic verification suite for 'Who is actually acting?' essay and interactive action receipt explainer.

Verifies:
1. Essay metadata, citations, and frontmatter integrity.
2. Responsive dual-SVG explainer (#ex-action-receipt) with role="img", <title>, and <desc>.
3. Phone-width mobile SVG boundary containment (zero overflow beyond 310px width in 330px viewBox).
4. Interactive revoke toggle wiring across desktop and mobile viewports in site.js.
5. Plain language voice rules: median sentence <= 22 words, zero > 35 words, zero em-dashes.
"""

from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

SITE_ROOT = Path(__file__).resolve().parents[1]
CONTENT_PATH = SITE_ROOT / "content" / "blog" / "who-is-actually-acting.html"
JS_PATH = SITE_ROOT / "assets" / "js" / "site.js"


class WhoIsActuallyActingEssayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assertTrue(CONTENT_PATH.exists(), f"Missing content file: {CONTENT_PATH}")
        cls.assertTrue(JS_PATH.exists(), f"Missing site.js file: {JS_PATH}")
        cls.html_text = CONTENT_PATH.read_text(encoding="utf-8")
        cls.js_text = JS_PATH.read_text(encoding="utf-8")

    def test_frontmatter_and_metadata(self):
        """Frontmatter must have required keys and sensible values."""
        self.assertTrue(self.html_text.startswith("---"))
        fm_match = re.match(r"^---\n(.*?)\n---", self.html_text, re.DOTALL)
        self.assertIsNotNone(fm_match, "Valid YAML frontmatter required")
        fm = fm_match.group(1)

        self.assertIn("title: Who is actually acting?", fm)
        self.assertIn("template: article", fm)
        self.assertIn("category: Seeing", fm)
        self.assertIn("image: post-who-is-acting.jpg", fm)
        self.assertIn("takeaway:", fm)

    def test_citations_valid(self):
        """Footnotes must reference METR, WIMSE/OAuth RFC, and HTTP Message Signatures."""
        self.assertIn('id="fn1"', self.html_text)
        self.assertIn('id="fn2"', self.html_text)
        self.assertIn('id="fn3"', self.html_text)
        self.assertIn("RFC 8693", self.html_text)
        self.assertIn("RFC 9421", self.html_text)
        self.assertIn("WIMSE", self.html_text)

    def test_explainer_presence_and_structure(self):
        """Figure #ex-action-receipt must contain both desktop and mobile SVGs with responsive CSS."""
        fig_match = re.search(r'<figure\b[^>]*\bid=["\']ex-action-receipt["\'][^>]*>(.*?)</figure>', self.html_text, re.DOTALL)
        self.assertIsNotNone(fig_match, "Figure #ex-action-receipt must be present")
        fig_content = fig_match.group(1)

        self.assertIn(".diagram-desktop {", fig_content)
        self.assertIn(".diagram-mobile {", fig_content)
        self.assertIn("@media (max-width: 640px)", fig_content)

        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', fig_content, re.DOTALL)
        self.assertEqual(len(svgs), 2, "Expected exactly two SVGs (desktop and mobile) inside #ex-action-receipt")

    def test_svg_xml_and_accessibility(self):
        """Both desktop and mobile SVGs must be valid XML with role='img', title, and desc."""
        fig_match = re.search(r'<figure\b[^>]*\bid=["\']ex-action-receipt["\'][^>]*>(.*?)</figure>', self.html_text, re.DOTALL)
        fig_content = fig_match.group(1)
        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', fig_content, re.DOTALL)

        for i, svg_str in enumerate(svgs):
            label = "desktop" if i == 0 else "mobile"
            root = ET.fromstring(svg_str)
            self.assertEqual(root.tag, "svg")
            self.assertEqual(root.attrib.get("role"), "img", f"{label} SVG must have role='img'")
            title = root.find("title")
            desc = root.find("desc")
            self.assertIsNotNone(title, f"{label} SVG missing <title>")
            self.assertIsNotNone(desc, f"{label} SVG missing <desc>")
            self.assertTrue(len((title.text or "").strip()) > 10, f"{label} SVG title too short")
            self.assertTrue(len((desc.text or "").strip()) > 20, f"{label} SVG desc too short")

    def test_mobile_svg_dimensions_and_containment(self):
        """Mobile SVG viewBox must be 330px wide and text must not overflow 310px inner bounds."""
        fig_match = re.search(r'<figure\b[^>]*\bid=["\']ex-action-receipt["\'][^>]*>(.*?)</figure>', self.html_text, re.DOTALL)
        fig_content = fig_match.group(1)
        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', fig_content, re.DOTALL)
        mobile_svg = svgs[1]

        root = ET.fromstring(mobile_svg)
        vb = root.attrib.get("viewBox", "")
        self.assertTrue(vb.startswith("0 0 330 "), f"Mobile SVG viewBox should start with '0 0 330 ', got '{vb}'")

        overflows = []
        for text_el in root.iter("text"):
            content = (text_el.text or "").strip()
            if not content:
                continue
            x = float(text_el.attrib.get("x", "0"))
            fs = float(text_el.attrib.get("font-size", "11"))
            anchor = text_el.attrib.get("text-anchor", "start")
            est_width = len(content) * (fs * 0.58)
            right_edge = x + (est_width / 2) if anchor == "middle" else (x if anchor == "end" else x + est_width)
            if right_edge > 310.0:
                overflows.append(f"'{content}' (len {len(content)}, right_edge={right_edge:.1f} > 310)")

        self.assertEqual(overflows, [], "Mobile SVG text elements overflow card boundaries:\n" + "\n".join(overflows))

    def test_interactive_revoke_controls(self):
        """Both desktop and mobile revoke buttons must carry proper accessibility and controls."""
        fig_match = re.search(r'<figure\b[^>]*\bid=["\']ex-action-receipt["\'][^>]*>(.*?)</figure>', self.html_text, re.DOTALL)
        fig_content = fig_match.group(1)

        self.assertIn('id="ex-revoke-btn"', fig_content)
        self.assertIn('id="ex-revoke-btn-m"', fig_content)
        self.assertIn('id="ex-receipt-status"', fig_content)
        self.assertIn('id="ex-receipt-status-m"', fig_content)
        self.assertIn('role="button"', fig_content)
        self.assertIn('tabindex="0"', fig_content)

    def test_site_js_wiring(self):
        """site.js must bind to both desktop and mobile revoke buttons and status elements."""
        self.assertIn("#ex-revoke-btn", self.js_text)
        self.assertIn("#ex-revoke-btn-m", self.js_text)
        self.assertIn("#ex-receipt-status", self.js_text)
        self.assertIn("#ex-receipt-status-m", self.js_text)
        self.assertIn("Status: Lease revoked", self.js_text)
        self.assertIn("Status: Active lease", self.js_text)

    def test_voice_and_sentence_constraints(self):
        """Body prose must follow voice rules: median <= 22 words, max <= 35 words, zero em-dashes."""
        body = re.sub(r"^---.*?---\s*", "", self.html_text, flags=re.DOTALL)
        clean = re.sub(r"<(style|script|figure|svg|aside|section)[^>]*>.*?</\1>", "", body, flags=re.DOTALL)
        clean_text = re.sub(r"<[^>]+>", " ", clean)

        sentences = [s.strip() for s in re.split(r"[.!?]+", clean_text) if s.strip()]
        words_per_sentence = [len(s.split()) for s in sentences if len(s.split()) > 3]

        median_len = sorted(words_per_sentence)[len(words_per_sentence) // 2]
        max_len = max(words_per_sentence)

        self.assertLessEqual(median_len, 22, f"Median sentence length {median_len} > 22")
        self.assertLessEqual(max_len, 35, f"Max sentence length {max_len} > 35")
        self.assertNotIn("—", clean_text, "Found forbidden em-dash in body prose")


if __name__ == "__main__":
    unittest.main()
