#!/usr/bin/env python3
"""Fresh-emulator Phase 6J walkActorTo/wait closure gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")


def u16(data: bytes, offset: int = 0) -> int:
    return int.from_bytes(data[offset:offset + 2], "little")


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=NEXEN)
    parser.add_argument("--port", type=int, default=44380)
    parser.add_argument("--frames", type=int, default=1200)
    parser.add_argument("--sa1", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as ms
    ms.validate_mesen_build = lambda _: None
    args.output.mkdir(parents=True, exist_ok=True)
    stable = ("pc", "k", "a", "x", "y", "sp", "d", "dbr", "ps", "emulationMode")
    with ms.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=4, socket_timeout=120,
        stderr_log=args.output / "nexen-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        sa1_before = session.get_cpu_state("Sa1") if args.sa1 else None
        result = session.run_frames(args.frames)
        require(result["framesAdvanced"] == args.frames and not result["timedOut"], "run timeout")
        core = session.read_memory("snesMemory", 0x7E2300, 8)
        variables = session.read_memory("snesMemory", 0x7E0800, 1600)
        position = session.read_memory("snesMemory", 0x7FF1A4, 4)
        moving = session.read_memory("snesMemory", 0x7FF221, 1)[0]
        walkbox = session.read_memory("snesMemory", 0x7FFDA6, 1)[0]
        destination_box = session.read_memory("snesMemory", 0x7FFDC6, 1)[0]
        destination_x = u16(session.read_memory("snesMemory", 0x7FFDE7, 2))
        destination_y = u16(session.read_memory("snesMemory", 0x7E7BAC, 2))
        current_box = session.read_memory("snesMemory", 0x7E7BEB, 1)[0]
        final_direction = session.read_memory("snesMemory", 0x7E7E8B, 1)[0]
        facing = u16(session.read_memory("snesMemory", 0x7E78F2, 2))
        waits = session.read_memory("snesMemory", 0x7E7EBB, 4)
        room = session.read_memory("snesMemory", 0x7FD403, 1)[0]
        sa1_after = session.get_cpu_state("Sa1") if args.sa1 else None

    sa1_unchanged = True if not args.sa1 else all(
        sa1_before[key] == sa1_after[key] for key in stable
    )
    evidence = {
        "format": "same-phase6j-walk-actor-to-evidence",
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "room": room,
        "var1": u16(variables, 2),
        "var119": u16(variables, 238),
        "var120": u16(variables, 240),
        "var121": u16(variables, 242),
        "actor1": {
            "position": [u16(position), u16(position, 2)],
            "moving": moving,
            "walkbox": walkbox,
            "destination": [destination_x, destination_y],
            "destination_box": destination_box,
            "current_box": current_box,
            "final_direction": final_direction,
            "facing": facing,
        },
        "wait_totals": {"blocks": u16(waits), "releases": u16(waits, 2)},
        "next_blocker": {
            "instruction_pc": 0x02D9,
            "continuation_pc": u16(core),
            "opcode": core[6],
            "error": core[3],
        },
        "sa1_unchanged": sa1_unchanged,
    }
    require(room == 49 and evidence["var1"] == 1, "authentic actor/room differs")
    require(evidence["actor1"] == {
        "position": [31, 38], "moving": 0, "walkbox": 1,
        "destination": [31, 38], "destination_box": 1,
        "current_box": 1, "final_direction": 0xFF, "facing": 270,
    }, "walk closure differs")
    require((evidence["var119"], evidence["var120"], evidence["var121"]) == (0, 0xFFFF, 0), "dense globals regressed")
    require(evidence["wait_totals"] == {"blocks": 95, "releases": 2}, "wait closure differs")
    require((u16(core), core[6], core[3]) == (0x02DE, 0x4C, 25), "next blocker differs")
    require(sa1_unchanged, "SA-1 state changed")
    (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
