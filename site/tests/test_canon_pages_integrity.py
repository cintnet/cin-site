"""Unit tests verifying the structural integrity, accessibility, and voice invariants

of the Canon triad pages: principles.html, governance.html, and corrections.html.
"""

import os
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = SITE_ROOT / "content"

FORBIDDEN_HUMANIZER_WORDS = [
    "delve", "tapestry", "testament", "underscore", "showcase",
    "foster", "pivotal", "intricate", "realm", "vibrant",
    "seamless", "crucial", "landscape"
]


def extract_clean_prose(html_content: str) -> str:
    """Strip frontmatter, SVG diagrams, styles, scripts, researcher asides, and footnotes."""
    body = re.sub(r"^---.*?---\s*", "", html_content, flags=re.DOTALL)
    clean = re.sub(r"<(style|script|figure|svg|aside)[^>]*>.*?</\1>", "", body, flags=re.DOTALL)
    clean = re.sub(r'<section\b[^>]*class=["\']footnotes["\'].*?</section>', "", clean, flags=re.DOTALL)
    clean_text = re.sub(r"<[^>]+>", " ", clean)
    clean_text = re.sub(r"\s+", " ", clean_text)
    return clean_text.strip()


def check_voice_invariants(test_case: unittest.TestCase, clean_text: str, page_name: str):
    """Enforce sentence length limits, zero em-dashes, and zero forbidden vocabulary."""
    raw_sentences = [s.strip() for s in re.split(r"[.!?]+", clean_text) if s.strip()]
    meaningful_sentences = [s for s in raw_sentences if len(s.split()) > 3]
    test_case.assertGreater(len(meaningful_sentences), 10, f"{page_name} must have substantial prose")

    lengths = [len(s.split()) for s in meaningful_sentences]
    median_len = sorted(lengths)[len(lengths) // 2]
    max_len = max(lengths)

    test_case.assertLessEqual(median_len, 22, f"{page_name} median sentence length {median_len} > 22")
    test_case.assertLessEqual(max_len, 35, f"{page_name} max sentence length {max_len} > 35")
    test_case.assertNotIn("—", clean_text, f"{page_name} body prose contains em-dash")

    lower = clean_text.lower()
    for word in FORBIDDEN_HUMANIZER_WORDS:
        test_case.assertFalse(
            re.search(rf"\b{word}\b", lower),
            f"{page_name} contains forbidden humanizer tell: '{word}'"
        )


class TestCanonPagesIntegrity(unittest.TestCase):
    def setUp(self):
        self.principles_path = CONTENT_DIR / "about" / "principles.html"
        self.governance_path = CONTENT_DIR / "about" / "governance.html"
        self.corrections_path = CONTENT_DIR / "corrections.html"

        self.assertTrue(self.principles_path.exists(), "principles.html missing")
        self.assertTrue(self.governance_path.exists(), "governance.html missing")
        self.assertTrue(self.corrections_path.exists(), "corrections.html missing")

        self.principles_content = self.principles_path.read_text(encoding="utf-8")
        self.governance_content = self.governance_path.read_text(encoding="utf-8")
        self.corrections_content = self.corrections_path.read_text(encoding="utf-8")

    def test_principles_nineteen_floor_commitments(self):
        """Ensure all 19 floor commitments are sequentially numbered and present."""
        expected_commitments = [
            "Your data is yours.",
            "Answers, not data.",
            "Sharing is never bought or punished.",
            "Fair process.",
            "Doubt falls on the system.",
            "No ranking of people.",
            "One person, one voice on values.",
            "Simulated people don't vote.",
            "People grant standing.",
            "You can always leave.",
            "Communities decide locally.",
            "No strings attached.",
            "No engagement tricks.",
            "Diversity is protected.",
            "A right to rest.",
            "Play is not waste.",
            "Your mind is your own.",
            "You don't have to be useful.",
            "No force."
        ]
        list_items = re.findall(r"<li><strong>(.*?)</strong>", self.principles_content)
        self.assertEqual(len(list_items), 19, "Must contain exactly nineteen numbered floor commitments")
        for i, expected in enumerate(expected_commitments):
            self.assertEqual(list_items[i], expected, f"Floor commitment {i+1} mismatch")

    def test_principles_architectural_svg_diagram(self):
        """Verify the #ex-principles-floor SVG diagram has role='img', valid XML, and five pillars."""
        match = re.search(r'<figure class="explainer" id="ex-principles-floor">.*?</figure>', self.principles_content, re.DOTALL)
        self.assertIsNotNone(match, "Missing #ex-principles-floor figure")
        fig = match.group(0)

        svg_match = re.search(r'<svg\b[^>]*>.*?</svg>', fig, re.DOTALL)
        self.assertIsNotNone(svg_match, "Missing SVG in #ex-principles-floor")
        svg_str = svg_match.group(0)

        self.assertTrue(bool(re.search(r'role=["\'](?:img|group)["\']', svg_str)))
        self.assertIn('viewBox="0 0 720 380"', svg_str)
        self.assertIn('<title id="ex-principles-floor-title">', svg_str)
        self.assertIn('<desc id="ex-principles-floor-desc">', svg_str)

        # XML validity
        root = ET.fromstring(svg_str)
        self.assertEqual(root.tag, "svg")

        # Five pillars
        self.assertIn("01 · BOUNDARY", svg_str)
        self.assertIn("02 · PROCESS", svg_str)
        self.assertIn("03 · VOICE", svg_str)
        self.assertIn("04 · REST", svg_str)
        self.assertIn("05 · PEACE", svg_str)

    def test_principles_emergent_self_rule_thesis_and_loop_stage(self):
        """Verify principles.html expresses single-user exploratory agent, shared ledger, channel seals, and #ex-emergent-loop."""
        self.assertIn("heading: One loyal agent per person. People write the rules.", self.principles_content)
        self.assertIn("exploratory", self.principles_content)
        self.assertIn("one human user", self.principles_content)
        self.assertIn("shared transparent ledger", self.principles_content)
        self.assertIn("channel-integrity", self.principles_content)
        self.assertIn("agent harness", self.principles_content)
        self.assertIn("never institute societal rules from above", self.principles_content)

        match = re.search(r'<figure class="explainer" id="ex-emergent-loop">.*?</figure>', self.principles_content, re.DOTALL)
        self.assertIsNotNone(match, "Missing #ex-emergent-loop figure in principles.html")
        fig = match.group(0)
        self.assertIsNone(re.search(r'\bstyle\s*=', fig, re.I), "Zero inline style= allowed inside #ex-emergent-loop")
        self.assertTrue('data-stage="matrix"' in fig or 'data-stage="switchboard"' in fig)

        svg_match = re.search(r'<svg\b[^>]*>.*?</svg>', fig, re.DOTALL)
        self.assertIsNotNone(svg_match, "Missing SVG in #ex-emergent-loop")
        svg_str = svg_match.group(0)
        self.assertTrue(bool(re.search(r'role=["\'](?:img|group)["\']', svg_str)))
        self.assertIn('<title id="ex-emergent-loop-title">', svg_str)
        self.assertIn('<desc id="ex-emergent-loop-desc">', svg_str)

        root = ET.fromstring(svg_str)
        self.assertEqual(root.tag, "svg")

        self.assertIn("01 · SINGLE-USER EXPLORATORY AGENT", svg_str)
        self.assertIn("02 · HIGH-FIDELITY LEDGER SIGNAL", svg_str)
        self.assertIn("03 · EMERGENT COLLECTIVE POLICIES", svg_str)

    def test_principles_voice_and_citations(self):
        """Check voice invariants and foundational literature citations."""
        prose = extract_clean_prose(self.principles_content)
        check_voice_invariants(self, prose, "principles.html")

        # Foundational sources
        self.assertIn("2212.08073", self.principles_content, "Constitutional AI citation missing")
        self.assertIn("2402.05070", self.principles_content, "Pluralistic Alignment citation missing")
        self.assertIn("10.1017/CBO9780511807763", self.principles_content, "Ostrom commons citation missing")
        self.assertIn("2406.07814", self.principles_content, "Collective Constitutional AI citation missing")

    def test_governance_stages_and_house_rules(self):
        """Verify governance stages and internal AI usage rules."""
        self.assertIn("STAGE 1 · FOUNDING STEWARD", self.governance_content)
        self.assertIn("STAGE 2 · FEDERATED STEWARDS", self.governance_content)
        self.assertIn("STAGE 3 · DEMOCRATIC STANDING", self.governance_content)

        self.assertIn("Agents propose; a person decides.", self.governance_content)
        self.assertIn("Automated checks catch what tired eyes miss.", self.governance_content)
        self.assertIn("Every agent run leaves a receipt.", self.governance_content)

        # Explainer SVG
        match = re.search(r'<figure class="explainer" id="ex-governance-stages">.*?</figure>', self.governance_content, re.DOTALL)
        self.assertIsNotNone(match, "Missing #ex-governance-stages figure")
        svg_str = re.search(r'<svg\b[^>]*>.*?</svg>', match.group(0), re.DOTALL).group(0)
        self.assertTrue(bool(re.search(r'role=["\'](?:img|group)["\']', svg_str)))
        root = ET.fromstring(svg_str)
        self.assertEqual(root.tag, "svg")

    def test_governance_active_lab_engagement_and_zero_veto(self):
        """Verify governance.html expresses active engagement with AI labs and safety institutes alongside zero veto."""
        self.assertIn(
            "<h2>How we engage AI labs, safety institutes, and other organisations</h2>",
            self.governance_content,
        )
        self.assertNotIn("<h2>Our relationship to other organisations</h2>", self.governance_content)
        self.assertIn("forty", self.governance_content)
        self.assertIn("fifty", self.governance_content)
        self.assertIn("/get-involved/labs/", self.governance_content)
        self.assertIn("/labs/institutions/", self.governance_content)
        self.assertIn("Zero editorial or research veto.", self.governance_content)
        self.assertIn("zero corporate equity", self.governance_content)

    def test_governance_voice_and_citations(self):
        """Check governance voice invariants and citations."""
        prose = extract_clean_prose(self.governance_content)
        check_voice_invariants(self, prose, "governance.html")

        self.assertIn("10.1109/PROC.1975.9939", self.governance_content, "Saltzer & Schroeder citation missing")
        self.assertIn("2406.16696", self.governance_content, "Public Constitutional AI citation missing")
        self.assertIn("2406.07814", self.governance_content, "Collective Constitutional AI citation missing")

    def test_corrections_lifecycle_and_calibration(self):
        """Verify corrections lifecycle, errata standards, and calibration benchmarks."""
        self.assertIn("Factual and numerical errors.", self.corrections_content)
        self.assertIn("Substantive claim revisions.", self.corrections_content)
        self.assertIn("Institutional and forecast updates.", self.corrections_content)

        # Explainer SVG
        match = re.search(r'<figure class="explainer" id="ex-corrections-lifecycle">.*?</figure>', self.corrections_content, re.DOTALL)
        self.assertIsNotNone(match, "Missing #ex-corrections-lifecycle figure")
        svg_str = re.search(r'<svg\b[^>]*>.*?</svg>', match.group(0), re.DOTALL).group(0)
        self.assertTrue(bool(re.search(r'role=["\'](?:img|group)["\']', svg_str)))
        root = ET.fromstring(svg_str)
        self.assertEqual(root.tag, "svg")

        # Epistemic calibration benchmarks
        self.assertIn("10.1175/1520-0493", self.corrections_content)
        self.assertIn("2409.19839", self.corrections_content, "ForecastBench citation missing")
        self.assertIn("2606.10777", self.corrections_content, "Hoarau second-order calibration missing")
        self.assertIn("2512.16030", self.corrections_content, "KalshiBench citation missing")

        prose = extract_clean_prose(self.corrections_content)
        check_voice_invariants(self, prose, "corrections.html")


if __name__ == "__main__":
    unittest.main()
