import re
from pathlib import Path
import unittest


SITE_ROOT = Path(__file__).resolve().parents[1]
LABS_INDEX = SITE_ROOT / "content" / "labs" / "index.html"


class TestSimSupplierSwapAndReadTimeMemoryLabs(unittest.TestCase):
    def test_lesson_16_and_researcher_provenance_present(self) -> None:
        html = LABS_INDEX.read_text(encoding="utf-8")
        self.assertIn("<h3>Sixteen lessons from our sandbox</h3>", html)
        self.assertIn(
            "16. Blind retries double-charge orders; dated notes stop mix-ups when switching suppliers.",
            html,
        )
        self.assertIn("We evaluate twenty-one structural mechanisms in our testbed:", html)
        self.assertIn("Idempotent supplier failover and read-time memory resolution:", html)
        for arxiv_id in ("2611.26966", "2611.15729", "2509.21712", "2611.25821"):
            self.assertIn(f"https://arxiv.org/abs/{arxiv_id}", html)

    def test_everyday_prose_excludes_internal_labels_and_keeps_short_sentences(self) -> None:
        html = LABS_INDEX.read_text(encoding="utf-8")
        body = re.sub(r"(?s)^---\n.*?\n---\n", "", html)
        body = re.sub(r"(?is)<style\b.*?</style>", " ", body)
        body = re.sub(r"(?is)<svg\b.*?</svg>", " ", body)
        body = re.sub(r"(?is)<aside\b[^>]*class=\"for-researchers\".*?</aside>", " ", body)
        body = re.sub(r"(?is)<section\b[^>]*class=\"footnotes\".*?</section>", " ", body)
        prose = re.sub(r"<[^>]+>", " ", body)
        prose = re.sub(r"\s+", " ", prose).strip()

        for leaked in ("Base Thesis", "Markov Blanket", "Exocortex", "Device Time", "IETF SCITT", "DISCERN", "OPCP"):
            self.assertNotIn(leaked, prose)
        self.assertNotIn("\u2014", prose)


if __name__ == "__main__":
    unittest.main()
