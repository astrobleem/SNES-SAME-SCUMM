from __future__ import annotations

import unittest

from generate_snes_cooked_rooms import cpu_visible_rom_bank


class Sa1RomBankAliasTests(unittest.TestCase):
    def test_sa1_bwram_window_has_upper_rom_alias_for_entire_bank_range(self):
        for bank in range(0x40, 0x50):
            with self.subTest(bank=bank):
                self.assertEqual(cpu_visible_rom_bank(bank, sa1_aliases=True), bank + 0x40)

    def test_sa1_alias_is_limited_to_the_overlaid_window_except_wram_rom_mirrors(self):
        for bank in (0x00, 0x3F, 0x50):
            with self.subTest(bank=bank):
                self.assertEqual(cpu_visible_rom_bank(bank, sa1_aliases=True), bank)
        for bank in (0x7E, 0x7F):
            with self.subTest(bank=bank):
                self.assertEqual(cpu_visible_rom_bank(bank, sa1_aliases=True), bank + 0x80)

    def test_non_sa1_lorom_addresses_are_unchanged(self):
        for bank in (0x3F, 0x40, 0x41, 0x4F, 0x50):
            with self.subTest(bank=bank):
                self.assertEqual(cpu_visible_rom_bank(bank, sa1_aliases=False), bank)

    def test_lorom_physical_wram_banks_use_their_upper_rom_mirrors(self):
        for bank in (0x7E, 0x7F):
            with self.subTest(bank=bank):
                self.assertEqual(cpu_visible_rom_bank(bank, sa1_aliases=False), bank + 0x80)


if __name__ == "__main__":
    unittest.main()
