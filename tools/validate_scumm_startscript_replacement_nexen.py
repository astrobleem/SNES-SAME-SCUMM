#!/usr/bin/env python3
"""Native control for nonrecursive same-script StartScript replacement."""

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
ERROR = 0x7E2303
LIFECYCLE = 0x7E2221
SLOT_STATUS = 0x7E2380
SLOT_NUMBER = 0x7E2399
SLOT_PROGRAM = 0x7E23B2
SLOT_PC = 0x7E23E4
SLOT_LOCALS = 0x7E2448
NEST_DEPTH = 0x7FF465
VARIABLES = 0x7E0800


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def u16(data: bytes, offset: int = 0) -> int:
    return data[offset] | data[offset + 1] << 8


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45726)
    args = parser.parse_args()
    require(args.rom.is_file() and args.manifest.is_file(), "ROM or manifest missing")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")

    manifest = json.loads(args.manifest.read_text())
    require(manifest.get("case") == "startscript-replacement",
            "wrong fixture manifest")
    source = next((item for item in manifest.get("global_scripts", [])
                   if item.get("number") == 75), None)
    require(source is not None, "fixture has no Global75 replacement body")
    body_path = args.manifest.parent / source["output"]
    body = body_path.read_bytes()
    body_sha = hashlib.sha256(body).hexdigest()
    require(len(body) == 24 and body_sha == source["sha256"],
            "Global75 fixture body differs from its manifest provenance")

    from validate_scumm_startup42_nexen import (
        mapped_cpu_address_for_rom,
        verified_symbol_map_for_rom,
    )

    verified_symbol_map_for_rom(args.rom.resolve())
    helper_address = mapped_cpu_address_for_rom(
        args.rom.resolve(), "ScummV5_C4_RunAllocatedNoParent", bank=0
    )

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None

    slot_observation: dict[str, int] | None = None
    no_parent_hits = 0
    frame = 0
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=2.0, socket_timeout=60.0,
        stderr_log=args.output.with_suffix(".stderr.log"),
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0, "cold reset failed")
        hook = session.add_exec_hook(helper_address)

        for frame in range(1, 121):
            session.run_frames(1)
            for event in session.drain_notifications(0.01):
                if (event.get("method") == "notifications/mesen/hookFired"
                        and event.get("params", {}).get("handle") == hook):
                    no_parent_hits += 1

            room = session.read_memory("snesMemory", ROOM, 1)[0]
            phase = session.read_memory("snesMemory", PHASE, 1)[0]
            error = session.read_memory("snesMemory", ERROR, 1)[0]
            lifecycle = session.read_memory("snesMemory", LIFECYCLE, 1)[0]
            require(error == 0,
                    f"runtime error before replacement checkpoint: "
                    f"room={room} phase={phase} error={error}")
            if room != manifest.get("fixture_room") or phase != 0:
                continue
            require(lifecycle == 2,
                    f"fixture room is not running at the replacement checkpoint: "
                    f"room={room} phase={phase} lifecycle={lifecycle}")

            statuses = session.read_memory("snesMemory", SLOT_STATUS, 25)
            numbers = session.read_memory("snesMemory", SLOT_NUMBER, 25)
            programs = session.read_memory("snesMemory", SLOT_PROGRAM, 25)
            pcs = session.read_memory("snesMemory", SLOT_PC, 50)
            locals_raw = session.read_memory("snesMemory", SLOT_LOCALS, 25 * 64)
            globals_raw = session.read_memory("snesMemory", VARIABLES, 24)
            for slot in range(1, 25):
                local0 = u16(locals_raw, slot * 64)
                pc = u16(pcs, slot * 2)
                if (numbers[slot] == 75 and statuses[slot] == 2
                        and pc == 23 and local0 == 0xBEEF):
                    slot_observation = {
                        "slot": slot, "status": statuses[slot],
                        "script_number": numbers[slot], "program": programs[slot],
                        "pc": pc, "local0": local0,
                        "global10": u16(globals_raw, 20),
                        "global11": u16(globals_raw, 22),
                        "nest_depth": session.read_memory(
                            "snesMemory", NEST_DEPTH, 1)[0],
                        "room": room, "phase": phase,
                    }
                    break
            if slot_observation is not None:
                break

        require(slot_observation is not None,
                "replacement did not yield at the authored post-entry PC")
        require(slot_observation["slot"] == 1
                and slot_observation["program"] != 0
                and slot_observation["global10"] == 0xBEEF
                and slot_observation["global11"] == 0
                and slot_observation["nest_depth"] == 0,
                f"replacement state or dead-tail sentinel differs: {slot_observation}")
        require(no_parent_hits == 1,
                f"expected one no-parent same-script replacement, got {no_parent_hits}")

        # Let the replacement's next scheduler turn reach STOP. The retired
        # activation's instruction after startScript must remain unreachable.
        session.run_frames(3)
        error_after = session.read_memory("snesMemory", ERROR, 1)[0]
        globals_after = session.read_memory("snesMemory", VARIABLES, 24)
        require(error_after == 0 and u16(globals_after, 22) == 0,
                "retired StartScript continuation resumed after replacement")

    report = {
        "gate": "SCUMM-v5-same-script-StartScript-replacement-Nexen",
        "result": "pass",
        "evidence_kind": "fresh-power-on-Nexen-native-execution",
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "build_identity_sha256": hashlib.sha256(
            args.rom.with_suffix(".build_identity.json").read_bytes()
        ).hexdigest(),
        "global75_body_sha256": body_sha,
        "global75_body_size": len(body),
        "no_parent_helper_cpu_address": helper_address,
        "no_parent_helper_hits": no_parent_hits,
        "replacement_yield": slot_observation,
        "error_after_replacement": error_after,
        "global11_after_retired_tail_window": u16(globals_after, 22),
        "frames_to_checkpoint": frame,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"SCUMM same-script StartScript replacement: PASS ({args.output})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
