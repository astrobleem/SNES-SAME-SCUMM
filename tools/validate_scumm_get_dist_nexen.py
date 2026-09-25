#!/usr/bin/env python3
"""Fresh-emulator copyright-free proof for canonical v5 getDist."""

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
COMMON = 0x7E2300
VARIABLES = 0x7E2320
ACTORS = 0x7F36C0
POSITIONS = 0x7FF1A0
WALKBOXES = 0x7FFDA5
GET_DIST = 0x7E7F23


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def actor_state(session: object) -> bytes:
    return b"".join((
        session.read_memory("snesMemory", ACTORS, 32 * 64),
        session.read_memory("snesMemory", POSITIONS, 32 * 4),
        session.read_memory("snesMemory", WALKBOXES, 64),
        session.read_memory("snesMemory", 0x7FF220, 32),
    ))


def run(rom: Path, nexen: Path, port: int, *, malformed: bool) -> dict[str, object]:
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    with mcp_session.McpSession(
        rom=rom.resolve(), mesen=nexen.resolve(), cwd=ROOT, port=port,
        boot_wait=2.0, socket_timeout=90.0,
        stderr_log=rom.with_suffix(".nexen-stderr.log"),
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        before = None
        common = raw = b""
        frame = 0
        for frame in range(1, 241):
            step = session.run_frames(1)
            require(step["framesAdvanced"] == 1 and not step["timedOut"], "emulator timeout")
            common = session.read_memory("snesMemory", COMMON, 16)
            raw = session.read_memory("snesMemory", GET_DIST, 35)
            variables = session.read_memory("snesMemory", VARIABLES, 64)
            if not malformed and before is None and raw[33] == 0 and u16(variables) == 0x7000:
                before = actor_state(session)
            if common[3] or (not malformed and raw[33] == 8):
                break
        variables = session.read_memory("snesMemory", VARIABLES, 64)
        after = actor_state(session)
        report = {
            "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
            "fresh_power_on": True, "debugger_writes": 0, "frame": frame,
            "error": common[3], "last_opcode": common[6], "pc": u16(common),
            "execution_count": raw[33],
            "results": [u16(variables, index * 2) for index in range(8)],
            "actor_state_before_sha256": hashlib.sha256(before).hexdigest() if before else None,
            "actor_state_after_sha256": hashlib.sha256(after).hexdigest(),
            "actor_state_unchanged": before == after,
            "last_query": {
                "pc_before": u16(raw, 0), "pc_after": u16(raw, 2),
                "result_offset": u16(raw, 4), "result_before": u16(raw, 6),
                "operand1": u16(raw, 8), "operand2": u16(raw, 10),
                "type1": raw[12], "type2": raw[13],
                "xy1": [u16(raw, 14), u16(raw, 16)],
                "xy2_raw": [u16(raw, 18), u16(raw, 20)],
                "xy2": [u16(raw, 22), u16(raw, 24)],
                "dx": u16(raw, 26), "dy": u16(raw, 28),
                "result": u16(raw, 30), "adjusted": raw[32],
            },
        }
        if malformed:
            require(report["error"] == 1 and report["execution_count"] == 0,
                    f"truncated getDist did not fail closed: {report}")
        else:
            require(report["error"] == 0 and report["execution_count"] == 8,
                    f"valid getDist program did not complete: {report}")
            require(report["results"] == [5, 0, 7, 8, 0, 7, 0xFF, 0xFF],
                    f"getDist results differ: {report}")
            require(report["actor_state_unchanged"], f"getDist mutated actor state: {report}")
        return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--valid-rom", type=Path, required=True)
    parser.add_argument("--malformed-rom", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45740)
    args = parser.parse_args()
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    report = {
        "gate": "canonical-v5-getDist", "result": "pass",
        "valid": run(args.valid_rom, args.nexen, args.port, malformed=False),
        "malformed": run(args.malformed_rom, args.nexen, args.port + 1, malformed=True),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
