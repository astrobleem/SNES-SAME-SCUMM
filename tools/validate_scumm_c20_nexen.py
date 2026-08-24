#!/usr/bin/env python3
"""Validate C20 SCUMM v5 doSentence queue semantics in Nexen."""

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
C20_ADDRESS = 0x7FD380
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 44


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
    sentence = session.read_memory("snesMemory", C20_ADDRESS, 0x2C)
    records = []
    for index in range(sentence[0]):
        offset = 2 + index * 6
        object_b = u16(sentence, offset + 4)
        records.append({
            "verb": sentence[offset],
            "object_a": u16(sentence, offset + 2),
            "object_b": object_b,
            "preposition": object_b != 0,
            "freeze_count": sentence[offset + 1],
        })
    return {
        "pc": u16(common), "status": common[0x02], "error": common[0x03],
        "last_opcode": common[0x06], "frame_count": u16(common, 0x08),
        "frame_ops": u16(common, 0x0A), "total_ops": u16(common, 0x0C),
        "fixture_active": common[0x5F], "program_select": common[0x62],
        "variables": [s16(common, 0x20 + index * 2) for index in range(16)],
        "sentence_count": sentence[0], "sentence_initialized": sentence[1],
        "sentences": records,
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
    output = (args.output or ROOT / "build" / f"scumm-c20-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C20-do-sentence", "result": "running", "rom": str(rom),
        "rom_sha256": rom_hash, "fresh_power_on": True, "frame_limit": 12,
        "donor_rom_used": False, "screenshots_captured": False, "audio_captured": False,
    }

    first_sentences = [
        {"verb": 1, "object_a": 100, "object_b": 0, "preposition": False, "freeze_count": 1},
        {"verb": 2, "object_a": 101, "object_b": 7, "preposition": True, "freeze_count": 1},
        {"verb": 3, "object_a": 0x1111, "object_b": 102, "preposition": True, "freeze_count": 1},
        {"verb": 4, "object_a": 0x1111, "object_b": 0x2222, "preposition": True, "freeze_count": 1},
    ]
    terminal_sentences = [
        {"verb": 7, "object_a": 103, "object_b": 0, "preposition": False, "freeze_count": 1},
        {"verb": 7, "object_a": 104, "object_b": 0x2222, "preposition": True, "freeze_count": 1},
        {"verb": 7, "object_a": 0x1111, "object_b": 105, "preposition": True, "freeze_count": 1},
        {"verb": 7, "object_a": 0x1111, "object_b": 0x2222, "preposition": True, "freeze_count": 1},
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
                if first["fixture_active"] == FIXTURE_ID and first["pc"] == 42:
                    break
            first["video_frame"] = session.get_state()["frameCount"]
            report["first_tick"] = first
            expected_variables = [7, 0x1111, 0x2222] + [0] * 13
            expected_first = {
                "pc": 42, "status": 2, "error": 0, "last_opcode": 0x80,
                "frame_count": 1, "frame_ops": 9, "total_ops": 9,
                "fixture_active": FIXTURE_ID, "program_select": FIXTURE_ID,
                "variables": expected_variables, "sentence_count": 4,
                "sentence_initialized": 1, "sentences": first_sentences,
            }
            for key, value in expected_first.items():
                require(first[key] == value, f"first {key}={first[key]!r}, expected {value!r}")

            terminal = snapshot(session)
            for _ in range(4):
                step_video_frame(session)
                terminal = snapshot(session)
                if terminal["pc"] == 77:
                    break
            terminal["video_frame"] = session.get_state()["frameCount"]
            report["terminal"] = terminal
            expected_terminal = {
                **expected_first, "pc": 77, "frame_count": 2,
                "frame_ops": 8, "total_ops": 17, "sentences": terminal_sentences,
            }
            for key, value in expected_terminal.items():
                require(terminal[key] == value, f"terminal {key}={terminal[key]!r}, expected {value!r}")
            require(terminal["video_frame"] <= 12, "gate exceeded twelve video frames")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C20 SCUMM doSentence: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C20 SCUMM doSentence: PASS (all operand forms, cancel, freeze, exact queue)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
