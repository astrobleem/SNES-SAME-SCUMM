from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_m25a_validator_room import (  # noqa: E402
    source_body_provenance,
    startup42_scripts,
)
from same.engines.scumm_v5.engine import ScriptSlot  # noqa: E402
from test_scumm_v5_engine import ScummV5EngineTests  # noqa: E402
from validate_fate_authentic_startup_nexen import (  # noqa: E402
    _drive_title_saw_prior_scene,
)


class Startup42LauncherTests(unittest.TestCase):
    def test_authentic_null_scene_arms_room_gated_title_input(self) -> None:
        self.assertTrue(_drive_title_saw_prior_scene(0xFF, 0, 68))
        self.assertFalse(_drive_title_saw_prior_scene(0xFF, 68, 68))
        self.assertTrue(_drive_title_saw_prior_scene(5, 68, 75))
        self.assertFalse(_drive_title_saw_prior_scene(0xFF, 0, 0))

    def test_authentic_global_provenance_binds_member_offset_and_decoded_body(self) -> None:
        decoded = bytes.fromhex("0a 12 ff 00")
        encoded = bytes(value ^ 0x69 for value in decoded)
        record = source_body_provenance(
            number=18, room_number=68,
            archive_member="ATLANTIS/ATLANTIS.001",
            member_offset=0x1234,
            encoded_body=encoded, decoded_body=decoded, program=decoded,
        )
        self.assertEqual(record["classification"], "authentic external game resource")
        self.assertEqual(record["container"], "LFLF room 68/DSCR[18]")
        self.assertEqual(record["member_offset"], 0x1234)
        self.assertEqual(record["decoded_body_size"], len(decoded))
        self.assertEqual(record["decoded_body_sha256"],
                         hashlib.sha256(decoded).hexdigest())

    def test_authentic_global_provenance_rejects_wrong_source_slice(self) -> None:
        decoded = bytes.fromhex("0a 12 ff 00")
        encoded = bytes(value ^ 0x69 for value in decoded)
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            source_body_provenance(
                number=18, room_number=68,
                archive_member="ATLANTIS/ATLANTIS.001",
                member_offset=0x1234,
                encoded_body=encoded, decoded_body=b"wrong", program=decoded,
            )

    def test_synthetic_root_passes_dos_cd_boot_param_to_authentic_global1(self) -> None:
        entry, _, _ = startup42_scripts()
        host = ScummV5EngineTests()._host(bytes((0x00,)))
        engine = host.engine
        slot = ScriptSlot("startup42-launcher", entry)

        calls = []
        while slot.pc < len(slot.program):
            start = slot.pc
            opcode = engine._u8(slot)
            engine.state.last_opcode = opcode
            if opcode == 0x0A:
                number = engine._var_or_direct_byte(slot, 0x80)
                args = engine._word_varargs(slot)
                calls.append((start, number, args, slot.pc))
                continue
            if opcode == 0x13:
                subop = engine._u8(slot)
                if subop != 0x03 or engine._u8(slot) != 0xFF:
                    self.fail("startup launcher actorOps terminator differs")
                continue
            if opcode == 0x00:
                self.assertEqual(slot.pc, len(slot.program))
                break
            self.fail(f"unexpected launcher opcode ${opcode:02X} at ${start:04X}")

        self.assertEqual(calls, [(0, 1, [-7873], 6)])
        self.assertEqual(slot.program[6:], bytes((0x13, 0x03, 0xFF, 0x00)))

    def test_authentic_bootstrap_schedules_a_global_without_synthetic_room(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "active_engine.inc.pasm"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/generate_snes_engine_selection.py"),
                    "--engine", "scumm_v5", "--scumm-m23a",
                    "--scumm-authentic-boot-script", "1",
                    "--scumm-authentic-boot-argument=-7873",
                    "--output", str(output),
                ],
                check=True, capture_output=True, text=True,
            )
            self.assertIn(": scumm_v5", result.stdout)
            config = output.with_name("build_config.inc.pasm").read_text()
            self.assertIn("SAME_BUILD_SCUMM_SCENARIO_FIXTURE = $00", config)
            self.assertIn("SAME_BUILD_SCUMM_AUTHENTIC_BOOTSTRAP = $01", config)
            self.assertIn("SCUMM_V5_AUTHENTIC_BOOT_SCRIPT = $01", config)
            self.assertIn("SCUMM_V5_AUTHENTIC_BOOT_ARGUMENT = $E13F", config)
            self.assertIn("SAME_BUILD_SCUMM_SYNTHETIC_BOOTSTRAP = $00", config)


if __name__ == "__main__":
    unittest.main()
