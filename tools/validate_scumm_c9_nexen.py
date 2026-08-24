#!/usr/bin/env python3
"""Validate C9 SCUMM v5 setVarRange semantics in Nexen."""

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
LOCAL_ADDRESS = 0x7E2448
BITS_ADDRESS = 0x7E2BA0
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 33


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON_ADDRESS, 0x64)
    locals_raw = session.read_memory("snesMemory", LOCAL_ADDRESS, 6)
    bits = session.read_memory("snesMemory", BITS_ADDRESS, 1)
    return {
        "pc": u16(common, 0x00),
        "status": common[0x02],
        "error": common[0x03],
        "last_opcode": common[0x06],
        "frame_count": u16(common, 0x08),
        "frame_ops": u16(common, 0x0A),
        "total_ops": u16(common, 0x0C),
        "variables": [u16(common, 0x20 + index * 2) for index in range(16)],
        "fixture_active": common[0x5F],
        "program_select": common[0x62],
        "locals": [u16(locals_raw, index * 2) for index in range(3)],
        "bits0": bits[0],
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
    parser.add_argument("--port", type=int, default=43994)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"scumm-c9-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C9-set-var-range",
        "result": "running",
        "rom": str(rom),
        "rom_sha256": rom_hash,
        "fresh_power_on": True,
        "frame_limit": 3,
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
            for _ in range(2):
                step_video_frame(session)
                observed = snapshot(session)
                if observed["fixture_active"] == FIXTURE_ID and observed["status"] == 2:
                    break
            observed["video_frame"] = session.get_state()["frameCount"]
            report["terminal"] = observed
            expected = {
                "pc": 32, "status": 2, "error": 0, "last_opcode": 0x80,
                "frame_count": 1, "frame_ops": 5, "total_ops": 5,
                "fixture_active": FIXTURE_ID, "program_select": FIXTURE_ID,
                "locals": [0xFFFF, 0x7FFF, 0x8000], "bits0": 0xC0,
            }
            for key, value in expected.items():
                require(observed[key] == value, f"{key}={observed[key]!r}, expected {value!r}")
            require(observed["variables"] == [2, 0, 0, 0, 0, 0, 1, 255, 128, 0, 0, 0, 0, 0, 0, 0],
                    f"variables={observed['variables']!r}")
            require(observed["video_frame"] <= 3, "gate exceeded three video frames")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C9 SCUMM setVarRange: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C9 SCUMM setVarRange: PASS (byte, word, indexed, local, and bit ranges)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
