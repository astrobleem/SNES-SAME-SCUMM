#!/usr/bin/env python3
"""Build one original, self-contained cooked room for controller conformance."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from same.engines.scumm_v5.cooked_room import ScriptChunkInput, decode_cooked_room, encode_cooked_room


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/scumm_v5_controller_conformance.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def chunk(tag: bytes, payload: bytes) -> bytes:
    return tag + struct.pack(">I", len(payload) + 8) + payload


def object_payload() -> bytes:
    # One original object: CDHD bounds (48, 56)-(104, 96), OBNA, and verb 3.
    cdhd = struct.pack("<HBBBBBBhhB", 7, 1, 1, 7, 5, 0, 0, 48, 56, 0)
    verb_program = bytes((0x00,))
    verb = bytes((3, 12, 0, 0)) + verb_program
    return chunk(b"CDHD", cdhd) + chunk(b"OBNA", b"test console") + chunk(b"VERB", verb)


def room() -> bytes:
    palette = bytes(value for index in range(256) for value in (index, index, index))
    smap = chunk(b"SMAP", struct.pack("<I", 12) + bytes((1,)) + bytes(range(16)))
    walkbox = struct.pack("<hhhhhhhhBBH", 0, 0, 255, 0, 255, 127, 0, 127, 0, 0, 255)
    entry = bytes((0x0A, 200, 0xFF, 0x00))
    verb_ops = bytes((0x7A, 3, 0x09, 0x02)) + b"Push\0" + bytes((0x06, 0xFF, 0x80))
    return b"".join((
        chunk(b"RMHD", struct.pack("<HHH", 8, 2, 1)),
        chunk(b"TRNS", struct.pack("<H", 255)), chunk(b"CLUT", palette),
        chunk(b"BOXD", struct.pack("<H", 1) + walkbox), chunk(b"BOXM", b"\xff"),
        chunk(b"RMIM", chunk(b"RMIH", b"\0\0") + chunk(b"IM00", smap)),
        chunk(b"OBCD", object_payload()), chunk(b"ENCD", entry), chunk(b"EXCD", b"\0"),
        chunk(b"LSCR", bytes((200,)) + verb_ops + b"\0"),
    ))


def scripts(payload: bytes) -> tuple[ScriptChunkInput, ...]:
    result = []
    offset = 0
    while offset < len(payload):
        tag = payload[offset:offset + 4]
        size = int.from_bytes(payload[offset + 4:offset + 8], "big")
        if tag in {b"ENCD", b"EXCD", b"LSCR"}:
            number = payload[offset + 8] if tag == b"LSCR" else (10002 if tag == b"ENCD" else 10001)
            body = 9 if tag == b"LSCR" else 8
            identity = f"room.1/LSCR.{number}" if tag == b"LSCR" else f"room.1/{tag.decode()}"
            result.append(ScriptChunkInput(tag.decode(), number, identity, offset, body, size - body))
        offset += size
    return tuple(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload = room()
    profile_hash = sha(PROFILE.read_bytes())
    game_hash = sha(b"same-scumm-controller\0copyright-free-synthetic")
    synthetic = {name: sha(f"controller-conformance-{name}".encode()) for name in ("archive", "index", "data")}
    encoded = encode_cooked_room(
        payload, room=1, flags=0, original_room_file_offset=0x10000,
        profile_sha256=profile_hash, game_identity_sha256=game_hash,
        archive_sha256=synthetic["archive"], index_sha256=synthetic["index"],
        data_sha256=synthetic["data"], scripts=scripts(payload),
    )
    decoded = decode_cooked_room(encoded, expected_room=1)
    output = args.output_dir / "room-1.sc5c"
    output.write_bytes(encoded)
    manifest = {
        "schema": "same_scumm_v5_cooked_rooms_v1", "num_global_scripts": 201,
        "profile": {"path": str(PROFILE), "sha256": profile_hash, "engine": "scumm_v5", "game": "same-scumm-controller", "variant": "copyright-free-synthetic", "identity_sha256": game_hash},
        "source": {f"{name}_sha256": value for name, value in synthetic.items()},
        "copyright": "original copyright-free controller conformance fixture",
        "records": [{"room": 1, "resource_key": "room.1", "output": output.name, "registration_only": False, "record_length": len(encoded), "record_sha256": sha(encoded), "compact_checksum": decoded.compact_checksum,
                     "scripts": [{"identity": item.identity, "kind": item.kind, "number": item.number, "program_length": len(item.program), "sha256": item.sha256} for item in decoded.scripts]}],
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"manifest": str(manifest_path), "room_sha256": sha(encoded)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
