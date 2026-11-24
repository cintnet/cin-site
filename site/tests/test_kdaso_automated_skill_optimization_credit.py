#!/usr/bin/env python3
"""Unit tests verifying research credit for KDASO on cintnet.org (D-1579).

Grounded in:
- Cheng et al. (arXiv:2611.06972, Nov 2026):
  KDASO: Knowledge-Data Dual-Driven Automated Skill Optimization for Liability Adjudication Tasks
"""
from __future__ import annotations

import re
import statistics
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OTHERS_HTML = ROOT / "content" / "about" / "others.html"


class TestKDASOAutomatedSkillOptimizationCredit(unittest.TestCase):
    def setUp(self):
        self.assertTrue(OTHERS_HTML.exists(), f"others.html must exist: {OTHERS_HTML}")
        self.html = OTHERS_HTML.read_text(encoding="utf-8")

    def test_citation_and_footnote_presence(self):
        self.assertIn("https://arxiv.org/abs/2611.06972", self.html)
        self.assertIn('id="fn112"', self.html)
        self.assertIn('href="#fn112"', self.html)
        self.assertIn("Zi-Jian Cheng", self.html)
        self.assertIn("Lan-Zhe Guo", self.html)
        self.assertIn("KDASO", self.html)

    def test_architectural_synthesis_mention(self):
        self.assertIn("KDASO; Cheng et al., 2026", self.html)

    def test_plain_language_voice_rules(self):
        # Extract the paragraph citing KDASO
        match = re.search(
            r"<p>(?:(?!</p>).)*?automated skill optimization(?:(?!</p>).)*?</p>",
            self.html,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "KDASO paragraph must be found in others.html")
        para_html = match.group(0)
        para_text = re.sub(r"<[^>]+>", "", para_html).strip()

        forbidden = [
            "mmct",
            "token sale",
            "investment return",
            "yield guarantee",
            "financial reward",
            "d-0",
            "f1-f19",
            "—",
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
        ]
        low = para_text.lower()
        for token in forbidden:
            self.assertNotIn(token, low, f"Forbidden token '{token}' in KDASO paragraph")

        sentences = [s.strip() for s in re.split(r"[.!?]+", para_text) if s.strip()]
        self.assertGreaterEqual(len(sentences), 2, "Paragraph must have multiple sentences")
        word_counts = [len(s.split()) for s in sentences]
        for wc, s in zip(word_counts, sentences):
            self.assertLessEqual(wc, 35, f"Sentence exceeds 35 words ({wc}): '{s}'")
        self.assertLessEqual(
            statistics.median(word_counts),
            22,
            f"Median sentence length > 22 ({statistics.median(word_counts)})",
        )


if __name__ == "__main__":
    unittest.main()
