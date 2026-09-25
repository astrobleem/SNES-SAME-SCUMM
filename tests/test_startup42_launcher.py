from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_m25a_validator_room import startup42_scripts  # noqa: E402
from same.engines.scumm_v5.engine import ScriptSlot  # noqa: E402
from test_scumm_v5_engine import ScummV5EngineTests  # noqa: E402


class Startup42LauncherTests(unittest.TestCase):
    def test_complete_launcher_decodes_as_separate_global_calls(self) -> None:
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

        self.assertEqual(calls, [(0, 1, [0], 6), (6, 18, [], 9)])
        self.assertEqual(slot.program[9:], bytes((0x13, 0x03, 0xFF, 0x00)))


if __name__ == "__main__":
    unittest.main()
