from __future__ import annotations

import unittest

from generate_snes_cooked_rooms import cpu_visible_rom_bank


class Sa1RomBankAliasTests(unittest.TestCase):
    def test_sa1_bwram_window_has_upper_rom_alias_for_entire_bank_range(self):
        for bank in range(0x40, 0x50):
            with self.subTest(bank=bank):
                self.assertEqual(cpu_visible_rom_bank(bank, sa1_aliases=True), bank + 0x40)

    def test_alias_is_limited_to_the_overlaid_window(self):
        for bank in (0x00, 0x3F, 0x50, 0x7F):
            with self.subTest(bank=bank):
                self.assertEqual(cpu_visible_rom_bank(bank, sa1_aliases=True), bank)

    def test_non_sa1_lorom_addresses_are_unchanged(self):
        for bank in (0x3F, 0x40, 0x41, 0x4F, 0x50, 0x7F):
            with self.subTest(bank=bank):
                self.assertEqual(cpu_visible_rom_bank(bank, sa1_aliases=False), bank)


if __name__ == "__main__":
    unittest.main()
