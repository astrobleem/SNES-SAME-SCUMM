from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from lint_poppy import include_closure  # noqa: E402


class PoppySourceTests(unittest.TestCase):
    def test_include_closure_skips_inactive_build_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "generated").mkdir()
            (root / "generated/build_config.inc.pasm").write_text(
                "SAME_BUILD_OPTIONAL = $00\n", encoding="utf-8"
            )
            (root / "present.inc.pasm").write_text("; present\n", encoding="utf-8")
            main = root / "main.pasm"
            main.write_text(
                '.include "generated/build_config.inc.pasm"\n'
                ".if SAME_BUILD_OPTIONAL\n"
                '.include "not-generated-for-this-profile.inc.pasm"\n'
                ".else\n"
                '.include "present.inc.pasm"\n'
                ".endif\n",
                encoding="utf-8",
            )
            closure = include_closure(main)
            self.assertIn((root / "present.inc.pasm").resolve(), closure)
            self.assertNotIn(
                (root / "not-generated-for-this-profile.inc.pasm").resolve(), closure
            )

    def test_include_closure_keeps_unknown_branches_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main = root / "main.pasm"
            main.write_text(
                ".if UNKNOWN_BUILD_SWITCH\n"
                '.include "missing-then.inc.pasm"\n'
                ".else\n"
                '.include "missing-else.inc.pasm"\n'
                ".endif\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "missing-then.inc.pasm"):
                include_closure(main)

    def test_unknown_branch_assignments_merge_before_later_conditions(self) -> None:
        cases = (
            ("different", "CHOSEN = $01", "CHOSEN = $00", True),
            ("identical-true", "CHOSEN = $01", "CHOSEN = $01", True),
            ("identical-false", "CHOSEN = $00", "CHOSEN = $00", False),
        )
        for name, then_assignment, else_assignment, missing_expected in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                main = root / "main.pasm"
                main.write_text(
                    ".if UNRESOLVED_FLAG\n"
                    f"    {then_assignment}\n"
                    ".else\n"
                    f"    {else_assignment}\n"
                    ".endif\n"
                    ".if CHOSEN\n"
                    '    .include "missing.pasm"\n'
                    ".endif\n",
                    encoding="utf-8",
                )
                if missing_expected:
                    with self.assertRaisesRegex(RuntimeError, "missing.pasm"):
                        include_closure(main)
                else:
                    self.assertEqual(include_closure(main), [main.resolve()])

    def test_single_branch_assignment_remains_unknown_after_merge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main = root / "main.pasm"
            main.write_text(
                ".if UNRESOLVED_FLAG\n"
                "    CHOSEN = $00\n"
                ".endif\n"
                ".if CHOSEN\n"
                '    .include "possibly-active.pasm"\n'
                ".endif\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "possibly-active.pasm"):
                include_closure(main)

    def test_nested_unknown_branches_merge_possible_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main = root / "main.pasm"
            main.write_text(
                ".if OUTER_UNKNOWN\n"
                "    .if INNER_UNKNOWN\n"
                "        CHOSEN = $00\n"
                "    .else\n"
                "        CHOSEN = $00\n"
                "    .endif\n"
                ".else\n"
                "    CHOSEN = $00\n"
                ".endif\n"
                ".if CHOSEN\n"
                '    .include "inactive.pasm"\n'
                ".endif\n",
                encoding="utf-8",
            )
            self.assertEqual(include_closure(main), [main.resolve()])

            main.write_text(
                ".if OUTER_UNKNOWN\n"
                "    .if INNER_UNKNOWN\n"
                "        CHOSEN = $00\n"
                "    .else\n"
                "        CHOSEN = $01\n"
                "    .endif\n"
                ".else\n"
                "    CHOSEN = $00\n"
                ".endif\n"
                ".if CHOSEN\n"
                '    .include "possibly-active.pasm"\n'
                ".endif\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "possibly-active.pasm"):
                include_closure(main)

    def test_static_lint(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/lint_poppy.py"), str(ROOT / "runtime/snes/main.pasm")],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lint_rejects_short_access_to_far_wram(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            generated = root / "generated"
            generated.mkdir()
            (generated / "abi.inc.pasm").write_text(
                "SAME_PACKET_SIZE                         = $10\n", encoding="utf-8"
            )
            source = [
                '.include "generated/abi.inc.pasm"',
                'SAME_FAR = $7E2222',
                'reset:',
                '    stz.w <(SAME_FAR)',
                '    rts',
                'nmi_handler:',
                '    rti',
            ]
            for label in sorted(
                {
                    "Same_Kernel_Init",
                    "Same_Frame_Run",
                    "Same_Event_Push",
                    "Same_Event_Pop",
                    "Same_Target_Boot",
                    "Same_Target_Frame",
                    "Same_Target_Shutdown",
                    "Same_Engine_Boot",
                    "Same_Engine_Frame",
                    "Same_Engine_Shutdown",
                }
            ):
                source.extend([f"{label}:", "    rts"])
            main = root / "main.pasm"
            main.write_text("\n".join(source) + "\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools/lint_poppy.py"), str(main)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("far WRAM symbol SAME_FAR", result.stderr)

    def test_wram_event_ring_does_not_overlap_input_state(self) -> None:
        text = (ROOT / "runtime/snes/kernel/memory.pasm").read_text()
        values = {
            name: int(value, 16)
            for name, value in re.findall(r"^(SAME_[A-Z0-9_]+)\s*=\s*\$([0-9A-F]+)", text, re.MULTILINE)
        }
        event_end = values["SAME_EVENT_BUFFER"] + values["SAME_EVENT_CAPACITY"] * 16
        self.assertLessEqual(event_end, values["SAME_INPUT_HELD"])

    def test_dma_queue_layout_is_bounded_and_separate(self) -> None:
        text = (ROOT / "runtime/snes/kernel/memory.pasm").read_text()
        values = {
            name: int(value, 16)
            for name, value in re.findall(r"^(SAME_[A-Z0-9_]+)\s*=\s*\$([0-9A-F]+)", text, re.MULTILINE)
        }
        queue_end = (
            values["SAME_DMA_QUEUE"]
            + values["SAME_DMA_QUEUE_SLOTS"] * values["SAME_DMA_QUEUE_SLOT_SIZE"]
        )
        self.assertEqual(queue_end, 0x7E22A0)
        self.assertLess(queue_end, 0x7E3000)
        self.assertNotIn("CHANNEL", "\n".join(
            line for line in text.splitlines() if line.startswith("SAME_DMA_REQUEST_")
        ))

    def test_scumm_conformance_state_is_bounded_and_separate(self) -> None:
        text = (ROOT / "runtime/snes/kernel/memory.pasm").read_text()
        values = {
            name: int(value, 16)
            for name, value in re.findall(r"^(SAME_[A-Z0-9_]+)\s*=\s*\$([0-9A-F]+)", text, re.MULTILINE)
        }
        dma_end = (
            values["SAME_DMA_QUEUE"]
            + values["SAME_DMA_QUEUE_SLOTS"] * values["SAME_DMA_QUEUE_SLOT_SIZE"]
        )
        self.assertLessEqual(dma_end, values["SAME_SCUMM_PC"])
        self.assertEqual(
            values["SAME_SCUMM_STATE_END"] - values["SAME_SCUMM_PC"],
            values["SAME_SCUMM_STATE_SIZE"],
        )
        self.assertLessEqual(values["SAME_SCUMM_STATE_END"], values["SAME_SCUMM_FIXTURE_REQUEST"])
        self.assertLess(values["SAME_SCUMM_SLOT0_PC"], values["SAME_SCUMM_SLOT1_PC"])
        self.assertLess(values["SAME_SCUMM_SLOT1_PC"], values["SAME_SCUMM_STATE_END"])
        self.assertLess(values["SAME_SCUMM_CONTROL_END"], 0x7E3000)

    def test_clients_do_not_claim_dma_channels_or_ppu_registers(self) -> None:
        forbidden = re.compile(
            r"\b(?:MDMAEN|HDMAEN|DMAP[0-7]|BBAD[0-7]|A1T[0-7]L|A1B[0-7]|DAS[0-7]L)\b"
        )
        roots = [
            ROOT / "runtime/snes/engines",
            ROOT / "runtime/snes/engine",
            ROOT / "runtime/snes/targets",
        ]
        offenders = []
        for source_root in roots:
            for path in source_root.glob("*.pasm"):
                if forbidden.search(path.read_text()):
                    offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
