"""Check arXiv and DOI citations in site content against the publishers' own records.

Every arXiv ID and DOI cited on the site must be in scripts/arxiv_cache.json (real title and
authors, fetched from export.arxiv.org, Crossref or DataCite). The build fails when:
  - a reference is cited but not in the cache (run: python scripts/citations.py --refresh),
  - an arXiv ID or DOI does not exist,
  - the citation names authors, but none of the paper's real authors,
  - the citation quotes a title that shares under half its words with the real title.
A bare pointer such as "(arXiv:2503.14499)" with no names is only checked for existence.

Usage:
  python scripts/citations.py            # check all content, print failures
  python scripts/citations.py --refresh  # fetch uncached references, then check
  python scripts/citations.py --show ID  # print the cached record (arXiv ID or doi:10.x/y)
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTENT = HERE.parent / "content"
CACHE = HERE / "arxiv_cache.json"
UA = {"User-Agent": "cintnet-citation-check/1.0"}

REF = re.compile(
    r"(?:arxiv[:./\s]*(?:org/(?:abs|pdf)/)?|abs/)(?P<ax>\d{4}\.\d{4,5})(?:v\d+)?"
    r"|(?:doi\.org/|\bdoi:\s?)(?P<doi>10\.\d{4,9}/[^\s\"\]]+)", re.I)
# Institutional authors (NIST, METR...) are cited by name of the body, not of the people on the record.
ORG_AUTHOR = re.compile(r"\b(?:National Institute|NIST|Institute|Agency|Commission|Department|Ministry|Office|"
                        r"Council|OECD|UNESCO|Bureau|Committee|Working Group|Task Force|METR)\b")
QUOTED = re.compile(r"[\"“]([^\"”]{12,200})[\"”]")
NS = {"a": "http://www.w3.org/2005/Atom"}
SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv"}
STOP = {"about", "after", "among", "their", "there", "these", "those", "which", "while", "where",
        "under", "through", "without", "within", "between", "towards", "toward", "using", "based"}
NAMES_SOMEONE = re.compile(
    r"\bet al\b|\b(?:Team|Consortium|Anonymous|Group|Lab)\b"
    r"|\b[A-Z]\.(?:\s?[A-Z]\.)*\s?[A-Z][\w'’-]+"                         # J. Smith
    r"|\b[A-Z][\w'’-]+,? (?:and|&) [A-Z][\w'’-]+"                          # Smith and Jones
    r"|\b[A-Z][a-zà-ÿ'’-]+ (?:[A-Z]\. )?[A-Z][a-zà-ÿ'’-]+(?:,| and| &| \()"  # Jane Smith, / Jane Smith (
)


def norm(s: str) -> str:
    s = s.translate(str.maketrans({"ł": "l", "Ł": "L", "ø": "o", "Ø": "O", "đ": "d", "ß": "ss", "æ": "ae"}))
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def surname(full: str) -> str:
    parts = [p for p in full.replace(",", " ").split() if norm(p) not in SUFFIXES]
    return norm(parts[-1]) if parts else ""


def ref_key(m: re.Match) -> str:
    if m.group("ax"):
        return m.group("ax")
    doi = urllib.parse.unquote(m.group("doi")).rstrip(".,;:)").lower()
    if doi.startswith("10.48550/arxiv."):
        return doi.split("arxiv.", 1)[1]
    return "doi:" + doi


def load_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict) -> None:
    CACHE.write_text(json.dumps(dict(sorted(cache.items())), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def get_json(url: str):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def fetch_arxiv(ids: list[str]) -> dict:
    out = {}
    ids = sorted(set(ids))
    for i in range(0, len(ids), 50):
        url = "https://export.arxiv.org/api/query?max_results=100&id_list=" + ",".join(ids[i:i + 50])
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                root = ET.fromstring(resp.read())
        except Exception:
            url_http = "http://export.arxiv.org/api/query?max_results=100&id_list=" + ",".join(ids[i:i + 50])
            req_http = urllib.request.Request(url_http, headers=UA)
            with urllib.request.urlopen(req_http, timeout=90) as resp:
                root = ET.fromstring(resp.read())
        for e in root.findall("a:entry", NS):
            m = re.search(r"(\d{4}\.\d{4,5})", e.find("a:id", NS).text or "")
            title = e.find("a:title", NS)
            if not m or title is None or not (title.text or "").strip():
                continue
            out[m.group(1)] = {
                "title": re.sub(r"\s+", " ", title.text).strip(),
                "authors": [a.find("a:name", NS).text for a in e.findall("a:author", NS)],
                "published": (e.find("a:published", NS).text or "")[:10],
                "abstract": re.sub(r"\s+", " ", e.find("a:summary", NS).text or "").strip(),
            }
        time.sleep(3)
    return out


def fetch_doi(doi: str) -> dict:
    q = urllib.parse.quote(doi, safe="/")
    cr = get_json(f"https://api.crossref.org/works/{q}")
    if cr:
        m = cr["message"]
        people = m.get("author") or m.get("editor") or []
        return {"title": (m.get("title") or [""])[0],
                "authors": [" ".join(x for x in (a.get("given"), a.get("family") or a.get("name")) if x) for a in people],
                "published": str(((m.get("issued") or {}).get("date-parts") or [[""]])[0][0]),
                "source": "crossref"}
    dc = get_json(f"https://api.datacite.org/dois/{q}")
    if dc:
        a = dc["data"]["attributes"]
        return {"title": (a.get("titles") or [{}])[0].get("title", ""),
                "authors": [c.get("name", "") for c in a.get("creators", [])],
                "published": str(a.get("publicationYear", "")), "source": "datacite"}
    h = get_json(f"https://doi.org/api/handles/{q}")
    if h and h.get("responseCode") == 1:
        return {"unverified": True, "note": "DOI resolves but has no Crossref or DataCite metadata"}
    return {"missing": True}


def plain(raw: str) -> str:
    # Keep link targets visible, after the link text, so citations whose ID lives only in an href are checked.
    raw = re.sub(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"\2 [\1]", raw, flags=re.S | re.I)
    return html.unescape(re.sub(r"<[^>]+>", " ", raw))


def segments(raw_html: str, with_fn: bool = False):
    """Yield (key, citation_text) for every arXiv ID or DOI in a page, plus, when with_fn is set,
    whether the reference sits in a footnote entry (<p id="fn…"> or <li id="fn…">).

    The citation text for a reference runs from the previous reference (or the start of its
    footnote/paragraph/list item) to the end of this one, capped at 400 characters."""
    parts = re.split(r"(?i)(</?(?:p|li|div|section|aside|details|summary|h\d|tr|td)\b[^>]*>)", raw_html)
    tags = [""] + parts[1::2]
    for tag, block in zip(tags, parts[0::2]):
        in_fn = bool(re.match(r'<(?:p|li)\b[^>]*\bid="fn', tag))
        text = re.sub(r"\s+", " ", plain(block)).strip()
        prev, last_key = 0, None
        for m in REF.finditer(text):
            key = ref_key(m)
            seg = text[prev:m.end()][-400:]
            prev = m.end()
            if key == last_key:      # "arXiv:X [https://arxiv.org/abs/X]": same reference twice in a row
                continue
            last_key = key
            # A reference list often packs several sources into one block, separated by
            # semicolons or "see also"; keep only the part that belongs to this reference.
            seg = re.split(r";\s|\bsee also\b", seg)[-1]
            yield (key, seg.strip(), in_fn) if with_fn else (key, seg.strip())


def names_someone(seg: str) -> bool:
    """True when the text just before a reference credits authors, as opposed to a bare '(arXiv:…)' pointer."""
    m = REF.search(seg)
    before = seg[:m.start()] if m else seg
    before = re.sub(r"\[https?://[^\]]*\]?", " ", before)
    if not re.match(r"\s*\d+\.\s", before):
        # Split at sentence ends, but not after an initial ("J. Smith").
        before = re.split(r"(?:(?<=[a-z0-9]{2}\.)|(?<=\))|(?<=\)\.))\s+(?=[A-Z])", before)[-1]
    return bool(NAMES_SOMEONE.search(before[-220:]))


def cited_surnames(seg: str, rec: dict) -> list[str] | None:
    """Surnames in a reference's leading author list ("1. Jane Smith, Ann Lee and Bo Wu, Title..."),
    or None when the segment doesn't start with a parseable author list."""
    if len(seg) >= 400:          # truncated: the start of the reference is not in view
        return None
    s = re.sub(r"^\s*\d+\.\s*", "", seg)
    s = re.sub(r"\[https?://[^\]]*\]?", " ", s)
    s = re.sub(r"\s*\([A-Z][a-z]+\)(?=\s*(?:,|&|and\b))", "", s)    # "Lynn Sagan (Margulis),"
    cuts = [i for i in (s.find('"'), s.find("“"), s.find(" et al")) if i > 0]
    m = re.search(r"\(?(?:19|20)\d\d", s)
    if m:
        cuts.append(m.start())
    title = norm(rec.get("title", ""))[:18]
    if title:
        i = norm(s).find(title)
        if i > 0:
            cuts.append(i)
    m = REF.search(s)
    if m:
        cuts.append(m.start())
    part = s[:min(cuts)].strip(" ,;") if cuts else ""
    if not part or len(part) > 220:
        return None
    out = []
    for nm in re.split(r",\s*|\s+and\s+|\s*&\s*", part):
        toks = [t for t in nm.replace("(", " ").split() if not re.fullmatch(r"(?:[A-Z]\.)+(?:-[A-Z]\.)?|[A-Z]", t)]
        if not toks:
            continue
        if len(toks) > 4 or not toks[-1][:1].isupper():
            return None
        out.append(norm(toks[-1].strip(".,")))
    return out or None


def check_text(name: str, raw_html: str, cache: dict) -> list[str]:
    errs = []
    seen = set()
    for key, seg, in_fn in segments(raw_html, with_fn=True):
        label = key if key.startswith("doi:") else f"arXiv:{key}"
        if (key, seg) in seen:
            continue
        seen.add((key, seg))
        rec = cache.get(key)
        if rec is None:
            errs.append(f"{name}: {label} is not in scripts/arxiv_cache.json; run `python scripts/citations.py --refresh` and check the citation against the real record")
            continue
        if rec.get("missing"):
            errs.append(f"{name}: {label} does not exist")
            continue
        if rec.get("unverified"):
            continue
        cited = norm(seg)
        surnames = {surname(a) for a in rec.get("authors", [])} - {""}
        if surnames and names_someone(seg) and not ORG_AUTHOR.search(seg) and not any(
                re.search(r"(?<![a-z])" + re.escape(s) + r"(?![a-z])", cited) for s in surnames):
            real = ", ".join(rec["authors"][:3]) + (" et al." if len(rec["authors"]) > 3 else "")
            errs.append(f"{name}: {label} citation names none of the real authors ({real}); cited text: …{seg[-160:]}")
            continue
        # Footnote entries carry full references: every listed author must be on the paper,
        # and the title must be the paper's (quoted or not).
        listed = cited_surnames(seg, rec) if in_fn and not ORG_AUTHOR.search(seg) else None
        if listed and surnames:
            clean = [re.sub(r"[{}\\]", "", a).replace("-", " ") for a in rec["authors"]]
            every_token = {norm(t.strip(".,")) for a in clean for t in a.split()} | surnames | {norm(a.split()[-1]) for a in clean if a.split()}
            extra = [s for s in listed if s not in every_token and not all(x in every_token for x in s.split("-"))]
            if extra:
                errs.append(f"{name}: {label} lists authors who are not on the paper ({', '.join(extra)}); real authors: {', '.join(rec['authors'][:6])}")
                continue
            # a full reference should carry (most of) the real title, quoted or not
            real_words = {w for w in re.findall(r"[a-z]{5,}", norm(rec.get("title", "")))} - STOP
            have = set(re.findall(r"[a-z]{5,}", cited))
            if len(real_words) >= 3 and len(real_words & have) < 0.4 * len(real_words):
                errs.append(f"{name}: {label} reference title does not match the real title \"{rec['title']}\"; cited text: …{seg[-160:]}")
                continue
        real_words = {w for w in re.findall(r"[a-z]{5,}", norm(rec.get("title", "")))} - STOP
        for q in QUOTED.findall(seg)[-1:]:      # the title nearest the reference is the one it belongs to
            qw = {w for w in re.findall(r"[a-z]{5,}", norm(q))} - STOP
            # Crossref often stores only the main title ("Sigstore"); accept a quoted title that contains it.
            if len(qw) >= 3 and real_words and not real_words <= qw and len(qw & real_words) < len(qw) / 2:
                errs.append(f"{name}: {label} quoted title \"{q}\" does not match the real title \"{rec['title']}\"")
                break
    return errs


def all_pages():
    for f in sorted(CONTENT.rglob("*.html")):
        yield f.relative_to(CONTENT).as_posix(), f.read_text(encoding="utf-8")


def refresh(cache: dict) -> dict:
    keys = {k for _, raw in all_pages() for k, _ in segments(raw)}
    missing = sorted(keys - set(cache))
    ax = [k for k in missing if not k.startswith("doi:")]
    if ax:
        got = fetch_arxiv(ax)
        for k in ax:
            cache[k] = got.get(k, {"missing": True})
    for k in missing:
        if k.startswith("doi:"):
            cache[k] = fetch_doi(k[4:])
            time.sleep(0.5)
    if missing:
        save_cache(cache)
    print(f"{len(keys)} references cited, {len(missing)} fetched")
    return cache


def main(argv: list[str]) -> int:
    cache = load_cache()
    if "--show" in argv:
        key = argv[argv.index("--show") + 1]
        print(json.dumps(cache.get(key), indent=1, ensure_ascii=False))
        return 0
    if "--refresh" in argv:
        cache = refresh(cache)
    errs = [e for name, raw in all_pages() for e in check_text(name, raw, cache)]
    for e in errs:
        print(e)
    print(f"{len(errs)} citation problem(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
