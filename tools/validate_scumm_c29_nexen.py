#!/usr/bin/env python3
"""Validate C29 canonical SCUMM v5 getActorFromPos semantics in Nexen."""

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
CLASS_RECORDS = 0x7F5F10
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 52


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON_ADDRESS, 0x64)
    variables = session.read_memory("snesMemory", VARIABLES, 10)
    return {
        "pc": u16(common), "status": common[2], "error": common[3],
        "last_opcode": common[6], "frame_count": u16(common, 8),
        "frame_ops": u16(common, 10), "total_ops": u16(common, 12),
        "fixture_active": common[0x5F], "program_select": common[0x62],
        "variables": [u16(variables, index * 2) for index in range(5)],
    }


def actor_record(*, room: int, visible: bool, hitbox: tuple[int, int, int, int]) -> bytes:
    record = bytearray(ACTOR_STRIDE)
    record[0x15] = int(visible)
    record[0x16] = room
    for offset, value in zip((0x17, 0x19, 0x1B, 0x1D), hitbox):
        record[offset : offset + 2] = int(value & 0xFFFF).to_bytes(2, "little")
    record[0x1F] = 1
    return bytes(record)


def install_spatial_fixture(session: object) -> None:
    actors = {
        1: actor_record(room=0, visible=True, hitbox=(10, 10, 30, 40)),
        2: actor_record(room=0, visible=True, hitbox=(10, 10, 30, 40)),
        3: actor_record(room=0, visible=True, hitbox=(40, 50, 70, 80)),
        4: actor_record(room=1, visible=True, hitbox=(10, 10, 30, 40)),
        5: actor_record(room=0, visible=False, hitbox=(10, 10, 30, 40)),
    }
    for actor_id, record in actors.items():
        session.write_memory(
            "snesMemory", ACTOR_RECORDS + actor_id * ACTOR_STRIDE, record.hex()
        )
    class_record = bytearray(8)
    class_record[0] = 1
    class_record[2:4] = (1).to_bytes(2, "little")
    class_record[7] = 0x80
    session.write_memory("snesMemory", CLASS_RECORDS, class_record.hex())


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
    output = (args.output or ROOT / f"build/scumm-c29-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C29-actor-from-pos", "result": "running", "rom": str(rom),
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
            first = snapshot(session)
            for _ in range(10):
                step_video_frame(session)
                first = snapshot(session)
                if first["fixture_active"] == FIXTURE_ID and first["pc"] == 1:
                    break
            require(first["status"] == 2 and first["error"] == 0 and
                    first["last_opcode"] == 0x80 and first["frame_ops"] == 1,
                    "fixture setup yield differs")
            install_spatial_fixture(session)
            queried = snapshot(session)
            for _ in range(8):
                step_video_frame(session)
                queried = snapshot(session)
                if queried["pc"] == 33:
                    break
            halted = snapshot(session)
            for _ in range(4):
                step_video_frame(session)
                halted = snapshot(session)
                if halted["pc"] == 34 and halted["status"] == 4:
                    break
            report["checkpoints"] = [first, queried, halted]
            require(queried["pc"] == 33 and queried["status"] == 2 and queried["error"] == 0,
                    "query tick failed")
            require(queried["last_opcode"] == 0x80 and queried["frame_ops"] == 6,
                    "query operation trace differs")
            require(queried["variables"] == [2, 3, 50, 60, 0],
                    "ordered, variable, or no-match query result differs")
            require(halted["pc"] == 34 and halted["status"] == 4 and halted["error"] == 0,
                    "fixture did not halt cleanly")
            require(halted["last_opcode"] == 0 and halted["frame_ops"] == 1 and
                    halted["total_ops"] == 8, "terminal operation trace differs")
            require(halted["fixture_active"] == FIXTURE_ID and
                    halted["program_select"] == FIXTURE_ID, "fixture selection differs")
            require(session.get_state()["frameCount"] <= 12, "gate exceeded twelve frames")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C29 SCUMM getActorFromPos: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C29 SCUMM getActorFromPos: PASS (ordering, class 32, variable, no match)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
