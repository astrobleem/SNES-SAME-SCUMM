#!/usr/bin/env python3
"""Cook one source-backed SCUMM room-object image for the visual fixture.

This is deliberately a small delivery helper, not a second object renderer:
the source OBIM/SMAP bytes are decoded by the existing host room decoder
conventions and the target receives indexed pixels through the normal surface
compositor.  Runtime state decides whether the authored object image is
present.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path
import zipfile

from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.engines.scumm_v5.room import _chunks, _decode_strip, _one
from same.profile import load_profile
from same.resources import MemoryResourceProvider


def source_bytes(archive: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        for prefix in ("ATLANTIS", "FATEDEMO"):
            index = f"{prefix}/{prefix}.000"
            data = f"{prefix}/{prefix}.001"
            if index in names and data in names:
                return {"game.index": bundle.read(index),
                        "game.data": bundle.read(data)}
    raise RuntimeError(f"{archive}: no supported SCUMM index/data pair")


def cook(archive: Path, profile: Path, room: int, object_id: int) -> tuple[int, int, bytes]:
    policy = parse_game_policy(load_profile(profile, verify_resources=False))
    if policy is None:
        raise RuntimeError("profile has no SCUMM v5 resource policy")
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider(source_bytes(archive)), policy)
    room_data = provider.read(f"room.{room}")
    top = _chunks(room_data, owner=f"room.{room}")
    objects = []
    images = [chunk for chunk in top if chunk.tag == b"OBIM"]
    for chunk in top:
        if chunk.tag != b"OBCD":
            continue
        children = _chunks(chunk.payload, owner="OBCD")
        cdhd = _one(children, b"CDHD", owner="OBCD")
        objects.append(struct.unpack_from("<H", cdhd.payload)[0])
    if object_id not in objects:
        raise RuntimeError(f"room {room} has no object {object_id}")
    index = objects.index(object_id)
    image = _one(_chunks(images[index].payload, owner="OBIM"), b"IM01", owner="OBIM")
    imhd = _one(_chunks(images[index].payload, owner="OBIM"), b"IMHD", owner="OBIM")
    width, height = struct.unpack_from("<HH", imhd.payload, 12)
    if width % 8 or width > 64 or height > 64:
        raise RuntimeError(f"unsupported object image dimensions {width}x{height}")
    smap = _one(_chunks(image.payload, owner="IM01"), b"SMAP", owner="IM01")
    strip_count = width // 8
    starts = struct.unpack_from("<" + "I" * strip_count, smap.raw, 8)
    pixels = bytearray(width * height)
    for strip, start in enumerate(starts):
        end = starts[strip + 1] if strip + 1 < strip_count else len(smap.raw)
        decoded, _ = _decode_strip(smap.raw[start:end], height=height,
                                    owner=f"object {object_id} strip {strip}")
        for y in range(height):
            pixels[y * width + strip * 8:y * width + strip * 8 + 8] = \
                decoded[y * 8:(y + 1) * 8]
    return width, height, bytes(pixels)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--room", type=int, required=True)
    parser.add_argument("--object", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bank", type=lambda value: int(value, 0), default=97)
    args = parser.parse_args()
    width, height, pixels = cook(args.archive, args.profile, args.room, args.object)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    binary = args.output.with_suffix(".bin")
    binary.write_bytes(pixels)
    args.output.write_text(
        "; Generated from source-backed SCUMM OBIM/SMAP bytes.\n"
        "; tools/generate_snes_scumm_object_sprite.py.\n"
        f"SCUMM_V5_OBJECT_SPRITE_WIDTH = ${width:04X}\n"
        f"SCUMM_V5_OBJECT_SPRITE_HEIGHT = ${height:04X}\n"
        f"SCUMM_V5_OBJECT_SPRITE_OBJECT = ${args.object:04X}\n"
        f".bank {args.bank}\n.org $8000\n"
        "ScummV5_ObjectSprite_Data:\n"
        f'    .incbin "{binary.resolve().as_posix()}"\n',
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
