#!/usr/bin/env python3
"""Fresh-emulator proof for complete generated room-local LSCR lookup."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from validate_scumm_m25_authentic_next_nexen import snapshot


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
COMPACT_VARIABLES = 0x7E2320
EXTENDED_VARIABLES = 0x7FF500


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def word(raw: bytes, index: int) -> int:
    return raw[index * 2] | raw[index * 2 + 1] << 8


def variables(session: object) -> dict[str, int]:
    compact = session.read_memory("snesMemory", COMPACT_VARIABLES, 32)
    extended = session.read_memory("snesMemory", EXTENDED_VARIABLES, 64)
    return {
        "10": word(compact, 10),
        **{str(index): word(extended, index) for index in (20, 21, 22, 28)},
    }


def reset(session: object) -> None:
    session.pause()
    session.tool("reset_emulator", {"power": True})
    session.pause()
    require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")


def run_valid(rom: Path, nexen: Path, port: int, output: Path) -> dict[str, object]:
    import mesen_mcp.session as mcp_session
    before = after = None
    with mcp_session.McpSession(
        rom=rom, mesen=nexen, cwd=ROOT, port=port, boot_wait=2.0,
        socket_timeout=90.0, stderr_log=output / "lookup-stderr.log",
    ) as session:
        reset(session)
        for frame in range(1, 31):
            session.run_frames(1)
            state = snapshot(session, frame)
            values = variables(session)
            if state["active_room"] == 49 and before is None:
                before = {"frame": frame, "state": state, "variables": values}
            if values == {"10": 0x10, "20": 0x200, "21": 0x201,
                          "22": 0x202, "28": 0x208}:
                after = {"frame": frame, "state": state, "variables": values}
                break
            require(not state["error"], f"valid lookup fixture faulted: {state}")
    require(before is not None and before["variables"] == {
        "10": 0, "20": 0, "21": 0, "22": 0, "28": 0,
    }, f"LSCR was automatically scheduled: {before}")
    require(after is not None, "not every generated global/local program executed")
    programs = {
        item["program"] for item in after["state"]["slots"] if item["slot"] != 0
    }
    require(programs == {0xD2, 0xD3, 0xD4, 0xD5, 0xD6},
            f"distinct generated programs alias: {programs}")
    return {"fresh_power_on": True, "before_explicit_start": before,
            "after_explicit_starts": after, "resolved_programs": sorted(programs)}


def run_missing(rom: Path, nexen: Path, port: int, output: Path) -> dict[str, object]:
    import mesen_mcp.session as mcp_session
    fault = None
    with mcp_session.McpSession(
        rom=rom, mesen=nexen, cwd=ROOT, port=port, boot_wait=2.0,
        socket_timeout=90.0, stderr_log=output / "missing-stderr.log",
    ) as session:
        reset(session)
        for frame in range(1, 31):
            session.run_frames(1)
            state = snapshot(session, frame)
            if state["error"]:
                fault = state
                break
    require(fault is not None and fault["error"] == 0x0B
            and fault["last_opcode"] == 0x0A and fault["nest_depth"] == 0,
            f"missing local did not fail closed: {fault}")
    require(len(fault["slots"]) == 1 and fault["slots"][0]["slot"] == 0,
            f"missing lookup leaked a child slot: {fault}")
    return {"fresh_power_on": True, "fault": fault}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--missing-rom", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45371)
    args = parser.parse_args()
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    manifest = json.loads(args.manifest.read_text())
    record = manifest["records"][0]
    locals_ = [item for item in record["scripts"] if item["kind"] == "LSCR"]
    numbers = [item["number"] for item in locals_]
    require(manifest["num_global_scripts"] == 200 and numbers == [200, 201, 202, 208],
            f"generated namespace metadata differs: {numbers}")
    output = args.output.parent
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    report = {
        "gate": "M25-complete-room-local-directory-conformance", "result": "pass",
        "namespace": {"num_global_scripts": 200, "local_numbers": numbers,
                      "local_indices": [number - 200 for number in numbers]},
        "scripts": locals_,
        "valid": run_valid(args.rom.resolve(), args.nexen.resolve(), args.port, output),
        "missing": run_missing(args.missing_rom.resolve(), args.nexen.resolve(),
                               args.port + 1, output),
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "missing_rom_sha256": hashlib.sha256(args.missing_rom.read_bytes()).hexdigest(),
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
