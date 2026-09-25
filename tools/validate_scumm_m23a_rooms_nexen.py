#!/usr/bin/env python3
"""Validate M23A authentic registration and copyright-free room lifecycle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
FIXTURE_REQUEST = 0x7E235E
COMMON = 0x7E2300
VARIABLES = 0x7E2320
M23A = 0x7FF2BE
AUDIO_TRACE_COUNT = 0x7E2B30
ACTIVE_MUSIC = 0x7FF24D
EVENT_STAGING = 0x7E2140
FIXTURES = {"room49": 0x42, "room63": 0x43, "lifecycle": 0x44}


class GateFailure(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise GateFailure(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def step(session: object) -> None:
    for _ in range(20):
        result = session.run_frames(1)
        if result["framesAdvanced"] == 1:
            return
    raise GateFailure(f"frame step made no progress: {result}")


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON, 0x64)
    state = session.read_memory("snesMemory", M23A, 66)
    variables = session.read_memory("snesMemory", VARIABLES, 32)
    staging = session.read_memory("snesMemory", EVENT_STAGING, 16)
    count = min(state[24], 14)
    return {
        "pc": u16(common), "status": common[2], "error": common[3],
        "last_opcode": common[6], "fixture": common[0x5F],
        "program": common[0x62],
        "active_record": state[0], "active_room": state[1],
        "pending_record": state[2], "pending_room": state[3],
        "phase": state[4], "hold": state[6], "requests": state[7],
        "validations": state[8], "registrations": state[9],
        "retirements": state[10], "entries": state[11], "exits": state[12],
        "descriptor_count": state[13], "local_count": state[14],
        "entry_program": state[15], "exit_program": state[16],
        "current_kind": state[17], "compact_checksum": u16(state, 18),
        "storage_packet": u16(state, 20), "descriptor_checksum": u16(state, 22),
        "lifecycle": list(state[25:25 + count]),
        "return_pc": u16(state, 39), "slot_rooms": list(state[41:66]),
        "variables": [u16(variables, index * 2) for index in range(16)],
        "audio_trace_count": session.read_memory("snesMemory", AUDIO_TRACE_COUNT, 1)[0],
        "active_music": session.read_memory("snesMemory", ACTIVE_MUSIC, 1)[0],
        "last_staging_packet": {"service": staging[1], "opcode": staging[2],
                                "source": staging[4], "destination": staging[5],
                                "arg0": u16(staging, 8)},
    }


def run_case(rom: Path, nexen: Path, output: Path, port: int,
             case: str) -> dict[str, object]:
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    case_dir = output / case
    case_dir.mkdir(parents=True, exist_ok=True)
    evidence: dict[str, object] = {"case": case, "fresh_power_on": True, "timeline": []}
    with mcp_session.McpSession(
        rom=rom, mesen=nexen, cwd=ROOT, port=port, boot_wait=2.0,
        socket_timeout=30.0, stderr_log=case_dir / "nexen-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")
        step(session)
        base_semantic_frame = u16(session.read_memory("snesMemory", COMMON, 10), 8)
        if case == "lifecycle":
            session.write_u8(0x7E2364, (base_semantic_frame + 1) & 0xFF)
        session.write_u8(FIXTURE_REQUEST, FIXTURES[case])
        if case in {"room49", "room63"}:
            expected = (49, 0, 20, 18, 0xD1, 0xD0, 0x6D4A) if case == "room49" else (
                63, 1, 5, 3, 0xE5, 0xE4, 0x0A02)
            for _ in range(600):
                step(session)
                state = snapshot(session)
                if not evidence["timeline"] or state["phase"] != evidence["timeline"][-1]["phase"]:
                    evidence["timeline"].append(state)
                if state["hold"]:
                    break
            room, record, descriptors, locals_, entry, exit_, descriptor_sum = expected
            require(state["active_room"] == room and state["active_record"] == record,
                    f"authentic room identity was not committed: {state}")
            require(state["phase"] == 3 and state["hold"] == 1 and state["pc"] == 0,
                    "registration-only barrier did not stop before dispatch")
            require(state["descriptor_count"] == descriptors and state["local_count"] == locals_,
                    f"discovered authentic script counts differ: {state}")
            require((state["entry_program"], state["exit_program"], state["descriptor_checksum"]) ==
                    (entry, exit_, descriptor_sum), "generated script registry differs")
            require(state["requests"] == 1 and state["validations"] == 1,
                    "normal resource request/validation counts differ")
            require(state["lifecycle"] == [1, 2, 4, 5, 6, 7, 8],
                    f"authentic registration lifecycle differs: {state['lifecycle']}")
            require(state["audio_trace_count"] == 0 and state["active_music"] == 0,
                    "authentic registration emitted an audio command")
            require(state["storage_packet"] == 0x0104 and state["pending_room"] == room,
                    f"resource did not travel through SAME Storage READ: {state}")
            evidence["final"] = state
        else:
            # The debugger-owned frame hold exposes each committed semantic
            # frame even when several engine frames fit in one video frame.
            for _ in range(120):
                step(session)
                state = snapshot(session)
                if state["phase"] == 5 and state["pending_room"] == 1:
                    break
            session.write_u8(0x7E2364, (base_semantic_frame + 2) & 0xFF)
            for _ in range(120):
                step(session)
                first = snapshot(session)
                if first["active_room"] == 1 and first["last_opcode"] == 0x80:
                    break
            require(first["active_room"] == 1 and first["last_opcode"] == 0x80,
                    f"room-1 lifecycle did not reach driver yield: {first}")
            require(first["variables"][10:12] == [1, 1], "room-1 ENCD/local execution differs")
            require(first["lifecycle"] == [1, 2, 4, 5, 6, 7, 8, 9, 10],
                    f"room-1 lifecycle ordering differs: {first['lifecycle']}")
            require(1 in first["slot_rooms"], "room-1 local script lacks room ownership")
            # Clear only the bounded evidence buffer between the two semantic
            # phases; this does not alter room, scheduler, or script state.
            session.write_u8(M23A + 24, 0)
            session.write_memory("snesMemory", M23A + 25, (b"\x00" * 14).hex())
            session.write_u8(0x7E2364, (base_semantic_frame + 3) & 0xFF)
            for _ in range(120):
                step(session)
                state = snapshot(session)
                if state["phase"] == 5 and state["pending_room"] == 2:
                    break
            session.write_u8(0x7E2364, (base_semantic_frame + 4) & 0xFF)
            for _ in range(120):
                step(session)
                second = snapshot(session)
                if second["active_room"] == 2 and second["last_opcode"] == 0x80:
                    break
            require(second["active_room"] == 2 and second["last_opcode"] == 0x80,
                    f"room-2 lifecycle did not reach driver yield: {second}")
            require(second["variables"][12:14] == [1, 1], "EXCD or new ENCD execution differs")
            require(second["lifecycle"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                    f"room transition ordering differs: {second['lifecycle']}")
            require(second["retirements"] == 1 and 1 not in second["slot_rooms"],
                    "old room-local script was not retired exactly once")
            require(second["error"] == 0 and second["audio_trace_count"] == 0,
                    "generic lifecycle failed or emitted audio")
            evidence["room1"] = first
            evidence["room2"] = second
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "build/same-scumm-v5-fate-m23a.sfc")
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44023)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--case", choices=tuple(FIXTURES))
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / f"build/scumm-m23a-rooms-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {"gate": "M23A-authentic-rooms-and-lifecycle", "result": "running",
              "rom": str(rom), "rom_sha256": rom_hash, "cases": []}
    path = output / "report.json"
    try:
        cases = (args.case,) if args.case else ("room49", "room63", "lifecycle")
        for index, case in enumerate(cases):
            report["cases"].append(run_case(rom, nexen, output, args.port + index, case))
        report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        path.write_text(json.dumps(report, indent=2) + "\n")
        print(f"M23A: FAIL: {exc}", file=sys.stderr)
        print(path)
        return 1
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("M23A: PASS (authentic registration + generic room lifecycle)")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
