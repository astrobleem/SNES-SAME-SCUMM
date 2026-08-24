#!/usr/bin/env python3
"""Validate C22 canonical SCUMM v5 room-zero transition semantics in Nexen."""

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
C22_ADDRESS = 0x7FD402
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 46


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
    room = session.read_memory("snesMemory", C22_ADDRESS, 6)
    return {
        "pc": u16(common), "status": common[0x02], "error": common[0x03],
        "last_opcode": common[0x06], "frame_count": u16(common, 0x08),
        "frame_ops": u16(common, 0x0A), "total_ops": u16(common, 0x0C),
        "fixture_active": common[0x5F], "program_select": common[0x62],
        "variables": [s16(common, 0x20 + index * 2) for index in range(16)],
        "initialized": room[0], "room": room[1], "transitions": room[2],
        "room_objects": room[3], "draw_queue": room[4], "null_scene": room[5],
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
    output = (args.output or ROOT / "build" / f"scumm-c22-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C22-null-room", "result": "running", "rom": str(rom),
        "rom_sha256": rom_hash, "fresh_power_on": True, "frame_limit": 12,
        "donor_rom_used": False, "screenshots_captured": False, "audio_captured": False,
    }
    variables = [1] + [0] * 15
    checkpoints = [
        {"pc": 6, "status": 2, "error": 0, "last_opcode": 0x80,
         "frame_count": 1, "frame_ops": 2, "total_ops": 2,
         "variables": variables, "initialized": 1, "room": 68, "transitions": 0,
         "room_objects": 3, "draw_queue": 2, "null_scene": 0},
        {"pc": 10, "status": 2, "error": 0, "last_opcode": 0x80,
         "frame_count": 2, "frame_ops": 2, "total_ops": 4,
         "variables": variables, "initialized": 1, "room": 1, "transitions": 1,
         "room_objects": 0, "draw_queue": 0, "null_scene": 0},
        {"pc": 13, "status": 2, "error": 0, "last_opcode": 0x80,
         "frame_count": 3, "frame_ops": 2, "total_ops": 6,
         "variables": variables, "initialized": 1, "room": 0, "transitions": 2,
         "room_objects": 0, "draw_queue": 0, "null_scene": 1},
        {"pc": 14, "status": 4, "error": 0, "last_opcode": 0,
         "frame_count": 4, "frame_ops": 1, "total_ops": 7,
         "variables": variables, "initialized": 1, "room": 0, "transitions": 2,
         "room_objects": 0, "draw_queue": 0, "null_scene": 1},
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
            observed = []
            for expected in checkpoints:
                state = snapshot(session)
                for _ in range(4):
                    step_video_frame(session)
                    state = snapshot(session)
                    if state["fixture_active"] == FIXTURE_ID and state["pc"] == expected["pc"]:
                        break
                state["video_frame"] = session.get_state()["frameCount"]
                observed.append(state)
                for key, value in expected.items():
                    require(state[key] == value, f"pc {expected['pc']} {key}={state[key]!r}, expected {value!r}")
                require(state["fixture_active"] == FIXTURE_ID, "fixture selection did not latch")
                require(state["program_select"] == FIXTURE_ID, "program selection differs")
            require(observed[-1]["video_frame"] <= 12, "gate exceeded twelve video frames")
            report["checkpoints"] = observed
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C22 SCUMM null room: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C22 SCUMM null room: PASS (variable/direct transition, local clear, no resource)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
