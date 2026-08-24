#!/usr/bin/env python3
"""Validate C13 SCUMM v5 resource-routine intent in Nexen."""

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
MAPPER_ADDRESS = 0x7F3510
LOADED_ADDRESS = 0x7F3590
LOCKED_ADDRESS = 0x7F3630
OBJECT_ADDRESS = 0x7F36B0
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 37
KINDS = ("script", "sound", "costume", "room", "charset")


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def unpack_tables(raw: bytes, kinds: tuple[str, ...]) -> dict[str, list[int]]:
    return {
        kind: [resource for resource in range(256) if raw[index * 32 + resource // 8] & (1 << (resource & 7))]
        for index, kind in enumerate(kinds)
    }


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON_ADDRESS, 0x64)
    mapper = session.read_memory("snesMemory", MAPPER_ADDRESS, 128)
    loaded = session.read_memory("snesMemory", LOADED_ADDRESS, 160)
    locked = session.read_memory("snesMemory", LOCKED_ADDRESS, 128)
    obj = session.read_memory("snesMemory", OBJECT_ADDRESS, 4)
    mapper_initialized = bool(session.read_memory("snesMemory", 0x7F3507, 1)[0])
    resource_initialized = bool(session.read_memory("snesMemory", 0x7F36B8, 1)[0])
    return {
        "pc": u16(common), "status": common[0x02], "error": common[0x03],
        "last_opcode": common[0x06], "frame_count": u16(common, 0x08),
        "frame_ops": u16(common, 0x0A), "total_ops": u16(common, 0x0C),
        "fixture_active": common[0x5F], "program_select": common[0x62],
        "resource_initialized": resource_initialized,
        "loaded": unpack_tables(loaded, KINDS) if resource_initialized else {},
        "locked": unpack_tables(locked, KINDS[:4]) if resource_initialized else {},
        "last_object": {"room": obj[0], "id": u16(obj, 2)} if resource_initialized else None,
        "mapper_initialized": mapper_initialized,
        "mapped_rooms": (
            {str(index): room for index, room in enumerate(mapper) if room}
            if mapper_initialized else {}
        ),
        "loaded_sha256": hashlib.sha256(loaded).hexdigest() if resource_initialized else None,
        "locked_sha256": hashlib.sha256(locked).hexdigest() if resource_initialized else None,
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
    parser.add_argument("--port", type=int, default=43998)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"scumm-c13-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C13-resource-routines", "result": "running",
        "rom": str(rom), "rom_sha256": rom_hash, "fresh_power_on": True,
        "frame_limit": 5, "donor_rom_used": False,
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
            observed = snapshot(session)
            for _ in range(4):
                step_video_frame(session)
                observed = snapshot(session)
                if observed["fixture_active"] == FIXTURE_ID and observed["pc"] == 76:
                    break
            observed["video_frame"] = session.get_state()["frameCount"]
            report["terminal"] = observed
            expected = {
                "pc": 76, "status": 2, "error": 0, "last_opcode": 0x80,
                "frame_count": 2, "frame_ops": 14, "total_ops": 25,
                "fixture_active": FIXTURE_ID, "program_select": FIXTURE_ID,
                "resource_initialized": True, "mapper_initialized": True,
                "loaded": {
                    "script": [], "sound": [8], "costume": [], "room": [42], "charset": [],
                },
                "locked": {"script": [], "sound": [], "costume": [], "room": []},
                "last_object": {"room": 42, "id": 0x1234},
                "mapped_rooms": {"0": 42},
            }
            for key, value in expected.items():
                require(observed[key] == value, f"{key}={observed[key]!r}, expected {value!r}")
            require(observed["video_frame"] <= 5, "gate exceeded five video frames")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C13 SCUMM resource routines: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C13 SCUMM resource routines: PASS (load, nuke, lock, unlock, variable, pseudo-room, object)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
