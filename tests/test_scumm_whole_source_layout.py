from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from examples.resources.scumm_v5.game_analysis_fixture import source_zip
from same.engines.scumm_v5.backend_layout import (
    LOROM_PAGE_BYTES, build_layout_ledger, physical_lorom_page,
    preflight_lorom_layout,
)
from tools.compile_scumm_v5_source_image import load_cooked_records, cooked_record_bytes
from tools.manifest_poppy_inputs import manifest as poppy_input_manifest


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/scumm_v5_game_analysis_fixture.json"


class ScummWholeSourceLayoutTests(unittest.TestCase):
    def test_fixture_builder_refuses_to_replace_unowned_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "fixture.zip"
            output.write_bytes(b"unowned content")
            result = subprocess.run([
                sys.executable,
                str(ROOT / "tools/build_scumm_whole_source_layout_fixture.py"),
                "--output", str(output),
            ], cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing to replace", result.stderr)
            self.assertEqual(output.read_bytes(), b"unowned content")

    def test_lorom_cpu_mirrors_share_physical_storage(self) -> None:
        self.assertEqual(physical_lorom_page(0x00), physical_lorom_page(0x80))
        self.assertEqual(physical_lorom_page(0x7D), physical_lorom_page(0xFD))
        with self.assertRaisesRegex(ValueError, "WRAM"):
            physical_lorom_page(0x7E)

    def test_preflight_rejects_capacity_and_mirrored_aliases(self) -> None:
        report = {
            "first_bank": 32, "last_bank": 128, "reserved_banks": [],
            "room_segments": [
                {"source_identity": "RoomResource(1)", "rom_bank": 0,
                 "bank_offset": 0, "payload_bytes": 32},
                {"source_identity": "RoomResource(2)", "rom_bank": 128,
                 "bank_offset": 0, "payload_bytes": 32},
            ],
        }
        result = preflight_lorom_layout(report, capacity_bytes=4 * 1024 * 1024)
        kinds = {row["kind"] for row in result["issues"]}
        self.assertEqual(result["result"], "reject")
        self.assertIn("PHYSICAL_ROM_PAGE_OUT_OF_CAPACITY", kinds)
        self.assertIn("MIRRORED_STORAGE_OVERLAP", kinds)

    def test_ledger_distinguishes_contained_room_bytes_from_emitted_carriers(self) -> None:
        report = {
            "first_bank": 32, "last_bank": 35, "reserved_banks": [],
            "sa1_rom_bank_aliases": False,
            "room_segments": [{
                "source_identity": "RoomResource(1)", "source_sha256": "roomhash",
                "payload_sha256": "roomhash", "rom_bank": 32, "bank_offset": 0,
                "payload_bytes": 64,
            }],
            "expected_room_directories": [{
                "source_identity": "RoomDirectory(1)", "source_sha256": "dirhash",
                "payload_sha256": "dirhash", "rom_bank": 33, "bank_offset": 0,
                "payload_bytes": 8,
            }],
            "generated_table_placements": [{
                "source_identity": "table-a", "label": "table-a",
                "payload_sha256": "tablehash", "rom_bank": 34, "bank_offset": 0,
                "payload_bytes": 16,
            }],
            "program_map": [{
                "program_unit_identity": "RoomEntryProgram(1)", "kind": "ENCD",
                "room": 1, "number": -1, "length": 4, "sha256": "bodyhash", "rom_bank": 35,
                "bank_offset": 0,
            }],
            "generated_bank_sections": [],
            "generated_assembly_source": {},
            "generated_table_payload_bytes": 16,
            "resolver_table_bytes": 0,
        }
        cooked = {"records": [{"room": 1, "scripts": [{
            "kind": "ENCD", "number": -1, "program_length": 4,
            "sha256": "bodyhash", "identity": "RoomEntry(1)",
        }]}]}
        ledger = build_layout_ledger(report, cooked)
        totals = ledger["totals"]
        self.assertEqual(totals["complete_room_resource_payload_bytes"], 64)
        self.assertEqual(totals["program_unit_body_bytes"], 4)
        self.assertEqual(totals["generated_room_directories_and_lookup_table_bytes"], 24)
        self.assertEqual(totals["program_bodies_also_present_in_cooked_record_bytes"], 4)
        self.assertEqual(ledger["target"]["logical_page_span_bytes"],
                         36 * LOROM_PAGE_BYTES)
        self.assertFalse(ledger["target"]["mapped_span_is_theoretical_minimum"])

    def test_verified_room_directory_alias_is_not_counted_as_emitted_payload(self) -> None:
        report = {
            "first_bank": 32, "last_bank": 32, "reserved_banks": [],
            "room_segments": [{
                "source_identity": "RoomResource(1)", "record_index": 0,
                "source_sha256": "room-hash", "payload_sha256": "room-hash",
                "source_payload_offset": 0, "rom_bank": 32, "bank_offset": 0,
                "payload_bytes": 64,
            }],
            "expected_room_directories": [{
                "source_identity": "RoomDirectory(1)", "rom_bank": 32,
                "bank_offset": 0, "payload_bytes": 8,
                "storage_kind": "ROOM_RECORD_DIRECTORY_ALIAS",
                "shared_storage": True, "storage_alias_of": "RoomResource(1)",
                "storage_source_offset": 0, "storage_payload_match_verified": True,
            }],
            "program_map": [], "generated_table_placements": [],
        }
        ledger = build_layout_ledger(report, {"records": []})
        self.assertEqual(ledger["layout_preflight"]["result"], "pass")
        self.assertEqual(ledger["totals"]["complete_room_resource_payload_bytes"], 64)
        self.assertEqual(ledger["totals"]["generated_room_directories_and_lookup_table_bytes"], 0)
        self.assertEqual(ledger["totals"]["room_directory_content_shared_bytes"], 8)
        self.assertEqual(ledger["totals"]["physically_placed_payload_bytes_non_double_counted"], 64)

    def test_whole_source_cli_rejects_dirty_build_root_without_touching_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "not-clean"
            output.mkdir()
            sentinel = output / "stale.bin"
            sentinel.write_bytes(b"must survive")
            result = subprocess.run([
                sys.executable, str(ROOT / "tools/compile_scumm_v5_source_image.py"),
                "--source", str(root / "missing.zip"), "--profile", str(PROFILE),
                "--output", str(output),
            ], cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing non-empty build root", result.stderr)
            self.assertEqual(sentinel.read_bytes(), b"must survive")

    def test_cooked_build_inputs_are_manifest_owned_not_globbed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cooked = Path(temporary)
            listed = cooked / "room-1.sc5c"
            stale = cooked / "room-999.sc5c"
            listed.write_bytes(b"listed room")
            stale.write_bytes(b"stale room must not enter input set")
            (cooked / "manifest.json").write_text(json.dumps({
                "records": [{"output": listed.name, "record_length": len(b"listed room"),
                             "record_sha256": hashlib.sha256(b"listed room").hexdigest()}],
            }), encoding="utf-8")
            manifest = load_cooked_records(cooked)
            self.assertEqual(cooked_record_bytes(manifest), len(b"listed room"))

    def test_stale_split_segment_cannot_enter_generator_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "fixture.zip"
            source.write_bytes(source_zip())
            cooked = root / "cooked"
            backend = root / "backend"
            segments = root / "segments"
            env = dict(os.environ)
            env["PYTHONPATH"] = os.pathsep.join((str(ROOT / "src"), str(ROOT / "tools")))
            subprocess.run([
                sys.executable, str(ROOT / "tools/cook_scumm_v5_rooms.py"),
                "--archive", str(source), "--profile", str(PROFILE),
                "--all-source-executables", "--executable", "--output-dir", str(cooked),
            ], cwd=ROOT, env=env, check=True, capture_output=True, text=True)
            command = [
                sys.executable, str(ROOT / "tools/generate_snes_cooked_rooms.py"),
                "--manifest", str(cooked / "manifest.json"),
                "--output", str(backend / "rooms.inc.pasm"),
                "--data-output", str(backend / "data.inc.pasm"),
                "--binary-dir", str(segments), "--report", str(backend / "report.json"),
                "--far-programs", "--share-room-program-bodies",
                "--share-room-directory-prefixes", "--layout-only",
            ]
            subprocess.run(command, cwd=ROOT, env=env, check=True,
                           capture_output=True, text=True)
            stale = segments / "stale-old-room-segment.bin"
            stale.write_bytes(b"must not be globbed")
            result = subprocess.run(command, cwd=ROOT, env=env,
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside its manifest", result.stderr)
            self.assertEqual(stale.read_bytes(), b"must not be globbed")

    def test_poppy_input_manifest_owns_recursive_includes_and_incbin_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            main = root / "runtime/snes/main.pasm"
            included = root / "runtime/snes/generated/rooms.inc.pasm"
            binary = root / "build/segments/room.bin"
            main.parent.mkdir(parents=True)
            included.parent.mkdir(parents=True)
            binary.parent.mkdir(parents=True)
            main.write_text('.include "generated/rooms.inc.pasm"\n', encoding="utf-8")
            included.write_text('.incbin "../../../build/segments/room.bin"\n', encoding="utf-8")
            binary.write_bytes(b"compiler-owned-room-segment")
            first = poppy_input_manifest(root, Path("runtime/snes/main.pasm"))
            second = poppy_input_manifest(root, Path("runtime/snes/main.pasm"))
            self.assertEqual(first, second)
            self.assertEqual(first["input_count"], 3)
            self.assertEqual({row["kind"] for row in first["inputs"]},
                             {"ASSEMBLY_INCLUDE", "BINARY_INCBIN"})
            self.assertNotIn(str(root), json.dumps(first))

    def test_synthetic_full_source_layout_is_declared_and_manifest_owned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "fixture.zip"
            source.write_bytes(source_zip(extra_global_scripts=180))
            output = root / "output"
            env = dict(os.environ)
            env["PYTHONPATH"] = os.pathsep.join((str(ROOT / "src"), str(ROOT / "tools")))
            result = subprocess.run([
                sys.executable, str(ROOT / "tools/compile_scumm_v5_source_image.py"),
                "--source", str(source), "--profile", str(PROFILE), "--output", str(output),
                "--policy", "experimental-diagnostic", "--layout-only",
            ], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((output / "whole-source-backend.json").read_text())
            self.assertGreater(report["source_census"]["program_units"], 178)
            self.assertEqual(report["assembly_emitted"], False)
            self.assertEqual(report["layout_preflight"]["result"], "pass")
            ledger = json.loads((output / "backend/layout-ledger.json").read_text())
            self.assertEqual(ledger["totals"]["program_unit_body_bytes"],
                             json.loads((output / "backend/generator-report.json").read_text())
                             ["program_code_bytes"])
            self.assertGreater(ledger["totals"][
                "program_unit_bodies_shared_with_room_records"], 0)
            generator = json.loads((output / "backend/generator-report.json").read_text())
            self.assertTrue(generator["expected_room_directories"])
            self.assertTrue(all(row["shared_storage"]
                                for row in generator["expected_room_directories"]))
            self.assertLessEqual(
                ledger["totals"]["physically_placed_payload_bytes_non_double_counted"],
                ledger["totals"]["complete_room_resource_payload_bytes"]
                + ledger["totals"]["separately_emitted_program_body_bytes"]
                + ledger["totals"]["generated_room_directories_and_lookup_table_bytes"],
            )
            artifacts = json.loads((output / "build-artifacts.json").read_text())
            listed = {row["path"] for row in artifacts["files"]}
            actual = {path.relative_to(output).as_posix()
                      for path in output.rglob("*") if path.is_file()}
            self.assertEqual(actual - {"build-artifacts.json"}, listed)
            self.assertFalse((output / "backend/scumm_v5_rooms.inc.pasm").exists())

    def test_synthetic_full_source_backend_emits_verified_aliases_and_all_bodies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "fixture.zip"
            source.write_bytes(source_zip(extra_global_scripts=180,
                                          cross_bank_body_size=0x7FFC,
                                          data_only_objects=64))
            output = root / "full-image"
            env = dict(os.environ)
            env["PYTHONPATH"] = os.pathsep.join((str(ROOT / "src"), str(ROOT / "tools")))
            result = subprocess.run([
                sys.executable, str(ROOT / "tools/compile_scumm_v5_source_image.py"),
                "--source", str(source), "--profile", str(PROFILE), "--output", str(output),
                "--policy", "experimental-diagnostic",
            ], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((output / "whole-source-backend.json").read_text())
            self.assertEqual(report["program_units_emitted"], 191)
            self.assertGreater(report["source_code_bytes"], 0x7FFC)
            generator = json.loads((output / "backend/generator-report.json").read_text())
            self.assertEqual(len(generator["program_map"]), 191)
            by_id = {row["program_unit_identity"]: row for row in generator["program_map"]}
            self.assertEqual(by_id["GlobalProgram(6)"]["length"], 0x7FFC)
            self.assertNotEqual(by_id["GlobalProgram(6)"]["rom_bank"],
                                by_id["GlobalProgram(7)"]["rom_bank"])
            self.assertTrue(by_id["RoomEntryProgram(1)"]["shared_storage"])
            self.assertTrue(by_id["RoomEntryProgram(1)"]["storage_payload_match_verified"])
            self.assertTrue(all(row["shared_storage"]
                                for row in generator["expected_room_directories"]))
            backend = json.loads((output / "backend/backend_program_directory.json").read_text())
            entry = next(row for row in backend["entries"]
                         if row["identity"] == "RoomEntryProgram(1)")
            self.assertEqual(entry["backend_descriptor"]["storage_kind"],
                             "COOKED_ROOM_RECORD_ALIAS")
            artifacts = json.loads((output / "build-artifacts.json").read_text())
            declared = {row["path"] for row in artifacts["files"]}
            actual = {path.relative_to(output).as_posix()
                      for path in output.rglob("*") if path.is_file()}
            self.assertEqual(actual - {"build-artifacts.json"}, declared)


if __name__ == "__main__":
    unittest.main()
