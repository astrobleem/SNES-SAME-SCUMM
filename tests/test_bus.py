from __future__ import annotations

import unittest

from same.bus import BusError, Endianness, GuestBus, Region
from same.guest import ScriptedGuest


class BusTests(unittest.TestCase):
    def test_big_endian_68k_access(self) -> None:
        bus = GuestBus(address_bits=24, endianness=Endianness.BIG)
        ram = bus.map_ram("work", 0xFF0000, 16)
        bus.write16(0xFF0000, 0x1234)
        bus.write32(0xFF0002, 0x89ABCDEF)
        self.assertEqual(ram[:6], bytes.fromhex("123489abcdef"))
        self.assertEqual(bus.read16(0xFF0000), 0x1234)
        self.assertEqual(bus.read32(0xFF0002), 0x89ABCDEF)

    def test_little_endian_z80_access(self) -> None:
        bus = GuestBus(address_bits=16, endianness=Endianness.LITTLE)
        ram = bus.map_ram("ram", 0x8000, 4)
        bus.write16(0x8000, 0x1234)
        self.assertEqual(ram[:2], b"\x34\x12")

    def test_device_portal_receives_byte_order(self) -> None:
        writes: list[tuple[int, int]] = []
        bus = GuestBus(address_bits=24, endianness="big")
        bus.map_device("vdp", 0xC00000, 4, write=lambda offset, value: writes.append((offset, value)))
        bus.write16(0xC00000, 0xABCD)
        self.assertEqual(writes, [(0, 0xAB), (1, 0xCD)])

    def test_overlap_and_unmapped_access_fail(self) -> None:
        bus = GuestBus(address_bits=16, endianness="little")
        bus.map_ram("a", 0x1000, 0x100)
        with self.assertRaises(BusError):
            bus.map_ram("b", 0x1080, 0x100)
        with self.assertRaises(BusError):
            bus.read8(0x2000)

    def test_rom_write_fails_before_partial_access(self) -> None:
        bus = GuestBus(address_bits=16, endianness="big")
        ram = bus.map_ram("ram", 0x0000, 1)
        bus.map_rom("rom", 0x0001, b"\xAA")
        with self.assertRaises(BusError):
            bus.write16(0x0000, 0x1234)
        self.assertEqual(ram[0], 0)

    def test_scripted_guest_save_restore(self) -> None:
        bus = GuestBus(address_bits=16, endianness="little")
        bus.map_ram("ram", 0x0000, 16)
        guest = ScriptedGuest(
            bus,
            [
                ("write", 0, 0x1234, 2),
                ("read", 0, 0x1234, 2),
                ("write", 2, 0x56, 1),
            ],
        )
        first = guest.step(1)
        self.assertTrue(first.yielded)
        state = guest.save_state()
        guest.step(10)
        self.assertTrue(guest.halted)
        guest.load_state(state)
        result = guest.step(10)
        self.assertTrue(result.halted)
        self.assertIsNone(result.fault)


if __name__ == "__main__":
    unittest.main()
