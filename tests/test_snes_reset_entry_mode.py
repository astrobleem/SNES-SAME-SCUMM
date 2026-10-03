from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SnesResetEntryModeTests(unittest.TestCase):
    def test_reset_enters_native_mode_before_width_sensitive_diagnostics(self) -> None:
        source = (ROOT / "runtime/snes/main.pasm").read_text(encoding="utf-8")
        reset = source.split("reset:\n", 1)[1].split(
            '.include "generated/carrier_boot.inc.pasm"', 1
        )[0]
        instructions = [
            line.split(";", 1)[0].strip().lower()
            for line in reset.splitlines()
            if line.split(";", 1)[0].strip()
            and not line.split(";", 1)[0].strip().startswith(".")
            and not line.split(";", 1)[0].strip().endswith(":")
        ]

        # Synthetic-bootstrap builds take a width-safe 8-bit diagnostic
        # detour after entering native mode.  The invariant is that XCE has
        # happened before any native-width immediate, and that the stack is
        # initialized only after REP establishes 16-bit M/X.
        self.assertLess(instructions.index("xce"), instructions.index("rep #$30"))
        self.assertLess(instructions.index("rep #$30"), instructions.index("lda #$1fff"))
        self.assertLess(instructions.index("lda #$1fff"), instructions.index("tcs"))
        self.assertLess(
            instructions.index("xce"),
            instructions.index("lda.l same_reset_diag_cookie"),
        )

    def test_reset_diagnostics_are_in_the_audited_high_wram_gap(self) -> None:
        source = (ROOT / "runtime/snes/kernel/memory.pasm").read_text(
            encoding="utf-8"
        ).lower()
        self.assertRegex(source, r"same_reset_diag_base\s*=\s*\$7ff46b")
        self.assertRegex(source, r"same_reset_diag_size\s*=\s*\$0068")
        self.assertRegex(
            source,
            r"same_reset_diag_end\s*=\s*same_reset_diag_base\+same_reset_diag_size",
        )
        self.assertRegex(
            source, r"same_scumm_m23a_request_api_active\s*=\s*\$7ff46a"
        )
        self.assertRegex(source, r"same_scumm_m23b_variables\s*=\s*\$7ff500")

        diag_start = 0x7FF46B
        diag_end = diag_start + 0x68
        self.assertEqual(diag_end, 0x7FF4D3)
        self.assertGreaterEqual(diag_start, 0x7FF46A + 1)
        self.assertLessEqual(diag_end, 0x7FF500)
        self.assertGreaterEqual(diag_start, 0x7E1800)

    def test_brk_stack_copy_pointer_matches_high_wram_record(self) -> None:
        source = (ROOT / "runtime/snes/main.pasm").read_text(
            encoding="utf-8"
        ).lower()
        handler = source.split("brk_handler:", 1)[1].split(
            ".endif", 1
        )[0]
        self.assertIn("lda #$f491", handler)
        self.assertIn("lda #$7f", handler)
        self.assertIn("same_reset_diag_stack                     = same_reset_diag_base+$26", (
            ROOT / "runtime/snes/kernel/memory.pasm"
        ).read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
