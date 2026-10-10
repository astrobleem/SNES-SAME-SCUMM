from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zlib

from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5.program_storage import (
    build_program_storage, read_package_prefix_sections,
)
from same.engines.scumm_v5.room_compiler import compile_room_payload
from same.input import SnesButton
from same.package import build_package, inspect_package
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices
from tools.build_scumm_native_residency_fixture import raw_room


ROOT = Path(__file__).resolve().parents[1]


class ScummMsu1ProgramStorageTests(unittest.TestCase):
    def directory(self) -> dict[str, object]:
        return {
            "schema": "same_scumm_v5_native_program_directory_v1",
            "entries": [
                {"program_unit_id": 0, "identity": "GlobalProgram(4)",
                 "bundle": "global", "dispatch": {"kind": "global"},
                 "source_provenance": {"body_offset": 12}},
                {"program_unit_id": 1, "identity": "RoomEntryProgram(2)",
                 "bundle": "room:2", "dispatch": {"kind": "entry"},
                 "source_provenance": {"body_offset": 3}},
                {"program_unit_id": 2, "identity": "ObjectProgram(room=2,object=9)",
                 "bundle": "room:2", "dispatch": {"verbs": [10, 11]},
                 "source_provenance": {"body_offset": 33}},
            ],
        }

    def test_program_units_pack_as_one_checked_collection_with_stable_records(self) -> None:
        directory = self.directory()
        bodies = {
            "GlobalProgram(4)": b"\x1a\xc8\x00\x41\x00\x80",
            "RoomEntryProgram(2)": b"\x1a\xc9\x00\x07\x00\x00",
            "ObjectProgram(room=2,object=9)": b"\x1a\xca\x00\x34\x12\x00",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = build_program_storage(directory, bodies, root)
            package = inspect_package(root / "scumm-programs.msu", verify=True)
            self.assertEqual(result["program_count"], 3)
            self.assertEqual(result["program_body_bytes"], sum(map(len, bodies.values())))
            self.assertEqual(package.sections[-1].name, "SC5CODE")
            rows = result["records"]
            self.assertEqual([row["identity"] for row in rows], list(bodies))
            for row in rows:
                body = bodies[str(row["identity"])]
                self.assertEqual(row["length"], len(body))
                self.assertEqual(row["crc32"], f"{zlib.crc32(body) & 0xFFFFFFFF:08x}")
                start = int(row["package_offset"])
                self.assertEqual((root / "scumm-programs.msu").read_bytes()[start:start + len(body)], body)
            include = (root / "scumm_msu1_programs.inc.pasm").read_text()
            self.assertIn("SCUMM_MSU1_PROGRAM_RECORD_SIZE = $000A", include)
            self.assertIn("ScummV5_MsuProgramRecords:", include)
            self.assertNotIn("selector", include.lower())

    def test_original_style_far_package_offset_is_emitted_as_u32(self) -> None:
        directory = self.directory()
        bodies = {
            "GlobalProgram(4)": b"\x00",
            "RoomEntryProgram(2)": b"\xa0",
            "ObjectProgram(room=2,object=9)": b"\x00",
        }
        # Mirrors the redistributable fixture's >16 MiB package layout without
        # checking its generated media/package into this test corpus.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = build_program_storage(
                directory, bodies, root,
                prefix_sections=(("PAD16M", "TEST", bytes(0x1000010), 1),),
            )
            self.assertGreater(int(result["records"][0]["package_offset"]), 0x1000000)
            package_bytes = (root / "scumm-programs.msu").read_bytes()
            package = inspect_package(root / "scumm-programs.msu", verify=True)
            self.assertGreater(len(package_bytes), 0x1000000)
            self.assertEqual(package.sections[-1].name, "SC5CODE")

    def test_prefix_sections_are_read_from_verified_samepkg_v1(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "pad.bin").write_bytes(bytes(range(64)))
            (source / "fixture.bin").write_bytes(b"original fixture resource")
            (source / "source.json").write_text(
                '{"same_package":1,"sections":['
                '{"name":"PAD64","kind":"TEST","path":"pad.bin",'
                '"alignment":16,"flags":["streamable","read_only"]},'
                '{"name":"FIXTURE","kind":"TEXT","path":"fixture.bin",'
                '"alignment":1,"flags":["streamable","read_only"]}]}'
            )
            source_package = source / "source.msu"
            build_package(source / "source.json", source_package)
            prefix = read_package_prefix_sections(source_package, ("PAD64", "FIXTURE"))
            self.assertEqual([(row[0], row[1], row[2], row[3]) for row in prefix], [
                ("PAD64", "TEST", bytes(range(64)), 16),
                ("FIXTURE", "TEXT", b"original fixture resource", 1),
            ])
            output = root / "compiled"
            result = build_program_storage(
                self.directory(), {
                    "GlobalProgram(4)": b"\0",
                    "RoomEntryProgram(2)": b"\xa0",
                    "ObjectProgram(room=2,object=9)": b"\0",
                }, output, prefix_sections=prefix,
            )
            package = inspect_package(output / "scumm-programs.msu", verify=True)
            self.assertEqual([section.name for section in package.sections],
                             ["PAD64", "FIXTURE", "SC5CODE"])
            raw = (output / "scumm-programs.msu").read_bytes()
            fixture = package.sections[1]
            self.assertEqual(raw[fixture.offset:fixture.offset + fixture.size],
                             b"original fixture resource")
            self.assertGreaterEqual(int(result["records"][0]["package_offset"]),
                                    fixture.offset + fixture.size)

    def test_cooked_room_resources_get_a_selector_free_u32_directory(self) -> None:
        directory = self.directory()
        bodies = {
            "GlobalProgram(4)": b"\0",
            "RoomEntryProgram(2)": b"\xa0",
            "ObjectProgram(room=2,object=9)": b"\0",
        }
        room2, room9 = b"SC5ROOM-room-2", bytes(range(80))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = build_program_storage(
                directory, bodies, root,
                room_resources={2: room2, 9: room9},
                prefix_sections=(("PAD16M", "TEST", bytes(0x1000010), 1),),
            )
            package = inspect_package(root / "scumm-programs.msu", verify=True)
            self.assertEqual([section.name for section in package.sections],
                             ["PAD16M", "SC5ROOM", "SC5CODE"])
            self.assertEqual(result["room_directory_count"], 10)
            self.assertEqual(result["room_resource_count"], 2)
            raw = (root / "scumm-programs.msu").read_bytes()
            rows = {int(row["room"]): row for row in result["room_records"]}
            for room, body in ((2, room2), (9, room9)):
                row = rows[room]
                offset = int(row["package_offset"])
                self.assertGreater(offset, 0x1000000)
                self.assertEqual(raw[offset:offset + len(body)], body)
                self.assertEqual(row["crc32"], f"{zlib.crc32(body) & 0xFFFFFFFF:08x}")
            include = (root / "scumm_msu1_programs.inc.pasm").read_text()
            self.assertIn("SCUMM_MSU1_ROOM_COUNT = $000A", include)
            self.assertIn("ScummV5_MsuRoomRecords:", include)
            self.assertNotIn("selector =", include.lower())

    def test_missing_extra_and_oversized_units_fail_before_directory_publish(self) -> None:
        directory = self.directory()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "body reconciliation"):
                build_program_storage(directory, {"GlobalProgram(4)": b"\0"}, root / "missing")
            bodies = {
                "GlobalProgram(4)": b"\0",
                "RoomEntryProgram(2)": b"\xa0",
                "ObjectProgram(room=2,object=9)": bytes(0x801),
            }
            with self.assertRaisesRegex(ValueError, "cache limit"):
                build_program_storage(directory, bodies, root / "large")
            self.assertFalse((root / "large" / "program-storage.json").exists())

    def test_host_reference_runs_generated_msu_fixture_programs_and_room_scripts(self) -> None:
        """The same copyright-free bodies have observable host/native markers."""
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "fixture"
            subprocess.run(
                [sys.executable, str(ROOT / "tools/build_scumm_native_residency_fixture.py"),
                 "--output-dir", str(fixture)],
                cwd=ROOT, check=True, capture_output=True, text=True,
            )
            source = json.loads((fixture / "manifest.json").read_text())
            profile_path = ROOT / "examples/profiles/scumm_v5_conformance.json"
            profile = load_profile(profile_path)
            profile = replace(profile, options={
                **profile.options,
                "title_start_action": {
                    "action": "menu", "from_room": 0, "target_room": 1,
                },
            })
            profile_sha = hashlib.sha256(profile_path.read_bytes()).hexdigest()
            game_sha = hashlib.sha256(
                f"{profile.engine_id}\0{profile.game_id}\0{profile.variant}".encode()
            ).hexdigest()
            source_sha = {
                name: hashlib.sha256(name.encode()).hexdigest()
                for name in ("archive", "index", "data")
            }
            payloads = {
                "script.boot": (fixture / "global-1.bin").read_bytes(),
                "room.0": (ROOT / "examples/resources/scumm_v5/room0.sc5r").read_bytes(),
            }
            kinds = {"script.boot": "SCRP", "room.0": "ROOM"}
            for row in source["global_scripts"]:
                key = f"script.{int(row['number'])}"
                payloads[key] = (fixture / row["output"]).read_bytes()
                kinds[key] = "SCRP"
            for room in range(1, 5):
                raw = raw_room(room)
                compiled = compile_room_payload(
                    raw, room_number=room, game_name="synthetic-msu-host-conformance",
                    resource_key=f"room.{room}", source_member=f"fixture/room-{room}.lflf",
                    source_container_offset=0, original_room_file_offset=room * 0x10000,
                    profile_sha256=profile_sha,
                    game_identity_sha256=game_sha,
                    archive_sha256=source_sha["archive"],
                    index_sha256=source_sha["index"],
                    data_sha256=source_sha["data"],
                    global_script_count=int(source["num_global_scripts"]),
                )
                payloads[f"room.{room}"] = raw
                payloads[f"cooked.room.{room}"] = compiled.cooked_record
                kinds[f"room.{room}"] = "ROOM"
                kinds[f"cooked.room.{room}"] = "SC5C"
            payloads["cooked.rooms.manifest"] = json.dumps({
                "schema": "same_scumm_v5_cooked_rooms_v1",
                "profile": {"sha256": profile_sha, "identity_sha256": game_sha},
                "source": {f"{name}_sha256": digest
                           for name, digest in source_sha.items()},
            }, sort_keys=True).encode()
            kinds["cooked.rooms.manifest"] = "JSON"

            host = EngineHost(
                profile, default_registry(),
                services=HostServices.create(
                    profile, resources=MemoryResourceProvider(payloads, kinds=kinds),
                ),
            )
            host.boot()
            for frame in range(1800):
                host.tick(input_word=int(SnesButton.START) if frame == 2 else 0)
                if host.lifecycle.value != "running":
                    break

            state = host.engine.inspect_state()
            self.assertEqual(host.lifecycle.value, "stopped")
            self.assertEqual(state["room"], 4)
            self.assertEqual(state.get("error"), None)
            expected = {
                "5": 1, "6": 2, "7": 192, "8": 3, "9": 3,
                "10": 10, "15": 1, "20": 4, "21": 5, "22": 6, "24": 4,
                "25": 1,
            }
            self.assertEqual(
                {key: state["variables"].get(key) for key in expected}, expected,
            )
            activated_rooms = [
                int(event["room"])
                for event in host.engine._room_lifecycle
                if event["phase"] == "new_room_activated"
            ]
            self.assertEqual(activated_rooms, [0, 1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
