#!/usr/bin/env python3
"""Native four-form actor-position query and return-balance control."""

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
VARIABLES = 0x7E0800
QUERY_SP_BEFORE = 0x7E56A0
QUERY_SP_AFTER = 0x7E56A2
QUERY_RETURNED = 0x7E56A4
TRACE_COUNT = 0x7E5A00
TRACE = 0x7E5A02
STATUS = 0x7E2302
PROGRAM = 0x7E2362
PC = 0x7E2300
FIXTURE_READY = 0x7E5601
CURRENT_SLOT = 0x7E2A88


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
    parser.add_argument("--port", type=int, default=45727)
    args = parser.parse_args()
    require(args.rom.is_file() and args.manifest.is_file(), "ROM or manifest missing")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    manifest = json.loads(args.manifest.read_text())
    require(manifest.get("case") == "actor-position-success",
            "wrong actor-position fixture manifest")
    entry = manifest["records"][0]["scripts"]
    encd = next(item for item in entry if item["kind"] == "ENCD")
    require(encd["program_length"] == 30,
            f"unexpected four-query fixture length: {encd['program_length']}")
    require(manifest["actor_positions"][7] == [0x1234, 0x2345],
            "manifest actor 7 position differs")

    from validate_scumm_startup42_nexen import verified_symbol_map_for_rom
    verified_symbol_map_for_rom(args.rom.resolve())

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None

    expected = {5: 0x43, 11: 0x23, 17: 0xC3, 23: 0xA3}
    observations: dict[int, dict[str, int]] = {}
    previous_count = 0
    terminal = None
    last_snapshot: dict[str, int] = {}
    trace_rows: list[tuple[int, int, int]] = []
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=2.0, socket_timeout=60.0,
        stderr_log=args.output.with_suffix(".stderr.log"),
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0, "cold reset failed")

        for frame in range(1, 121):
            session.run_frames(1)
            room = session.read_memory("snesMemory", ROOM, 1)[0]
            phase = session.read_memory("snesMemory", PHASE, 1)[0]
            error = session.read_memory("snesMemory", ERROR, 1)[0]
            lifecycle = session.read_memory("snesMemory", LIFECYCLE, 1)[0]
            last_snapshot = {
                "frame": frame, "room": room, "phase": phase,
                "error": error, "lifecycle": lifecycle,
                "status": session.read_memory("snesMemory", STATUS, 1)[0],
                "program": session.read_memory("snesMemory", PROGRAM, 1)[0],
                "pc": u16(session.read_memory("snesMemory", PC, 2)),
                "slot": session.read_memory("snesMemory", CURRENT_SLOT, 1)[0],
                "fixture_ready": session.read_memory(
                    "snesMemory", FIXTURE_READY, 1)[0],
            }
            require(error == 0, f"SCUMM error during actor queries: room={room} phase={phase}")

            count = min(u16(session.read_memory("snesMemory", TRACE_COUNT, 2)), 256)
            trace_raw = session.read_memory("snesMemory", TRACE, 256 * 4)
            trace_rows = [
                (trace_raw[index * 4],
                 u16(trace_raw[index * 4 + 1:index * 4 + 3]),
                 trace_raw[index * 4 + 3])
                for index in range(count)
            ]
            for index in range(previous_count, count):
                program, pc, _untrusted_opcode = trace_rows[index]
                if pc in expected and pc not in observations:
                    before = u16(session.read_memory("snesMemory", QUERY_SP_BEFORE, 2))
                    after = u16(session.read_memory("snesMemory", QUERY_SP_AFTER, 2))
                    returned = session.read_memory("snesMemory", QUERY_RETURNED, 1)[0]
                    observations[pc] = {
                        "frame": frame, "program": program, "pc": pc,
                        "opcode_from_fixture_bytes": expected[pc],
                        "stack_before": before, "stack_after": after,
                        "dispatcher_return_latch": returned,
                    }
            previous_count = count

            if (room == manifest.get("fixture_room") and phase == 0
                    and lifecycle == 2 and count >= 7
                    and u16(session.read_memory("snesMemory", PC, 2)) == 30):
                terminal = {"frame": frame, "room": room, "phase": phase,
                            "error": error, "lifecycle": lifecycle,
                            "opcode_trace_count": count,
                            "program_pc": u16(session.read_memory("snesMemory", PC, 2)),
                            "vm_status": session.read_memory(
                                "snesMemory", STATUS, 1)[0]}
                break

        require(set(observations) == set(expected),
                f"did not execute all query forms: {observations}; "
                f"last state={last_snapshot}; trace={trace_rows}")
        require(terminal is not None,
                "actor query fixture did not reach its normal room frame")
        for pc, event in observations.items():
            require(event["stack_before"] == event["stack_after"]
                    and event["dispatcher_return_latch"] == 1,
                    f"native JSL/RTL query contract failed at PC {pc}: {event}")

        globals_raw = session.read_memory("snesMemory", VARIABLES, 48)
        results = [u16(globals_raw, number * 2) for number in range(20, 24)]
        require(results == [0x1234, 0x2345, 0x1234, 0x2345],
                f"actor-position results differ: {results}")
        error_final = session.read_memory("snesMemory", ERROR, 1)[0]
        require(error_final == 0, f"final actor-position error is {error_final}")

    build_identity = args.rom.with_suffix(".build_identity.json").read_bytes()
    report = {
        "gate": "M25A-actor-position-four-form-native",
        "result": "pass",
        "evidence_kind": "fresh-power-on-Nexen-native-execution",
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "build_identity_sha256": hashlib.sha256(build_identity).hexdigest(),
        "actor7_position": [0x1234, 0x2345],
        "query_observations": [observations[pc] for pc in expected],
        "results_v20_v23": results,
        "terminal": terminal,
        "error": error_final,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"M25A actor-position four-form native matrix: PASS ({args.output})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
