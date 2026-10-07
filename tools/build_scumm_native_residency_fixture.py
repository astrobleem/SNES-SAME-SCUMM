#!/usr/bin/env python3
"""Build a copyright-free four-room corpus for native selector residency."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from same.engines.scumm_v5.room_compiler import compile_room_payload


GLOBAL_COUNT = 254
SOURCE_GLOBALS = 193
ROOM_COUNT = 4


def chunk(tag: bytes, payload: bytes) -> bytes:
    return tag + struct.pack(">I", len(payload) + 8) + payload


def object_chunks() -> tuple[bytes, bytes]:
    """One two-verb carrier plus one passive data-only object."""
    def cdhd(object_id: int) -> bytes:
        return chunk(b"CDHD", struct.pack(
            "<HBBBBBBhhB", object_id, 1, 1, 1, 1, 0, 0, 1, 1, 0,
        ))

    # The source entry offsets are OBCD-relative. Both verb bodies write an
    # observable marker before stopping, proving dispatch through one shared
    # object carrier rather than merely counting the metadata record.
    verbs = bytes((
        3, 15, 0, 10, 21, 0, 0,
        0x1A, 9, 0, 3, 0, 0xA0,
        0x1A, 10, 0, 10, 0, 0xA0,
    ))
    carrier = chunk(b"OBCD", cdhd(70) + chunk(b"VERB", verbs))
    passive = chunk(b"OBCD", cdhd(71))
    return carrier, passive


def raw_room(room: int) -> bytes:
    palette = bytes(value for index in range(256) for value in (index, index, index))
    smap = chunk(b"SMAP", struct.pack("<I", 12) + bytes((1,)) + bytes(range(16)))
    rmim = chunk(b"RMIM", chunk(b"RMIH", b"\0\0") + chunk(b"IM00", smap))
    walkbox = struct.pack(
        "<hhhhhhhhBBH", 0, 0, 255, 0, 255, 127, 0, 127, 0, 0, 255,
    )
    if room == 1:
        entry = bytes((
            0x1A, 24, 0, 1, 0,
            0x37, 70, 0, 3, 0xFF,   # StartObject(70, verb=3)
            0x37, 70, 0, 10, 0xFF,  # same object carrier, verb=10
            0x72, 2, 0xA0,
        ))
    elif room < ROOM_COUNT:
        entry = bytes((0x1A, 24, 0, room, 0, 0x72, room + 1, 0xA0))
    else:
        # Start the pressure/churn caller independently of GlobalScript(1).
        # Its initial yield window lets the persistent global retire before
        # the pool needs to recycle its first selector.
        entry = bytes((0x1A, 24, 0, room, 0, 0x0A, 4, 0xFF, 0xA0))
    objects = object_chunks() if room == 1 else ()
    return b"".join((
        chunk(b"RMHD", struct.pack("<HHH", 8, 2, len(objects))),
        chunk(b"CLUT", palette), rmim,
        chunk(b"BOXD", struct.pack("<H", 1) + walkbox),
        chunk(b"BOXM", b"\xff"), *objects,
        chunk(b"ENCD", entry), chunk(b"EXCD", b"\xA0"),
        chunk(b"LSCR", bytes((GLOBAL_COUNT, 0xA0))),
    ))


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    ids = {
        "profile": sha(b"synthetic-resident-profile-v1"),
        "game": sha(b"synthetic-resident-game-v1"),
        "archive": sha(b"synthetic-resident-archive-v1"),
        "index": sha(b"synthetic-resident-index-v1"),
        "data": sha(b"synthetic-resident-data-v1"),
    }
    records = []
    for room in range(1, ROOM_COUNT + 1):
        payload = raw_room(room)
        compiled = compile_room_payload(
            payload, room_number=room,
            game_name="copyright-free-native-residency-fixture",
            resource_key=f"room.{room}", source_member=f"fixture/room-{room}.lflf",
            source_container_offset=0, original_room_file_offset=room * 0x10000,
            profile_sha256=ids["profile"], game_identity_sha256=ids["game"],
            archive_sha256=ids["archive"], index_sha256=ids["index"],
            data_sha256=ids["data"], global_script_count=GLOBAL_COUNT,
        )
        name = f"room-{room}.sc5c"
        (out / name).write_bytes(compiled.cooked_record)
        records.append({**compiled.record_manifest, "output": name})

    # Keep the room-transition route bounded while exercising dynamic global
    # resolution. A separate candidate-probe global selects two distant
    # members from the >178-global universe; no candidate universe is eagerly
    # bound merely because it exists.
    global_one_code = bytearray((0x80,))  # retain a live caller activation
    for target in (2, 3):
        global_one_code.extend((
            0x1A, 7, 0, target, 0,      # variable 7 = selected script
            0x8A, 7, 0, 0xFF,            # dynamic StartScript(variable[7])
            0x80,                         # caller yields to the child
        ))
    # The profile's ordinary title START input enters room 1. Keep this global
    # yielded over the room-entry chain so its selector pin is tested without
    # making the same activation the transition requester.
    global_one_code.extend((0x80,) * 40)
    global_one_code.extend((
        0x1A, 5, 0, 1, 0,
        0x1A, 15, 0, 1, 0,
        0xA0,
    ))
    global_one = bytes(global_one_code)
    global_two = bytes((
        0x80,
        0x1A, 6, 0, 2, 0,       # marker: yielded child resumed and completed
        0xA0,
    ))
    global_three = bytes((
        0x1A, 8, 0, 3, 0,       # marker: second dynamic target executed
        0xA0,
    ))
    global_four_code = bytearray()
    # Allow GlobalScript(1), which has yielded across the room chain, to
    # finish before selector pressure reaches its first evictable binding.
    global_four_code.extend((0x80,) * 40)
    # Exercise actual reuse instead of assuming the allocator should evict a
    # still-useful binding while free selectors remain.  These children are
    # serialized through one caller, keeping live activations bounded while
    # the candidate universe exceeds the 178-selector resident pool.
    for target in range(5, 191):
        global_four_code.extend((
            0x1A, 7, 0, target, 0,
            0x8A, 7, 0, 0xFF,
            0x80,
        ))
    global_four_code.extend((
        0x1A, 7, 0, 191, 0,
        0x8A, 7, 0, 0xFF,
        0x80,
        0x1A, 7, 0, 192, 0,
        0x8A, 7, 0, 0xFF,
        0x80,
        0x1A, 20, 0, 4, 0,
        0xA0,
    ))
    global_four = bytes(global_four_code)
    global_191 = bytes((0x1A, 21, 0, 5, 0, 0xA0))
    global_192 = bytes((0x1A, 22, 0, 6, 0, 0xA0))
    global_193 = bytes((
        0x1A, 7, 0, 191, 0, 0x8A, 7, 0, 0xFF, 0x80,
        0x1A, 7, 0, 192, 0, 0x8A, 7, 0, 0xFF, 0x80,
        0x1A, 23, 0, 7, 0, 0xA0,
    ))
    globals_ = [(1, global_one), (2, global_two), (3, global_three), (4, global_four),
                (191, global_191), (192, global_192), (193, global_193)] + [
        (number, bytes((0xA0,))) for number in range(5, 191)
    ]
    for number, program in globals_:
        (out / f"global-{number}.bin").write_bytes(program)
    manifest = {
        "schema": "same_scumm_v5_cooked_rooms_v1",
        "num_global_scripts": GLOBAL_COUNT,
        "copyright": "Copyright-free generated structural/runtime fixture.",
        "records": records,
        "global_scripts": [
            {"number": number, "output": f"global-{number}.bin", "length": len(program)}
            for number, program in globals_
        ],
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "manifest": str(manifest_path), "rooms": len(records),
        "room_local_units": len(records),
        "global_units": len(globals_), "object_carriers": 1, "passive_objects": 1,
        "program_units_lower_bound": len(records) * 3 + len(globals_) + 1,
        "boot_global": 1,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
