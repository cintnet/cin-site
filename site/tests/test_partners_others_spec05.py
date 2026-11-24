"""Spec 05 and Base Thesis standards-credit tests for /about/others/."""

from pathlib import Path
import re
import unittest

SITE_ROOT = Path(__file__).resolve().parents[1]
OTHERS_HTML = SITE_ROOT / "content" / "about" / "others.html"


class PartnersOthersSpec05Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = OTHERS_HTML.read_text(encoding="utf-8")

    def test_connected_rooms_svg_has_dark_mode_and_mobile_parity(self) -> None:
        self.assertIn(':root[data-theme="dark"] #ex-connected-rooms', self.text)
        self.assertIn("#8FD4B6", self.text)
        self.assertIn("#F09D82", self.text)
        self.assertIn('class="diagram-desktop"', self.text)
        self.assertIn('class="diagram-mobile"', self.text)
        self.assertIn("@media (max-width: 600px)", self.text)

        mobile_match = re.search(
            r'<svg class="diagram-mobile"[^>]*viewBox="0 0 (\d+) \d+"[^>]*>(.*?)</svg>',
            self.text,
            re.DOTALL,
        )
        self.assertIsNotNone(mobile_match)
        assert mobile_match is not None
        self.assertLessEqual(int(mobile_match.group(1)), 310)

        for svg_block in re.findall(r"<svg\b.*?</svg>", self.text, re.DOTALL):
            for size in re.findall(r'font-size="([0-9.]+)"', svg_block):
                self.assertGreaterEqual(float(size), 11.0)

    def test_five_primitive_standards_and_research_credits_and_anti_leakage(self) -> None:
        for required in (
            "IEC 61508",
            "Leveson",
            "Kevin Fu and Wenyuan Xu",
            "RATS",
            "SPDM",
            "DICE",
            "SCITT",
            "C2PA",
            "ISO/IEC TS 27560:2023",
            "Lamport",
            "Balkin",
            "Joscha Bach",
        ):
            self.assertIn(required, self.text)

        for forbidden in ("Base Thesis", "Markov Blanket", "Exocortex"):
            self.assertNotIn(forbidden, self.text)


if __name__ == "__main__":
    unittest.main()
