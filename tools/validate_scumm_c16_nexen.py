#!/usr/bin/env python3
"""Validate C16 SCUMM v5 sparse object-class state in Nexen."""

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
CLASS_RECORDS = 0x7F5F10
CLASS_INITIALIZED = 0x7F6F1B
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 40


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON_ADDRESS, 0x64)
    initialized = session.read_memory("snesMemory", CLASS_INITIALIZED, 1)[0]
    records = (
        session.read_memory("snesMemory", CLASS_RECORDS, 0x1000)
        if initialized else bytes(0x1000)
    )
    classes: dict[str, list[int]] = {}
    for offset in range(0, len(records), 8):
        if not records[offset]:
            continue
        object_id = u16(records, offset + 2)
        mask = int.from_bytes(records[offset + 4 : offset + 8], "little")
        classes[str(object_id)] = [index + 1 for index in range(32) if mask & (1 << index)]
    return {
        "pc": u16(common), "status": common[0x02], "error": common[0x03],
        "last_opcode": common[0x06], "frame_count": u16(common, 0x08),
        "frame_ops": u16(common, 0x0A), "total_ops": u16(common, 0x0C),
        "fixture_active": common[0x5F], "program_select": common[0x62],
        "object_classes": classes, "class_state_initialized": bool(initialized),
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
    output = (args.output or ROOT / "build" / f"scumm-c16-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C16-set-class", "result": "running",
        "rom": str(rom), "rom_sha256": rom_hash, "fresh_power_on": True,
        "frame_limit": 6, "donor_rom_used": False,
        "screenshots_captured": False, "audio_captured": False,
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

            first = snapshot(session)
            # C19 adds bounded boot-state initialization; allow the existing
            # six-frame gate to reach this exact first semantic tick even when
            # fixture selection lands near the following NMI boundary.
            for _ in range(4):
                step_video_frame(session)
                first = snapshot(session)
                if first["fixture_active"] == FIXTURE_ID and first["pc"] == 34:
                    break
            first["video_frame"] = session.get_state()["frameCount"]
            report["first_tick"] = first
            expected_first = {
                "pc": 34, "status": 2, "error": 0, "last_opcode": 0x80,
                "frame_count": 1, "frame_ops": 5, "total_ops": 5,
                "fixture_active": FIXTURE_ID, "program_select": FIXTURE_ID,
                "object_classes": {"42": [5], "300": [2, 5]},
                "class_state_initialized": True,
            }
            for key, value in expected_first.items():
                require(first[key] == value, f"first {key}={first[key]!r}, expected {value!r}")

            terminal = snapshot(session)
            for _ in range(2):
                step_video_frame(session)
                terminal = snapshot(session)
                if terminal["pc"] == 52:
                    break
            terminal["video_frame"] = session.get_state()["frameCount"]
            report["terminal"] = terminal
            expected_terminal = {
                "pc": 52, "status": 2, "error": 0, "last_opcode": 0x80,
                "frame_count": 2, "frame_ops": 3, "total_ops": 8,
                "fixture_active": FIXTURE_ID, "program_select": FIXTURE_ID,
                "object_classes": {"300": [2, 3]},
                "class_state_initialized": True,
            }
            for key, value in expected_terminal.items():
                require(terminal[key] == value, f"terminal {key}={terminal[key]!r}, expected {value!r}")
            require(terminal["video_frame"] <= 6, "gate exceeded six video frames")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C16 SCUMM setClass: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C16 SCUMM setClass: PASS (direct/variable sparse class masks and clear persistence)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
