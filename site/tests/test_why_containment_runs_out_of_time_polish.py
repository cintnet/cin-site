"""Unit tests verifying line editing, claim-first lede, single comparison rule, and voice compliance in why-containment-runs-out-of-time.html."""

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE_ROOT = HERE.parent
PAGE_HTML = SITE_ROOT / "content" / "blog" / "why-containment-runs-out-of-time.html"


class TestWhyContainmentRunsOutOfTimePolish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not PAGE_HTML.is_file():
            raise FileNotFoundError(f"Missing {PAGE_HTML}")
        cls.content = PAGE_HTML.read_text(encoding="utf-8")

    def test_file_exists_and_loads(self):
        self.assertGreater(len(self.content), 2000)
        self.assertIn("Why containment runs out of time", self.content)

    def test_claim_first_lede_and_takeaway(self):
        """Lede must state the claim in the first two sentences naming AI containment directly."""
        match = re.search(r"^lede:\s*(.+)$", self.content, re.MULTILINE)
        self.assertIsNotNone(match, "Missing frontmatter lede")
        lede = match.group(1).strip()
        self.assertTrue(
            lede.startswith("Strict isolation inside laboratory sandboxes buys vital time today, but it is not a permanent solution for powerful AI."),
            f"Lede does not open with direct claim: {lede[:100]}"
        )
        self.assertIn("AI", lede)
        self.assertIn("sandboxes", lede)
        self.assertNotIn("bell jar", lede.lower(), "Lede must not open with decorative bell-jar metaphor")

    def test_single_comparison_rule_and_headings(self):
        """Headings must be sentence-case and free of competing carried metaphors."""
        self.assertIn("<h2>Why perimeter walls eventually fail</h2>", self.content)
        self.assertIn("<h2>Using bought time to build layered civic gates</h2>", self.content)
        self.assertIn("<h2>What happens when a model slips past the first wall</h2>", self.content)
        self.assertNotIn("<h2>Why the glass jar and the pressure cooker eventually fail</h2>", self.content)
        self.assertNotIn("<h2>Using the time the box buys to build canal locks</h2>", self.content)

    def test_valet_keys_anchor_text_repaired(self):
        """Anchor text linking to power-on-loan-not-owned must be grammatically correct."""
        self.assertIn(
            'No agent should hold <a href="/blog/power-on-loan-not-owned/">permanent master keys</a> to public databases',
            self.content
        )
        self.assertNotIn('AI agents should hold permissions that expire</a> to public databases', self.content)

    def test_explainer_diagram_presence_and_xml_validity(self):
        """Explainer must contain accessible desktop and mobile SVGs with valid XML."""
        match = re.search(r'<figure class="explainer" id="ex-containment-horizon">.*?</figure>', self.content, re.DOTALL)
        self.assertIsNotNone(match, "Missing #ex-containment-horizon figure")
        fig = match.group(0)

        self.assertIn('class="diagram-desktop"', fig)
        self.assertIn('class="diagram-mobile"', fig)
        self.assertIn('viewBox="0 0 700 350"', fig)
        self.assertIn('viewBox="0 0 330 690"', fig)

        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', fig, re.DOTALL)
        self.assertEqual(len(svgs), 2)
        for svg_str in svgs:
            root = ET.fromstring(svg_str)
            self.assertEqual(root.tag, "svg")

    def test_sentence_length_and_voice_rules(self):
        """Prose sentences must obey median <= 22 words, zero > 35 words, and humanizer rules."""
        # Strip frontmatter
        body = re.sub(r"^---.*?---\s*", "", self.content, flags=re.DOTALL)
        # Strip styles, scripts, figures, SVGs, researcher asides, footnotes
        clean = re.sub(r"<(style|script|figure|svg|aside|section)[^>]*>.*?</\1>", "", body, flags=re.DOTALL)
        # Strip remaining HTML tags
        clean_text = re.sub(r"<[^>]+>", " ", clean)

        # Sentences
        raw_sentences = [s.strip() for s in re.split(r"[.!?]+", clean_text) if s.strip()]
        words_per_sentence = [len(s.split()) for s in raw_sentences if len(s.split()) > 3]

        self.assertGreater(len(words_per_sentence), 30)
        median_len = sorted(words_per_sentence)[len(words_per_sentence) // 2]
        max_len = max(words_per_sentence)

        self.assertLessEqual(median_len, 22, f"Median sentence length {median_len} exceeds 22 words")
        self.assertLessEqual(max_len, 35, f"Max sentence length {max_len} exceeds 35 words")

        # Zero em-dashes in prose
        self.assertNotIn("—", clean_text, "Found em-dash in body prose")

        # Humanizer forbidden vocabulary
        forbidden = [
            "delve", "tapestry", "testament", "underscore", "showcase",
            "foster", "pivotal", "intricate", "realm", "vibrant",
            "seamless", "crucial", "landscape"
        ]
        lower_body = clean_text.lower()
        for word in forbidden:
            self.assertFalse(
                re.search(rf"\b{word}\b", lower_body),
                f"Forbidden humanizer word found in prose: {word}"
            )

    def test_citations_grounding(self):
        """All primary source citations must be properly formatted in footnotes and aside."""
        self.assertIn("arXiv:2312.06942", self.content)
        self.assertIn("arXiv:2503.18813", self.content)
        self.assertIn("RFC 9449", self.content)
        self.assertIn("arXiv:2501.17315", self.content)
        self.assertIn('id="fn1"', self.content)
        self.assertIn('id="fn5"', self.content)


if __name__ == "__main__":
    unittest.main()
