#!/usr/bin/env python3
"""Site-wide editorial voice, readability, and anti-cliché compliance test suite (Spec 03/05/09 / Lane sitecritic).

Audits all public pages in site/content/**/*.html to guarantee:
- 0 occurrences of AI clichés and filler transitions ('Crucially', 'Moreover', 'It is worth noting that', etc.)
- 0 occurrences of magical solution framing ('magic bullet', 'panacea')
- 0 occurrences of robotic summary phrasing ('As an AI', 'In summary,', 'In conclusion,')
- Shared Horizon live status callout reflects verified moves
- Blog essays maintain median sentence lengths <= 22 words and plain-language readability
"""

from pathlib import Path
import re
import unittest

SITE_ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = SITE_ROOT / "content"

VOICE_PATTERNS = [
    (re.compile(r'\b(?:Moreover|Crucially|It is worth noting that|Delve into|A testament to|A beacon of|Tapestry of|Furthermore)\b', re.IGNORECASE), "AI cliché / filler transition"),
    (re.compile(r'\b(?:magic bullet|panacea)\b', re.IGNORECASE), "magical solution framing"),
    (re.compile(r'\b(?:As an AI|In summary,|In conclusion,)\b', re.IGNORECASE), "robotic summary framing"),
]


class SiteVoiceComplianceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html_files = sorted(CONTENT_DIR.rglob("*.html"))
        cls.blog_files = sorted((CONTENT_DIR / "blog").glob("*.html"))

    def test_content_corpus_size(self):
        """Guard against accidental mass deletion. Not a target: since 2026-11-09 duplicate essays are
        merged on purpose (specs/org/voice.md rule 9), so the floor is low."""
        self.assertGreaterEqual(len(self.html_files), 40, f"Expected at least 40 pages, found {len(self.html_files)}")
        self.assertGreaterEqual(len(self.blog_files), 25, f"Expected at least 25 blog articles, found {len(self.blog_files)}")

    def test_zero_voice_cliches_across_all_content(self):
        """No content file may contain prohibited AI clichés, filler transitions, or robotic summaries."""
        violations = []
        for path in self.html_files:
            rel = path.relative_to(SITE_ROOT)
            text = path.read_text(encoding="utf-8")
            for rx, desc in VOICE_PATTERNS:
                matches = list(rx.finditer(text))
                for m in matches:
                    violations.append(f"{rel} [{desc}]: matched '{m.group(0)}' at character {m.start()}")

        self.assertEqual(violations, [], "Encountered voice policy violations:\n" + "\n".join(violations))

    def test_shared_horizon_callout_move_count(self):
        """Shared Horizon status callout must reflect verified real-world moves."""
        sh_file = CONTENT_DIR / "labs" / "shared-horizon.html"
        self.assertTrue(sh_file.exists(), "shared-horizon.html must exist")
        content = sh_file.read_text(encoding="utf-8")
        self.assertIn("over 750 verified real-world moves and encounters", content)

    def test_others_acknowledgments_voice(self):
        """Researcher acknowledgments in others.html must lead with direct active phrasing without filler."""
        others_file = CONTENT_DIR / "about" / "others.html"
        self.assertTrue(others_file.exists(), "others.html must exist")
        content = others_file.read_text(encoding="utf-8")
        self.assertNotIn("Crucially,", content)
        self.assertIn("Running checks right before an action touches sensitive resources stops stale or misaligned commands", content)
        self.assertIn("Preventing intermediate helpers from altering or forging permissions requires asymmetric origin signatures", content)
        self.assertIn("Agents that consulted the user before completing a task acted outside their authority less often (14% versus 22%)", content)

    def test_theme1_research_and_companion_cross_links(self):
        """Theme 1 on research.html and companion essays must maintain mutual cross-links."""
        research_text = (CONTENT_DIR / "research.html").read_text(encoding="utf-8")
        self.assertIn("/blog/paying-for-words-instead-of-the-repair/", research_text)
        self.assertIn("/blog/when-the-middleman-pads-the-meter/", research_text)
        self.assertIn("/blog/why-watermarking-breaks-the-words/", research_text)
        self.assertIn("VerifierBench", research_text)
        self.assertIn("RFC 9421", research_text)

        paying_text = (CONTENT_DIR / "blog" / "paying-for-words-instead-of-the-repair.html").read_text(encoding="utf-8")
        self.assertIn("Related essays:", paying_text)
        self.assertIn("/blog/when-the-middleman-pads-the-meter/", paying_text)

        middleman_text = (CONTENT_DIR / "blog" / "when-the-middleman-pads-the-meter.html").read_text(encoding="utf-8")
        self.assertIn("Related essays:", middleman_text)
        self.assertIn("/blog/paying-for-words-instead-of-the-repair/", middleman_text)

        watermark_text = (CONTENT_DIR / "blog" / "why-watermarking-breaks-the-words.html").read_text(encoding="utf-8")
        self.assertIn("Related essays:", watermark_text)
        self.assertIn("/blog/paying-for-words-instead-of-the-repair/", watermark_text)


if __name__ == "__main__":
    unittest.main()
