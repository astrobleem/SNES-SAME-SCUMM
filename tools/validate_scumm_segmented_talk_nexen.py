#!/usr/bin/env python3
"""Fresh-emulator Phase 6G-B segmented-talk and BG2 evidence gate."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from same.snes_video_overlay import decode_bg2_mask
NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
TALK = 0x7E7A20
SCUMM = 0x7E2300
OVERLAY = 0x41F000
OVERLAY_WORK = 0x41F614
OVERLAY_ACTIVE = 0x41F58C
FRAME_COUNTER = 0x7E2210


def u16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 2], "little")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=NEXEN)
    parser.add_argument("--output", type=Path, default=ROOT / "build/phase6gb-segmented-talk")
    parser.add_argument("--port", type=int, default=44207)
    parser.add_argument("--frames", type=int, default=1800)
    parser.add_argument("--semantic-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    require(args.rom.is_file(), "ROM unavailable")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None

    timeline: list[dict[str, object]] = []
    cpu_tail: list[dict[str, object]] = []
    captures: dict[str, dict[str, object]] = {}
    previous: tuple[int, ...] | None = None
    sa1_start: dict[str, object]
    sa1_end: dict[str, object]
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT, port=args.port,
        boot_wait=2.0, socket_timeout=90.0, stderr_log=args.output / "nexen-stderr.log",
    ) as session:
        session.pause(); session.tool("reset_emulator", {"power": True}); session.pause()
        sa1_start = {} if args.semantic_only else session.get_cpu_state("Sa1")
        for frame in range(1, args.frames + 1):
            run = session.run_frames(1)
            require(run["framesAdvanced"] == 1 and not run["timedOut"], "frame timeout")
            talk = session.read_memory("snesMemory", TALK, 0xAD)
            work = (bytes(0x40) if args.semantic_only else
                    session.read_memory("snesMemory", OVERLAY_WORK, 0x40))
            scumm = session.read_memory("snesMemory", SCUMM, 0x20)
            kernel_frame = u16(session.read_memory("snesMemory", FRAME_COUNTER, 2), 0)
            stage_frames = tuple(u16(session.read_memory("snesMemory", OVERLAY_WORK + 0xB2, 0x16), i)
                                 for i in range(0, 0x16, 2)) if not args.semantic_only else (0,) * 11
            stage_edges = tuple(u16(session.read_memory("snesMemory", OVERLAY_WORK + 0xC8, 0x10), i)
                                for i in range(0, 0x10, 2)) if not args.semantic_only else (0,) * 8
            state = (
                talk[0], talk[1], talk[2], u16(talk, 4), talk[0xA1], talk[0xA2],
                talk[0xA3], talk[0xA5], talk[0xA7], talk[0xAA], talk[0xAB],
                work[0], u16(work, 2), u16(work, 6), work[0x0A], work[0x0B],
                u16(scumm, 0), scumm[3], scumm[4], kernel_frame, *stage_frames, *stage_edges,
            )
            if state != previous:
                row = {
                    "frame": frame, "active": state[0], "have_msg": state[1],
                    "actor": state[2], "delay": state[3], "cursor": state[4],
                    "segment_start": state[5], "segment_length": state[6],
                    "segment_index": state[7], "visual_status": state[8],
                    "actor_frame": state[9], "continue_count": state[10],
                    "overlay_state": state[11], "overlay_generation": state[12],
                    "overlay_committed": state[13], "overlay_active_cells": state[14],
                    "overlay_pending_cells": state[15],
                    "pc": state[16], "vm_status": state[17], "vm_error": state[18],
                    "kernel_frame": state[19],
                    "stages": dict(zip(("S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S11"), state[20:])),
                    "stage_edges": dict(zip(("S6_entry", "S6_exit", "S7_entry", "S7_exit",
                                              "S8_entry", "S8_exit", "S9_entry", "S9_exit"),
                                             state[31:])),
                }
                timeline.append(row)
                previous = state
            if frame >= max(1, args.frames - 40):
                cpu = session.get_cpu_state("Snes")
                cpu_tail.append({"frame": frame, "pc": cpu["pc"], "k": cpu["k"],
                                 "sp": cpu["sp"], "ps": cpu["ps"]})
            committed = u16(work, 6)
            # Generations 1/2 belong to the earlier authentic actor-1 message.
            # The actor-2 segmented line owns generations 3/4/5.
            label = None if args.semantic_only else {3: "segment1", 4: "segment2", 5: "hidden"}.get(committed)
            if label and label not in captures and work[0] == 0:
                vram = session.read_memory("snesVideoRam", 0, 0x10000)
                screenshot = base64.b64decode(session.take_screenshot(format="base64")["base64"])
                path = args.output / f"{label}.png"
                path.write_bytes(screenshot)
                mask = decode_bg2_mask(vram[0xE800:0x10000], vram[0xF800:0x10000])
                mask_image = Image.frombytes("L", (256, 224), bytes(value * 255 for value in mask)).convert("RGB")
                mask_path = args.output / f"{label}-mask.png"
                mask_image.save(mask_path)
                pixels = session.read_memory("snesMemory", 0x41F020, 0x280)
                tile_stage = session.read_memory("snesMemory", 0x41F2A0, 0x2C0)
                captures[label] = {
                    "frame": frame, "screenshot_sha256": sha(screenshot),
                    "bg2_char_sha256": sha(vram[0xE800:0xF800]),
                    "bg2_tilemap_sha256": sha(vram[0xF800:0x10000]),
                    "mask_index8_sha256": sha(mask),
                    "mask_png_sha256": sha(mask_path.read_bytes()),
                    "mask_pixels": sum(mask),
                    "active_cells": work[0x0A],
                    "pending_cells_count": work[0x0B],
                    "cells": list(session.read_memory("snesMemory", OVERLAY_ACTIVE, work[0x0A] * 2)),
                    "descriptor": list(session.read_memory("snesMemory", 0x41F000, 0x20)),
                    "pixel_sha256": sha(pixels),
                    "nonzero_pixels": sum(value != 0 for value in pixels),
                    "nonzero_positions": [i for i, value in enumerate(pixels) if value],
                    "tile_stage_sha256": sha(tile_stage),
                    "tile_stage_nonzero": sum(value != 0 for value in tile_stage),
                }
            visual_done = args.semantic_only or (committed >= 5 and work[0] == 0)
            if talk[0] == 0 and u16(scumm, 0) > 0x0296 and visual_done:
                break
        sa1_end = {} if args.semantic_only else session.get_cpu_state("Sa1")
        snes_end = session.get_cpu_state("Snes")
        final_talk = session.read_memory("snesMemory", TALK, 0xAD)
        final_scumm = session.read_memory("snesMemory", SCUMM, 0x20)
        final_work = (bytes(0x40) if args.semantic_only else
                      session.read_memory("snesMemory", OVERLAY_WORK, 0x40))
        final_hw = session.read_memory("snesMemory", 0x4200, 1)
        final_kernel_frame = session.read_memory("snesMemory", 0x7E2200, 2)
        engine_host = session.read_memory("snesMemory", 0x7E2220, 0x12)
        final_producer = session.read_memory("snesMemory", OVERLAY_WORK + 0x80, 0x20)
        trace_tail = session.tool("trace_log", {"count": 200, "cpuType": "Snes"})
        slot_status = session.read_memory("snesMemory", 0x7E2380, 25)
        slot_number = session.read_memory("snesMemory", 0x7E2399, 25)
        slot_program = session.read_memory("snesMemory", 0x7E23B2, 25)
        slot_pc = session.read_memory("snesMemory", 0x7E23E4, 50)
        current_slot = session.read_memory("snesMemory", 0x7E2A88, 1)[0]
        error_site = session.read_memory("snesMemory", 0x7FF466, 1)[0]

    stable = ("pc", "k", "a", "x", "y", "sp", "d", "dbr", "ps", "emulationMode")
    evidence = {
        "format": "same-phase6gb-segmented-talk-evidence", "rom_sha256": sha(args.rom.read_bytes()),
        "timeline": timeline, "captures": captures,
        "cpu_tail": cpu_tail,
        "final": {"talk_active": final_talk[0], "have_msg": final_talk[1],
                  "start_count": final_talk[9], "stop_count": final_talk[10],
                  "continue_count": final_talk[0xAB], "pc": u16(final_scumm, 0),
                  "vm_status": final_scumm[3], "vm_error": final_scumm[4],
                  "overlay_committed": u16(final_work, 6)},
        "sa1_unchanged": (True if args.semantic_only else
                          {key: sa1_start[key] for key in stable} ==
                          {key: sa1_end[key] for key in stable}),
        "snes_end": snes_end,
        "overlay_scratch": list(final_work),
        "producer_scratch": list(final_producer),
        "trace_tail": trace_tail,
        "nmitimen": final_hw[0], "kernel_frame": u16(final_kernel_frame, 0),
        "engine_host": list(engine_host),
        "current_slot": current_slot,
        "error_site": error_site,
        "slots": [{"slot": i, "status": slot_status[i], "number": slot_number[i],
                   "program": slot_program[i], "pc": u16(slot_pc, i * 2)}
                  for i in range(25) if slot_status[i] or slot_number[i] or slot_program[i]],
    }
    (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence["final"], sort_keys=True))
    print(f"timeline transitions: {len(timeline)} captures: {sorted(captures)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
