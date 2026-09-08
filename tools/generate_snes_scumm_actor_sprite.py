#!/usr/bin/env python3
"""Cook a small source-backed SCUMM v5 actor pose set for the SNES surface.

The host costume decoder remains the format oracle.  The target receives
indexed pixels and a compact frame table; it does not decode copyrighted
costume RLE at runtime or bypass the video-surface service.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import zipfile

from same.engines.scumm_v5.costume import ScummV5Costume
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.profile import load_profile
from same.resources import MemoryResourceProvider


def source_bytes(archive: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        pairs = (
            ("ATLANTIS/ATLANTIS.000", "ATLANTIS/ATLANTIS.001"),
            ("FATEDEMO/PLAYFATE.000", "FATEDEMO/PLAYFATE.001"),
        )
        for index_name, data_name in pairs:
            if index_name in names and data_name in names:
                return {"game.index": bundle.read(index_name),
                        "game.data": bundle.read(data_name)}
    raise RuntimeError(f"{archive}: no supported SCUMM v5 index/data pair")


def cook_pose(
    costume: ScummV5Costume,
    frame: int,
    *,
    width: int,
    height: int,
    facing: int = 180,
) -> bytes:
    pose = costume.decode_pose(frame, facing=facing, step=0)
    pixels = bytearray(width * height)
    for cel in pose.cels:
        # Costume BYLE data is traversed in source column-major order.  Keep
        # the same directional placement contract as ScummV5RoomRenderer:
        # facing-dependent poses may paint from right to left around the
        # actor anchor.  The old cooker flattened the cel row-major and
        # therefore emitted a transposed/striped actor while its self-check
        # still compared two copies of the same wrong composition.
        origin_x = width // 2 + cel.relative_x if pose.draw_to_right else width // 2 - cel.relative_x
        origin_y = height - 9 + cel.relative_y
        x_step = 1 if pose.draw_to_right else -1
        for y in range(cel.height):
            target_y = origin_y + y
            if not 0 <= target_y < height:
                continue
            for x in range(cel.width):
                target_x = origin_x + x_step * x
                if not 0 <= target_x < width:
                    continue
                value = cel.pixels[x * cel.height + y]
                if value:
                    pixels[target_y * width + target_x] = costume.palette[value]
    return bytes(pixels)


def rows(data: bytes, width: int) -> str:
    return "\n".join(
        "    .byte " + ",".join(f"${value:02X}" for value in data[offset:offset + width])
        for offset in range(0, len(data), width)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--costume", type=int, default=2)
    parser.add_argument("--facing", type=int, default=180)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bank", type=lambda value: int(value, 0), default=95)
    args = parser.parse_args()

    profile = load_profile(args.profile, verify_resources=False)
    policy = parse_game_policy(profile)
    if policy is None:
        raise RuntimeError("profile has no SCUMM v5 resource policy")
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider(source_bytes(args.archive)), policy
    )
    key = policy.costume_key_template.format(costume=args.costume)
    costume = ScummV5Costume(provider.read(key), key=key)
    width, height = 32, 64
    frames = tuple(cook_pose(costume, frame, width=width, height=height,
                             facing=args.facing)
                   for frame in (1, 2, 3, 4))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    binary = args.output.with_suffix(".bin")
    binary.write_bytes(b"".join(frames))
    lines = [
        "; Generated from the source-backed SCUMM costume by",
        "; tools/generate_snes_scumm_actor_sprite.py.",
        f"SCUMM_V5_ACTOR_SPRITE_WIDTH = ${width:04X}",
        f"SCUMM_V5_ACTOR_SPRITE_HEIGHT = ${height:04X}",
        f"SCUMM_V5_ACTOR_SPRITE_FRAME_COUNT = ${len(frames):02X}",
        f"SCUMM_V5_ACTOR_SPRITE_COSTUME = ${args.costume:02X}",
        f"SCUMM_V5_ACTOR_SPRITE_FACING = ${args.facing:04X}",
        f"SCUMM_V5_ACTOR_SPRITE_BANK = ${args.bank:02X}",
        f".bank {args.bank}", ".org $8000",
        "ScummV5_ActorSprite_Data:",
        f'    .incbin "{binary.resolve()}"',
    ]
    args.output.write_text("\n".join(lines) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
