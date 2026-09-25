#!/usr/bin/env python3
"""Fresh-emulator proof for the first post-M25A authentic Fate blocker."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from same.engines.scumm_v5.cooked_room import decode_cooked_room


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/"
    "linux-x64/publish/Nexen"
)
COMMON = 0x7E2300
SLOT_STATUS = 0x7E2380
SLOT_NUMBER = 0x7E2399
SLOT_PROGRAM = 0x7E23B2
SLOT_PC = 0x7E23E4
CURRENT_SLOT = 0x7E2A88
ACTIVE_MUSIC = 0x7FF24D
ROUTE_KIND = 0x7FF25A
ROUTE_VALUE = 0x7FF25B
ACTIVE_RECORD = 0x7FF2BE
ACTIVE_ROOM = 0x7FF2BF
ROOM_PHASE = 0x7FF2C2
VALIDATION_COUNT = 0x7FF2C6
ENTRY_COUNT = 0x7FF2C9
NEST_DEPTH = 0x7FF465
MATRIX_STATE = 0x7FFA40
ACTORS = 0x7F36C0
POSITIONS = 0x7FF1A0
MOVING = 0x7FF220
PUT_ACTOR = 0x7FFB65
SETSTATE = 0x7E5FF0


class GateFailure(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise GateFailure(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def snapshot(session: object, frame: int) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON, 0x64)
    status = session.read_memory("snesMemory", SLOT_STATUS, 25)
    numbers = session.read_memory("snesMemory", SLOT_NUMBER, 25)
    programs = session.read_memory("snesMemory", SLOT_PROGRAM, 25)
    pcs = session.read_memory("snesMemory", SLOT_PC, 50)
    matrix = session.read_memory("snesMemory", MATRIX_STATE, 0x125)
    actor_record = session.read_memory("snesMemory", ACTORS + 10 * 0x40, 0x20)
    position = session.read_memory("snesMemory", POSITIONS + 10 * 4, 4)
    put_actor = session.read_memory("snesMemory", PUT_ACTOR, 0x44C)
    setstate = session.read_memory("snesMemory", SETSTATE, 0x18B1)
    matrix_trace = []
    for index in range(min(matrix[0x104], 4)):
        base = 0x105 + index * 8
        matrix_trace.append({
            "subopcode": matrix[base], "box": matrix[base + 1],
            "flags": matrix[base + 2], "pc_before": u16(matrix, base + 3),
            "pc_after": u16(matrix, base + 5),
        })
    slots = [{
        "slot": index, "status": status[index], "number": numbers[index],
        "program": programs[index], "pc": u16(pcs, index * 2),
    } for index in range(25) if status[index] or numbers[index] or programs[index]]
    return {
        "frame": frame, "pc": u16(common), "status": common[2],
        "error": common[3], "last_opcode": common[6],
        "program": common[0x62], "return_mode": common[0x63],
        "current_slot": session.read_memory("snesMemory", CURRENT_SLOT, 1)[0],
        "nest_depth": session.read_memory("snesMemory", NEST_DEPTH, 1)[0],
        "active_record": session.read_memory("snesMemory", ACTIVE_RECORD, 1)[0],
        "active_room": session.read_memory("snesMemory", ACTIVE_ROOM, 1)[0],
        "room_phase": session.read_memory("snesMemory", ROOM_PHASE, 1)[0],
        "validation_count": session.read_memory("snesMemory", VALIDATION_COUNT, 1)[0],
        "entry_count": session.read_memory("snesMemory", ENTRY_COUNT, 1)[0],
        "active_music": session.read_memory("snesMemory", ACTIVE_MUSIC, 1)[0],
        "route_kind": session.read_memory("snesMemory", ROUTE_KIND, 1)[0],
        "route_value": session.read_memory("snesMemory", ROUTE_VALUE, 1)[0],
        "matrix": {
            "box_count": matrix[0], "box_12_flags": matrix[1 + 12],
            "box_20_flags": matrix[1 + 20], "last_subopcode": matrix[0x100],
            "last_box": matrix[0x101], "last_flags": matrix[0x102],
            "execution_count": matrix[0x103], "trace": matrix_trace,
        },
        "actor_10": {
            "position": [u16(position), u16(position, 2)],
            "moving": session.read_memory("snesMemory", MOVING + 10, 1)[0],
            "visible": actor_record[0x15], "room": actor_record[0x16],
            "walkbox": put_actor[0x240 + 10],
            "destination_box": put_actor[0x260 + 10],
            "destination_x": u16(put_actor, 0x280 + 10 * 2),
            "redraw": put_actor[0x2C0 + 10],
            "box_scale_raw": u16(put_actor, 0x40C + 10 * 2),
            "effective_scale": [actor_record[0x0D], actor_record[0x0E]],
        },
        "put_actor": {
            "actor": put_actor[0x360], "request_x": u16(put_actor, 0x361),
            "request_y": u16(put_actor, 0x363), "result_x": u16(put_actor, 0x365),
            "result_y": u16(put_actor, 0x367), "result_box": put_actor[0x369],
            "pc_before": u16(put_actor, 0x37D), "pc_after": u16(put_actor, 0x37F),
            "execution_count": put_actor[0x381],
        },
        "set_state": {
            "global_count": u16(setstate), "object": u16(setstate, 2),
            "state": setstate[4], "local_found": setstate[5],
            "background_needs_redraw": setstate[6], "execution_count": setstate[7],
            "pc_before": u16(setstate, 8), "pc_after": u16(setstate, 10),
            "local_count": setstate[12], "dirty_count": setstate[13],
            "object_590_state": setstate[0x10 + 590],
            "dirty_rect": [u16(setstate, 0x18A8 + offset) for offset in (0, 2, 4, 6)],
            "draw_queue_count": setstate[0x18B0],
        },
        "slots": slots,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--host-report", type=Path, required=True)
    parser.add_argument(
        "--cooked-room", type=Path,
        default=ROOT / "build/m23a-rooms/authentic/room-49.sc5c",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44740)
    args = parser.parse_args()
    require(args.rom.is_file(), f"ROM missing: {args.rom}")
    require(args.host_report.is_file(), f"host report missing: {args.host_report}")
    require(args.cooked_room.is_file(), f"cooked room missing: {args.cooked_room}")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")

    host = json.loads(args.host_report.read_text())
    cooked = decode_cooked_room(args.cooked_room.read_bytes(), expected_room=49)
    local200 = next(
        (item for item in cooked.scripts if item.kind == "LSCR" and item.number == 200),
        None,
    )
    require(local200 is not None, "authentic cooked room has no LSCR 200")
    require(
        local200.sha256 == "dc34f2d549455fbd6ee30eb057470b39e97e4544ff3cbe49d94424158e3cbc6c",
        f"authentic LSCR 200 identity differs: {local200.sha256}",
    )
    require(local200.program[:8] == bytes.fromhex("30 01 0c 80 30 01 14 80"),
            f"authentic matrixOps prefix differs: {local200.program[:8].hex()}")
    positive = (next(item for item in host["cases"] if item["case"] == "pre-thera-positive")
                if "cases" in host else {"trace": []})
    host_prefix = [{
        "script": item["script"],
        "offset": item["runtime_instruction_offset"],
        "opcode": item["opcode"],
        "next": item["next_runtime_offset"],
    } for item in positive["trace"] if (
        item["script"] in {"room.49/ENCD", "script.144", "script.145"}
        and item["runtime_instruction_offset"] <= 0x7A
    )]
    host_matrix = [item for item in positive["trace"]
                   if item["script"] == "room.49/LSCR.200"
                   and item["runtime_instruction_offset"] in {0, 4}]
    if host_matrix:
        require([(item["runtime_instruction_offset"], item["opcode"],
              item["next_runtime_offset"], item.get("box_flag_changes"))
             for item in host_matrix] == [
                 (0, 0x30, 4, [[12, 0, 128]]),
                 (4, 0x30, 8, [[20, 0, 128]]),
             ], f"host matrixOps oracle differs: {host_matrix}")

    args.output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None

    timeline: list[dict[str, object]] = []
    restored = None
    nested = None
    final = None
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=2.0, socket_timeout=90.0,
        stderr_log=args.output / "nexen-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")
        previous = None
        for frame in range(1, 501):
            step = session.run_frames(1)
            require(step["framesAdvanced"] == 1 and not step["timedOut"], "emulator frame timeout")
            state = snapshot(session, frame)
            key = (state["pc"], state["status"], state["error"], state["last_opcode"],
                   state["program"], state["return_mode"], state["current_slot"],
                   state["nest_depth"], state["active_music"], state["route_value"])
            if key != previous:
                timeline.append(state)
                previous = key
            if state["program"] == 0xE5 and state["nest_depth"] == 2:
                nested = state
            if (state["program"] == 0xD1 and state["nest_depth"] == 0
                    and state["return_mode"] == 0 and state["pc"] >= 0x6A
                    and state["error"] == 0):
                restored = state
            if state["error"]:
                final = state
                break

    require(nested is not None, "authentic ENCD -> global 144 -> global 145 nesting was not observed")
    require(restored is not None, "authentic outer ENCD context was not restored")
    require(final is not None,
            f"authentic execution did not reach a fail-closed next blocker: {timeline[-1]}")
    require(restored["active_room"] == 49 and restored["validation_count"] == 1
            and restored["entry_count"] == 1 and restored["room_phase"] == 2,
            f"room-49 resource/lifecycle evidence differs: {restored}")
    require(restored["active_music"] == 80 and restored["route_kind"] == 1
            and restored["route_value"] == 14,
            f"authentic music block was not naturally reached: {restored}")
    blocked = next((item for item in final["slots"] if item["number"] == 201), None)
    expected_matrix = {
        "box_count": 23, "box_12_flags": 128, "box_20_flags": 128,
        "last_subopcode": 1, "last_box": 20, "last_flags": 128,
        "execution_count": 2,
        "trace": [
            {"subopcode": 1, "box": 12, "flags": 128,
             "pc_before": 0, "pc_after": 4},
            {"subopcode": 1, "box": 20, "flags": 128,
             "pc_before": 4, "pc_after": 8},
        ],
    }
    require(final["matrix"] == expected_matrix,
            f"authentic matrixOps state/trace differs: {final['matrix']}")
    require(final["actor_10"] == {
        "position": [536, 137], "moving": 0, "visible": 1, "room": 49,
        "walkbox": 9, "destination_box": 9, "destination_x": 0xFFFF,
        "redraw": 1,
        "box_scale_raw": 0x8001, "effective_scale": [255, 255],
    }, f"authentic actor-10 state differs: {final['actor_10']}")
    require(final["set_state"] == {
        "global_count": 1395, "object": 590, "state": 0,
        "local_found": 1, "background_needs_redraw": 1,
        "execution_count": 1, "pc_before": 0x014F, "pc_after": 0x0153,
        "local_count": 8, "dirty_count": 1, "object_590_state": 0,
        "dirty_rect": [312, 64, 96, 64], "draw_queue_count": 0,
    }, f"authentic setState decode/state/invalidation differs: {final['set_state']}")

    report = {
        "gate": "M25-authentic-one-semantic-blocker",
        "result": "pass",
        "fresh_power_on": True,
        "debugger_writes": 0,
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "host_oracle": {"report": str(args.host_report), "prefix": host_prefix,
                        "matrix_ops": host_matrix},
        "observed_nested_global145": nested,
        "observed_restored_room49_encd": restored,
        "set_state": final["set_state"],
        "next_blocker": {
            "script": "room.49/LSCR.201", "program": 0xD3,
            "offset": 0, "opcode": 0x63,
            "bytes": next(item for item in cooked.scripts if item.kind == "LSCR" and item.number == 201).program[:24].hex(),
            "operands": {"result_variable": 0, "actor": 10},
            "error": host.get("next_blocker", {}).get("error"), "slot": blocked,
        },
        "terminal_after_nested_blocker": {
            "error": final["error"], "last_opcode": final["last_opcode"],
            "slot": next((item for item in final["slots"] if item["number"] == 200), None),
        },
        "put_actor_latest": final["put_actor"],
        "actor_10": final["actor_10"],
        "matrix_ops": final["matrix"],
        "authentic_blocker_source": {
            "cooked_room": str(args.cooked_room),
            "record_sha256": hashlib.sha256(args.cooked_room.read_bytes()).hexdigest(),
            "script_sha256": local200.sha256,
            "original_file_offset": local200.original_file_offset,
            "original_room_offset": local200.original_room_offset,
            "original_chunk_offset": local200.original_chunk_offset,
            "cooked_record_offset": local200.cooked_record_offset,
            "prefix": local200.program[:8].hex(),
        },
        "timeline": timeline,
    }
    path = args.output / "report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "rom_sha256": report["rom_sha256"],
                      "report": str(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
