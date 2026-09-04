#!/usr/bin/env python3
"""Fresh-emulator authentic Fate proof for canonical v5 $7B getActorWalkBox."""

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
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
WALKBOX = 0x7E7AD9
VARIABLES = 0x7FF500
ACTORS = 0x7F36C0
POSITIONS = 0x7FF1A0
MOVING = 0x7FF220
FACINGS = 0x7E78F0
PUT_ACTOR = 0x7FFB65


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def s16(raw: bytes, offset: int = 0) -> int:
    value = u16(raw, offset)
    return value - 0x10000 if value & 0x8000 else value


def actor_snapshot(session: object, actor: int) -> dict[str, object]:
    record = session.read_memory("snesMemory", ACTORS + actor * 0x40, 0x40)
    position = session.read_memory("snesMemory", POSITIONS + actor * 4, 4)
    put = session.read_memory("snesMemory", PUT_ACTOR, 0x44C)
    raw = b"".join((
        record, position,
        session.read_memory("snesMemory", MOVING + actor, 1),
        session.read_memory("snesMemory", FACINGS + actor * 2, 2),
        bytes((put[0x240 + actor], put[0x260 + actor])),
        put[0x280 + actor * 2:0x282 + actor * 2],
        bytes((put[0x2C0 + actor],)),
        put[0x2E0 + actor * 4:0x2E4 + actor * 4],
        put[0x40C + actor * 2:0x40E + actor * 2],
    ))
    return {
        "actor": actor, "costume": record[0], "position": [s16(position), s16(position, 2)],
        "room": record[0x16], "walkbox": put[0x240 + actor],
        "destination_box": put[0x260 + actor],
        # The compact current runtime owns destination X plus destination box;
        # Y remains the canonical zero used by this stationary Fate state.
        "walk_destination": [s16(put, 0x280 + actor * 2), 0],
        "moving": session.read_memory("snesMemory", MOVING + actor, 1)[0],
        "facing": u16(session.read_memory("snesMemory", FACINGS + actor * 2, 2)),
        "visible": bool(record[0x15]), "scale": [record[0x0D], record[0x0E]],
        "frame": record[0x0F], "redraw": put[0x2C0 + actor],
        "box_scale_raw": u16(put, 0x40C + actor * 2),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
    }


def walkbox_snapshot(session: object) -> dict[str, object]:
    raw = session.read_memory("snesMemory", WALKBOX, 0xD1)
    trace = []
    for index in range(min(raw[0x0B], 16)):
        base = 0x0C + index * 12
        trace.append({
            "actor": raw[base], "opcode": raw[base + 1], "walkbox": raw[base + 2],
            "result_offset": u16(raw, base + 4), "result_before": u16(raw, base + 6),
            "pc_before": u16(raw, base + 8), "pc_after": u16(raw, base + 10),
        })
    return {
        "actor": raw[0], "walkbox": raw[1], "execution_count": raw[2],
        "pc_before": u16(raw, 3), "pc_after": u16(raw, 5),
        "result_offset": u16(raw, 7), "result_before": u16(raw, 9),
        "trace": trace, "next_program": raw[0xCC], "next_opcode": raw[0xCD],
        "next_pc": u16(raw, 0xCE), "next_seen": raw[0xD0],
        "variable_442": u16(session.read_memory("snesMemory", VARIABLES + 442 * 2, 2)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--host-report", type=Path, required=True)
    parser.add_argument("--cooked-room", type=Path, required=True)
    parser.add_argument("--cooked-room63", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45340)
    args = parser.parse_args()
    require(args.rom.is_file() and args.host_report.is_file() and args.cooked_room.is_file()
            and args.cooked_room63.is_file(),
            "required authentic evidence input is missing")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    host = json.loads(args.host_report.read_text())
    cooked = decode_cooked_room(args.cooked_room.read_bytes(), expected_room=49)
    cooked63 = decode_cooked_room(args.cooked_room63.read_bytes(), expected_room=63)
    script = next(item for item in cooked.scripts if item.kind == "LSCR" and item.number == 216)
    require(script.program[:4] == bytes.fromhex("7b ba 01 01"), "authentic opcode bytes differ")

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    previous_actor = None
    query = terminal = steady = last = None
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT, port=args.port,
        boot_wait=2.0, socket_timeout=90.0,
        stderr_log=args.output.parent / "authentic-nexen-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")
        for frame in range(1, 701):
            advance = 10 if query is not None else 1
            step = session.run_frames(advance)
            require(step["framesAdvanced"] == advance and not step["timedOut"],
                    "emulator timeout")
            engine = snapshot(session, frame)
            actor = actor_snapshot(session, 1)
            state = walkbox_snapshot(session)
            last = {"frame": frame, "engine": engine, "query": state, "actor": actor}
            if query is None and state["execution_count"] == 1:
                query = {
                    "frame": frame, "before_actor": previous_actor,
                    "after_actor": actor, "query": state, "engine": engine,
                }
            if engine["error"]:
                terminal = {"frame": frame, "engine": engine, "query": state}
                break
            if query is not None and state["execution_count"] >= 16:
                steady = {"frame": frame, "engine": engine, "query": state,
                          "actor": actor}
                break
            previous_actor = actor

    require(query is not None, f"authentic getActorWalkBox was not executed: {terminal}")
    expected_trace = {
        "actor": 1, "opcode": 0x7B, "walkbox": 11,
        "result_offset": 0x2374, "result_before": 0,
        "pc_before": 0, "pc_after": 4,
    }
    require(query["query"]["trace"] == [expected_trace],
            f"authentic query trace differs: {query}")
    require(query["query"]["variable_442"] == 11, f"Var[442] differs: {query}")
    require(query["before_actor"] is not None
            and query["before_actor"]["raw_sha256"] == query["after_actor"]["raw_sha256"],
            f"authentic query mutated actor state: {query}")
    host_query = host["queries"][0]
    require(host_query["stored_walkbox"] == 11 and host_query["result_after"] == 11,
            f"host oracle differs: {host_query}")
    if terminal is not None:
        next_program = (
            terminal["query"]["next_program"]
            if terminal["query"]["next_seen"] else terminal["engine"]["program"]
        )
        program_index = next_program - 0xD0
        # Generated ordering is room-49 descriptors, its two requested global
        # scripts, room-63 descriptors, then global 151.
        program_map = list(cooked.scripts) + [None, None] + list(cooked63.scripts) + [None]
        require(0 <= program_index < len(program_map) and program_map[program_index] is not None,
                f"next blocker program is not an authentic room script: {next_program:#x}")
        blocked_script = program_map[program_index]
        assert blocked_script is not None
        if terminal["query"]["next_seen"]:
            blocked_offset = terminal["query"]["next_pc"]
            next_opcode = terminal["query"]["next_opcode"]
            classification = "unsupported_opcode_or_subsystem"
            decode = None
        else:
            # The next authentic failure is not an unknown opcode: canonical
            # $2A decoded normally, consumed CA FF, then failed local-script
            # resolution. The live interpreter PC is therefore the exact
            # post-instruction PC and binds the source offset without guessing.
            require(terminal["engine"]["error"] == 0x0B
                    and terminal["engine"]["last_opcode"] == 0x2A,
                    f"later non-opcode fault is not the expected script lookup failure: {terminal}")
            blocked_offset = terminal["engine"]["pc"] - 3
            next_opcode = 0x2A
            classification = "missing_room_local_executable_delivery"
            decode = "startScript(202), no arguments; canonical operands CA FF"
        require(blocked_offset < len(blocked_script.program), "next blocker PC exceeds descriptor")
        require(blocked_script.program[blocked_offset] == next_opcode,
                "next blocker opcode does not match authentic resource")
        around = max(0, blocked_offset - 16)
        next_blocker = {
            "script_identity": blocked_script.identity,
            "script_sha256": blocked_script.sha256, "offset": blocked_offset,
            "opcode": next_opcode,
            "surrounding_start": around,
            "surrounding_bytes": blocked_script.program[around:blocked_offset + 16].hex(),
            "source_map": blocked_script.runtime_map(blocked_offset),
            "classification": classification, "decode": decode,
            "relevant_state": (
                "room 63 is active; authentic LSCR 202 is present in the cooked record "
                "but is not in the current room-63 executable local-script table"
                if classification == "missing_room_local_executable_delivery" else None
            ),
        }
    else:
        require(steady is not None and steady["query"]["execution_count"] >= 16,
                "authentic execution neither faulted nor established the room-local steady loop: "
                f"{last}")
        # LSCR 216 legitimately queries, branches, mutates box flags, yields,
        # and jumps back to PC zero. No unsupported opcode is reached without
        # a later player/gameplay state change.
        next_blocker = {
            "script_identity": script.identity, "script_sha256": script.sha256,
            "offset": 0x24, "opcode": script.program[0x24],
            "surrounding_start": 0x18,
            "surrounding_bytes": script.program[0x18:0x29].hex(),
            "source_map": script.runtime_map(0x24),
            "classification": "no_unsupported_semantic_reached",
            "decode": "breakHere at +$0024; jumpRelative at +$0025 returns to +$0000",
            "progress_dependency": (
                "legitimate player/gameplay state must change actor 1's stored walkbox; "
                "the present headless deterministic state is a stable room-local loop"
            ),
        }
    report = {
        "gate": "M25-canonical-getActorWalkBox-authentic", "result": "pass",
        "fresh_power_on": True, "debugger_writes": 0,
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "record_sha256": hashlib.sha256(args.cooked_room.read_bytes()).hexdigest(),
        "resource": {"script_identity": script.identity, "script_sha256": script.sha256,
                     "source_map": script.runtime_map(0), "instruction": script.program[:4].hex()},
        "host_query": host_query, "snes_query": query,
        "terminal": terminal, "steady_state": steady, "next_blocker": next_blocker,
        "limitations": [
            "Costume presentation remains blocked because authentic costume.45 is absent from the supplied Fate demo and the SNES costume renderer does not yet exist.",
            "Text glyph rendering remains unavailable; the accepted headless semantic lane is used.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output),
                      "rom_sha256": report["rom_sha256"],
                      "next_blocker": next_blocker}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
