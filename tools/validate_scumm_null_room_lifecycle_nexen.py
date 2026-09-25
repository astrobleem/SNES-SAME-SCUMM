#!/usr/bin/env python3
"""Native M23A control for resource-less room-zero outgoing cleanup."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/"
    "linux-x64/publish/Nexen"
)
ROOM = 0x7FF2BF
PHASE = 0x7FF2C2
ACTIVE_RECORD = 0x7FF2BE
REQUEST_COUNT = 0x7FF2C5
VALIDATION_COUNT = 0x7FF2C6
EXIT_COUNT = 0x7FF2CA
ERROR = 0x7E2303
LIFECYCLE = 0x7E2221
VARIABLES = 0x7E0800
STATUS = 0x7E2380
NUMBER = 0x7E2399
PROGRAM = 0x7E23B2
WHERE = 0x7E7F46
SLOT_ROOMS = 0x7FF2E7
LOCALS = 0x7E2448
SLOT_STRIDE = 0x40
SCUMM_VM_STOPPED = 4
SCUMM_WIO_GLOBAL = 2


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45751)
    args = parser.parse_args()
    require(args.rom.is_file() and args.manifest.is_file(), "ROM or manifest missing")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    manifest = json.loads(args.manifest.read_text())
    require(manifest.get("case") == "null-room-lifecycle", "wrong native fixture case")
    require(manifest.get("room_provenance", "").startswith("synthetic fixture"),
            "fixture provenance must remain explicit")
    require({item["number"] for item in manifest["global_scripts"]} >= {75},
            "fixture Global75 body is absent")

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None

    snapshots: list[dict[str, object]] = []
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=2.0, socket_timeout=60.0,
        stderr_log=args.output.with_suffix(".stderr.log"),
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0, "power reset not at frame zero")
        reached_null = False
        for frame in range(1, 121):
            result = session.run_frames(1)
            require(result["framesAdvanced"] == 1 and not result["timedOut"],
                    f"frame did not advance: {result}")
            state = {
                "frame": frame,
                "room": session.read_memory("snesMemory", ROOM, 1)[0],
                "phase": session.read_memory("snesMemory", PHASE, 1)[0],
                "active_record": session.read_memory("snesMemory", ACTIVE_RECORD, 1)[0],
                "requests": session.read_memory("snesMemory", REQUEST_COUNT, 1)[0],
                "validations": session.read_memory("snesMemory", VALIDATION_COUNT, 1)[0],
                "exits": session.read_memory("snesMemory", EXIT_COUNT, 1)[0],
                "error": session.read_memory("snesMemory", ERROR, 1)[0],
                "lifecycle": session.read_memory("snesMemory", LIFECYCLE, 1)[0],
                "variables": [u16(session.read_memory(
                    "snesMemory", VARIABLES, 44), index * 2) for index in (11, 12, 20)],
            }
            snapshots.append(state)
            require(state["error"] == 0, f"SCUMM error ${state['error']:02X} at frame {frame}")
            if state["room"] == 0 and state["phase"] == 0 and state["exits"] == 1:
                reached_null = True
                break

        require(reached_null, f"resource-less room 0 did not settle: {snapshots[-1]}")
        before = snapshots[-1]
        statuses = session.read_memory("snesMemory", STATUS, 25)
        numbers = session.read_memory("snesMemory", NUMBER, 25)
        programs = session.read_memory("snesMemory", PROGRAM, 25)
        where = session.read_memory("snesMemory", WHERE, 25)
        owners = session.read_memory("snesMemory", SLOT_ROOMS, 25)
        locals_raw = session.read_memory("snesMemory", LOCALS, 25 * SLOT_STRIDE)
        slots = [{
            "slot": slot, "number": numbers[slot], "program": programs[slot],
            "status": statuses[slot], "where": where[slot],
            "room_owner": owners[slot],
            "local0": u16(locals_raw, slot * SLOT_STRIDE),
        } for slot in range(25) if statuses[slot] != 0 or numbers[slot] != 0]
        local_old = [slot for slot in slots if slot["number"] == 200]
        globals75 = [slot for slot in slots if slot["number"] == 75
                     and slot["where"] == SCUMM_WIO_GLOBAL]
        for _ in range(8):
            session.run_frames(1)
        after = {
            "room": session.read_memory("snesMemory", ROOM, 1)[0],
            "phase": session.read_memory("snesMemory", PHASE, 1)[0],
            "active_record": session.read_memory("snesMemory", ACTIVE_RECORD, 1)[0],
            "requests": session.read_memory("snesMemory", REQUEST_COUNT, 1)[0],
            "validations": session.read_memory("snesMemory", VALIDATION_COUNT, 1)[0],
            "exits": session.read_memory("snesMemory", EXIT_COUNT, 1)[0],
            "error": session.read_memory("snesMemory", ERROR, 1)[0],
            "lifecycle": session.read_memory("snesMemory", LIFECYCLE, 1)[0],
            "variables": [u16(session.read_memory(
                "snesMemory", VARIABLES, 44), index * 2) for index in (11, 12, 20)],
        }
        global_status = [session.read_memory(
            "snesMemory", STATUS + item["slot"], 1)[0] for item in globals75]

    checks = {
        "resource_less_room_zero_installed": (
            before["room"] == after["room"] == 0
            and before["active_record"] == after["active_record"] == 0xFF
        ),
        "old_exit_executed_exactly_once": before["exits"] == after["exits"] == 1
            and before["variables"][1] == after["variables"][1] == 1,
        "old_room_local_retired": not local_old and before["variables"][0] == 1
            and after["variables"][0] == 1,
        "legitimate_global_survives_and_runs": bool(globals75)
            and all(value not in (0, SCUMM_VM_STOPPED) for value in global_status)
            and after["variables"][2] > before["variables"][2],
        "room_zero_did_not_issue_storage_read": before["requests"] == 2
            and after["requests"] == 2
            and before["validations"] == after["validations"] == 1,
        "engine_remains_healthy": after["error"] == 0 and after["lifecycle"] == 2
            and after["phase"] == 0,
    }
    require(all(checks.values()),
            f"null-room lifecycle assertions failed: {checks}; "
            f"before={before}; slots={slots}; global_status={global_status}; after={after}")
    report = {
        "gate": "M23A-resource-less-room-zero-outgoing-lifecycle",
        "result": "pass", "evidence_kind": "fresh-power-on-Nexen-native-execution",
        "debugger_state_writes": 0,
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "synthetic_fixture": True,
        "checks": checks, "timeline": snapshots,
        "slots_after_commit": slots, "global75_status_after_commit": global_status,
        "after_eight_more_frames": after,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"SNES resource-less room-zero lifecycle: PASS ({args.output})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
