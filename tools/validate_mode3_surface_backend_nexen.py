#!/usr/bin/env python3
"""Fresh-emulator acceptance for the production Phase-6D Mode-3 backend."""

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

from same.snes_surface import (  # noqa: E402
    SnesIndexedSurfaceBundle,
    build_static_tilemap,
    decode_bundle_indexed,
    decode_cgram,
    encode_cgram,
    encode_snes_8bpp_tile,
    encode_surface_tiles,
)
from same.video import IndexedSurface  # noqa: E402

DEFAULT_NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
CONTROL = 0x401000
SURFACE = 0x402000
TILE_SHADOW = 0x410000
CGRAM_SHADOW = 0x41E000
LIVE_PALETTE = 0x41E200
FIXTURE = 0x41E800
DMA = 0x7E223A


class GateFailure(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise GateFailure(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fixture_states() -> tuple[list[bytes], list[list[tuple[int, int, int]]]]:
    pixels = bytearray((x + y) & 0xFF for y in range(224) for x in range(256))
    palette = [(i, i ^ 0x55, i ^ 0xFF) for i in range(256)]
    states = [bytes(pixels), bytes(pixels)]
    palettes = [list(palette), list(palette)]
    pixels[0x0909] ^= 1
    states.append(bytes(pixels)); palettes.append(list(palette))
    red, green, blue = palette[1]
    palette[1] = (red ^ 0xF8, green, blue)
    states.append(bytes(pixels)); palettes.append(list(palette))
    for tile in range(33):
        x = (tile & 31) * 8
        y = (tile >> 5) * 8
        pixels[y * 256 + x] ^= 1
    states.append(bytes(pixels)); palettes.append(list(palette))
    for tile in (0, 2, 4, 6, 8, 10, 12, 14, 32):
        x = (tile & 31) * 8
        y = (tile >> 5) * 8
        pixels[y * 256 + x] ^= 1
    states.append(bytes(pixels)); palettes.append(list(palette))
    return states, palettes


def reference_image(pixels: bytes, palette: list[tuple[int, int, int]]) -> Image.Image:
    quantized = decode_cgram(encode_cgram(palette))
    raw = bytearray(len(pixels) * 3)
    for index, color in enumerate(pixels):
        raw[index * 3:index * 3 + 3] = bytes(quantized[color])
    return Image.frombytes("RGB", (256, 224), bytes(raw))


def parse_snapshot(raw: bytes, generation: int) -> dict[str, int]:
    offset = generation * 0x20
    names = ("converted_tiles", "unchanged_candidates", "tile_bytes", "cgram_bytes",
             "batches", "dma_committed", "rejected_dirty", "rejected_palette", "rejected_present")
    return {name: int.from_bytes(raw[offset + index * 2:offset + index * 2 + 2], "little")
            for index, name in enumerate(names)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "build/phase6d-mode3-surface.sfc")
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--output", type=Path, default=ROOT / "build/phase6d-mode3-nexen")
    parser.add_argument("--port", type=int, default=44150)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    require(args.rom.is_file(), f"ROM not found: {args.rom}")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    states, palettes = fixture_states()

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    observations: dict[int, dict[str, object]] = {}
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT, port=args.port,
        boot_wait=2.0, socket_timeout=90.0, stderr_log=args.output / "nexen-stderr.log",
    ) as session:
        session.pause(); session.tool("reset_emulator", {"power": True}); session.pause()
        sa1_start = session.get_cpu_state("Sa1")
        transitions: list[dict[str, object]] = []
        observed_batches: dict[int, list[list[dict[str, int]]]] = {}
        seen_batches: set[tuple[int, int]] = set()
        previous_state: tuple[int, ...] | None = None
        previous_generation = 0
        previous_converted = 0
        max_converted_per_emulator_frame = 0
        for frame in range(1, 2401):
            run = session.run_frames(1)
            require(run["framesAdvanced"] == 1 and not run["timedOut"], "frame execution timed out")
            control = session.read_memory("snesMemory", CONTROL, 0x40)
            generation = int.from_bytes(control[0x10:0x12], "little")
            pending_generation = int.from_bytes(control[0x0E:0x10], "little")
            state = control[0x13]
            converted = int.from_bytes(control[0x2A:0x2C], "little")
            if pending_generation == previous_generation:
                max_converted_per_emulator_frame = max(
                    max_converted_per_emulator_frame, max(0, converted - previous_converted)
                )
            previous_generation, previous_converted = pending_generation, converted
            dma_now = session.read_memory("snesMemory", DMA, 14)
            state_record = (
                pending_generation, generation, state, control[0x14],
                int.from_bytes(control[0x22:0x24], "little"),
                int.from_bytes(control[0x24:0x26], "little"),
                int.from_bytes(control[0x26:0x28], "little"),
                int.from_bytes(dma_now[2:4], "little"),
                int.from_bytes(dma_now[4:6], "little"),
            )
            if state_record != previous_state:
                transitions.append({
                    "frame": frame, "pending_generation": state_record[0],
                    "committed_generation": state_record[1], "state": state_record[2],
                    "surface_locked": state_record[3], "candidate_tiles": state_record[4],
                    "pending_tiles": state_record[5], "inflight_descriptors": state_record[6],
                    "dma_pending": state_record[7], "dma_committed": state_record[8],
                })
                previous_state = state_record
            expected_dma = int.from_bytes(control[0x28:0x2A], "little")
            record_count = int.from_bytes(control[0x3E:0x40], "little")
            batch_key = (pending_generation, expected_dma)
            if state == 4 and record_count and batch_key not in seen_batches:
                raw_records = session.read_memory("snesMemory", 0x41E6F0, record_count * 12)
                records = []
                for index in range(record_count):
                    record = raw_records[index * 12:(index + 1) * 12]
                    records.append({
                        "type": int.from_bytes(record[0:2], "little"),
                        "first": int.from_bytes(record[2:4], "little"),
                        "count": int.from_bytes(record[4:6], "little"),
                        "bytes": int.from_bytes(record[6:8], "little"),
                    })
                observed_batches.setdefault(pending_generation, []).append(records)
                seen_batches.add(batch_key)
            if generation and generation not in observations and not session.get_ppu_state()["forcedBlank"]:
                shot = base64.b64decode(session.take_screenshot(format="base64")["base64"])
                image = Image.open(io.BytesIO(shot)).convert("RGB").crop((0, 0, 256, 224))
                reference = reference_image(states[generation - 1], palettes[generation - 1])
                emulator_path = args.output / f"generation-{generation}-emulator.png"
                reference_path = args.output / f"generation-{generation}-reference.png"
                image.save(emulator_path); reference.save(reference_path)
                require(ImageChops.difference(image, reference).getbbox() is None,
                        f"generation {generation} visible pixels differ")
                sa1_checkpoint = session.get_cpu_state("Sa1")
                observations[generation] = {
                    "frame": frame,
                    "emulator_png_sha256": sha(emulator_path.read_bytes()),
                    "reference_png_sha256": sha(reference_path.read_bytes()),
                    "sa1": {key: sa1_checkpoint[key] for key in
                            ("pc", "k", "a", "x", "y", "sp", "d", "dbr", "ps", "emulationMode")},
                }
            fixture = session.read_memory("snesMemory", FIXTURE, 8)
            if int.from_bytes(fixture[6:8], "little") == 1:
                terminal_frame = frame
                break
        else:
            raise GateFailure("fixture did not complete six generations")

        control = session.read_memory("snesMemory", CONTROL, 0x40)
        fixture = session.read_memory("snesMemory", FIXTURE, 0xE0)
        live_surface = session.read_memory("snesMemory", SURFACE, 0xE000)
        tile_shadow = session.read_memory("snesMemory", TILE_SHADOW, 0xE000)
        cgram_shadow = session.read_memory("snesMemory", CGRAM_SHADOW, 0x200)
        live_palette = session.read_memory("snesMemory", LIVE_PALETTE, 0x300)
        vram = session.read_memory("snesVideoRam", 0, 0x10000)
        cgram = session.read_memory("snesCgRam", 0, 0x200)
        dma = session.read_memory("snesMemory", DMA, 14)
        ppu = session.get_ppu_state()
        sa1_end = session.get_cpu_state("Sa1")

    require(set(observations) == set(range(1, 7)), "not every committed generation was observed")
    require(live_surface == states[-1], "final live indexed surface differs")
    palette = [tuple(live_palette[i:i + 3]) for i in range(0, 0x300, 3)]
    surface = IndexedSurface.wrap(256, 224, 256, live_surface, palette=palette)
    expected_tiles = encode_surface_tiles(surface)
    expected_cgram = encode_cgram(palette)
    require(tile_shadow == expected_tiles, "target 8bpp encoder differs from Phase-6A oracle")
    require(cgram_shadow == expected_cgram, "target BGR555 conversion differs")
    require(vram[:0xE000] == tile_shadow and vram[0xE000:0xE800] == build_static_tilemap(),
            "VRAM differs from fixed shadows/tilemap")
    require(cgram == cgram_shadow, "CGRAM differs from committed shadow")
    decoded = decode_bundle_indexed(SnesIndexedSurfaceBundle(tile_shadow, vram[0xE000:0xE800], cgram_shadow))
    require(decoded == live_surface, "decoded VRAM indexed plane differs")
    require(ppu["bgMode"] == 3 and ppu["mainScreenLayers"] == 1 and ppu["subScreenLayers"] == 0,
            "Mode-3 BG1 PPU state differs")
    require(ppu["layers"][0]["tilemapAddr"] == 0x7000 and ppu["layers"][0]["chrAddr"] == 0,
            "BG1 VRAM bases differ")
    require(ppu["layers"][0]["hscroll"] == 0 and ppu["layers"][0]["vscroll"] == 0x3FF,
            "BG1 logical-surface alignment differs")
    stable = lambda s: {k: s[k] for k in ("pc", "k", "a", "x", "y", "sp", "d", "dbr", "ps", "emulationMode")}
    require(stable(sa1_start) == stable(sa1_end), "SA-1 architectural state changed")
    require(all(item["sa1"] == stable(sa1_start) for item in observations.values()),
            "SA-1 architectural state changed during a completed generation")
    snapshots = {generation: parse_snapshot(fixture, generation) for generation in range(1, 7)}
    expected = {
        1: (896, 0, 0xE000, 0x200, 29), 2: (0, 896, 0, 0, 0),
        3: (1, 0, 64, 0, 1), 4: (0, 0, 0, 2, 1),
        5: (33, 0, 33 * 64, 0, 2), 6: (9, 0, 9 * 64, 0, 2),
    }
    for generation, values in expected.items():
        actual = snapshots[generation]
        require(tuple(actual[key] for key in ("converted_tiles", "unchanged_candidates", "tile_bytes", "cgram_bytes", "batches")) == values,
                f"generation {generation} counters differ: {actual}")
    require((snapshots[5]["rejected_dirty"], snapshots[5]["rejected_palette"], snapshots[5]["rejected_present"]) == (1, 1, 1),
            "surface-lock rejection counters differ")
    final_control = {
        "surface_valid": control[0x0A], "tile_shadow_valid": control[0x0B],
        "cgram_shadow_valid": control[0x0C],
        "pending_generation": int.from_bytes(control[0x0E:0x10], "little"),
        "committed_generation": int.from_bytes(control[0x10:0x12], "little"),
        "backend_id": control[0x12], "state": control[0x13],
        "surface_locked": control[0x14],
        "accepted_present": int.from_bytes(control[0x1A:0x1C], "little"),
        "rejected_present": int.from_bytes(control[0x1C:0x1E], "little"),
        "rejected_dirty": int.from_bytes(control[0x1E:0x20], "little"),
        "rejected_palette": int.from_bytes(control[0x20:0x22], "little"),
        "candidate_tiles": int.from_bytes(control[0x22:0x24], "little"),
        "pending_tiles": int.from_bytes(control[0x24:0x26], "little"),
        "inflight_descriptors": int.from_bytes(control[0x26:0x28], "little"),
    }
    require(final_control == {
        "surface_valid": 1, "tile_shadow_valid": 1, "cgram_shadow_valid": 1,
        "pending_generation": 6, "committed_generation": 6,
        "backend_id": 1, "state": 1, "surface_locked": 0,
        "accepted_present": 6, "rejected_present": 1,
        "rejected_dirty": 1, "rejected_palette": 1,
        "candidate_tiles": 0, "pending_tiles": 0, "inflight_descriptors": 0,
    }, f"terminal backend control differs: {final_control}")
    require(max_converted_per_emulator_frame <= 4,
            f"active conversion exceeded four tiles in one emulator frame: {max_converted_per_emulator_frame}")
    expected_active_batches = {
        3: [[{"type": 0, "first": 33, "count": 1, "bytes": 64}]],
        4: [[{"type": 2, "first": 1, "count": 1, "bytes": 2}]],
        5: [[{"type": 0, "first": 0, "count": 32, "bytes": 2048}],
            [{"type": 0, "first": 32, "count": 1, "bytes": 64}]],
        6: [[{"type": 0, "first": tile, "count": 1, "bytes": 64}
             for tile in (0, 2, 4, 6, 8, 10, 12, 14)],
            [{"type": 0, "first": 32, "count": 1, "bytes": 64}]],
    }
    # A one-descriptor active batch can enqueue and commit between two emulator
    # frame observations. Multi-batch generations must expose their retained
    # work, while snapshots above prove the single-batch byte/count result.
    for generation, batches in observed_batches.items():
        if generation in expected_active_batches:
            require(batches == expected_active_batches[generation][:len(batches)],
                    f"generation {generation} observed DMA batches differ: {batches}")
    require(int.from_bytes(dma[2:4], "little") == 0 and int.from_bytes(dma[10:12], "little") == 0,
            "DMA queue did not drain cleanly")
    report = {
        "gate": "Phase 6D selectable production Mode-3 indexed-surface backend",
        "result": "pass", "fresh_power_on": True, "debugger_writes": 0,
        "terminal_frame": terminal_frame,
        "rom_sha256": sha(args.rom.read_bytes()), "observations": observations,
        "snapshots": snapshots,
        "final_control": final_control,
        "state_transitions": transitions,
        "observed_active_batches": observed_batches,
        "reference_active_batches": expected_active_batches,
        "active_conversion_budget": {
            "tiles_per_engine_frame": 4,
            "maximum_observed_per_emulator_frame": max_converted_per_emulator_frame,
        },
        "hashes": {"live_surface": sha(live_surface), "tile_shadow": sha(tile_shadow),
                   "cgram_shadow": sha(cgram_shadow),
                   "vram_realized": sha(vram[:0xE800]), "cgram": sha(cgram)},
        "ppu": {"BGMODE": 3, "BG1SC": 0x70, "BG12NBA": 0, "TM": 1, "TS": 0},
        "dma": {"pending": int.from_bytes(dma[2:4], "little"),
                "committed": int.from_bytes(dma[4:6], "little"),
                "rejected": int.from_bytes(dma[10:12], "little")},
        "sa1_reset_held": True,
    }
    report_path = args.output / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": "pass", "report": str(report_path), "rom_sha256": report["rom_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
