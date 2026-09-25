#!/usr/bin/env python3
"""Fresh-emulator proof of authentic room-49 backdrop-only presentation."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import sys

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from same.engines.scumm_v5.room_visual import decode_room_visual  # noqa: E402
from same.snes_surface import (  # noqa: E402
    SnesIndexedSurfaceBundle, build_static_tilemap, decode_bundle_indexed,
    decode_cgram, encode_cgram, encode_surface_tiles,
)
from same.video import IndexedSurface  # noqa: E402


DEFAULT_NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
CONTROL = 0x401000
VISUAL = 0x401080
SURFACE = 0x402000
TILE_SHADOW = 0x410000
CGRAM_SHADOW = 0x41E000
LIVE_PALETTE = 0x41E200
DMA = 0x7E223A


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def quantized_image(pixels: bytes, palette: list[tuple[int, int, int]]) -> Image.Image:
    quantized = decode_cgram(encode_cgram(palette))
    rgb = bytearray(len(pixels) * 3)
    for offset, index in enumerate(pixels):
        rgb[offset * 3:offset * 3 + 3] = bytes(quantized[index])
    return Image.frombytes("RGB", (256, 224), bytes(rgb))


def expected_frame(record_path: Path, room: int) -> tuple[bytes, list[tuple[int, int, int]], object, tuple[int, ...]]:
    visual = decode_room_visual(record_path.read_bytes(), expected_room=room)
    copy_width, copy_height = min(256, visual.width), min(224, visual.height)
    source_x, source_y = (visual.width - copy_width) // 2, (visual.height - copy_height) // 2
    destination_x, destination_y = (256 - copy_width) // 2, (224 - copy_height) // 2
    output = bytearray(256 * 224)
    for row in range(copy_height):
        source = (source_y + row) * visual.pitch + source_x
        target = (destination_y + row) * 256 + destination_x
        output[target:target + copy_width] = visual.pixels[source:source + copy_width]
    palette = [tuple(visual.palette[i:i + 3]) for i in range(0, 768, 3)]
    return bytes(output), palette, visual, (
        source_x, source_y, destination_x, destination_y, copy_width, copy_height,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "build/m25-start-object-sa1-mode3-room49.sfc")
    parser.add_argument("--visual", type=Path, default=ROOT / "build/m23a-rooms/authentic/room-49.sc5v")
    parser.add_argument("--room", type=int, default=49)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--output", type=Path, default=ROOT / "build/phase6e-room49-nexen")
    parser.add_argument("--port", type=int, default=44186)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    require(args.rom.is_file() and args.visual.is_file(), "ROM or cooked visual is unavailable")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    expected_pixels, expected_palette, visual_record, geometry = expected_frame(args.visual, args.room)
    expected_surface = IndexedSurface.wrap(256, 224, 256, expected_pixels, palette=expected_palette)
    expected_tiles = encode_surface_tiles(expected_surface)
    expected_cgram = encode_cgram(expected_palette)
    reference = quantized_image(expected_pixels, expected_palette)

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    transitions: list[dict[str, int | bool]] = []
    previous = None
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT, port=args.port,
        boot_wait=2.0, socket_timeout=90.0, stderr_log=args.output / "nexen-stderr.log",
    ) as session:
        session.pause(); session.tool("reset_emulator", {"power": True}); session.pause()
        sa1_start = session.get_cpu_state("Sa1")
        terminal_frame = 0
        for frame in range(1, 1601):
            run = session.run_frames(1)
            require(run["framesAdvanced"] == 1 and not run["timedOut"], "frame execution timed out")
            control = session.read_memory("snesMemory", CONTROL, 0x40)
            ppu = session.get_ppu_state()
            state = (
                int.from_bytes(control[0x0E:0x10], "little"),
                int.from_bytes(control[0x10:0x12], "little"), control[0x13], control[0x14],
                int.from_bytes(control[0x22:0x24], "little"),
                int.from_bytes(control[0x24:0x26], "little"),
                int.from_bytes(control[0x26:0x28], "little"), ppu["forcedBlank"],
            )
            if state != previous:
                transitions.append({
                    "frame": frame, "pending_generation": state[0],
                    "committed_generation": state[1], "backend_state": state[2],
                    "surface_locked": state[3], "candidate_tiles": state[4],
                    "pending_tiles": state[5], "inflight_descriptors": state[6],
                    "forced_blank": state[7],
                })
                previous = state
            if state[1] == 1 and not state[7]:
                terminal_frame = frame
                break
        require(terminal_frame != 0, "initial room presentation did not commit")
        visual = session.read_memory("snesMemory", VISUAL, 0x28)
        control = session.read_memory("snesMemory", CONTROL, 0x40)
        live_surface = session.read_memory("snesMemory", SURFACE, 0xE000)
        live_palette = session.read_memory("snesMemory", LIVE_PALETTE, 0x300)
        tile_shadow = session.read_memory("snesMemory", TILE_SHADOW, 0xE000)
        cgram_shadow = session.read_memory("snesMemory", CGRAM_SHADOW, 0x200)
        vram = session.read_memory("snesVideoRam", 0, 0x10000)
        cgram = session.read_memory("snesCgRam", 0, 0x200)
        dma = session.read_memory("snesMemory", DMA, 14)
        ppu = session.get_ppu_state()
        sa1_end = session.get_cpu_state("Sa1")
        screenshot_bytes = base64.b64decode(session.take_screenshot(format="base64")["base64"])

    emulator = Image.open(io.BytesIO(screenshot_bytes)).convert("RGB").crop((0, 0, 256, 224))
    emulator_path = args.output / f"room{args.room}-backdrop-emulator.png"
    reference_path = args.output / f"room{args.room}-backdrop-reference.png"
    emulator.save(emulator_path); reference.save(reference_path)
    difference = ImageChops.difference(emulator, reference)
    pixel_differences = sum(1 for pixel in difference.getdata() if pixel != (0, 0, 0))
    require(live_surface == expected_pixels, "live INDEX8 surface differs from host backdrop oracle")
    require(live_palette == b"".join(bytes(color) for color in expected_palette),
            "live RGB8 palette differs from authentic palette")
    require(tile_shadow == expected_tiles, "target tile shadow differs from Phase-6A realization")
    require(cgram_shadow == expected_cgram and cgram == expected_cgram,
            "CGRAM shadow or hardware CGRAM differs")
    require(vram[:0xE000] == expected_tiles and vram[0xE000:0xE800] == build_static_tilemap(),
            "VRAM characters or static tilemap differ")
    decoded = decode_bundle_indexed(SnesIndexedSurfaceBundle(tile_shadow, vram[0xE000:0xE800], cgram_shadow))
    require(decoded == expected_pixels, "decoded VRAM indexed plane differs")
    require(pixel_differences == 0, f"emulator image differs at {pixel_differences} pixels")
    require((int.from_bytes(visual[0:2], "little"), int.from_bytes(visual[2:4], "little"), visual[4]) == (args.room, 1, 1),
            "room visual ownership/status differs")
    require(tuple(int.from_bytes(visual[o:o + 2], "little") for o in range(6, 24, 2)) ==
            (visual_record.width, visual_record.height, visual_record.pitch, *geometry), "captured viewport differs")
    require((control[0x0A], control[0x0B], control[0x0C], control[0x13], control[0x14]) == (1, 1, 1, 1, 0),
            "terminal backend validity/state differs")
    require(ppu["bgMode"] == 3 and ppu["mainScreenLayers"] == 1 and ppu["subScreenLayers"] == 0,
            "Mode-3 BG1 state differs")
    require(ppu["layers"][0]["tilemapAddr"] == 0x7000 and ppu["layers"][0]["chrAddr"] == 0 and
            ppu["layers"][0]["hscroll"] == 0 and ppu["layers"][0]["vscroll"] == 0x3FF,
            "Mode-3 BG1 layout/alignment differs")
    stable = lambda value: {key: value[key] for key in
                            ("pc", "k", "a", "x", "y", "sp", "d", "dbr", "ps", "emulationMode")}
    require(stable(sa1_start) == stable(sa1_end), "SA-1 architectural state changed")
    report = {
        "gate": ("Phase 6E authentic room-49 backdrop-only presentation" if args.room == 49
                 else "Phase 6E copyright-free room-visual production lifecycle"),
        "result": "pass", "fresh_power_on": True, "debugger_writes": 0,
        "terminal_emulator_frame": terminal_frame,
        "rom_sha256": sha(args.rom.read_bytes()),
        "visual_record_sha256": sha(args.visual.read_bytes()),
        "source": {
            "archive_sha256": visual_record.archive_sha256,
            "index_sha256": visual_record.index_sha256,
            "data_sha256": visual_record.data_sha256,
            "room_sha256": visual_record.room_sha256,
            "decoded_pixels_sha256": visual_record.decoded_pixels_sha256,
            "decoded_palette_sha256": visual_record.decoded_palette_sha256,
        },
        "viewport": {"source": [geometry[0], geometry[1], geometry[4], geometry[5]],
                     "destination": [geometry[2], geometry[3], geometry[4], geometry[5]],
                     "clear_index": 0},
        "hashes": {
            "live_surface": sha(live_surface), "live_palette": sha(live_palette),
            "tile_shadow": sha(tile_shadow), "vram_characters": sha(vram[:0xE000]),
            "tilemap": sha(vram[0xE000:0xE800]), "cgram_shadow": sha(cgram_shadow),
            "cgram": sha(cgram), "reference_png": sha(reference_path.read_bytes()),
            "emulator_png": sha(emulator_path.read_bytes()),
        },
        "pixel_difference_count": pixel_differences, "state_transitions": transitions,
        "dma": {"pending": int.from_bytes(dma[2:4], "little"),
                "committed": int.from_bytes(dma[4:6], "little"),
                "rejected": int.from_bytes(dma[10:12], "little")},
        "sa1_reset_held": True,
        "limitations": ["backdrop only", "no actors/costumes", "no text", "no cursor", "no dynamic camera redraw"],
    }
    report_path = args.output / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "report": str(report_path),
                      "rom_sha256": report["rom_sha256"], "pixel_differences": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
