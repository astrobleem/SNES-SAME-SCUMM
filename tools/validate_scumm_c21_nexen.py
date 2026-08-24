#!/usr/bin/env python3
"""Validate C21 canonical SCUMM v5 drawObject semantics in Nexen."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "build" / "same-scumm-v5.sfc"
DEFAULT_NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
COMMON_ADDRESS = 0x7E2300
C21_ADDRESS = 0x7FD3AC
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 45


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def s16(raw: bytes, offset: int = 0) -> int:
    value = u16(raw, offset)
    return value - 0x10000 if value & 0x8000 else value


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON_ADDRESS, 0x64)
    state = session.read_memory("snesMemory", C21_ADDRESS, 0x56)
    records = []
    for index in range(state[1]):
        offset = 4 + index * 16
        records.append({
            "object": u16(state, offset),
            "position": [s16(state, offset + 2), s16(state, offset + 4)],
            "size": [u16(state, offset + 6), u16(state, offset + 8)],
            "walk": [s16(state, offset + 10), s16(state, offset + 12)],
            "state": state[offset + 14],
        })
    queue_count = state[2]
    return {
        "pc": u16(common), "status": common[0x02], "error": common[0x03],
        "last_opcode": common[0x06], "frame_count": u16(common, 0x08),
        "frame_ops": u16(common, 0x0A), "total_ops": u16(common, 0x0C),
        "fixture_active": common[0x5F], "program_select": common[0x62],
        "variables": [s16(common, 0x20 + index * 2) for index in range(16)],
        "initialized": state[0], "record_count": state[1],
        "queue_count": queue_count, "positioned": state[3],
        "records": records,
        "draw_queue": [u16(state, 0x34 + index * 2) for index in range(queue_count)],
    }


def step_video_frame(session: object) -> None:
    for _ in range(20):
        run = session.run_frames(1)
        if run["framesAdvanced"] == 1:
            return
    raise GateFailure(f"one-frame step made no progress: {run}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44001)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"scumm-c21-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C21-draw-object", "result": "running", "rom": str(rom),
        "rom_sha256": rom_hash, "fresh_power_on": True, "frame_limit": 12,
        "donor_rom_used": False, "screenshots_captured": False, "audio_captured": False,
    }
    expected_records = [
        {"object": 100, "position": [96, 104], "size": [16, 24], "walk": [108, 118], "state": 5},
        {"object": 101, "position": [40, 48], "size": [16, 24], "walk": [50, 60], "state": 3},
        {"object": 102, "position": [40, 48], "size": [16, 24], "walk": [70, 80], "state": 0},
    ]

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    try:
        with mcp_session.McpSession(
            rom=rom, mesen=nexen, cwd=ROOT, port=args.port, boot_wait=2.0,
            socket_timeout=30.0, stderr_log=output / "nexen-stderr.log",
        ) as session:
            session.pause()
            session.tool("reset_emulator", {"power": True})
            session.pause()
            require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")
            step_video_frame(session)
            report["bootstrap"] = snapshot(session)
            session.write_u8(FIXTURE_REQUEST, FIXTURE_ID)

            first = snapshot(session)
            for _ in range(8):
                step_video_frame(session)
                first = snapshot(session)
                if first["fixture_active"] == FIXTURE_ID and first["pc"] == 45:
                    break
            first["video_frame"] = session.get_state()["frameCount"]
            report["first_tick"] = first
            expected_first = {
                "pc": 45, "status": 2, "error": 0, "last_opcode": 0x80,
                "frame_count": 1, "frame_ops": 9, "total_ops": 9,
                "fixture_active": FIXTURE_ID, "program_select": FIXTURE_ID,
                "variables": [100, 12, 13, 5] + [0] * 12,
                "initialized": 1, "record_count": 3, "queue_count": 3,
                "positioned": 0, "records": expected_records,
                "draw_queue": [100, 101, 100],
            }
            for key, value in expected_first.items():
                require(first[key] == value, f"first {key}={first[key]!r}, expected {value!r}")

            terminal = snapshot(session)
            for _ in range(4):
                step_video_frame(session)
                terminal = snapshot(session)
                if terminal["pc"] == 46:
                    break
            terminal["video_frame"] = session.get_state()["frameCount"]
            report["terminal"] = terminal
            expected_terminal = {
                **expected_first, "pc": 46, "status": 4, "last_opcode": 0,
                "frame_count": 2, "frame_ops": 1, "total_ops": 10,
            }
            for key, value in expected_terminal.items():
                require(terminal[key] == value, f"terminal {key}={terminal[key]!r}, expected {value!r}")
            require(terminal["video_frame"] <= 12, "gate exceeded twelve video frames")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C21 SCUMM drawObject: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C21 SCUMM drawObject: PASS (operands, relocation, overlap, queue, missing object)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
