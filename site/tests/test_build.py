"""Tests for the ORG site build checks (specs/org/requirements-and-tasks.md R3-R5, R10, and T7 RSI suite)."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build


def meta(body: str, **kw) -> dict:
    m = {"title": "t", "description": "d", "reader": "r", "takeaway": "k", "template": "page",
         "route": "/x/", "body": body, "src": build.CONTENT / "x.html"}
    m.update(kw)
    return m


def _extract_json_ld(doc_or_tag: str) -> dict:
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', doc_or_tag, re.S)
    if not m:
        raise AssertionError(f"Missing JSON-LD script in: {doc_or_tag!r}")
    return json.loads(m.group(1))


def _make_synthetic_jpeg(width: int, height: int, sof_marker: int = 0xC0) -> bytes:
    soi = b"\xff\xd8"
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof = (
        b"\xff\xff\xff"
        + bytes([sof_marker])
        + struct.pack(">HBHHB3s", 11, 8, height, width, 1, b"\x01\x11\x00")
    )
    return soi + app0 + sof + b"\xff\xd9"


def _make_synthetic_png(width: int, height: int) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">I", 13) + b"IHDR" + struct.pack(">II5s", width, height, b"\x08\x06\x00\x00\x00")
    return sig + ihdr


class CheckPageTests(unittest.TestCase):
    def test_clean_page_passes(self):
        self.assertEqual(build.check_page(meta("<p>A plain sentence about receipts.</p>"), ""), [])

    def test_missing_front_matter(self):
        errs = build.check_page(meta("<p>x</p>", reader=""), "")
        self.assertTrue(any("reader" in e for e in errs))

    def test_steward_gate_money_and_tokens(self):
        errs = build.check_page(meta("<p>Members save $500 per year with Contribution Tokens.</p>"), "")
        self.assertTrue(any("dollar" in e for e in errs))
        self.assertTrue(any("token" in e for e in errs))

    def test_internal_codes_blocked(self):
        errs = build.check_page(meta("<p>See D-0123 and F7.</p>"), "")
        self.assertEqual(sum("internal code" in e for e in errs), 2)

    def test_research_terms_only_in_researcher_aside(self):
        errs = build.check_page(meta("<p>Our Markov blanket.</p>"), "")
        self.assertTrue(any("research term" in e for e in errs))
        ok = build.check_page(meta('<p>Your boundary.</p><aside class="for-researchers"><details><summary>For researchers</summary><div><p>Markov blanket.</p></div></details></aside>'), "")
        self.assertEqual(ok, [])

    def test_article_fields_required(self):
        errs = build.check_page(meta("<p>x</p>", template="article"), "")
        self.assertTrue(any("date" in e for e in errs))
        self.assertTrue(any("'image'" in e for e in errs))

    def test_article_image_must_exist(self):
        m = meta("<p>x</p>", template="article", date="2026-11-06", category="c", minutes="3", lede="l",
                 image="does-not-exist.jpg", image_alt="A descriptive editorial illustration of a postbox.")
        self.assertTrue(any("not found" in e for e in build.check_page(m, "")))


class SiteTests(unittest.TestCase):
    def test_full_build_has_no_errors_and_emits_feed_and_sitemap(self):
        self.assertEqual(build.build(), 0)
        self.assertTrue((build.DIST / "blog" / "feed.xml").is_file())
        self.assertTrue((build.DIST / "sitemap.xml").is_file())

    def test_js_is_safe(self):
        self.assertEqual(build.check_js(), [])

    def test_shared_horizon_five_phase_explorer_and_three_cases(self):
        sh_path = build.CONTENT / "labs" / "shared-horizon.html"
        m = build.parse(sh_path)
        body = m["body"]
        self.assertIn('id="ex-horizon-phases"', body)
        self.assertIn('id="sh-phase-deck"', body)
        for p in ("1", "2", "3", "4", "5"):
            self.assertIn(f'data-phase-panel="{p}"', body)
        for c in ("1", "2", "3"):
            self.assertIn(f'data-case-panel="{c}"', body)
        self.assertIn("universal basic compute", body.lower())
        self.assertNotIn("Evidence grade A", body)
        self.assertNotIn("Oversight +1", body)

    def test_research_standards_and_working_drafts_section(self):
        res_path = build.CONTENT / "research.html"
        m = build.parse(res_path)
        body = m["body"]
        h_standards = body.find("<h2>Standards and working drafts</h2>")
        h_others = body.find("<h2>Who else is working on these problems</h2>")
        self.assertNotEqual(h_standards, -1)
        self.assertNotEqual(h_others, -1)
        self.assertLess(h_standards, h_others)
        self.assertIn('<div class="grid-2">', body)
        for term in ("IETF WIMSE", "RFC 9000", "RFC 9221", "RFC 8693", "RFC 9476", "COSE RFC 9052", "draft-cin-agent-network-00"):
            self.assertIn(term, body)
        plain = build.EXEMPT_BLOCKS.sub("", body)
        self.assertNotIn("draft-cin-agent-network-00", plain)

    def test_shared_horizon_collective_atlas_builder_role(self):
        """Ensure collective atlas compiler aggregates the canonical builder role and includes it in the table and researcher drawer."""
        html_summary = build.sync_and_render_shared_horizon_atlas()
        self.assertIn("05 · Independent Builder", html_summary)
        self.assertIn("sourced moves", html_summary)
        self.assertIn("organisations", html_summary)
        self.assertIn("Apache Software Foundation", html_summary)
        self.assertIn("Bytecode Alliance", html_summary)

        atlas_path = build.ASSETS / "data" / "collective-atlas.json"
        self.assertTrue(atlas_path.exists(), "collective-atlas.json must be generated")
        data = json.loads(atlas_path.read_text(encoding="utf-8"))
        self.assertIn("builder", data.get("by_role", {}))
        builder_data = data["by_role"]["builder"]
        self.assertGreaterEqual(builder_data["action_cards"], 100)
        self.assertGreaterEqual(builder_data["institutions"], 50)
        self.assertGreaterEqual(len(builder_data["sample_institutions"]), 2)

    def test_observatory_honest_status_across_cards(self):
        """Ensure Observatory cards consistently reflect early in-development state, not premature Live · Scored."""
        index_body = (build.CONTENT / "index.html").read_text(encoding="utf-8")
        labs_index_body = (build.CONTENT / "labs" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('<span class="status">Live · Scored</span><h3>Observatory</h3>', index_body)
        self.assertNotIn('<span class="status">Live · Scored</span><h3>Observatory</h3>', labs_index_body)
        self.assertIn('<span class="status">Early · In development</span><h3>Observatory</h3>', index_body)
        self.assertIn('<span class="status">Early · In development</span><h3>Observatory</h3>', labs_index_body)

    def test_zero_tracking_page_comments_render_and_escape_safely(self):
        research_html = (build.DIST / "research" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="comments"', research_html)
        self.assertIn("https://github.com/cintnet/cin-site/discussions", research_html)
        self.assertIn("mailto:contact@collectiveintelligencenetwork.org", research_html)
        self.assertNotIn("giscus.app", research_html)

        privacy_html = (build.DIST / "privacy" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('id="comments"', privacy_html)

        fixture = {
            "routes": {
                "/research/": {
                    "discussion_url": "https://github.com/cintnet/cin-site/discussions/42",
                    "comments": [
                        {
                            "author": "alice",
                            "created_at": "2026-11-24",
                            "body": "<script>alert(1)</script>Check RFC 9334 reference.",
                        }
                    ],
                }
            }
        }
        rendered = build.render_comments({"route": "/research/", "title": "Research"}, fixture)
        self.assertIn("https://github.com/cintnet/cin-site/discussions/42", rendered)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
        self.assertNotIn("<script>", rendered)


if __name__ == "__main__":
    unittest.main()
