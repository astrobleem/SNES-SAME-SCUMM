#!/usr/bin/env python3
"""Validate C28 canonical SCUMM v5 animateActor semantics in Nexen."""

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
ACTOR_RECORDS = 0x7F36C0
ACTOR_STRIDE = 0x40
ACTOR_ANIMATION = 0x14
ACTOR_PRESENT = 0x1F
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 51


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON_ADDRESS, 0x64)
    actor = session.read_memory(
        "snesMemory", ACTOR_RECORDS + 10 * ACTOR_STRIDE, ACTOR_STRIDE
    )
    return {
        "pc": u16(common), "status": common[2], "error": common[3],
        "last_opcode": common[6], "frame_count": u16(common, 8),
        "frame_ops": u16(common, 10), "total_ops": u16(common, 12),
        "fixture_active": common[0x5F], "program_select": common[0x62],
        "actor_10": {
            "present": bool(actor[ACTOR_PRESENT]),
            "animation": actor[ACTOR_ANIMATION],
        },
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
    parser.add_argument("--port", type=int, default=44004)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / f"build/scumm-c28-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C28-animate-actor", "result": "running", "rom": str(rom),
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
            observed = []
            for checkpoint, expected_pc in enumerate((4, 20, 21)):
                current = snapshot(session)
                for _ in range(10 if checkpoint == 0 else 4):
                    step_video_frame(session)
                    current = snapshot(session)
                    if current["fixture_active"] == FIXTURE_ID and current["pc"] == expected_pc:
                        break
                observed.append(current)
            direct, variable, halted = observed
            report["checkpoints"] = observed
            require(direct["status"] == 2 and direct["error"] == 0, "direct tick failed")
            require(direct["last_opcode"] == 0x80 and direct["frame_ops"] == 2,
                    "direct tick trace differs")
            require(direct["actor_10"] == {"present": True, "animation": 250},
                    "direct animation request differs")
            require(variable["status"] == 2 and variable["error"] == 0,
                    "variable tick failed")
            require(variable["last_opcode"] == 0x80 and variable["frame_ops"] == 4,
                    "variable tick trace differs")
            require(variable["actor_10"] == {"present": True, "animation": 6},
                    "variable animation request differs")
            require(halted["pc"] == 21 and halted["status"] == 4 and halted["error"] == 0,
                    "fixture did not halt cleanly")
            require(halted["last_opcode"] == 0 and halted["frame_ops"] == 1 and
                    halted["total_ops"] == 7, "terminal operation trace differs")
            require(halted["fixture_active"] == FIXTURE_ID and
                    halted["program_select"] == FIXTURE_ID, "fixture selection differs")
            require(session.get_state()["frameCount"] <= 12, "gate exceeded twelve frames")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C28 SCUMM animateActor: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C28 SCUMM animateActor: PASS (direct and variable actor/animation)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
