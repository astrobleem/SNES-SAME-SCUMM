#!/usr/bin/env python3
"""Validate C31 canonical SCUMM v5 putActorInRoom semantics in Nexen."""

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
COMMON_ADDRESS = 0x7E2300
VARIABLES = 0x7E2320
ACTOR_RECORDS = 0x7F36C0
ACTOR_STRIDE = 0x40
POSITIONS = 0x7FF1A0
MOVING = 0x7FF220
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 54


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


def actor_snapshot(session: object, actor_id: int) -> dict[str, object]:
    record = session.read_memory(
        "snesMemory", ACTOR_RECORDS + actor_id * ACTOR_STRIDE, ACTOR_STRIDE
    )
    position = session.read_memory("snesMemory", POSITIONS + actor_id * 4, 4)
    moving = session.read_memory("snesMemory", MOVING + actor_id, 1)[0]
    return {
        "room": record[0x16], "visible": bool(record[0x15]),
        "position": [s16(position), s16(position, 2)], "moving": moving,
        "hitbox": [
            s16(record, 0x17), s16(record, 0x19),
            s16(record, 0x1B), s16(record, 0x1D),
        ],
        "present": bool(record[0x1F]),
    }


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON_ADDRESS, 0x64)
    variables = session.read_memory("snesMemory", VARIABLES, 4)
    return {
        "pc": u16(common), "status": common[2], "error": common[3],
        "last_opcode": common[6], "frame_count": u16(common, 8),
        "frame_ops": u16(common, 10), "total_ops": u16(common, 12),
        "fixture_active": common[0x5F], "program_select": common[0x62],
        "variables": [u16(variables), u16(variables, 2)],
        "actors": {
            "1": actor_snapshot(session, 1),
            "2": actor_snapshot(session, 2),
        },
    }


def actor_record(*, room: int, visible: bool, hitbox: tuple[int, int, int, int]) -> bytes:
    record = bytearray(ACTOR_STRIDE)
    record[0x15] = int(visible)
    record[0x16] = room
    for offset, value in zip((0x17, 0x19, 0x1B, 0x1D), hitbox):
        record[offset : offset + 2] = int(value & 0xFFFF).to_bytes(2, "little")
    record[0x1F] = 1
    return bytes(record)


def install_actor_fixture(session: object) -> None:
    actors = {
        1: (actor_record(room=4, visible=True, hitbox=(88, 40, 112, 90)), (100, 90), 3),
        2: (actor_record(room=0, visible=True, hitbox=(188, 30, 212, 80)), (200, 80), 1),
    }
    for actor_id, (record, position, moving) in actors.items():
        session.write_memory(
            "snesMemory", ACTOR_RECORDS + actor_id * ACTOR_STRIDE, record.hex()
        )
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
    output = (args.output or ROOT / f"build/scumm-c31-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C31-put-actor-in-room", "result": "running", "rom": str(rom),
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
            install_actor_fixture(session)
            assigned = snapshot(session)
            for _ in range(6):
                step_video_frame(session)
                assigned = snapshot(session)
                if assigned["pc"] == 5:
                    break
            require(assigned["pc"] == 5 and assigned["status"] == 2 and
                    assigned["error"] == 0 and assigned["frame_ops"] == 2,
                    "direct room assignment checkpoint differs")
            require(assigned["actors"]["1"] == {
                "room": 75, "visible": True, "position": [100, 90], "moving": 3,
                "hitbox": [88, 40, 112, 90], "present": True,
            }, "nonzero room assignment changed actor placement")
            removed = snapshot(session)
            for _ in range(6):
                step_video_frame(session)
                removed = snapshot(session)
                if removed["pc"] == 24:
                    break
            require(removed["pc"] == 24 and removed["status"] == 2 and
                    removed["error"] == 0 and removed["frame_ops"] == 5,
                    "variable assignment/removal checkpoint differs")
            require(removed["variables"] == [2, 331], "fixture variable setup differs")
            require(removed["actors"]["2"] == {
                "room": 75, "visible": True, "position": [200, 80], "moving": 1,
                "hitbox": [188, 30, 212, 80], "present": True,
            }, "variable room assignment or byte truncation differs")
            require(removed["actors"]["1"] == {
                "room": 0, "visible": False, "position": [0, 0], "moving": 0,
                "hitbox": [88, 40, 112, 90], "present": True,
            }, "room-zero actor removal differs")
            halted = snapshot(session)
            for _ in range(4):
                step_video_frame(session)
                halted = snapshot(session)
                if halted["pc"] == 25 and halted["status"] == 4:
                    break
            report["checkpoints"] = [setup, assigned, removed, halted]
            require(halted["pc"] == 25 and halted["status"] == 4 and halted["error"] == 0,
                    "fixture did not halt cleanly")
            require(halted["last_opcode"] == 0 and halted["frame_ops"] == 1 and
                    halted["total_ops"] == 9, "terminal operation trace differs")
            require(session.get_state()["frameCount"] <= 12, "gate exceeded twelve frames")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C31 SCUMM putActorInRoom: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C31 SCUMM putActorInRoom: PASS (direct, variable, room-zero removal)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
