"""Prose gate: catch the rhetorical tics that made cintnet.org read as machine-written.

Counts, per page (body prose only; footnotes, researcher boxes, SVG and styles are skipped):
  staged    staged contrasts: "X isn't A. It's B", "not just A but B", headings shaped "A, not B"
  tics      stock phrases: quiet/quietly, Tuesday scenes, "the trap of", "the real question",
            "here's the thing", "we don't have all the answers", "we do not pretend", "it turns out"
  aphorism  closing-line maxims: "Real progress is not ...", "True safety is never ..."
   buried        articles only: subject (AI, agents, software...) first named after 150 words,
                 or the front-matter takeaway not stated within the lede + first 150 words
   internal_leak hard limit 0 for ALL pages: internal L1-L5 layer codes, Layer 1-5: architecture
                 labels, 5-Layer Functional Deliverable, Waymo-grade, Heartbeat Stack, Base Thesis,
                 or bare ungrounded jargon (Markov blanket, exocortex, teleonomic) in body prose

Ratchet: scripts/prose_baseline.json holds today's counts. An existing page fails if any count
rises above its baseline. A new page fails above NEW_PAGE_LIMITS. After cleaning pages up, run
`python scripts/prose.py --lower-baseline` to lock in the lower counts (it never raises them).
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTENT = HERE.parent / "content"
BASELINE = HERE / "prose_baseline.json"
NEW_PAGE_LIMITS = {"staged": 1, "tics": 0, "aphorism": 0, "buried": 0, "internal_leak": 0}

PATTERNS = {
    "staged": [
        re.compile(r"\b(?:isn['’]t|is not|aren['’]t|are not|wasn['’]t|was not)\b[^.!?<]{0,70}[.;]\s+(?:it|they|that|this)(?:['’]s| is| are| was)\b", re.I),
        re.compile(r"\bnot (?:just|only|merely|simply)\b[^.?!]{1,90}\bbut\b", re.I),
        re.compile(r"\b(?:is|are) not about\b[^.?!]{3,80}[.;,]\s*(?:it|they)(?:['’]s| is| are)\b", re.I),
    ],
    "tics": [
        re.compile(r"\bquiet(?:ly)?\b", re.I),
        re.compile(r"\bTuesday\b"),
        re.compile(r"\bthe trap of\b", re.I),
        re.compile(r"\bthe (?:real|deeper|true) (?:question|problem|issue|lesson)\b", re.I),
        re.compile(r"\bhere['’]s the (?:thing|catch|twist)\b", re.I),
        re.compile(r"\bwe (?:don['’]t|do not) have all the answers\b", re.I),
        re.compile(r"\bwe (?:do not|don['’]t) pretend\b", re.I),
        re.compile(r"\bit turns out\b", re.I),
    ],
    "aphorism": [
        re.compile(r"\b(?:Real|True|Genuine|Lasting) [a-z]+ (?:is|are) (?:not|never|rarely)\b"),
        re.compile(r"\bthe (?:loudest|quietest|smallest|humblest) [a-z]+ is (?:rarely|often|always)\b", re.I),
    ],
    "internal_leak": [
        re.compile(r"\bL[1-5]\b(?!\s*(?i:cache|(?:instruction|data)\s+cache|/\s*L[1-3]\s+cache))"),
        re.compile(
            r"\bLayer\s+[1-5]\s*:(?!\s*(?:Public\s+libraries|Co-operatives\s+and\s+municipal|Personal\s+devices\s+at\s+the\s+edge))",
            re.I,
        ),
        re.compile(r"\b5-Layer\s+Functional\s+Deliverable\b", re.I),
        re.compile(r"\bWaymo-grade\b|\bWaymo\s+like\s+hardware\b", re.I),
        re.compile(r"\bHeartbeat\s+Stack\b", re.I),
        re.compile(r"\bBase\s+Thesis\b", re.I),
        re.compile(r"\bMarkov\s+[Bb]lankets?\b", re.I),
        re.compile(r"\bexocortex(?:es)?\b|\bexocortices\b", re.I),
        re.compile(r"\bteleonomic\b", re.I),
    ],
}
HEADING_CONTRAST = re.compile(r"<h[23][^>]*>[^<]{2,60}, not [^<]{2,40}</h[23]>", re.I)
TOPIC = re.compile(r"\b(?:AI|agents?|assistants?|software|algorithms?|bots?|chatbots?|machines?|models?)\b")
STOP = set("""a an the and or but of to in on for with by at as is are be been being it its it's this that these those
we you your our they their them he she his her not no rather than instead more most less very can could should would will
real really just only even also into from about over under when what which who whom how why where while than then so
do does did done has have had make makes made one ones own any every each some all many much such through without within
there here other others people person thing things way ways""".split())


def split_doc(text: str):
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n(.*)", text, re.S)
    fm, body = (m.group(1), m.group(2)) if m else ("", text)
    meta = {}
    for line in fm.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, body


def prose_html(body: str) -> str:
    body = re.split(r"<h2[^>]*>\s*(?:Sources|Footnotes|Notes and sources|References|Further reading)\b", body)[0]
    body = re.sub(r"<(style|script|svg|aside|figure)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)
    return re.sub(r'<section class="footnotes".*?</section>', " ", body, flags=re.S)


def plain(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def keys(s: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-z']+", s.lower()) if w not in STOP and len(w) > 3}


def measure(text: str) -> dict:
    meta, body = split_doc(text)
    ph = prose_html(body)
    lede = meta.get("lede", "")
    prose = (lede + " " + plain(ph)).strip()
    counts = {k: sum(len(rx.findall(prose)) for rx in rxs) for k, rxs in PATTERNS.items()}
    counts["staged"] += len(HEADING_CONTRAST.findall(ph))
    counts["buried"] = 0
    if meta.get("template") == "article":
        m = TOPIC.search(prose)
        if not m or len(prose[:m.start()].split()) > 150:
            counts["buried"] += 1
        tk = keys(meta.get("takeaway", ""))
        if tk:
            opening = " ".join(prose.split()[: len(lede.split()) + 150])
            if len(keys(opening) & tk) < max(3, round(len(tk) * 0.3)):
                counts["buried"] += 1
    return counts


def load_baseline() -> dict:
    return json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}


def check_text(name: str, text: str, baseline: dict) -> list[str]:
    counts = measure(text)
    limits = baseline.get(name, NEW_PAGE_LIMITS)
    errs = []
    for k, v in counts.items():
        limit = 0 if k == "internal_leak" else limits.get(k, NEW_PAGE_LIMITS[k])
        if v > limit:
            what = {
                "staged": "staged 'not X, it's Y' contrasts",
                "tics": "stock phrases (quiet, Tuesday, the trap of, the real question...)",
                "aphorism": "closing maxims ('Real X is not...')",
                "buried": "buried point (subject or takeaway missing from the first 150 words)",
                "internal_leak": "internal architecture or ungrounded jargon leak (L1-L5, Layer 1-5:, Waymo-grade, Heartbeat Stack, Base Thesis, Markov blanket, exocortex, teleonomic)",
            }[k]
            errs.append(f"{name}: {v} {what}, limit {limit} (specs/org/voice.md; run scripts/prose.py for details)")
    return errs


def all_pages():
    for f in sorted(CONTENT.rglob("*.html")):
        yield f.relative_to(CONTENT).as_posix(), f.read_text(encoding="utf-8")


def detail(name: str, text: str) -> None:
    meta, body = split_doc(text)
    prose = (meta.get("lede", "") + " " + plain(prose_html(body)))
    for k, rxs in PATTERNS.items():
        for rx in rxs:
            for m in rx.finditer(prose):
                print(f"  {k}: …{prose[max(0, m.start() - 40):m.end() + 40]}…")
    for m in HEADING_CONTRAST.finditer(prose_html(body)):
        print(f"  staged heading: {plain(m.group(0))}")


def main(argv: list[str]) -> int:
    pages = dict(all_pages())
    if "--write-baseline" in argv:
        BASELINE.write_text(json.dumps({n: measure(t) for n, t in pages.items()}, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"baseline written for {len(pages)} pages")
        return 0
    base = load_baseline()
    if "--lower-baseline" in argv:
        for n, t in pages.items():
            if n in base:
                cur = measure(t)
                base[n] = {k: min(base[n].get(k, v), v) for k, v in cur.items()}
        base = {n: v for n, v in base.items() if n in pages}
        BASELINE.write_text(json.dumps(base, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("baseline lowered where pages improved")
        return 0
    targets = [a for a in argv if not a.startswith("-")]
    errs = []
    for n, t in pages.items():
        if targets and n not in targets:
            continue
        e = check_text(n, t, base)
        errs += e
        if targets:
            print(n, measure(t))
            detail(n, t)
    for e in errs:
        print(e)
    total = {k: sum(measure(t)[k] for t in pages.values()) for k in NEW_PAGE_LIMITS}
    print(f"{len(errs)} prose problem(s); site totals {total}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
