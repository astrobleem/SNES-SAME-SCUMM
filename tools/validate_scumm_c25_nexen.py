#!/usr/bin/env python3
"""Validate C25 canonical SCUMM v5 soundKludge queue/flush semantics."""

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
C25_ADDRESS = 0x7FD459
AUDIO_TRACE_ADDRESS = 0x7E2B30
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 49


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON_ADDRESS, 0x64)
    sound = session.read_memory("snesMemory", C25_ADDRESS, 0x453)
    trace = session.read_memory("snesMemory", AUDIO_TRACE_ADDRESS, 0x3A)
    count = min(trace[0], 8)
    packets = [
        {
            "opcode": trace[1 + index],
            "source": trace[9 + index],
            "destination": trace[17 + index],
            "arg0": u16(trace, 0x1A + index * 2),
            "arg1": u16(trace, 0x2A + index * 2),
        }
        for index in range(count)
    ]
    return {
        "pc": u16(common), "status": common[2], "error": common[3],
        "last_opcode": common[6], "frame_count": u16(common, 8),
        "frame_ops": u16(common, 10), "total_ops": u16(common, 12),
        "fixture_active": common[0x5F], "program_select": common[0x62],
        "queue_count": sound[0], "first_count": sound[1],
        "first_words": [u16(sound, 2 + index * 2) for index in range(min(sound[1], 32))],
        "last_count": sound[0x411],
        "last_words": [u16(sound, 0x412 + index * 2) for index in range(min(sound[0x411], 32))],
        "flush_count": sound[0x452], "audio_packets": packets,
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
    parser.add_argument("--port", type=int, default=44003)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"scumm-c25-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C25-sound-kludge", "result": "running", "rom": str(rom),
        "rom_sha256": rom_hash, "fresh_power_on": True, "frame_limit": 10,
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
            observed = []
            for expected_pc in (6, 12, 13):
                current = snapshot(session)
                for _ in range(4):
                    step_video_frame(session)
                    current = snapshot(session)
                    if current["fixture_active"] == FIXTURE_ID and current["pc"] == expected_pc:
                        break
                observed.append(current)
            queued, flushed, halted = observed
            report["checkpoints"] = observed
            require(queued["status"] == 2 and queued["error"] == 0, "queue tick failed")
            require(queued["last_opcode"] == 0x80 and queued["frame_ops"] == 2, "queue trace differs")
            require(queued["queue_count"] == 1 and queued["first_count"] == 1,
                    "command 11 was not retained")
            require(queued["first_words"] == [11] and queued["audio_packets"] == [],
                    "queued command executed before flush")
            require(flushed["status"] == 2 and flushed["error"] == 0, "flush tick failed")
            require(flushed["last_opcode"] == 0x80 and flushed["frame_ops"] == 2,
                    "flush trace differs")
            require(flushed["queue_count"] == 0 and flushed["last_count"] == 1,
                    "flush did not drain and record the command")
            require(flushed["last_words"] == [11] and flushed["flush_count"] == 1,
                    "flush history differs")
            require(flushed["audio_packets"] == [
                {"opcode": 1, "source": 6, "destination": 4, "arg0": 0, "arg1": 0},
                {"opcode": 3, "source": 6, "destination": 4, "arg0": 0xFFFF, "arg1": 0},
                {"opcode": 10, "source": 6, "destination": 4, "arg0": 0, "arg1": 0},
                {"opcode": 8, "source": 6, "destination": 4, "arg0": 0, "arg1": 0},
            ], "normalized stop-all/flush packets differ")
            require(halted["pc"] == 13 and halted["status"] == 4 and halted["error"] == 0,
                    "fixture did not halt cleanly")
            require(halted["last_opcode"] == 0 and halted["frame_ops"] == 1,
                    "halt trace differs")
            require(halted["total_ops"] == 5, "total operation count differs")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C25 SCUMM soundKludge: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C25 SCUMM soundKludge: PASS (queue persistence, command 11, flush packets)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
