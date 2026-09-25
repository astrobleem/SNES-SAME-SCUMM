#!/usr/bin/env python3
"""Native M23A control for invalid outgoing room-local continuations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/"
    "linux-x64/publish/Nexen"
)
ROOM = 0x7FF2BF
PHASE = 0x7FF2C2
RETURN_VALID = 0x7FF467
RETURN_SLOT = 0x7FF468
RETURN_PROGRAM = 0x7FF2C3
RETURN_PC = 0x7FF2E5
VALIDATIONS = 0x7FF2C6
ERROR = 0x7E2303
LIFECYCLE = 0x7E2221
VARIABLES = 0x7E0800
NUMBERS = 0x7E2399
STATUSES = 0x7E2380
WHERES = 0x7E7F46


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def u16(data: bytes, offset: int = 0) -> int:
    return int.from_bytes(data[offset:offset + 2], "little")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45742)
    args = parser.parse_args()
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK),
            f"Nexen unavailable: {args.nexen}")
    manifest = json.loads(args.manifest.read_text())
    require(manifest.get("room_provenance", "").startswith("synthetic fixture"),
            "native control must identify both rooms as synthetic")
    require({r["room"] for r in manifest["records"]} >= {49, 50},
            "local-return fixture lacks source or destination record")

    import sys
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None

    observations: list[dict[str, object]] = []
    storage_invalid_seen = False
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=Path(__file__).resolve().parents[1],
        port=args.port, boot_wait=2.0, socket_timeout=60.0,
        stderr_log=args.output.with_suffix(".stderr.log"),
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0, "cold reset failed")
        previous_validations = 0
        reached_destination = False
        for frame in range(1, 121):
            result = session.run_frames(1)
            require(result["framesAdvanced"] == 1 and not result["timedOut"],
                    f"native frame did not advance: {result}")
            room = session.read_memory("snesMemory", ROOM, 1)[0]
            phase = session.read_memory("snesMemory", PHASE, 1)[0]
            validations = session.read_memory("snesMemory", VALIDATIONS, 1)[0]
            valid = session.read_memory("snesMemory", RETURN_VALID, 1)[0]
            return_slot = session.read_memory("snesMemory", RETURN_SLOT, 1)[0]
            return_program = session.read_memory("snesMemory", RETURN_PROGRAM, 1)[0]
            return_pc = u16(session.read_memory("snesMemory", RETURN_PC, 2))
            globals_raw = session.read_memory("snesMemory", VARIABLES, 32)
            values = [u16(globals_raw, i * 2) for i in range(16)]
            if validations > previous_validations:
                observation = {
                    "frame": frame, "room": room, "phase": phase,
                    "validations": validations, "return_valid": valid,
                    "return_slot": return_slot, "return_program": return_program,
                    "return_pc": return_pc,
                }
                observations.append(observation)
                if room == 49 and phase == 5 and valid == 0 and not return_slot:
                    storage_invalid_seen = True
                previous_validations = validations
            require(session.read_memory("snesMemory", ERROR, 1)[0] == 0,
                    f"SCUMM error at frame {frame}, room={room}, phase={phase}")
            if room == 50 and phase == 0 and values[12] == 0xBEEF:
                reached_destination = True
                if frame >= 25:
                    break

        numbers = session.read_memory("snesMemory", NUMBERS, 25)
        statuses = session.read_memory("snesMemory", STATUSES, 25)
        wheres = session.read_memory("snesMemory", WHERES, 25)
        live = [
            {"slot": i, "number": numbers[i], "status": statuses[i], "where": wheres[i]}
            for i in range(1, 25)
            if numbers[i] == 200 and statuses[i] not in (0, 4)
        ]
        final_room = session.read_memory("snesMemory", ROOM, 1)[0]
        final_phase = session.read_memory("snesMemory", PHASE, 1)[0]
        final_error = session.read_memory("snesMemory", ERROR, 1)[0]
        final_lifecycle = session.read_memory("snesMemory", LIFECYCLE, 1)[0]
        globals_raw = session.read_memory("snesMemory", VARIABLES, 32)
        values = [u16(globals_raw, i * 2) for i in range(16)]

    require(storage_invalid_seen,
            f"outgoing-local invalid state not observed through storage validation: {observations}")
    require(reached_destination and final_room == 50 and final_phase == 0,
            f"destination did not install: room={final_room} phase={final_phase}")
    require(values[12] == 0xBEEF and values[13] == 0,
            f"destination or stale-local continuation mismatch: V12={values[12]:04X} V13={values[13]:04X}")
    require(not live, f"outgoing room-local activation survived commit: {live}")
    require(final_error == 0 and final_lifecycle == 2,
            f"runtime unhealthy: error={final_error} lifecycle={final_lifecycle}")

    report = {
        "gate": "M23A-room-local-return-invalid-through-storage",
        "result": "pass",
        "evidence_kind": "fresh-power-on-Nexen-native-execution",
        "debugger_state_writes": 0,
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "synthetic_fixture": True,
        "storage_validation_observations": observations,
        "final": {"room": final_room, "phase": final_phase,
                  "error": final_error, "lifecycle": final_lifecycle,
                  "V12_destination_marker": values[12],
                  "V13_stale_local_marker": values[13], "live_old_locals": live},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
