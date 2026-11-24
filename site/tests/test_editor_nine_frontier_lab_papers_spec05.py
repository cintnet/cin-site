import pathlib
import re
import statistics
import unittest

SITE_DIR = pathlib.Path(__file__).resolve().parents[1]
LAB_PAPERS_DIR = SITE_DIR / "content" / "labs" / "lab-papers"

PAPERS = {
    "openai.html": "ex-lp-openai",
    "anthropic.html": "ex-lp-anthropic",
    "google-deepmind.html": "ex-lp-google-deepmind",
    "meta-ai.html": "ex-lp-meta-ai",
    "deepseek.html": "ex-lp-deepseek",
    "mistral-ai.html": "ex-lp-mistral-ai",
    "alibaba-qwen.html": "ex-lp-alibaba-qwen",
    "safe-superintelligence.html": "ex-lp-safe-superintelligence",
    "physical-intelligence.html": "ex-lp-physical-intelligence",
}

REQUIRED_38_AND_14_BASE_THESIS_TERMS = [
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


def _strip_front_matter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2]
    return text


def _public_body(text: str) -> str:
    body = _strip_front_matter(text)
    body = re.sub(r"<aside\b[^>]*>.*?</aside>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<figure\b[^>]*>.*?</figure>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<section\s+class=\"footnotes\"[^>]*>.*?</section>", " ", body, flags=re.S | re.I)
    return body


class EditorNineFrontierLabPapersSpec05Tests(unittest.TestCase):
    def test_spec05_dark_mode_and_dual_responsive_svgs_with_mobile_connectors(self):
        for filename, fig_id in PAPERS.items():
            path = LAB_PAPERS_DIR / filename
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

    def test_base_thesis_38_and_14_full_name_grounding_and_lab_links(self):
        for filename in PAPERS:
            text = (LAB_PAPERS_DIR / filename).read_text(encoding="utf-8")
            asides = re.findall(r'<aside class="for-researchers">.*?</aside>', text, flags=re.S)
            self.assertTrue(asides, f"{filename} missing for-researchers asides")
            combined_asides = "\n".join(asides)

            for term in REQUIRED_38_AND_14_BASE_THESIS_TERMS:
                self.assertIn(
                    term.lower(),
                    combined_asides.lower(),
                    f"{filename} researcher asides missing Base Thesis term: {term}",
                )

            for lab_link in ("/labs/protocol-inspector/", "/labs/sensor-boundary/", "/labs/shared-horizon/"):
                self.assertIn(lab_link, combined_asides, f"{filename} researcher asides missing link to {lab_link}")

    def test_claim_first_opening_and_humanizer_sentence_invariants(self):
        for filename in PAPERS:
            raw = (LAB_PAPERS_DIR / filename).read_text(encoding="utf-8")
            takeaway_match = re.search(r"^takeaway:\s*(.+)$", raw, flags=re.M)
            self.assertIsNotNone(takeaway_match, f"{filename} missing takeaway front matter")
            takeaway = takeaway_match.group(1).strip()

            body = _public_body(raw)
            first_big = re.search(r'<p class="big">(.*?)</p>', body, flags=re.S)
            self.assertIsNotNone(first_big, f"{filename} missing opening <p class=\"big\">")
            first_big_plain = re.sub(r"<[^>]+>", "", first_big.group(1)).strip()
            self.assertTrue(
                first_big_plain.startswith(takeaway[:45]),
                f"{filename} does not open sentence 1 with its direct takeaway claim: {first_big_plain[:80]}",
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
                    f"{filename} leaks internal term '{leaked}' into public body prose",
                )

            paragraphs = re.findall(r"<p(?:\s+[^>]*)?>(.*?)</p>", body, flags=re.S)
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
