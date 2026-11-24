import pathlib
import re
import statistics
import unittest

SITE_DIR = pathlib.Path(__file__).resolve().parents[1]
BLOG_DIR = SITE_DIR / "content" / "blog"

ESSAYS = {
    "aviation-safety-for-ai-infrastructure.html": "ex-valve-interlock",
    "eight-ways-ai-goes-wrong.html": "ex-eight-harbors",
    "slowing-frontier-training-without-a-global-censor.html": "ex-seismic-threshold",
    "what-canadas-ai-security-framework-gets-right-and-whats-still-missing.html": "ex-canada-ai-srmf",
    "why-people-dont-want-an-ai-mother.html": "ex-mother-vs-aide",
    "why-rules-need-blueprints-before-code.html": "ex-artifact-models",
}

REQUIRED_38_BASE_THESIS_TERMS = [
    "Device Time",
    "observation confidence",
    "PUF",
    "TCG DICE",
    "DMTF SPDM",
    "IETF RATS",
    "9334",
    "optical data diode",
    "IEC 61508",
    "dead-man",
    "C2PA",
    "Merkle",
    "episodic memory vault",
    "Tulving",
    "Endel Tulving",
    "Signed Is Not True",
    "analog hole",
    "Fu",
    "Xu",
    "1:1",
    "exocortex",
    "Bach",
    "Joscha Bach",
    "Clark",
    "Chalmers",
    "Andy Clark",
    "David Chalmers",
    "information fiduciary",
    "Balkin",
    "Jack Balkin",
    "unassisted competence",
    "Markov blanket",
    "Friston",
    "Karl Friston",
    "Private Autobiographical Ledger",
    "Public Attestation",
    "Escrow Ledger",
    "ZK",
    "IETF SCITT",
    "9943",
    "Object-Capability",
    "capability lease",
    "Dennis",
    "Van Horn",
    "3f + 1",
    "Wide Network Ledger",
    "Universal Basic Services",
    "Meluso",
    "Jacob Meluso",
    "reciprocal mutual credit",
    "Stodder",
    "James Stodder",
    "Meidner",
    "Rudolf Meidner",
    "Ostrom",
    "Elinor Ostrom",
]

CANONICAL_BASE_THESIS_SOURCES = (
    "10.1145/3176402",
    "rfc9334",
    "c2pa.org/specifications/specifications/2.1/specs/C2PA_Specification.html",
    "information-fiduciaries-and-first-amendment",
    "10.1098/rsif.2013.0475",
    "10.1145/365230.365252",
    "rfc9943",
    "employeeinvestme0000meid",
)


def _strip_front_matter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2]
    return text


def _everyday_body(text: str) -> str:
    body = _strip_front_matter(text)
    body = re.sub(r"<aside\b[^>]*>.*?</aside>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<figure\b[^>]*>.*?</figure>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<section\s+class=\"footnotes\"[^>]*>.*?</section>", " ", body, flags=re.S | re.I)
    return body


class EditorFiveObservatoryAndCanadaSrmfEssaysSpec05Tests(unittest.TestCase):
    def test_spec05_dark_mode_and_dual_responsive_svgs_with_mobile_connectors(self):
        for filename, fig_id in ESSAYS.items():
            path = BLOG_DIR / filename
            self.assertTrue(path.exists(), f"Missing {filename}")
            text = path.read_text(encoding="utf-8")

            self.assertIn(f'id="{fig_id}"', text, f"{filename} missing figure #{fig_id}")
            self.assertIn(f':root[data-theme="dark"] #{fig_id}', text, f"{filename} missing dark-mode selector")
            self.assertIn("@media (prefers-color-scheme: dark)", text, f"{filename} missing prefers-color-scheme dark block")
            self.assertIn("#8FD4B6", text, f"{filename} missing Spec 05 dark forest token #8FD4B6")
            self.assertIn("#F09D82", text, f"{filename} missing Spec 05 dark terracotta token #F09D82")
            self.assertIn('class="diagram-desktop"', text, f"{filename} missing .diagram-desktop SVG")
            self.assertIn('class="diagram-mobile"', text, f"{filename} missing .diagram-mobile SVG")

            for match in re.finditer(r'font-size="([0-9.]+)"', text):
                size = float(match.group(1))
                self.assertGreaterEqual(size, 11.0, f"{filename} has sub-11px SVG font-size {size}")

            mobile_match = re.search(
                r'<svg[^>]*class="diagram-mobile"[^>]*viewBox="0 0 ([0-9.]+) ([0-9.]+)"[^>]*>(.*?)</svg>',
                text,
                flags=re.S,
            )
            self.assertIsNotNone(mobile_match, f"{filename} missing .diagram-mobile viewBox")
            mobile_width = float(mobile_match.group(1))
            self.assertLessEqual(mobile_width, 310.0, f"{filename} mobile viewBox width {mobile_width} > 310")
            mobile_inner = mobile_match.group(3)
            self.assertIn("<line", mobile_inner, f"{filename} .diagram-mobile missing connector <line>")
            self.assertIn("<polygon", mobile_inner, f"{filename} .diagram-mobile missing arrowhead <polygon>")

    def test_base_thesis_38_term_grounding_and_lab_links(self):
        for filename in ESSAYS:
            text = (BLOG_DIR / filename).read_text(encoding="utf-8")
            aside_match = re.search(r'<aside class="for-researchers">.*?</aside>', text, flags=re.S)
            self.assertIsNotNone(aside_match, f"{filename} missing for-researchers aside")
            aside = aside_match.group(0)

            for term in REQUIRED_38_BASE_THESIS_TERMS:
                self.assertIn(term.lower(), aside.lower(), f"{filename} researcher aside missing Base Thesis term: {term}")

            for lab_link in ("/labs/protocol-inspector/", "/labs/sensor-boundary/", "/labs/shared-horizon/"):
                self.assertIn(lab_link, aside, f"{filename} researcher aside missing link to {lab_link}")

            for src in CANONICAL_BASE_THESIS_SOURCES:
                self.assertIn(src, text, f"{filename} footnotes missing canonical Base Thesis source '{src}'")

    def test_claim_first_voice_and_humanizer_sentence_invariants(self):
        for filename in ESSAYS:
            raw = (BLOG_DIR / filename).read_text(encoding="utf-8")
            takeaway_m = re.search(r"^takeaway:\s*(.+)$", raw, flags=re.M)
            self.assertIsNotNone(takeaway_m, f"{filename} missing takeaway front matter")
            takeaway = takeaway_m.group(1).strip()
            body = _everyday_body(raw)

            first_p = re.search(r"<p>(.*?)</p>", body, flags=re.S)
            self.assertIsNotNone(first_p, f"{filename} missing opening paragraph")
            first_p_plain = re.sub(r"<[^>]+>", "", first_p.group(1)).strip()
            self.assertTrue(
                first_p_plain.startswith(takeaway[:45]),
                f"{filename} does not open sentence 1 with its direct takeaway claim: {first_p_plain[:80]}",
            )
            self.assertFalse(
                first_p_plain.startswith(("Picture a", "Suppose every", "Imagine a")),
                f"{filename} still opens with a scene starter: {first_p_plain[:60]}",
            )

            plain = re.sub(r"<[^>]+>", " ", body)
            plain = re.sub(r"\s+", " ", plain).strip()
            self.assertNotIn("—", plain, f"{filename} contains an em-dash")

            for forbidden in ("rather than", "instead of", "not just", "not only", "not merely"):
                self.assertIsNone(
                    re.search(rf"\b{re.escape(forbidden)}\b", plain, flags=re.I),
                    f"{filename} contains forbidden contrast phrase '{forbidden}'",
                )

            for leaked in ("Base Thesis", "Markov blanket", "Exocortex"):
                self.assertIsNone(
                    re.search(rf"\b{re.escape(leaked)}\b", plain, flags=re.I),
                    f"{filename} leaks internal term '{leaked}' into everyday prose",
                )

            paragraphs = re.findall(r"<p>(.*?)</p>", body, flags=re.S)
            lengths = []
            for p in paragraphs:
                p_clean = re.sub(r"<[^>]+>", " ", p)
                p_clean = re.sub(r"\s+", " ", p_clean).strip()
                for sent in re.split(r"(?<=[.!?])\s+", p_clean):
                    words = [w for w in sent.split() if w]
                    if len(words) >= 3:
                        lengths.append(len(words))
                        self.assertLessEqual(
                            len(words),
                            35,
                            f"{filename} has sentence > 35 words ({len(words)}): {sent}",
                        )
            self.assertLessEqual(
                statistics.median(lengths),
                20.0,
                f"{filename} median sentence length {statistics.median(lengths)} > 20",
            )


if __name__ == "__main__":
    unittest.main()
