"""Tests for the November 2026 Epoch AI Observatory update."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

SITE_DIR = Path(__file__).resolve().parents[1]
OBSERVATORY_PATH = SITE_DIR / "content" / "labs" / "observatory.html"
sys.path.insert(0, str(SITE_DIR))
import build


class TrajectoryObservatoryEpochNov2026Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = OBSERVATORY_PATH.read_text(encoding="utf-8")

    def test_epoch_nov2026_primary_sources_and_metrics_present(self) -> None:
        for needle in (
            '"updated": "2026-11-27"',
            "https://epoch.ai/data-insights/agentic-inference-capacity-growth",
            "https://epoch.ai/publications/how-good-are-fable-5-2-and-gpt-6-2-astra-at-real-work",
            "https://epoch.ai/data/benchmark-reviews-documentation",
            "Inference Performance Index",
            "4.6x",
            "2.6x",
            "Fable 5.2",
            "GPT-6.2 Astra",
            'id="fn61"',
            'id="fn62"',
        ):
            self.assertIn(needle, self.text)

    def test_observatory_passes_site_build_checks(self) -> None:
        meta = build.parse(OBSERVATORY_PATH)
        meta["route"] = "/labs/observatory/"
        meta["src"] = OBSERVATORY_PATH
        errs = build.check_page(meta, meta["body"])
        self.assertEqual(errs, [])


if __name__ == "__main__":
    unittest.main()
