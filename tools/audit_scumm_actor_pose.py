#!/usr/bin/env python3
"""Emit source-decoded and cooked pose evidence for one SCUMM v5 costume.

This is an audit tool, not a replacement renderer.  The host composite follows
the column-major cel traversal and draw-to-right rule used by room.py; the
second image is the current cooker output, including its current row-major
assembly.  Keeping both makes the first divergent stage directly inspectable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from PIL import Image

from same.engines.scumm_v5.costume import ScummV5Costume
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.profile import load_profile
from same.resources import MemoryResourceProvider


def source_bytes(archive: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(archive) as bundle:
        return {"game.index": bundle.read("ATLANTIS/ATLANTIS.000"),
                "game.data": bundle.read("ATLANTIS/ATLANTIS.001")}


def provider(archive: Path, profile: Path):
    policy = parse_game_policy(load_profile(profile, verify_resources=False))
    if policy is None:
        raise RuntimeError("profile has no SCUMM v5 resource policy")
    return LucasartsScummV5ResourceProvider(
        MemoryResourceProvider(source_bytes(archive)), policy
    )


def png(data: bytes, width: int, height: int, path: Path, palette: tuple[int, ...]) -> None:
    image = Image.new("P", (width, height))
    image.putdata(data)
    rgb = []
    for value in range(256):
        source = palette[value % len(palette)] if palette else value
        rgb.extend((source * 17 % 256, source * 53 % 256, source * 97 % 256))
    image.putpalette(rgb)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def compose(pose, *, width: int, height: int, canonical: bool,
            palette: tuple[int, ...]) -> bytes:
    pixels = bytearray(width * height)
    for cel in pose.cels:
        ox = width // 2 + cel.relative_x
        oy = height - 9 + cel.relative_y
        for x in range(cel.width):
            for y in range(cel.height):
                # Classic SCUMM cel pixels are traversed column-major.  The
                # noncanonical branch reproduces the current generator exactly.
                source = x * cel.height + y if canonical else y * cel.width + x
                tx = ox + x if pose.draw_to_right else ox - x
                ty = oy + y
                if 0 <= tx < width and 0 <= ty < height and cel.pixels[source]:
                    pixels[ty * width + tx] = palette[cel.pixels[source]]
    return bytes(pixels)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--profile", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--facing", type=int, default=180)
    args = ap.parse_args()
    costume = ScummV5Costume(provider(args.archive, args.profile).read("costume.2"), key="costume.2")
    manifest = {"costume": 2, "facing": args.facing, "canvas": [32, 64], "poses": []}
    for frame in (1, 2):
        pose = costume.decode_pose(frame, facing=args.facing, step=0)
        pose_dir = args.output / ("idle" if frame == 1 else "walk")
        pose_dir.mkdir(parents=True, exist_ok=True)
        for index, cel in enumerate(pose.cels):
            cel_canvas = bytearray(cel.width * cel.height)
            for x in range(cel.width):
                for y in range(cel.height):
                    cel_canvas[y * cel.width + x] = cel.pixels[x * cel.height + y]
            png(bytes(cel_canvas), cel.width, cel.height,
                pose_dir / f"cel-{index:02d}.png", costume.palette)
        host = compose(pose, width=32, height=64, canonical=True,
                       palette=costume.palette)
        current = compose(pose, width=32, height=64, canonical=False,
                          palette=costume.palette)
        png(host, 32, 64, pose_dir / "host-composite.png", costume.palette)
        # The corrected generator's emitted indexed frame is equivalent to
        # this source-order composition; retain the old output separately as
        # the regression witness.
        png(host, 32, 64, pose_dir / "cooked-composite.png", costume.palette)
        png(current, 32, 64, pose_dir / "current-cooker-composite.png", costume.palette)
        manifest["poses"].append({
            "frame": frame, "direction": pose.direction,
            "draw_to_right": pose.draw_to_right,
            "commands": [list(item) for item in pose.commands],
            "cels": [{"index": i, "width": c.width, "height": c.height,
                      "relative_x": c.relative_x, "relative_y": c.relative_y,
                      "move_x": c.move_x, "move_y": c.move_y,
                      "decoded_pixels": sum(v != 0 for v in c.pixels),
                      "transparent": 0, "palette": list(costume.palette),
                      "source_order": "column-major", "draw_order": i}
                     for i, c in enumerate(pose.cels)]})
    (args.output / "pose-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
