from __future__ import annotations

import unittest

from same_vdp.vdp import CRAM_WRITE, VRAM_WRITE, VDPState, command_words, cram_bus_word, cram_components, register_word


class VDPTests(unittest.TestCase):
    def test_command_roundtrip(self) -> None:
        state = VDPState()
        state.write_control(register_word(1, 0x04))
        first, second = command_words(0xC246, VRAM_WRITE)
        state.write_control(first)
        state.write_control(second)
        self.assertEqual(state.address, 0xC246)
        self.assertEqual(state.code, VRAM_WRITE)

    def test_vram_write_and_auto_increment(self) -> None:
        state = VDPState()
        state.write_control(register_word(1, 0x04))
        state.write_control(register_word(15, 2))
        for word in command_words(0x0100, VRAM_WRITE):
            state.write_control(word)
        state.write_data(0x1234)
        self.assertEqual(state.vram[0x100:0x102], b"\x12\x34")
        self.assertEqual(state.address, 0x0102)

    def test_cram_pack(self) -> None:
        state = VDPState()
        state.write_control(register_word(1, 0x04))
        state.write_control(register_word(15, 2))
        for word in command_words(0, CRAM_WRITE):
            state.write_control(word)
        state.write_data(cram_bus_word(7, 3, 5))
        self.assertEqual(cram_components(state.cram[0]), (7, 3, 5))


if __name__ == "__main__":
    unittest.main()
