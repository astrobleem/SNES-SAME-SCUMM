from __future__ import annotations

import json
from pathlib import Path
import struct
import unittest

from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5 import decode_room
from same.engines.scumm_v5.engine import ActorState
from same.errors import EngineExecutionError, ResourceError, SaveFormatError
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices
from same.video import IndexedSurface, Rect
from tools.build_m25a_validator_room import scheduler_scripts

ROOT = Path(__file__).resolve().parents[1]


def chunk(tag: bytes, payload: bytes) -> bytes:
    return tag + (len(payload) + 8).to_bytes(4, "big") + payload


def pack_lsb(bits: list[int]) -> bytes:
    result = bytearray((len(bits) + 7) // 8)
    for index, bit in enumerate(bits):
        result[index // 8] |= bit << (index % 8)
    return bytes(result)


def absolute_strip(codec: int, pixels: bytes, *, vertical: bool = False) -> bytes:
    height = len(pixels) // 8
    order = (
        [pixels[y * 8 + x] for x in range(8) for y in range(height)]
        if vertical
        else list(pixels)
    )
    bits: list[int] = []
    for color in (*order[1:], order[-1]):
        bits.extend((1, 0))
        bits.extend((color >> bit) & 1 for bit in range(codec % 10))
    return bytes((codec, order[0])) + pack_lsb(bits)


def raw_room(
    *strips: bytes,
    height: int = 2,
    zplanes: tuple[tuple[bytes | None, ...], ...] = (),
    walkboxes: tuple[bytes, ...] | None = None,
    box_matrix: bytes | None = None,
    object_headers: tuple[bytes, ...] = (),
    object_payloads: tuple[bytes, ...] | None = None,
    entry_script: bytes | None = None,
    exit_script: bytes | None = None,
    local_scripts: tuple[tuple[int, bytes], ...] = (),
) -> bytes:
    width = len(strips) * 8
    table_end = 8 + len(strips) * 4
    offsets: list[int] = []
    offset = table_end
    for strip in strips:
        offsets.append(offset)
        offset += len(strip)
    smap = chunk(
        b"SMAP",
        b"".join(value.to_bytes(4, "little") for value in offsets) + b"".join(strips),
    )
    zplane_chunks = []
    for plane_index, mask_strips in enumerate(zplanes, 1):
        if len(mask_strips) != len(strips):
            raise ValueError("z-plane strip count differs from room strip count")
        z_table_end = 8 + len(strips) * 2
        z_offsets: list[int] = []
        z_data = bytearray()
        for mask_strip in mask_strips:
            if mask_strip is None:
                z_offsets.append(0)
            else:
                z_offsets.append(z_table_end + len(z_data))
                z_data.extend(mask_strip)
        zplane_chunks.append(chunk(
            f"ZP{plane_index:02d}".encode("ascii"),
            b"".join(value.to_bytes(2, "little") for value in z_offsets) + bytes(z_data),
        ))
    palette = bytes(component for color in range(256) for component in (color, color, color))
    if walkboxes is None:
        walkboxes = (
            struct.pack("<hhhhhhhhBBH", *([-32000] * 8), 0, 0, 255),
            struct.pack(
                "<hhhhhhhhBBH",
                0, 0, width - 1, 0, width - 1, height - 1, 0, height - 1,
                0, 0, 255,
            ),
        )
    if any(len(box) != 20 for box in walkboxes):
        raise ValueError("walkbox records must be 20 bytes")
    if box_matrix is None:
        box_matrix = b"".join(bytes((index, index, index, 0xFF)) for index in range(len(walkboxes)))
    return b"".join(
        (
            chunk(b"RMHD", struct.pack(
                "<HHH", width, height,
                len(object_headers) if object_payloads is None else len(object_payloads),
            )),
            chunk(b"TRNS", struct.pack("<H", 255)),
            chunk(b"CLUT", palette),
            chunk(b"BOXD", struct.pack("<H", len(walkboxes)) + b"".join(walkboxes)),
            chunk(b"BOXM", box_matrix),
            chunk(
                b"RMIM",
                chunk(b"RMIH", struct.pack("<H", len(zplanes)))
                + chunk(b"IM00", smap + b"".join(zplane_chunks)),
            ),
            *(chunk(b"OBCD", payload) for payload in (
                object_payloads
                if object_payloads is not None
                else tuple(chunk(b"CDHD", header) for header in object_headers)
            )),
            *(chunk(b"ENCD", entry_script) for _ in range(entry_script is not None)),
            *(chunk(b"EXCD", exit_script) for _ in range(exit_script is not None)),
            *(chunk(b"LSCR", bytes((script_id,)) + program) for script_id, program in local_scripts),
        )
    )


class ScummV5RawRoomTests(unittest.TestCase):
    def _matrix_host(self, script: bytes, room_data: bytes | None) -> EngineHost:
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        payloads = {"script.boot": script}
        kinds = {"script.boot": "SCRP"}
        if room_data is not None:
            payloads["room.0"] = room_data
            kinds["room.0"] = "ROOM"
        resources = MemoryResourceProvider(payloads, kinds=kinds)
        host = EngineHost(
            profile, default_registry(), services=HostServices.create(profile, resources=resources)
        )
        host.boot()
        return host

    def test_room_local_scheduler_pass_resumes_each_yielded_slot_once(self) -> None:
        entry, locals_ = scheduler_scripts()
        strip = bytes((1,)) + bytes(range(16))
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = MemoryResourceProvider(
            {
                "script.boot": bytes((0x72, 1)) + entry,
                "room.1": raw_room(strip, local_scripts=locals_),
            },
            kinds={"script.boot": "SCRP", "room.1": "ROOM"},
        )
        host = EngineHost(
            profile, default_registry(),
            services=HostServices.create(profile, resources=resources),
        )
        host.boot()

        host.tick()  # load room and execute all immediate nested first segments
        first = host.engine.inspect_state()
        self.assertEqual(
            {key: first["variables"].get(str(key), 0)
             for key in (10, 11, 12, 13, 14, 20, 21, 22, 23, 24, 25)},
            {10: 0xA, 11: 0xB, 12: 0xD, 13: 0, 14: 0,
             20: 0x20, 21: 0, 22: 0, 23: 0x30, 24: 0x40, 25: 0},
        )
        active = {item["number"]: item for item in first["scripts"]
                  if item["active"] and item["number"]}
        self.assertEqual(set(active), {200, 201, 202})
        self.assertTrue(all(item["yielded"] for item in active.values()))
        self.assertTrue(all(
            slot.did_exec for slot in host.engine.state.scripts
            if slot.active and slot.number in active
        ))
        self.assertNotIn(204, active)

        host.tick()
        second = host.engine.inspect_state()
        self.assertEqual(
            {key: second["variables"].get(str(key), 0) for key in (13, 14, 21, 25)},
            {13: 0xF, 14: 0xE, 21: 0x21, 25: 0},
        )
        active = [item for item in second["scripts"]
                  if item["active"] and item["number"]]
        self.assertEqual([(item["number"], item["yielded"]) for item in active], [(202, True)])

        host.tick()
        third = host.engine.inspect_state()
        self.assertEqual(third["variables"]["22"], 0x22)
        self.assertFalse(any(item["active"] and item["number"]
                             for item in third["scripts"]))

    @staticmethod
    def _matrix_room() -> bytes:
        boxes = tuple(
            struct.pack(
                "<hhhhhhhhBBH", 0, 0, 7, 0, 7, 1, 0, 1,
                0, flags, 255,
            )
            for flags in (0x00, 0x11, 0x22)
        )
        return raw_room(bytes((1,)) + bytes(16), walkboxes=boxes)

    def test_matrix_ops_set_box_flags_direct_variable_replace_and_lengths(self) -> None:
        script = bytes((
            0x1A, 0, 0, 2, 0,             # v0 = box 2
            0x1A, 1, 0, 0x80, 0,          # v1 = flags $80
            0x30, 0x01, 1, 0x7F,          # direct box/direct flags
            0x30, 0x81, 0, 0, 0x33,       # variable box/direct flags
            0x30, 0x41, 1, 1, 0,          # direct box/variable flags
            0x30, 0xC1, 0, 0, 1, 0,       # variable box/variable flags
            0x30, 0x01, 1, 0x44,          # replacement, not bitwise merge
            0x30, 0x01, 0xFF, 0x99,       # canonical absent-box sentinel
            0x80,
        ))
        host = self._matrix_host(script, self._matrix_room())
        host.tick()
        room = host.engine._video.room
        self.assertEqual([box.flags for box in room.walkboxes], [0x00, 0x44, 0x80])
        slot = host.engine.state.scripts[0]
        self.assertEqual(slot.pc, len(script))
        self.assertTrue(slot.yielded)

    def test_matrix_ops_missing_invalid_and_unsupported_fail_policy(self) -> None:
        missing = self._matrix_host(bytes((0x30, 0x01, 2, 0x80, 0x00)), None)
        missing.tick()
        self.assertFalse(missing.engine.state.scripts[0].active)

        invalid = self._matrix_host(bytes((0x30, 0x01, 3, 0x80)), self._matrix_room())
        with self.assertRaisesRegex(EngineExecutionError, "walkbox 3 is outside"):
            invalid.tick()

        for subopcode in (0x02, 0x03, 0x04, 0x1F):
            with self.subTest(subopcode=subopcode):
                host = self._matrix_host(bytes((0x30, subopcode)), self._matrix_room())
                with self.assertRaisesRegex(
                    EngineExecutionError,
                    rf"matrixOps subopcode \${subopcode:02X} is not implemented",
                ):
                    host.tick()
                self.assertEqual(host.engine.state.scripts[0].pc, 2)

    def test_put_actor_applies_bounded_canonical_v5_placement_side_effects(self) -> None:
        boxes = (
            struct.pack("<hhhhhhhhBBH", -32000, -32000, -32000, -32000,
                        -32000, -32000, -32000, -32000, 0, 0, 255),
            struct.pack("<hhhhhhhhBBH", 452, 137, 536, 137,
                        536, 141, 452, 141, 0, 0, 255),
            struct.pack("<hhhhhhhhBBH", 535, 137, 600, 137,
                        600, 137, 535, 137, 0, 0x80, 255),
        )
        room_data = raw_room(bytes((1,)) + bytes(16), walkboxes=boxes)
        host = self._matrix_host(bytes.fromhex("01 01 47 02 88 00 80"), room_data)
        host.engine.state.current_room = 1
        host.engine.state.actors[1] = ActorState(
            room=1, visible=False, position=(10, 20), moving=7,
            walk_destination=(700, 150), walk_destination_box=2,
            costume_frame=None,
        )
        host.tick()
        actor = host.engine.state.actors[1]
        self.assertEqual(actor.position, (536, 137))
        self.assertEqual((actor.walkbox, actor.walk_destination_box), (1, 1))
        self.assertEqual(actor.walk_destination, (-1, 150))
        self.assertEqual(actor.moving, 0)
        self.assertTrue(actor.visible)
        self.assertEqual(actor.costume_frame, actor.init_frame)

    def test_raw_basic_vertical_horizontal_and_major_minor_strips(self) -> None:
        raw_pixels = bytes(range(16))
        vertical_pixels = bytes((*range(20, 28), *range(30, 38)))
        major_pixels = bytes((*range(40, 48), *range(50, 58)))
        room = decode_room(
            raw_room(
                bytes((1,)) + raw_pixels,
                absolute_strip(18, vertical_pixels, vertical=True),
                absolute_strip(68, major_pixels),
                object_headers=(struct.pack("<HBBBBBBhhB", 100, 3, 4, 34, 18, 2, 0, 108, 118, 1),),
            ),
            key="room.synthetic",
        )

        self.assertEqual((room.width, room.height), (24, 2))
        self.assertEqual(room.source_format, "raw-v5")
        self.assertEqual(room.strip_codecs, (1, 18, 68))
        self.assertEqual(room.zplanes, ())
        self.assertEqual(len(room.walkboxes), 2)
        self.assertEqual(room.next_box(1, 1), 1)
        self.assertEqual(
            room.pixels,
            raw_pixels[:8] + vertical_pixels[:8] + major_pixels[:8]
            + raw_pixels[8:] + vertical_pixels[8:] + major_pixels[8:],
        )
        self.assertEqual(room.palette[37], (37, 37, 37))
        self.assertEqual(len(room.objects), 1)
        self.assertIsNone(room.entry_script)
        self.assertIsNone(room.exit_script)
        self.assertEqual(room.local_scripts, ())
        obj = room.objects[0]
        self.assertEqual(
            (
                obj.object_id, obj.x, obj.y, obj.width, obj.height, obj.flags,
                obj.parent, obj.walk_x, obj.walk_y, obj.actor_direction,
            ),
            (100, 24, 32, 272, 144, 2, 0, 108, 118, 1),
        )

    def test_raw_obcd_retains_complete_executable_and_canonical_verb_directory(self) -> None:
        header = struct.pack("<HBBBBBBhhB", 100, 3, 4, 1, 1, 0, 0, 5, 6, 0)
        exact_program = bytes((0x80, 0x00, 0x00))
        fallback_program = bytes((0x00,))
        verb_chunk_offset = 8 + (8 + len(header))
        program_offset = verb_chunk_offset + 8 + 7
        verb = bytes((10,)) + struct.pack("<H", 8 + 7)
        verb += bytes((0xFF,)) + struct.pack("<H", 8 + 7 + len(exact_program))
        verb += bytes((0,))
        obcd_payload = chunk(b"CDHD", header) + chunk(
            b"VERB", verb + exact_program + fallback_program
        )
        raw = raw_room(
            bytes((1,)) + bytes(range(16)),
            object_payloads=(obcd_payload,),
        )
        room = decode_room(raw, key="room.synthetic.obcd")
        self.assertEqual(len(room.objects), 1)
        item = room.objects[0]
        self.assertEqual(item.object_id, 100)
        self.assertEqual(item.verb_entries, ((10, program_offset), (0xFF, program_offset + 3)))
        self.assertEqual(item.verb_entrypoint(10), program_offset)
        self.assertEqual(item.verb_entrypoint(8), program_offset + 3)
        self.assertEqual(item.obcd[:8], b"OBCD" + len(item.obcd).to_bytes(4, "big"))
        self.assertEqual(item.obcd[program_offset:program_offset + 3], exact_program)
        self.assertGreater(item.verb_table_offset, 0)
        self.assertEqual(item.verb_table_length, 8 + 7 + 4)

    def test_source_object_hit_test_uses_room_coordinates_edges_and_source_order(self) -> None:
        headers = (
            struct.pack("<HBBBBBBhhB", 100, 1, 1, 2, 2, 0, 0, 0, 0, 0),
            struct.pack("<HBBBBBBhhB", 101, 1, 1, 2, 2, 0, 0, 0, 0, 0),
            struct.pack("<HBBBBBBhhB", 102, 4, 1, 1, 1, 0x80, 1, 0, 0, 0),
        )
        room = decode_room(
            raw_room(bytes((1,)) + bytes(16), object_headers=headers),
            key="room.synthetic.hit-test",
        )
        # CDHD units are strips/cells, so the first two records overlap at
        # (8, 8); canonical v5 findObject returns the first source record.
        self.assertEqual(room.hit_test_object(8, 8).object_id, 100)
        self.assertEqual(room.hit_test_object(7, 7), None)
        self.assertEqual(room.hit_test_object(24, 8), None)  # right edge
        self.assertEqual(room.hit_test_object(8, 24), None)  # bottom edge
        self.assertEqual(room.hit_test_object(32, 8, object_states={100: 0}), None)
        self.assertEqual(room.hit_test_object(32, 8, object_states={100: 1}).object_id, 102)
        self.assertEqual(
            room.hit_test_object(8, 8, object_owners={101: 1}).object_id, 100,
        )

    def test_authored_verb_directory_excludes_only_the_fallback_entry(self) -> None:
        header = struct.pack("<HBBBBBBhhB", 100, 1, 1, 1, 1, 0, 0, 0, 0, 0)
        program = bytes((0x80,))
        verb = bytes((3,)) + struct.pack("<H", 7) + bytes((0xFF,)) + struct.pack("<H", 8) + bytes((0,))
        room = decode_room(
            raw_room(bytes((1,)) + bytes(16), object_payloads=(chunk(b"CDHD", header) + chunk(b"VERB", verb + program + program),)),
            key="room.synthetic.verbs",
        )
        self.assertEqual(room.objects[0].authored_verbs, (3,))
        self.assertNotIn(0xFF, room.objects[0].authored_verbs)

    def test_zigzag_and_major_minor_control_branches(self) -> None:
        zigzag_bits = [
            0,              # 5 -> 5
            1, 1, 0,        # increment -1: 5 -> 4
            1, 1, 1,        # reverse increment: 4 -> 5
            1, 0, 1, 0, 0, 1,  # absolute 9
            1, 1, 0,        # 9 -> 8
            1, 1, 1,        # 8 -> 9
            0,
        ]
        major_bits = [
            0,                  # 10 -> 10
            1, 1, 1, 0, 1,     # delta +1
            1, 0, 1, 1, 1, 0, 0, 0, 0, 0,  # absolute 7
            1, 1, 0, 0, 1,     # repeat marker (difference zero)
            1, 1, 0, 0, 0, 0, 0, 0,  # repeat count 3
            0,
            0,
        ]
        room = decode_room(
            raw_room(
                bytes((14, 5)) + pack_lsb(zigzag_bits),
                bytes((68, 10)) + pack_lsb(major_bits),
                height=1,
            ),
            key="room.controls",
        )

        self.assertEqual(room.pixels[:8], bytes((5, 5, 4, 5, 9, 8, 9, 9)))
        self.assertEqual(room.pixels[8:], bytes((10, 10, 11, 7, 7, 7, 7, 7)))

    def test_raw_room_corruption_and_unknown_codec_fail_closed(self) -> None:
        valid = raw_room(bytes((1,)) + bytes(range(16)))
        with self.assertRaisesRegex(ResourceError, "truncated"):
            decode_room(valid[:-1], key="room.truncated")

        unsupported = raw_room(bytes((63, 0, 0)))
        with self.assertRaisesRegex(ResourceError, "unsupported strip codec 63"):
            decode_room(unsupported, key="room.unsupported")

        bad_offset = bytearray(valid)
        smap = bad_offset.index(b"SMAP")
        bad_offset[smap + 8 : smap + 12] = (0).to_bytes(4, "little")
        with self.assertRaisesRegex(ResourceError, "offset is out of bounds"):
            decode_room(bytes(bad_offset), key="room.bad-offset")

        chained_bad_parent = raw_room(
            bytes((1,)) + bytes(range(16)),
            object_headers=(
                struct.pack("<HBBBBBBhhB", 100, 0, 0, 1, 1, 0, 2, 0, 0, 0),
                struct.pack("<HBBBBBBhhB", 101, 0, 0, 1, 1, 0, 3, 0, 0, 0),
            ),
        )
        with self.assertRaisesRegex(ResourceError, "parent index 3 is out of bounds"):
            decode_room(chained_bad_parent, key="room.bad-parent")

        cyclic_parents = raw_room(
            bytes((1,)) + bytes(range(16)),
            object_headers=(
                struct.pack("<HBBBBBBhhB", 100, 0, 0, 1, 1, 0, 2, 0, 0, 0),
                struct.pack("<HBBBBBBhhB", 101, 0, 0, 1, 1, 0, 1, 0, 0, 0),
            ),
        )
        with self.assertRaisesRegex(ResourceError, "hierarchy contains a cycle"):
            decode_room(cyclic_parents, key="room.parent-cycle")

    def test_raw_zplane_rle_zero_strips_and_msb_pixel_order(self) -> None:
        room = decode_room(
            raw_room(
                bytes((1,)) + bytes(range(64)),
                bytes((1,)) + bytes(range(64, 128)),
                height=8,
                zplanes=((bytes((0x84, 0x18, 4, 0x80, 0x40, 0x20, 0x10)), None),),
            ),
            key="room.zplane",
        )

        self.assertEqual(len(room.zplanes), 1)
        self.assertEqual(
            room.zplanes[0],
            bytes((0x18, 0, 0x18, 0, 0x18, 0, 0x18, 0, 0x80, 0, 0x40, 0, 0x20, 0, 0x10, 0)),
        )

        truncated = raw_room(
            bytes((1,)) + bytes(range(64)), height=8,
            zplanes=((bytes((0x88,)),),),
        )
        with self.assertRaisesRegex(ResourceError, "repeated mask RLE is truncated"):
            decode_room(truncated, key="room.bad-zplane")

    def test_raw_walkbox_geometry_mask_and_corruption(self) -> None:
        sentinel = struct.pack("<hhhhhhhhBBH", *([-32000] * 8), 0, 0, 255)
        trapezoid = struct.pack(
            "<hhhhhhhhBBH", 1, 1, 7, 1, 6, 7, 2, 7, 1, 0x08, 0x8001,
        )
        room = decode_room(
            raw_room(
                bytes((1,)) + bytes(64), height=8,
                zplanes=((bytes((0x88, 0)),),), walkboxes=(sentinel, trapezoid),
                box_matrix=bytes((0, 0, 0, 1, 1, 1, 0xFF, 0, 1, 0, 0xFF)),
            ),
            key="room.walkboxes",
        )
        box = room.walkboxes[1]
        self.assertEqual(
            (box.index, box.upper_left, box.upper_right, box.lower_right,
             box.lower_left, box.mask, box.flags, box.scale),
            (1, (1, 1), (7, 1), (6, 7), (2, 7), 1, 0x08, 0x8001),
        )
        self.assertTrue(box.contains(4, 4))
        self.assertFalse(box.contains(0, 4))
        self.assertEqual(room.next_box(0, 1), 1)
        self.assertEqual(room.next_box(1, 0), 0)
        self.assertEqual(room.next_box(1, 1), 1)

        bad_mask = raw_room(
            bytes((1,)) + bytes(16),
            walkboxes=(sentinel, trapezoid),
        )
        with self.assertRaisesRegex(ResourceError, "mask 1 exceeds 0 z-planes"):
            decode_room(bad_mask, key="room.bad-box-mask")

        bad_matrix = raw_room(
            bytes((1,)) + bytes(16), box_matrix=bytes((0, 2, 0, 0xFF, 1, 1, 1, 0xFF)),
        )
        with self.assertRaisesRegex(ResourceError, "contains an invalid route"):
            decode_room(bad_matrix, key="room.bad-box-matrix")

    def test_source_backed_high_index_walkboxes_survive_decode(self) -> None:
        boxes = tuple(
            struct.pack(
                "<hhhhhhhhBBH",
                index * 4, 0, index * 4 + 3, 0,
                index * 4 + 3, 7, index * 4, 7,
                0, index & 0xFF, 0x8000 + index,
            )
            for index in range(64)
        )
        matrix = b"".join(
            bytes((index, index, index, 0xFF)) for index in range(64)
        )
        room = decode_room(
            raw_room(bytes((1,)) + bytes(range(64)), height=8,
                     walkboxes=boxes, box_matrix=matrix),
            key="room.sixty-four-boxes",
        )
        high = room.walkboxes[63]
        self.assertEqual(high.index, 63)
        self.assertEqual(high.upper_left, (252, 0))
        self.assertEqual(high.scale, 0x803F)
        self.assertEqual(room.next_box(63, 63), 63)

    def test_get_actor_walkbox_direct_variable_and_save(self) -> None:
        sentinel = struct.pack("<hhhhhhhhBBH", *([-32000] * 8), 0, 0, 255)
        left = struct.pack("<hhhhhhhhBBH", 0, 0, 7, 0, 7, 7, 0, 7, 0, 0, 255)
        right = struct.pack("<hhhhhhhhBBH", 8, 0, 15, 0, 15, 7, 8, 7, 0, 0, 255)
        room_data = raw_room(
            bytes((1,)) + bytes(16), bytes((1,)) + bytes(range(16, 32)), height=2,
            walkboxes=(sentinel, left, right),
            box_matrix=bytes((
                0, 0, 0, 1, 2, 1, 0xFF,
                0, 1, 0, 2, 2, 2, 0xFF,
                0, 0, 1, 1, 2, 1, 0xFF,
            )),
        )
        script = bytes((
            0x72, 1,
            0x7B, 0, 0, 1,
            0x80,
            0x1A, 1, 0, 1, 0,
            0xFB, 2, 0, 1, 0,
            0x80, 0x00,
        ))
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = MemoryResourceProvider(
            {"script.boot": script, "room.1": room_data},
            kinds={"script.boot": "SCRP", "room.1": "ROOM"},
        )
        host = EngineHost(
            profile, default_registry(), services=HostServices.create(profile, resources=resources)
        )
        host.boot()
        # Position lies in box 1 while the stored canonical field says box 2;
        # getActorWalkBox must not recompute it from room geometry.
        host.engine.state.actors[1] = ActorState(room=1, position=(4, 1), walkbox=2)
        host.tick()
        self.assertEqual(host.engine.state.variables[0], 2)
        self.assertEqual(host.engine.state.actors[1].walkbox, 2)
        saved = host.save(0)
        self.assertEqual(saved.schema, 6)
        host.engine.state.actors[1].walkbox = 0
        host.load(0)
        self.assertEqual(host.engine.state.actors[1].walkbox, 2)

        host.tick()
        self.assertEqual(host.engine.state.variables[2], 2)

    def test_c39_walk_actor_routes_waits_queries_and_restores_mid_leg(self) -> None:
        sentinel = struct.pack("<hhhhhhhhBBH", *([-32000] * 8), 0, 0, 255)
        boxes = (
            sentinel,
            struct.pack("<hhhhhhhhBBH", 0, 0, 8, 0, 8, 7, 0, 7, 0, 0, 255),
            struct.pack("<hhhhhhhhBBH", 8, 0, 16, 0, 16, 7, 8, 7, 0, 0, 255),
            struct.pack("<hhhhhhhhBBH", 16, 0, 23, 0, 23, 7, 16, 7, 0, 0, 255),
        )
        matrix = bytes((
            0, 3, 0, 0xFF,
            0, 0, 0, 1, 1, 1, 2, 3, 2, 0xFF,
            0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 0xFF,
            0, 0, 0, 1, 2, 2, 3, 3, 3, 0xFF,
        ))
        room_data = raw_room(
            *(bytes((1,)) + bytes(range(64)) for _ in range(3)),
            height=8,
            walkboxes=boxes,
            box_matrix=matrix,
        )
        room = decode_room(room_data, key="room.c39")
        self.assertEqual(room.adjust_point(30, 4), ((23, 4), 3))
        self.assertEqual(room.route_gate(1, 2, 3, (4, 4), (20, 4)), (False, (8, 4)))
        self.assertEqual(room.route_gate(2, 3, 3, (8, 4), (20, 4)), (True, None))

        script = bytes((
            0x72, 1,
            0x1E, 1, 20, 0, 4, 0,
            0x56, 0, 0, 1,
            0x80,
            0x3B, 1, 0, 1,
            0x56, 1, 0, 1,
            0x7B, 2, 0, 1,
            0x00,
        ))
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = MemoryResourceProvider(
            {"script.boot": script, "room.1": room_data},
            kinds={"script.boot": "SCRP", "room.1": "ROOM"},
        )
        host = EngineHost(
            profile, default_registry(), services=HostServices.create(profile, resources=resources)
        )
        host.boot()
        host.engine.state.actors[1] = ActorState(room=1, position=(4, 4), walkbox=1)

        host.tick()
        actor = host.engine.state.actors[1]
        self.assertEqual(host.engine.state.variables[0], 1)
        self.assertEqual((actor.position, actor.walkbox, actor.moving), ((15, 4), 2, 10))
        saved = host.save(0)
        self.assertEqual(saved.schema, 6)
        expected_record = actor.to_dict()

        actor.position = (0, 0)
        actor.moving = 0
        host.load(0)
        actor = host.engine.state.actors[1]
        self.assertEqual(actor.to_dict(), expected_record)
        host.tick()
        self.assertEqual(host.engine.state.variables[1], 10)
        self.assertEqual(host.engine.state.variables[2], 2)
        self.assertFalse(host.engine.state.scripts[0].active)

    def test_engine_presents_raw_room_on_the_host_viewport(self) -> None:
        strip = bytes((1,)) + bytes(range(16))
        room_data = raw_room(*(strip for _ in range(32)))
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = MemoryResourceProvider(
            {"script.boot": b"\x00", "room.0": room_data},
            kinds={"script.boot": "SCRP", "room.0": "ROOM"},
        )
        host = EngineHost(
            profile,
            default_registry(),
            services=HostServices.create(profile, resources=resources),
        )
        host.boot()

        video = host.engine.inspect_state()["video"]
        self.assertEqual(video["format"], "raw-v5")
        self.assertEqual(video["dimensions"], [256, 2])
        self.assertEqual(video["projection"], [0, 0, 0, 111, 256, 2])
        self.assertEqual(host.services.video.surface.pixels[111 * 256 : 111 * 256 + 8], bytes(range(8)))
        self.assertEqual(
            host.services.video._dirty.rects,
            (
                Rect(0, 0, 256, 224),
                Rect(0, 0, 256, 224),
                Rect(0, 0, 256, 224),
                Rect(0, 111, 256, 2),
            ),
        )
        adapter = host.engine._video
        backdrop = adapter.backdrop_surface
        self.assertIsNotNone(backdrop)
        assert backdrop is not None and adapter.room is not None
        self.assertIs(backdrop.pixels, adapter.room.pixels)
        self.assertTrue(backdrop.readonly)
        self.assertEqual(backdrop.visible_bytes(), adapter.room.pixels)
        owned = IndexedSurface(backdrop.width, backdrop.height)
        owned.set_palette(0, backdrop.palette)
        owned.pixels[:] = adapter.room.pixels
        self.assertEqual(backdrop.hash(), owned.hash())
        self.assertEqual(backdrop.to_image().tobytes(), owned.to_image().tobytes())
        with self.assertRaisesRegex(TypeError, "read-only"):
            backdrop.set_pixel(0, 0, 7)

    def test_room_local_scripts_decode_resolve_save_and_retire_on_transition(self) -> None:
        strip = bytes((1,)) + bytes(range(16))
        local_program = bytes((0x1A, 9, 0, 123, 0, 0x80, 0x00))
        room_one = raw_room(
            strip,
            entry_script=b"\x80\x00",
            exit_script=b"\x00",
            local_scripts=((200, local_program),),
        )
        decoded = decode_room(room_one, key="room.1")
        self.assertEqual(decoded.entry_script, b"\x80\x00")
        self.assertEqual(decoded.exit_script, b"\x00")
        self.assertEqual(decoded.local_scripts, ((200, local_program),))

        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = MemoryResourceProvider(
            {
                "script.boot": bytes((0x72, 1, 0x0A, 200, 0xFF, 0x80, 0x72, 2, 0x00)),
                "room.1": room_one,
                "room.2": raw_room(strip),
            },
            kinds={"script.boot": "SCRP", "room.1": "ROOM", "room.2": "ROOM"},
        )
        host = EngineHost(
            profile,
            default_registry(),
            services=HostServices.create(profile, resources=resources),
        )
        host.boot()
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["variables"]["9"], 123)
        local = next(slot for slot in state["scripts"] if slot["number"] == 200)
        self.assertEqual(
            (local["resource"], local["room"], local["pc"], local["active"]),
            ("room.1/LSCR.200", 1, 6, True),
        )

        saved = host.save(0)
        assert host.context is not None
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        local_payload = next(item for item in payload["scripts"] if item["room"] is not None)
        local_payload["resource"] = "room.1/LSCR.201"
        with self.assertRaisesRegex(SaveFormatError, "local-script identity is invalid"):
            host.engine.load_state(host.context, json.dumps(payload).encode("utf-8"))
        host.engine.state.variables[9] = 0
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["variables"]["9"], 123)
        host.tick()
        transitioned = host.engine.inspect_state()
        self.assertEqual(transitioned["room"], 2)
        self.assertFalse(any(slot["active"] and slot["room"] is not None for slot in transitioned["scripts"]))

    def test_room_local_scripts_fail_closed_on_malformed_chunks_and_save_identity(self) -> None:
        strip = bytes((1,)) + bytes(range(16))
        duplicate = raw_room(strip, local_scripts=((200, b"\x00"), (200, b"\x80")))
        with self.assertRaisesRegex(ResourceError, "duplicate local script 200"):
            decode_room(duplicate, key="room.duplicate-local")
        empty = raw_room(strip) + chunk(b"LSCR", b"\xC8")
        with self.assertRaisesRegex(ResourceError, "has no script body"):
            decode_room(empty, key="room.empty-local")

    def test_complete_room_local_namespace_resolves_without_auto_scheduling(self) -> None:
        strip = bytes((1,)) + bytes(range(16))

        def set_var(variable: int, value: int) -> bytes:
            return bytes((0x1A, variable, 0, value, 0, 0x00))

        def start(number: int) -> bytes:
            return bytes((0x0A, number, 0xFF))

        locals_one = tuple(
            (number, set_var(variable, value))
            for number, variable, value in (
                (200, 20, 1), (201, 21, 2), (202, 22, 3), (208, 28, 8)
            )
        )
        room_one = raw_room(strip, local_scripts=locals_one)
        room_two = raw_room(
            strip,
            local_scripts=((202, set_var(22, 9)),),
        )
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = MemoryResourceProvider(
            {
                "script.boot": b"".join((
                    bytes((0x72, 1)),
                    start(10), start(200), start(201), start(202), start(208),
                    bytes((0x72, 2)), start(202), bytes((0x00,)),
                )),
                "script.10": set_var(10, 10),
                "room.1": room_one,
                "room.2": room_two,
            },
            kinds={
                "script.boot": "SCRP", "script.10": "SCRP",
                "room.1": "ROOM", "room.2": "ROOM",
            },
        )
        host = EngineHost(
            profile, default_registry(),
            services=HostServices.create(profile, resources=resources),
        )
        host.boot()
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["room"], 2)
        self.assertEqual(
            {key: state["variables"][str(key)] for key in (10, 20, 21, 22, 28)},
            {10: 10, 20: 1, 21: 2, 22: 9, 28: 8},
        )
        self.assertFalse(any(
            item["active"] and item["room"] == 1 for item in state["scripts"]
        ))

    def test_local_namespace_missing_entry_does_not_fall_back_to_global(self) -> None:
        strip = bytes((1,)) + bytes(range(16))
        room_one = raw_room(strip, local_scripts=((202, bytes((0x00,))),))
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = MemoryResourceProvider(
            {
                "script.boot": bytes((0x72, 1, 0x0A, 203, 0xFF, 0x00)),
                # A resource with the same numeric name must not satisfy a
                # current-room-local request above the boundary.
                "script.203": bytes((0x00,)),
                "room.1": room_one,
            },
            kinds={"script.boot": "SCRP", "script.203": "SCRP", "room.1": "ROOM"},
        )
        host = EngineHost(
            profile, default_registry(),
            services=HostServices.create(profile, resources=resources),
        )
        host.boot()
        with self.assertRaisesRegex(EngineExecutionError, "no local script 203"):
            host.tick()


if __name__ == "__main__":
    unittest.main()
