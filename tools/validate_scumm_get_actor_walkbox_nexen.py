#!/usr/bin/env python3
"""Fresh-emulator copyright-free proof for canonical v5 $7B getActorWalkBox."""

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
LEGACY_VARIABLES = 0x7E2320
EXTENDED_VARIABLES = 0x7FF500
ACTOR_RECORDS = 0x7F36C0
ACTOR_FACINGS = 0x7E78F0
ACTOR_PLACEMENT = 0x7FF1A0
PUT_ACTOR_WALKBOX = 0x7FFDA5
WALKBOX_STATE = 0x7E7AD9


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def actor_state(session: object) -> bytes:
    """All canonical actor storage that the pure query must leave untouched."""
    return b"".join((
        session.read_memory("snesMemory", ACTOR_RECORDS, 32 * 0x40),
        session.read_memory("snesMemory", ACTOR_FACINGS, 32 * 2),
        session.read_memory("snesMemory", ACTOR_PLACEMENT, 0xA4),
        session.read_memory("snesMemory", PUT_ACTOR_WALKBOX, 32 * 2),
    ))


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
        before = None
        final = None
        for frame in range(1, 181):
            step = session.run_frames(1)
            require(step["framesAdvanced"] == 1 and not step["timedOut"], "emulator timeout")
            common = session.read_memory("snesMemory", COMMON, 8)
            raw = session.read_memory("snesMemory", WALKBOX_STATE, 0xCC)
            if expected_error is None and before is None and raw[0x0B] == 0:
                legacy = session.read_memory("snesMemory", LEGACY_VARIABLES, 32)
                if (u16(legacy, 0) == 0x7777 and u16(legacy, 10) == 0x5555
                        and u16(legacy, 18) == 0x9999 and u16(legacy, 24) == 0x1212):
                    before = actor_state(session)
            final = (frame, common, raw)
            if common[3] or (expected_error is None and raw[0x0B] == 4):
                break
        assert final is not None
        frame, common, raw = final
        trace = []
        for index in range(min(raw[0x0B], 16)):
            base = 0x0C + index * 12
            trace.append({
                "actor": raw[base], "opcode": raw[base + 1],
                "walkbox": raw[base + 2], "result_offset": u16(raw, base + 4),
                "result_before": u16(raw, base + 6),
                "pc_before": u16(raw, base + 8), "pc_after": u16(raw, base + 10),
            })
        legacy = session.read_memory("snesMemory", LEGACY_VARIABLES, 32)
        extended = session.read_memory("snesMemory", EXTENDED_VARIABLES, 64)
        positions = session.read_memory("snesMemory", ACTOR_PLACEMENT, 32 * 4)
        boxes = session.read_memory("snesMemory", PUT_ACTOR_WALKBOX, 32)
        after = actor_state(session)
        result = {
            "rom": str(rom), "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
            "fresh_power_on": True, "frame": frame, "status": common[2],
            "error": common[3], "last_opcode": common[6],
            "execution_count": raw[2], "trace": trace,
            "results": [u16(legacy, index * 2) for index in (0, 5, 9, 12)],
            "variable_30": u16(extended, 60), "variable_31": u16(extended, 62),
            "actor_positions": [[u16(positions, i * 4), u16(positions, i * 4 + 2)]
                                for i in range(4)],
            "actor_walkboxes": list(boxes[:4]),
            "actor_state_before_sha256": hashlib.sha256(before).hexdigest() if before else None,
            "actor_state_after_sha256": hashlib.sha256(after).hexdigest(),
            "actor_state_unchanged": before == after,
        }
        if expected_error is None:
            require(trace == [
                {"actor": 1, "opcode": 0x7B, "walkbox": 0,
                 "result_offset": 0, "result_before": 0x7777,
                 "pc_before": 43, "pc_after": 47},
                {"actor": 2, "opcode": 0x7B, "walkbox": 2,
                 "result_offset": 10, "result_before": 0x5555,
                 "pc_before": 47, "pc_after": 51},
                {"actor": 3, "opcode": 0x7B, "walkbox": 3,
                 "result_offset": 18, "result_before": 0x9999,
                 "pc_before": 51, "pc_after": 55},
                {"actor": 3, "opcode": 0xFB, "walkbox": 3,
                 "result_offset": 24, "result_before": 0x1212,
                 "pc_before": 55, "pc_after": 60},
            ], f"getActorWalkBox trace differs: {trace}")
            require(result["results"] == [0, 2, 3, 3], f"query results differ: {result}")
            require(result["variable_30"] == 3 and result["variable_31"] == 0x5151,
                    f"variable isolation differs: {result}")
            require(result["actor_positions"][3] == [4, 1]
                    and result["actor_walkboxes"][3] == 3,
                    f"geometry-mismatch control differs: {result}")
            require(result["actor_state_unchanged"], f"query mutated actor state: {result}")
            require(result["execution_count"] == 4 and result["error"] == 0,
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
    parser.add_argument("--port", type=int, default=45320)
    args = parser.parse_args()
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    report = {
        "gate": "canonical-v5-getActorWalkBox", "result": "pass",
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
