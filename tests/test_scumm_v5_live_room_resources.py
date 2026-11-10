from __future__ import annotations

import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

from same.msu1 import (
    CheckedPackageReader, FileDataPort, Msu1ReadError, ReadStatus,
    trusted_package,
)
from same.package import build_package, inspect_package
from same.engines.scumm_v5.live_room_resources import (
    HEADER, MAX_ACTIVE_BYTES, MAX_PENDING_BYTES, MAX_SOURCE_RECORD_BYTES, OBJECT_WALK,
    decode_live_room, encode_live_room, encode_live_room_sections,
)
from same.engines.scumm_v5.room_visual import decode_room_visual, encode_room_visual
from same.engines.scumm_v5.room import decode_room
from tools.generate_snes_carrier import generate as generate_carrier
from tools.build_scumm_native_residency_fixture import raw_room
from tools.generate_snes_cooked_rooms import (
    inject_diagnostic_invalid_sparse_route_value,
)
from tools.validate_scumm_native_residency_nexen import (
    live_room_ppu_generation_ready, read_active_route_matrix,
)


class LiveRoomResourceTests(unittest.TestCase):
    def source_record(self) -> tuple[dict[str, object], list[dict[str, object]]]:
        units = [
            {"id": 3, "room": 4, "unit_identity": "RoomEntryProgram(4)"},
            {"id": 4, "room": 4, "unit_identity": "RoomExitProgram(4)"},
            {"id": 5, "room": 4, "unit_identity": "ObjectProgram(room=4,object=22)"},
            {"id": 6, "room": 4, "unit_identity": "RoomLocalProgram(room=4,local=9)"},
            {"id": 0, "room": None, "unit_identity": "GlobalProgram(1)"},
        ]
        record = {
            "room": 4, "raw": b"copyright-free-source-room",
            "walkbox_flags": b"\x00\x80",
            "walkbox_geometry": bytes(36),
            "box_routes": b"\x00\x01\xff\x00",
            "portals": bytes(2 * 2 * 7),
            "objects": struct.pack("<HhhhhB", 22, 10, 20, 30, 40, 1),
            "object_names": ((22, b"multi-verb"),),
            "object_walk": struct.pack("<HhhBhhB", 22, 10, 20, 2, 11, 21, 1),
            "object_programs": [{
                "id": 5, "unit_identity": "ObjectProgram(room=4,object=22)",
                "number": 22, "executable": True,
                "entrypoints": ((3, 7), (10, 12)),
            }],
            "executable_locals": [{"id": 6, "number": 9}],
            "entry": 3, "exit": 4,
        }
        return record, units

    def test_round_trip_keeps_carrier_and_verb_identities_distinct(self) -> None:
        record, units = self.source_record()
        raw = encode_live_room(record, program_units=units)
        live = decode_live_room(raw, expected_room=4)
        self.assertEqual(live.room, 4)
        self.assertEqual(live.box_count, 2)
        self.assertEqual(live.object_count, 1)
        self.assertEqual(live.verb_count, 2)
        self.assertEqual(live.local_count, 1)
        self.assertEqual(live.bundle_count, 4)
        self.assertEqual(live.object_names, ((22, b"multi-verb"),))
        self.assertEqual(
            live.offsets["verbs"] - live.offsets["object_walk"],
            live.object_count * OBJECT_WALK.size,
        )
        self.assertEqual(live.portal_indices, (None, None, None, None))
        self.assertEqual(live.portal_records, ())
        self.assertEqual(live.entry_program_unit, 3)
        self.assertEqual(live.exit_program_unit, 4)
        verb_offset = live.offsets["verbs"]
        self.assertEqual(struct.unpack_from("<HHHH", raw, verb_offset), (22, 3, 7, 5))
        self.assertEqual(struct.unpack_from("<HHHH", raw, verb_offset + 8), (22, 10, 12, 5))
        self.assertEqual(raw[0:8], b"SC5LIVE\0")
        self.assertLessEqual(len(raw), MAX_ACTIVE_BYTES)
        self.assertEqual(struct.unpack_from("<H", raw, 8)[0], 3)
        self.assertEqual(live.source_room_sha256, hashlib.sha256(record["raw"]).hexdigest())

    def test_sectioned_v4_round_trip_externalizes_routes_and_packs_portals(self) -> None:
        record, units = self.source_record()
        record["portals"] = b"".join(
            struct.pack("<Bhhh", 1, 120, -8, 8)
            if (src, dst) == (0, 1) else bytes(7)
            for src in range(2) for dst in range(2)
        )
        active, routes = encode_live_room_sections(record, program_units=units)
        decoded = decode_live_room(active, expected_room=4, route_data=routes)
        self.assertEqual(struct.unpack_from("<H", active, 8)[0], 4)
        self.assertEqual(len(active), struct.unpack_from("<H", active, 48)[0])
        self.assertEqual(decoded.route_matrix, bytes(record["box_routes"]))
        self.assertEqual(decoded.portal_indices, (None, 0, None, None))
        self.assertEqual(decoded.portal_records, (struct.pack("<Bhhh", 1, 120, -8, 8),))
        self.assertEqual(active[0x20:0x22], b"\xff\xff")
        self.assertLessEqual(len(active), MAX_ACTIVE_BYTES)
        self.assertLessEqual(len(routes), MAX_PENDING_BYTES)

    def test_sectioned_v4_sparse_route_rows_keep_ascending_destinations(self) -> None:
        record, units = self.source_record()
        box_count = 8
        matrix = bytearray(b"\xff" * (box_count * box_count))
        matrix[2] = 3
        matrix[5] = 4
        record["walkbox_flags"] = bytes(box_count)
        record["walkbox_geometry"] = bytes(box_count * 18)
        record["box_routes"] = bytes(matrix)
        record["portals"] = bytes(box_count * box_count * 7)

        active, routes = encode_live_room_sections(record, program_units=units)
        directory_size = struct.unpack_from("<H", routes, 2)[0]
        self.assertEqual(routes[4], 2)  # row zero is sparse
        self.assertEqual(routes[directory_size:directory_size + 4],
                         bytes((2, 3, 5, 4)))
        decoded = decode_live_room(active, expected_room=4, route_data=routes)
        self.assertEqual(decoded.route_matrix, bytes(matrix))

    def test_route_values_are_walkbox_indices_or_ff_in_every_host_representation(self) -> None:
        record, units = self.source_record()
        invalid = dict(record, box_routes=b"\x00\x02\xff\x00")
        with self.assertRaisesRegex(Exception, "outside 0\\.\\.1"):
            encode_live_room(invalid, program_units=units)
        with self.assertRaisesRegex(Exception, "outside 0\\.\\.1"):
            encode_live_room_sections(invalid, program_units=units)

        valid_v3 = bytearray(encode_live_room(record, program_units=units))
        route_offset = HEADER.unpack_from(valid_v3)[14]
        valid_v3[route_offset + 1] = 2
        with self.assertRaisesRegex(Exception, "outside 0\\.\\.1"):
            decode_live_room(bytes(valid_v3))

        record["walkbox_flags"] = bytes(8)
        record["walkbox_geometry"] = bytes(8 * 18)
        record["portals"] = bytes(8 * 8 * 7)
        for expected_mode, row in (
            (0, bytes(index & 1 for index in range(8))),
            (1, bytes([2] * 8)),
            (2, bytes((0xFF, 0xFF, 3, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF))),
        ):
            matrix = bytearray([0xFF] * 64)
            matrix[:8] = row
            record["box_routes"] = bytes(matrix)
            active, routes = encode_live_room_sections(record, program_units=units)
            directory_size = struct.unpack_from("<H", routes, 2)[0]
            self.assertEqual(routes[4], expected_mode)
            malformed = bytearray(routes)
            malformed[directory_size + (1 if expected_mode else 0)] = 8
            with self.assertRaisesRegex(Exception, "outside 0\\.\\.7"):
                decode_live_room(active, route_data=bytes(malformed))

    def test_valid_package_crc_does_not_bypass_sparse_route_semantic_validation(self) -> None:
        record, units = self.source_record()
        box_count = 8
        record["walkbox_flags"] = bytes(box_count)
        record["walkbox_geometry"] = bytes(box_count * 18)
        route_matrix = bytearray([0xFF] * (box_count * box_count))
        route_matrix[0] = 0
        record["box_routes"] = bytes(route_matrix)
        record["portals"] = bytes(box_count * box_count * 7)
        active, routes = encode_live_room_sections(record, program_units=units)
        directory_size = struct.unpack_from("<H", routes, 2)[0]
        self.assertEqual(routes[4], 2)  # sparse rows
        malformed = bytearray(routes)
        malformed[directory_size + 1] = box_count

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "active.bin").write_bytes(active)
            (root / "routes.bin").write_bytes(malformed)
            manifest = {
                "same_package": 1,
                "sections": [
                    {"name": "LIVE", "kind": "SCVL", "path": "active.bin",
                     "flags": ["streamable", "read_only"]},
                    {"name": "ROUTES", "kind": "SCRT", "path": "routes.bin",
                     "flags": ["streamable", "read_only"]},
                ],
            }
            (root / "package.json").write_text(json.dumps(manifest))
            package_path = root / "routes.samepkg"
            info = build_package(root / "package.json", package_path)
            verified = inspect_package(package_path, verify=True)
            self.assertEqual(verified.crc32, info.crc32)
            self.assertEqual(len(verified.sections), 2)

        with self.assertRaisesRegex(Exception, "outside 0\\.\\.7"):
            decode_live_room(active, route_data=bytes(malformed))

    def test_diagnostic_sparse_route_mutation_preserves_directory_and_is_explicit(self) -> None:
        record, units = self.source_record()
        box_count = 8
        record["walkbox_flags"] = bytes(box_count)
        record["walkbox_geometry"] = bytes(box_count * 18)
        route_matrix = bytearray([0xFF] * (box_count * box_count))
        route_matrix[0] = 0
        record["box_routes"] = bytes(route_matrix)
        record["portals"] = bytes(box_count * box_count * 7)
        active, routes = encode_live_room_sections(record, program_units=units)
        malformed = inject_diagnostic_invalid_sparse_route_value(
            routes, room=4, row=0, pair_index=0, value=box_count,
        )
        self.assertEqual(len(malformed), len(routes))
        directory_size = struct.unpack_from("<H", routes, 2)[0]
        changed_at = directory_size + 1
        self.assertEqual(malformed[changed_at], box_count)
        self.assertEqual(
            malformed[:changed_at] + malformed[changed_at + 1:],
            routes[:changed_at] + routes[changed_at + 1:],
        )
        with self.assertRaisesRegex(Exception, "outside 0\\.\\.7"):
            decode_live_room(active, route_data=malformed)
        with self.assertRaisesRegex(ValueError, "no pair"):
            inject_diagnostic_invalid_sparse_route_value(
                routes, room=4, row=1, pair_index=0, value=box_count,
            )

    def test_v4_compact_active_limit_is_independent_of_normalized_host_size(self) -> None:
        record, units = self.source_record()
        box_count = 64
        record["walkbox_flags"] = bytes(box_count)
        record["walkbox_geometry"] = bytes(box_count * 18)
        record["box_routes"] = bytes([0xFF] * (box_count * box_count))
        record["portals"] = bytes(box_count * box_count * 7)
        object_ids = tuple(range(22, 39))
        record["objects"] = b"".join(
            struct.pack("<HhhhhB", object_id, 0, 0, 1, 1, 0)
            for object_id in object_ids
        )
        record["object_walk"] = b"".join(
            struct.pack("<HhhBhhB", object_id, 0, 0, 0, 0, 0, 0)
            for object_id in object_ids
        )
        record["object_names"] = tuple((object_id, b"n" * 32)
                                        for object_id in object_ids)
        active, routes = encode_live_room_sections(record, program_units=units)
        decoded = decode_live_room(active, expected_room=4, route_data=routes)
        self.assertLessEqual(len(active), MAX_ACTIVE_BYTES)
        self.assertGreater(sum(decoded.section_sizes.values()), MAX_ACTIVE_BYTES)
        bounded = decode_live_room(
            active, expected_room=4, max_size=MAX_ACTIVE_BYTES, route_data=routes,
        )
        self.assertEqual(bounded.route_matrix, record["box_routes"])

    def test_v4_active_records_at_allocation_boundary_are_bounded(self) -> None:
        record, units = self.source_record()

        def build_exact(target: int) -> tuple[bytes, bytes]:
            for count in range(1, 256):
                object_ids = tuple(22 + index for index in range(count))
                candidate = dict(record)
                candidate["objects"] = b"".join(
                    struct.pack("<HhhhhB", object_id, 0, 0, 1, 1, 0)
                    for object_id in object_ids
                )
                candidate["object_walk"] = b"".join(
                    struct.pack("<HhhBhhB", object_id, 0, 0, 0, 0, 0, 0)
                    for object_id in object_ids
                )
                candidate["object_names"] = tuple((object_id, b"")
                                                   for object_id in object_ids)
                empty_active, _empty_routes = encode_live_room_sections(
                    candidate, program_units=units,
                )
                extra = target - len(empty_active)
                if 0 <= extra <= count * 32:
                    names = []
                    for object_id in object_ids:
                        take = min(extra, 32)
                        names.append((object_id, b"n" * take))
                        extra -= take
                    candidate["object_names"] = tuple(names)
                    active, routes = encode_live_room_sections(
                        candidate, program_units=units, max_active_size=target,
                    )
                    if len(active) == target:
                        return active, routes
            self.fail(f"could not construct a valid {target}-byte SC5LIVE v4 record")

        for size in (6143, 6144):
            active, routes = build_exact(size)
            decoded = decode_live_room(
                active, max_size=MAX_ACTIVE_BYTES, route_data=routes,
            )
            self.assertEqual(len(decoded.payload), size)

        active, routes = build_exact(6145)
        with self.assertRaisesRegex(Exception, "length exceeds"):
            decode_live_room(active, max_size=MAX_ACTIVE_BYTES, route_data=routes)

    def test_native_sparse_routes_accept_sorted_pairs_and_rle_no_route_sentinel(self) -> None:
        source = (Path(__file__).resolve().parents[1]
                  / "runtime/snes/engines/scumm_v5_msu_live_room.pasm").read_text()
        sparse = source.split(
            "ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_value_ok:", 1,
        )[1].split(
            "ScummV5_LiveRoom_ValidateRouteDirectory_Far__row_done:", 1,
        )[0]
        self.assertIn("cmp #$FFFF", sparse)
        self.assertIn("sta.l SCUMM_LIVE_ROOM_ROUTE_VALUE", sparse)
        self.assertRegex(
            sparse,
            r"lda\.l SCUMM_LIVE_ROOM_ROUTE_VALUE\s+and #\$00FF\s+"
            r"cmp\.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT\s+"
            r"bcc ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_value_in_range",
        )
        self.assertIn(
            "cmp.l SCUMM_LIVE_ROOM_TEMP4\n"
            "    bcc ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad\n"
            "    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad",
            sparse,
        )
        rle = source.split(
            "ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_value_nonmissing:", 1,
        )[1].split(
            "ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_value_ok:", 1,
        )[0]
        self.assertIn(
            "cmp #$00FF\n"
            "    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_value_ok",
            rle,
        )

    def test_native_route_matrix_observer_removes_runtime_row_padding(self) -> None:
        class Session:
            def __init__(self) -> None:
                self.rows = bytes(
                    byte for row in range(64)
                    for byte in ((row + column) & 0xFF for column in range(64))
                )

            def read_memory(self, _space: str, address: int, length: int) -> bytes:
                offset = address - 0x7F2000
                return self.rows[offset:offset + length]

        actual = read_active_route_matrix(Session(), 61)
        expected = bytes(
            (row + column) & 0xFF
            for row in range(61) for column in range(61)
        )
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 61 * 61)

    def test_generated_large_room_source_has_many_objects_boxes_and_shared_verbs(self) -> None:
        decoded = decode_room(
            raw_room(1, large_live_room=True), key="fixture.large-live-room",
        )
        self.assertEqual(len(decoded.walkboxes), 64)
        self.assertEqual(len(decoded.objects), 36)
        self.assertEqual(sum(len(item.verb_entries) for item in decoded.objects), 2)
        self.assertEqual(sum(bool(item.object_name) for item in decoded.objects), 36)
        self.assertEqual(decoded.objects[0].object_id, 70)
        self.assertEqual(decoded.objects[0].verb_entries[0][0], 3)
        self.assertEqual(decoded.objects[0].verb_entries[1][0], 10)
        self.assertTrue(all(item.parent == 0 for item in decoded.objects))
        self.assertEqual(decoded.box_routes[0][1], 1)
        self.assertEqual(decoded.box_routes[1][0], 0)
        padded = decode_room(
            raw_room(1, large_live_room=True,
                     large_live_room_name_padding_bytes=27),
            key="fixture.large-live-room-boundary",
        )
        self.assertEqual(
            sum(len(item.object_name) for item in padded.objects)
            - sum(len(item.object_name) for item in decoded.objects),
            27,
        )

    def test_large_sectioned_record_exceeds_legacy_window_without_large_active_allocation(self) -> None:
        box_count = 64
        object_count = 34
        geometry = b"".join(
            struct.pack("<hhhhhhhhH", left, 0, left + 1, 0,
                        left + 1, 1, left, 1, 255)
            for left in (0,) * 56 + (4,) * 8
        )
        routes = bytes((0xFF,)) * (box_count * box_count)
        routes = bytearray(routes)
        routes[1] = 1
        routes[box_count] = 0
        portal_rows = bytearray(box_count * box_count * 7)
        for group, fixed in ((range(56), 0), (range(56, 64), 4)):
            for source in group:
                for destination in group:
                    struct.pack_into(
                        "<Bhhh", portal_rows,
                        (source * box_count + destination) * 7,
                        1, fixed, 0, 1,
                    )
        objects = b"".join(
            struct.pack("<HhhhhB", object_id, object_id, 10, 8, 8, 0)
            for object_id in range(70, 70 + object_count)
        )
        names = tuple(
            (object_id, f"large-room-object-{object_id:03d}".encode())
            for object_id in range(70, 70 + object_count)
        )
        object_walk = b"".join(
            struct.pack("<HhhBhhB", object_id, 8, 9, 2, 8, 9, 1)
            for object_id in range(70, 70 + object_count)
        )
        record = {
            "room": 1, "raw": b"copyright-free-large-room-source",
            "walkbox_flags": bytes(box_count),
            "walkbox_geometry": geometry,
            "box_routes": bytes(routes),
            "portals": bytes(portal_rows),
            "objects": objects, "object_names": names,
            "object_walk": object_walk,
            "object_programs": [{
                "id": 5, "unit_identity": "ObjectProgram(room=1,object=70)",
                "number": 70, "executable": True,
                "entrypoints": ((3, 19), (10, 29)),
            }],
            "executable_locals": [], "entry": 3, "exit": 4,
        }
        units = [
            {"id": 3, "room": 1, "unit_identity": "RoomEntryProgram(1)"},
            {"id": 4, "room": 1, "unit_identity": "RoomExitProgram(1)"},
            {"id": 5, "room": 1,
             "unit_identity": "ObjectProgram(room=1,object=70)"},
        ]
        active, route_data = encode_live_room_sections(record, program_units=units)
        semantic = decode_live_room(active, expected_room=1, route_data=route_data)
        expanded_size = sum(semantic.section_sizes.values())
        self.assertGreater(expanded_size, 19_135)
        self.assertLessEqual(len(active), MAX_ACTIVE_BYTES)
        self.assertLessEqual(len(route_data), MAX_PENDING_BYTES)
        self.assertEqual(semantic.box_count, box_count)
        self.assertEqual(semantic.object_count, object_count)
        self.assertEqual(semantic.verb_count, 2)
        self.assertEqual(semantic.route_matrix, routes)
        self.assertEqual(semantic.object_names, names)
        self.assertEqual(semantic.portal_indices[1], 0)
        self.assertEqual(len(semantic.portal_records), 2)
        active_verbs_offset = HEADER.unpack_from(active)[19]
        self.assertEqual(struct.unpack_from("<HHHH", active,
                                            active_verbs_offset),
                         (70, 3, 19, 5))

    def test_sectioned_v4_rejects_corrupt_route_row_and_portal_directory(self) -> None:
        record, units = self.source_record()
        active, routes = encode_live_room_sections(record, program_units=units)
        corrupt_routes = bytearray(routes)
        corrupt_routes[4] = 0xFF
        with self.assertRaisesRegex(Exception, "route row mode"):
            decode_live_room(active, route_data=bytes(corrupt_routes))
        corrupt_active = bytearray(active)
        portal_offset = struct.unpack_from("<H", active, 0x22)[0]
        corrupt_active[portal_offset + 4] = 0xFF
        with self.assertRaisesRegex(Exception, "portal bit layout"):
            decode_live_room(bytes(corrupt_active), route_data=routes)

    def test_v2_dense_portal_records_remain_decodable(self) -> None:
        record, units = self.source_record()
        record["portals"] = b"".join(
            struct.pack("<Bhhh", 1, 0, 0, 0)
            if (src, dst) == (0, 1) else bytes(7)
            for src in range(2) for dst in range(2)
        )
        v3 = encode_live_room(record, program_units=units)
        decoded_v3 = decode_live_room(v3)
        portal_offset = decoded_v3.offsets["portals"]
        object_offset = decoded_v3.offsets["objects"]
        dense = b"".join(
            struct.pack("<H", 0xFFFF if index is None else index)
            for index in decoded_v3.portal_indices
        )
        old_portals = dense + b"".join(decoded_v3.portal_records)
        delta = len(old_portals) - (object_offset - portal_offset)
        v2 = bytearray(v3[:portal_offset] + old_portals + v3[object_offset:])
        header_values = list(HEADER.unpack_from(v2))
        header_values[1] = 2
        for offset_index in range(4, 10):
            header_values[12 + offset_index] += delta
        header_values[22] = len(v2)
        v2[:HEADER.size] = HEADER.pack(*header_values)

        decoded_v2 = decode_live_room(bytes(v2), expected_room=4)
        self.assertEqual(decoded_v2.portal_indices, decoded_v3.portal_indices)
        self.assertEqual(decoded_v2.portal_records, decoded_v3.portal_records)
        self.assertEqual(decoded_v2.object_names, decoded_v3.object_names)

    def test_decoder_rejects_noncanonical_offsets_and_trailing_payload(self) -> None:
        record, units = self.source_record()
        raw = bytearray(encode_live_room(record, program_units=units))
        # First table offset starts immediately after the fixed header.
        struct.pack_into("<H", raw, 28, HEADER.size + 1)
        with self.assertRaisesRegex(Exception, "out of bounds or noncanonical"):
            decode_live_room(bytes(raw))
        raw = encode_live_room(record, program_units=units) + b"x"
        with self.assertRaisesRegex(Exception, "length exceeds"):
            decode_live_room(raw)

    def test_compact_name_rows_cover_empty_and_full_width_names(self) -> None:
        record, units = self.source_record()
        record["object_names"] = ((22, b""),)
        raw = encode_live_room(record, program_units=units)
        live = decode_live_room(raw)
        self.assertEqual(live.object_names, ((22, b""),))
        self.assertEqual(
            live.offsets["object_walk"] - live.offsets["names"], 1,
        )

        record["object_names"] = ((22, b"x" * 32),)
        raw = encode_live_room(record, program_units=units)
        self.assertEqual(decode_live_room(raw).object_names, ((22, b"x" * 32),))
        self.assertEqual(
            decode_live_room(raw).offsets["object_walk"]
            - decode_live_room(raw).offsets["names"], 33,
        )

    def test_encoder_rejects_object_walk_identity_drift(self) -> None:
        record, units = self.source_record()
        record["object_walk"] = struct.pack("<HhhBhhB", 23, 10, 20, 2, 11, 21, 1)
        with self.assertRaisesRegex(Exception, "object-walk row 0 does not match"):
            encode_live_room(record, program_units=units)

    def test_live_resource_preserves_u16_object_ids_beyond_name_cache(self) -> None:
        record, units = self.source_record()
        record["objects"] = struct.pack("<HhhhhB", 1200, 1, 2, 3, 4, 0)
        record["object_names"] = ((1200, b"external object"),)
        record["object_walk"] = struct.pack("<HhhBhhB", 1200, 10, 20, 2, 11, 21, 1)
        live = decode_live_room(encode_live_room(record, program_units=units))
        self.assertEqual(live.object_names, ((1200, b"external object"),))

    def test_sparse_portal_directory_preserves_shared_edge_descriptor(self) -> None:
        record, units = self.source_record()
        descriptor = struct.pack("<Bhhh", 1, 40, 10, 20)
        record["portals"] = b"\0" * 7 + descriptor + b"\0" * 14
        live = decode_live_room(encode_live_room(record, program_units=units))
        self.assertEqual(live.portal_indices, (None, 0, None, None))
        self.assertEqual(live.portal_records, (descriptor,))
        self.assertEqual(
            live.offsets["objects"] - live.offsets["portals"],
            2 * 2 * 2 + 7,
        )

    def test_decoder_rejects_invalid_compact_name_rows(self) -> None:
        record, units = self.source_record()
        raw = bytearray(encode_live_room(record, program_units=units))
        names_offset = struct.unpack_from("<H", raw, 38)[0]
        raw[names_offset] = 33
        with self.assertRaisesRegex(Exception, "name length exceeds"):
            decode_live_room(bytes(raw))

        raw = bytearray(encode_live_room(record, program_units=units))
        object_walk_offset = struct.unpack_from("<H", raw, 40)[0]
        struct.pack_into("<H", raw, 40, object_walk_offset - 1)
        with self.assertRaisesRegex(Exception, "name length exceeds|unclaimed bytes|truncated"):
            decode_live_room(bytes(raw))

    def test_checked_live_room_crc_failure_does_not_publish_staging(self) -> None:
        record, units = self.source_record()
        live_record = encode_live_room(record, program_units=units)
        with tempfile.TemporaryDirectory(prefix="same-live-room-crc-") as temporary:
            root = Path(temporary)
            (root / "room.bin").write_bytes(live_record)
            manifest = root / "package.json"
            manifest.write_text(json.dumps({
                "same_package": 1,
                "sections": [{
                    "name": "SC5LIVE", "kind": "SCVR", "path": "room.bin",
                    "alignment": 1, "flags": ["read_only", "streamable"],
                }],
            }))
            package = root / "room.msu"
            build_package(manifest, package)
            trusted, length = trusted_package(package)
            section = trusted.sections[0]

            damaged = bytearray(package.read_bytes())
            damaged[section.offset + HEADER.size] ^= 0x01
            corrupt_package = root / "room-corrupt.msu"
            corrupt_package.write_bytes(damaged)

            reader = CheckedPackageReader(
                FileDataPort(corrupt_package), trusted, package_length=length,
            )
            destination = bytearray([0xA7] * section.size)
            with self.assertRaises(Msu1ReadError) as raised:
                reader.read_section("SC5LIVE", destination)
            self.assertEqual(raised.exception.status, ReadStatus.SECTION_CRC)
            self.assertEqual(destination, bytearray([0xA7] * section.size))

    def test_large_live_room_compacts_portals_but_reports_runtime_capacity_separately(self) -> None:
        record, units = self.source_record()
        object_ids = range(22, 222)
        record["objects"] = b"".join(
            struct.pack("<HhhhhB", object_id, 0, 0, 1, 1, 0)
            for object_id in object_ids
        )
        record["object_names"] = tuple((object_id, b"synthetic")
                                       for object_id in object_ids)
        record["object_walk"] = b"".join(
            struct.pack("<HhhBhhB", object_id, 0, 0, 0, 0, 0, 0)
            for object_id in object_ids
        )
        raw = encode_live_room(record, program_units=units)
        self.assertGreater(len(raw), MAX_PENDING_BYTES)
        self.assertGreater(len(raw), MAX_ACTIVE_BYTES)
        self.assertLessEqual(len(raw), MAX_SOURCE_RECORD_BYTES)
        live = decode_live_room(raw, expected_room=4)
        self.assertEqual(live.object_count, 200)

    def test_metadata_record_fits_packed_pending_capacity(self) -> None:
        record, units = self.source_record()
        object_ids = range(22, 74)
        record["objects"] = b"".join(
            struct.pack("<HhhhhB", object_id, 0, 0, 1, 1, 0)
            for object_id in object_ids
        )
        record["object_names"] = tuple(
            (object_id, f"fixture-{object_id}".encode()) for object_id in object_ids
        )
        record["object_walk"] = b"".join(
            struct.pack("<HhhBhhB", object_id, 0, 0, 0, 0, 0, 0)
            for object_id in object_ids
        )
        raw = encode_live_room(record, program_units=units)
        self.assertLessEqual(len(raw), MAX_PENDING_BYTES)
        live = decode_live_room(raw, expected_room=4)
        self.assertEqual(live.object_count, len(object_ids))
        self.assertLess(
            live.offsets["object_walk"] - live.offsets["names"],
            len(object_ids) * 34,
        )

    def test_visual_source_record_is_checked_before_storage_projection(self) -> None:
        identities = [hashlib.sha256(name.encode()).hexdigest()
                      for name in ("archive", "index", "data", "room")]
        palette = bytes(value for i in range(256) for value in (i, 255 - i, i // 2))
        pixels = bytes((x + y) & 0xFF for y in range(224) for x in range(256))
        raw = encode_room_visual(
            room=4, width=256, height=224, pitch=256,
            palette=palette, pixels=pixels,
            archive_sha256=identities[0], index_sha256=identities[1],
            data_sha256=identities[2], room_sha256=identities[3],
        )
        decoded = decode_room_visual(raw, expected_room=4)
        self.assertEqual(decoded.visible_row(3), pixels[3 * 256:4 * 256])
        damaged = bytearray(raw)
        damaged[-1] ^= 1
        with self.assertRaisesRegex(Exception, "decoded payload identity"):
            decode_room_visual(bytes(damaged), expected_room=4)

    def test_ppu_sampling_accepts_superseded_generation_ticket_for_exact_content_check(self) -> None:
        class Session:
            def read_memory(self, _kind: str, address: int, length: int) -> bytes:
                control = bytearray(10)
                control[0:2] = (3).to_bytes(2, "little")
                control[3] = 1
                control[4] = 0
                control[8:10] = b"\x00\x00"
                values = {
                    0x401010: bytes(control),
                    0x401013: bytes((1,)),
                    0x401014: bytes((0,)),
                    0x401018: b"\x00\x00",
                }
                return values[address][:length]

        # The caller must still compare actual VRAM/CGRAM with SC5VIS. This
        # only says presentation is idle; an older ticket may have been
        # superseded by a later room generation before the sampler observed it.
        inputs = {"rom_symbols": {
            "SAME_BWRAM_BACKEND_BASE": 0x401000,
            "SAME_MODE3_CONTROL_STATE": 0x401013,
            "SAME_MODE3_CONTROL_SURFACE_LOCKED": 0x401014,
            "SAME_MODE3_CONTROL_COMMITTED_GENERATION_HI": 0x401018,
        }}
        self.assertTrue(live_room_ppu_generation_ready(Session(), inputs, 1))

    def test_active_visual_validity_is_not_the_incoming_transfer_validity(self) -> None:
        root = Path(__file__).resolve().parents[1]
        programs = (root / "runtime/snes/engines/scumm_v5_msu_programs.pasm").read_text()
        live_room = (root / "runtime/snes/engines/scumm_v5_msu_live_room.pasm").read_text()
        video = (root / "runtime/snes/services/video_surface.pasm").read_text()

        self.assertIn(
            "SCUMM_LIVE_ROOM_ACTIVE_VISUAL_VALID = SAME_SCUMM_LIVE_ROOM_CONTROL+$21",
            programs,
        )
        self.assertIn(
            "SCUMM_LIVE_ROOM_OLD_BUNDLE_RELEASED = SAME_SCUMM_LIVE_ROOM_CONTROL+$22",
            programs,
        )
        reset = programs.split("ScummV5_MsuProgram_Reset_Far:", 1)[1].split(
            "ScummV5_MsuProgram_Reset_Far__failed:", 1,
        )[0]
        self.assertIn("sta.l SCUMM_LIVE_ROOM_ACTIVE_VISUAL_VALID", reset)
        self.assertIn("sta.l SCUMM_LIVE_ROOM_OLD_BUNDLE_RELEASED", reset)
        self.assertIn("sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1F", reset)
        request = programs.split("ScummV5_MsuRoom_Request_Far:", 1)[1].split(
            "ScummV5_MsuRoom_Request_Far__coalesced:", 1,
        )[0]
        self.assertNotIn("SCUMM_LIVE_ROOM_ACTIVE_VISUAL_VALID", request)
        self.assertIn("sta.l SCUMM_LIVE_ROOM_OLD_BUNDLE_RELEASED", request)

        commit = (root / "runtime/snes/engines/scumm_v5_m24rb_far.pasm").read_text()
        release = commit.split(
            "ScummV5_M24RB_Far_CommitRoom__old_bundle_released:", 1,
        )[0].split("; Preserve the outgoing room bundle through EXCD", 1)[1]
        self.assertIn("lda.l SCUMM_LIVE_ROOM_OLD_BUNDLE_RELEASED", release)
        self.assertIn("bne ScummV5_M24RB_Far_CommitRoom__old_bundle_released", release)
        released = commit.split(
            "ScummV5_M24RB_Far_CommitRoom__old_bundle_released:", 1,
        )[1].split(".if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES", 1)[1]
        self.assertIn("sta.l SCUMM_LIVE_ROOM_OLD_BUNDLE_RELEASED", released)

        publish = live_room.split("ScummV5_LiveRoom_PublishVisual_Far:", 1)[1].split(
            "ScummV5_LiveRoom_PublishVisual_Far__bad:", 1,
        )[0]
        self.assertIn("sta.l SCUMM_LIVE_ROOM_ACTIVE_VISUAL_VALID", publish)
        compose = video.split("Same_VideoSurface_ComposeRoom_Far:", 1)[1].split(
            "Same_VideoSurface_ComposeRoom__presented:", 1,
        )[0]
        self.assertIn("lda.l SCUMM_LIVE_ROOM_ACTIVE_VISUAL_VALID", compose)

    def test_live_camera_reprojection_uses_installed_surface_not_rom_directory(self) -> None:
        root = Path(__file__).resolve().parents[1]
        video = (root / "runtime/snes/services/video_surface.pasm").read_text()
        service = video.split("Same_VideoSurface_ServicePending__generation_ok:", 1)[1]
        live_path = service.split(".else", 1)[0]
        self.assertIn("jsr Same_VideoSurface_ComputeCameraProjection", live_path)
        self.assertIn("jsr Same_VideoSurface_BlitProjection", live_path)
        self.assertIn("jsr Same_VideoSurface_PushDirtyPresent", live_path)
        self.assertNotIn("Same_VideoSurface_FindVisual", live_path)
        self.assertIn("Same_VideoSurface_ServicePending__live_defer", live_path)

        # These exits are shared by static and live-resource personalities.
        shared_exits = video.split(".endif\n\n; Shared exits", 1)[1].split(
            "Same_VideoSurface_ServicePending__initial:", 1,
        )[0]
        for label in ("Same_VideoSurface_ServicePending__defer:",
                      "Same_VideoSurface_ServicePending__stale:",
                      "Same_VideoSurface_ServicePending__stale16:"):
            self.assertIn(label, shared_exits)

    def test_external_pixel_stage_invalidates_mode3_tile_shadow_on_room_present(self) -> None:
        root = Path(__file__).resolve().parents[1]
        layout = json.loads(
            (root / "runtime/snes/carriers/sa1_bwram_layout.json").read_text()
        )
        # Generated includes are build outputs: another test/build personality
        # may have most recently generated the ordinary LoROM constants there.
        # Generate the SA-1 contract in an isolated directory so this test is
        # independent of suite order and stale ignored files.
        with tempfile.TemporaryDirectory() as temporary:
            generated = Path(temporary)
            generate_carrier(
                carrier_name="sa1_bwram",
                save_enabled=True,
                rom_size_code=8,
                output_dir=generated,
                manifest_path=generated / "carrier-manifest.json",
            )
            constants = (generated / "carrier_constants.inc.pasm").read_text()
        mode3 = (root / "runtime/snes/services/video_mode3.pasm").read_text()
        self.assertEqual(layout["tile_shadow"]["address"], "41:0000")
        self.assertIn(
            "SAME_SCUMM_LIVE_ROOM_PIXEL_STAGE_BASE = SAME_BWRAM_TILE_SHADOW_BASE",
            constants,
        )
        live = (root / "runtime/snes/engines/scumm_v5_msu_live_room.pasm").read_text()
        publish = live.split("ScummV5_LiveRoom_PublishVisual_Far:", 1)[1].split(
            "ScummV5_LiveRoom_PublishVisual_Far__bad:", 1,
        )[0]
        self.assertIn("Same_VideoSurface_InvalidateTileCache_Far", publish)
        self.assertLess(
            publish.index("cpx #$E000"),
            publish.index("Same_VideoSurface_InvalidateTileCache_Far"),
        )
        accepted = mode3.split("Same_Mode3_HandlePresent__accept:", 1)[1].split(
            "Same_Mode3_HandlePresent__reject:", 1,
        )[0]
        self.assertNotIn("sta.l SAME_BWRAM_CONTROL_TILE_VALID", accepted)

    def test_invalid_mode3_tile_shadow_forces_upload_of_blank_and_nonblank_tiles(self) -> None:
        root = Path(__file__).resolve().parents[1]
        mode3 = (root / "runtime/snes/services/video_mode3.pasm").read_text()
        present = mode3.split("Same_Mode3_HandlePresent__accept:", 1)[1].split(
            "Same_Mode3_HandlePresent__reject:", 1,
        )[0]
        invalidate = present.split(
            "Same_Mode3_HandlePresent__invalidate_all_tiles:", 1,
        )[0]
        self.assertIn("lda.l SAME_BWRAM_CONTROL_TILE_VALID", invalidate)
        self.assertIn("sta.l SAME_MODE3_CANDIDATE_TILES,x", present)
        self.assertIn("cpx #SAME_MODE3_CANDIDATE_TILES_SIZE", present)
        self.assertIn("lda #SAME_MODE3_TILE_COUNT", present)
        self.assertIn("sta.l SAME_MODE3_CONTROL_CANDIDATE_COUNT", present)
        self.assertLess(
            present.index("Same_Mode3_HandlePresent__tile_candidates_ready:"),
            present.index("lda #$01\n    sta.l SAME_MODE3_CONTROL_SURFACE_LOCKED"),
        )

    def test_actor_damage_present_preserves_valid_tile_shadow(self) -> None:
        root = Path(__file__).resolve().parents[1]
        mode3 = (root / "runtime/snes/services/video_mode3.pasm").read_text()
        surface = (root / "runtime/snes/services/video_surface.pasm").read_text()
        present = mode3.split("Same_Mode3_HandlePresent__accept:", 1)[1].split(
            "Same_Mode3_HandlePresent__reject:", 1,
        )[0]
        damage = surface.split("Same_VideoSurface_PushDamagePresent:", 1)[1].split(
            "Same_VideoSurface_PushDamagePresent__fail_capacity:", 1,
        )[0]
        invalidate = surface.split(
            "Same_VideoSurface_InvalidateTileCache_Far:", 1,
        )[1].split("Same_VideoSurface_CanWrite_Far:", 1)[0]
        self.assertNotRegex(
            present, r"(?:sta|stz)\.l SAME_BWRAM_CONTROL_TILE_VALID",
        )
        self.assertNotIn("SAME_BWRAM_CONTROL_TILE_VALID", damage)
        self.assertIn("sta.l SAME_BWRAM_CONTROL_TILE_VALID", invalidate)

    def test_video_wait_holds_scheduler_until_room_commit_can_resume(self) -> None:
        root = Path(__file__).resolve().parents[1]
        m24rb = (root / "runtime/snes/engines/scumm_v5_m24rb_far.pasm").read_text()
        preflight = m24rb.split("ScummV5_M24RB_Far_CommitRoom__resource_room:", 1)[1].split(
            "ScummV5_M24RB_Far_CommitRoom__first_entry:", 1,
        )[0]
        self.assertIn("SCUMM_LIVE_ROOM_STAGE_PREFLIGHT_READY", preflight)
        self.assertIn("Same_VideoSurface_CanWrite_Far", preflight)
        self.assertLess(
            m24rb.index("Same_VideoSurface_CanWrite_Far", m24rb.index(
                "ScummV5_M24RB_Far_CommitRoom__resource_room:")),
            m24rb.index("ScummV5_M24RB_Far_CommitRoom__first_entry:"),
        )
        wait = m24rb.split("ScummV5_M24RB_Far_CommitRoom__live_visual_wait:", 1)[1].split(
            "ScummV5_M24RB_Far_CommitRoom__first_entry:", 1,
        )[0]
        self.assertIn("lda #$03", wait)
        self.assertIn("sta.l SAME_SCUMM_M23A_PHASE", wait)
        self.assertIn("sta.l SAME_SCUMM_M23A_HOLD", wait)
        resume = m24rb.split("ScummV5_M24RB_Far_ResumeVisualCommit:", 1)[1].split(
            "ScummV5_M24RB_Far_ResumeVisualCommit_FarEntry:", 1,
        )[0]
        self.assertIn("jsl Same_VideoSurface_CanWrite_Far", resume)
        self.assertIn("jsr ScummV5_M24RB_Far_CommitRoom", resume)
        engine = (root / "runtime/snes/engines/scumm_v5.pasm").read_text()
        self.assertIn("jsl ScummV5_M24RB_Far_ResumeVisualCommit_FarEntry", engine)
        self.assertIn("SCUMM_LIVE_ROOM_STAGE_PREFLIGHT_READY", engine)
        load = m24rb.split(
            "ScummV5_M24RB_Far_CommitRoom__load_incoming_bundle:", 1,
        )[1].split("ScummV5_M24RB_Far_CommitRoom__new_bundle_loaded:", 1)[0]
        self.assertLess(load.index(".a8"), load.index("lda #$00"))
        self.assertLess(load.index("lda #$00"),
                        load.index("sta.l SAME_SCUMM_M23A_HOLD"))

    def test_lifecycle_chain_completion_preserves_async_resource_ready_phase(self) -> None:
        root = Path(__file__).resolve().parents[1]
        m24rb = (root / "runtime/snes/engines/scumm_v5_m24rb_far.pasm").read_text()
        complete = m24rb.split(
            "ScummV5_M23A_PollLifecycleChain__complete:", 1,
        )[1].split("ScummV5_M23A_PollLifecycleChain__entry_done:", 1)[0]
        self.assertIn(
            "lda.l SAME_SCUMM_M23A_PHASE\n"
            "    cmp #$05\n"
            "    beq ScummV5_M23A_PollLifecycleChain__preserve_resource_ready\n"
            "    lda #$00\n"
            "    sta.l SAME_SCUMM_M23A_PHASE\n"
            "ScummV5_M23A_PollLifecycleChain__preserve_resource_ready:",
            complete,
        )
        self.assertLess(
            complete.index("ScummV5_M23A_PollLifecycleChain__preserve_resource_ready:"),
            complete.index("pla\n    cmp #$01"),
        )


if __name__ == "__main__":
    unittest.main()
