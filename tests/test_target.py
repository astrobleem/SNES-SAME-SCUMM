from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

from same.errors import TargetValidationError
from same.target import load_target


class TargetTests(unittest.TestCase):
    def fixture(self) -> dict[str, object]:
        return {
            "same_target": 1,
            "id": "test_target",
            "name": "Test target",
            "guest": {"kind": "m68k_z80", "buses": {"m68k": {"address_bits": 24, "endianness": "big"}, "z80": {"address_bits": 16, "endianness": "little"}}},
            "memory_map": [
                {"bus": "m68k", "name": "ram68k", "start": "0xFF0000", "size": "0x10000", "kind": "ram"},
                {"bus": "z80", "name": "ramz80", "start": "0x0000", "size": "0x2000", "kind": "ram"}
            ],
            "execution": [
                {"name": "guest.m68k", "affinity": "SA1", "phase": "GUEST", "budget": 10},
                {"name": "guest.z80", "affinity": "SA1", "phase": "GUEST", "budget": 10},
                {"name": "video.vdp", "affinity": "SA1", "phase": "TRANSLATE", "budget": 10},
            ],
            "services": {
                "video": {"adapter": "genesis_vdp"},
                "audio": {"backend": "tad"},
                "input": {"profile": "genesis_3button"},
                "storage": {"backend": "msu1", "package": "test.samepkg"},
            },
        }

    def write(self, root: Path, obj: object) -> Path:
        path = root / "target.json"
        path.write_text(json.dumps(obj))
        return path

    def test_valid_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = load_target(self.write(Path(temporary), self.fixture()))
            self.assertEqual(target.identifier, "test_target")
            self.assertEqual(target.guest_kind, "m68k_z80")
            self.assertFalse(target.warnings)

    def test_foreign_video_without_translate_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            obj = self.fixture()
            obj["execution"] = obj["execution"][:2]
            target = load_target(self.write(Path(temporary), obj))
            self.assertTrue(any("TRANSLATE" in warning for warning in target.warnings))

    def test_openbor_sa1_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            obj = self.fixture()
            obj["guest"] = {"kind": "openbor_vm"}
            obj["memory_map"] = []
            obj["services"]["input"]["profile"] = "openbor"
            target = load_target(self.write(Path(temporary), obj))
            self.assertTrue(any("OpenBOR" in warning for warning in target.warnings))

    def test_invalid_profile_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            obj = self.fixture()
            obj["services"]["input"]["profile"] = "dreamcast"
            with self.assertRaises(TargetValidationError):
                load_target(self.write(Path(temporary), obj))

    def test_memory_map(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            obj = self.fixture()
            obj["guest"]["buses"] = {"main": {"address_bits": 16, "endianness": "little"}}
            obj["memory_map"] = [
                {"bus": "main", "name": "rom", "start": "0x0000", "size": "0x8000", "kind": "rom", "source": "CODE"},
                {"bus": "main", "name": "ram", "start": "0x8000", "size": "0x1000", "kind": "ram"},
            ]
            target = load_target(self.write(Path(temporary), obj))
            self.assertEqual(target.buses[0].address_bits, 16)
            self.assertEqual(target.memory_map[0].end, 0x8000)

    def test_overlapping_memory_map_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            obj = self.fixture()
            obj["guest"]["buses"] = {"main": {"address_bits": 16, "endianness": "little"}}
            obj["memory_map"] = [
                {"bus": "main", "name": "a", "start": 0, "size": 256, "kind": "ram"},
                {"bus": "main", "name": "b", "start": 128, "size": 256, "kind": "ram"},
            ]
            with self.assertRaises(TargetValidationError):
                load_target(self.write(Path(temporary), obj))


if __name__ == "__main__":
    unittest.main()
