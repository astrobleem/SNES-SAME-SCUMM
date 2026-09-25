#!/usr/bin/env python3
"""Generate and assemble the copyright-free Phase 6A Mode-3 proof ROM."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from same.snes_surface import decode_bundle_indexed, decode_cgram, realize_indexed_surface
from same.video import IndexedSurface


def proof_surface() -> IndexedSurface:
    surface = IndexedSurface(256, 224)
    for y in range(224):
        for x in range(256):
            value = (x + y * 3 + (x // 8) * 17 + (y // 8) * 29) & 0xFF
            if x in {0, 7, 8, 255} or y in {0, 7, 8, 223}:
                value ^= 0xFF
            surface.pixels[y * 256 + x] = value
    surface.palette[:] = [
        ((index * 5) & 0xFF, (index * 11) & 0xFF, (index * 23) & 0xFF)
        for index in range(256)
    ]
    surface.palette[0] = (0, 0, 0)
    surface.palette[1] = (255, 255, 255)
    surface.palette[2] = (255, 0, 0)
    surface.palette[3] = (0, 255, 0)
    surface.palette[4] = (0, 0, 255)
    return surface


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "build/snes-surface-proof")
    parser.add_argument(
        "--poppy-root", type=Path, default=Path("/home/chad/poppy-astrobleem-latest")
    )
    args = parser.parse_args()
    output = args.output.resolve()
    generated = ROOT / "labs/snes_surface/generated"
    generated.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)

    surface = proof_surface()
    if set(surface.visible_bytes()) != set(range(256)):
        raise RuntimeError("proof surface does not exercise every indexed value")
    bundle = realize_indexed_surface(surface)
    decoded = decode_bundle_indexed(bundle)
    if decoded != surface.visible_bytes():
        raise RuntimeError("independent bundle decode differs from source indexed pixels")

    (generated / "tiles-first.8bpp").write_bytes(bundle.tiles_8bpp[:0x7000])
    (generated / "tiles-second.8bpp").write_bytes(bundle.tiles_8bpp[0x7000:])
    (generated / "tilemap.bin").write_bytes(bundle.tilemap)
    (generated / "palette.cgram").write_bytes(bundle.cgram)

    palette = decode_cgram(bundle.cgram)
    image = Image.new("RGB", (256, 224))
    image.putdata([palette[value] for value in decoded])
    reference = output / "reference.png"
    image.save(reference)

    poppy_dll = args.poppy_root / "src/Poppy.CLI/bin/Release/net10.0/poppy.dll"
    subprocess.run(
        [sys.executable, str(ROOT / "tools/check_poppy.py"), str(args.poppy_root), "--dll", str(poppy_dll)],
        check=True,
        cwd=ROOT,
    )
    rom = output / "same-snes-surface-proof.sfc"
    environment = dict(os.environ)
    environment.setdefault("DOTNET_ROOT", "/home/chad/.dotnet10")
    environment["PATH"] = f"{environment['DOTNET_ROOT']}:{environment.get('PATH', '')}"
    subprocess.run(
        [
            "dotnet",
            str(poppy_dll),
            "-t",
            "snes",
            "labs/snes_surface/main.pasm",
            "-o",
            str(rom),
            "--no-verify",
        ],
        check=True,
        cwd=ROOT,
        env=environment,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "tools/finalize_snes_rom.py"), str(rom)],
        check=True,
        cwd=ROOT,
    )
    manifest = {
        "format": "same-snes-index8-mode3-proof",
        "version": 1,
        "copyright_free": True,
        "source_indexed_sha256": sha256(surface.visible_bytes()),
        "tiles_sha256": sha256(bundle.tiles_8bpp),
        "tilemap_sha256": sha256(bundle.tilemap),
        "cgram_sha256": sha256(bundle.cgram),
        "reference_png_sha256": sha256(reference.read_bytes()),
        "rom_sha256": sha256(rom.read_bytes()),
        "rom_size": rom.stat().st_size,
        "registers": {"BGMODE": 3, "BG1SC": 0x70, "BG12NBA": 0, "TM": 1, "TS": 0},
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(manifest_path)
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
