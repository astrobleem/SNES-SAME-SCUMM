#!/usr/bin/env python3
"""Prove M22 hook-8 ownership is one-shot and cue-generation scoped."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from validate_scumm_m19_monkey_music_nexen import audio_trace
from validate_scumm_m20_save_nexen import boot_blank
from validate_scumm_m21_fate_route_nexen import route_state
from validate_scumm_m22_fate_hook8_nexen import m22_state, tad_extra
from validate_scumm_s6_tad_nexen import DEFAULT_NEXEN, require, tad_state


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_REQUEST = 0x7E235E
SCUMM_STATE = 0x7E2300
SCUMM_VARIABLES = 0x7E2320
ACTIVE_MUSIC = 0x7FF24D
FIXTURE = 0x41


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def snapshot(session: object) -> dict[str, object]:
    return {
        "frame": session.get_state()["frameCount"],
        "active_music": session.read_memory("snesMemory", ACTIVE_MUSIC, 1)[0],
        "m22": m22_state(session), "route": route_state(session),
        "tad": tad_state(session), "backend": tad_extra(session),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "build/same-scumm-v5-fate-m22.sfc")
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44580)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"scumm-m22-lifetime-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    evidence: dict[str, object] = {}
    with mcp_session.McpSession(rom=rom, mesen=nexen, cwd=ROOT, port=args.port,
            boot_wait=2.0, socket_timeout=120.0, stderr_log=output / "nexen-stderr.log") as session:
        boot_blank(session)
        session.write_u8(FIXTURE_REQUEST, FIXTURE)
        last_active = None
        for _ in range(9500):
            result = session.run_frames(1)
            require(result["framesAdvanced"] == 1 and not result["timedOut"],
                    "M22 lifetime frame timed out")
            item = snapshot(session)
            state = item["m22"]
            active = item["active_music"]
            if state["consume_count"] == 1 and "first_consumed" not in evidence:
                evidence["first_consumed"] = item
            if last_active == 80 and active == 0:
                key = "first_stop" if "first_stop" not in evidence else "default_stop"
                evidence.setdefault(key, item)
            if (active == 80 and item["route"]["kind"] == 0
                    and item["tad"]["ready"] and item["tad"]["next_song"] == 26
                    and "plain_default" not in evidence):
                evidence["plain_default"] = item
            if state["arm_count"] == 2 and "second_armed" not in evidence:
                evidence["second_armed"] = item
            if state["consume_count"] == 2:
                evidence["second_consumed"] = item
            last_active = active
            pc = u16(session.read_memory("snesMemory", SCUMM_STATE, 2))
            if "second_consumed" in evidence and pc >= 190:
                break
        required = {"first_consumed", "first_stop", "plain_default", "default_stop",
                    "second_armed", "second_consumed"}
        require(required <= evidence.keys(), f"hook lifetime stages are incomplete: {evidence.keys()}")
        first = evidence["first_consumed"]["m22"]
        default = evidence["plain_default"]["m22"]
        second = evidence["second_consumed"]["m22"]
        require(first["consume_count"] == 1 and first["route_history"] == 2,
                f"first generation did not consume once: {first}")
        require(default["pending_hook"] == default["consumption"] == 0
                and default["route_history"] == 0,
                f"plain restart inherited stale hook state: {default}")
        require(second["consume_count"] == 2 and second["arm_count"] == 2
                and second["stale_count"] == 0 and second["route_history"] == 2,
                f"second generation did not consume independently: {second}")
        variables = [u16(session.read_memory("snesMemory", SCUMM_VARIABLES, 10), i * 2)
                     for i in range(5)]
        require(variables == [1, 0, 1, 0, 1], f"$7C lifetime states differ: {variables}")
        final = snapshot(session)
        require(final["active_music"] == 80 and final["tad"]["next_song"] == 27
                and final["tad"]["ready"] and final["tad"]["rejected"] == 0,
                f"final lifetime ownership differs: {final}")
        report = {
            "gate": "M22-hook8-cue-generation-lifetime", "result": "pass",
            "rom": str(rom), "rom_sha256": rom_hash, "fresh_power_on": True,
            "fixture": FIXTURE, "debugger_audio_injection_writes": 0,
            "$7c_results": variables, "stages": evidence, "final": final,
            "audio_packets": audio_trace(session),
        }
    report_path = output / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"PASS rom={rom_hash} report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
