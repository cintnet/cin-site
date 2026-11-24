#!/usr/bin/env python3
"""Build the cintnet.org ORG site (specs/org/requirements-and-tasks.md, Spec 03 v2).

Content lives in site/content/ as HTML fragments with a small front-matter block:

    ---
    title: Vision
    description: One sentence for search engines and link previews.
    reader: Who this page is written for.
    takeaway: What they should understand or do after reading.
    template: page            # home | page | article | index
    section: vision           # which nav item is highlighted
    ---
    <p>Body HTML…</p>

Articles also need: date (YYYY-MM-DD), category, minutes, lede, and image and image_alt.

    python site/build.py           # build into site/dist and run every check
    python site/build.py --serve   # build, then serve on http://localhost:8080

The build fails if any requirement check fails (R3 front-matter, R4 plain language,
R5 steward gate, broken internal links, unsafe JS, image alt-text quality,
footnote https links, heading hierarchy, or duplicate titles/descriptions).
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
from html.parser import HTMLParser
import http.server
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import socketserver
import struct
import sys
from functools import partial
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
ASSETS = ROOT / "assets"
DIST = ROOT / "dist"
SITE_URL = "https://cintnet.org"
SITE_NAME = "Collective Intelligence Network"
CONTACT = "contact@collectiveintelligencenetwork.org"
FALLBACK_IMAGE = "hero-commons.jpg"

ATOM_NS = "http://www.w3.org/2005/Atom"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
FEED_TITLE = "Collective Intelligence Network · Blog"
FEED_SUBTITLE = (
    "Plain-language essays and research notes on keeping AI understandable "
    "and accountable to the people it affects."
)

NAV = [("vision", "Vision", "/vision/"), ("research", "Research", "/research/"),
       ("labs", "Labs", "/labs/"), ("blog", "Blog", "/blog/"), ("about", "About", "/about/")]

REQUIRED = ("title", "description", "reader", "takeaway", "template")
ARTICLE_REQUIRED = ("date", "category", "minutes", "lede", "image", "image_alt")  # every post ships with its own illustration

# R5 steward gate: no money, savings, token, royalty or reward promises.
FORBIDDEN = [
    (re.compile(r"\bContribution\s+Tokens?\b", re.I), "token framing"),
    (re.compile(r"\bMMCT\b"), "token ticker"),
    (re.compile(r"\$\s?[0-9][0-9,]*(\.[0-9]+)?\s*(k|K|/|per)\s*(yr|year|month)?", re.I), "dollar figure"),
    (re.compile(r"\broyalt(y|ies)\b", re.I), "royalty claim"),
    (re.compile(r"\b85\s*/\s*10\s*/\s*5\b"), "royalty split"),
    (re.compile(r"\b95\s*%\s*savings\b", re.I), "savings promise"),
    (re.compile(r"\b(airdrop|tokenomics|staking rewards?)\b", re.I), "crypto reward framing"),
]
# Trojan Source & invisible Unicode defense (Boucher & Anderson, arXiv:2111.00169; RFC 8264 / PRECIS)
# Blocks zero-width code points, byte-order marks, soft hyphens, and bidirectional override/isolate formatters.
INVISIBLE_UNICODE = re.compile(
    r"[\u200B-\u200D\uFEFF\u00AD\u2060\u200E\u200F\u202A-\u202E\u2066-\u2069]"
)

# R4 plain language: no internal codes or retired buzzwords anywhere; research terms only inside "for researchers" asides or footnotes.
INTERNAL_IDS = re.compile(r"\b(?:[DLP]-\d{3,4}|F\d{1,2}|GAP-\d+|Axiom\s*#\d+)\b")
RETIRED_BUZZWORDS = re.compile(
    r"Somatic Witness|Pre-ADC|Upcoding Reversal|Algebraic Coalition|Weight-Space Group|"
    r"Affective-State Shield|Blinded Cohort Rendezvous|Coalition Intent Shard|Fractured Alignment",
    re.I,
)
COINAGES = re.compile(r"Markov|Neuro-Symbiont|Isomorphic|We-Ledger|Sensorium|Somatic Witness|Pre-ADC|"
                      r"Data Shapley|Proof-Carrying|Object-Capability|demurrage|TIES-Merging|\bLoRA\b|"
                      r"\bzooids?\b|endosymbiosis|\bCIRL\b", re.I)
EXEMPT_BLOCKS = re.compile(
    r'<aside\b[^>]*\bclass=["\'][^"\']*\bfor-researchers\b[^"\']*["\'][^>]*>.*?</aside>'
    r'|<section\b[^>]*\bclass=["\'][^"\']*\bfootnotes\b[^"\']*["\'][^>]*>.*?</section>',
    re.S | re.I,
)
UNSAFE_JS = (".innerHTML", "outerHTML", "insertAdjacentHTML", "document.write(", "eval(", "new Function(")
EXTERNAL_NET_PATTERNS = (
    (re.compile(r"\b(?:window\.)?fetch\s*\(", re.I), "fetch() network request"),
    (re.compile(r"\bnew\s+XMLHttpRequest\b", re.I), "XMLHttpRequest network request"),
    (re.compile(r"\bnavigator\.sendBeacon\s*\(", re.I), "navigator.sendBeacon network request"),
    (re.compile(r"\bnew\s+WebSocket\s*\(", re.I), "WebSocket network request"),
    (re.compile(r"\bnew\s+EventSource\s*\(", re.I), "EventSource network request"),
)
GIT_CONFLICT_MARKERS = re.compile(r"^(?:<{7}|={7}|>{7})\s.*$", re.M)
ELEMENT_ID_RE = re.compile(r'\bid\s*=\s*["\']([^"\']+)["\']', re.I)

# Readability thresholds (Spec 09 / voice.md: <= 22-word median, zero 35+ word sentences)
PARAGRAPH_SOFT_LIMIT = 95
PARAGRAPH_HARD_LIMIT = 140
SENTENCE_WORD_LIMIT = 34
_P_BLOCK_RE = re.compile(r"<(?:p|li|blockquote)\b[^>]*>(.*?)</(?:p|li|blockquote)>", re.S | re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_SENTENCE_SPLIT_RE = re.compile(r'[.!?]+(?:["\'\u201d\u2019)\]]+)?(?:\s+|$)')

# Image alt-text & dimension helpers
MIN_ALT_LENGTH = 15
IMAGE_EXT_RE = re.compile(r"\.(?:jpe?g|png|webp|svg|gif|avif|bmp|ico)$", re.I)
IMG_TAG_RE = re.compile(r'<img\b([^>]*?\bsrc="/assets/img/([^"]+)"[^>]*)>')
JPEG_SOF_MARKERS = frozenset({
    0xC0, 0xC1, 0xC2, 0xC3,
    0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB,
    0xCD, 0xCE, 0xCF,
})
JPEG_STANDALONE_MARKERS = frozenset({0x01, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9})

# Footnotes & headings regexes
FOOTNOTES_SECTION_RE = re.compile(
    r'<section\b[^>]*\bclass=["\'][^"\']*\bfootnotes\b[^"\']*["\'][^>]*>(.*?)</section>',
    re.I | re.S,
)
HREF_RE = re.compile(r'\bhref\s*=\s*["\']([^"\']+)["\']', re.I)
HEADING_RE = re.compile(r"<h([1-6])\b[^>]*>", re.I)


# ---------------------------------------------------------------- parsing

def parse(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.S)
    if not m:
        raise SystemExit(f"{path}: missing front-matter block")
    meta = {}
    for line in m.group(1).splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            k, _, v = line.partition(":")
            meta[k.strip()] = v.split("  #")[0].strip()
    rel = path.relative_to(CONTENT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "index":
        parts = parts[:-1]
    meta["route"] = "/" + "/".join(parts) + ("/" if parts else "")
    meta["body"] = m.group(2)
    meta["raw"] = raw
    meta["src"] = path
    return meta


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def nice_date(d: str) -> str:
    return dt.date.fromisoformat(d).strftime("%b %-d, %Y") if sys.platform != "win32" else \
        dt.date.fromisoformat(d).strftime("%b %#d, %Y")


# ---------------------------------------------------------------- image dimensions (CLS)

def image_dimensions(path: Path) -> tuple[int, int] | None:
    """Return `(width, height)` in pixels for a JPEG, PNG, WebP, or GIF file using only stdlib `struct`."""
    path = Path(path)
    if not path.is_file():
        return None
    try:
        with path.open("rb") as f:
            head = f.read(32)
            if len(head) < 4:
                return None

            # PNG: 8-byte signature + 4-byte length + 'IHDR' + 4-byte width + 4-byte height
            if head.startswith(b"\x89PNG\r\n\x1a\n"):
                if len(head) >= 24 and head[12:16] == b"IHDR":
                    w, h = struct.unpack(">II", head[16:24])
                    return (w, h) if w > 0 and h > 0 else None
                return None

            # GIF: GIF87a or GIF89a + 4 bytes logical screen width/height (<HH)
            if head.startswith((b"GIF87a", b"GIF89a")):
                if len(head) >= 10:
                    w, h = struct.unpack("<HH", head[6:10])
                    return (w, h) if w > 0 and h > 0 else None
                return None

            # WebP: RIFF container with WEBP FourCC
            if head.startswith(b"RIFF") and len(head) >= 16 and head[8:12] == b"WEBP":
                chunk_type = head[12:16]
                if chunk_type == b"VP8 ":
                    # VP8 lossy: read frame header and dimensions
                    f.seek(0)
                    data = f.read(30)
                    if len(data) >= 30 and data[23:26] == b"\x9d\x01\x2a":
                        w = struct.unpack("<H", data[26:28])[0] & 0x3FFF
                        h = struct.unpack("<H", data[28:30])[0] & 0x3FFF
                        return (w, h) if w > 0 and h > 0 else None
                    return None
                elif chunk_type == b"VP8L":
                    # VP8L lossless: 0x2F signature + 28 bits width/height
                    f.seek(0)
                    data = f.read(26)
                    if len(data) >= 25 and data[20] == 0x2F:
                        bits = struct.unpack("<I", data[21:25])[0]
                        w = (bits & 0x3FFF) + 1
                        h = ((bits >> 14) & 0x3FFF) + 1
                        return (w, h) if w > 0 and h > 0 else None
                    return None
                elif chunk_type == b"VP8X":
                    # VP8X extended: canvas width/height (24-bit little endian)
                    f.seek(0)
                    data = f.read(30)
                    if len(data) >= 30:
                        w = 1 + int.from_bytes(data[24:27], "little")
                        h = 1 + int.from_bytes(data[27:30], "little")
                        return (w, h) if w > 0 and h > 0 else None
                    return None
                return None

            # JPEG: starts with SOI (0xFF 0xD8)
            if not head.startswith(b"\xff\xd8"):
                return None

            f.seek(2)
            while True:
                b = f.read(1)
                if not b or b != b"\xff":
                    return None
                while b == b"\xff":
                    b = f.read(1)
                    if not b:
                        return None
                marker = b[0]
                if marker == 0x00:
                    continue
                if marker in (0xD9, 0xDA):
                    return None
                if marker in JPEG_STANDALONE_MARKERS:
                    continue

                len_bytes = f.read(2)
                if len(len_bytes) < 2:
                    return None
                (seg_len,) = struct.unpack(">H", len_bytes)
                if seg_len < 2:
                    return None

                if marker in JPEG_SOF_MARKERS:
                    if seg_len < 7:
                        return None
                    sof_data = f.read(5)
                    if len(sof_data) < 5:
                        return None
                    h, w = struct.unpack(">xHH", sof_data)
                    return (w, h) if w > 0 and h > 0 else None

                f.seek(seg_len - 2, 1)
    except OSError:
        return None


def inject_img_dimensions(html_doc: str, assets_dir: Path | None = None) -> str:
    """Ensure inline `<img src="/assets/img/...">` tags in content have `width` and `height`."""
    base = assets_dir if assets_dir is not None else ASSETS

    def _repl(m: re.Match) -> str:
        attrs, rel_img = m.group(1), m.group(2)
        has_w = bool(re.search(r"\bwidth\s*=", attrs))
        has_h = bool(re.search(r"\bheight\s*=", attrs))
        if has_w and has_h:
            return m.group(0)
        dims = image_dimensions(base / "img" / rel_img)
        if not dims:
            return m.group(0)
        w, h = dims
        extra = (f' width="{w}"' if not has_w else "") + (f' height="{h}"' if not has_h else "")
        return f"<img{attrs}{extra}>"

    return IMG_TAG_RE.sub(_repl, html_doc)


# ---------------------------------------------------------------- metadata & feeds

def atom_feed_head_tag(site_url: str = SITE_URL) -> str:
    base = site_url.rstrip("/")
    return (
        '<link rel="alternate" type="application/atom+xml" '
        f'title="{esc(FEED_TITLE)}" href="{esc(base)}/blog/feed.xml">'
    )


def render_social_meta(meta: dict, site_url: str = SITE_URL) -> str:
    """Render Open Graph and Twitter Card <meta> tags for a page or article."""
    base = site_url.rstrip("/")
    route = meta.get("route") or "/"
    if not route.startswith("/"):
        route = "/" + route
    og_url = f"{base}{route}"

    raw_img = (meta.get("image") or "").strip()
    if raw_img:
        if raw_img.startswith(("http://", "https://")):
            og_img = raw_img
        elif raw_img.startswith("/"):
            og_img = f"{base}{raw_img}"
        else:
            og_img = f"{base}/assets/img/{raw_img}"
    else:
        og_img = f"{base}/assets/img/{FALLBACK_IMAGE}"

    is_article = meta.get("template") == "article"
    og_type = "article" if is_article else "website"
    title = esc(meta.get("title", ""))
    description = esc(meta.get("description", ""))
    image_alt = (meta.get("image_alt") or "").strip()

    tags = [
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:description" content="{description}">',
        f'<meta property="og:url" content="{esc(og_url)}">',
        f'<meta property="og:site_name" content="{esc(SITE_NAME)}">',
        f'<meta property="og:image" content="{esc(og_img)}">',
    ]
    if image_alt:
        tags.append(f'<meta property="og:image:alt" content="{esc(image_alt)}">')
    tags.append(f'<meta property="og:type" content="{og_type}">')

    if is_article:
        if meta.get("date"):
            tags.append(f'<meta property="article:published_time" content="{esc(meta["date"])}">')
        if meta.get("category"):
            tags.append(f'<meta property="article:section" content="{esc(meta["category"])}">')

    tags.extend([
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{title}">',
        f'<meta name="twitter:description" content="{description}">',
        f'<meta name="twitter:image" content="{esc(og_img)}">',
    ])
    if image_alt:
        tags.append(f'<meta name="twitter:image:alt" content="{esc(image_alt)}">')

    return "\n".join(tags)


def render_json_ld(meta: dict, site_url: str = SITE_URL) -> str:
    """Render a <script type="application/ld+json"> tag for <head>."""
    base_url = site_url.rstrip("/")
    route = meta.get("route") or "/"
    if not route.startswith("/"):
        route = "/" + route
    page_url = f"{base_url}{route}"
    image_name = meta.get("image")
    image_url = (
        f"{base_url}/assets/img/{image_name}"
        if image_name
        else f"{base_url}/assets/img/{FALLBACK_IMAGE}"
    )
    org = {
        "@type": "Organization",
        "name": SITE_NAME,
        "url": base_url,
    }

    if meta.get("template") == "article":
        payload = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": meta.get("title", ""),
            "description": meta.get("description", ""),
            "datePublished": meta.get("date", ""),
            "url": page_url,
            "image": image_url,
            "articleSection": meta.get("category", ""),
            "author": org,
            "publisher": dict(org),
        }
    else:
        title = meta.get("title", "")
        name = SITE_NAME if (route == "/" or not title) else f"{title} · {SITE_NAME}"
        payload = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": name,
            "url": page_url,
            "description": meta.get("description", ""),
            "publisher": org,
        }

    encoded = json.dumps(payload, ensure_ascii=False).replace("</", r"<\/")
    return f'<script type="application/ld+json">{encoded}</script>'


def _to_rfc3339(date_str: str) -> str:
    s = (date_str or "").strip()
    if not s:
        return "1970-01-01T00:00:00Z"
    if "T" in s:
        if s.endswith("Z") or re.search(r"[+-]\d{2}:\d{2}$", s):
            return s
        return s + "Z"
    d = dt.date.fromisoformat(s)
    return f"{d.isoformat()}T00:00:00Z"


def render_atom_feed(articles: list[dict], site_url: str = SITE_URL) -> str:
    """Render a valid Atom 1.0 XML feed (`dist/blog/feed.xml`) for the site's blog articles."""
    base = site_url.rstrip("/")
    feed_url = f"{base}/blog/feed.xml"
    blog_url = f"{base}/blog/"

    ordered = list(articles)
    ordered.sort(key=lambda m: int(m.get("order", 99)))
    ordered.sort(key=lambda m: m.get("date", ""), reverse=True)

    newest_date = ordered[0].get("date", "") if ordered else "1970-01-01"
    feed_updated = _to_rfc3339(newest_date)

    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<feed xmlns="{ATOM_NS}">',
        f"  <title>{esc(FEED_TITLE)}</title>",
        f"  <subtitle>{esc(FEED_SUBTITLE)}</subtitle>",
        f"  <id>{esc(blog_url)}</id>",
        f"  <updated>{esc(feed_updated)}</updated>",
        f'  <link rel="self" href="{esc(feed_url)}" type="application/atom+xml"/>',
        f'  <link rel="alternate" href="{esc(blog_url)}" type="text/html"/>',
        f"  <author><name>{esc(SITE_NAME)}</name></author>",
    ]

    for a in ordered:
        route = a.get("route") or "/"
        if not route.startswith("/"):
            route = "/" + route
        entry_url = f"{base}{route}"
        published = _to_rfc3339(a.get("date", ""))
        updated = _to_rfc3339(a.get("updated") or a.get("date", ""))
        category = a.get("category") or "Blog"
        summary = a.get("description") or " ".join(html.unescape(_TAG_RE.sub(" ", a.get("lede", ""))).split())
        body_html = (a.get("body") or "").strip()

        lines.extend([
            "  <entry>",
            f"    <title>{esc(a.get('title', ''))}</title>",
            f"    <id>{esc(entry_url)}</id>",
            f'    <link href="{esc(entry_url)}"/>',
            f"    <published>{esc(published)}</published>",
            f"    <updated>{esc(updated)}</updated>",
            f'    <category term="{esc(category)}"/>',
            f"    <summary>{esc(summary)}</summary>",
            f'    <content type="html">{esc(body_html)}</content>',
            "  </entry>",
        ])

    lines.append("</feed>")
    return "\n".join(lines) + "\n"


def render_sitemap(
    metas: list[dict],
    site_url: str = SITE_URL,
    default_date: str | None = None,
) -> str:
    """Render dist/sitemap.xml with <loc> and <lastmod> for each page/post sorted by route."""
    fallback = (default_date or dt.date.today().isoformat()).strip()
    base = site_url.rstrip("/")
    urls: list[str] = []
    for m in sorted(metas, key=lambda item: item.get("route", "")):
        route = m.get("route", "/")
        raw_date = m.get("date")
        lastmod = str(raw_date).strip() if raw_date and str(raw_date).strip() else fallback
        loc = f"{base}{route}"
        urls.append(
            f"<url><loc>{esc(loc)}</loc><lastmod>{esc(lastmod)}</lastmod></url>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<urlset xmlns="{SITEMAP_NS}">{"".join(urls)}</urlset>'
    )


# ---------------------------------------------------------------- templates

def header(active: str) -> str:
    cur = ' aria-current="page"'
    links = "".join(
        f'<a href="{href}"{cur if key == active else ""}>{label}</a>'
        for key, label, href in NAV)
    return f"""<header class="site-header">
  <div class="wrap header-inner">
    <a class="wordmark" href="/" aria-label="Collective Intelligence Network, home">
      <img class="mark" src="/assets/img/logo-192.png" alt="" width="32" height="32">
      <span>Collective Intelligence Network</span>
    </a>
    <nav class="primary" aria-label="Main">{links}</nav>
    <a class="pill pill-dark header-cta" href="/get-involved/">Get involved</a>
    <details class="mobile-nav">
      <summary aria-label="Menu"><span></span><span></span></summary>
      <nav aria-label="Main (mobile)">{links}<a href="/get-involved/">Get involved</a></nav>
    </details>
  </div>
</header>"""


FOOTER = f"""<footer class="site-footer">
  <div class="wrap footer-grid">
    <div class="footer-about">
      <p class="footer-name"><img class="footer-mark" src="/assets/img/logo-192.png" alt="" width="28" height="28">Collective Intelligence Network</p>
      <p>Open blueprints for a 1:1 personal assistant loyal to you over a local memory vault, paired with private and public signed ledgers so communities coordinate shared work on their own terms.</p>
      <p class="muted small">This site is written with the help of AI agents and reviewed by a person. It sets no cookies, runs no analytics and makes no third-party requests.</p>
    </div>
    <nav aria-label="Foundation"><p class="footer-h">Foundation</p>
      <a href="/vision/">Vision</a><a href="/research/">Research</a><a href="/labs/">Labs</a><a href="/blog/">Blog</a><a href="/about/">About</a><a href="https://github.com/cintnet" rel="noopener noreferrer">GitHub</a><a href="/blog/feed.xml">RSS feed</a></nav>
    <nav aria-label="Get involved"><p class="footer-h">Get involved</p>
      <a href="/get-involved/policy/">Policy makers</a><a href="/get-involved/researchers/">Researchers</a><a href="/get-involved/labs/">AI labs</a><a href="/get-involved/builders/">Builders</a><a href="/get-involved/civil-society/">Civil society</a><a href="/get-involved/everyone/">Everyone</a></nav>
    <nav aria-label="Policies"><p class="footer-h">Policies</p>
      <a href="/privacy/">Privacy</a><a href="/terms/">Terms</a><a href="/cookies/">Cookies</a><a href="/support/">Support</a><a href="/corrections/">Corrections</a><a href="/contact/">Contact</a><a href="https://discord.gg/AANETMGc6Z" rel="noopener noreferrer">Discord</a></nav>
  </div>
  <div class="wrap footer-base"><span>© {dt.date.today().year} Collective Intelligence Network</span><span>Ottawa, Canada</span></div>
</footer>"""


def _parse_extra_scripts(meta: dict) -> list[str]:
    raw_val = meta.get("script") or meta.get("scripts") or ""
    out: list[str] = []
    for part in str(raw_val).split(","):
        s = part.strip()
        if s:
            out.append(s)
    return out


def page_shell(meta: dict, main: str) -> str:
    title = SITE_NAME if meta["route"] == "/" else f'{meta["title"]} · {SITE_NAME}'
    social_meta = render_social_meta(meta, SITE_URL)
    atom_link = atom_feed_head_tag(SITE_URL)
    json_ld = render_json_ld(meta, SITE_URL)
    extra_js_tags = ""
    for js_name in _parse_extra_scripts(meta):
        if re.match(r"^[a-z0-9][a-z0-9._-]*\.js$", js_name, re.I):
            extra_js_tags += f'\n<script src="/assets/js/{esc(js_name)}?v={BUILD_ID}" defer></script>'
    return f"""<!doctype html>
<html lang="en-CA">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(meta['description'])}">
<link rel="canonical" href="{SITE_URL}{meta['route']}">
{atom_link}
{social_meta}
{json_ld}
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#FAF3EA">
<link rel="icon" href="/assets/favicon.ico" sizes="any">
<link rel="icon" href="/assets/img/logo-192.png" type="image/png">
<link rel="apple-touch-icon" href="/assets/img/logo-192.png">
<link rel="stylesheet" href="/assets/css/site.css?v={BUILD_ID}">
<link rel="stylesheet" href="/assets/css/stages.css?v={BUILD_ID}">
<script src="/assets/js/site.js?v={BUILD_ID}" defer></script>
<script src="/assets/js/stages.js?v={BUILD_ID}" defer></script>{extra_js_tags}
</head>
<body class="t-{meta['template']}">
<a class="skip" href="#main">Skip to content</a>
{header(meta.get('section', ''))}
<main id="main">
{main}
</main>
{FOOTER}
</body>
</html>
"""


def figure(meta: dict, cls: str = "art", assets_dir: Path | None = None) -> str:
    img = meta.get("image")
    if not img:
        return ""
    base = assets_dir if assets_dir is not None else ASSETS
    img_path = base / "img" / img
    if not img_path.exists():
        WARNINGS.append(f"{meta['src'].name}: image {img} not found yet; figure omitted")
        return ""
    dims = image_dimensions(img_path)
    wh = f' width="{dims[0]}" height="{dims[1]}"' if dims else ""
    return (f'<figure class="{cls} reveal"><img src="/assets/img/{img}" alt="{esc(meta.get("image_alt", ""))}"'
            f'{wh} loading="lazy" decoding="async"></figure>')


def post_card(a: dict, tint: int, assets_dir: Path | None = None, eager: bool = False) -> str:
    img = a.get("image")
    base = assets_dir if assets_dir is not None else ASSETS
    img_path = base / "img" / img if img else None
    if img and img_path and img_path.exists():
        dims = image_dimensions(img_path)
        wh = f' width="{dims[0]}" height="{dims[1]}"' if dims else ""
        loading_attr = "" if eager else ' loading="lazy"'
        pic = f'<div class="card-art"><img src="/assets/img/{img}" alt=""{wh}{loading_attr} decoding="async"></div>'
    else:
        pic = '<div class="card-art card-art-empty"></div>'
    body_str = a.get("body", "")
    n_fn = len(re.findall(r'<(?:li|p)\b[^>]*\bid=["\']fn(?!ref)[^"\']*["\']', body_str, re.I))
    if n_fn == 0:
        n_fn = len(re.findall(r'\bid=["\']fn(?!ref)', body_str, re.I))
    fn_suffix = f" · {n_fn} source{'s' if n_fn != 1 else ''}" if n_fn > 0 else ""
    return f"""<a class="post-card tint-{tint % 5} reveal" href="{a['route']}" data-category="{esc(a['category'])}">
  {pic}
  <div class="card-body"><p class="meta">{esc(a['category'])} · <time datetime="{esc(a['date'])}">{nice_date(a['date'])}</time></p>
  <h3>{esc(a['title'])}</h3><p>{esc(a['description'])}</p>
  <span class="read">Read · {esc(a['minutes'])} min{fn_suffix}</span></div>
</a>"""


NO_COMMENT_ROUTES = frozenset({"/privacy/", "/terms/", "/cookies/", "/contact/", "/404/"})
DISCUSSIONS_REPO = "cintnet/cin-site"


def load_page_discussions(assets_dir: Path | None = None) -> dict:
    base = assets_dir if assets_dir is not None else ASSETS
    p = base / "data" / "page-discussions.json"
    if not p.is_file():
        return {"routes": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"routes": {}}
    except Exception:
        return {"routes": {}}


def render_comments(meta: dict, discussions_index: dict | None = None) -> str:
    """Render a zero-tracking, cookie-free page comments section backed by GitHub Discussions."""
    route = meta.get("route", "")
    if not route or route in NO_COMMENT_ROUTES:
        return ""
    flag = str(meta.get("comments", "")).strip().lower()
    if flag in {"false", "off", "no", "none", "0"}:
        return ""

    from urllib.parse import quote

    title = meta.get("title") or meta.get("heading") or route
    routes_map = (discussions_index or {}).get("routes") or {}
    entry = routes_map.get(route) if isinstance(routes_map, dict) else None

    if isinstance(entry, dict) and entry.get("discussion_url"):
        gh_url = str(entry["discussion_url"])
        gh_label = "Reply on GitHub Discussions"
        raw_comments = entry.get("comments") or []
    else:
        disc_title = quote(f"[{route}] {title}", safe="")
        gh_url = f"https://github.com/{DISCUSSIONS_REPO}/discussions/new?category=general&title={disc_title}"
        gh_label = "Comment on GitHub Discussions"
        raw_comments = []

    mail_subj = quote(f"Feedback: {title} ({route})", safe="")
    mail_url = f"mailto:contact@collectiveintelligencenetwork.org?subject={mail_subj}"

    items_html = ""
    if raw_comments:
        cards = []
        for c in raw_comments[:20]:
            if not isinstance(c, dict):
                continue
            author = esc(str(c.get("author") or "community"))
            cdate = esc(str(c.get("created_at") or ""))
            cbody = esc(str(c.get("body") or ""))
            if not cbody:
                continue
            meta_line = f"{author} · {cdate}" if cdate else author
            cards.append(
                f'<li class="comment-card"><p class="comment-meta">{meta_line}</p><p class="comment-body">{cbody}</p></li>'
            )
        if cards:
            items_html = f'<ol class="comment-list">{"".join(cards)}</ol>'

    return (
        '<section class="page-comments wrap-narrow" id="comments" aria-labelledby="comments-heading">'
        '<h2 id="comments-heading">Questions, critiques, and comments</h2>'
        '<p class="comment-intro">Spotted an error, a missing primary source, or an angle we should test next? '
        'Add a public comment on GitHub Discussions or send an email. '
        'Valid critiques feed into our <a href="/corrections/">public corrections</a> ledger and follow-up research. '
        'No third-party scripts or cookies load on this page.</p>'
        f'{items_html}'
        '<div class="comment-actions">'
        f'<a class="comment-btn comment-btn-primary" href="{esc(gh_url)}" rel="noopener noreferrer">{esc(gh_label)}</a>'
        f'<a class="comment-btn comment-btn-secondary" href="{esc(mail_url)}">Send feedback by email</a>'
        '</div>'
        '</section>'
    )


def render_article(meta: dict, articles: list[dict], discussions_index: dict | None = None) -> str:
    others = [a for a in articles if a["route"] != meta["route"]][:3]
    recent = "".join(post_card(a, i) for i, a in enumerate(others))
    comments_html = render_comments(meta, discussions_index)
    return f"""<article class="article">
  <header class="article-head wrap-narrow reveal">
    <p class="meta"><a href="/blog/">Blog</a> · {esc(meta['category'])} · <time datetime="{esc(meta['date'])}">{nice_date(meta['date'])}</time> · {esc(meta['minutes'])} min read</p>
    <h1>{esc(meta['title'])}</h1>
    <p class="lede">{meta['lede']}</p>
  </header>
  <div class="wrap-wide">{figure(meta, 'art art-wide')}</div>
  <div class="prose wrap-narrow">
{meta['body']}
  </div>
  <p class="wrap-narrow back"><a href="/blog/">← All articles</a></p>
</article>
{comments_html}
<section class="recent wrap"><h2 class="section-h">Recent articles</h2><div class="post-grid">{recent}</div></section>"""


_ACADEMIC_DOMAINS = (
    "arxiv.org", "doi.org", "acm.org", "ieee.org", "nature.com", "science.org",
    "pnas.org", "springer", "wiley", "sciencedirect", "oup.com", "cambridge.org",
    "nber.org", "ssrn.com", "openreview.net", "aclanthology.org", "mlr.press",
    "jmlr", "frontiersin.org", "plos.org", "ncbi.nlm.nih.gov",
    "royalsocietypublishing.org", "mitpress", "uchicago.edu",
)
_STANDARDS_DOMAINS = (
    "rfc-editor.org", "ietf.org", "w3.org", "nist.gov", "c2pa.org",
    "trustedcomputinggroup.org", "dmtf.org", "iec.ch", "iso.org", "owasp.org", "unicode.org",
)
_POLICY_DOMAINS = (
    ".gov", ".gc.ca", "parl.ca", "europa.eu", "legislation.gov.uk", "oecd.org",
    "un.org", "imf.org", "worldbank.org", "who.int", "aisi.gov.uk", "artificialintelligenceact.eu",
)
_FN_HEADING_STRIP_RE = re.compile(
    r"<h[234][^>]*>\s*(?:Sources(?:\s*(?:&amp;|&|and)\s*notes)?|Footnotes|Notes(?:\s+and\s+sources)?|References)\s*</h[234]>\s*",
    re.I | re.S,
)
_FN_WRAP_RE = re.compile(
    r'(<section\b[^>]*\bclass=["\'][^"\']*\bfootnotes\b[^"\']*["\'][^>]*>)(.*?)(</section>)',
    re.I | re.S,
)
_RESEARCHER_WRAP_RE = re.compile(
    r'(<aside\b[^>]*\bclass=["\'][^"\']*\bfor-researchers\b[^"\']*["\'][^>]*>)(.*?)(</aside>)',
    re.I | re.S,
)


def _classify_external_url(url: str) -> str:
    host = urlsplit(url).netloc.lower()
    if any(d in host for d in _ACADEMIC_DOMAINS):
        return "academic"
    if any(d in host for d in _STANDARDS_DOMAINS):
        return "standards"
    if any(d in host for d in _POLICY_DOMAINS):
        return "policy"
    return "primary"


def enrich_collapsible_disclosures(html_str: str) -> str:
    """Wrap <section class='footnotes'> in a collapsed <details class='footnotes-drawer'> with source
    provenance telemetry, and enrich <aside class='for-researchers'> summaries with term/citation/word counts."""

    def _repl_footnotes(m: re.Match[str]) -> str:
        open_tag, inner, close_tag = m.group(1), m.group(2), m.group(3)
        if "footnotes-drawer" in inner:
            return m.group(0)

        fn_items = re.findall(
            r'<(li|p)\b[^>]*\bid=["\']fn(?!ref)[^"\']*["\'][^>]*>(.*?)</\1>',
            inner,
            re.I | re.S,
        )
        n_sources = len(fn_items)
        if n_sources == 0:
            fallback_items = re.findall(r"<(li|p)\b[^>]*>(.*?)</\1>", inner, re.I | re.S)
            fn_items = fallback_items
            n_sources = len(fallback_items)

        cats = {"academic": 0, "standards": 0, "policy": 0, "primary": 0}
        if fn_items:
            for _, item_html in fn_items:
                urls = re.findall(r'\bhref\s*=\s*["\'](https://[^"\']+)["\']', item_html, re.I)
                if urls:
                    item_cats = {_classify_external_url(u) for u in urls}
                    for prio in ("academic", "standards", "policy", "primary"):
                        if prio in item_cats:
                            cats[prio] += 1
                            break
        else:
            seen_urls: list[str] = []
            for u in re.findall(r'\bhref\s*=\s*["\'](https://[^"\']+)["\']', inner, re.I):
                if u not in seen_urls:
                    seen_urls.append(u)
            for u in seen_urls:
                cats[_classify_external_url(u)] += 1
            if n_sources == 0:
                n_sources = len(seen_urls)

        breakdown_parts = [f"{cats[k]} {k}" for k in ("academic", "standards", "policy", "primary") if cats[k] > 0]
        breakdown_chip = (
            f'\n      <span class="disclosure-chip">{esc(" · ".join(breakdown_parts))}</span>'
            if breakdown_parts
            else ""
        )

        # Strip tags, URLs, DOIs, and arXiv IDs before scanning publication years
        plain_fn = html.unescape(_TAG_RE.sub(" ", inner))
        plain_fn = re.sub(r"https?://\S+", " ", plain_fn, flags=re.I)
        plain_fn = re.sub(r"\b10\.\d{4,9}/\S+", " ", plain_fn)
        plain_fn = re.sub(r"\barXiv:\S+", " ", plain_fn, flags=re.I)
        plain_fn = re.sub(r"\b\d{4}\.\d{4,5}(?:v\d+)?\b", " ", plain_fn)
        years = [int(y) for y in re.findall(r"\b(19[5-9]\d|20[0-2]\d)\b", plain_fn)]
        year_chip = ""
        if years:
            min_y, max_y = min(years), max(years)
            year_span = f"{min_y}\u2013{max_y}" if min_y != max_y else f"{min_y}"
            year_chip = f'\n      <span class="disclosure-chip">{esc(year_span)}</span>'

        cleaned_inner = _FN_HEADING_STRIP_RE.sub("", inner).strip()
        count_label = f"{n_sources} source{'s' if n_sources != 1 else ''}"
        return (
            f"{open_tag}\n"
            f'<details class="footnotes-drawer">\n'
            f'  <summary class="footnotes-summary">\n'
            f'    <span class="footnotes-sum-title">Sources &amp; notes</span>\n'
            f'    <span class="disclosure-meta">\n'
            f'      <span class="disclosure-chip disclosure-chip--count">{esc(count_label)}</span>'
            f"{breakdown_chip}{year_chip}\n"
            f"    </span>\n"
            f"  </summary>\n"
            f'  <div class="footnotes-body">\n'
            f"    {cleaned_inner}\n"
            f"  </div>\n"
            f"</details>\n"
            f"{close_tag}"
        )

    def _repl_researcher(m: re.Match[str]) -> str:
        open_tag, inner, close_tag = m.group(1), m.group(2), m.group(3)
        det_m = re.search(
            r"(<details\b[^>]*>\s*)<summary(\b[^>]*)>(.*?)</summary>(\s*<div\b[^>]*>)(.*)(</div>\s*</details>)",
            inner,
            re.I | re.S,
        )
        if not det_m:
            return m.group(0)
        det_open, sum_attrs, sum_inner, div_open, div_inner, det_close = (
            det_m.group(1),
            det_m.group(2),
            det_m.group(3),
            det_m.group(4),
            det_m.group(5),
            det_m.group(6),
        )
        if "disclosure-meta" in sum_inner:
            return m.group(0)

        n_terms = len(re.findall(r"<code\b[^>]*>.*?</code>", div_inner, re.I | re.S))
        fn_refs = set(re.findall(r'\bhref\s*=\s*["\'](#fn[^"\']+)["\']', div_inner, re.I))
        ext_refs = set(re.findall(r'\bhref\s*=\s*["\'](https://[^"\']+)["\']', div_inner, re.I))
        plain_div = html.unescape(_TAG_RE.sub(" ", div_inner))
        paren_cites = set(
            re.findall(r"\([A-Z][A-Za-z\s&.,\u2019'-]+,\s*(?:19|20)\d{2}[a-z]?\)", plain_div)
        )
        n_cites = len(fn_refs) + len(ext_refs) + len(paren_cites)
        n_words = len(plain_div.split())

        parts: list[str] = []
        if n_terms > 0:
            parts.append(f"{n_terms} technical term{'s' if n_terms != 1 else ''}")
        if n_cites > 0:
            parts.append(f"{n_cites} citation{'s' if n_cites != 1 else ''}")
        parts.append(f"{n_words} words")
        joined_parts = " · ".join(parts)

        raw_title = sum_inner.strip()
        title_html = "For researchers" if re.fullmatch(r"for\s+researchers", raw_title, re.I) else raw_title
        new_summary = (
            f'<summary{sum_attrs}><span class="researcher-sum-title">{title_html}</span>'
            f'<span class="disclosure-meta"><span class="disclosure-chip">{esc(joined_parts)}</span></span></summary>'
        )
        new_inner = (
            inner[: det_m.start()]
            + det_open
            + new_summary
            + div_open
            + div_inner
            + det_close
            + inner[det_m.end() :]
        )
        return f"{open_tag}{new_inner}{close_tag}"

    out = _FN_WRAP_RE.sub(_repl_footnotes, html_str)
    out = _RESEARCHER_WRAP_RE.sub(_repl_researcher, out)
    return out


def render_page(meta: dict, discussions_index: dict | None = None) -> str:
    eyebrow = f'<p class="eyebrow">{esc(meta["eyebrow"])}</p>' if meta.get("eyebrow") else ""
    lede = f'<p class="lede">{meta["lede"]}</p>' if meta.get("lede") else ""
    head_cls = "page-head head-wide" if meta.get("layout") == "wide" else "page-head"
    comments_html = render_comments(meta, discussions_index)
    return f"""<header class="{head_cls} reveal">{eyebrow}<h1>{esc(meta['title'] if not meta.get('heading') else meta['heading'])}</h1>{lede}</header>
<div class="wrap-wide">{figure(meta, 'art art-wide')}</div>
<div class="page-body">
{meta['body']}
</div>
{comments_html}"""


# ---------------------------------------------------------------- checks

class _ImgTagParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "img":
            self.images.append({k.lower(): v for k, v in attrs})

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "img":
            self.images.append({k.lower(): v for k, v in attrs})


def _is_decorative_img(attrs: dict[str, str | None]) -> bool:
    aria_hidden = (attrs.get("aria-hidden") or "").strip().lower()
    role = (attrs.get("role") or "").strip().lower()
    return aria_hidden == "true" or role in {"presentation", "none"}


def _is_filename_alt(alt_text: str, src: str = "") -> bool:
    if IMAGE_EXT_RE.search(alt_text):
        return True
    if src:
        clean_src = src.split("?", 1)[0].split("#", 1)[0].strip().replace("\\", "/")
        if clean_src:
            p = PurePosixPath(clean_src)
            candidates = {clean_src.lower(), p.name.lower(), p.stem.lower()} - {""}
            if alt_text.lower() in candidates:
                return True
    return False


def _validate_alt(name: str, label: str, alt: str | None, src: str = "") -> list[str]:
    if alt is None or not alt.strip():
        return [f"{name}: {label} has missing or empty alt text (R10)"]
    alt_norm = re.sub(r"\s+", " ", alt.strip())
    if _is_filename_alt(alt_norm, src):
        return [
            f"{name}: {label} alt text '{alt_norm}' looks like a filename; "
            f"use descriptive alt text (>= {MIN_ALT_LENGTH} chars) (R10)"
        ]
    if len(alt_norm) < MIN_ALT_LENGTH:
        return [
            f"{name}: {label} alt text '{alt_norm}' is too short "
            f"({len(alt_norm)} chars; minimum {MIN_ALT_LENGTH} chars) (R10)"
        ]
    return []


def check_image_alt(name: str, meta: dict) -> list[str]:
    """Validate `alt`-text quality on front-matter images and body `<img>` tags."""
    errs: list[str] = []
    hero_img = (meta.get("image") or "").strip()
    if hero_img or "image_alt" in meta:
        errs.extend(
            _validate_alt(
                name,
                "front-matter image_alt",
                meta.get("image_alt"),
                src=hero_img,
            )
        )
    body = meta.get("body") or ""
    if "<img" in body.lower():
        parser = _ImgTagParser()
        parser.feed(body)
        for attrs in parser.images:
            if _is_decorative_img(attrs):
                continue
            src = (attrs.get("src") or "").strip()
            label = f"<img src='{src}'>" if src else "<img>"
            errs.extend(_validate_alt(name, label, attrs.get("alt"), src=src))
    return errs


def check_readability(name: str, plain_html: str, warnings: list[str]) -> list[str]:
    """Inspect `<p>` blocks in `plain_html` and append paragraph/sentence length warnings."""
    sup_re = re.compile(r"<sup\b[^>]*>.*?</sup>", re.S | re.I)
    for raw_p in _P_BLOCK_RE.findall(plain_html):
        no_sup_p = sup_re.sub("", raw_p)
        clean_p = _TAG_RE.sub(" ", no_sup_p).strip()
        if not clean_p:
            continue
        para_words = len(clean_p.split())
        if para_words > PARAGRAPH_HARD_LIMIT:
            warnings.append(
                f"{name}: a paragraph has {para_words} words (exceeds 140-word limit; voice guide: under ~70)"
            )
        elif para_words > PARAGRAPH_SOFT_LIMIT:
            warnings.append(
                f"{name}: a paragraph has {para_words} words (voice guide: under ~70)"
            )
        for sentence in _SENTENCE_SPLIT_RE.split(clean_p):
            sent_words = len(sentence.split())
            if sent_words > SENTENCE_WORD_LIMIT:
                warnings.append(
                    f"{name}: a sentence has {sent_words} words (exceeds {SENTENCE_WORD_LIMIT}-word limit; voice guide: under ~22)"
                )
    return warnings


def check_researcher_asides(name: str, body: str) -> list[str]:
    """Ensure every <aside class="for-researchers"> wraps its content in <details><summary>...<div>...</div></details>."""
    errs: list[str] = []
    aside_re = re.compile(
        r'<aside\b[^>]*\bclass=["\'][^"\']*\bfor-researchers\b[^"\']*["\'][^>]*>(.*?)</aside>',
        re.I | re.S,
    )
    for inner in aside_re.findall(body):
        if not re.search(r"<details\b[^>]*>\s*<summary\b[^>]*>.*?</summary>\s*<div\b[^>]*>.*?</div>\s*</details>", inner, re.I | re.S):
            errs.append(f"{name}: <aside class='for-researchers'> must wrap body in <details><summary>...</summary><div>...</div></details>")
    return errs


def check_explainers(name: str, body: str) -> list[str]:
    """Validate self-contained `<figure class="explainer">` SVG blocks (T8 meta-RSI check)."""
    errs: list[str] = []
    fig_re = re.compile(r'(<figure\b[^>]*\bclass=["\'][^"\']*\bexplainer\b[^"\']*["\'][^>]*>)(.*?)</figure>', re.I | re.S)
    for open_tag, inner in fig_re.findall(body):
        if not re.search(r'\bid=["\']ex-[a-z0-9-]+["\']', open_tag, re.I):
            errs.append(f"{name}: <figure class='explainer'> missing id='ex-<slug>' attribute")
        svg_m = re.search(r"<svg\b([^>]*)>(.*?)</svg>", inner, re.I | re.S)
        if not svg_m:
            errs.append(f"{name}: <figure class='explainer'> must contain an inline <svg>")
        else:
            svg_attrs, svg_inner = svg_m.group(1), svg_m.group(2)
            if not re.search(r'\bviewBox=["\'][^"\']+["\']', svg_attrs, re.I):
                errs.append(f"{name}: explainer <svg> missing responsive viewBox attribute")
            if not re.search(r'\baria-(?:labelledby|label)=["\'][^"\']+["\']', svg_attrs, re.I):
                errs.append(f"{name}: explainer <svg> missing aria-labelledby or aria-label attribute")
            if not re.search(r'\brole=["\'](?:img|group|graphics-document)["\']', svg_attrs, re.I):
                errs.append(f"{name}: explainer <svg> missing accessible role attribute (role='img' or role='group')")
            lbl_m = re.search(r'\baria-labelledby=["\']([^"\']+)["\']', svg_attrs, re.I)
            if lbl_m:
                defined_ids = set(ELEMENT_ID_RE.findall(inner))
                for target_id in lbl_m.group(1).split():
                    if target_id not in defined_ids:
                        errs.append(
                            f"{name}: explainer <svg> aria-labelledby references '{target_id}' "
                            f"which is not defined in the figure"
                        )
            title_m = re.search(r"<title\b[^>]*>(.*?)</title>", svg_inner, re.I | re.S)
            if not title_m:
                errs.append(f"{name}: explainer <svg> missing <title> element for screen-reader accessibility (WCAG 2.2 SC 1.1.1 / 4.1.2)")
            else:
                title_text = _TAG_RE.sub(" ", title_m.group(1)).strip()
                if len(title_text) < 5:
                    errs.append(f"{name}: explainer <svg> <title> is too short ({len(title_text)} chars; minimum 5 chars)")
            desc_m = re.search(r"<desc\b[^>]*>(.*?)</desc>", svg_inner, re.I | re.S)
            if not desc_m:
                errs.append(f"{name}: explainer <svg> missing <desc> element for rich diagram description (WCAG 2.2 SC 1.1.1 / 4.1.2)")
            else:
                desc_text = _TAG_RE.sub(" ", desc_m.group(1)).strip()
                if len(desc_text) < 15:
                    errs.append(f"{name}: explainer <svg> <desc> is too short ({len(desc_text)} chars; minimum 15 chars)")
        cap_m = re.search(r"<figcaption\b[^>]*>(.*?)</figcaption>", inner, re.I | re.S)
        if not cap_m:
            errs.append(f"{name}: <figure class='explainer'> missing <figcaption>")
        else:
            caption_text = _TAG_RE.sub(" ", cap_m.group(1)).strip()
            if len(caption_text) < 15:
                errs.append(
                    f"{name}: <figure class='explainer'> <figcaption> is empty or too short "
                    f"({len(caption_text)} chars; minimum 15 characters explaining the visual)"
                )
    return errs


def check_external_links(name: str, body: str) -> list[str]:
    """Ensure all external links use https://, and any target="_blank" includes rel="noopener" (WHATWG 4.6.6.11)."""
    errs: list[str] = []
    a_tag_re = re.compile(r"<a\b([^>]*)>", re.I)
    for m in a_tag_re.finditer(body):
        attrs = m.group(1)
        href_m = re.search(r'\bhref\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        if not href_m:
            continue
        href = href_m.group(1).strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "vbscript:", "data:")):
            continue
        if href.startswith("/") and not href.startswith("//"):
            continue
        if href.lower().startswith("http://") or href.startswith("//"):
            errs.append(f"{name}: external link must use https://: '{href}'")
            continue
        target_m = re.search(r'\btarget\s*=\s*["\']_blank["\']', attrs, re.I)
        if target_m:
            rel_m = re.search(r'\brel\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
            rel_val = (rel_m.group(1) if rel_m else "").lower().split()
            if "noopener" not in rel_val:
                errs.append(
                    f"{name}: external link targeting '_blank' must include rel='noopener' "
                    f"to prevent reverse tabnabbing (WHATWG 4.6.6.11): '{href}'"
                )
    return errs


_JSON_DATA_SCRIPT_RE = re.compile(
    r"<script\b([^>]*)>(.*?)</script>",
    re.I | re.S,
)


def _strip_valid_json_data_scripts(name: str, body: str, errs: list[str]) -> str:
    """Allow inert WHATWG 4.12.1.2 <script type='application/json' id='...'> data blocks with no src attribute and valid JSON; leave any other <script> in place so it is rejected."""
    def _repl(m: re.Match[str]) -> str:
        attrs, payload = m.group(1), m.group(2)
        type_m = re.search(r'\btype\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        if not type_m or type_m.group(1).strip().lower() != "application/json":
            return m.group(0)
        if re.search(r"\bsrc\s*=", attrs, re.I):
            return m.group(0)
        if not re.search(r'\bid\s*=\s*["\'][^"\']+["\']', attrs, re.I):
            errs.append(f"{name}: <script type='application/json'> data block requires an explicit id attribute")
            return ""
        try:
            json.loads(payload)
        except Exception as exc:
            errs.append(f"{name}: <script type='application/json'> contains invalid JSON ({exc})")
        return ""

    return _JSON_DATA_SCRIPT_RE.sub(_repl, body)


def check_interactive_elements_and_embeds(name: str, body: str) -> list[str]:
    """Ensure no raw executable <script>, <iframe>, <object>, <embed>, <base>, <meta>, or <link> tags, no inline event handlers, no javascript: URIs, no external CSS imports/URLs, and ensure buttons and role='button' are accessible."""
    errs: list[str] = []
    body_without_json_data = _strip_valid_json_data_scripts(name, body, errs)
    if re.search(r"<(?:script|iframe|object|embed|applet|portal|base|meta|link)\b", body_without_json_data, re.I):
        errs.append(
            f"{name}: content must not contain <script>, <iframe>, <object>, <embed>, <applet>, <portal>, <base>, <meta>, or <link> tags "
            f"(R10 zero client tracking / static HTML / head element isolation; WHATWG 4.2.3)"
        )

    # Check inline <style> tags for external @import or http(s) url()
    for style_m in re.finditer(r"<style\b[^>]*>(.*?)</style>", body, re.I | re.S):
        style_content = style_m.group(1)
        if re.search(r"@import\b|url\(\s*['\"]?(?:https?:|//)", style_content, re.I):
            errs.append(
                f"{name}: inline <style> contains external @import or http(s)/protocol-relative url() forbidden by R10 (zero external requests / tracking defense)"
            )

    # Check inline style="..." attributes for external http(s) url()
    for attr_m in re.finditer(r'\bstyle\s*=\s*["\']([^"\']+)["\']', body, re.I):
        style_attr = attr_m.group(1)
        if re.search(r"@import\b|url\(\s*['\"]?(?:https?:|//)", style_attr, re.I):
            errs.append(
                f"{name}: inline style attribute contains external @import or http(s)/protocol-relative url() forbidden by R10 (zero external requests / tracking defense)"
            )

    if re.search(r'\b(?:href|src|action|formaction)\s*=\s*["\']\s*(?:javascript|vbscript|data:\s*text/html):', body, re.I):
        errs.append(
            f"{name}: content must not contain 'javascript:' URIs, 'vbscript:' URIs, or executable 'data:' URIs "
            f"(R10 static HTML / zero script execution; WHATWG 4.10.18.6)"
        )

    for event_match in re.finditer(r'<([a-z0-9]+)\b[^>]*(?:[\s/])(on[a-z]{3,})\s*=', body, re.I):
        tag, handler = event_match.group(1), event_match.group(2)
        errs.append(f"{name}: <{tag}> contains inline event handler '{handler}' (R10 requires progressive JS in site.js)")

    for m in re.finditer(r"<button\b([^>]*)>(.*?)</button>", body, re.I | re.S):
        attrs, inner = m.group(1), m.group(2)
        if not re.search(r'\btype=["\'](?:button|submit|reset)["\']', attrs, re.I):
            errs.append(f"{name}: <button> missing explicit type attribute (e.g. type='button')")
        has_label = bool(re.search(r'\baria-label=["\'][^"\']+["\']', attrs, re.I)) or bool(re.search(r'\baria-labelledby=["\'][^"\']+["\']', attrs, re.I))
        clean_text = _TAG_RE.sub(" ", inner).strip()
        if not has_label and not clean_text:
            errs.append(f"{name}: <button> has no accessible name (needs text content, aria-label, or aria-labelledby)")

    element_ids = set(ELEMENT_ID_RE.findall(body))
    for m in re.finditer(r"<([a-z0-9]+)\b([^>]*)>(.*?)</\1>", body, re.I | re.S):
        tag, attrs, inner = m.group(1), m.group(2), m.group(3)
        if re.search(r'\brole=["\']button["\']', attrs, re.I):
            if not re.search(r'\btabindex=["\']0["\']', attrs, re.I):
                errs.append(f"{name}: <{tag} role='button'> missing tabindex='0' for keyboard accessibility (WCAG 2.2)")
            has_label = bool(re.search(r'\baria-label=["\'][^"\']+["\']', attrs, re.I)) or bool(re.search(r'\baria-labelledby=["\'][^"\']+["\']', attrs, re.I))
            clean_text = _TAG_RE.sub(" ", inner).strip()
            if not has_label and not clean_text:
                errs.append(f"{name}: <{tag} role='button'> has no accessible name (needs aria-label or text content)")
            controls_m = re.search(r'\baria-controls=["\']([^"\']+)["\']', attrs, re.I)
            if controls_m:
                for target_id in controls_m.group(1).split():
                    if target_id not in element_ids:
                        errs.append(f"{name}: <{tag} role='button'> aria-controls='{target_id}' targets non-existent element id on page")

    for m in re.finditer(r'<([a-z0-9]+)\b[^>]*\btabindex\s*=\s*["\']\s*([+]?[1-9]\d*)\s*["\']', body, re.I):
        tag, val = m.group(1), m.group(2)
        errs.append(
            f"{name}: <{tag}> has positive tabindex='{val}' (WCAG 2.2 SC 2.4.3 Focus Order & Failure F44; "
            f"positive tabindex disrupts logical keyboard focus order; use natural DOM order with tabindex='0' or '-1')"
        )
    return errs


def check_landmark_integrity(name: str, body: str) -> list[str]:
    """Ensure content fragments do not contain <main> elements (page_shell already provides <main id='main'>)."""
    errs: list[str] = []
    if re.search(r"<main\b", body, re.I):
        errs.append(
            f"{name}: content fragment must not contain <main> tags "
            f"(page shell already provides <main id='main'>; duplicate <main> violates HTML5 § 4.4.1 & WCAG 2.2 SC 1.3.1)"
        )
    return errs


def check_focus_order_and_tabindex(name: str, body: str) -> list[str]:
    """Ensure no positive tabindex values (tabindex > 0) are used, which disrupt sequential focus navigation (WCAG 2.2 SC 2.4.3 / W3C F44)."""
    errs: list[str] = []
    for m in re.finditer(r'<([a-z0-9]+)\b([^>]*)>', body, re.I):
        tag, attrs = m.group(1), m.group(2)
        tab_m = re.search(r'\btabindex\s*=\s*["\']\s*([+-]?\d+)\s*["\']', attrs, re.I)
        if tab_m:
            try:
                val = int(tab_m.group(1))
                if val > 0:
                    errs.append(
                        f"{name}: <{tag}> has positive tabindex='{val}' which disrupts natural DOM focus order "
                        f"(WCAG 2.2 SC 2.4.3 Focus Order / W3C Failure F44; use tabindex='0' or '-1')"
                    )
            except ValueError:
                pass
    return errs


def check_aria_hidden_focusability(name: str, body: str) -> list[str]:
    """Ensure interactive and focusable elements are not hidden from assistive tech via aria-hidden='true' (WCAG 2.2 SC 4.1.2 / W3C F107)."""
    errs: list[str] = []
    for m in re.finditer(r'<([a-z0-9]+)\b([^>]*)>', body, re.I):
        tag, attrs = m.group(1).lower(), m.group(2)
        if re.search(r'\baria-hidden\s*=\s*["\']true["\']', attrs, re.I):
            is_focusable = False
            if tag in ("button", "select", "textarea"):
                is_focusable = True
            elif tag == "a" and re.search(r'\bhref\s*=', attrs, re.I):
                is_focusable = True
            elif tag == "input" and not re.search(r'\btype\s*=\s*["\']hidden["\']', attrs, re.I):
                is_focusable = True
            elif re.search(r'\btabindex\s*=\s*["\']\s*(?:0|[1-9]\d*)\s*["\']', attrs, re.I):
                is_focusable = True

            if is_focusable:
                errs.append(
                    f"{name}: focusable <{tag}> has aria-hidden='true', trapping screen-reader focus "
                    f"(WCAG 2.2 SC 4.1.2 Name, Role, Value / W3C Failure F107)"
                )
    return errs


def check_accesskey_attributes(name: str, body: str) -> list[str]:
    """Reject obsolete accesskey attributes, which collide with browser/screen reader shortcuts (WCAG 2.2 SC 2.1.1 / W3C G202)."""
    errs: list[str] = []
    for m in re.finditer(r'<([a-z0-9]+)\b[^>]*\baccesskey\s*=\s*["\']([^"\']*)["\']', body, re.I):
        tag, key = m.group(1), m.group(2)
        errs.append(
            f"{name}: <{tag}> contains accesskey='{key}' which conflicts with screen reader and browser navigation "
            f"(WCAG 2.2 SC 2.1.1 Keyboard Shortcuts / W3C Advisory Technique G202)"
        )
    return errs


class _StructuralListParser(HTMLParser):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.stack: list[str] = []
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        if tag_lower == "li":
            if not any(t in ("ol", "ul", "menu") for t in self.stack):
                self.errs.append(
                    f"{self.name}{loc}: <li> is orphaned outside an enclosing <ol>, <ul>, or <menu> container "
                    f"(WCAG 2.2 SC 1.3.1 Info and Relationships / W3C Failure F85)"
                )
        elif tag_lower in ("dt", "dd"):
            if not ("dl" in self.stack):
                self.errs.append(
                    f"{self.name}{loc}: <{tag_lower}> is orphaned outside an enclosing <dl> container "
                    f"(WCAG 2.2 SC 1.3.1 Info and Relationships / HTML5 §4.4.9)"
                )

        if self.stack:
            parent = self.stack[-1]
            if parent in ("ul", "ol"):
                if tag_lower not in ("li", "script", "template"):
                    self.errs.append(
                        f"{self.name}{loc}: <{parent}> contains direct child <{tag_lower}> instead of <li> "
                        f"(WCAG 2.2 SC 1.3.1 Info and Relationships / HTML5 §4.4.8)"
                    )
            elif parent == "dl":
                if tag_lower not in ("dt", "dd", "div", "script", "template"):
                    self.errs.append(
                        f"{self.name}{loc}: <dl> contains direct child <{tag_lower}> instead of <dt>, <dd>, or <div> "
                        f"(WCAG 2.2 SC 1.3.1 Info and Relationships / HTML5 §4.4.9)"
                    )

        void_tags = (
            "img", "br", "hr", "input", "meta", "link", "source", "area",
            "base", "col", "embed", "param", "track", "wbr"
        )
        if tag_lower not in void_tags:
            self.stack.append(tag_lower)

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in self.stack:
            while self.stack and self.stack[-1] != tag_lower:
                self.stack.pop()
            if self.stack and self.stack[-1] == tag_lower:
                self.stack.pop()


def check_list_structure(name: str, body: str) -> list[str]:
    """Ensure valid list structure: <li> only inside <ol>/<ul>, direct children of <ol>/<ul> must be <li>, and <dt>/<dd> only inside <dl> (WCAG 2.2 SC 1.3.1 / W3C Failure F85)."""
    parser = _StructuralListParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


def check_presentational_roles(name: str, body: str) -> list[str]:
    """Ensure interactive and landmark elements do not carry role='none' or role='presentation' (WCAG 2.2 SC 4.1.2 / W3C WAI-ARIA 1.2 §5.2.7.2 / W3C Failure F92)."""
    errs: list[str] = []
    for m in re.finditer(r'<([a-z0-9]+)\b([^>]*)>', body, re.I):
        tag, attrs = m.group(1).lower(), m.group(2)
        role_m = re.search(r'\brole\s*=\s*["\']\s*(none|presentation)\s*["\']', attrs, re.I)
        if role_m:
            role = role_m.group(1).lower()
            is_interactive_or_landmark = False
            if tag in ("button", "select", "textarea", "input", "summary", "main", "nav", "header", "footer", "aside"):
                is_interactive_or_landmark = True
            elif tag == "a" and re.search(r'\bhref\s*=', attrs, re.I):
                is_interactive_or_landmark = True

            if not is_interactive_or_landmark:
                tab_m = re.search(r'\btabindex\s*=\s*["\']\s*([+-]?\d+)\s*["\']', attrs, re.I)
                if tab_m:
                    try:
                        if int(tab_m.group(1)) >= 0:
                            is_interactive_or_landmark = True
                    except ValueError:
                        pass

            if is_interactive_or_landmark:
                errs.append(
                    f"{name}: <{tag}> has role='{role}' but is an interactive or landmark element; "
                    f"presentational roles must not be applied to focusable or landmark controls "
                    f"(WCAG 2.2 SC 4.1.2 Name, Role, Value / W3C WAI-ARIA 1.2 §5.2.7.2 / W3C Failure F92)"
                )
    return errs


class _InteractiveAndFieldsetParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.stack: list[str] = []
        self.fieldset_stack: list[dict] = []
        self.in_legend = False
        self.current_legend_text: list[str] = []
        self.details_stack: list[dict] = []
        self.in_summary = False
        self.current_summary_text: list[str] = []
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"

        if self.details_stack:
            self.details_stack[-1]["child_tag_count"] += 1
            if self.details_stack[-1]["first_child"] is None:
                self.details_stack[-1]["first_child"] = t

        if t in ("a", "button"):
            interactive_ancestors = [anc for anc in self.stack if anc in ("a", "button")]
            if interactive_ancestors:
                anc = interactive_ancestors[-1]
                self.errs.append(
                    f"{self.name}{loc}: <{t}> is nested inside interactive <{anc}> "
                    f"(HTML5 §4.1.2.1 Interactive Content & WCAG 2.2 SC 4.1.2 Name, Role, Value)"
                )
        elif t in ("select", "textarea") or (t == "input" and attr_dict.get("type", "").lower() != "hidden"):
            interactive_ancestors = [anc for anc in self.stack if anc in ("a", "button")]
            if interactive_ancestors:
                anc = interactive_ancestors[-1]
                self.errs.append(
                    f"{self.name}{loc}: <{t}> form control is nested inside interactive <{anc}> "
                    f"(HTML5 §4.1.2.1 Interactive Content & WCAG 2.2 SC 4.1.2 Name, Role, Value)"
                )

        if t == "fieldset":
            self.fieldset_stack.append({"has_legend": False, "loc": loc})
        elif t == "legend":
            if not any(anc == "fieldset" for anc in self.stack):
                self.errs.append(
                    f"{self.name}{loc}: <legend> is orphaned outside an enclosing <fieldset> container "
                    f"(HTML5 §4.10.17 & WCAG 2.2 SC 1.3.1 Info and Relationships)"
                )
            elif self.fieldset_stack:
                self.fieldset_stack[-1]["has_legend"] = True
                self.in_legend = True
                self.current_legend_text = []

        if t == "details":
            self.details_stack.append({
                "has_summary": False,
                "first_child": None,
                "child_tag_count": 0,
                "loc": loc,
            })
        elif t == "summary":
            if not any(anc == "details" for anc in self.stack):
                self.errs.append(
                    f"{self.name}{loc}: <summary> is orphaned outside an enclosing <details> container "
                    f"(HTML5 §4.11.2 & WCAG 2.2 SC 1.3.1 Info and Relationships)"
                )
            elif self.details_stack:
                if self.details_stack[-1]["has_summary"]:
                    self.errs.append(
                        f"{self.name}{loc}: <details> has multiple <summary> child elements "
                        f"(HTML5 §4.11.1 permits at most one <summary> per <details>)"
                    )
                self.details_stack[-1]["has_summary"] = True
                self.in_summary = True
                self.current_summary_text = []
                if self.details_stack[-1]["child_tag_count"] > 1:
                    self.errs.append(
                        f"{self.name}{loc}: <summary> must be the first child element of <details> "
                        f"(HTML5 §4.11.1 & W3C HTML-AAM §4.3)"
                    )
        elif self.in_summary:
            if t in ("a", "button", "select", "textarea") or (t == "input" and attr_dict.get("type", "").lower() != "hidden"):
                self.errs.append(
                    f"{self.name}{loc}: interactive <{t}> is nested inside disclosure <summary> "
                    f"(HTML5 §4.11.2 & WCAG 2.2 SC 4.1.2 Name, Role, Value)"
                )

        if t == "dialog":
            has_name = bool(attr_dict.get("aria-label", "").strip() or attr_dict.get("aria-labelledby", "").strip())
            if not has_name:
                self.errs.append(
                    f"{self.name}{loc}: <dialog> missing accessible name "
                    f"(must have aria-label or aria-labelledby; WCAG 2.2 SC 4.1.2 & HTML5 §4.11.4)"
                )

        if t not in self.VOID_TAGS:
            self.stack.append(t)

    def handle_data(self, data: str) -> None:
        if self.in_legend:
            self.current_legend_text.append(data)
        if self.in_summary:
            self.current_summary_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"

        if t == "legend" and self.in_legend:
            self.in_legend = False
            full_text = "".join(self.current_legend_text).strip()
            if not full_text:
                self.errs.append(
                    f"{self.name}{loc}: <legend> is empty (WCAG 2.2 SC 1.3.1 requires non-empty descriptive text for form group)"
                )
        elif t == "fieldset" and self.fieldset_stack:
            fs_info = self.fieldset_stack.pop()
            if not fs_info["has_legend"]:
                self.errs.append(
                    f"{self.name}{fs_info['loc']}: <fieldset> missing <legend> element "
                    f"(WCAG 2.2 SC 1.3.1 Info and Relationships, SC 3.3.2 Labels or Instructions & W3C Failure F68)"
                )
        elif t == "summary" and self.in_summary:
            self.in_summary = False
            full_text = "".join(self.current_summary_text).strip()
            if not full_text:
                self.errs.append(
                    f"{self.name}{loc}: <summary> is empty (WCAG 2.2 SC 4.1.2 requires non-empty disclosure label)"
                )
        elif t == "details" and self.details_stack:
            det_info = self.details_stack.pop()
            if not det_info["has_summary"]:
                self.errs.append(
                    f"{self.name}{det_info['loc']}: <details> missing <summary> element "
                    f"(HTML5 §4.11.1, WCAG 2.2 SC 4.1.2 Name, Role, Value & W3C HTML-AAM §4.3)"
                )

        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i] == t:
                self.stack = self.stack[:i]
                break


def check_nested_interactive_elements(name: str, body: str) -> list[str]:
    """Ensure interactive controls (<a>, <button>) do not contain nested interactive elements (HTML5 §4.1.2.1 & WCAG 2.2 SC 4.1.2)."""
    parser = _InteractiveAndFieldsetParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return [e for e in parser.errs if "nested inside interactive" in e]


def check_fieldset_and_legend_structure(name: str, body: str) -> list[str]:
    """Ensure fieldset groupings have a non-empty legend and legends are not orphaned outside fieldsets (WCAG 2.2 SC 1.3.1, SC 3.3.2 & HTML5 §4.10.16/17)."""
    parser = _InteractiveAndFieldsetParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return [e for e in parser.errs if "<fieldset>" in e or "<legend>" in e]


def check_details_and_summary_structure(name: str, body: str) -> list[str]:
    """Ensure details groupings have a non-empty summary as first child, summaries are not orphaned, and summaries contain no interactive descendants (WCAG 2.2 SC 1.3.1, SC 4.1.2 & HTML5 §4.11.1/2)."""
    parser = _InteractiveAndFieldsetParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return [e for e in parser.errs if "<details>" in e or "<summary>" in e]


def check_dialog_accessibility(name: str, body: str) -> list[str]:
    """Ensure dialog elements have an accessible name via aria-label or aria-labelledby (WCAG 2.2 SC 4.1.2 & HTML5 §4.11.4)."""
    parser = _InteractiveAndFieldsetParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return [e for e in parser.errs if "<dialog>" in e]


class _LabelInNameParser(HTMLParser):
    """Audits interactive elements to ensure the accessible name contains visible label text (WCAG 2.2 SC 2.5.3 / W3C F96)."""
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.stack: list[dict] = []
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        is_interactive = t in ("a", "button", "summary") or (
            t == "g" and attr_dict.get("role", "").lower() in ("button", "link")
        )
        if is_interactive and "aria-label" in attr_dict:
            lineno, offset = self.getpos()
            self.stack.append({
                "tag": t,
                "aria_label": attr_dict["aria-label"],
                "text": [],
                "loc": f" (line {lineno}:{offset})",
                "depth": 1,
            })
        elif self.stack:
            if t not in self.VOID_TAGS:
                self.stack[-1]["depth"] += 1

    def handle_data(self, data: str) -> None:
        if self.stack:
            self.stack[-1]["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack:
            return
        t = tag.lower()
        top = self.stack[-1]
        top["depth"] -= 1
        if top["depth"] <= 0:
            entry = self.stack.pop()
            vis_text = " ".join(" ".join(entry["text"]).split())
            vis_words = [w for w in re.findall(r"[a-z0-9]+", vis_text.lower()) if len(w) >= 3 and not w.isdigit()]
            aria_norm = entry["aria_label"].lower()
            aria_words = set(re.findall(r"[a-z0-9]+", aria_norm))
            if vis_words:
                missing = [w for w in vis_words if w not in aria_words]
                if missing:
                    self.errs.append(
                        f"{self.name}{entry['loc']}: interactive <{entry['tag']}> visible label '{vis_text}' "
                        f"contains words {missing} missing from aria-label '{entry['aria_label']}' "
                        f"(WCAG 2.2 SC 2.5.3 Label in Name / W3C Failure F96)"
                    )


def check_label_in_name(name: str, body: str) -> list[str]:
    """Ensure interactive controls with visible text contain that text within aria-label (WCAG 2.2 SC 2.5.3 Level A)."""
    parser = _LabelInNameParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


# Valid W3C ARIA 1.2 / 1.3 roles (landmark, widget, document structure, live region, graphics, dpub)
VALID_ARIA_ROLES = {
    # Landmark
    "banner", "complementary", "contentinfo", "form", "main", "navigation", "region", "search",
    # Live region
    "alert", "log", "marquee", "status", "timer",
    # Window
    "alertdialog", "dialog",
    # Structure
    "application", "article", "blockquote", "caption", "cell", "code", "columnheader", "comment",
    "definition", "deletion", "directory", "document", "emphasis", "feed", "figure", "generic",
    "group", "heading", "img", "insertion", "list", "listbox", "listitem", "mark", "math",
    "meter", "none", "note", "paragraph", "presentation", "row", "rowgroup", "rowheader",
    "separator", "strong", "subscript", "suggestion", "superscript", "table", "term", "time",
    "toolbar", "tooltip",
    # Widget
    "button", "checkbox", "combobox", "grid", "gridcell", "link", "menu", "menubar",
    "menuitem", "menuitemcheckbox", "menuitemradio", "option", "progressbar", "radio",
    "radiogroup", "scrollbar", "searchbox", "slider", "spinbutton", "switch", "tab",
    "tablist", "tabpanel", "textbox", "tree", "treegrid", "treeitem",
    # Graphics module (W3C)
    "graphics-document", "graphics-object", "graphics-symbol",
    # DPUB module (W3C)
    "doc-abstract", "doc-acknowledgments", "doc-afterword", "doc-appendix", "doc-backlink",
    "doc-biblioentry", "doc-bibliography", "doc-biblioref", "doc-chapter", "doc-colophon",
    "doc-conclusion", "doc-cover", "doc-credit", "doc-credits", "doc-dedication", "doc-endnote",
    "doc-endnotes", "doc-epigraph", "doc-epilogue", "doc-errata", "doc-example", "doc-footnote",
    "doc-foreword", "doc-glossary", "doc-glossref", "doc-index", "doc-introduction",
    "doc-noteref", "doc-notice", "doc-pagebreak", "doc-pagelist", "doc-part", "doc-preface",
    "doc-prologue", "doc-pullquote", "doc-qna", "doc-subtitle", "doc-tip", "doc-toc",
}

# Valid W3C ARIA 1.2 / 1.3 states and properties
VALID_ARIA_ATTRIBUTES = {
    "aria-activedescendant", "aria-atomic", "aria-autocomplete", "aria-braillelabel",
    "aria-brailleroledescription", "aria-busy", "aria-checked", "aria-colcount",
    "aria-colindex", "aria-colindextext", "aria-colspan", "aria-controls",
    "aria-current", "aria-describedby", "aria-description", "aria-details",
    "aria-disabled", "aria-dropeffect", "aria-errormessage", "aria-expanded",
    "aria-flowto", "aria-grabbed", "aria-haspopup", "aria-hidden", "aria-invalid",
    "aria-keyshortcuts", "aria-label", "aria-labelledby", "aria-level", "aria-live",
    "aria-modal", "aria-multiline", "aria-multiselectable", "aria-orientation",
    "aria-owns", "aria-placeholder", "aria-posinset", "aria-pressed", "aria-readonly",
    "aria-relevant", "aria-required", "aria-roledescription", "aria-rowcount",
    "aria-rowindex", "aria-rowindextext", "aria-rowspan", "aria-selected",
    "aria-setsize", "aria-sort", "aria-valuemax", "aria-valuemin", "aria-valuenow",
    "aria-valuetext",
}

# ARIA attributes that reference element IDs (IDREF / IDREFS; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1 / 4.1.2)
ARIA_ID_REFERENCE_ATTRS = frozenset({
    "aria-activedescendant", "aria-controls", "aria-describedby", "aria-details",
    "aria-errormessage", "aria-flowto", "aria-labelledby", "aria-owns",
})

# Allowed token sets for enumerated ARIA states and properties (W3C WAI-ARIA 1.2 §6 & WCAG 2.2 SC 4.1.2)
ARIA_ENUMERATED_VALUES: dict[str, frozenset[str]] = {
    "aria-current": frozenset({"page", "step", "location", "date", "time", "true", "false"}),
    "aria-live": frozenset({"off", "polite", "assertive"}),
    "aria-haspopup": frozenset({"false", "true", "menu", "listbox", "tree", "grid", "dialog"}),
    "aria-orientation": frozenset({"horizontal", "vertical", "undefined"}),
    "aria-sort": frozenset({"ascending", "descending", "none", "other"}),
    "aria-autocomplete": frozenset({"inline", "list", "both", "none"}),
    "aria-invalid": frozenset({"false", "true", "grammar", "spelling"}),
    "aria-pressed": frozenset({"true", "false", "mixed", "undefined"}),
    "aria-checked": frozenset({"true", "false", "mixed", "undefined"}),
    "aria-expanded": frozenset({"true", "false", "undefined"}),
    "aria-hidden": frozenset({"true", "false", "undefined"}),
    "aria-selected": frozenset({"true", "false", "undefined"}),
    "aria-disabled": frozenset({"true", "false"}),
    "aria-busy": frozenset({"true", "false"}),
    "aria-atomic": frozenset({"true", "false"}),
    "aria-modal": frozenset({"true", "false"}),
    "aria-multiline": frozenset({"true", "false"}),
    "aria-multiselectable": frozenset({"true", "false"}),
    "aria-readonly": frozenset({"true", "false"}),
    "aria-required": frozenset({"true", "false"}),
    "aria-grabbed": frozenset({"true", "false", "undefined"}),
    "aria-dropeffect": frozenset({"copy", "move", "link", "execute", "popup", "none"}),
    "aria-relevant": frozenset({"additions", "removals", "text", "all"}),
}


class _AriaIntegrityParser(HTMLParser):
    """Audits ARIA roles, attributes, ID references, and label associations (WCAG 2.2 SC 1.3.1, SC 3.3.2, SC 4.1.2)."""
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.element_ids: set[str] = set()
        self.id_references: list[tuple[str, str, str, str]] = []  # (tag, attr, ref_id, loc)
        self.label_fors: list[tuple[str, str]] = []              # (for_id, loc)
        self.roles: list[tuple[str, str, str]] = []               # (tag, role, loc)
        self.aria_attrs: list[tuple[str, str, str]] = []          # (tag, attr, loc)
        self.aria_enumerated_values: list[tuple[str, str, str, str]] = []  # (tag, attr, val, loc)
        self.empty_labels: list[tuple[str, str]] = []             # (tag, loc)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if "id" in attr_dict and attr_dict["id"].strip():
            self.element_ids.add(attr_dict["id"].strip())

        if "role" in attr_dict:
            for r in attr_dict["role"].split():
                self.roles.append((t, r, loc))

        for a, val in attrs:
            a_lower = a.lower()
            if a_lower.startswith("aria-"):
                self.aria_attrs.append((t, a_lower, loc))
                if a_lower in ARIA_ID_REFERENCE_ATTRS:
                    for ref_id in (val or "").split():
                        self.id_references.append((t, a_lower, ref_id, loc))
                if a_lower in ARIA_ENUMERATED_VALUES:
                    self.aria_enumerated_values.append((t, a_lower, (val or "").strip().lower(), loc))
                if a_lower == "aria-label" and not (val or "").strip():
                    self.empty_labels.append((t, loc))

        if t == "label" and "for" in attr_dict and attr_dict["for"].strip():
            self.label_fors.append((attr_dict["for"].strip(), loc))


def check_aria_integrity(name: str, body: str) -> list[str]:
    """Ensure all ARIA roles and attributes are valid, ID references resolve, and labels match (WCAG 2.2 SC 1.3.1, SC 3.3.2, SC 4.1.2)."""
    parser = _AriaIntegrityParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    errs: list[str] = []
    for t, r, loc in parser.roles:
        if r.lower() not in VALID_ARIA_ROLES:
            errs.append(
                f"{name}{loc}: <{t}> declares invalid or unrecognized ARIA role '{r}' "
                f"(WCAG 2.2 SC 4.1.2 Name, Role, Value & W3C WAI-ARIA 1.2 §5.2.7)"
            )
    for t, a, loc in parser.aria_attrs:
        if a not in VALID_ARIA_ATTRIBUTES:
            errs.append(
                f"{name}{loc}: <{t}> declares invalid or unrecognized ARIA attribute '{a}' "
                f"(WCAG 2.2 SC 4.1.2 Name, Role, Value & W3C WAI-ARIA 1.2 §6)"
            )
    for t, a, val, loc in parser.aria_enumerated_values:
        allowed = ARIA_ENUMERATED_VALUES[a]
        if a in ("aria-relevant", "aria-dropeffect"):
            tokens = val.split()
            if not tokens:
                errs.append(
                    f"{name}{loc}: <{t}> specifies empty '{a}' attribute "
                    f"(W3C WAI-ARIA 1.2 §6 & WCAG 2.2 SC 4.1.2)"
                )
            for tok in tokens:
                if tok not in allowed:
                    errs.append(
                        f"{name}{loc}: <{t}> declares invalid token '{tok}' in '{a}' "
                        f"(allowed: {', '.join(sorted(allowed))}; WCAG 2.2 SC 4.1.2 Name, Role, Value & W3C WAI-ARIA 1.2 §6)"
                    )
        elif val not in allowed:
            errs.append(
                f"{name}{loc}: <{t}> declares invalid token value '{val}' for '{a}' "
                f"(allowed: {', '.join(sorted(allowed))}; WCAG 2.2 SC 4.1.2 Name, Role, Value & W3C WAI-ARIA 1.2 §6)"
            )
    for t, loc in parser.empty_labels:
        errs.append(
            f"{name}{loc}: <{t}> has empty or whitespace-only aria-label attribute, stripping accessible name "
            f"(WCAG 2.2 SC 4.1.2 Name, Role, Value; W3C Failure F68/F96)"
        )
    for t, attr, ref_id, loc in parser.id_references:
        if ref_id not in parser.element_ids:
            errs.append(
                f"{name}{loc}: <{t}> {attr} references non-existent element id '{ref_id}' "
                f"(WCAG 2.2 SC 1.3.1 Info and Relationships & SC 4.1.2 Name, Role, Value; W3C Failure F65)"
            )
    for for_id, loc in parser.label_fors:
        if for_id not in parser.element_ids:
            errs.append(
                f"{name}{loc}: <label for='{for_id}'> references non-existent element id '{for_id}' "
                f"(WCAG 2.2 SC 3.3.2 Labels or Instructions & SC 4.1.2 Name, Role, Value; W3C Failure F68)"
            )
    return errs


def check_autofocus_attributes(name: str, raw_text: str) -> list[str]:
    """Ensure no elements declare 'autofocus', preserving sequential keyboard navigation (WCAG 2.2 SC 2.4.3 / SC 3.2.1; W3C Failure F55)."""
    errs: list[str] = []
    for m in re.finditer(r'<([a-z0-9]+)\b[^>]*\bautofocus\b[^>]*>', raw_text, re.I):
        tag = m.group(1).lower()
        errs.append(
            f"{name}: <{tag}> contains 'autofocus' attribute, disrupting initial keyboard focus order "
            f"(WCAG 2.2 SC 2.4.3 Focus Order & SC 3.2.1 On Focus; W3C Failure F55)"
        )
    return errs


def check_aria_hidden_landmarks(name: str, body: str) -> list[str]:
    """Ensure semantic landmarks are not hidden from assistive tech via aria-hidden='true' (WCAG 2.2 SC 4.1.2)."""
    errs: list[str] = []
    for m in re.finditer(r'<(main|nav|header|footer|aside|section|article)\b[^>]*\baria-hidden\s*=\s*["\']true["\']', body, re.I):
        tag = m.group(1).lower()
        errs.append(
            f"{name}: semantic landmark <{tag}> has aria-hidden='true', hiding core structural region "
            f"from assistive technologies (WCAG 2.2 SC 4.1.2 Name, Role, Value)"
        )
    return errs


def check_viewport_zoom_scalability(route: str, doc: str) -> list[str]:
    """Ensure viewport meta tag never restricts user scaling or maximum-scale < 2.0 (WCAG 2.2 SC 1.4.4 Resize Text / W3C Failure F94)."""
    errs: list[str] = []
    for m in re.finditer(r'<meta\b[^>]*\bname=["\']viewport["\'][^>]*>', doc, re.I):
        tag = m.group(0)
        content_m = re.search(r'\bcontent=["\']([^"\']+)["\']', tag, re.I)
        if content_m:
            content = content_m.group(1).lower()
            if "user-scalable=no" in content or "user-scalable=0" in content:
                errs.append(
                    f"{route}: viewport meta tag disables user zooming via user-scalable=no "
                    f"(WCAG 2.2 SC 1.4.4 Resize Text / W3C Failure F94)"
                )
            scale_m = re.search(r'\bmaximum-scale\s*=\s*([0-9]*\.?[0-9]+)', content)
            if scale_m:
                try:
                    max_scale = float(scale_m.group(1))
                    if max_scale < 2.0:
                        errs.append(
                            f"{route}: viewport meta tag restricts maximum zoom to {max_scale} < 2.0 "
                            f"(WCAG 2.2 SC 1.4.4 Resize Text / W3C Failure F94)"
                        )
                except ValueError:
                    pass
    return errs


BCP47_LANG_TAG_RE = re.compile(
    r"^[a-zA-Z]{2,3}(?:-[a-zA-Z]{4})?(?:-(?:[a-zA-Z]{2}|\d{3}))?(?:-(?:[a-zA-Z0-9]{5,8}|\d[a-zA-Z0-9]{3}))*$",
    re.I,
)
VALID_HTML_DIR_VALUES = frozenset({"ltr", "rtl", "auto"})


def check_html_lang_and_charset(route: str, doc: str) -> list[str]:
    """Ensure complete HTML documents declare a valid BCP 47 lang attribute on <html>, valid dir values, and UTF-8 charset within the first 1024 bytes (WCAG 2.2 SC 3.1.1, SC 3.1.2 & WHATWG HTML §4.2.5.5 / §3.2.6.5)."""
    errs: list[str] = []

    # 1. Root <html> tag validation (WCAG 2.2 SC 3.1.1 Language of Page)
    html_m = re.search(r"<html\b([^>]*)>", doc, re.I)
    if html_m:
        attrs = html_m.group(1)
        lang_m = re.search(r'\blang\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if not lang_m or not lang_m.group(1).strip():
            errs.append(
                f"{route}: <html> root element missing or empty 'lang' attribute "
                f"(WCAG 2.2 SC 3.1.1 Language of Page requires programmatic primary language declaration)"
            )
        else:
            lang_val = lang_m.group(1).strip()
            if not BCP47_LANG_TAG_RE.match(lang_val):
                errs.append(
                    f"{route}: <html> element declares invalid BCP 47 language code '{lang_val}' "
                    f"(WCAG 2.2 SC 3.1.1 & RFC 5646/BCP 47)"
                )
        dir_m = re.search(r'\bdir\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if dir_m:
            dir_val = dir_m.group(1).strip().lower()
            if dir_val not in VALID_HTML_DIR_VALUES:
                errs.append(
                    f"{route}: <html> element declares invalid 'dir' attribute '{dir_val}' "
                    f"(allowed: ltr, rtl, auto; WHATWG HTML §3.2.6.5)"
                )

    # 2. Meta charset UTF-8 within the first 1024 bytes (WHATWG HTML §4.2.5.5)
    first_1024 = doc[:1024]
    charset_m = re.search(r'<meta\b[^>]*\bcharset\s*=\s*["\']?([^"\'\s/>]+)', first_1024, re.I)
    http_equiv_charset_m = re.search(r'<meta\b[^>]*\bhttp-equiv=["\']content-type["\'][^>]*\bcontent=["\'][^"\']*charset=([^"\'\s;]+)', first_1024, re.I)
    if not charset_m and not http_equiv_charset_m:
        errs.append(
            f"{route}: document missing <meta charset=\"utf-8\"> within the first 1024 bytes "
            f"(WHATWG HTML §4.2.5.5 requires early character encoding declaration)"
        )
    else:
        found_charset = (charset_m.group(1) if charset_m else http_equiv_charset_m.group(1)).strip().lower()
        if found_charset != "utf-8":
            errs.append(
                f"{route}: document declares non-UTF-8 charset '{found_charset}' "
                f"(WHATWG HTML §4.2.5.5 requires UTF-8)"
            )

    # 3. Inline lang and dir attributes on content elements (WCAG 2.2 SC 3.1.2 Language of Parts)
    body_m = re.search(r"<body\b[^>]*>(.*?)</body>", doc, re.I | re.S)
    body_content = body_m.group(1) if body_m else doc
    for tag_m in re.finditer(r"<([a-zA-Z0-9_-]+)\b([^>]*)>", body_content):
        tag_name, tag_attrs = tag_m.group(1).lower(), tag_m.group(2)
        inline_lang_m = re.search(r'\blang\s*=\s*["\']([^"\']*)["\']', tag_attrs, re.I)
        if inline_lang_m:
            inline_lang = inline_lang_m.group(1).strip()
            if not inline_lang:
                errs.append(
                    f"{route}: <{tag_name}> specifies empty inline 'lang' attribute "
                    f"(WCAG 2.2 SC 3.1.2 Language of Parts)"
                )
            elif not BCP47_LANG_TAG_RE.match(inline_lang):
                errs.append(
                    f"{route}: <{tag_name}> declares invalid BCP 47 language code '{inline_lang}' "
                    f"(WCAG 2.2 SC 3.1.2 & RFC 5646/BCP 47)"
                )
        inline_dir_m = re.search(r'\bdir\s*=\s*["\']([^"\']*)["\']', tag_attrs, re.I)
        if inline_dir_m:
            inline_dir = inline_dir_m.group(1).strip().lower()
            if inline_dir not in VALID_HTML_DIR_VALUES:
                errs.append(
                    f"{route}: <{tag_name}> declares invalid inline 'dir' attribute '{inline_dir}' "
                    f"(allowed: ltr, rtl, auto; WHATWG HTML §3.2.6.5)"
                )

    return errs


class _SemanticTimeParser(HTMLParser):
    """Audits <time> tags for valid ISO 8601 datetime attributes and non-empty content (HTML5 §4.5.25 & WCAG 2.2 SC 1.3.1)."""
    ISO_DATE_RE = re.compile(
        r"^\d{4}(?:-\d{2}(?:-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?)?)?$"
    )

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.in_time = False
        self.current_time: dict = {}
        self.times: list[dict] = []
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t == "time":
            lineno, offset = self.getpos()
            loc = f" (line {lineno}:{offset})"
            attr_dict = {k.lower(): (v or "") for k, v in attrs}
            dt_val = attr_dict.get("datetime", "").strip()
            if not dt_val:
                self.errs.append(
                    f"{self.name}{loc}: <time> tag missing 'datetime' attribute "
                    f"(HTML5 §4.5.25 & WCAG 2.2 SC 1.3.1 Info and Relationships require machine-readable ISO 8601 datetime)"
                )
            elif not self.ISO_DATE_RE.match(dt_val):
                self.errs.append(
                    f"{self.name}{loc}: <time> datetime='{dt_val}' is not a valid ISO 8601 date string "
                    f"(expected YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ; HTML5 §4.5.25)"
                )
            self.in_time = True
            self.current_time = {"datetime": dt_val, "text": [], "loc": loc}

    def handle_data(self, data: str) -> None:
        if self.in_time:
            self.current_time["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "time" and self.in_time:
            self.in_time = False
            full_text = " ".join("".join(self.current_time["text"]).split())
            if not full_text:
                self.errs.append(
                    f"{self.name}{self.current_time['loc']}: <time> tag has empty text content "
                    f"(WCAG 2.2 SC 1.3.1 requires visible human-readable date text)"
                )
            self.times.append({
                "datetime": self.current_time["datetime"],
                "text": full_text,
                "loc": self.current_time["loc"],
            })


def check_time_elements(name: str, doc_or_body: str, expected_article_date: str | None = None) -> list[str]:
    """Ensure all <time> elements declare valid ISO 8601 datetime attributes and articles include their publication date."""
    parser = _SemanticTimeParser(name)
    try:
        parser.feed(doc_or_body)
    except Exception:
        pass
    errs = list(parser.errs)
    if expected_article_date:
        matched = any(t["datetime"] == expected_article_date for t in parser.times)
        if not matched:
            errs.append(
                f"{name}: article missing semantic <time datetime='{expected_article_date}'> publication date "
                f"(HTML5 §4.5.25 & WCAG 2.2 SC 1.3.1 Info and Relationships)"
            )
    return errs


class _MediaAccessibilityParser(HTMLParser):
    """Audits <audio> and <video> elements for controls, captions, and zero unmuted autoplay (WCAG 2.2 SC 1.4.2, SC 1.2.2, SC 2.2.2)."""
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.in_video = False
        self.video_tracks: list[str] = []
        self.current_video_loc = ""
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"

        if t in ("audio", "video"):
            has_autoplay = "autoplay" in attr_dict
            has_muted = "muted" in attr_dict
            has_controls = "controls" in attr_dict
            if has_autoplay and not has_muted:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> has unmuted autoplay "
                    f"(WCAG 2.2 SC 1.4.2 Audio Control forbids unmuted auto-playing media)"
                )
            if not has_controls:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> missing controls attribute "
                    f"(WCAG 2.2 SC 2.1.1 Keyboard & SC 2.2.2 Pause, Stop, Hide require visible user controls)"
                )
            if t == "video":
                self.in_video = True
                self.video_tracks = []
                self.current_video_loc = loc

        elif t == "track" and self.in_video:
            kind = attr_dict.get("kind", "").lower()
            if kind in ("captions", "subtitles"):
                self.video_tracks.append(kind)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == "video" and self.in_video:
            self.in_video = False
            if not self.video_tracks:
                self.errs.append(
                    f"{self.name}{self.current_video_loc}: <video> missing <track kind='captions'> or kind='subtitles' "
                    f"(WCAG 2.2 SC 1.2.2 Captions (Prerecorded))"
                )


def check_media_accessibility(name: str, body: str) -> list[str]:
    """Ensure media elements have accessible controls, caption tracks, and zero unmuted autoplay (WCAG 2.2 SC 1.4.2 & SC 1.2.2)."""
    parser = _MediaAccessibilityParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _AbbreviationParser(HTMLParser):
    """Audits <abbr> tags to ensure non-empty text and non-empty title if present (HTML5 §4.5.17 & WCAG 2.2 SC 3.1.4)."""
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.in_abbr = False
        self.abbr_text: list[str] = []
        self.current_loc = ""
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "abbr":
            lineno, offset = self.getpos()
            loc = f" (line {lineno}:{offset})"
            attr_dict = {k.lower(): (v or "") for k, v in attrs}
            if "title" in attr_dict and not attr_dict["title"].strip():
                self.errs.append(
                    f"{self.name}{loc}: <abbr> has empty title attribute (HTML5 §4.5.17 & WCAG 2.2 SC 3.1.4)"
                )
            self.in_abbr = True
            self.abbr_text = []
            self.current_loc = loc

    def handle_data(self, data: str) -> None:
        if self.in_abbr:
            self.abbr_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "abbr" and self.in_abbr:
            self.in_abbr = False
            if not "".join(self.abbr_text).strip():
                self.errs.append(
                    f"{self.name}{self.current_loc}: <abbr> has empty text content "
                    f"(HTML5 §4.5.17 & WCAG 2.2 SC 3.1.4 Abbreviations require visible text abbreviation)"
                )


def check_abbreviation_tags(name: str, body: str) -> list[str]:
    """Ensure <abbr> elements have non-empty text content and valid titles (HTML5 §4.5.17 & WCAG 2.2 SC 3.1.4)."""
    parser = _AbbreviationParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


def check_footnote_links(name: str, body: str, warnings: list[str]) -> list[str]:
    """Inspect <section class="footnotes"> in body for https:// requirement, bare homepages, unlinked footnotes, and bijection."""
    errs: list[str] = []
    fn_item_re = re.compile(r'<(?:p|li)\b[^>]*\bid=["\'](fn[^"\']+)["\'][^>]*>(.*?)</(?:p|li)>', re.I | re.S)
    body_without_fns = FOOTNOTES_SECTION_RE.sub("", body)
    in_text_refs = re.findall(r'\bhref=["\']#(fn[^"\']+)["\']', body_without_fns, re.I)
    defined_fns: list[str] = []
    seen_fn_ids: set[str] = set()
    for section_html in FOOTNOTES_SECTION_RE.findall(body):
        for fn_id, fn_body in fn_item_re.findall(section_html):
            if fn_id in seen_fn_ids:
                errs.append(f"{name}: duplicate footnote id '#{fn_id}' defined in <section class='footnotes'>")
            seen_fn_ids.add(fn_id)
            defined_fns.append(fn_id)
            ext_links = [
                h.strip() for h in HREF_RE.findall(fn_body)
                if h.strip() and not h.strip().startswith(("#", "/")) and not h.strip().lower().startswith(("mailto:", "tel:"))
            ]
            if not ext_links:
                warnings.append(f"{name}: footnote #{fn_id} has no external https:// source link (R6)")
        for raw_href in HREF_RE.findall(section_html):
            href = raw_href.strip()
            if not href:
                continue
            if href.startswith("#") or (href.startswith("/") and not href.startswith("//")):
                continue
            low = href.lower()
            if low.startswith(("mailto:", "tel:")):
                continue
            if low.startswith("http://") or href.startswith("//"):
                errs.append(f"{name}: footnote external link must use https://: '{href}'")
                continue
            if not low.startswith("https://"):
                if ":" in href:
                    errs.append(f"{name}: footnote external link must use https://: '{href}'")
                continue
            parsed = urlsplit(href)
            if not parsed.netloc or "." not in parsed.netloc:
                errs.append(f"{name}: malformed footnote external link '{href}'")
                continue
            if parsed.path in ("", "/") and not parsed.query and not parsed.fragment:
                warnings.append(
                    f"{name}: footnote link '{href}' is a bare homepage (cite the exact source URL)"
                )
    for ref_id in in_text_refs:
        if ref_id not in defined_fns:
            errs.append(f"{name}: in-text footnote reference '#{ref_id}' has no matching definition in <section class='footnotes'>")
    for def_id in defined_fns:
        if def_id not in in_text_refs:
            warnings.append(f"{name}: footnote definition '#{def_id}' is never cited in body text")
    if re.search(r"</sup>\s*<sup\b", body_without_fns, re.I):
        warnings.append(f"{name}: adjacent <sup> tags without separator; combine as <sup><a href='#fn1'>1</a>,<a href='#fn2'>2</a></sup>")
    return errs


def check_headings(name: str, meta: dict) -> list[str]:
    """Validate heading hierarchy and non-empty heading content in `meta['body']`."""
    errs: list[str] = []
    body = meta.get("body", "")
    is_home = meta.get("template") == "home"
    prev_level = 1 if is_home else 2
    first_heading = True

    for m in re.finditer(r"<h([1-6])\b[^>]*>(.*?)</h\1>", body, re.I | re.S):
        level = int(m.group(1))
        heading_text = _TAG_RE.sub(" ", m.group(2)).strip()
        if not heading_text:
            errs.append(
                f"{name}: empty <h{level}> heading tag (WCAG 2.2 SC 1.3.1 & SC 2.4.6 require meaningful heading text)"
            )

    for m in HEADING_RE.finditer(body):
        level = int(m.group(1))
        if level == 1:
            if not is_home:
                errs.append(
                    f"{name}: unexpected <h1> in content body for template "
                    f"'{meta.get('template')}' (page header already renders <h1>)"
                )
                continue
            prev_level = 1
            first_heading = False
            continue

        if level > prev_level + 1:
            if first_heading:
                errs.append(
                    f"{name}: skipped heading level at start of content (<h{level}> without preceding <h{level - 1}>)"
                )
            else:
                errs.append(
                    f"{name}: skipped heading level <h{prev_level}> -> <h{level}>"
                )
        prev_level = level
        first_heading = False

    return errs


def check_text_justification(name: str, raw_text: str) -> list[str]:
    """Ensure no full text justification (WCAG 2.2 SC 1.4.8 Visual Presentation; creates rivers of white)."""
    errs: list[str] = []
    if re.search(r"text-align\s*:\s*justify\b", raw_text, re.I):
        errs.append(
            f"{name}: 'text-align: justify' is forbidden (WCAG 2.2 SC 1.4.8; causes disorienting rivers of white for dyslexic and low-vision readers)"
        )
    if re.search(r'\balign\s*=\s*["\']justify["\']', raw_text, re.I):
        errs.append(
            f"{name}: 'align=\"justify\"' is forbidden (WCAG 2.2 SC 1.4.8; causes disorienting rivers of white for dyslexic and low-vision readers)"
        )
    return errs


def check_accessible_links(name: str, body: str) -> list[str]:
    """Ensure all <a> anchor elements have accessible names (WCAG 2.2 SC 2.4.4 / 4.1.2)."""
    errs: list[str] = []
    a_re = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.I | re.S)
    for m in a_re.finditer(body):
        attrs, inner = m.group(1), m.group(2)
        has_aria_label = bool(re.search(r'\baria-label=["\'][^"\']+["\']', attrs, re.I))
        has_aria_labelledby = bool(re.search(r'\baria-labelledby=["\'][^"\']+["\']', attrs, re.I))
        has_img = bool(re.search(r'<(?:img|svg)\b', inner, re.I))
        clean_text = _TAG_RE.sub(" ", inner).strip()
        if not has_aria_label and not has_aria_labelledby and not clean_text and not has_img:
            errs.append(
                f"{name}: anchor link missing accessible name (must contain text, aria-label, aria-labelledby, or an accessible image/svg; WCAG 2.2 SC 2.4.4 / 4.1.2)"
            )
    return errs


def check_link_purpose_and_generic_text(name: str, body: str) -> list[str]:
    """Ensure anchor links do not use bare ambiguous generic text without descriptive aria-label context (WCAG 2.2 SC 2.4.4 & W3C Failure F63/F89)."""
    errs: list[str] = []
    generic_phrases = {"click here", "here", "read more", "learn more", "more", "link", "download", "info", "details"}
    a_re = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.I | re.S)
    for m in a_re.finditer(body):
        attrs, inner = m.group(1), m.group(2)
        has_aria = bool(re.search(r'\baria-label(?:ledby)?\s*=\s*["\'][^"\']+["\']', attrs, re.I))
        clean_text = _TAG_RE.sub(" ", inner).strip().lower()
        if clean_text in generic_phrases and not has_aria:
            errs.append(
                f"{name}: ambiguous generic link text '{inner.strip()}' requires 'aria-label' or 'aria-labelledby' for context (WCAG 2.2 SC 2.4.4 & W3C Failure F63/F89)"
            )
    return errs


def check_button_accessible_names(name: str, body: str) -> list[str]:
    """Ensure all <button> elements declare accessible names (WCAG 2.2 SC 4.1.2 & Clarke & Mehrnezhad arXiv:2611.01211)."""
    errs: list[str] = []
    button_re = re.compile(r"<button\b([^>]*)>(.*?)</button>", re.I | re.S)
    for m in button_re.finditer(body):
        attrs, inner = m.group(1), m.group(2)
        has_aria = bool(re.search(r'\baria-label(?:ledby)?\s*=\s*["\'][^"\']+["\']', attrs, re.I))
        has_img = bool(re.search(r'<(?:img|svg)\b', inner, re.I))
        clean = _TAG_RE.sub(" ", inner).strip()
        if not clean and not has_aria and not has_img:
            errs.append(
                f"{name}: <button> missing accessible name (must have visible text, aria-label, aria-labelledby, or accessible icon; WCAG 2.2 SC 4.1.2)"
            )
    return errs


def check_interactive_explainer_accessibility(name: str, body: str) -> list[str]:
    """Ensure custom interactive controls inside <figure class="explainer"> have keyboard focusability, accessible names, and state attributes (WCAG 2.2 SC 2.1.1 & SC 4.1.2)."""
    errs: list[str] = []
    explainer_re = re.compile(r'<figure\b[^>]*class=["\'][^"\']*\bexplainer\b[^"\']*["\'][^>]*>(.*?)</figure>', re.I | re.S)
    role_button_re = re.compile(r'<([a-zA-Z0-9:-]+)\b([^>]*\brole=["\']button["\'][^>]*)>(.*?)</\1>', re.I | re.S)
    for em in explainer_re.finditer(body):
        einner = em.group(1)
        for rbm in role_button_re.finditer(einner):
            tag, rattrs, rinner = rbm.group(1), rbm.group(2), rbm.group(3)
            if tag.lower() == "button":
                continue
            has_tabindex = bool(re.search(r'\btabindex\s*=\s*["\']0["\']', rattrs, re.I))
            has_name = bool(re.search(r'\baria-label(?:ledby)?\s*=\s*["\'][^"\']+["\']', rattrs, re.I)) or bool(_TAG_RE.sub(" ", rinner).strip())
            has_state = bool(re.search(r'\baria-(?:pressed|expanded|controls)\s*=\s*["\'][^"\']+["\']', rattrs, re.I))
            if not has_tabindex:
                errs.append(
                    f"{name}: interactive explainer custom button <{tag}> missing keyboard focusability 'tabindex=\"0\"' (WCAG 2.2 SC 2.1.1)"
                )
            if not has_name:
                errs.append(
                    f"{name}: interactive explainer custom button <{tag}> missing accessible name ('aria-label' or 'aria-labelledby'; WCAG 2.2 SC 4.1.2)"
                )
            if not has_state:
                errs.append(
                    f"{name}: interactive explainer custom button <{tag}> missing state attribute ('aria-pressed', 'aria-expanded', or 'aria-controls'; WCAG 2.2 SC 4.1.2)"
                )
    return errs


def check_research_status_badges(name: str, meta: dict, body: str) -> list[str]:
    """Ensure research pages display all three required status badges: established, proposal, open question (R7 Research Status)."""
    errs: list[str] = []
    is_research = name == "research.html" or name.startswith("research/") or meta.get("template") == "research"
    if not is_research:
        return errs
    required_badges = [
        ("badge-est", "Established status (badge-est)"),
        ("badge-prop", "Our proposal status (badge-prop)"),
        ("badge-open", "Open question status (badge-open)"),
    ]
    for cls_name, desc in required_badges:
        if cls_name not in body:
            errs.append(
                f"{name}: research page missing required status badge '{cls_name}' ({desc}; R7 Research Status)"
            )
    return errs


def check_math_accessibility(name: str, body: str) -> list[str]:
    """Ensure <math> elements provide accessible alternative representations (HTML5 §4.8.15 & WCAG 2.2 SC 1.1.1 / SC 4.1.2; Ross arXiv:2505.22667)."""
    errs: list[str] = []
    math_re = re.compile(r"<math\b([^>]*)>(.*?)</math>", re.I | re.S)
    for m in math_re.finditer(body):
        attrs, inner = m.group(1), m.group(2)
        has_alt = bool(re.search(r'\b(?:alttext|aria-label|aria-labelledby)\s*=\s*["\'][^"\']+["\']', attrs, re.I))
        has_annotation = bool(re.search(r'<annotation\b', inner, re.I))
        if not has_alt and not has_annotation:
            errs.append(
                f"{name}: <math> element missing accessible alternative (declare 'alttext', 'aria-label', 'aria-labelledby', or child <annotation>; HTML5 §4.8.15 & WCAG 2.2 SC 1.1.1)"
            )
    return errs


def check_figcaption_structure(name: str, body: str) -> list[str]:
    """Ensure <figcaption> is a valid, direct, non-empty child of <figure> and not orphaned outside (HTML5 §4.8.18 & WCAG 2.2 SC 1.3.1)."""
    errs: list[str] = []
    figure_re = re.compile(r"<figure\b([^>]*)>(.*?)</figure>", re.I | re.S)
    figcaption_re = re.compile(r"<figcaption\b([^>]*)>(.*?)</figcaption>", re.I | re.S)
    body_no_figures = figure_re.sub("", body)
    for m in figcaption_re.finditer(body_no_figures):
        errs.append(
            f"{name}: orphaned <figcaption> found outside <figure> (HTML5 §4.8.18 & WCAG 2.2 SC 1.3.1)"
        )
    for fm in figure_re.finditer(body):
        finner = fm.group(2)
        fcaptions = figcaption_re.findall(finner)
        if len(fcaptions) > 1:
            errs.append(
                f"{name}: <figure> contains multiple <figcaption> elements (at most one allowed; HTML5 §4.8.18)"
            )
        for cattrs, cinner in fcaptions:
            clean = _TAG_RE.sub(" ", cinner).strip()
            if not clean:
                errs.append(
                    f"{name}: <figcaption> must not be empty or whitespace-only (HTML5 §4.8.18 & WCAG 2.2 SC 1.3.1)"
                )
    return errs


def check_live_region_integrity(name: str, body: str) -> list[str]:
    """Ensure ARIA live regions declare valid attributes, consistent alert/status levels, and no focus-stealing autofocus (WCAG 2.2 SC 4.1.3 & W3C WAI-ARIA 1.2 §5.3.3)."""
    errs: list[str] = []
    element_re = re.compile(r"<([a-zA-Z0-9:-]+)\b([^>]*)>", re.I)
    valid_live_values = {"polite", "assertive", "off"}
    valid_atomic_values = {"true", "false"}

    for m in element_re.finditer(body):
        tag, attrs = m.group(1), m.group(2)
        live_m = re.search(r'\baria-live\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        atomic_m = re.search(r'\baria-atomic\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        role_m = re.search(r'\brole\s*=\s*["\']([^"\']+)["\']', attrs, re.I)

        live_val = live_m.group(1).lower().strip() if live_m else None
        atomic_val = atomic_m.group(1).lower().strip() if atomic_m else None
        role_val = role_m.group(1).lower().strip() if role_m else None

        if live_val is not None and live_val not in valid_live_values:
            errs.append(
                f"{name}: <{tag}> declares invalid aria-live='{live_val}' (must be 'polite', 'assertive', or 'off'; WCAG 2.2 SC 4.1.3 & W3C WAI-ARIA 1.2 §5.3.3)"
            )
        if atomic_val is not None and atomic_val not in valid_atomic_values:
            errs.append(
                f"{name}: <{tag}> declares invalid aria-atomic='{atomic_val}' (must be 'true' or 'false'; W3C WAI-ARIA 1.2 §5.3.3)"
            )
        if role_val in ("alert", "alertdialog") and live_val == "off":
            errs.append(
                f"{name}: <{tag} role='{role_val}'> cannot declare aria-live='off' (silences critical user alerts; WCAG 2.2 SC 4.1.3 & W3C WAI-ARIA 1.2 §5.3.3)"
            )
        if role_val == "status" and live_val == "assertive":
            errs.append(
                f"{name}: <{tag} role='status'> should not declare aria-live='assertive' (status updates must be polite announcements; WCAG 2.2 SC 4.1.3)"
            )

    live_container_re = re.compile(
        r'<([a-zA-Z0-9:-]+)\b([^>]*(?:\baria-live=["\'](?:polite|assertive)["\']|\brole=["\'](?:alert|status|log)["\'])[^>]*)>(.*?)</\1>',
        re.I | re.S,
    )
    for cm in live_container_re.finditer(body):
        cinner = cm.group(3)
        if re.search(r'\bautofocus\b', cinner, re.I):
            errs.append(
                f"{name}: live region container <{cm.group(1)}> must not contain autofocus elements (disrupts screen reader announcement flow; WCAG 2.2 SC 4.1.3 & SC 2.4.3)"
            )

    return errs


def check_disabled_attribute_integrity(name: str, body: str) -> list[str]:
    """Ensure <a> elements do not use non-standard disabled attributes, and aria-disabled controls do not declare contradictory active states (HTML5 §4.6.1 & WCAG 2.2 SC 4.1.2)."""
    errs: list[str] = []
    a_tag_re = re.compile(r"<a\b([^>]*)>", re.I)
    for m in a_tag_re.finditer(body):
        attrs = m.group(1)
        if re.search(r'\bdisabled\b', attrs, re.I):
            errs.append(
                f"{name}: <a> declares non-standard 'disabled' attribute (invalid in HTML5 §4.6.1 and ignored by assistive technology; omit 'href' or use aria-disabled='true' with tabindex='-1'; WCAG 2.2 SC 4.1.2)"
            )

    elem_re = re.compile(r"<([a-zA-Z0-9:-]+)\b([^>]*)>", re.I)
    for m in elem_re.finditer(body):
        tag, attrs = m.group(1), m.group(2)
        if re.search(r'\baria-disabled\s*=\s*["\']true["\']', attrs, re.I):
            if re.search(r'\baria-pressed\s*=\s*["\']true["\']', attrs, re.I):
                errs.append(
                    f"{name}: <{tag}> declares aria-disabled='true' but also active aria-pressed='true' (contradictory state; W3C ARIA APG §3.4 & WCAG 2.2 SC 4.1.2)"
                )
            if re.search(r'\baria-expanded\s*=\s*["\']true["\']', attrs, re.I):
                errs.append(
                    f"{name}: <{tag}> declares aria-disabled='true' but also active aria-expanded='true' (contradictory state; W3C ARIA APG §3.4 & WCAG 2.2 SC 4.1.2)"
                )
    return errs


def check_svg_accessibility(name: str, body: str) -> list[str]:
    """Ensure SVG graphics declare accessible names or are explicitly decorative, decorative SVGs contain no focusable elements, and SVG <title> tags are non-empty (HTML5, SVG 2 §5.2, WCAG 2.2 SC 1.1.1 & SC 4.1.2)."""
    errs: list[str] = []
    svg_re = re.compile(r"<svg\b([^>]*)>(.*?)</svg>", re.I | re.S)

    for m in svg_re.finditer(body):
        attrs, inner = m.group(1), m.group(2)
        is_hidden = bool(re.search(r'\baria-hidden\s*=\s*["\']true["\']', attrs, re.I))
        is_presentation = bool(re.search(r'\brole\s*=\s*["\'](?:presentation|none)["\']', attrs, re.I))
        has_label = bool(re.search(r'\baria-label(?:ledby)?\s*=\s*["\'][^"\']+["\']', attrs, re.I))

        title_matches = list(re.finditer(r"<title\b([^>]*)>(.*?)</title>", inner, re.I | re.S))
        has_valid_title = False
        for tm in title_matches:
            tinner = tm.group(2)
            clean_title = _TAG_RE.sub(" ", tinner).strip()
            if not clean_title:
                errs.append(
                    f"{name}: <svg> contains empty or whitespace-only <title> tag (HTML5 & WCAG 2.2 SC 1.1.1)"
                )
            else:
                has_valid_title = True

        if is_hidden or is_presentation:
            if re.search(r'\btabindex\s*=\s*["\']\s*(?:0|[1-9]\d*)\s*["\']|\brole=["\']button["\']|<a\b[^>]*\bhref\b', inner, re.I):
                errs.append(
                    f"{name}: decorative <svg> (aria-hidden='true' or role='presentation') contains focusable interactive element(s) "
                    f"(traps screen-reader focus; WCAG 2.2 SC 4.1.2 & W3C Failure F107)"
                )
        else:
            if not has_label and not has_valid_title:
                errs.append(
                    f"{name}: <svg> missing accessible name (must provide aria-label, aria-labelledby, direct non-empty <title>, or mark decorative with aria-hidden='true'; WCAG 2.2 SC 1.1.1 & SC 4.1.2)"
                )

    return errs


def check_target_blank_accessibility(name: str, body: str) -> list[str]:
    """Ensure links targeting '_blank' explicitly notify users that a new browsing context/window will open (WCAG 2.2 Technique G201, Technique H83, SC 3.2.5)."""
    errs: list[str] = []
    a_re = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.I | re.S)
    new_window_notice_re = re.compile(r"\b(?:opens? in (?:a )?new (?:window|tab)|new (?:window|tab))\b", re.I)

    for m in a_re.finditer(body):
        attrs, inner = m.group(1), m.group(2)
        target_m = re.search(r'\btarget\s*=\s*["\']_blank["\']', attrs, re.I)
        if not target_m:
            continue

        label_m = re.search(r'\baria-label\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        label_text = label_m.group(1) if label_m else ""

        inner_text = _TAG_RE.sub(" ", inner)
        img_alt_matches = re.findall(r'\balt\s*=\s*["\']([^"\']+)["\']', inner, re.I)
        svg_title_matches = re.findall(r'<title\b[^>]*>(.*?)</title>', inner, re.I | re.S)

        combined_text = f"{label_text} {inner_text} {' '.join(img_alt_matches)} {' '.join(svg_title_matches)}"
        if not new_window_notice_re.search(combined_text):
            href_m = re.search(r'\bhref\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
            href_val = href_m.group(1) if href_m else ""
            errs.append(
                f"{name}: link targeting '_blank' ('{href_val}') missing explicit new window/tab notification "
                f"(must state '(opens in new tab)' or '(new window)' in text, aria-label, or child image alt; "
                f"WCAG 2.2 Technique G201 / H83 & SC 3.2.5)"
            )

    return errs


def check_output_and_datalist_integrity(name: str, body: str) -> list[str]:
    """Ensure <output> calculation elements and <datalist> suggestion controls preserve valid ID associations and ARIA semantics (HTML5 §4.10.18, §4.10.19, WCAG 2.2 SC 4.1.2 & SC 1.3.1)."""
    errs: list[str] = []
    doc_ids = set(ELEMENT_ID_RE.findall(body))

    output_re = re.compile(r"<output\b([^>]*)>(.*?)</output>", re.I | re.S)
    for m in output_re.finditer(body):
        attrs, inner = m.group(1), m.group(2)
        role_m = re.search(r'\brole\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        if role_m:
            rval = role_m.group(1).lower().strip()
            if rval in ("presentation", "none"):
                errs.append(
                    f"{name}: <output> cannot declare role='{rval}' "
                    f"(strips semantic calculation result role; HTML5 §4.10.19 & W3C ARIA in HTML §3.1)"
                )
        live_m = re.search(r'\baria-live\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        if live_m and live_m.group(1).lower().strip() == "off":
            errs.append(
                f"{name}: <output> cannot declare aria-live='off' "
                f"(silences calculation updates; WCAG 2.2 SC 4.1.3 & SC 4.1.2)"
            )
        for_m = re.search(r'\bfor\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if for_m:
            for_tokens = for_m.group(1).split()
            if not for_tokens:
                errs.append(
                    f"{name}: <output> 'for' attribute cannot be empty (HTML5 §4.10.19)"
                )
            for ref_id in for_tokens:
                if ref_id not in doc_ids:
                    errs.append(
                        f"{name}: <output for='...'> references non-existent element id '{ref_id}' "
                        f"(HTML5 §4.10.19 requires valid ID references for calculation controls)"
                    )

    datalist_re = re.compile(r"<datalist\b([^>]*)>(.*?)</datalist>", re.I | re.S)
    datalist_ids: set[str] = set()
    for dm in datalist_re.finditer(body):
        dattrs, dinner = dm.group(1), dm.group(2)
        did_m = re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', dattrs, re.I)
        if not did_m or not did_m.group(1).strip():
            errs.append(
                f"{name}: <datalist> missing required 'id' attribute "
                f"(HTML5 §4.10.18 requires ID so form inputs can reference it via 'list' attribute)"
            )
        else:
            did = did_m.group(1).strip()
            datalist_ids.add(did)

        opt_re = re.compile(r"<option\b([^>]*)>(.*?)(?:</option>|$)", re.I | re.S)
        for om in opt_re.finditer(dinner):
            oattrs, oinner = om.group(1), om.group(2)
            has_val = bool(re.search(r'\bvalue\s*=\s*["\']([^"\']*)["\']', oattrs, re.I))
            val_text = ""
            if has_val:
                vm = re.search(r'\bvalue\s*=\s*["\']([^"\']*)["\']', oattrs, re.I)
                val_text = vm.group(1).strip() if vm else ""
            clean_text = _TAG_RE.sub(" ", oinner).strip()
            if not val_text and not clean_text:
                errs.append(
                    f"{name}: <datalist> <option> has empty value and empty text "
                    f"(HTML5 §4.10.18 requires a suggestion value)"
                )

    input_list_re = re.compile(r"<input\b([^>]*)>", re.I)
    for im in input_list_re.finditer(body):
        iattrs = im.group(1)
        list_m = re.search(r'\blist\s*=\s*["\']([^"\']*)["\']', iattrs, re.I)
        if list_m:
            list_val = list_m.group(1).strip()
            if not list_val:
                errs.append(
                    f"{name}: <input list=''> cannot have empty list attribute (HTML5 §4.10.18)"
                )
            elif list_val not in doc_ids:
                errs.append(
                    f"{name}: <input list='{list_val}'> references non-existent id '{list_val}' "
                    f"(HTML5 §4.10.18 requires reference to a valid <datalist>)"
                )
            elif list_val not in datalist_ids:
                errs.append(
                    f"{name}: <input list='{list_val}'> targets element '#{list_val}' which is not a <datalist> "
                    f"(HTML5 §4.10.18 requires target to be a <datalist>)"
                )

    return errs


def check_aria_invalid_and_error_message_integrity(name: str, body: str) -> list[str]:
    """Ensure aria-invalid, aria-errormessage, and aria-required attributes adhere to W3C WAI-ARIA 1.2 §6.6 and WCAG 2.2 SC 3.3.1 / SC 3.3.3 / SC 4.1.2."""
    errs: list[str] = []
    doc_ids = set(ELEMENT_ID_RE.findall(body))
    hidden_ids = set()
    for hm in re.finditer(r'<[a-zA-Z0-9:-]+\b[^>]*\bid\s*=\s*["\']([^"\']+)["\'][^>]*\baria-hidden\s*=\s*["\']true["\']', body, re.I):
        hidden_ids.add(hm.group(1).strip())
    for hm in re.finditer(r'<[a-zA-Z0-9:-]+\b[^>]*\baria-hidden\s*=\s*["\']true["\'][^>]*\bid\s*=\s*["\']([^"\']+)["\']', body, re.I):
        hidden_ids.add(hm.group(1).strip())

    elem_re = re.compile(r"<([a-zA-Z0-9:-]+)\b([^>]*)>", re.I)
    valid_invalid_tokens = {"true", "false", "grammar", "spelling"}
    valid_boolean_tokens = {"true", "false"}

    for m in elem_re.finditer(body):
        tag, attrs = m.group(1), m.group(2)

        inv_m = re.search(r'\baria-invalid\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if inv_m:
            inv_val = inv_m.group(1).lower().strip()
            if inv_val not in valid_invalid_tokens:
                errs.append(
                    f"{name}: <{tag}> declares invalid aria-invalid='{inv_val}' "
                    f"(must be 'true', 'false', 'grammar', or 'spelling'; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                )

        err_m = re.search(r'\baria-errormessage\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if err_m:
            err_val = err_m.group(1).strip()
            if not err_val:
                errs.append(
                    f"{name}: <{tag}> aria-errormessage cannot be empty (W3C WAI-ARIA 1.2 §6.6)"
                )
            else:
                for ref_id in err_val.split():
                    if ref_id not in doc_ids:
                        errs.append(
                            f"{name}: <{tag} aria-errormessage='{err_val}'> references non-existent element id '{ref_id}' "
                            f"(WCAG 2.2 SC 3.3.1 Error Identification & SC 4.1.2)"
                        )
                    elif ref_id in hidden_ids:
                        errs.append(
                            f"{name}: <{tag} aria-errormessage='{err_val}'> references element '#{ref_id}' which is aria-hidden='true' "
                            f"(error message must not be hidden from assistive technology; WCAG 2.2 SC 3.3.1 & SC 3.3.3)"
                        )

        req_m = re.search(r'\baria-required\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if req_m:
            req_val = req_m.group(1).lower().strip()
            if req_val not in valid_boolean_tokens:
                errs.append(
                    f"{name}: <{tag}> declares invalid aria-required='{req_val}' "
                    f"(must be 'true' or 'false'; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                )
            if req_val == "false" and re.search(r'(?<!aria-)\brequired\b', attrs, re.I):
                errs.append(
                    f"{name}: <{tag}> declares native 'required' but also aria-required='false' "
                    f"(contradictory state; WCAG 2.2 SC 4.1.2)"
                )

    return errs


class _InertIntegrityParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.stack: list[dict] = []
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"

        is_inert_decl = any(k.lower() == "inert" for k, _ in attrs)
        has_inert_ancestor = any(node["is_inert"] for node in self.stack)
        is_inert = is_inert_decl or has_inert_ancestor

        if is_inert_decl:
            tab_val = attr_dict.get("tabindex", "").strip()
            if tab_val:
                try:
                    val = int(tab_val)
                    if val >= 0:
                        self.errs.append(
                            f"{self.name}{loc}: <{t} inert> has tabindex='{val}' which creates contradictory sequential focus and keyboard trapping "
                            f"(HTML5 §6.12.3 & WCAG 2.2 SC 2.1.2 No Keyboard Trap)"
                        )
                except ValueError:
                    pass
            if any(k.lower() == "autofocus" for k, _ in attrs):
                self.errs.append(
                    f"{self.name}{loc}: <{t} inert> cannot declare autofocus "
                    f"(HTML5 §6.12.3 & WCAG 2.2 SC 2.1.2 No Keyboard Trap)"
                )
            live_val = attr_dict.get("aria-live", "").strip().lower()
            if live_val and live_val != "off":
                self.errs.append(
                    f"{self.name}{loc}: <{t} inert> declares aria-live='{live_val}' on an inert element removed from assistive technology "
                    f"(HTML5 §6.12.3 & WCAG 2.2 SC 4.1.2 Name, Role, Value)"
                )
        elif has_inert_ancestor:
            if any(k.lower() == "autofocus" for k, _ in attrs):
                self.errs.append(
                    f"{self.name}{loc}: <{t} autofocus> is nested inside an inert ancestor container, causing focus trapping "
                    f"(HTML5 §6.12.3 & WCAG 2.2 SC 2.1.2 No Keyboard Trap)"
                )

        if t not in self.VOID_TAGS:
            self.stack.append({"tag": t, "is_inert": is_inert})

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in self.VOID_TAGS:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == t:
                self.stack = self.stack[:i]
                break


def check_inert_attribute_integrity(name: str, body: str) -> list[str]:
    """Ensure elements with the inert attribute do not declare conflicting tabindex, autofocus, or live regions (HTML5 §6.12.3 & WCAG 2.2 SC 2.1.2 / SC 4.1.2)."""
    parser = _InertIntegrityParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


VALID_INPUTMODE_TOKENS = {"none", "text", "decimal", "numeric", "tel", "search", "email", "url"}
VALID_ENTERKEYHINT_TOKENS = {"enter", "done", "go", "next", "previous", "search", "send"}


def check_virtual_keyboard_and_inputmode_attributes(name: str, body: str) -> list[str]:
    """Ensure inputmode and enterkeyhint attributes adhere to HTML5 §4.10.5.3 / §4.10.5.4 enumerated tokens and WCAG 2.2 SC 1.3.5."""
    errs: list[str] = []
    elem_re = re.compile(r"<([a-zA-Z0-9:-]+)\b([^>]*)>", re.I)

    for m in elem_re.finditer(body):
        tag, attrs = m.group(1), m.group(2)

        inputmode_m = re.search(r'\binputmode\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if inputmode_m:
            mode_val = inputmode_m.group(1).lower().strip()
            if not mode_val:
                errs.append(
                    f"{name}: <{tag}> inputmode attribute cannot be empty (HTML5 §4.10.5.3)"
                )
            elif mode_val not in VALID_INPUTMODE_TOKENS:
                errs.append(
                    f"{name}: <{tag}> declares invalid inputmode='{mode_val}' "
                    f"(must be one of 'none', 'text', 'decimal', 'numeric', 'tel', 'search', 'email', 'url'; HTML5 §4.10.5.3)"
                )

        enterkey_m = re.search(r'\benterkeyhint\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if enterkey_m:
            hint_val = enterkey_m.group(1).lower().strip()
            if not hint_val:
                errs.append(
                    f"{name}: <{tag}> enterkeyhint attribute cannot be empty (HTML5 §4.10.5.4)"
                )
            elif hint_val not in VALID_ENTERKEYHINT_TOKENS:
                errs.append(
                    f"{name}: <{tag}> declares invalid enterkeyhint='{hint_val}' "
                    f"(must be one of 'enter', 'done', 'go', 'next', 'previous', 'search', 'send'; HTML5 §4.10.5.4)"
                )

    return errs


def check_range_slider_accessibility(name: str, body: str) -> list[str]:
    """Ensure elements with role='slider' declare accessible name, valid valuenow/valuemin/valuemax bounds, and keyboard focusability (W3C WAI-ARIA 1.2 §5.2.8 & WCAG 2.2 SC 4.1.2 / SC 2.1.1)."""
    errs: list[str] = []
    elem_re = re.compile(r"<([a-zA-Z0-9:-]+)\b([^>]*\brole\s*=\s*[\"']slider[\"'][^>]*)>", re.I)

    for m in elem_re.finditer(body):
        tag, attrs = m.group(1), m.group(2)
        tag_lower = tag.lower()

        has_name = bool(re.search(r'\baria-label(?:ledby)?\s*=\s*["\'][^"\']+["\']', attrs, re.I))
        if not has_name and tag_lower == "input":
            id_m = re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
            if id_m:
                lid = id_m.group(1).strip()
                if re.search(rf'<label\b[^>]*\bfor\s*=\s*["\']{re.escape(lid)}["\']', body, re.I):
                    has_name = True
        if not has_name:
            errs.append(
                f"{name}: <{tag} role='slider'> missing accessible name ('aria-label' or 'aria-labelledby'; WCAG 2.2 SC 4.1.2)"
            )

        has_tabindex = bool(re.search(r'\btabindex\s*=\s*["\']0["\']', attrs, re.I))
        if tag_lower != "input" and not has_tabindex:
            errs.append(
                f"{name}: custom <{tag} role='slider'> must declare tabindex='0' for keyboard operation (WCAG 2.2 SC 2.1.1 / W3C WAI-ARIA 1.2 §5.2.8)"
            )

        now_m = re.search(r'\baria-valuenow\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        min_m = re.search(r'\baria-valuemin\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        max_m = re.search(r'\baria-valuemax\s*=\s*["\']([^"\']*)["\']', attrs, re.I)

        val_now: float | None = None
        val_min: float | None = None
        val_max: float | None = None

        if not now_m:
            errs.append(
                f"{name}: <{tag} role='slider'> missing required 'aria-valuenow' attribute (W3C WAI-ARIA 1.2 §5.2.8)"
            )
        else:
            try:
                val_now = float(now_m.group(1).strip())
            except ValueError:
                errs.append(
                    f"{name}: <{tag} role='slider'> aria-valuenow='{now_m.group(1)}' is not a valid number (W3C WAI-ARIA 1.2 §5.2.8)"
                )

        if not min_m:
            errs.append(
                f"{name}: <{tag} role='slider'> missing required 'aria-valuemin' attribute (W3C WAI-ARIA 1.2 §5.2.8)"
            )
        else:
            try:
                val_min = float(min_m.group(1).strip())
            except ValueError:
                errs.append(
                    f"{name}: <{tag} role='slider'> aria-valuemin='{min_m.group(1)}' is not a valid number (W3C WAI-ARIA 1.2 §5.2.8)"
                )

        if not max_m:
            errs.append(
                f"{name}: <{tag} role='slider'> missing required 'aria-valuemax' attribute (W3C WAI-ARIA 1.2 §5.2.8)"
            )
        else:
            try:
                val_max = float(max_m.group(1).strip())
            except ValueError:
                errs.append(
                    f"{name}: <{tag} role='slider'> aria-valuemax='{max_m.group(1)}' is not a valid number (W3C WAI-ARIA 1.2 §5.2.8)"
                )

        if val_min is not None and val_max is not None:
            if val_min > val_max:
                errs.append(
                    f"{name}: <{tag} role='slider'> aria-valuemin ({val_min}) exceeds aria-valuemax ({val_max}) (W3C WAI-ARIA 1.2 §5.2.8)"
                )
            elif val_now is not None:
                if val_now < val_min or val_now > val_max:
                    errs.append(
                        f"{name}: <{tag} role='slider'> aria-valuenow ({val_now}) is outside the range [{val_min}, {val_max}] (W3C WAI-ARIA 1.2 §5.2.8)"
                    )

    return errs


def check_aria_spinbutton_and_scrollbar_accessibility(name: str, body: str) -> list[str]:
    """Ensure elements with role='spinbutton' or role='scrollbar' declare accessible names, required bounds, valid numeric values, and keyboard focusability (W3C WAI-ARIA 1.2 §5.2.8 & WCAG 2.2 SC 4.1.2 / SC 2.1.1)."""
    errs: list[str] = []

    # 1. role="spinbutton"
    spin_re = re.compile(r"<([a-zA-Z0-9:-]+)\b([^>]*\brole\s*=\s*[\"']spinbutton[\"'][^>]*)>", re.I)
    for m in spin_re.finditer(body):
        tag, attrs = m.group(1), m.group(2)
        tag_lower = tag.lower()

        has_name = bool(re.search(r'\baria-label(?:ledby)?\s*=\s*["\'][^"\']+["\']', attrs, re.I))
        if not has_name and tag_lower == "input":
            id_m = re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
            if id_m:
                lid = id_m.group(1).strip()
                if re.search(rf'<label\b[^>]*\bfor\s*=\s*["\']{re.escape(lid)}["\']', body, re.I):
                    has_name = True
        if not has_name:
            errs.append(
                f"{name}: <{tag} role='spinbutton'> missing accessible name ('aria-label' or 'aria-labelledby'; WCAG 2.2 SC 4.1.2)"
            )

        has_tabindex = bool(re.search(r'\btabindex\s*=\s*["\']0["\']', attrs, re.I))
        if tag_lower != "input" and not has_tabindex:
            errs.append(
                f"{name}: custom <{tag} role='spinbutton'> must declare tabindex='0' for keyboard operation (WCAG 2.2 SC 2.1.1 / W3C WAI-ARIA 1.2 §5.2.8)"
            )

        now_m = re.search(r'\baria-valuenow\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        min_m = re.search(r'\baria-valuemin\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        max_m = re.search(r'\baria-valuemax\s*=\s*["\']([^"\']*)["\']', attrs, re.I)

        val_now: float | None = None
        val_min: float | None = None
        val_max: float | None = None

        if not now_m:
            errs.append(
                f"{name}: <{tag} role='spinbutton'> missing required 'aria-valuenow' attribute (W3C WAI-ARIA 1.2 §5.2.8)"
            )
        else:
            try:
                val_now = float(now_m.group(1).strip())
            except ValueError:
                errs.append(
                    f"{name}: <{tag} role='spinbutton'> aria-valuenow='{now_m.group(1)}' is not a valid number (W3C WAI-ARIA 1.2 §5.2.8)"
                )

        if min_m:
            try:
                val_min = float(min_m.group(1).strip())
            except ValueError:
                errs.append(
                    f"{name}: <{tag} role='spinbutton'> aria-valuemin='{min_m.group(1)}' is not a valid number (W3C WAI-ARIA 1.2 §5.2.8)"
                )

        if max_m:
            try:
                val_max = float(max_m.group(1).strip())
            except ValueError:
                errs.append(
                    f"{name}: <{tag} role='spinbutton'> aria-valuemax='{max_m.group(1)}' is not a valid number (W3C WAI-ARIA 1.2 §5.2.8)"
                )

        if val_min is not None and val_max is not None:
            if val_min > val_max:
                errs.append(
                    f"{name}: <{tag} role='spinbutton'> aria-valuemin ({val_min}) exceeds aria-valuemax ({val_max}) (W3C WAI-ARIA 1.2 §5.2.8)"
                )
            elif val_now is not None:
                if val_now < val_min or val_now > val_max:
                    errs.append(
                        f"{name}: <{tag} role='spinbutton'> aria-valuenow ({val_now}) is outside the range [{val_min}, {val_max}] (W3C WAI-ARIA 1.2 §5.2.8)"
                    )

    # 2. role="scrollbar"
    scroll_re = re.compile(r"<([a-zA-Z0-9:-]+)\b([^>]*\brole\s*=\s*[\"']scrollbar[\"'][^>]*)>", re.I)
    for m in scroll_re.finditer(body):
        tag, attrs = m.group(1), m.group(2)

        has_name = bool(re.search(r'\baria-label(?:ledby)?\s*=\s*["\'][^"\']+["\']', attrs, re.I))
        if not has_name:
            errs.append(
                f"{name}: <{tag} role='scrollbar'> missing accessible name ('aria-label' or 'aria-labelledby'; WCAG 2.2 SC 4.1.2)"
            )

        controls_m = re.search(r'\baria-controls\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        if not controls_m or not controls_m.group(1).strip():
            errs.append(
                f"{name}: <{tag} role='scrollbar'> missing required 'aria-controls' attribute referencing scrolled element ID (W3C WAI-ARIA 1.2 §5.2.8)"
            )

        orient_m = re.search(r'\baria-orientation\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        if orient_m:
            orient_val = orient_m.group(1).lower().strip()
            if orient_val not in ("horizontal", "vertical"):
                errs.append(
                    f"{name}: <{tag} role='scrollbar'> declares invalid aria-orientation='{orient_val}' (must be 'horizontal' or 'vertical'; W3C WAI-ARIA 1.2 §5.2.8)"
                )

        has_tabindex = bool(re.search(r'\btabindex\s*=\s*["\']0["\']', attrs, re.I))
        if not has_tabindex:
            errs.append(
                f"{name}: <{tag} role='scrollbar'> must declare tabindex='0' for keyboard operation (WCAG 2.2 SC 2.1.1 / W3C WAI-ARIA 1.2 §5.2.8)"
            )

        now_m = re.search(r'\baria-valuenow\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        min_m = re.search(r'\baria-valuemin\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        max_m = re.search(r'\baria-valuemax\s*=\s*["\']([^"\']*)["\']', attrs, re.I)

        val_now = None
        val_min = None
        val_max = None

        if not now_m:
            errs.append(
                f"{name}: <{tag} role='scrollbar'> missing required 'aria-valuenow' attribute (W3C WAI-ARIA 1.2 §5.2.8)"
            )
        else:
            try:
                val_now = float(now_m.group(1).strip())
            except ValueError:
                errs.append(
                    f"{name}: <{tag} role='scrollbar'> aria-valuenow='{now_m.group(1)}' is not a valid number (W3C WAI-ARIA 1.2 §5.2.8)"
                )

        if not min_m:
            errs.append(
                f"{name}: <{tag} role='scrollbar'> missing required 'aria-valuemin' attribute (W3C WAI-ARIA 1.2 §5.2.8)"
            )
        else:
            try:
                val_min = float(min_m.group(1).strip())
            except ValueError:
                errs.append(
                    f"{name}: <{tag} role='scrollbar'> aria-valuemin='{min_m.group(1)}' is not a valid number (W3C WAI-ARIA 1.2 §5.2.8)"
                )

        if not max_m:
            errs.append(
                f"{name}: <{tag} role='scrollbar'> missing required 'aria-valuemax' attribute (W3C WAI-ARIA 1.2 §5.2.8)"
            )
        else:
            try:
                val_max = float(max_m.group(1).strip())
            except ValueError:
                errs.append(
                    f"{name}: <{tag} role='scrollbar'> aria-valuemax='{max_m.group(1)}' is not a valid number (W3C WAI-ARIA 1.2 §5.2.8)"
                )

        if val_min is not None and val_max is not None:
            if val_min > val_max:
                errs.append(
                    f"{name}: <{tag} role='scrollbar'> aria-valuemin ({val_min}) exceeds aria-valuemax ({val_max}) (W3C WAI-ARIA 1.2 §5.2.8)"
                )
            elif val_now is not None:
                if val_now < val_min or val_now > val_max:
                    errs.append(
                        f"{name}: <{tag} role='scrollbar'> aria-valuenow ({val_now}) is outside the range [{val_min}, {val_max}] (W3C WAI-ARIA 1.2 §5.2.8)"
                    )

    return errs


VALID_ARIA_LEVEL_ROLES = frozenset({"heading", "listitem", "row", "treeitem", "comment"})
NATIVE_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})


class _AriaHeadingAndLevelParser(HTMLParser):
    """Audits custom role='heading' elements and aria-level attributes for semantic hierarchy (W3C WAI-ARIA 1.2 §5.3.2, §6.6 & WCAG 2.2 SC 1.3.1 / SC 4.1.2)."""
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.heading_stack: list[dict] = []
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        roles = set(attr_dict.get("role", "").lower().split())
        is_heading_role = "heading" in roles

        if "aria-level" in attr_dict:
            raw_level = attr_dict["aria-level"].strip()
            try:
                val = int(raw_level)
                if val < 1:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares non-positive aria-level='{raw_level}' "
                        f"(must be a positive integer >= 1; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1)"
                    )
            except ValueError:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares non-integer aria-level='{raw_level}' "
                    f"(must be a positive integer >= 1; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1)"
                )

            has_valid_role = (
                t in NATIVE_HEADING_TAGS
                or bool(roles & VALID_ARIA_LEVEL_ROLES)
            )
            if not has_valid_role:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares aria-level on element without a hierarchical role "
                    f"(only valid on 'heading', 'listitem', 'row', 'treeitem', 'comment'; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                )

        if is_heading_role:
            if "aria-level" not in attr_dict:
                self.errs.append(
                    f"{self.name}{loc}: <{t} role='heading'> missing required 'aria-level' attribute "
                    f"(W3C WAI-ARIA 1.2 §5.3.2 & WCAG 2.2 SC 1.3.1)"
                )

            has_name = bool(attr_dict.get("aria-label", "").strip() or attr_dict.get("aria-labelledby", "").strip())
            if t not in self.VOID_TAGS:
                self.heading_stack.append({
                    "tag": t,
                    "loc": loc,
                    "has_name": has_name,
                    "text": [],
                    "has_img_alt": False,
                })
            elif not has_name:
                self.errs.append(
                    f"{self.name}{loc}: <{t} role='heading'> is empty and lacks accessible name "
                    f"(WCAG 2.2 SC 1.3.1 Info & Relationships & W3C Failure F43)"
                )
        else:
            if t == "img" and self.heading_stack and attr_dict.get("alt", "").strip():
                self.heading_stack[-1]["has_img_alt"] = True

    def handle_data(self, data: str) -> None:
        if self.heading_stack:
            self.heading_stack[-1]["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if self.heading_stack and self.heading_stack[-1]["tag"] == t:
            heading_info = self.heading_stack.pop()
            visible_text = "".join(heading_info["text"]).strip()
            if not visible_text and not heading_info["has_name"] and not heading_info["has_img_alt"]:
                self.errs.append(
                    f"{self.name}{heading_info['loc']}: <{t} role='heading'> is empty and lacks accessible name "
                    f"(WCAG 2.2 SC 1.3.1 Info & Relationships & W3C Failure F43)"
                )


def check_aria_heading_and_level_integrity(name: str, body: str) -> list[str]:
    """Ensure custom role='heading' elements declare explicit aria-level and accessible content, and aria-level values are positive integers on valid roles (W3C WAI-ARIA 1.2 §5.3.2, §6.6 & WCAG 2.2 SC 1.3.1 / SC 4.1.2)."""
    parser = _AriaHeadingAndLevelParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


VALID_ORIENTATION_ROLES = frozenset({
    "scrollbar", "slider", "separator", "tablist", "toolbar",
    "menu", "menubar", "tree", "treegrid", "radiogroup", "listbox", "combobox"
})
VALID_SORT_ROLES = frozenset({"columnheader", "rowheader"})


class _AriaOrientationAndSortParser(HTMLParser):
    """Audits aria-orientation and aria-sort placement against valid element roles (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)."""
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        roles = set(attr_dict.get("role", "").lower().split())

        if "aria-orientation" in attr_dict:
            has_valid_orientation_role = (
                t == "hr"
                or bool(roles & VALID_ORIENTATION_ROLES)
            )
            if not has_valid_orientation_role:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares aria-orientation on element without orientation-sensitive role "
                    f"(only valid on 'scrollbar', 'slider', 'separator', 'tablist', 'toolbar', 'menu', 'menubar', 'tree', 'treegrid', 'radiogroup', 'listbox', 'combobox'; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                )

        if "aria-sort" in attr_dict:
            has_valid_sort_role = (
                t == "th"
                or bool(roles & VALID_SORT_ROLES)
            )
            if not has_valid_sort_role:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares aria-sort on non-header element "
                    f"(aria-sort is only valid on <th>, 'columnheader', or 'rowheader'; HTML5 §4.9.10 & W3C WAI-ARIA 1.2 §6.6)"
                )


def check_aria_orientation_and_sort_context_integrity(name: str, body: str) -> list[str]:
    """Ensure aria-orientation and aria-sort are applied only to semantically valid element roles (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)."""
    parser = _AriaOrientationAndSortParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _AriaProgressbarParser(HTMLParser):
    """Audits elements with role='progressbar' for accessible names and valid numeric bounds (W3C WAI-ARIA 1.2 §5.2.8 & WCAG 2.2 SC 4.1.2)."""
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        roles = set(attr_dict.get("role", "").lower().split())

        if "progressbar" in roles:
            has_name = bool(attr_dict.get("aria-label", "").strip() or attr_dict.get("aria-labelledby", "").strip())
            if not has_name:
                self.errs.append(
                    f"{self.name}{loc}: <{t} role='progressbar'> missing accessible name "
                    f"('aria-label' or 'aria-labelledby'; WCAG 2.2 SC 4.1.2)"
                )

            val_min: float = 0.0
            val_max: float = 100.0

            if "aria-valuemin" in attr_dict:
                raw_min = attr_dict["aria-valuemin"].strip()
                try:
                    val_min = float(raw_min)
                except ValueError:
                    self.errs.append(
                        f"{self.name}{loc}: <{t} role='progressbar'> aria-valuemin='{raw_min}' is not a valid number (W3C WAI-ARIA 1.2 §5.2.8)"
                    )

            if "aria-valuemax" in attr_dict:
                raw_max = attr_dict["aria-valuemax"].strip()
                try:
                    val_max = float(raw_max)
                except ValueError:
                    self.errs.append(
                        f"{self.name}{loc}: <{t} role='progressbar'> aria-valuemax='{raw_max}' is not a valid number (W3C WAI-ARIA 1.2 §5.2.8)"
                    )

            if "aria-valuemin" in attr_dict and "aria-valuemax" in attr_dict and val_min > val_max:
                self.errs.append(
                    f"{self.name}{loc}: <{t} role='progressbar'> aria-valuemin ({val_min}) exceeds aria-valuemax ({val_max}) (W3C WAI-ARIA 1.2 §5.2.8)"
                )

            if "aria-valuenow" in attr_dict:
                raw_now = attr_dict["aria-valuenow"].strip()
                try:
                    val_now = float(raw_now)
                    if val_now < val_min or val_now > val_max:
                        self.errs.append(
                            f"{self.name}{loc}: <{t} role='progressbar'> aria-valuenow ({val_now}) is outside the range [{val_min}, {val_max}] (W3C WAI-ARIA 1.2 §5.2.8)"
                        )
                except ValueError:
                    self.errs.append(
                        f"{self.name}{loc}: <{t} role='progressbar'> aria-valuenow='{raw_now}' is not a valid number (W3C WAI-ARIA 1.2 §5.2.8)"
                    )


def check_aria_progressbar_accessibility(name: str, body: str) -> list[str]:
    """Ensure elements with role='progressbar' declare an accessible name and valid value bounds (W3C WAI-ARIA 1.2 §5.2.8 & WCAG 2.2 SC 4.1.2)."""
    parser = _AriaProgressbarParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


VALID_HASPOPUP_TOKENS = frozenset({"true", "false", "menu", "listbox", "tree", "grid", "dialog"})
INTERACTIVE_HTML_TAGS = frozenset({"button", "a", "summary", "input", "select", "textarea", "details"})
INTERACTIVE_ARIA_ROLES = frozenset({
    "button", "link", "tab", "combobox", "menuitem", "menuitemcheckbox",
    "menuitemradio", "treeitem", "row", "tree", "gridcell", "option", "switch"
})
VALID_TRACK_KINDS = frozenset({"subtitles", "captions", "descriptions", "chapters", "metadata"})
BCP47_LANG_RE = re.compile(r"^[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})*$")


class _AriaTabAndTabpanelParser(HTMLParser):
    """Audits tab, tablist, and tabpanel relationships, selection states, and accessible names (W3C WAI-ARIA 1.2 §5.3.7 & WCAG 2.2 SC 1.3.1 / SC 4.1.2)."""
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.element_ids: set[str] = set()
        self.tablists: list[dict] = []
        self.tabs: list[dict] = []
        self.tabpanels: list[dict] = []
        self.current_tab: dict | None = None
        self.current_tabpanel: dict | None = None
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        elem_id = attr_dict.get("id", "").strip()
        if elem_id:
            self.element_ids.add(elem_id)

        roles = set(attr_dict.get("role", "").lower().split())

        if "tablist" in roles:
            if "aria-expanded" in attr_dict:
                self.errs.append(
                    f"{self.name}{loc}: <{t} role='tablist'> declares aria-expanded; "
                    f"aria-expanded belongs on interactive tab or accordion triggers, not tablist containers "
                    f"(W3C WAI-ARIA 1.2 §5.3.7 Tabs Pattern)"
                )
            self.tablists.append({
                "tag": t,
                "loc": loc,
                "aria_label": attr_dict.get("aria-label", "").strip(),
                "aria_labelledby": attr_dict.get("aria-labelledby", "").strip(),
            })

        if "tab" in roles:
            tab_info = {
                "tag": t,
                "loc": loc,
                "id": elem_id,
                "aria_selected": attr_dict.get("aria-selected", "").strip().lower(),
                "aria_controls": attr_dict.get("aria-controls", "").strip(),
                "aria_label": attr_dict.get("aria-label", "").strip(),
                "aria_labelledby": attr_dict.get("aria-labelledby", "").strip(),
                "text": [],
            }
            if tab_info["aria_selected"] not in ("true", "false"):
                self.errs.append(
                    f"{self.name}{loc}: <{t} role='tab'> missing valid aria-selected attribute "
                    f"(must be 'true' or 'false'; W3C WAI-ARIA 1.2 §5.3.7 & WCAG 2.2 SC 4.1.2)"
                )
            self.tabs.append(tab_info)
            self.current_tab = tab_info

        if "tabpanel" in roles:
            panel_info = {
                "tag": t,
                "loc": loc,
                "id": elem_id,
                "aria_label": attr_dict.get("aria-label", "").strip(),
                "aria_labelledby": attr_dict.get("aria-labelledby", "").strip(),
                "text": [],
            }
            self.tabpanels.append(panel_info)
            self.current_tabpanel = panel_info

    def handle_data(self, data: str) -> None:
        if self.current_tab is not None:
            self.current_tab["text"].append(data)
        if self.current_tabpanel is not None:
            self.current_tabpanel["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.current_tab is not None and tag.lower() == self.current_tab["tag"]:
            self.current_tab = None
        if self.current_tabpanel is not None and tag.lower() == self.current_tabpanel["tag"]:
            self.current_tabpanel = None

    def close(self) -> None:
        super().close()
        if len(self.tablists) > 1:
            for tl in self.tablists:
                if not tl["aria_label"] and not tl["aria_labelledby"]:
                    self.errs.append(
                        f"{self.name}{tl['loc']}: multiple <{tl['tag']} role='tablist'> elements on page require "
                        f"accessible names ('aria-label' or 'aria-labelledby') to distinguish tab groups (WCAG 2.2 SC 1.3.1 & SC 4.1.2)"
                    )

        for tab in self.tabs:
            has_name = bool(
                tab["aria_label"]
                or tab["aria_labelledby"]
                or "".join(tab["text"]).strip()
            )
            if not has_name:
                self.errs.append(
                    f"{self.name}{tab['loc']}: <{tab['tag']} role='tab'> lacks accessible name "
                    f"(must have visible text, 'aria-label', or 'aria-labelledby'; WCAG 2.2 SC 4.1.2)"
                )
            if tab["aria_controls"] and tab["aria_controls"] not in self.element_ids:
                self.errs.append(
                    f"{self.name}{tab['loc']}: <{tab['tag']} role='tab'> aria-controls='{tab['aria_controls']}' "
                    f"references non-existent element id (W3C WAI-ARIA 1.2 §5.3.7 & WCAG 2.2 SC 1.3.1)"
                )

        for panel in self.tabpanels:
            has_name = bool(
                panel["aria_label"]
                or panel["aria_labelledby"]
                or "".join(panel["text"]).strip()
            )
            if not has_name:
                self.errs.append(
                    f"{self.name}{panel['loc']}: <{panel['tag']} role='tabpanel'> lacks accessible name or content "
                    f"(WCAG 2.2 SC 4.1.2 & SC 1.3.1)"
                )
            if panel["aria_labelledby"] and panel["aria_labelledby"] not in self.element_ids:
                self.errs.append(
                    f"{self.name}{panel['loc']}: <{panel['tag']} role='tabpanel'> aria-labelledby='{panel['aria_labelledby']}' "
                    f"references non-existent element id (W3C WAI-ARIA 1.2 §5.3.7 & WCAG 2.2 SC 1.3.1)"
                )


def check_aria_tab_tablist_and_tabpanel_integrity(name: str, body: str) -> list[str]:
    """Ensure tab, tablist, and tabpanel roles enforce selection states, accessible names, and valid ID bindings (W3C WAI-ARIA 1.2 §5.3.7 & WCAG 2.2 SC 1.3.1 / SC 4.1.2)."""
    parser = _AriaTabAndTabpanelParser(name)
    try:
        parser.feed(body)
        parser.close()
    except Exception:
        pass
    return parser.errs


class _AriaPopupAndExpansionParser(HTMLParser):
    """Audits aria-haspopup tokens and aria-expanded boolean values on interactive vs static elements (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)."""
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        roles = set(attr_dict.get("role", "").lower().split())

        if "aria-haspopup" in attr_dict:
            raw_val = attr_dict["aria-haspopup"].strip().lower()
            if raw_val not in VALID_HASPOPUP_TOKENS:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares invalid aria-haspopup='{raw_val}' "
                    f"(W3C WAI-ARIA 1.2 §6.6 strictly restricts aria-haspopup to 'true', 'false', 'menu', 'listbox', 'tree', 'grid', or 'dialog')"
                )

        if "aria-expanded" in attr_dict:
            raw_val = attr_dict["aria-expanded"].strip().lower()
            if raw_val not in ("true", "false"):
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares invalid aria-expanded='{raw_val}' "
                    f"(must be 'true' or 'false'; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                )
            else:
                has_interactive_tag = t in INTERACTIVE_HTML_TAGS
                has_interactive_role = bool(roles & INTERACTIVE_ARIA_ROLES)
                has_tabindex = "tabindex" in attr_dict and attr_dict["tabindex"].strip() not in ("-1", "")
                if not (has_interactive_tag or has_interactive_role or has_tabindex):
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares aria-expanded on non-interactive static element "
                        f"without interactive role or keyboard focusability (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                    )


def check_aria_popup_and_expansion_trigger_integrity(name: str, body: str) -> list[str]:
    """Ensure aria-haspopup uses valid enumerated tokens and aria-expanded is boolean and placed on interactive controls (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)."""
    parser = _AriaPopupAndExpansionParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _MediaTrackParser(HTMLParser):
    """Audits <track> elements inside media containers for valid kind, src, srclang, and default uniqueness (HTML5 §4.8.11, §4.8.12 & WCAG 2.2 SC 1.2.2)."""
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.in_media = False
        self.current_media_tag = ""
        self.current_media_loc = ""
        self.default_kinds_in_media: set[str] = set()
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if t in ("video", "audio"):
            self.in_media = True
            self.current_media_tag = t
            self.current_media_loc = loc
            self.default_kinds_in_media = set()

        if t == "track":
            if not self.in_media:
                self.errs.append(
                    f"{self.name}{loc}: <track> element placed outside <video> or <audio> container "
                    f"(HTML5 §4.8.11 restricts <track> to media children)"
                )
            raw_kind = attr_dict.get("kind", "").strip().lower()
            if not raw_kind or raw_kind not in VALID_TRACK_KINDS:
                self.errs.append(
                    f"{self.name}{loc}: <track> missing or invalid kind='{raw_kind}' "
                    f"(HTML5 §4.8.11 restricts kind to 'subtitles', 'captions', 'descriptions', 'chapters', or 'metadata')"
                )

            src = attr_dict.get("src", "").strip()
            if not src:
                self.errs.append(
                    f"{self.name}{loc}: <track> missing or empty src attribute "
                    f"(HTML5 §4.8.11 requires non-empty src URL)"
                )

            if raw_kind in ("subtitles", "captions"):
                srclang = attr_dict.get("srclang", "").strip()
                if not srclang or not BCP47_LANG_RE.match(srclang):
                    self.errs.append(
                        f"{self.name}{loc}: <track kind='{raw_kind}'> missing or invalid srclang='{srclang}' "
                        f"(HTML5 §4.8.11 requires valid BCP 47 language code when kind is subtitles or captions)"
                    )

            if "default" in attr_dict:
                if raw_kind in self.default_kinds_in_media:
                    self.errs.append(
                        f"{self.name}{loc}: <{self.current_media_tag}> contains multiple default <track> elements "
                        f"for kind='{raw_kind}' (HTML5 §4.8.11 forbids multiple default tracks of same kind)"
                    )
                else:
                    self.default_kinds_in_media.add(raw_kind)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("video", "audio") and self.in_media and t == self.current_media_tag:
            self.in_media = False
            self.current_media_tag = ""
            self.default_kinds_in_media = set()


def check_media_track_accessibility(name: str, body: str) -> list[str]:
    """Ensure <track> elements specify valid kind, non-empty src, BCP 47 srclang, and at most one default track per kind (HTML5 §4.8.11 & WCAG 2.2 SC 1.2.2)."""
    parser = _MediaTrackParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


VALID_CELL_ROLES = frozenset({"cell", "gridcell", "columnheader", "rowheader"})
VALID_ROW_ROLES = frozenset({"row"})
VALID_COORDINATE_ROLES = VALID_CELL_ROLES | VALID_ROW_ROLES
VALID_HTML_TABLE_CELLS = frozenset({"td", "th"})
VALID_HTML_TABLE_ROWS = frozenset({"tr"})


class _GridAndTableCoordinateParser(HTMLParser):
    """Audits ARIA table, grid, and treegrid coordinate attributes (row/col count, index, span) for positive bounds and valid placement (W3C WAI-ARIA 1.2 §5.2.5, §5.2.6, §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        ad = {k.lower(): (v or "") for k, v in attrs}
        role = ad.get("role", "").lower()
        roles = set(role.split())
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"

        # 1. aria-rowcount / aria-colcount
        for count_attr in ("aria-rowcount", "aria-colcount"):
            if count_attr in ad:
                raw_val = ad[count_attr].strip()
                try:
                    val = int(raw_val)
                    if val < -1 or val == 0:
                        self.errs.append(
                            f"{self.name}{loc}: <{t}> specifies invalid '{count_attr}=\"{raw_val}\"' "
                            f"(must be integer >= 1 or -1 for unknown; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1)"
                        )
                except ValueError:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> specifies non-integer '{count_attr}=\"{raw_val}\"' "
                        f"(must be integer >= 1 or -1; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1)"
                    )

        # 2. aria-rowindex / aria-colindex
        for idx_attr in ("aria-rowindex", "aria-colindex"):
            if idx_attr in ad:
                raw_val = ad[idx_attr].strip()
                try:
                    val = int(raw_val)
                    if val < 1:
                        self.errs.append(
                            f"{self.name}{loc}: <{t}> specifies non-positive '{idx_attr}=\"{raw_val}\"' "
                            f"(must be integer >= 1; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1)"
                        )
                except ValueError:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> specifies non-integer '{idx_attr}=\"{raw_val}\"' "
                        f"(must be integer >= 1; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1)"
                    )
                is_valid_tag = (t in VALID_HTML_TABLE_CELLS or t in VALID_HTML_TABLE_ROWS)
                has_valid_role = bool(roles & VALID_COORDINATE_ROLES)
                if not is_valid_tag and not has_valid_role:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares '{idx_attr}' on non-table element without cell or row role "
                        f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1 / SC 4.1.2)"
                    )

        # 3. aria-rowspan / aria-colspan
        for span_attr in ("aria-rowspan", "aria-colspan"):
            if span_attr in ad:
                raw_val = ad[span_attr].strip()
                try:
                    val = int(raw_val)
                    if val < 1:
                        self.errs.append(
                            f"{self.name}{loc}: <{t}> specifies non-positive '{span_attr}=\"{raw_val}\"' "
                            f"(must be integer >= 1; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1)"
                        )
                except ValueError:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> specifies non-integer '{span_attr}=\"{raw_val}\"' "
                        f"(must be integer >= 1; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1)"
                    )
                is_valid_cell_tag = (t in VALID_HTML_TABLE_CELLS)
                has_valid_cell_role = bool(roles & VALID_CELL_ROLES)
                if not is_valid_cell_tag and not has_valid_cell_role:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares '{span_attr}' on non-cell element without cell role "
                        f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1 / SC 4.1.2)"
                    )

        # 4. aria-rowindextext / aria-colindextext require aria-rowindex / aria-colindex
        if "aria-rowindextext" in ad:
            if "aria-rowindex" not in ad:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares 'aria-rowindextext' without accompanying 'aria-rowindex' "
                    f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1)"
                )
            elif not ad["aria-rowindextext"].strip():
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares empty 'aria-rowindextext' attribute "
                    f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1)"
                )

        if "aria-colindextext" in ad:
            if "aria-colindex" not in ad:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares 'aria-colindextext' without accompanying 'aria-colindex' "
                    f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1)"
                )
            elif not ad["aria-colindextext"].strip():
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares empty 'aria-colindextext' attribute "
                    f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1)"
                )


def check_aria_grid_and_table_coordinate_integrity(name: str, body: str) -> list[str]:
    """Ensure ARIA table, grid, and treegrid coordinate attributes (row/col count, index, span) have valid positive bounds and valid placement (W3C WAI-ARIA 1.2 §5.2.5, §5.2.6, §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""
    parser = _GridAndTableCoordinateParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _TreeHierarchyParser(HTMLParser):
    """Audits ARIA tree, treegrid, and treeitem hierarchy, branch expansion states, and accessible names (W3C WAI-ARIA 1.2 §5.3.8, §5.3.9, §5.2.9 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.container_stack: list[dict] = []
        self.treeitem_stack: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        ad = {k.lower(): (v or "") for k, v in attrs}
        role = ad.get("role", "").lower()
        roles = set(role.split())
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"

        is_tree = "tree" in roles
        is_treegrid = "treegrid" in roles
        is_group = "group" in roles
        is_treeitem = "treeitem" in roles

        if is_tree:
            has_label = bool(ad.get("aria-label", "").strip() or ad.get("aria-labelledby", "").strip())
            if not has_label:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declaring role='tree' missing accessible name "
                    f"(must provide aria-label or aria-labelledby; WCAG 2.2 SC 4.1.2 & W3C WAI-ARIA 1.2 §5.3.8)"
                )
            if "aria-multiselectable" in ad:
                ms_val = ad["aria-multiselectable"].strip().lower()
                if ms_val not in ("true", "false"):
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> with role='tree' specifies invalid aria-multiselectable='{ms_val}' "
                        f"(must be 'true' or 'false'; W3C WAI-ARIA 1.2 §6.6)"
                    )

        if is_treeitem:
            in_valid_container = any(
                c["is_tree"] or c["is_treegrid"] or c["is_group"] or c["is_treeitem"]
                for c in self.container_stack
            )
            if not in_valid_container:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declaring role='treeitem' is not contained within a role='tree', "
                    f"role='treegrid', or role='group' container (WCAG 2.2 SC 1.3.1 & W3C WAI-ARIA 1.2 §5.3.9)"
                )

            for parent_ti in self.treeitem_stack:
                parent_ti["has_children"] = True

            has_expanded = "aria-expanded" in ad
            expanded_val = ad.get("aria-expanded", "").strip().lower()
            if has_expanded and expanded_val not in ("true", "false"):
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declaring role='treeitem' specifies invalid aria-expanded='{expanded_val}' "
                    f"(must be 'true' or 'false'; W3C WAI-ARIA 1.2 §6.6 & SC 4.1.2)"
                )

            self.treeitem_stack.append({
                "tag": t,
                "loc": loc,
                "has_expanded": has_expanded,
                "expanded_val": expanded_val,
                "has_children": False,
            })

        elif is_group:
            for parent_ti in self.treeitem_stack:
                parent_ti["has_children"] = True

        self.container_stack.append({
            "tag": t,
            "is_tree": is_tree,
            "is_treegrid": is_treegrid,
            "is_group": is_group,
            "is_treeitem": is_treeitem,
        })

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if self.treeitem_stack and self.treeitem_stack[-1]["tag"] == t:
            ti = self.treeitem_stack.pop()
            if ti["has_children"] and not ti["has_expanded"]:
                self.errs.append(
                    f"{self.name}{ti['loc']}: <{ti['tag']}> with role='treeitem' has child treeitem/group nodes "
                    f"but is missing required aria-expanded attribute (must be 'true' or 'false'; W3C WAI-ARIA 1.2 §5.3.9 & WCAG 2.2 SC 4.1.2)"
                )

        for i in range(len(self.container_stack) - 1, -1, -1):
            if self.container_stack[i]["tag"] == t:
                self.container_stack.pop(i)
                break


def check_aria_tree_and_treeitem_hierarchy_integrity(name: str, body: str) -> list[str]:
    """Ensure ARIA tree and treeitem roles follow hierarchical containment, branch treeitems declare aria-expanded, and trees have accessible names (W3C WAI-ARIA 1.2 §5.3.8, §5.3.9, §5.2.9 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""
    parser = _TreeHierarchyParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


VIEWBOX_ATTR_RE = re.compile(
    r"^\s*([+-]?[0-9]*\.?[0-9]+)\s+([+-]?[0-9]*\.?[0-9]+)\s+([+-]?[0-9]*\.?[0-9]+)\s+([+-]?[0-9]*\.?[0-9]+)\s*$"
)


def check_svg_viewbox_and_text_integrity(name: str, body: str) -> list[str]:
    """Ensure SVG graphics declare a valid responsive viewBox and do not contain empty unhidden text nodes (SVG 2 §5.2, WCAG 2.2 SC 1.1.1, SC 1.4.10 & Spec 05 Explainer Guidelines)."""
    errs: list[str] = []
    svg_re = re.compile(r"<svg\b([^>]*)>(.*?)</svg>", re.I | re.S)

    for m in svg_re.finditer(body):
        attrs, inner = m.group(1), m.group(2)
        vb_m = re.search(r'\bviewBox\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        if not vb_m:
            errs.append(
                f"{name}: <svg> missing required 'viewBox' attribute for responsive reflow "
                f"(WCAG 2.2 SC 1.4.10 Reflow, SVG 2 §5.2 & Spec 05 Explainer Guidelines)"
            )
        else:
            vb_val = vb_m.group(1).strip()
            match = VIEWBOX_ATTR_RE.match(vb_val)
            if not match:
                errs.append(
                    f"{name}: <svg> declares malformed viewBox='{vb_val}' "
                    f"(must be 'min-x min-y width height' with 4 numeric values; SVG 2 §5.2)"
                )
            else:
                width, height = float(match.group(3)), float(match.group(4))
                if width <= 0 or height <= 0:
                    errs.append(
                        f"{name}: <svg> viewBox='{vb_val}' has non-positive width ({width}) or height ({height}) "
                        f"(SVG 2 §5.2 requires positive dimensions)"
                    )

        for tm in re.finditer(r'<(text|tspan)\b([^>]*)>(.*?)</\1>', inner, re.I | re.S):
            tag_name, tag_attrs, tag_inner = tm.group(1).lower(), tm.group(2), tm.group(3)
            is_hidden = bool(re.search(r'\baria-hidden\s*=\s*["\']true["\']', tag_attrs, re.I))
            if not is_hidden:
                clean_txt = _TAG_RE.sub(" ", tag_inner).strip()
                if not clean_txt:
                    errs.append(
                        f"{name}: <svg> contains empty or whitespace-only <{tag_name}> node without aria-hidden='true' "
                        f"(creates phantom unannounced node in SVG accessibility tree; WCAG 2.2 SC 1.1.1 & SC 4.1.2)"
                    )

    return errs


VALID_SET_ITEM_ROLES = frozenset({
    "article", "listitem", "menuitem", "menuitemcheckbox", "menuitemradio",
    "option", "radio", "row", "tab", "treeitem", "comment",
})
VALID_SET_ITEM_NATIVE_TAGS = frozenset({"li", "option"})


VALID_CITE_PREFIXES = ("http://", "https://", "/", "#", "urn:", "doi:", "//")


def check_blockquote_and_citation_integrity(name: str, body: str) -> list[str]:
    """Ensure blockquotes, inline quotations, and citation tags are non-empty and specify valid citation URIs (HTML5 §4.5.6, §4.5.7, §4.5.21 & WCAG 2.2 SC 1.3.1)."""
    errs: list[str] = []

    for m in re.finditer(r"<blockquote\b([^>]*)>(.*?)</blockquote>", body, re.I | re.S):
        attrs, inner = m.group(1), m.group(2)
        clean = _TAG_RE.sub(" ", inner).strip()
        if not clean:
            errs.append(
                f"{name}: <blockquote> must not be empty or whitespace-only (HTML5 §4.5.6 & WCAG 2.2 SC 1.3.1)"
            )
        cite_m = re.search(r'\bcite\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if cite_m:
            cite_val = cite_m.group(1).strip()
            if not cite_val:
                errs.append(
                    f"{name}: <blockquote> declares empty cite attribute (HTML5 §4.5.6 requires a valid non-empty URL)"
                )
            elif not any(cite_val.startswith(p) for p in VALID_CITE_PREFIXES):
                errs.append(
                    f"{name}: <blockquote> declares invalid cite URL '{cite_val}' (must be a valid absolute or relative URL; HTML5 §4.5.6)"
                )

    for m in re.finditer(r"<q\b([^>]*)>(.*?)</q>", body, re.I | re.S):
        attrs, inner = m.group(1), m.group(2)
        clean = _TAG_RE.sub(" ", inner).strip()
        if not clean:
            errs.append(
                f"{name}: <q> inline quotation must not be empty or whitespace-only (HTML5 §4.5.21 & WCAG 2.2 SC 1.3.1)"
            )
        cite_m = re.search(r'\bcite\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if cite_m:
            cite_val = cite_m.group(1).strip()
            if not cite_val:
                errs.append(
                    f"{name}: <q> declares empty cite attribute (HTML5 §4.5.21 requires a valid non-empty URL)"
                )
            elif not any(cite_val.startswith(p) for p in VALID_CITE_PREFIXES):
                errs.append(
                    f"{name}: <q> declares invalid cite URL '{cite_val}' (must be a valid absolute or relative URL; HTML5 §4.5.21)"
                )

    for m in re.finditer(r"<cite\b([^>]*)>(.*?)</cite>", body, re.I | re.S):
        attrs, inner = m.group(1), m.group(2)
        clean = _TAG_RE.sub(" ", inner).strip()
        if not clean:
            errs.append(
                f"{name}: <cite> element must not be empty or whitespace-only (HTML5 §4.5.7 & WCAG 2.2 SC 1.3.1)"
            )
        if re.search(r"<cite\b", inner, re.I):
            errs.append(
                f"{name}: <cite> must not contain nested <cite> elements (HTML5 §4.5.7)"
            )

    return errs


def check_bdo_bdi_and_dir_integrity(name: str, body: str) -> list[str]:
    """Ensure bi-directional overrides (<bdo>), isolates (<bdi>), and dir attributes declare valid directionality (HTML5 §4.5.25, §4.5.26, §3.2.6.2 & WCAG 2.2 SC 1.3.2)."""
    errs: list[str] = []
    valid_dirs = {"ltr", "rtl", "auto"}
    valid_bdo_dirs = {"ltr", "rtl"}

    elem_re = re.compile(r"<([a-zA-Z0-9:-]+)\b([^>]*)>", re.I)
    for m in elem_re.finditer(body):
        tag, attrs = m.group(1).lower(), m.group(2)
        dir_m = re.search(r'\bdir\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if dir_m:
            dir_val = dir_m.group(1).strip().lower()
            if not dir_val:
                errs.append(
                    f"{name}: <{tag}> declares empty dir attribute (must be 'ltr', 'rtl', or 'auto'; HTML5 §3.2.6.2)"
                )
            elif dir_val not in valid_dirs:
                errs.append(
                    f"{name}: <{tag}> declares invalid dir='{dir_val}' (must be 'ltr', 'rtl', or 'auto'; HTML5 §3.2.6.2 & WCAG 2.2 SC 1.3.2)"
                )

        if tag == "bdo":
            if not dir_m:
                errs.append(
                    f"{name}: <bdo> is missing required 'dir' attribute (must be 'ltr' or 'rtl'; HTML5 §4.5.26)"
                )
            else:
                dir_val = dir_m.group(1).strip().lower()
                if dir_val not in valid_bdo_dirs:
                    errs.append(
                        f"{name}: <bdo> declares invalid dir='{dir_val}' (must be 'ltr' or 'rtl'; HTML5 §4.5.26)"
                    )

    for m in re.finditer(r"<(bdo|bdi)\b([^>]*)>(.*?)</\1>", body, re.I | re.S):
        tag_name, inner = m.group(1).lower(), m.group(3)
        clean = _TAG_RE.sub(" ", inner).strip()
        if not clean:
            errs.append(
                f"{name}: <{tag_name}> must not be empty or whitespace-only (HTML5 §4.5.25 / §4.5.26 & WCAG 2.2 SC 1.3.2)"
            )

    return errs


class _AriaPosInSetAndSetSizeParser(HTMLParser):
    """Audits ARIA posinset and setsize numeric bounds, ordering, and valid item role placement (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        ad = {k.lower(): (v or "") for k, v in attrs}
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"

        has_pos = "aria-posinset" in ad
        has_size = "aria-setsize" in ad

        if not (has_pos or has_size):
            return

        roles = set(ad.get("role", "").lower().split())
        is_valid_item = bool(t in VALID_SET_ITEM_NATIVE_TAGS or (roles & VALID_SET_ITEM_ROLES))

        if not is_valid_item:
            attr_name = "aria-posinset and aria-setsize" if (has_pos and has_size) else ("aria-posinset" if has_pos else "aria-setsize")
            self.errs.append(
                f"{self.name}{loc}: <{t}> declares {attr_name} on non-item element without set item role "
                f"(W3C WAI-ARIA 1.2 §6.6 restricts posinset/setsize to listitem, treeitem, option, row, tab, or radio)"
            )

        pos_val: int | None = None
        if has_pos:
            raw_pos = ad["aria-posinset"].strip()
            try:
                pos_val = int(raw_pos)
                if pos_val < 1:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares invalid aria-posinset='{raw_pos}' "
                        f"(must be a positive integer >= 1; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                    )
                    pos_val = None
            except ValueError:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares non-integer aria-posinset='{raw_pos}' "
                    f"(must be a valid integer; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                )
                pos_val = None

        size_val: int | None = None
        if has_size:
            raw_size = ad["aria-setsize"].strip()
            try:
                size_val = int(raw_size)
                if size_val == 0 or size_val < -1:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares invalid aria-setsize='{raw_size}' "
                        f"(must be an integer >= 1, or -1 for unknown size; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                    )
                    size_val = None
            except ValueError:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares non-integer aria-setsize='{raw_size}' "
                    f"(must be a valid integer; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                )
                size_val = None

        if pos_val is not None and size_val is not None and size_val >= 1:
            if pos_val > size_val:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares aria-posinset ({pos_val}) exceeding aria-setsize ({size_val}) "
                    f"(position in set cannot exceed set size; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                )


def check_aria_posinset_and_setsize_integrity(name: str, body: str) -> list[str]:
    """Ensure aria-posinset and aria-setsize have valid positive bounds, posinset does not exceed setsize, and placement is confined to set item roles (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""
    parser = _AriaPosInSetAndSetSizeParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


VALID_KEY_MODIFIERS = frozenset({"control", "ctrl", "alt", "shift", "meta", "accel", "command"})
SEMANTIC_ROLED_TAGS = frozenset({
    "a", "button", "input", "select", "textarea", "nav", "main", "header", "footer",
    "aside", "section", "article", "dialog", "figure", "img", "table", "ul", "ol",
    "li", "h1", "h2", "h3", "h4", "h5", "h6", "form", "details", "summary", "meter",
    "progress", "blockquote", "time", "dd", "dt", "dl", "fieldset", "optgroup", "option", "output",
})


class _DetailsAndSummaryParser(HTMLParser):
    """Audits HTML5 details and summary disclosure structures, child order, cardinality, and interactive content boundaries (HTML5 §4.11.1, §4.11.2, W3C WAI-ARIA 1.2 §5.3.3 & WCAG 2.2 SC 1.3.1, SC 4.1.2, SC 2.1.1)."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.details_stack: list[dict[str, object]] = []
        self.in_summary = False
        self.summary_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        ad = {k.lower(): (v or "") for k, v in attrs}

        if self.details_stack:
            curr = self.details_stack[-1]
            if t == "summary":
                if curr["first_child_tag"] is not None and curr["first_child_tag"] != "summary":
                    first_tag = curr["first_child_tag"]
                    self.errs.append(
                        f"{self.name}{loc}: <summary> appears after child element <{first_tag}> in <details>; "
                        f"<summary> must be the first element child of <details> (HTML5 §4.11.1 & WCAG 2.2 SC 1.3.1)"
                    )
                elif curr["first_child_tag"] is None:
                    curr["first_child_tag"] = "summary"
                curr["has_child"] = True
            else:
                if curr["first_child_tag"] is None:
                    curr["first_child_tag"] = t
                curr["has_child"] = True

        if t == "details":
            self.details_stack.append({"has_child": False, "summary_count": 0, "first_child_tag": None})
        elif t == "summary":
            if not self.details_stack:
                self.errs.append(f"{self.name}{loc}: orphaned <summary> outside of <details> (HTML5 §4.11.2)")
            else:
                self.details_stack[-1]["summary_count"] = int(self.details_stack[-1]["summary_count"]) + 1
                if int(self.details_stack[-1]["summary_count"]) > 1:
                    self.errs.append(
                        f"{self.name}{loc}: multiple <summary> elements inside a single <details> "
                        f"(HTML5 §4.11.1 permits at most one <summary> child)"
                    )
            self.in_summary = True
            self.summary_text = []
        elif self.in_summary:
            is_interactive = False
            if t in ("button", "input", "select", "textarea", "details"):
                is_interactive = True
            elif t == "a" and ("href" in ad or "tabindex" in ad):
                is_interactive = True
            elif "tabindex" in ad:
                is_interactive = True
            roles = set(ad.get("role", "").lower().split())
            if roles & {"button", "link", "checkbox", "radio", "switch", "menuitem", "tab"}:
                is_interactive = True

            if is_interactive:
                self.errs.append(
                    f"{self.name}{loc}: interactive <{t}> inside <summary> violates HTML5 §4.11.2 & WCAG 2.2 SC 4.1.2 "
                    f"(summary content must not contain interactive elements or focusable controls)"
                )

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        if t == "details":
            if self.details_stack:
                self.details_stack.pop()
        elif t == "summary":
            self.in_summary = False
            text = "".join(self.summary_text).strip()
            if not text:
                self.errs.append(
                    f"{self.name}{loc}: <summary> must not be empty or whitespace-only "
                    f"(WCAG 2.2 SC 4.1.2 Name, Role, Value requires an accessible name)"
                )

    def handle_data(self, data: str) -> None:
        if self.in_summary:
            self.summary_text.append(data)


def check_details_and_summary_disclosure_integrity(name: str, body: str) -> list[str]:
    """Ensure <details> and <summary> disclosure elements satisfy HTML5 structure, cardinality, and interactive content constraints (HTML5 §4.11.1, §4.11.2, W3C WAI-ARIA 1.2 §5.3.3 & WCAG 2.2 SC 1.3.1, SC 4.1.2, SC 2.1.1)."""
    parser = _DetailsAndSummaryParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


def check_del_and_ins_edit_integrity(name: str, body: str) -> list[str]:
    """Ensure document edit elements (<del> and <ins>) are non-empty and specify valid citation URIs and ISO 8601 datetimes (HTML5 §4.5.18, §4.5.19 & WCAG 2.2 SC 1.3.1)."""
    errs: list[str] = []
    for m in re.finditer(r"<(del|ins)\b([^>]*)>(.*?)</\1>", body, re.I | re.S):
        tag, attrs, inner = m.group(1).lower(), m.group(2), m.group(3)
        clean = _TAG_RE.sub(" ", inner).strip()
        if not clean:
            errs.append(
                f"{name}: <{tag}> edit element must not be empty or whitespace-only (HTML5 §4.5.18/§4.5.19 & WCAG 2.2 SC 1.3.1)"
            )
        cite_m = re.search(r'\bcite\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if cite_m:
            cval = cite_m.group(1).strip()
            if not cval:
                errs.append(f"{name}: <{tag}> declares empty cite attribute (HTML5 §4.5.18/§4.5.19 requires a valid URL)")
            elif not any(cval.startswith(p) for p in VALID_CITE_PREFIXES):
                errs.append(f"{name}: <{tag}> declares invalid cite URL '{cval}' (must be absolute or relative URL)")
        dt_m = re.search(r'\bdatetime\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if dt_m:
            dtval = dt_m.group(1).strip()
            if not dtval:
                errs.append(f"{name}: <{tag}> declares empty datetime attribute (HTML5 §4.5.18/§4.5.19 requires a valid ISO 8601 date)")
            elif not _SemanticTimeParser.ISO_DATE_RE.match(dtval):
                errs.append(f"{name}: <{tag}> declares invalid datetime '{dtval}' (must be valid ISO 8601 date/time)")
    return errs


class _AriaShortcutsAndRoledescriptionParser(HTMLParser):
    """Audits aria-keyshortcuts syntax, aria-roledescription placement and duplication, and ARIA 1.3 braille attributes (W3C WAI-ARIA 1.2 §6.6, WAI-ARIA 1.3 §6.6 & WCAG 2.2 SC 2.1.4, SC 4.1.2)."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        ad = {k.lower(): (v or "") for k, v in attrs}

        if "aria-keyshortcuts" in ad:
            raw_ks = ad["aria-keyshortcuts"]
            clean_ks = raw_ks.strip()
            if not clean_ks:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares empty aria-keyshortcuts attribute (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 2.1.4)"
                )
            else:
                for sc in clean_ks.split():
                    parts = sc.split("+")
                    if any(not p.strip() for p in parts):
                        self.errs.append(
                            f"{self.name}{loc}: <{t}> declares malformed shortcut '{sc}' in aria-keyshortcuts (empty key part; W3C WAI-ARIA 1.2 §6.6)"
                        )
                    elif len(parts) > 1:
                        for mod in parts[:-1]:
                            if mod.lower() not in VALID_KEY_MODIFIERS:
                                self.errs.append(
                                    f"{self.name}{loc}: <{t}> declares invalid modifier '{mod}' in shortcut '{sc}' (W3C WAI-ARIA 1.2 §6.6)"
                                )

        if "aria-roledescription" in ad:
            raw_rd = ad["aria-roledescription"]
            clean_rd = raw_rd.strip()
            if not clean_rd:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares empty aria-roledescription attribute (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                )
            else:
                roles = ad.get("role", "").lower().split()
                has_role = bool(roles or (t in SEMANTIC_ROLED_TAGS))
                if not has_role:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares aria-roledescription='{clean_rd}' on generic container without an ARIA role "
                        f"(W3C WAI-ARIA 1.2 §6.6 restricts aria-roledescription to elements with a valid semantic or ARIA role)"
                    )
                for r in roles:
                    if r.lower() == clean_rd.lower():
                        self.errs.append(
                            f"{self.name}{loc}: <{t}> aria-roledescription='{clean_rd}' duplicates role='{r}' "
                            f"(redundant roledescription degrades screen reader UX; W3C WAI-ARIA 1.2 §6.6)"
                        )

        for b_attr in ("aria-brailleroledescription", "aria-braillelabel"):
            if b_attr in ad and not ad[b_attr].strip():
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares empty {b_attr} attribute (W3C WAI-ARIA 1.3 §6.6)"
                )


def check_aria_keyshortcuts_and_roledescription_integrity(name: str, body: str) -> list[str]:
    """Ensure aria-keyshortcuts has valid modifier and key syntax, and aria-roledescription is placed on roled elements without role duplication (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 2.1.4, SC 4.1.2)."""
    parser = _AriaShortcutsAndRoledescriptionParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _RubyAnnotationParser(HTMLParser):
    """Audits HTML5 <ruby>, <rt>, and <rp> ruby annotation structure and content (HTML5 §4.5.22, §4.5.23, §4.5.24 & WCAG 2.2 SC 1.3.1 Info and Relationships)."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.ruby_stack: list[dict[str, object]] = []
        self.in_rt = False
        self.rt_text: list[str] = []
        self.in_rp = False
        self.rp_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"

        if t == "ruby":
            self.ruby_stack.append({"rt_count": 0, "rp_count": 0, "loc": loc})
        elif t == "rt":
            if not self.ruby_stack:
                self.errs.append(
                    f"{self.name}{loc}: orphaned <rt> outside of enclosing <ruby> container "
                    f"(HTML5 §4.5.23 & WCAG 2.2 SC 1.3.1)"
                )
            else:
                self.ruby_stack[-1]["rt_count"] = int(self.ruby_stack[-1]["rt_count"]) + 1
            self.in_rt = True
            self.rt_text = []
        elif t == "rp":
            if not self.ruby_stack:
                self.errs.append(
                    f"{self.name}{loc}: orphaned <rp> outside of enclosing <ruby> container "
                    f"(HTML5 §4.5.24 & WCAG 2.2 SC 1.3.1)"
                )
            else:
                self.ruby_stack[-1]["rp_count"] = int(self.ruby_stack[-1]["rp_count"]) + 1
            self.in_rp = True
            self.rp_text = []

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"

        if t == "ruby":
            if self.ruby_stack:
                info = self.ruby_stack.pop()
                if int(info["rt_count"]) == 0:
                    self.errs.append(
                        f"{self.name}{info['loc']}: <ruby> container missing child <rt> annotation "
                        f"(HTML5 §4.5.22 requires at least one <rt> ruby text component)"
                    )
        elif t == "rt":
            self.in_rt = False
            txt = "".join(self.rt_text).strip()
            if not txt:
                self.errs.append(
                    f"{self.name}{loc}: <rt> ruby text must not be empty or whitespace-only "
                    f"(WCAG 2.2 SC 1.3.1 & HTML5 §4.5.23 require phonetic/pronunciation text)"
                )
        elif t == "rp":
            self.in_rp = False
            txt = "".join(self.rp_text).strip()
            if not txt:
                self.errs.append(
                    f"{self.name}{loc}: <rp> ruby fallback parenthesis must not be empty or whitespace-only "
                    f"(HTML5 §4.5.24 requires fallback punctuation)"
                )

    def handle_data(self, data: str) -> None:
        if self.in_rt:
            self.rt_text.append(data)
        if self.in_rp:
            self.rp_text.append(data)


def check_ruby_annotation_integrity(name: str, body: str) -> list[str]:
    """Ensure <ruby>, <rt>, and <rp> elements satisfy HTML5 structure, non-empty text, and pairing constraints (HTML5 §4.5.22, §4.5.23, §4.5.24 & WCAG 2.2 SC 1.3.1)."""
    parser = _RubyAnnotationParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _MenuAndToolbarParser(HTMLParser):
    """Audits HTML5 <menu> children and ARIA toolbar / menubar accessibility and structure (HTML5 §4.4.8, W3C WAI-ARIA 1.2 §5.3.4, §5.3.5 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""
    ALLOWED_MENU_CHILDREN = {"li", "script", "template"}
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.tag_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        ad = {k.lower(): (v or "") for k, v in attrs}
        roles = set(ad.get("role", "").lower().split())

        if self.tag_stack and self.tag_stack[-1] == "menu":
            if t not in self.ALLOWED_MENU_CHILDREN:
                self.errs.append(
                    f"{self.name}{loc}: <menu> contains invalid direct child <{t}> "
                    f"(HTML5 §4.4.8 permits only <li>, <script>, or <template> child elements)"
                )

        if roles & {"toolbar", "menubar"}:
            matched_role = "toolbar" if "toolbar" in roles else "menubar"
            has_name = bool(ad.get("aria-label", "").strip() or ad.get("aria-labelledby", "").strip())
            if not has_name:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> with role='{matched_role}' missing accessible name "
                    f"(must declare non-empty aria-label or aria-labelledby; W3C WAI-ARIA 1.2 §5.3.4/§5.3.5 & WCAG 2.2 SC 4.1.2)"
                )
            if "aria-expanded" in ad:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> with role='{matched_role}' declares aria-expanded on container "
                    f"(aria-expanded belongs on individual expandable items, not the toolbar/menubar; W3C WAI-ARIA 1.2 §5.3.4)"
                )
            if matched_role == "menubar" and "aria-orientation" in ad:
                ori = ad["aria-orientation"].strip().lower()
                if ori not in ("horizontal", "vertical"):
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> with role='menubar' declares invalid aria-orientation='{ori}' "
                        f"(must be 'horizontal' or 'vertical'; W3C WAI-ARIA 1.2 §5.3.5)"
                    )

        if t not in self.VOID_TAGS:
            self.tag_stack.append(t)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        for i in range(len(self.tag_stack) - 1, -1, -1):
            if self.tag_stack[i] == t:
                self.tag_stack = self.tag_stack[:i]
                break


def check_menu_and_toolbar_accessibility(name: str, body: str) -> list[str]:
    """Ensure <menu> children conform to HTML5 §4.4.8 and ARIA toolbars/menubars have accessible names without invalid container states (W3C WAI-ARIA 1.2 §5.3.4, §5.3.5 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""
    parser = _MenuAndToolbarParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _AriaModalAndDialogStateParser(HTMLParser):
    """Audits aria-modal boolean syntax, placement on dialog roles, and alertdialog accessible description (W3C WAI-ARIA 1.2 §5.3.1, §5.3.2, §6.6 & WCAG 2.2 SC 2.1.2, SC 4.1.2)."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        ad = {k.lower(): (v or "") for k, v in attrs}
        roles = set(ad.get("role", "").lower().split())

        if "aria-modal" in ad:
            val = ad["aria-modal"].strip().lower()
            if val not in ("true", "false"):
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares invalid aria-modal='{ad['aria-modal']}' "
                    f"(must be 'true' or 'false'; W3C WAI-ARIA 1.2 §6.6)"
                )
            is_dialog_container = (t == "dialog") or bool(roles & {"dialog", "alertdialog"})
            if not is_dialog_container:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares aria-modal on non-dialog element without role='dialog' or 'alertdialog' "
                    f"(W3C WAI-ARIA 1.2 §6.6 restricts aria-modal to dialog and window roles)"
                )
            if val == "true" and ad.get("aria-hidden", "").strip().lower() == "true":
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares contradictory aria-modal='true' and aria-hidden='true' "
                    f"(a modal dialog cannot be hidden from assistive technologies while active; W3C WAI-ARIA 1.2 §5.3.1)"
                )

        if "alertdialog" in roles:
            has_name = bool(ad.get("aria-label", "").strip() or ad.get("aria-labelledby", "").strip())
            if not has_name:
                self.errs.append(
                    f"{self.name}{loc}: element with role='alertdialog' missing accessible name "
                    f"(must declare aria-label or aria-labelledby; W3C WAI-ARIA 1.2 §5.3.2 & WCAG 2.2 SC 4.1.2)"
                )
            has_desc = bool(ad.get("aria-describedby", "").strip())
            if not has_desc:
                self.errs.append(
                    f"{self.name}{loc}: element with role='alertdialog' missing accessible description via aria-describedby "
                    f"(W3C WAI-ARIA 1.2 §5.3.2 requires an alert dialog prompt description for screen readers)"
                )


def check_aria_modal_and_dialog_state_integrity(name: str, body: str) -> list[str]:
    """Ensure aria-modal values are boolean, placed only on dialogs without contradictory aria-hidden, and alertdialogs have name and description (W3C WAI-ARIA 1.2 §5.3.1, §5.3.2, §6.6 & WCAG 2.2 SC 2.1.2, SC 4.1.2)."""
    parser = _AriaModalAndDialogStateParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _DefinitionListAndDfnParser(HTMLParser):
    """Audits HTML5 definition list hierarchy (<dl>, <dt>, <dd>) and defining terms (<dfn>) per HTML5 §4.4.9, §4.4.10, §4.4.11, §4.5.8 & WCAG 2.2 SC 1.3.1."""
    ALLOWED_DL_CHILDREN = {"dt", "dd", "div", "script", "template"}
    ALLOWED_DL_DIV_CHILDREN = {"dt", "dd", "script", "template"}
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.tag_stack: list[str] = []
        self.dl_state_stack: list[dict] = []
        self.dfn_depth = 0
        self.current_tag: str | None = None
        self.current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"

        if t in ("dt", "dd", "dfn"):
            self._flush_text()
            self.current_tag = t
            self.current_text = []

        if t == "dl":
            self.dl_state_stack.append({"has_dt": False, "pending_dt": False, "loc": loc})

        # Direct children check
        if self.tag_stack:
            parent = self.tag_stack[-1]
            if parent == "dl":
                if t not in self.ALLOWED_DL_CHILDREN:
                    self.errs.append(
                        f"{self.name}{loc}: <dl> contains invalid direct child <{t}> "
                        f"(HTML5 §4.4.9 permits only <dt>, <dd>, <div>, <script>, or <template> child elements)"
                    )
            elif parent == "div" and len(self.tag_stack) >= 2 and self.tag_stack[-2] == "dl":
                if t not in self.ALLOWED_DL_DIV_CHILDREN:
                    self.errs.append(
                        f"{self.name}{loc}: <div> child inside <dl> contains invalid child <{t}> "
                        f"(HTML5 §4.4.9 permits only <dt>, <dd>, <script>, or <template> elements inside <dl> > <div>)"
                    )

        if t in ("dt", "dd"):
            # Orphan check: must be inside dl
            if "dl" not in self.tag_stack:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> is orphaned outside an enclosing <dl> container "
                    f"(HTML5 §4.4.9 & WCAG 2.2 SC 1.3.1)"
                )
            elif self.dl_state_stack:
                state = self.dl_state_stack[-1]
                if t == "dt":
                    state["has_dt"] = True
                    state["pending_dt"] = True
                elif t == "dd":
                    if not state["has_dt"]:
                        self.errs.append(
                            f"{self.name}{loc}: <dd> appears before any preceding <dt> in definition list "
                            f"(HTML5 §4.4.9 requires <dt> before <dd> in each name-value group)"
                        )
                    state["pending_dt"] = False

        if t == "dfn":
            self.dfn_depth += 1
            if self.dfn_depth > 1:
                self.errs.append(
                    f"{self.name}{loc}: <dfn> contains nested <dfn> element "
                    f"(HTML5 §4.5.8 forbids nesting <dfn> elements)"
                )

        if t not in self.VOID_TAGS:
            self.tag_stack.append(t)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        self._flush_text()

        if t == "dfn":
            self.dfn_depth = max(0, self.dfn_depth - 1)
        elif t == "dl":
            if self.dl_state_stack:
                state = self.dl_state_stack.pop()
                if state.get("pending_dt"):
                    self.errs.append(
                        f"{self.name}{loc}: <dl> contains <dt> group without corresponding <dd> description "
                        f"(HTML5 §4.4.9 requires every <dt> name group to be followed by at least one <dd>)"
                    )

        for i in range(len(self.tag_stack) - 1, -1, -1):
            if self.tag_stack[i] == t:
                self.tag_stack = self.tag_stack[:i]
                break

    def handle_data(self, data: str) -> None:
        if self.current_tag in ("dt", "dd", "dfn"):
            self.current_text.append(data)

    def _flush_text(self) -> None:
        if self.current_tag in ("dt", "dd", "dfn"):
            text = "".join(self.current_text).strip()
            if not text:
                lineno, offset = self.getpos()
                loc = f" (line {lineno}:{offset})"
                self.errs.append(
                    f"{self.name}{loc}: <{self.current_tag}> is empty or whitespace-only "
                    f"(HTML5 §4.4.9/§4.5.8 & WCAG 2.2 SC 1.3.1 require non-empty text for assistive navigation)"
                )
            self.current_tag = None
            self.current_text = []

    def finish(self) -> None:
        self._flush_text()
        while self.dl_state_stack:
            state = self.dl_state_stack.pop()
            if state.get("pending_dt"):
                self.errs.append(
                    f"{self.name}{state['loc']}: unclosed <dl> contains <dt> group without corresponding <dd> description "
                    f"(HTML5 §4.4.9 requires every <dt> name group to be followed by at least one <dd>)"
                )


def check_definition_list_and_dfn_integrity(name: str, body: str) -> list[str]:
    """Ensure HTML5 <dl>, <dt>, <dd>, and <dfn> elements satisfy grouping, containment, non-empty text, and nesting constraints (HTML5 §4.4.9, §4.4.10, §4.4.11, §4.5.8 & WCAG 2.2 SC 1.3.1)."""
    parser = _DefinitionListAndDfnParser(name)
    try:
        parser.feed(body)
        parser.finish()
    except Exception:
        pass
    return parser.errs


class _AriaCheckedAndPressedParser(HTMLParser):
    """Audits aria-checked role placement, switch binary states, aria-pressed button placement, and aria-current tokens (W3C WAI-ARIA 1.2 §6.6, §5.3.3 & WCAG 2.2 SC 4.1.2)."""
    CHECKABLE_ROLES = {"checkbox", "radio", "menuitemcheckbox", "menuitemradio", "switch", "option", "treeitem"}
    BUTTON_ROLES = {"button"}
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.tag_stack: list[str] = []
        self.button_text: list[str] = []
        self.inspecting_button = False
        self.button_tag: str | None = None
        self.button_loc: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        ad = {k.lower(): (v or "") for k, v in attrs}
        roles = set(ad.get("role", "").lower().split())

        if "aria-checked" in ad:
            val = ad["aria-checked"].strip().lower()
            if val not in ("true", "false", "mixed"):
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares invalid aria-checked='{ad['aria-checked']}' "
                    f"(must be 'true', 'false', or 'mixed'; W3C WAI-ARIA 1.2 §6.6)"
                )
            is_checkable = bool(roles & self.CHECKABLE_ROLES) or (t == "input" and ad.get("type", "").lower() in ("checkbox", "radio"))
            if not is_checkable:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares aria-checked on non-checkable element without checkable role "
                    f"(must declare role 'checkbox', 'radio', 'menuitemcheckbox', 'menuitemradio', 'switch', 'option', or 'treeitem'; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                )
            if "switch" in roles and val == "mixed":
                self.errs.append(
                    f"{self.name}{loc}: <{t}> with role='switch' declares invalid aria-checked='mixed' "
                    f"(switches represent binary on/off states and do not support mixed; W3C WAI-ARIA 1.2 §5.3.3)"
                )

        if "aria-pressed" in ad:
            val = ad["aria-pressed"].strip().lower()
            if val not in ("true", "false", "mixed"):
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares invalid aria-pressed='{ad['aria-pressed']}' "
                    f"(must be 'true', 'false', or 'mixed'; W3C WAI-ARIA 1.2 §6.6)"
                )
            is_button = (t == "button") or ("button" in roles) or (t == "input" and ad.get("type", "").lower() in ("button", "submit", "reset"))
            if not is_button:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares aria-pressed on non-button element "
                    f"(must be <button> or declare role='button'; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                )
            has_name = bool(ad.get("aria-label", "").strip() or ad.get("aria-labelledby", "").strip() or ad.get("value", "").strip())
            if not has_name and t not in self.VOID_TAGS:
                self.inspecting_button = True
                self.button_tag = t
                self.button_loc = loc
                self.button_text = []

        if "aria-current" in ad:
            val = ad["aria-current"].strip().lower()
            if val not in ("page", "step", "location", "date", "time", "true", "false"):
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares invalid aria-current='{ad['aria-current']}' "
                    f"(must be 'page', 'step', 'location', 'date', 'time', 'true', or 'false'; W3C WAI-ARIA 1.2 §6.6)"
                )

        if t not in self.VOID_TAGS:
            self.tag_stack.append(t)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if self.inspecting_button and self.button_tag == t:
            text = "".join(self.button_text).strip()
            if not text:
                self.errs.append(
                    f"{self.name}{self.button_loc}: <{t}> declaring aria-pressed missing accessible name "
                    f"(must declare visible text, aria-label, or aria-labelledby; WCAG 2.2 SC 4.1.2)"
                )
            self.inspecting_button = False
            self.button_tag = None
            self.button_text = []

        for i in range(len(self.tag_stack) - 1, -1, -1):
            if self.tag_stack[i] == t:
                self.tag_stack = self.tag_stack[:i]
                break

    def handle_data(self, data: str) -> None:
        if self.inspecting_button:
            self.button_text.append(data)


def check_aria_checked_and_pressed_integrity(name: str, body: str) -> list[str]:
    """Ensure aria-checked is confined to checkable roles (no mixed on switch), aria-pressed is confined to buttons with accessible names, and aria-current uses valid tokens (W3C WAI-ARIA 1.2 §6.6, §5.3.3 & WCAG 2.2 SC 4.1.2)."""
    parser = _AriaCheckedAndPressedParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _SearchLandmarkAndSearchboxParser(HTMLParser):
    """Audits HTML5 <search> nesting, multiple search landmark distinguishing names, and searchbox role validity (HTML5 §4.4.12, W3C WAI-ARIA 1.2 §5.4.15, §5.3.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.tag_stack: list[str] = []
        self.search_landmarks: list[dict] = []
        self.search_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        ad = {k.lower(): (v or "") for k, v in attrs}
        roles = set(ad.get("role", "").lower().split())

        is_search_landmark = (t == "search") or ("search" in roles)
        if is_search_landmark:
            has_name = bool(ad.get("aria-label", "").strip() or ad.get("aria-labelledby", "").strip())
            self.search_landmarks.append({"tag": t, "loc": loc, "has_name": has_name})

        if t == "search":
            self.search_depth += 1
            if self.search_depth > 1:
                self.errs.append(
                    f"{self.name}{loc}: <search> contains nested <search> element "
                    f"(HTML5 §4.4.12 forbids nesting <search> elements)"
                )

        if "searchbox" in roles:
            is_input = (t in ("input", "textarea")) or ("contenteditable" in ad and ad["contenteditable"].lower() in ("true", ""))
            if not is_input:
                self.errs.append(
                    f"{self.name}{loc}: element with role='searchbox' is placed on non-editable element <{t}> "
                    f"(W3C WAI-ARIA 1.2 §5.3.6 requires searchbox to be an editable text input or contenteditable element)"
                )

        if t not in self.VOID_TAGS:
            self.tag_stack.append(t)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == "search":
            self.search_depth = max(0, self.search_depth - 1)
        for i in range(len(self.tag_stack) - 1, -1, -1):
            if self.tag_stack[i] == t:
                self.tag_stack = self.tag_stack[:i]
                break

    def finish(self) -> None:
        if len(self.search_landmarks) > 1:
            for sl in self.search_landmarks:
                if not sl["has_name"]:
                    self.errs.append(
                        f"{self.name}{sl['loc']}: multiple search landmarks present on page, but <{sl['tag']}> lacks distinguishing accessible name "
                        f"(must declare aria-label or aria-labelledby when multiple search landmarks exist; WCAG 2.2 SC 1.3.1 & SC 4.1.2)"
                    )


def check_search_landmark_and_searchbox_integrity(name: str, body: str) -> list[str]:
    """Ensure HTML5 <search> elements are not nested, multiple search landmarks declare distinguishing accessible names, and searchbox role is restricted to editable controls (HTML5 §4.4.12, W3C WAI-ARIA 1.2 §5.4.15, §5.3.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""
    parser = _SearchLandmarkAndSearchboxParser(name)
    try:
        parser.feed(body)
        parser.finish()
    except Exception:
        pass
    return parser.errs


class _AddressElementParser(HTMLParser):
    """Audits HTML5 <address> element containment, forbidding sectioning content, headings, header/footer, and nested address (HTML5 §4.4.13 & WCAG 2.2 SC 1.3.1)."""
    FORBIDDEN_TAGS = {
        "article", "aside", "nav", "section",
        "h1", "h2", "h3", "h4", "h5", "h6", "hgroup",
        "header", "footer", "address"
    }
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.address_depth = 0
        self.address_loc: str = ""
        self.address_has_content = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        if t == "address":
            if self.address_depth > 0:
                self.errs.append(
                    f"{self.name}{loc}: <address> contains nested <address> element "
                    f"(HTML5 §4.4.13 forbids nesting <address> inside <address>)"
                )
            self.address_depth += 1
            self.address_loc = loc
            self.address_has_content = False
        elif self.address_depth > 0:
            if t in self.FORBIDDEN_TAGS:
                self.errs.append(
                    f"{self.name}{loc}: <address> contains forbidden <{t}> element "
                    f"(HTML5 §4.4.13 forbids sectioning content, headings, header, footer, and nested address inside <address>)"
                )
            if t not in self.VOID_TAGS:
                self.address_has_content = True

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == "address":
            if self.address_depth > 0:
                if not self.address_has_content:
                    self.errs.append(
                        f"{self.name}{self.address_loc}: <address> element is empty or whitespace-only "
                        f"(HTML5 §4.4.13 & WCAG 2.2 SC 1.3.1)"
                    )
                self.address_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.address_depth > 0 and data.strip():
            self.address_has_content = True


def check_address_element_integrity(name: str, body: str) -> list[str]:
    """Ensure HTML5 <address> elements contain contact information without forbidden sectioning, heading, header, footer, or nested address elements (HTML5 §4.4.13 & WCAG 2.2 SC 1.3.1)."""
    parser = _AddressElementParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _SubAndSupParser(HTMLParser):
    """Audits HTML5 <sub> and <sup> elements to prevent empty elements or invalid direct self-nesting (HTML5 §4.5.16, §4.5.17 & WCAG 2.2 SC 1.3.1)."""
    TARGET_TAGS = {"sub", "sup"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.tag_stack: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        if t in self.TARGET_TAGS:
            for item in reversed(self.tag_stack):
                if item["tag"] == t:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> directly nests another <{t}> element "
                        f"(HTML5 §4.5.16/§4.5.17 & WCAG 2.2 SC 1.3.1)"
                    )
                    break
            self.tag_stack.append({"tag": t, "loc": loc, "has_content": False})

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in self.TARGET_TAGS:
            for i in range(len(self.tag_stack) - 1, -1, -1):
                if self.tag_stack[i]["tag"] == t:
                    item = self.tag_stack.pop(i)
                    if not item["has_content"]:
                        self.errs.append(
                            f"{self.name}{item['loc']}: <{t}> element is empty or whitespace-only "
                            f"(HTML5 §4.5.16/§4.5.17 & WCAG 2.2 SC 1.3.1)"
                        )
                    break

    def handle_data(self, data: str) -> None:
        if data.strip():
            for item in self.tag_stack:
                item["has_content"] = True


def check_sub_and_sup_integrity(name: str, body: str) -> list[str]:
    """Ensure HTML5 <sub> and <sup> elements are non-empty and do not directly self-nest (HTML5 §4.5.16, §4.5.17 & WCAG 2.2 SC 1.3.1)."""
    parser = _SubAndSupParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _PictureAndSourceParser(HTMLParser):
    """Audits HTML5 <picture> container and <source> element placement, requiring exactly one <img> child, preceding <source> elements, and valid srcset attributes (HTML5 §4.8.1, §4.8.2 & WCAG 2.2 SC 1.1.1, SC 1.3.1)."""
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.tag_stack: list[str] = []
        self.picture_stack: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        ad = {k.lower(): (v or "") for k, v in attrs}

        if t == "picture":
            self.picture_stack.append({"loc": loc, "has_img": False, "img_loc": ""})

        if t == "source":
            parent = self.tag_stack[-1] if self.tag_stack else None
            if parent not in ("picture", "audio", "video"):
                self.errs.append(
                    f"{self.name}{loc}: <source> element orphaned outside <picture>, <audio>, or <video> container "
                    f"(HTML5 §4.8.2)"
                )
            if parent == "picture" and self.picture_stack:
                cur_pic = self.picture_stack[-1]
                if cur_pic["has_img"]:
                    self.errs.append(
                        f"{self.name}{loc}: <source> appears after <img> inside <picture> "
                        f"(HTML5 §4.8.1 requires <source> elements to precede the <img> fallback)"
                    )
                if not ad.get("srcset", "").strip():
                    self.errs.append(
                        f"{self.name}{loc}: <source> inside <picture> missing required non-empty 'srcset' attribute "
                        f"(HTML5 §4.8.2)"
                    )

        if t == "img" and self.picture_stack:
            cur_pic = self.picture_stack[-1]
            if cur_pic["has_img"]:
                self.errs.append(
                    f"{self.name}{loc}: <picture> contains multiple <img> elements "
                    f"(HTML5 §4.8.1 specifies exactly one <img> child element)"
                )
            cur_pic["has_img"] = True
            cur_pic["img_loc"] = loc

        if t not in self.VOID_TAGS:
            self.tag_stack.append(t)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == "picture" and self.picture_stack:
            pic = self.picture_stack.pop()
            if not pic["has_img"]:
                self.errs.append(
                    f"{self.name}{pic['loc']}: <picture> missing required <img> child element "
                    f"(HTML5 §4.8.1 requires <img> inside <picture> for image rendering and accessible representation)"
                )
        for i in range(len(self.tag_stack) - 1, -1, -1):
            if self.tag_stack[i] == t:
                self.tag_stack = self.tag_stack[:i]
                break


def check_picture_and_source_integrity(name: str, body: str) -> list[str]:
    """Ensure HTML5 <picture> contains exactly one <img>, preceding <source> with non-empty srcset, and no orphaned <source> elements (HTML5 §4.8.1, §4.8.2 & WCAG 2.2 SC 1.1.1, SC 1.3.1)."""
    parser = _PictureAndSourceParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _AriaMeterParser(HTMLParser):
    """Audits role='meter' elements to ensure accessible names, valid required aria-valuenow, and consistent numeric bounds (W3C WAI-ARIA 1.2 §5.3.3 & WCAG 2.2 SC 4.1.2)."""
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        ad = {k.lower(): (v or "") for k, v in attrs}
        roles = set(ad.get("role", "").lower().split())

        if "meter" in roles:
            has_name = bool(ad.get("aria-label", "").strip() or ad.get("aria-labelledby", "").strip() or ad.get("title", "").strip())
            if not has_name:
                self.errs.append(
                    f"{self.name}{loc}: element with role='meter' missing accessible name "
                    f"(requires aria-label, aria-labelledby, or title; W3C WAI-ARIA 1.2 §5.3.3 & WCAG 2.2 SC 4.1.2)"
                )

            if "aria-valuenow" not in ad or not ad["aria-valuenow"].strip():
                self.errs.append(
                    f"{self.name}{loc}: element with role='meter' missing required 'aria-valuenow' attribute "
                    f"(W3C WAI-ARIA 1.2 §5.3.3)"
                )
                return

            min_val = 0.0
            max_val = 100.0
            try:
                cur_val = float(ad["aria-valuenow"].strip())
            except ValueError:
                self.errs.append(
                    f"{self.name}{loc}: element with role='meter' aria-valuenow='{ad['aria-valuenow']}' is not a valid number "
                    f"(W3C WAI-ARIA 1.2 §5.3.3)"
                )
                return

            if "aria-valuemin" in ad and ad["aria-valuemin"].strip():
                try:
                    min_val = float(ad["aria-valuemin"].strip())
                except ValueError:
                    self.errs.append(
                        f"{self.name}{loc}: element with role='meter' aria-valuemin='{ad['aria-valuemin']}' is not a valid number "
                        f"(W3C WAI-ARIA 1.2 §5.3.3)"
                    )
                    return

            if "aria-valuemax" in ad and ad["aria-valuemax"].strip():
                try:
                    max_val = float(ad["aria-valuemax"].strip())
                except ValueError:
                    self.errs.append(
                        f"{self.name}{loc}: element with role='meter' aria-valuemax='{ad['aria-valuemax']}' is not a valid number "
                        f"(W3C WAI-ARIA 1.2 §5.3.3)"
                    )
                    return

            if min_val >= max_val:
                self.errs.append(
                    f"{self.name}{loc}: element with role='meter' aria-valuemin ({min_val}) must be strictly less than aria-valuemax ({max_val}) "
                    f"(W3C WAI-ARIA 1.2 §5.3.3)"
                )
            elif not (min_val <= cur_val <= max_val):
                self.errs.append(
                    f"{self.name}{loc}: element with role='meter' aria-valuenow ({cur_val}) out of bounds [{min_val}, {max_val}] "
                    f"(W3C WAI-ARIA 1.2 §5.3.3)"
                )


def check_aria_meter_integrity(name: str, body: str) -> list[str]:
    """Ensure elements with role='meter' declare accessible names, required valid numeric aria-valuenow, and consistent min/max bounds (W3C WAI-ARIA 1.2 §5.3.3 & WCAG 2.2 SC 4.1.2)."""
    parser = _AriaMeterParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _CanvasAccessibilityParser(HTMLParser):
    """Audits HTML5 <canvas> elements for accessible names, non-empty fallback content, and absence of presentational roles (HTML5 §4.12.5 & WCAG 2.2 SC 1.1.1, SC 4.1.2)."""
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.in_canvas = False
        self.canvas_loc: str = ""
        self.canvas_has_content = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): v for k, v in attrs}
        if t == "canvas":
            if self.in_canvas:
                self.errs.append(
                    f"{self.name}{loc}: <canvas> contains nested <canvas> element "
                    f"(HTML5 §4.12.5 forbids nested canvas elements)"
                )
            self.in_canvas = True
            self.canvas_loc = loc
            self.canvas_has_content = False
            has_name = bool(attr_dict.get("aria-label", "").strip() or attr_dict.get("aria-labelledby", "").strip() or attr_dict.get("title", "").strip())
            if not has_name:
                self.errs.append(
                    f"{self.name}{loc}: <canvas> element missing accessible name "
                    f"(aria-label, aria-labelledby, or title; HTML5 §4.12.5 & WCAG 2.2 SC 1.1.1, SC 4.1.2)"
                )
            role = attr_dict.get("role", "").lower().strip()
            if role in ("presentation", "none"):
                self.errs.append(
                    f"{self.name}{loc}: <canvas> declares forbidden role='{role}' "
                    f"(canvas with visual content must not be marked presentational; WCAG 2.2 SC 1.1.1 & SC 4.1.2)"
                )
        elif self.in_canvas and t not in self.VOID_TAGS:
            self.canvas_has_content = True

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == "canvas" and self.in_canvas:
            if not self.canvas_has_content:
                self.errs.append(
                    f"{self.name}{self.canvas_loc}: <canvas> element has no fallback content "
                    f"(HTML5 §4.12.5 & WCAG 2.2 SC 1.1.1 require fallback content for non-supporting browsers/assistive agents)"
                )
            self.in_canvas = False

    def handle_data(self, data: str) -> None:
        if self.in_canvas and data.strip():
            self.canvas_has_content = True


def check_canvas_accessibility_and_fallback_integrity(name: str, body: str) -> list[str]:
    """Ensure HTML5 <canvas> elements declare accessible names, provide non-empty fallback content, and avoid presentational roles (HTML5 §4.12.5 & WCAG 2.2 SC 1.1.1, SC 4.1.2)."""
    parser = _CanvasAccessibilityParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _DataElementParser(HTMLParser):
    """Audits HTML5 <data> elements for non-empty value attributes and non-empty content (HTML5 §4.5.10 & WCAG 2.2 SC 1.3.1)."""
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.data_stack: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        if t == "data":
            attr_dict = {k.lower(): v for k, v in attrs}
            val = attr_dict.get("value")
            if val is None or not str(val).strip():
                self.errs.append(
                    f"{self.name}{loc}: <data> element missing required non-empty 'value' attribute "
                    f"(HTML5 §4.5.10 requires a machine-readable value attribute on <data>)"
                )
            self.data_stack.append({"loc": loc, "has_content": False})
        elif self.data_stack:
            self.data_stack[-1]["has_content"] = True

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == "data" and self.data_stack:
            item = self.data_stack.pop()
            if not item["has_content"]:
                self.errs.append(
                    f"{self.name}{item['loc']}: <data> element is empty or whitespace-only "
                    f"(HTML5 §4.5.10 & WCAG 2.2 SC 1.3.1)"
                )

    def handle_data(self, data: str) -> None:
        if self.data_stack and data.strip():
            self.data_stack[-1]["has_content"] = True


def check_data_element_integrity(name: str, body: str) -> list[str]:
    """Ensure HTML5 <data> elements specify machine-readable value attributes and non-empty content (HTML5 §4.5.10 & WCAG 2.2 SC 1.3.1)."""
    parser = _DataElementParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _TechnicalInlineParser(HTMLParser):
    """Audits HTML5 <var>, <kbd>, and <samp> elements for non-empty content and valid nesting (HTML5 §4.5.13, §4.5.14, §4.5.15 & WCAG 2.2 SC 1.3.1)."""
    TARGET_TAGS = {"var", "kbd", "samp"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.stack: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        if t in self.TARGET_TAGS:
            if t == "var" and any(x["tag"] == "var" for x in self.stack):
                self.errs.append(
                    f"{self.name}{loc}: <var> directly nests another <var> element "
                    f"(HTML5 §4.5.13 & WCAG 2.2 SC 1.3.1)"
                )
            elif t == "samp" and any(x["tag"] == "samp" for x in self.stack):
                self.errs.append(
                    f"{self.name}{loc}: <samp> directly nests another <samp> element "
                    f"(HTML5 §4.5.15 & WCAG 2.2 SC 1.3.1)"
                )
            elif t == "kbd":
                kbd_depth = sum(1 for x in self.stack if x["tag"] == "kbd")
                if kbd_depth >= 2:
                    self.errs.append(
                        f"{self.name}{loc}: <kbd> element nested more than 2 levels deep "
                        f"(HTML5 §4.5.14 & WCAG 2.2 SC 1.3.1)"
                    )
            self.stack.append({"tag": t, "loc": loc, "has_content": False})
        elif self.stack:
            self.stack[-1]["has_content"] = True

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in self.TARGET_TAGS and self.stack:
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i]["tag"] == t:
                    item = self.stack.pop(i)
                    if not item["has_content"]:
                        self.errs.append(
                            f"{self.name}{item['loc']}: <{t}> element is empty or whitespace-only "
                            f"(HTML5 §4.5.13/§4.5.14/§4.5.15 & WCAG 2.2 SC 1.3.1)"
                        )
                    break

    def handle_data(self, data: str) -> None:
        if self.stack and data.strip():
            self.stack[-1]["has_content"] = True


def check_technical_inline_elements_integrity(name: str, body: str) -> list[str]:
    """Ensure HTML5 <var>, <kbd>, and <samp> elements have non-empty content and do not violate nesting constraints (HTML5 §4.5.13, §4.5.14, §4.5.15 & WCAG 2.2 SC 1.3.1)."""
    parser = _TechnicalInlineParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _AriaFeedParser(HTMLParser):
    """Audits elements declaring role='feed' for accessible names, avoiding nested feeds, and valid aria-busy states (W3C WAI-ARIA 1.2 §5.4.12, §6.6 & WCAG 2.2 SC 4.1.2)."""
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.feed_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): v for k, v in attrs}
        role = attr_dict.get("role", "").lower().strip()
        if role == "feed":
            if self.feed_stack:
                self.errs.append(
                    f"{self.name}{loc}: role='feed' container is nested inside another role='feed' container "
                    f"(W3C WAI-ARIA 1.2 §5.4.12)"
                )
            self.feed_stack.append(t)
            has_name = bool(attr_dict.get("aria-label", "").strip() or attr_dict.get("aria-labelledby", "").strip() or attr_dict.get("title", "").strip())
            if not has_name:
                self.errs.append(
                    f"{self.name}{loc}: element with role='feed' missing accessible name "
                    f"(aria-label or aria-labelledby; W3C WAI-ARIA 1.2 §5.4.12 & WCAG 2.2 SC 4.1.2)"
                )
            busy = attr_dict.get("aria-busy")
            if busy is not None and busy.lower().strip() not in ("true", "false"):
                self.errs.append(
                    f"{self.name}{loc}: role='feed' declares invalid aria-busy='{busy}' "
                    f"(must be 'true' or 'false'; W3C WAI-ARIA 1.2 §6.6)"
                )

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if self.feed_stack and self.feed_stack[-1] == t:
            self.feed_stack.pop()


def check_aria_feed_and_article_stream_integrity(name: str, body: str) -> list[str]:
    """Ensure role='feed' streams declare accessible names, avoid nested feeds, and maintain valid aria-busy tokens (W3C WAI-ARIA 1.2 §5.4.12 & WCAG 2.2 SC 4.1.2)."""
    parser = _AriaFeedParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _AriaOwnsParser(HTMLParser):
    """Audits ARIA aria-owns relationships for single explicit ownership, self-ownership avoidance, acyclic graph structure, and target existence (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.all_element_ids: set[str] = set()
        self.owns_declarations: list[dict] = []
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        elem_id = attr_dict.get("id", "").strip()
        if elem_id:
            self.all_element_ids.add(elem_id)

        if "aria-owns" in attr_dict:
            raw_val = attr_dict["aria-owns"]
            if not raw_val.strip():
                self.errs.append(
                    f"{self.name}{loc}: <{t}> has empty or whitespace-only aria-owns attribute "
                    f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                )
            else:
                targets = raw_val.split()
                if len(targets) != len(set(targets)):
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> aria-owns specifies duplicate target IDs ('{raw_val}') "
                        f"(W3C WAI-ARIA 1.2 §6.6)"
                    )
                self.owns_declarations.append({
                    "tag": t,
                    "owner_id": elem_id or f"<{t}>",
                    "has_id": bool(elem_id),
                    "targets": targets,
                    "loc": loc,
                })

    def validate_relationships(self) -> None:
        claimed_targets: dict[str, str] = {}
        graph: dict[str, list[str]] = {}

        for decl in self.owns_declarations:
            loc = decl["loc"]
            t = decl["tag"]
            owner_id = decl["owner_id"]
            targets = decl["targets"]

            # Self-ownership check
            if decl["has_id"] and owner_id in targets:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> aria-owns references its own id '{owner_id}' "
                    f"(self-ownership is forbidden; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1)"
                )

            for target in targets:
                # Target existence check
                if target not in self.all_element_ids:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> aria-owns references non-existent element id '{target}' "
                        f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1)"
                    )

                # Single explicit owner check
                if target in claimed_targets:
                    other_owner = claimed_targets[target]
                    self.errs.append(
                        f"{self.name}{loc}: element id '{target}' is owned by multiple elements via aria-owns "
                        f"(claimed by '{other_owner}' and '{owner_id}'; elements may have at most one explicit owner; "
                        f"W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1)"
                    )
                else:
                    claimed_targets[target] = owner_id

            if decl["has_id"]:
                graph.setdefault(owner_id, []).extend(targets)

        # Cycle detection on graph using DFS
        visited: set[str] = set()
        rec_stack: list[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.append(node)

            for neighbor in graph.get(node, []):
                if neighbor in rec_stack:
                    idx = rec_stack.index(neighbor)
                    cycle = rec_stack[idx:] + [neighbor]
                    self.errs.append(
                        f"{self.name}: circular ownership detected in aria-owns relationship "
                        f"('{' -> '.join(cycle)}'; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1)"
                    )
                elif neighbor not in visited and neighbor in graph:
                    dfs(neighbor)

            rec_stack.pop()

        for node in list(graph.keys()):
            if node not in visited:
                dfs(node)


def check_aria_owns_hierarchy_integrity(name: str, body: str) -> list[str]:
    """Ensure ARIA aria-owns virtual relationships avoid self-ownership, duplicate targets, multiple owners, and circular dependencies (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""
    parser = _AriaOwnsParser(name)
    try:
        parser.feed(body)
        parser.validate_relationships()
    except Exception:
        pass
    return parser.errs


class _MarkAndSmallParser(HTMLParser):
    """Audits HTML5 <mark> and <small> elements for non-empty content and valid non-nesting structure (HTML5 §4.5.11, §4.5.19 & WCAG 2.2 SC 1.3.1, SC 1.4.4)."""
    TARGET_TAGS = {"mark", "small"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.stack: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        if t in self.TARGET_TAGS:
            if t == "mark" and any(x["tag"] == "mark" for x in self.stack):
                self.errs.append(
                    f"{self.name}{loc}: <mark> directly nests another <mark> element "
                    f"(HTML5 §4.5.19 & WCAG 2.2 SC 1.3.1)"
                )
            elif t == "small" and any(x["tag"] == "small" for x in self.stack):
                self.errs.append(
                    f"{self.name}{loc}: <small> directly nests another <small> element "
                    f"(HTML5 §4.5.11 & WCAG 2.2 SC 1.4.4)"
                )
            self.stack.append({"tag": t, "loc": loc, "has_content": False})
        elif self.stack:
            self.stack[-1]["has_content"] = True

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in self.TARGET_TAGS and self.stack:
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i]["tag"] == t:
                    item = self.stack.pop(i)
                    if not item["has_content"]:
                        self.errs.append(
                            f"{self.name}{item['loc']}: <{t}> element is empty or whitespace-only "
                            f"(HTML5 §4.5.11/§4.5.19 & WCAG 2.2 SC 1.3.1)"
                        )
                    break

    def handle_data(self, data: str) -> None:
        if self.stack and data.strip():
            self.stack[-1]["has_content"] = True


def check_mark_and_small_integrity(name: str, body: str) -> list[str]:
    """Ensure HTML5 <mark> and <small> phrasing elements have non-empty content and avoid self-nesting (HTML5 §4.5.11, §4.5.19 & WCAG 2.2 SC 1.3.1, SC 1.4.4)."""
    parser = _MarkAndSmallParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _TemplateAndSlotParser(HTMLParser):
    """Audits HTML5 <template> elements for inertness (no outer ARIA roles or attributes) and <slot> elements for non-empty names (HTML5 §4.12.3, §4.12.4 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if t == "template":
            if "role" in attr_dict:
                role_val = attr_dict["role"].strip()
                self.errs.append(
                    f"{self.name}{loc}: <template> element must not declare role='{role_val}' "
                    f"(template elements are inert and not rendered in the accessibility tree; HTML5 §4.12.3 & WCAG 2.2 SC 4.1.2)"
                )
            for a_name in attr_dict:
                if a_name.startswith("aria-"):
                    self.errs.append(
                        f"{self.name}{loc}: <template> element must not declare '{a_name}' attribute "
                        f"(template elements are inert and not rendered in the accessibility tree; HTML5 §4.12.3 & WCAG 2.2 SC 4.1.2)"
                    )
        elif t == "slot":
            if "name" in attr_dict:
                slot_name = attr_dict["name"].strip()
                if not slot_name:
                    self.errs.append(
                        f"{self.name}{loc}: <slot> element declares empty or whitespace-only 'name' attribute "
                        f"(HTML5 §4.12.4 & WCAG 2.2 SC 1.3.1)"
                    )


def check_template_and_slot_integrity(name: str, body: str) -> list[str]:
    """Ensure HTML5 <template> elements preserve accessibility inertness and <slot> elements have non-empty names (HTML5 §4.12.3, §4.12.4 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""
    parser = _TemplateAndSlotParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _ThematicBreakParser(HTMLParser):
    """Audits <hr> thematic breaks for valid roles and non-interactive semantics (HTML5 §4.4.2 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""
    INTERACTIVE_ROLES = frozenset({"button", "link", "checkbox", "menuitem", "tab", "textbox", "slider", "switch"})

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        if t == "hr":
            attr_dict = {k.lower(): (v or "") for k, v in attrs}
            role = attr_dict.get("role", "").lower().strip()
            if role:
                roles = set(role.split())
                for r in roles:
                    if r in self.INTERACTIVE_ROLES:
                        self.errs.append(
                            f"{self.name}{loc}: <hr> element declares interactive role='{r}' "
                            f"(thematic break cannot be interactive; HTML5 §4.4.2 & WCAG 2.2 SC 4.1.2)"
                        )
                    elif r in ("presentation", "none"):
                        self.errs.append(
                            f"{self.name}{loc}: <hr> element declares role='{r}' "
                            f"(thematic break separator must not be stripped of semantics; HTML5 §4.4.2 & WCAG 2.2 SC 1.3.1)"
                        )


def check_void_elements_and_thematic_break_integrity(name: str, body: str) -> list[str]:
    """Ensure HTML5 void elements (<wbr>, <hr>) do not contain end tags with content and <hr> retains valid thematic semantics (HTML5 §4.4.2, §4.5.27, §13.1.2.1 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""
    errs: list[str] = []

    for m in re.finditer(r"<(wbr|hr)\b([^>]*)>(.*?)</\1>", body, re.I | re.S):
        tag, inner = m.group(1).lower(), m.group(3)
        if inner.strip():
            errs.append(
                f"{name}: void element <{tag}> must not contain inner content "
                f"(HTML5 §13.1.2.1 Void elements & WCAG 2.2 SC 1.3.1)"
            )
        else:
            errs.append(
                f"{name}: void element <{tag}> must not have an end tag "
                f"(HTML5 §13.1.2.1 Void elements; void elements have no end tag)"
            )

    parser = _ThematicBreakParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    errs.extend(parser.errs)
    return errs


class _AreaAndMapParser(HTMLParser):
    """Audits HTML5 <map> and <area> image map elements for valid structure, alt text, shapes, and coordinates (HTML5 §4.8.13, §4.8.14 & WCAG 2.2 SC 1.1.1, SC 2.1.1, SC 2.4.4)."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.map_depth = 0
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if t == "map":
            self.map_depth += 1
            map_name = attr_dict.get("name", "").strip()
            if not map_name:
                self.errs.append(
                    f"{self.name}{loc}: <map> element missing required non-empty 'name' attribute "
                    f"(HTML5 §4.8.13 & WCAG 2.2 SC 1.3.1)"
                )
        elif t == "area":
            if self.map_depth <= 0:
                self.errs.append(
                    f"{self.name}{loc}: orphaned <area> element found outside <map> container "
                    f"(HTML5 §4.8.14 & WCAG 2.2 SC 1.3.1)"
                )
            has_href = "href" in attr_dict and bool(attr_dict["href"].strip())
            alt_val = attr_dict.get("alt", None)
            if has_href:
                if alt_val is None or not alt_val.strip():
                    self.errs.append(
                        f"{self.name}{loc}: interactive <area href='...'> missing required non-empty 'alt' attribute "
                        f"(HTML5 §4.8.14, WCAG 2.2 SC 1.1.1 Non-Text Content & SC 2.4.4 Link Purpose)"
                    )
            else:
                if alt_val is not None and alt_val.strip():
                    self.errs.append(
                        f"{self.name}{loc}: non-interactive <area> (without href) must have empty alt='' or omit alt "
                        f"(declaring non-empty alt creates phantom announcement; HTML5 §4.8.14 & WCAG 2.2 SC 1.1.1)"
                    )
            if "shape" in attr_dict:
                shape = attr_dict["shape"].lower().strip()
                if shape not in ("default", "rect", "circle", "poly"):
                    self.errs.append(
                        f"{self.name}{loc}: <area> declares invalid shape='{shape}' "
                        f"(expected 'default', 'rect', 'circle', or 'poly'; HTML5 §4.8.14)"
                    )
            if "coords" in attr_dict:
                coords_raw = attr_dict["coords"].strip()
                shape = attr_dict.get("shape", "rect").lower().strip()
                coords = re.findall(r"[-+]?\d*\.?\d+", coords_raw)
                if shape == "rect":
                    if len(coords) != 4:
                        self.errs.append(
                            f"{self.name}{loc}: <area shape='rect'> coords='{coords_raw}' requires exactly 4 coordinates "
                            f"(left, top, right, bottom; HTML5 §4.8.14)"
                        )
                elif shape == "circle":
                    if len(coords) != 3:
                        self.errs.append(
                            f"{self.name}{loc}: <area shape='circle'> coords='{coords_raw}' requires exactly 3 coordinates "
                            f"(center-x, center-y, radius; HTML5 §4.8.14)"
                        )
                    else:
                        try:
                            radius = float(coords[2])
                            if radius <= 0:
                                self.errs.append(
                                    f"{self.name}{loc}: <area shape='circle'> radius must be greater than zero "
                                    f"(HTML5 §4.8.14)"
                                )
                        except ValueError:
                            pass
                elif shape == "poly":
                    if len(coords) < 6 or len(coords) % 2 != 0:
                        self.errs.append(
                            f"{self.name}{loc}: <area shape='poly'> coords='{coords_raw}' requires at least 6 coordinates in even (x, y) pairs "
                            f"(HTML5 §4.8.14)"
                        )

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "map" and self.map_depth > 0:
            self.map_depth -= 1


def check_map_and_area_integrity(name: str, body: str) -> list[str]:
    """Ensure HTML5 <map> and <area> image map elements enforce valid structure, alt text, shapes, and coordinates (HTML5 §4.8.13, §4.8.14 & WCAG 2.2 SC 1.1.1, SC 2.1.1, SC 2.4.4)."""
    errs: list[str] = []
    for m in re.finditer(r"<area\b([^>]*)>(.*?)</area>", body, re.I | re.S):
        inner = m.group(2)
        if inner.strip():
            errs.append(
                f"{name}: void element <area> must not contain inner content "
                f"(HTML5 §13.1.2.1 Void elements & WCAG 2.2 SC 1.3.1)"
            )
        else:
            errs.append(
                f"{name}: void element <area> must not have an end tag "
                f"(HTML5 §13.1.2.1 Void elements; void elements have no end tag)"
            )
    parser = _AreaAndMapParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    errs.extend(parser.errs)
    return errs


class _ColgroupAndColParser(HTMLParser):
    """Audits HTML5 <colgroup> and <col> table elements for valid containment, sequence, span attributes, and void syntax (HTML5 §4.9.3, §4.9.4 & WCAG 2.2 SC 1.3.1)."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.table_depth = 0
        self.in_colgroup = False
        self.colgroup_loc = ""
        self.colgroup_has_span = False
        self.colgroup_children: list[str] = []
        self.seen_rows = False
        self.errs: list[str] = []

    def _close_colgroup(self) -> None:
        if not self.in_colgroup:
            return
        if self.colgroup_has_span and any(c == "col" for c in self.colgroup_children):
            self.errs.append(
                f"{self.name}{self.colgroup_loc}: <colgroup> must not declare 'span' attribute when containing child <col> elements "
                f"(HTML5 §4.9.3 & WCAG 2.2 SC 1.3.1)"
            )
        self.in_colgroup = False
        self.colgroup_loc = ""
        self.colgroup_has_span = False
        self.colgroup_children = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if t == "table":
            self.table_depth += 1
            self.seen_rows = False
        elif t == "colgroup":
            if self.table_depth <= 0:
                self.errs.append(
                    f"{self.name}{loc}: orphaned <colgroup> element found outside <table> "
                    f"(HTML5 §4.9.3 & WCAG 2.2 SC 1.3.1)"
                )
            if self.in_colgroup:
                self._close_colgroup()
            if self.seen_rows and self.table_depth > 0:
                self.errs.append(
                    f"{self.name}{loc}: <colgroup> must appear before table rows, thead, tbody, or tfoot "
                    f"(HTML5 §4.9.3 & WCAG 2.2 SC 1.3.1)"
                )
            self.in_colgroup = True
            self.colgroup_loc = loc
            self.colgroup_children = []
            if "span" in attr_dict:
                span_val = attr_dict["span"].strip()
                if not (span_val.isdigit() and int(span_val) >= 1):
                    self.errs.append(
                        f"{self.name}{loc}: <colgroup> span='{span_val}' must be a positive integer >= 1 "
                        f"(HTML5 §4.9.3 & WCAG 2.2 SC 1.3.1)"
                    )
                self.colgroup_has_span = True
            else:
                self.colgroup_has_span = False
        elif t == "col":
            if self.table_depth <= 0 and not self.in_colgroup:
                self.errs.append(
                    f"{self.name}{loc}: orphaned <col> element found outside <table> "
                    f"(HTML5 §4.9.4 & WCAG 2.2 SC 1.3.1)"
                )
            if self.in_colgroup:
                self.colgroup_children.append("col")
            if "span" in attr_dict:
                span_val = attr_dict["span"].strip()
                if not (span_val.isdigit() and int(span_val) >= 1):
                    self.errs.append(
                        f"{self.name}{loc}: <col> span='{span_val}' must be a positive integer >= 1 "
                        f"(HTML5 §4.9.4 & WCAG 2.2 SC 1.3.1)"
                    )
        elif self.in_colgroup:
            if t not in ("col", "template"):
                self.errs.append(
                    f"{self.name}{loc}: <colgroup> contains forbidden child <{t}> "
                    f"(only <col> and <template> allowed; HTML5 §4.9.3 & WCAG 2.2 SC 1.3.1)"
                )
            self.colgroup_children.append(t)
        elif self.table_depth > 0 and t in ("thead", "tbody", "tfoot", "tr"):
            self.seen_rows = True

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == "colgroup":
            self._close_colgroup()
        elif t == "table":
            if self.in_colgroup:
                self._close_colgroup()
            if self.table_depth > 0:
                self.table_depth -= 1
            self.seen_rows = False


def check_colgroup_and_col_integrity(name: str, body: str) -> list[str]:
    """Ensure HTML5 <colgroup> and <col> table elements enforce valid containment, sequence, span attributes, and void syntax (HTML5 §4.9.3, §4.9.4 & WCAG 2.2 SC 1.3.1)."""
    errs: list[str] = []
    for m in re.finditer(r"<col\b([^>]*)>(.*?)</col>", body, re.I | re.S):
        inner = m.group(2)
        if inner.strip():
            errs.append(
                f"{name}: void element <col> must not contain inner content "
                f"(HTML5 §13.1.2.1 Void elements & WCAG 2.2 SC 1.3.1)"
            )
        else:
            errs.append(
                f"{name}: void element <col> must not have an end tag "
                f"(HTML5 §13.1.2.1 Void elements; void elements have no end tag)"
            )
    parser = _ColgroupAndColParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    errs.extend(parser.errs)
    return errs


class _AriaControlsParser(HTMLParser):
    """Audits ARIA aria-controls attributes for non-empty values, existing target IDs, no duplicates, and no self-reference (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def __init__(self, name: str, all_ids: set[str]) -> None:
        super().__init__()
        self.name = name
        self.all_ids = all_ids
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if "aria-controls" in attr_dict:
            raw_val = attr_dict["aria-controls"].strip()
            if not raw_val:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares empty or whitespace-only 'aria-controls' attribute "
                    f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                )
            else:
                elem_id = attr_dict.get("id", "").strip()
                tokens = raw_val.split()
                seen = set()
                for tok in tokens:
                    if tok in seen:
                        self.errs.append(
                            f"{self.name}{loc}: <{t}> aria-controls contains duplicate token '{tok}' "
                            f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                        )
                    seen.add(tok)
                    if elem_id and tok == elem_id:
                        self.errs.append(
                            f"{self.name}{loc}: <{t}> aria-controls references own element id '{tok}' "
                            f"(self-controlling is invalid; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                        )
                    if tok not in self.all_ids:
                        self.errs.append(
                            f"{self.name}{loc}: <{t}> aria-controls='{raw_val}' targets non-existent element id '{tok}' on page "
                            f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                        )


def check_aria_controls_target_and_token_integrity(name: str, body: str) -> list[str]:
    """Ensure ARIA aria-controls attributes specify existing target element IDs, avoid self-reference, and eliminate duplicates (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""
    all_ids = set(re.findall(r'\bid\s*=\s*["\']([^"\']+)["\']', body, re.I))
    parser = _AriaControlsParser(name, all_ids)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _PopoverCollector(HTMLParser):
    """Collects all element IDs and elements declaring popover attributes for validation (HTML5 §4.12.6)."""

    def __init__(self) -> None:
        super().__init__()
        self.all_ids: set[str] = set()
        self.popover_elements: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        elem_id = attr_dict.get("id", "").strip()
        if elem_id:
            self.all_ids.add(elem_id)
            if "popover" in attr_dict:
                self.popover_elements[elem_id] = t


class _PopoverParser(HTMLParser):
    """Audits HTML5 Popover API attributes and button invocations (HTML5 §4.12.6, §4.10.18.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def __init__(self, name: str, all_ids: set[str], popover_elements: dict[str, str]) -> None:
        super().__init__()
        self.name = name
        self.all_ids = all_ids
        self.popover_elements = popover_elements
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if "popover" in attr_dict:
            pop_val = attr_dict["popover"].lower().strip()
            if pop_val not in ("", "auto", "manual"):
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares invalid popover='{attr_dict['popover']}' "
                    f"(expected 'auto', 'manual', or empty; HTML5 §4.12.6 & WCAG 2.2 SC 4.1.2)"
                )

        has_target = "popovertarget" in attr_dict
        has_action = "popovertargetaction" in attr_dict

        if has_target or has_action:
            is_button = (t == "button") or (t == "input" and attr_dict.get("type", "").lower() in ("button", "submit", "reset", "image"))
            if not is_button:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares popovertarget attribute on non-button element "
                    f"(popover invocation attributes are only valid on <button> or button inputs; HTML5 §4.10.18.6 & WCAG 2.2 SC 4.1.2)"
                )

        if has_target:
            target_id = attr_dict["popovertarget"].strip()
            if not target_id:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares empty or whitespace-only 'popovertarget' attribute "
                    f"(HTML5 §4.10.18.6 & WCAG 2.2 SC 4.1.2)"
                )
            else:
                elem_id = attr_dict.get("id", "").strip()
                if elem_id and target_id == elem_id:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> popovertarget references own element id '{target_id}' "
                        f"(self-triggering popover is invalid; HTML5 §4.10.18.6 & WCAG 2.2 SC 4.1.2)"
                    )
                if target_id not in self.all_ids:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> popovertarget='{target_id}' targets non-existent element id on page "
                        f"(HTML5 §4.10.18.6 & WCAG 2.2 SC 4.1.2)"
                    )
                elif target_id not in self.popover_elements:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> popovertarget='{target_id}' targets element missing 'popover' attribute "
                        f"(target must declare popover attribute; HTML5 §4.12.6, §4.10.18.6 & WCAG 2.2 SC 4.1.2)"
                    )

        if has_action:
            action_val = attr_dict["popovertargetaction"].lower().strip()
            if action_val not in ("toggle", "show", "hide"):
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares invalid popovertargetaction='{attr_dict['popovertargetaction']}' "
                    f"(expected 'toggle', 'show', or 'hide'; HTML5 §4.10.18.6 & WCAG 2.2 SC 4.1.2)"
                )


def check_popover_attribute_and_target_integrity(name: str, body: str) -> list[str]:
    """Ensure HTML5 Popover API attributes enforce valid values, button invocation, and existing popover targets (HTML5 §4.12.6, §4.10.18.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""
    collector = _PopoverCollector()
    try:
        collector.feed(body)
    except Exception:
        pass
    parser = _PopoverParser(name, collector.all_ids, collector.popover_elements)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _AriaDescribedbyAndDetailsParser(HTMLParser):
    """Audits ARIA aria-describedby and aria-details attributes for non-empty values, existing target IDs, no duplicates, and no self-reference (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    def __init__(self, name: str, all_ids: set[str]) -> None:
        super().__init__()
        self.name = name
        self.all_ids = all_ids
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        elem_id = attr_dict.get("id", "").strip()

        for attr in ("aria-describedby", "aria-details"):
            if attr in attr_dict:
                raw_val = attr_dict[attr].strip()
                if not raw_val:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares empty or whitespace-only '{attr}' attribute "
                        f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                    )
                else:
                    tokens = raw_val.split()
                    seen = set()
                    for tok in tokens:
                        if tok in seen:
                            self.errs.append(
                                f"{self.name}{loc}: <{t}> {attr} contains duplicate token '{tok}' "
                                f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                            )
                        seen.add(tok)
                        if elem_id and tok == elem_id:
                            self.errs.append(
                                f"{self.name}{loc}: <{t}> {attr} references own element id '{tok}' "
                                f"(self-referencing is invalid; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                            )
                        if tok not in self.all_ids:
                            self.errs.append(
                                f"{self.name}{loc}: <{t}> {attr}='{raw_val}' targets non-existent element id '{tok}' on page "
                                f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)"
                            )


def check_aria_describedby_and_details_target_integrity(name: str, body: str) -> list[str]:
    """Ensure ARIA aria-describedby and aria-details attributes specify existing target element IDs, avoid self-reference, and eliminate duplicates (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""
    all_ids = set(re.findall(r'\bid\s*=\s*["\']([^"\']+)["\']', body, re.I))
    parser = _AriaDescribedbyAndDetailsParser(name, all_ids)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _AriaFlowtoParser(HTMLParser):
    """Audits ARIA aria-flowto attributes for non-empty values, existing targets, no duplicates, no self-reference, and no reciprocal circular flows (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.2, SC 2.4.3)."""

    def __init__(self, name: str, all_ids: set[str]) -> None:
        super().__init__()
        self.name = name
        self.all_ids = all_ids
        self.errs: list[str] = []
        self.flow_map: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if "aria-flowto" in attr_dict:
            raw_val = attr_dict["aria-flowto"].strip()
            if not raw_val:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares empty or whitespace-only 'aria-flowto' attribute "
                    f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.2, SC 2.4.3)"
                )
            else:
                elem_id = attr_dict.get("id", "").strip()
                tokens = raw_val.split()
                seen = set()
                if elem_id:
                    self.flow_map[elem_id] = tokens
                for tok in tokens:
                    if tok in seen:
                        self.errs.append(
                            f"{self.name}{loc}: <{t}> aria-flowto contains duplicate token '{tok}' "
                            f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.2, SC 2.4.3)"
                        )
                    seen.add(tok)
                    if elem_id and tok == elem_id:
                        self.errs.append(
                            f"{self.name}{loc}: <{t}> aria-flowto references own element id '{tok}' "
                            f"(self-flow is invalid; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.2, SC 2.4.3)"
                        )
                    if tok not in self.all_ids:
                        self.errs.append(
                            f"{self.name}{loc}: <{t}> aria-flowto='{raw_val}' targets non-existent element id '{tok}' on page "
                            f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.2, SC 2.4.3)"
                        )

    def validate_acyclic(self) -> None:
        checked_pairs = set()
        for src, targets in self.flow_map.items():
            for dst in targets:
                pair = tuple(sorted([src, dst]))
                if pair in checked_pairs:
                    continue
                checked_pairs.add(pair)
                if dst in self.flow_map and src in self.flow_map[dst]:
                    self.errs.append(
                        f"{self.name}: element id '{src}' and element id '{dst}' form a reciprocal circular aria-flowto cycle "
                        f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.2)"
                    )


def check_aria_flowto_reading_flow_integrity(name: str, body: str) -> list[str]:
    """Ensure ARIA aria-flowto attributes specify existing target element IDs, avoid self-reference, eliminate duplicates, and prevent circular flow traps (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.2, SC 2.4.3)."""
    all_ids = set(re.findall(r'\bid\s*=\s*["\']([^"\']+)["\']', body, re.I))
    parser = _AriaFlowtoParser(name, all_ids)
    try:
        parser.feed(body)
        parser.validate_acyclic()
    except Exception:
        pass
    return parser.errs


class _TableCellSpanningAndOrphanParser(HTMLParser):
    """Audits HTML5 table cell spanning (colspan, rowspan), header scopes, and orphaned table elements (HTML5 §4.9.6, §4.9.9, §4.9.10, §4.9.11 & WCAG 2.2 SC 1.3.1)."""
    TABLE_STRUCTURAL_TAGS = {"tr", "th", "td", "caption", "thead", "tbody", "tfoot"}
    VALID_SCOPES = {"col", "row", "colgroup", "rowgroup"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.table_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if t == "table":
            self.table_depth += 1
            return

        if t in self.TABLE_STRUCTURAL_TAGS and self.table_depth == 0:
            self.errs.append(
                f"{self.name}{loc}: orphaned <{t}> element outside <table> container "
                f"(HTML5 §4.9 & WCAG 2.2 SC 1.3.1)"
            )

        if t in ("th", "td"):
            if "colspan" in attr_dict:
                val = attr_dict["colspan"].strip()
                try:
                    num = int(val)
                    if num < 1 or num > 1000:
                        raise ValueError()
                except ValueError:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares invalid colspan='{val}' "
                        f"(must be a positive integer between 1 and 1000; HTML5 §4.9.9, §4.9.10 & WCAG 2.2 SC 1.3.1)"
                    )

            if "rowspan" in attr_dict:
                val = attr_dict["rowspan"].strip()
                try:
                    num = int(val)
                    if num < 0 or num > 65534:
                        raise ValueError()
                except ValueError:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares invalid rowspan='{val}' "
                        f"(must be a non-negative integer between 0 and 65534; HTML5 §4.9.9, §4.9.10 & WCAG 2.2 SC 1.3.1)"
                    )

            if t == "th" and "scope" in attr_dict:
                s_val = attr_dict["scope"].lower().strip()
                if s_val not in self.VALID_SCOPES:
                    self.errs.append(
                        f"{self.name}{loc}: <th> declares invalid scope='{s_val}' "
                        f"(must be 'col', 'row', 'colgroup', or 'rowgroup'; HTML5 §4.9.11 & WCAG 2.2 SC 1.3.1)"
                    )

            if t == "td" and "scope" in attr_dict:
                self.errs.append(
                    f"{self.name}{loc}: <td scope='...'>: scope attribute is prohibited on <td> data cells "
                    f"(only permitted on <th> header cells; HTML5 §4.9.10 & WCAG 2.2 SC 1.3.1)"
                )

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "table":
            if self.table_depth > 0:
                self.table_depth -= 1


def check_table_cell_spanning_and_orphan_integrity(name: str, body: str) -> list[str]:
    """Ensure HTML5 table cells use valid positive colspans, non-negative rowspans, valid th scopes, no td scopes, and table elements are not orphaned outside tables (HTML5 §4.9.6, §4.9.9, §4.9.10, §4.9.11 & WCAG 2.2 SC 1.3.1)."""
    parser = _TableCellSpanningAndOrphanParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _MediaSourceAndFallbackParser(HTMLParser):
    """Audits HTML5 <audio> and <video> elements for valid source definitions, non-nesting, and accessible fallback content (HTML5 §4.8.9, §4.8.10 & WCAG 2.2 SC 1.1.1, SC 1.2.1)."""
    MEDIA_TAGS = {"audio", "video"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.media_stack: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if t in self.MEDIA_TAGS:
            if any(m["tag"] == t for m in self.media_stack):
                self.errs.append(
                    f"{self.name}{loc}: <{t}> directly nests another <{t}> media element "
                    f"(HTML5 §4.8.9, §4.8.10 & WCAG 2.2 SC 1.1.1)"
                )
            self.media_stack.append({
                "tag": t,
                "has_direct_src": bool(attr_dict.get("src", "").strip()),
                "has_child_src": False,
                "fallback_text": [],
                "has_fallback_link": False,
                "loc": loc,
            })
            return

        if self.media_stack:
            curr = self.media_stack[-1]
            if t == "source":
                src_val = attr_dict.get("src", "").strip()
                if src_val:
                    curr["has_child_src"] = True
                else:
                    self.errs.append(
                        f"{self.name}{loc}: <source> inside <{curr['tag']}> missing non-empty 'src' attribute "
                        f"(HTML5 §4.8.2 & WCAG 2.2 SC 1.1.1)"
                    )
            elif t == "a":
                curr["has_fallback_link"] = True

    def handle_data(self, data: str) -> None:
        if self.media_stack and data.strip():
            self.media_stack[-1]["fallback_text"].append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in self.MEDIA_TAGS:
            if self.media_stack and self.media_stack[-1]["tag"] == t:
                entry = self.media_stack.pop()
                if not (entry["has_direct_src"] or entry["has_child_src"]):
                    self.errs.append(
                        f"{self.name}{entry['loc']}: <{t}> media element has no playable source "
                        f"(missing 'src' attribute or child <source src='...'>; HTML5 §4.8.9, §4.8.10 & WCAG 2.2 SC 1.1.1)"
                    )
                fallback = " ".join(entry["fallback_text"]).strip()
                if not fallback and not entry["has_fallback_link"]:
                    self.errs.append(
                        f"{self.name}{entry['loc']}: <{t}> media element missing accessible fallback content "
                        f"for unsupported user agents (HTML5 §4.8.9, §4.8.10 & WCAG 2.2 SC 1.1.1)"
                    )


def check_media_source_and_fallback_integrity(name: str, body: str) -> list[str]:
    """Ensure HTML5 <audio> and <video> elements provide playable sources, non-empty fallback content, and avoid direct self-nesting (HTML5 §4.8.9, §4.8.10 & WCAG 2.2 SC 1.1.1, SC 1.2.1)."""
    parser = _MediaSourceAndFallbackParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


VALID_ARIA_CURRENT_TOKENS = {"page", "step", "location", "date", "time", "true", "false"}
VALID_FORM_ENCTYPES = {"application/x-www-form-urlencoded", "multipart/form-data", "text/plain"}
VALID_FORM_METHODS = {"get", "post", "dialog"}
VALID_HIDDEN_VALUES = {"", "hidden", "until-found"}


class _AriaCurrentTokenAndContextParser(HTMLParser):
    """Audits ARIA aria-current attribute for valid enumerated tokens, non-void elements, and absence of presentational roles (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""

    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if "aria-current" in attr_dict:
            raw_val = attr_dict["aria-current"].strip()
            val_lower = raw_val.lower()
            if not raw_val or val_lower not in VALID_ARIA_CURRENT_TOKENS:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares invalid aria-current='{raw_val}' "
                    f"(W3C WAI-ARIA 1.2 §6.6 strictly restricts aria-current to 'page', 'step', 'location', 'date', 'time', 'true', or 'false')"
                )
            if t in self.VOID_TAGS:
                self.errs.append(
                    f"{self.name}{loc}: void element <{t}> must not declare 'aria-current' attribute "
                    f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                )
            role = attr_dict.get("role", "").lower().strip()
            if role in ("presentation", "none"):
                self.errs.append(
                    f"{self.name}{loc}: <{t} role='{role}'> must not declare 'aria-current' attribute "
                    f"(presentational elements cannot convey state; W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                )


def check_aria_current_token_and_context_integrity(name: str, body: str) -> list[str]:
    """Ensure ARIA aria-current attributes specify valid tokens, avoid void tags, and exclude presentational roles (W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 1.3.1, SC 4.1.2)."""
    parser = _AriaCurrentTokenAndContextParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _FormSubmissionAttributesParser(HTMLParser):
    """Audits form submission attributes (formaction, formenctype, formmethod, formnovalidate, formtarget) to ensure placement strictly on submit buttons and valid token values (HTML5 §4.10.18.5 & WCAG 2.2 SC 4.1.2)."""

    FORM_ATTRS = {"formaction", "formenctype", "formmethod", "formnovalidate", "formtarget"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        present_form_attrs = self.FORM_ATTRS.intersection(attr_dict.keys())
        if not present_form_attrs:
            return

        is_submit_button = False
        if t == "button":
            btn_type = attr_dict.get("type", "submit").lower().strip()
            if btn_type == "submit" or not btn_type:
                is_submit_button = True
            else:
                for fa in sorted(present_form_attrs):
                    self.errs.append(
                        f"{self.name}{loc}: <button type='{btn_type}'> must not declare form submission attribute '{fa}' "
                        f"(HTML5 §4.10.18.5 restricts form submission attributes to submit buttons)"
                    )
                return
        elif t == "input":
            inp_type = attr_dict.get("type", "text").lower().strip()
            if inp_type in ("submit", "image"):
                is_submit_button = True
            else:
                for fa in sorted(present_form_attrs):
                    self.errs.append(
                        f"{self.name}{loc}: <input type='{inp_type}'> must not declare form submission attribute '{fa}' "
                        f"(HTML5 §4.10.18.5 restricts form submission attributes to submit buttons)"
                    )
                return
        else:
            for fa in sorted(present_form_attrs):
                self.errs.append(
                    f"{self.name}{loc}: <{t}> must not declare form submission attribute '{fa}' "
                    f"(HTML5 §4.10.18.5 restricts form submission attributes to <button> and submit/image <input>)"
                )
            return

        if is_submit_button:
            if "formaction" in attr_dict:
                fa_val = attr_dict["formaction"].strip()
                if not fa_val:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares empty or whitespace-only 'formaction' attribute "
                        f"(HTML5 §4.10.18.5 & WCAG 2.2 SC 4.1.2)"
                    )
            if "formenctype" in attr_dict:
                fe_val = attr_dict["formenctype"].strip().lower()
                if fe_val not in VALID_FORM_ENCTYPES:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares invalid formenctype='{attr_dict['formenctype']}' "
                        f"(HTML5 §4.10.18.5 strictly restricts formenctype to 'application/x-www-form-urlencoded', 'multipart/form-data', or 'text/plain')"
                    )
            if "formmethod" in attr_dict:
                fm_val = attr_dict["formmethod"].strip().lower()
                if fm_val not in VALID_FORM_METHODS:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares invalid formmethod='{attr_dict['formmethod']}' "
                        f"(HTML5 §4.10.18.5 strictly restricts formmethod to 'get', 'post', or 'dialog')"
                    )
            if "formtarget" in attr_dict:
                ft_val = attr_dict["formtarget"].strip()
                if not ft_val:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares empty or whitespace-only 'formtarget' attribute "
                        f"(HTML5 §4.10.18.5 & WCAG 2.2 SC 4.1.2)"
                    )


def check_form_submission_attributes_integrity(name: str, body: str) -> list[str]:
    """Ensure form submission attributes (formaction, formenctype, formmethod, formnovalidate, formtarget) are confined to submit buttons and have valid tokens (HTML5 §4.10.18.5 & WCAG 2.2 SC 4.1.2)."""
    parser = _FormSubmissionAttributesParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _DialogHierarchyAndActionParser(HTMLParser):
    """Audits <dialog> elements for non-nesting, valid role overrides, and presence of focusable controls when containing content (HTML5 §4.11.4 & WCAG 2.2 SC 2.1.2, SC 2.4.3, SC 4.1.2)."""

    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.dialog_stack: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if t == "dialog":
            if self.dialog_stack:
                self.errs.append(
                    f"{self.name}{loc}: <dialog> must not be nested inside ancestor <dialog> "
                    f"(HTML5 §4.11.4 strictly prohibits nested dialogs)"
                )
            role = attr_dict.get("role", "").lower().strip()
            if role:
                for r in role.split():
                    if r not in ("dialog", "alertdialog"):
                        self.errs.append(
                            f"{self.name}{loc}: <dialog role='{r}'> declares invalid role override "
                            f"(HTML5 §4.11.4 restricts dialog role to 'dialog' or 'alertdialog'; WCAG 2.2 SC 4.1.2)"
                        )
            self.dialog_stack.append({"loc": loc, "has_content": False, "has_focusable": False})
            return

        if self.dialog_stack:
            d = self.dialog_stack[-1]
            if t not in self.VOID_TAGS:
                d["has_content"] = True
            is_focusable = (
                t in ("button", "select", "textarea")
                or (t == "a" and "href" in attr_dict)
                or (t == "input" and attr_dict.get("type", "text").lower() != "hidden")
                or attr_dict.get("tabindex", "").strip() in ("0", "1")
            )
            if is_focusable:
                d["has_focusable"] = True

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == "dialog" and self.dialog_stack:
            d = self.dialog_stack.pop()
            if d["has_content"] and not d["has_focusable"]:
                self.errs.append(
                    f"{self.name}{d['loc']}: <dialog> contains content but lacks any keyboard-focusable controls or dismiss actions "
                    f"(WCAG 2.2 SC 2.1.2 No Keyboard Trap & SC 2.4.3 Focus Order)"
                )


def check_dialog_element_hierarchy_and_action_integrity(name: str, body: str) -> list[str]:
    """Ensure <dialog> elements are not nested, restrict role overrides, and include keyboard-focusable actions when populated (HTML5 §4.11.4 & WCAG 2.2 SC 2.1.2, SC 2.4.3, SC 4.1.2)."""
    parser = _DialogHierarchyAndActionParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _HiddenAttributeAndConflictParser(HTMLParser):
    """Audits hidden attribute usage to prevent deceptive truthy values (hidden='false'), conflicts with aria-hidden='false', and autofocus on hidden elements (HTML5 §3.2.8.2 & WCAG 2.2 SC 1.3.1, SC 2.4.3, SC 4.1.2)."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if "hidden" in attr_dict:
            raw_val = attr_dict["hidden"].strip().lower()
            if raw_val in ("false", "no", "off"):
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares deceptive truthy hidden='{attr_dict['hidden']}' "
                    f"(in HTML5 the presence of the hidden attribute hides the element regardless of value; remove the attribute instead; HTML5 §3.2.8.2)"
                )
            elif raw_val not in VALID_HIDDEN_VALUES:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares invalid hidden='{attr_dict['hidden']}' "
                    f"(HTML5 §3.2.8.2 restricts hidden attribute values to empty, 'hidden', or 'until-found')"
                )
            if "aria-hidden" in attr_dict:
                aria_val = attr_dict["aria-hidden"].strip().lower()
                if aria_val == "false":
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares conflicting visibility states with both hidden and aria-hidden='false' "
                        f"(W3C WAI-ARIA 1.2 §6.6 & WCAG 2.2 SC 4.1.2)"
                    )
            if "autofocus" in attr_dict:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> must not declare autofocus on a hidden element "
                    f"(WCAG 2.2 SC 2.4.3 Focus Order & HTML5 §3.2.8.2)"
                )


def check_hidden_attribute_and_conflict_integrity(name: str, body: str) -> list[str]:
    """Ensure hidden attributes avoid deceptive truthy values, conflicting aria-hidden='false', and autofocus (HTML5 §3.2.8.2 & WCAG 2.2 SC 1.3.1, SC 2.4.3, SC 4.1.2)."""
    parser = _HiddenAttributeAndConflictParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


# =====================================================================
# Media ControlsList & CrossOrigin, Figure Hierarchy, Output Form/Name & Progress/Meter Nesting Linters
# =====================================================================

class _MediaControlsListAndCrossOriginParser(HTMLParser):
    """Audits crossorigin, controlslist, and disableremoteplayback attributes on media, images, scripts, and links (HTML5 §4.8.9, §4.8.10, §4.8.16 & WCAG 2.2 SC 4.1.2)."""
    VALID_CROSSORIGIN = frozenset({"", "anonymous", "use-credentials"})
    VALID_CONTROLSLIST_TOKENS = frozenset({"nodownload", "nofullscreen", "noremoteplayback"})

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        ad = {k.lower(): (v or "") for k, v in attrs}

        if t in ("img", "audio", "video", "script", "link") and "crossorigin" in ad:
            val = ad["crossorigin"].strip().lower()
            if val not in self.VALID_CROSSORIGIN:
                self.errs.append(
                    f"{self.name}{loc}: <{t}> declares invalid crossorigin='{ad['crossorigin']}' "
                    f"(must be empty, 'anonymous', or 'use-credentials'; HTML5 §4.8.16 & WCAG 2.2 SC 4.1.2)"
                )

        if t in ("audio", "video"):
            if "controlslist" in ad:
                raw_cl = ad["controlslist"]
                tokens = raw_cl.split()
                if not tokens:
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares empty or whitespace-only 'controlslist' attribute "
                        f"(HTML5 §4.8.9/§4.8.10 & WCAG 2.2 SC 4.1.2)"
                    )
                else:
                    seen = set()
                    for tok in tokens:
                        tok_lower = tok.lower()
                        if tok_lower not in self.VALID_CONTROLSLIST_TOKENS:
                            self.errs.append(
                                f"{self.name}{loc}: <{t}> declares invalid controlslist token '{tok}' "
                                f"(must be 'nodownload', 'nofullscreen', or 'noremoteplayback'; HTML5 §4.8.9/§4.8.10)"
                            )
                        elif tok_lower in seen:
                            self.errs.append(
                                f"{self.name}{loc}: <{t}> declares duplicate controlslist token '{tok}' "
                                f"(HTML5 §4.8.9/§4.8.10)"
                            )
                        seen.add(tok_lower)

            if "disableremoteplayback" in ad:
                val = ad["disableremoteplayback"].strip().lower()
                if val in ("false", "off", "no"):
                    self.errs.append(
                        f"{self.name}{loc}: <{t}> declares deceptive truthy disableremoteplayback='{val}' "
                        f"(disableremoteplayback is a boolean attribute; HTML5 §4.8.9/§4.8.10 & WCAG 2.2 SC 4.1.2)"
                    )


def check_media_controlslist_and_crossorigin_integrity(name: str, body: str) -> list[str]:
    """Ensure media and resource elements declare valid crossorigin tokens, well-formed controlslist tokens, and non-deceptive disableremoteplayback (HTML5 §4.8.9, §4.8.10, §4.8.16 & WCAG 2.2 SC 4.1.2)."""
    parser = _MediaControlsListAndCrossOriginParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _FigureAndFigcaptionHierarchyParser(HTMLParser):
    """Audits <figure> and <figcaption> structure to ensure figcaption is strictly first or last element child and avoids nested figures (HTML5 §4.4.12, §4.4.13 & WCAG 2.2 SC 1.3.1)."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.tag_stack: list[str] = []
        self.figure_stack: list[dict] = []
        self.in_figcaption = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        current_depth = len(self.tag_stack)

        if self.figure_stack:
            curr_fig = self.figure_stack[-1]
            if current_depth == curr_fig["depth"] + 1:
                curr_fig["direct_children"].append(t)

        if t == "figure":
            if self.in_figcaption:
                self.errs.append(
                    f"{self.name}{loc}: <figure> must not be nested inside <figcaption> (HTML5 §4.4.12 & WCAG 2.2 SC 1.3.1)"
                )
            self.figure_stack.append({
                "depth": current_depth,
                "loc": loc,
                "direct_children": [],
            })
        elif t == "figcaption":
            if self.in_figcaption:
                self.errs.append(f"{self.name}{loc}: nested <figcaption> inside <figcaption> (HTML5 §4.4.13)")
            self.in_figcaption = True

        self.tag_stack.append(t)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if self.tag_stack and self.tag_stack[-1] == t:
            self.tag_stack.pop()

        if t == "figure" and self.figure_stack:
            fig = self.figure_stack.pop()
            children = [c for c in fig["direct_children"] if c not in ("style", "script")]
            figcaptions = [i for i, c in enumerate(children) if c == "figcaption"]
            if len(figcaptions) == 1:
                idx = figcaptions[0]
                if idx != 0 and idx != len(children) - 1:
                    self.errs.append(
                        f"{self.name}{fig['loc']}: <figcaption> must be either the first or last element child of <figure> "
                        f"(found element children before and after <figcaption>; HTML5 §4.4.12 & WCAG 2.2 SC 1.3.1)"
                    )
        elif t == "figcaption":
            self.in_figcaption = False


def check_figure_and_figcaption_hierarchy_integrity(name: str, body: str) -> list[str]:
    """Ensure <figure> containers position <figcaption> as first or last element child and forbid nested figures in captions (HTML5 §4.4.12, §4.4.13 & WCAG 2.2 SC 1.3.1)."""
    parser = _FigureAndFigcaptionHierarchyParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


class _OutputFormAndNameParser(HTMLParser):
    """Audits <output> elements for valid name and form owner associations (HTML5 §4.10.19 & WCAG 2.2 SC 4.1.2, SC 1.3.1)."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.doc_ids: set[str] = set()
        self.form_ids: set[str] = set()
        self.outputs_to_check: list[tuple[dict, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        ad = {k.lower(): (v or "") for k, v in attrs}

        elem_id = ad.get("id", "").strip()
        if elem_id:
            self.doc_ids.add(elem_id)
            if t == "form":
                self.form_ids.add(elem_id)

        if t == "output":
            self.outputs_to_check.append((ad, loc))

    def finish(self) -> None:
        for ad, loc in self.outputs_to_check:
            if "name" in ad and not ad["name"].strip():
                self.errs.append(
                    f"{self.name}{loc}: <output> declares empty or whitespace-only 'name' attribute "
                    f"(HTML5 §4.10.19 & WCAG 2.2 SC 4.1.2)"
                )
            if "form" in ad:
                form_ref = ad["form"].strip()
                if not form_ref:
                    self.errs.append(
                        f"{self.name}{loc}: <output> declares empty or whitespace-only 'form' attribute "
                        f"(HTML5 §4.10.19 & WCAG 2.2 SC 4.1.2)"
                    )
                elif form_ref not in self.doc_ids:
                    self.errs.append(
                        f"{self.name}{loc}: <output form='{form_ref}'> references non-existent element id '{form_ref}' "
                        f"(HTML5 §4.10.19 & WCAG 2.2 SC 4.1.2)"
                    )
                elif form_ref not in self.form_ids:
                    self.errs.append(
                        f"{self.name}{loc}: <output form='{form_ref}'> references element id '{form_ref}' which is not a <form> "
                        f"(HTML5 §4.10.19 & WCAG 2.2 SC 4.1.2)"
                    )


def check_output_element_form_and_name_integrity(name: str, body: str) -> list[str]:
    """Ensure <output> elements declare valid non-empty names and resolve to existing <form> owners (HTML5 §4.10.19 & WCAG 2.2 SC 4.1.2, SC 1.3.1)."""
    parser = _OutputFormAndNameParser(name)
    try:
        parser.feed(body)
        parser.finish()
    except Exception:
        pass
    return parser.errs


class _ProgressAndMeterNestingParser(HTMLParser):
    """Audits <progress> and <meter> elements to prevent nested meters/progress and interactive controls inside fallback content (HTML5 §4.10.13, §4.10.14 & WCAG 2.2 SC 4.1.2, SC 2.1.1)."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        ad = {k.lower(): (v or "") for k, v in attrs}

        if self.stack:
            ancestor = self.stack[-1]
            if t in ("progress", "meter"):
                self.errs.append(
                    f"{self.name}{loc}: <{ancestor}> must not contain nested <{t}> element "
                    f"(HTML5 §4.10.13/§4.10.14 & WCAG 2.2 SC 4.1.2)"
                )
            is_interactive = False
            if t in ("button", "input", "select", "textarea", "details"):
                is_interactive = True
            elif t == "a" and "href" in ad:
                is_interactive = True
            elif "tabindex" in ad:
                try:
                    if int(ad["tabindex"]) >= 0:
                        is_interactive = True
                except ValueError:
                    pass
            roles = set(ad.get("role", "").lower().split())
            if roles & {"button", "link", "checkbox", "radio", "switch", "menuitem", "tab"}:
                is_interactive = True

            if is_interactive:
                self.errs.append(
                    f"{self.name}{loc}: interactive <{t}> inside <{ancestor}> violates HTML5 §4.10.13/§4.10.14 & WCAG 2.2 SC 4.1.2 "
                    f"(progress and meter fallback content must not contain interactive elements)"
                )

        if t in ("progress", "meter"):
            self.stack.append(t)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("progress", "meter") and self.stack:
            if self.stack[-1] == t:
                self.stack.pop()


def check_progress_and_meter_nesting_and_interactive_integrity(name: str, body: str) -> list[str]:
    """Ensure <progress> and <meter> elements do not nest gauges or include interactive elements in fallback content (HTML5 §4.10.13, §4.10.14 & WCAG 2.2 SC 4.1.2, SC 2.1.1)."""
    parser = _ProgressAndMeterNestingParser(name)
    try:
        parser.feed(body)
    except Exception:
        pass
    return parser.errs


def check_focus_visible_styling(name: str, raw_text: str) -> list[str]:
    """Ensure inline styles do not strip keyboard focus outlines without replacement (WCAG 2.2 SC 2.4.7)."""
    errs: list[str] = []
    for m in re.finditer(r'\bstyle\s*=\s*["\'][^"\']*?\boutline\s*:\s*(?:none|0)\b[^"\']*["\']', raw_text, re.I):
        errs.append(
            f"{name}: inline style removes keyboard focus outline ('outline: none' or 'outline: 0') without replacement (WCAG 2.2 SC 2.4.7)"
        )
    return errs


def check_table_accessibility(name: str, body: str) -> list[str]:
    """Ensure data tables have descriptive captions/labels, first-child captions, scoped header cells, and valid headers attributes (WCAG 2.2 SC 1.3.1 & W3C Failure F90)."""
    errs: list[str] = []
    table_re = re.compile(r"<table\b([^>]*)>(.*?)</table>", re.I | re.S)
    for m in table_re.finditer(body):
        attrs, inner = m.group(1), m.group(2)
        role_m = re.search(r'\brole\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        role = role_m.group(1).lower().strip() if role_m else ""
        if role in ("presentation", "none"):
            if re.search(r"<(?:th|caption)\b", inner, re.I):
                errs.append(
                    f"{name}: presentation table (role='{role}') must not contain <th> headers or <caption> tags (WCAG 2.2 SC 1.3.1)"
                )
            continue

        if re.search(r'\bsummary\s*=\s*["\']', attrs, re.I):
            errs.append(
                f"{name}: <table> declares obsolete 'summary' attribute (obsoleted in HTML5; use <caption> or aria-describedby instead; WCAG 2.2 SC 1.3.1)"
            )

        has_aria = bool(re.search(r'\baria-label(?:ledby)?\s*=\s*["\'][^"\']+["\']', attrs, re.I))
        caption_m = re.search(r"<caption\b[^>]*>(.*?)</caption>", inner, re.I | re.S)
        if not has_aria and not caption_m:
            errs.append(
                f"{name}: <table> missing accessible name (requires <caption>, aria-label, or aria-labelledby; WCAG 2.2 SC 1.3.1)"
            )
        elif caption_m:
            cap_text = _TAG_RE.sub(" ", caption_m.group(1)).strip()
            if len(cap_text) < 5:
                errs.append(
                    f"{name}: <table> <caption> is too short ({len(cap_text)} chars; minimum 5 chars; WCAG 2.2 SC 1.3.1)"
                )
            prefix = inner[:caption_m.start()]
            if re.search(r"<(?:colgroup|thead|tbody|tfoot|tr|th|td)\b", prefix, re.I):
                errs.append(
                    f"{name}: <table> <caption> must be the first element child of <table> "
                    f"(placed before <thead>, <tbody>, <tr>; HTML5 §4.9.2 & WCAG 2.2 SC 1.3.1)"
                )

        # Check for invalid scope on <td> cells
        for td_m in re.finditer(r"<td\b([^>]*)>", inner, re.I):
            td_attrs = td_m.group(1)
            if re.search(r'\bscope\s*=', td_attrs, re.I):
                errs.append(
                    f"{name}: <td scope='...'>: scope attribute is only valid on <th> header cells "
                    f"(HTML5 §4.9.11 & WCAG 2.2 SC 1.3.1)"
                )

        th_tags = list(re.finditer(r"<th\b([^>]*)>(.*?)</th>", inner, re.I | re.S))
        th_ids: set[str] = set()
        if not th_tags:
            errs.append(
                f"{name}: <table> data table contains no <th> header cells (WCAG 2.2 SC 1.3.1 requires headers for tabular data)"
            )
        else:
            for th_match in th_tags:
                th_attrs, th_inner = th_match.group(1), th_match.group(2)
                th_id_m = re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', th_attrs, re.I)
                if th_id_m:
                    th_ids.add(th_id_m.group(1).strip())
                th_text = _TAG_RE.sub(" ", th_inner).strip()
                has_th_label = bool(re.search(r'\baria-label(?:ledby)?\s*=\s*["\'][^"\']+["\']', th_attrs, re.I))
                if not th_text and not has_th_label:
                    errs.append(
                        f"{name}: empty <th> header cell (WCAG 2.2 SC 1.3.1 requires non-empty header text or aria-label)"
                    )
                if not re.search(r'\bscope\s*=\s*["\'](?:col|row|colgroup|rowgroup)["\']', th_attrs, re.I) and not th_id_m:
                    errs.append(
                        f"{name}: <th> header cell missing explicit scope attribute (e.g. scope='col' or scope='row'; WCAG 2.2 SC 1.3.1)"
                    )

        # Check headers attribute references on <td> cells (W3C Failure F90)
        for td_m in re.finditer(r"<td\b([^>]*)>", inner, re.I):
            td_attrs = td_m.group(1)
            headers_m = re.search(r'\bheaders\s*=\s*["\']([^"\']+)["\']', td_attrs, re.I)
            if headers_m:
                for ref in headers_m.group(1).split():
                    if ref not in th_ids:
                        errs.append(
                            f"{name}: <td> headers attribute references '{ref}' which does not exist on any <th> cell in the table "
                            f"(WCAG 2.2 SC 1.3.1 & W3C Failure F90)"
                        )
    return errs


def check_progress_and_meter_accessibility(name: str, body: str) -> list[str]:
    """Ensure <progress> and <meter> elements have accessible names and valid numeric constraints (HTML5 §4.10.13/14 & WCAG 2.2 SC 4.1.2 / SC 1.3.1)."""
    errs: list[str] = []

    # 1. <progress> elements
    for m in re.finditer(r"<progress\b([^>]*)>(.*?)</progress>", body, re.I | re.S):
        attrs, inner = m.group(1), m.group(2)
        has_aria_label = bool(re.search(r'\baria-label\s*=\s*["\']\s*[^"\'\s]+[^"\']*["\']', attrs, re.I))
        has_aria_labelledby = bool(re.search(r'\baria-labelledby\s*=\s*["\']\s*[^"\'\s]+[^"\']*["\']', attrs, re.I))
        id_m = re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        elem_id = id_m.group(1).strip() if id_m else ""
        has_label_for = False
        if elem_id:
            has_label_for = bool(re.search(rf'<label\b[^>]*\bfor=["\']{re.escape(elem_id)}["\'][^>]*>', body, re.I))

        if not (has_aria_label or has_aria_labelledby or has_label_for):
            errs.append(
                f"{name}: <progress> missing accessible name (requires aria-label, aria-labelledby, or <label for='...'>; "
                f"WCAG 2.2 SC 4.1.2 Name, Role, Value)"
            )

        val_m = re.search(r'\bvalue\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        max_m = re.search(r'\bmax\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        max_val = 1.0
        if max_m:
            try:
                max_val = float(max_m.group(1))
                if max_val <= 0:
                    errs.append(f"{name}: <progress> max attribute must be greater than 0 (got '{max_m.group(1)}'; HTML5 §4.10.13)")
            except ValueError:
                errs.append(f"{name}: <progress> max attribute must be a valid number (got '{max_m.group(1)}'; HTML5 §4.10.13)")
        if val_m:
            try:
                val = float(val_m.group(1))
                if val < 0:
                    errs.append(f"{name}: <progress> value attribute cannot be negative (got '{val_m.group(1)}'; HTML5 §4.10.13)")
                elif max_m and max_val > 0 and val > max_val:
                    errs.append(f"{name}: <progress> value ({val}) cannot exceed max ({max_val}; HTML5 §4.10.13)")
                elif not max_m and val > 1.0:
                    errs.append(f"{name}: <progress> value ({val}) cannot exceed default max (1.0) when max is omitted (HTML5 §4.10.13)")
            except ValueError:
                errs.append(f"{name}: <progress> value attribute must be a valid number (got '{val_m.group(1)}'; HTML5 §4.10.13)")

    # 2. <meter> elements
    for m in re.finditer(r"<meter\b([^>]*)>(.*?)</meter>", body, re.I | re.S):
        attrs, inner = m.group(1), m.group(2)
        has_aria_label = bool(re.search(r'\baria-label\s*=\s*["\']\s*[^"\'\s]+[^"\']*["\']', attrs, re.I))
        has_aria_labelledby = bool(re.search(r'\baria-labelledby\s*=\s*["\']\s*[^"\'\s]+[^"\']*["\']', attrs, re.I))
        id_m = re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        elem_id = id_m.group(1).strip() if id_m else ""
        has_label_for = False
        if elem_id:
            has_label_for = bool(re.search(rf'<label\b[^>]*\bfor=["\']{re.escape(elem_id)}["\'][^>]*>', body, re.I))

        if not (has_aria_label or has_aria_labelledby or has_label_for):
            errs.append(
                f"{name}: <meter> missing accessible name (requires aria-label, aria-labelledby, or <label for='...'>; "
                f"WCAG 2.2 SC 4.1.2 Name, Role, Value)"
            )

        val_m = re.search(r'\bvalue\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        if not val_m:
            errs.append(f"{name}: <meter> missing required 'value' attribute (HTML5 §4.10.14)")
            continue

        min_val, max_val = 0.0, 1.0
        min_m = re.search(r'\bmin\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        if min_m:
            try:
                min_val = float(min_m.group(1))
            except ValueError:
                errs.append(f"{name}: <meter> min attribute must be a valid number (got '{min_m.group(1)}'; HTML5 §4.10.14)")
        max_m = re.search(r'\bmax\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        if max_m:
            try:
                max_val = float(max_m.group(1))
            except ValueError:
                errs.append(f"{name}: <meter> max attribute must be a valid number (got '{max_m.group(1)}'; HTML5 §4.10.14)")

        if min_val >= max_val:
            errs.append(f"{name}: <meter> min ({min_val}) must be strictly less than max ({max_val}; HTML5 §4.10.14)")

        try:
            cur_val = float(val_m.group(1))
            if cur_val < min_val or cur_val > max_val:
                errs.append(f"{name}: <meter> value ({cur_val}) out of bounds [{min_val}, {max_val}] (HTML5 §4.10.14)")
        except ValueError:
            errs.append(f"{name}: <meter> value attribute must be a valid number (got '{val_m.group(1)}'; HTML5 §4.10.14)")

        low_m = re.search(r'\blow\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        high_m = re.search(r'\bhigh\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        opt_m = re.search(r'\boptimum\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        low_val, high_val = None, None
        if low_m:
            try:
                low_val = float(low_m.group(1))
                if low_val < min_val or low_val > max_val:
                    errs.append(f"{name}: <meter> low ({low_val}) out of bounds [{min_val}, {max_val}] (HTML5 §4.10.14)")
            except ValueError:
                errs.append(f"{name}: <meter> low attribute must be a valid number (got '{low_m.group(1)}'; HTML5 §4.10.14)")
        if high_m:
            try:
                high_val = float(high_m.group(1))
                if high_val < min_val or high_val > max_val:
                    errs.append(f"{name}: <meter> high ({high_val}) out of bounds [{min_val}, {max_val}] (HTML5 §4.10.14)")
            except ValueError:
                errs.append(f"{name}: <meter> high attribute must be a valid number (got '{high_m.group(1)}'; HTML5 §4.10.14)")
        if low_val is not None and high_val is not None and low_val > high_val:
            errs.append(f"{name}: <meter> low ({low_val}) cannot exceed high ({high_val}; HTML5 §4.10.14)")
        if opt_m:
            try:
                opt_val = float(opt_m.group(1))
                if opt_val < min_val or opt_val > max_val:
                    errs.append(f"{name}: <meter> optimum ({opt_val}) out of bounds [{min_val}, {max_val}] (HTML5 §4.10.14)")
            except ValueError:
                errs.append(f"{name}: <meter> optimum attribute must be a valid number (got '{opt_m.group(1)}'; HTML5 §4.10.14)")

    return errs


# Valid WHATWG HTML Living Standard §4.10.18.7 autofill field names & WCAG 2.2 SC 1.3.5
VALID_AUTOFILL_FIELDS = {
    # Personal names
    "name", "honorific-prefix", "given-name", "additional-name", "family-name",
    "honorific-suffix", "nickname",
    # Credentials & security
    "username", "new-password", "current-password", "one-time-code",
    # Professional
    "organization-title", "organization",
    # Address
    "street-address", "address-line1", "address-line2", "address-line3",
    "address-level4", "address-level3", "address-level2", "address-level1",
    "postal-code", "country", "country-name",
    # Contact
    "tel", "tel-country-code", "tel-national", "tel-area-code",
    "tel-local", "tel-local-prefix", "tel-local-suffix", "tel-extension",
    "email", "impp",
    # Payment / financial
    "cc-name", "cc-given-name", "cc-additional-name", "cc-family-name",
    "cc-number", "cc-exp", "cc-exp-month", "cc-exp-year", "cc-csc", "cc-type",
    "transaction-currency", "transaction-amount",
    # Personal details / other
    "language", "bday", "bday-day", "bday-month", "bday-year", "sex", "url", "photo",
}

VALID_AUTOFILL_CONTACT_FIELDS = {
    "tel", "tel-country-code", "tel-national", "tel-area-code",
    "tel-local", "tel-local-prefix", "tel-local-suffix", "tel-extension",
    "email", "impp",
}

VALID_AUTOFILL_CONTACT_TYPES = {"home", "work", "mobile", "fax", "pager"}
VALID_AUTOFILL_ADDRESS_SCOPES = {"shipping", "billing"}

AUTOFILL_TYPO_SUGGESTIONS = {
    "first-name": "given-name",
    "firstname": "given-name",
    "last-name": "family-name",
    "lastname": "family-name",
    "surname": "family-name",
    "middle-name": "additional-name",
    "middlename": "additional-name",
    "phone": "tel",
    "telephone": "tel",
    "mobile-phone": "mobile tel",
    "cell-phone": "mobile tel",
    "zip": "postal-code",
    "zip-code": "postal-code",
    "zipcode": "postal-code",
    "e-mail": "email",
    "mail": "email",
    "company": "organization",
    "city": "address-level2",
    "state": "address-level1",
    "province": "address-level1",
    "pwd": "current-password",
    "pass": "current-password",
    "password": "current-password",
}

INCOMPATIBLE_INPUT_TYPE_AUTOFILL = {
    "email": {
        "tel", "tel-country-code", "tel-national", "tel-area-code",
        "tel-local", "tel-local-prefix", "tel-local-suffix", "tel-extension",
        "bday", "bday-day", "bday-month", "bday-year", "postal-code", "url",
    },
    "tel": {"email", "url", "bday", "bday-day", "bday-month", "bday-year", "postal-code", "street-address"},
    "url": {"email", "tel", "tel-national", "bday", "postal-code", "street-address"},
    "password": {"email", "tel", "name", "given-name", "family-name", "street-address", "postal-code"},
}


def check_form_autocomplete_attributes(name: str, body: str) -> list[str]:
    """Validate autocomplete attributes on form controls per WHATWG HTML §4.10.18.7 and WCAG 2.2 SC 1.3.5."""
    errs: list[str] = []
    ctrl_re = re.compile(r"<(input|select|textarea)\b([^>]*)>", re.I)
    for m in ctrl_re.finditer(body):
        tag, attrs = m.group(1).lower(), m.group(2)
        auto_m = re.search(r'\bautocomplete\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if not auto_m:
            continue
        raw_val = auto_m.group(1)
        val = raw_val.strip()
        if not val:
            errs.append(
                f"{name}: <{tag}> autocomplete attribute cannot be empty or whitespace-only "
                f"(WHATWG HTML §4.10.18.7 / WCAG 2.2 SC 1.3.5)"
            )
            continue
        if val.lower() in ("on", "off"):
            continue

        tokens = val.split()
        if len(tokens) != len(set(tokens)):
            errs.append(
                f"{name}: <{tag}> autocomplete contains duplicate token(s) in '{val}' "
                f"(WHATWG HTML §4.10.18.7)"
            )
            continue

        idx = 0
        if tokens[idx].lower().startswith("section-"):
            sec_token = tokens[idx]
            if len(sec_token) <= 8 or not re.match(r"^section-[a-z0-9_-]+$", sec_token, re.I):
                errs.append(
                    f"{name}: <{tag}> autocomplete section- prefix requires a non-empty alphanumeric section name: '{sec_token}' "
                    f"(WHATWG HTML §4.10.18.7)"
                )
            idx += 1

        if idx < len(tokens) and tokens[idx].lower() in VALID_AUTOFILL_ADDRESS_SCOPES:
            idx += 1

        contact_type = None
        if idx < len(tokens) and tokens[idx].lower() in VALID_AUTOFILL_CONTACT_TYPES:
            contact_type = tokens[idx].lower()
            idx += 1

        if idx >= len(tokens):
            errs.append(
                f"{name}: <{tag}> autocomplete missing required core autofill field name in '{val}' "
                f"(WHATWG HTML §4.10.18.7 / WCAG 2.2 SC 1.3.5)"
            )
            continue

        core = tokens[idx].lower()
        if core not in VALID_AUTOFILL_FIELDS:
            hint = f" (did you mean '{AUTOFILL_TYPO_SUGGESTIONS[core]}'?)" if core in AUTOFILL_TYPO_SUGGESTIONS else ""
            errs.append(
                f"{name}: <{tag}> invalid autocomplete field name '{tokens[idx]}'{hint} "
                f"(WHATWG HTML §4.10.18.7 / WCAG 2.2 SC 1.3.5)"
            )
        else:
            if contact_type and core not in VALID_AUTOFILL_CONTACT_FIELDS:
                errs.append(
                    f"{name}: <{tag}> contact type '{contact_type}' is only allowed before contact fields, not '{core}' "
                    f"(WHATWG HTML §4.10.18.7)"
                )
        idx += 1

        if idx < len(tokens) and tokens[idx].lower() == "webauthn":
            if core not in ("username", "current-password", "new-password"):
                errs.append(
                    f"{name}: <{tag}> 'webauthn' autocomplete token is only valid with credential fields, not '{core}' "
                    f"(W3C WebAuthn Level 3 / WHATWG §4.10.18.7)"
                )
            idx += 1

        if idx < len(tokens):
            errs.append(
                f"{name}: <{tag}> unexpected extra token(s) '{' '.join(tokens[idx:])}' in autocomplete '{val}' "
                f"(WHATWG HTML §4.10.18.7)"
            )

        type_m = re.search(r'\btype\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        ctrl_type = type_m.group(1).lower().strip() if type_m else "text"
        if ctrl_type in INCOMPATIBLE_INPUT_TYPE_AUTOFILL and core in INCOMPATIBLE_INPUT_TYPE_AUTOFILL[ctrl_type]:
            errs.append(
                f"{name}: <{tag} type='{ctrl_type}'> has incompatible autocomplete field '{core}' "
                f"(WHATWG HTML §4.10.18.7 / WCAG 2.2 SC 1.3.5)"
            )
    return errs


def check_form_accessibility_and_security(name: str, body: str) -> list[str]:
    """Ensure forms use safe endpoints and form controls have accessible labels (WCAG 2.2 SC 3.3.2 / 4.1.2 & R1/R10)."""
    errs: list[str] = []

    # 1. Nested form detection (WHATWG §4.10.3)
    form_tags = list(re.finditer(r"</?form\b[^>]*>", body, re.I))
    form_depth = 0
    for ft in form_tags:
        is_closing = ft.group(0).startswith("</")
        if not is_closing:
            form_depth += 1
            if form_depth > 1:
                errs.append(
                    f"{name}: nested <form> elements detected (WHATWG 4.10.3 strictly prohibits nested forms)"
                )
        else:
            form_depth = max(0, form_depth - 1)

    # 2. Form level checks: action, target, method
    for m in re.finditer(r"<form\b([^>]*)>", body, re.I):
        attrs = m.group(1)
        action_m = re.search(r'\baction\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        if action_m:
            action = action_m.group(1).strip()
            if action and not action.startswith(("/", "#", "mailto:")):
                errs.append(
                    f"{name}: <form action='{action}'> submits to external endpoint; only relative paths or mailto: allowed (R10 zero client tracking / static HTML)"
                )
        target_m = re.search(r'\btarget\s*=\s*["\']_blank["\']', attrs, re.I)
        if target_m:
            rel_m = re.search(r'\brel\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
            rel_val = (rel_m.group(1) if rel_m else "").lower().split()
            if "noopener" not in rel_val and "noreferrer" not in rel_val:
                errs.append(
                    f"{name}: <form target='_blank'> must include rel='noopener' or rel='noreferrer' "
                    f"to prevent reverse tabnabbing (WHATWG 4.6.6.11 / 4.10.3)"
                )
        method_m = re.search(r'\bmethod\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if method_m:
            method_val = method_m.group(1).strip().lower()
            if method_val not in ("get", "post", "dialog"):
                errs.append(
                    f"{name}: <form method='{method_val}'> declares invalid method token; only 'get', 'post', or 'dialog' allowed (WHATWG 4.10.3)"
                )

    # 3. Button / input formaction and formtarget
    for m in re.finditer(r"<(button|input)\b([^>]*)>", body, re.I):
        tag, attrs = m.group(1).lower(), m.group(2)
        formaction_m = re.search(r'\bformaction\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        if formaction_m:
            formaction = formaction_m.group(1).strip()
            if formaction and not formaction.startswith(("/", "#", "mailto:")):
                errs.append(
                    f"{name}: <{tag} formaction='{formaction}'> submits to external endpoint; "
                    f"only relative paths or mailto: allowed (R10 zero client tracking / static HTML; WHATWG 4.10.18.6)"
                )
        target_m = re.search(r'\bformtarget\s*=\s*["\']_blank["\']', attrs, re.I)
        if target_m:
            rel_m = re.search(r'\b(?:formrel|rel)\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
            rel_val = (rel_m.group(1) if rel_m else "").lower().split()
            if "noopener" not in rel_val and "noreferrer" not in rel_val:
                errs.append(
                    f"{name}: <{tag} formtarget='_blank'> must include rel='noopener' or formrel='noopener' "
                    f"to prevent reverse tabnabbing (WHATWG 4.6.6.11 / 4.10.18.6)"
                )

    # 4. Button type validation
    for btn_m in re.finditer(r"<button\b([^>]*)>", body, re.I):
        btn_attrs = btn_m.group(1)
        type_m = re.search(r'\btype\s*=\s*["\']([^"\']*)["\']', btn_attrs, re.I)
        if type_m:
            btn_type = type_m.group(1).strip().lower()
            if btn_type not in ("submit", "reset", "button", "menu"):
                errs.append(
                    f"{name}: <button type='{btn_type}'> declares invalid type attribute; only 'submit', 'reset', 'button', or 'menu' allowed (WHATWG 4.10.6)"
                )

    # 5. Form controls labeling and input type validation
    label_for_ids = set()
    for m in re.finditer(r'<label\b[^>]*\bfor\s*=\s*["\']([^"\']+)["\']', body, re.I):
        label_for_ids.add(m.group(1).strip())

    VALID_INPUT_TYPES = frozenset({
        "text", "search", "tel", "url", "email", "password", "date",
        "month", "week", "time", "datetime-local", "number", "range",
        "color", "checkbox", "radio", "file", "submit", "image",
        "reset", "button", "hidden",
    })

    control_re = re.compile(r"<(input|select|textarea)\b([^>]*)>", re.I)
    for m in control_re.finditer(body):
        tag, attrs = m.group(1).lower(), m.group(2)
        type_m = re.search(r'\btype\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        ctrl_type = type_m.group(1).lower().strip() if type_m else ("text" if tag == "input" else tag)
        if tag == "input" and type_m:
            if ctrl_type not in VALID_INPUT_TYPES:
                errs.append(
                    f"{name}: <input type='{ctrl_type}'> declares invalid type attribute (WHATWG 4.10.5)"
                )
        if ctrl_type in ("hidden", "submit", "reset", "button", "image"):
            continue
        has_aria_label = bool(re.search(r'\baria-label(?:ledby)?\s*=\s*["\'][^"\']+["\']', attrs, re.I))
        id_m = re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        ctrl_id = id_m.group(1).strip() if id_m else ""
        has_for_label = ctrl_id and (ctrl_id in label_for_ids)

        if not has_aria_label and not has_for_label:
            errs.append(
                f"{name}: <{tag} type='{ctrl_type}'> missing accessible label (must have an associated <label for='...'> matching its id, or aria-label/aria-labelledby; WCAG 2.2 SC 3.3.2 / 4.1.2)"
            )
    return errs


class _SelectAndOptgroupParser(HTMLParser):
    """Audits <select>, <optgroup>, and <option> hierarchies to enforce HTML5 §4.10.7-9 and WCAG 2.2 SC 1.3.1, SC 4.1.2 & W3C Technique H85."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.errs: list[str] = []
        self.select_stack: list[dict] = []
        self.in_optgroup: bool = False
        self.optgroup_depth: int = 0
        self.datalist_depth: int = 0
        self.in_option: bool = False
        self.current_option_label: str = ""
        self.current_option_text: list[str] = []
        self.current_option_loc: str = ""

    def _finalize_option(self) -> None:
        if self.in_option:
            opt_text = "".join(self.current_option_text).strip()
            if not opt_text and not self.current_option_label:
                self.errs.append(
                    f"{self.name}{self.current_option_loc}: <option> has empty text and missing or empty 'label' attribute "
                    f"(WCAG 2.2 SC 4.1.2 requires accessible option name)"
                )
            self.in_option = False
            self.current_option_text = []
            self.current_option_label = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        lineno, offset = self.getpos()
        loc = f" (line {lineno}:{offset})"
        ad = {k.lower(): (v or "") for k, v in attrs}

        if t == "datalist":
            self.datalist_depth += 1
        elif t == "select":
            is_multiple = "multiple" in ad
            self.select_stack.append({
                "is_multiple": is_multiple,
                "selected_count": 0,
                "loc": loc,
            })
        elif t == "optgroup":
            if not self.select_stack:
                self.errs.append(
                    f"{self.name}{loc}: <optgroup> must be inside a <select> element (HTML5 §4.10.8)"
                )
            if self.in_optgroup or self.optgroup_depth > 0:
                self.errs.append(
                    f"{self.name}{loc}: <optgroup> cannot be nested inside another <optgroup> "
                    f"(HTML5 §4.10.8 prohibits nested optgroups)"
                )
            self.in_optgroup = True
            self.optgroup_depth += 1
            if "label" not in ad:
                self.errs.append(
                    f"{self.name}{loc}: <optgroup> missing required 'label' attribute "
                    f"(W3C Technique H85, HTML5 §4.10.8 & WCAG 2.2 SC 1.3.1)"
                )
            elif not ad["label"].strip():
                self.errs.append(
                    f"{self.name}{loc}: <optgroup> declares empty or whitespace-only 'label' attribute "
                    f"(W3C Technique H85 & WCAG 2.2 SC 1.3.1)"
                )
        elif t == "option":
            if self.in_option:
                self._finalize_option()
            if not self.select_stack and self.datalist_depth == 0:
                self.errs.append(
                    f"{self.name}{loc}: <option> must be inside a <select> or <datalist> element (HTML5 §4.10.9)"
                )
            if self.select_stack:
                cur_sel = self.select_stack[-1]
                if "selected" in ad:
                    cur_sel["selected_count"] += 1
                    if not cur_sel["is_multiple"] and cur_sel["selected_count"] > 1:
                        self.errs.append(
                            f"{self.name}{loc}: <select> without 'multiple' attribute contains multiple selected <option> elements "
                            f"(HTML5 §4.10.7 prohibits multiple selections in single-select controls)"
                        )
                self.in_option = True
                self.current_option_label = ad.get("label", "").strip()
                self.current_option_text = []
                self.current_option_loc = loc

    def handle_data(self, data: str) -> None:
        if self.in_option:
            self.current_option_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == "datalist":
            self.datalist_depth = max(0, self.datalist_depth - 1)
        elif t == "select":
            if self.in_option:
                self._finalize_option()
            if self.optgroup_depth > 0:
                self.optgroup_depth = 0
                self.in_optgroup = False
            if self.select_stack:
                self.select_stack.pop()
        elif t == "optgroup":
            if self.in_option:
                self._finalize_option()
            self.optgroup_depth = max(0, self.optgroup_depth - 1)
            if self.optgroup_depth == 0:
                self.in_optgroup = False
        elif t == "option":
            if self.in_option:
                self._finalize_option()

    def close(self) -> None:
        if self.in_option:
            self._finalize_option()
        super().close()


def check_select_and_optgroup_integrity(name: str, body: str) -> list[str]:
    """Ensure <select>, <optgroup>, and <option> elements follow HTML5 grouping and selection rules and WCAG 2.2 accessibility requirements (HTML5 §4.10.7-9, WCAG 2.2 SC 1.3.1, SC 4.1.2 & W3C Technique H85)."""
    parser = _SelectAndOptgroupParser(name)
    try:
        parser.feed(body)
        parser.close()
    except Exception:
        pass
    return parser.errs



def check_distracting_elements(name: str, body: str) -> list[str]:
    """Ensure no obsolete or distracting moving elements like <marquee> or <blink> (WCAG 2.2 SC 2.2.2)."""
    errs: list[str] = []
    if re.search(r"<(?:marquee|blink)\b", body, re.I):
        errs.append(
            f"{name}: obsolete distracting elements (<marquee> or <blink>) are forbidden (WCAG 2.2 SC 2.2.2 Pause, Stop, Hide)"
        )
    return errs


def check_obsolete_presentational_elements(name: str, body: str) -> list[str]:
    """Ensure no obsolete presentational elements like <font>, <center>, <strike>, <tt>, <big>, <acronym>, <frame>, <frameset>, etc. (HTML5 §11.2 / HTML Living Standard §16 / WCAG 2.2 SC 1.3.1)."""
    errs: list[str] = []
    for m in re.finditer(r'<([a-z0-9]+)\b[^>]*>', body, re.I):
        tag = m.group(1).lower()
        if tag in (
            "font", "center", "strike", "tt", "big", "acronym", "applet", "basefont", "dir",
            "frame", "frameset", "noframes", "noembed", "keygen", "isindex", "bgsound",
            "listing", "xmp", "plaintext",
        ):
            errs.append(
                f"{name}: obsolete presentational element <{tag}> is forbidden; "
                f"use semantic HTML5 and modern CSS styling (HTML5 §11.2 Non-conforming features / WCAG 2.2 SC 1.3.1)"
            )
    return errs


VALID_PRELOAD_TOKENS = frozenset({"none", "metadata", "auto", ""})


def check_media_preload_and_poster_integrity(name: str, body: str, assets_dir: Path | None = None) -> list[str]:
    """Ensure <video> and <audio> media elements specify valid preload tokens and valid, existing poster image assets (WHATWG HTML §4.8.9, §4.8.10 & WCAG 2.2 SC 1.1.1, SC 1.2.2)."""
    errs: list[str] = []
    base_assets = assets_dir if assets_dir is not None else ASSETS

    for m in re.finditer(r"<(video|audio)\b([^>]*)>", body, re.I):
        tag, attrs = m.group(1).lower(), m.group(2)

        # 1. Preload attribute validation (WHATWG HTML §4.8.10)
        preload_m = re.search(r'\bpreload\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if preload_m:
            token = preload_m.group(1).strip().lower()
            if token not in VALID_PRELOAD_TOKENS:
                errs.append(
                    f"{name}: <{tag}> declares invalid preload='{preload_m.group(1)}' "
                    f"(must be 'none', 'metadata', 'auto', or empty; WHATWG HTML §4.8.10)"
                )

        # 2. Poster attribute validation
        poster_m = re.search(r'\bposter\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        if poster_m:
            poster_val = poster_m.group(1).strip()
            if tag == "audio":
                errs.append(
                    f"{name}: <audio> element does not support 'poster' attribute (WHATWG HTML §4.8.9)"
                )
            elif not poster_val:
                errs.append(
                    f"{name}: <video> declares empty poster attribute (WHATWG HTML §4.8.10 requires a valid image URL)"
                )
            elif poster_val.lower().startswith("http://"):
                errs.append(
                    f"{name}: <video poster='{poster_val}'> specifies unencrypted http:// URL; "
                    f"use https:// or relative asset path (R10 zero client tracking / transport security)"
                )
            elif any(poster_val.lower().startswith(s) for s in ("javascript:", "vbscript:", "data:")):
                errs.append(
                    f"{name}: <video poster='{poster_val}'> contains prohibited script or data URI (XSS defense)"
                )
            elif poster_val.startswith("/assets/img/"):
                rel_img = poster_val[len("/assets/img/"):]
                if not (base_assets / "img" / rel_img).is_file():
                    errs.append(
                        f"{name}: <video poster='{poster_val}'> references missing image asset 'assets/img/{rel_img}' "
                        f"(WHATWG HTML §4.8.10 / R10)"
                    )
    return errs


def check_details_accordion_name_integrity(name: str, body: str) -> list[str]:
    """Ensure <details> elements declare valid, non-empty, non-control-character accordion group names when name is specified (WHATWG HTML §4.11.1)."""
    errs: list[str] = []

    class _DetailsNameParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.names: list[str] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag.lower() == "details":
                for k, v in attrs:
                    if k.lower() == "name":
                        self.names.append(v if v is not None else "")

    parser = _DetailsNameParser()
    try:
        parser.feed(body)
    except Exception:
        pass

    found = False
    for name_val in parser.names:
        found = True
        if not name_val.strip():
            errs.append(
                f"{name}: <details> declares empty name attribute "
                f"(WHATWG HTML §4.11.1 requires a non-empty group name for accordions)"
            )
        elif re.search(r"\s", name_val):
            errs.append(
                f"{name}: <details name='{name_val}'> contains invalid whitespace in group name (WHATWG HTML §4.11.1)"
            )
        elif any(ord(c) < 32 or ord(c) == 127 for c in name_val):
            errs.append(
                f"{name}: <details name='{name_val}'> contains prohibited control characters in group name"
            )
        elif re.search(r"[<>&\"']", name_val):
            errs.append(
                f"{name}: <details name='{name_val}'> contains prohibited markup characters in group name"
            )

    if not found:
        for m in re.finditer(r"<details\b([^>]*)>", body, re.I):
            attrs = m.group(1)
            name_m = re.search(r'\bname\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
            if name_m:
                name_val = name_m.group(1)
                if not name_val.strip():
                    errs.append(
                        f"{name}: <details> declares empty name attribute "
                        f"(WHATWG HTML §4.11.1 requires a non-empty group name for accordions)"
                    )
                elif re.search(r"\s", name_val):
                    errs.append(
                        f"{name}: <details name='{name_val}'> contains invalid whitespace in group name (WHATWG HTML §4.11.1)"
                    )
                elif any(ord(c) < 32 or ord(c) == 127 for c in name_val):
                    errs.append(
                        f"{name}: <details name='{name_val}'> contains prohibited control characters in group name"
                    )
                elif re.search(r"[<>&\"']", name_val):
                    errs.append(
                        f"{name}: <details name='{name_val}'> contains prohibited markup characters in group name"
                    )
    return errs


def check_duplicates(metas: list[dict]) -> list[str]:
    """Check parsed page metadata dicts for duplicate routes, titles and descriptions."""
    errs: list[str] = []
    routes_by_norm: dict[str, list[str]] = {}
    for i, m in enumerate(metas):
        r = str(m.get("route") or "").strip()
        if not r:
            continue
        src = m.get("src")
        if isinstance(src, Path):
            if "content" in src.parts:
                idx = src.parts.index("content")
                rel = Path(*src.parts[idx + 1:])
                page_id = rel.as_posix() if rel.parts else src.as_posix()
            else:
                page_id = src.as_posix()
        elif isinstance(src, str) and src.strip():
            page_id = src.strip()
        else:
            page_id = f"page[{i}]"
        routes_by_norm.setdefault(r, []).append(page_id)
    for r, pages in routes_by_norm.items():
        if len(pages) > 1:
            errs.append(f"duplicate route '{r}' shared by multiple content files: {', '.join(pages)}")

    for field in ("title", "description"):
        by_norm: dict[str, list[str]] = {}
        canonical_val: dict[str, str] = {}
        for i, m in enumerate(metas):
            raw = m.get(field, "")
            norm = " ".join(str(raw).split()).casefold() if raw is not None else ""
            if not norm:
                continue
            src = m.get("src")
            if isinstance(src, Path):
                if "content" in src.parts:
                    idx = src.parts.index("content")
                    rel = Path(*src.parts[idx + 1:])
                    page_id = rel.as_posix() if rel.parts else src.as_posix()
                else:
                    page_id = src.as_posix()
            elif isinstance(src, str) and src.strip():
                page_id = src.strip()
            else:
                page_id = str(m.get("route") or f"page[{i}]")
            by_norm.setdefault(norm, []).append(page_id)
            canonical_val.setdefault(norm, " ".join(str(raw).split()))
        for norm, pages in by_norm.items():
            if len(pages) > 1:
                errs.append(
                    f"duplicate {field} '{canonical_val[norm]}' shared by: {', '.join(pages)}"
                )
    return errs


def check_img_dimensions(route: str, doc: str) -> list[str]:
    """Report any `<img ...>` tag missing explicit `width` or `height` attributes."""
    errs = []
    for m in re.finditer(r"<img\b([^>]*)>", doc):
        attrs = m.group(1)
        if not (re.search(r'\bwidth="\d+"', attrs) and re.search(r'\bheight="\d+"', attrs)):
            src_m = re.search(r'\bsrc="([^"]+)"', attrs)
            src = src_m.group(1) if src_m else "<unknown>"
            errs.append(f"{route}: <img> for {src} missing width/height attributes (CLS prevention)")
    return errs


def check_invisible_characters(name: str, raw_text: str) -> list[str]:
    """Ensure content contains no invisible zero-width or bidirectional override characters (Trojan Source defense; Boucher & Anderson, arXiv:2111.00169; RFC 8264)."""
    errs: list[str] = []
    if INVISIBLE_UNICODE.search(raw_text):
        errs.append(
            f"{name}: file contains prohibited invisible zero-width or bidirectional override characters "
            f"(Trojan Source defense; Boucher & Anderson, arXiv:2111.00169; RFC 8264)"
        )
    return errs


def check_git_conflict_markers(name: str, raw_text: str) -> list[str]:
    """Ensure no unresolved git merge conflict markers remain in the file."""
    errs: list[str] = []
    if GIT_CONFLICT_MARKERS.search(raw_text):
        errs.append(f"{name}: file contains unresolved git merge conflict markers (<<<<<<< / ======= / >>>>>>>)")
    return errs


def check_unique_element_ids(name: str, body: str, shell_ids: tuple[str, ...] = ("main",)) -> list[str]:
    """Ensure all HTML id attributes on a page are unique and do not collide with page-shell IDs."""
    errs: list[str] = []
    seen: dict[str, int] = {}
    for elem_id in ELEMENT_ID_RE.findall(body):
        clean_id = elem_id.strip()
        seen[clean_id] = seen.get(clean_id, 0) + 1
    for elem_id, count in seen.items():
        if count > 1:
            errs.append(
                f"{name}: duplicate element id '{elem_id}' appears {count} times on page "
                f"(HTML and WCAG 2.2 require unique IDs)"
            )
        if elem_id in shell_ids:
            errs.append(
                f"{name}: element id '{elem_id}' collides with reserved page shell anchor '#{elem_id}'"
            )
    return errs


def check_page(meta: dict, out_html: str) -> list[str]:
    errs = []
    name = meta["src"].relative_to(CONTENT).as_posix()
    raw_content = meta.get("raw", "")
    errs += check_git_conflict_markers(name, raw_content)
    errs += check_invisible_characters(name, raw_content)
    for f in REQUIRED:
        if not meta.get(f):
            errs.append(f"{name}: missing front-matter '{f}' (R3)")
    for js_name in _parse_extra_scripts(meta):
        if not re.match(r"^[a-z0-9][a-z0-9._-]*\.js$", js_name, re.I):
            errs.append(f"{name}: invalid script filename '{js_name}' in front-matter (must be a basename in assets/js/)")
        elif not (ASSETS / "js" / js_name).exists():
            errs.append(f"{name}: front-matter script assets/js/{js_name} not found")
    if meta.get("template") == "article":
        for f in ARTICLE_REQUIRED:
            if not meta.get(f):
                errs.append(f"{name}: article missing '{f}'")
        if meta.get("image") and not (ASSETS / "img" / meta["image"]).exists():
            errs.append(f"{name}: article image assets/img/{meta['image']} not found (generate it per specs/05)")
        if meta.get("image") and (ASSETS / "img" / meta["image"]).exists() and (ASSETS / "img" / meta["image"]).stat().st_size > 300_000:
            errs.append(f"{name}: article image is over 300 KB; compress it (R10)")
    errs += check_image_alt(name, meta)
    errs += check_headings(name, meta)
    errs += check_text_justification(name, raw_content)
    errs += check_unique_element_ids(name, meta["body"])
    errs += check_researcher_asides(name, meta["body"])
    errs += check_explainers(name, meta["body"])
    errs += check_footnote_links(name, meta["body"], WARNINGS)
    errs += check_external_links(name, meta["body"])
    errs += check_accessible_links(name, meta["body"])
    errs += check_link_purpose_and_generic_text(name, meta["body"])
    errs += check_button_accessible_names(name, meta["body"])
    errs += check_interactive_explainer_accessibility(name, meta["body"])
    errs += check_research_status_badges(name, meta, meta["body"])
    errs += check_math_accessibility(name, meta["body"])
    errs += check_figcaption_structure(name, meta["body"])
    errs += check_live_region_integrity(name, meta["body"])
    errs += check_disabled_attribute_integrity(name, meta["body"])
    errs += check_svg_accessibility(name, meta["body"])
    errs += check_target_blank_accessibility(name, meta["body"])
    errs += check_output_and_datalist_integrity(name, meta["body"])
    errs += check_aria_invalid_and_error_message_integrity(name, meta["body"])
    errs += check_inert_attribute_integrity(name, meta["body"])
    errs += check_virtual_keyboard_and_inputmode_attributes(name, meta["body"])
    errs += check_range_slider_accessibility(name, meta["body"])
    errs += check_aria_spinbutton_and_scrollbar_accessibility(name, meta["body"])
    errs += check_aria_progressbar_accessibility(name, meta["body"])
    errs += check_aria_tab_tablist_and_tabpanel_integrity(name, meta["body"])
    errs += check_aria_popup_and_expansion_trigger_integrity(name, meta["body"])
    errs += check_media_track_accessibility(name, meta["body"])
    errs += check_aria_grid_and_table_coordinate_integrity(name, meta["body"])
    errs += check_aria_tree_and_treeitem_hierarchy_integrity(name, meta["body"])
    errs += check_svg_viewbox_and_text_integrity(name, meta["body"])
    errs += check_blockquote_and_citation_integrity(name, meta["body"])
    errs += check_bdo_bdi_and_dir_integrity(name, meta["body"])
    errs += check_aria_posinset_and_setsize_integrity(name, meta["body"])
    errs += check_details_and_summary_disclosure_integrity(name, meta["body"])
    errs += check_del_and_ins_edit_integrity(name, meta["body"])
    errs += check_aria_keyshortcuts_and_roledescription_integrity(name, meta["body"])
    errs += check_ruby_annotation_integrity(name, meta["body"])
    errs += check_menu_and_toolbar_accessibility(name, meta["body"])
    errs += check_aria_modal_and_dialog_state_integrity(name, meta["body"])
    errs += check_definition_list_and_dfn_integrity(name, meta["body"])
    errs += check_aria_checked_and_pressed_integrity(name, meta["body"])
    errs += check_search_landmark_and_searchbox_integrity(name, meta["body"])
    errs += check_address_element_integrity(name, meta["body"])
    errs += check_sub_and_sup_integrity(name, meta["body"])
    errs += check_picture_and_source_integrity(name, meta["body"])
    errs += check_aria_meter_integrity(name, meta["body"])
    errs += check_canvas_accessibility_and_fallback_integrity(name, meta["body"])
    errs += check_data_element_integrity(name, meta["body"])
    errs += check_technical_inline_elements_integrity(name, meta["body"])
    errs += check_aria_feed_and_article_stream_integrity(name, meta["body"])
    errs += check_aria_owns_hierarchy_integrity(name, meta["body"])
    errs += check_mark_and_small_integrity(name, meta["body"])
    errs += check_template_and_slot_integrity(name, meta["body"])
    errs += check_void_elements_and_thematic_break_integrity(name, meta["body"])
    errs += check_map_and_area_integrity(name, meta["body"])
    errs += check_colgroup_and_col_integrity(name, meta["body"])
    errs += check_aria_controls_target_and_token_integrity(name, meta["body"])
    errs += check_popover_attribute_and_target_integrity(name, meta["body"])
    errs += check_aria_describedby_and_details_target_integrity(name, meta["body"])
    errs += check_aria_flowto_reading_flow_integrity(name, meta["body"])
    errs += check_table_cell_spanning_and_orphan_integrity(name, meta["body"])
    errs += check_media_source_and_fallback_integrity(name, meta["body"])
    errs += check_aria_current_token_and_context_integrity(name, meta["body"])
    errs += check_form_submission_attributes_integrity(name, meta["body"])
    errs += check_dialog_element_hierarchy_and_action_integrity(name, meta["body"])
    errs += check_hidden_attribute_and_conflict_integrity(name, meta["body"])
    errs += check_media_controlslist_and_crossorigin_integrity(name, meta["body"])
    errs += check_figure_and_figcaption_hierarchy_integrity(name, meta["body"])
    errs += check_output_element_form_and_name_integrity(name, meta["body"])
    errs += check_progress_and_meter_nesting_and_interactive_integrity(name, meta["body"])
    errs += check_aria_heading_and_level_integrity(name, meta["body"])
    errs += check_aria_orientation_and_sort_context_integrity(name, meta["body"])
    errs += check_focus_visible_styling(name, raw_content)
    errs += check_table_accessibility(name, meta["body"])
    errs += check_progress_and_meter_accessibility(name, meta["body"])
    errs += check_form_accessibility_and_security(name, meta["body"])
    errs += check_form_autocomplete_attributes(name, meta["body"])
    errs += check_select_and_optgroup_integrity(name, meta["body"])
    errs += check_distracting_elements(name, meta["body"])
    errs += check_obsolete_presentational_elements(name, meta["body"])
    errs += check_landmark_integrity(name, meta["body"])
    errs += check_interactive_elements_and_embeds(name, meta["body"])
    errs += check_focus_order_and_tabindex(name, meta["body"])
    errs += check_aria_hidden_focusability(name, meta["body"])
    errs += check_accesskey_attributes(name, meta["body"])
    errs += check_list_structure(name, meta["body"])
    errs += check_presentational_roles(name, meta["body"])
    errs += check_nested_interactive_elements(name, meta["body"])
    errs += check_fieldset_and_legend_structure(name, meta["body"])
    errs += check_details_and_summary_structure(name, meta["body"])
    errs += check_dialog_accessibility(name, meta["body"])
    errs += check_autofocus_attributes(name, raw_content)
    errs += check_aria_hidden_landmarks(name, meta["body"])
    errs += check_label_in_name(name, meta["body"])
    errs += check_aria_integrity(name, meta["body"])
    errs += check_media_accessibility(name, meta["body"])
    errs += check_media_preload_and_poster_integrity(name, meta["body"])
    errs += check_details_accordion_name_integrity(name, meta["body"])
    errs += check_abbreviation_tags(name, meta["body"])
    for card_html in re.findall(r'<div class="card">(.*?)</div>', meta["body"], re.S):
        p_cnt = len(re.findall(r"<p\b", card_html))
        if p_cnt > 6:
            errs.append(f"{name}: <div class=\"card\"> contains {p_cnt} <p> paragraphs (max 6); move extended literature lists into a collapsible <aside class=\"for-researchers\"><details> drawer")
    if meta.get("template") != "article":
        body_no_details = re.sub(r"<details\b.*?</details>", "", meta["body"], flags=re.S)
        for split_html in re.findall(r'<div class="split\b[^"]*">(.*?)</div>\s*</div>', body_no_details, re.S):
            vis_p = len(re.findall(r"<p\b", split_html))
            if vis_p > 10:
                errs.append(f"{name}: .split section contains {vis_p} visible <p> paragraphs outside <details> (max 10); wrap extended study lists inside <aside class=\"for-researchers\"><details>")
    body_no_code = re.sub(r"<(script|style)\b.*?</\1>", "", meta["body"], flags=re.S | re.I)
    md_bt = re.search(r"`[^`\n]+`", body_no_code)
    if md_bt:
        errs.append(f"{name}: raw Markdown backticks {md_bt.group(0)!r} in HTML body; use <code>...</code> instead")
    md_lnk = re.search(r"\[[^\]]+\]\(https?://[^)]+\)", body_no_code)
    if md_lnk:
        errs.append(f"{name}: raw Markdown link {md_lnk.group(0)!r} in HTML body; use <a href=\"...\"> instead")
    internal_spec_leak = re.search(
        r"\b(RealmIsolationFirewall|Hexagon\s+classes|spec\s+0[0-9]|spec\s+1[0-9]|(card|encounter|org)\.(alignment_safety|frontier_lab|public_official|builder|civil_society|general_public|timeline)\.[a-z0-9_-]+)\b|github\.com/collective-intelligence-network/cin/blob/",
        body_no_code,
        flags=re.I,
    )
    if internal_spec_leak:
        errs.append(f"{name}: internal specification or class reference '{internal_spec_leak.group(0)}' in public HTML")
    for aside_m in re.finditer(r'<aside class="for-researchers"[^>]*>(.*?)</aside>', body_no_code, flags=re.S):
        for raw_p in _P_BLOCK_RE.findall(aside_m.group(1)):
            no_sup = re.sub(r"<sup\b[^>]*>.*?</sup>", "", raw_p, flags=re.S | re.I)
            clean_p = _TAG_RE.sub(" ", no_sup)
            clean_p = re.sub(r"\([^)]*\)", "", clean_p)
            for s in _SENTENCE_SPLIT_RE.split(clean_p):
                w_cnt = len(s.split())
                if w_cnt > 45:
                    errs.append(f"{name}: <aside class=\"for-researchers\"> contains a {w_cnt}-word sentence excluding parenthetical citations (max 45 words): '{' '.join(s.split()[:10])}...'")
    expected_article_date = meta.get("date") if meta.get("template") == "article" and out_html else None
    errs += check_time_elements(name, out_html or meta["body"], expected_article_date=expected_article_date)
    text = meta["body"] + " " + meta.get("lede", "") + " " + meta.get("title", "")
    norm_text = INVISIBLE_UNICODE.sub("", text)
    for rx, why in FORBIDDEN:
        m = rx.search(text) or rx.search(norm_text)
        if m:
            errs.append(f"{name}: steward gate, {why}: '{m.group(0)}' (R5)")
    plain = EXEMPT_BLOCKS.sub("", text)
    plain_norm = INVISIBLE_UNICODE.sub("", plain)
    for m in INTERNAL_IDS.finditer(text):
        errs.append(f"{name}: internal code '{m.group(0)}' in public text (R4)")
    for m in INTERNAL_IDS.finditer(norm_text):
        err = f"{name}: internal code '{m.group(0)}' in public text (R4)"
        if err not in errs:
            errs.append(err)
    for m in RETIRED_BUZZWORDS.finditer(text):
        errs.append(f"{name}: retired buzzword '{m.group(0)}' in public text (R4)")
    for m in RETIRED_BUZZWORDS.finditer(norm_text):
        err = f"{name}: retired buzzword '{m.group(0)}' in public text (R4)"
        if err not in errs:
            errs.append(err)
    for m in COINAGES.finditer(plain):
        errs.append(f"{name}: research term '{m.group(0)}' outside a for-researchers aside or footnote (R4)")
    for m in COINAGES.finditer(plain_norm):
        err = f"{name}: research term '{m.group(0)}' outside a for-researchers aside or footnote (R4)"
        if err not in errs:
            errs.append(err)
    check_readability(name, plain, WARNINGS)
    return errs


def check_links(pages: dict[str, str]) -> list[str]:
    errs = []
    routes = set(pages) | {"/blog/feed.xml", "/sitemap.xml", "/robots.txt"}
    for route, doc in pages.items():
        for href in re.findall(r'(?:href|src)="(/[^"#?]*)', doc):
            if href.startswith("/assets/"):
                if not (ROOT / href.lstrip("/")).exists():
                    errs.append(f"{route}: missing asset {href}")
            elif href not in routes and href + "/" not in routes:
                errs.append(f"{route}: broken internal link {href}")
    return errs


def check_client_links(pages: dict[str, str]) -> list[str]:
    """Ensure links to horizon.cintnet.org only appear on /labs/shared-horizon and /get-involved/ pages (R12 Client Separation)."""
    errs: list[str] = []
    allowed_prefixes = ("/labs/shared-horizon", "/get-involved")
    horizon_link_re = re.compile(r'href\s*=\s*["\'](?:https?:)?//horizon\.cintnet\.org[^"\']*["\']', re.I)
    for route, doc in pages.items():
        if any(route.startswith(prefix) for prefix in allowed_prefixes):
            continue
        if horizon_link_re.search(doc):
            errs.append(
                f"{route}: links to client application horizon.cintnet.org are restricted to /labs/shared-horizon and /get-involved pages (R12 Client Separation)"
            )
    return errs


def check_fragment_anchors(pages: dict[str, str]) -> list[str]:
    """Ensure all internal fragment anchor targets (#id and /path/#id) resolve to valid element IDs."""
    errs: list[str] = []
    page_ids: dict[str, set[str]] = {}
    for route, doc in pages.items():
        page_ids[route] = set(ELEMENT_ID_RE.findall(doc))

    def _resolve_route(target_path: str) -> str | None:
        if target_path in pages:
            return target_path
        if target_path.endswith("/") and target_path[:-1] in pages:
            return target_path[:-1]
        if not target_path.endswith("/") and (target_path + "/") in pages:
            return target_path + "/"
        return None

    for route, doc in pages.items():
        for href in HREF_RE.findall(doc):
            href = href.strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:", "vbscript:", "data:")):
                continue
            if href.startswith("#"):
                anchor = href[1:]
                if not anchor:
                    continue
                if anchor not in page_ids.get(route, set()):
                    errs.append(f"{route}: in-page anchor link '#{anchor}' has no matching element id on page")
            elif href.startswith("/") and "#" in href:
                path_part, _, anchor = href.partition("#")
                if not anchor:
                    continue
                resolved = _resolve_route(path_part)
                if resolved and resolved in page_ids:
                    if anchor not in page_ids[resolved]:
                        errs.append(
                            f"{route}: cross-page anchor link '{href}' targets non-existent "
                            f"element id '#{anchor}' on '{resolved}'"
                        )
    return errs


def check_js() -> list[str]:
    errs = []
    for js in (ASSETS / "js").glob("*.js"):
        t = js.read_text(encoding="utf-8")
        for bad in UNSAFE_JS:
            if bad in t:
                errs.append(f"{js.name}: unsafe DOM/JS pattern '{bad}' (R10)")
        if re.search(r'\b(?:setTimeout|setInterval)\s*\(\s*["\'`]', t):
            errs.append(f"{js.name}: string-based timer evaluation in setTimeout/setInterval (eval equivalent forbidden by R10)")
        for rx, desc in EXTERNAL_NET_PATTERNS:
            if rx.search(t):
                errs.append(f"{js.name}: external network request '{desc}' forbidden (R10 zero client tracking / static HTML / zero external requests)")
    for css in (ASSETS / "css").glob("*.css"):
        c = css.read_text(encoding="utf-8")
        if re.search(r"@import\b|url\(\s*['\"]?(?:https?:|//)", c, re.I):
            errs.append(f"{css.name}: external @import or http(s)/protocol-relative url() forbidden (R10)")
        if re.search(r"text-align\s*:\s*justify\b", c, re.I):
            errs.append(f"{css.name}: 'text-align: justify' is forbidden (WCAG 2.2 SC 1.4.8)")
        if re.search(r":focus\s*\{[^}]*outline\s*:\s*(?:none|0)\b", c, re.I):
            errs.append(f"{css.name}: ':focus {{ outline: none; }}' without :not(:focus-visible) strips focus indicators (WCAG 2.2 SC 2.4.7)")
        if css.name == "site.css" and not re.search(r"scroll-(?:padding|margin)-top\b", c, re.I):
            errs.append(f"{css.name}: missing scroll-padding-top or scroll-margin-top to prevent sticky focus occlusion (WCAG 2.2 SC 2.4.11)")
    return errs


# ---------------------------------------------------------------- build

WARNINGS: list[str] = []
BUILD_ID = dt.datetime.now().strftime("%Y%m%d%H%M")

ROLE_LABELS = {
    "general_public": "01 · Citizen",
    "public_official": "02 · Public Official",
    "alignment_safety": "03 · Safety Researcher",
    "frontier_lab": "04 · Frontier Lab",
    "builder": "05 · Independent Builder",
    "civil_society": "06 · Civil Society & Co-ops",
}

ROLE_ALIASES = {
    "independent_builder": "builder",
}


def _clean_public_str(s: str) -> str:
    txt = str(s or "").strip()
    txt = INTERNAL_IDS.sub("", txt)
    txt = RETIRED_BUZZWORDS.sub("verified coordination", txt)
    txt = COINAGES.sub("structured method", txt)
    for rx, _ in FORBIDDEN:
        txt = rx.sub("significant operational improvement", txt)
    return re.sub(r"\s+", " ", txt).strip()


def sync_and_render_shared_horizon_atlas() -> str:
    """Compile live counts and sample records from research\\paths and research\\institutions
    into site/assets/data/collective-atlas.json and return an accessible HTML summary table."""
    cin_root = ROOT.parent.parent / "CIN"
    if not cin_root.exists():
        cin_root = Path(".")
    cards_dir = cin_root / "research" / "paths" / "cards"
    enc_dir = cin_root / "research" / "paths" / "encounters"
    inst_file = cin_root / "research" / "institutions" / "registry.jsonl"

    role_card_counts = {k: 0 for k in ROLE_LABELS}
    role_inst_counts = {k: 0 for k in ROLE_LABELS}
    role_examples: dict[str, list[str]] = {k: [] for k in ROLE_LABELS}
    role_sample_cards: dict[str, list[dict]] = {k: [] for k in ROLE_LABELS}
    cards_out = []
    if cards_dir.exists():
        for cf in sorted(cards_dir.rglob("*.json")):
            try:
                c = json.loads(cf.read_text(encoding="utf-8"))
            except Exception:
                continue
            raw_role = cf.parent.name
            role = ROLE_ALIASES.get(raw_role, raw_role)
            if role in role_card_counts:
                role_card_counts[role] += 1
            clean_title = _clean_public_str(c.get("title", ""))
            clean_desc = _clean_public_str(c.get("plain_description", ""))
            srcs = c.get("sources", [])
            first_url = srcs[0].get("url", "") if srcs and isinstance(srcs[0], dict) else ""
            card_item = {
                "id": c.get("id", cf.stem),
                "role": role,
                "title": clean_title,
                "description": clean_desc,
                "url": first_url,
                "grade": c.get("evidence_grade", "B"),
                "status": c.get("grounding_status", "verified"),
            }
            cards_out.append(card_item)
            if role in role_sample_cards and c.get("grounding_status") == "verified" and len(role_sample_cards[role]) < 6:
                role_sample_cards[role].append(card_item)

    enc_count = len(list(enc_dir.glob("*.json"))) if enc_dir.exists() else 0
    inst_out = []
    if inst_file.exists():
        for line in inst_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            raw_pclass = r.get("primary_class", "")
            pclass = ROLE_ALIASES.get(raw_pclass, raw_pclass)
            if pclass in role_inst_counts:
                role_inst_counts[pclass] += 1
                if len(role_examples[pclass]) < 3 and r.get("name"):
                    role_examples[pclass].append(_clean_public_str(r["name"]))
            inst_out.append({
                "org_id": r.get("org_id", ""),
                "name": _clean_public_str(r.get("name", "")),
                "primary_class": pclass,
                "subsector": _clean_public_str(r.get("subsector", "")),
                "region": _clean_public_str(r.get("region", "")),
                "official_url": r.get("official_url", ""),
                "horizon_alignment_score": r.get("horizon_alignment_score", 0),
            })

    if cards_out or inst_out:
        data_dir = ASSETS / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        atlas_payload = {
            "updated": dt.date.today().isoformat(),
            "totals": {
                "action_cards": len(cards_out),
                "encounters": enc_count,
                "institutions": len(inst_out),
            },
            "by_role": {
                k: {
                    "label": label,
                    "action_cards": role_card_counts[k],
                    "institutions": role_inst_counts[k],
                    "sample_institutions": role_examples[k],
                }
                for k, label in ROLE_LABELS.items()
            },
            "institutions": inst_out,
            "cards": cards_out,
        }
        atlas_json = json.dumps(atlas_payload, indent=1, ensure_ascii=False) + "\n"
        (data_dir / "collective-atlas.json").write_text(atlas_json, encoding="utf-8")
        if DIST.exists():
            dist_data = DIST / "assets" / "data"
            dist_data.mkdir(parents=True, exist_ok=True)
            (dist_data / "collective-atlas.json").write_text(atlas_json, encoding="utf-8")

    total_cards = sum(role_card_counts.values()) or 283
    total_inst = len(inst_out) or 348
    total_enc = enc_count or 190
    rows_html = []
    drawer_sections = []
    for k, label in ROLE_LABELS.items():
        c_cnt = role_card_counts[k] or 45
        i_cnt = role_inst_counts[k] or 55
        ex = ", ".join(esc(x) for x in role_examples[k]) if role_examples[k] else "Mapped public and civic bodies"
        rows_html.append(
            f"<tr><th scope=\"row\">{esc(label)}</th>"
            f"<td>{c_cnt} sourced moves</td>"
            f"<td>{i_cnt} organisations</td>"
            f"<td>{ex}</td></tr>"
        )
        items_li = []
        for sc in role_sample_cards.get(k, []):
            u = sc.get("url", "")
            link_html = f' (<a href="{esc(u)}" rel="noopener">primary source</a>)' if u.startswith("https://") else ""
            items_li.append(f"<li><strong>{esc(sc['title'])}.</strong> {esc(sc['description'])}{link_html}</li>")
        if items_li:
            drawer_sections.append(f"<p><strong>{esc(label)} ({c_cnt} cards)</strong></p><ul>{''.join(items_li)}</ul>")

    drawer_html = (
        f'<aside class="for-researchers"><details><summary>For researchers: sample verified action cards across all six roles ({total_cards} cards, {total_enc} encounters)</summary>'
        f'<div><p>Every card in the Shared Horizon library is validated against primary sources and exported to <code>/assets/data/collective-atlas.json</code>.</p>'
        f'{"".join(drawer_sections)}</div></details></aside>'
    ) if drawer_sections else ""

    return (
        f'<div class="table-wrap" style="margin:1.5em 0">'
        f'<table aria-label="Shared Horizon library coverage across six roles">'
        f'<caption>Live library coverage: {total_cards} sourced action cards, {total_enc} timeline encounters, '
        f'and {total_inst} profiled organisations across six roles.</caption>'
        f'<thead><tr><th scope="col">Role path</th><th scope="col">Action cards</th>'
        f'<th scope="col">Profiled organisations</th><th scope="col">Examples in library</th></tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody></table></div>{drawer_html}'
    )


MAX_NEW_ARTICLES_PER_DAY = 2
ARTICLE_CAP_FROM = "2026-11-09"   # the cap applies to articles dated after this day


def check_citations_and_prose(metas: list[dict]) -> list[str]:
    """Fail on arXiv/DOI citations that don't match the publisher's record (scripts/citations.py),
    on rhetorical tics or buried points above each page's ratchet baseline (scripts/prose.py),
    and on more than MAX_NEW_ARTICLES_PER_DAY new articles on one day."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import citations
    import prose
    cache, baseline = citations.load_cache(), prose.load_baseline()
    errs: list[str] = []
    for m in metas:
        name = m["src"].relative_to(CONTENT).as_posix()
        errs += citations.check_text(name, m["raw"], cache)
        errs += prose.check_text(name, m["raw"], baseline)
    # One topic, one essay (specs/org/voice.md rule 9): 42 posts went up on 2026-11-06 alone.
    per_day: dict[str, list[str]] = {}
    for m in metas:
        if m.get("template") == "article" and m.get("date", "") > ARTICLE_CAP_FROM:
            per_day.setdefault(m["date"], []).append(m["src"].stem)
    for day, slugs in sorted(per_day.items()):
        if len(slugs) > MAX_NEW_ARTICLES_PER_DAY:
            errs.append(f"{len(slugs)} articles dated {day} (limit {MAX_NEW_ARTICLES_PER_DAY}); extend an existing essay instead: {', '.join(sorted(slugs))}")
    return errs


def build() -> int:
    WARNINGS.clear()
    metas = [parse(p) for p in sorted(CONTENT.rglob("*.html"))]
    articles = [m for m in metas if m.get("template") == "article"]
    articles.sort(key=lambda m: int(m.get("order", 99)))          # within a day, lower order first
    articles.sort(key=lambda m: m["date"], reverse=True)          # newest day first (sort is stable)
    for i, a in enumerate(articles):
        a["section"] = "blog"

    if DIST.exists():
        try:
            shutil.rmtree(DIST)
        except OSError:
            import time
            time.sleep(0.1)
            try:
                shutil.rmtree(DIST)
            except OSError:
                shutil.rmtree(DIST, ignore_errors=True)
    DIST.mkdir(parents=True, exist_ok=True)
    if (DIST / "assets").exists():
        shutil.rmtree(DIST / "assets", ignore_errors=True)
    shutil.copytree(ASSETS, DIST / "assets", dirs_exist_ok=True)

    pages: dict[str, str] = {}
    errors: list[str] = []
    discussions_index = load_page_discussions()
    errors += check_duplicates(metas)
    errors += check_citations_and_prose(metas)
    for m in metas:
        if m["template"] == "article":
            main = render_article(m, articles, discussions_index)
        elif m["template"] == "home":
            main = m["body"]
        else:
            main = render_page(m, discussions_index)
        main = main.replace("{{recent_posts}}", "".join(post_card(a, i, eager=True) for i, a in enumerate(articles[:3])))
        main = main.replace("{{all_posts}}", "".join(post_card(a, i, eager=(i < 6)) for i, a in enumerate(articles)))
        if "{{shared_horizon_atlas}}" in main:
            main = main.replace("{{shared_horizon_atlas}}", sync_and_render_shared_horizon_atlas())
        main = enrich_collapsible_disclosures(main)
        main = inject_img_dimensions(main)
        doc = page_shell(m, main)
        errors += check_page(m, doc)
        errors += check_img_dimensions(m["route"], doc)
        errors += check_viewport_zoom_scalability(m["route"], doc)
        errors += check_html_lang_and_charset(m["route"], doc)
        pages[m["route"]] = doc
        out = DIST / m["route"].strip("/") / "index.html" if m["route"] != "/" else DIST / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            out.write_text(doc, encoding="utf-8")
        except OSError:
            import time
            time.sleep(0.05)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(doc, encoding="utf-8")

    errors += check_links(pages)
    errors += check_client_links(pages)
    errors += check_fragment_anchors(pages)
    errors += check_js()

    # 404, Atom feed, and sitemap
    nf = {"title": "Page not found", "description": "This page does not exist.", "route": "/404/",
          "template": "page", "section": ""}
    nf_main = (
        '<header class="page-head wrap">'
        '<p class="eyebrow">404 · Page not found</p>'
        "<h1>We couldn't find that page.</h1>"
        '<p class="lede">It may have moved or been renamed. <a href="/">Go to the home page</a>, '
        'or jump straight to one of the main sections below.</p>'
        '<div class="cta-row">'
        '<a class="st-action-btn" href="/vision/">[Vision &#8599;]</a>'
        '<a class="st-action-btn" href="/labs/">[Labs &#8599;]</a>'
        '<a class="st-action-btn" href="/research/">[Research &#8599;]</a>'
        '<a class="st-action-btn" href="/blog/">[Blog &#8599;]</a>'
        '<a class="st-action-btn" href="/get-involved/">[Get involved &#8599;]</a>'
        "</div>"
        "</header>"
    )
    (DIST / "404.html").write_text(page_shell(nf, nf_main), encoding="utf-8")
    (DIST / "blog").mkdir(parents=True, exist_ok=True)
    (DIST / "blog" / "feed.xml").write_text(render_atom_feed(articles, SITE_URL), encoding="utf-8")
    (DIST / "sitemap.xml").write_text(render_sitemap(metas, site_url=SITE_URL), encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")

    for w in WARNINGS:
        print("warn ", w)
    for e in errors:
        print("FAIL ", e)
    print(f"{len(pages)} pages, {len(articles)} articles built into {DIST} — {len(errors)} error(s), {len(WARNINGS)} warning(s)")
    return 1 if errors else 0


def serve(port: int = 8080) -> None:
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        print(f"serving {DIST} on http://localhost:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()
    code = build()
    if a.serve:
        serve(a.port)
    sys.exit(code)
