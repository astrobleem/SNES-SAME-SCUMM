from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import unittest

from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5.cooked_room import (
    HEADER, SCRIPT, ScriptChunkInput, decode_cooked_room, encode_cooked_room,
)
from same.errors import EngineExecutionError, ResourceError
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/scumm_v5_conformance.json"


def chunk(tag: bytes, payload: bytes) -> bytes:
    return tag + struct.pack(">I", len(payload) + 8) + payload


def raw_room(*, entry: bytes, exit: bytes, locals: tuple[tuple[int, bytes], ...]) -> bytes:
    palette = bytes(value for index in range(256) for value in (index, index, index))
    strip = bytes((1,)) + bytes(range(16))
    smap = chunk(b"SMAP", struct.pack("<I", 12) + strip)
    rmim = chunk(b"RMIM", chunk(b"RMIH", struct.pack("<H", 0)) + chunk(b"IM00", smap))
    walkboxes = (
        struct.pack("<hhhhhhhhBBH", *([-32000] * 8), 0, 0, 255),
        struct.pack("<hhhhhhhhBBH", 0, 0, 7, 0, 7, 1, 0, 1, 0, 0, 255),
    )
    box_matrix = b"\x00\x00\x00\xff\x01\x01\x01\xff"
    return b"".join((
        chunk(b"RMHD", struct.pack("<HHH", 8, 2, 0)),
        chunk(b"CLUT", palette), rmim,
        chunk(b"BOXD", struct.pack("<H", 2) + b"".join(walkboxes)),
        chunk(b"BOXM", box_matrix),
        chunk(b"ENCD", entry), chunk(b"EXCD", exit),
        *(chunk(b"LSCR", bytes((number,)) + program) for number, program in locals),
    ))


def script_inputs(room: int, payload: bytes) -> tuple[ScriptChunkInput, ...]:
    result = []
    offset = 0
    while offset < len(payload):
        tag = payload[offset:offset + 4].decode("ascii")
        size = int.from_bytes(payload[offset + 4:offset + 8], "big")
        if tag in {"ENCD", "EXCD", "LSCR"}:
            if tag == "LSCR":
                number = payload[offset + 8]
                body_offset = 9
                length = size - 9
                identity = f"room.{room}/LSCR.{number}"
            else:
                number = 10002 if tag == "ENCD" else 10001
                body_offset = 8
                length = size - 8
                identity = f"room.{room}/{tag}"
            result.append(ScriptChunkInput(
                tag, number, identity, offset, body_offset, length,
            ))
        offset += size
    return tuple(result)


def identities() -> tuple[str, str, str, str, str]:
    profile = load_profile(PROFILE)
    profile_hash = hashlib.sha256(PROFILE.read_bytes()).hexdigest()
    game_hash = hashlib.sha256(
        f"{profile.engine_id}\0{profile.game_id}\0{profile.variant}".encode()
    ).hexdigest()
    return profile_hash, game_hash, *(hashlib.sha256(name.encode()).hexdigest()
                                      for name in ("archive", "index", "data"))


def cooked(room: int, payload: bytes, *, flags: int = 0) -> bytes:
    profile_hash, game_hash, archive_hash, index_hash, data_hash = identities()
    return encode_cooked_room(
        payload, room=room, flags=flags, original_room_file_offset=100_000 + room * 1000,
        profile_sha256=profile_hash, game_identity_sha256=game_hash,
        archive_sha256=archive_hash, index_sha256=index_hash, data_sha256=data_hash,
        scripts=script_inputs(room, payload),
    )


def manifest() -> bytes:
    profile_hash, game_hash, archive_hash, index_hash, data_hash = identities()
    return json.dumps({
        "schema": "same_scumm_v5_cooked_rooms_v1",
        "profile": {"sha256": profile_hash, "identity_sha256": game_hash},
        "source": {
            "archive_sha256": archive_hash,
            "index_sha256": index_hash,
            "data_sha256": data_hash,
        },
    }).encode()


class CookedRoomTests(unittest.TestCase):
    def test_record_round_trip_and_strict_transactional_validation(self) -> None:
        payload = raw_room(entry=b"\x00", exit=b"\x00", locals=((200, b"\x80\x00"),))
        record_bytes = cooked(1, payload)
        profile_hash, game_hash, archive_hash, index_hash, data_hash = identities()
        record = decode_cooked_room(
            record_bytes, expected_room=1, expected_profile_sha256=profile_hash,
            expected_game_identity_sha256=game_hash,
            expected_archive_sha256=archive_hash, expected_index_sha256=index_hash,
            expected_data_sha256=data_hash,
        )
        self.assertEqual(record.room_payload, payload)
        self.assertEqual([item.identity for item in record.scripts], [
            "room.1/ENCD", "room.1/EXCD", "room.1/LSCR.200",
        ])
        self.assertEqual(record.entry.runtime_map(0)["runtime_instruction_offset"], 0)

        mutations = []
        corrupt = bytearray(record_bytes)
        corrupt[-40] ^= 1
        mutations.append(("corrupt record", bytes(corrupt)))
        bad_length = bytearray(record_bytes)
        struct.pack_into("<I", bad_length, 16, len(record_bytes) + 1)
        mutations.append(("record length differs", bytes(bad_length)))
        bad_schema = bytearray(record_bytes)
        struct.pack_into("<H", bad_schema, 8, 2)
        mutations.append(("schema", bytes(bad_schema)))
        bad_range = bytearray(record_bytes)
        struct.pack_into("<I", bad_range, HEADER.size + 20, len(record_bytes) + 100)
        mutations.append(("out-of-range source mapping", bytes(bad_range)))
        overlap = bytearray(record_bytes)
        first_cooked = struct.unpack_from("<I", overlap, HEADER.size + 20)[0]
        struct.pack_into("<I", overlap, HEADER.size + SCRIPT.size + 20, first_cooked)
        mutations.append(("overlapping source mapping", bytes(overlap)))
        for message, value in mutations:
            with self.subTest(message=message), self.assertRaises(ResourceError):
                decode_cooked_room(value)
        with self.assertRaisesRegex(ResourceError, "room identity differs"):
            decode_cooked_room(record_bytes, expected_room=2)
        for field in ("profile", "game identity", "archive", "index", "data"):
            kwargs = {
                "expected_profile_sha256": profile_hash,
                "expected_game_identity_sha256": game_hash,
                "expected_archive_sha256": archive_hash,
                "expected_index_sha256": index_hash,
                "expected_data_sha256": data_hash,
            }
            key = next(name for name in kwargs if field.replace(" ", "_") in name)
            kwargs[key] = "00" * 32
            with self.subTest(binding=field), self.assertRaises(ResourceError):
                decode_cooked_room(record_bytes, **kwargs)

    def test_host_executes_authoritative_exit_retire_activate_register_entry_order(self) -> None:
        # Room 1 entry starts a persistent local script. Room 2 transition must
        # execute room 1 EXCD before retiring that local, then run room 2 ENCD.
        room1 = raw_room(
            entry=bytes((0x1A, 10, 0, 1, 0, 0x0A, 200, 0xFF, 0x00)),
            exit=bytes((0x46, 12, 0, 0x00)),
            locals=((200, bytes((0x46, 11, 0, 0x80, 0x18, 0xFC, 0xFF))),),
        )
        room2 = raw_room(
            entry=bytes((0x46, 13, 0, 0x00)), exit=b"\x00",
            locals=((201, b"\x00"),),
        )
        # load room 1; yield; load room 2; stop
        boot = bytes((0x72, 1, 0x80, 0x72, 2, 0x00))
        resources = MemoryResourceProvider({
            "script.boot": boot,
            "room.1": room1, "room.2": room2,
            "cooked.room.1": cooked(1, room1),
            "cooked.room.2": cooked(2, room2),
            "cooked.rooms.manifest": manifest(),
        })
        profile = load_profile(PROFILE)
        host = EngineHost(
            profile, default_registry(),
            services=HostServices.create(profile, resources=resources),
        )
        host.boot()
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(first["room"], 1)
        self.assertEqual(first["variables"]["10"], 1)
        self.assertEqual(first["variables"]["11"], 1)
        self.assertTrue(any(slot["active"] and slot["script_kind"] == "LSCR"
                            for slot in first["scripts"]))
        host.tick()
        second = host.engine.inspect_state()
        self.assertEqual(second["room"], 2)
        self.assertEqual(second["variables"]["12"], 1)
        self.assertEqual(second["variables"]["13"], 1)
        self.assertFalse(any(slot["active"] and slot["room"] == 1
                             for slot in second["scripts"]))
        phases = [item["phase"] for item in host.engine.inspect_room_lifecycle()]
        exit_index = phases.index("old_exit_scheduled")
        retire_index = phases.index("old_room_scripts_retired", exit_index)
        activate_index = phases.index("new_room_activated", retire_index)
        entry_index = phases.index("entry_script_scheduled", activate_index)
        execute_index = phases.index("entry_first_instruction", entry_index)
        self.assertLess(exit_index, retire_index)
        self.assertLess(retire_index, activate_index)
        self.assertLess(activate_index, entry_index)
        self.assertLess(entry_index, execute_index)

    def test_room_local_nested_child_runs_immediately_then_resumes_later(self) -> None:
        # ENCD starts local A. A owns local[0]=1, immediately starts local B,
        # then resumes in the same frame after B's breakHere and increments its
        # own local. B's independent local resumes on the next scheduler pass.
        local_a = bytes((
            0x1A, 0x00, 0x40, 0x01, 0x00,  # local[0] = 1
            0x0A, 0xC9, 0xFF,              # startScript(201)
            0x46, 0x00, 0x40,              # local[0]++ after child yield
            0x80,                           # parent yields
            0x00,
        ))
        local_b = bytes((
            0x1A, 0x00, 0x40, 0x0A, 0x00,  # child local[0] = 10
            0x80,                           # immediate child yield
            0x46, 0x00, 0x40,              # next frame: child local[0]++
            0x00,
        ))
        room = raw_room(
            entry=bytes((0x0A, 0xC8, 0xFF, 0x00)), exit=b"\x00",
            locals=((200, local_a), (201, local_b)),
        )
        resources = MemoryResourceProvider({
            "script.boot": bytes((0x72, 1, 0x80, 0x00)),
            "room.1": room,
            "cooked.room.1": cooked(1, room),
            "cooked.rooms.manifest": manifest(),
        })
        profile = load_profile(PROFILE)
        host = EngineHost(
            profile, default_registry(),
            services=HostServices.create(profile, resources=resources),
        )
        host.boot()
        host.tick()
        first = host.engine.inspect_state()
        scripts = {item["number"]: item for item in first["scripts"] if item["number"]}
        self.assertEqual((scripts[200]["pc"], scripts[200]["locals"][0]), (12, 2))
        self.assertEqual((scripts[201]["pc"], scripts[201]["locals"][0]), (6, 10))
        self.assertTrue(scripts[200]["yielded"] and scripts[201]["yielded"])
        self.assertEqual((scripts[200]["room"], scripts[201]["room"]), (1, 1))

        host.tick()
        second = host.engine.inspect_state()
        scripts = {item["resource"]: item for item in second["scripts"]}
        self.assertFalse(scripts["room.1/LSCR.200"]["active"])
        self.assertFalse(scripts["room.1/LSCR.201"]["active"])
        self.assertEqual(scripts["room.1/LSCR.201"]["locals"][0], 11)

    def test_room_entry_outer_context_survives_immediate_child_stop_and_yield(self) -> None:
        entry = bytes((
            0x1A, 10, 0, 0x10, 0x10,
            0x0A, 200, 0xFF,
            0x1A, 11, 0, 0x11, 0x11,
            0x80,
            0x1A, 12, 0, 0x12, 0x12,
            0x00,
        ))
        child = bytes((0x1A, 0, 0x40, 0x20, 0x20, 0x00))
        room = raw_room(entry=entry, exit=b"\x00", locals=((200, child),))
        resources = MemoryResourceProvider({
            "script.boot": bytes((0x72, 1, 0x80, 0x00)),
            "room.1": room,
            "cooked.room.1": cooked(1, room),
            "cooked.rooms.manifest": manifest(),
        })
        profile = load_profile(PROFILE)
        host = EngineHost(
            profile, default_registry(),
            services=HostServices.create(profile, resources=resources),
        )
        host.boot()
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(first["variables"]["10"], 0x1010)
        self.assertEqual(first["variables"]["11"], 0x1111)
        self.assertNotIn("12", first["variables"])
        child_slot = next(item for item in first["scripts"] if item["resource"] == "room.1/LSCR.200")
        self.assertFalse(child_slot["active"])
        self.assertEqual(child_slot["locals"][0], 0x2020)

        host.tick()
        second = host.engine.inspect_state()
        self.assertEqual(second["variables"]["12"], 0x1212)
        entry_slot = next(item for item in second["scripts"] if item["script_kind"] == "ENCD")
        self.assertFalse(entry_slot["active"])

    def test_host_rejects_new_room_before_exit_or_registry_mutation(self) -> None:
        room1 = raw_room(entry=b"\x00", exit=bytes((0x46, 12, 0, 0x00)), locals=())
        room2 = raw_room(entry=b"\x00", exit=b"\x00", locals=())
        damaged = bytearray(cooked(2, room2))
        damaged[-40] ^= 1
        resources = MemoryResourceProvider({
            "script.boot": bytes((0x72, 1, 0x80, 0x72, 2, 0x00)),
            "room.1": room1, "room.2": room2,
            "cooked.room.1": cooked(1, room1),
            "cooked.room.2": bytes(damaged),
            "cooked.rooms.manifest": manifest(),
        })
        profile = load_profile(PROFILE)
        host = EngineHost(profile, default_registry(), services=HostServices.create(
            profile, resources=resources,
        ))
        host.boot()
        host.tick()
        before = host.engine.inspect_state()
        with self.assertRaisesRegex(EngineExecutionError, "whole-record SHA-256 differs"):
            host.tick()
        after = host.engine.inspect_state()
        self.assertEqual(after["room"], 1)
        self.assertEqual(after["variables"].get("12", 0), 0)
        self.assertEqual(after["room_resource"]["record_sha256"],
                         before["room_resource"]["record_sha256"])


if __name__ == "__main__":
    unittest.main()
