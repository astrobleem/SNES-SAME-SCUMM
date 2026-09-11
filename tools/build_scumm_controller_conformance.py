#!/usr/bin/env python3
"""Build one original, self-contained cooked room for controller conformance."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from same.engines.scumm_v5.cooked_room import ScriptChunkInput, decode_cooked_room, encode_cooked_room
from same.engines.scumm_v5.room_visual import encode_room_visual, decode_room_visual


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/scumm_v5_controller_conformance.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def chunk(tag: bytes, payload: bytes) -> bytes:
    return tag + struct.pack(">I", len(payload) + 8) + payload


def object_payload() -> bytes:
    # One original object: CDHD bounds (48, 56)-(104, 96), OBNA, and verb 3.
    cdhd = struct.pack("<HBBBBBBhhB", 7, 1, 1, 7, 5, 0, 0, 48, 56, 0)
    # The ordinary action has one observable fixture-local effect, then STOPs
    # normally.  Completion is still determined by sentence/script retirement,
    # never by this variable.
    verb_program = bytes.fromhex("26 05 00 01 01 00")
    verb = bytes((3, 12, 0, 0)) + verb_program
    return chunk(b"CDHD", cdhd) + chunk(b"OBNA", b"test console") + chunk(b"VERB", verb)


def room() -> bytes:
    palette = bytes(value for index in range(256) for value in (index, index, index))
    smap = chunk(b"SMAP", struct.pack("<I", 12) + bytes((1,)) + bytes(range(16)))
    walkbox = struct.pack("<hhhhhhhhBBH", 0, 0, 255, 0, 255, 127, 0, 127, 0, 0, 255)
    verb_ops = bytes((0x7A, 3, 0x09, 0x02)) + b"Push\0" + bytes((0x06, 0xFF, 0x80))
    entry = bytes((0x0A, 200, 0xFF, 0x00))
    # Set VAR_SENTENCE_SCRIPT=2 through authored SetVarRange.  This is the
    # normal SCUMM incoming-state contract consumed by SentenceProcess.
    sentence_script = bytes((0x26, 0x21, 0x00, 0x01, 0x02))
    local_script = bytes((200,)) + sentence_script + verb_ops + b"\0"
    return b"".join((
        chunk(b"RMHD", struct.pack("<HHH", 8, 2, 1)),
        chunk(b"TRNS", struct.pack("<H", 255)), chunk(b"CLUT", palette),
        chunk(b"BOXD", struct.pack("<H", 1) + walkbox), chunk(b"BOXM", b"\xff"),
        chunk(b"RMIM", chunk(b"RMIH", b"\0\0") + chunk(b"IM00", smap)),
        chunk(b"OBCD", object_payload()), chunk(b"ENCD", entry), chunk(b"EXCD", b"\0"),
        *(() if not local_script else (chunk(b"LSCR", local_script),)),
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
    # The ordinary sentence dispatcher resolves VAR_SENTENCE_SCRIPT through
    # the generated global-script directory.  Keep that incoming state
    # authored by the synthetic startup script, rather than relying on an
    # M23B/Fate boot personality or a validator WRAM write.
    sentence_launcher = bytes.fromhex(
        "f7 01 40 00 40 81 02 40 81 00 40 ff 00"
    )
    sentence_output = args.output_dir / "script-2.scrp"
    sentence_output.write_bytes(sentence_launcher)
    visual_dir = args.output_dir / "visual"
    visual_dir.mkdir(exist_ok=True)
    palette = bytes(value for index in range(256) for value in (index, index, index))
    pixels = bytes((1 if (x // 8 + y // 8) % 2 else 0) for y in range(224) for x in range(256))
    visual = encode_room_visual(
        room=1, width=256, height=224, pitch=256, palette=palette, pixels=pixels,
        archive_sha256=synthetic["archive"], index_sha256=synthetic["index"],
        data_sha256=synthetic["data"], room_sha256=sha(encoded),
    )
    visual_path = visual_dir / "room-1.sc5v"
    visual_path.write_bytes(visual)
    decoded_visual = decode_room_visual(visual, expected_room=1)
    generated_dir = ROOT / "runtime/snes/generated"
    # The source includes these names behind the controller-fixture condition;
    # keep the static assembler/linter include graph complete without shipping
    # or generating any actor/object sprite payload for this personality.
    for name in ("scumm_v5_actor_sprite.inc.pasm", "scumm_v5_object_sprite.inc.pasm"):
        (generated_dir / name).write_text(
            "; Empty in standalone controller conformance; fixture-only.\n",
            encoding="utf-8",
        )
    manifest = {
        "schema": "same_scumm_v5_cooked_rooms_v1", "num_global_scripts": 200,
        "profile": {"path": str(PROFILE), "sha256": profile_hash, "engine": "scumm_v5", "game": "same-scumm-controller", "variant": "copyright-free-synthetic", "identity_sha256": game_hash},
        "source": {f"{name}_sha256": value for name, value in synthetic.items()},
        "copyright": "original copyright-free controller conformance fixture",
        "global_scripts": [{
            "number": 2, "resource_key": "script.2", "output": sentence_output.name,
            "length": len(sentence_launcher), "sha256": sha(sentence_launcher),
            "source": "original synthetic sentence launcher",
        }],
        "records": [{"room": 1, "resource_key": "room.1", "output": output.name, "registration_only": False, "record_length": len(encoded), "record_sha256": sha(encoded), "compact_checksum": decoded.compact_checksum,
                     "visual": {"output": str(Path("visual") / visual_path.name), "record_sha256": decoded_visual.record_sha256},
                     "scripts": [{"identity": item.identity, "kind": item.kind, "number": item.number, "program_length": len(item.program), "sha256": item.sha256} for item in decoded.scripts]}],
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"manifest": str(manifest_path), "room_sha256": sha(encoded)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
