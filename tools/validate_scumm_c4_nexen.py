#!/usr/bin/env python3
"""Validate C4 script lifecycle, locals, reuse, and capacity in Nexen."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "build" / "same-engine-host.sfc"
DEFAULT_NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
COMMON_ADDRESS = 0x7E2300
C4_ADDRESS = 0x7E2380
FIXTURE_REQUEST = 0x7E235E


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON_ADDRESS, 0x64)
    c4 = session.read_memory("snesMemory", C4_ADDRESS, 0x756)
    slots = [
        {
            "status": c4[index],
            "number": c4[0x19 + index],
            "program": c4[0x32 + index],
            "did_exec": c4[0x4B + index],
            "pc": u16(c4, 0x64 + index * 2),
            "delay": u16(c4, 0x96 + index * 2),
            "local0": u16(c4, 0xC8 + index * 64),
        }
        for index in range(25)
    ]
    return {
        "pc": u16(common, 0x00), "status": common[0x02], "error": common[0x03],
        "last_opcode": common[0x06], "frame_count": u16(common, 0x08),
        "frame_ops": u16(common, 0x0A), "total_ops": u16(common, 0x0C),
        "variables": [u16(common, 0x20 + index * 2) for index in range(16)],
        "fixture_request": common[0x5E], "fixture_active": common[0x5F],
        "program_select": common[0x62], "return_mode": common[0x63],
        "slots": slots, "current_slot": c4[0x708],
        "last_allocated": c4[0x709], "active_count": c4[0x70A],
    }


def step_video_frame(session: object) -> None:
    for _ in range(20):
        run = session.run_frames(1)
        if run["framesAdvanced"] == 1:
            return
    raise GateFailure(f"one-frame step made no progress: {run}")


def assert_fields(name: str, observed: dict[str, object], expected: dict[str, object]) -> None:
    for key, value in expected.items():
        require(observed[key] == value, f"{name}: {key}={observed[key]!r}, expected {value!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=43989)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"scumm-c4-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C4-script-lifecycle-locals-capacity", "result": "running",
        "rom": str(rom), "rom_sha256": rom_hash, "fresh_power_on": True,
        "frame_limit": 8, "donor_rom_used": False,
        "screenshots_captured": False, "audio_captured": False, "cases": [],
    }
    expected = [
        ({"pc": 12, "status": 2, "error": 0, "last_opcode": 0x80, "frame_count": 1,
          "frame_ops": 6, "total_ops": 6, "variables": [1, 10] + [0] * 14,
          "active_count": 2, "last_allocated": 1, "program_select": 14, "return_mode": 0},
         {"status": 2, "number": 1, "program": 14, "did_exec": 1, "pc": 12, "delay": 0, "local0": 0},
         {"status": 2, "number": 2, "program": 15, "did_exec": 1, "pc": 9, "delay": 0, "local0": 11}),
        ({"pc": 26, "status": 2, "error": 0, "last_opcode": 0x80, "frame_count": 2,
          "frame_ops": 8, "total_ops": 14, "variables": [2, 10, 20, 21] + [0] * 12,
          "active_count": 1, "last_allocated": 1, "program_select": 14, "return_mode": 0},
         {"status": 2, "number": 1, "program": 14, "did_exec": 1, "pc": 26, "delay": 0, "local0": 0},
         {"status": 4, "number": 0, "program": 16, "did_exec": 1, "pc": 15, "delay": 0, "local0": 21}),
        ({"pc": 35, "status": 4, "error": 0, "last_opcode": 0x00, "frame_count": 3,
          "frame_ops": 5, "total_ops": 19, "variables": [2, 10, 20, 21, 30] + [0] * 11,
          "active_count": 0, "last_allocated": 1, "program_select": 14, "return_mode": 0},
         {"status": 4, "number": 0, "program": 14, "did_exec": 1, "pc": 35, "delay": 0, "local0": 0},
         {"status": 4, "number": 0, "program": 17, "did_exec": 1, "pc": 6, "delay": 0, "local0": 30}),
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
            session.write_u8(FIXTURE_REQUEST, 14)
            timeline = []
            for frame, (fields, slot0, slot1) in enumerate(expected, start=1):
                observed = snapshot(session)
                for _ in range(3):
                    step_video_frame(session)
                    observed = snapshot(session)
                    if observed["fixture_active"] == 14 and observed["frame_count"] >= frame:
                        break
                observed["video_frame"] = session.get_state()["frameCount"]
                timeline.append(observed)
                report["in_progress_lifecycle"] = timeline
                assert_fields(f"lifecycle frame {frame}", observed, fields)
                require(observed["slots"][0] == slot0, f"lifecycle frame {frame}: slot0={observed['slots'][0]!r}")
                require(observed["slots"][1] == slot1, f"lifecycle frame {frame}: slot1={observed['slots'][1]!r}")
                require(all(item["status"] == 0 for item in observed["slots"][2:]), f"lifecycle frame {frame}: unexpected occupied slot")
            report["cases"].append({"id": 14, "name": "nested-lifecycle-locals-reuse", "result": "pass", "timeline": timeline})
            report.pop("in_progress_lifecycle", None)
            session.write_u8(FIXTURE_REQUEST, 18)
            capacity = snapshot(session)
            for _ in range(3):
                step_video_frame(session)
                capacity = snapshot(session)
                if capacity["fixture_active"] == 18 and capacity["status"] == 0xFF:
                    break
            capacity["video_frame"] = session.get_state()["frameCount"]
            assert_fields("capacity", capacity, {
                "pc": 3, "status": 0xFF, "error": 9, "last_opcode": 0x2A,
                "frame_count": 0, "frame_ops": 1, "total_ops": 1,
                "variables": [0] * 16, "active_count": 25,
                "fixture_active": 18, "program_select": 18, "return_mode": 0,
            })
            require(capacity["slots"][0]["status"] == 0xFF, "capacity: slot0 did not retain error")
            require(all(item["status"] == 1 for item in capacity["slots"][1:]), "capacity: table was not full")
            report["cases"].append({"id": 18, "name": "slot-capacity", "result": "pass", "terminal": capacity})
            report["video_frames_used"] = session.get_state()["frameCount"]
            require(int(report["video_frames_used"]) <= 8, "gate exceeded eight video frames")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C4 SCUMM lifecycle: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"C4 SCUMM lifecycle: PASS ({len(report['cases'])} cases, {report['video_frames_used']} video frames)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
