#!/usr/bin/env python3
"""Validate C14 full-header SCUMM v5 actorOps state in Nexen."""

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
ACTORS_ADDRESS = 0x7F36C0
NAME_SIZES_ADDRESS = 0x7F3EC0
NAMES_ADDRESS = 0x7F3F00
INITIALIZED_ADDRESS = 0x7F5F08
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 38
ACTOR_STRIDE = 64


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


def actor_state(session: object, actor: int) -> dict[str, object] | None:
    raw = session.read_memory("snesMemory", ACTORS_ADDRESS + actor * ACTOR_STRIDE, ACTOR_STRIDE)
    if not raw[0x1F]:
        return None
    name_size = session.read_memory("snesMemory", NAME_SIZES_ADDRESS + actor, 1)[0]
    name = session.read_memory("snesMemory", NAMES_ADDRESS + actor * 256, name_size)
    return {
        "costume": raw[0],
        "walk_speed": [raw[1], raw[2]],
        "sound": raw[3],
        "frames": [raw[4], raw[5], raw[6], raw[7], raw[8]],
        "talk_color": raw[9],
        "elevation": s16(raw, 0x0A),
        "width": raw[0x0C],
        "scale": [raw[0x0D], raw[0x0E]],
        "box_scale": raw[0x0F],
        "force_clip": raw[0x10],
        "ignore_boxes": bool(raw[0x11]),
        "animation_speed": raw[0x12],
        "shadow": raw[0x13],
        "palette": {str(slot): value for slot, value in enumerate(raw[0x20:0x40]) if value},
        "name": list(name),
    }


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON_ADDRESS, 0x64)
    initialized = bool(session.read_memory("snesMemory", INITIALIZED_ADDRESS, 1)[0])
    return {
        "pc": u16(common), "status": common[0x02], "error": common[0x03],
        "last_opcode": common[0x06], "frame_count": u16(common, 0x08),
        "frame_ops": u16(common, 0x0A), "total_ops": u16(common, 0x0C),
        "fixture_active": common[0x5F], "program_select": common[0x62],
        "actor_state_initialized": initialized,
        "actors": {
            str(actor): state
            for actor in range(32)
            if (state := actor_state(session, actor)) is not None
        } if initialized else {},
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
    parser.add_argument("--port", type=int, default=43999)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"scumm-c14-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C14-actor-ops", "result": "running",
        "rom": str(rom), "rom_sha256": rom_hash, "fresh_power_on": True,
        "frame_limit": 8, "donor_rom_used": False,
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
            for _ in range(6):
                step_video_frame(session)
                first = snapshot(session)
                if first["fixture_active"] == FIXTURE_ID and first["pc"] == 89:
                    break
            first["video_frame"] = session.get_state()["frameCount"]
            report["first_tick"] = first
            terminal = snapshot(session)
            for _ in range(3):
                step_video_frame(session)
                terminal = snapshot(session)
                if terminal["pc"] == 115:
                    break
            terminal["video_frame"] = session.get_state()["frameCount"]
            report["terminal"] = terminal

            expected_actor1 = {
                "costume": 7, "walk_speed": [3, 4], "sound": 5,
                "frames": [16, 17, 18, 19, 20], "talk_color": 34,
                "elevation": -2, "width": 35, "scale": [36, 37], "box_scale": 36,
                "force_clip": 0, "ignore_boxes": False,
                "animation_speed": 39, "shadow": 40,
                "palette": {"2": 33}, "name": list(b"Actor One\0"),
            }
            expected_actor2 = {
                "costume": 55, "walk_speed": [8, 2], "sound": 0,
                "frames": [1, 2, 3, 4, 5], "talk_color": 15,
                "elevation": 0, "width": 24, "scale": [255, 255], "box_scale": 255,
                "force_clip": 0, "ignore_boxes": False,
                "animation_speed": 0, "shadow": 0,
                "palette": {"3": 44}, "name": list(b"Actor Two\0"),
            }
            require(first["pc"] == 89, f"first pc={first['pc']!r}, expected 89")
            require(first["actors"] == {"1": expected_actor1}, f"first actors={first['actors']!r}")
            expected_terminal = {
                "pc": 115, "status": 2, "error": 0, "last_opcode": 0x80,
                "frame_count": 2, "frame_ops": 2, "total_ops": 8,
                "fixture_active": FIXTURE_ID, "program_select": FIXTURE_ID,
                "actor_state_initialized": True,
                "actors": {"1": expected_actor1, "2": expected_actor2},
            }
            for key, value in expected_terminal.items():
                require(terminal[key] == value, f"{key}={terminal[key]!r}, expected {value!r}")
            require(terminal["video_frame"] <= 8, "gate exceeded eight video frames")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C14 SCUMM actorOps: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C14 SCUMM actorOps: PASS (full header, variables, defaults, names, palette, clipping)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
