import re
import unittest
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent.parent
OTHERS = SITE_ROOT / "content" / "about" / "others.html"
RESEARCHERS = SITE_ROOT / "content" / "get-involved" / "researchers.html"


class TestAdoptAtiSeraTetherAgenttrustAttestmcpCredits(unittest.TestCase):
    def test_all_eight_adopted_works_credited_on_both_pages(self):
        expected_tokens = [
            "2611.23202",
            "Nguyen",
            "Husain",
            "Agent Trust Infrastructure",
            "2601.20789",
            "SERA",
            "Shen",
            "2611.25599",
            "Tether",
            "Sistla",
            "2606.21399",
            "Zhang",
            "2606.08919",
            "Turan",
            "2605.04785",
            "2606.08539",
            "AgentTrust",
            "Yang",
            "2601.17549",
            "AttestMCP",
            "Maloyan",
            "draft-hcf-bpm-agent-security-benchmark-profiles-00",
            "Han",
        ]
        for path in (OTHERS, RESEARCHERS):
            text = path.read_text(encoding="utf-8")
            for token in expected_tokens:
                self.assertIn(token, text, f"Missing {token} in {path.name}")

    def test_non_endorsement_and_anti_leakage_preserved(self):
        for path in (OTHERS, RESEARCHERS):
            text = path.read_text(encoding="utf-8")
            body_only = text.split("---\n", 2)[2]
            body_only = re.sub(r'<aside class="for-researchers">.*?</aside>', "", body_only, flags=re.DOTALL)
            body_only = re.sub(r'<section class="footnotes">.*?</section>', "", body_only, flags=re.DOTALL)
            self.assertNotIn("Base Thesis", body_only)
            self.assertNotIn("Markov Blanket", body_only)
            self.assertNotIn("Exocortex", body_only)
            for marker in (
                "2611.23202",
                "2601.20789",
                "2611.25599",
                "2606.21399",
                "2606.08919",
                "2605.04785",
                "2606.08539",
                "2601.17549",
            ):
                idx = text.find(marker)
                self.assertNotEqual(idx, -1)
                snippet = text[max(0, idx - 250) : idx + 300]
                self.assertNotIn("\u2014", snippet, f"Em-dash found near {marker} in {path.name}")
                self.assertNotIn("Base Thesis", snippet, f"Base Thesis label found near {marker} in {path.name}")


if __name__ == "__main__":
    unittest.main()
