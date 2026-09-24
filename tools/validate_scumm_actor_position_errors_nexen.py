#!/usr/bin/env python3
"""Native error-path and JSL/RTL balance checks for v5 actor-position queries."""

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
ERROR = 0x7E2303
STATUS = 0x7E2302
CURRENT_PC = 0x7E2300
LAST_OPCODE = 0x7E2306
CURRENT_PROGRAM = 0x7E2362
ENGINE_LIFECYCLE = 0x7E2221
SP_BEFORE = 0x7E56A0
SP_AFTER = 0x7E56A2
QUERY_RETURNED = 0x7E56A4


CASES = (
    ("truncated-result", "truncated_result_rom", 0x01,
     "truncated result-reference word"),
    ("invalid-result", "invalid_result_rom", 0x0A,
     "out-of-range local result reference"),
    ("truncated-selector", "truncated_selector_rom", 0x01,
     "truncated direct actor-selector word"),
)


class GateFailure(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise GateFailure(message)


def u16(raw: bytes) -> int:
    return raw[0] | raw[1] << 8


def run_case(rom: Path, nexen: Path, port: int, name: str,
             expected_error: int, reason: str) -> dict[str, object]:
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    log = ROOT / "build" / "m25a-validator" / "actor-position-errors" / f"{name}.stderr.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with mcp_session.McpSession(
        rom=rom.resolve(), mesen=nexen.resolve(), cwd=ROOT, port=port,
        boot_wait=2.0, socket_timeout=60.0, stderr_log=log,
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0,
                f"{name}: power reset did not reach frame zero")
        error = 0
        observed_frame = 0
        last_state: dict[str, int] = {}
        for frame in range(1, 121):
            result = session.run_frames(1)
            require(result["framesAdvanced"] == 1 and not result["timedOut"],
                    f"{name}: emulator frame did not advance: {result}")
            error = session.read_memory("snesMemory", ERROR, 1)[0]
            last_state = {
                "error": error,
                "status": session.read_memory("snesMemory", STATUS, 1)[0],
                "program": session.read_memory("snesMemory", CURRENT_PROGRAM, 1)[0],
                "pc": u16(session.read_memory("snesMemory", CURRENT_PC, 2)),
                "opcode": session.read_memory("snesMemory", LAST_OPCODE, 1)[0],
                "lifecycle": session.read_memory("snesMemory", ENGINE_LIFECYCLE, 1)[0],
                "returned": session.read_memory("snesMemory", QUERY_RETURNED, 1)[0],
            }
            if error:
                observed_frame = frame
                break
        require(error == expected_error,
                f"{name}: expected SCUMM error ${expected_error:02X}, got ${error:02X}; "
                f"last state={last_state}")
        before = u16(session.read_memory("snesMemory", SP_BEFORE, 2))
        after = u16(session.read_memory("snesMemory", SP_AFTER, 2))
        returned = session.read_memory("snesMemory", QUERY_RETURNED, 1)[0]
        vm_pc = u16(session.read_memory("snesMemory", CURRENT_PC, 2))
        opcode = session.read_memory("snesMemory", LAST_OPCODE, 1)[0]
        program = session.read_memory("snesMemory", CURRENT_PROGRAM, 1)[0]
        status = session.read_memory("snesMemory", STATUS, 1)[0]
        lifecycle = session.read_memory("snesMemory", ENGINE_LIFECYCLE, 1)[0]

    require(returned == 1, f"{name}: did not return from actor-query JSL to dispatcher")
    require(before == after,
            f"{name}: JSL/RTL stack imbalance SP ${before:04X} -> ${after:04X}")
    require(opcode == 0x43, f"{name}: expected getActorX $43, got ${opcode:02X}")
    require(status == 0xFF, f"{name}: expected SCUMM_VM_ERROR, got ${status:02X}")
    return {
        "case": name,
        "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
        "expected_failure": reason,
        "frame": observed_frame,
        "error": error,
        "program": program,
        "last_opcode": opcode,
        "vm_pc": vm_pc,
        "native_sp_before_call": before,
        "native_sp_after_return": after,
        "query_returned_to_dispatcher": bool(returned),
        "vm_status": status,
        "engine_lifecycle": lifecycle,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    for _name, argument, _error, _reason in CASES:
        parser.add_argument(f"--{argument.replace('_', '-')}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45731)
    args = parser.parse_args()
    if not args.nexen.is_file() or not os.access(args.nexen, os.X_OK):
        raise GateFailure(f"Nexen unavailable: {args.nexen}")

    results = []
    for offset, (name, argument, expected, reason) in enumerate(CASES):
        rom = getattr(args, argument)
        require(rom.is_file(), f"missing {name} ROM: {rom}")
        results.append(run_case(rom, args.nexen, args.port + offset,
                                name, expected, reason))

    report = {
        "gate": "M25A-actor-position-error-return-native",
        "result": "pass",
        "evidence_kind": "fresh-power-on-Nexen-native-execution",
        "debugger_state_writes": 0,
        "assertions": {
            "truncated_result_is_pc_range": results[0]["error"] == 0x01,
            "invalid_result_preserves_local_error": results[1]["error"] == 0x0A,
            "truncated_selector_is_pc_range": results[2]["error"] == 0x01,
            "all_jSL_rtl_stack_contracts_balanced": all(
                item["native_sp_before_call"] == item["native_sp_after_return"]
                and item["query_returned_to_dispatcher"] for item in results
            ),
        },
        "cases": results,
    }
    require(all(report["assertions"].values()), "native actor-query error assertions failed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
