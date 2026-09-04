#!/usr/bin/env python3
"""Fresh-emulator copyright-free proof for canonical v5 $01 putActor."""

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
POSITIONS = 0x7FF1A0
PUT_ACTOR = 0x7FFB65


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def run(rom: Path, nexen: Path, port: int, *, expected_error: int | None) -> dict[str, object]:
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
        require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")
        final = None
        for frame in range(1, 181):
            session.run_frames(1)
            common = session.read_memory("snesMemory", COMMON, 0x64)
            state = session.read_memory("snesMemory", PUT_ACTOR, 0x40C)
            final = (frame, common, state)
            if expected_error is not None and common[3]:
                break
            if expected_error is None and state[0x39B] == 8:
                break
        assert final is not None
        frame, common, state = final
        traces = []
        for index in range(min(state[0x39B], 8)):
            base = 0x39C + index * 14
            traces.append({
                "actor": state[base], "opcode": state[base + 1],
                "request": [u16(state, base + 2), u16(state, base + 4)],
                "result": [u16(state, base + 6), u16(state, base + 8)],
                "pc_before": u16(state, base + 10), "pc_after": u16(state, base + 12),
            })
        positions = session.read_memory("snesMemory", POSITIONS, 32 * 4)
        result = {
            "rom": str(rom), "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
            "fresh_power_on": True, "frame": frame, "status": common[2],
            "error": common[3], "last_opcode": common[6],
            "execution_count": state[0x381], "trace": traces,
            "positions": {str(actor): [u16(positions, actor * 4), u16(positions, actor * 4 + 2)]
                          for actor in range(1, 9)},
        }
        if expected_error is None:
            expected = []
            pc = 0
            for index, opcode in enumerate((0x01, 0x21, 0x41, 0x61, 0x81, 0xA1, 0xC1, 0xE1)):
                actor, x, y = index + 1, 300 + index, 400 + index
                pc += 7
                if opcode & 0x80:
                    pc += 5
                if opcode & 0x40:
                    pc += 5
                if opcode & 0x20:
                    pc += 5
                start = pc
                length = 1 + (2 if opcode & 0x80 else 1) + 2 + 2
                expected.append({"actor": actor, "opcode": opcode, "request": [x, y],
                                 "result": [x, y], "pc_before": start,
                                 "pc_after": start + length})
                pc += length
            require(traces == expected, f"putActor decode trace differs: {traces}")
            require(result["execution_count"] == 8 and result["error"] == 0,
                    f"valid execution state differs: {result}")
            require(result["positions"] == {
                str(i + 1): [300 + i, 400 + i] for i in range(8)
            }, f"actor isolation/positions differ: {result['positions']}")
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
    parser.add_argument("--port", type=int, default=44850)
    args = parser.parse_args()
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    report = {
        "gate": "canonical-v5-putActor", "result": "pass",
        "valid": run(args.valid_rom, args.nexen, args.port, expected_error=None),
        "invalid_actor": run(args.invalid_rom, args.nexen, args.port + 1, expected_error=0x0C),
        "malformed": run(args.malformed_rom, args.nexen, args.port + 2, expected_error=0x01),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
