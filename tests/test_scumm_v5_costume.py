from __future__ import annotations

from pathlib import Path
import json
import struct
import unittest

from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5 import ScummV5Costume
from same.engines.scumm_v5.engine import ActorState
from same.errors import ResourceError, SaveFormatError
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices

ROOT = Path(__file__).resolve().parents[1]


def synthetic_costume(*, color_count: int = 16) -> bytes:
    costume_format = 0x58 if color_count == 16 else 0x59
    animation_count = 6
    table = 2 + color_count
    data_offsets = table + 34
    record = data_offsets + (animation_count + 1) * 2
    commands = record + 5
    frame_table = commands + 1
    cel = frame_table + 2
    data = bytearray(cel + 12)
    data[0:2] = bytes((animation_count, costume_format))
    data[2 : 2 + color_count] = bytes(range(color_count))
    struct.pack_into("<H", data, table, commands + 6)
    struct.pack_into("<H", data, table + 2, frame_table + 6)
    struct.pack_into("<H", data, data_offsets + 6 * 2, record + 6)
    struct.pack_into("<HHB", data, record, 0x8000, 0, 0)
    data[commands] = 0
    struct.pack_into("<H", data, frame_table, cel + 6)
    struct.pack_into("<HHhhhh", data, cel, 2, 2, -1, -1, 0, 0)
    shift = 4 if color_count == 16 else 3
    data.extend(bytes(((color << shift) | 1) for color in (1, 2, 2, 1)))
    return bytes(data)


def animated_costume(*, one_shot: bool = False) -> bytes:
    """Two one-pixel cels with a counter command between them."""
    color_count = 16
    animation_count = 6
    table = 2 + color_count
    data_offsets = table + 34
    record = data_offsets + (animation_count + 1) * 2
    commands = record + 5
    frame_table = commands + 3
    cel0 = frame_table + 4
    cel1 = cel0 + 13
    data = bytearray(cel1 + 13)
    data[0:2] = bytes((animation_count, 0x58))
    data[2:18] = bytes(range(16))
    struct.pack_into("<H", data, table, commands + 6)
    struct.pack_into("<H", data, table + 2, frame_table + 6)
    struct.pack_into("<H", data, data_offsets + 6 * 2, record + 6)
    struct.pack_into("<HHB", data, record, 0x8000, 0, 0x82 if one_shot else 2)
    data[commands : commands + 3] = bytes((0, 0x7C, 1))
    struct.pack_into("<HH", data, frame_table, cel0 + 6, cel1 + 6)
    struct.pack_into("<HHhhhhB", data, cel0, 1, 1, 0, 0, 0, 0, 0x11)
    struct.pack_into("<HHhhhhB", data, cel1, 1, 1, 0, 0, 0, 0, 0x21)
    return bytes(data)


def rectangular_costume() -> bytes:
    """A directional 4x4 cel whose RLE stream exposes column traversal."""
    animation_count = 7
    table = 18
    data_offsets = table + 34
    record = data_offsets + (animation_count + 1) * 2
    commands = record + 5
    frame_table = commands + 1
    cel = frame_table + 2
    pixels = bytes((*range(1, 16), 1))
    data = bytearray(cel + 12)
    data[0:2] = bytes((animation_count, 0x58))
    data[2:18] = bytes(range(16))
    struct.pack_into("<H", data, table, commands + 6)
    struct.pack_into("<H", data, table + 2, frame_table + 6)
    for animation in range(4, 8):
        struct.pack_into("<H", data, data_offsets + animation * 2, record + 6)
    struct.pack_into("<HHB", data, record, 0x8000, 0, 0)
    data[commands] = 0
    struct.pack_into("<H", data, frame_table, cel + 6)
    struct.pack_into("<HHhhhh", data, cel, 4, 4, 0, 0, 0, 0)
    data.extend(bytes((color << 4) | 1 for color in pixels))
    return bytes(data)


def masked_raw_room() -> bytes:
    def chunk(tag: bytes, payload: bytes) -> bytes:
        return tag + (len(payload) + 8).to_bytes(4, "big") + payload

    palette = bytes(component for color in range(256) for component in (color, color, color))
    smap = chunk(b"SMAP", (12).to_bytes(4, "little") + bytes((1,)) + bytes(64))
    zplane = chunk(b"ZP01", (10).to_bytes(2, "little") + bytes((0x88, 0x18)))
    sentinel = struct.pack("<hhhhhhhhBBH", *([-32000] * 8), 0, 0, 255)
    background = struct.pack(
        "<hhhhhhhhBBH", 0, 0, 7, 0, 7, 7, 0, 7, 0, 0, 255,
    )
    foreground = struct.pack(
        "<hhhhhhhhBBH", 2, 2, 6, 2, 6, 6, 2, 6, 1, 0, 255,
    )
    return b"".join((
        chunk(b"RMHD", struct.pack("<HHH", 8, 8, 0)),
        chunk(b"TRNS", struct.pack("<H", 255)),
        chunk(b"CLUT", palette),
        chunk(b"BOXD", struct.pack("<H", 3) + sentinel + background + foreground),
        chunk(b"BOXM", bytes((0, 0, 0, 0xFF, 1, 1, 1, 0xFF, 2, 2, 2, 0xFF))),
        chunk(b"RMIM", chunk(b"RMIH", b"\x01\x00") + chunk(b"IM00", smap + zplane)),
    ))


class ScummV5CostumeTests(unittest.TestCase):
    def test_direction_selection_uses_canonical_old_direction_mapping(self) -> None:
        expected = {
            0: 3,
            70: 3,
            71: 1,
            90: 1,
            109: 1,
            110: 2,
            180: 2,
            250: 2,
            251: 2,
            270: 0,
            289: 0,
            290: 3,
            359: 3,
        }
        self.assertEqual(
            {angle: ScummV5Costume.direction_index(angle) for angle in expected},
            expected,
        )

    def test_format_58_initial_pose_tables_palette_and_rle(self) -> None:
        costume = ScummV5Costume(synthetic_costume(), key="costume.synthetic")
        pose = costume.decode_pose(1, facing=180)
        self.assertEqual((costume.animation_count, costume.format), (6, 0x58))
        self.assertEqual(costume.palette, tuple(range(16)))
        self.assertTrue(pose.draw_to_right)
        self.assertEqual(len(pose.cels), 1)
        cel = pose.cels[0]
        self.assertEqual(
            (cel.width, cel.height, cel.relative_x, cel.relative_y, cel.move_x, cel.move_y),
            (2, 2, -1, -1, 0, 0),
        )
        self.assertEqual(cel.pixels, bytes((1, 2, 2, 1)))

    def test_format_59_and_absent_pose(self) -> None:
        costume = ScummV5Costume(
            synthetic_costume(color_count=32), key="costume.synthetic32"
        )
        self.assertEqual(costume.decode_pose(1, facing=180).cels[0].pixels, bytes((1, 2, 2, 1)))
        self.assertEqual(costume.decode_pose(2, facing=180).cels, ())

    def test_chore_cursor_skips_counter_and_loops_or_holds(self) -> None:
        looping = ScummV5Costume(animated_costume(), key="costume.loop")
        self.assertEqual(
            [looping.decode_pose(1, step=step).cels[0].pixels for step in range(4)],
            [b"\x01", b"\x02", b"\x01", b"\x02"],
        )
        held = ScummV5Costume(animated_costume(one_shot=True), key="costume.hold")
        self.assertEqual(
            [held.decode_pose(1, step=step).cels[0].pixels for step in range(4)],
            [b"\x01", b"\x02", b"\x02", b"\x02"],
        )

    def test_costume_corruption_fails_closed(self) -> None:
        unsupported = bytearray(synthetic_costume())
        unsupported[1] = 0x57
        with self.assertRaisesRegex(ResourceError, "unsupported format"):
            ScummV5Costume(bytes(unsupported), key="costume.bad-format")

        truncated = synthetic_costume()[:-1]
        with self.assertRaisesRegex(ResourceError, "RLE is truncated"):
            ScummV5Costume(truncated, key="costume.truncated").decode_pose(1)

        bad_offset = bytearray(synthetic_costume())
        bad_offset[18:20] = (5).to_bytes(2, "little")
        with self.assertRaisesRegex(ResourceError, "offset 5 is invalid"):
            ScummV5Costume(bytes(bad_offset), key="costume.bad-offset")

    def test_initial_pose_composites_into_room_and_publishes_hitbox(self) -> None:
        palette = bytes(component for color in range(3) for component in (color, color, color))
        room = struct.pack("<4sBHHH", b"SC5R", 1, 8, 8, 3) + palette + bytes(64)
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = MemoryResourceProvider(
            {
                "script.boot": bytes((0x72, 1, 0x80, 0x00)),
                "room.1": room,
                "costume.1": synthetic_costume(),
            },
            kinds={"script.boot": "SCRP", "room.1": "ROOM", "costume.1": "COST"},
        )
        host = EngineHost(
            profile, default_registry(), services=HostServices.create(profile, resources=resources)
        )
        host.boot()
        host.engine.state.actors[1] = ActorState(
            costume=1, room=1, visible=True, position=(4, 4)
        )
        host.tick()
        logical = host.engine._video.logical_surface
        assert logical is not None
        self.assertEqual(
            [logical.pixels[y * 8 + x] for y in (3, 4) for x in (3, 4)],
            [1, 2, 2, 1],
        )
        state = host.engine.inspect_state()
        self.assertEqual(state["actors"]["1"]["hitbox"], [3, 3, 4, 4])
        self.assertEqual(
            state["video"]["actors"],
            [{
                "actor": 1, "costume": 1, "frame": 1, "step": 0, "facing": 180,
                "scale": [255, 255], "walkbox": None,
                "z_plane": 0, "occluded": 0,
                "cels": 1, "pixels": 4,
                "bounds": [3, 3, 4, 4],
            }],
        )

    def test_walkbox_mask_composites_actor_behind_raw_zplane(self) -> None:
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = MemoryResourceProvider(
            {
                "script.boot": bytes((0x72, 1, 0x80, 0x00)),
                "room.1": masked_raw_room(),
                "costume.1": synthetic_costume(),
            },
            kinds={"script.boot": "SCRP", "room.1": "ROOM", "costume.1": "COST"},
        )
        host = EngineHost(
            profile, default_registry(), services=HostServices.create(profile, resources=resources)
        )
        host.boot()
        actor = ActorState(
            costume=1, room=1, visible=True, position=(4, 4),
        )
        host.engine.state.actors[1] = actor
        host.tick()

        logical = host.engine._video.logical_surface
        assert logical is not None
        self.assertEqual(bytes(logical.pixels), bytes(64))
        self.assertEqual(actor.hitbox, (0, 0, 0, 0))
        self.assertEqual(host.engine.inspect_state()["video"]["zplanes"], 1)
        self.assertEqual(host.engine.inspect_state()["video"]["walkboxes"], 3)
        self.assertEqual(
            host.engine.inspect_state()["video"]["actors"][0],
            {
                "actor": 1, "costume": 1, "frame": 1, "step": 0, "facing": 180,
                "scale": [255, 255], "walkbox": 2,
                "z_plane": 1, "occluded": 4,
                "cels": 1, "pixels": 0, "bounds": None,
            },
        )

        actor.costume_step = 0
        host.engine.state.object_classes[1] = {20}
        host.engine._video.render_actors(
            {1: actor}, current_room=1, costume_key=lambda costume: f"costume.{costume}",
            object_classes=host.engine.state.object_classes,
        )
        self.assertEqual(host.engine._video.actor_draws[0]["z_plane"], 0)
        self.assertEqual(host.engine._video.actor_draws[0]["pixels"], 4)

        actor.force_clip = 1
        host.engine._video.render_actors(
            {1: actor}, current_room=1, costume_key=lambda costume: f"costume.{costume}",
            object_classes=host.engine.state.object_classes,
        )
        self.assertEqual(host.engine._video.actor_draws[0]["z_plane"], 1)
        self.assertEqual(host.engine._video.actor_draws[0]["occluded"], 4)

    def test_classic_phase_scaling_anchor_columns_rows_and_mirror(self) -> None:
        palette = bytes(component for color in range(16) for component in (color, color, color))
        room = struct.pack("<4sBHHH", b"SC5R", 1, 12, 12, 16) + palette + bytes(144)
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = MemoryResourceProvider(
            {
                "script.boot": bytes((0x72, 1, 0x80, 0x00)),
                "room.1": room,
                "costume.1": rectangular_costume(),
            },
            kinds={"script.boot": "SCRP", "room.1": "ROOM", "costume.1": "COST"},
        )
        host = EngineHost(
            profile, default_registry(), services=HostServices.create(profile, resources=resources)
        )
        host.boot()
        actor = ActorState(
            costume=1, room=1, visible=True, position=(6, 6), scale=(128, 192)
        )
        host.engine.state.actors[1] = actor
        host.tick()
        logical = host.engine._video.logical_surface
        assert logical is not None
        self.assertEqual(actor.hitbox, (6, 6, 8, 8))
        self.assertEqual(
            [[logical.pixels[y * 12 + x] for x in range(6, 9)] for y in range(6, 9)],
            [[1, 9, 13], [2, 10, 14], [3, 11, 15]],
        )
        draw = host.engine.inspect_state()["video"]["actors"][0]
        self.assertEqual((draw["scale"], draw["pixels"], draw["bounds"]),
                         ([128, 192], 9, [6, 6, 8, 8]))

        # Canonical old direction zero is internal 270 degrees and is the
        # non-mirrored classic-costume orientation.
        actor.facing = 270
        actor.costume_step = 0
        host.engine._actors_dirty = True
        host.engine._video.render_actors(
            host.engine.state.actors, current_room=1,
            costume_key=lambda costume: f"costume.{costume}",
        )
        self.assertEqual(
            [[logical.pixels[y * 12 + x] for x in range(3, 7)] for y in range(6, 9)],
            [[13, 9, 5, 1], [14, 10, 6, 2], [15, 11, 7, 3]],
        )
        mirrored = host.engine.inspect_state()["video"]["actors"][0]
        self.assertEqual((mirrored["pixels"], mirrored["bounds"]), (12, [3, 6, 6, 8]))

    def test_engine_draws_then_advances_at_actor_speed_and_saves_cursor(self) -> None:
        palette = bytes(component for color in range(3) for component in (color, color, color))
        room = struct.pack("<4sBHHH", b"SC5R", 1, 8, 8, 3) + palette + bytes(64)
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = MemoryResourceProvider(
            {
                "script.boot": bytes((0x72, 1, 0x80, 0x18, 0xFC, 0xFF)),
                "room.1": room,
                "costume.1": animated_costume(),
            },
            kinds={"script.boot": "SCRP", "room.1": "ROOM", "costume.1": "COST"},
        )
        host = EngineHost(
            profile, default_registry(), services=HostServices.create(profile, resources=resources)
        )
        host.boot()
        host.engine.state.actors[1] = ActorState(
            costume=1, room=1, visible=True, position=(4, 4), animation_speed=2
        )
        host.engine._actors_dirty = True
        host.tick()
        self.assertEqual(host.engine.inspect_state()["video"]["actors"][0]["step"], 0)
        self.assertEqual(host.engine.state.actors[1].animation_progress, 1)
        host.tick()
        self.assertEqual(host.engine.state.actors[1].costume_step, 1)
        self.assertEqual(host.engine.inspect_state()["video"]["actors"][0]["step"], 0)
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["video"]["actors"][0]["step"], 1)
        logical = host.engine._video.logical_surface
        assert logical is not None
        self.assertEqual(logical.pixels[4 * 8 + 4], 2)
        saved = host.save(0)
        host.engine.state.actors[1].costume_step = 99
        host.load(0)
        self.assertEqual(host.engine.state.actors[1].costume_step, 1)
        self.assertEqual(saved.schema, 6)
        assert host.context is not None
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed = (
            ({**payload["actors"]["1"], "facing": 45}, "facing must be cardinal"),
            ({**payload["actors"]["1"], "costume_frame": 256}, "frame must fit u8"),
            ({**payload["actors"]["1"], "costume_step": -1}, "step must fit u32"),
            ({**payload["actors"]["1"], "animation_progress": 256}, "progress must fit u8"),
        )
        for actor, message in malformed:
            candidate = {**payload, "actors": {"1": actor}}
            with self.assertRaisesRegex(SaveFormatError, message):
                host.engine.load_state(host.context, json.dumps(candidate).encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
