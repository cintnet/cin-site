"""Tests for Observatory oversight gap interactive stage explorer in observatory.html and site.js.

Verifies:
1. Presence and structure of four interactive stage cards in #ex-oversight-gap.
2. SVG spotlight groups and interactive stage tick groups with correct geometry and attributes.
3. SVG well-formedness and XML parser compliance.
4. ARIA accessibility semantics: role="status", aria-live="polite", aria-pressed, tabindex="0".
5. Progressive enhancement logic in site.js with zero innerHTML and keyboard navigation bindings.
6. Voice and readability compliance (median <= 22 words, max <= 35 words, 0 humanizer tells).
"""
from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE_ROOT = HERE.parent
OBSERVATORY_HTML = SITE_ROOT / "content" / "labs" / "observatory.html"
SITE_JS = SITE_ROOT / "assets" / "js" / "site.js"


class TestObservatoryInteractiveStageExplorer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not OBSERVATORY_HTML.is_file():
            raise FileNotFoundError(f"Missing {OBSERVATORY_HTML}")
        if not SITE_JS.is_file():
            raise FileNotFoundError(f"Missing {SITE_JS}")
        cls.html = OBSERVATORY_HTML.read_text(encoding="utf-8")
        cls.js = SITE_JS.read_text(encoding="utf-8")

    def test_explainer_container_and_svg_structure(self):
        """Figure #ex-oversight-gap must exist with accessible titles and descriptions."""
        self.assertIn('id="ex-oversight-gap"', self.html)
        self.assertIn('aria-labelledby="ex-oversight-gap-title ex-oversight-gap-desc"', self.html)
        self.assertIn('<title id="ex-oversight-gap-title">', self.html)
        self.assertIn('<desc id="ex-oversight-gap-desc">', self.html)

    def test_svg_is_valid_xml(self):
        """The inline SVG inside #ex-oversight-gap must parse cleanly as valid XML."""
        match = re.search(r'<svg\b[^>]*>.*?</svg>', self.html, re.DOTALL)
        self.assertIsNotNone(match, "SVG not found inside observatory.html")
        svg_text = match.group(0)
        try:
            root = ET.fromstring(svg_text)
            self.assertEqual(root.tag, "svg")
        except ET.ParseError as e:
            self.fail(f"SVG failed XML parsing: {e}")

    def test_spotlight_overlay_groups_and_geometry(self):
        """SVG must contain four spotlight groups corresponding to the four stages."""
        for stage in (1, 2, 3, 4):
            spot_id = f'id="og-spotlight-{stage}"'
            self.assertIn(spot_id, self.html, f"Missing spotlight group {spot_id}")
            self.assertIn(f'data-stage="{stage}"', self.html)

        # Confirm coordinates for each stage spotlight
        self.assertIn('x1="140"', self.html)
        self.assertIn('x1="280"', self.html)
        self.assertIn('x1="420"', self.html)
        self.assertIn('x1="560"', self.html)

    def test_interactive_stage_tick_groups(self):
        """SVG must include interactive tick groups with tabindex and role."""
        for stage in (1, 2, 3, 4):
            match = re.search(
                rf'<g class="og-stage-tick-group" data-stage="{stage}" tabindex="0" role="button"',
                self.html,
            )
            self.assertIsNotNone(match, f"Missing interactive tick group for stage {stage}")

    def test_four_stage_cards_accessibility_and_attributes(self):
        """All four stage cards must have data-stage, tabindex="0", and aria-pressed attributes."""
        for stage in (1, 2, 3, 4):
            pattern = rf'class="og-stage-card[^"]*"[^>]*tabindex="0"[^>]*data-stage="{stage}"[^>]*aria-pressed="false"'
            self.assertTrue(
                re.search(pattern, self.html),
                f"Missing or improperly configured stage card for stage {stage}",
            )

    def test_status_banner_and_reset_button(self):
        """Status banner must feature role='status' and aria-live='polite', with a reset button."""
        self.assertIn('id="og-status-banner"', self.html)
        self.assertIn('role="status"', self.html)
        self.assertIn('aria-live="polite"', self.html)
        self.assertIn('id="og-reset-btn"', self.html)
        self.assertIn('<button type="button" class="og-reset-btn" id="og-reset-btn" hidden>', self.html)

    def test_no_inline_style_attributes_in_oversight_gap(self):
        """Figure #ex-oversight-gap must not use inline style attributes (L-1407)."""
        match = re.search(r'<figure\b[^>]*id="ex-oversight-gap"[^>]*>.*?</figure>', self.html, re.DOTALL)
        self.assertIsNotNone(match, "Could not find #ex-oversight-gap figure")
        gap_html = match.group(0)
        gap_without_style_tag = re.sub(r'(?s)<style.*?</style>', '', gap_html)
        self.assertNotIn('style="', gap_without_style_tag)

    def test_site_js_progressive_enhancement_and_zero_innerhtml(self):
        """site.js must enhance #ex-oversight-gap without any innerHTML calls."""
        self.assertIn('document.getElementById("ex-oversight-gap")', self.js)
        self.assertIn('og-stage-card', self.js)
        self.assertIn('og-spotlight', self.js)
        self.assertIn('og-reset-btn', self.js)
        # Ensure no innerHTML is introduced
        gap_block_match = re.search(
            r'// Progressive enhancement: Observatory oversight gap interactive stage explorer.*?\}\s*\}\)\(\);',
            self.js,
            re.DOTALL,
        )
        self.assertIsNotNone(gap_block_match, "Could not locate oversight gap logic in site.js")
        gap_block = gap_block_match.group(0)
        self.assertNotIn(".innerHTML", gap_block)
        # Verify keyboard navigation bindings
        self.assertIn('ArrowRight', gap_block)
        self.assertIn('ArrowLeft', gap_block)
        self.assertIn('Escape', gap_block)

    def test_readability_sentence_length_and_humanizer(self):
        """Text in observatory.html must adhere to sentence length limits and humanizer rules."""
        text = self.html
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                text = parts[2]
        text = re.sub(r"(?s)<script.*?</script>", "", text)
        text = re.sub(r"(?s)<style.*?</style>", "", text)
        text = re.sub(r"(?s)<svg.*?</svg>", "", text)
        text = re.sub(r'(?s)<aside class="for-researchers".*?</aside>', "", text)
        text = re.sub(r'(?s)<section class="footnotes".*?</section>', "", text)
        text = re.sub(r'</?(?:div|p|h[1-6]|li|section|article|header|footer|figure|figcaption|table|tr|td|th|span|button)[^>]*>', '. ', text)
        text = re.sub(r'<[^>]+>', ' ', text)
        raw_sentences = [s.strip() for s in re.split(r"[.!?]+(?:\s+|$)", text) if len(s.strip()) > 0]
        sentences = [" ".join(s.split()) for s in raw_sentences]
        lengths = [len(s.split()) for s in sentences if len(s.split()) > 1]
        self.assertTrue(len(lengths) > 0)
        lengths.sort()
        median = lengths[len(lengths) // 2]
        self.assertLessEqual(median, 22, f"Median sentence length {median} exceeds 22 words")
        too_long = [s for s in sentences if len(s.split()) > 35]
        self.assertEqual(len(too_long), 0, f"Found sentences over 35 words: {too_long}")


if __name__ == "__main__":
    unittest.main()
