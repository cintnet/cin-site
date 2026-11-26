#!/usr/bin/env python3
"""Regression tests for micro-VM sandbox isolation, kernel socket holds, decoy upload buckets,
evaluation egress airlocks, and fatigue-bounded oversight guidance on /get-involved/builders/
and /get-involved/labs/."""
from __future__ import annotations

import re
import statistics
import unittest
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = SITE_DIR / "content"


class SecurityBuildersAndLabsMicrovmAndAirlockGuidanceTests(unittest.TestCase):
    def test_builders_microvm_socket_hold_and_decoy_sink_grounding(self) -> None:
        raw = (CONTENT_DIR / "get-involved/builders.html").read_text(encoding="utf-8")
        for needle in (
            "micro-virtual machines",
            "948 working local root exploits",
            "decoy bucket",
            "a-thousand-fewer-paths-to-root",
            "2610.26501",
            "2611.25599",
            "2608.00801",
            "cohere-s-qwen-incident-giving-the-suspected-backdoor-a-way",
            "Ashok Subbabhatta Gopalakrishna",
            "Meghana Aparna Sistla",
            "Anton Sokolov",
            "Geoffrey Voyer",
        ):
            self.assertIn(needle, raw, f"builders.html missing {needle!r}")

    def test_labs_fatigue_routers_eval_airlocks_and_sabotage_audit_grounding(self) -> None:
        raw = (CONTENT_DIR / "get-involved/labs.html").read_text(encoding="utf-8")
        for needle in (
            "reviewer fatigue limits",
            "0.51 to 0.09",
            "default-deny network airlocks",
            "17 percent of the time",
            "2606.08919",
            "2606.21399",
            "2611.30848",
            "2611.21832",
            "2605.26079",
            "2608.28945",
            "Emre Turan",
            "Chubin Zhang",
            "Frederic Lemieux",
            "Keshav Shenoy",
            "Junlin Wang",
            "Jan Hendrik Kirchner",
        ):
            self.assertIn(needle, raw, f"labs.html missing {needle!r}")

    def test_everyday_prose_sentence_bounds_and_zero_leaks(self) -> None:
        for rel_path in ("get-involved/builders.html", "get-involved/labs.html"):
            raw = (CONTENT_DIR / rel_path).read_text(encoding="utf-8")
            _, _, body = raw.split("---", 2)
            everyday = re.sub(r'<aside\b[^>]*for-researchers[^>]*>.*?</aside>', "", body, flags=re.S)
            everyday = re.sub(r'<section class="footnotes">.*?</section>', "", everyday, flags=re.S)
            everyday = re.sub(r"<figure\b.*?</figure>", "", everyday, flags=re.S)
            for leak in ("Base Thesis", "Markov", "Exocortex", "exocortex", "SCITT", "IEC 61508", "—"):
                self.assertNotIn(leak, everyday, f"{rel_path} leaked {leak!r} into everyday prose")

            ps = re.findall(r"<(?:p|li)\b[^>]*>(.*?)</(?:p|li)>", everyday, flags=re.S)
            sentences = []
            for p in ps:
                ct = re.sub(r"<sup[^>]*>.*?</sup>", "", p)
                ct = re.sub(r"<[^>]+>", " ", ct)
                ct = re.sub(r"\s+", " ", ct).strip()
                for s in re.split(r"(?<=[.!?])\s+", ct):
                    if len(s.split()) > 3:
                        sentences.append(s)
            counts = [len(s.split()) for s in sentences]
            self.assertLessEqual(statistics.median(counts), 20.0, f"{rel_path} median > 20")
            self.assertLessEqual(max(counts), 34, f"{rel_path} max > 34 ({max(counts)})")


if __name__ == "__main__":
    unittest.main()
