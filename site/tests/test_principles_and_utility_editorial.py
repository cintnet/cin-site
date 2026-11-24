#!/usr/bin/env python3
"""Unit tests verifying the editorial polish of /about/principles/ and utility routes.

Ensures:
- /about/principles/ opens with a plain claim in the first two sentences (no >50w scene opener)
- /about/principles/ grounds the 19 channel seals across all 4 CIN functional-deliverable pillars
- Sentence lengths stay within <= 22w median and <= 35w max, with 0 humanizer tells
- /privacy/, /cookies/, and /contact/ have live cross-links and no stale pre-launch Shared Horizon copy
"""

from pathlib import Path
import re
import statistics
import unittest

SITE_ROOT = Path(__file__).resolve().parents[1]
PRINCIPLES_PATH = SITE_ROOT / "content" / "about" / "principles.html"
PRIVACY_PATH = SITE_ROOT / "content" / "privacy.html"
COOKIES_PATH = SITE_ROOT / "content" / "cookies.html"
CONTACT_PATH = SITE_ROOT / "content" / "contact.html"


class PrinciplesAndUtilityEditorialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.principles_raw = PRINCIPLES_PATH.read_text(encoding="utf-8")
        cls.privacy_raw = PRIVACY_PATH.read_text(encoding="utf-8")
        cls.cookies_raw = COOKIES_PATH.read_text(encoding="utf-8")
        cls.contact_raw = CONTACT_PATH.read_text(encoding="utf-8")

    def test_principles_claim_first_opener_and_five_primitives(self):
        """Opening paragraph of /about/principles/ must state the claim directly under 50 words."""
        m = re.search(r'<p class="big">(.*?)</p>', self.principles_raw, flags=re.S)
        self.assertIsNotNone(m, "Missing <p class=\"big\"> opener in about/principles.html")
        opener = re.sub(r"<[^>]+>", " ", m.group(1)).strip()
        opener_words = opener.split()
        self.assertLessEqual(
            len(opener_words),
            45,
            f"Opener exceeds claim-first word bound ({len(opener_words)}w): {opener}",
        )
        self.assertNotIn("farming valley", self.principles_raw.lower())
        self.assertNotIn("apartment building", opener.lower())

        # Five-primitive functional deliverable coverage in body prose
        lower_raw = self.principles_raw.lower()
        for phrase in (
            "1:1 personal agent",
            "undivided loyalty",
            "wearable and home sensors",
            "sealed local memory vault",
            "noisy wearable readings cannot verify physical truth alone",
            "honest uncertainty",
            "human judgment stays in charge",
            "private ledger",
            "public ledger",
            "separate network for agents",
            "expiring capability lease",
            "physical dead-man relay",
            "wide network ledger",
            "shared horizon",
            "capacity-backed mutual-credit",
            "cooperative share",
        ):
            self.assertIn(phrase, lower_raw, f"Missing functional-deliverable phrase: {phrase}")

    def test_principles_sentence_length_and_humanizer_bounds(self):
        """Body prose must obey <= 22 words median and <= 35 words max sentence length."""
        clean = re.sub(r"^---.*?---", "", self.principles_raw, flags=re.S)
        clean = re.sub(r"<aside.*?</aside>", " ", clean, flags=re.S)
        clean = re.sub(r"<section class=\"footnotes\">.*?</section>", " ", clean, flags=re.S)
        clean = re.sub(r"<(style|script|svg)\b[^>]*>.*?</\1>", " ", clean, flags=re.I | re.S)
        blocks = re.findall(r"<(p|li|figcaption)\b[^>]*>(.*?)</\1>", clean, flags=re.I | re.S)

        sentences = []
        for _, blk in blocks:
            txt = re.sub(r"<[^>]+>", " ", blk)
            for s in re.split(r"[.?!]\s+", txt):
                s_clean = re.sub(r"\s+", " ", s).strip()
                if len(s_clean.split()) >= 2:
                    sentences.append(s_clean)

        self.assertGreaterEqual(len(sentences), 30)
        lengths = [len(s.split()) for s in sentences]
        self.assertLessEqual(statistics.median(lengths), 22.0)
        for s in sentences:
            self.assertLessEqual(
                len(s.split()),
                35,
                f"Sentence exceeds 35-word ceiling ({len(s.split())}w): {s}",
            )

        self.assertNotIn("—", self.principles_raw)

    def test_utility_routes_healed_and_shared_horizon_live(self):
        """/privacy/, /cookies/, and /contact/ must cross-link and avoid stale pre-launch copy."""
        self.assertNotIn("When we launch Shared Horizon", self.privacy_raw)
        self.assertIn('href="/labs/shared-horizon/"', self.privacy_raw)
        self.assertIn('href="/cookies/"', self.privacy_raw)
        self.assertIn('href="/terms/"', self.privacy_raw)
        self.assertIn('href="/contact/"', self.privacy_raw)

        self.assertIn('href="/privacy/"', self.cookies_raw)
        self.assertIn('href="/terms/"', self.cookies_raw)

        self.assertIn('href="/about/"', self.contact_raw)
        self.assertIn('href="/get-involved/"', self.contact_raw)
        self.assertIn('href="/corrections/"', self.contact_raw)


if __name__ == "__main__":
    unittest.main()
