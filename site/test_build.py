"""Tests for the ORG site build checks (specs/org/requirements-and-tasks.md R3-R5, R10, and T7 RSI suite)."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import re
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET

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


def _make_synthetic_gif(width: int, height: int) -> bytes:
    return b"GIF89a" + struct.pack("<HH", width, height)


def _make_synthetic_webp_lossy(width: int, height: int) -> bytes:
    payload = b"VP8 " + struct.pack("<I", 14) + b"\x00\x00\x00\x9d\x01\x2a" + struct.pack("<HH", width, height)
    file_size = len(payload) + 4
    return b"RIFF" + struct.pack("<I", file_size) + b"WEBP" + payload


def _make_synthetic_webp_lossless(width: int, height: int) -> bytes:
    bits = ((width - 1) & 0x3FFF) | (((height - 1) & 0x3FFF) << 14)
    payload = b"VP8L" + struct.pack("<I", 5) + b"\x2f" + struct.pack("<I", bits)
    file_size = len(payload) + 4
    return b"RIFF" + struct.pack("<I", file_size) + b"WEBP" + payload


def _make_synthetic_webp_extended(width: int, height: int) -> bytes:
    w_bytes = (width - 1).to_bytes(3, "little")
    h_bytes = (height - 1).to_bytes(3, "little")
    payload = b"VP8X" + struct.pack("<I", 10) + b"\x00\x00\x00\x00" + w_bytes + h_bytes
    file_size = len(payload) + 4
    return b"RIFF" + struct.pack("<I", file_size) + b"WEBP" + payload


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

    def test_steward_gate_rejects_royalty_split_and_savings_promise(self):
        errs1 = build.check_page(meta("<p>Contributors split value 85/10/5 automatically.</p>"), "")
        self.assertTrue(any("royalty split" in e for e in errs1))
        errs2 = build.check_page(meta("<p>Bypassing cloud intermediaries yields 95% savings for clinics.</p>"), "")
        self.assertTrue(any("savings promise" in e for e in errs2))

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


# 1. Readability lint check tests
class ReadabilityCheckTests(unittest.TestCase):
    def test_clean_prose_produces_zero_warnings(self):
        warnings: list[str] = []
        fragment = (
            "<p>Why create a personal AI? It is a fair question that deserves a plain answer. "
            "Your assistant should work only for you, like a lawyer who answers to their client.</p>"
        )
        build.check_readability("test.html", fragment, warnings)
        self.assertEqual(warnings, [])

    def test_sentence_at_34_words_passes_cleanly(self):
        warnings: list[str] = []
        sentence_34 = " ".join(f"word{i}" for i in range(1, 35)) + "."
        build.check_readability("boundary_sent.html", f"<p>{sentence_34}</p>", warnings)
        self.assertEqual(warnings, [])

    def test_sentence_over_34_words_produces_warning(self):
        warnings: list[str] = []
        long_sentence = " ".join(f"word{i}" for i in range(1, 36)) + "."
        build.check_readability("long_sent.html", f"<p>{long_sentence}</p>", warnings)
        self.assertEqual(len(warnings), 1)
        self.assertIn("sentence has 35 words", warnings[0])
        self.assertIn("34-word limit", warnings[0])

    def test_paragraph_over_140_words_produces_warning(self):
        warnings: list[str] = []
        s20 = " ".join(f"term{i}" for i in range(20)) + "."
        para160 = " ".join(s20 for _ in range(8))
        build.check_readability("long_para.html", f"<p>{para160}</p>", warnings)
        self.assertEqual(len(warnings), 1)
        self.assertIn("paragraph has 160 words", warnings[0])
        self.assertIn("140-word", warnings[0])

    def test_list_item_and_blockquote_readability_checked(self):
        warnings: list[str] = []
        long_sent = " ".join(f"word{i}" for i in range(1, 36)) + "."
        fragment = f"<ul><li>{long_sent}</li></ul><blockquote><p>Short quote.</p></blockquote>"
        build.check_readability("list_check.html", fragment, warnings)
        self.assertTrue(any("sentence has 35 words" in w for w in warnings))


class ExternalLinkSecurityCheckTests(unittest.TestCase):
    def test_insecure_http_rejected(self):
        errs = build.check_external_links("test.html", '<p>Read <a href="http://insecure.example.org/spec">spec</a>.</p>')
        self.assertTrue(any("must use https://" in e for e in errs))

    def test_protocol_relative_rejected(self):
        errs = build.check_external_links("test.html", '<p>Read <a href="//cdn.example.org/spec">spec</a>.</p>')
        self.assertTrue(any("must use https://" in e for e in errs))

    def test_target_blank_without_noopener_rejected(self):
        errs = build.check_external_links("test.html", '<p><a href="https://example.org/safe" target="_blank">Safe</a></p>')
        self.assertTrue(any("rel='noopener'" in e for e in errs))

    def test_target_blank_with_noopener_passes(self):
        errs = build.check_external_links("test.html", '<p><a href="https://example.org/safe" target="_blank" rel="noopener noreferrer">Safe</a></p>')
        self.assertEqual(errs, [])

    def test_internal_and_fragment_links_pass(self):
        errs = build.check_external_links("test.html", '<p><a href="/blog/">Blog</a> and <a href="#section">Section</a></p>')
        self.assertEqual(errs, [])


# 2. Image alt-text quality check tests
class AltTextCheckTests(unittest.TestCase):
    def test_empty_or_missing_alt_rejected(self):
        errs_fm = build.check_image_alt("blog/p.html", {"image": "post-hero.jpg", "image_alt": "", "body": ""})
        self.assertTrue(any("empty" in e for e in errs_fm))
        errs_body = build.check_image_alt("p.html", {"body": '<p><img src="/assets/img/a.jpg" alt=""></p>'})
        self.assertTrue(any("empty" in e for e in errs_body))

    def test_filename_alt_rejected(self):
        errs = build.check_image_alt("blog/p.html", {"image": "post-hero.jpg", "image_alt": "post-hero.jpg", "body": ""})
        self.assertTrue(any("filename" in e for e in errs))
        errs_stem = build.check_image_alt(
            "p.html",
            {"body": '<img src="/assets/img/vision-two-roads-illustration.jpg" alt="vision-two-roads-illustration">'},
        )
        self.assertTrue(any("filename" in e for e in errs_stem))

    def test_short_under_15_char_alt_rejected(self):
        errs = build.check_image_alt("blog/p.html", {"image": "post-hero.jpg", "image_alt": "A drawing", "body": ""})
        self.assertTrue(any("too short" in e for e in errs))

    def test_valid_descriptive_alt_passes(self):
        valid_alt = "Drawing of a town from above, with a footpath beside a separate canal."
        m = {
            "image": "vision-two-roads.jpg",
            "image_alt": valid_alt,
            "body": f'<figure><img src="/assets/img/vision-two-roads.jpg" alt="{valid_alt}"></figure>',
        }
        self.assertEqual(build.check_image_alt("vision.html", m), [])


# 3. External-link hygiene check in footnotes tests
class FootnoteLinksCheckTests(unittest.TestCase):
    def test_http_link_in_footnotes_rejected_as_error(self):
        warnings: list[str] = []
        body = '<section class="footnotes"><ol><li><a href="http://example.com/doc.pdf">Doc</a></li></ol></section>'
        errs = build.check_footnote_links("blog/p.html", body, warnings)
        self.assertEqual(len(errs), 1)
        self.assertIn("https://", errs[0])

    def test_bare_homepage_in_footnotes_warns(self):
        warnings: list[str] = []
        body = '<section class="footnotes"><ol><li><a href="https://www.imperva.com/">Imperva</a></li></ol></section>'
        errs = build.check_footnote_links("blog/p.html", body, warnings)
        self.assertEqual(errs, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("bare homepage", warnings[0])

    def test_deep_https_url_passes_cleanly(self):
        warnings: list[str] = []
        body = (
            '<section class="footnotes"><ol>'
            '<li><a href="https://c2pa.org/specifications/specifications/2.1/specs/C2PA_Specification.html">C2PA</a> '
            '<a href="#fnref1">↩</a></li></ol></section>'
        )
        errs = build.check_footnote_links("blog/p.html", body, warnings)
        self.assertEqual(errs, [])
        self.assertEqual(warnings, [])

    def test_protocol_relative_and_javascript_links_rejected_as_error(self):
        warnings: list[str] = []
        body = '<section class="footnotes"><ol><li><a href="//insecure.org/path">Relative</a></li><li><a href="javascript:alert(1)">JS</a></li></ol></section>'
        errs = build.check_footnote_links("blog/p.html", body, warnings)
        self.assertEqual(len(errs), 2)
        self.assertTrue(all("https://" in e for e in errs))

    def test_adjacent_footnote_tags_warning(self):
        warnings: list[str] = []
        body = '<p>Claim<sup><a href="#fn1">1</a></sup><sup><a href="#fn2">2</a></sup></p><section class="footnotes"><p id="fn1">1. <a href="https://example.org/1">One</a></p><p id="fn2">2. <a href="https://example.org/2">Two</a></p></section>'
        errs = build.check_footnote_links("blog/p.html", body, warnings)
        self.assertEqual(errs, [])
        self.assertTrue(any("adjacent <sup> tags without separator" in w for w in warnings))


# 4. Atom/RSS feed generator tests
class AtomFeedTests(unittest.TestCase):
    NS = {"atom": build.ATOM_NS}

    def test_atom_feed_valid_xml_and_metadata(self):
        articles = [
            {
                "title": "Two roads: one for people, one for agents",
                "description": "Keeping human conversation spaces distinct from high-speed machine traffic.",
                "route": "/blog/two-roads/",
                "date": "2026-11-04",
                "category": "Architecture",
                "minutes": "5",
                "lede": "Sidewalks and freight rail exist for good reasons.",
                "body": "<p>Sidewalks are built for walking speed.</p>",
            }
        ]
        xml_text = build.render_atom_feed(articles, site_url="https://cintnet.org")
        root = ET.fromstring(xml_text)
        self.assertEqual(root.tag, f"{{{build.ATOM_NS}}}feed")
        self.assertEqual(root.findtext("atom:id", namespaces=self.NS), "https://cintnet.org/blog/")
        entries = root.findall("atom:entry", namespaces=self.NS)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].findtext("atom:title", namespaces=self.NS), "Two roads: one for people, one for agents")
        self.assertEqual(entries[0].findtext("atom:published", namespaces=self.NS), "2026-11-04T00:00:00Z")

    def test_page_shell_includes_atom_alternate_link(self):
        doc = build.page_shell(meta("<p>Hello</p>"), "<p>Hello</p>")
        self.assertIn('<link rel="alternate" type="application/atom+xml"', doc)
        self.assertIn('href="https://cintnet.org/blog/feed.xml"', doc)


# 5. Structured JSON-LD metadata tests
class JsonLdTests(unittest.TestCase):
    def test_article_json_ld_emits_article_schema(self):
        m = meta(
            "<p>Body</p>",
            title="Why receipts matter",
            description="Every agent action should leave an inspectable record.",
            template="article",
            route="/blog/why-receipts-matter/",
            date="2026-11-06",
            category="Oversight",
            image="post-who-is-acting.jpg",
        )
        data = _extract_json_ld(build.page_shell(m, "<p>Body</p>"))
        self.assertEqual(data["@type"], "Article")
        self.assertEqual(data["headline"], "Why receipts matter")
        self.assertEqual(data["image"], "https://cintnet.org/assets/img/post-who-is-acting.jpg")
        self.assertEqual(data["publisher"]["@type"], "Organization")

    def test_page_json_ld_emits_website_and_organization(self):
        m = meta("<p>Body</p>", title="Vision", description="Keeping human oversight practical.", route="/vision/")
        data = _extract_json_ld(build.page_shell(m, "<p>Body</p>"))
        self.assertEqual(data["@type"], "WebSite")
        self.assertEqual(data["publisher"]["@type"], "Organization")


# 6. Per-post Open Graph & Twitter Card tests
class OpenGraphTests(unittest.TestCase):
    def test_article_open_graph_and_twitter_card(self):
        m = meta(
            "<p>Body</p>",
            title="Why receipts matter",
            description="Plain-language receipts.",
            template="article",
            route="/blog/why-receipts-matter/",
            date="2026-11-06",
            category="Oversight",
            image="post-who-is-acting.jpg",
            image_alt="A mechanical hand posting a letter with a blank tag.",
        )
        doc = build.page_shell(m, "<p>Body</p>")
        self.assertIn('<meta property="og:type" content="article">', doc)
        self.assertIn('<meta property="og:image" content="https://cintnet.org/assets/img/post-who-is-acting.jpg">', doc)
        self.assertIn('<meta name="twitter:card" content="summary_large_image">', doc)
        self.assertIn('<meta name="twitter:image" content="https://cintnet.org/assets/img/post-who-is-acting.jpg">', doc)


# 7. Sitemap <lastmod> support tests
class SitemapLastmodTests(unittest.TestCase):
    def test_sitemap_includes_lastmod_for_posts_and_pages(self):
        sample = [
            {"route": "/", "title": "Home"},
            {"route": "/blog/post-one/", "title": "Post One", "date": "2026-09-14"},
        ]
        xml_text = build.render_sitemap(sample, site_url="https://cintnet.org", default_date="2026-11-06")
        root = ET.fromstring(xml_text)
        entries = {
            u.find(f"{{{build.SITEMAP_NS}}}loc").text: u.find(f"{{{build.SITEMAP_NS}}}lastmod").text
            for u in root.findall(f"{{{build.SITEMAP_NS}}}url")
        }
        self.assertEqual(entries["https://cintnet.org/blog/post-one/"], "2026-09-14")
        self.assertEqual(entries["https://cintnet.org/"], "2026-11-06")


# 8. Heading-hierarchy check tests
class HeadingHierarchyTests(unittest.TestCase):
    def test_h1_rejected_in_page_and_article_but_allowed_in_home(self):
        self.assertTrue(any("<h1>" in e for e in build.check_headings("p.html", meta("<h1>Dup</h1>", template="page"))))
        self.assertTrue(any("<h1>" in e for e in build.check_headings("a.html", meta("<h1>Dup</h1>", template="article"))))
        self.assertEqual(build.check_headings("index.html", meta("<h1>Hero</h1><h2>Sec</h2>", template="home")), [])

    def test_skipped_heading_levels_rejected(self):
        errs = build.check_headings("bad.html", meta("<h2>Section</h2><h4>Skipped h3</h4>", template="page"))
        self.assertEqual(len(errs), 1)
        self.assertIn("<h2> -> <h4>", errs[0])


# 9. Duplicate title and description detection tests
class DuplicateMetaTests(unittest.TestCase):
    def test_duplicate_title_and_description_detected(self):
        metas = [
            {"title": "Same Title", "description": "Unique 1", "route": "/a/", "src": Path("content/a.html")},
            {"title": "same title", "description": "Shared Desc", "route": "/b/", "src": Path("content/b.html")},
            {"title": "Other Title", "description": "shared   desc", "route": "/c/", "src": Path("content/c.html")},
        ]
        errs = build.check_duplicates(metas)
        self.assertTrue(any("duplicate title" in e for e in errs))
        self.assertTrue(any("duplicate description" in e for e in errs))

    def test_duplicate_route_detected(self):
        metas = [
            {"title": "About Page", "description": "About CIN", "route": "/about/", "src": Path("content/about.html")},
            {"title": "About Section", "description": "About Index", "route": "/about/", "src": Path("content/about/index.html")},
        ]
        errs = build.check_duplicates(metas)
        self.assertTrue(any("duplicate route '/about/'" in e for e in errs))


# 10. Automatic image width/height CLS prevention tests
class ImageDimensionsTests(unittest.TestCase):
    def test_stdlib_jpeg_and_png_dimension_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            jpg = Path(tmp) / "test.jpg"
            jpg.write_bytes(_make_synthetic_jpeg(1280, 720, sof_marker=0xC2))
            self.assertEqual(build.image_dimensions(jpg), (1280, 720))

            png = Path(tmp) / "test.png"
            png.write_bytes(_make_synthetic_png(640, 480))
            self.assertEqual(build.image_dimensions(png), (640, 480))

    def test_stdlib_webp_and_gif_dimension_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            gif = Path(tmp) / "test.gif"
            gif.write_bytes(_make_synthetic_gif(320, 240))
            self.assertEqual(build.image_dimensions(gif), (320, 240))

            webp_lossy = Path(tmp) / "test_lossy.webp"
            webp_lossy.write_bytes(_make_synthetic_webp_lossy(800, 600))
            self.assertEqual(build.image_dimensions(webp_lossy), (800, 600))

            webp_lossless = Path(tmp) / "test_lossless.webp"
            webp_lossless.write_bytes(_make_synthetic_webp_lossless(1024, 768))
            self.assertEqual(build.image_dimensions(webp_lossless), (1024, 768))

            webp_ext = Path(tmp) / "test_ext.webp"
            webp_ext.write_bytes(_make_synthetic_webp_extended(1920, 1080))
            self.assertEqual(build.image_dimensions(webp_ext), (1920, 1080))

    def test_rendered_figure_and_card_include_width_and_height(self):
        sample_jpg = next((build.ASSETS / "img").glob("*.jpg"))
        w, h = build.image_dimensions(sample_jpg)
        m = meta(
            "<p>x</p>",
            template="article",
            date="2026-11-06",
            category="Essays",
            minutes="4",
            lede="Lede",
            image=sample_jpg.name,
            image_alt="Detailed pen-and-wash illustration of the scene.",
        )
        fig = build.figure(m, "art art-wide")
        card = build.post_card(m, 0)
        self.assertIn(f'width="{w}" height="{h}"', fig)
        self.assertIn(f'width="{w}" height="{h}"', card)


class CrossTeamMetaRSITests(unittest.TestCase):
    def test_researcher_aside_requires_details_summary_div(self):
        bad = '<aside class="for-researchers"><p>Unwrapped text</p></aside>'
        self.assertTrue(any("must wrap body" in e for e in build.check_researcher_asides("test.html", bad)))
        good = '<aside class="for-researchers"><details><summary>For researchers</summary><div><p>Wrapped</p></div></details></aside>'
        self.assertEqual(build.check_researcher_asides("test.html", good), [])

    def test_explainer_figure_validation(self):
        bad = '<figure class="explainer"><svg></svg></figure>'
        errs = build.check_explainers("test.html", bad)
        self.assertEqual(len(errs), 7)
        good = '<figure class="explainer" id="ex-demo"><svg viewBox="0 0 100 50" aria-label="Demo" role="img"><title>Demo figure</title><desc>Comprehensive diagram description</desc><rect width="10" height="10"/></svg><figcaption>Comprehensive diagram caption</figcaption></figure>'
        self.assertEqual(build.check_explainers("test.html", good), [])

    def test_explainer_figcaption_empty_or_too_short_rejected(self):
        empty_cap = '<figure class="explainer" id="ex-demo"><svg viewBox="0 0 100 50" aria-label="Demo" role="img"><rect/></svg><figcaption>   </figcaption></figure>'
        errs_empty = build.check_explainers("test.html", empty_cap)
        self.assertTrue(any("empty or too short" in e for e in errs_empty))

        short_cap = '<figure class="explainer" id="ex-demo"><svg viewBox="0 0 100 50" aria-label="Demo" role="img"><rect/></svg><figcaption>Short</figcaption></figure>'
        errs_short = build.check_explainers("test.html", short_cap)
        self.assertTrue(any("empty or too short" in e for e in errs_short))

    def test_footnote_bijection_catches_dangling_in_text_ref(self):
        w = []
        body = '<p>Claim<sup><a href="#fn2">2</a></sup></p><section class="footnotes"><p id="fn1">1. <a href="https://example.org/paper">Paper</a></p></section>'
        errs = build.check_footnote_links("test.html", body, w)
        self.assertTrue(any("#fn2" in e for e in errs))
        self.assertTrue(any("#fn1" in msg for msg in w))

    def test_footnote_bijection_catches_duplicate_defined_footnote_id(self):
        w = []
        body = (
            '<p>Claim<sup><a href="#fn1">1</a></sup></p>'
            '<section class="footnotes">'
            '<p id="fn1">1. <a href="https://example.org/a">First source</a></p>'
            '<p id="fn1">1. <a href="https://example.org/b">Duplicate source</a></p>'
            '</section>'
        )
        errs = build.check_footnote_links("test.html", body, w)
        self.assertTrue(any("duplicate footnote id '#fn1'" in e for e in errs))

    def test_retired_buzzwords_rejected_even_inside_researcher_aside(self):
        m = meta('<aside class="for-researchers"><details><summary>For researchers</summary><div><p>Somatic Witness</p></div></details></aside>')
        errs = build.check_page(m, "")
        self.assertTrue(any("retired buzzword" in e for e in errs))

    def test_duplicate_element_ids_rejected(self):
        body = '<p><span id="step-one">Step 1</span></p><p><span id="step-one">Duplicate</span></p>'
        errs = build.check_unique_element_ids("test.html", body)
        self.assertTrue(any("duplicate element id 'step-one'" in e for e in errs))
        m = meta(body)
        page_errs = build.check_page(m, "")
        self.assertTrue(any("duplicate element id 'step-one'" in e for e in page_errs))

    def test_element_id_colliding_with_shell_main_rejected(self):
        body = '<section id="main"><p>Content</p></section>'
        errs = build.check_unique_element_ids("test.html", body)
        self.assertTrue(any("collides with reserved page shell anchor '#main'" in e for e in errs))

    def test_unique_element_ids_pass(self):
        body = '<section id="sec-1"><p id="p-1">Text</p><figure id="ex-figure"><p>Fig</p></figure></section>'
        errs = build.check_unique_element_ids("test.html", body)
        self.assertEqual(errs, [])

    def test_git_conflict_markers_rejected(self):
        clean_text = "---\ntitle: T\n---\n<p>Clean text</p>"
        self.assertEqual(build.check_git_conflict_markers("clean.html", clean_text), [])
        conflict_text = "<<<<<<< HEAD\n<p>Left</p>\n=======\n<p>Right</p>\n>>>>>>> loop/integration"
        errs = build.check_git_conflict_markers("conflict.html", conflict_text)
        self.assertTrue(any("git merge conflict markers" in e for e in errs))

    def test_script_and_iframe_tags_rejected_in_content(self):
        errs_script = build.check_interactive_elements_and_embeds("test.html", "<p>Hello <script>alert(1)</script></p>")
        self.assertTrue(any("<script>" in e for e in errs_script))
        errs_iframe = build.check_interactive_elements_and_embeds("test.html", '<p><iframe src="https://example.org"></iframe></p>')
        self.assertTrue(any("<iframe>" in e for e in errs_iframe))

    def test_object_and_embed_tags_rejected_in_content(self):
        errs_obj = build.check_interactive_elements_and_embeds("test.html", '<p><object data="test.pdf"></object></p>')
        self.assertTrue(any("<object>" in e for e in errs_obj))
        errs_emb = build.check_interactive_elements_and_embeds("test.html", '<p><embed src="test.swf"></embed></p>')
        self.assertTrue(any("<embed>" in e for e in errs_emb))

    def test_base_and_meta_tags_rejected_in_content(self):
        errs_base = build.check_interactive_elements_and_embeds("test.html", '<p><base href="https://example.org/"></p>')
        self.assertTrue(any("<base>" in e for e in errs_base))
        errs_meta = build.check_interactive_elements_and_embeds("test.html", '<p><meta http-equiv="refresh" content="0"></p>')
        self.assertTrue(any("<meta>" in e for e in errs_meta))
        errs_link = build.check_interactive_elements_and_embeds("test.html", '<p><link rel="stylesheet" href="https://example.org/style.css"></p>')
        self.assertTrue(any("<link>" in e for e in errs_link))

    def test_inline_style_and_attribute_external_network_requests_rejected(self):
        errs_import = build.check_interactive_elements_and_embeds(
            "test.html",
            "<style>@import url('https://example.org/font.css');</style><p>Hello</p>"
        )
        self.assertTrue(any("external @import or http(s)/protocol-relative url()" in e for e in errs_import))

        errs_url = build.check_interactive_elements_and_embeds(
            "test.html",
            "<style>.beacon { background: url('https://tracker.org/p.png'); }</style><p>Track</p>"
        )
        self.assertTrue(any("external @import or http(s)/protocol-relative url()" in e for e in errs_url))

        errs_proto_rel = build.check_interactive_elements_and_embeds(
            "test.html",
            "<style>.beacon { background: url('//tracker.org/p.png'); }</style><p>Track</p>"
        )
        self.assertTrue(any("external @import or http(s)/protocol-relative url()" in e for e in errs_proto_rel))

        errs_attr = build.check_interactive_elements_and_embeds(
            "test.html",
            '<div style="background-image: url(//tracker.org/pixel.gif)">Track</div>'
        )
        self.assertTrue(any("inline style attribute contains external @import or http(s)/protocol-relative url()" in e for e in errs_attr))

        # Local SVG fragment identifiers like url(#arrow) or url(#cl-arrow) pass cleanly
        ok_svg = build.check_interactive_elements_and_embeds(
            "test.html",
            '<figure class="explainer" id="ex-arrow"><svg><path marker-end="url(#arrow)" /></svg>'
            '<style>#ex-arrow path { stroke: #333; }</style></figure>'
        )
        self.assertEqual(ok_svg, [])

    def test_javascript_uris_rejected_in_content(self):
        errs_href = build.check_interactive_elements_and_embeds("test.html", '<p><a href="javascript:alert(1)">Click</a></p>')
        self.assertTrue(any("javascript:' URIs" in e for e in errs_href))
        errs_src = build.check_interactive_elements_and_embeds("test.html", '<p><img src="javascript:doEvil()" alt="test"></p>')
        self.assertTrue(any("javascript:' URIs" in e for e in errs_src))

    def test_inline_event_handlers_rejected_in_content(self):
        errs_onclick = build.check_interactive_elements_and_embeds("test.html", '<p><button type="button" onclick="run()">Click</button></p>')
        self.assertTrue(any("inline event handler 'onclick'" in e for e in errs_onclick))
        errs_onerror = build.check_interactive_elements_and_embeds("test.html", '<p><img src="/assets/img/a.jpg" onerror="fail()" alt="photo"></p>')
        self.assertTrue(any("inline event handler 'onerror'" in e for e in errs_onerror))
        # Hyphenated data attributes such as data-online or data-onset must not trigger false positives
        ok_data = build.check_interactive_elements_and_embeds("test.html", '<p><span data-online="true">Online</span></p>')
        self.assertEqual(ok_data, [])

    def test_button_missing_type_or_accessible_name_rejected(self):
        errs_no_type = build.check_interactive_elements_and_embeds("test.html", "<p><button>Submit query</button></p>")
        self.assertTrue(any("missing explicit type attribute" in e for e in errs_no_type))
        errs_no_label = build.check_interactive_elements_and_embeds("test.html", '<p><button type="button"></button></p>')
        self.assertTrue(any("no accessible name" in e for e in errs_no_label))
        ok1 = build.check_interactive_elements_and_embeds("test.html", '<p><button type="button">Valid Label</button></p>')
        self.assertEqual(ok1, [])
        ok2 = build.check_interactive_elements_and_embeds("test.html", '<p><button type="button" aria-label="Close dialog"></button></p>')
        self.assertEqual(ok2, [])

    def test_role_button_accessibility_validation(self):
        errs_tabindex = build.check_interactive_elements_and_embeds("test.html", '<g role="button"><text>Click</text></g>')
        self.assertTrue(any("missing tabindex='0'" in e for e in errs_tabindex))
        errs_label = build.check_interactive_elements_and_embeds("test.html", '<g role="button" tabindex="0"><rect width="10" height="10"/></g>')
        self.assertTrue(any("no accessible name" in e for e in errs_label))
        errs_controls = build.check_interactive_elements_and_embeds(
            "test.html",
            '<g role="button" tabindex="0" aria-label="Toggle" aria-controls="missing-target"><rect width="10" height="10"/></g>',
        )
        self.assertTrue(any("targets non-existent element id" in e for e in errs_controls))
        ok = build.check_interactive_elements_and_embeds(
            "test.html",
            '<section id="real-target"><p>Content</p></section>'
            '<g role="button" tabindex="0" aria-label="Toggle" aria-controls="real-target"><rect width="10" height="10"/></g>',
        )
        self.assertEqual(ok, [])

    def test_small_assistants_article_and_explainer(self):
        f = build.CONTENT / "blog" / "why-many-small-assistants-beat-one-giant-mind.html"
        self.assertTrue(f.exists(), "Article must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn('id="ex-small-assistants"', text)
        self.assertIn('id="ex-assistants-toggle"', text)
        self.assertIn('id="ex-assistants-status"', text)
        self.assertIn('id="ex-assistants-left-note"', text)
        self.assertIn('id="ex-assistants-right-note"', text)
        self.assertIn('role="button"', text)
        self.assertIn('tabindex="0"', text)

    def test_ask_dont_equip_explainer(self):
        f = build.CONTENT / "blog" / "why-assistants-should-ask-first.html"
        self.assertTrue(f.exists(), "Article must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn('id="ex-ask-dont-equip"', text)
        self.assertIn('id="ex-toggle-mode"', text)
        self.assertIn('id="ex-waypoint-status"', text)
        self.assertIn('role="button"', text)
        self.assertIn('tabindex="0"', text)
        errs = build.check_explainers("why-assistants-should-ask-first.html", text)
        self.assertEqual(errs, [])

    def test_five_questions_procurement_rubric_explainer(self):
        f = build.CONTENT / "blog" / "five-questions-before-buying-an-ai-agent.html"
        self.assertTrue(f.exists(), "Article must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn('id="ex-procurement-rubric"', text)
        self.assertIn('id="ex-rubric-toggle"', text)
        self.assertIn('id="ex-rubric-status"', text)
        self.assertIn('id="ex-rubric-left-panel"', text)
        self.assertIn('id="ex-rubric-right-panel"', text)
        self.assertIn('role="button"', text)
        self.assertIn('tabindex="0"', text)
        errs = build.check_explainers("five-questions.html", text)
        self.assertEqual(errs, [])

    def test_quests_not_feeds_explainer(self):
        f = build.CONTENT / "blog" / "quests-not-feeds.html"
        self.assertTrue(f.exists(), "Article must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn('id="ex-quests-not-feeds"', text)
        self.assertIn('id="ex-quests-toggle"', text)
        self.assertIn('id="ex-quests-status"', text)
        self.assertIn('id="ex-quests-left-panel"', text)
        self.assertIn('id="ex-quests-right-panel"', text)
        self.assertIn('role="button"', text)
        self.assertIn('tabindex="0"', text)
        errs = build.check_explainers("quests-not-feeds.html", text)
        self.assertEqual(errs, [])

    def test_how_an_ai_assistant_should_say_it_might_be_wrong_explainer(self):
        f = build.CONTENT / "blog" / "how-an-ai-assistant-should-say-it-might-be-wrong.html"
        self.assertTrue(f.exists(), "Article must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn('id="ex-confidence-calibration"', text)
        self.assertIn('id="ex-calib-title"', text)
        self.assertIn('id="ex-calib-desc"', text)
        self.assertIn('id="ex-calibration-toggle"', text)
        self.assertIn('id="ex-calibration-status"', text)
        self.assertIn('role="group"', text)
        self.assertIn('role="button"', text)
        self.assertIn('tabindex="0"', text)
        self.assertIn('aria-labelledby="ex-calib-title ex-calib-desc"', text)
        errs = build.check_explainers("how-an-ai-assistant-should-say-it-might-be-wrong.html", text)
        self.assertEqual(errs, [])
        embed_errs = build.check_interactive_elements_and_embeds("how-an-ai-assistant-should-say-it-might-be-wrong.html", text)
        self.assertEqual(embed_errs, [])

    def test_when_every_assistant_agrees_explainer(self):
        f = build.CONTENT / "blog" / "when-every-assistant-agrees.html"
        self.assertTrue(f.exists(), "Article must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn('id="ex-deliberation-diversity"', text)
        self.assertIn('id="ex-delib-title"', text)
        self.assertIn('id="ex-delib-desc"', text)
        self.assertIn('id="ex-panel-toggle"', text)
        self.assertIn('id="ex-panel-status"', text)
        self.assertIn('role="group"', text)
        self.assertIn('role="button"', text)
        self.assertIn('tabindex="0"', text)
        self.assertIn('aria-labelledby="ex-delib-title ex-delib-desc"', text)
        errs = build.check_explainers("when-every-assistant-agrees.html", text)
        self.assertEqual(errs, [])
        embed_errs = build.check_interactive_elements_and_embeds("when-every-assistant-agrees.html", text)
        self.assertEqual(embed_errs, [])

    def test_out_of_band_approval_explainer(self):
        f = build.CONTENT / "blog" / "why-your-inbox-is-not-a-security-guard.html"
        self.assertTrue(f.exists(), "Article must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn('id="ex-out-of-band-approval"', text)
        self.assertIn('id="ex-oob-title"', text)
        self.assertIn('id="ex-oob-desc"', text)
        self.assertIn('id="ex-oob-toggle"', text)
        self.assertIn('id="ex-oob-left-status"', text)
        self.assertIn('id="ex-oob-right-status"', text)
        self.assertIn('role="group"', text)
        self.assertIn('role="button"', text)
        self.assertIn('tabindex="0"', text)
        self.assertIn('aria-labelledby="ex-oob-title ex-oob-desc"', text)
        errs = build.check_explainers("why-your-inbox-is-not-a-security-guard.html", text)
        self.assertEqual(errs, [])
        embed_errs = build.check_interactive_elements_and_embeds("why-your-inbox-is-not-a-security-guard.html", text)
        self.assertEqual(embed_errs, [])

    def test_principles_floor_explainer(self):
        f = build.CONTENT / "about" / "principles.html"
        self.assertTrue(f.exists(), "principles.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn('id="ex-principles-floor"', text)
        self.assertIn('id="ex-principles-floor-title"', text)
        self.assertIn('id="ex-principles-floor-desc"', text)
        self.assertTrue('role="img"' in text or 'role="group"' in text)
        self.assertIn('aria-labelledby="ex-principles-floor-title ex-principles-floor-desc"', text)
        self.assertIn("01 · BOUNDARY", text)
        self.assertIn("02 · PROCESS", text)
        self.assertIn("03 · VOICE", text)
        self.assertIn("04 · REST", text)
        self.assertIn("05 · PEACE", text)
        self.assertTrue("FAIL-CLOSED BEDROCK" in text or "HARNESS SELF-RESTRAINT" in text)
        errs = build.check_explainers("about/principles.html", text)
        self.assertEqual(errs, [])
        embed_errs = build.check_interactive_elements_and_embeds("about/principles.html", text)
        self.assertEqual(embed_errs, [])

    def test_builders_circuits_explainer(self):
        f = build.CONTENT / "get-involved" / "builders.html"
        self.assertTrue(f.exists(), "builders.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn('id="ex-builder-circuits"', text)
        self.assertIn('id="ex-builder-circuits-title"', text)
        self.assertIn('id="ex-builder-circuits-desc"', text)
        self.assertTrue('role="img"' in text or 'role="group"' in text)
        self.assertIn('aria-labelledby="ex-builder-circuits-title ex-builder-circuits-desc"', text)
        self.assertIn("UNGROUNDED CIRCUIT", text)
        self.assertIn("GROUNDED CIRCUIT", text)
        self.assertIn('data-stage="switchyard"', text)
        self.assertIn("arXiv:2509.13597", text)
        self.assertIn("RFC 8693", text)
        errs = build.check_explainers("get-involved/builders.html", text)
        self.assertEqual(errs, [])
        embed_errs = build.check_interactive_elements_and_embeds("get-involved/builders.html", text)
        self.assertEqual(embed_errs, [])

    def test_how_groups_govern_shared_resource_explainer(self):
        f = build.CONTENT / "blog" / "how-groups-govern-a-shared-resource.html"
        self.assertTrue(f.exists(), "Article must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn('id="ex-commons-governance"', text)
        self.assertIn('id="ex-commons-title"', text)
        self.assertIn('id="ex-commons-desc"', text)
        self.assertIn('role="img"', text)
        self.assertIn('aria-labelledby="ex-commons-title ex-commons-desc"', text)
        self.assertIn('id="ex-ostrom-commons"', text)
        self.assertIn('id="ex-ostrom-title"', text)
        self.assertIn('id="ex-ostrom-desc"', text)
        errs = build.check_explainers("how-groups-govern-a-shared-resource.html", text)
        self.assertEqual(errs, [])
        embed_errs = build.check_interactive_elements_and_embeds("how-groups-govern-a-shared-resource.html", text)
        self.assertEqual(embed_errs, [])

    def test_why_parallel_agents_need_transaction_locks_article(self):
        f = build.CONTENT / "blog" / "why-parallel-agents-need-transaction-locks.html"
        self.assertTrue(f.exists(), "Article must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn('id="ex-transaction-locks"', text)
        self.assertIn('id="ex-tl-desk-title"', text)
        self.assertIn('id="ex-tl-desk-desc"', text)
        self.assertIn('id="ex-tl-mob-title"', text)
        self.assertIn('id="ex-tl-mob-desc"', text)
        self.assertIn('role="group"', text)
        self.assertIn("STATELESS PROMPT GUARDS", text)
        self.assertIn("STATEFUL GOVERNANCE PROXY", text)
        self.assertIn("arXiv:2608.02764", text)
        self.assertIn("doi:10.1145/223784.223785", text)
        self.assertIn("post-why-parallel-agents-need-transaction-locks.jpg", text)
        errs = build.check_explainers("blog/why-parallel-agents-need-transaction-locks.html", text)
        self.assertEqual(errs, [])
        embed_errs = build.check_interactive_elements_and_embeds("blog/why-parallel-agents-need-transaction-locks.html", text)
        self.assertEqual(embed_errs, [])

    def test_others_page_has_participatory_budgeting_citations(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Zambrano", text)
        self.assertIn("Hausladen", text)
        self.assertIn("arXiv:2508.06577", text)
        self.assertIn("arXiv:2609.29819", text)
        self.assertIn("fn33", text)

    def test_get_involved_pages_have_researcher_asides_and_citations(self):
        for name in ("everyone.html", "builders.html", "labs.html", "policy.html", "civil-society.html"):
            f = build.CONTENT / "get-involved" / name
            self.assertTrue(f.exists(), f"Page {name} must exist")
            text = f.read_text(encoding="utf-8")
            self.assertIn('<aside class="for-researchers">', text, f"{name} missing researcher aside")
            self.assertIn('<details><summary>For researchers</summary>', text)
            self.assertIn('<section class="footnotes">', text, f"{name} missing footnotes section")

    def test_policy_safeguards_page_integrity(self):
        f = build.CONTENT / "get-involved" / "policy.html"
        self.assertTrue(f.exists(), "policy.html must exist")
        m = build.parse(f)
        body = m["body"]
        self.assertIn("1. Make public AI visible before it touches residents", body)
        self.assertIn("2. Give software agents their own badges, never a human clerk's login", body)
        self.assertIn("3. Write checkable receipts into every procurement contract", body)
        self.assertIn("4. Guarantee a real human appeal with the power to reverse mistakes", body)
        self.assertIn("5. Invest in public computing the way cities invest in libraries and roads", body)
        # Citations in researcher aside
        self.assertIn("Booth et al., 2026", body)
        self.assertIn("Hulea et al., 2026", body)
        self.assertIn("Mantelero, 2024", body)
        self.assertIn("Dennis &amp; Van Horn, 1966", body)
        self.assertIn("Necula, 1997", body)
        self.assertIn("Ghanem, 2026", body)
        # Footnotes fn1 through fn7
        for i in range(1, 8):
            self.assertIn(f'id="fn{i}"', body)
            self.assertIn(f'href="#fn{i}"', body)
        self.assertIn("arXiv:2411.15149", body)
        self.assertIn("draft-hulea-wimse-agent-mandate", body)
        errs = build.check_page(m, "")
        self.assertEqual(errs, [])
        warnings: list[str] = []
        plain = build.EXEMPT_BLOCKS.sub("", body)
        build.check_readability("get-involved/policy.html", plain, warnings)
        self.assertEqual(warnings, [])

    def test_everyone_civic_deliberation_page_integrity(self):
        f = build.CONTENT / "get-involved" / "everyone.html"
        self.assertTrue(f.exists(), "everyone.html must exist")
        m = build.parse(f)
        body = m["body"]
        self.assertIn("Keep human facilitators in charge of community deliberation", body)
        self.assertIn("Jungherr &amp; Rauchfleisch, 2025", body)
        self.assertIn("arXiv:2503.07690", body)
        self.assertIn('id="fn7"', body)
        self.assertIn('href="#fn7"', body)
        errs = build.check_page(m, "")
        self.assertEqual(errs, [])
        warnings: list[str] = []
        plain = build.EXEMPT_BLOCKS.sub("", body)
        build.check_readability("get-involved/everyone.html", plain, warnings)
        self.assertEqual(warnings, [])


    def test_others_page_has_execution_boundary_citations(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("B&uuml;hler", text)
        self.assertIn("arXiv:2510.21236", text)
        self.assertIn("arXiv:2606.28739", text)
        self.assertIn("fn34", text)

    def test_others_page_has_organizational_governance_and_delegation_citations(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Dux", text)
        self.assertIn("arXiv:2605.20210", text)
        self.assertIn("fn35", text)
        self.assertIn("Rafael Asor", text)
        self.assertIn("draft-asor-wimse-agent-delegation-chain", text)
        self.assertIn("fn36", text)
        self.assertIn("Avatar Intelligence", text)
        self.assertIn("arXiv:2611.03092", text)
        self.assertIn("fn37", text)

    def test_others_page_has_singapore_consensus_citations(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Singapore Consensus", text)
        self.assertIn("Casper", text)
        self.assertIn("arXiv:2608.14611", text)
        self.assertIn("fn39", text)

    def test_others_page_has_privacy_preserving_safety_auditing_citations(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Yixiang Luo", text)
        self.assertIn("arXiv:2610.41401", text)
        self.assertIn("fn45", text)
        self.assertIn("SealCall", text)

    def test_researchers_page_has_encrypted_auditing_invitation(self):
        f = build.CONTENT / "get-involved" / "researchers.html"
        self.assertTrue(f.exists(), "researchers.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("arXiv:2610.41401", text)
        self.assertIn("fn6", text)
        self.assertIn("SealCall", text)

    def test_others_page_has_mechanistic_concept_bottleneck_citations(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Antonio De Santis", text)
        self.assertIn("Schrasing Tong", text)
        self.assertIn("MIT CSAIL", text)
        self.assertIn("arXiv:2603.07343", text)
        self.assertIn("M-CBM", text)
        self.assertIn("fn40", text)

    def test_others_page_has_leaseguard_admission_control_citations(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Junru Zhu", text)
        self.assertIn("admission control", text)
        self.assertIn("arXiv:2609.24077", text)
        self.assertIn("LeaseGuard", text)

    def test_others_page_has_dependable_agent_hard_guard_citations(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Frederick Roth", text)
        self.assertIn("arXiv:2611.01043", text)
        self.assertIn("fn43", text)
        self.assertIn("deterministic code guards", text)

    def test_others_page_has_orbit_multi_agent_evaluation_citations(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("ORBIT", text)
        self.assertIn("Hagag", text)
        self.assertIn("arXiv:2609.33102", text)
        self.assertIn("fn44", text)
        self.assertIn("defense transferability gap", text)
        r_file = build.CONTENT / "get-involved" / "researchers.html"
        self.assertTrue(r_file.exists(), "researchers.html must exist")
        r_text = r_file.read_text(encoding="utf-8")
        self.assertIn("arXiv:2609.33102", r_text)

    def test_others_page_has_untrusted_monitoring_and_securegard_citations(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Gardner-Challis", text)
        self.assertIn("arXiv:2602.20628", text)
        self.assertIn("fn47", text)
        self.assertIn("Xiong", text)
        self.assertIn("arXiv:2611.06682", text)
        self.assertIn("fn48", text)
        self.assertIn("SecureGARD", text)

        r_file = build.CONTENT / "get-involved" / "researchers.html"
        self.assertTrue(r_file.exists(), "researchers.html must exist")
        r_text = r_file.read_text(encoding="utf-8")
        self.assertIn("arXiv:2602.20628", r_text)
        self.assertIn("arXiv:2611.06682", r_text)
        self.assertIn("SecureGARD", r_text)
        self.assertIn("arXiv:2611.03939", r_text)
        self.assertIn("draft-ietf-wimse-http-signature", r_text)
        self.assertIn("fn7", r_text)
        self.assertIn("fn8", r_text)
        self.assertIn("fn9", r_text)

    def test_others_page_has_coordx_principal_chain_and_authorization_citations(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Hyland-Wood", text)
        self.assertIn("arXiv:2611.06034", text)
        self.assertIn("fn52", text)
        self.assertIn("Muruaga", text)
        self.assertIn("arXiv:2608.15888", text)
        self.assertIn("fn53", text)
        self.assertIn("AuthorizationBench", text)
        self.assertIn("arXiv:2610.27548", text)
        self.assertIn("fn54", text)
        self.assertIn("AuthBench", text)
        self.assertIn("arXiv:2605.14859", text)
        self.assertIn("fn55", text)
        self.assertIn("MiniScope", text)
        self.assertIn("arXiv:2512.11147", text)
        self.assertIn("fn56", text)

        r_file = build.CONTENT / "get-involved" / "researchers.html"
        self.assertTrue(r_file.exists(), "researchers.html must exist")
        r_text = r_file.read_text(encoding="utf-8")
        self.assertIn("arXiv:2611.06034", r_text)
        self.assertIn("arXiv:2610.27548", r_text)
        self.assertIn("fn10", r_text)
        self.assertIn("fn11", r_text)
        self.assertIn("arXiv:2512.11147", r_text)
        self.assertIn("arXiv:2605.14859", r_text)
        self.assertIn("fn12", r_text)
        self.assertIn("fn13", r_text)

    def test_others_page_has_continuous_authorization_and_delegation_provenance_citations(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Shajari", text)
        self.assertIn("arXiv:2611.05632", text)
        self.assertIn("fn64", text)
        self.assertIn("Dalugoda", text)
        self.assertIn("draft-helixar-hdp-agentic-delegation", text)
        self.assertIn("fn65", text)

    def test_others_page_has_delegate_eval_citations(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("DelegateEval", text)
        self.assertIn("Jichao Li", text)
        self.assertIn("arXiv:2611.07508", text)
        self.assertIn("fn66", text)

    def test_others_page_has_delegated_misalignment_and_ancestry_attestation_citations(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Zonghao Ying", text)
        self.assertIn("arXiv:2609.27900", text)
        self.assertIn("fn67", text)
        self.assertIn("Lifei Liu", text)
        self.assertIn("arXiv:2608.30387", text)
        self.assertIn("fn68", text)

    def test_others_page_has_structured_specifications_and_mesh_resilience_citations(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Xin Liu", text)
        self.assertIn("arXiv:2611.06263", text)
        self.assertIn("fn73", text)
        self.assertIn("JunYong Lee", text)
        self.assertIn("arXiv:2611.06389", text)
        self.assertIn("fn74", text)

    def test_others_page_has_attested_capability_leases_and_biometric_delegation_citations(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Zhiyang Ding", text)
        self.assertIn("arXiv:2609.02690", text)
        self.assertIn("fn75", text)
        self.assertIn("Joseph Geo Benjamin", text)
        self.assertIn("arXiv:2608.04292", text)
        self.assertIn("fn76", text)

    def test_others_page_has_intent_verified_delegation_chains_citation(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "others.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("KrishnaSaiReddy Patil", text)
        self.assertIn("arXiv:2604.02767", text)
        self.assertIn("fn77", text)
        self.assertIn("SentinelAgent", text)

    def test_honest_assistant_essay_has_rational_updating_and_anti_sycophancy_citation(self):
        f = build.CONTENT / "blog" / "how-an-ai-assistant-should-say-it-might-be-wrong.html"
        self.assertTrue(f.exists(), "how-an-ai-assistant-should-say-it-might-be-wrong.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("rational belief updating", text)
        self.assertIn("2608.26511", text)
        self.assertIn("fn5", text)
        self.assertIn("Ma et al.", text)

    def test_researchers_page_has_clear_specification_citation(self):
        f = build.CONTENT / "get-involved" / "researchers.html"
        self.assertTrue(f.exists(), "researchers.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("arXiv:2611.06263", text)
        self.assertIn("fn21", text)

    def test_researchers_page_has_attested_capability_leases_citation(self):
        f = build.CONTENT / "get-involved" / "researchers.html"
        self.assertTrue(f.exists(), "researchers.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("arXiv:2609.02690", text)
        self.assertIn("arXiv:2608.04292", text)
        self.assertIn("fn22", text)

    def test_research_page_theme_3_has_for_researchers_aside(self):
        f = build.CONTENT / "research.html"
        self.assertTrue(f.exists(), "research.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Theme 3", text)
        self.assertIn("DelegateEval", text)
        self.assertIn("Li et al., 2026", text)
        self.assertIn("Dennis &amp; Van Horn, 1966", text)
        self.assertIn("arXiv:2611.07508", text)

    def test_labs_page_has_five_simulation_lessons_and_sticky_collusion_citations(self):
        f = build.CONTENT / "labs" / "index.html"
        self.assertTrue(f.exists(), "labs index.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertTrue(
            any(
                k in text
                for k in [
                    "Five lessons from our sandbox",
                    "Six lessons from our sandbox",
                    "Seven lessons from our sandbox",
                    "Eight lessons from our sandbox",
                    "Nine lessons from our sandbox",
                    "Ten lessons from our sandbox",
                    "Eleven lessons from our sandbox",
                    "Twelve lessons from our sandbox",
                    "Thirteen lessons from our sandbox",
                    "Fourteen lessons from our sandbox",
                    "Fifteen lessons from our sandbox",
                    "Sixteen lessons from our sandbox",
                ]
            )
        )
        self.assertIn("Memory carries bad habits; clean slates protect the network", text)
        self.assertIn("One central dispatcher bottlenecks; local clusters adapt best", text)
        self.assertIn("Polite talk cannot replace mathematical agreement bounds", text)
        self.assertIn("2610.39660", text)
        self.assertIn("2609.24967", text)
        self.assertIn("2602.16873", text)
        self.assertIn("2603.01213", text)
        self.assertIn("AdaptOrch", text)
        self.assertIn("Joshua Adrian Cahyono", text)
        self.assertIn("Xinrui Shi", text)
        self.assertIn("Berdoz", text)

    def test_support_page_has_permission_fatigue_and_researcher_asides(self):
        f = build.CONTENT / "support.html"
        self.assertTrue(f.exists(), "support.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Why can't I just click", text)
        self.assertIn("alert fatigue", text)
        self.assertIn("Zhang et al.", text)
        self.assertIn("arXiv:2510.04465", text)
        self.assertIn("Wu et al.", text)
        self.assertIn("arXiv:2511.17959", text)
        self.assertIn("Freiberger", text)
        self.assertIn("arXiv:2604.21455", text)
        self.assertIn("Can an automated assistant vote", text)
        self.assertIn("De Liddo et al.", text)
        self.assertIn("arXiv:2603.16260", text)
        self.assertIn("Enr&iacute;quez et al.", text)
        self.assertIn("arXiv:2609.20059", text)
        self.assertIn("how can it work with others without exposing my private data", text)
        self.assertIn("Meel &amp; Ulukus", text)
        self.assertIn("arXiv:2510.05068", text)
        errs = build.check_explainers("support.html", text)
        self.assertEqual(errs, [])
        embed_errs = build.check_interactive_elements_and_embeds("support.html", text)
        self.assertEqual(embed_errs, [])

    def test_observatory_page_has_scale_dependent_progress_citations(self):
        f = build.CONTENT / "labs" / "observatory.html"
        self.assertTrue(f.exists(), "observatory.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Gundlach", text)
        self.assertIn("arxiv.org/abs/2511.21622", text)
        self.assertIn("fn7", text)
        self.assertIn("scale-dependent", text)

    def test_observatory_page_has_ai_risk_repository_citations(self):
        f = build.CONTENT / "labs" / "observatory.html"
        self.assertTrue(f.exists(), "observatory.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Slattery", text)
        self.assertIn("arxiv.org/abs/2408.12622", text)
        self.assertIn("airisk.mit.edu/risks", text)
        self.assertIn("fn8", text)
        self.assertIn("MIT AI Risk Repository", text)

    def test_observatory_page_has_trace_evaluation_citations(self):
        f = build.CONTENT / "labs" / "observatory.html"
        self.assertTrue(f.exists(), "observatory.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Johnson and Hayden Helm", text)
        self.assertIn("arxiv.org/abs/2611.06803", text)
        self.assertIn("fn9", text)
        self.assertIn("Task-Efficient Agent Evaluation", text)

    def test_observatory_page_has_semantic_incident_tracking_citations(self):
        f = build.CONTENT / "labs" / "observatory.html"
        self.assertTrue(f.exists(), "observatory.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Russo", text)
        self.assertIn("arxiv.org/abs/2507.23669", text)
        self.assertIn("fn13", text)
        self.assertIn("semantic similarity", text)

    def test_observatory_page_has_swe_marathon_citations(self):
        f = build.CONTENT / "labs" / "observatory.html"
        self.assertTrue(f.exists(), "observatory.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Desai", text)
        self.assertIn("arxiv.org/abs/2606.07682", text)
        self.assertIn("fn17", text)
        self.assertIn("SWE-Marathon", text)

    def test_observatory_page_has_incident_governance_citations(self):
        f = build.CONTENT / "labs" / "observatory.html"
        self.assertTrue(f.exists(), "observatory.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Sidhu", text)
        self.assertIn("arxiv.org/abs/2607.05163", text)
        self.assertIn("fn18", text)
        self.assertIn("AI Incident Governance", text)

    def test_builders_page_has_capability_scoped_harness_citations(self):
        f = build.CONTENT / "get-involved" / "builders.html"
        self.assertTrue(f.exists(), "builders.html must exist")
        text = f.read_text(encoding="utf-8")
        self.assertIn("Bouras et al.", text)
        self.assertIn("arXiv:2609.08371", text)
        self.assertIn("Authority Is Not a String", text)
        errs = build.check_explainers("get-involved/builders.html", text)
        self.assertEqual(errs, [])

    def test_about_others_page_citations_and_structure(self):
        f = build.CONTENT / "about" / "others.html"
        self.assertTrue(f.exists(), "about/others.html must exist")
        m = build.parse(f)
        self.assertEqual(m["section"], "about")
        text = m["body"]
        self.assertIn("Redwood Research", text)
        self.assertIn("NIST CAISI", text)
        self.assertIn("LawZero", text)
        self.assertIn("IETF", text)
        self.assertIn("Salvaneschi", text)
        self.assertIn("Nusrat &amp; Nusrat", text)
        self.assertIn("arXiv:2611.05341", text)
        self.assertIn("Weight-space programming for auditing clinical decision networks", text)
        self.assertIn("Joe Salowey and Yaron Sheffer", text)
        self.assertIn("draft-ietf-wimse-http-signature", text)
        self.assertIn("Nick Hagar", text)
        self.assertIn("Northwestern University", text)
        self.assertIn("arXiv:2611.03939", text)
        errs = build.check_page(m, "")
        self.assertEqual(errs, [])

    def test_keeping_the_story_behind_what_we_build_essay_structure_and_citations(self):
        f = build.CONTENT / "blog" / "keeping-the-story-behind-what-we-build.html"
        self.assertTrue(f.exists(), "keeping-the-story-behind-what-we-build.html must exist")
        m = build.parse(f)
        self.assertEqual(m["template"], "article")
        self.assertEqual(m["category"], "Building")
        self.assertEqual(m["image"], "post-keeping-the-story-behind-the-system.jpg")
        img_path = build.ASSETS / "img" / m["image"]
        self.assertTrue(img_path.is_file(), "article image must exist")
        self.assertLess(img_path.stat().st_size, 300_000, "article image must be < 300 KB")
        text = m["body"]
        self.assertIn("Margaret-Anne Storey", text)
        self.assertIn("arXiv:2611.08456", text)
        self.assertIn("David Hyland-Wood and Rob Ewin", text)
        self.assertIn("arXiv:2611.06034", text)
        self.assertIn("ex-cognitive-tours", text)
        self.assertIn("ex-tour-inspect-btn", text)
        errs = build.check_page(m, "")
        self.assertEqual(errs, [])
        explainer_errs = build.check_explainers("blog/keeping-the-story-behind-what-we-build.html", text)
        self.assertEqual(explainer_errs, [])



class SiteTests(unittest.TestCase):
    def test_full_build_has_no_errors_and_emits_feed_and_sitemap(self):
        self.assertEqual(build.build(), 0)
        self.assertTrue((build.DIST / "blog" / "feed.xml").is_file())
        self.assertTrue((build.DIST / "sitemap.xml").is_file())

    def test_js_is_safe(self):
        self.assertEqual(build.check_js(), [])

    def test_check_js_catches_eval_and_string_timers(self):
        with tempfile.TemporaryDirectory() as td:
            js_dir = Path(td) / "js"
            js_dir.mkdir()
            css_dir = Path(td) / "css"
            css_dir.mkdir()
            bad_js = js_dir / "bad.js"
            bad_js.write_text('setTimeout("doSomething()", 100);', encoding="utf-8")
            old_assets = build.ASSETS
            try:
                build.ASSETS = Path(td)
                errs = build.check_js()
                self.assertTrue(any("string-based timer evaluation" in e for e in errs))
            finally:
                build.ASSETS = old_assets

    def test_check_js_catches_external_network_requests(self):
        with tempfile.TemporaryDirectory() as td:
            js_dir = Path(td) / "js"
            js_dir.mkdir()
            css_dir = Path(td) / "css"
            css_dir.mkdir()
            old_assets = build.ASSETS
            try:
                build.ASSETS = Path(td)
                for snippet, label in (
                    ('fetch("https://api.example.com")', "fetch()"),
                    ('const xhr = new XMLHttpRequest();', "XMLHttpRequest"),
                    ('navigator.sendBeacon("/telemetry", data);', "navigator.sendBeacon"),
                    ('const ws = new WebSocket("wss://relay.example.com");', "WebSocket"),
                    ('const ev = new EventSource("/stream");', "EventSource"),
                ):
                    test_file = js_dir / f"test_{abs(hash(label))}.js"
                    test_file.write_text(snippet, encoding="utf-8")
                    errs = build.check_js()
                    self.assertTrue(
                        any("external network request" in e for e in errs),
                        f"Expected external network request rejection for '{label}', got: {errs}",
                    )
                    test_file.unlink()
            finally:
                build.ASSETS = old_assets

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
        errs = build.check_page(m, "")
        self.assertEqual(errs, [])

    def test_research_69_working_papers_and_pdfs(self):
        res_path = build.CONTENT / "research.html"
        m = build.parse(res_path)
        body = m["body"]
        self.assertIn('id="working-papers"', body)
        self.assertIn("Dima Baker", body)
        pdf_links = re.findall(r'href="(/assets/papers/m\d{2}_[a-z0-9_]+\.pdf)"', body)
        self.assertEqual(len(set(pdf_links)), 69)
        self.assertGreaterEqual(len(pdf_links), 69)
        for rel_href in pdf_links:
            pdf_file = build.ROOT / rel_href.lstrip("/")
            self.assertTrue(pdf_file.exists(), f"Missing PDF asset {pdf_file}")

    def test_humanizer_audit_zero_tells_across_all_site_content(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("humanizer_audit", r"loop\humanizer_audit.py")
        if spec and spec.loader:
            ha = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ha)
            all_tells = []
            for html_file in sorted(build.CONTENT.rglob("*.html")):
                all_tells.extend(ha.audit_file(html_file, build.CONTENT))
            self.assertEqual(all_tells, [])

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

    def test_research_page_has_proof_carrying_message_citation(self):
        res_path = build.CONTENT / "research.html"
        m = build.parse(res_path)
        body = m["body"]
        self.assertIn("arXiv:2610.39109", body)
        self.assertIn("Ghosh", body)
        self.assertIn("Proof-Carrying Message Protocol", body)
        plain = build.EXEMPT_BLOCKS.sub("", body)
        self.assertNotIn("Proof-Carrying Message Protocol", plain)

    def test_pooling_orders_article_and_explainer(self):
        post_path = build.CONTENT / "blog" / "pooling-orders-without-showing-your-books.html"
        self.assertTrue(post_path.is_file())
        m = build.parse(post_path)
        body = m["body"]
        self.assertIn('id="ex-buyer-pool"', body)
        self.assertIn('id="ex-pool-toggle"', body)
        self.assertIn('id="ex-pool-status"', body)
        self.assertIn('role="button"', body)
        self.assertIn('aria-controls="ex-pool-status"', body)
        self.assertIn('<aside class="for-researchers">', body)
        plain = build.EXEMPT_BLOCKS.sub("", body)
        self.assertNotIn("Private Set Intersection", plain)
        self.assertNotIn("Homomorphic", plain)

    def test_giving_credit_article_and_counterfactual_explainer(self):
        post_path = build.CONTENT / "blog" / "giving-credit-when-many-hands-build.html"
        self.assertTrue(post_path.is_file())
        m = build.parse(post_path)
        body = m["body"]
        self.assertIn('id="ex-counterfactual-credit"', body)
        self.assertIn('role="img"', body)
        self.assertIn('aria-labelledby="ex-credit-title ex-credit-desc"', body)
        self.assertIn('<figcaption>', body)
        self.assertIn('<aside class="for-researchers">', body)
        plain = build.EXEMPT_BLOCKS.sub("", body)
        self.assertNotIn("Data Shapley", plain)
        self.assertIn("counterfactual credit", body.lower())
        self.assertIn("testing what changes when a piece is removed", body.lower())



class FragmentAnchorCheckTests(unittest.TestCase):
    def test_in_page_anchor_missing_rejected(self):
        pages = {"/page/": '<a href="#missing-id">Jump</a><h2 id="real-id">Title</h2>'}
        errs = build.check_fragment_anchors(pages)
        self.assertEqual(len(errs), 1)
        self.assertIn("in-page anchor link '#missing-id'", errs[0])

    def test_in_page_anchor_present_passes(self):
        pages = {"/page/": '<a href="#real-id">Jump</a><h2 id="real-id">Title</h2>'}
        self.assertEqual(build.check_fragment_anchors(pages), [])

    def test_cross_page_anchor_missing_rejected(self):
        pages = {
            "/about/": '<a href="/vision/#missing-sec">Vision</a>',
            "/vision/": '<section id="real-sec">Vision</section>',
        }
        errs = build.check_fragment_anchors(pages)
        self.assertEqual(len(errs), 1)
        self.assertIn("cross-page anchor link '/vision/#missing-sec'", errs[0])

    def test_cross_page_anchor_present_passes(self):
        pages = {
            "/about/": '<a href="/vision/#real-sec">Vision</a>',
            "/vision/": '<section id="real-sec">Vision</section>',
        }
        self.assertEqual(build.check_fragment_anchors(pages), [])

    def test_bare_hash_and_special_schemes_ignored(self):
        pages = {"/home/": '<a href="#">Back to top</a><a href="mailto:test@cintnet.org">Contact</a>'}
        self.assertEqual(build.check_fragment_anchors(pages), [])


class CognitiveAccessibilityAndMarkupIntegrityTests(unittest.TestCase):
    def test_empty_heading_rejected(self):
        m = meta("<h2></h2><p>Paragraph</p>")
        errs = build.check_headings("empty_h2.html", m)
        self.assertTrue(any("empty <h2" in e for e in errs))

        m_ws = meta("<h3 id='sec'>   </h3><p>Paragraph</p>")
        errs_ws = build.check_headings("whitespace_h3.html", m_ws)
        self.assertTrue(any("empty <h3" in e for e in errs_ws))

    def test_valid_heading_passes(self):
        m = meta("<h2>Clear Section Title</h2><p>Paragraph</p>")
        errs = build.check_headings("clean_heading.html", m)
        self.assertEqual(errs, [])

    def test_text_justification_in_content_rejected(self):
        body_inline = '<p style="text-align: justify">Rivers of white text.</p>'
        errs_inline = build.check_text_justification("justified.html", body_inline)
        self.assertTrue(any("text-align: justify" in e for e in errs_inline))

        body_attr = '<p align="justify">Rivers of white text.</p>'
        errs_attr = build.check_text_justification("justified_attr.html", body_attr)
        self.assertTrue(any("align=\"justify\"" in e for e in errs_attr))

    def test_text_justification_in_css_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            css_dir = Path(td)
            (css_dir / "bad.css").write_text("p { text-align: justify; }", encoding="utf-8")
            orig_assets = build.ASSETS
            try:
                build.ASSETS = Path(td).parent
                # Ensure the mock ASSETS/css points to css_dir
                mock_assets = Path(td)
                (mock_assets / "js").mkdir()
                (mock_assets / "css").mkdir(exist_ok=True)
                (mock_assets / "css" / "style.css").write_text(".prose { text-align: justify; }", encoding="utf-8")
                build.ASSETS = mock_assets
                errs = build.check_js()
                self.assertTrue(any("text-align: justify" in e for e in errs))
            finally:
                build.ASSETS = orig_assets

    def test_anchor_missing_accessible_name_rejected(self):
        body_empty = '<p>Visit <a href="/vision/"></a> today.</p>'
        errs = build.check_accessible_links("empty_a.html", body_empty)
        self.assertEqual(len(errs), 1)
        self.assertIn("anchor link missing accessible name", errs[0])

    def test_anchor_with_accessible_name_passes(self):
        body_text = '<p>Visit <a href="/vision/">our vision</a> today.</p>'
        self.assertEqual(build.check_accessible_links("text_a.html", body_text), [])

        body_aria = '<p>Visit <a href="/vision/" aria-label="Our Vision"></a> today.</p>'
        self.assertEqual(build.check_accessible_links("aria_a.html", body_aria), [])

        body_img = '<p><a href="/vision/"><img src="/assets/img/logo-192.png" alt="Collective Intelligence Network"></a></p>'
        self.assertEqual(build.check_accessible_links("img_a.html", body_img), [])

    def test_explainer_missing_title_or_desc_rejected(self):
        fig_no_title = """<figure class="explainer" id="ex-test">
          <svg viewBox="0 0 100 100" role="img" aria-labelledby="ex-desc">
            <desc id="ex-desc">A detailed description of the graphic that exceeds fifteen characters.</desc>
          </svg>
          <figcaption>A valid descriptive caption explaining this diagram in detail.</figcaption>
        </figure>"""
        errs = build.check_explainers("no_title.html", fig_no_title)
        self.assertTrue(any("missing <title>" in e for e in errs))

        fig_no_desc = """<figure class="explainer" id="ex-test">
          <svg viewBox="0 0 100 100" role="img" aria-labelledby="ex-title">
            <title id="ex-title">Valid Title</title>
          </svg>
          <figcaption>A valid descriptive caption explaining this diagram in detail.</figcaption>
        </figure>"""
        errs_desc = build.check_explainers("no_desc.html", fig_no_desc)
        self.assertTrue(any("missing <desc>" in e for e in errs_desc))

    def test_explainer_short_title_or_desc_rejected(self):
        fig_short = """<figure class="explainer" id="ex-test">
          <svg viewBox="0 0 100 100" role="img" aria-labelledby="ex-title ex-desc">
            <title id="ex-title">A</title>
            <desc id="ex-desc">Too short</desc>
          </svg>
          <figcaption>A valid descriptive caption explaining this diagram in detail.</figcaption>
        </figure>"""
        errs = build.check_explainers("short_meta.html", fig_short)
        self.assertTrue(any("<title> is too short" in e for e in errs))
        self.assertTrue(any("<desc> is too short" in e for e in errs))

    def test_explainer_valid_title_and_desc_passes(self):
        fig_valid = """<figure class="explainer" id="ex-test">
          <svg viewBox="0 0 100 100" role="img" aria-labelledby="ex-title ex-desc">
            <title id="ex-title">Overview of Network Routing</title>
            <desc id="ex-desc">A detailed description of the graphic that exceeds fifteen characters.</desc>
          </svg>
          <figcaption>A valid descriptive caption explaining this diagram in detail.</figcaption>
        </figure>"""
        errs = build.check_explainers("valid.html", fig_valid)
        self.assertEqual(errs, [])

    def test_corrections_page_structure_and_verification(self):
        corr_path = build.CONTENT / "corrections.html"
        self.assertTrue(corr_path.exists())
        meta = build.parse(corr_path)
        self.assertEqual(meta["section"], "about")
        self.assertIn("ex-corrections-lifecycle", meta["body"])
        self.assertIn("aside class=\"for-researchers\"", meta["body"])
        self.assertIn("ForecastBench", meta["body"])
        errs = build.check_page(meta, "")
        self.assertEqual(errs, [])


class ComprehensiveWebAccessibilityAndFormSecurityTests(unittest.TestCase):
    def test_inline_focus_outline_removal_rejected(self):
        body1 = '<p style="outline: none;">Focus outline stripped</p>'
        errs1 = build.check_focus_visible_styling("test.html", body1)
        self.assertTrue(any("outline: none" in e for e in errs1))

        body2 = '<a href="/vision/" style="outline: 0;">Vision</a>'
        errs2 = build.check_focus_visible_styling("test.html", body2)
        self.assertTrue(any("outline: 0" in e for e in errs2))

    def test_inline_valid_styling_passes(self):
        body = '<p style="margin: 1.5rem 0; color: #131014;">Clean inline styling</p>'
        self.assertEqual(build.check_focus_visible_styling("test.html", body), [])

    def test_css_focus_outline_removal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            mock_assets = Path(td)
            (mock_assets / "js").mkdir()
            (mock_assets / "css").mkdir()
            (mock_assets / "css" / "bad.css").write_text(":focus { outline: none; }", encoding="utf-8")
            orig_assets = build.ASSETS
            try:
                build.ASSETS = mock_assets
                errs = build.check_js()
                self.assertTrue(any("strips focus indicators" in e for e in errs))
            finally:
                build.ASSETS = orig_assets

    def test_css_valid_focus_visible_passes(self):
        with tempfile.TemporaryDirectory() as td:
            mock_assets = Path(td)
            (mock_assets / "js").mkdir()
            (mock_assets / "css").mkdir()
            css_code = ":focus:not(:focus-visible) { outline: none; }\n:focus-visible { outline: 2px solid green; }"
            (mock_assets / "css" / "good.css").write_text(css_code, encoding="utf-8")
            orig_assets = build.ASSETS
            try:
                build.ASSETS = mock_assets
                errs = build.check_js()
                self.assertEqual(errs, [])
            finally:
                build.ASSETS = orig_assets

    def test_table_missing_accessible_name_rejected(self):
        table_html = '<table><tr><th scope="col">Header</th></tr><tr><td>Data</td></tr></table>'
        errs = build.check_table_accessibility("test.html", table_html)
        self.assertTrue(any("missing accessible name" in e for e in errs))

    def test_table_short_caption_rejected(self):
        table_html = '<table><caption>AB</caption><tr><th scope="col">Header</th></tr></table>'
        errs = build.check_table_accessibility("test.html", table_html)
        self.assertTrue(any("<caption> is too short" in e for e in errs))

    def test_table_missing_th_headers_rejected(self):
        table_html = '<table><caption>Metric Comparison Table</caption><tr><td>Row</td></tr></table>'
        errs = build.check_table_accessibility("test.html", table_html)
        self.assertTrue(any("contains no <th> header cells" in e for e in errs))

    def test_table_empty_th_header_rejected(self):
        table_html = '<table><caption>Metric Comparison Table</caption><tr><th scope="col"></th></tr></table>'
        errs = build.check_table_accessibility("test.html", table_html)
        self.assertTrue(any("empty <th> header cell" in e for e in errs))

    def test_table_th_missing_scope_rejected(self):
        table_html = '<table><caption>Metric Comparison Table</caption><tr><th>Metric Name</th></tr></table>'
        errs = build.check_table_accessibility("test.html", table_html)
        self.assertTrue(any("missing explicit scope attribute" in e for e in errs))

    def test_presentation_table_with_th_or_caption_rejected(self):
        table_html = '<table role="presentation"><caption>Layout</caption><tr><td>Text</td></tr></table>'
        errs = build.check_table_accessibility("test.html", table_html)
        self.assertTrue(any("presentation table" in e for e in errs))

    def test_valid_data_table_passes(self):
        table_html = (
            '<table>'
            '  <caption>Comparison of Architectural Isolation Mechanisms</caption>'
            '  <thead><tr><th scope="col">Mechanism</th><th scope="col">Verification</th></tr></thead>'
            '  <tbody><tr><td>Object-Capability</td><td>Proof-Carrying Code</td></tr></tbody>'
            '</table>'
        )
        self.assertEqual(build.check_table_accessibility("test.html", table_html), [])

    def test_table_summary_attribute_rejected(self):
        table_html = (
            '<table summary="Obsolete summary">'
            '  <caption>Comparison of Isolation</caption>'
            '  <thead><tr><th scope="col">Col</th></tr></thead>'
            '  <tbody><tr><td>Data</td></tr></tbody>'
            '</table>'
        )
        errs = build.check_table_accessibility("test.html", table_html)
        self.assertTrue(any("obsolete 'summary' attribute" in e for e in errs))

    def test_table_caption_not_first_child_rejected(self):
        table_html = (
            '<table>'
            '  <thead><tr><th scope="col">Col</th></tr></thead>'
            '  <caption>Comparison of Isolation</caption>'
            '  <tbody><tr><td>Data</td></tr></tbody>'
            '</table>'
        )
        errs = build.check_table_accessibility("test.html", table_html)
        self.assertTrue(any("must be the first element child of <table>" in e for e in errs))

    def test_table_td_with_scope_rejected(self):
        table_html = (
            '<table>'
            '  <caption>Comparison of Isolation</caption>'
            '  <thead><tr><th scope="col">Col</th></tr></thead>'
            '  <tbody><tr><td scope="row">Data</td></tr></tbody>'
            '</table>'
        )
        errs = build.check_table_accessibility("test.html", table_html)
        self.assertTrue(any("scope attribute is only valid on <th> header cells" in e for e in errs))

    def test_table_td_dangling_headers_reference_rejected(self):
        table_html = (
            '<table>'
            '  <caption>Comparison of Isolation</caption>'
            '  <thead><tr><th id="h1" scope="col">Col1</th></tr></thead>'
            '  <tbody><tr><td headers="h1 h2">Data</td></tr></tbody>'
            '</table>'
        )
        errs = build.check_table_accessibility("test.html", table_html)
        self.assertTrue(any("references 'h2' which does not exist on any <th> cell" in e for e in errs))

    def test_table_td_valid_headers_reference_passes(self):
        table_html = (
            '<table>'
            '  <caption>Comparison of Isolation</caption>'
            '  <thead><tr><th id="h1" scope="col">Col1</th><th id="h2" scope="col">Col2</th></tr></thead>'
            '  <tbody><tr><td headers="h1 h2">Data</td><td>Data2</td></tr></tbody>'
            '</table>'
        )
        self.assertEqual(build.check_table_accessibility("test.html", table_html), [])

    def test_form_external_action_rejected(self):
        form_html = '<form action="https://tracker.thirdparty.com/collect"><input type="text" aria-label="Search"></form>'
        errs = build.check_form_accessibility_and_security("test.html", form_html)
        self.assertTrue(any("submits to external endpoint" in e for e in errs))

    def test_form_relative_action_passes(self):
        form_html = '<form action="/search/"><label for="q">Query</label><input type="text" id="q"></form>'
        self.assertEqual(build.check_form_accessibility_and_security("test.html", form_html), [])

    def test_form_control_missing_accessible_label_rejected(self):
        form_html = '<form action="/feedback/"><input type="text" name="comment"></form>'
        errs = build.check_form_accessibility_and_security("test.html", form_html)
        self.assertTrue(any("missing accessible label" in e for e in errs))

    def test_form_control_with_label_for_or_aria_passes(self):
        form_aria = '<form action="/"><input type="text" aria-label="Full search term"></form>'
        self.assertEqual(build.check_form_accessibility_and_security("test.html", form_aria), [])

        form_for = '<form action="/"><label for="email-in">Email</label><input type="email" id="email-in"></form>'
        self.assertEqual(build.check_form_accessibility_and_security("test.html", form_for), [])

    def test_form_hidden_and_button_inputs_exempt(self):
        form_html = '<form action="/"><input type="hidden" name="csrf" value="123"><input type="submit" value="Send"></form>'
        self.assertEqual(build.check_form_accessibility_and_security("test.html", form_html), [])

    def test_formaction_external_endpoint_rejected(self):
        btn_html = '<form action="/"><label for="t1">Text</label><input id="t1" type="text"><button type="submit" formaction="https://tracker.org/submit">Go</button></form>'
        errs = build.check_form_accessibility_and_security("test.html", btn_html)
        self.assertTrue(any("submits to external endpoint" in e for e in errs), f"Expected formaction error, got: {errs}")

        inp_html = '<form action="/"><label for="t2">Text</label><input id="t2" type="text"><input type="submit" formaction="https://leak.com/data" value="Submit"></form>'
        errs2 = build.check_form_accessibility_and_security("test.html", inp_html)
        self.assertTrue(any("submits to external endpoint" in e for e in errs2), f"Expected input formaction error, got: {errs2}")

    def test_formaction_relative_path_passes(self):
        btn_html = '<form action="/"><label for="t3">Text</label><input id="t3" type="text"><button type="submit" formaction="/local/submit">Go</button></form>'
        self.assertEqual(build.check_form_accessibility_and_security("test.html", btn_html), [])

    def test_formtarget_blank_without_noopener_rejected(self):
        btn_html = '<form action="/"><label for="t4">Text</label><input id="t4" type="text"><button type="submit" formtarget="_blank">Open</button></form>'
        errs = build.check_form_accessibility_and_security("test.html", btn_html)
        self.assertTrue(any("must include rel='noopener' or formrel='noopener'" in e for e in errs), f"Expected reverse tabnabbing error, got: {errs}")

    def test_formtarget_blank_with_noopener_passes(self):
        btn_html = '<form action="/"><label for="t5">Text</label><input id="t5" type="text"><button type="submit" formtarget="_blank" rel="noopener">Open</button></form>'
        self.assertEqual(build.check_form_accessibility_and_security("test.html", btn_html), [])

    def test_form_container_target_blank_without_noopener_rejected(self):
        form_html = '<form action="/" target="_blank"><label for="t_blank">Text</label><input id="t_blank" type="text"></form>'
        errs = build.check_form_accessibility_and_security("test.html", form_html)
        self.assertTrue(any("must include rel='noopener' or rel='noreferrer'" in e for e in errs))

    def test_form_container_target_blank_with_noopener_passes(self):
        form_html = '<form action="/" target="_blank" rel="noopener"><label for="t_ok">Text</label><input id="t_ok" type="text"></form>'
        self.assertEqual(build.check_form_accessibility_and_security("test.html", form_html), [])

    def test_nested_form_rejected(self):
        form_html = '<form action="/outer/"><form action="/inner/"><label for="nested_in">Text</label><input id="nested_in" type="text"></form></form>'
        errs = build.check_form_accessibility_and_security("test.html", form_html)
        self.assertTrue(any("nested <form> elements detected" in e for e in errs))

    def test_form_invalid_method_rejected(self):
        form_html = '<form action="/" method="put"><label for="m_in">Text</label><input id="m_in" type="text"></form>'
        errs = build.check_form_accessibility_and_security("test.html", form_html)
        self.assertTrue(any("declares invalid method token" in e for e in errs))

    def test_form_valid_methods_pass(self):
        for method in ("get", "post", "dialog"):
            form_html = f'<form action="/" method="{method}"><label for="m_{method}">Text</label><input id="m_{method}" type="text"></form>'
            self.assertEqual(build.check_form_accessibility_and_security("test.html", form_html), [])

    def test_button_invalid_type_rejected(self):
        btn_html = '<form action="/"><button type="invalid">Click</button></form>'
        errs = build.check_form_accessibility_and_security("test.html", btn_html)
        self.assertTrue(any("declares invalid type attribute" in e for e in errs))

    def test_button_valid_types_pass(self):
        for btype in ("submit", "reset", "button", "menu"):
            btn_html = f'<form action="/"><button type="{btype}">Click</button></form>'
            self.assertEqual(build.check_form_accessibility_and_security("test.html", btn_html), [])

    def test_input_invalid_type_rejected(self):
        inp_html = '<form action="/"><input type="unsupported" aria-label="Unsupported"></form>'
        errs = build.check_form_accessibility_and_security("test.html", inp_html)
        self.assertTrue(any("declares invalid type attribute" in e for e in errs))

    def test_portal_tag_rejected(self):
        portal_html = '<portal src="/test/"></portal>'
        errs = build.check_interactive_elements_and_embeds("test.html", portal_html)
        self.assertTrue(any("<portal>" in e for e in errs))

    def test_vbscript_and_data_uris_rejected(self):
        vbs_html = '<a href="vbscript:msgbox(1)">Click</a>'
        errs = build.check_interactive_elements_and_embeds("test.html", vbs_html)
        self.assertTrue(any("'vbscript:'" in e for e in errs), f"Expected vbscript URI error, got: {errs}")

        data_html = '<iframe src="data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg=="></iframe>'
        errs2 = build.check_interactive_elements_and_embeds("test.html", data_html)
        self.assertTrue(any("content must not contain" in e for e in errs2), f"Expected iframe/data URI error, got: {errs2}")

    def test_distracting_elements_marquee_blink_rejected(self):
        self.assertTrue(any("distracting elements" in e for e in build.check_distracting_elements("t.html", "<marquee>Alert</marquee>")))
        self.assertTrue(any("distracting elements" in e for e in build.check_distracting_elements("t.html", "<blink>Important</blink>")))

    def test_distracting_elements_clean_html_passes(self):
        self.assertEqual(build.check_distracting_elements("t.html", "<p>Calm, accessible web content.</p>"), [])

    def test_obsolete_presentational_elements_rejected(self):
        for tag in ("<font color='red'>Text</font>", "<center>Centered</center>", "<strike>Old</strike>", "<tt>Code</tt>", "<big>Huge</big>", "<acronym title='Test'>T</acronym>"):
            errs = build.check_obsolete_presentational_elements("t.html", f"<p>{tag}</p>")
            self.assertTrue(any("obsolete presentational element" in e for e in errs), f"Expected rejection for {tag}")

    def test_obsolete_presentational_elements_clean_html_passes(self):
        self.assertEqual(build.check_obsolete_presentational_elements("t.html", "<p>Semantic <em>emphasized</em> and <strong>strong</strong> text.</p>"), [])

    def test_positive_tabindex_rejected(self):
        errs = build.check_interactive_elements_and_embeds("test.html", '<p><a href="/" tabindex="1">Link</a></p>')
        self.assertTrue(any("positive tabindex='1'" in e for e in errs))
        errs2 = build.check_interactive_elements_and_embeds("test.html", '<div tabindex="+2">Interactive</div>')
        self.assertTrue(any("positive tabindex='+2'" in e for e in errs2))

    def test_natural_and_programmatic_tabindex_passes(self):
        errs = build.check_interactive_elements_and_embeds(
            "test.html",
            '<div role="button" tabindex="0" aria-label="Action">Click</div><div tabindex="-1">Target</div>'
        )
        self.assertEqual(errs, [])

    def test_landmark_main_tag_in_content_rejected(self):
        errs = build.check_landmark_integrity("test.html", '<main><h2>Heading</h2></main>')
        self.assertTrue(any("duplicate <main>" in e for e in errs))

    def test_clean_content_without_main_passes(self):
        errs = build.check_landmark_integrity("test.html", '<section><h2>Heading</h2><p>Body</p></section>')
        self.assertEqual(errs, [])


class PolicyPageProcurementGatesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dest = build.DIST / "get-involved" / "policy" / "index.html"
        if not dest.exists():
            build.build()

    def test_policy_page_has_accessible_procurement_gates_explainer(self):
        policy_html = (build.CONTENT / "get-involved" / "policy.html").read_text(encoding="utf-8")
        self.assertIn('id="ex-policy-procurement-gates"', policy_html)
        self.assertIn('id="ex-policy-gates-title"', policy_html)
        self.assertIn('id="ex-policy-gates-desc"', policy_html)
        self.assertIn("PUBLIC PROCUREMENT GATES", policy_html)
        self.assertIn("GATE 01 · REGISTRY", policy_html)
        self.assertIn("GATE 02 · BADGES", policy_html)
        self.assertIn("GATE 03 · AUDIT", policy_html)
        self.assertIn("GATE 04 · CONTEST", policy_html)
        self.assertIn("CIVIC INVARIANT", policy_html)
        errs = build.check_explainers("get-involved/policy.html", policy_html)
        self.assertEqual(errs, [], f"check_explainers failed on policy.html: {errs}")

    def test_policy_built_page_contains_explainer(self):
        dest = build.DIST / "get-involved" / "policy" / "index.html"
        self.assertTrue(dest.exists(), f"Expected {dest} to exist")
        html = dest.read_text(encoding="utf-8")
        self.assertIn('id="ex-policy-procurement-gates"', html)
        self.assertIn("Public register", html)
        self.assertIn("Scoped agent badges", html)
        self.assertIn("Open action receipts", html)
        self.assertIn("Human appeal", html)



class GovernancePageExplainerTests(unittest.TestCase):
    def test_governance_page_has_accessible_stages_explainer(self):
        gov_html = (build.CONTENT / "about" / "governance.html").read_text(encoding="utf-8")
        self.assertIn('id="ex-governance-stages"', gov_html)
        self.assertIn('id="ex-gov-title"', gov_html)
        self.assertIn('id="ex-gov-desc"', gov_html)
        self.assertIn("STAGE 1 · FOUNDING STEWARD", gov_html)
        self.assertIn("STAGE 2 · FEDERATED STEWARDS", gov_html)
        self.assertIn("STAGE 3 · DEMOCRATIC STANDING", gov_html)
        self.assertTrue("19 NON-DEROGABLE FLOOR INVARIANTS" in gov_html or "19 HARNESS &amp; LEDGER SEALS" in gov_html)
        errs = build.check_explainers("about/governance.html", gov_html)
        self.assertEqual(errs, [], f"check_explainers failed on governance.html: {errs}")

    def test_governance_page_cites_public_constitutional_ai(self):
        gov_html = (build.CONTENT / "about" / "governance.html").read_text(encoding="utf-8")
        self.assertIn("2406.16696", gov_html)
        self.assertIn("Gilad Abiri", gov_html)
        self.assertIn("Public Constitutional AI", gov_html)


class ResearchersPageExplainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dest = build.DIST / "get-involved" / "researchers" / "index.html"
        if not dest.exists():
            build.build()

    def test_researchers_page_has_accessible_agenda_explainer(self):
        res_html = (build.CONTENT / "get-involved" / "researchers.html").read_text(encoding="utf-8")
        self.assertIn('id="ex-research-agenda"', res_html)
        self.assertIn('id="ex-research-title"', res_html)
        self.assertIn('id="ex-research-desc"', res_html)
        self.assertIn("01 · AGENT BOUNDARIES", res_html)
        self.assertIn("02 · MULTI-AGENT NETWORKS", res_html)
        self.assertIn("03 · CIVIC OVERSIGHT", res_html)
        self.assertIn("SANDBOX SIMULATION", res_html)
        errs = build.check_explainers("get-involved/researchers.html", res_html)
        self.assertEqual(errs, [], f"check_explainers failed on researchers.html: {errs}")

    def test_researchers_built_page_contains_explainer(self):
        dest = build.DIST / "get-involved" / "researchers" / "index.html"
        self.assertTrue(dest.exists(), f"Expected {dest} to exist")
        html = dest.read_text(encoding="utf-8")
        self.assertIn('id="ex-research-agenda"', html)
        self.assertIn("AGENT BOUNDARIES", html)
        self.assertIn("MULTI-AGENT NETWORKS", html)
        self.assertIn("CIVIC OVERSIGHT", html)


class FocusOrderAndAriaAccessibilityTests(unittest.TestCase):
    def test_positive_tabindex_rejected(self):
        html = '<button tabindex="1">Submit</button>'
        errs = build.check_focus_order_and_tabindex("test.html", html)
        self.assertTrue(any("positive tabindex" in e for e in errs), f"Expected positive tabindex rejection, got: {errs}")

        html_link = '<a href="/about" tabindex="5">About</a>'
        errs = build.check_focus_order_and_tabindex("test.html", html_link)
        self.assertTrue(any("positive tabindex" in e for e in errs), f"Expected positive tabindex rejection, got: {errs}")

    def test_zero_and_negative_tabindex_pass(self):
        html = '<div tabindex="0">Interactive region</div><a href="/research" tabindex="-1">Skip target</a>'
        errs = build.check_focus_order_and_tabindex("test.html", html)
        self.assertEqual(errs, [])

    def test_aria_hidden_on_interactive_button_rejected(self):
        html = '<button type="button" aria-hidden="true">Hidden action</button>'
        errs = build.check_aria_hidden_focusability("test.html", html)
        self.assertTrue(any("aria-hidden='true'" in e for e in errs), f"Expected aria-hidden rejection, got: {errs}")

    def test_aria_hidden_on_link_with_href_rejected(self):
        html = '<a href="/contact" aria-hidden="true">Contact us</a>'
        errs = build.check_aria_hidden_focusability("test.html", html)
        self.assertTrue(any("aria-hidden='true'" in e for e in errs), f"Expected aria-hidden rejection, got: {errs}")

    def test_aria_hidden_on_explicit_tabindex_zero_rejected(self):
        html = '<div tabindex="0" aria-hidden="true">Custom widget</div>'
        errs = build.check_aria_hidden_focusability("test.html", html)
        self.assertTrue(any("aria-hidden='true'" in e for e in errs), f"Expected aria-hidden rejection, got: {errs}")

    def test_aria_hidden_on_non_interactive_elements_passes(self):
        html = '<span aria-hidden="true">*</span><svg aria-hidden="true"><circle r="5"></circle></svg>'
        errs = build.check_aria_hidden_focusability("test.html", html)
        self.assertEqual(errs, [])

    def test_accesskey_rejected(self):
        html = '<a href="/" accesskey="h">Home</a>'
        errs = build.check_accesskey_attributes("test.html", html)
        self.assertTrue(any("accesskey='h'" in e for e in errs), f"Expected accesskey rejection, got: {errs}")

    def test_clean_html_passes_all_checks(self):
        html = '<header><a href="/vision/">Vision</a></header><main><button type="button">Action</button></main>'
        self.assertEqual(build.check_focus_order_and_tabindex("clean.html", html), [])
        self.assertEqual(build.check_aria_hidden_focusability("clean.html", html), [])
        self.assertEqual(build.check_accesskey_attributes("clean.html", html), [])

    def test_site_css_includes_scroll_padding_or_margin_top(self):
        css_text = (build.ASSETS / "css" / "site.css").read_text(encoding="utf-8")
        self.assertTrue(
            bool(re.search(r"scroll-(?:padding|margin)-top\b", css_text, re.I)),
            "site.css must declare scroll-padding-top or scroll-margin-top for WCAG 2.2 SC 2.4.11",
        )


class StructuralListAndPresentationalRoleAccessibilityTests(unittest.TestCase):
    def test_orphaned_li_rejected(self):
        html = '<p>Some text</p><li>Orphaned list item</li>'
        errs = build.check_list_structure("test.html", html)
        self.assertTrue(any("orphaned outside" in e for e in errs), f"Expected orphaned <li> error, got: {errs}")

    def test_direct_non_li_child_in_ul_rejected(self):
        html = '<ul><p>Direct paragraph inside ul</p><li>Valid item</li></ul>'
        errs = build.check_list_structure("test.html", html)
        self.assertTrue(any("contains direct child <p>" in e for e in errs), f"Expected direct child rejection, got: {errs}")

    def test_direct_non_li_child_in_ol_rejected(self):
        html = '<ol><div>Direct div inside ol</div><li>Valid item</li></ol>'
        errs = build.check_list_structure("test.html", html)
        self.assertTrue(any("contains direct child <div>" in e for e in errs), f"Expected direct child rejection, got: {errs}")

    def test_valid_list_structure_passes(self):
        html = '<ul><li>First item</li><li>Second item with <a href="/about">link</a></li></ul>'
        errs = build.check_list_structure("test.html", html)
        self.assertEqual(errs, [])

    def test_orphaned_dt_dd_rejected(self):
        html = '<dt>Orphaned term</dt><dd>Orphaned description</dd>'
        errs = build.check_list_structure("test.html", html)
        self.assertTrue(any("orphaned outside" in e for e in errs), f"Expected orphaned <dt>/<dd> error, got: {errs}")

    def test_valid_dl_structure_passes(self):
        html = '<dl><dt>Term</dt><dd>Definition</dd></dl>'
        errs = build.check_list_structure("test.html", html)
        self.assertEqual(errs, [])

    def test_presentational_role_on_button_rejected(self):
        html = '<button type="button" role="presentation">Submit</button>'
        errs = build.check_presentational_roles("test.html", html)
        self.assertTrue(any("presentational roles must not be applied" in e for e in errs), f"Expected role='presentation' error, got: {errs}")

    def test_presentational_role_on_link_with_href_rejected(self):
        html = '<a href="/vision" role="none">Vision page</a>'
        errs = build.check_presentational_roles("test.html", html)
        self.assertTrue(any("presentational roles must not be applied" in e for e in errs), f"Expected role='none' error, got: {errs}")

    def test_presentational_role_on_landmark_rejected(self):
        html = '<nav role="presentation"><a href="/">Home</a></nav>'
        errs = build.check_presentational_roles("test.html", html)
        self.assertTrue(any("presentational roles must not be applied" in e for e in errs), f"Expected landmark presentation error, got: {errs}")

    def test_presentational_role_on_focusable_custom_element_rejected(self):
        html = '<div tabindex="0" role="presentation">Custom focusable card</div>'
        errs = build.check_presentational_roles("test.html", html)
        self.assertTrue(any("presentational roles must not be applied" in e for e in errs), f"Expected role='presentation' error, got: {errs}")

    def test_presentational_role_on_decorative_image_or_div_passes(self):
        html = '<img src="/assets/img/icon.png" alt="" role="presentation"><div role="none">Content</div>'
        errs = build.check_presentational_roles("test.html", html)
        self.assertEqual(errs, [])

    def test_viewport_zoom_scalability_rejects_user_scalable_no(self):
        doc = '<html><head><meta name="viewport" content="width=device-width, user-scalable=no"></head><body></body></html>'
        errs = build.check_viewport_zoom_scalability("/test/", doc)
        self.assertTrue(any("user-scalable=no" in e for e in errs), f"Expected user-scalable=no error, got: {errs}")

    def test_viewport_zoom_scalability_rejects_maximum_scale_one(self):
        doc = '<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0"></head><body></body></html>'
        errs = build.check_viewport_zoom_scalability("/test/", doc)
        self.assertTrue(any("restricts maximum zoom" in e for e in errs), f"Expected maximum-scale error, got: {errs}")

    def test_viewport_zoom_scalability_rejects_sub_two_zoom_cap(self):
        doc = '<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.5"></head><body></body></html>'
        errs = build.check_viewport_zoom_scalability("/test/", doc)
        self.assertTrue(any("restricts maximum zoom to 1.5 < 2.0" in e for e in errs), f"Expected sub-2.0 zoom cap error, got: {errs}")

    def test_viewport_zoom_scalability_clean_passes(self):
        doc = '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body></body></html>'
        errs = build.check_viewport_zoom_scalability("/test/", doc)
        self.assertEqual(errs, [])


class LabsPageExplainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dest = build.DIST / "get-involved" / "labs" / "index.html"
        if not dest.exists():
            build.build()

    def test_labs_page_has_accessible_safeguards_explainer(self):
        labs_html = (build.CONTENT / "get-involved" / "labs.html").read_text(encoding="utf-8")
        self.assertIn('id="ex-lab-safeguards"', labs_html)
        self.assertIn('id="ex-lab-safeguards-title"', labs_html)
        self.assertIn('id="ex-lab-safeguards-desc"', labs_html)
        self.assertIn("SIX OPERATIONAL BOUNDARIES", labs_html)
        self.assertIn("01 · SIGNED RECEIPTS &amp; LEASES", labs_html)
        self.assertIn("02 · QUARANTINED READING", labs_html)
        self.assertIn("03 · BOUNDED HORIZONS", labs_html)
        self.assertIn("04 · HONEST CALIBRATION", labs_html)
        self.assertIn("05 · INDEPENDENT RED-TEAMS", labs_html)
        self.assertIn("06 · PORTABLE USER MEMORY", labs_html)
        self.assertIn("INVARIANT: EXPLICIT TIME-BOUNDED PERMISSION LEASES", labs_html)
        errs = build.check_explainers("get-involved/labs.html", labs_html)
        self.assertEqual(errs, [], f"check_explainers failed on labs.html: {errs}")

    def test_labs_built_page_contains_explainer(self):
        dest = build.DIST / "get-involved" / "labs" / "index.html"
        if not dest.exists():
            build.build()
        self.assertTrue(dest.exists(), f"Expected {dest} to exist")
        html = dest.read_text(encoding="utf-8")
        self.assertIn('id="ex-lab-safeguards"', html)
        self.assertIn("Signed receipts &amp; leases", html)
        self.assertIn("Quarantined reading", html)
        self.assertIn("Bounded horizons", html)
        self.assertIn("Honest calibration", html)
        self.assertIn("Independent red-teams", html)
        self.assertIn("Portable user memory", html)

    def test_labs_page_cites_attested_capability_leases(self):
        labs_html = (build.CONTENT / "get-involved" / "labs.html").read_text(encoding="utf-8")
        self.assertIn("2609.02690", labs_html)
        self.assertIn("Ding et al.", labs_html)
        self.assertIn("ACLE-MCP", labs_html)


class AboutPageWorkshopExplainerTests(unittest.TestCase):
    def test_about_page_has_accessible_workshop_explainer(self):
        about_html = (build.CONTENT / "about" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="ex-independent-workshop"', about_html)
        self.assertIn('id="ex-workshop-title"', about_html)
        self.assertIn('id="ex-workshop-desc"', about_html)
        self.assertIn("INSTITUTIONAL POSTURE · INCENTIVES &amp; CUSTODY", about_html)
        self.assertIn("01 · COMMERCIAL VENDOR", about_html)
        self.assertIn("02 · DISTANT CRITIC", about_html)
        self.assertIn("03 · CIVIC TESTING WORKSHOP (CIN)", about_html)
        errs = build.check_explainers("about/index.html", about_html)
        self.assertEqual(errs, [], f"check_explainers failed on about/index.html: {errs}")

    def test_about_built_page_contains_explainer(self):
        dest = build.DIST / "about" / "index.html"
        if not dest.exists():
            build.build()
        self.assertTrue(dest.exists(), f"Expected {dest} to exist")
        html = dest.read_text(encoding="utf-8")
        self.assertIn('id="ex-independent-workshop"', html)
        self.assertIn("01 · COMMERCIAL VENDOR", html)
        self.assertIn("02 · DISTANT CRITIC", html)
        self.assertIn("03 · CIVIC TESTING WORKSHOP (CIN)", html)


class FounderPageExplainerTests(unittest.TestCase):
    def test_founder_page_has_accessible_cellular_coordination_explainer(self):
        founder_html = (build.CONTENT / "about" / "founder.html").read_text(encoding="utf-8")
        self.assertIn('id="ex-cellular-coordination"', founder_html)
        self.assertIn('id="ex-cellular-title"', founder_html)
        self.assertIn('id="ex-cellular-desc"', founder_html)
        self.assertIn("FRAGILE CENTRAL PYRAMID", founder_html)
        self.assertIn("CELLULAR COORDINATION ACTIVE", founder_html)
        self.assertIn("LOCAL CELL A · SELECTIVE SKIN", founder_html)
        self.assertIn("VERIFIED PEER SIGNAL", founder_html)
        errs = build.check_explainers("about/founder.html", founder_html)
        self.assertEqual(errs, [], f"check_explainers failed on about/founder.html: {errs}")

    def test_founder_built_page_contains_explainer(self):
        dest = build.DIST / "about" / "founder" / "index.html"
        if not dest.exists():
            build.build()
        self.assertTrue(dest.exists(), f"Expected {dest} to exist")
        html = dest.read_text(encoding="utf-8")
        self.assertIn('id="ex-cellular-coordination"', html)
        self.assertIn("FRAGILE CENTRAL PYRAMID", html)
        self.assertIn("CELLULAR COORDINATION ACTIVE", html)
        self.assertIn("LOCAL CELL A · SELECTIVE SKIN", html)


class GetInvolvedHubPageExplainerTests(unittest.TestCase):
    def test_get_involved_hub_has_accessible_roles_cycle_explainer(self):
        hub_html = (build.CONTENT / "get-involved" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="ex-five-roles-cycle"', hub_html)
        self.assertIn('id="ex-five-roles-title"', hub_html)
        self.assertIn('id="ex-five-roles-desc"', hub_html)
        self.assertIn("THE REINFORCEMENT CYCLE", hub_html)
        self.assertIn("01 · BUILDERS", hub_html)
        self.assertIn("02 · RESEARCHERS", hub_html)
        self.assertIn("03 · LAB TEAMS", hub_html)
        self.assertIn("04 · POLICY MAKERS", hub_html)
        self.assertIn("05 · CIVIL SOCIETY", hub_html)
        self.assertIn("06 · CITIZENS", hub_html)
        errs = build.check_explainers("get-involved/index.html", hub_html)
        self.assertEqual(errs, [], f"check_explainers failed on get-involved/index.html: {errs}")

    def test_get_involved_hub_built_page_contains_explainer(self):
        dest = build.DIST / "get-involved" / "index.html"
        if not dest.exists():
            build.build()
        self.assertTrue(dest.exists(), f"Expected {dest} to exist")
        html = dest.read_text(encoding="utf-8")
        self.assertIn('id="ex-five-roles-cycle"', html)
        self.assertIn("THE REINFORCEMENT CYCLE", html)
        self.assertIn("01 · BUILDERS", html)
        self.assertIn("02 · RESEARCHERS", html)
        self.assertIn("03 · LAB TEAMS", html)
        self.assertIn("04 · POLICY MAKERS", html)
        self.assertIn("05 · CIVIL SOCIETY", html)
        self.assertIn("06 · CITIZENS", html)


class TrojanSourceAndInvisibleUnicodeTests(unittest.TestCase):
    """Tests for Trojan Source invisible character detection and zero-width bypass defense (arXiv:2111.00169; RFC 8264)."""

    def test_invisible_zero_width_space_rejected(self):
        m = meta("<p>This sentence has an invisible\u200b zero-width space inside it.</p>")
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("prohibited invisible zero-width or bidirectional override" in e for e in errs))

    def test_bidirectional_override_character_rejected(self):
        m = meta("<p>This sentence has a bidirectional \u202eoverride character.</p>")
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("prohibited invisible zero-width or bidirectional override" in e for e in errs))

    def test_zero_width_steward_gate_bypass_caught(self):
        m = meta("<p>Using Contri\u200bbution Tokens for decentralized governance.</p>")
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("steward gate, token framing" in e for e in errs))
        self.assertTrue(any("prohibited invisible zero-width or bidirectional override" in e for e in errs))

    def test_zero_width_retired_buzzword_bypass_caught(self):
        m = meta("<p>Relying on Somatic\u200b Witness for monitoring.</p>")
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("retired buzzword" in e for e in errs))
        self.assertTrue(any("prohibited invisible zero-width or bidirectional override" in e for e in errs))

    def test_zero_width_coinage_bypass_caught(self):
        m = meta("<p>An unboxed Object-\u200bCapability token without an aside.</p>")
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("research term" in e for e in errs))


class NestedInteractiveAndFieldsetAccessibilityTests(unittest.TestCase):
    """Tests for nested interactive elements and fieldset/legend structure (WCAG 2.2 SC 1.3.1, 3.3.2, 4.1.2 & HTML5 §4.1.2.1/4.10.16/17)."""

    def test_nested_anchor_inside_anchor_rejected(self):
        html = '<p><a href="/outer">Outer link <a href="/inner">Inner link</a></a></p>'
        errs = build.check_nested_interactive_elements("test.html", html)
        self.assertTrue(any("<a> is nested inside interactive <a>" in e for e in errs), f"Expected nested anchor error, got: {errs}")

    def test_nested_button_inside_anchor_rejected(self):
        html = '<p><a href="/details">Learn more <button type="button">Trigger</button></a></p>'
        errs = build.check_nested_interactive_elements("test.html", html)
        self.assertTrue(any("<button> is nested inside interactive <a>" in e for e in errs), f"Expected nested button in link error, got: {errs}")

    def test_nested_button_inside_button_rejected(self):
        html = '<button type="button">Action <button type="button">Sub-action</button></button>'
        errs = build.check_nested_interactive_elements("test.html", html)
        self.assertTrue(any("<button> is nested inside interactive <button>" in e for e in errs), f"Expected nested button in button error, got: {errs}")

    def test_nested_form_control_inside_anchor_rejected(self):
        html = '<a href="/signup">Sign up now <input type="text" name="email"></a>'
        errs = build.check_nested_interactive_elements("test.html", html)
        self.assertTrue(any("<input> form control is nested inside interactive <a>" in e for e in errs), f"Expected form control in link error, got: {errs}")

    def test_hidden_input_inside_interactive_allowed(self):
        html = '<button type="submit">Submit <input type="hidden" name="csrf" value="token"></button>'
        errs = build.check_nested_interactive_elements("test.html", html)
        self.assertEqual(errs, [])

    def test_valid_separate_interactive_elements_pass(self):
        html = '<nav><a href="/home">Home</a><a href="/research">Research</a><button type="button">Menu</button></nav>'
        errs = build.check_nested_interactive_elements("test.html", html)
        self.assertEqual(errs, [])

    def test_fieldset_without_legend_rejected(self):
        html = '<fieldset><label><input type="radio" name="plan" value="a"> A</label></fieldset>'
        errs = build.check_fieldset_and_legend_structure("test.html", html)
        self.assertTrue(any("<fieldset> missing <legend>" in e for e in errs), f"Expected missing legend error, got: {errs}")

    def test_fieldset_with_empty_legend_rejected(self):
        html = '<fieldset><legend>   </legend><label><input type="radio" name="plan" value="a"> A</label></fieldset>'
        errs = build.check_fieldset_and_legend_structure("test.html", html)
        self.assertTrue(any("<legend> is empty" in e for e in errs), f"Expected empty legend error, got: {errs}")

    def test_orphaned_legend_outside_fieldset_rejected(self):
        html = '<form><div><legend>Orphaned group title</legend><input type="text"></div></form>'
        errs = build.check_fieldset_and_legend_structure("test.html", html)
        self.assertTrue(any("<legend> is orphaned" in e for e in errs), f"Expected orphaned legend error, got: {errs}")

    def test_valid_fieldset_with_legend_passes(self):
        html = (
            '<fieldset>'
            '  <legend>Communication Preferences</legend>'
            '  <label><input type="checkbox" name="news"> Newsletter</label>'
            '</fieldset>'
        )
        errs = build.check_fieldset_and_legend_structure("test.html", html)
        self.assertEqual(errs, [])

    def test_check_page_integrates_nested_interactive_and_fieldset_guards(self):
        m = meta('<p><a href="/one"><a href="/two">Inner</a></a></p>')
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("nested inside interactive" in e for e in errs))

        m_fs = meta('<fieldset><input type="text"></fieldset>')
        m_fs["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m_fs['body']}"
        errs_fs = build.check_page(m_fs, "")
        self.assertTrue(any("<fieldset> missing <legend>" in e for e in errs_fs))


class InteractiveAndFieldsetStructureTests(unittest.TestCase):
    """Tests for nested interactive elements and fieldset/legend structure (HTML5 §4.1.2.1, WCAG 2.2 SC 4.1.2 & SC 1.3.1)."""

    def test_nested_interactive_link_in_link_rejected(self):
        body = '<p><a href="/first">Parent <a href="/second">Child</a> link</a></p>'
        errs = build.check_nested_interactive_elements("test-page", body)
        self.assertTrue(any("nested inside interactive <a>" in e for e in errs))

    def test_nested_button_in_link_rejected(self):
        body = '<p><a href="/action">Submit <button type="button">Click</button></a></p>'
        errs = build.check_nested_interactive_elements("test-page", body)
        self.assertTrue(any("nested inside interactive <a>" in e for e in errs))

    def test_nested_input_in_button_rejected(self):
        body = '<button><input type="text" name="query"></button>'
        errs = build.check_nested_interactive_elements("test-page", body)
        self.assertTrue(any("form control is nested inside interactive <button>" in e for e in errs))

    def test_hidden_input_inside_interactive_allowed(self):
        body = '<button><input type="hidden" name="token" value="abc">Click</button>'
        errs = build.check_nested_interactive_elements("test-page", body)
        self.assertEqual(errs, [])

    def test_fieldset_without_legend_rejected(self):
        body = '<fieldset><label><input type="checkbox"> Option</label></fieldset>'
        errs = build.check_fieldset_and_legend_structure("test-page", body)
        self.assertTrue(any("<fieldset> missing <legend> element" in e for e in errs))

    def test_fieldset_with_empty_legend_rejected(self):
        body = '<fieldset><legend>   </legend><label><input type="checkbox"> Option</label></fieldset>'
        errs = build.check_fieldset_and_legend_structure("test-page", body)
        self.assertTrue(any("<legend> is empty" in e for e in errs))

    def test_orphaned_legend_outside_fieldset_rejected(self):
        body = '<div><legend>Group heading</legend><p>Text</p></div>'
        errs = build.check_fieldset_and_legend_structure("test-page", body)
        self.assertTrue(any("<legend> is orphaned outside an enclosing <fieldset>" in e for e in errs))

    def test_valid_fieldset_with_legend_passes(self):
        body = '<fieldset><legend>Subscription options</legend><label><input type="checkbox"> Updates</label></fieldset>'
        errs = build.check_fieldset_and_legend_structure("test-page", body)
        self.assertEqual(errs, [])


class LabelInNameAndFocusIntegrityTests(unittest.TestCase):
    def test_valid_label_in_name_passes(self):
        body = '<button type="button" aria-label="Submit application">Submit</button>'
        errs = build.check_label_in_name("test-page", body)
        self.assertEqual(errs, [])

    def test_label_in_name_missing_word_rejected(self):
        body = '<button type="button" aria-label="Send telemetry">Submit application</button>'
        errs = build.check_label_in_name("test-page", body)
        self.assertTrue(any("WCAG 2.2 SC 2.5.3 Label in Name" in e for e in errs))

    def test_label_in_name_svg_role_button_passes(self):
        body = (
            '<svg><g id="toggle" role="button" tabindex="0" '
            'aria-label="Highlight Calibrated: Toggle calibration inspection">'
            '<rect width="100" height="30"></rect>'
            '<text>Highlight Calibrated</text></g></svg>'
        )
        errs = build.check_label_in_name("test-page", body)
        self.assertEqual(errs, [])

    def test_label_in_name_svg_role_button_missing_word_rejected(self):
        body = (
            '<svg><g id="toggle" role="button" tabindex="0" '
            'aria-label="Toggle calibration inspection">'
            '<rect width="100" height="30"></rect>'
            '<text>Highlight Calibrated</text></g></svg>'
        )
        errs = build.check_label_in_name("test-page", body)
        self.assertTrue(any("WCAG 2.2 SC 2.5.3 Label in Name" in e for e in errs))

    def test_label_in_name_exempts_icon_only_or_symbols(self):
        body = '<a href="#fnref-1" aria-label="Back to text">↩</a>'
        errs = build.check_label_in_name("test-page", body)
        self.assertEqual(errs, [])

    def test_autofocus_attribute_rejected(self):
        content = '<form><input type="text" autofocus placeholder="Search"></form>'
        errs = build.check_autofocus_attributes("test-page", content)
        self.assertTrue(any("contains 'autofocus' attribute" in e for e in errs))

    def test_autofocus_clean_content_passes(self):
        content = '<form><input type="text" placeholder="Search"></form>'
        errs = build.check_autofocus_attributes("test-page", content)
        self.assertEqual(errs, [])

    def test_aria_hidden_on_semantic_landmark_rejected(self):
        body = '<main aria-hidden="true"><p>Main content</p></main>'
        errs = build.check_aria_hidden_landmarks("test-page", body)
        self.assertTrue(any("semantic landmark <main> has aria-hidden='true'" in e for e in errs))

    def test_aria_hidden_on_nav_rejected(self):
        body = '<nav aria-hidden="true"><ul><li><a href="/">Home</a></li></ul></nav>'
        errs = build.check_aria_hidden_landmarks("test-page", body)
        self.assertTrue(any("semantic landmark <nav> has aria-hidden='true'" in e for e in errs))

    def test_clean_semantic_landmarks_pass(self):
        body = '<main><section><h2>Section heading</h2><p>Body text</p></section></main>'
        errs = build.check_aria_hidden_landmarks("test-page", body)
        self.assertEqual(errs, [])


class MultiAgentDeliberationArticleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build.build()

    def test_deliberation_conformity_article_built(self):
        # The conformity essay was merged into "When every assistant agrees" on 2026-11-09.
        dest = build.DIST / "blog" / "when-every-assistant-agrees" / "index.html"
        if not dest.exists():
            build.build()
        self.assertTrue(dest.exists(), f"Expected {dest} to exist")
        html = dest.read_text(encoding="utf-8")
        self.assertIn("When every assistant agrees", html)
        self.assertIn("TrueMAD", html)
        self.assertIn("arXiv:2610.18240", html)
        self.assertIn("arXiv:2607.01661", html)


class DetailsSummaryAndDialogAccessibilityTests(unittest.TestCase):
    """Tests for <details>/<summary> disclosure structure and <dialog> accessibility (HTML5 §4.11.1/2/4, WCAG 2.2 SC 4.1.2 & SC 1.3.1)."""

    def test_details_without_summary_rejected(self):
        body = '<details><p>Content without explicit summary disclosure label</p></details>'
        errs = build.check_details_and_summary_structure("test-page", body)
        self.assertTrue(any("<details> missing <summary> element" in e for e in errs))

    def test_details_with_summary_not_first_child_rejected(self):
        body = '<details><p>Preceding paragraph</p><summary>Late summary disclosure</summary></details>'
        errs = build.check_details_and_summary_structure("test-page", body)
        self.assertTrue(any("<summary> must be the first child element of <details>" in e for e in errs))

    def test_details_with_multiple_summaries_rejected(self):
        body = '<details><summary>Primary summary</summary><summary>Duplicate second summary</summary><p>Body</p></details>'
        errs = build.check_details_and_summary_structure("test-page", body)
        self.assertTrue(any("<details> has multiple <summary> child elements" in e for e in errs))

    def test_orphaned_summary_outside_details_rejected(self):
        body = '<section><summary>Orphaned summary label</summary><p>Some section text</p></section>'
        errs = build.check_details_and_summary_structure("test-page", body)
        self.assertTrue(any("<summary> is orphaned outside an enclosing <details> container" in e for e in errs))

    def test_empty_summary_rejected(self):
        body = '<details><summary>   </summary><p>Non-empty detail content</p></details>'
        errs = build.check_details_and_summary_structure("test-page", body)
        self.assertTrue(any("<summary> is empty" in e for e in errs))

    def test_nested_interactive_link_in_summary_rejected(self):
        body = '<details><summary>Disclose details <a href="/research">View paper</a></summary><p>Content</p></details>'
        errs = build.check_details_and_summary_structure("test-page", body)
        self.assertTrue(any("interactive <a> is nested inside disclosure <summary>" in e for e in errs))

    def test_nested_button_in_summary_rejected(self):
        body = '<details><summary>Disclose details <button type="button">Trigger</button></summary><p>Content</p></details>'
        errs = build.check_details_and_summary_structure("test-page", body)
        self.assertTrue(any("interactive <button> is nested inside disclosure <summary>" in e for e in errs))

    def test_nested_input_in_summary_rejected(self):
        body = '<details><summary>Filter <input type="text" name="filter"></summary><p>Content</p></details>'
        errs = build.check_details_and_summary_structure("test-page", body)
        self.assertTrue(any("interactive <input> is nested inside disclosure <summary>" in e for e in errs))

    def test_dialog_missing_accessible_name_rejected(self):
        body = '<dialog open><p>Modal content without name</p></dialog>'
        errs = build.check_dialog_accessibility("test-page", body)
        self.assertTrue(any("<dialog> missing accessible name" in e for e in errs))

    def test_dialog_with_aria_label_passes(self):
        body = '<dialog open aria-label="Privacy settings dialog"><p>Dialog body text</p></dialog>'
        errs = build.check_dialog_accessibility("test-page", body)
        self.assertEqual(errs, [])

    def test_dialog_with_aria_labelledby_passes(self):
        body = '<dialog open aria-labelledby="dlg-title"><h2 id="dlg-title">Export Options</h2></dialog>'
        errs = build.check_dialog_accessibility("test-page", body)
        self.assertEqual(errs, [])

    def test_valid_details_and_summary_passes(self):
        body = (
            '<aside class="for-researchers">'
            '  <details>'
            '    <summary>For researchers</summary>'
            '    <div><p>Technical implementation details and citations.</p></div>'
            '  </details>'
            '</aside>'
        )
        errs = build.check_details_and_summary_structure("test-page", body)
        self.assertEqual(errs, [])

    def test_check_page_integrates_details_summary_and_dialog_guards(self):
        m_det = meta('<details><p>No summary</p></details>')
        m_det["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m_det['body']}"
        errs_det = build.check_page(m_det, "")
        self.assertTrue(any("<details> missing <summary> element" in e for e in errs_det))

        m_dlg = meta('<dialog open><p>No label</p></dialog>')
        m_dlg["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m_dlg['body']}"
        errs_dlg = build.check_page(m_dlg, "")
        self.assertTrue(any("<dialog> missing accessible name" in e for e in errs_dlg))


class AriaIntegrityAndAttributeValidationTests(unittest.TestCase):
    def test_valid_aria_roles_and_attributes_pass(self):
        body = (
            '<div role="region" aria-label="Key insights">'
            '  <button role="button" aria-pressed="false" aria-label="Toggle details">Toggle</button>'
            '  <span aria-hidden="true">★</span>'
            '</div>'
        )
        errs = build.check_aria_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_invalid_aria_role_rejected(self):
        body = '<div role="card"><p>Card content</p></div>'
        errs = build.check_aria_integrity("test-page", body)
        self.assertTrue(any("declares invalid or unrecognized ARIA role 'card'" in e for e in errs))

    def test_invalid_aria_attribute_rejected(self):
        body = '<button aria-tooltip="Click here to save">Save</button>'
        errs = build.check_aria_integrity("test-page", body)
        self.assertTrue(any("declares invalid or unrecognized ARIA attribute 'aria-tooltip'" in e for e in errs))

    def test_empty_or_whitespace_aria_label_rejected(self):
        body1 = '<button aria-label="">Submit</button>'
        errs1 = build.check_aria_integrity("test-page", body1)
        self.assertTrue(any("has empty or whitespace-only aria-label attribute" in e for e in errs1))

        body2 = '<button aria-label="   ">Submit</button>'
        errs2 = build.check_aria_integrity("test-page", body2)
        self.assertTrue(any("has empty or whitespace-only aria-label attribute" in e for e in errs2))

    def test_broken_aria_labelledby_reference_rejected(self):
        body = '<button aria-labelledby="missing-btn-label">Submit</button>'
        errs = build.check_aria_integrity("test-page", body)
        self.assertTrue(any("aria-labelledby references non-existent element id 'missing-btn-label'" in e for e in errs))

    def test_valid_aria_labelledby_reference_passes(self):
        body = '<button aria-labelledby="real-btn-label"><span id="real-btn-label">Submit</span></button>'
        errs = build.check_aria_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_broken_aria_describedby_reference_rejected(self):
        body = '<input id="txt-input" aria-describedby="missing-help-desc">'
        errs = build.check_aria_integrity("test-page", body)
        self.assertTrue(any("aria-describedby references non-existent element id 'missing-help-desc'" in e for e in errs))

    def test_valid_aria_describedby_reference_passes(self):
        body = '<input id="txt-input" aria-describedby="help-desc"><span id="help-desc">Enter text</span>'
        errs = build.check_aria_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_broken_aria_controls_reference_rejected(self):
        body = '<button aria-controls="missing-tabpanel">Tab</button>'
        errs = build.check_aria_integrity("test-page", body)
        self.assertTrue(any("aria-controls references non-existent element id 'missing-tabpanel'" in e for e in errs))

    def test_broken_aria_details_reference_rejected(self):
        body = '<button aria-details="missing-extended-details">Inspect</button>'
        errs = build.check_aria_integrity("test-page", body)
        self.assertTrue(any("aria-details references non-existent element id 'missing-extended-details'" in e for e in errs))

    def test_valid_aria_details_reference_passes(self):
        body = '<button aria-details="ext-details">Inspect</button><div id="ext-details"><p>Deep context</p></div>'
        errs = build.check_aria_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_broken_aria_errormessage_reference_rejected(self):
        body = '<input id="email-fld" aria-invalid="true" aria-errormessage="missing-err-notice">'
        errs = build.check_aria_integrity("test-page", body)
        self.assertTrue(any("aria-errormessage references non-existent element id 'missing-err-notice'" in e for e in errs))

    def test_valid_aria_errormessage_reference_passes(self):
        body = '<input id="email-fld" aria-invalid="true" aria-errormessage="err-notice"><p id="err-notice" role="alert">Format error</p>'
        errs = build.check_aria_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_invalid_aria_current_token_rejected(self):
        body = '<a href="/blog/" aria-current="active">Blog</a>'
        errs = build.check_aria_integrity("test-page", body)
        self.assertTrue(any("declares invalid token value 'active' for 'aria-current'" in e for e in errs))

    def test_valid_aria_current_tokens_pass(self):
        body = '<nav><a href="/" aria-current="page">Home</a><a href="/steps/" aria-current="step">Step 2</a></nav>'
        errs = build.check_aria_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_invalid_aria_live_token_rejected(self):
        body = '<div role="status" aria-live="loud"><p>Update</p></div>'
        errs = build.check_aria_integrity("test-page", body)
        self.assertTrue(any("declares invalid token value 'loud' for 'aria-live'" in e for e in errs))

    def test_valid_aria_live_tokens_pass(self):
        body = '<div role="status" aria-live="polite"><p>Update</p></div>'
        errs = build.check_aria_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_invalid_aria_haspopup_token_rejected(self):
        body = '<button aria-haspopup="dropdown">Menu</button>'
        errs = build.check_aria_integrity("test-page", body)
        self.assertTrue(any("declares invalid token value 'dropdown' for 'aria-haspopup'" in e for e in errs))

    def test_invalid_aria_boolean_state_rejected(self):
        body = '<button aria-pressed="yes">Filter</button>'
        errs = build.check_aria_integrity("test-page", body)
        self.assertTrue(any("declares invalid token value 'yes' for 'aria-pressed'" in e for e in errs))

    def test_broken_label_for_reference_rejected(self):
        body = '<label for="missing-input-field">Name</label>'
        errs = build.check_aria_integrity("test-page", body)
        self.assertTrue(any("<label for='missing-input-field'> references non-existent element id 'missing-input-field'" in e for e in errs))

    def test_valid_label_for_reference_passes(self):
        body = '<label for="valid-input">Name</label><input id="valid-input">'
        errs = build.check_aria_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_check_page_integrates_aria_integrity(self):
        m = meta('<button role="invented-role">Test</button>')
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("declares invalid or unrecognized ARIA role 'invented-role'" in e for e in errs))


class SemanticTimeAndMediaAccessibilityTests(unittest.TestCase):
    """Tests for <time> semantics, <audio>/<video> controls, and <abbr> integrity (HTML5 §4.5.25/§4.8.9, WCAG 2.2 SC 1.3.1, SC 1.4.2, SC 1.2.2)."""

    def test_valid_time_element_passes(self):
        body = '<p>Published on <time datetime="2026-11-06">Nov 6, 2026</time>.</p>'
        errs = build.check_time_elements("test-page", body)
        self.assertEqual(errs, [])

    def test_missing_datetime_on_time_rejected(self):
        body = '<p>Published on <time>Nov 6, 2026</time>.</p>'
        errs = build.check_time_elements("test-page", body)
        self.assertTrue(any("<time> tag missing 'datetime' attribute" in e for e in errs))

    def test_invalid_iso_datetime_on_time_rejected(self):
        body = '<p>Published on <time datetime="11/06/2026">Nov 6, 2026</time>.</p>'
        errs = build.check_time_elements("test-page", body)
        self.assertTrue(any("is not a valid ISO 8601 date string" in e for e in errs))

    def test_empty_time_tag_content_rejected(self):
        body = '<p>Published on <time datetime="2026-11-06">   </time>.</p>'
        errs = build.check_time_elements("test-page", body)
        self.assertTrue(any("<time> tag has empty text content" in e for e in errs))

    def test_article_requires_matching_time_element(self):
        body = '<article><p>Some article text without time</p></article>'
        errs = build.check_time_elements("test-page", body, expected_article_date="2026-11-06")
        self.assertTrue(any("article missing semantic <time datetime='2026-11-06'>" in e for e in errs))

    def test_video_unmuted_autoplay_rejected(self):
        body = '<video src="/assets/media/demo.mp4" autoplay controls><track kind="captions" src="/captions.vtt"></video>'
        errs = build.check_media_accessibility("test-page", body)
        self.assertTrue(any("<video> has unmuted autoplay" in e for e in errs))

    def test_audio_unmuted_autoplay_rejected(self):
        body = '<audio src="/assets/media/brief.mp3" autoplay controls></audio>'
        errs = build.check_media_accessibility("test-page", body)
        self.assertTrue(any("<audio> has unmuted autoplay" in e for e in errs))

    def test_audio_missing_controls_rejected(self):
        body = '<audio src="/assets/media/brief.mp3"></audio>'
        errs = build.check_media_accessibility("test-page", body)
        self.assertTrue(any("<audio> missing controls attribute" in e for e in errs))

    def test_video_missing_caption_track_rejected(self):
        body = '<video src="/assets/media/demo.mp4" controls></video>'
        errs = build.check_media_accessibility("test-page", body)
        self.assertTrue(any("<video> missing <track kind='captions'>" in e for e in errs))

    def test_valid_video_with_captions_and_controls_passes(self):
        body = (
            '<video src="/assets/media/demo.mp4" controls>'
            '  <track kind="captions" src="/captions.vtt" srclang="en" label="English">'
            '</video>'
        )
        errs = build.check_media_accessibility("test-page", body)
        self.assertEqual(errs, [])

    def test_abbr_empty_title_rejected(self):
        body = '<p>Learn about <abbr title="">WCAG</abbr> standards.</p>'
        errs = build.check_abbreviation_tags("test-page", body)
        self.assertTrue(any("<abbr> has empty title attribute" in e for e in errs))

    def test_abbr_empty_text_rejected(self):
        body = '<p>Learn about <abbr title="Web Content Accessibility Guidelines"></abbr> standards.</p>'
        errs = build.check_abbreviation_tags("test-page", body)
        self.assertTrue(any("<abbr> has empty text content" in e for e in errs))

    def test_valid_abbr_passes(self):
        body = '<p>Learn about <abbr title="Web Content Accessibility Guidelines">WCAG</abbr> standards.</p>'
        errs = build.check_abbreviation_tags("test-page", body)
        self.assertEqual(errs, [])

    def test_check_page_integrates_time_and_media_checks(self):
        m = meta('<p><time>No datetime</time></p>')
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("<time> tag missing 'datetime' attribute" in e for e in errs))

        m_media = meta('<video src="test.mp4" autoplay controls><track kind="captions" src="sub.vtt"></video>')
        m_media["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m_media['body']}"
        errs_media = build.check_page(m_media, "")
        self.assertTrue(any("<video> has unmuted autoplay" in e for e in errs_media))


class SiteAuditAndLinkDimensionVerificationTests(unittest.TestCase):
    """Direct verification of image dimensions, internal link routing, and Trojan Unicode detection."""

    def test_check_img_dimensions_rejects_missing_width_or_height(self):
        doc_no_dims = '<p><img src="/assets/img/hero.jpg" alt="A wide illustration"></p>'
        errs = build.check_img_dimensions("/test/", doc_no_dims)
        self.assertTrue(any("missing width/height attributes (CLS prevention)" in e for e in errs))

        doc_width_only = '<p><img src="/assets/img/hero.jpg" width="800" alt="A wide illustration"></p>'
        errs_w = build.check_img_dimensions("/test/", doc_width_only)
        self.assertTrue(any("missing width/height attributes (CLS prevention)" in e for e in errs_w))

    def test_check_img_dimensions_passes_with_explicit_dimensions(self):
        doc_valid = '<p><img src="/assets/img/hero.jpg" width="800" height="450" alt="A wide illustration"></p>'
        errs = build.check_img_dimensions("/test/", doc_valid)
        self.assertEqual(errs, [])

    def test_check_links_rejects_broken_internal_route(self):
        pages = {
            "/page-a/": '<p><a href="/page-b/">Valid</a> and <a href="/nonexistent-route/">Broken</a></p>',
            "/page-b/": '<p>Content</p>',
        }
        errs = build.check_links(pages)
        self.assertTrue(any("broken internal link /nonexistent-route/" in e for e in errs))
        self.assertFalse(any("broken internal link /page-b/" in e for e in errs))

    def test_check_links_rejects_missing_asset(self):
        pages = {
            "/page-a/": '<p><img src="/assets/img/definitely-missing-graphic-999.png" width="100" height="100" alt="Missing"></p>',
        }
        errs = build.check_links(pages)
        self.assertTrue(any("missing asset /assets/img/definitely-missing-graphic-999.png" in e for e in errs))

    def test_check_links_accepts_valid_routes_and_special_files(self):
        pages = {
            "/page-a/": '<p><a href="/blog/feed.xml">Feed</a> <a href="/sitemap.xml">Sitemap</a> <a href="/robots.txt">Robots</a></p>',
        }
        errs = build.check_links(pages)
        self.assertEqual(errs, [])

    def test_check_invisible_characters_directly_rejects_trojan_codepoints(self):
        # Zero-width space (U+200B)
        errs_zws = build.check_invisible_characters("doc.html", "Hello\u200BWorld")
        self.assertTrue(any("prohibited invisible zero-width or bidirectional override characters" in e for e in errs_zws))

        # Byte order mark (U+FEFF)
        errs_bom = build.check_invisible_characters("doc.html", "Prefix\uFEFFSuffix")
        self.assertTrue(any("prohibited invisible zero-width or bidirectional override characters" in e for e in errs_bom))

        # Soft hyphen (U+00AD)
        errs_shy = build.check_invisible_characters("doc.html", "Dis\u00ADcretion")
        self.assertTrue(any("prohibited invisible zero-width or bidirectional override characters" in e for e in errs_shy))

        # Right-to-left override (U+202E)
        errs_bidi = build.check_invisible_characters("doc.html", "Admin\u202EUser")
        self.assertTrue(any("prohibited invisible zero-width or bidirectional override characters" in e for e in errs_bidi))

    def test_check_invisible_characters_passes_clean_unicode(self):
        clean_text = "<p>Standard text with curly quotes \u201c\u201d, em-dash \u2014, and accented \u00e9.</p>"
        self.assertEqual(build.check_invisible_characters("clean.html", clean_text), [])


class ProgressAndMeterAccessibilityTests(unittest.TestCase):
    """Verify accessible names and numeric validity for <progress> and <meter> (HTML5 §4.10.13/14, WCAG 2.2 SC 4.1.2 & SC 1.3.1)."""

    def test_progress_missing_accessible_name_rejected(self):
        body = '<p>Processing: <progress value="50" max="100"></progress></p>'
        errs = build.check_progress_and_meter_accessibility("test.html", body)
        self.assertTrue(any("missing accessible name" in e for e in errs))

    def test_progress_with_aria_label_passes(self):
        body = '<p><progress aria-label="Task synchronization progress" value="75" max="100"></progress></p>'
        self.assertEqual(build.check_progress_and_meter_accessibility("test.html", body), [])

    def test_progress_with_label_for_passes(self):
        body = '<p><label for="pr-1">Import progress</label><progress id="pr-1" value="0.5"></progress></p>'
        self.assertEqual(build.check_progress_and_meter_accessibility("test.html", body), [])

    def test_progress_negative_value_rejected(self):
        body = '<p><progress aria-label="Progress" value="-10" max="100"></progress></p>'
        errs = build.check_progress_and_meter_accessibility("test.html", body)
        self.assertTrue(any("cannot be negative" in e for e in errs))

    def test_progress_value_exceeding_max_rejected(self):
        body = '<p><progress aria-label="Progress" value="120" max="100"></progress></p>'
        errs = build.check_progress_and_meter_accessibility("test.html", body)
        self.assertTrue(any("cannot exceed max" in e for e in errs))

    def test_progress_value_exceeding_default_max_rejected(self):
        body = '<p><progress aria-label="Progress" value="1.5"></progress></p>'
        errs = build.check_progress_and_meter_accessibility("test.html", body)
        self.assertTrue(any("cannot exceed default max (1.0)" in e for e in errs))

    def test_progress_invalid_number_rejected(self):
        body = '<p><progress aria-label="Progress" value="fast" max="100"></progress></p>'
        errs = build.check_progress_and_meter_accessibility("test.html", body)
        self.assertTrue(any("must be a valid number" in e for e in errs))

    def test_meter_missing_accessible_name_rejected(self):
        body = '<p>Disk space: <meter value="60" min="0" max="100"></meter></p>'
        errs = build.check_progress_and_meter_accessibility("test.html", body)
        self.assertTrue(any("missing accessible name" in e for e in errs))

    def test_meter_missing_value_rejected(self):
        body = '<p><meter aria-label="Disk space" min="0" max="100"></meter></p>'
        errs = build.check_progress_and_meter_accessibility("test.html", body)
        self.assertTrue(any("missing required 'value' attribute" in e for e in errs))

    def test_meter_out_of_bounds_rejected(self):
        body = '<p><meter aria-label="Disk space" min="10" max="50" value="70"></meter></p>'
        errs = build.check_progress_and_meter_accessibility("test.html", body)
        self.assertTrue(any("out of bounds" in e for e in errs))

    def test_meter_min_greater_than_max_rejected(self):
        body = '<p><meter aria-label="Temperature" min="100" max="50" value="60"></meter></p>'
        errs = build.check_progress_and_meter_accessibility("test.html", body)
        self.assertTrue(any("must be strictly less than max" in e for e in errs))

    def test_meter_low_greater_than_high_rejected(self):
        body = '<p><meter aria-label="Score" min="0" max="100" low="80" high="20" value="50"></meter></p>'
        errs = build.check_progress_and_meter_accessibility("test.html", body)
        self.assertTrue(any("low (80.0) cannot exceed high (20.0" in e for e in errs))

    def test_meter_valid_passes(self):
        body = '<p><meter aria-label="Bandwidth utilization" min="0" max="100" low="25" high="75" optimum="50" value="65"></meter></p>'
        self.assertEqual(build.check_progress_and_meter_accessibility("test.html", body), [])


class FormAutocompleteAttributeValidationTests(unittest.TestCase):
    """Verify form control autocomplete attribute conformance to WHATWG HTML §4.10.18.7 and WCAG 2.2 SC 1.3.5."""

    def test_empty_or_whitespace_autocomplete_rejected(self):
        body = '<p><input type="text" aria-label="Full name" autocomplete=""></p>'
        errs = build.check_form_autocomplete_attributes("test.html", body)
        self.assertTrue(any("cannot be empty or whitespace-only" in e for e in errs))

        body_ws = '<p><input type="text" aria-label="Full name" autocomplete="   "></p>'
        errs_ws = build.check_form_autocomplete_attributes("test.html", body_ws)
        self.assertTrue(any("cannot be empty or whitespace-only" in e for e in errs_ws))

    def test_on_and_off_tokens_pass(self):
        body_on = '<p><input type="text" aria-label="Search query" autocomplete="on"></p>'
        body_off = '<p><input type="password" aria-label="Security key" autocomplete="off"></p>'
        self.assertEqual(build.check_form_autocomplete_attributes("test.html", body_on), [])
        self.assertEqual(build.check_form_autocomplete_attributes("test.html", body_off), [])

    def test_standard_autofill_field_names_pass(self):
        body = (
            '<p><input type="text" aria-label="Full Name" autocomplete="name">'
            '<input type="text" aria-label="First Name" autocomplete="given-name">'
            '<input type="text" aria-label="Family Name" autocomplete="family-name">'
            '<input type="email" aria-label="Email" autocomplete="email">'
            '<input type="text" aria-label="Username" autocomplete="username"></p>'
        )
        self.assertEqual(build.check_form_autocomplete_attributes("test.html", body), [])

    def test_section_prefix_and_address_scope_pass(self):
        body = (
            '<p><input type="text" aria-label="Shipping Address" '
            'autocomplete="section-billing shipping street-address"></p>'
        )
        self.assertEqual(build.check_form_autocomplete_attributes("test.html", body), [])

    def test_malformed_section_prefix_rejected(self):
        body = '<p><input type="text" aria-label="Address" autocomplete="section- street-address"></p>'
        errs = build.check_form_autocomplete_attributes("test.html", body)
        self.assertTrue(any("section- prefix requires a non-empty alphanumeric section name" in e for e in errs))

    def test_contact_type_valid_for_contact_fields(self):
        body = (
            '<p><input type="tel" aria-label="Home Phone" autocomplete="home tel">'
            '<input type="email" aria-label="Work Email" autocomplete="work email"></p>'
        )
        self.assertEqual(build.check_form_autocomplete_attributes("test.html", body), [])

    def test_contact_type_invalid_for_non_contact_field_rejected(self):
        body = '<p><input type="text" aria-label="Home Address" autocomplete="home street-address"></p>'
        errs = build.check_form_autocomplete_attributes("test.html", body)
        self.assertTrue(any("contact type 'home' is only allowed before contact fields" in e for e in errs))

    def test_common_autofill_typos_caught_with_suggestions(self):
        body_fn = '<p><input type="text" aria-label="First Name" autocomplete="first-name"></p>'
        errs_fn = build.check_form_autocomplete_attributes("test.html", body_fn)
        self.assertTrue(any("did you mean 'given-name'?" in e for e in errs_fn))

        body_ln = '<p><input type="text" aria-label="Last Name" autocomplete="last-name"></p>'
        errs_ln = build.check_form_autocomplete_attributes("test.html", body_ln)
        self.assertTrue(any("did you mean 'family-name'?" in e for e in errs_ln))

        body_zip = '<p><input type="text" aria-label="Zip Code" autocomplete="zip"></p>'
        errs_zip = build.check_form_autocomplete_attributes("test.html", body_zip)
        self.assertTrue(any("did you mean 'postal-code'?" in e for e in errs_zip))

        body_phone = '<p><input type="tel" aria-label="Phone" autocomplete="phone"></p>'
        errs_phone = build.check_form_autocomplete_attributes("test.html", body_phone)
        self.assertTrue(any("did you mean 'tel'?" in e for e in errs_phone))

    def test_duplicate_tokens_rejected(self):
        body = '<p><input type="email" aria-label="Email" autocomplete="email email"></p>'
        errs = build.check_form_autocomplete_attributes("test.html", body)
        self.assertTrue(any("contains duplicate token(s)" in e for e in errs))

    def test_missing_core_field_name_rejected(self):
        body = '<p><input type="text" aria-label="Shipping" autocomplete="shipping"></p>'
        errs = build.check_form_autocomplete_attributes("test.html", body)
        self.assertTrue(any("missing required core autofill field name" in e for e in errs))

    def test_webauthn_token_valid_for_credentials_rejected_for_others(self):
        body_pass = '<p><input type="password" aria-label="Current Password" autocomplete="current-password webauthn"></p>'
        self.assertEqual(build.check_form_autocomplete_attributes("test.html", body_pass), [])

        body_email = '<p><input type="email" aria-label="Email" autocomplete="email webauthn"></p>'
        errs_email = build.check_form_autocomplete_attributes("test.html", body_email)
        self.assertTrue(any("'webauthn' autocomplete token is only valid with credential fields" in e for e in errs_email))

    def test_incompatible_input_type_rejected(self):
        body = '<p><input type="email" aria-label="Email" autocomplete="tel"></p>'
        errs = build.check_form_autocomplete_attributes("test.html", body)
        self.assertTrue(any("has incompatible autocomplete field 'tel'" in e for e in errs))

    def test_textarea_and_select_supported(self):
        body = (
            '<p><textarea aria-label="Street Address" autocomplete="street-address"></textarea>'
            '<select aria-label="Country" autocomplete="country"><option value="US">US</option></select></p>'
        )
        self.assertEqual(build.check_form_autocomplete_attributes("test.html", body), [])

    def test_check_page_integrates_autocomplete_validation(self):
        meta = {
            "title": "Account Settings",
            "description": "Preferences and account settings page for registered participants.",
            "reader": "All registered network participants.",
            "takeaway": "Understand your account settings and credentials.",
            "template": "page",
            "section": "labs",
            "src": build.CONTENT / "test-autocomplete.html",
            "body": '<p><input type="text" aria-label="First Name" autocomplete="first-name"></p>',
            "raw": "---\ntitle: Account Settings\n---",
        }
        errs = build.check_page(meta, "")
        self.assertTrue(any("invalid autocomplete field name 'first-name'" in e for e in errs))


class ClientSeparationAndResearchBadgeTests(unittest.TestCase):
    def test_client_link_allowed_on_shared_horizon(self):
        pages = {
            "/labs/shared-horizon/": '<p><a href="https://horizon.cintnet.org/">Play Shared Horizon</a></p>',
            "/get-involved/builders/": '<p><a href="https://horizon.cintnet.org/atlas">Explore Atlas</a></p>',
        }
        self.assertEqual(build.check_client_links(pages), [])

    def test_client_link_rejected_on_about_or_blog(self):
        pages = {
            "/about/": '<p><a href="https://horizon.cintnet.org/">Shared Horizon Client</a></p>',
            "/blog/why-trust-multiplies/": '<p><a href="http://horizon.cintnet.org/game">Game Client</a></p>',
        }
        errs = build.check_client_links(pages)
        self.assertEqual(len(errs), 2)
        self.assertTrue(all("restricted to /labs/shared-horizon and /get-involved pages" in e for e in errs))

    def test_research_page_missing_badges_rejected(self):
        meta = {"template": "research", "title": "Research"}
        body_no_est = '<p><span class="badge badge-prop">Proposal</span><span class="badge badge-open">Open</span></p>'
        errs = build.check_research_status_badges("research.html", meta, body_no_est)
        self.assertTrue(any("missing required status badge 'badge-est'" in e for e in errs))

        body_no_prop = '<p><span class="badge badge-est">Established</span><span class="badge badge-open">Open</span></p>'
        errs_prop = build.check_research_status_badges("research.html", meta, body_no_prop)
        self.assertTrue(any("missing required status badge 'badge-prop'" in e for e in errs_prop))

        body_no_open = '<p><span class="badge badge-est">Established</span><span class="badge badge-prop">Proposal</span></p>'
        errs_open = build.check_research_status_badges("research.html", meta, body_no_open)
        self.assertTrue(any("missing required status badge 'badge-open'" in e for e in errs_open))

    def test_research_page_with_all_three_badges_passes(self):
        meta = {"template": "research", "title": "Research"}
        body_clean = '<p><span class="badge badge-est">Established</span><span class="badge badge-prop">Proposal</span><span class="badge badge-open">Open</span></p>'
        self.assertEqual(build.check_research_status_badges("research.html", meta, body_clean), [])


class InteractiveExplainerAndLinkPurposeAccessibilityTests(unittest.TestCase):
    def test_interactive_explainer_custom_button_missing_tabindex_rejected(self):
        body = '<figure class="explainer"><g role="button" aria-label="Toggle node" aria-pressed="false"><rect/></g></figure>'
        errs = build.check_interactive_explainer_accessibility("test.html", body)
        self.assertTrue(any("missing keyboard focusability 'tabindex=\"0\"'" in e for e in errs))

    def test_interactive_explainer_custom_button_missing_accessible_name_rejected(self):
        body = '<figure class="explainer"><g role="button" tabindex="0" aria-pressed="false"><rect/></g></figure>'
        errs = build.check_interactive_explainer_accessibility("test.html", body)
        self.assertTrue(any("missing accessible name" in e for e in errs))

    def test_interactive_explainer_custom_button_missing_state_rejected(self):
        body = '<figure class="explainer"><g role="button" tabindex="0" aria-label="Activate node"><rect/></g></figure>'
        errs = build.check_interactive_explainer_accessibility("test.html", body)
        self.assertTrue(any("missing state attribute" in e for e in errs))

    def test_interactive_explainer_valid_custom_button_passes(self):
        body = '<figure class="explainer"><g role="button" tabindex="0" aria-label="Toggle node" aria-pressed="false"><rect/></g></figure>'
        self.assertEqual(build.check_interactive_explainer_accessibility("test.html", body), [])

    def test_generic_link_phrase_without_aria_label_rejected(self):
        body = '<p>To find out more about our protocol, <a href="/research/">read more</a> or <a href="/about/">click here</a>.</p>'
        errs = build.check_link_purpose_and_generic_text("test.html", body)
        self.assertEqual(len(errs), 2)
        self.assertTrue(all("requires 'aria-label' or 'aria-labelledby' for context" in e for e in errs))

    def test_generic_link_phrase_with_aria_label_passes(self):
        body = '<p>To find out more, <a href="/research/" aria-label="Read more about our research protocol">read more</a>.</p>'
        self.assertEqual(build.check_link_purpose_and_generic_text("test.html", body), [])

    def test_descriptive_link_text_passes(self):
        body = '<p>Explore our <a href="/research/">research standards and verified drafts</a>.</p>'
        self.assertEqual(build.check_link_purpose_and_generic_text("test.html", body), [])


class MathAndFigcaptionAccessibilityTests(unittest.TestCase):
    def test_math_without_accessible_representation_rejected(self):
        body = '<p>Energy formula: <math><mi>E</mi><mo>=</mo><mi>m</mi><msup><mi>c</mi><mn>2</mn></msup></math></p>'
        errs = build.check_math_accessibility("test.html", body)
        self.assertTrue(any("missing accessible alternative" in e for e in errs))

    def test_math_with_alttext_passes(self):
        body = '<p>Energy formula: <math alttext="E equals m c squared"><mi>E</mi><mo>=</mo><mi>m</mi><msup><mi>c</mi><mn>2</mn></msup></math></p>'
        self.assertEqual(build.check_math_accessibility("test.html", body), [])

    def test_math_with_annotation_passes(self):
        body = '<p>Formula: <math><semantics><mrow><mi>x</mi></mrow><annotation encoding="application/x-tex">x</annotation></semantics></math></p>'
        self.assertEqual(build.check_math_accessibility("test.html", body), [])

    def test_orphaned_figcaption_rejected(self):
        body = '<div><p>Paragraph</p><figcaption>Orphaned caption</figcaption></div>'
        errs = build.check_figcaption_structure("test.html", body)
        self.assertTrue(any("orphaned <figcaption> found outside <figure>" in e for e in errs))

    def test_multiple_figcaptions_in_figure_rejected(self):
        body = '<figure><img src="/assets/img/chart.jpg" alt="Chart"><figcaption>First caption</figcaption><figcaption>Second caption</figcaption></figure>'
        errs = build.check_figcaption_structure("test.html", body)
        self.assertTrue(any("contains multiple <figcaption> elements" in e for e in errs))

    def test_empty_figcaption_rejected(self):
        body = '<figure><img src="/assets/img/chart.jpg" alt="Chart"><figcaption>   </figcaption></figure>'
        errs = build.check_figcaption_structure("test.html", body)
        self.assertTrue(any("must not be empty or whitespace-only" in e for e in errs))

    def test_valid_figure_and_figcaption_passes(self):
        body = '<figure><img src="/assets/img/chart.jpg" alt="Chart"><figcaption>Descriptive caption</figcaption></figure>'
        self.assertEqual(build.check_figcaption_structure("test.html", body), [])


class ButtonAccessibleNameTests(unittest.TestCase):
    def test_empty_button_without_accessible_name_rejected(self):
        body = '<p><button class="icon-toggle"></button></p>'
        errs = build.check_button_accessible_names("test.html", body)
        self.assertTrue(any("<button> missing accessible name" in e for e in errs))

    def test_button_with_text_passes(self):
        body = '<p><button type="button">Submit Feedback</button></p>'
        self.assertEqual(build.check_button_accessible_names("test.html", body), [])

    def test_button_with_aria_label_passes(self):
        body = '<p><button type="button" aria-label="Close dialog"></button></p>'
        self.assertEqual(build.check_button_accessible_names("test.html", body), [])

    def test_button_with_accessible_icon_passes(self):
        body = '<p><button type="button"><svg aria-label="Search icon"><circle/></svg></button></p>'
        self.assertEqual(build.check_button_accessible_names("test.html", body), [])


class LiveRegionIntegrityTests(unittest.TestCase):
    def test_invalid_aria_live_token_rejected(self):
        body = '<div aria-live="aggressive">Dynamic notice</div>'
        errs = build.check_live_region_integrity("test.html", body)
        self.assertTrue(any("invalid aria-live='aggressive'" in e for e in errs))

    def test_invalid_aria_atomic_token_rejected(self):
        body = '<div aria-live="polite" aria-atomic="yes">Dynamic notice</div>'
        errs = build.check_live_region_integrity("test.html", body)
        self.assertTrue(any("invalid aria-atomic='yes'" in e for e in errs))

    def test_alert_with_live_off_rejected(self):
        body = '<div role="alert" aria-live="off">Silent critical warning</div>'
        errs = build.check_live_region_integrity("test.html", body)
        self.assertTrue(any("cannot declare aria-live='off'" in e for e in errs))

    def test_status_with_live_assertive_rejected(self):
        body = '<div role="status" aria-live="assertive">Status update</div>'
        errs = build.check_live_region_integrity("test.html", body)
        self.assertTrue(any("should not declare aria-live='assertive'" in e for e in errs))

    def test_live_container_with_autofocus_rejected(self):
        body = '<div aria-live="polite"><p>Loading</p><input type="text" autofocus></div>'
        errs = build.check_live_region_integrity("test.html", body)
        self.assertTrue(any("must not contain autofocus elements" in e for e in errs))

    def test_valid_live_regions_pass(self):
        body = '<div aria-live="polite" aria-atomic="true"><p>Feed updated</p></div><div role="alert"><p>Warning</p></div>'
        self.assertEqual(build.check_live_region_integrity("test.html", body), [])


class DisabledAttributeIntegrityTests(unittest.TestCase):
    def test_anchor_with_disabled_attribute_rejected(self):
        body = '<p>Check <a href="/research/" disabled>our research</a>.</p>'
        errs = build.check_disabled_attribute_integrity("test.html", body)
        self.assertTrue(any("<a> declares non-standard 'disabled' attribute" in e for e in errs))

    def test_aria_disabled_with_active_pressed_rejected(self):
        body = '<p><button type="button" aria-disabled="true" aria-pressed="true">Mute</button></p>'
        errs = build.check_disabled_attribute_integrity("test.html", body)
        self.assertTrue(any("declares aria-disabled='true' but also active aria-pressed='true'" in e for e in errs))

    def test_aria_disabled_with_active_expanded_rejected(self):
        body = '<p><button type="button" aria-disabled="true" aria-expanded="true">Details</button></p>'
        errs = build.check_disabled_attribute_integrity("test.html", body)
        self.assertTrue(any("declares aria-disabled='true' but also active aria-expanded='true'" in e for e in errs))

    def test_valid_disabled_and_aria_disabled_pass(self):
        body = '<p><button type="button" disabled>Native disabled</button><button type="button" aria-disabled="true" tabindex="-1">ARIA disabled</button></p>'
        self.assertEqual(build.check_disabled_attribute_integrity("test.html", body), [])

    def test_placeholder_anchor_without_href_passes(self):
        body = '<p>Upcoming feature: <a>Coming soon in release 2</a>.</p>'
        self.assertEqual(build.check_disabled_attribute_integrity("test.html", body), [])


class SvgAccessibilityAndDecorativeIntegrityTests(unittest.TestCase):
    def test_svg_missing_accessible_name_or_decorative_attribute_rejected(self):
        body = '<figure><svg><circle cx="10" cy="10" r="5"/></svg></figure>'
        errs = build.check_svg_accessibility("test.html", body)
        self.assertTrue(any("<svg> missing accessible name" in e for e in errs))

    def test_svg_with_empty_title_rejected(self):
        body = '<figure><svg><title>   </title><circle cx="10" cy="10" r="5"/></svg></figure>'
        errs = build.check_svg_accessibility("test.html", body)
        self.assertTrue(any("<svg> contains empty or whitespace-only <title> tag" in e for e in errs))

    def test_decorative_svg_with_focusable_element_rejected(self):
        body = '<figure><svg aria-hidden="true"><g role="button" tabindex="0" aria-label="Action"><rect width="20" height="20"/></g></svg></figure>'
        errs = build.check_svg_accessibility("test.html", body)
        self.assertTrue(any("decorative <svg> (aria-hidden='true' or role='presentation') contains focusable interactive element(s)" in e for e in errs))

    def test_decorative_svg_clean_passes(self):
        body = '<figure><svg aria-hidden="true"><path d="M0 0 L10 10"/></svg></figure>'
        self.assertEqual(build.check_svg_accessibility("test.html", body), [])

    def test_accessible_svg_with_aria_label_passes(self):
        body = '<figure><svg role="img" aria-label="Network topology map"><path d="M0 0 L10 10"/></svg></figure>'
        self.assertEqual(build.check_svg_accessibility("test.html", body), [])

    def test_accessible_svg_with_title_passes(self):
        body = '<figure><svg role="img"><title>Workflow coordination chart</title><rect width="10" height="10"/></svg></figure>'
        self.assertEqual(build.check_svg_accessibility("test.html", body), [])


class HtmlLangAndCharsetIntegrityTests(unittest.TestCase):
    def test_valid_html_shell_passes(self):
        doc = """<!doctype html>
<html lang="en-CA">
<head>
<meta charset="utf-8">
<title>Valid Page</title>
</head>
<body>
<p>Hello world in English</p>
<p lang="fr">Bonjour le monde</p>
</body>
</html>"""
        self.assertEqual(build.check_html_lang_and_charset("/test", doc), [])

    def test_missing_html_lang_rejected(self):
        doc = '<!doctype html><html><head><meta charset="utf-8"><title>T</title></head><body><p>Text</p></body></html>'
        errs = build.check_html_lang_and_charset("/test", doc)
        self.assertTrue(any("<html> root element missing or empty 'lang' attribute" in e for e in errs))

    def test_empty_html_lang_rejected(self):
        doc = '<!doctype html><html lang="  "><head><meta charset="utf-8"><title>T</title></head><body><p>Text</p></body></html>'
        errs = build.check_html_lang_and_charset("/test", doc)
        self.assertTrue(any("<html> root element missing or empty 'lang' attribute" in e for e in errs))

    def test_invalid_bcp47_lang_code_rejected(self):
        doc = '<!doctype html><html lang="english"><head><meta charset="utf-8"><title>T</title></head><body><p>Text</p></body></html>'
        errs = build.check_html_lang_and_charset("/test", doc)
        self.assertTrue(any("declares invalid BCP 47 language code 'english'" in e for e in errs))

    def test_invalid_html_dir_rejected(self):
        doc = '<!doctype html><html lang="en" dir="upwards"><head><meta charset="utf-8"><title>T</title></head><body><p>Text</p></body></html>'
        errs = build.check_html_lang_and_charset("/test", doc)
        self.assertTrue(any("declares invalid 'dir' attribute 'upwards'" in e for e in errs))

    def test_missing_early_meta_charset_rejected(self):
        # Charset missing entirely
        doc = '<!doctype html><html lang="en"><head><title>T</title></head><body><p>Text</p></body></html>'
        errs = build.check_html_lang_and_charset("/test", doc)
        self.assertTrue(any("missing <meta charset=\"utf-8\"> within the first 1024 bytes" in e for e in errs))

    def test_meta_charset_beyond_1024_bytes_rejected(self):
        # 1100 bytes of filler before meta charset
        filler = "<!-- " + ("x" * 1100) + " -->\n"
        doc = f'<!doctype html><html lang="en"><head>{filler}<meta charset="utf-8"><title>T</title></head><body><p>Text</p></body></html>'
        errs = build.check_html_lang_and_charset("/test", doc)
        self.assertTrue(any("missing <meta charset=\"utf-8\"> within the first 1024 bytes" in e for e in errs))

    def test_non_utf8_meta_charset_rejected(self):
        doc = '<!doctype html><html lang="en"><head><meta charset="iso-8859-1"><title>T</title></head><body><p>Text</p></body></html>'
        errs = build.check_html_lang_and_charset("/test", doc)
        self.assertTrue(any("declares non-UTF-8 charset 'iso-8859-1'" in e for e in errs))

    def test_invalid_inline_lang_subtag_rejected(self):
        doc = '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>T</title></head><body><p lang="invalid_code!">Text</p></body></html>'
        errs = build.check_html_lang_and_charset("/test", doc)
        self.assertTrue(any("declares invalid BCP 47 language code 'invalid_code!'" in e for e in errs))

    def test_empty_inline_lang_rejected(self):
        doc = '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>T</title></head><body><p lang="   ">Text</p></body></html>'
        errs = build.check_html_lang_and_charset("/test", doc)
        self.assertTrue(any("specifies empty inline 'lang' attribute" in e for e in errs))

    def test_invalid_inline_dir_rejected(self):
        doc = '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>T</title></head><body><blockquote dir="diagonal">Quote</blockquote></body></html>'
        errs = build.check_html_lang_and_charset("/test", doc)
        self.assertTrue(any("declares invalid inline 'dir' attribute 'diagonal'" in e for e in errs))


class AriaExtendedEnumeratedAndTokenListTests(unittest.TestCase):
    def test_valid_aria_relevant_tokens_pass(self):
        body = '<div aria-live="polite" aria-relevant="additions text">Live updates</div>'
        self.assertEqual(build.check_aria_integrity("test.html", body), [])

    def test_invalid_aria_relevant_token_rejected(self):
        body = '<div aria-live="polite" aria-relevant="additions bogus">Live updates</div>'
        errs = build.check_aria_integrity("test.html", body)
        self.assertTrue(any("declares invalid token 'bogus' in 'aria-relevant'" in e for e in errs))

    def test_empty_aria_relevant_rejected(self):
        body = '<div aria-live="polite" aria-relevant="   ">Live updates</div>'
        errs = build.check_aria_integrity("test.html", body)
        self.assertTrue(any("specifies empty 'aria-relevant' attribute" in e for e in errs))

    def test_valid_aria_dropeffect_tokens_pass(self):
        body = '<div aria-dropeffect="copy execute">Drop zone</div>'
        self.assertEqual(build.check_aria_integrity("test.html", body), [])

    def test_invalid_aria_dropeffect_token_rejected(self):
        body = '<div aria-dropeffect="copy invalid_drop">Drop zone</div>'
        errs = build.check_aria_integrity("test.html", body)
        self.assertTrue(any("declares invalid token 'invalid_drop' in 'aria-dropeffect'" in e for e in errs))

    def test_valid_aria_grabbed_pass(self):
        body = '<div aria-grabbed="true">Draggable item</div>'
        self.assertEqual(build.check_aria_integrity("test.html", body), [])

    def test_invalid_aria_grabbed_rejected(self):
        body = '<div aria-grabbed="yes">Draggable item</div>'
        errs = build.check_aria_integrity("test.html", body)
        self.assertTrue(any("declares invalid token value 'yes' for 'aria-grabbed'" in e for e in errs))


class TargetBlankAccessibilityTests(unittest.TestCase):
    """Tests for new window/tab notifications on target='_blank' links (WCAG 2.2 Technique G201 / H83 & SC 3.2.5)."""

    def test_regular_link_passes_without_notice(self):
        body = '<p><a href="/blog/why-trust-multiplies/">Read our essay</a></p>'
        self.assertEqual(build.check_target_blank_accessibility("test-page", body), [])

    def test_valid_target_blank_with_aria_label_passes(self):
        body = '<p><a href="https://example.org" target="_blank" rel="noopener" aria-label="Visit external registry (opens in new tab)">Registry</a></p>'
        self.assertEqual(build.check_target_blank_accessibility("test-page", body), [])

    def test_valid_target_blank_with_visible_text_passes(self):
        body = '<p><a href="https://example.org" target="_blank" rel="noopener">Documentation (opens in new window)</a></p>'
        self.assertEqual(build.check_target_blank_accessibility("test-page", body), [])

    def test_valid_target_blank_with_img_alt_passes(self):
        body = '<p><a href="https://example.org" target="_blank" rel="noopener"><img src="/assets/img/logo.jpg" alt="Partner Logo (new tab)"></a></p>'
        self.assertEqual(build.check_target_blank_accessibility("test-page", body), [])

    def test_target_blank_without_notice_rejected(self):
        body = '<p><a href="https://example.org" target="_blank" rel="noopener">Silent external link</a></p>'
        errs = build.check_target_blank_accessibility("test-page", body)
        self.assertTrue(any("missing explicit new window/tab notification" in e for e in errs))


class OutputAndDatalistIntegrityTests(unittest.TestCase):
    """Tests for <output> calculation elements and <datalist> suggestion controls (HTML5 §4.10.18, §4.10.19, WCAG 2.2 SC 4.1.2 & SC 1.3.1)."""

    def test_valid_output_element_passes(self):
        body = '<input id="a" type="number"><input id="b" type="number"><output for="a b" id="res">0</output>'
        self.assertEqual(build.check_output_and_datalist_integrity("test-page", body), [])

    def test_output_with_role_presentation_rejected(self):
        body = '<output role="presentation">Result</output>'
        errs = build.check_output_and_datalist_integrity("test-page", body)
        self.assertTrue(any("<output> cannot declare role='presentation'" in e for e in errs))

    def test_output_with_aria_live_off_rejected(self):
        body = '<output aria-live="off">Result</output>'
        errs = build.check_output_and_datalist_integrity("test-page", body)
        self.assertTrue(any("<output> cannot declare aria-live='off'" in e for e in errs))

    def test_output_with_dangling_for_reference_rejected(self):
        body = '<output for="missing-input-id">Calculation</output>'
        errs = build.check_output_and_datalist_integrity("test-page", body)
        self.assertTrue(any("references non-existent element id 'missing-input-id'" in e for e in errs))

    def test_output_with_empty_for_rejected(self):
        body = '<output for="   ">Calculation</output>'
        errs = build.check_output_and_datalist_integrity("test-page", body)
        self.assertTrue(any("<output> 'for' attribute cannot be empty" in e for e in errs))

    def test_valid_datalist_and_input_passes(self):
        body = '<input list="role-options" id="user-role"><datalist id="role-options"><option value="Citizen"><option value="Researcher"></datalist>'
        self.assertEqual(build.check_output_and_datalist_integrity("test-page", body), [])

    def test_datalist_missing_id_rejected(self):
        body = '<datalist><option value="Test"></datalist>'
        errs = build.check_output_and_datalist_integrity("test-page", body)
        self.assertTrue(any("<datalist> missing required 'id' attribute" in e for e in errs))

    def test_datalist_option_empty_value_and_text_rejected(self):
        body = '<datalist id="opts"><option value=""></datalist>'
        errs = build.check_output_and_datalist_integrity("test-page", body)
        self.assertTrue(any("<datalist> <option> has empty value and empty text" in e for e in errs))

    def test_input_list_dangling_id_rejected(self):
        body = '<input list="missing-datalist-id">'
        errs = build.check_output_and_datalist_integrity("test-page", body)
        self.assertTrue(any("references non-existent id 'missing-datalist-id'" in e for e in errs))

    def test_input_list_targeting_non_datalist_rejected(self):
        body = '<input list="not-a-datalist"><div id="not-a-datalist">Options</div>'
        errs = build.check_output_and_datalist_integrity("test-page", body)
        self.assertTrue(any("which is not a <datalist>" in e for e in errs))

    def test_input_list_empty_rejected(self):
        body = '<input list="   ">'
        errs = build.check_output_and_datalist_integrity("test-page", body)
        self.assertTrue(any("<input list=''> cannot have empty list attribute" in e for e in errs))


class AriaInvalidAndErrorMessageIntegrityTests(unittest.TestCase):
    """Tests for aria-invalid, aria-errormessage, and aria-required attributes (W3C WAI-ARIA 1.2 §6.6 and WCAG 2.2 SC 3.3.1 / SC 3.3.3 / SC 4.1.2)."""

    def test_valid_aria_invalid_tokens_pass(self):
        body = '<input aria-invalid="true"><input aria-invalid="false"><input aria-invalid="grammar"><input aria-invalid="spelling">'
        self.assertEqual(build.check_aria_invalid_and_error_message_integrity("test-page", body), [])

    def test_invalid_aria_invalid_token_rejected(self):
        body = '<input aria-invalid="yes">'
        errs = build.check_aria_invalid_and_error_message_integrity("test-page", body)
        self.assertTrue(any("declares invalid aria-invalid='yes'" in e for e in errs))

    def test_valid_aria_errormessage_passes(self):
        body = '<input id="field" aria-invalid="true" aria-errormessage="err-field"><p id="err-field">Invalid input</p>'
        self.assertEqual(build.check_aria_invalid_and_error_message_integrity("test-page", body), [])

    def test_empty_aria_errormessage_rejected(self):
        body = '<input aria-errormessage="   ">'
        errs = build.check_aria_invalid_and_error_message_integrity("test-page", body)
        self.assertTrue(any("aria-errormessage cannot be empty" in e for e in errs))

    def test_aria_errormessage_dangling_id_rejected(self):
        body = '<input aria-errormessage="missing-err-id">'
        errs = build.check_aria_invalid_and_error_message_integrity("test-page", body)
        self.assertTrue(any("references non-existent element id 'missing-err-id'" in e for e in errs))

    def test_aria_errormessage_targeting_aria_hidden_element_rejected(self):
        body = '<input aria-errormessage="hidden-err"><p id="hidden-err" aria-hidden="true">Hidden error</p>'
        errs = build.check_aria_invalid_and_error_message_integrity("test-page", body)
        self.assertTrue(any("which is aria-hidden='true'" in e for e in errs))

    def test_valid_aria_required_tokens_pass(self):
        body = '<input aria-required="true"><input aria-required="false">'
        self.assertEqual(build.check_aria_invalid_and_error_message_integrity("test-page", body), [])

    def test_invalid_aria_required_token_rejected(self):
        body = '<input aria-required="mandatory">'
        errs = build.check_aria_invalid_and_error_message_integrity("test-page", body)
        self.assertTrue(any("declares invalid aria-required='mandatory'" in e for e in errs))

    def test_contradictory_native_required_and_aria_required_false_rejected(self):
        body = '<input required aria-required="false">'
        errs = build.check_aria_invalid_and_error_message_integrity("test-page", body)
        self.assertTrue(any("declares native 'required' but also aria-required='false'" in e for e in errs))

    def test_check_page_integrates_new_aria_and_form_checks(self):
        m = meta('<a href="https://example.com" target="_blank" rel="noopener">Silent external link</a>')
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("missing explicit new window/tab notification" in e for e in errs))


class InertAttributeIntegrityTests(unittest.TestCase):
    """Tests for HTML5 §6.12.3 inert attribute and keyboard trap prevention (WCAG 2.2 SC 2.1.2 & SC 4.1.2)."""

    def test_valid_inert_element_passes(self):
        body = '<div inert><p>Background content not focusable</p></div>'
        self.assertEqual(build.check_inert_attribute_integrity("test-page", body), [])

    def test_inert_with_tabindex_zero_rejected(self):
        body = '<div inert tabindex="0">Interactive trap</div>'
        errs = build.check_inert_attribute_integrity("test-page", body)
        self.assertTrue(any("creates contradictory sequential focus and keyboard trapping" in e for e in errs))

    def test_inert_with_positive_tabindex_rejected(self):
        body = '<div inert tabindex="1">Interactive trap</div>'
        errs = build.check_inert_attribute_integrity("test-page", body)
        self.assertTrue(any("creates contradictory sequential focus and keyboard trapping" in e for e in errs))

    def test_inert_with_autofocus_rejected(self):
        body = '<button inert autofocus>Action</button>'
        errs = build.check_inert_attribute_integrity("test-page", body)
        self.assertTrue(any("<button inert> cannot declare autofocus" in e for e in errs))

    def test_inert_with_aria_live_rejected(self):
        body = '<div inert aria-live="polite">Announcements</div>'
        errs = build.check_inert_attribute_integrity("test-page", body)
        self.assertTrue(any("declares aria-live='polite' on an inert element removed from assistive technology" in e for e in errs))

    def test_inert_with_aria_live_off_passes(self):
        body = '<div inert aria-live="off">Silent inert container</div>'
        self.assertEqual(build.check_inert_attribute_integrity("test-page", body), [])

    def test_nested_autofocus_inside_inert_ancestor_rejected(self):
        body = '<section inert><div><input autofocus></div></section>'
        errs = build.check_inert_attribute_integrity("test-page", body)
        self.assertTrue(any("is nested inside an inert ancestor container, causing focus trapping" in e for e in errs))


class VirtualKeyboardAndInputmodeAttributeTests(unittest.TestCase):
    """Tests for virtual keyboard inputmode and enterkeyhint enumerated tokens (HTML5 §4.10.5.3, §4.10.5.4 & WCAG 2.2 SC 1.3.5)."""

    def test_valid_inputmode_tokens_pass(self):
        body = '<input inputmode="decimal"><input inputmode="numeric"><input inputmode="search"><input inputmode="text">'
        self.assertEqual(build.check_virtual_keyboard_and_inputmode_attributes("test-page", body), [])

    def test_empty_inputmode_rejected(self):
        body = '<input inputmode="">'
        errs = build.check_virtual_keyboard_and_inputmode_attributes("test-page", body)
        self.assertTrue(any("inputmode attribute cannot be empty" in e for e in errs))

    def test_invalid_inputmode_token_rejected(self):
        body = '<input inputmode="phone">'
        errs = build.check_virtual_keyboard_and_inputmode_attributes("test-page", body)
        self.assertTrue(any("declares invalid inputmode='phone'" in e for e in errs))

    def test_valid_enterkeyhint_tokens_pass(self):
        body = '<input enterkeyhint="search"><input enterkeyhint="done"><input enterkeyhint="go">'
        self.assertEqual(build.check_virtual_keyboard_and_inputmode_attributes("test-page", body), [])

    def test_empty_enterkeyhint_rejected(self):
        body = '<input enterkeyhint="  ">'
        errs = build.check_virtual_keyboard_and_inputmode_attributes("test-page", body)
        self.assertTrue(any("enterkeyhint attribute cannot be empty" in e for e in errs))

    def test_invalid_enterkeyhint_token_rejected(self):
        body = '<input enterkeyhint="submit">'
        errs = build.check_virtual_keyboard_and_inputmode_attributes("test-page", body)
        self.assertTrue(any("declares invalid enterkeyhint='submit'" in e for e in errs))


class RangeSliderAccessibilityTests(unittest.TestCase):
    """Tests for role='slider' ARIA bounds, accessible naming, and keyboard focusability (W3C WAI-ARIA 1.2 §5.2.8 & WCAG 2.2 SC 4.1.2 / SC 2.1.1)."""

    def test_valid_slider_passes(self):
        body = '<div role="slider" aria-label="Volume level" tabindex="0" aria-valuenow="50" aria-valuemin="0" aria-valuemax="100"></div>'
        self.assertEqual(build.check_range_slider_accessibility("test-page", body), [])

    def test_slider_missing_accessible_name_rejected(self):
        body = '<div role="slider" tabindex="0" aria-valuenow="50" aria-valuemin="0" aria-valuemax="100"></div>'
        errs = build.check_range_slider_accessibility("test-page", body)
        self.assertTrue(any("missing accessible name ('aria-label' or 'aria-labelledby'" in e for e in errs))

    def test_custom_slider_missing_tabindex_rejected(self):
        body = '<div role="slider" aria-label="Volume" aria-valuenow="50" aria-valuemin="0" aria-valuemax="100"></div>'
        errs = build.check_range_slider_accessibility("test-page", body)
        self.assertTrue(any("custom <div role='slider'> must declare tabindex='0' for keyboard operation" in e for e in errs))

    def test_slider_missing_valuenow_rejected(self):
        body = '<div role="slider" aria-label="Volume" tabindex="0" aria-valuemin="0" aria-valuemax="100"></div>'
        errs = build.check_range_slider_accessibility("test-page", body)
        self.assertTrue(any("missing required 'aria-valuenow' attribute" in e for e in errs))

    def test_slider_non_numeric_valuenow_rejected(self):
        body = '<div role="slider" aria-label="Volume" tabindex="0" aria-valuenow="mid" aria-valuemin="0" aria-valuemax="100"></div>'
        errs = build.check_range_slider_accessibility("test-page", body)
        self.assertTrue(any("aria-valuenow='mid' is not a valid number" in e for e in errs))

    def test_slider_min_exceeds_max_rejected(self):
        body = '<div role="slider" aria-label="Volume" tabindex="0" aria-valuenow="50" aria-valuemin="100" aria-valuemax="0"></div>'
        errs = build.check_range_slider_accessibility("test-page", body)
        self.assertTrue(any("aria-valuemin (100.0) exceeds aria-valuemax (0.0)" in e for e in errs))

    def test_slider_valuenow_out_of_bounds_rejected(self):
        body = '<div role="slider" aria-label="Volume" tabindex="0" aria-valuenow="150" aria-valuemin="0" aria-valuemax="100"></div>'
        errs = build.check_range_slider_accessibility("test-page", body)
        self.assertTrue(any("aria-valuenow (150.0) is outside the range [0.0, 100.0]" in e for e in errs))

    def test_check_page_integrates_inert_and_slider_linters(self):
        m = meta('<div inert tabindex="0">Conflicting focus trap</div>')
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("creates contradictory sequential focus and keyboard trapping" in e for e in errs))


class AriaSpinbuttonAndScrollbarAccessibilityTests(unittest.TestCase):
    """Tests for role='spinbutton' and role='scrollbar' ARIA bounds, accessible naming, controls, and keyboard focusability (W3C WAI-ARIA 1.2 §5.2.8 & WCAG 2.2 SC 4.1.2 / SC 2.1.1)."""

    def test_valid_spinbutton_passes(self):
        body = '<div role="spinbutton" aria-label="Quantity" tabindex="0" aria-valuenow="5" aria-valuemin="1" aria-valuemax="10">5</div>'
        self.assertEqual(build.check_aria_spinbutton_and_scrollbar_accessibility("test-page", body), [])

    def test_spinbutton_missing_accessible_name_rejected(self):
        body = '<div role="spinbutton" tabindex="0" aria-valuenow="5" aria-valuemin="1" aria-valuemax="10">5</div>'
        errs = build.check_aria_spinbutton_and_scrollbar_accessibility("test-page", body)
        self.assertTrue(any("missing accessible name ('aria-label' or 'aria-labelledby'" in e for e in errs))

    def test_custom_spinbutton_missing_tabindex_rejected(self):
        body = '<div role="spinbutton" aria-label="Quantity" aria-valuenow="5" aria-valuemin="1" aria-valuemax="10">5</div>'
        errs = build.check_aria_spinbutton_and_scrollbar_accessibility("test-page", body)
        self.assertTrue(any("must declare tabindex='0' for keyboard operation" in e for e in errs))

    def test_spinbutton_missing_valuenow_rejected(self):
        body = '<div role="spinbutton" aria-label="Quantity" tabindex="0" aria-valuemin="1" aria-valuemax="10">5</div>'
        errs = build.check_aria_spinbutton_and_scrollbar_accessibility("test-page", body)
        self.assertTrue(any("missing required 'aria-valuenow' attribute" in e for e in errs))

    def test_spinbutton_non_numeric_valuenow_rejected(self):
        body = '<div role="spinbutton" aria-label="Quantity" tabindex="0" aria-valuenow="three" aria-valuemin="1" aria-valuemax="10">3</div>'
        errs = build.check_aria_spinbutton_and_scrollbar_accessibility("test-page", body)
        self.assertTrue(any("aria-valuenow='three' is not a valid number" in e for e in errs))

    def test_spinbutton_min_exceeds_max_rejected(self):
        body = '<div role="spinbutton" aria-label="Quantity" tabindex="0" aria-valuenow="5" aria-valuemin="20" aria-valuemax="10">5</div>'
        errs = build.check_aria_spinbutton_and_scrollbar_accessibility("test-page", body)
        self.assertTrue(any("aria-valuemin (20.0) exceeds aria-valuemax (10.0)" in e for e in errs))

    def test_spinbutton_valuenow_out_of_bounds_rejected(self):
        body = '<div role="spinbutton" aria-label="Quantity" tabindex="0" aria-valuenow="15" aria-valuemin="1" aria-valuemax="10">15</div>'
        errs = build.check_aria_spinbutton_and_scrollbar_accessibility("test-page", body)
        self.assertTrue(any("aria-valuenow (15.0) is outside the range [1.0, 10.0]" in e for e in errs))

    def test_valid_scrollbar_passes(self):
        body = '<div role="scrollbar" aria-label="Log viewport scrollbar" aria-controls="log-content" tabindex="0" aria-orientation="vertical" aria-valuenow="20" aria-valuemin="0" aria-valuemax="100"></div>'
        self.assertEqual(build.check_aria_spinbutton_and_scrollbar_accessibility("test-page", body), [])

    def test_scrollbar_missing_accessible_name_rejected(self):
        body = '<div role="scrollbar" aria-controls="log-content" tabindex="0" aria-valuenow="20" aria-valuemin="0" aria-valuemax="100"></div>'
        errs = build.check_aria_spinbutton_and_scrollbar_accessibility("test-page", body)
        self.assertTrue(any("missing accessible name ('aria-label' or 'aria-labelledby'" in e for e in errs))

    def test_scrollbar_missing_controls_rejected(self):
        body = '<div role="scrollbar" aria-label="Scroll" tabindex="0" aria-valuenow="20" aria-valuemin="0" aria-valuemax="100"></div>'
        errs = build.check_aria_spinbutton_and_scrollbar_accessibility("test-page", body)
        self.assertTrue(any("missing required 'aria-controls' attribute" in e for e in errs))

    def test_scrollbar_invalid_orientation_rejected(self):
        body = '<div role="scrollbar" aria-label="Scroll" aria-controls="log-content" tabindex="0" aria-orientation="diagonal" aria-valuenow="20" aria-valuemin="0" aria-valuemax="100"></div>'
        errs = build.check_aria_spinbutton_and_scrollbar_accessibility("test-page", body)
        self.assertTrue(any("declares invalid aria-orientation='diagonal'" in e for e in errs))

    def test_scrollbar_missing_tabindex_rejected(self):
        body = '<div role="scrollbar" aria-label="Scroll" aria-controls="log-content" aria-valuenow="20" aria-valuemin="0" aria-valuemax="100"></div>'
        errs = build.check_aria_spinbutton_and_scrollbar_accessibility("test-page", body)
        self.assertTrue(any("must declare tabindex='0' for keyboard operation" in e for e in errs))

    def test_scrollbar_min_exceeds_max_rejected(self):
        body = '<div role="scrollbar" aria-label="Scroll" aria-controls="log-content" tabindex="0" aria-valuenow="20" aria-valuemin="100" aria-valuemax="0"></div>'
        errs = build.check_aria_spinbutton_and_scrollbar_accessibility("test-page", body)
        self.assertTrue(any("aria-valuemin (100.0) exceeds aria-valuemax (0.0)" in e for e in errs))

    def test_scrollbar_valuenow_out_of_bounds_rejected(self):
        body = '<div role="scrollbar" aria-label="Scroll" aria-controls="log-content" tabindex="0" aria-valuenow="120" aria-valuemin="0" aria-valuemax="100"></div>'
        errs = build.check_aria_spinbutton_and_scrollbar_accessibility("test-page", body)
        self.assertTrue(any("aria-valuenow (120.0) is outside the range [0.0, 100.0]" in e for e in errs))

    def test_check_page_integrates_spinbutton_and_scrollbar_linter(self):
        m = meta('<div role="scrollbar" aria-controls="log-pane" tabindex="0" aria-valuenow="50" aria-valuemin="0" aria-valuemax="100"></div>')
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("missing accessible name ('aria-label' or 'aria-labelledby'" in e for e in errs))


class AriaHeadingAndLevelIntegrityTests(unittest.TestCase):
    """Tests for custom role='heading' elements, explicit aria-level, and outline semantics (W3C WAI-ARIA 1.2 §5.3.2, §6.6 & WCAG 2.2 SC 1.3.1 / SC 4.1.2)."""

    def test_valid_custom_heading_with_level_and_text_passes(self):
        body = '<div role="heading" aria-level="2">Section Heading</div>'
        self.assertEqual(build.check_aria_heading_and_level_integrity("test-page", body), [])

    def test_valid_custom_heading_with_aria_label_passes(self):
        body = '<div role="heading" aria-level="3" aria-label="Accessible title"></div>'
        self.assertEqual(build.check_aria_heading_and_level_integrity("test-page", body), [])

    def test_custom_heading_missing_aria_level_rejected(self):
        body = '<div role="heading">Missing Level</div>'
        errs = build.check_aria_heading_and_level_integrity("test-page", body)
        self.assertTrue(any("missing required 'aria-level' attribute" in e for e in errs))

    def test_empty_custom_heading_rejected(self):
        body = '<div role="heading" aria-level="2">   </div>'
        errs = build.check_aria_heading_and_level_integrity("test-page", body)
        self.assertTrue(any("is empty and lacks accessible name" in e for e in errs))

    def test_non_positive_aria_level_rejected(self):
        body = '<div role="heading" aria-level="0">Zero Level</div>'
        errs = build.check_aria_heading_and_level_integrity("test-page", body)
        self.assertTrue(any("declares non-positive aria-level='0'" in e for e in errs))

    def test_negative_aria_level_rejected(self):
        body = '<div role="heading" aria-level="-2">Negative Level</div>'
        errs = build.check_aria_heading_and_level_integrity("test-page", body)
        self.assertTrue(any("declares non-positive aria-level='-2'" in e for e in errs))

    def test_non_integer_aria_level_rejected(self):
        body = '<div role="heading" aria-level="second">Invalid Level</div>'
        errs = build.check_aria_heading_and_level_integrity("test-page", body)
        self.assertTrue(any("declares non-integer aria-level='second'" in e for e in errs))

    def test_aria_level_on_unsupported_role_rejected(self):
        body = '<button aria-level="2">Button</button>'
        errs = build.check_aria_heading_and_level_integrity("test-page", body)
        self.assertTrue(any("declares aria-level on element without a hierarchical role" in e for e in errs))

    def test_valid_aria_level_on_treeitem_or_listitem_passes(self):
        body = '<ul><li role="treeitem" aria-level="2">Nested leaf</li></ul>'
        self.assertEqual(build.check_aria_heading_and_level_integrity("test-page", body), [])


class AriaOrientationAndSortContextIntegrityTests(unittest.TestCase):
    """Tests for valid placement of aria-orientation and aria-sort on supporting roles (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)."""

    def test_valid_orientation_on_tablist_and_slider_passes(self):
        body = '<div role="tablist" aria-orientation="horizontal"></div><div role="slider" aria-label="Level" tabindex="0" aria-orientation="vertical" aria-valuenow="50"></div>'
        self.assertEqual(build.check_aria_orientation_and_sort_context_integrity("test-page", body), [])

    def test_orientation_on_unsupported_element_rejected(self):
        body = '<p aria-orientation="horizontal">Paragraph</p>'
        errs = build.check_aria_orientation_and_sort_context_integrity("test-page", body)
        self.assertTrue(any("declares aria-orientation on element without orientation-sensitive role" in e for e in errs))

    def test_valid_sort_on_th_passes(self):
        body = '<table><thead><tr><th scope="col" aria-sort="ascending">Column</th></tr></thead></table>'
        self.assertEqual(build.check_aria_orientation_and_sort_context_integrity("test-page", body), [])

    def test_valid_sort_on_columnheader_role_passes(self):
        body = '<div role="columnheader" aria-sort="descending">Header</div>'
        self.assertEqual(build.check_aria_orientation_and_sort_context_integrity("test-page", body), [])

    def test_sort_on_non_header_rejected(self):
        body = '<td aria-sort="ascending">Data cell</td>'
        errs = build.check_aria_orientation_and_sort_context_integrity("test-page", body)
        self.assertTrue(any("declares aria-sort on non-header element" in e for e in errs))


class AriaProgressbarAccessibilityTests(unittest.TestCase):
    """Tests for role='progressbar' ARIA bounds and accessible naming (W3C WAI-ARIA 1.2 §5.2.8 & WCAG 2.2 SC 4.1.2)."""

    def test_valid_determinate_progressbar_passes(self):
        body = '<div role="progressbar" aria-label="File upload" aria-valuenow="60" aria-valuemin="0" aria-valuemax="100"></div>'
        self.assertEqual(build.check_aria_progressbar_accessibility("test-page", body), [])

    def test_valid_indeterminate_progressbar_passes(self):
        body = '<div role="progressbar" aria-label="Syncing ledger..."></div>'
        self.assertEqual(build.check_aria_progressbar_accessibility("test-page", body), [])

    def test_progressbar_missing_accessible_name_rejected(self):
        body = '<div role="progressbar" aria-valuenow="50"></div>'
        errs = build.check_aria_progressbar_accessibility("test-page", body)
        self.assertTrue(any("missing accessible name ('aria-label' or 'aria-labelledby'" in e for e in errs))

    def test_progressbar_non_numeric_valuenow_rejected(self):
        body = '<div role="progressbar" aria-label="Sync" aria-valuenow="almost"></div>'
        errs = build.check_aria_progressbar_accessibility("test-page", body)
        self.assertTrue(any("aria-valuenow='almost' is not a valid number" in e for e in errs))

    def test_progressbar_min_exceeds_max_rejected(self):
        body = '<div role="progressbar" aria-label="Sync" aria-valuemin="100" aria-valuemax="0"></div>'
        errs = build.check_aria_progressbar_accessibility("test-page", body)
        self.assertTrue(any("aria-valuemin (100.0) exceeds aria-valuemax (0.0)" in e for e in errs))

    def test_progressbar_valuenow_out_of_bounds_rejected(self):
        body = '<div role="progressbar" aria-label="Sync" aria-valuenow="120" aria-valuemin="0" aria-valuemax="100"></div>'
        errs = build.check_aria_progressbar_accessibility("test-page", body)
        self.assertTrue(any("aria-valuenow (120.0) is outside the range [0.0, 100.0]" in e for e in errs))

    def test_check_page_integrates_heading_and_widget_linters(self):
        m = meta('<div role="heading">Missing level</div>')
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("missing required 'aria-level' attribute" in e for e in errs))


class AriaTabAndTabpanelAccessibilityTests(unittest.TestCase):
    """Tests for role='tab', 'tablist', and 'tabpanel' ARIA relationship and state invariants (W3C WAI-ARIA 1.2 §5.3.7 & WCAG 2.2 SC 1.3.1 / SC 4.1.2)."""

    def test_valid_tab_and_tabpanel_passes(self):
        body = (
            '<div role="tablist" aria-label="Feature modes">'
            '<button role="tab" id="tab-opt1" aria-selected="true" aria-controls="panel-opt1">Option 1</button>'
            '<button role="tab" id="tab-opt2" aria-selected="false" aria-controls="panel-opt2">Option 2</button>'
            '</div>'
            '<div role="tabpanel" id="panel-opt1" aria-labelledby="tab-opt1"><p>Panel 1 text</p></div>'
            '<div role="tabpanel" id="panel-opt2" aria-labelledby="tab-opt2"><p>Panel 2 text</p></div>'
        )
        self.assertEqual(build.check_aria_tab_tablist_and_tabpanel_integrity("test-page", body), [])

    def test_tab_missing_aria_selected_rejected(self):
        body = (
            '<div role="tablist">'
            '<button role="tab" id="t1" aria-controls="p1">Tab 1</button>'
            '</div>'
            '<div role="tabpanel" id="p1" aria-labelledby="t1">Content</div>'
        )
        errs = build.check_aria_tab_tablist_and_tabpanel_integrity("test-page", body)
        self.assertTrue(any("missing valid aria-selected attribute" in e for e in errs))

    def test_tab_invalid_aria_selected_token_rejected(self):
        body = (
            '<div role="tablist">'
            '<button role="tab" id="t1" aria-selected="active" aria-controls="p1">Tab 1</button>'
            '</div>'
            '<div role="tabpanel" id="p1" aria-labelledby="t1">Content</div>'
        )
        errs = build.check_aria_tab_tablist_and_tabpanel_integrity("test-page", body)
        self.assertTrue(any("must be 'true' or 'false'" in e for e in errs))

    def test_tab_missing_accessible_name_rejected(self):
        body = (
            '<div role="tablist">'
            '<button role="tab" id="t1" aria-selected="true" aria-controls="p1"></button>'
            '</div>'
            '<div role="tabpanel" id="p1" aria-labelledby="t1">Content</div>'
        )
        errs = build.check_aria_tab_tablist_and_tabpanel_integrity("test-page", body)
        self.assertTrue(any("lacks accessible name" in e for e in errs))

    def test_tab_broken_aria_controls_rejected(self):
        body = (
            '<div role="tablist">'
            '<button role="tab" id="t1" aria-selected="true" aria-controls="missing-panel">Tab</button>'
            '</div>'
        )
        errs = build.check_aria_tab_tablist_and_tabpanel_integrity("test-page", body)
        self.assertTrue(any("references non-existent element id" in e for e in errs))

    def test_tabpanel_missing_accessible_name_rejected(self):
        body = '<div role="tabpanel" id="p1"></div>'
        errs = build.check_aria_tab_tablist_and_tabpanel_integrity("test-page", body)
        self.assertTrue(any("lacks accessible name or content" in e for e in errs))

    def test_tabpanel_broken_aria_labelledby_rejected(self):
        body = '<div role="tabpanel" id="p1" aria-labelledby="missing-tab">Content</div>'
        errs = build.check_aria_tab_tablist_and_tabpanel_integrity("test-page", body)
        self.assertTrue(any("references non-existent element id" in e for e in errs))

    def test_tablist_declaring_aria_expanded_rejected(self):
        body = '<div role="tablist" aria-expanded="true"><button role="tab" id="t1" aria-selected="true">Tab</button></div>'
        errs = build.check_aria_tab_tablist_and_tabpanel_integrity("test-page", body)
        self.assertTrue(any("declares aria-expanded; aria-expanded belongs on interactive tab or accordion triggers" in e for e in errs))

    def test_multiple_tablists_without_names_rejected(self):
        body = (
            '<div role="tablist"><button role="tab" id="t1" aria-selected="true">Tab 1</button></div>'
            '<div role="tablist"><button role="tab" id="t2" aria-selected="true">Tab 2</button></div>'
        )
        errs = build.check_aria_tab_tablist_and_tabpanel_integrity("test-page", body)
        self.assertTrue(any("multiple <div role='tablist'> elements on page require accessible names" in e for e in errs))


class AriaPopupAndExpansionTriggerTests(unittest.TestCase):
    """Tests for aria-haspopup tokens and aria-expanded boolean values on interactive elements (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)."""

    def test_valid_aria_haspopup_tokens_pass(self):
        for token in ("true", "false", "menu", "listbox", "tree", "grid", "dialog"):
            body = f'<button aria-haspopup="{token}">Trigger</button>'
            self.assertEqual(build.check_aria_popup_and_expansion_trigger_integrity("test-page", body), [])

    def test_invalid_aria_haspopup_token_rejected(self):
        for bad in ("popup", "dropdown", "tooltip", "modal", "window"):
            body = f'<button aria-haspopup="{bad}">Trigger</button>'
            errs = build.check_aria_popup_and_expansion_trigger_integrity("test-page", body)
            self.assertTrue(any("declares invalid aria-haspopup" in e for e in errs))

    def test_valid_aria_expanded_on_button_passes(self):
        body = '<button aria-expanded="false" aria-controls="sect">Toggle</button><div id="sect">Body</div>'
        self.assertEqual(build.check_aria_popup_and_expansion_trigger_integrity("test-page", body), [])

    def test_valid_aria_expanded_on_interactive_role_passes(self):
        body = '<div role="button" tabindex="0" aria-expanded="true">Custom button</div>'
        self.assertEqual(build.check_aria_popup_and_expansion_trigger_integrity("test-page", body), [])

    def test_invalid_non_boolean_aria_expanded_rejected(self):
        body = '<button aria-expanded="yes">Button</button>'
        errs = build.check_aria_popup_and_expansion_trigger_integrity("test-page", body)
        self.assertTrue(any("must be 'true' or 'false'" in e for e in errs))

    def test_aria_expanded_on_static_element_rejected(self):
        body = '<p aria-expanded="true">Static paragraph</p>'
        errs = build.check_aria_popup_and_expansion_trigger_integrity("test-page", body)
        self.assertTrue(any("declares aria-expanded on non-interactive static element" in e for e in errs))


class MediaTrackAccessibilityTests(unittest.TestCase):
    """Tests for <track> elements inside video/audio containers (HTML5 §4.8.11, §4.8.12 & WCAG 2.2 SC 1.2.2)."""

    def test_valid_media_track_passes(self):
        body = (
            '<video controls>'
            '<source src="overview.mp4" type="video/mp4">'
            '<track kind="captions" src="captions-en.vtt" srclang="en" label="English" default>'
            '<track kind="subtitles" src="subtitles-es.vtt" srclang="es" label="Español">'
            '</video>'
        )
        self.assertEqual(build.check_media_track_accessibility("test-page", body), [])

    def test_track_outside_media_rejected(self):
        body = '<track kind="captions" src="cap.vtt" srclang="en">'
        errs = build.check_media_track_accessibility("test-page", body)
        self.assertTrue(any("element placed outside <video> or <audio> container" in e for e in errs))

    def test_track_missing_or_invalid_kind_rejected(self):
        body = '<video controls><track kind="transcript" src="cap.vtt" srclang="en"></video>'
        errs = build.check_media_track_accessibility("test-page", body)
        self.assertTrue(any("missing or invalid kind='transcript'" in e for e in errs))

    def test_track_empty_src_rejected(self):
        body = '<video controls><track kind="captions" src="" srclang="en"></video>'
        errs = build.check_media_track_accessibility("test-page", body)
        self.assertTrue(any("missing or empty src attribute" in e for e in errs))

    def test_track_missing_srclang_on_subtitles_rejected(self):
        body = '<video controls><track kind="subtitles" src="sub.vtt"></video>'
        errs = build.check_media_track_accessibility("test-page", body)
        self.assertTrue(any("missing or invalid srclang=''" in e for e in errs))

    def test_track_invalid_srclang_format_rejected(self):
        body = '<video controls><track kind="captions" src="cap.vtt" srclang="English!"></video>'
        errs = build.check_media_track_accessibility("test-page", body)
        self.assertTrue(any("missing or invalid srclang='English!'" in e for e in errs))

    def test_multiple_default_tracks_of_same_kind_rejected(self):
        body = (
            '<video controls>'
            '<track kind="captions" src="c1.vtt" srclang="en" default>'
            '<track kind="captions" src="c2.vtt" srclang="fr" default>'
            '</video>'
        )
        errs = build.check_media_track_accessibility("test-page", body)
        self.assertTrue(any("contains multiple default <track> elements for kind='captions'" in e for e in errs))

    def test_check_page_integrates_tab_and_media_track_linters(self):
        m = meta('<button role="tab" id="t1" aria-controls="missing_p">Tab</button>')
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("references non-existent element id" in e for e in errs))


class AriaGridAndTableCoordinateTests(unittest.TestCase):
    """Tests for ARIA table/grid coordinate attributes and placement (W3C WAI-ARIA 1.2 §5.2.5, §5.2.6, §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def test_valid_grid_coordinates_pass(self):
        body = (
            '<div role="grid" aria-label="Verification matrix" aria-rowcount="10" aria-colcount="5">'
            '<div role="row" aria-rowindex="1">'
            '<span role="columnheader" aria-colindex="1">Spec</span>'
            '<span role="columnheader" aria-colindex="2" aria-colspan="2">Outcome</span>'
            '</div>'
            '<div role="row" aria-rowindex="2">'
            '<span role="gridcell" aria-rowindex="2" aria-colindex="1" aria-rowspan="1" aria-rowindextext="Row 2">PASS</span>'
            '</div>'
            '</div>'
        )
        self.assertEqual(build.check_aria_grid_and_table_coordinate_integrity("test-page", body), [])

    def test_invalid_negative_or_zero_rowcount_rejected(self):
        body = '<div role="grid" aria-label="Matrix" aria-rowcount="0"></div>'
        errs = build.check_aria_grid_and_table_coordinate_integrity("test-page", body)
        self.assertTrue(any("specifies invalid 'aria-rowcount=\"0\"'" in e for e in errs))

        body2 = '<div role="grid" aria-label="Matrix" aria-colcount="-2"></div>'
        errs2 = build.check_aria_grid_and_table_coordinate_integrity("test-page", body2)
        self.assertTrue(any("specifies invalid 'aria-colcount=\"-2\"'" in e for e in errs2))

    def test_non_integer_rowcount_rejected(self):
        body = '<div role="grid" aria-label="Matrix" aria-rowcount="ten"></div>'
        errs = build.check_aria_grid_and_table_coordinate_integrity("test-page", body)
        self.assertTrue(any("specifies non-integer 'aria-rowcount=\"ten\"'" in e for e in errs))

    def test_non_positive_or_non_integer_rowindex_rejected(self):
        body = '<table><tr aria-rowindex="0"><td>Cell</td></tr></table>'
        errs = build.check_aria_grid_and_table_coordinate_integrity("test-page", body)
        self.assertTrue(any("specifies non-positive 'aria-rowindex=\"0\"'" in e for e in errs))

        body2 = '<table><tr aria-rowindex="first"><td>Cell</td></tr></table>'
        errs2 = build.check_aria_grid_and_table_coordinate_integrity("test-page", body2)
        self.assertTrue(any("specifies non-integer 'aria-rowindex=\"first\"'" in e for e in errs2))

    def test_rowindex_on_non_table_element_rejected(self):
        body = '<p aria-rowindex="2">Paragraph with rowindex</p>'
        errs = build.check_aria_grid_and_table_coordinate_integrity("test-page", body)
        self.assertTrue(any("declares 'aria-rowindex' on non-table element without cell or row role" in e for e in errs))

    def test_non_positive_or_non_integer_span_rejected(self):
        body = '<table><tr><td aria-colspan="0">Cell</td></tr></table>'
        errs = build.check_aria_grid_and_table_coordinate_integrity("test-page", body)
        self.assertTrue(any("specifies non-positive 'aria-colspan=\"0\"'" in e for e in errs))

        body2 = '<table><tr><td aria-rowspan="all">Cell</td></tr></table>'
        errs2 = build.check_aria_grid_and_table_coordinate_integrity("test-page", body2)
        self.assertTrue(any("specifies non-integer 'aria-rowspan=\"all\"'" in e for e in errs2))

    def test_span_on_non_cell_element_rejected(self):
        body = '<div role="row" aria-colspan="2">Row with colspan</div>'
        errs = build.check_aria_grid_and_table_coordinate_integrity("test-page", body)
        self.assertTrue(any("declares 'aria-colspan' on non-cell element without cell role" in e for e in errs))

    def test_rowindextext_without_rowindex_rejected(self):
        body = '<table><tr><td aria-rowindextext="Second row">Data</td></tr></table>'
        errs = build.check_aria_grid_and_table_coordinate_integrity("test-page", body)
        self.assertTrue(any("declares 'aria-rowindextext' without accompanying 'aria-rowindex'" in e for e in errs))

    def test_empty_rowindextext_rejected(self):
        body = '<table><tr><td aria-rowindex="2" aria-rowindextext="   ">Data</td></tr></table>'
        errs = build.check_aria_grid_and_table_coordinate_integrity("test-page", body)
        self.assertTrue(any("declares empty 'aria-rowindextext' attribute" in e for e in errs))

    def test_colindextext_without_colindex_rejected(self):
        body = '<table><tr><td aria-colindextext="Col 2">Data</td></tr></table>'
        errs = build.check_aria_grid_and_table_coordinate_integrity("test-page", body)
        self.assertTrue(any("declares 'aria-colindextext' without accompanying 'aria-colindex'" in e for e in errs))


class AriaTreeAndTreeitemHierarchyTests(unittest.TestCase):
    """Tests for ARIA tree, treegrid, and treeitem hierarchy (W3C WAI-ARIA 1.2 §5.3.8, §5.3.9, §5.2.9 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def test_valid_tree_structure_passes(self):
        body = (
            '<ul role="tree" aria-label="Governance directories">'
            '<li role="treeitem" aria-expanded="true">'
            '<span>Protocols</span>'
            '<ul role="group">'
            '<li role="treeitem">RFC 9000</li>'
            '<li role="treeitem">RFC 9221</li>'
            '</ul>'
            '</li>'
            '</ul>'
        )
        self.assertEqual(build.check_aria_tree_and_treeitem_hierarchy_integrity("test-page", body), [])

    def test_tree_missing_accessible_name_rejected(self):
        body = '<ul role="tree"><li role="treeitem">Item</li></ul>'
        errs = build.check_aria_tree_and_treeitem_hierarchy_integrity("test-page", body)
        self.assertTrue(any("declaring role='tree' missing accessible name" in e for e in errs))

    def test_tree_invalid_multiselectable_rejected(self):
        body = '<ul role="tree" aria-label="Files" aria-multiselectable="multi"><li role="treeitem">Item</li></ul>'
        errs = build.check_aria_tree_and_treeitem_hierarchy_integrity("test-page", body)
        self.assertTrue(any("specifies invalid aria-multiselectable='multi'" in e for e in errs))

    def test_treeitem_outside_tree_or_group_rejected(self):
        body = '<div><p role="treeitem">Orphaned tree item</p></div>'
        errs = build.check_aria_tree_and_treeitem_hierarchy_integrity("test-page", body)
        self.assertTrue(any("declaring role='treeitem' is not contained within a role='tree'" in e for e in errs))

    def test_treeitem_invalid_aria_expanded_rejected(self):
        body = (
            '<ul role="tree" aria-label="Files">'
            '<li role="treeitem" aria-expanded="open">Branch</li>'
            '</ul>'
        )
        errs = build.check_aria_tree_and_treeitem_hierarchy_integrity("test-page", body)
        self.assertTrue(any("specifies invalid aria-expanded='open'" in e for e in errs))

    def test_branch_treeitem_missing_aria_expanded_rejected(self):
        body = (
            '<ul role="tree" aria-label="Files">'
            '<li role="treeitem">'
            '<span>Folder</span>'
            '<ul role="group">'
            '<li role="treeitem">Leaf</li>'
            '</ul>'
            '</li>'
            '</ul>'
        )
        errs = build.check_aria_tree_and_treeitem_hierarchy_integrity("test-page", body)
        self.assertTrue(any("has child treeitem/group nodes but is missing required aria-expanded attribute" in e for e in errs))


class SvgViewBoxAndTextIntegrityTests(unittest.TestCase):
    """Tests for SVG responsive viewBox and text node integrity (SVG 2 §5.2, WCAG 2.2 SC 1.1.1, SC 1.4.10 & Spec 05 Explainer Guidelines)."""

    def test_valid_svg_viewbox_and_text_passes(self):
        body = (
            '<svg viewBox="0 0 400 300" aria-label="Architecture diagram">'
            '<text x="20" y="40">QUIC P2P Flow</text>'
            '</svg>'
        )
        self.assertEqual(build.check_svg_viewbox_and_text_integrity("test-page", body), [])

    def test_svg_missing_viewbox_rejected(self):
        body = '<svg width="400" height="300" aria-label="Static diagram"></svg>'
        errs = build.check_svg_viewbox_and_text_integrity("test-page", body)
        self.assertTrue(any("missing required 'viewBox' attribute for responsive reflow" in e for e in errs))

    def test_svg_malformed_viewbox_rejected(self):
        body = '<svg viewBox="0 0 400" aria-label="Diagram"></svg>'
        errs = build.check_svg_viewbox_and_text_integrity("test-page", body)
        self.assertTrue(any("declares malformed viewBox='0 0 400'" in e for e in errs))

    def test_svg_non_positive_viewbox_dimensions_rejected(self):
        body = '<svg viewBox="0 0 400 0" aria-label="Diagram"></svg>'
        errs = build.check_svg_viewbox_and_text_integrity("test-page", body)
        self.assertTrue(any("has non-positive width (400.0) or height (0.0)" in e for e in errs))

    def test_svg_empty_text_node_without_aria_hidden_rejected(self):
        body = (
            '<svg viewBox="0 0 400 300" aria-label="Diagram">'
            '<text x="10" y="20">   </text>'
            '</svg>'
        )
        errs = build.check_svg_viewbox_and_text_integrity("test-page", body)
        self.assertTrue(any("contains empty or whitespace-only <text> node without aria-hidden='true'" in e for e in errs))

    def test_svg_empty_text_node_with_aria_hidden_passes(self):
        body = (
            '<svg viewBox="0 0 400 300" aria-label="Diagram">'
            '<text x="10" y="20" aria-hidden="true"></text>'
            '</svg>'
        )
        self.assertEqual(build.check_svg_viewbox_and_text_integrity("test-page", body), [])

    def test_check_page_integrates_grid_tree_and_svg_linters(self):
        m = meta('<p aria-rowindex="2">Paragraph with coordinate</p>')
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("declares 'aria-rowindex' on non-table element" in e for e in errs))


class BlockquoteAndCitationIntegrityTests(unittest.TestCase):
    """Tests for <blockquote>, <q>, and <cite> semantic integrity (HTML5 §4.5.6, §4.5.7, §4.5.21 & WCAG 2.2 SC 1.3.1)."""

    def test_valid_blockquote_and_citation_pass(self):
        body = (
            '<blockquote cite="https://example.org/source">'
            '<p>Valid quotation with proper source reference.</p>'
            '</blockquote>'
            '<p>As stated in <cite>The Architecture of Open Systems</cite>, modularity matters.</p>'
            '<p><q cite="/notes/context.html">Inline quote</q></p>'
            '<blockquote cite="doi:10.1145/365230.365252"><p>Dennis and Van Horn foundational paper.</p></blockquote>'
        )
        self.assertEqual(build.check_blockquote_and_citation_integrity("test-page", body), [])

    def test_empty_blockquote_rejected(self):
        body = '<blockquote>   </blockquote>'
        errs = build.check_blockquote_and_citation_integrity("test-page", body)
        self.assertTrue(any("<blockquote> must not be empty or whitespace-only" in e for e in errs))

    def test_blockquote_empty_cite_rejected(self):
        body = '<blockquote cite="">Quote text</blockquote>'
        errs = build.check_blockquote_and_citation_integrity("test-page", body)
        self.assertTrue(any("<blockquote> declares empty cite attribute" in e for e in errs))

    def test_blockquote_invalid_cite_url_rejected(self):
        body = '<blockquote cite="javascript:void(0)">Quote text</blockquote>'
        errs = build.check_blockquote_and_citation_integrity("test-page", body)
        self.assertTrue(any("declares invalid cite URL" in e for e in errs))

    def test_empty_q_inline_quote_rejected(self):
        body = '<p>Quoting: <q></q></p>'
        errs = build.check_blockquote_and_citation_integrity("test-page", body)
        self.assertTrue(any("<q> inline quotation must not be empty or whitespace-only" in e for e in errs))

    def test_q_invalid_cite_url_rejected(self):
        body = '<p><q cite="not a valid url">Quote</q></p>'
        errs = build.check_blockquote_and_citation_integrity("test-page", body)
        self.assertTrue(any("<q> declares invalid cite URL" in e for e in errs))

    def test_empty_cite_element_rejected(self):
        body = '<p>Book title: <cite>   </cite></p>'
        errs = build.check_blockquote_and_citation_integrity("test-page", body)
        self.assertTrue(any("<cite> element must not be empty or whitespace-only" in e for e in errs))

    def test_nested_cite_element_rejected(self):
        body = '<p><cite>Outer <cite>Inner</cite></cite></p>'
        errs = build.check_blockquote_and_citation_integrity("test-page", body)
        self.assertTrue(any("<cite> must not contain nested <cite> elements" in e for e in errs))


class BdoBdiAndDirIntegrityTests(unittest.TestCase):
    """Tests for bi-directional overrides (<bdo>), isolates (<bdi>), and dir attributes (HTML5 §4.5.25, §4.5.26, §3.2.6.2 & WCAG 2.2 SC 1.3.2)."""

    def test_valid_bdo_bdi_and_dir_pass(self):
        body = (
            '<p dir="ltr">Standard left-to-right paragraph.</p>'
            '<p>User handle: <bdi>arabic_username</bdi></p>'
            '<p><bdo dir="rtl">Hebrew or Arabic text override</bdo></p>'
        )
        self.assertEqual(build.check_bdo_bdi_and_dir_integrity("test-page", body), [])

    def test_bdo_missing_dir_rejected(self):
        body = '<p><bdo>Override text without dir</bdo></p>'
        errs = build.check_bdo_bdi_and_dir_integrity("test-page", body)
        self.assertTrue(any("<bdo> is missing required 'dir' attribute" in e for e in errs))

    def test_bdo_invalid_dir_token_rejected(self):
        body = '<p><bdo dir="auto">Override text with auto dir</bdo></p>'
        errs = build.check_bdo_bdi_and_dir_integrity("test-page", body)
        self.assertTrue(any("<bdo> declares invalid dir='auto'" in e for e in errs))

    def test_element_invalid_dir_token_rejected(self):
        body = '<p dir="left">Paragraph with colloquial left dir</p>'
        errs = build.check_bdo_bdi_and_dir_integrity("test-page", body)
        self.assertTrue(any("declares invalid dir='left'" in e for e in errs))

    def test_element_empty_dir_rejected(self):
        body = '<p dir="  ">Paragraph with empty dir</p>'
        errs = build.check_bdo_bdi_and_dir_integrity("test-page", body)
        self.assertTrue(any("declares empty dir attribute" in e for e in errs))

    def test_empty_bdo_rejected(self):
        body = '<p><bdo dir="rtl">   </bdo></p>'
        errs = build.check_bdo_bdi_and_dir_integrity("test-page", body)
        self.assertTrue(any("<bdo> must not be empty or whitespace-only" in e for e in errs))

    def test_empty_bdi_rejected(self):
        body = '<p>Name: <bdi></bdi></p>'
        errs = build.check_bdo_bdi_and_dir_integrity("test-page", body)
        self.assertTrue(any("<bdi> must not be empty or whitespace-only" in e for e in errs))


class AriaPosInSetAndSetSizeTests(unittest.TestCase):
    """Tests for ARIA posinset and setsize numeric bounds, ordering, and valid item role placement (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def test_valid_posinset_and_setsize_pass(self):
        body = (
            '<ul>'
            '<li aria-posinset="1" aria-setsize="3">Item 1</li>'
            '<li aria-posinset="2" aria-setsize="3">Item 2</li>'
            '<li aria-posinset="3" aria-setsize="3">Item 3</li>'
            '</ul>'
            '<div role="tablist">'
            '<div role="tab" aria-posinset="1" aria-setsize="2" aria-selected="true">Tab 1</div>'
            '<div role="tab" aria-posinset="2" aria-setsize="2" aria-selected="false">Tab 2</div>'
            '</div>'
        )
        self.assertEqual(build.check_aria_posinset_and_setsize_integrity("test-page", body), [])

    def test_valid_setsize_minus_one_pass(self):
        body = '<ol><li aria-posinset="12" aria-setsize="-1">Streaming item</li></ol>'
        self.assertEqual(build.check_aria_posinset_and_setsize_integrity("test-page", body), [])

    def test_posinset_on_non_item_element_rejected(self):
        body = '<div aria-posinset="1" aria-setsize="5">Arbitrary container</div>'
        errs = build.check_aria_posinset_and_setsize_integrity("test-page", body)
        self.assertTrue(any("declares aria-posinset and aria-setsize on non-item element without set item role" in e for e in errs))

    def test_non_positive_or_zero_posinset_rejected(self):
        body = '<ul><li aria-posinset="0" aria-setsize="5">Item zero</li></ul>'
        errs = build.check_aria_posinset_and_setsize_integrity("test-page", body)
        self.assertTrue(any("declares invalid aria-posinset='0'" in e for e in errs))

    def test_non_integer_posinset_rejected(self):
        body = '<ul><li aria-posinset="first" aria-setsize="5">First item</li></ul>'
        errs = build.check_aria_posinset_and_setsize_integrity("test-page", body)
        self.assertTrue(any("declares non-integer aria-posinset='first'" in e for e in errs))

    def test_invalid_zero_or_sub_minus_one_setsize_rejected(self):
        body = '<ul><li aria-posinset="1" aria-setsize="0">Item in empty set</li></ul>'
        errs = build.check_aria_posinset_and_setsize_integrity("test-page", body)
        self.assertTrue(any("declares invalid aria-setsize='0'" in e for e in errs))

    def test_non_integer_setsize_rejected(self):
        body = '<ul><li aria-posinset="1" aria-setsize="many">Item</li></ul>'
        errs = build.check_aria_posinset_and_setsize_integrity("test-page", body)
        self.assertTrue(any("declares non-integer aria-setsize='many'" in e for e in errs))

    def test_posinset_exceeding_setsize_rejected(self):
        body = '<ul><li aria-posinset="5" aria-setsize="3">Overflow item</li></ul>'
        errs = build.check_aria_posinset_and_setsize_integrity("test-page", body)
        self.assertTrue(any("declares aria-posinset (5) exceeding aria-setsize (3)" in e for e in errs))

    def test_check_page_integrates_blockquote_dir_and_posinset_linters(self):
        m = meta('<bdo>Missing dir on override</bdo>')
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("<bdo> is missing required 'dir' attribute" in e for e in errs))


class DetailsAndSummaryDisclosureIntegrityTests(unittest.TestCase):
    """Tests for HTML5 details and summary disclosure structure, child order, cardinality, and interactive content constraints (HTML5 §4.11.1, §4.11.2, W3C WAI-ARIA 1.2 §5.3.3 & WCAG 2.2 SC 1.3.1, SC 4.1.2, SC 2.1.1)."""

    def test_valid_disclosure_structure_passes(self):
        body = '<details><summary>For researchers</summary><div>Technical content and equations.</div></details>'
        self.assertEqual(build.check_details_and_summary_disclosure_integrity("test-page", body), [])

    def test_details_without_summary_passes(self):
        body = '<details><p>Browser provides default disclosure summary</p></details>'
        self.assertEqual(build.check_details_and_summary_disclosure_integrity("test-page", body), [])

    def test_child_element_before_summary_rejected(self):
        body = '<details><p>Leading paragraph</p><summary>Belated summary</summary><div>Content</div></details>'
        errs = build.check_details_and_summary_disclosure_integrity("test-page", body)
        self.assertTrue(any("<summary> appears after child element <p> in <details>" in e or "contains child <p> before <summary>" in e for e in errs))

    def test_multiple_summaries_in_single_details_rejected(self):
        body = '<details><summary>First summary</summary><summary>Second summary</summary><div>Body</div></details>'
        errs = build.check_details_and_summary_disclosure_integrity("test-page", body)
        self.assertTrue(any("multiple <summary> elements inside a single <details>" in e for e in errs))

    def test_orphaned_summary_rejected(self):
        body = '<div><summary>Orphaned summary outside details</summary></div>'
        errs = build.check_details_and_summary_disclosure_integrity("test-page", body)
        self.assertTrue(any("orphaned <summary> outside of <details>" in e for e in errs))

    def test_empty_or_whitespace_summary_rejected(self):
        body = '<details><summary>   \n  </summary><div>Body</div></details>'
        errs = build.check_details_and_summary_disclosure_integrity("test-page", body)
        self.assertTrue(any("<summary> must not be empty or whitespace-only" in e for e in errs))

    def test_interactive_link_in_summary_rejected(self):
        body = '<details><summary>Review <a href="/terms">terms</a> first</summary><div>Body</div></details>'
        errs = build.check_details_and_summary_disclosure_integrity("test-page", body)
        self.assertTrue(any("interactive <a> inside <summary> violates HTML5 §4.11.2 & WCAG 2.2 SC 4.1.2" in e for e in errs))

    def test_interactive_button_in_summary_rejected(self):
        body = '<details><summary>Summary <button type="button">Reset</button></summary><div>Body</div></details>'
        errs = build.check_details_and_summary_disclosure_integrity("test-page", body)
        self.assertTrue(any("interactive <button> inside <summary> violates HTML5 §4.11.2 & WCAG 2.2 SC 4.1.2" in e for e in errs))

    def test_interactive_input_in_summary_rejected(self):
        body = '<details><summary>Filter <input type="text" aria-label="Query"></summary><div>Body</div></details>'
        errs = build.check_details_and_summary_disclosure_integrity("test-page", body)
        self.assertTrue(any("interactive <input> inside <summary> violates HTML5 §4.11.2 & WCAG 2.2 SC 4.1.2" in e for e in errs))

    def test_tabindex_in_summary_rejected(self):
        body = '<details><summary>Help <span tabindex="0">Icon</span></summary><div>Body</div></details>'
        errs = build.check_details_and_summary_disclosure_integrity("test-page", body)
        self.assertTrue(any("interactive <span> inside <summary>" in e for e in errs))

    def test_interactive_role_in_summary_rejected(self):
        body = '<details><summary>Action <span role="button">Run</span></summary><div>Body</div></details>'
        errs = build.check_details_and_summary_disclosure_integrity("test-page", body)
        self.assertTrue(any("interactive <span> inside <summary>" in e for e in errs))


class DelAndInsEditIntegrityTests(unittest.TestCase):
    """Tests for HTML5 document edit elements (<del> and <ins>) citation URIs and ISO 8601 datetimes (HTML5 §4.5.18, §4.5.19 & WCAG 2.2 SC 1.3.1)."""

    def test_valid_del_and_ins_pass(self):
        body = '<p>Revised: <del datetime="2026-11-01">legacy draft</del> <ins datetime="2026-11-07" cite="https://cintnet.org/changes">audited release</ins></p>'
        self.assertEqual(build.check_del_and_ins_edit_integrity("test-page", body), [])

    def test_empty_del_rejected(self):
        body = '<p>Draft: <del>   </del></p>'
        errs = build.check_del_and_ins_edit_integrity("test-page", body)
        self.assertTrue(any("<del> edit element must not be empty or whitespace-only" in e for e in errs))

    def test_empty_ins_rejected(self):
        body = '<p>Draft: <ins></ins></p>'
        errs = build.check_del_and_ins_edit_integrity("test-page", body)
        self.assertTrue(any("<ins> edit element must not be empty or whitespace-only" in e for e in errs))

    def test_empty_cite_rejected(self):
        body = '<p><ins cite="">Inserted amendment</ins></p>'
        errs = build.check_del_and_ins_edit_integrity("test-page", body)
        self.assertTrue(any("<ins> declares empty cite attribute" in e for e in errs))

    def test_invalid_cite_url_rejected(self):
        body = '<p><del cite="javascript:void(0)">Deleted text</del></p>'
        errs = build.check_del_and_ins_edit_integrity("test-page", body)
        self.assertTrue(any("<del> declares invalid cite URL 'javascript:void(0)'" in e for e in errs))

    def test_empty_datetime_rejected(self):
        body = '<p><ins datetime="">Inserted text</ins></p>'
        errs = build.check_del_and_ins_edit_integrity("test-page", body)
        self.assertTrue(any("<ins> declares empty datetime attribute" in e for e in errs))

    def test_invalid_datetime_rejected(self):
        body = '<p><del datetime="yesterday">Old term</del></p>'
        errs = build.check_del_and_ins_edit_integrity("test-page", body)
        self.assertTrue(any("<del> declares invalid datetime 'yesterday'" in e for e in errs))


class AriaKeyShortcutsAndRoledescriptionIntegrityTests(unittest.TestCase):
    """Tests for aria-keyshortcuts syntax, aria-roledescription placement and duplication, and ARIA 1.3 braille attributes (W3C WAI-ARIA 1.2 §6.6, WAI-ARIA 1.3 §6.6 & WCAG 2.2 SC 2.1.4, SC 4.1.2)."""

    def test_valid_keyshortcuts_pass(self):
        body = '<button type="button" aria-keyshortcuts="Control+S Alt+Shift+D">Save Document</button>'
        self.assertEqual(build.check_aria_keyshortcuts_and_roledescription_integrity("test-page", body), [])

    def test_valid_roledescription_passes(self):
        body = '<div role="region" aria-roledescription="slide" aria-label="Slide 1">Slide contents</div>'
        self.assertEqual(build.check_aria_keyshortcuts_and_roledescription_integrity("test-page", body), [])

    def test_empty_keyshortcuts_rejected(self):
        body = '<button type="button" aria-keyshortcuts="">Action</button>'
        errs = build.check_aria_keyshortcuts_and_roledescription_integrity("test-page", body)
        self.assertTrue(any("<button> declares empty aria-keyshortcuts attribute" in e for e in errs))

    def test_malformed_keyshortcuts_dangling_plus_rejected(self):
        body = '<button type="button" aria-keyshortcuts="Control+">Incomplete</button>'
        errs = build.check_aria_keyshortcuts_and_roledescription_integrity("test-page", body)
        self.assertTrue(any("declares malformed shortcut 'Control+' in aria-keyshortcuts" in e for e in errs))

    def test_invalid_modifier_in_keyshortcuts_rejected(self):
        body = '<button type="button" aria-keyshortcuts="Super+S">Custom</button>'
        errs = build.check_aria_keyshortcuts_and_roledescription_integrity("test-page", body)
        self.assertTrue(any("declares invalid modifier 'Super' in shortcut 'Super+S'" in e for e in errs))

    def test_empty_roledescription_rejected(self):
        body = '<button type="button" aria-roledescription="">Action</button>'
        errs = build.check_aria_keyshortcuts_and_roledescription_integrity("test-page", body)
        self.assertTrue(any("<button> declares empty aria-roledescription attribute" in e for e in errs))

    def test_roledescription_on_generic_container_rejected(self):
        body = '<div aria-roledescription="card">Generic container</div>'
        errs = build.check_aria_keyshortcuts_and_roledescription_integrity("test-page", body)
        self.assertTrue(any("declares aria-roledescription='card' on generic container without an ARIA role" in e for e in errs))

    def test_roledescription_duplicating_role_rejected(self):
        body = '<button type="button" role="button" aria-roledescription="button">Save</button>'
        errs = build.check_aria_keyshortcuts_and_roledescription_integrity("test-page", body)
        self.assertTrue(any("aria-roledescription='button' duplicates role='button'" in e for e in errs))

    def test_empty_braille_attributes_rejected(self):
        body = '<div role="region" aria-label="Overview" aria-braillelabel="">Content</div>'
        errs = build.check_aria_keyshortcuts_and_roledescription_integrity("test-page", body)
        self.assertTrue(any("declares empty aria-braillelabel attribute" in e for e in errs))

    def test_check_page_integrates_details_del_and_shortcuts_linters(self):
        m = meta('<details><summary>Valid summary</summary><div><del>   </del></div></details>')
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("<del> edit element must not be empty or whitespace-only" in e for e in errs))


class SelectAndOptgroupAccessibilityTests(unittest.TestCase):
    def test_valid_select_and_optgroups_pass(self):
        body = (
            '<label for="fruit-select">Choose fruit</label>'
            '<select id="fruit-select">'
            '  <optgroup label="Citrus">'
            '    <option value="orange">Orange</option>'
            '    <option value="lemon">Lemon</option>'
            '  </optgroup>'
            '  <optgroup label="Berries">'
            '    <option value="strawberry">Strawberry</option>'
            '  </optgroup>'
            '</select>'
        )
        errs = build.check_select_and_optgroup_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_optgroup_missing_label_rejected(self):
        body = (
            '<select aria-label="Choices">'
            '  <optgroup>'
            '    <option value="1">One</option>'
            '  </optgroup>'
            '</select>'
        )
        errs = build.check_select_and_optgroup_integrity("test-page", body)
        self.assertTrue(any("<optgroup> missing required 'label' attribute" in e for e in errs))

    def test_optgroup_empty_label_rejected(self):
        body = (
            '<select aria-label="Choices">'
            '  <optgroup label="   ">'
            '    <option value="1">One</option>'
            '  </optgroup>'
            '</select>'
        )
        errs = build.check_select_and_optgroup_integrity("test-page", body)
        self.assertTrue(any("<optgroup> declares empty or whitespace-only 'label' attribute" in e for e in errs))

    def test_optgroup_outside_select_rejected(self):
        body = '<optgroup label="Orphan Group"><option value="1">One</option></optgroup>'
        errs = build.check_select_and_optgroup_integrity("test-page", body)
        self.assertTrue(any("<optgroup> must be inside a <select> element" in e for e in errs))

    def test_nested_optgroups_rejected(self):
        body = (
            '<select aria-label="Nested Groups">'
            '  <optgroup label="Outer">'
            '    <optgroup label="Inner">'
            '      <option value="1">One</option>'
            '    </optgroup>'
            '  </optgroup>'
            '</select>'
        )
        errs = build.check_select_and_optgroup_integrity("test-page", body)
        self.assertTrue(any("<optgroup> cannot be nested inside another <optgroup>" in e for e in errs))

    def test_option_outside_container_rejected(self):
        body = '<div><option value="1">Orphan option</option></div>'
        errs = build.check_select_and_optgroup_integrity("test-page", body)
        self.assertTrue(any("<option> must be inside a <select> or <datalist> element" in e for e in errs))

    def test_option_empty_text_and_label_rejected(self):
        body = (
            '<select aria-label="Empty Option">'
            '  <option value="1">   </option>'
            '</select>'
        )
        errs = build.check_select_and_optgroup_integrity("test-page", body)
        self.assertTrue(any("<option> has empty text and missing or empty 'label' attribute" in e for e in errs))

    def test_option_with_valid_label_attribute_passes(self):
        body = (
            '<select aria-label="Label Attribute">'
            '  <option value="1" label="Accessible One"></option>'
            '</select>'
        )
        errs = build.check_select_and_optgroup_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_single_select_multiple_selected_rejected(self):
        body = (
            '<select aria-label="Single Select">'
            '  <option value="1" selected>First</option>'
            '  <option value="2" selected>Second</option>'
            '</select>'
        )
        errs = build.check_select_and_optgroup_integrity("test-page", body)
        self.assertTrue(any("<select> without 'multiple' attribute contains multiple selected <option> elements" in e for e in errs))

    def test_multiple_select_with_multiple_selected_passes(self):
        body = (
            '<select aria-label="Multi Select" multiple>'
            '  <option value="1" selected>First</option>'
            '  <option value="2" selected>Second</option>'
            '</select>'
        )
        errs = build.check_select_and_optgroup_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_check_page_integrates_select_linter(self):
        m = meta('<select aria-label="Test"><optgroup><option value="1">One</option></optgroup></select>')
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("<optgroup> missing required 'label' attribute" in e for e in errs))


class RubyAnnotationIntegrityTests(unittest.TestCase):
    def test_valid_ruby_with_rt_and_rp_passes(self):
        body = '<p><ruby>漢<rp>(</rp><rt>kan</rt><rp>)</rp>字<rp>(</rp><rt>ji</rt><rp>)</rp></ruby></p>'
        errs = build.check_ruby_annotation_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_valid_ruby_without_rp_passes(self):
        body = '<p><ruby>漢<rt>kan</rt>字<rt>ji</rt></ruby></p>'
        errs = build.check_ruby_annotation_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_orphaned_rt_rejected(self):
        body = '<p>Some text <rt>kan</rt></p>'
        errs = build.check_ruby_annotation_integrity("test-page", body)
        self.assertTrue(any("orphaned <rt> outside of enclosing <ruby> container" in e for e in errs))

    def test_orphaned_rp_rejected(self):
        body = '<p>Some text <rp>(</rp></p>'
        errs = build.check_ruby_annotation_integrity("test-page", body)
        self.assertTrue(any("orphaned <rp> outside of enclosing <ruby> container" in e for e in errs))

    def test_ruby_missing_rt_rejected(self):
        body = '<p><ruby>漢字</ruby></p>'
        errs = build.check_ruby_annotation_integrity("test-page", body)
        self.assertTrue(any("<ruby> container missing child <rt> annotation" in e for e in errs))

    def test_ruby_with_empty_rt_rejected(self):
        body = '<p><ruby>漢<rt>   </rt></ruby></p>'
        errs = build.check_ruby_annotation_integrity("test-page", body)
        self.assertTrue(any("<rt> ruby text must not be empty or whitespace-only" in e for e in errs))

    def test_ruby_with_empty_rp_rejected(self):
        body = '<p><ruby>漢<rp>  </rp><rt>kan</rt><rp>)</rp></ruby></p>'
        errs = build.check_ruby_annotation_integrity("test-page", body)
        self.assertTrue(any("<rp> ruby fallback parenthesis must not be empty or whitespace-only" in e for e in errs))


class MenuAndToolbarAccessibilityTests(unittest.TestCase):
    def test_valid_menu_with_li_passes(self):
        body = '<menu><li><button type="button">Copy</button></li><li><button type="button">Paste</button></li></menu>'
        errs = build.check_menu_and_toolbar_accessibility("test-page", body)
        self.assertEqual(errs, [])

    def test_menu_with_invalid_direct_child_rejected(self):
        body = '<menu><div><button type="button">Copy</button></div></menu>'
        errs = build.check_menu_and_toolbar_accessibility("test-page", body)
        self.assertTrue(any("<menu> contains invalid direct child <div>" in e for e in errs))

    def test_valid_toolbar_with_aria_label_passes(self):
        body = '<div role="toolbar" aria-label="Editor formatting tools"><button type="button">Bold</button></div>'
        errs = build.check_menu_and_toolbar_accessibility("test-page", body)
        self.assertEqual(errs, [])

    def test_valid_toolbar_with_aria_labelledby_passes(self):
        body = '<div role="toolbar" aria-labelledby="tb-heading"><span id="tb-heading">Tools</span></div>'
        errs = build.check_menu_and_toolbar_accessibility("test-page", body)
        self.assertEqual(errs, [])

    def test_toolbar_missing_accessible_name_rejected(self):
        body = '<div role="toolbar"><button type="button">Bold</button></div>'
        errs = build.check_menu_and_toolbar_accessibility("test-page", body)
        self.assertTrue(any("with role='toolbar' missing accessible name" in e for e in errs))

    def test_toolbar_with_aria_expanded_on_container_rejected(self):
        body = '<div role="toolbar" aria-label="Tools" aria-expanded="true"><button type="button">Bold</button></div>'
        errs = build.check_menu_and_toolbar_accessibility("test-page", body)
        self.assertTrue(any("declares aria-expanded on container" in e for e in errs))

    def test_valid_menubar_passes(self):
        body = '<div role="menubar" aria-label="Main menu" aria-orientation="horizontal"><div role="menuitem">File</div></div>'
        errs = build.check_menu_and_toolbar_accessibility("test-page", body)
        self.assertEqual(errs, [])

    def test_menubar_with_invalid_orientation_rejected(self):
        body = '<div role="menubar" aria-label="Main menu" aria-orientation="diagonal"><div role="menuitem">File</div></div>'
        errs = build.check_menu_and_toolbar_accessibility("test-page", body)
        self.assertTrue(any("declares invalid aria-orientation='diagonal'" in e for e in errs))


class AriaModalAndDialogStateTests(unittest.TestCase):
    def test_valid_dialog_with_aria_modal_passes(self):
        body = '<dialog aria-modal="true" aria-label="User settings dialog"><p>Dialog body</p></dialog>'
        errs = build.check_aria_modal_and_dialog_state_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_dialog_with_invalid_aria_modal_rejected(self):
        body = '<dialog aria-modal="dialog-mode" aria-label="User settings"><p>Dialog</p></dialog>'
        errs = build.check_aria_modal_and_dialog_state_integrity("test-page", body)
        self.assertTrue(any("declares invalid aria-modal='dialog-mode'" in e for e in errs))

    def test_aria_modal_on_non_dialog_element_rejected(self):
        body = '<div aria-modal="true"><p>Not a dialog</p></div>'
        errs = build.check_aria_modal_and_dialog_state_integrity("test-page", body)
        self.assertTrue(any("declares aria-modal on non-dialog element" in e for e in errs))

    def test_dialog_contradictory_modal_and_hidden_rejected(self):
        body = '<dialog aria-modal="true" aria-hidden="true" aria-label="Hidden modal"><p>Dialog</p></dialog>'
        errs = build.check_aria_modal_and_dialog_state_integrity("test-page", body)
        self.assertTrue(any("declares contradictory aria-modal='true' and aria-hidden='true'" in e for e in errs))

    def test_valid_alertdialog_with_name_and_describedby_passes(self):
        body = (
            '<div role="alertdialog" aria-label="Confirm Action" aria-describedby="desc-prompt">'
            '  <p id="desc-prompt">Are you sure you want to discard your draft?</p>'
            '</div>'
        )
        errs = build.check_aria_modal_and_dialog_state_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_alertdialog_missing_accessible_name_rejected(self):
        body = (
            '<div role="alertdialog" aria-describedby="desc-prompt">'
            '  <p id="desc-prompt">Discard?</p>'
            '</div>'
        )
        errs = build.check_aria_modal_and_dialog_state_integrity("test-page", body)
        self.assertTrue(any("element with role='alertdialog' missing accessible name" in e for e in errs))

    def test_alertdialog_missing_aria_describedby_rejected(self):
        body = (
            '<div role="alertdialog" aria-label="Confirm Action">'
            '  <p>Discard?</p>'
            '</div>'
        )
        errs = build.check_aria_modal_and_dialog_state_integrity("test-page", body)
        self.assertTrue(any("missing accessible description via aria-describedby" in e for e in errs))

    def test_check_page_integrates_ruby_and_toolbar_and_modal_linters(self):
        # Test ruby integration
        m1 = meta('<p><ruby>漢字</ruby></p>')
        m1["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m1['body']}"
        errs1 = build.check_page(m1, "")
        self.assertTrue(any("<ruby> container missing child <rt> annotation" in e for e in errs1))

        # Test toolbar integration
        m2 = meta('<div role="toolbar"><button>Tool</button></div>')
        m2["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m2['body']}"
        errs2 = build.check_page(m2, "")
        self.assertTrue(any("with role='toolbar' missing accessible name" in e for e in errs2))

        # Test modal integration
        m3 = meta('<div aria-modal="true"><p>Modal</p></div>')
        m3["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m3['body']}"
        errs3 = build.check_page(m3, "")
        self.assertTrue(any("declares aria-modal on non-dialog element" in e for e in errs3))


class DefinitionListAndDfnIntegrityTests(unittest.TestCase):
    def test_valid_dl_with_dt_and_dd_passes(self):
        body = '<dl><dt>Term</dt><dd>Definition of term</dd></dl>'
        errs = build.check_definition_list_and_dfn_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_valid_dl_with_div_groups_passes(self):
        body = '<dl><div><dt>Term 1</dt><dd>Definition 1</dd></div><div><dt>Term 2</dt><dd>Definition 2</dd></div></dl>'
        errs = build.check_definition_list_and_dfn_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_dl_invalid_direct_child_rejected(self):
        body = '<dl><p>Invalid direct paragraph</p><dt>Term</dt><dd>Definition</dd></dl>'
        errs = build.check_definition_list_and_dfn_integrity("test-page", body)
        self.assertTrue(any("<dl> contains invalid direct child <p>" in e for e in errs))

    def test_dl_div_invalid_child_rejected(self):
        body = '<dl><div><span>Invalid span inside div in dl</span><dt>Term</dt><dd>Definition</dd></div></dl>'
        errs = build.check_definition_list_and_dfn_integrity("test-page", body)
        self.assertTrue(any("<div> child inside <dl> contains invalid child <span>" in e for e in errs))

    def test_orphaned_dt_dd_outside_dl_rejected(self):
        body = '<dt>Orphaned term</dt><dd>Orphaned description</dd>'
        errs = build.check_definition_list_and_dfn_integrity("test-page", body)
        self.assertTrue(any("<dt> is orphaned outside an enclosing <dl> container" in e for e in errs))
        self.assertTrue(any("<dd> is orphaned outside an enclosing <dl> container" in e for e in errs))

    def test_orphaned_dt_inside_div_outside_dl_rejected(self):
        body = '<div><dt>Term inside plain div</dt><dd>Desc inside plain div</dd></div>'
        errs = build.check_definition_list_and_dfn_integrity("test-page", body)
        self.assertTrue(any("<dt> is orphaned outside an enclosing <dl> container" in e for e in errs))

    def test_dl_dd_before_dt_rejected(self):
        body = '<dl><dd>Orphaned leading description</dd><dt>Term</dt></dl>'
        errs = build.check_definition_list_and_dfn_integrity("test-page", body)
        self.assertTrue(any("<dd> appears before any preceding <dt> in definition list" in e for e in errs))

    def test_dl_trailing_dt_without_dd_rejected(self):
        body = '<dl><dt>Term without description</dt></dl>'
        errs = build.check_definition_list_and_dfn_integrity("test-page", body)
        self.assertTrue(any("<dl> contains <dt> group without corresponding <dd> description" in e for e in errs))

    def test_empty_dt_or_dd_rejected(self):
        body = '<dl><dt>   </dt><dd>Valid desc</dd></dl>'
        errs = build.check_definition_list_and_dfn_integrity("test-page", body)
        self.assertTrue(any("<dt> is empty or whitespace-only" in e for e in errs))

    def test_valid_dfn_passes(self):
        body = '<p>The <dfn>collective intelligence</dfn> coordinates multiple minds.</p>'
        errs = build.check_definition_list_and_dfn_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_empty_dfn_rejected(self):
        body = '<p>The <dfn>  </dfn> coordinates multiple minds.</p>'
        errs = build.check_definition_list_and_dfn_integrity("test-page", body)
        self.assertTrue(any("<dfn> is empty or whitespace-only" in e for e in errs))

    def test_nested_dfn_rejected(self):
        body = '<p><dfn>Outer term <dfn>Inner term</dfn></dfn></p>'
        errs = build.check_definition_list_and_dfn_integrity("test-page", body)
        self.assertTrue(any("<dfn> contains nested <dfn> element" in e for e in errs))


class AriaCheckedAndPressedStateTests(unittest.TestCase):
    def test_valid_aria_checked_on_checkbox_passes(self):
        body = '<div role="checkbox" aria-checked="true" aria-label="Accept terms" tabindex="0">Accept</div>'
        errs = build.check_aria_checked_and_pressed_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_valid_aria_checked_on_native_input_passes(self):
        body = '<input type="checkbox" aria-checked="mixed">'
        errs = build.check_aria_checked_and_pressed_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_invalid_aria_checked_token_rejected(self):
        body = '<div role="checkbox" aria-checked="yes" aria-label="Accept">Accept</div>'
        errs = build.check_aria_checked_and_pressed_integrity("test-page", body)
        self.assertTrue(any("declares invalid aria-checked='yes'" in e for e in errs))

    def test_aria_checked_on_non_checkable_role_rejected(self):
        body = '<div role="button" aria-checked="true" aria-label="Button">Click</div>'
        errs = build.check_aria_checked_and_pressed_integrity("test-page", body)
        self.assertTrue(any("declares aria-checked on non-checkable element without checkable role" in e for e in errs))

    def test_switch_with_aria_checked_mixed_rejected(self):
        body = '<div role="switch" aria-checked="mixed" aria-label="Mute audio">Mute</div>'
        errs = build.check_aria_checked_and_pressed_integrity("test-page", body)
        self.assertTrue(any("with role='switch' declares invalid aria-checked='mixed'" in e for e in errs))

    def test_valid_switch_with_boolean_checked_passes(self):
        body = '<div role="switch" aria-checked="true" aria-label="Mute audio">Mute</div>'
        errs = build.check_aria_checked_and_pressed_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_valid_aria_pressed_button_passes(self):
        body = '<button type="button" aria-pressed="true">Mute</button>'
        errs = build.check_aria_checked_and_pressed_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_valid_aria_pressed_custom_button_passes(self):
        body = '<g role="button" tabindex="0" aria-pressed="false" aria-label="Inspect panel"></g>'
        errs = build.check_aria_checked_and_pressed_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_invalid_aria_pressed_token_rejected(self):
        body = '<button type="button" aria-pressed="active">Toggle</button>'
        errs = build.check_aria_checked_and_pressed_integrity("test-page", body)
        self.assertTrue(any("declares invalid aria-pressed='active'" in e for e in errs))

    def test_aria_pressed_on_non_button_rejected(self):
        body = '<a href="/about" aria-pressed="true">About</a>'
        errs = build.check_aria_checked_and_pressed_integrity("test-page", body)
        self.assertTrue(any("declares aria-pressed on non-button element" in e for e in errs))

    def test_aria_pressed_button_missing_accessible_name_rejected(self):
        body = '<button type="button" aria-pressed="false">   </button>'
        errs = build.check_aria_checked_and_pressed_integrity("test-page", body)
        self.assertTrue(any("declaring aria-pressed missing accessible name" in e for e in errs))

    def test_valid_aria_current_tokens_pass(self):
        body = '<nav><a href="/blog" aria-current="page">Blog</a><a href="/step2" aria-current="step">Step 2</a></nav>'
        errs = build.check_aria_checked_and_pressed_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_invalid_aria_current_token_rejected(self):
        body = '<nav><a href="/blog" aria-current="selected">Blog</a></nav>'
        errs = build.check_aria_checked_and_pressed_integrity("test-page", body)
        self.assertTrue(any("declares invalid aria-current='selected'" in e for e in errs))


class SearchLandmarkAndSearchboxTests(unittest.TestCase):
    def test_valid_search_landmark_passes(self):
        body = '<search><form action="/search"><input type="search" aria-label="Site query"></form></search>'
        errs = build.check_search_landmark_and_searchbox_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_nested_search_landmark_rejected(self):
        body = '<search><search><input type="search" aria-label="Query"></search></search>'
        errs = build.check_search_landmark_and_searchbox_integrity("test-page", body)
        self.assertTrue(any("<search> contains nested <search> element" in e for e in errs))

    def test_multiple_search_landmarks_without_distinguishing_labels_rejected(self):
        body = '<search><input type="search"></search><div role="search"><input type="search"></div>'
        errs = build.check_search_landmark_and_searchbox_integrity("test-page", body)
        self.assertTrue(any("multiple search landmarks present on page, but <search> lacks distinguishing accessible name" in e for e in errs))

    def test_multiple_search_landmarks_with_labels_pass(self):
        body = (
            '<search aria-label="Site documentation search"><input type="search"></search>'
            '<div role="search" aria-label="Table filter search"><input type="search"></div>'
        )
        errs = build.check_search_landmark_and_searchbox_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_valid_searchbox_on_input_passes(self):
        body = '<input type="text" role="searchbox" aria-label="Search articles">'
        errs = build.check_search_landmark_and_searchbox_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_searchbox_on_non_editable_element_rejected(self):
        body = '<div role="searchbox" aria-label="Search box">Static search container</div>'
        errs = build.check_search_landmark_and_searchbox_integrity("test-page", body)
        self.assertTrue(any("element with role='searchbox' is placed on non-editable element <div>" in e for e in errs))

    def test_check_page_integrates_dl_pressed_and_search_linters(self):
        # Test dl integration
        m1 = meta('<dl><dt>Lonely Term</dt></dl>')
        m1["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m1['body']}"
        errs1 = build.check_page(m1, "")
        self.assertTrue(any("<dl> contains <dt> group without corresponding <dd> description" in e for e in errs1))

        # Test aria-pressed on non-button integration
        m2 = meta('<a href="/about" aria-pressed="true">About</a>')
        m2["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m2['body']}"
        errs2 = build.check_page(m2, "")
        self.assertTrue(any("declares aria-pressed on non-button element" in e for e in errs2))

        # Test search landmark nesting integration
        m3 = meta('<search><search><input type="search" aria-label="Query"></search></search>')
        m3["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m3['body']}"
        errs3 = build.check_page(m3, "")
        self.assertTrue(any("<search> contains nested <search> element" in e for e in errs3))


class AddressElementIntegrityTests(unittest.TestCase):
    """Ensure HTML5 <address> elements satisfy containment, non-empty, and nesting constraints (HTML5 §4.4.13 & WCAG 2.2 SC 1.3.1)."""

    def test_empty_address_rejected(self):
        body = '<address></address>'
        errs = build.check_address_element_integrity("test-page", body)
        self.assertTrue(any("<address> element is empty or whitespace-only" in e for e in errs))

    def test_whitespace_address_rejected(self):
        body = '<address>   \n   </address>'
        errs = build.check_address_element_integrity("test-page", body)
        self.assertTrue(any("<address> element is empty or whitespace-only" in e for e in errs))

    def test_address_with_forbidden_sectioning_rejected(self):
        for tag in ("article", "aside", "nav", "section"):
            body = f'<address>Contact: <{tag}>inner content</{tag}></address>'
            errs = build.check_address_element_integrity("test-page", body)
            self.assertTrue(any(f"contains forbidden <{tag}> element" in e for e in errs), f"Failed to reject <{tag}> in <address>")

    def test_address_with_forbidden_headings_rejected(self):
        for tag in ("h1", "h2", "h3", "h4", "h5", "h6", "hgroup"):
            body = f'<address><{tag}>Contact Us</{tag}> support@cin.org</address>'
            errs = build.check_address_element_integrity("test-page", body)
            self.assertTrue(any(f"contains forbidden <{tag}> element" in e for e in errs), f"Failed to reject <{tag}> in <address>")

    def test_address_with_forbidden_header_footer_rejected(self):
        for tag in ("header", "footer"):
            body = f'<address><{tag}>Header info</{tag}> support@cin.org</address>'
            errs = build.check_address_element_integrity("test-page", body)
            self.assertTrue(any(f"contains forbidden <{tag}> element" in e for e in errs), f"Failed to reject <{tag}> in <address>")

    def test_nested_address_rejected(self):
        body = '<address>Editorial office: <address>nested branch</address></address>'
        errs = build.check_address_element_integrity("test-page", body)
        self.assertTrue(any("<address> contains nested <address> element" in e for e in errs))

    def test_valid_address_with_contact_link_passes(self):
        body = '<address>Published by CIN. Email: <a href="mailto:contact@cin.org">contact@cin.org</a></address>'
        errs = build.check_address_element_integrity("test-page", body)
        self.assertEqual(errs, [])


class SubAndSupIntegrityTests(unittest.TestCase):
    """Ensure HTML5 <sub> and <sup> elements are non-empty and do not directly self-nest (HTML5 §4.5.16, §4.5.17 & WCAG 2.2 SC 1.3.1)."""

    def test_empty_sub_rejected(self):
        body = '<p>CO<sub></sub></p>'
        errs = build.check_sub_and_sup_integrity("test-page", body)
        self.assertTrue(any("<sub> element is empty or whitespace-only" in e for e in errs))

    def test_empty_sup_rejected(self):
        body = '<p>Note<sup></sup></p>'
        errs = build.check_sub_and_sup_integrity("test-page", body)
        self.assertTrue(any("<sup> element is empty or whitespace-only" in e for e in errs))

    def test_directly_nested_sub_rejected(self):
        body = '<p>Variable: X<sub><sub>i</sub></sub></p>'
        errs = build.check_sub_and_sup_integrity("test-page", body)
        self.assertTrue(any("<sub> directly nests another <sub> element" in e for e in errs))

    def test_directly_nested_sup_rejected(self):
        body = '<p>Power: 2<sup><sup>3</sup></sup></p>'
        errs = build.check_sub_and_sup_integrity("test-page", body)
        self.assertTrue(any("<sup> directly nests another <sup> element" in e for e in errs))

    def test_valid_sub_and_sup_pass(self):
        body = '<p>Water is H<sub>2</sub>O and references are cited<sup><a href="#fn1">1</a></sup>.</p>'
        errs = build.check_sub_and_sup_integrity("test-page", body)
        self.assertEqual(errs, [])


class PictureAndSourceIntegrityTests(unittest.TestCase):
    """Ensure HTML5 <picture> contains exactly one <img> fallback, preceding <source> with non-empty srcset, and no orphaned <source> elements (HTML5 §4.8.1, §4.8.2 & WCAG 2.2 SC 1.1.1, SC 1.3.1)."""

    def test_picture_missing_img_rejected(self):
        body = '<picture><source srcset="/assets/img/hero.webp" type="image/webp"></picture>'
        errs = build.check_picture_and_source_integrity("test-page", body)
        self.assertTrue(any("<picture> missing required <img> child element" in e for e in errs))

    def test_picture_source_after_img_rejected(self):
        body = '<picture><img src="/assets/img/hero.jpg" alt="A descriptive hero illustration"><source srcset="/assets/img/hero.webp" type="image/webp"></picture>'
        errs = build.check_picture_and_source_integrity("test-page", body)
        self.assertTrue(any("<source> appears after <img> inside <picture>" in e for e in errs))

    def test_picture_source_missing_srcset_rejected(self):
        body = '<picture><source type="image/webp"><img src="/assets/img/hero.jpg" alt="A descriptive hero illustration"></picture>'
        errs = build.check_picture_and_source_integrity("test-page", body)
        self.assertTrue(any("<source> inside <picture> missing required non-empty 'srcset' attribute" in e for e in errs))

    def test_picture_multiple_img_rejected(self):
        body = '<picture><img src="/assets/img/a.jpg" alt="First descriptive illustration"><img src="/assets/img/b.jpg" alt="Second descriptive illustration"></picture>'
        errs = build.check_picture_and_source_integrity("test-page", body)
        self.assertTrue(any("<picture> contains multiple <img> elements" in e for e in errs))

    def test_orphaned_source_outside_containers_rejected(self):
        body = '<div><source srcset="/assets/img/hero.webp"></div>'
        errs = build.check_picture_and_source_integrity("test-page", body)
        self.assertTrue(any("<source> element orphaned outside <picture>, <audio>, or <video> container" in e for e in errs))

    def test_valid_picture_passes(self):
        body = '<picture><source srcset="/assets/img/hero.webp" type="image/webp"><img src="/assets/img/hero.jpg" alt="A descriptive hero illustration"></picture>'
        errs = build.check_picture_and_source_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_valid_video_and_audio_source_passes(self):
        body = '<video controls><source src="movie.mp4" type="video/mp4"></video><audio controls><source src="audio.mp3" type="audio/mpeg"></audio>'
        errs = build.check_picture_and_source_integrity("test-page", body)
        self.assertEqual(errs, [])


class AriaMeterIntegrityTests(unittest.TestCase):
    """Ensure elements with role='meter' declare accessible names, required valid numeric aria-valuenow, and consistent min/max bounds (W3C WAI-ARIA 1.2 §5.3.3 & WCAG 2.2 SC 4.1.2)."""

    def test_meter_missing_accessible_name_rejected(self):
        body = '<div role="meter" aria-valuenow="45"></div>'
        errs = build.check_aria_meter_integrity("test-page", body)
        self.assertTrue(any("element with role='meter' missing accessible name" in e for e in errs))

    def test_meter_missing_valuenow_rejected(self):
        body = '<div role="meter" aria-label="Bandwidth load"></div>'
        errs = build.check_aria_meter_integrity("test-page", body)
        self.assertTrue(any("missing required 'aria-valuenow' attribute" in e for e in errs))

    def test_meter_non_numeric_valuenow_rejected(self):
        body = '<div role="meter" aria-label="Bandwidth load" aria-valuenow="fifty"></div>'
        errs = build.check_aria_meter_integrity("test-page", body)
        self.assertTrue(any("aria-valuenow='fifty' is not a valid number" in e for e in errs))

    def test_meter_min_greater_than_or_equal_max_rejected(self):
        body = '<div role="meter" aria-label="Load" aria-valuenow="50" aria-valuemin="100" aria-valuemax="50"></div>'
        errs = build.check_aria_meter_integrity("test-page", body)
        self.assertTrue(any("aria-valuemin (100.0) must be strictly less than aria-valuemax (50.0)" in e for e in errs))

    def test_meter_valuenow_out_of_bounds_rejected(self):
        body = '<div role="meter" aria-label="Load" aria-valuenow="120" aria-valuemin="0" aria-valuemax="100"></div>'
        errs = build.check_aria_meter_integrity("test-page", body)
        self.assertTrue(any("aria-valuenow (120.0) out of bounds [0.0, 100.0]" in e for e in errs))

    def test_valid_meter_passes(self):
        body = '<div role="meter" aria-label="Network capacity" aria-valuenow="42" aria-valuemin="0" aria-valuemax="100"></div>'
        errs = build.check_aria_meter_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_check_page_integrates_address_sub_picture_and_meter_linters(self):
        # 1. Address test integration
        m1 = meta('<address><article>Forbidden</article></address>')
        m1["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m1['body']}"
        errs1 = build.check_page(m1, "")
        self.assertTrue(any("<address> contains forbidden <article> element" in e for e in errs1))

        # 2. Sub test integration
        m2 = meta('<p>CO<sub></sub></p>')
        m2["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m2['body']}"
        errs2 = build.check_page(m2, "")
        self.assertTrue(any("<sub> element is empty or whitespace-only" in e for e in errs2))

        # 3. Picture test integration
        m3 = meta('<picture><source srcset="pic.webp"></picture>')
        m3["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m3['body']}"
        errs3 = build.check_page(m3, "")
        self.assertTrue(any("<picture> missing required <img> child element" in e for e in errs3))

        # 4. Meter test integration
        m4 = meta('<div role="meter" aria-label="Load" aria-valuenow="150" aria-valuemin="0" aria-valuemax="100"></div>')
        m4["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m4['body']}"
        errs4 = build.check_page(m4, "")
        self.assertTrue(any("aria-valuenow (150.0) out of bounds" in e for e in errs4))


class CanvasAccessibilityIntegrityTests(unittest.TestCase):
    """Ensure HTML5 <canvas> elements declare accessible names, provide non-empty fallback content, and avoid presentational roles (HTML5 §4.12.5 & WCAG 2.2 SC 1.1.1, SC 4.1.2)."""

    def test_canvas_missing_accessible_name_rejected(self):
        body = '<canvas width="300" height="150"><p>Fallback text</p></canvas>'
        errs = build.check_canvas_accessibility_and_fallback_integrity("test-page", body)
        self.assertTrue(any("<canvas> element missing accessible name" in e for e in errs))

    def test_canvas_missing_fallback_content_rejected(self):
        body = '<canvas aria-label="Network activity graph" width="300" height="150"></canvas>'
        errs = build.check_canvas_accessibility_and_fallback_integrity("test-page", body)
        self.assertTrue(any("<canvas> element has no fallback content" in e for e in errs))

    def test_canvas_whitespace_fallback_rejected(self):
        body = '<canvas aria-label="Network activity graph">   \n  \t </canvas>'
        errs = build.check_canvas_accessibility_and_fallback_integrity("test-page", body)
        self.assertTrue(any("<canvas> element has no fallback content" in e for e in errs))

    def test_canvas_with_presentation_role_rejected(self):
        body = '<canvas aria-label="Graph" role="presentation"><p>Fallback</p></canvas>'
        errs = build.check_canvas_accessibility_and_fallback_integrity("test-page", body)
        self.assertTrue(any("<canvas> declares forbidden role='presentation'" in e for e in errs))

    def test_canvas_with_none_role_rejected(self):
        body = '<canvas aria-label="Graph" role="none"><p>Fallback</p></canvas>'
        errs = build.check_canvas_accessibility_and_fallback_integrity("test-page", body)
        self.assertTrue(any("<canvas> declares forbidden role='none'" in e for e in errs))

    def test_nested_canvas_rejected(self):
        body = '<canvas aria-label="Outer"><canvas aria-label="Inner"><p>Fallback</p></canvas></canvas>'
        errs = build.check_canvas_accessibility_and_fallback_integrity("test-page", body)
        self.assertTrue(any("<canvas> contains nested <canvas> element" in e for e in errs))

    def test_valid_canvas_with_aria_label_and_fallback_passes(self):
        body = '<canvas aria-label="Real-time consensus ring" width="300" height="200"><p>Dynamic visualization showing consensus nodes communicating over local channels.</p></canvas>'
        errs = build.check_canvas_accessibility_and_fallback_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_valid_canvas_with_labelledby_and_fallback_passes(self):
        body = '<p id="c-desc">Simulation map</p><canvas aria-labelledby="c-desc"><p>Fallback representation of the network topology.</p></canvas>'
        errs = build.check_canvas_accessibility_and_fallback_integrity("test-page", body)
        self.assertEqual(errs, [])


class DataElementIntegrityTests(unittest.TestCase):
    """Ensure HTML5 <data> elements specify machine-readable value attributes and non-empty content (HTML5 §4.5.10 & WCAG 2.2 SC 1.3.1)."""

    def test_data_missing_value_rejected(self):
        body = '<p>Current tier: <data>Level 3</data></p>'
        errs = build.check_data_element_integrity("test-page", body)
        self.assertTrue(any("<data> element missing required non-empty 'value' attribute" in e for e in errs))

    def test_data_empty_value_rejected(self):
        body = '<p>Current tier: <data value="">Level 3</data></p>'
        errs = build.check_data_element_integrity("test-page", body)
        self.assertTrue(any("<data> element missing required non-empty 'value' attribute" in e for e in errs))

    def test_data_whitespace_value_rejected(self):
        body = '<p>Current tier: <data value="   ">Level 3</data></p>'
        errs = build.check_data_element_integrity("test-page", body)
        self.assertTrue(any("<data> element missing required non-empty 'value' attribute" in e for e in errs))

    def test_data_empty_content_rejected(self):
        body = '<p>Score: <data value="42"></data></p>'
        errs = build.check_data_element_integrity("test-page", body)
        self.assertTrue(any("<data> element is empty or whitespace-only" in e for e in errs))

    def test_data_whitespace_content_rejected(self):
        body = '<p>Score: <data value="42">   </data></p>'
        errs = build.check_data_element_integrity("test-page", body)
        self.assertTrue(any("<data> element is empty or whitespace-only" in e for e in errs))

    def test_valid_data_passes(self):
        body = '<p>Contribution weight: <data value="0.95">95% confidence</data></p>'
        errs = build.check_data_element_integrity("test-page", body)
        self.assertEqual(errs, [])


class TechnicalInlineElementsIntegrityTests(unittest.TestCase):
    """Ensure HTML5 <var>, <kbd>, and <samp> elements have non-empty content and do not violate nesting constraints (HTML5 §4.5.13, §4.5.14, §4.5.15 & WCAG 2.2 SC 1.3.1)."""

    def test_empty_var_rejected(self):
        body = '<p>Variable <var></var> is undefined.</p>'
        errs = build.check_technical_inline_elements_integrity("test-page", body)
        self.assertTrue(any("<var> element is empty or whitespace-only" in e for e in errs))

    def test_whitespace_var_rejected(self):
        body = '<p>Variable <var>   </var> is undefined.</p>'
        errs = build.check_technical_inline_elements_integrity("test-page", body)
        self.assertTrue(any("<var> element is empty or whitespace-only" in e for e in errs))

    def test_nested_var_rejected(self):
        body = '<p><var>x<var>i</var></var></p>'
        errs = build.check_technical_inline_elements_integrity("test-page", body)
        self.assertTrue(any("<var> directly nests another <var> element" in e for e in errs))

    def test_empty_samp_rejected(self):
        body = '<p>Output: <samp></samp></p>'
        errs = build.check_technical_inline_elements_integrity("test-page", body)
        self.assertTrue(any("<samp> element is empty or whitespace-only" in e for e in errs))

    def test_whitespace_samp_rejected(self):
        body = '<p>Output: <samp>  \n  </samp></p>'
        errs = build.check_technical_inline_elements_integrity("test-page", body)
        self.assertTrue(any("<samp> element is empty or whitespace-only" in e for e in errs))

    def test_nested_samp_rejected(self):
        body = '<p><samp>status: <samp>ok</samp></samp></p>'
        errs = build.check_technical_inline_elements_integrity("test-page", body)
        self.assertTrue(any("<samp> directly nests another <samp> element" in e for e in errs))

    def test_empty_kbd_rejected(self):
        body = '<p>Press <kbd></kbd> to continue.</p>'
        errs = build.check_technical_inline_elements_integrity("test-page", body)
        self.assertTrue(any("<kbd> element is empty or whitespace-only" in e for e in errs))

    def test_whitespace_kbd_rejected(self):
        body = '<p>Press <kbd>  </kbd> to continue.</p>'
        errs = build.check_technical_inline_elements_integrity("test-page", body)
        self.assertTrue(any("<kbd> element is empty or whitespace-only" in e for e in errs))

    def test_triple_nested_kbd_rejected(self):
        body = '<p><kbd><kbd><kbd>Ctrl</kbd></kbd></kbd></p>'
        errs = build.check_technical_inline_elements_integrity("test-page", body)
        self.assertTrue(any("<kbd> element nested more than 2 levels deep" in e for e in errs))

    def test_valid_var_passes(self):
        body = '<p>Let <var>n</var> denote the number of participating nodes.</p>'
        errs = build.check_technical_inline_elements_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_valid_samp_passes(self):
        body = '<p>System returned: <samp>200 OK: verification passed</samp>.</p>'
        errs = build.check_technical_inline_elements_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_valid_kbd_single_and_combo_passes(self):
        body = '<p>Press <kbd>Enter</kbd> or <kbd><kbd>Ctrl</kbd> + <kbd>C</kbd></kbd> to cancel.</p>'
        errs = build.check_technical_inline_elements_integrity("test-page", body)
        self.assertEqual(errs, [])


class AriaFeedIntegrityTests(unittest.TestCase):
    """Ensure role='feed' streams declare accessible names, avoid nested feeds, and maintain valid aria-busy tokens (W3C WAI-ARIA 1.2 §5.4.12 & WCAG 2.2 SC 4.1.2)."""

    def test_feed_missing_accessible_name_rejected(self):
        body = '<div role="feed"><article>Story 1</article></div>'
        errs = build.check_aria_feed_and_article_stream_integrity("test-page", body)
        self.assertTrue(any("element with role='feed' missing accessible name" in e for e in errs))

    def test_nested_feed_rejected(self):
        body = '<section role="feed" aria-label="Outer feed"><div role="feed" aria-label="Inner feed"><article>Story</article></div></section>'
        errs = build.check_aria_feed_and_article_stream_integrity("test-page", body)
        self.assertTrue(any("role='feed' container is nested inside another role='feed' container" in e for e in errs))

    def test_feed_invalid_aria_busy_rejected(self):
        body = '<div role="feed" aria-label="Updates feed" aria-busy="loading"><article>Story</article></div>'
        errs = build.check_aria_feed_and_article_stream_integrity("test-page", body)
        self.assertTrue(any("role='feed' declares invalid aria-busy='loading'" in e for e in errs))

    def test_valid_feed_passes(self):
        body = '<section role="feed" aria-label="Community updates feed" aria-busy="false"><article>Update 1</article></section>'
        errs = build.check_aria_feed_and_article_stream_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_check_page_integrates_canvas_data_tech_and_feed_linters(self):
        # 1. Canvas test integration
        m1 = meta('<canvas aria-label="Graph"></canvas>')
        m1["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m1['body']}"
        errs1 = build.check_page(m1, "")
        self.assertTrue(any("<canvas> element has no fallback content" in e for e in errs1))

        # 2. Data test integration
        m2 = meta('<p><data>No value</data></p>')
        m2["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m2['body']}"
        errs2 = build.check_page(m2, "")
        self.assertTrue(any("<data> element missing required non-empty 'value' attribute" in e for e in errs2))

        # 3. Technical inline test integration
        m3 = meta('<p><var></var></p>')
        m3["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m3['body']}"
        errs3 = build.check_page(m3, "")
        self.assertTrue(any("<var> element is empty or whitespace-only" in e for e in errs3))

        # 4. Feed test integration
        m4 = meta('<div role="feed"><article>Article</article></div>')
        m4["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m4['body']}"
        errs4 = build.check_page(m4, "")
        self.assertTrue(any("element with role='feed' missing accessible name" in e for e in errs4))


class AriaOwnsHierarchyIntegrityTests(unittest.TestCase):
    """Ensure ARIA aria-owns virtual relationships avoid self-ownership, duplicate targets, multiple owners, and circular dependencies (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def test_empty_or_whitespace_aria_owns_rejected(self):
        body = '<div aria-owns="   "></div>'
        errs = build.check_aria_owns_hierarchy_integrity("test-page", body)
        self.assertTrue(any("empty or whitespace-only aria-owns attribute" in e for e in errs))

    def test_duplicate_target_ids_rejected(self):
        body = '<div id="parent" aria-owns="child1 child1"><span id="child1">Child</span></div>'
        errs = build.check_aria_owns_hierarchy_integrity("test-page", body)
        self.assertTrue(any("aria-owns specifies duplicate target IDs" in e for e in errs))

    def test_self_ownership_rejected(self):
        body = '<div id="self1" aria-owns="self1">Content</div>'
        errs = build.check_aria_owns_hierarchy_integrity("test-page", body)
        self.assertTrue(any("aria-owns references its own id 'self1'" in e for e in errs))

    def test_non_existent_target_id_rejected(self):
        body = '<div id="owner" aria-owns="missing_node">Owner</div>'
        errs = build.check_aria_owns_hierarchy_integrity("test-page", body)
        self.assertTrue(any("aria-owns references non-existent element id 'missing_node'" in e for e in errs))

    def test_multiple_owners_rejected(self):
        body = (
            '<div id="owner1" aria-owns="target_elem">First</div>'
            '<div id="owner2" aria-owns="target_elem">Second</div>'
            '<div id="target_elem">Target</div>'
        )
        errs = build.check_aria_owns_hierarchy_integrity("test-page", body)
        self.assertTrue(any("element id 'target_elem' is owned by multiple elements via aria-owns" in e for e in errs))

    def test_direct_cycle_rejected(self):
        body = (
            '<div id="nodeA" aria-owns="nodeB">Node A</div>'
            '<div id="nodeB" aria-owns="nodeA">Node B</div>'
        )
        errs = build.check_aria_owns_hierarchy_integrity("test-page", body)
        self.assertTrue(any("circular ownership detected in aria-owns relationship" in e for e in errs))

    def test_transitive_cycle_rejected(self):
        body = (
            '<div id="node1" aria-owns="node2">1</div>'
            '<div id="node2" aria-owns="node3">2</div>'
            '<div id="node3" aria-owns="node1">3</div>'
        )
        errs = build.check_aria_owns_hierarchy_integrity("test-page", body)
        self.assertTrue(any("circular ownership detected in aria-owns relationship" in e for e in errs))

    def test_valid_aria_owns_passes(self):
        body = (
            '<div id="container" aria-owns="extra1 extra2"><p>Container</p></div>'
            '<div id="extra1">Extra 1</div>'
            '<div id="extra2">Extra 2</div>'
        )
        errs = build.check_aria_owns_hierarchy_integrity("test-page", body)
        self.assertEqual(errs, [])


class MarkAndSmallIntegrityTests(unittest.TestCase):
    """Ensure HTML5 <mark> and <small> phrasing elements have non-empty content and avoid self-nesting (HTML5 §4.5.11, §4.5.19 & WCAG 2.2 SC 1.3.1, SC 1.4.4)."""

    def test_empty_mark_rejected(self):
        body = '<p>Search result: <mark></mark></p>'
        errs = build.check_mark_and_small_integrity("test-page", body)
        self.assertTrue(any("<mark> element is empty or whitespace-only" in e for e in errs))

    def test_whitespace_mark_rejected(self):
        body = '<p>Search result: <mark>   </mark></p>'
        errs = build.check_mark_and_small_integrity("test-page", body)
        self.assertTrue(any("<mark> element is empty or whitespace-only" in e for e in errs))

    def test_nested_mark_rejected(self):
        body = '<p><mark>Outer <mark>Inner</mark> text</mark></p>'
        errs = build.check_mark_and_small_integrity("test-page", body)
        self.assertTrue(any("<mark> directly nests another <mark> element" in e for e in errs))

    def test_valid_mark_passes(self):
        body = '<p>Matches for <mark>coordination</mark> in document.</p>'
        errs = build.check_mark_and_small_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_empty_small_rejected(self):
        body = '<p>Footnote: <small></small></p>'
        errs = build.check_mark_and_small_integrity("test-page", body)
        self.assertTrue(any("<small> element is empty or whitespace-only" in e for e in errs))

    def test_whitespace_small_rejected(self):
        body = '<p>Footnote: <small> \t </small></p>'
        errs = build.check_mark_and_small_integrity("test-page", body)
        self.assertTrue(any("<small> element is empty or whitespace-only" in e for e in errs))

    def test_nested_small_rejected(self):
        body = '<p><small>Outer disclaimer <small>Inner microtext</small></small></p>'
        errs = build.check_mark_and_small_integrity("test-page", body)
        self.assertTrue(any("<small> directly nests another <small> element" in e for e in errs))

    def test_valid_small_passes(self):
        body = '<p><small>Copyright 2026 Collective Intelligence Network.</small></p>'
        errs = build.check_mark_and_small_integrity("test-page", body)
        self.assertEqual(errs, [])


class TemplateAndSlotIntegrityTests(unittest.TestCase):
    """Ensure HTML5 <template> elements preserve accessibility inertness and <slot> elements have non-empty names (HTML5 §4.12.3, §4.12.4 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def test_template_with_role_rejected(self):
        body = '<template role="region"><div>Inert card</div></template>'
        errs = build.check_template_and_slot_integrity("test-page", body)
        self.assertTrue(any("<template> element must not declare role='region'" in e for e in errs))

    def test_template_with_aria_label_rejected(self):
        body = '<template aria-label="Card blueprint"><div>Inert card</div></template>'
        errs = build.check_template_and_slot_integrity("test-page", body)
        self.assertTrue(any("<template> element must not declare 'aria-label' attribute" in e for e in errs))

    def test_template_with_aria_hidden_rejected(self):
        body = '<template aria-hidden="true"><div>Inert card</div></template>'
        errs = build.check_template_and_slot_integrity("test-page", body)
        self.assertTrue(any("<template> element must not declare 'aria-hidden' attribute" in e for e in errs))

    def test_valid_template_passes(self):
        body = '<template id="card-template"><div class="card"><h3>Title</h3></div></template>'
        errs = build.check_template_and_slot_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_slot_with_empty_name_rejected(self):
        body = '<div class="component"><slot name=""></slot></div>'
        errs = build.check_template_and_slot_integrity("test-page", body)
        self.assertTrue(any("<slot> element declares empty or whitespace-only 'name' attribute" in e for e in errs))

    def test_slot_with_whitespace_name_rejected(self):
        body = '<div class="component"><slot name="   "></slot></div>'
        errs = build.check_template_and_slot_integrity("test-page", body)
        self.assertTrue(any("<slot> element declares empty or whitespace-only 'name' attribute" in e for e in errs))

    def test_valid_slot_with_name_passes(self):
        body = '<div class="component"><slot name="header"></slot></div>'
        errs = build.check_template_and_slot_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_valid_unnamed_slot_passes(self):
        body = '<div class="component"><slot></slot></div>'
        errs = build.check_template_and_slot_integrity("test-page", body)
        self.assertEqual(errs, [])


class VoidElementsAndThematicBreakIntegrityTests(unittest.TestCase):
    """Ensure HTML5 void elements (<wbr>, <hr>) do not contain end tags with content and <hr> retains valid thematic semantics (HTML5 §4.4.2, §4.5.27, §13.1.2.1 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def test_wbr_with_inner_content_rejected(self):
        body = '<p>Long<wbr>break</wbr>word</p>'
        errs = build.check_void_elements_and_thematic_break_integrity("test-page", body)
        self.assertTrue(any("void element <wbr> must not contain inner content" in e for e in errs))

    def test_wbr_with_end_tag_rejected(self):
        body = '<p>Long<wbr></wbr>word</p>'
        errs = build.check_void_elements_and_thematic_break_integrity("test-page", body)
        self.assertTrue(any("void element <wbr> must not have an end tag" in e for e in errs))

    def test_hr_with_inner_content_rejected(self):
        body = '<section><hr>Thematic text</hr></section>'
        errs = build.check_void_elements_and_thematic_break_integrity("test-page", body)
        self.assertTrue(any("void element <hr> must not contain inner content" in e for e in errs))

    def test_hr_with_end_tag_rejected(self):
        body = '<section><hr></hr></section>'
        errs = build.check_void_elements_and_thematic_break_integrity("test-page", body)
        self.assertTrue(any("void element <hr> must not have an end tag" in e for e in errs))

    def test_hr_with_interactive_role_button_rejected(self):
        body = '<hr role="button">'
        errs = build.check_void_elements_and_thematic_break_integrity("test-page", body)
        self.assertTrue(any("<hr> element declares interactive role='button'" in e for e in errs))

    def test_hr_with_interactive_role_link_rejected(self):
        body = '<hr role="link">'
        errs = build.check_void_elements_and_thematic_break_integrity("test-page", body)
        self.assertTrue(any("<hr> element declares interactive role='link'" in e for e in errs))

    def test_hr_with_presentational_role_rejected(self):
        body = '<hr role="presentation">'
        errs = build.check_void_elements_and_thematic_break_integrity("test-page", body)
        self.assertTrue(any("<hr> element declares role='presentation'" in e for e in errs))

    def test_valid_hr_and_wbr_pass(self):
        body = '<p>VeryLongWord<wbr>MayBreakHere</p><hr class="divider"><p>Next thematic section</p>'
        errs = build.check_void_elements_and_thematic_break_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_check_page_integrates_owns_mark_template_and_void_linters(self):
        # 1. aria-owns test integration
        m1 = meta('<div id="p" aria-owns="p"></div>')
        m1["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m1['body']}"
        errs1 = build.check_page(m1, "")
        self.assertTrue(any("aria-owns references its own id 'p'" in e for e in errs1))

        # 2. mark/small test integration
        m2 = meta('<p><mark></mark></p>')
        m2["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m2['body']}"
        errs2 = build.check_page(m2, "")
        self.assertTrue(any("<mark> element is empty or whitespace-only" in e for e in errs2))

        # 3. template/slot test integration
        m3 = meta('<template role="region"><div>Inert</div></template>')
        m3["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m3['body']}"
        errs3 = build.check_page(m3, "")
        self.assertTrue(any("<template> element must not declare role='region'" in e for e in errs3))

        # 4. void elements test integration
        m4 = meta('<hr role="button">')
        m4["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m4['body']}"
        errs4 = build.check_page(m4, "")
        self.assertTrue(any("<hr> element declares interactive role='button'" in e for e in errs4))


class MapAndAreaIntegrityTests(unittest.TestCase):
    """Enforce HTML5 <map> and <area> structure, alt text, shapes, and coordinates (HTML5 §4.8.13, §4.8.14 & WCAG 2.2 SC 1.1.1, SC 2.1.1, SC 2.4.4)."""

    def test_orphaned_area_rejected(self):
        body = '<p>Diagram</p><area shape="default">'
        errs = build.check_map_and_area_integrity("test-page", body)
        self.assertTrue(any("orphaned <area> element found outside <map> container" in e for e in errs))

    def test_void_area_with_end_tag_and_content_rejected(self):
        body = '<map name="site-map"><area shape="rect">Hotspot Text</area></map>'
        errs = build.check_map_and_area_integrity("test-page", body)
        self.assertTrue(any("void element <area> must not contain inner content" in e for e in errs))

    def test_void_area_with_empty_end_tag_rejected(self):
        body = '<map name="site-map"><area shape="rect"></area></map>'
        errs = build.check_map_and_area_integrity("test-page", body)
        self.assertTrue(any("void element <area> must not have an end tag" in e for e in errs))

    def test_map_missing_name_rejected(self):
        body = '<map><area shape="default"></map>'
        errs = build.check_map_and_area_integrity("test-page", body)
        self.assertTrue(any("<map> element missing required non-empty 'name' attribute" in e for e in errs))

    def test_map_empty_name_rejected(self):
        body = '<map name="   "><area shape="default"></map>'
        errs = build.check_map_and_area_integrity("test-page", body)
        self.assertTrue(any("<map> element missing required non-empty 'name' attribute" in e for e in errs))

    def test_interactive_area_missing_alt_rejected(self):
        body = '<map name="m1"><area href="/docs" shape="rect" coords="0,0,10,10"></map>'
        errs = build.check_map_and_area_integrity("test-page", body)
        self.assertTrue(any("interactive <area href='...'> missing required non-empty 'alt' attribute" in e for e in errs))

    def test_interactive_area_empty_alt_rejected(self):
        body = '<map name="m1"><area href="/docs" alt="   " shape="rect" coords="0,0,10,10"></map>'
        errs = build.check_map_and_area_integrity("test-page", body)
        self.assertTrue(any("interactive <area href='...'> missing required non-empty 'alt' attribute" in e for e in errs))

    def test_non_interactive_area_with_alt_rejected(self):
        body = '<map name="m1"><area shape="rect" coords="0,0,10,10" alt="Inert region"></map>'
        errs = build.check_map_and_area_integrity("test-page", body)
        self.assertTrue(any("non-interactive <area> (without href) must have empty alt='' or omit alt" in e for e in errs))

    def test_area_invalid_shape_rejected(self):
        body = '<map name="m1"><area shape="octagon" coords="0,0,10,10"></map>'
        errs = build.check_map_and_area_integrity("test-page", body)
        self.assertTrue(any("declares invalid shape='octagon'" in e for e in errs))

    def test_area_rect_invalid_coords_rejected(self):
        body = '<map name="m1"><area shape="rect" coords="0,0,10"></map>'
        errs = build.check_map_and_area_integrity("test-page", body)
        self.assertTrue(any("<area shape='rect'> coords='0,0,10' requires exactly 4 coordinates" in e for e in errs))

    def test_area_circle_invalid_coords_rejected(self):
        body = '<map name="m1"><area shape="circle" coords="10,20"></map>'
        errs = build.check_map_and_area_integrity("test-page", body)
        self.assertTrue(any("<area shape='circle'> coords='10,20' requires exactly 3 coordinates" in e for e in errs))

    def test_area_circle_zero_radius_rejected(self):
        body = '<map name="m1"><area shape="circle" coords="10,20,0"></map>'
        errs = build.check_map_and_area_integrity("test-page", body)
        self.assertTrue(any("<area shape='circle'> radius must be greater than zero" in e for e in errs))

    def test_area_poly_odd_coords_rejected(self):
        body = '<map name="m1"><area shape="poly" coords="0,0,10,10,20"></map>'
        errs = build.check_map_and_area_integrity("test-page", body)
        self.assertTrue(any("<area shape='poly'> coords='0,0,10,10,20' requires at least 6 coordinates in even (x, y) pairs" in e for e in errs))

    def test_valid_map_and_area_pass(self):
        body = (
            '<map name="overview-map">'
            '  <area shape="rect" coords="0,0,50,50" href="/section-a" alt="Section A overview">'
            '  <area shape="circle" coords="100,100,25" href="/section-b" alt="Section B details">'
            '  <area shape="poly" coords="0,0,20,0,20,20,0,20,0,0,10,10" href="/section-c" alt="Section C boundary">'
            '  <area shape="default">'
            '</map>'
        )
        errs = build.check_map_and_area_integrity("test-page", body)
        self.assertEqual(errs, [])


class ColgroupAndColIntegrityTests(unittest.TestCase):
    """Enforce HTML5 <colgroup> and <col> table elements for containment, sequence, span attributes, and void syntax (HTML5 §4.9.3, §4.9.4 & WCAG 2.2 SC 1.3.1)."""

    def test_orphaned_col_rejected(self):
        body = '<p>Table description</p><col span="1">'
        errs = build.check_colgroup_and_col_integrity("test-page", body)
        self.assertTrue(any("orphaned <col> element found outside <table>" in e for e in errs))

    def test_orphaned_colgroup_rejected(self):
        body = '<p>Table description</p><colgroup><col></colgroup>'
        errs = build.check_colgroup_and_col_integrity("test-page", body)
        self.assertTrue(any("orphaned <colgroup> element found outside <table>" in e for e in errs))

    def test_void_col_with_end_tag_and_content_rejected(self):
        body = '<table><colgroup><col>Span text</col></colgroup></table>'
        errs = build.check_colgroup_and_col_integrity("test-page", body)
        self.assertTrue(any("void element <col> must not contain inner content" in e for e in errs))

    def test_void_col_with_empty_end_tag_rejected(self):
        body = '<table><colgroup><col></col></colgroup></table>'
        errs = build.check_colgroup_and_col_integrity("test-page", body)
        self.assertTrue(any("void element <col> must not have an end tag" in e for e in errs))

    def test_colgroup_span_with_child_cols_rejected(self):
        body = '<table><colgroup span="2"><col><col></colgroup><tbody><tr><td>A</td><td>B</td></tr></tbody></table>'
        errs = build.check_colgroup_and_col_integrity("test-page", body)
        self.assertTrue(any("<colgroup> must not declare 'span' attribute when containing child <col> elements" in e for e in errs))

    def test_colgroup_invalid_span_rejected(self):
        body = '<table><colgroup span="0"></colgroup><tbody><tr><td>A</td></tr></tbody></table>'
        errs = build.check_colgroup_and_col_integrity("test-page", body)
        self.assertTrue(any("<colgroup> span='0' must be a positive integer >= 1" in e for e in errs))

    def test_col_invalid_span_rejected(self):
        body = '<table><colgroup><col span="-2"></colgroup><tbody><tr><td>A</td></tr></tbody></table>'
        errs = build.check_colgroup_and_col_integrity("test-page", body)
        self.assertTrue(any("<col> span='-2' must be a positive integer >= 1" in e for e in errs))

    def test_colgroup_after_table_rows_rejected(self):
        body = '<table><tr><td>A</td></tr><colgroup><col></colgroup></table>'
        errs = build.check_colgroup_and_col_integrity("test-page", body)
        self.assertTrue(any("<colgroup> must appear before table rows, thead, tbody, or tfoot" in e for e in errs))

    def test_colgroup_forbidden_child_rejected(self):
        body = '<table><colgroup><div>Not permitted</div></colgroup><tbody><tr><td>A</td></tr></tbody></table>'
        errs = build.check_colgroup_and_col_integrity("test-page", body)
        self.assertTrue(any("<colgroup> contains forbidden child <div>" in e for e in errs))

    def test_valid_colgroup_with_cols_pass(self):
        body = (
            '<table>'
            '  <colgroup>'
            '    <col span="1">'
            '    <col class="col-highlight">'
            '  </colgroup>'
            '  <thead><tr><th>ID</th><th>Value</th></tr></thead>'
            '  <tbody><tr><td>1</td><td>100</td></tr></tbody>'
            '</table>'
        )
        errs = build.check_colgroup_and_col_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_valid_colgroup_with_span_only_pass(self):
        body = (
            '<table>'
            '  <colgroup span="2"></colgroup>'
            '  <tbody><tr><td>1</td><td>2</td></tr></tbody>'
            '</table>'
        )
        errs = build.check_colgroup_and_col_integrity("test-page", body)
        self.assertEqual(errs, [])


class AriaControlsIntegrityTests(unittest.TestCase):
    """Enforce ARIA aria-controls target existence, no duplicates, and no self-reference (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def test_empty_aria_controls_rejected(self):
        body = '<button aria-controls="">Expand Panel</button>'
        errs = build.check_aria_controls_target_and_token_integrity("test-page", body)
        self.assertTrue(any("declares empty or whitespace-only 'aria-controls' attribute" in e for e in errs))

    def test_whitespace_aria_controls_rejected(self):
        body = '<button aria-controls="   ">Expand Panel</button>'
        errs = build.check_aria_controls_target_and_token_integrity("test-page", body)
        self.assertTrue(any("declares empty or whitespace-only 'aria-controls' attribute" in e for e in errs))

    def test_duplicate_aria_controls_token_rejected(self):
        body = '<button aria-controls="panel1 panel1">Toggle</button><div id="panel1">Content</div>'
        errs = build.check_aria_controls_target_and_token_integrity("test-page", body)
        self.assertTrue(any("aria-controls contains duplicate token 'panel1'" in e for e in errs))

    def test_aria_controls_self_reference_rejected(self):
        body = '<div id="panel-self" aria-controls="panel-self">Content</div>'
        errs = build.check_aria_controls_target_and_token_integrity("test-page", body)
        self.assertTrue(any("aria-controls references own element id 'panel-self'" in e for e in errs))

    def test_aria_controls_nonexistent_target_rejected(self):
        body = '<button aria-controls="missing-panel">Toggle</button>'
        errs = build.check_aria_controls_target_and_token_integrity("test-page", body)
        self.assertTrue(any("targets non-existent element id 'missing-panel' on page" in e for e in errs))

    def test_valid_aria_controls_single_target_passes(self):
        body = '<button aria-controls="panel-a">Toggle</button><div id="panel-a">Content A</div>'
        errs = build.check_aria_controls_target_and_token_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_valid_aria_controls_multi_target_passes(self):
        body = '<button aria-controls="panel-x panel-y">Toggle All</button><div id="panel-x">X</div><div id="panel-y">Y</div>'
        errs = build.check_aria_controls_target_and_token_integrity("test-page", body)
        self.assertEqual(errs, [])


class PopoverAttributeAndTargetIntegrityTests(unittest.TestCase):
    """Enforce HTML5 Popover API attributes, button invocation, and target validation (HTML5 §4.12.6, §4.10.18.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def test_invalid_popover_value_rejected(self):
        body = '<div id="pop1" popover="modal">Content</div>'
        errs = build.check_popover_attribute_and_target_integrity("test-page", body)
        self.assertTrue(any("declares invalid popover='modal'" in e for e in errs))

    def test_popovertarget_on_non_button_rejected(self):
        body = '<a href="#pop1" popovertarget="pop1">Trigger</a><div id="pop1" popover>Content</div>'
        errs = build.check_popover_attribute_and_target_integrity("test-page", body)
        self.assertTrue(any("declares popovertarget attribute on non-button element" in e for e in errs))

    def test_empty_popovertarget_rejected(self):
        body = '<button popovertarget="">Trigger</button>'
        errs = build.check_popover_attribute_and_target_integrity("test-page", body)
        self.assertTrue(any("declares empty or whitespace-only 'popovertarget' attribute" in e for e in errs))

    def test_popovertarget_self_reference_rejected(self):
        body = '<button id="btn1" popovertarget="btn1" popover>Trigger</button>'
        errs = build.check_popover_attribute_and_target_integrity("test-page", body)
        self.assertTrue(any("popovertarget references own element id 'btn1'" in e for e in errs))

    def test_popovertarget_nonexistent_id_rejected(self):
        body = '<button popovertarget="ghost-pop">Trigger</button>'
        errs = build.check_popover_attribute_and_target_integrity("test-page", body)
        self.assertTrue(any("popovertarget='ghost-pop' targets non-existent element id on page" in e for e in errs))

    def test_popovertarget_targets_element_missing_popover_attribute_rejected(self):
        body = '<button popovertarget="standard-box">Trigger</button><div id="standard-box">Content</div>'
        errs = build.check_popover_attribute_and_target_integrity("test-page", body)
        self.assertTrue(any("targets element missing 'popover' attribute" in e for e in errs))

    def test_invalid_popovertargetaction_rejected(self):
        body = '<button popovertarget="pop1" popovertargetaction="dance">Trigger</button><div id="pop1" popover>Content</div>'
        errs = build.check_popover_attribute_and_target_integrity("test-page", body)
        self.assertTrue(any("declares invalid popovertargetaction='dance'" in e for e in errs))

    def test_valid_popover_and_triggers_pass(self):
        body = (
            '<button popovertarget="help-dialog" popovertargetaction="toggle">Help</button>'
            '<div id="help-dialog" popover="auto">'
            '  <p>Help content</p>'
            '  <button popovertarget="help-dialog" popovertargetaction="hide">Close</button>'
            '</div>'
        )
        errs = build.check_popover_attribute_and_target_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_valid_input_button_trigger_passes(self):
        body = (
            '<input type="button" popovertarget="info-box" value="Info">'
            '<div id="info-box" popover="manual"><p>Information details</p></div>'
        )
        errs = build.check_popover_attribute_and_target_integrity("test-page", body)
        self.assertEqual(errs, [])

    def test_check_page_integrates_map_colgroup_controls_and_popover_linters(self):
        # 1. map/area integration
        m1 = meta('<area shape="default">')
        m1["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m1['body']}"
        errs1 = build.check_page(m1, "")
        self.assertTrue(any("orphaned <area> element found outside <map> container" in e for e in errs1))

        # 2. colgroup/col integration
        m2 = meta('<col span="1">')
        m2["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m2['body']}"
        errs2 = build.check_page(m2, "")
        self.assertTrue(any("orphaned <col> element found outside <table>" in e for e in errs2))

        # 3. aria-controls integration
        m3 = meta('<button aria-controls="nonexistent-target">Click</button>')
        m3["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m3['body']}"
        errs3 = build.check_page(m3, "")
        self.assertTrue(any("targets non-existent element id 'nonexistent-target' on page" in e for e in errs3))

        # 4. popover integration
        m4 = meta('<div id="p-bad" popover="invalid-popover">Bad</div>')
        m4["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m4['body']}"
        errs4 = build.check_page(m4, "")
        self.assertTrue(any("declares invalid popover='invalid-popover'" in e for e in errs4))


class Spec05ArtworkAndMediaAuditTests(unittest.TestCase):
    """Enforce Spec 05 artwork and media direction invariants across all site assets and markup."""

    def test_all_site_images_under_300kb(self):
        img_dir = build.ASSETS / "img"
        self.assertTrue(img_dir.exists(), f"Expected {img_dir} to exist")
        oversized = []
        for img_path in img_dir.glob("*"):
            if img_path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                sz = img_path.stat().st_size
                if sz > 300 * 1024:
                    oversized.append(f"{img_path.name} ({sz / 1024:.1f} KB)")
        self.assertEqual(oversized, [], f"Images exceeding 300 KB budget: {oversized}")

    def test_all_content_img_tags_have_explicit_dimensions(self):
        img_pattern = re.compile(r'<img\b([^>]*)>', re.IGNORECASE)
        missing_dims = []
        for html_file in build.CONTENT.rglob("*.html"):
            content = html_file.read_text(encoding="utf-8")
            for m in img_pattern.finditer(content):
                attrs = m.group(1)
                has_w = bool(re.search(r'\bwidth=["\']\d+["\']', attrs))
                has_h = bool(re.search(r'\bheight=["\']\d+["\']', attrs))
                if not (has_w and has_h):
                    src_m = re.search(r'\bsrc=["\']([^"\']+)["\']', attrs)
                    src = src_m.group(1) if src_m else "<unknown>"
                    missing_dims.append(f"{html_file.name}: img src={src}")
        self.assertEqual(missing_dims, [], f"Content <img> tags missing explicit width/height: {missing_dims}")

    def test_all_content_img_tags_have_descriptive_alt(self):
        img_pattern = re.compile(r'<img\b([^>]*)>', re.IGNORECASE)
        short_alts = []
        for html_file in build.CONTENT.rglob("*.html"):
            content = html_file.read_text(encoding="utf-8")
            for m in img_pattern.finditer(content):
                attrs = m.group(1)
                alt_m = re.search(r'\balt=["\']([^"\']*)["\']', attrs)
                alt = alt_m.group(1) if alt_m else ""
                if len(alt.strip()) < 15:
                    src_m = re.search(r'\bsrc=["\']([^"\']+)["\']', attrs)
                    src = src_m.group(1) if src_m else "<unknown>"
                    short_alts.append(f"{html_file.name}: img src={src} (alt={alt!r})")
        self.assertEqual(short_alts, [], f"Content <img> tags with alt text < 15 chars: {short_alts}")

    def test_all_content_explainer_figures_contract(self):
        fig_re = re.compile(r'(<figure\b[^>]*\bclass=["\'][^"\']*\bexplainer\b[^"\']*["\'][^>]*>)(.*?)</figure>', re.IGNORECASE | re.DOTALL)
        for html_file in build.CONTENT.rglob("*.html"):
            content = html_file.read_text(encoding="utf-8")
            for open_tag, inner in fig_re.findall(content):
                id_m = re.search(r'\bid=["\'](ex-[a-z0-9-]+)["\']', open_tag, re.IGNORECASE)
                self.assertIsNotNone(id_m, f"{html_file.name}: explainer figure missing valid id='ex-<slug>'")
                self.assertIn("<svg", inner, f"{html_file.name}: explainer figure missing inline <svg>")
                self.assertIn("viewBox=", inner, f"{html_file.name}: explainer <svg> missing viewBox")
                self.assertIn("<figcaption", inner, f"{html_file.name}: explainer missing <figcaption>")

    def test_all_inline_explainer_svgs_are_valid_xml(self):
        """Spec 05 Artwork & Media Audit: All inline explainer <svg> elements must be well-formed XML without parse errors."""
        errors = []
        svg_pattern = re.compile(r'(<svg\b[^>]*>.*?</svg>)', re.IGNORECASE | re.DOTALL)
        for html_file in build.CONTENT.rglob("*.html"):
            content = html_file.read_text(encoding="utf-8")
            for idx, svg_str in enumerate(svg_pattern.findall(content)):
                try:
                    ET.fromstring(svg_str)
                except Exception as e:
                    errors.append(f"{html_file.name} svg #{idx}: {e}")
        self.assertEqual(errors, [], f"Inline SVGs with XML parse errors: {errors}")

    def test_explainer_svg_xml_malformed_rejected(self):
        """Verify that malformed XML entities inside an inline SVG are detected and rejected by XML parser."""
        malformed_svg = '<svg viewBox="0 0 100 100"><text>Unescaped & ampersand</text></svg>'
        with self.assertRaises(ET.ParseError):
            ET.fromstring(malformed_svg)


class ObsoletePresentationalElementsExtendedTests(unittest.TestCase):
    """Verify that obsolete non-conforming HTML elements are strictly rejected (HTML5 §11.2 / HTML Living Standard §16 / WCAG 2.2 SC 1.3.1)."""

    def test_extended_obsolete_elements_rejected(self):
        obsolete_tags = [
            "frame", "frameset", "noframes", "noembed", "keygen",
            "isindex", "bgsound", "listing", "xmp", "plaintext",
            "font", "center", "strike", "tt", "big", "acronym", "applet", "basefont", "dir"
        ]
        for tag in obsolete_tags:
            snippet = f"<div><{tag}>Obsolete content</{tag}></div>"
            errs = build.check_obsolete_presentational_elements("test-obsolete", snippet)
            self.assertTrue(
                any(f"<{tag}> is forbidden" in e for e in errs),
                f"Expected rejection for obsolete element <{tag}>, got: {errs}"
            )

    def test_semantic_html_passes_obsolete_check(self):
        snippet = "<main><article><section><h1>Title</h1><p>Clean semantic body.</p></section></article></main>"
        errs = build.check_obsolete_presentational_elements("test-clean", snippet)
        self.assertEqual(errs, [])


class MediaPreloadPosterAndDetailsAccordionIntegrityTests(unittest.TestCase):
    """Verify media preload tokens, poster image asset integrity, and details accordion name groups (WHATWG HTML §4.8.9, §4.8.10, §4.11.1 & WCAG 2.2 SC 1.1.1, SC 1.2.2)."""

    def test_valid_video_and_audio_preload_pass(self):
        valid_snippets = [
            '<video controls preload="none"><source src="clip.mp4"></video>',
            '<video controls preload="metadata"><source src="clip.mp4"></video>',
            '<video controls preload="auto"><source src="clip.mp4"></video>',
            '<video controls preload=""><source src="clip.mp4"></video>',
            '<audio controls preload="metadata"><source src="clip.mp3"></audio>',
        ]
        for snippet in valid_snippets:
            errs = build.check_media_preload_and_poster_integrity("test-media-valid", snippet)
            self.assertEqual(errs, [], f"Expected clean pass for '{snippet}', got: {errs}")

    def test_invalid_preload_tokens_rejected(self):
        invalid_tokens = ["true", "false", "all", "preload", "invalid", "100"]
        for token in invalid_tokens:
            snippet = f'<video controls preload="{token}"><source src="clip.mp4"></video>'
            errs = build.check_media_preload_and_poster_integrity("test-media-bad-preload", snippet)
            self.assertTrue(
                any(f"invalid preload='{token}'" in e for e in errs),
                f"Expected rejection for preload='{token}', got: {errs}"
            )

    def test_valid_video_poster_with_existing_asset_passes(self):
        # hero-commons.jpg exists in assets/img/
        snippet = '<video controls preload="metadata" poster="/assets/img/hero-commons.jpg"><source src="clip.mp4"></video>'
        errs = build.check_media_preload_and_poster_integrity("test-valid-poster", snippet)
        self.assertEqual(errs, [])

    def test_missing_local_poster_asset_rejected(self):
        snippet = '<video controls poster="/assets/img/nonexistent-missing-sample-image.jpg"><source src="clip.mp4"></video>'
        errs = build.check_media_preload_and_poster_integrity("test-missing-poster", snippet)
        self.assertTrue(
            any("references missing image asset" in e for e in errs),
            f"Expected missing asset error, got: {errs}"
        )

    def test_empty_or_insecure_poster_rejected(self):
        # Empty poster
        errs_empty = build.check_media_preload_and_poster_integrity(
            "test-empty-poster", '<video controls poster=""><source src="clip.mp4"></video>'
        )
        self.assertTrue(any("empty poster attribute" in e for e in errs_empty))

        # Insecure HTTP poster
        errs_http = build.check_media_preload_and_poster_integrity(
            "test-http-poster", '<video controls poster="http://insecure.example.com/poster.jpg"><source src="clip.mp4"></video>'
        )
        self.assertTrue(any("unencrypted http:// URL" in e for e in errs_http))

        # Prohibited script or data URI poster
        errs_js = build.check_media_preload_and_poster_integrity(
            "test-js-poster", '<video controls poster="javascript:alert(1)"><source src="clip.mp4"></video>'
        )
        self.assertTrue(any("prohibited script or data URI" in e for e in errs_js))

    def test_audio_poster_rejected(self):
        snippet = '<audio controls poster="/assets/img/hero-commons.jpg"><source src="clip.mp3"></audio>'
        errs = build.check_media_preload_and_poster_integrity("test-audio-poster", snippet)
        self.assertTrue(
            any("<audio> element does not support 'poster' attribute" in e for e in errs),
            f"Expected audio poster rejection, got: {errs}"
        )

    def test_valid_details_accordion_name_passes(self):
        valid_snippets = [
            "<details><summary>Plain Details</summary><p>Content</p></details>",
            '<details name="faq-group"><summary>FAQ 1</summary><p>Content</p></details>',
            '<details name="pricing_options"><summary>Plan A</summary><p>Content</p></details>',
        ]
        for snippet in valid_snippets:
            errs = build.check_details_accordion_name_integrity("test-details-valid", snippet)
            self.assertEqual(errs, [], f"Expected clean pass for '{snippet}', got: {errs}")

    def test_invalid_details_accordion_name_rejected(self):
        # Empty name
        errs_empty = build.check_details_accordion_name_integrity(
            "test-empty-name", '<details name=""><summary>Summary</summary><p>Content</p></details>'
        )
        self.assertTrue(any("empty name attribute" in e for e in errs_empty))

        # Whitespace in name
        errs_ws = build.check_details_accordion_name_integrity(
            "test-ws-name", '<details name="faq group"><summary>Summary</summary><p>Content</p></details>'
        )
        self.assertTrue(any("invalid whitespace in group name" in e for e in errs_ws))

        # Prohibited control characters in name
        errs_ctrl = build.check_details_accordion_name_integrity(
            "test-ctrl-name", '<details name="faq\x00group"><summary>Summary</summary><p>Content</p></details>'
        )
        self.assertTrue(any("control characters in group name" in e for e in errs_ctrl))

        # Prohibited markup characters in name
        errs_markup = build.check_details_accordion_name_integrity(
            "test-markup-name", '<details name="faq&amp;script"><summary>Summary</summary><p>Content</p></details>'
        )
        self.assertTrue(any("prohibited markup characters in group name" in e for e in errs_markup))


class AriaDescribedbyAndDetailsIntegrityTests(unittest.TestCase):
    """Enforce ARIA aria-describedby and aria-details target existence, uniqueness, and self-reference prevention (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def test_valid_describedby_and_details_pass(self):
        html = '<p id="d1">Detail description</p><button aria-describedby="d1">Save</button><section id="det">Full details</section><article aria-details="det">Content</article>'
        self.assertEqual(build.check_aria_describedby_and_details_target_integrity("test.html", html), [])

    def test_empty_aria_describedby_rejected(self):
        html = '<button aria-describedby="">Save</button>'
        errs = build.check_aria_describedby_and_details_target_integrity("test.html", html)
        self.assertTrue(any("empty or whitespace-only 'aria-describedby'" in e for e in errs))

    def test_whitespace_aria_details_rejected(self):
        html = '<article aria-details="   ">Content</article>'
        errs = build.check_aria_describedby_and_details_target_integrity("test.html", html)
        self.assertTrue(any("empty or whitespace-only 'aria-details'" in e for e in errs))

    def test_duplicate_describedby_token_rejected(self):
        html = '<p id="desc">Note</p><button aria-describedby="desc desc">Save</button>'
        errs = build.check_aria_describedby_and_details_target_integrity("test.html", html)
        self.assertTrue(any("contains duplicate token 'desc'" in e for e in errs))

    def test_self_referencing_describedby_rejected(self):
        html = '<div id="box" aria-describedby="box">Text</div>'
        errs = build.check_aria_describedby_and_details_target_integrity("test.html", html)
        self.assertTrue(any("references own element id 'box'" in e for e in errs))

    def test_self_referencing_details_rejected(self):
        html = '<section id="sec" aria-details="sec">Text</section>'
        errs = build.check_aria_describedby_and_details_target_integrity("test.html", html)
        self.assertTrue(any("references own element id 'sec'" in e for e in errs))

    def test_nonexistent_describedby_target_rejected(self):
        html = '<button aria-describedby="missing-tip">Action</button>'
        errs = build.check_aria_describedby_and_details_target_integrity("test.html", html)
        self.assertTrue(any("targets non-existent element id 'missing-tip'" in e for e in errs))

    def test_nonexistent_details_target_rejected(self):
        html = '<article aria-details="nonexistent-analysis">Body</article>'
        errs = build.check_aria_describedby_and_details_target_integrity("test.html", html)
        self.assertTrue(any("targets non-existent element id 'nonexistent-analysis'" in e for e in errs))


class AriaFlowtoReadingFlowIntegrityTests(unittest.TestCase):
    """Enforce ARIA aria-flowto target existence, uniqueness, self-reference prevention, and acyclic flow graphs (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.2, SC 2.4.3)."""

    def test_valid_flowto_passes(self):
        html = '<div id="step1" aria-flowto="step2">Step 1</div><div id="step2">Step 2</div>'
        self.assertEqual(build.check_aria_flowto_reading_flow_integrity("test.html", html), [])

    def test_empty_aria_flowto_rejected(self):
        html = '<div aria-flowto="">Step 1</div>'
        errs = build.check_aria_flowto_reading_flow_integrity("test.html", html)
        self.assertTrue(any("empty or whitespace-only 'aria-flowto'" in e for e in errs))

    def test_whitespace_aria_flowto_rejected(self):
        html = '<div aria-flowto="  \t ">Step 1</div>'
        errs = build.check_aria_flowto_reading_flow_integrity("test.html", html)
        self.assertTrue(any("empty or whitespace-only 'aria-flowto'" in e for e in errs))

    def test_duplicate_flowto_token_rejected(self):
        html = '<div id="s1" aria-flowto="s2 s2">1</div><div id="s2">2</div>'
        errs = build.check_aria_flowto_reading_flow_integrity("test.html", html)
        self.assertTrue(any("contains duplicate token 's2'" in e for e in errs))

    def test_self_referencing_flowto_rejected(self):
        html = '<div id="loop" aria-flowto="loop">Content</div>'
        errs = build.check_aria_flowto_reading_flow_integrity("test.html", html)
        self.assertTrue(any("references own element id 'loop'" in e for e in errs))

    def test_nonexistent_flowto_target_rejected(self):
        html = '<div id="p1" aria-flowto="ghost">Start</div>'
        errs = build.check_aria_flowto_reading_flow_integrity("test.html", html)
        self.assertTrue(any("targets non-existent element id 'ghost'" in e for e in errs))

    def test_reciprocal_cycle_flowto_rejected(self):
        html = '<div id="a" aria-flowto="b">A</div><div id="b" aria-flowto="a">B</div>'
        errs = build.check_aria_flowto_reading_flow_integrity("test.html", html)
        self.assertTrue(any("reciprocal circular aria-flowto cycle" in e for e in errs))


class TableCellSpanningAndOrphanIntegrityTests(unittest.TestCase):
    """Enforce HTML5 table cell spanning (colspan, rowspan), header scopes, and orphaned table elements (HTML5 §4.9.6, §4.9.9, §4.9.10, §4.9.11 & WCAG 2.2 SC 1.3.1)."""

    def test_valid_table_passes(self):
        html = '<table><caption>Metrics</caption><thead><tr><th scope="col" colspan="2">Name</th></tr></thead><tbody><tr><td rowspan="2">Data</td><td>Val</td></tr></tbody></table>'
        self.assertEqual(build.check_table_cell_spanning_and_orphan_integrity("test.html", html), [])

    def test_orphaned_tr_rejected(self):
        html = '<p>Intro</p><tr><td>Orphan</td></tr>'
        errs = build.check_table_cell_spanning_and_orphan_integrity("test.html", html)
        self.assertTrue(any("orphaned <tr>" in e for e in errs))

    def test_orphaned_td_rejected(self):
        html = '<div><td>Orphan Cell</td></div>'
        errs = build.check_table_cell_spanning_and_orphan_integrity("test.html", html)
        self.assertTrue(any("orphaned <td>" in e for e in errs))

    def test_orphaned_th_rejected(self):
        html = '<div><th>Orphan Header</th></div>'
        errs = build.check_table_cell_spanning_and_orphan_integrity("test.html", html)
        self.assertTrue(any("orphaned <th>" in e for e in errs))

    def test_invalid_colspan_zero_rejected(self):
        html = '<table><tr><th colspan="0">Col</th></tr></table>'
        errs = build.check_table_cell_spanning_and_orphan_integrity("test.html", html)
        self.assertTrue(any("invalid colspan='0'" in e for e in errs))

    def test_invalid_colspan_negative_rejected(self):
        html = '<table><tr><td colspan="-1">Cell</td></tr></table>'
        errs = build.check_table_cell_spanning_and_orphan_integrity("test.html", html)
        self.assertTrue(any("invalid colspan='-1'" in e for e in errs))

    def test_invalid_colspan_non_numeric_rejected(self):
        html = '<table><tr><td colspan="all">Cell</td></tr></table>'
        errs = build.check_table_cell_spanning_and_orphan_integrity("test.html", html)
        self.assertTrue(any("invalid colspan='all'" in e for e in errs))

    def test_invalid_rowspan_negative_rejected(self):
        html = '<table><tr><td rowspan="-2">Cell</td></tr></table>'
        errs = build.check_table_cell_spanning_and_orphan_integrity("test.html", html)
        self.assertTrue(any("invalid rowspan='-2'" in e for e in errs))

    def test_invalid_rowspan_non_numeric_rejected(self):
        html = '<table><tr><td rowspan="many">Cell</td></tr></table>'
        errs = build.check_table_cell_spanning_and_orphan_integrity("test.html", html)
        self.assertTrue(any("invalid rowspan='many'" in e for e in errs))

    def test_invalid_th_scope_token_rejected(self):
        html = '<table><tr><th scope="header">Title</th></tr></table>'
        errs = build.check_table_cell_spanning_and_orphan_integrity("test.html", html)
        self.assertTrue(any("invalid scope='header'" in e for e in errs))

    def test_td_with_scope_rejected(self):
        html = '<table><tr><td scope="col">Data</td></tr></table>'
        errs = build.check_table_cell_spanning_and_orphan_integrity("test.html", html)
        self.assertTrue(any("scope attribute is prohibited on <td>" in e for e in errs))


class MediaSourceAndFallbackIntegrityTests(unittest.TestCase):
    """Enforce HTML5 <audio> and <video> elements for valid source definitions, non-nesting, and accessible fallback content (HTML5 §4.8.9, §4.8.10 & WCAG 2.2 SC 1.1.1, SC 1.2.1)."""

    def test_valid_audio_with_src_and_fallback_passes(self):
        html = '<audio src="/assets/audio/podcast.mp3">Download <a href="/assets/audio/podcast.mp3">podcast audio</a>.</audio>'
        self.assertEqual(build.check_media_source_and_fallback_integrity("test.html", html), [])

    def test_valid_video_with_source_child_passes(self):
        html = '<video><source src="/assets/video/intro.mp4" type="video/mp4"><p>Your browser does not support HTML5 video.</p></video>'
        self.assertEqual(build.check_media_source_and_fallback_integrity("test.html", html), [])

    def test_audio_without_source_rejected(self):
        html = '<audio>Fallback text</audio>'
        errs = build.check_media_source_and_fallback_integrity("test.html", html)
        self.assertTrue(any("media element has no playable source" in e for e in errs))

    def test_video_without_fallback_rejected(self):
        html = '<video src="/assets/video/demo.mp4"></video>'
        errs = build.check_media_source_and_fallback_integrity("test.html", html)
        self.assertTrue(any("media element missing accessible fallback content" in e for e in errs))

    def test_video_whitespace_fallback_rejected(self):
        html = '<video src="/assets/video/demo.mp4">   \n  </video>'
        errs = build.check_media_source_and_fallback_integrity("test.html", html)
        self.assertTrue(any("media element missing accessible fallback content" in e for e in errs))

    def test_nested_video_rejected(self):
        html = '<video src="/a.mp4"><video src="/b.mp4">Fallback</video></video>'
        errs = build.check_media_source_and_fallback_integrity("test.html", html)
        self.assertTrue(any("directly nests another <video>" in e for e in errs))

    def test_empty_source_src_rejected(self):
        html = '<audio><source src=""><p>Fallback</p></audio>'
        errs = build.check_media_source_and_fallback_integrity("test.html", html)
        self.assertTrue(any("missing non-empty 'src' attribute" in e for e in errs))


class AriaCurrentTokenAndContextIntegrityTests(unittest.TestCase):
    """Enforce ARIA aria-current attribute for valid enumerated tokens, non-void elements, and absence of presentational roles (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def test_valid_aria_current_tokens_pass(self):
        for token in ("page", "step", "location", "date", "time", "true", "false"):
            html = f'<nav><a href="/blog" aria-current="{token}">Current {token}</a></nav>'
            self.assertEqual(build.check_aria_current_token_and_context_integrity("test.html", html), [])

    def test_invalid_aria_current_token_rejected(self):
        for invalid in ("current", "active", "yes", "main", "selected", "1"):
            html = f'<a href="/blog" aria-current="{invalid}">Blog</a>'
            errs = build.check_aria_current_token_and_context_integrity("test.html", html)
            self.assertTrue(any("declares invalid aria-current" in e for e in errs), f"Expected rejection for '{invalid}'")

    def test_empty_aria_current_rejected(self):
        html = '<a href="/blog" aria-current="">Blog</a>'
        errs = build.check_aria_current_token_and_context_integrity("test.html", html)
        self.assertTrue(any("declares invalid aria-current" in e for e in errs))

    def test_void_element_with_aria_current_rejected(self):
        html = '<hr aria-current="page">'
        errs = build.check_aria_current_token_and_context_integrity("test.html", html)
        self.assertTrue(any("void element <hr> must not declare 'aria-current' attribute" in e for e in errs))

    def test_img_void_with_aria_current_rejected(self):
        html = '<img src="/assets/img/icon.png" alt="icon" aria-current="true">'
        errs = build.check_aria_current_token_and_context_integrity("test.html", html)
        self.assertTrue(any("void element <img> must not declare 'aria-current' attribute" in e for e in errs))

    def test_presentational_element_with_aria_current_rejected(self):
        html = '<span role="presentation" aria-current="page">Step 1</span>'
        errs = build.check_aria_current_token_and_context_integrity("test.html", html)
        self.assertTrue(any("presentational elements cannot convey state" in e for e in errs))

    def test_role_none_with_aria_current_rejected(self):
        html = '<li role="none" aria-current="step">Step 2</li>'
        errs = build.check_aria_current_token_and_context_integrity("test.html", html)
        self.assertTrue(any("presentational elements cannot convey state" in e for e in errs))


class FormSubmissionAttributesIntegrityTests(unittest.TestCase):
    """Enforce form submission attributes (formaction, formenctype, formmethod, formnovalidate, formtarget) strictly on submit buttons with valid parameters (HTML5 §4.10.18.5 & WCAG 2.2 SC 4.1.2)."""

    def test_valid_submit_button_passes(self):
        html = '<form action="/api"><button type="submit" formaction="/save" formmethod="post" formenctype="multipart/form-data" formtarget="_self">Save</button></form>'
        self.assertEqual(build.check_form_submission_attributes_integrity("test.html", html), [])

    def test_button_without_type_defaults_to_submit_passes(self):
        html = '<button formaction="/save" formmethod="dialog">Close & Save</button>'
        self.assertEqual(build.check_form_submission_attributes_integrity("test.html", html), [])

    def test_input_submit_passes(self):
        html = '<input type="submit" formaction="/submit" formmethod="get">'
        self.assertEqual(build.check_form_submission_attributes_integrity("test.html", html), [])

    def test_input_image_passes(self):
        html = '<input type="image" src="/btn.png" alt="Submit" formaction="/submit">'
        self.assertEqual(build.check_form_submission_attributes_integrity("test.html", html), [])

    def test_button_type_button_with_form_attr_rejected(self):
        html = '<button type="button" formaction="/action">Click</button>'
        errs = build.check_form_submission_attributes_integrity("test.html", html)
        self.assertTrue(any("<button type='button'> must not declare form submission attribute 'formaction'" in e for e in errs))

    def test_button_type_reset_with_form_attr_rejected(self):
        html = '<button type="reset" formmethod="post">Reset</button>'
        errs = build.check_form_submission_attributes_integrity("test.html", html)
        self.assertTrue(any("<button type='reset'> must not declare form submission attribute 'formmethod'" in e for e in errs))

    def test_input_text_with_form_attr_rejected(self):
        html = '<input type="text" formaction="/search">'
        errs = build.check_form_submission_attributes_integrity("test.html", html)
        self.assertTrue(any("<input type='text'> must not declare form submission attribute 'formaction'" in e for e in errs))

    def test_div_with_form_attr_rejected(self):
        html = '<div formaction="/save">Fake submit</div>'
        errs = build.check_form_submission_attributes_integrity("test.html", html)
        self.assertTrue(any("<div> must not declare form submission attribute 'formaction'" in e for e in errs))

    def test_empty_formaction_rejected(self):
        html = '<button type="submit" formaction="">Submit</button>'
        errs = build.check_form_submission_attributes_integrity("test.html", html)
        self.assertTrue(any("declares empty or whitespace-only 'formaction' attribute" in e for e in errs))

    def test_invalid_formenctype_rejected(self):
        html = '<button type="submit" formenctype="application/json">Submit</button>'
        errs = build.check_form_submission_attributes_integrity("test.html", html)
        self.assertTrue(any("declares invalid formenctype='application/json'" in e for e in errs))

    def test_invalid_formmethod_rejected(self):
        html = '<button type="submit" formmethod="put">Submit</button>'
        errs = build.check_form_submission_attributes_integrity("test.html", html)
        self.assertTrue(any("declares invalid formmethod='put'" in e for e in errs))

    def test_empty_formtarget_rejected(self):
        html = '<button type="submit" formtarget="   ">Submit</button>'
        errs = build.check_form_submission_attributes_integrity("test.html", html)
        self.assertTrue(any("declares empty or whitespace-only 'formtarget' attribute" in e for e in errs))


class DialogHierarchyAndActionIntegrityTests(unittest.TestCase):
    """Enforce <dialog> non-nesting, role override restrictions, and keyboard-focusable controls (HTML5 §4.11.4 & WCAG 2.2 SC 2.1.2, SC 2.4.3, SC 4.1.2)."""

    def test_valid_dialog_with_button_passes(self):
        html = '<dialog id="d1"><p>Notice text</p><button type="button">Dismiss</button></dialog>'
        self.assertEqual(build.check_dialog_element_hierarchy_and_action_integrity("test.html", html), [])

    def test_valid_dialog_with_link_passes(self):
        html = '<dialog id="d2"><h2>Update Available</h2><a href="/download">Download now</a></dialog>'
        self.assertEqual(build.check_dialog_element_hierarchy_and_action_integrity("test.html", html), [])

    def test_valid_dialog_with_tabindex_passes(self):
        html = '<dialog id="d3"><p>Custom control</p><span tabindex="0" role="button">Close</span></dialog>'
        self.assertEqual(build.check_dialog_element_hierarchy_and_action_integrity("test.html", html), [])

    def test_empty_dialog_passes(self):
        html = '<dialog id="d_empty"></dialog>'
        self.assertEqual(build.check_dialog_element_hierarchy_and_action_integrity("test.html", html), [])

    def test_nested_dialog_rejected(self):
        html = '<dialog id="d_outer"><p>Outer</p><button>Close</button><dialog id="d_inner"><button>Sub</button></dialog></dialog>'
        errs = build.check_dialog_element_hierarchy_and_action_integrity("test.html", html)
        self.assertTrue(any("must not be nested inside ancestor <dialog>" in e for e in errs))

    def test_dialog_invalid_role_override_rejected(self):
        html = '<dialog role="region"><p>Dialog body</p><button>OK</button></dialog>'
        errs = build.check_dialog_element_hierarchy_and_action_integrity("test.html", html)
        self.assertTrue(any("declares invalid role override" in e for e in errs))

    def test_dialog_valid_alertdialog_role_passes(self):
        html = '<dialog role="alertdialog"><p>Alert!</p><button>Acknowledge</button></dialog>'
        self.assertEqual(build.check_dialog_element_hierarchy_and_action_integrity("test.html", html), [])

    def test_dialog_with_content_lacking_focusable_control_rejected(self):
        html = '<dialog id="trapped"><p>You cannot dismiss or escape this dialog without a mouse or developer console.</p></dialog>'
        errs = build.check_dialog_element_hierarchy_and_action_integrity("test.html", html)
        self.assertTrue(any("contains content but lacks any keyboard-focusable controls or dismiss actions" in e for e in errs))


class HiddenAttributeAndConflictIntegrityTests(unittest.TestCase):
    """Enforce hidden attribute usage avoiding deceptive truthy values, conflicting aria-hidden='false', and autofocus (HTML5 §3.2.8.2 & WCAG 2.2 SC 1.3.1, SC 2.4.3, SC 4.1.2)."""

    def test_valid_boolean_hidden_passes(self):
        html = '<div hidden><p>Hidden text</p></div>'
        self.assertEqual(build.check_hidden_attribute_and_conflict_integrity("test.html", html), [])

    def test_valid_empty_hidden_passes(self):
        html = '<section hidden=""><p>Hidden section</p></section>'
        self.assertEqual(build.check_hidden_attribute_and_conflict_integrity("test.html", html), [])

    def test_valid_hidden_value_passes(self):
        html = '<aside hidden="hidden"><p>Hidden aside</p></aside>'
        self.assertEqual(build.check_hidden_attribute_and_conflict_integrity("test.html", html), [])

    def test_valid_until_found_hidden_passes(self):
        html = '<details hidden="until-found"><p>Searchable hidden details</p></details>'
        self.assertEqual(build.check_hidden_attribute_and_conflict_integrity("test.html", html), [])

    def test_deceptive_hidden_false_rejected(self):
        html = '<div hidden="false"><p>Visible text</p></div>'
        errs = build.check_hidden_attribute_and_conflict_integrity("test.html", html)
        self.assertTrue(any("declares deceptive truthy hidden='false'" in e for e in errs))

    def test_deceptive_hidden_no_rejected(self):
        html = '<p hidden="no">Text</p>'
        errs = build.check_hidden_attribute_and_conflict_integrity("test.html", html)
        self.assertTrue(any("declares deceptive truthy hidden='no'" in e for e in errs))

    def test_invalid_hidden_true_rejected(self):
        html = '<div hidden="true"><p>Text</p></div>'
        errs = build.check_hidden_attribute_and_conflict_integrity("test.html", html)
        self.assertTrue(any("declares invalid hidden='true'" in e for e in errs))

    def test_conflicting_hidden_and_aria_hidden_false_rejected(self):
        html = '<div hidden aria-hidden="false"><p>Conflicting states</p></div>'
        errs = build.check_hidden_attribute_and_conflict_integrity("test.html", html)
        self.assertTrue(any("declares conflicting visibility states with both hidden and aria-hidden='false'" in e for e in errs))

    def test_hidden_with_autofocus_rejected(self):
        html = '<input type="text" hidden autofocus>'
        errs = build.check_hidden_attribute_and_conflict_integrity("test.html", html)
        self.assertTrue(any("must not declare autofocus on a hidden element" in e for e in errs))


class MediaControlsListAndCrossOriginIntegrityTests(unittest.TestCase):
    """Enforce valid crossorigin, controlslist, and disableremoteplayback attributes (HTML5 §4.8.9, §4.8.10, §4.8.16 & WCAG 2.2 SC 4.1.2)."""

    def test_valid_crossorigin_tokens_pass(self):
        html = '<img src="/test.jpg" alt="Test image" crossorigin="anonymous"><video src="/vid.mp4" crossorigin="use-credentials"><p>Fallback</p></video>'
        self.assertEqual(build.check_media_controlslist_and_crossorigin_integrity("test.html", html), [])

    def test_empty_crossorigin_attribute_passes(self):
        html = '<img src="/test.jpg" alt="Test image" crossorigin>'
        self.assertEqual(build.check_media_controlslist_and_crossorigin_integrity("test.html", html), [])

    def test_invalid_crossorigin_token_rejected(self):
        html = '<img src="/test.jpg" alt="Test image" crossorigin="cors">'
        errs = build.check_media_controlslist_and_crossorigin_integrity("test.html", html)
        self.assertTrue(any("declares invalid crossorigin='cors'" in e for e in errs))

    def test_valid_controlslist_tokens_pass(self):
        html = '<video src="/vid.mp4" controlslist="nodownload nofullscreen"><p>Fallback</p></video>'
        self.assertEqual(build.check_media_controlslist_and_crossorigin_integrity("test.html", html), [])

    def test_empty_controlslist_rejected(self):
        html = '<audio src="/audio.mp3" controlslist="   "><p>Fallback</p></audio>'
        errs = build.check_media_controlslist_and_crossorigin_integrity("test.html", html)
        self.assertTrue(any("declares empty or whitespace-only 'controlslist' attribute" in e for e in errs))

    def test_invalid_controlslist_token_rejected(self):
        html = '<video src="/vid.mp4" controlslist="nocontrols"><p>Fallback</p></video>'
        errs = build.check_media_controlslist_and_crossorigin_integrity("test.html", html)
        self.assertTrue(any("declares invalid controlslist token 'nocontrols'" in e for e in errs))

    def test_duplicate_controlslist_token_rejected(self):
        html = '<video src="/vid.mp4" controlslist="nodownload nodownload"><p>Fallback</p></video>'
        errs = build.check_media_controlslist_and_crossorigin_integrity("test.html", html)
        self.assertTrue(any("declares duplicate controlslist token 'nodownload'" in e for e in errs))

    def test_deceptive_disableremoteplayback_false_rejected(self):
        html = '<video src="/vid.mp4" disableremoteplayback="false"><p>Fallback</p></video>'
        errs = build.check_media_controlslist_and_crossorigin_integrity("test.html", html)
        self.assertTrue(any("declares deceptive truthy disableremoteplayback='false'" in e for e in errs))


class FigureAndFigcaptionHierarchyIntegrityTests(unittest.TestCase):
    """Enforce <figure> child ordering: <figcaption> as first or last child and non-nesting (HTML5 §4.4.12, §4.4.13 & WCAG 2.2 SC 1.3.1)."""

    def test_valid_first_figcaption_passes(self):
        html = '<figure><figcaption>Caption text</figcaption><img src="/img.jpg" alt="Figure image"></figure>'
        self.assertEqual(build.check_figure_and_figcaption_hierarchy_integrity("test.html", html), [])

    def test_valid_last_figcaption_passes(self):
        html = '<figure><img src="/img.jpg" alt="Figure image"><figcaption>Caption text</figcaption></figure>'
        self.assertEqual(build.check_figure_and_figcaption_hierarchy_integrity("test.html", html), [])

    def test_invalid_middle_figcaption_sandwich_rejected(self):
        html = '<figure><p>Leading paragraph</p><figcaption>Caption text</figcaption><p>Trailing paragraph</p></figure>'
        errs = build.check_figure_and_figcaption_hierarchy_integrity("test.html", html)
        self.assertTrue(any("<figcaption> must be either the first or last element child of <figure>" in e for e in errs))

    def test_nested_figcaption_rejected(self):
        html = '<figure><figcaption>Outer <figcaption>Inner</figcaption></figcaption></figure>'
        errs = build.check_figure_and_figcaption_hierarchy_integrity("test.html", html)
        self.assertTrue(any("nested <figcaption> inside <figcaption>" in e for e in errs))

    def test_figure_nested_inside_figcaption_rejected(self):
        html = '<figure><figcaption>Text <figure><img src="/x.jpg" alt="x"></figure></figcaption></figure>'
        errs = build.check_figure_and_figcaption_hierarchy_integrity("test.html", html)
        self.assertTrue(any("<figure> must not be nested inside <figcaption>" in e for e in errs))


class OutputElementFormAndNameIntegrityTests(unittest.TestCase):
    """Enforce <output> non-empty name and valid form owner references (HTML5 §4.10.19 & WCAG 2.2 SC 4.1.2, SC 1.3.1)."""

    def test_valid_output_passes(self):
        html = '<form id="calc-form"><output name="total">0</output></form>'
        self.assertEqual(build.check_output_element_form_and_name_integrity("test.html", html), [])

    def test_valid_output_with_external_form_passes(self):
        html = '<form id="form-a"></form><output form="form-a" name="res">Result</output>'
        self.assertEqual(build.check_output_element_form_and_name_integrity("test.html", html), [])

    def test_output_empty_name_rejected(self):
        html = '<output name="   ">Result</output>'
        errs = build.check_output_element_form_and_name_integrity("test.html", html)
        self.assertTrue(any("<output> declares empty or whitespace-only 'name' attribute" in e for e in errs))

    def test_output_empty_form_rejected(self):
        html = '<output form="">Result</output>'
        errs = build.check_output_element_form_and_name_integrity("test.html", html)
        self.assertTrue(any("<output> declares empty or whitespace-only 'form' attribute" in e for e in errs))

    def test_output_dangling_form_id_rejected(self):
        html = '<output form="missing-form">Result</output>'
        errs = build.check_output_element_form_and_name_integrity("test.html", html)
        self.assertTrue(any("references non-existent element id 'missing-form'" in e for e in errs))

    def test_output_form_targeting_non_form_rejected(self):
        html = '<div id="not-a-form"></div><output form="not-a-form">Result</output>'
        errs = build.check_output_element_form_and_name_integrity("test.html", html)
        self.assertTrue(any("which is not a <form>" in e for e in errs))


class ProgressAndMeterNestingAndInteractiveIntegrityTests(unittest.TestCase):
    """Enforce <progress> and <meter> non-nesting and non-interactive fallback content (HTML5 §4.10.13, §4.10.14 & WCAG 2.2 SC 4.1.2, SC 2.1.1)."""

    def test_valid_progress_and_meter_pass(self):
        html = '<progress value="50" max="100">50%</progress><meter value="0.7">70%</meter>'
        self.assertEqual(build.check_progress_and_meter_nesting_and_interactive_integrity("test.html", html), [])

    def test_nested_progress_in_progress_rejected(self):
        html = '<progress value="50" max="100"><progress value="25" max="100"></progress></progress>'
        errs = build.check_progress_and_meter_nesting_and_interactive_integrity("test.html", html)
        self.assertTrue(any("<progress> must not contain nested <progress> element" in e for e in errs))

    def test_nested_meter_in_progress_rejected(self):
        html = '<progress value="50" max="100"><meter value="0.5"></meter></progress>'
        errs = build.check_progress_and_meter_nesting_and_interactive_integrity("test.html", html)
        self.assertTrue(any("<progress> must not contain nested <meter> element" in e for e in errs))

    def test_nested_meter_in_meter_rejected(self):
        html = '<meter value="0.5"><meter value="0.2"></meter></meter>'
        errs = build.check_progress_and_meter_nesting_and_interactive_integrity("test.html", html)
        self.assertTrue(any("<meter> must not contain nested <meter> element" in e for e in errs))

    def test_nested_progress_in_meter_rejected(self):
        html = '<meter value="0.5"><progress value="50" max="100"></progress></meter>'
        errs = build.check_progress_and_meter_nesting_and_interactive_integrity("test.html", html)
        self.assertTrue(any("<meter> must not contain nested <progress> element" in e for e in errs))

    def test_interactive_button_inside_progress_rejected(self):
        html = '<progress value="50" max="100"><button type="button">Cancel</button></progress>'
        errs = build.check_progress_and_meter_nesting_and_interactive_integrity("test.html", html)
        self.assertTrue(any("interactive <button> inside <progress> violates HTML5" in e for e in errs))

    def test_interactive_link_inside_meter_rejected(self):
        html = '<meter value="0.5"><a href="/details">View Details</a></meter>'
        errs = build.check_progress_and_meter_nesting_and_interactive_integrity("test.html", html)
        self.assertTrue(any("interactive <a> inside <meter> violates HTML5" in e for e in errs))

    def test_check_page_integrates_media_controls_and_figure_checks(self):
        m = meta('<img src="/test.jpg" alt="test" crossorigin="bad-token">')
        m["raw"] = f"---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n{m['body']}"
        errs = build.check_page(m, "")
        self.assertTrue(any("declares invalid crossorigin='bad-token'" in e for e in errs))


class JsonDataBlockAndFrontmatterScriptTests(unittest.TestCase):
    def test_valid_application_json_data_block_passes(self):
        snippet = '<p>Intro</p><script type="application/json" id="demo-data">{"items": [1, 2, 3]}</script>'
        errs = build.check_interactive_elements_and_embeds("test.html", snippet)
        self.assertEqual(errs, [])

    def test_json_data_block_rejects_src_missing_id_or_invalid_json(self):
        errs_src = build.check_interactive_elements_and_embeds(
            "test.html", '<script type="application/json" id="x" src="/assets/js/site.js">{}</script>'
        )
        self.assertTrue(any("content must not contain <script>" in e for e in errs_src))

        errs_no_id = build.check_interactive_elements_and_embeds(
            "test.html", '<script type="application/json">{"ok": true}</script>'
        )
        self.assertTrue(any("requires an explicit id attribute" in e for e in errs_no_id))

        errs_bad_json = build.check_interactive_elements_and_embeds(
            "test.html", '<script type="application/json" id="bad">{not json}</script>'
        )
        self.assertTrue(any("contains invalid JSON" in e for e in errs_bad_json))

    def test_frontmatter_script_validates_basename_and_existence(self):
        m_ok = meta("<p>Clean short sentence.</p>", script="site.js")
        m_ok["raw"] = "---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\nscript: site.js\n---\n<p>Clean short sentence.</p>"
        self.assertEqual(build.check_page(m_ok, ""), [])
        rendered = build.page_shell(m_ok, "<p>Body</p>")
        self.assertEqual(rendered.count("/assets/js/site.js?v="), 2)

        m_missing = meta("<p>Clean short sentence.</p>", script="missing-nonexistent.js")
        m_missing["raw"] = "---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n<p>Clean short sentence.</p>"
        errs_missing = build.check_page(m_missing, "")
        self.assertTrue(any("assets/js/missing-nonexistent.js not found" in e for e in errs_missing))

        m_traversal = meta("<p>Clean short sentence.</p>", script="../evil.js")
        m_traversal["raw"] = "---\ntitle: t\ndescription: d\nreader: r\ntakeaway: k\ntemplate: page\n---\n<p>Clean short sentence.</p>"
        errs_trav = build.check_page(m_traversal, "")
        self.assertTrue(any("invalid script filename" in e for e in errs_trav))


if __name__ == "__main__":

    unittest.main()
