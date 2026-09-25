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
    def test_same_path_artifact_replacements_are_revalidated_without_cache_clear(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "target.sfc"
            other = Path(directory) / "other.sfc"
            first.write_bytes(b"rom A")
            other.write_bytes(b"rom B")
            write_pair(first, 0x8123)
            write_pair(other, 0x9456)
            self.assertEqual(
                mapped_cpu_address_for_rom(first, "Same_Main_Loop", bank=0), 0x008123)

            # Replacing the map beside the same ROM path must be checked, not
            # hidden by a successful pathname-cached lookup.
            other.with_suffix(".map").replace(first.with_suffix(".map"))
            with self.assertRaisesRegex(RuntimeError, "map SHA mismatch"):
                verified_symbol_map_for_rom(first)

            # Installing a newly matching tuple at those exact paths returns
            # its own symbols rather than the earlier parsed mapping.
            write_pair(first, 0x8333)
            self.assertEqual(
                mapped_cpu_address_for_rom(first, "Same_Main_Loop", bank=0), 0x008333)

            # Replacing only the ROM invalidates the adjacent build identity.
            first.write_bytes(b"substituted ROM")
            with self.assertRaisesRegex(RuntimeError, "ROM SHA does not match"):
                verified_symbol_map_for_rom(first)

            # Missing artifacts fail closed even after a prior successful
            # resolution, and a changed identity cannot reuse old symbols.
            write_pair(first, 0x8444)
            first.unlink()
            with self.assertRaisesRegex(RuntimeError, "artifact missing"):
                verified_symbol_map_for_rom(first)
            first.write_bytes(b"rom C")
            write_pair(first, 0x8555)
            identity_path = first.with_suffix(".build_identity.json")
            identity_path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "invalid ROM build identity"):
                verified_symbol_map_for_rom(first)
            write_pair(first, 0x8666)
            self.assertEqual(
                mapped_cpu_address_for_rom(first, "Same_Main_Loop", bank=0), 0x008666)

    def test_two_roms_resolve_only_their_own_bound_maps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.sfc"
            second = Path(directory) / "second.sfc"
            first.write_bytes(b"rom A")
            second.write_bytes(b"rom B")
            write_pair(first, 0x8123)
            write_pair(second, 0x9456)
            self.assertEqual(mapped_cpu_address_for_rom(first, "Same_Main_Loop", bank=0), 0x008123)
            self.assertEqual(mapped_cpu_address_for_rom(second, "Same_Main_Loop", bank=0), 0x009456)
            self.assertEqual(mapped_cpu_address_for_rom(
                first, "ScummV5_Matrix_LoadActiveRoom_Far", bank=110), 0x6E8123)

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
