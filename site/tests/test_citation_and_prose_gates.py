"""Tests for the citation gate (scripts/citations.py), the prose gate (scripts/prose.py)
and the daily article cap in build.py. Added 2026-11-09 after a review found ~60 citations
naming the wrong authors and the same rhetorical template across most posts."""
import sys
import unittest
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE / "scripts"))
sys.path.insert(0, str(SITE))

import citations  # noqa: E402
import prose  # noqa: E402

CACHE = {
    "2401.06889": {"title": "Invisible Labor in Open Source Software Ecosystems",
                   "authors": ["John Meluso", "Amanda Casari", "Katie McLaughlin", "Milo Z. Trujillo"]},
    "doi:10.1145/3442188.3445921": {"title": "Reviewable Automated Decision-Making",
                                    "authors": ["Jennifer Cobbe", "Michelle Seng Ah Lee", "Jatinder Singh"]},
}


class CitationGateTests(unittest.TestCase):
    def check(self, html):
        return citations.check_text("t.html", html, CACHE)

    def test_correct_authors_pass(self):
        self.assertEqual(self.check('<p id="fn1">1. John Meluso et al., "Invisible Labor in Open Source Software Ecosystems," arXiv:2401.06889.</p>'), [])

    def test_wrong_authors_fail(self):
        errs = self.check('<p id="fn1">1. Johan Linåker et al., "Invisible Labor in Open Source Software Ecosystems," arXiv:2401.06889.</p>')
        self.assertEqual(len(errs), 1)
        self.assertIn("none of the real authors", errs[0])

    def test_wrong_title_fails(self):
        errs = self.check('<p id="fn1">1. Meluso et al., "Review Latency and the Backlog Death Spiral in Software Commons," arXiv:2401.06889.</p>')
        self.assertTrue(any("title" in e for e in errs))

    def test_unquoted_wrong_title_in_footnote_fails(self):
        errs = self.check('<p id="fn1">1. John Meluso et al., <em>The Backlog Death Spiral in Review Queues</em>, arXiv:2401.06889.</p>')
        self.assertTrue(any("title does not match" in e for e in errs))

    def test_invented_co_authors_fail(self):
        errs = self.check('<p id="fn1">1. John Meluso, Milad Nasr and Florian Tramer, "Invisible Labor in Open Source Software Ecosystems," arXiv:2401.06889.</p>')
        self.assertTrue(any("not on the paper" in e and "nasr" in e for e in errs))

    def test_real_author_list_passes(self):
        ok = '<p id="fn1">1. John Meluso, Amanda Casari, Katie McLaughlin and Milo Z. Trujillo, "Invisible Labor in Open Source Software Ecosystems," arXiv:2401.06889.</p>'
        self.assertEqual(self.check(ok), [])

    def test_bare_pointer_only_needs_to_exist(self):
        self.assertEqual(self.check("<p>Most of this work is never counted (arXiv:2401.06889).</p>"), [])

    def test_uncached_reference_fails(self):
        errs = self.check("<p>See arXiv:2999.00001.</p>")
        self.assertIn("not in scripts/arxiv_cache.json", errs[0])

    def test_doi_in_href_is_checked(self):
        bad = '<li id="fn3">J. Smith, <a href="https://doi.org/10.1145/3442188.3445921">&ldquo;Reviewable Automated Decision-Making,&rdquo;</a> (2021).</li>'
        good = bad.replace("J. Smith", "J. Cobbe, M. S. A. Lee, and J. Singh")
        self.assertEqual(len(self.check(bad)), 1)
        self.assertEqual(self.check(good), [])

    def test_site_citations_all_verified(self):
        cache = citations.load_cache()
        errs = [e for name, raw in citations.all_pages() for e in citations.check_text(name, raw, cache)]
        self.assertEqual(errs, [])


ARTICLE = """---
title: T
takeaway: AI agents need expiring permissions so a stolen credential stops working.
template: article
lede: {lede}
---
{body}
"""


class ProseGateTests(unittest.TestCase):
    def test_new_page_with_staged_contrast_and_tics_fails(self):
        text = ARTICLE.format(lede="AI agents need expiring permissions so a stolen credential stops working.",
                              body="<p>It's a quiet Tuesday. This isn't about speed. It's about trust. That isn't control. It's care.</p>")
        errs = prose.check_text("blog/new.html", text, {})
        self.assertTrue(any("staged" in e for e in errs))
        self.assertTrue(any("stock phrases" in e for e in errs))

    def test_claim_first_page_passes(self):
        text = ARTICLE.format(lede="AI agents need expiring permissions so a stolen credential stops working.",
                              body="<p>Give each agent the narrowest permission for a limited time.</p>")
        self.assertEqual(prose.check_text("blog/new.html", text, {}), [])

    def test_buried_point_fails(self):
        filler = " ".join(["The harbour was busy that morning."] * 40)
        text = ARTICLE.format(lede="A morning at the harbour.", body=f"<p>{filler}</p><p>AI agents need expiring permissions.</p>")
        errs = prose.check_text("blog/new.html", text, {})
        self.assertTrue(any("buried point" in e for e in errs))

    def test_existing_page_may_not_get_worse(self):
        text = ARTICLE.format(lede="AI agents need expiring permissions so a stolen credential stops working.",
                              body="<p>A quiet change. Another quiet change.</p>")
        base = {"blog/old.html": {"staged": 0, "tics": 1, "aphorism": 0, "buried": 0}}
        self.assertTrue(prose.check_text("blog/old.html", text, base))
        base["blog/old.html"]["tics"] = 2
        self.assertEqual(prose.check_text("blog/old.html", text, base), [])


class DailyCapTests(unittest.TestCase):
    def test_more_than_two_new_articles_a_day_fails(self):
        import build
        metas = [{"template": "article", "date": "2026-12-01", "src": build.CONTENT / "blog" / f"p{i}.html",
                  "raw": "---\ntitle: x\n---\n<p>x</p>"} for i in range(3)]
        errs = build.check_citations_and_prose(metas)
        self.assertTrue(any("articles dated 2026-12-01" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
