#!/usr/bin/env python3
"""Fresh-emulator copyright-free proof for canonical v5 $63 getActorFacing."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
COMMON = 0x7E2300
LEGACY_VARIABLES = 0x7E2320
EXTENDED_VARIABLES = 0x7FF500
ACTOR_RECORDS = 0x7F36C0
FACING_STATE = 0x7E78F0
ANGLES = (0, 70, 71, 90, 109, 110, 180, 250, 251, 270, 289, 290, 359)
RESULTS = (3, 3, 1, 1, 1, 2, 2, 2, 2, 0, 0, 3, 3)


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def run(rom: Path, nexen: Path, port: int, expected_error: int | None) -> dict[str, object]:
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
        session.pause()
        final = None
        actor_records_before = None
        for frame in range(1, 181):
            step = session.run_frames(1)
            require(step["framesAdvanced"] == 1 and not step["timedOut"], "emulator timeout")
            common = session.read_memory("snesMemory", COMMON, 0x64)
            facing = session.read_memory("snesMemory", FACING_STATE, 0x130)
            if (
                expected_error is None and actor_records_before is None
                and facing[0x45] == 0
                and [u16(facing, index * 2) for index in range(1, 14)] == list(ANGLES)
            ):
                actor_records_before = session.read_memory(
                    "snesMemory", ACTOR_RECORDS, 32 * 0x40
                )
            final = (frame, common, facing)
            if common[3] or (expected_error is None and facing[0x45] == 14):
                break
        assert final is not None
        frame, common, facing = final
        trace = []
        for index in range(min(facing[0x4C], 16)):
            base = 0x50 + index * 14
            trace.append({
                "actor": facing[base], "opcode": facing[base + 1],
                "result": facing[base + 2], "raw_facing": u16(facing, base + 4),
                "result_offset": u16(facing, base + 6),
                "result_before": u16(facing, base + 8),
                "pc_before": u16(facing, base + 10), "pc_after": u16(facing, base + 12),
            })
        actor_records = session.read_memory("snesMemory", ACTOR_RECORDS, 32 * 0x40)
        legacy = session.read_memory("snesMemory", LEGACY_VARIABLES, 32)
        extended = session.read_memory("snesMemory", EXTENDED_VARIABLES, 64)
        result = {
            "rom": str(rom), "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
            "fresh_power_on": True, "frame": frame, "status": common[2],
            "error": common[3], "last_opcode": common[6],
            "execution_count": facing[0x45], "trace": trace,
            "actor_facings": [u16(facing, index * 2) for index in range(32)],
            "actor_records_sha256": hashlib.sha256(actor_records).hexdigest(),
            "actor_records_before_sha256": (
                hashlib.sha256(actor_records_before).hexdigest()
                if actor_records_before is not None else None
            ),
            "actor_records_unchanged": actor_records_before == actor_records,
            "results": [u16(legacy, index * 2) for index in range(13)],
            "variable_20": u16(extended, 20 * 2),
            "variable_30": u16(extended, 30 * 2),
            "variable_31": u16(extended, 31 * 2),
        }
        if expected_error is None:
            expected_trace = [{
                "actor": index + 1, "opcode": 0x63, "result": RESULTS[index],
                "raw_facing": angle, "result_offset": index * 2,
                "result_before": 0x7777 if index == 0 else 0,
                "pc_before": 11 + index * 4, "pc_after": 15 + index * 4,
            } for index, angle in enumerate(ANGLES)]
            expected_trace.append({
                "actor": 13, "opcode": 0xE3, "result": 3,
                "raw_facing": 359, "result_offset": 0x2028,
                "result_before": 0,
                "pc_before": 68, "pc_after": 73,
            })
            require(trace == expected_trace, f"getActorFacing trace differs: {trace}")
            require(result["results"] == list(RESULTS), f"direction results differ: {result}")
            require(result["variable_20"] == 3 and result["variable_30"] == 13
                    and result["variable_31"] == 0x5151, f"variable isolation differs: {result}")
            require(result["actor_facings"][1:14] == list(ANGLES), f"facings mutated: {result}")
            require(result["actor_records_unchanged"], f"query mutated actor records: {result}")
            require(result["execution_count"] == 14 and result["error"] == 0,
                    f"valid execution differs: {result}")
        else:
            require(result["error"] == expected_error and result["execution_count"] == 0,
                    f"fail-closed result differs: {result}")
        return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--valid-rom", type=Path, required=True)
    parser.add_argument("--invalid-rom", type=Path, required=True)
    parser.add_argument("--malformed-rom", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44920)
    args = parser.parse_args()
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    report = {
        "gate": "canonical-v5-getActorFacing", "result": "pass",
        "valid": run(args.valid_rom, args.nexen, args.port, None),
        "invalid_actor": run(args.invalid_rom, args.nexen, args.port + 1, 0x0C),
        "malformed": run(args.malformed_rom, args.nexen, args.port + 2, 0x01),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
