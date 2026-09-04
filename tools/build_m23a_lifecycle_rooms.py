#!/usr/bin/env python3
"""Build copyright-free cooked rooms for the generic M23A lifecycle oracle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from same.engines.scumm_v5.cooked_room import ScriptChunkInput, decode_cooked_room, encode_cooked_room
from same.profile import load_profile


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def chunk(tag: bytes, payload: bytes) -> bytes:
    return tag + struct.pack(">I", len(payload) + 8) + payload


def room(entry: bytes, exit: bytes, locals_: tuple[tuple[int, bytes], ...]) -> bytes:
    palette = bytes(value for index in range(256) for value in (index, index, index))
    strip = bytes((1,)) + bytes(range(16))
    smap = chunk(b"SMAP", struct.pack("<I", 12) + strip)
    walkboxes = (
        struct.pack("<hhhhhhhhBBH", *([-32000] * 8), 0, 0, 255),
        struct.pack("<hhhhhhhhBBH", 0, 0, 7, 0, 7, 1, 0, 1, 0, 0, 255),
    )
    return b"".join((
        chunk(b"RMHD", struct.pack("<HHH", 8, 2, 0)),
        chunk(b"TRNS", struct.pack("<H", 255)), chunk(b"CLUT", palette),
        chunk(b"BOXD", struct.pack("<H", 2) + b"".join(walkboxes)),
        chunk(b"BOXM", b"\x00\x00\x00\xff\x01\x01\x01\xff"),
        chunk(b"RMIM", chunk(b"RMIH", b"\x00\x00") + chunk(b"IM00", smap)),
        chunk(b"ENCD", entry), chunk(b"EXCD", exit),
        *(chunk(b"LSCR", bytes((number,)) + program) for number, program in locals_),
    ))


def inputs(number: int, payload: bytes) -> tuple[ScriptChunkInput, ...]:
    result = []
    offset = 0
    while offset < len(payload):
        tag = payload[offset:offset + 4].decode("ascii")
        size = int.from_bytes(payload[offset + 4:offset + 8], "big")
        if tag in {"ENCD", "EXCD", "LSCR"}:
            if tag == "LSCR":
                script_number, body_offset = payload[offset + 8], 9
                identity = f"room.{number}/LSCR.{script_number}"
            else:
                script_number, body_offset = (10002 if tag == "ENCD" else 10001), 8
                identity = f"room.{number}/{tag}"
            result.append(ScriptChunkInput(
                tag, script_number, identity, offset, body_offset, size - body_offset,
            ))
        offset += size
    return tuple(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    profile = load_profile(PROFILE, verify_resources=False)
    profile_hash = sha(PROFILE.read_bytes())
    game_hash = sha(f"{profile.engine_id}\0{profile.game_id}\0{profile.variant}".encode())
    source_hashes = {name: sha(f"M23A copyright-free {name}".encode())
                     for name in ("archive", "index", "data")}
    # ENCD starts a room-local script. It remains yielded and owned by room 1
    # until room 2's transition retires it after EXCD.
    rooms = {
        1: room(
            bytes((0x1A, 10, 0, 1, 0, 0x0A, 200, 0xFF, 0x00)),
            bytes((0x46, 12, 0, 0x00)),
            ((200, bytes((0x46, 11, 0, 0x80, 0x18, 0xFC, 0xFF))),),
        ),
        2: room(bytes((0x46, 13, 0, 0x00)), b"\x00", ((201, b"\x00"),)),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for number, payload in rooms.items():
        encoded = encode_cooked_room(
            payload, room=number, flags=0, original_room_file_offset=number * 0x10000,
            profile_sha256=profile_hash, game_identity_sha256=game_hash,
            archive_sha256=source_hashes["archive"], index_sha256=source_hashes["index"],
            data_sha256=source_hashes["data"], scripts=inputs(number, payload),
        )
        decoded = decode_cooked_room(encoded, expected_room=number)
        path = args.output_dir / f"room-{number}.sc5c"
        path.write_bytes(encoded)
        records.append({
            "room": number, "resource_key": f"room.{number}", "output": path.name,
            "registration_only": False, "record_length": len(encoded),
            "record_sha256": sha(encoded), "compact_checksum": decoded.compact_checksum,
            "scripts": [{
                "identity": item.identity, "kind": item.kind, "number": item.number,
                "program_length": len(item.program), "sha256": item.sha256,
                **item.runtime_map(0),
            } for item in decoded.scripts],
        })
    manifest = {
        "schema": "same_scumm_v5_cooked_rooms_v1",
        "num_global_scripts": 200,
        "profile": {"path": str(PROFILE), "sha256": profile_hash,
                    "engine": profile.engine_id, "game": profile.game_id,
                    "variant": profile.variant, "identity_sha256": game_hash},
        "source": {f"{name}_sha256": value for name, value in source_hashes.items()},
        "copyright": "generated copyright-free lifecycle fixture",
        "records": records,
    }
    path = args.output_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"manifest": str(path), "sha256": sha(path.read_bytes())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
