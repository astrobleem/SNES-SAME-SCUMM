#!/usr/bin/env python3
"""Copyright-free SNES conformance for production v5 object-script execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
LEGACY_VARIABLES = 0x7E2320
SLOT_STATUS = 0x7E2380
SLOT_NUMBER = 0x7E2399
SLOT_WHERE = 0x7E7F46
SLOT_OBJECT = 0x7E7F5F
SLOT_PC = 0x7E23E4
START_OBJECT = 0x7E7F91
START_TRACE_COUNT = 0x7E7ED7
START_TRACE = 0x7E7ED8
ERROR = 0x7E2303
NEST_DEPTH = 0x7FF465


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45725)
    args = parser.parse_args()
    if not args.nexen.is_file() or not os.access(args.nexen, os.X_OK):
        raise RuntimeError("Nexen unavailable")
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=2.0, socket_timeout=60.0,
        stderr_log=args.output.with_suffix(".stderr.log"),
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        for frame in range(1, 180):
            session.run_frames(1)
            variables = session.read_memory("snesMemory", LEGACY_VARIABLES, 32)
            error = session.read_memory("snesMemory", ERROR, 1)[0]
            if error or all(u16(variables, index * 2) for index in range(10, 14)):
                break
        start = session.read_memory("snesMemory", START_OBJECT, 22)
        nest_depth = session.read_memory("snesMemory", NEST_DEPTH, 1)[0]
        status = session.read_memory("snesMemory", SLOT_STATUS, 25)
        numbers = session.read_memory("snesMemory", SLOT_NUMBER, 25)
        wheres = session.read_memory("snesMemory", SLOT_WHERE, 25)
        objects = session.read_memory("snesMemory", SLOT_OBJECT, 50)
        pcs = session.read_memory("snesMemory", SLOT_PC, 50)
        trace_count = session.read_memory("snesMemory", START_TRACE_COUNT, 1)[0]
        trace_raw = session.read_memory(
            "snesMemory", START_TRACE, min(trace_count, 16) * 4
        )
        trace = [list(trace_raw[index:index + 4])
                 for index in range(0, len(trace_raw), 4)]
    slots = [{
        "slot": index, "status": status[index], "number": numbers[index],
        "where": wheres[index], "object": u16(objects, index * 2),
        "pc": u16(pcs, index * 2),
    } for index in range(25) if status[index] or numbers[index] or wheres[index]]
    observed = [u16(variables, index * 2) for index in range(10, 14)]
    assertions = {
        "distinct_programs": observed == [0xA00A, 0xA008, 0xA0FF, 0xB00A],
        "four_object_programs_executed": start[12] == 4,
        "missing_entry_did_not_fault": error == 0,
        "missing_entry_did_not_leave_object_slot": all(
            item["where"] != 1 for item in slots
        ),
        "nested_depth_returned_to_zero": nest_depth == 0,
    }
    if not all(assertions.values()):
        raise RuntimeError(
            f"startObject conformance failed: {assertions}; values={observed}; "
            f"exec={start[12]}; depth={nest_depth}; slots={slots}; trace={trace}"
        )
    report = {
        "gate": "M25-startObject-copyright-free-SNES",
        "result": "pass", "fresh_power_on": True, "debugger_writes": 0,
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "frame": frame, "variables_10_13": observed,
        "start_object_exec_count": start[12], "slots": slots,
        "trace_count": trace_count, "trace": trace, "assertions": assertions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
