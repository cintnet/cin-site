#!/usr/bin/env python3
"""Regression suite for unified warm-paper palette, anti-card feeds, and collapsed disclosure telemetry."""
from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest

SITE_ROOT = Path(__file__).resolve().parent.parent
if str(SITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SITE_ROOT))
import build  # noqa: E402


class WarmPaletteAndCollapsedDisclosuresTests(unittest.TestCase):
    def test_zero_split_brain_dark_mode_media_queries(self) -> None:
        """No CSS or non-explainer content HTML file may inject partial prefers-color-scheme: dark overrides."""
        offenders: list[str] = []
        for p in sorted((SITE_ROOT / "assets" / "css").glob("*.css")):
            if "prefers-color-scheme: dark" in p.read_text(encoding="utf-8"):
                offenders.append(p.relative_to(SITE_ROOT).as_posix())
        for p in sorted((SITE_ROOT / "content").rglob("*.html")):
            raw = p.read_text(encoding="utf-8")
            if "explainer" in raw or "diagram-desktop" in raw:
                continue
            if "prefers-color-scheme: dark" in raw:
                offenders.append(p.relative_to(SITE_ROOT).as_posix())
        self.assertEqual(offenders, [], f"Split-brain prefers-color-scheme: dark found in: {offenders}")

    def test_collapsed_footnotes_and_researcher_telemetry_in_dist(self) -> None:
        """Every built page with footnotes or researcher drawers must collapse and show rich telemetry."""
        dist = SITE_ROOT / "dist"
        if not (dist / "vision" / "index.html").exists():
            self.assertEqual(build.build(), 0)

        checked_footnotes = 0
        checked_researchers = 0
        for html_file in sorted(dist.rglob("index.html")):
            doc = html_file.read_text(encoding="utf-8")
            self.assertIn('<meta name="color-scheme" content="light">', doc)

            for sec_m in re.finditer(
                r'<section\b[^>]*\bclass=["\'][^"\']*\bfootnotes\b[^"\']*["\'][^>]*>(.*?)</section>',
                doc,
                re.S | re.I,
            ):
                sec_inner = sec_m.group(1)
                checked_footnotes += 1
                self.assertIn('class="footnotes-drawer"', sec_inner, f"{html_file} footnotes not wrapped in drawer")
                self.assertNotRegex(
                    sec_inner,
                    r'<details\b[^>]*\bclass="footnotes-drawer"[^>]*\bopen\b',
                    f"{html_file} footnotes drawer must be collapsed by default",
                )
                fn_defs = re.findall(r'<(?:li|p)\b[^>]*\bid=["\']fn[^"\']+["\']', sec_inner, re.I)
                if fn_defs:
                    expected_label = f"{len(fn_defs)} source" + ("s" if len(fn_defs) != 1 else "")
                    self.assertIn(expected_label, sec_inner, f"{html_file} missing exact '{expected_label}' badge")

            for aside_m in re.finditer(
                r'<aside\b[^>]*\bclass=["\'][^"\']*\bfor-researchers\b[^"\']*["\'][^>]*>(.*?)</aside>',
                doc,
                re.S | re.I,
            ):
                aside_inner = aside_m.group(1)
                checked_researchers += 1
                sum_m = re.search(r"<summary\b[^>]*>(.*?)</summary>", aside_inner, re.S | re.I)
                self.assertIsNotNone(sum_m, f"{html_file} researcher aside missing <summary>")
                self.assertIn("disclosure-meta", sum_m.group(1), f"{html_file} researcher summary missing telemetry")
                self.assertIn("words", sum_m.group(1), f"{html_file} researcher summary missing word count")

        self.assertGreaterEqual(checked_footnotes, 90)
        self.assertGreaterEqual(checked_researchers, 90)

    def test_footnote_anchor_auto_expand_in_site_js(self) -> None:
        js = (SITE_ROOT / "assets" / "js" / "site.js").read_text(encoding="utf-8")
        self.assertIn("footnotes-drawer", js)

    def test_anti_card_broadsheet_styles_in_site_css(self) -> None:
        css = (SITE_ROOT / "assets" / "css" / "site.css").read_text(encoding="utf-8")
        self.assertIn("footnotes-drawer", css)
        self.assertIn("disclosure-meta", css)


if __name__ == "__main__":
    unittest.main()
