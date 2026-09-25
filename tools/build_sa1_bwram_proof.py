#!/usr/bin/env python3
"""Build the isolated Phase 6B reset-held SA-1 BW-RAM carrier proof."""

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
from same.snes_carrier import layout_regions
from same.video import IndexedSurface


LAYOUT_PATH = ROOT / "runtime/snes/carriers/sa1_bwram_layout.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_address(value: str) -> int:
    bank, offset = value.split(":", 1)
    return (int(bank, 16) << 16) | int(offset, 16)


def validate_layout(layout: dict[str, object]) -> None:
    # Phase 6B and production consume the same canonical layout validator.
    layout_regions(layout)


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


def write_alias_test_include(path: Path) -> None:
    lines = [
        "; Generated complete BMAPS alias comparison for seven 8 KiB surface bands.",
        "SurfaceProof_TestAliases:",
        "    sep #$20",
        "    .a8",
        "    rep #$10",
        "    .i16",
        "    lda #$00",
        "    sta.l SURFACE_PROOF_ALIAS_FLAGS",
    ]
    for block in range(1, 8):
        base = 0x400000 + block * 0x2000
        bit = 1 << (block - 1)
        lines.extend(
            [
                f"    lda #${block:02X}",
                "    sta BMAPS",
                "    ldx #$0000",
                f"SurfaceProof_Alias{block}_Compare:",
                "    .a8",
                "    .i16",
                f"    lda.l ${base:06X},x",
                "    cmp.l $006000,x",
                f"    bne SurfaceProof_Alias{block}_Fail",
                f"    cmp.l $806000,x",
                f"    bne SurfaceProof_Alias{block}_Fail",
                "    inx",
                "    cpx #$2000",
                f"    bcc SurfaceProof_Alias{block}_Compare",
                f"    lda.l ${base + 0x1FFE:06X}",
                "    sta.l SURFACE_PROOF_ALIAS_SCRATCH",
                "    eor #$5A",
                f"    sta.l ${base + 0x1FFE:06X}",
                "    cmp.l $007FFE",
                f"    bne SurfaceProof_Alias{block}_RestoreDirectFail",
                "    lda.l SURFACE_PROOF_ALIAS_SCRATCH",
                f"    sta.l ${base + 0x1FFE:06X}",
                f"    lda.l ${base + 0x1FFF:06X}",
                "    sta.l SURFACE_PROOF_ALIAS_SCRATCH",
                "    eor #$A5",
                "    sta.l $007FFF",
                f"    cmp.l ${base + 0x1FFF:06X}",
                f"    bne SurfaceProof_Alias{block}_RestoreWindowFail",
                "    lda.l SURFACE_PROOF_ALIAS_SCRATCH",
                "    sta.l $007FFF",
                "    lda.l SURFACE_PROOF_ALIAS_FLAGS",
                f"    ora #${bit:02X}",
                "    sta.l SURFACE_PROOF_ALIAS_FLAGS",
                f"    bra SurfaceProof_Alias{block}_Done",
                f"SurfaceProof_Alias{block}_RestoreDirectFail:",
                "    lda.l SURFACE_PROOF_ALIAS_SCRATCH",
                f"    sta.l ${base + 0x1FFE:06X}",
                f"    bra SurfaceProof_Alias{block}_Fail",
                f"SurfaceProof_Alias{block}_RestoreWindowFail:",
                "    lda.l SURFACE_PROOF_ALIAS_SCRATCH",
                "    sta.l $007FFF",
                f"SurfaceProof_Alias{block}_Fail:",
                "    lda.l SURFACE_PROOF_ERRORS",
                "    inc",
                "    sta.l SURFACE_PROOF_ERRORS",
                f"SurfaceProof_Alias{block}_Done:",
                "    .a8",
                "    .i16",
            ]
        )
    lines.extend(
        [
            "    stz BMAPS",
            "    lda #$00",
            "    sta.l SURFACE_PROOF_BMAPS_SHADOW",
            "    rts",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "build/sa1-bwram-proof")
    parser.add_argument(
        "--poppy-root", type=Path, default=Path("/home/chad/poppy-astrobleem-latest")
    )
    args = parser.parse_args()
    output = args.output.resolve()
    generated = ROOT / "labs/sa1_bwram/generated"
    output.mkdir(parents=True, exist_ok=True)
    generated.mkdir(parents=True, exist_ok=True)

    layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    validate_layout(layout)
    surface = proof_surface()
    if set(surface.visible_bytes()) != set(range(256)):
        raise RuntimeError("proof surface does not exercise every indexed value")
    bundle = realize_indexed_surface(surface)
    if decode_bundle_indexed(bundle) != surface.visible_bytes():
        raise RuntimeError("independent bundle decode differs from source indexed pixels")

    assets = {
        "surface-first.index8": surface.visible_bytes()[:0x7000],
        "surface-second.index8": surface.visible_bytes()[0x7000:],
        "tiles-first.8bpp": bundle.tiles_8bpp[:0x7000],
        "tiles-second.8bpp": bundle.tiles_8bpp[0x7000:],
        "tilemap.bin": bundle.tilemap,
        "palette.cgram": bundle.cgram,
    }
    for name, data in assets.items():
        (generated / name).write_bytes(data)
    write_alias_test_include(generated / "alias-tests.inc.pasm")

    palette = decode_cgram(bundle.cgram)
    image = Image.new("RGB", (256, 224))
    image.putdata([palette[value] for value in surface.visible_bytes()])
    reference = output / "reference.png"
    image.save(reference)

    poppy_dll = args.poppy_root / "src/Poppy.CLI/bin/Release/net10.0/poppy.dll"
    subprocess.run(
        [sys.executable, str(ROOT / "tools/check_poppy.py"), str(args.poppy_root), "--dll", str(poppy_dll)],
        check=True,
        cwd=ROOT,
    )
    rom = output / "same-sa1-bwram-proof.sfc"
    environment = dict(os.environ)
    environment.setdefault("DOTNET_ROOT", "/home/chad/.dotnet10")
    environment["PATH"] = f"{environment['DOTNET_ROOT']}:{environment.get('PATH', '')}"
    subprocess.run(
        [
            "dotnet",
            str(poppy_dll),
            "-t",
            "snes",
            "labs/sa1_bwram/main.pasm",
            "-o",
            str(rom),
            "--no-verify",
        ],
        check=True,
        cwd=ROOT,
        env=environment,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/finalize_snes_rom.py"),
            str(rom),
            "--carrier",
            "sa1_bwram",
        ],
        check=True,
        cwd=ROOT,
    )
    manifest = {
        "format": "same-sa1-bwram-proof",
        "version": 1,
        "copyright_free": True,
        "layout": layout,
        "header": {"map_mode": 0x23, "cartridge_type": 0x35, "ram_size": 0x07},
        "surface_sha256": sha256(surface.visible_bytes()),
        "tile_shadow_sha256": sha256(bundle.tiles_8bpp),
        "cgram_shadow_sha256": sha256(bundle.cgram),
        "tilemap_sha256": sha256(bundle.tilemap),
        "reference_png_sha256": sha256(reference.read_bytes()),
        "rom_sha256": sha256(rom.read_bytes()),
        "rom_size": rom.stat().st_size,
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(manifest_path)
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
