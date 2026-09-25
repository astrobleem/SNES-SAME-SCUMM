#!/usr/bin/env python3
"""Fresh-emulator proof for the integrated production SCUMM scheduler pass."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from validate_scumm_m25a_nested_nexen import snapshot, step


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
LEGACY_VARIABLES = 0x7E2320
EXTENDED_VARIABLES = 0x7FF500


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def u16(raw: bytes) -> int:
    return raw[0] | raw[1] << 8


def variable(session: object, number: int) -> int:
    base = LEGACY_VARIABLES if number < 16 else EXTENDED_VARIABLES
    return u16(session.read_memory("snesMemory", base + number * 2, 2))


def values(session: object) -> dict[str, int]:
    return {str(number): variable(session, number) for number in (
        10, 11, 12, 13, 14, 20, 21, 22, 23, 24, 25,
    )}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45388)
    args = parser.parse_args()
    require(args.rom.is_file() and args.manifest.is_file(), "validator input missing")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    manifest = json.loads(args.manifest.read_text())
    scripts = {item["number"]: item for item in manifest["records"][0]["scripts"]
               if item["kind"] == "LSCR"}
    require(list(scripts) == [200, 201, 202, 203, 204],
            f"generated local directory differs: {list(scripts)}")

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    states: list[dict[str, object]] = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=2.0, socket_timeout=60.0,
        stderr_log=args.output.parent / "scheduler-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        initialized = False
        for frame in range(1, 61):
            step(session)
            state = snapshot(session)
            if not initialized:
                initialized = state["trace_count"] == 0
                continue
            scheduler = [item for item in state["trace"] if item["event"] == 5]
            if state["trace_count"] >= 18:
                states.append({"video_frame": frame, "state": state,
                               "variables": values(session)})
            if len(scheduler) == 4 and state["active_count"] == 0:
                break
        else:
            raise RuntimeError("scheduler fixture did not complete")

    first = next(item for item in states
                 if item["state"]["trace_count"] == 20)
    pass_one = next(item for item in states
                    if len([x for x in item["state"]["trace"] if x["event"] == 5]) == 3)
    final = states[-1]
    immediate = first["state"]["trace"]
    scheduler = [item for item in final["state"]["trace"] if item["event"] == 5]
    require([(x["slot"], x["program"], x["pc"]) for x in scheduler]
            == [(1, 0xD2, 19), (2, 0xD3, 11), (3, 0xD4, 11), (3, 0xD4, 17)],
            f"canonical pass/slot order differs: {scheduler}")
    require(not any(x["event"] == 5 for x in immediate),
            "a yielded immediate child ran twice in its creation pass")
    require(first["variables"] == {
        "10": 0xA, "11": 0xB, "12": 0xD, "13": 0, "14": 0,
        "20": 0x20, "21": 0, "22": 0, "23": 0x30,
        "24": 0x40, "25": 0,
    }, f"immediate execution state differs: {first['variables']}")
    require(pass_one["variables"]["13"] == 0xF
            and pass_one["variables"]["14"] == 0xE
            and pass_one["variables"]["21"] == 0x21,
            f"first scheduler-pass continuation differs: {pass_one['variables']}")
    require(final["variables"]["22"] == 0x22 and final["variables"]["25"] == 0,
            f"repeat/stopped continuation differs: {final['variables']}")
    require(final["state"]["error"] == 0 and final["state"]["active_count"] == 0,
            "fixture did not retire every completed slot cleanly")
    require(final["state"]["slots"][1]["locals"][0] == 0xA0A0
            and final["state"]["slots"][2]["locals"][0] == 0xB0B0
            and final["state"]["slots"][3]["locals"][0] == 0xC0C0,
            "parent/child/repeated-script locals were corrupted")
    require(not any(x["event"] == 5 and x["program"] in {0xD5, 0xD6}
                    for x in final["state"]["trace"]),
            "terminated or explicitly stopped child resumed")

    report = {
        "gate": "M25-integrated-production-scheduler-pass",
        "result": "pass", "fresh_power_on": True, "debugger_writes": 0,
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "generated_scripts": scripts,
        "states": states,
        "scheduler_order": [(x["slot"], x["program"], x["pc"]) for x in scheduler],
        "claims": {
            "immediate_child_once": True, "ascending_slot_order": True,
            "three_yielded_slots": True, "stopped_child_not_resumed": True,
            "terminating_child_not_resumed": True, "repeated_break_here": True,
            "independent_locals": True,
        },
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output),
                      "rom_sha256": report["rom_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
