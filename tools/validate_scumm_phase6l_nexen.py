#!/usr/bin/env python3
"""Fresh-emulator Phase 6L semantic room-transition evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")


def u16(raw: bytes, at: int = 0) -> int:
    return int.from_bytes(raw[at:at + 2], "little")


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", 0x7E2300, 0x64)
    room = session.read_memory("snesMemory", 0x7FF2BE, 0x42)
    load = session.read_memory("snesMemory", 0x7E7FCC, 0x0E)
    slots = session.read_memory("snesMemory", 0x7E2380, 25)
    numbers = session.read_memory("snesMemory", 0x7E2399, 25)
    programs = session.read_memory("snesMemory", 0x7E23B2, 25)
    pcs = session.read_memory("snesMemory", 0x7E23E4, 50)
    variables = session.read_memory("snesMemory", 0x7E0800, 1600)
    positions = session.read_memory("snesMemory", 0x7FF1A4, 128)
    moving = session.read_memory("snesMemory", 0x7FF220, 32)
    walkbox = session.read_memory("snesMemory", 0x7FFDA5, 32)
    sound_count = session.read_memory("snesMemory", 0x7FD459, 1)[0]
    sound_pending = session.read_memory("snesMemory", 0x7FD8AC, 1)[0]
    sound_command = session.read_memory("snesMemory", 0x7FD8ED, 1)[0]
    sound_word = session.read_memory("snesMemory", 0x7FD8F1, 1)[0]
    return {
        "frame": session.get_state()["frameCount"], "pc": u16(common),
        "status": common[2], "error": common[3], "opcode": common[6],
        "program": common[0x62], "room": room[1], "record": room[0],
        "room_phase": room[4], "room_hold": room[6],
        "requests": room[7], "validations": room[8], "retirements": room[10],
        "entries": room[11], "exits": room[12],
        "lifecycle": list(room[25:25 + min(room[24], 14)]),
        "load": {"active": load[0], "object": u16(load, 1), "room": load[3],
                 "x": u16(load, 4), "y": u16(load, 6), "pc_after": u16(load, 8),
                 "caller_slot": load[10], "caller_program": load[11],
                 "previous_room": load[12], "ego": load[13]},
        "vars": {"ego": u16(variables, 2), "room": u16(variables, 8),
                 "walkto": u16(variables, 76), "previous224": u16(variables, 448),
                 "v119": u16(variables, 238), "v120": u16(variables, 240),
                 "v121": u16(variables, 242)},
        "actor1": {"x": u16(positions, 4), "y": u16(positions, 6),
                   "moving": moving[1], "walkbox": walkbox[1]},
        "sound_queue": {"count": sound_count, "pending": sound_pending,
                        "word_index": sound_word, "command_index": sound_command},
        "slots": [{"slot": i, "status": slots[i], "number": numbers[i],
                   "program": programs[i], "pc": u16(pcs, i * 2)}
                  for i in range(25) if slots[i] or numbers[i] or programs[i]],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--nexen", type=Path, default=NEXEN)
    ap.add_argument("--port", type=int, default=44420)
    ap.add_argument("--frames", type=int, default=1800)
    args = ap.parse_args()
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as ms
    ms.validate_mesen_build = lambda _: None
    args.output.mkdir(parents=True, exist_ok=True)
    trace: list[dict[str, object]] = []
    with ms.McpSession(rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
            port=args.port, boot_wait=4, socket_timeout=120,
            stderr_log=args.output / "nexen-stderr.log") as session:
        session.pause(); session.tool("reset_emulator", {"power": True}); session.pause()
        previous = None
        for _ in range(args.frames // 5):
            session.run_frames(5)
            state = snapshot(session)
            key = (state["room"], state["room_phase"], state["load"]["active"],
                   state["program"], state["pc"], state["error"],
                   state["actor1"]["x"], state["actor1"]["y"])
            if key != previous:
                trace.append(state); previous = key
            if state["error"] or (state["room"] == 63 and state["room_phase"] == 0
                                  and state["actor1"]["moving"] == 0 and state["frame"] > 1100):
                break
    report = {"gate": "phase6l-load-room-with-ego", "rom_sha256":
              hashlib.sha256(args.rom.read_bytes()).hexdigest(), "trace": trace,
              "final": trace[-1]}
    (args.output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report["final"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
