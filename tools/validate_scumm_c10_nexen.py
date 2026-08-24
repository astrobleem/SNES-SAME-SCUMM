#!/usr/bin/env python3
"""Validate C10 SCUMM v5 roomOps intent state in Nexen."""

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
C8_SIZES_ADDRESS = 0x7E2DA0
C8_DATA_ADDRESS = 0x7E3000
C10_ADDRESS = 0x7F3000
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 34


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON_ADDRESS, 0x64)
    room = session.read_memory("snesMemory", C10_ADDRESS, 0x500)
    string_size = session.read_memory("snesMemory", C8_SIZES_ADDRESS + 5, 1)[0]
    string_data = session.read_memory("snesMemory", C8_DATA_ADDRESS + 5 * 0x100, 4)
    return {
        "pc": u16(common, 0x00),
        "status": common[0x02],
        "error": common[0x03],
        "last_opcode": common[0x06],
        "frame_count": u16(common, 0x08),
        "frame_ops": u16(common, 0x0A),
        "total_ops": u16(common, 0x0C),
        "fixture_active": common[0x5F],
        "program_select": common[0x62],
        "scroll": [u16(room, 0x02), u16(room, 0x04)],
        "screen": [u16(room, 0x06), u16(room, 0x08)],
        "shake": room[0x0A],
        "room_width": u16(room, 0x0C),
        "scale_slot_2": list(room[0x14:0x18]),
        "intensity": list(room[0x20:0x25]),
        "save_request": list(room[0x25:0x27]),
        "fade": u16(room, 0x28),
        "rgb_intensity": list(room[0x2A:0x2F]),
        "shadow": list(room[0x2F:0x34]),
        "transform": list(room[0x34:0x38]),
        "cycle_3_delay": u16(room, 0x3C),
        "palette_7_present": bool(room[0x58] & 0x80),
        "palette_7": list(room[0x8D:0x90]),
        "aux_name": bytes(room[0x379:0x37C]).decode("ascii"),
        "aux_size": room[0x3F8],
        "aux_data": list(room[0x400:0x404]),
        "string_5_size": string_size,
        "string_5_data": list(string_data),
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
    parser.add_argument("--port", type=int, default=43995)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"scumm-c10-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C10-room-ops",
        "result": "running",
        "rom": str(rom),
        "rom_sha256": rom_hash,
        "fresh_power_on": True,
        "frame_limit": 8,
        "donor_rom_used": False,
        "screenshots_captured": False,
        "audio_captured": False,
    }

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
            observed = snapshot(session)
            for _ in range(7):
                step_video_frame(session)
                observed = snapshot(session)
                if observed["fixture_active"] == FIXTURE_ID and observed["status"] == 2:
                    break
            observed["video_frame"] = session.get_state()["frameCount"]
            report["terminal"] = observed
            expected = {
                "pc": 111, "status": 2, "error": 0, "last_opcode": 0x80,
                "frame_count": 1, "frame_ops": 19, "total_ops": 19,
                "fixture_active": FIXTURE_ID, "program_select": FIXTURE_ID,
                "scroll": [160, 480], "screen": [16, 184], "shake": 1,
                "room_width": 640, "scale_slot_2": [100, 20, 200, 180],
                "intensity": [128, 128, 128, 4, 9], "save_request": [1, 99],
                "fade": 0x1234, "rgb_intensity": [100, 110, 120, 2, 8],
                "shadow": [50, 60, 70, 3, 9], "transform": [6, 2, 10, 12],
                "cycle_3_delay": 107, "palette_7_present": True,
                "palette_7": [10, 20, 30], "aux_name": "aux", "aux_size": 4,
                "aux_data": [65, 66, 67, 0], "string_5_size": 4,
                "string_5_data": [65, 66, 67, 0],
            }
            for key, value in expected.items():
                require(observed[key] == value, f"{key}={observed[key]!r}, expected {value!r}")
            require(observed["video_frame"] <= 8, "gate exceeded eight video frames")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C10 SCUMM roomOps: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C10 SCUMM roomOps: PASS (intent state, palette, strings, and cycle timing)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
