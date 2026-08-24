#!/usr/bin/env python3
"""Validate C3 indexed operands and two-slot SCUMM scheduling in Nexen."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "build" / "same-engine-host.sfc"
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
STATE_ADDRESS = 0x7E2300
STATE_LENGTH = 0x64
FIXTURE_REQUEST = 0x7E235E
BITS_ADDRESS = 0x7E2BA0


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def snapshot(session: object) -> dict[str, object]:
    raw = session.read_memory("snesMemory", STATE_ADDRESS, STATE_LENGTH)
    return {
        "pc": u16(raw, 0x00),
        "status": raw[0x02],
        "error": raw[0x03],
        "delay": u16(raw, 0x04),
        "last_opcode": raw[0x06],
        "frame_count": u16(raw, 0x08),
        "frame_ops": u16(raw, 0x0A),
        "total_ops": u16(raw, 0x0C),
        "variables": [u16(raw, 0x20 + index * 2) for index in range(16)],
        "slot0": {"pc": u16(raw, 0x50), "delay": u16(raw, 0x52), "status": raw[0x54]},
        "slot1": {"pc": u16(raw, 0x56), "delay": u16(raw, 0x58), "status": raw[0x5A]},
        "scheduler_ops": u16(raw, 0x5C),
        "fixture_request": raw[0x5E],
        "fixture_active": raw[0x5F],
        "program_select": raw[0x62],
        "return_mode": raw[0x63],
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


def select_and_collect(session: object, fixture: int, completed_frames: int) -> list[dict[str, object]]:
    session.write_u8(FIXTURE_REQUEST, fixture)
    timeline: list[dict[str, object]] = []
    seen: set[int] = set()
    for _ in range(completed_frames + 4):
        step_video_frame(session)
        state = snapshot(session)
        state["video_frame"] = session.get_state()["frameCount"]
        frame = int(state["frame_count"])
        if state["fixture_active"] == fixture and 1 <= frame <= completed_frames and frame not in seen:
            seen.add(frame)
            timeline.append(state)
        if len(timeline) == completed_frames:
            break
    require(len(timeline) == completed_frames, f"fixture {fixture}: completed frames {sorted(seen)}")
    return timeline


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=43988)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rom = args.rom.resolve()
    nexen = args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"scumm-c3-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C3-indexed-operands-and-script-slots",
        "result": "running",
        "rom": str(rom),
        "rom_sha256": rom_hash,
        "fresh_power_on": True,
        "frame_limit": 119,
        "donor_rom_used": False,
        "screenshots_captured": False,
        "audio_captured": False,
        "cases": [],
    }

    operand_vars_1 = [2, 0x8000, 1, 0, 0, 0, 5, 0x1234] + [0] * 8
    operand_vars_2 = [2, 0x7FFF, 1, 0, 0, 0, 5, 0x1234] + [0] * 8
    operand_vars_3 = [2, 4681, 1, 7, 255, 255, 6, 0x1234] + [0] * 8
    operand_expected = [
        {"pc": 35, "status": 2, "error": 0, "last_opcode": 0x80, "frame_count": 1, "frame_ops": 7, "total_ops": 7, "variables": operand_vars_1},
        {"pc": 41, "status": 2, "error": 0, "last_opcode": 0x80, "frame_count": 2, "frame_ops": 2, "total_ops": 9, "variables": operand_vars_2},
        {"pc": 134, "status": 4, "error": 0, "last_opcode": 0x00, "frame_count": 3, "frame_ops": 17, "total_ops": 26, "variables": operand_vars_3},
    ]
    scheduler_expected = [
        (3, 3, 4, 2, 3, 4, 1, 0),
        (3, 6, 4, 1, 3, 4, 2, 0),
        (3, 9, 4, 0, 3, 4, 3, 0),
        (5, 14, 8, 0, 2, 4, 4, 1),
        (6, 20, 8, 0, 2, 4, 5, 2),
    ]

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session

    mcp_session.validate_mesen_build = lambda _path: None
    try:
        with mcp_session.McpSession(
            rom=rom,
            mesen=nexen,
            cwd=ROOT,
            port=args.port,
            boot_wait=2.0,
            socket_timeout=30.0,
            stderr_log=output / "nexen-stderr.log",
        ) as session:
            session.pause()
            session.tool("reset_emulator", {"power": True})
            session.pause()
            require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")
            step_video_frame(session)
            report["bootstrap"] = snapshot(session)

            operands = select_and_collect(session, 9, 3)
            for observed, expected in zip(operands, operand_expected, strict=True):
                assert_fields("operands", observed, expected)
            report["cases"].append({"id": 9, "name": "indexed-variable-wrap", "result": "pass", "timeline": operands})

            session.write_u8(FIXTURE_REQUEST, 13)
            bit_terminal = None
            bit_observations = []
            for _ in range(3):
                step_video_frame(session)
                state = snapshot(session)
                state["video_frame"] = session.get_state()["frameCount"]
                bit_observations.append(state)
                if state["fixture_active"] == 13 and state["status"] == 4:
                    bit_terminal = state
                    break
            require(bit_terminal is not None, "bit-variable fixture did not stop")
            assert_fields("bit-variable", bit_terminal, {
                "pc": 6, "status": 4, "error": 0, "last_opcode": 0x00,
                "frame_count": 1, "frame_ops": 2, "total_ops": 2,
                "variables": [0] * 16,
            })
            require(session.read_memory("snesMemory", BITS_ADDRESS, 1) == bytes([1]),
                    "bit-variable: packed bit zero was not set")
            report["cases"].append({"id": 13, "name": "bit-variable-result", "result": "pass", "terminal": bit_terminal, "bits": [0], "observations": bit_observations})

            scheduler = select_and_collect(session, 10, 5)
            for frame, (observed, expected) in enumerate(zip(scheduler, scheduler_expected, strict=True), start=1):
                frame_ops, total_ops, slot0_pc, slot0_delay, slot0_status, slot1_pc, peer_count, delayed_count = expected
                assert_fields("scheduler", observed, {
                    "status": 2, "error": 0, "frame_count": frame,
                    "frame_ops": frame_ops, "total_ops": total_ops,
                    "slot0": {"pc": slot0_pc, "delay": slot0_delay, "status": slot0_status},
                    "slot1": {"pc": slot1_pc, "delay": 0, "status": 2},
                    "scheduler_ops": frame_ops,
                    "program_select": 10, "return_mode": 0,
                })
                variables = observed["variables"]
                require(variables[11] == peer_count, f"scheduler frame {frame}: peer count {variables[11]}")
                require(variables[10] == delayed_count, f"scheduler frame {frame}: delayed count {variables[10]}")
            report["cases"].append({"id": 10, "name": "two-slot-fairness", "result": "pass", "timeline": scheduler})

            report["video_frames_used"] = session.get_state()["frameCount"]
            require(int(report["video_frames_used"]) < 120, "gate exceeded its 119-frame limit")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C3 SCUMM matrix: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1

    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"C3 SCUMM matrix: PASS ({len(report['cases'])} cases, {report['video_frames_used']} video frames)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
