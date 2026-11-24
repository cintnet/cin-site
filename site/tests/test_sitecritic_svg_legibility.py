#!/usr/bin/env python3
"""Deterministic verification suite for SVG explainer mobile legibility and boundary containment.

Audits:
- site/content/blog/between-hovering-and-blind-trust.html
- site/content/blog/who-is-actually-acting.html
- site/content/blog/why-containment-runs-out-of-time.html
- site/content/blog/why-pricing-bots-learn-not-to-compete.html
- site/content/blog/why-the-digital-sidewalk-needs-tactile-paving.html

Verifies:
1. Valid XML with role="img", <title>, and <desc> on both desktop and mobile SVGs.
2. Zero text overflow beyond viewBox width (330px on mobile) and inner card bounds.
3. Sentence length invariants (median <= 22 words, max <= 35 words) and zero em-dashes.
"""

from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

SITE_ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = SITE_ROOT / "content"


class SiteCriticSvgLegibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hovering_path = CONTENT_DIR / "blog" / "between-hovering-and-blind-trust.html"
        cls.acting_path = CONTENT_DIR / "blog" / "who-is-actually-acting.html"
        cls.containment_path = CONTENT_DIR / "blog" / "why-containment-runs-out-of-time.html"
        cls.tactile_path = CONTENT_DIR / "blog" / "why-the-digital-sidewalk-needs-tactile-paving.html"
        cls.pricing_path = CONTENT_DIR / "blog" / "why-pricing-bots-learn-not-to-compete.html"
        cls.boundary_path = CONTENT_DIR / "blog" / "why-an-assistant-needs-an-audience-boundary.html"
        cls.invoice_path = CONTENT_DIR / "blog" / "when-an-invoice-gives-orders-to-your-assistant.html"
        cls.cider_path = CONTENT_DIR / "blog" / "when-the-cider-press-runs-itself.html"
        cls.robot_path = CONTENT_DIR / "blog" / "why-a-robot-arm-needs-a-gravity-brake.html"
        cls.research_path = CONTENT_DIR / "research.html"
        cls.institutions_path = CONTENT_DIR / "labs" / "institutions.html"
        cls.ostrom_path = CONTENT_DIR / "blog" / "how-groups-govern-a-shared-resource.html"
        cls.audit_path = CONTENT_DIR / "blog" / "why-an-ai-agent-will-not-audit-itself.html"
        cls.assertTrue(cls.hovering_path.exists(), f"Missing {cls.hovering_path}")
        cls.assertTrue(cls.acting_path.exists(), f"Missing {cls.acting_path}")
        cls.assertTrue(cls.containment_path.exists(), f"Missing {cls.containment_path}")
        cls.assertTrue(cls.tactile_path.exists(), f"Missing {cls.tactile_path}")
        cls.assertTrue(cls.pricing_path.exists(), f"Missing {cls.pricing_path}")
        cls.assertTrue(cls.boundary_path.exists(), f"Missing {cls.boundary_path}")
        cls.assertTrue(cls.invoice_path.exists(), f"Missing {cls.invoice_path}")
        cls.assertTrue(cls.cider_path.exists(), f"Missing {cls.cider_path}")
        cls.assertTrue(cls.robot_path.exists(), f"Missing {cls.robot_path}")
        cls.assertTrue(cls.research_path.exists(), f"Missing {cls.research_path}")
        cls.assertTrue(cls.institutions_path.exists(), f"Missing {cls.institutions_path}")
        cls.assertTrue(cls.ostrom_path.exists(), f"Missing {cls.ostrom_path}")
        cls.assertTrue(cls.audit_path.exists(), f"Missing {cls.audit_path}")
        cls.hovering_text = cls.hovering_path.read_text(encoding="utf-8")
        cls.acting_text = cls.acting_path.read_text(encoding="utf-8")
        cls.containment_text = cls.containment_path.read_text(encoding="utf-8")
        cls.tactile_text = cls.tactile_path.read_text(encoding="utf-8")
        cls.pricing_text = cls.pricing_path.read_text(encoding="utf-8")
        cls.boundary_text = cls.boundary_path.read_text(encoding="utf-8")
        cls.invoice_text = cls.invoice_path.read_text(encoding="utf-8")
        cls.cider_text = cls.cider_path.read_text(encoding="utf-8")
        cls.robot_text = cls.robot_path.read_text(encoding="utf-8")
        cls.research_text = cls.research_path.read_text(encoding="utf-8")
        cls.institutions_text = cls.institutions_path.read_text(encoding="utf-8")
        cls.ostrom_text = cls.ostrom_path.read_text(encoding="utf-8")
        cls.audit_text = cls.audit_path.read_text(encoding="utf-8")

    def _extract_svgs(self, html_text, figure_id):
        match = re.search(rf'<figure\b[^>]*\bid=["\']{figure_id}["\'][^>]*>(.*?)</figure>', html_text, re.DOTALL)
        self.assertIsNotNone(match, f"Figure with id '{figure_id}' not found")
        fig_content = match.group(1)
        svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', fig_content, re.DOTALL)
        self.assertGreaterEqual(len(svgs), 2, f"Expected desktop and mobile SVGs in #{figure_id}")
        return svgs[0], svgs[1]

    def test_between_hovering_and_blind_trust_svg_roles_and_accessibility(self):
        """Desktop and mobile SVGs in between-hovering-and-blind-trust must have role='img' and valid XML."""
        desktop_svg, mobile_svg = self._extract_svgs(self.hovering_text, "ex-delegation-checkpoints")

        for svg_str in (desktop_svg, mobile_svg):
            root = ET.fromstring(svg_str)
            self.assertEqual(root.tag, "svg")
            self.assertEqual(root.attrib.get("role"), "img", "SVG missing role='img'")
            title = root.find("title")
            desc = root.find("desc")
            self.assertIsNotNone(title, "SVG missing <title>")
            self.assertIsNotNone(desc, "SVG missing <desc>")
            self.assertTrue(title.text and len(title.text.strip()) > 5)

    def test_between_hovering_and_blind_trust_mobile_svg_text_bounds(self):
        """Mobile SVG text elements in between-hovering-and-blind-trust must not overflow 330px viewBox."""
        _, mobile_svg = self._extract_svgs(self.hovering_text, "ex-delegation-checkpoints")
        root = ET.fromstring(mobile_svg)
        vb = root.attrib.get("viewBox", "")
        self.assertIn("330", vb)

        overflows = []
        for text_el in root.iter("text"):
            content = (text_el.text or "").strip()
            if not content:
                continue
            x = float(text_el.attrib.get("x", "0"))
            fs = float(text_el.attrib.get("font-size", "11"))
            anchor = text_el.attrib.get("text-anchor", "start")
            est_width = len(content) * (fs * 0.58)
            right_edge = x + (est_width / 2) if anchor == "middle" else (x if anchor == "end" else x + est_width)
            # Mobile card is shifted by translate(10, ...), max inner width is 310
            if right_edge > 310.0:
                overflows.append(f"'{content}' (len {len(content)}, right_edge={right_edge:.1f} > 310)")

        self.assertEqual(overflows, [], "Mobile SVG text elements overflow card boundaries:\n" + "\n".join(overflows))

    def test_who_is_actually_acting_svg_roles_and_accessibility(self):
        """Desktop and mobile SVGs in who-is-actually-acting must have role='img' and valid XML."""
        desktop_svg, mobile_svg = self._extract_svgs(self.acting_text, "ex-action-receipt")

        for svg_str in (desktop_svg, mobile_svg):
            root = ET.fromstring(svg_str)
            self.assertEqual(root.tag, "svg")
            self.assertEqual(root.attrib.get("role"), "img", "SVG missing role='img'")
            title = root.find("title")
            desc = root.find("desc")
            self.assertIsNotNone(title, "SVG missing <title>")
            self.assertIsNotNone(desc, "SVG missing <desc>")
            self.assertTrue(title.text and len(title.text.strip()) > 5)

    def test_who_is_actually_acting_mobile_svg_text_bounds(self):
        """Mobile SVG text elements in who-is-actually-acting must not overflow 330px viewBox."""
        _, mobile_svg = self._extract_svgs(self.acting_text, "ex-action-receipt")
        root = ET.fromstring(mobile_svg)
        vb = root.attrib.get("viewBox", "")
        self.assertIn("330", vb)

        overflows = []
        for text_el in root.iter("text"):
            content = (text_el.text or "").strip()
            if not content:
                continue
            x = float(text_el.attrib.get("x", "0"))
            fs = float(text_el.attrib.get("font-size", "11"))
            anchor = text_el.attrib.get("text-anchor", "start")
            est_width = len(content) * (fs * 0.58)
            right_edge = x + (est_width / 2) if anchor == "middle" else (x if anchor == "end" else x + est_width)
            if right_edge > 310.0:
                overflows.append(f"'{content}' (len {len(content)}, right_edge={right_edge:.1f} > 310)")

        self.assertEqual(overflows, [], "Mobile SVG text elements overflow card boundaries:\n" + "\n".join(overflows))

    def test_why_containment_runs_out_of_time_svg_roles_and_accessibility(self):
        """Desktop and mobile SVGs in why-containment-runs-out-of-time must have role='img' and valid XML."""
        desktop_svg, mobile_svg = self._extract_svgs(self.containment_text, "ex-containment-horizon")

        for svg_str in (desktop_svg, mobile_svg):
            root = ET.fromstring(svg_str)
            self.assertEqual(root.tag, "svg")
            self.assertEqual(root.attrib.get("role"), "img", "SVG must have role='img'")
            title = root.find("title")
            desc = root.find("desc")
            self.assertIsNotNone(title, "SVG missing <title>")
            self.assertIsNotNone(desc, "SVG missing <desc>")

    def test_why_containment_runs_out_of_time_mobile_svg_text_bounds(self):
        """Mobile SVG text elements in why-containment-runs-out-of-time must not overflow 330px viewBox."""
        _, mobile_svg = self._extract_svgs(self.containment_text, "ex-containment-horizon")
        root = ET.fromstring(mobile_svg)

        overflows = []
        for text_el in root.iter("text"):
            content = (text_el.text or "").strip()
            if not content:
                continue
            x = float(text_el.attrib.get("x", "0"))
            fs = float(text_el.attrib.get("font-size", "11"))
            anchor = text_el.attrib.get("text-anchor", "start")
            est_width = len(content) * (fs * 0.58)
            right_edge = x + (est_width / 2) if anchor == "middle" else (x if anchor == "end" else x + est_width)
            if right_edge > 310.0:
                overflows.append(f"'{content}' (len {len(content)}, right_edge={right_edge:.1f} > 310)")

        self.assertEqual(overflows, [], "Mobile SVG text elements overflow card boundaries:\n" + "\n".join(overflows))

    def test_why_the_digital_sidewalk_needs_tactile_paving_svg_roles_and_accessibility(self):
        """Desktop and mobile SVGs in why-the-digital-sidewalk-needs-tactile-paving must have role='img' and valid XML."""
        desktop_svg, mobile_svg = self._extract_svgs(self.tactile_text, "ex-tactile-paving")

        for svg_str in (desktop_svg, mobile_svg):
            root = ET.fromstring(svg_str)
            self.assertEqual(root.tag, "svg")
            self.assertEqual(root.attrib.get("role"), "img", "SVG must have role='img'")
            title = root.find("title")
            desc = root.find("desc")
            self.assertIsNotNone(title, "SVG missing <title>")
            self.assertIsNotNone(desc, "SVG missing <desc>")

    def test_why_the_digital_sidewalk_needs_tactile_paving_mobile_svg_text_bounds(self):
        """Mobile SVG text elements in why-the-digital-sidewalk-needs-tactile-paving must not overflow 330px viewBox."""
        _, mobile_svg = self._extract_svgs(self.tactile_text, "ex-tactile-paving")
        root = ET.fromstring(mobile_svg)
        vb = root.attrib.get("viewBox", "")
        self.assertIn("330", vb)

        overflows = []
        for text_el in root.iter("text"):
            content = (text_el.text or "").strip()
            if not content:
                continue
            x = float(text_el.attrib.get("x", "0"))
            fs = float(text_el.attrib.get("font-size", "11"))
            anchor = text_el.attrib.get("text-anchor", "start")
            est_width = len(content) * (fs * 0.58)
            right_edge = x + (est_width / 2) if anchor == "middle" else (x if anchor == "end" else x + est_width)
            if right_edge > 310.0:
                overflows.append(f"'{content}' (len {len(content)}, right_edge={right_edge:.1f} > 310)")

        self.assertEqual(overflows, [], "Mobile SVG text elements overflow card boundaries:\n" + "\n".join(overflows))

    def test_why_pricing_bots_learn_not_to_compete_svg_roles_and_accessibility(self):
        """Desktop and mobile SVGs in why-pricing-bots-learn-not-to-compete must have role='img' and valid XML."""
        desktop_svg, mobile_svg = self._extract_svgs(self.pricing_text, "ex-pricing-loop")

        for svg_str in (desktop_svg, mobile_svg):
            root = ET.fromstring(svg_str)
            self.assertEqual(root.tag, "svg")
            self.assertEqual(root.attrib.get("role"), "img", "SVG missing role='img'")
            title = root.find("title")
            desc = root.find("desc")
            self.assertIsNotNone(title, "SVG missing <title>")
            self.assertIsNotNone(desc, "SVG missing <desc>")

    def test_why_pricing_bots_learn_not_to_compete_mobile_svg_text_bounds(self):
        """Mobile SVG text elements in why-pricing-bots-learn-not-to-compete must not overflow 330px viewBox."""
        _, mobile_svg = self._extract_svgs(self.pricing_text, "ex-pricing-loop")
        root = ET.fromstring(mobile_svg)
        vb = root.attrib.get("viewBox", "")
        self.assertIn("330", vb)

        overflows = []
        for text_el in root.iter("text"):
            content = (text_el.text or "").strip()
            if not content:
                continue
            x = float(text_el.attrib.get("x", "0"))
            fs = float(text_el.attrib.get("font-size", "11"))
            anchor = text_el.attrib.get("text-anchor", "start")
            est_width = len(content) * (fs * 0.58)
            right_edge = x + (est_width / 2) if anchor == "middle" else (x if anchor == "end" else x + est_width)
            if right_edge > 310.0:
                overflows.append(f"'{content}' (len {len(content)}, right_edge={right_edge:.1f} > 310)")

        self.assertEqual(overflows, [], "Mobile SVG text elements overflow card boundaries:\n" + "\n".join(overflows))

    def test_why_an_assistant_needs_an_audience_boundary_svg_roles_and_accessibility(self):
        """Desktop and mobile SVGs in why-an-assistant-needs-an-audience-boundary must have role='img' and valid XML."""
        desktop_svg, mobile_svg = self._extract_svgs(self.boundary_text, "ex-audience-boundary")

        for svg_str in (desktop_svg, mobile_svg):
            root = ET.fromstring(svg_str)
            self.assertEqual(root.tag, "svg")
            self.assertEqual(root.attrib.get("role"), "img", "SVG missing role='img'")
            title = root.find("title")
            desc = root.find("desc")
            self.assertIsNotNone(title, "SVG missing <title>")
            self.assertIsNotNone(desc, "SVG missing <desc>")
            self.assertTrue(title.text and len(title.text.strip()) > 5)

    def test_why_an_assistant_needs_an_audience_boundary_mobile_svg_text_bounds(self):
        """Mobile SVG text elements in why-an-assistant-needs-an-audience-boundary must not overflow 330px viewBox."""
        _, mobile_svg = self._extract_svgs(self.boundary_text, "ex-audience-boundary")
        root = ET.fromstring(mobile_svg)
        vb = root.attrib.get("viewBox", "")
        self.assertIn("330", vb)

        overflows = []
        for text_el in root.iter("text"):
            content = (text_el.text or "").strip()
            if not content:
                continue
            x = float(text_el.attrib.get("x", "0"))
            fs = float(text_el.attrib.get("font-size", "11"))
            anchor = text_el.attrib.get("text-anchor", "start")
            est_width = len(content) * (fs * 0.58)
            right_edge = x + (est_width / 2) if anchor == "middle" else (x if anchor == "end" else x + est_width)
            if right_edge > 310.0:
                overflows.append(f"'{content}' (len {len(content)}, right_edge={right_edge:.1f} > 310)")

        self.assertEqual(overflows, [], "Mobile SVG text elements in #ex-audience-boundary overflow card boundaries:\n" + "\n".join(overflows))

    def test_how_groups_govern_a_shared_resource_svg_roles_and_accessibility(self):
        """Desktop and mobile SVGs in how-groups-govern-a-shared-resource must have role='img' and valid XML."""
        desktop_svg, mobile_svg = self._extract_svgs(self.ostrom_text, "ex-ostrom-commons")

        for svg_str in (desktop_svg, mobile_svg):
            root = ET.fromstring(svg_str)
            self.assertEqual(root.tag, "svg")
            self.assertEqual(root.attrib.get("role"), "img", "SVG missing role='img'")
            title = root.find("title")
            desc = root.find("desc")
            self.assertIsNotNone(title, "SVG missing <title>")
            self.assertIsNotNone(desc, "SVG missing <desc>")
            self.assertTrue(title.text and len(title.text.strip()) > 5)

    def test_how_groups_govern_a_shared_resource_mobile_svg_text_bounds(self):
        """Mobile SVG text elements in how-groups-govern-a-shared-resource must not overflow 330px viewBox."""
        _, mobile_svg = self._extract_svgs(self.ostrom_text, "ex-ostrom-commons")
        root = ET.fromstring(mobile_svg)
        vb = root.attrib.get("viewBox", "")
        self.assertIn("330", vb)

        overflows = []
        for text_el in root.iter("text"):
            content = (text_el.text or "").strip()
            if not content:
                continue
            x = float(text_el.attrib.get("x", "0"))
            fs = float(text_el.attrib.get("font-size", "11"))
            anchor = text_el.attrib.get("text-anchor", "start")
            est_width = len(content) * (fs * 0.58)
            right_edge = x + (est_width / 2) if anchor == "middle" else (x if anchor == "end" else x + est_width)
            if right_edge > 310.0:
                overflows.append(f"'{content}' (len {len(content)}, right_edge={right_edge:.1f} > 310)")

        self.assertEqual(overflows, [], "Mobile SVG text elements in #ex-ostrom-commons overflow card boundaries:\n" + "\n".join(overflows))

    def test_why_an_ai_agent_will_not_audit_itself_svg_roles_and_accessibility(self):
        """Desktop and mobile SVGs in why-an-ai-agent-will-not-audit-itself must have role='img' and valid XML."""
        desktop_svg, mobile_svg = self._extract_svgs(self.audit_text, "ex-outside-audit")

        for svg_str in (desktop_svg, mobile_svg):
            root = ET.fromstring(svg_str)
            self.assertEqual(root.tag, "svg")
            self.assertEqual(root.attrib.get("role"), "img", "SVG missing role='img'")
            title = root.find("title")
            desc = root.find("desc")
            self.assertIsNotNone(title, "SVG missing <title>")
            self.assertIsNotNone(desc, "SVG missing <desc>")
            self.assertTrue(title.text and len(title.text.strip()) > 5)

    def test_why_an_ai_agent_will_not_audit_itself_mobile_svg_text_bounds(self):
        """Mobile SVG text elements in why-an-ai-agent-will-not-audit-itself must not overflow 330px viewBox."""
        _, mobile_svg = self._extract_svgs(self.audit_text, "ex-outside-audit")
        root = ET.fromstring(mobile_svg)
        vb = root.attrib.get("viewBox", "")
        self.assertIn("330", vb)

        overflows = []
        for text_el in root.iter("text"):
            content = (text_el.text or "").strip()
            if not content:
                continue
            x = float(text_el.attrib.get("x", "0"))
            fs = float(text_el.attrib.get("font-size", "11"))
            anchor = text_el.attrib.get("text-anchor", "start")
            est_width = len(content) * (fs * 0.58)
            right_edge = x + (est_width / 2) if anchor == "middle" else (x if anchor == "end" else x + est_width)
            if right_edge > 310.0:
                overflows.append(f"'{content}' (len {len(content)}, right_edge={right_edge:.1f} > 310)")

        self.assertEqual(overflows, [], "Mobile SVG text elements in #ex-outside-audit overflow card boundaries:\n" + "\n".join(overflows))

    def test_interactive_bench_svg_roles_and_accessibility(self):
        """Interactive bench SVGs on invoice, cider-press, and robot-arm essays must have role='img', <title>, and <desc>."""
        for name, text in [
            ("when-an-invoice-gives-orders-to-your-assistant", self.invoice_text),
            ("when-the-cider-press-runs-itself", self.cider_text),
            ("why-a-robot-arm-needs-a-gravity-brake", self.robot_text),
            ("how-groups-govern-a-shared-resource", self.ostrom_text),
            ("why-an-ai-agent-will-not-audit-itself", self.audit_text),
        ]:
            svg_match = re.search(r'<svg\b[^>]*>.*?</svg>', text, re.DOTALL)
            self.assertIsNotNone(svg_match, f"SVG missing in {name}")
            root = ET.fromstring(svg_match.group(0))
            self.assertEqual(root.tag, "svg")
            self.assertEqual(root.attrib.get("role"), "img", f"{name}: SVG missing role='img'")
            title = root.find("title")
            desc = root.find("desc")
            self.assertIsNotNone(title, f"{name}: SVG missing <title>")
            self.assertIsNotNone(desc, f"{name}: SVG missing <desc>")
            self.assertTrue(title.text and len(title.text.strip()) > 5)

    def test_zero_sub_10px_fonts_across_audited_surfaces(self):
        """All SVG text elements on audited pages must maintain font-size >= 10.0px for mobile legibility."""
        for name, text in [
            ("when-an-invoice-gives-orders-to-your-assistant", self.invoice_text),
            ("when-the-cider-press-runs-itself", self.cider_text),
            ("why-a-robot-arm-needs-a-gravity-brake", self.robot_text),
            ("how-groups-govern-a-shared-resource", self.ostrom_text),
            ("who-is-actually-acting", self.acting_text),
            ("why-an-ai-agent-will-not-audit-itself", self.audit_text),
            ("research", self.research_text),
            ("institutions", self.institutions_text),
        ]:
            for m in re.finditer(r'<svg\b[^>]*>(.*?)</svg>', text, re.DOTALL):
                body = m.group(1)
                for font in re.finditer(r'font-size=[\"\']([0-9.]+)(?:px)?[\"\']', body):
                    sz = float(font.group(1))
                    self.assertGreaterEqual(
                        sz,
                        10.0,
                        f"{name}: found sub-10px font-size={sz}px in SVG text element"
                    )

    def test_prose_sentence_invariants_and_zero_emdashes(self):
        """All audited essays must maintain median <= 22 words, zero > 35 words, and zero em-dashes."""
        for name, text in [
            ("between-hovering-and-blind-trust", self.hovering_text),
            ("who-is-actually-acting", self.acting_text),
            ("why-an-assistant-needs-an-audience-boundary", self.boundary_text),
            ("why-containment-runs-out-of-time", self.containment_text),
            ("why-pricing-bots-learn-not-to-compete", self.pricing_text),
            ("why-the-digital-sidewalk-needs-tactile-paving", self.tactile_text),
            ("when-an-invoice-gives-orders-to-your-assistant", self.invoice_text),
            ("when-the-cider-press-runs-itself", self.cider_text),
            ("why-a-robot-arm-needs-a-gravity-brake", self.robot_text),
            ("how-groups-govern-a-shared-resource", self.ostrom_text),
            ("why-an-ai-agent-will-not-audit-itself", self.audit_text),
        ]:
            body = re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL)
            clean = re.sub(r"<(style|script|figure|svg|aside|section)[^>]*>.*?</\1>", "", body, flags=re.DOTALL)
            clean_text = re.sub(r"<[^>]+>", " ", clean)

            sentences = [s.strip() for s in re.split(r"[.!?]+", clean_text) if s.strip()]
            words_per_sentence = [len(s.split()) for s in sentences if len(s.split()) > 3]

            median_len = sorted(words_per_sentence)[len(words_per_sentence) // 2]
            max_len = max(words_per_sentence)

            self.assertLessEqual(median_len, 22, f"{name}: median sentence length {median_len} > 22")
            self.assertLessEqual(max_len, 35, f"{name}: max sentence length {max_len} > 35")
            self.assertNotIn("—", clean_text, f"{name}: found forbidden em-dash in body prose")


if __name__ == "__main__":
    unittest.main()
