#!/usr/bin/env python3
"""Emit source-bound M23A command inspection from complete cooked ENCDs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from same.engines.scumm_v5.cooked_room import decode_cooked_room


def command(script, offset: int, length: int, decoded: str) -> dict[str, object]:
    raw = script.program[offset:offset + length]
    if len(raw) != length:
        raise RuntimeError(f"{script.identity} +0x{offset:04X} is truncated")
    source = script.runtime_map(offset)
    return {
        "script": script.identity,
        "script_relative_offset": offset,
        "bytes": raw.hex(),
        "decoded": decoded,
        **source,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    records = {}
    for item in manifest["records"]:
        path = args.manifest.parent / item["output"]
        record = decode_cooked_room(path.read_bytes(), expected_room=item["room"])
        records[item["room"]] = record
    room49, room63 = records[49].entry, records[63].entry
    expected = {
        "room49": [
            (room49, 0x004F, 8, "soundKludge [8, 80] (queue start sound 80)"),
            (room49, 0x0057, 14, "soundKludge [0x010C, 80, 0, 14] (queue hook 14)"),
            (room49, 0x0065, 5, "soundKludge [-1] (single flush of both queued commands)"),
        ],
        "room63": [
            (room63, 0x00A7, 14, "soundKludge [0x010C, 80, 0, 8] (queue hook 8)"),
            (room63, 0x00B5, 3, "startScript 151, no arguments"),
            (room63, 0x00B8, 4, "var[0] = isSoundRunning(82)"),
            (room63, 0x00BC, 5, "if var[0] != 0, do not take +0x001D skip to ENCD +0x00DE"),
            (room63, 0x00C1, 5, "soundKludge [0x0110] (intervening queued command)"),
            (room63, 0x00C6, 5, "soundKludge [-1] (eventual flush on the sound-82-running path)"),
        ],
    }
    byte_oracles = {
        (49, 0x004F): "4c010800015000ff",
        (49, 0x0057): "4c010c01015000010000010e00ff",
        (49, 0x0065): "4c01ffffff",
        (63, 0x00A7): "4c010c01015000010000010800ff",
        (63, 0x00B5): "0a97ff",
        (63, 0x00B8): "7c000052",
        (63, 0x00BC): "a800001d00",
        (63, 0x00C1): "4c011001ff",
        (63, 0x00C6): "4c01ffffff",
    }
    result = {
        "schema": "same_scumm_v5_m23a_inspection_v1",
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "rooms": {},
        "claims": {
            "room49_batch": "start 80 and hook 14 are queued, then processed by one flush",
            "room63_batch": "hook 8 is queued; startScript 151, isSoundRunning 82, a conditional, and command 0x0110 intervene before the path's later flush",
            "execution": "inspection/provenance only; neither authentic ENCD was dispatched",
        },
    }
    for name, items in expected.items():
        room = 49 if name == "room49" else 63
        encoded = [command(*item) for item in items]
        for item in encoded:
            wanted = byte_oracles[(room, item["script_relative_offset"])]
            if item["bytes"] != wanted:
                raise RuntimeError(f"{name} +0x{item['script_relative_offset']:04X} differs")
        result["rooms"][str(room)] = {
            "room_sha256": records[room].room_sha256,
            "entry_sha256": records[room].entry.sha256,
            "commands": encoded,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
