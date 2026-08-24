#!/usr/bin/env python3
"""Validate C26 canonical SCUMM v5 saveRestoreVerbs semantics in Nexen."""

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
SAVED_RECORDS = 0x7FD900
SAVED_STRIDE = 0x62
SAVED_COUNT = 64
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 50


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON_ADDRESS, 0x64)
    initialized = session.read_memory("snesMemory", VERB_INITIALIZED, 1)[0]
    active: dict[str, object] = {}
    if initialized:
        for verb_id in (1, 2):
            raw = session.read_memory(
                "snesMemory", VERB_RECORDS + verb_id * VERB_STRIDE, VERB_STRIDE
            )
            if raw[0]:
                active[str(verb_id)] = {"color": raw[2], "save_id": u16(raw, 0x16)}
    pool = session.read_memory("snesMemory", SAVED_RECORDS, SAVED_STRIDE * SAVED_COUNT)
    saved = []
    for slot in range(SAVED_COUNT if initialized else 0):
        offset = slot * SAVED_STRIDE
        if pool[offset]:
            payload = offset + 2
            saved.append({
                "slot": slot, "verb": pool[offset + 1], "color": pool[payload + 2],
                "save_id": u16(pool, payload + 0x16),
            })
    return {
        "pc": u16(common), "status": common[2], "error": common[3],
        "last_opcode": common[6], "frame_count": u16(common, 8),
        "frame_ops": u16(common, 10), "total_ops": u16(common, 12),
        "fixture_active": common[0x5F], "program_select": common[0x62],
        "verb_state_initialized": bool(initialized),
        "active_verbs": active, "saved_verbs": saved,
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
    output = (args.output or ROOT / f"build/scumm-c26-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C26-save-restore-verbs", "result": "running", "rom": str(rom),
        "rom_sha256": rom_hash, "fresh_power_on": True, "frame_limit": 16,
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
            for checkpoint, expected_pc in enumerate((18, 30, 41, 42)):
                current = snapshot(session)
                for _ in range(12 if checkpoint == 0 else 4):
                    step_video_frame(session)
                    current = snapshot(session)
                    if current["fixture_active"] == FIXTURE_ID and current["pc"] == expected_pc:
                        break
                observed.append(current)
            first, restored, deleted, halted = observed
            report["checkpoints"] = observed
            require(first["status"] == 2 and first["error"] == 0, "save tick failed")
            require(first["last_opcode"] == 0x80 and first["frame_ops"] == 4,
                    "save tick trace differs")
            require(first["active_verbs"] == {}, "saved verbs remained active")
            require(first["saved_verbs"] == [
                {"slot": 0, "verb": 1, "color": 3, "save_id": 5},
                {"slot": 1, "verb": 2, "color": 4, "save_id": 5},
            ], "saved-bank records differ")
            require(restored["status"] == 2 and restored["error"] == 0,
                    "restore tick failed")
            require(restored["last_opcode"] == 0x80 and restored["frame_ops"] == 3,
                    "restore tick trace differs")
            require(restored["active_verbs"] == {"1": {"color": 3, "save_id": 0}},
                    "restore did not replace the active verb")
            require(restored["saved_verbs"] == [
                {"slot": 1, "verb": 2, "color": 4, "save_id": 5}
            ], "restore removed the wrong saved slot")
            require(deleted["status"] == 2 and deleted["error"] == 0,
                    "delete/reversed-range tick failed")
            require(deleted["last_opcode"] == 0x80 and deleted["frame_ops"] == 3,
                    "delete tick trace differs")
            require(deleted["active_verbs"] == restored["active_verbs"] and
                    deleted["saved_verbs"] == [], "delete or reversed range differs")
            require(halted["pc"] == 42 and halted["status"] == 4 and halted["error"] == 0,
                    "fixture did not halt cleanly")
            require(halted["last_opcode"] == 0 and halted["frame_ops"] == 1 and
                    halted["total_ops"] == 11, "terminal operation trace differs")
            require(halted["fixture_active"] == FIXTURE_ID and
                    halted["program_select"] == FIXTURE_ID, "fixture selection differs")
            require(session.get_state()["frameCount"] <= 16, "gate exceeded sixteen frames")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C26 SCUMM saveRestoreVerbs: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C26 SCUMM saveRestoreVerbs: PASS (save bank, replacement restore, delete)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
