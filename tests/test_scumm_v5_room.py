from __future__ import annotations

import json
from pathlib import Path
import struct
import unittest

from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5 import decode_room
from same.errors import ResourceError, SaveFormatError
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices

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
    object_headers: tuple[bytes, ...] = (),
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
    palette = bytes(component for color in range(256) for component in (color, color, color))
    return b"".join(
        (
            chunk(b"RMHD", struct.pack("<HHH", width, height, len(object_headers))),
            chunk(b"TRNS", struct.pack("<H", 255)),
            chunk(b"CLUT", palette),
            chunk(b"RMIM", chunk(b"RMIH", b"\x01\x00") + chunk(b"IM00", smap)),
            *(chunk(b"OBCD", chunk(b"CDHD", header)) for header in object_headers),
            *(chunk(b"ENCD", entry_script) for _ in range(entry_script is not None)),
            *(chunk(b"EXCD", exit_script) for _ in range(exit_script is not None)),
            *(chunk(b"LSCR", bytes((script_id,)) + program) for script_id, program in local_scripts),
        )
    )


class ScummV5RawRoomTests(unittest.TestCase):
    def test_raw_basic_vertical_horizontal_and_major_minor_strips(self) -> None:
        raw_pixels = bytes(range(16))
        vertical_pixels = bytes((*range(20, 28), *range(30, 38)))
        major_pixels = bytes((*range(40, 48), *range(50, 58)))
        room = decode_room(
            raw_room(
                bytes((1,)) + raw_pixels,
                absolute_strip(18, vertical_pixels, vertical=True),
                absolute_strip(68, major_pixels),
                object_headers=(struct.pack("<HBBBBBBhhB", 100, 3, 4, 34, 18, 2, 7, 108, 118, 1),),
            ),
            key="room.synthetic",
        )

        self.assertEqual((room.width, room.height), (24, 2))
        self.assertEqual(room.source_format, "raw-v5")
        self.assertEqual(room.strip_codecs, (1, 18, 68))
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
            (100, 24, 32, 272, 144, 2, 7, 108, 118, 1),
        )

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


if __name__ == "__main__":
    unittest.main()
