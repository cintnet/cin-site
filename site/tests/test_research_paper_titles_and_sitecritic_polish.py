#!/usr/bin/env python3
"""Deterministic verification suite for research paper titles, LaTeX formatting, and site critic polish (Spec 03/05 / Lane sitecritic).

Audits all public pages in site/content/**/*.html to guarantee:
- 0 leaked raw LaTeX control sequences (\\textbf, \\textit, \\emph, \\cite, \\ref, \\label, \\section, \\subsection, vs.\\)
- Shared Horizon card on homepage reflects all six canonical perspectives
- Shared Horizon takeaway accurately describes the live 348-organisation guidance atlas
- Shared Horizon move count callout stays synchronized with verified records
"""

from pathlib import Path
import re
import unittest

SITE_ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = SITE_ROOT / "content"

LATEX_LEAK_PATTERN = re.compile(
    r'\\[a-zA-Z]+(?:\*|(?=[{_\^]))|\\(?:textbf|textit|emph|cite|ref|label|section|subsection)\b|vs\.\\',
    re.IGNORECASE
)


class ResearchTitlesAndSiteCriticPolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html_files = sorted(CONTENT_DIR.rglob("*.html"))

    def test_zero_raw_latex_leaks_in_public_html(self):
        """No public content file may contain leaked raw LaTeX control sequences in prose or links."""
        violations = []
        for path in self.html_files:
            rel = path.relative_to(SITE_ROOT)
            text = path.read_text(encoding="utf-8")
            # Exclude math mode blocks ($$...$$ and <aside class="for-researchers"> math expressions)
            # Check prose outside of math blocks
            clean_text = re.sub(r'\$\$.*?\$\$', '', text, flags=re.DOTALL)
            clean_text = re.sub(r'\$[^\$]+\$', '', clean_text)
            
            matches = list(LATEX_LEAK_PATTERN.finditer(clean_text))
            for m in matches:
                violations.append(f"{rel}: matched raw LaTeX pattern '{m.group(0)}' at character {m.start()}")

        self.assertEqual(violations, [], "Encountered leaked LaTeX syntax in public content:\n" + "\n".join(violations))

    def test_home_labs_strip_shared_horizon_six_roles(self):
        """Home page Labs strip for Shared Horizon must mention the six canonical roles without em-dashes."""
        home_path = CONTENT_DIR / "index.html"
        self.assertTrue(home_path.exists())
        text = home_path.read_text(encoding="utf-8")
        self.assertIn("one of six roles", text)
        self.assertIn("citizen, official, researcher, lab, builder, or organiser", text)
        self.assertNotIn("role—citizen", text, "Em-dashes must not be present in card description")

    def test_shared_horizon_takeaway_clarity(self):
        """Shared Horizon page takeaway must clearly state the live 348-organisation guidance atlas."""
        sh_path = CONTENT_DIR / "labs" / "shared-horizon.html"
        self.assertTrue(sh_path.exists())
        text = sh_path.read_text(encoding="utf-8")
        self.assertIn("348-organisation guidance atlas", text)
        self.assertNotIn("and that it isn't available yet", text, "Outdated unavailable framing should be removed")

    def test_shared_horizon_callout_move_count(self):
        """Shared Horizon status callout must reflect verified real-world moves."""
        sh_file = CONTENT_DIR / "labs" / "shared-horizon.html"
        content = sh_file.read_text(encoding="utf-8")
        self.assertIn("over 750 verified real-world moves and encounters", content)


if __name__ == "__main__":
    unittest.main()
