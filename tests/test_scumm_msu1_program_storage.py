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
    build_program_storage, plan_program_pages, read_package_prefix_sections,
)
from same.engines.scumm_v5.live_room_resources import (
    MAX_PENDING_BYTES, OBJECT, SOURCE_OBJECT_WALK, decode_live_room, encode_live_room,
    encode_live_room_sections,
)
from same.engines.scumm_v5.room_compiler import compile_room_payload, decode_script
from same.engines.scumm_v5.room_visual import decode_room_visual, encode_room_visual
from same.input import SnesButton
from same.package import build_package, inspect_package
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices
from tools.build_scumm_native_residency_fixture import large_program_body, raw_room


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

    def test_live_tables_and_visual_payloads_are_package_owned(self) -> None:
        directory = self.directory()
        bodies = {
            "GlobalProgram(4)": b"\0",
            "RoomEntryProgram(2)": b"\xa0",
            "ObjectProgram(room=2,object=9)": b"\0",
        }
        room = {
            "room": 2, "raw": b"synthetic source room", "entry": 1, "exit": 0xFFFF,
            "walkbox_flags": b"\x00", "walkbox_geometry": bytes(18),
            "box_routes": b"\xff", "portals": bytes(7),
            "objects": b"", "object_names": (), "object_walk": b"",
            "object_programs": (), "executable_locals": (),
        }
        room_units = [
            {"id": 1, "room": 2, "unit_identity": "RoomEntryProgram(2)"},
            {"id": 2, "room": 2, "unit_identity": "ObjectProgram(room=2,object=9)"},
        ]
        live = encode_live_room(room, program_units=room_units)
        identities = [hashlib.sha256(name.encode()).hexdigest() for name in (
            "archive", "index", "data", "room",
        )]
        palette = bytes(value for i in range(256) for value in (i, 255 - i, i // 2))
        pixels = bytes((x + y) & 0xFF for y in range(224) for x in range(256))
        visual = encode_room_visual(
            room=2, width=256, height=224, pitch=256, palette=palette, pixels=pixels,
            archive_sha256=identities[0], index_sha256=identities[1],
            data_sha256=identities[2], room_sha256=identities[3],
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = build_program_storage(
                directory, bodies, root, room_resources={2: b"SC5ROOM"},
                live_room_resources={2: live}, room_visual_resources={2: visual},
            )
            package = inspect_package(root / "scumm-programs.msu", verify=True)
            self.assertEqual([s.name for s in package.sections],
                             ["SC5ROOM", "SC5LIVE", "SC5VIS", "SC5CODE"])
            raw = (root / "scumm-programs.msu").read_bytes()
            live_row = result["live_room_records"][0]
            visual_row = result["visual_records"][0]
            self.assertEqual(raw[int(live_row["package_offset"]):
                                 int(live_row["package_offset"]) + len(live)], live)
            self.assertEqual(raw[int(visual_row["pixel_package_offset"]):
                                 int(visual_row["pixel_package_offset"]) + len(pixels)], pixels)
            include = (root / "scumm_msu1_programs.inc.pasm").read_text()
            self.assertIn("ScummV5_MsuLiveRoomRecords:", include)
            self.assertIn("ScummV5_MsuVisualRecords:", include)
            self.assertEqual(result["live_room_resource_count"], 1)
            self.assertEqual(result["visual_resource_count"], 1)

    def test_explicit_route_failure_package_keeps_valid_crcs_for_native_semantic_test(self) -> None:
        directory = self.directory()
        bodies = {
            "GlobalProgram(4)": b"\0",
            "RoomEntryProgram(2)": b"\xa0",
            "ObjectProgram(room=2,object=9)": b"\0",
        }
        box_count = 8
        room = {
            "room": 2, "raw": b"copyright-free diagnostic room",
            "entry": 1, "exit": 0xFFFF, "walkbox_flags": bytes(box_count),
            "walkbox_geometry": bytes(box_count * 18),
            "box_routes": bytes([0] + [0xFF] * (box_count * box_count - 1)),
            "portals": bytes(box_count * box_count * 7),
            "objects": b"", "object_names": (), "object_walk": b"",
            "object_programs": (), "executable_locals": (),
        }
        units = [
            {"id": 1, "room": 2, "unit_identity": "RoomEntryProgram(2)"},
            {"id": 2, "room": 2,
             "unit_identity": "ObjectProgram(room=2,object=9)"},
        ]
        active, valid_route = encode_live_room_sections(room, program_units=units)
        malformed_route = bytearray(valid_route)
        directory_size = int.from_bytes(valid_route[2:4], "little")
        self.assertEqual(valid_route[4], 2)
        malformed_route[directory_size + 1] = box_count
        malformed_route = bytes(malformed_route)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(Exception, "outside 0\\.\\.7"):
                build_program_storage(
                    directory, bodies, root / "strict",
                    live_room_resources={2: active},
                    live_route_resources={2: malformed_route},
                )
            result = build_program_storage(
                directory, bodies, root / "diagnostic",
                live_room_resources={2: active},
                live_route_resources={2: malformed_route},
                diagnostic_allow_invalid_live_route=True,
                diagnostic_live_route_validation_resources={2: valid_route},
            )
            package_path = root / "diagnostic" / "scumm-programs.msu"
            package = inspect_package(package_path, verify=True)
            package_bytes = package_path.read_bytes()
            route_row = result["live_route_records"][0]
            route_bytes = package_bytes[
                int(route_row["package_offset"]):
                int(route_row["package_offset"]) + int(route_row["length"])
            ]
            self.assertEqual(route_bytes, malformed_route)
            self.assertEqual(result["package_sha256"], hashlib.sha256(
                package_bytes,
            ).hexdigest())
            self.assertIn("SC5ROUT", {section.name for section in package.sections})
            with self.assertRaisesRegex(Exception, "outside 0\\.\\.7"):
                decode_live_room(active, route_data=route_bytes)

    def test_package_chunks_large_compact_live_room_records(self) -> None:
        directory = self.directory()
        bodies = {
            "GlobalProgram(4)": b"\0",
            "RoomEntryProgram(2)": b"\xa0",
            "ObjectProgram(room=2,object=9)": b"\0",
        }
        object_ids = tuple(range(200))
        objects = b"".join(OBJECT.pack(value, 0, 0, 1, 1, 0) for value in object_ids)
        names = tuple((value, b"passive") for value in object_ids)
        object_walk = b"".join(
            SOURCE_OBJECT_WALK.pack(value, 0, 0, 0, 0, 0, 0) for value in object_ids
        )
        room = {
            "room": 2, "raw": b"source", "entry": 1, "exit": 0xFFFF,
            "walkbox_flags": b"\x00", "walkbox_geometry": bytes(18),
            "box_routes": b"\xff", "portals": bytes(7),
            "objects": objects, "object_names": names, "object_walk": object_walk,
            "object_programs": (), "executable_locals": (),
        }
        room_units = [{"id": 1, "room": 2, "unit_identity": "RoomEntryProgram(2)"}]
        live = encode_live_room(room, program_units=room_units, max_size=0xFFFF)
        self.assertGreater(len(live), MAX_PENDING_BYTES)
        self.assertEqual(decode_live_room(live, expected_room=2).room, 2)
        source_room = bytes((index * 7) & 0xFF for index in range(100_000))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = build_program_storage(
                directory, bodies, root,
                source_room_resources={2: source_room},
                live_room_resources={2: live},
            )
            package = inspect_package(root / "scumm-programs.msu", verify=True)
            self.assertEqual([section.name for section in package.sections],
                             ["SC5ROOM", "SC5LIVE", "SC5CODE"])
            source_row = result["source_room_records"][0]
            live_row = result["live_room_records"][0]
            self.assertFalse(source_row["native_loadable"])
            self.assertFalse(live_row["native_loadable"])
            self.assertIn("exceeds audited pending metadata capacity",
                          live_row["native_loadability_reason"])
            self.assertEqual(live_row["chunk_count"],
                             (len(live) + 0x7FF) // 0x800)
            self.assertEqual(len(live_row["chunks"]), live_row["chunk_count"])
            raw = (root / "scumm-programs.msu").read_bytes()
            source_offset = int(source_row["package_offset"])
            self.assertEqual(raw[source_offset:source_offset + len(source_room)], source_room)
            self.assertIn("SC5ROOM", [section.name for section in package.sections])

    def test_native_v4_reader_skips_crc_before_chunk_directory_fields(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_msu_live_room.pasm").read_text()
        start = source.index("ScummV5_MsuLiveRoom_Start_Far__metadata_v4_room_ok:")
        end = source.index("ScummV5_MsuLiveRoom_Start_Far__metadata_v4_prepared:", start)
        reader = source[start:end]
        length_hi = reader.index("sta.l SCUMM_LIVE_ROOM_READ_LENGTH+1")
        chunk_first = reader.index("sta.l SCUMM_LIVE_ROOM_CHUNK_FIRST\n", length_hi)
        field_advance = reader[length_hi:chunk_first]
        # The 13-byte row is offset:u32, length:u16, CRC32, chunk-first:u16,
        # chunk-count:u8. From byte 5 the reader advances to byte 10; omitting
        # one INX aliases the CRC tail as the chunk index and rejects every
        # nonempty room before its first checked SC5LIVE read.
        self.assertEqual(sum(line.strip().startswith("inx")
                             for line in field_advance.splitlines()), 5)

    def test_storage_projects_fate_sized_visuals_to_native_surface_in_package(self) -> None:
        directory = self.directory()
        bodies = {
            "GlobalProgram(4)": b"\0",
            "RoomEntryProgram(2)": b"\xa0",
            "ObjectProgram(room=2,object=9)": b"\0",
        }
        hashes = [hashlib.sha256(value.encode()).hexdigest()
                  for value in ("archive", "index", "data", "room")]
        width, height, pitch = 320, 200, 320
        palette = bytes(value for index in range(256) for value in (index, index, index))
        source_pixels = bytes((x + y) & 0xFF for y in range(height) for x in range(width))
        source_visual = encode_room_visual(
            room=2, width=width, height=height, pitch=pitch,
            palette=palette, pixels=source_pixels,
            archive_sha256=hashes[0], index_sha256=hashes[1],
            data_sha256=hashes[2], room_sha256=hashes[3],
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = build_program_storage(
                directory, bodies, root, room_visual_resources={2: source_visual},
            )
            row = result["visual_records"][0]
            self.assertEqual((row["width"], row["height"], row["pitch"]), (256, 224, 256))
            self.assertEqual(row["source_record_sha256"], hashlib.sha256(source_visual).hexdigest())
            self.assertEqual(row["projection"]["source_width"], 320)
            self.assertEqual(row["projection"]["source_height"], 200)
            package_bytes = (root / "scumm-programs.msu").read_bytes()
            pixel_offset = int(row["pixel_package_offset"])
            projected_pixels = package_bytes[pixel_offset:pixel_offset + 256 * 224]
            self.assertEqual(len(projected_pixels), 256 * 224)
            self.assertEqual(projected_pixels[31 * 256:32 * 256], bytes(256))
            self.assertEqual(projected_pixels[32 * 256], 0)
            self.assertEqual(projected_pixels[32 * 256 + 255], (319 + 0) & 0xFF)
            self.assertEqual(projected_pixels[191 * 256 + 255], (319 + 199) & 0xFF)
            self.assertEqual(projected_pixels[192 * 256:193 * 256], bytes(256))
            self.assertNotEqual(projected_pixels, source_pixels)
            self.assertEqual(row["projection"]["sampling"], "nearest_neighbor_aspect_fit")

    def test_live_room_fixture_has_distinct_checked_visuals_for_each_room(self) -> None:
        from same.engines.scumm_v5.room_visual import decode_room_visual

        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary)
            subprocess.run(
                [sys.executable, str(ROOT / "tools/build_scumm_native_residency_fixture.py"),
                 "--output-dir", str(fixture), "--live-room-resources",
                 "--load-room-with-ego"],
                cwd=ROOT, check=True, capture_output=True, text=True,
            )
            manifest = json.loads((fixture / "manifest.json").read_text())
            visual_hashes = []
            for record in manifest["records"]:
                self.assertIn("visual", record)
                visual = decode_room_visual(
                    (fixture / record["visual"]["output"]).read_bytes(),
                    expected_room=int(record["room"]),
                )
                self.assertEqual(len(visual.pixels), 256 * 224)
                visual_hashes.append(visual.record_sha256)
            self.assertEqual(len(visual_hashes), 4)
            self.assertEqual(len(set(visual_hashes)), 4)

    def test_large_live_room_fixture_revisits_after_second_room(self) -> None:
        def room_scripts(raw: bytes) -> dict[bytes, bytes]:
            scripts: dict[bytes, bytes] = {}
            cursor = 0
            while cursor < len(raw):
                tag = raw[cursor:cursor + 4]
                size = int.from_bytes(raw[cursor + 4:cursor + 8], "big")
                self.assertGreaterEqual(size, 8)
                self.assertLessEqual(cursor + size, len(raw))
                if tag in (b"ENCD", b"EXCD"):
                    scripts[tag] = raw[cursor + 8:cursor + size]
                cursor += size
            self.assertEqual(cursor, len(raw))
            return scripts

        first = room_scripts(raw_room(1, large_live_room=True))[b"ENCD"]
        second = room_scripts(raw_room(2, large_live_room=True))[b"ENCD"]
        decode_args = {
            "number": None, "room": 1,
            "game_name": "copyright-free-native-residency-fixture",
            "resource_offset": 0, "source_offset": 0,
        }
        decoded_first = decode_script(
            first, identity="fixture:large-room-entry", kind="ENCD",
            resource_key="fixture.room.1/ENCD", source_member="fixture/room-1",
            **decode_args,
        )
        decoded_second = decode_script(
            second, identity="fixture:return-room-entry", kind="ENCD",
            resource_key="fixture.room.2/ENCD", source_member="fixture/room-2",
            **decode_args,
        )
        self.assertTrue(decoded_first.decode_complete)
        self.assertTrue(decoded_second.decode_complete)
        self.assertEqual(first[0], 0x28)  # branch to stop on the second visit
        self.assertIn(bytes((0x1A, 200, 0, 1, 0)), first)
        verb3 = first.index(bytes((0x37, 70, 0, 3)))
        break_after_verb3 = first.index(b"\x80", verb3 + 5)
        verb10 = first.index(bytes((0x37, 70, 0, 10)))
        self.assertLess(verb3, break_after_verb3)
        self.assertLess(break_after_verb3, verb10)
        self.assertIn(bytes((0x72, 2)), first)
        self.assertIn(bytes((0x72, 1)), second)

    def test_room_crc_failure_fixture_uses_two_real_room_transitions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary)
            subprocess.run(
                [sys.executable, str(ROOT / "tools/build_scumm_native_residency_fixture.py"),
                 "--output-dir", str(fixture), "--room-resource-failure",
                 "--live-room-resources"],
                cwd=ROOT, check=True, capture_output=True, text=True,
            )
            manifest = json.loads((fixture / "manifest.json").read_text())
            self.assertEqual(manifest["conformance_case"], "room-resource-failure")
            global_one = (fixture / "global-1.bin").read_bytes()
            self.assertIn(bytes((0x24, 70, 0, 1)), global_one)
            self.assertIn(bytes((0xE4, 40, 0, 41, 0, 6, 0, 7, 0)), global_one)
            self.assertNotIn(bytes((0x72, 1)), global_one)
            room_records = {int(row["room"]): row for row in manifest["records"]}
            for room, object_id in ((1, 70), (2, 72)):
                object_rows = room_records[room]["objects"]
                carrier = next(row for row in object_rows
                               if int(row["object_id"]) == object_id)
                self.assertGreaterEqual(len(carrier["verb_entries"]), 2)
                self.assertIn("visual", room_records[room])

    def test_missing_extra_and_unmapped_large_units_fail_before_directory_publish(self) -> None:
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
            with self.assertRaisesRegex(ValueError, "instruction boundaries"):
                build_program_storage(directory, bodies, root / "large")
            self.assertFalse((root / "large" / "program-storage.json").exists())

    def test_large_program_units_are_segmented_at_instruction_boundaries_with_page_crcs(self) -> None:
        directory = self.directory()
        # Include a body just above the authentic FATE maximum (21,002 bytes)
        # so the page directory and u16 body-length descriptor are exercised
        # beyond the complete known source corpus.
        sizes = (0x801, 0x2301, 0x5201, 0x520B)
        identities = [row["identity"] for row in directory["entries"]]
        bodies = {
            identity: bytes((index * 13 + unit) & 0xFF for index in range(size))
            for unit, (identity, size) in enumerate(zip(identities, sizes))
        }
        metadata = {
            identity: {"instruction_spans": [[pc, 1] for pc in range(len(body))],
                       "opaque_ranges": []}
            for identity, body in bodies.items()
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = build_program_storage(
                directory, bodies, root, page_metadata=metadata,
                rom_bank=10, page_directory_bank=11,
            )
            self.assertGreater(result["program_page_count"], len(bodies))
            self.assertEqual(result["program_page_directory_bank"], 11)
            self.assertIn("ScummV5_MsuProgramPageIndex:",
                          (root / "scumm_msu1_programs.inc.pasm").read_text())
            pages = result["page_records"]
            for row in result["records"]:
                identity = str(row["identity"])
                body = bodies[identity]
                first = int(row["first_page"])
                count = int(row["page_count"])
                self.assertEqual(row["length"], len(body))
                self.assertLessEqual(row["length"], 0xFFFF)
                selected = pages[first:first + count]
                self.assertEqual(selected[0]["start_pc"], 0)
                self.assertEqual(selected[-1]["start_pc"] + selected[-1]["length"], len(body))
                self.assertTrue(all(0 < int(page["length"]) <= 0x800 for page in selected))
                rebuilt = bytearray()
                for page in selected:
                    start, length = int(page["start_pc"]), int(page["length"])
                    part = body[start:start + length]
                    self.assertEqual(page["crc32"], f"{zlib.crc32(part) & 0xFFFFFFFF:08x}")
                    rebuilt.extend(part)
                self.assertEqual(bytes(rebuilt), body)

    def test_page_planner_never_splits_an_instruction_or_opaque_tail(self) -> None:
        body = bytes(0x2400)
        pages = plan_program_pages(
            body,
            {"instruction_spans": [[0, 4], [4, 1800], [1804, 596]],
             "opaque_ranges": []},
        )
        for start, length in pages[:-1]:
            end = start + length
            self.assertFalse(any(span_start < end < span_start + width
                                 for span_start, width in
                                 ((0, 4), (4, 1800), (1804, 596))))
        with self.assertRaisesRegex(ValueError, "blocking span"):
            plan_program_pages(
                bytes(5000),
                {"instruction_spans": [[0, 1000]], "opaque_ranges": [[1000, 5000]]},
            )

    def test_large_native_fixture_body_has_decoded_cross_page_branches(self) -> None:
        body = large_program_body()
        script = decode_script(
            body, identity="GlobalProgram(2)", kind="global", number=2,
            room=0, resource_key="global.2", game_name="copyright-free",
            source_member="fixture/global-2.bin", resource_offset=0,
            source_offset=0,
        )
        self.assertGreater(len(body), 21002)
        self.assertIsNone(script.opaque_from_pc)
        branches = [item.branch_target for item in script.instructions
                    if item.branch_target is not None]
        branch_pcs = [item.pc for item in script.instructions
                       if item.branch_target is not None]
        self.assertGreater(branches[0], 0x1800)
        self.assertEqual(len(branches), 2)
        self.assertLess(branches[1], branch_pcs[1])
        metadata = {
            "instruction_spans": [[item.pc, item.instruction_width]
                                  for item in script.instructions],
            "opaque_ranges": [],
        }
        pages = plan_program_pages(body, metadata)
        self.assertEqual(len(pages), 11)
        self.assertEqual(sum(length for _start, length in pages), len(body))
        self.assertTrue(all(0 < length <= 0x800 for _start, length in pages))
        page_ends = {start + length for start, length in pages[:-1]}
        self.assertTrue(all(
            not (item.pc < end < item.pc + item.instruction_width)
            for end in page_ends for item in script.instructions
        ))
        self.assertTrue(any(0 < end < 0x1801 for end in page_ends))
        self.assertTrue(any(15005 < end < 21008 for end in page_ends))

    def test_large_program_refuses_page_cuts_without_decoded_boundaries(self) -> None:
        body = large_program_body()
        with self.assertRaisesRegex(ValueError, "no decoded instruction or opaque boundaries"):
            plan_program_pages(body, {"instruction_spans": [], "opaque_ranges": []})

    def test_host_reference_runs_large_yielding_msu_body_and_room_scripts(self) -> None:
        """Large body branches/yields preserve the host-visible route markers."""
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "fixture"
            subprocess.run(
                [sys.executable, str(ROOT / "tools/build_scumm_native_residency_fixture.py"),
                 "--output-dir", str(fixture), "--large-program-body"],
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
            for frame in range(5000):
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
                "25": 1, "50": 1, "51": 0, "53": 4000, "54": 2,
            }
            self.assertEqual(
                {key: state["variables"].get(key, 0) for key in expected}, expected,
            )
            activated_rooms = [
                int(event["room"])
                for event in host.engine._room_lifecycle
                if event["phase"] == "new_room_activated"
            ]
            self.assertEqual(activated_rooms, [0, 1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
