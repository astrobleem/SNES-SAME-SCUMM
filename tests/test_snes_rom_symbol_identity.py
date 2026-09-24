from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate_scumm_startup42_nexen import (  # noqa: E402
    mapped_cpu_address_for_rom,
    verified_symbol_map_for_rom,
)


def write_pair(rom: Path, symbol_address: int) -> None:
    map_path = rom.with_suffix(".map")
    listing_path = rom.with_suffix(".lst")
    identity_path = rom.with_suffix(".build_identity.json")
    map_path.write_text(
        f"; ${symbol_address:04X} Same_Main_Loop\n"
        f"; ${symbol_address:04X} ScummV5_Matrix_LoadActiveRoom_Far\n",
        encoding="utf-8",
    )
    listing_path.write_text(f"listing for {rom.name}\n", encoding="utf-8")
    identity = {
        "rom": {"sha256": hashlib.sha256(rom.read_bytes()).hexdigest()},
        "native_symbols": {
            "map": {"name": map_path.name,
                    "sha256": hashlib.sha256(map_path.read_bytes()).hexdigest()},
            "listing": {"name": listing_path.name,
                        "sha256": hashlib.sha256(listing_path.read_bytes()).hexdigest()},
        },
    }
    identity_path.write_text(json.dumps(identity), encoding="utf-8")


class RomSymbolIdentityTests(unittest.TestCase):
    def test_two_roms_resolve_only_their_own_bound_maps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.sfc"
            second = Path(directory) / "second.sfc"
            first.write_bytes(b"rom A")
            second.write_bytes(b"rom B")
            write_pair(first, 0x8123)
            write_pair(second, 0x9456)
            self.assertEqual(
                mapped_cpu_address_for_rom(first, "Same_Main_Loop", bank=0), 0x008123)
            self.assertEqual(
                mapped_cpu_address_for_rom(second, "Same_Main_Loop", bank=0), 0x009456)
            self.assertEqual(
                mapped_cpu_address_for_rom(
                    first, "ScummV5_Matrix_LoadActiveRoom_Far", bank=110),
                0x6E8123,
            )
            self.assertEqual(
                mapped_cpu_address_for_rom(
                    first, "ScummV5_Matrix_LoadActiveRoom_Far", bank=0),
                0x008123,
            )

            # A map from the other image cannot be silently substituted.
            second.with_suffix(".map").replace(first.with_suffix(".map"))
            verified_symbol_map_for_rom.cache_clear()
            with self.assertRaisesRegex(RuntimeError, "map SHA mismatch"):
                verified_symbol_map_for_rom(first)

    def test_missing_or_rom_mismatched_artifacts_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rom = Path(directory) / "target.sfc"
            rom.write_bytes(b"target ROM")
            with self.assertRaisesRegex(RuntimeError, "artifact missing"):
                verified_symbol_map_for_rom(rom)

            write_pair(rom, 0x8000)
            rom.write_bytes(b"different ROM")
            with self.assertRaisesRegex(RuntimeError, "ROM SHA does not match"):
                verified_symbol_map_for_rom(rom)

    def test_execution_symbol_requires_valid_rom_bank_address(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rom = Path(directory) / "banked.sfc"
            rom.write_bytes(b"banked ROM")
            write_pair(rom, 0x8123)
            with self.assertRaisesRegex(TypeError, "bank"):
                mapped_cpu_address_for_rom(rom, "Same_Main_Loop")
            with self.assertRaisesRegex(ValueError, "PBR bank"):
                mapped_cpu_address_for_rom(rom, "Same_Main_Loop", bank=0x100)


if __name__ == "__main__":
    unittest.main()
