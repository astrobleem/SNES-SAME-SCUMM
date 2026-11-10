from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest
import zlib

from same.msu1 import (
    CheckedPackageReader,
    FileDataPort,
    Msu1ReadError,
    ReadStatus,
    trusted_package,
)
from same.package import build_package
from tools.generate_snes_msu1_directory import generate as generate_directory


class CheckedMsu1ReadTests(unittest.TestCase):
    def make_package(self, root: Path) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        (root / "a.bin").write_bytes(bytes(range(256)) * 4)
        (root / "b.bin").write_bytes(b"resource-b" * 19)
        manifest = root / "package.json"
        manifest.write_text(json.dumps({
            "same_package": 1,
            "sections": [
                {"name": "A", "kind": "TEST", "path": "a.bin", "alignment": 1,
                 "flags": ["read_only", "streamable"]},
                {"name": "B", "kind": "TEST", "path": "b.bin", "alignment": 16,
                 "flags": ["read_only"]},
            ],
        }))
        package = root / "unit.msu"
        build_package(manifest, package)
        return package

    def reader(self, package: Path, **port_options: object) -> CheckedPackageReader:
        info, length = trusted_package(package)
        return CheckedPackageReader(
            FileDataPort(package, **port_options), info, package_length=length,
            transfer_budget=31, busy_poll_limit=5,
        )

    def test_header_and_directory_identity_then_checked_section_publish(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = self.make_package(Path(temporary))
            reader = self.reader(package, busy_reads=2)
            section = reader.trusted.sections[0]
            destination = bytearray([0xA5] * section.size)
            result = reader.read_section("A", destination)
            self.assertEqual(result.status, ReadStatus.OK)
            self.assertEqual(result.crc32, section.crc32)
            self.assertEqual(destination, bytes(range(256)) * 4)
            self.assertTrue(reader.initialized)
            self.assertGreaterEqual(reader.seek_count, 2)

    def test_section_crc_failure_does_not_publish_partial_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = self.make_package(Path(temporary))
            reader = self.reader(package)
            section = reader.trusted.sections[0]
            destination = bytearray([0xC7] * section.size)
            with self.assertRaises(Msu1ReadError) as raised:
                reader.read_range(section.offset, section.size, destination,
                                  expected_crc32=section.crc32 ^ 1)
            self.assertEqual(raised.exception.status, ReadStatus.SECTION_CRC)
            self.assertEqual(destination, bytearray([0xC7] * section.size))

    def test_bounds_overflow_zero_at_eof_and_canaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = self.make_package(Path(temporary))
            reader = self.reader(package)
            reader.initialize()
            destination = bytearray(b"\xD3" * 18)
            with self.assertRaises(Msu1ReadError) as out_of_bounds:
                reader.read_range(reader.package_length - 1, 2, destination)
            self.assertEqual(out_of_bounds.exception.status, ReadStatus.RANGE_ERROR)
            with self.assertRaises(Msu1ReadError) as overflow:
                reader.read_range(0xFFFFFFF0, 0x40, destination)
            self.assertEqual(overflow.exception.status, ReadStatus.RANGE_ERROR)
            seeks = reader.seek_count
            result = reader.read_range(reader.package_length, 0, destination)
            self.assertEqual(result.status, ReadStatus.OK)
            self.assertEqual(reader.seek_count, seeks)
            self.assertEqual(destination, bytearray(b"\xD3" * 18))

    def test_interleaved_clients_reseek_their_own_offsets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = self.make_package(Path(temporary))
            reader = self.reader(package)
            raw = package.read_bytes()
            a1 = bytearray(17)
            b = bytearray(127)
            a2 = bytearray(19)
            reader.read_range(0x20, len(a1), a1)
            reader.read_range(0x80, len(b), b)
            reader.read_range(0x30, len(a2), a2)
            self.assertEqual(a1, raw[0x20:0x20 + len(a1)])
            self.assertEqual(b, raw[0x80:0x80 + len(b)])
            self.assertEqual(a2, raw[0x30:0x30 + len(a2)])
            self.assertEqual(reader.last_offset, 0x30)

    def test_absent_device_wrong_id_stuck_busy_and_physical_truncation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.make_package(root)
            for options, status in (
                ({"present": False}, ReadStatus.NO_DEVICE),
                ({"missing_id": True}, ReadStatus.NO_DEVICE),
                ({"busy_stuck": True}, ReadStatus.BUSY_TIMEOUT),
            ):
                reader = self.reader(package, **options)
                with self.assertRaises(Msu1ReadError) as raised:
                    reader.initialize()
                self.assertEqual(raised.exception.status, status)

            truncated = root / "truncated.msu"
            truncated.write_bytes(package.read_bytes()[:-1])
            info, trusted_length = trusted_package(package)
            short_reader = CheckedPackageReader(
                FileDataPort(truncated), info, package_length=trusted_length,
                transfer_budget=128, busy_poll_limit=5,
            )
            with self.assertRaises(Msu1ReadError) as raised:
                short_reader.read_range(trusted_length - 4, 4, bytearray(4))
            self.assertEqual(raised.exception.status, ReadStatus.DEVICE_SHORT_READ)

    def test_wrong_package_identity_rejected_before_section_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            trusted_path = self.make_package(root / "trusted")
            changed_root = root / "changed"
            changed_root.mkdir()
            changed_path = self.make_package(changed_root)
            changed = bytearray(changed_path.read_bytes())
            changed[0] ^= 1
            changed_path.write_bytes(changed)
            info, length = trusted_package(trusted_path)
            reader = CheckedPackageReader(FileDataPort(changed_path), info, package_length=length)
            with self.assertRaises(Msu1ReadError) as raised:
                reader.initialize()
            self.assertEqual(raised.exception.status, ReadStatus.PACKAGE_IDENTITY)

    def test_native_interleave_oracles_are_manifest_owned_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.make_package(root / "source")
            raw = package.read_bytes()
            read_cases = root / "read_cases.json"
            read_cases.write_text(json.dumps({
                "cases": [{
                    "name": "ordinary",
                    "offset": 0x20,
                    "length": 9,
                    "expected": "OK",
                    "crc32": f"{zlib.crc32(raw[0x20:0x29]) & 0xFFFFFFFF:08x}",
                    "expected_hex": raw[0x20:0x29].hex(),
                }],
                "interleaved_clients": [
                    {"client": "A", "offset": 0x30, "length": 17},
                    {"client": "B", "offset": 0x80, "length": 31},
                    {"client": "A", "offset": 0x41, "length": 19},
                ],
            }))

            outputs = []
            results = []
            for run in ("one", "two"):
                output = root / run
                output.mkdir()
                result = generate_directory(
                    package,
                    output / "directory.inc.pasm",
                    output / "manifest.json",
                    read_cases,
                    output / "cases.inc.pasm",
                )
                outputs.append(tuple(
                    (output / filename).read_bytes()
                    for filename in ("directory.inc.pasm", "manifest.json", "cases.inc.pasm")
                ))
                results.append(result)

            self.assertEqual(outputs[0], outputs[1])
            section_offset = int(results[0]["sections"][0]["offset"])
            directory_text = outputs[0][0].decode("utf-8")
            self.assertIn(
                f"SAME_MSU1_SECTION_A_OFFSET_LOW_WORD = ${section_offset & 0xFFFF:04X}",
                directory_text,
            )
            self.assertIn(
                f"SAME_MSU1_SECTION_A_OFFSET_HIGH_WORD = ${(section_offset >> 16) & 0xFFFF:04X}",
                directory_text,
            )
            self.assertEqual(results[0]["native_read_case_count"], 4)
            actual = results[0]["interleaved_native_cases"]
            self.assertEqual([entry["client"] for entry in actual], ["A", "B", "A"])
            self.assertEqual([entry["native_case_index"] for entry in actual], [1, 2, 3])
            for entry in actual:
                offset = int(entry["offset"])
                length = int(entry["length"])
                payload = raw[offset:offset + length]
                self.assertEqual(entry["sample_hex"], payload[:32].hex())
                self.assertEqual(entry["crc32"], f"{zlib.crc32(payload) & 0xFFFFFFFF:08x}")

    def test_native_interleave_oracle_rejects_out_of_package_range(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.make_package(root / "source")
            cases = root / "read_cases.json"
            cases.write_text(json.dumps({
                "cases": [{"name": "empty", "offset": 0, "length": 0,
                           "expected": "OK", "crc32": "00000000", "expected_hex": ""}],
                "interleaved_clients": [{"client": "A", "offset": len(package.read_bytes()), "length": 1}],
            }))
            with self.assertRaisesRegex(ValueError, "outside the source package"):
                generate_directory(
                    package, root / "directory.inc.pasm", root / "manifest.json",
                    cases, root / "cases.inc.pasm",
                )


if __name__ == "__main__":
    unittest.main()
