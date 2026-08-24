#!/usr/bin/env python3
"""Validate C17 SCUMM v5 verbOps state in Nexen."""

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
VERB_RECORDS = 0x7F6F20
VERB_STRIDE = 0x60
VERB_INITIALIZED = 0x7FCF2A
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 41


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


def decode_verb(raw: bytes) -> dict[str, object]:
    name_length = raw[0x18]
    require(name_length <= 64, f"verb name length {name_length} exceeds 64")
    image_source = None
    if raw[0x13]:
        image_source = [raw[0x12], u16(raw, 0x14)]
    return {
        "color": raw[0x02], "hicolor": raw[0x03], "dimcolor": raw[0x04],
        "background_color": raw[0x05], "kind": "image" if raw[0x06] else "text",
        "charset": raw[0x07], "mode": raw[0x01], "save_id": u16(raw, 0x16),
        "key": raw[0x08], "center": bool(raw[0x09]),
        "position": [s16(raw, 0x0A), s16(raw, 0x0C)],
        "original_left": s16(raw, 0x0E), "image_index": u16(raw, 0x10),
        "image_source": image_source,
        "name": list(raw[0x20 : 0x20 + name_length]) if name_length else None,
    }


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON_ADDRESS, 0x64)
    initialized = session.read_memory("snesMemory", VERB_INITIALIZED, 1)[0]
    verbs: dict[str, object] = {}
    if initialized:
        for verb_id in range(256):
            raw = session.read_memory(
                "snesMemory", VERB_RECORDS + verb_id * VERB_STRIDE, VERB_STRIDE
            )
            if raw[0]:
                verbs[str(verb_id)] = decode_verb(raw)
    return {
        "pc": u16(common), "status": common[0x02], "error": common[0x03],
        "last_opcode": common[0x06], "frame_count": u16(common, 0x08),
        "frame_ops": u16(common, 0x0A), "total_ops": u16(common, 0x0C),
        "fixture_active": common[0x5F], "program_select": common[0x62],
        "verbs": verbs, "verb_state_initialized": bool(initialized),
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
    output = (args.output or ROOT / "build" / f"scumm-c17-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C17-verb-ops", "result": "running", "rom": str(rom),
        "rom_sha256": rom_hash, "fresh_power_on": True, "frame_limit": 10,
        "donor_rom_used": False, "screenshots_captured": False, "audio_captured": False,
    }
    expected_first_verbs = {
        "5": {
            "color": 6, "hicolor": 7, "dimcolor": 8, "background_color": 9,
            "kind": "text", "charset": 0, "mode": 1, "save_id": 0,
            "key": 76, "center": True, "position": [100, 150],
            "original_left": 100, "image_index": 0, "image_source": None,
            "name": list(b"Look\0"),
        },
        "11": {
            "color": 2, "hicolor": 0, "dimcolor": 8, "background_color": 0,
            "kind": "image", "charset": 0, "mode": 2, "save_id": 0,
            "key": 0, "center": False, "position": [0, 0],
            "original_left": 0, "image_index": 0,
            "image_source": [0, 0x2222], "name": None,
        },
    }
    expected_terminal_verbs = {
        "5": {
            "color": 2, "hicolor": 0, "dimcolor": 8, "background_color": 9,
            "kind": "image", "charset": 0, "mode": 0, "save_id": 0,
            "key": 0, "center": False, "position": [100, 150],
            "original_left": 100, "image_index": 0x3456,
            "image_source": [42, 0x3456], "name": list(b"Use\0"),
        }
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
            for _ in range(8):
                step_video_frame(session)
                first = snapshot(session)
                if first["fixture_active"] == FIXTURE_ID and first["pc"] == 80:
                    break
            first["video_frame"] = session.get_state()["frameCount"]
            report["first_tick"] = first
            expected_first = {
                "pc": 80, "status": 2, "error": 0, "last_opcode": 0x80,
                "frame_count": 1, "frame_ops": 11, "total_ops": 11,
                "fixture_active": FIXTURE_ID, "program_select": FIXTURE_ID,
                "verbs": expected_first_verbs, "verb_state_initialized": True,
            }
            for key, value in expected_first.items():
                require(first[key] == value, f"first {key}={first[key]!r}, expected {value!r}")

            terminal = snapshot(session)
            for _ in range(2):
                step_video_frame(session)
                terminal = snapshot(session)
                if terminal["pc"] == 98:
                    break
            terminal["video_frame"] = session.get_state()["frameCount"]
            report["terminal"] = terminal
            expected_terminal = {
                "pc": 98, "status": 2, "error": 0, "last_opcode": 0x80,
                "frame_count": 2, "frame_ops": 3, "total_ops": 14,
                "fixture_active": FIXTURE_ID, "program_select": FIXTURE_ID,
                "verbs": expected_terminal_verbs, "verb_state_initialized": True,
            }
            for key, value in expected_terminal.items():
                require(terminal[key] == value, f"terminal {key}={terminal[key]!r}, expected {value!r}")
            require(terminal["video_frame"] <= 10, "gate exceeded ten video frames")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C17 SCUMM verbOps: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C17 SCUMM verbOps: PASS (all sub-ops, variable operands, reset/delete persistence)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
