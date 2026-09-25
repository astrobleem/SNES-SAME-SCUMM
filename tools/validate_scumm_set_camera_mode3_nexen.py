#!/usr/bin/env python3
"""Fresh-emulator Phase 6F camera/backdrop convergence proof."""

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
    SnesIndexedSurfaceBundle,
    build_static_tilemap,
    build_tile_runs,
    candidate_tiles,
    changed_tiles,
    decode_bundle_indexed,
    decode_cgram,
    encode_cgram,
    encode_surface_tiles,
    plan_tile_transfers,
)
from same.video import IndexedSurface, Rect  # noqa: E402


DEFAULT_NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
CONTROL = 0x401000
VISUAL = 0x401080
SURFACE = 0x402000
TILE_SHADOW = 0x410000
CGRAM_SHADOW = 0x41E000
LIVE_PALETTE = 0x41E200
DMA = 0x7E223A
SCUMM = 0x7E2300
CAMERA = 0x7E7FA8


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def u16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 2], "little")


def expected_frame(visual_path: Path, source_x: int) -> tuple[bytes, list[tuple[int, int, int]], object]:
    visual = decode_room_visual(visual_path.read_bytes(), expected_room=49)
    pixels = bytearray(256 * 224)
    for row in range(144):
        source = row * visual.pitch + source_x
        target = (40 + row) * 256
        pixels[target:target + 256] = visual.pixels[source:source + 256]
    palette = [tuple(visual.palette[i:i + 3]) for i in range(0, 768, 3)]
    return bytes(pixels), palette, visual


def quantized_image(pixels: bytes, palette: list[tuple[int, int, int]]) -> Image.Image:
    quantized = decode_cgram(encode_cgram(palette))
    rgb = bytearray(len(pixels) * 3)
    for offset, index in enumerate(pixels):
        rgb[offset * 3:offset * 3 + 3] = bytes(quantized[index])
    return Image.frombytes("RGB", (256, 224), bytes(rgb))


def stable_sa1(value: dict[str, object]) -> dict[str, object]:
    return {key: value[key] for key in
            ("pc", "k", "a", "x", "y", "sp", "d", "dbr", "ps", "emulationMode")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "build/m25-set-camera-sa1-mode3-room49.sfc")
    parser.add_argument("--visual", type=Path, default=ROOT / "build/m23a-rooms/authentic/room-49.sc5v")
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--output", type=Path, default=ROOT / "build/phase6f-set-camera-nexen")
    parser.add_argument("--port", type=int, default=44187)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    require(args.rom.is_file() and args.visual.is_file(), "ROM or cooked visual is unavailable")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")

    old_pixels, palette, visual_record = expected_frame(args.visual, 192)
    expected_pixels, expected_palette, _ = expected_frame(args.visual, 32)
    old_tiles = encode_surface_tiles(IndexedSurface.wrap(256, 224, 256, old_pixels, palette=palette))
    expected_surface = IndexedSurface.wrap(256, 224, 256, expected_pixels, palette=expected_palette)
    expected_tiles = encode_surface_tiles(expected_surface)
    expected_cgram = encode_cgram(expected_palette)
    changed = changed_tiles(
        expected_tiles, old_tiles, candidate_tiles((Rect(0, 0, 256, 224),))
    )
    expected_runs = build_tile_runs(changed)
    pending = changed
    expected_batches: list[dict[str, object]] = []
    while pending:
        plan = plan_tile_transfers(pending)
        expected_batches.append({
            "runs": [[run.first_tile, run.tile_count] for run in plan.runs],
            "bytes": plan.byte_length,
        })
        pending = plan.pending_tiles

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    transitions: list[dict[str, object]] = []
    previous: tuple[int, ...] | None = None
    immediate: dict[str, int] | None = None
    published: dict[str, int] | None = None
    before: dict[str, int] | None = None
    previous_camera: dict[str, int] | None = None
    generation_two_start = 0
    generation_two_commit = 0
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT, port=args.port,
        boot_wait=2.0, socket_timeout=90.0, stderr_log=args.output / "nexen-stderr.log",
    ) as session:
        session.pause(); session.tool("reset_emulator", {"power": True}); session.pause()
        sa1_start = session.get_cpu_state("Sa1")
        for frame in range(1, 2401):
            run = session.run_frames(1)
            require(run["framesAdvanced"] == 1 and not run["timedOut"], "frame execution timed out")
            control = session.read_memory("snesMemory", CONTROL, 0x40)
            camera = session.read_memory("snesMemory", CAMERA, 0x24)
            camera_snapshot = {
                "current_x": u16(camera, 0), "current_y": u16(camera, 2),
                "destination_x": u16(camera, 4), "destination_y": u16(camera, 6),
                "last_x": u16(camera, 8), "last_y": u16(camera, 10),
                "screen_start_strip": u16(camera, 12),
                "screen_end_strip": u16(camera, 14), "xstart": u16(camera, 16),
                "update_pending": camera[30], "scroll_script": camera[31],
            }
            state = (
                u16(control, 0x0E), u16(control, 0x10), control[0x13], control[0x14],
                u16(control, 0x22), u16(control, 0x24), u16(control, 0x26),
                u16(camera, 0x18), u16(camera, 0x1A), u16(camera, 0x1C), camera[0x1E],
            )
            if state != previous:
                transitions.append({
                    "frame": frame, "pending_generation": state[0],
                    "committed_generation": state[1], "backend_state": state[2],
                    "surface_locked": state[3], "candidate_tiles": state[4],
                    "pending_tiles": state[5], "inflight_descriptors": state[6],
                    "camera_immediate_count": state[7], "camera_publish_count": state[8],
                    "scroll_script_count": state[9], "camera_update_pending": state[10],
                })
                previous = state
            if state[7] == 1 and immediate is None:
                before = previous_camera
                immediate = {
                    "frame": frame, "current_x": u16(camera, 0), "destination_x": u16(camera, 4),
                    "screen_start_strip": u16(camera, 12), "xstart": u16(camera, 16),
                    "requested_x": u16(camera, 18), "pc_before": u16(camera, 20),
                    "pc_after": u16(camera, 22), "update_pending": camera[30],
                }
            if state[8] == 1 and published is None:
                published = {
                    "frame": frame, "current_x": u16(camera, 0), "destination_x": u16(camera, 4),
                    "screen_start_strip": u16(camera, 12), "screen_end_strip": u16(camera, 14),
                    "xstart": u16(camera, 16), "update_pending": camera[30],
                }
            if state[0] == 2 and generation_two_start == 0:
                generation_two_start = frame
            if state[1] == 2 and state[2] == 1 and state[3] == 0:
                generation_two_commit = frame
                scumm = session.read_memory("snesMemory", SCUMM, 0x20)
                if u16(scumm, 0) == 0x0296 and scumm[3] == 0x0E:
                    break
            previous_camera = camera_snapshot
        require(generation_two_commit != 0, "post-camera generation did not commit")
        control = session.read_memory("snesMemory", CONTROL, 0x40)
        visual = session.read_memory("snesMemory", VISUAL, 0x34)
        camera = session.read_memory("snesMemory", CAMERA, 0x24)
        scumm = session.read_memory("snesMemory", SCUMM, 0x20)
        live_surface = session.read_memory("snesMemory", SURFACE, 0xE000)
        live_palette = session.read_memory("snesMemory", LIVE_PALETTE, 0x300)
        tile_shadow = session.read_memory("snesMemory", TILE_SHADOW, 0xE000)
        cgram_shadow = session.read_memory("snesMemory", CGRAM_SHADOW, 0x200)
        vram = session.read_memory("snesVideoRam", 0, 0x10000)
        cgram = session.read_memory("snesCgRam", 0, 0x200)
        dma = session.read_memory("snesMemory", DMA, 14)
        ppu = session.get_ppu_state()
        cpu = session.get_cpu_state("Snes")
        sa1_end = session.get_cpu_state("Sa1")
        screenshot_bytes = base64.b64decode(session.take_screenshot(format="base64")["base64"])

    emulator = Image.open(io.BytesIO(screenshot_bytes)).convert("RGB").crop((0, 0, 256, 224))
    reference = quantized_image(expected_pixels, expected_palette)
    emulator_path = args.output / "room49-post-camera-emulator.png"
    reference_path = args.output / "room49-post-camera-reference.png"
    emulator.save(emulator_path); reference.save(reference_path)
    difference = ImageChops.difference(emulator, reference)
    pixel_differences = sum(pixel != (0, 0, 0) for pixel in difference.getdata())

    require(before is not None and immediate is not None and published is not None,
            "camera checkpoints were not observed")
    require((before["current_x"], before["destination_x"], before["last_x"],
             before["screen_start_strip"], before["screen_end_strip"], before["xstart"]) ==
            (160, 160, 160, 0, 39, 0), "pre-opcode camera state differs")
    require((immediate["current_x"], immediate["destination_x"], immediate["requested_x"]) == (160, 0, 0),
            "immediate camera state differs")
    require((immediate["pc_before"], immediate["pc_after"]) == (0x026E, 0x0271), "camera PC boundary differs")
    require((published["current_x"], published["destination_x"], published["screen_start_strip"],
             published["screen_end_strip"], published["xstart"]) == (160, 160, 0, 39, 0),
            "published camera state differs")
    require(live_surface == expected_pixels, "live surface differs from post-camera oracle")
    require(live_palette == visual_record.palette, "live palette changed across camera reprojection")
    require(tile_shadow == expected_tiles and vram[:0xE000] == expected_tiles, "tile shadow/VRAM differs")
    require(cgram_shadow == expected_cgram and cgram == expected_cgram, "CGRAM differs")
    require(vram[0xE000:0xE800] == build_static_tilemap(), "static tilemap differs")
    decoded = decode_bundle_indexed(SnesIndexedSurfaceBundle(tile_shadow, vram[0xE000:0xE800], cgram_shadow))
    require(decoded == expected_pixels, "decoded indexed framebuffer differs")
    require(pixel_differences == 0, f"emulator image differs at {pixel_differences} pixels")
    require((u16(scumm, 0), scumm[2], scumm[3], scumm[6]) == (0x0296, 2, 0x0E, 0x14),
            "next unsupported semantic blocker differs")
    require(u16(camera, 0x1C) == 1 and camera[0x1F] == 214, "authentic scroll-script side effect differs")
    require(u16(visual, 0x0C) == 32 and u16(visual, 0x24) == 32 and visual[0x26] == 0,
            "camera visual ownership/pending state differs")
    require(u16(visual, 0x2C) == 1 and u16(control, 0x30) == 0,
            "camera presentation count or CGRAM byte count differs: "
            f"present={u16(visual, 0x2C)} cgram={u16(control, 0x30)}")
    require((control[0x13], control[0x14], u16(control, 0x10)) == (1, 0, 2),
            "backend did not finish generation 2")
    require(ppu["bgMode"] == 3 and ppu["layers"][0]["hscroll"] == 0 and
            ppu["layers"][0]["vscroll"] == 0x3FF, "Mode-3 register state differs")
    require(stable_sa1(sa1_start) == stable_sa1(sa1_end), "SA-1 architectural state changed")

    report = {
        "gate": "Phase 6F canonical setCameraAt and camera-driven backdrop reprojection",
        "result": "pass", "fresh_power_on": True, "debugger_writes": 0,
        "rom_sha256": sha(args.rom.read_bytes()),
        "authentic_instruction": {"resource": "room.49/LSCR.211", "offset": "026E",
                                  "bytes": "b20200", "operand": "Var[2]", "value": 0,
                                  "pc_after": "0271"},
        "camera": {"before": before, "immediate": immediate, "published": published,
                   "minimum_x": 160, "maximum_x": 160, "scroll_script": 214,
                   "talk_stop_active": False},
        "viewport": {"old_source": [192, 0, 256, 144], "new_source": [32, 0, 256, 144],
                     "destination": [0, 40, 256, 144], "clear_index": 0},
        "generation": {"start_frame": generation_two_start, "commit_frame": generation_two_commit,
                       "latency_frames": generation_two_commit - generation_two_start + 1,
                       "pending": u16(control, 0x0E), "committed": u16(control, 0x10),
                       "surface_locked": control[0x14], "converted_tiles": u16(control, 0x2A),
                       "unchanged_candidates": u16(control, 0x2C),
                       "queued_tile_bytes": u16(control, 0x2E),
                       "queued_cgram_bytes": u16(control, 0x30), "batches": u16(control, 0x32)},
        "oracle": {"changed_tiles": list(changed),
                   "runs": [[run.first_tile, run.tile_count] for run in expected_runs],
                   "dma_batches": expected_batches},
        "hashes": {"old_surface": sha(old_pixels), "live_surface": sha(live_surface),
                   "live_palette": sha(live_palette), "tile_shadow": sha(tile_shadow),
                   "vram_characters": sha(vram[:0xE000]), "cgram_shadow": sha(cgram_shadow),
                   "cgram": sha(cgram), "reference_png": sha(reference_path.read_bytes()),
                   "emulator_png": sha(emulator_path.read_bytes())},
        "pixel_difference_count": pixel_differences,
        "dma": {"pending": u16(dma, 2), "committed": u16(dma, 4),
                "frame_bytes": u16(dma, 6), "rejected": u16(dma, 10)},
        "terminal": {"pc": "0296", "status": "yielded", "error": "0E",
                     "opcode": "14", "classification": "encoded talk/text subsystem gap",
                     "surrounding_bytes": "14020f49276c6c207761697420686572652eff032a736967682a00"},
        "s_cpu": cpu, "sa1_start": stable_sa1(sa1_start), "sa1_end": stable_sa1(sa1_end),
        "state_transitions": transitions,
        "limitations": ["backdrop only", "incremental active-display convergence",
                        "no actors/costumes", "no text pixels", "no cursor", "no room-63 visual"],
    }
    report_path = args.output / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "report": str(report_path),
                      "rom_sha256": report["rom_sha256"], "pixel_differences": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
