#!/usr/bin/env python3
"""Validate C23 canonical SCUMM v5 print semantics in Nexen."""

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
C23_ADDRESS = 0x7FD408
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 47


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def style(raw: bytes, offset: int) -> dict[str, object]:
    flags = raw[offset + 10]
    return {
        "position": [u16(raw, offset), u16(raw, offset + 2)],
        "right": u16(raw, offset + 4), "height": u16(raw, offset + 6),
        "color": raw[offset + 8], "charset": raw[offset + 9],
        "center": bool(flags & 1), "overhead": bool(flags & 2),
    }


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON_ADDRESS, 0x64)
    state = session.read_memory("snesMemory", C23_ADDRESS, 0x51)
    length = state[48]
    return {
        "pc": u16(common), "status": common[2], "error": common[3],
        "last_opcode": common[6], "frame_count": u16(common, 8),
        "frame_ops": u16(common, 10), "total_ops": u16(common, 12),
        "fixture_active": common[0x5F], "program_select": common[0x62],
        "variables": [u16(common, 0x20 + index * 2) for index in range(4)],
        "initialized": state[0],
        "slots": [style(state, 1 + index * 11) for index in range(4)],
        "message_count": state[45], "last_actor": state[46],
        "last_slot": state[47], "last_raw": list(state[49 : 49 + length]),
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
    output = (args.output or ROOT / "build" / f"scumm-c23-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C23-print", "result": "running", "rom": str(rom),
        "rom_sha256": rom_hash, "fresh_power_on": True, "frame_limit": 10,
        "donor_rom_used": False, "screenshots_captured": False, "audio_captured": False,
    }
    expected_slot3 = {
        "position": [70, 20], "right": 319, "height": 0, "color": 31,
        "charset": 0, "center": True, "overhead": True,
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
            for expected_pc in (52, 53):
                current = snapshot(session)
                for _ in range(4):
                    step_video_frame(session)
                    current = snapshot(session)
                    if current["fixture_active"] == FIXTURE_ID and current["pc"] == expected_pc:
                        break
                observed.append(current)
            running, halted = observed
            require(running["status"] == 2 and running["error"] == 0, "print fixture did not run cleanly")
            require(running["last_opcode"] == 0x80 and running["frame_ops"] == 8, "print execution trace differs")
            require(running["variables"] == [253, 70, 20, 31], "variable operands differ")
            require(running["initialized"] == 1, "print state was not initialized")
            require(running["slots"][3] == expected_slot3, "slot-3 saved defaults differ")
            require(running["slots"][2]["position"] == [2, 5], "text emission mutated slot-2 defaults")
            require(running["message_count"] == 2, "print message count differs")
            require((running["last_actor"], running["last_slot"]) == (1, 0), "printEgo routing differs")
            require(running["last_raw"] == [ord("F"), 0xFF, 0x03, 0], "encoded text differs")
            require(halted["status"] == 4 and halted["error"] == 0, "fixture did not halt cleanly")
            require(halted["total_ops"] == 9, "total operation count differs")
            report["checkpoints"] = observed
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C23 SCUMM print: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C23 SCUMM print: PASS (slots, defaults, variable operands, printEgo, encoded text)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
