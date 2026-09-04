#!/usr/bin/env python3
"""Fresh-emulator Phase 6H-A global-script delivery/lifecycle gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
SCUMM = 0x7E2300
STATUS = 0x7E2380
NUMBER = 0x7E2399
PROGRAM = 0x7E23B2
PC = 0x7E23E4
HOLD = 0x7FF2C4
NEST_DEPTH = 0x7FF465
HIGH_VARIABLES = 0x7FF500


def u16(data: bytes, offset: int = 0) -> int:
    return int.from_bytes(data[offset:offset + 2], "little")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=NEXEN)
    parser.add_argument("--manifest", type=Path, default=ROOT / "build/m23a-rooms/authentic/manifest.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=44321)
    parser.add_argument("--frames", type=int, default=1250)
    parser.add_argument("--sa1", action="store_true")
    args = parser.parse_args()
    require(args.rom.is_file(), "ROM unavailable")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    manifest = json.loads(args.manifest.read_text())
    script = next(item for item in manifest["global_scripts"] if item["number"] == 14)
    require(script["length"] == 258, "script 14 length differs")
    require(script["sha256"] == "ee6b379d25e4ace9772673b05bb40d2f428dd2c0bd9142a8f53d85005fb4e371",
            "script 14 identity differs")
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    args.output.mkdir(parents=True, exist_ok=True)
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT, port=args.port,
        boot_wait=2.0, socket_timeout=120.0,
        stderr_log=args.output / "nexen-stderr.log",
    ) as session:
        session.pause(); session.tool("reset_emulator", {"power": True}); session.pause()
        sa1_start = session.get_cpu_state("Sa1") if args.sa1 else None
        run = session.run_frames(args.frames)
        require(run["framesAdvanced"] == args.frames and not run["timedOut"], "frame timeout")
        core = session.read_memory("snesMemory", SCUMM, 8)
        statuses = session.read_memory("snesMemory", STATUS, 25)
        numbers = session.read_memory("snesMemory", NUMBER, 25)
        programs = session.read_memory("snesMemory", PROGRAM, 25)
        pcs = session.read_memory("snesMemory", PC, 50)
        hold = session.read_memory("snesMemory", HOLD, 1)[0]
        depth = session.read_memory("snesMemory", NEST_DEPTH, 1)[0]
        var120 = u16(session.read_memory("snesMemory", HIGH_VARIABLES + 120 * 2, 2))
        sa1_end = session.get_cpu_state("Sa1") if args.sa1 else None
    parent = next((index for index in range(25)
                   if numbers[index] == 2 and programs[index] == 0xEC), None)
    child = next((index for index in range(25) if programs[index] == 0xED), None)
    require(parent is not None, "parent global script 2 slot unavailable")
    require(child is not None, "script 14 slot evidence unavailable")
    require(pcs[parent * 2:parent * 2 + 2] == b"\x6b\x04", "parent was not restored at $046B")
    require(statuses[parent] == 2, "parent is not canonically yielded at the profile gate")
    require(statuses[child] == 4 and u16(pcs, child * 2) == 0x0102,
            "script 14 did not terminate at its complete payload end")
    require(hold == 1, "profile execution gate did not hold")
    require(var120 == 0, "Var[120] changed during Phase 6H-A")
    require(core[4] == 0, "VM error is nonzero")
    stable = ("pc", "k", "a", "x", "y", "sp", "d", "dbr", "ps", "emulationMode")
    sa1_unchanged = (True if not args.sa1 else
                     {key: sa1_start[key] for key in stable} ==
                     {key: sa1_end[key] for key in stable})
    require(sa1_unchanged, "SA-1 architectural state changed")
    evidence = {
        "format": "same-phase6ha-global-script14-evidence",
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "script14": {**script, "program": 0xED, "entry_pc": 0,
                     "terminal_pc": u16(pcs, child * 2), "slot": child,
                     "status": statuses[child]},
        "parent": {"slot": parent, "number": numbers[parent], "program": programs[parent],
                   "pc": u16(pcs, parent * 2), "status": statuses[parent]},
        "hold": hold, "nested_depth": depth, "var120": var120,
        "vm": {"pc": u16(core), "status": core[3], "error": core[4], "opcode": core[5]},
        "sa1_unchanged": sa1_unchanged,
    }
    (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
