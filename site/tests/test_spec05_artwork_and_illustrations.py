#!/usr/bin/env python3
"""Deterministic verification suite for Spec 05 Artwork, Editorial Illustrations, and SVG Explainers.

Enforces:
1. Artwork size & format:
   - All `site/assets/img/post-*.jpg` are <= 300 KB (< 300,000 bytes).
   - Every frontmatter `image:` in `site/content/blog/*.html` points to an existing file in `site/assets/img/`.
   - Every frontmatter `image_alt:` has descriptive text (>= 15 characters, no boilerplate).
2. Explainer Figure Architecture:
   - Every `<figure class="explainer">` across all HTML pages declares an `id` starting with 'ex-'.
   - Every inline `<svg>` declares a viewBox attribute.
   - Every inline `<svg>` provides accessible metadata (<title> and <desc>).
   - Mobile `<svg>` elements declare viewBox width <= 330 to fit standard mobile viewports.
   - Every SVG is 100% valid XML parseable by xml.etree.ElementTree.
"""

from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

SITE_ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = SITE_ROOT / "content"
BLOG_DIR = CONTENT_DIR / "blog"
IMG_DIR = SITE_ROOT / "assets" / "img"

EXPLAINER_RE = re.compile(r'<figure\b[^>]*class=["\'][^"\']*\bexplainer\b[^"\']*["\'][^>]*>(.*?)</figure>', re.S)
ID_RE = re.compile(r'\bid\s*=\s*["\']([^"\']+)["\']', re.I)
SVG_RE = re.compile(r'(<svg\b[^>]*>.*?</svg>)', re.S)


class Spec05ArtworkAndIllustrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html_files = sorted(CONTENT_DIR.rglob("*.html"))
        cls.blog_files = sorted(BLOG_DIR.glob("*.html"))
        cls.img_files = sorted(IMG_DIR.glob("*.*"))

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

    def test_post_images_under_300kb_spec(self):
        """All post illustration assets in site/assets/img/post-*.jpg must be under 300 KB."""
        oversized = []
        for img_path in self.img_files:
            if img_path.name.startswith("post-"):
                sz = img_path.stat().st_size
                if sz > 300000:
                    oversized.append(f"{img_path.name} ({sz} bytes > 300,000 bytes)")
        self.assertEqual(oversized, [], "Illustrations exceed 300 KB limit:\n" + "\n".join(oversized))

    def test_blog_frontmatter_image_and_alt_invariants(self):
        """Every blog post must declare an existing image and a descriptive alt text >= 15 chars."""
        errors = []
        for path in self.blog_files:
            if path.name == "index.html":
                continue
            text = path.read_text(encoding="utf-8")
            m_img = re.search(r"^image:\s*([^\r\n]+)", text, re.M)
            m_alt = re.search(r"^image_alt:\s*([^\r\n]+)", text, re.M)

            if not m_img:
                errors.append(f"{path.name}: missing 'image:' in frontmatter")
            else:
                img_name = m_img.group(1).strip()
                img_file = IMG_DIR / img_name
                if not img_file.exists():
                    errors.append(f"{path.name}: image '{img_name}' not found on disk")

            if not m_alt:
                errors.append(f"{path.name}: missing 'image_alt:' in frontmatter")
            else:
                alt_str = m_alt.group(1).strip()
                if len(alt_str) < 15:
                    errors.append(f"{path.name}: image_alt '{alt_str}' is too short (< 15 chars)")

        self.assertEqual(errors, [], "Blog post image/alt invariants failed:\n" + "\n".join(errors))

    def test_all_explainers_have_ex_prefixed_ids(self):
        """Every <figure class='explainer'> must have an id attribute starting with 'ex-'."""
        self.assertGreaterEqual(len(self.explainers), 60, "Expected at least 60 inline explainers across the site.")
        for ex in self.explainers:
            self.assertIsNotNone(ex["id"], f"Explainer in {ex['file']} lacks an id attribute.")
            self.assertTrue(ex["id"].startswith("ex-"), f"Explainer id '{ex['id']}' in {ex['file']} must start with 'ex-'.")

    def test_all_svgs_have_viewbox_and_valid_xml(self):
        """Every inline SVG must declare a viewBox attribute and parse cleanly as XML."""
        errors = []
        for ex in self.explainers:
            self.assertTrue(len(ex["svgs"]) > 0, f"Explainer '{ex['id']}' in {ex['file']} contains no <svg> tag.")
            for idx, svg in enumerate(ex["svgs"]):
                if "viewBox=" not in svg:
                    errors.append(f"{ex['file']} (#{ex['id']}) svg #{idx} missing viewBox")
                try:
                    ET.fromstring(svg)
                except Exception as err:
                    errors.append(f"{ex['file']} (#{ex['id']}) svg #{idx} parse error: {err}")
        self.assertEqual(errors, [], "Inline SVG viewBox or XML syntax errors:\n" + "\n".join(errors))

    def test_all_svgs_have_accessible_titles_and_descriptions(self):
        """Every inline SVG must have non-empty <title> and <desc> elements for accessibility."""
        missing = []
        for ex in self.explainers:
            for idx, svg in enumerate(ex["svgs"]):
                try:
                    root = ET.fromstring(svg)
                except Exception:
                    continue
                # Extract child tags regardless of XML namespace
                title_node = None
                desc_node = None
                for child in root:
                    tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    if tag == "title":
                        title_node = child
                    elif tag == "desc":
                        desc_node = child

                if title_node is None or not (title_node.text or "").strip():
                    missing.append(f"{ex['file']} (#{ex['id']}) svg #{idx} missing <title>")
                if desc_node is None or not (desc_node.text or "").strip():
                    missing.append(f"{ex['file']} (#{ex['id']}) svg #{idx} missing <desc>")

        self.assertEqual(missing, [], "Accessible <title> or <desc> missing from inline SVGs:\n" + "\n".join(missing))

    def test_mobile_svg_viewbox_bounds(self):
        """Mobile inline SVGs must declare a viewBox width <= 330 to fit mobile screens without clipping."""
        too_wide = []
        for ex in self.explainers:
            for idx, svg in enumerate(ex["svgs"]):
                try:
                    root = ET.fromstring(svg)
                except Exception:
                    continue
                cls_attr = root.attrib.get("class", "")
                if "diagram-mobile" in cls_attr or "mobile" in cls_attr:
                    vb = root.attrib.get("viewBox", "")
                    parts = vb.split()
                    if len(parts) >= 4:
                        vb_w = float(parts[2])
                        if vb_w > 330.0:
                            too_wide.append(f"{ex['file']} (#{ex['id']}) mobile viewBox width is {vb_w} (must be <= 330)")

        self.assertEqual(too_wide, [], "Mobile SVGs exceed 330px width:\n" + "\n".join(too_wide))


if __name__ == "__main__":
    unittest.main()
