#!/usr/bin/env python3
"""Build a copyright-free SC5VIS record for target lifecycle conformance."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from same.engines.scumm_v5.room_visual import encode_room_visual


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    width, height, pitch, room = 320, 224, 328, 1
    pixels = bytearray([0xCC] * (pitch * height))
    for y in range(height):
        for x in range(width):
            pixels[y * pitch + x] = (
                x * 13 + y * 29 + (x // 8) * 47 + (y // 8) * 71
            ) & 0xFF
    palette = bytes(
        component
        for index in range(256)
        for component in ((index * 3) & 0xFF, (index * 5) & 0xFF, (index * 11) & 0xFF)
    )
    source_hashes = [sha(name.encode("ascii")) for name in
                     ("same-fixture-archive", "same-fixture-index", "same-fixture-data",
                      "same-fixture-room-1")]
    record = encode_room_visual(
        room=room, width=width, height=height, pitch=pitch,
        palette=palette, pixels=bytes(pixels), archive_sha256=source_hashes[0],
        index_sha256=source_hashes[1], data_sha256=source_hashes[2],
        room_sha256=source_hashes[3],
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "room-1.sc5v"
    output.write_bytes(record)
    visual = {
        "schema": "same_scumm_v5_room_visual_v1", "output": output.name,
        "record_length": len(record), "record_sha256": sha(record),
        "pixel_format": "indexed8", "palette_format": "rgb8",
        "width": width, "height": height, "pitch": pitch, "palette_entries": 256,
        "decoded_pixels_sha256": sha(bytes(pixels)),
        "decoded_palette_sha256": sha(palette),
    }
    manifest = {
        "schema": "same_scumm_v5_cooked_rooms_v1",
        "source": {"kind": "copyright-free deterministic Phase-6E fixture"},
        "records": [{"room": room, "visual": visual}],
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"manifest": str(manifest_path), "record_sha256": sha(record)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
