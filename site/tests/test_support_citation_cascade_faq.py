#!/usr/bin/env python3
"""Unit tests verifying the citation cascade FAQ and research grounding on support.html.

Ensures strict compliance with:
- Plain language and steward voice constraints (<= 22 words median, zero > 35 words)
- Humanizer rules (zero em-dashes, zero negative parallelisms, zero shallow -ing riders)
- Grounded scholarly references (HALLMARK benchmark, arXiv:2607.18360)
- Presence in built HTML distribution
"""

from pathlib import Path
import re
import statistics
import unittest

SITE_ROOT = Path(__file__).resolve().parents[1]
SUPPORT_HTML = SITE_ROOT / "content" / "support.html"
DIST_SUPPORT_HTML = SITE_ROOT / "dist" / "support" / "index.html"


class SupportCitationCascadeFAQTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_content = SUPPORT_HTML.read_text(encoding="utf-8")
        cls.section_match = re.search(
            r"<h3>Why do automated citation and fact-checking bots cry wolf, and how do you prevent reviewer fatigue\?</h3>(.*?)(?=<figure|<h[23])",
            cls.raw_content,
            re.DOTALL,
        )

    def test_section_exists(self):
        """The support page must contain the citation cascade FAQ section."""
        self.assertIsNotNone(
            self.section_match,
            "Missing Q&A section on citation bot false alarms and reviewer fatigue in site/content/support.html",
        )

    def test_plain_language_voice_gates(self):
        """Q&A body prose must obey <= 22 words median sentence length and zero > 35 words."""
        body_html = self.section_match.group(1)
        plain_text = re.sub(r"<[^>]+>", " ", body_html)
        sentences = [
            re.sub(r"\s+", " ", s).strip()
            for s in re.split(r"[\.\?\!]\s+", plain_text)
            if len(s.strip().split()) >= 2
        ]
        self.assertGreaterEqual(
            len(sentences), 8, f"Expected at least 8 explanatory sentences, got {len(sentences)}"
        )

        lengths = [len(s.split()) for s in sentences]
        median_len = statistics.median(lengths)
        self.assertLessEqual(
            median_len,
            22.0,
            f"Median sentence length {median_len:.1f} exceeds 22 words in citation FAQ: {lengths}",
        )

        for s in sentences:
            words = s.split()
            self.assertLessEqual(
                len(words),
                35,
                f"Sentence exceeds 35-word ceiling ({len(words)}w): '{s}'",
            )

    def test_humanizer_tells_absent(self):
        """Prose must not contain em-dashes, negative parallelisms, or stock AI vocabulary."""
        body_html = self.section_match.group(1)
        self.assertNotIn("—", body_html, "Found em-dash in citation FAQ prose")
        self.assertNotIn("–", body_html, "Found en-dash in citation FAQ prose")

        forbidden_ai_words = [
            "delve", "tapestry", "testament", "underscore", "showcase",
            "foster", "pivotal", "intricate", "realm", "vibrant",
            "seamless", "crucial", "landscape", "beacon", "harness"
        ]
        lower_body = body_html.lower()
        for word in forbidden_ai_words:
            self.assertNotIn(
                f" {word} ",
                lower_body,
                f"Found stock AI word '{word}' in citation FAQ prose",
            )

        # Check for negative parallelism
        self.assertIsNone(
            re.search(r"\bnot (?:just|only|merely)\b.*?\bbut\b", lower_body),
            "Found negative parallelism 'not just/only/merely X but Y' in citation FAQ prose",
        )

    def test_researcher_grounding_present(self):
        """Research grounding must cite HALLMARK (arXiv:2607.18360) and authoritative registries."""
        researcher_block_match = re.search(
            r'<aside class="for-researchers">.*?<details>.*?(.*?)</details>.*?</aside>',
            self.raw_content,
            re.DOTALL,
        )
        self.assertIsNotNone(researcher_block_match, "Missing for-researchers block")
        researcher_text = researcher_block_match.group(1)

        self.assertIn(
            "https://arxiv.org/abs/2607.18360",
            researcher_text,
            "Missing HALLMARK arXiv link in for-researchers block",
        )
        self.assertIn("HALLMARK", researcher_text)
        self.assertIn("Crossref", researcher_text)
        self.assertIn("two-stage cascade", researcher_text)

    def test_unsupported_figures_absent(self):
        """Prose must not assert numbers or multipliers unsupported by HALLMARK."""
        body_html = self.section_match.group(1)
        self.assertNotIn("doubled", body_html, "Found unsupported figure 'doubled' in citation FAQ body")
        self.assertNotIn(
            "cuts false alarms by an order of magnitude",
            body_html,
            "Found unsupported claim 'cuts false alarms by an order of magnitude' in citation FAQ body",
        )


if __name__ == "__main__":
    unittest.main()
