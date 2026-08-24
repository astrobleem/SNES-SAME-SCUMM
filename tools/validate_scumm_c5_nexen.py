#!/usr/bin/env python3
"""Validate C5 recursive, freeze-resistant SCUMM scheduling in Nexen."""

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
    state = session.read_memory("snesMemory", C4_ADDRESS, 0x7A2)
    slots = [
        {
            "status": state[index],
            "number": state[0x19 + index],
            "program": state[0x32 + index],
            "did_exec": state[0x4B + index],
            "pc": u16(state, 0x64 + index * 2),
            "delay": u16(state, 0x96 + index * 2),
            "freeze_resistant": state[0x756 + index],
            "recursive": state[0x76F + index],
            "freeze_count": state[0x788 + index],
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
        "slots": slots, "last_allocated": state[0x709],
        "active_count": state[0x70A],
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


def slot(status: int, number: int, program: int, did_exec: int, pc: int,
         freeze_resistant: int = 0, recursive: int = 0, freeze_count: int = 0) -> dict[str, int]:
    return {
        "status": status, "number": number, "program": program,
        "did_exec": did_exec, "pc": pc, "delay": 0,
        "freeze_resistant": freeze_resistant, "recursive": recursive,
        "freeze_count": freeze_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=43990)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"scumm-c5-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C5-recursive-freeze-resistant-scheduler", "result": "running",
        "rom": str(rom), "rom_sha256": rom_hash, "fresh_power_on": True,
        "frame_limit": 8, "donor_rom_used": False,
        "screenshots_captured": False, "audio_captured": False, "cases": [],
    }
    variables = [[0] * 16 for _ in range(5)]
    variables[0][0], variables[0][10] = 1, 2
    variables[1][0:3], variables[1][10:13] = [1, 1, 1], [3, 1, 1]
    variables[2][0:4], variables[2][10:13] = [1, 1, 1, 1], [3, 1, 2]
    variables[3][0:5], variables[3][10:13] = [1, 1, 1, 1, 1], [4, 2, 3]
    variables[4] = variables[3].copy()
    expected = [
        ({"pc": 11, "status": 2, "last_opcode": 0x80, "frame_ops": 8, "total_ops": 8,
          "active_count": 3, "last_allocated": 2},
         [slot(2, 1, 19, 1, 11), slot(2, 5, 20, 1, 4), slot(2, 5, 20, 1, 4, recursive=1)]),
        ({"pc": 31, "status": 2, "last_opcode": 0x80, "frame_ops": 13, "total_ops": 21,
          "active_count": 4, "last_allocated": 3},
         [slot(2, 1, 19, 1, 31), slot(2, 5, 20, 1, 4, freeze_count=1),
          slot(2, 6, 21, 1, 4, freeze_count=1), slot(2, 7, 22, 1, 4, freeze_resistant=1)]),
        ({"pc": 4, "status": 2, "last_opcode": 0x80, "frame_ops": 7, "total_ops": 28,
          "active_count": 4, "last_allocated": 3},
         [slot(2, 1, 19, 1, 40), slot(2, 5, 20, 0, 4, freeze_count=1),
          slot(2, 6, 21, 0, 4, freeze_count=1), slot(2, 7, 22, 1, 4, freeze_resistant=1)]),
        ({"pc": 4, "status": 2, "last_opcode": 0x80, "frame_ops": 13, "total_ops": 41,
          "active_count": 4, "last_allocated": 3},
         [slot(2, 1, 19, 1, 51), slot(2, 5, 20, 1, 4), slot(2, 6, 21, 1, 4),
          slot(2, 7, 22, 1, 4, freeze_resistant=1)]),
        ({"pc": 62, "status": 4, "last_opcode": 0x00, "frame_ops": 5, "total_ops": 46,
          "active_count": 0, "last_allocated": 3},
         [slot(4, 0, 19, 1, 62), slot(4, 0, 20, 0, 4), slot(4, 0, 21, 0, 4),
          slot(4, 0, 22, 0, 4)]),
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
            session.write_u8(FIXTURE_REQUEST, 19)
            timeline = []
            for frame, (fields, expected_slots) in enumerate(expected, start=1):
                observed = snapshot(session)
                for _ in range(3):
                    step_video_frame(session)
                    observed = snapshot(session)
                    if observed["fixture_active"] == 19 and observed["frame_count"] >= frame:
                        break
                observed["video_frame"] = session.get_state()["frameCount"]
                timeline.append(observed)
                report["in_progress_timeline"] = timeline
                assert_fields(f"scheduler frame {frame}", observed, {
                    **fields, "error": 0, "frame_count": frame,
                    "variables": variables[frame - 1], "fixture_active": 19,
                    "program_select": 19, "return_mode": 0,
                })
                require(observed["slots"][:len(expected_slots)] == expected_slots,
                        f"scheduler frame {frame}: slots={observed['slots'][:len(expected_slots)]!r}")
                require(all(item["status"] == 0 for item in observed["slots"][len(expected_slots):]),
                        f"scheduler frame {frame}: unexpected occupied slot")
            report["cases"].append({"id": 19, "name": "recursive-freeze-query", "result": "pass", "timeline": timeline})
            report.pop("in_progress_timeline", None)
            report["video_frames_used"] = session.get_state()["frameCount"]
            require(int(report["video_frames_used"]) <= 8, "gate exceeded eight video frames")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C5 SCUMM scheduler: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"C5 SCUMM scheduler: PASS ({len(report['cases'])} case, {report['video_frames_used']} video frames)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
