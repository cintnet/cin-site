#!/usr/bin/env python3
"""Unit tests for the planar 69-vs-59 research arc switch and clustering/truss citations on /research/.

Verifies:
1. Planar 1px hairline `[ 69 DISTINCT PAPERS | 59 CONSOLIDATED ARCS ]` view-mode switch
   (`role="group"`, `aria-pressed`, `border-radius: 0`, zero rounded card/pill classes).
2. Exact 10 companion-paper pairs (`69 - 10 = 59` consolidated arcs), combined page counts,
   unified plain-language Part I + Part II scope summaries, and expandable two-part drawers
   with direct `[PART I PDF ↗]` and `[PART II PDF ↗]` links using strict DOM creation (`createElement`/`textContent`).
3. Searchability of `e-means`, `k-means`, `flash-kmeans`, and `k-truss` across `M13`, `M17`, `M19`,
   and `M37` (and `M36+M37` in consolidated arc mode).
4. Technical grounding strictly confined to `<aside class="for-researchers">` and `<section class="footnotes">` (`#fn9`)
   for Bessa et al. (2026, `arXiv:2611.09501`), Yang et al. (2026, `arXiv:2603.09229`),
   Wang & Cheng (2012, `doi:10.14778/2311906.2311909`), and Hossain & Sarıyüce (2026, `arXiv:2603.05207`).
"""

import html
import json
from pathlib import Path
import re
import sys
import unicodedata
import unittest

SITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE_ROOT / "scripts"))
sys.path.insert(0, str(SITE_ROOT))
import build  # noqa: E402
import citations  # noqa: E402

RESEARCH_HTML = SITE_ROOT / "content" / "research.html"
EXPLORER_JS = SITE_ROOT / "assets" / "js" / "research-explorer.js"
STAGES_CSS = SITE_ROOT / "assets" / "css" / "stages.css"
ARXIV_CACHE = SITE_ROOT / "scripts" / "arxiv_cache.json"

EXPECTED_ARC_PAIRS = [
    ("M05+M09", ["M05", "M09"]),
    ("M11+M12", ["M11", "M12"]),
    ("M16+M18", ["M16", "M18"]),
    ("M32+M33", ["M32", "M33"]),
    ("M36+M37", ["M36", "M37"]),
    ("M41+M52", ["M41", "M52"]),
    ("M42+M51", ["M42", "M51"]),
    ("M43+M48", ["M43", "M48"]),
    ("M57+M59", ["M57", "M59"]),
    ("M62+M63", ["M62", "M63"]),
]


def _norm_text(val: str) -> str:
    """Mirror research-explorer.js normText() normalization."""
    s = re.sub(r"[\u2010-\u2015\u2212]", "-", str(val or ""))
    s = s.replace("\u0131", "i")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()


def _build_item_haystack(it: dict, theme_by_id: dict, paper_by_id: dict) -> str:
    parts = [
        it.get("id", ""),
        it.get("title", ""),
        it.get("formal_title", ""),
        it.get("summary", ""),
        it.get("keywords", ""),
        it.get("track", ""),
        it.get("category", ""),
        it.get("status", ""),
    ]
    for tid in it.get("themes", []):
        th = theme_by_id.get(tid)
        if th:
            parts.append(f"theme {tid}")
            parts.append(f"track {tid}")
            parts.append(f"track {tid:02d}")
            parts.append(th.get("short", ""))
            parts.append(th.get("title", ""))
    for es in it.get("essays", []):
        if es and es.get("title"):
            parts.append(es["title"])
    for pid in it.get("papers", []):
        parts.append(pid)
        if pid in paper_by_id:
            parts.append(paper_by_id[pid].get("title", ""))
            parts.append(paper_by_id[pid].get("formal_title", ""))
    joined = _norm_text(" ".join(parts))
    return f" {joined} {joined.replace('-', ' ')} "


def _matches_token(haystack: str, tok: str) -> bool:
    if tok in haystack:
        return True
    tok_space = tok.replace("-", " ")
    if re.match(r"^[a-z0-9]-", tok):
        return f" {tok_space} " in haystack
    return tok_space in haystack


def _search_ids(entries: list[dict], query: str) -> set[str]:
    tokens = [t for t in _norm_text(query).strip().split() if t]
    matched = set()
    for entry in entries:
        if all(_matches_token(entry["_haystack"], tok) for tok in tokens):
            matched.add(entry["id"])
    return matched


class ResearchArcsAndClusteringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_html = RESEARCH_HTML.read_text(encoding="utf-8")
        cls.raw_js = EXPLORER_JS.read_text(encoding="utf-8")
        cls.raw_css = STAGES_CSS.read_text(encoding="utf-8")
        cls.arxiv_cache = json.loads(ARXIV_CACHE.read_text(encoding="utf-8"))

        cat_m = re.search(
            r'<script\b[^>]*id=["\']research-catalog-data["\'][^>]*>(.*?)</script>',
            cls.raw_html,
            re.DOTALL,
        )
        assert cat_m is not None, "Missing #research-catalog-data in research.html"
        cls.catalog = json.loads(cat_m.group(1))
        cls.themes = cls.catalog.get("themes", [])
        cls.items = cls.catalog.get("items", [])
        cls.arcs = cls.catalog.get("arcs", [])

        cls.theme_by_id = {t["id"]: t for t in cls.themes}
        cls.paper_by_id = {it["id"]: it for it in cls.items if it.get("kind") == "paper"}

        cls.distinct_papers = []
        for it in cls.items:
            if it.get("kind") == "paper":
                copy_it = dict(it)
                copy_it["_haystack"] = _build_item_haystack(copy_it, cls.theme_by_id, cls.paper_by_id)
                cls.distinct_papers.append(copy_it)

        distinct_by_id = {p["id"]: p for p in cls.distinct_papers}
        arc_by_paper = {}
        for arc in cls.arcs:
            p1 = distinct_by_id[arc["parts"][0]]
            p2 = distinct_by_id[arc["parts"][1]]
            code_label = f"ARC \u00b7 {p1['id']} + {p2['id']}"
            meta_joined = _norm_text(" ".join([arc["id"], code_label, arc.get("title", ""), arc.get("summary", "")]))
            arc_obj = {
                "id": arc["id"],
                "kind": "arc",
                "parts": list(arc["parts"]),
                "pages": int(p1["pages"]) + int(p2["pages"]),
                "_haystack": f" {meta_joined} {meta_joined.replace('-', ' ')}{p1['_haystack']}{p2['_haystack']}",
            }
            arc_by_paper[p1["id"]] = arc_obj
            arc_by_paper[p2["id"]] = arc_obj

        cls.consolidated_paper_entries = []
        seen_arcs = set()
        for p in cls.distinct_papers:
            if p["id"] in arc_by_paper:
                arc_obj = arc_by_paper[p["id"]]
                if arc_obj["id"] not in seen_arcs:
                    seen_arcs.add(arc_obj["id"])
                    cls.consolidated_paper_entries.append(arc_obj)
            else:
                cls.consolidated_paper_entries.append(p)

    def test_planar_view_mode_switch_markup_and_css(self):
        """Control bar must expose planar 1px hairline 69-vs-59 toggle with role='group' and aria-pressed."""
        bar_m = re.search(
            r'<div class="rx-view-bar">(.*?)</div>\s*<div class="rx-filter-group"',
            self.raw_html,
            re.DOTALL,
        )
        self.assertIsNotNone(bar_m, "Missing .rx-view-bar inside #explorer .rx-controls")
        bar_html = bar_m.group(1)

        self.assertIn('class="rx-view-switch" role="group" aria-label="Paper catalog view mode"', bar_html)
        self.assertRegex(
            bar_html,
            r'<button[^>]*data-view-mode="distinct"[^>]*aria-pressed="true"[^>]*>.*?69 DISTINCT PAPERS</button>',
        )
        self.assertRegex(
            bar_html,
            r'<button[^>]*data-view-mode="arcs"[^>]*aria-pressed="false"[^>]*>.*?59 CONSOLIDATED ARCS</button>',
        )
        self.assertNotRegex(bar_html, r'\b(card|pill)\b')

        self.assertIn(".rx-view-switch", self.raw_css)
        self.assertIn(".rx-view-btn", self.raw_css)
        self.assertIn(".rx-row.rx-row-arc .rx-row-main", self.raw_css)
        self.assertIn(".rx-arc-parts-grid", self.raw_css)
        self.assertIn("border-radius: 0;", self.raw_css)

    def test_ten_companion_pairs_consolidate_69_to_59(self):
        """10 disjoint two-part companion arcs must consolidate 69 distinct papers into 59 paper entries."""
        self.assertEqual(len(self.distinct_papers), 69)
        self.assertEqual(len(self.arcs), 10)

        actual_pairs = [(a["id"], a["parts"]) for a in self.arcs]
        self.assertEqual(actual_pairs, EXPECTED_ARC_PAIRS)

        paired_ids = [pid for _, parts in actual_pairs for pid in parts]
        self.assertEqual(len(paired_ids), 20)
        self.assertEqual(len(set(paired_ids)), 20, "Companion paper pairs must be strictly disjoint")
        for pid in paired_ids:
            self.assertIn(pid, self.paper_by_id, f"Paired paper {pid} missing from catalog items")

        self.assertEqual(len(self.consolidated_paper_entries), 59)

        for arc in self.arcs:
            p1_id, p2_id = arc["parts"]
            title = arc.get("title", "").strip()
            summary = arc.get("summary", "").strip()
            self.assertTrue(title, f"Arc {arc['id']} missing unified title")
            self.assertIn(f"Part I ({p1_id})", summary)
            self.assertIn(f"Part II ({p2_id})", summary)
            self.assertNotIn("\u2014", title + " " + summary, f"Em-dash forbidden in {arc['id']}")
            self.assertNotIn("$", title + " " + summary, f"Raw LaTeX forbidden in {arc['id']}")
            words = re.findall(r"[A-Za-z0-9'-]+", summary)
            self.assertLessEqual(len(words), 35, f"Arc {arc['id']} summary exceeds 35-word plain-language cap")

    def test_explorer_js_strict_dom_creation_and_arc_controls(self):
        """research-explorer.js must use createElement/textContent only and expose both Part I & II PDFs."""
        for forbidden in (".innerHTML", "outerHTML", "insertAdjacentHTML", "document.write(", "eval("):
            self.assertNotIn(forbidden, self.raw_js, f"Forbidden unsafe DOM sink {forbidden} in research-explorer.js")

        self.assertIn("document.createElement(", self.raw_js)
        self.assertIn(".textContent", self.raw_js)
        self.assertIn('"ARC \\u00B7 " + p1.id + " + " + p2.id', self.raw_js)
        self.assertIn('"[PART I PDF \\u2197]"', self.raw_js)
        self.assertIn('"[PART II PDF \\u2197]"', self.raw_js)
        self.assertIn('buildArcPartSpec("PART I", p1)', self.raw_js)
        self.assertIn('buildArcPartSpec("PART II", p2)', self.raw_js)

        js_arc_ids = re.findall(r'id:\s*"(M\d{2}\+M\d{2})"', self.raw_js)
        self.assertEqual(js_arc_ids, [pair_id for pair_id, _ in EXPECTED_ARC_PAIRS])

    def test_emeans_flash_kmeans_and_ktruss_searchability(self):
        """Searching e-means, k-means, flash-kmeans, or k-truss must return M13, M17, M19, and M37 cleanly."""
        emeans_hits = _search_ids(self.distinct_papers, "e-means")
        self.assertTrue({"M17", "M19", "M37"}.issubset(emeans_hits), f"Expected M17/M19/M37 in {emeans_hits}")

        kmeans_hits = _search_ids(self.distinct_papers, "k-means")
        self.assertTrue({"M17", "M19", "M37"}.issubset(kmeans_hits), f"Expected M17/M19/M37 in {kmeans_hits}")

        flash_hits = _search_ids(self.distinct_papers, "flash-kmeans")
        self.assertIn("M37", flash_hits)
        self.assertIn("M37", _search_ids(self.distinct_papers, "flash kmeans"))

        ktruss_hits = _search_ids(self.distinct_papers, "k-truss")
        self.assertTrue({"M13", "M37"}.issubset(ktruss_hits), f"Expected M13/M37 in {ktruss_hits}")
        self.assertTrue({"M13", "M37"}.issubset(_search_ids(self.distinct_papers, "k truss")))

        # Author diacritic & Turkish dotless-i searchability
        self.assertTrue({"M13", "M37"}.issubset(_search_ids(self.distinct_papers, "sariyuce")))
        self.assertTrue({"M13", "M37"}.issubset(_search_ids(self.distinct_papers, "sar\u0131y\u00fcce")))
        self.assertTrue({"M17", "M19", "M37"}.issubset(_search_ids(self.distinct_papers, "bessa")))

        # Consolidated arc mode resolves M37 matches to unified M36+M37 arc
        self.assertIn("M36+M37", _search_ids(self.consolidated_paper_entries, "e-means"))
        self.assertIn("M36+M37", _search_ids(self.consolidated_paper_entries, "flash-kmeans"))
        self.assertTrue({"M13", "M36+M37"}.issubset(_search_ids(self.consolidated_paper_entries, "k-truss")))

    def test_researcher_notes_and_footnote_bijection(self):
        """Technical clustering/truss citations must live strictly inside .for-researchers and #fn9."""
        asides = re.findall(
            r'<aside class="for-researchers">.*?</aside>',
            self.raw_html,
            re.DOTALL,
        )
        footnotes_m = re.search(
            r'<section class="footnotes">(.*?)</section>',
            self.raw_html,
            re.DOTALL,
        )
        self.assertIsNotNone(footnotes_m, "Missing <section class='footnotes'> in research.html")
        asides_blob = html.unescape(" ".join(asides))
        footnotes_blob = html.unescape(footnotes_m.group(1))

        # Grounding inside <aside class="for-researchers">
        self.assertIn("e-means", asides_blob)
        self.assertIn("Flash-KMeans", asides_blob)
        self.assertIn("k-truss", asides_blob)
        self.assertIn("Bessa et al., 2026", asides_blob)
        self.assertIn("Yang et al., 2026", asides_blob)
        self.assertIn("Wang & Cheng, 2012", asides_blob)
        self.assertIn("Hossain & Sar\u0131y\u00fcce, 2026", asides_blob)
        self.assertGreaterEqual(len(re.findall(r'<a href="#fn9">9</a>', " ".join(asides))), 3)

        # Grounding inside <section class="footnotes"> (#fn9) + arxiv_cache.json
        fn9_m = re.search(r'<p id="fn9">(.*?)</p>', footnotes_m.group(1), re.DOTALL)
        self.assertIsNotNone(fn9_m, "Missing <p id='fn9'> in research.html footnotes")
        fn9_text = html.unescape(fn9_m.group(1))
        for expected_ref in (
            "https://arxiv.org/abs/2611.09501",
            "https://arxiv.org/abs/2603.09229",
            "https://doi.org/10.14778/2311906.2311909",
            "https://arxiv.org/abs/2603.05207",
        ):
            self.assertIn(expected_ref, fn9_text)

        for cache_key in ("2611.09501", "2603.09229", "2603.05207", "doi:10.14778/2311906.2311909"):
            self.assertIn(cache_key, self.arxiv_cache, f"Missing {cache_key} in arxiv_cache.json")

        # Main prose must stay 100% plain everyday English (zero technical leakage)
        prose_only = re.sub(r"<style\b[^>]*>.*?</style>", "", self.raw_html, flags=re.DOTALL)
        prose_only = re.sub(r"<script\b[^>]*>.*?</script>", "", prose_only, flags=re.DOTALL)
        prose_only = re.sub(r'<aside class="for-researchers">.*?</aside>', "", prose_only, flags=re.DOTALL)
        prose_only = re.sub(r'<section class="footnotes">.*?</section>', "", prose_only, flags=re.DOTALL)
        prose_unescaped = html.unescape(prose_only)

        for technical_term in (
            "e-means",
            "Flash-KMeans",
            "k-truss",
            "2611.09501",
            "2603.09229",
            "2603.05207",
            "2311906.2311909",
            "Sarıyüce",
        ):
            self.assertNotIn(
                technical_term,
                prose_unescaped,
                f"Technical term/citation '{technical_term}' leaked into plain-language main prose",
            )

        # Build footnote bijection and publisher citation gates pass with 0 errors and 0 warnings
        fn_warnings: list[str] = []
        fn_errors = build.check_footnote_links("research.html", self.raw_html, fn_warnings)
        self.assertEqual(fn_errors, [])
        self.assertEqual(fn_warnings, [])
        self.assertEqual(citations.check_text("research.html", self.raw_html, self.arxiv_cache), [])


if __name__ == "__main__":
    unittest.main()
