#!/usr/bin/env python3
"""Fresh-emulator copyright-free proof for canonical v5 $07 setState."""

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
STATE = 0x7E5FF0


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
        for frame in range(1, 181):
            session.run_frames(1)
            common = session.read_memory("snesMemory", COMMON, 0x64)
            state = session.read_memory("snesMemory", STATE, 0x1900)
            final = (frame, common, state)
            if common[3] or (expected_error is None and state[0x18B1] == 4):
                break
        assert final is not None
        frame, common, state = final
        trace = []
        for index in range(min(state[0x18B1], 8)):
            base = 0x18C0 + index * 8
            trace.append({
                "object": u16(state, base), "state": state[base + 2],
                "opcode": state[base + 3], "pc_before": u16(state, base + 4),
                "pc_after": u16(state, base + 6),
            })
        result = {
            "rom": str(rom), "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
            "fresh_power_on": True, "frame": frame, "status": common[2],
            "error": common[3], "last_opcode": common[6],
            "global_count": u16(state), "execution_count": state[7], "trace": trace,
            "states": {"590": state[0x10 + 590], "591": state[0x10 + 591]},
            "local_found": state[5], "background_needs_redraw": state[6],
            "dirty_count": state[13],
            "dirty_rect": [u16(state, 0x18A8 + i) for i in (0, 2, 4, 6)],
            "draw_queue_count": state[0x18B0],
        }
        if expected_error is None:
            expected = [
                {"object": 590, "state": 0, "opcode": 0x07, "pc_before": 0, "pc_after": 4},
                {"object": 590, "state": 1, "opcode": 0x47, "pc_before": 9, "pc_after": 14},
                {"object": 591, "state": 255, "opcode": 0x87, "pc_before": 19, "pc_after": 23},
                {"object": 590, "state": 128, "opcode": 0xC7, "pc_before": 33, "pc_after": 38},
            ]
            require(trace == expected, f"setState decode/PC trace differs: {trace}")
            require(result["states"] == {"590": 128, "591": 255}, f"states differ: {result}")
            require(result["execution_count"] == 4 and result["error"] == 0, f"valid result differs: {result}")
            require(result["dirty_rect"] == [8, 8, 24, 8] and result["draw_queue_count"] == 0,
                    f"redraw invalidation differs: {result}")
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
    parser.add_argument("--port", type=int, default=44900)
    args = parser.parse_args()
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    report = {
        "gate": "canonical-v5-setState", "result": "pass",
        "valid": run(args.valid_rom, args.nexen, args.port, None),
        "invalid_object": run(args.invalid_rom, args.nexen, args.port + 1, 0x0C),
        "malformed": run(args.malformed_rom, args.nexen, args.port + 2, 0x0C),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
