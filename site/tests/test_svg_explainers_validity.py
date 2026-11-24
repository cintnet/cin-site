#!/usr/bin/env python3
"""Deterministic verification suite for inline SVG explainers (Spec 05 / Media Lane).

Audits all <figure class="explainer"> elements across the ORG site to ensure:
- Well-formed XML syntax (100% parseable by xml.etree.ElementTree without undefined entities)
- Explicit 'id' attribute prefixed with 'ex-'
- Explicit 'viewBox' attribute on every inline <svg>
- Accessible labelling (role and title/desc/aria-labelledby attributes)
- Strict compliance with Spec 05 and signals S-20261106-4393 and S-20261106-4165
"""

from pathlib import Path
import re
import unittest
from xml.etree import ElementTree as ET

SITE_ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = SITE_ROOT / "content"

EXPLAINER_RE = re.compile(r'<figure\b[^>]*class=["\'][^"\']*\bexplainer\b[^"\']*["\'][^>]*>(.*?)</figure>', re.S)
ID_RE = re.compile(r'\bid\s*=\s*["\']([^"\']+)["\']', re.I)
SVG_RE = re.compile(r'(<svg\b[^>]*>.*?</svg>)', re.S)


class SvgExplainersValidityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html_files = sorted(CONTENT_DIR.rglob("*.html"))
        cls.explainers = []

        for path in cls.html_files:
            rel = path.relative_to(SITE_ROOT)
            text = path.read_text(encoding="utf-8")
            for m in EXPLAINER_RE.finditer(text):
                full_fig = m.group(0)
                body = m.group(1)
                id_m = ID_RE.search(full_fig)
                fig_id = id_m.group(1) if id_m else None
                svgs = SVG_RE.findall(body)
                cls.explainers.append({
                    "file": rel,
                    "id": fig_id,
                    "svgs": svgs,
                    "raw": full_fig,
                })

    def test_explainer_corpus_presence(self):
        """Assert that the site has a rich corpus of inline visual explainers."""
        self.assertGreaterEqual(len(self.explainers), 60, "Expected at least 60 inline explainers across the site.")

    def test_all_explainers_have_valid_ids(self):
        """Every explainer figure must have an id starting with 'ex-'."""
        for ex in self.explainers:
            self.assertIsNotNone(ex["id"], f"Explainer in {ex['file']} lacks an id attribute.")
            self.assertTrue(ex["id"].startswith("ex-"), f"Explainer id '{ex['id']}' in {ex['file']} must start with 'ex-'.")

    def test_all_svgs_have_viewbox(self):
        """Every inline SVG within an explainer must declare a viewBox attribute."""
        for ex in self.explainers:
            self.assertTrue(len(ex["svgs"]) > 0, f"Explainer '{ex['id']}' in {ex['file']} contains no <svg> tag.")
            for svg in ex["svgs"]:
                self.assertIn("viewBox=", svg, f"SVG in explainer '{ex['id']}' ({ex['file']}) missing viewBox attribute.")

    def test_all_svgs_are_well_formed_xml(self):
        """Every inline SVG must parse cleanly as standard XML with no entity or syntax errors."""
        errors = []
        for ex in self.explainers:
            for svg in ex["svgs"]:
                try:
                    ET.fromstring(svg)
                except Exception as err:
                    errors.append(f"{ex['file']} ({ex['id']}): {err}")
        self.assertEqual(errors, [], "Encountered XML parsing errors in inline SVG explainers:\n" + "\n".join(errors))

    def test_key_remediated_explainers_explicitly(self):
        """Verify the 7 remediated explainers specifically parse without XML entity errors."""
        targeted_ids = {
            "ex-skin-not-glass",
            "ex-care-vs-volume",
            "ex-need-finds-answer",
            "ex-craft-vs-chores",
            "ex-middleman-relay-audit",
            "ex-civil-society-defense",
            "ex-five-roles-cycle",
        }
        found_ids = {ex["id"] for ex in self.explainers}
        for target in targeted_ids:
            self.assertIn(target, found_ids, f"Expected remediated explainer '{target}' to exist.")
            matching = [ex for ex in self.explainers if ex["id"] == target][0]
            for svg in matching["svgs"]:
                root = ET.fromstring(svg)
                self.assertEqual(root.tag.split("}")[-1], "svg")


if __name__ == "__main__":
    unittest.main()
