"""Tests for the mechanical anti-slop internal-leak guardrails in `site/scripts/prose.py`
and `loop/agent_contribution_auditor.py`."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

SITE_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SITE_DIR / "scripts"
CIN_LOOP_DIR = SITE_DIR.parent.parent.parent / "CIN" / "loop"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))
if str(SITE_DIR) not in sys.path:
    sys.path.append(str(SITE_DIR))

import prose  # noqa: E402


PAGE_TEMPLATE = """---
title: Plain Everyday Guide
takeaway: Software assistants need expiring passes so a leaked key stops working at noon.
template: page
lede: {lede}
---
{body}
"""


class ProseAntiSlopLeakGateTests(unittest.TestCase):
    def _check(self, body: str, lede: str = "Software assistants need expiring passes.", baseline: dict | None = None) -> list[str]:
        doc = PAGE_TEMPLATE.format(lede=lede, body=body)
        return prose.check_text("blog/candidate.html", doc, baseline or {})

    def test_rejects_internal_l1_through_l5_architecture_codes(self) -> None:
        for code in ("L1", "L2", "L3", "L4", "L5", "L1-L5", "L1–L5"):
            errs = self._check(f"<p>Our {code} verification pipeline signs local readings.</p>")
            self.assertTrue(
                any("internal architecture or ungrounded jargon leak" in e for e in errs),
                msg=f"Expected {code!r} to be rejected, got {errs!r}",
            )

    def test_allows_legitimate_cpu_cache_references(self) -> None:
        errs = self._check("<p>A modern processor stores hot instructions in its L1 cache and L2 cache.</p>")
        self.assertEqual(errs, [])

    def test_rejects_numbered_layer_colon_and_five_layer_deliverable(self) -> None:
        errs_layer = self._check("<p>Layer 1: Perceptual sensorium latches hardware clocks.</p>")
        self.assertTrue(any("internal architecture" in e for e in errs_layer))
        errs_deliverable = self._check("<p>This 5-Layer Functional Deliverable protects users.</p>")
        self.assertTrue(any("internal architecture" in e for e in errs_deliverable))

    def test_rejects_waymo_grade_heartbeat_stack_and_base_thesis(self) -> None:
        for phrase in ("Waymo-grade", "Waymo like hardware", "Heartbeat Stack", "Base Thesis"):
            errs = self._check(f"<p>Every household gets {phrase} protection locally.</p>")
            self.assertTrue(
                any("internal architecture or ungrounded jargon leak" in e for e in errs),
                msg=f"Expected {phrase!r} to fail prose check, got {errs!r}",
            )

    def test_rejects_bare_markov_blanket_exocortex_and_teleonomic_in_body_prose(self) -> None:
        for jargon in ("Markov blanket", "Markov blankets", "exocortex", "Exocortex", "teleonomic", "Teleonomic"):
            errs = self._check(f"<p>Your personal {jargon} filters outgoing requests.</p>")
            self.assertTrue(
                any("internal architecture or ungrounded jargon leak" in e for e in errs),
                msg=f"Expected bare {jargon!r} in body prose to fail, got {errs!r}",
            )

    def test_allows_markov_blanket_and_technical_terms_inside_for_researchers_aside_and_footnotes(self) -> None:
        body = (
            "<p>Your assistant works like an accountant bound to keep your family ledger private.</p>"
            '<aside class="for-researchers"><details><summary>For researchers</summary>'
            "<div><p>Formally, this boundary acts as a Markov blanket around an exocortex with teleonomic goals.</p></div>"
            "</details></aside>"
            '<section class="footnotes"><p id="fn1">1. Karl Friston on Markov blankets in active inference.</p></section>'
        )
        self.assertEqual(self._check(body), [])

    def test_hard_limit_zero_cannot_be_grandfathered_by_baseline(self) -> None:
        spoofed_baseline = {
            "blog/candidate.html": {
                "staged": 5,
                "tics": 5,
                "aphorism": 5,
                "buried": 5,
                "internal_leak": 5,
            }
        }
        errs = self._check("<p>The Heartbeat Stack seals L3 memory.</p>", baseline=spoofed_baseline)
        self.assertTrue(any("limit 0" in e for e in errs))

    def test_all_existing_site_pages_pass_with_zero_errors(self) -> None:
        baseline = prose.load_baseline()
        pages = list(prose.all_pages())
        self.assertGreaterEqual(len(pages), 100)
        all_errs: list[str] = []
        for name, raw in pages:
            counts = prose.measure(raw)
            self.assertEqual(
                counts["internal_leak"],
                0,
                msg=f"Existing page {name} has internal_leak={counts['internal_leak']}",
            )
            all_errs.extend(prose.check_text(name, raw, baseline))
        self.assertEqual(all_errs, [])

    def test_auditor_forbidden_patterns_catch_public_surface_scaffolding(self) -> None:
        if not (CIN_LOOP_DIR / "agent_contribution_auditor.py").exists():
            self.skipTest("CIN loop directory not mounted alongside site repo")
        if str(CIN_LOOP_DIR) not in sys.path:
            sys.path.insert(0, str(CIN_LOOP_DIR))
        import agent_contribution_auditor as aca  # type: ignore[import-not-found]

        samples = (
            "L1 · Multimodal Sensorium",
            "Architecture spans L1 to L5 end to end",
            "The (L3) layer filters private records",
            "Equipped with Waymo-grade sensors",
            "Powered by the Heartbeat Stack",
            "Derived from the Base Thesis Kernel",
        )
        for sample in samples:
            matched = any(rx.search(sample) for rx, _reason in aca.FORBIDDEN_VALUE_PATTERNS)
            self.assertTrue(matched, msg=f"Auditor failed to flag leaked scaffolding: {sample!r}")


if __name__ == "__main__":
    unittest.main()
