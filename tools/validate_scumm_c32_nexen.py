#!/usr/bin/env python3
"""Validate C32 canonical SCUMM v5 putActorAtObject semantics in Nexen."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "build/same-scumm-v5.sfc"
DEFAULT_NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
COMMON = 0x7E2300
VARIABLES = 0x7E2320
ACTORS = 0x7F36C0
ACTOR_STRIDE = 0x40
OBJECT_COUNT = 0x7FD3AD
OBJECT_RECORDS = 0x7FD3B0
OBJECT_STRIDE = 0x10
CURRENT_ROOM = 0x7FD403
POSITIONS = 0x7FF1A0
MOVING = 0x7FF220
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 55


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def s16(raw: bytes, offset: int = 0) -> int:
    value = u16(raw, offset)
    return value - 0x10000 if value & 0x8000 else value


def actor_snapshot(session: object, actor_id: int) -> dict[str, object]:
    record = session.read_memory("snesMemory", ACTORS + actor_id * ACTOR_STRIDE, ACTOR_STRIDE)
    position = session.read_memory("snesMemory", POSITIONS + actor_id * 4, 4)
    return {
        "room": record[0x16], "visible": bool(record[0x15]),
        "position": [s16(position), s16(position, 2)],
        "moving": session.read_memory("snesMemory", MOVING + actor_id, 1)[0],
        "present": bool(record[0x1F]),
    }


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON, 0x64)
    variables = session.read_memory("snesMemory", VARIABLES, 4)
    return {
        "pc": u16(common), "status": common[2], "error": common[3],
        "last_opcode": common[6], "frame_count": u16(common, 8),
        "frame_ops": u16(common, 10), "total_ops": u16(common, 12),
        "fixture_active": common[0x5F], "program_select": common[0x62],
        "variables": [u16(variables), u16(variables, 2)],
        "current_room": session.read_memory("snesMemory", CURRENT_ROOM, 1)[0],
        "actors": {str(actor_id): actor_snapshot(session, actor_id) for actor_id in (1, 2, 3)},
    }


def actor_record(room: int, visible: bool) -> bytes:
    record = bytearray(ACTOR_STRIDE)
    record[0x15], record[0x16], record[0x1F] = int(visible), room, 1
    return bytes(record)


def object_record(object_id: int, walk: tuple[int, int]) -> bytes:
    record = bytearray(OBJECT_STRIDE)
    record[0:2] = object_id.to_bytes(2, "little")
    record[2:4], record[4:6] = (80).to_bytes(2, "little"), (60).to_bytes(2, "little")
    record[6:8], record[8:10] = (24).to_bytes(2, "little"), (24).to_bytes(2, "little")
    record[10:12] = int(walk[0] & 0xFFFF).to_bytes(2, "little")
    record[12:14] = int(walk[1] & 0xFFFF).to_bytes(2, "little")
    return bytes(record)


def install_fixture_state(session: object) -> None:
    session.write_u8(CURRENT_ROOM, 75)
    session.write_u8(OBJECT_COUNT, 2)
    for index, record in enumerate((object_record(100, (120, 80)), object_record(101, (300, 90)))):
        session.write_memory("snesMemory", OBJECT_RECORDS + index * OBJECT_STRIDE, record.hex())
    initial = {
        1: (75, False, (0, 0), 4),
        2: (76, True, (5, 6), 3),
        3: (76, False, (7, 8), 2),
    }
    for actor_id, (room, visible, position, moving) in initial.items():
        session.write_memory("snesMemory", ACTORS + actor_id * ACTOR_STRIDE,
                             actor_record(room, visible).hex())
        encoded = b"".join(int(value & 0xFFFF).to_bytes(2, "little") for value in position)
        session.write_memory("snesMemory", POSITIONS + actor_id * 4, encoded.hex())
        session.write_u8(MOVING + actor_id, moving)


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
    parser.add_argument("--port", type=int, default=44004)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / f"build/scumm-c32-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C32-put-actor-at-object", "result": "running", "rom": str(rom),
        "rom_sha256": rom_hash, "fresh_power_on": True, "frame_limit": 12,
        "donor_rom_used": False, "screenshots_captured": False, "audio_captured": False,
    }
    try:
        sys.path.insert(0, "/home/chad/Mesen2/python")
        import mesen_mcp.session as mcp_session
        mcp_session.validate_mesen_build = lambda _path: None
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
            setup = snapshot(session)
            for _ in range(10):
                step_video_frame(session)
                setup = snapshot(session)
                if setup["fixture_active"] == FIXTURE_ID and setup["pc"] == 1:
                    break
            require(setup["status"] == 2 and setup["error"] == 0 and
                    setup["last_opcode"] == 0x80 and setup["frame_ops"] == 1,
                    "fixture setup yield differs")
            install_fixture_state(session)
            direct = snapshot(session)
            for _ in range(6):
                step_video_frame(session)
                direct = snapshot(session)
                if direct["pc"] == 6:
                    break
            require(direct["pc"] == 6 and direct["status"] == 2 and
                    direct["error"] == 0 and direct["frame_ops"] == 2,
                    "direct placement checkpoint differs")
            require(direct["actors"]["1"] == {
                "room": 75, "visible": True, "position": [120, 80],
                "moving": 0, "present": True,
            }, "current-room object walk-point placement differs")
            resolved = snapshot(session)
            for _ in range(6):
                step_video_frame(session)
                resolved = snapshot(session)
                if resolved["pc"] == 26:
                    break
            require(resolved["pc"] == 26 and resolved["status"] == 2 and
                    resolved["error"] == 0 and resolved["frame_ops"] == 5,
                    "variable/fallback placement checkpoint differs")
            require(resolved["variables"] == [2, 101], "fixture variable setup differs")
            require(resolved["actors"]["2"] == {
                "room": 76, "visible": False, "position": [300, 90],
                "moving": 0, "present": True,
            }, "noncurrent visible actor lifecycle differs")
            require(resolved["actors"]["3"] == {
                "room": 76, "visible": False, "position": [240, 120],
                "moving": 2, "present": True,
            }, "missing-object fallback or hidden actor lifecycle differs")
            halted = snapshot(session)
            for _ in range(4):
                step_video_frame(session)
                halted = snapshot(session)
                if halted["pc"] == 27 and halted["status"] == 4:
                    break
            report["checkpoints"] = [setup, direct, resolved, halted]
            require(halted["pc"] == 27 and halted["status"] == 4 and halted["error"] == 0,
                    "fixture did not halt cleanly")
            # The pause can observe either the terminal frame (one operation)
            # or the first quiescent frame (zero). The cumulative count is the
            # stable exact semantic trace across that emulator timing boundary.
            require(halted["last_opcode"] == 0 and halted["frame_ops"] in (0, 1) and
                    halted["total_ops"] == 9, "terminal operation trace differs")
            require(session.get_state()["frameCount"] <= 12, "gate exceeded twelve frames")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C32 SCUMM putActorAtObject: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C32 SCUMM putActorAtObject: PASS (walk point, fallback, lifecycle)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
