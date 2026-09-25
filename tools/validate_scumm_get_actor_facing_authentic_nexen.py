#!/usr/bin/env python3
"""Fresh-emulator authentic Fate proof for canonical v5 $63 getActorFacing."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from same.engines.scumm_v5.cooked_room import decode_cooked_room
from validate_scumm_m25_authentic_next_nexen import snapshot

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
FACING_STATE = 0x7E78F0
VARIABLE_ZERO = 0x7FF500


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def facing_snapshot(session: object) -> dict[str, object]:
    raw = session.read_memory("snesMemory", FACING_STATE, 0x130)
    trace = []
    for index in range(min(raw[0x4C], 16)):
        base = 0x50 + index * 14
        trace.append({
            "actor": raw[base], "opcode": raw[base + 1], "result": raw[base + 2],
            "raw_facing": u16(raw, base + 4), "result_offset": u16(raw, base + 6),
            "result_before": u16(raw, base + 8),
            "pc_before": u16(raw, base + 10), "pc_after": u16(raw, base + 12),
        })
    return {
        "actor_facings": [u16(raw, index * 2) for index in range(32)],
        "actor": raw[0x40], "raw_facing": u16(raw, 0x42), "result": raw[0x44],
        "execution_count": raw[0x45], "pc_before": u16(raw, 0x46),
        "pc_after": u16(raw, 0x48), "result_offset": u16(raw, 0x4A),
        "stage": raw[0x4D],
        "result_before": u16(raw, 0x4E), "trace": trace,
        "variable_zero": u16(session.read_memory("snesMemory", VARIABLE_ZERO, 2)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--host-report", type=Path, required=True)
    parser.add_argument("--cooked-room", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44940)
    args = parser.parse_args()
    require(args.rom.is_file() and args.host_report.is_file() and args.cooked_room.is_file(),
            "required authentic evidence input is missing")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    host = json.loads(args.host_report.read_text())
    cooked = decode_cooked_room(args.cooked_room.read_bytes(), expected_room=49)
    script = next(item for item in cooked.scripts if item.kind == "LSCR" and item.number == 201)
    require(script.program[:4] == bytes.fromhex("63 00 00 0a"), "authentic opcode bytes differ")

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    first_query = None
    terminal = None
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT, port=args.port,
        boot_wait=2.0, socket_timeout=90.0,
        stderr_log=args.output.parent / "nexen-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")
        for frame in range(1, 601):
            step = session.run_frames(1)
            require(step["framesAdvanced"] == 1 and not step["timedOut"], "emulator timeout")
            engine = snapshot(session, frame)
            facing = facing_snapshot(session)
            if (
                first_query is None and facing["trace"]
                and facing["trace"][0].get("actor") == 10
                and facing["trace"][0].get("opcode") == 0x63
                and facing["trace"][0].get("pc_before") == 0
                and engine["active_room"] == 49
            ):
                first_query = {"frame": frame, **facing, "engine": engine}
            if engine["error"]:
                terminal = {"frame": frame, "engine": engine, "facing": facing}
                break
    require(first_query is not None, f"authentic getActorFacing was not executed: {terminal}")
    expected = {
        "actor": 10, "opcode": 0x63, "result": 1, "raw_facing": 90,
        "result_offset": 0, "result_before": 0, "pc_before": 0, "pc_after": 4,
    }
    require(first_query["trace"][0] == expected,
            f"authentic first getActorFacing trace differs: {first_query}")
    require(len(first_query["trace"]) >= 2
            and first_query["trace"][1]["result_before"] == 1,
            f"authentic Var[0] write was not observed by the next query: {first_query}")
    require(first_query["engine"]["active_room"] == 49
            and first_query["engine"]["active_music"] == 80
            and first_query["engine"]["route_kind"] == 1
            and first_query["engine"]["route_value"] == 14,
            f"authentic room/music ownership differs: {first_query['engine']}")
    require(terminal is not None, "SNES did not reach a later fail-closed boundary")
    report = {
        "gate": "M25-canonical-getActorFacing-authentic", "result": "pass",
        "fresh_power_on": True, "debugger_writes": 0,
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "record_sha256": hashlib.sha256(args.cooked_room.read_bytes()).hexdigest(),
        "script_identity": script.identity, "script_sha256": script.sha256,
        "source_map": script.runtime_map(0), "instruction": script.program[:4].hex(),
        "host_query": host["queries"][0], "first_query": first_query,
        "host_next_blocker": host["next_blocker"], "snes_terminal": terminal,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
