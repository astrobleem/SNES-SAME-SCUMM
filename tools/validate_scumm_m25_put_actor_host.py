#!/usr/bin/env python3
"""Authoritative host trace for authentic room-49 LSCR 200 setState."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from same.errors import EngineExecutionError
from same.engines.scumm_v5.cooked_room import decode_cooked_room
from same.engines.scumm_v5.room import decode_room
from validate_scumm_m23b_host import STATE, make_host


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/fatedemo-box.zip"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--cooked-room", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fixture = json.loads(STATE.read_text())
    cooked = decode_cooked_room(args.cooked_room.read_bytes(), expected_room=49)
    script = next(item for item in cooked.scripts if item.kind == "LSCR" and item.number == 200)
    assert script.program[0x146:0x14C] == bytes.fromhex("01 0a 47 02 88 00")
    assert script.program[0x14F:0x153] == bytes.fromhex("07 4e 02 00")
    room = decode_room(cooked.room_payload, key="room.49")
    local_index, resource_object = next(
        (index, item) for index, item in enumerate(room.objects, 1)
        if item.object_id == 590
    )
    host, _ = make_host(args.archive, args.manifest)
    engine = host.engine
    engine.state.scripts[0].active = False
    for bit in fixture["bits_set"]:
        engine.state.bit_variables[int(bit)] = True
    for key, spec in fixture["strings"].items():
        engine.state.strings[int(key)] = bytearray([int(spec["fill"])] * int(spec["length"]))
    engine._load_room(host.context, 49, required=True)
    observed = {}
    original = engine._op_set_state

    def traced(slot, context):
        target = engine.state.room_objects[590]
        before = {
            "global_state": engine.state.object_states.get(590, 0),
            "local_state": target.state,
            "draw_queue": list(engine.state.object_draw_queue),
            "background_needs_redraw": engine._background_needs_redraw,
        }
        pc_before = slot.pc - 1
        result = original(slot, context)
        observed.update({"pc_before": pc_before, "pc_after": slot.pc,
                         "before": before,
                         "after": {
                             "global_state": engine.state.object_states[590],
                             "local_state": target.state,
                             "draw_queue": list(engine.state.object_draw_queue),
                             "background_needs_redraw": engine._background_needs_redraw,
                         }})
        return result

    for opcode in (0x07, 0x47, 0x87, 0xC7):
        engine._handlers[opcode] = traced
    error = None
    try:
        host.tick()
    except EngineExecutionError as exc:
        error = str(exc)
    assert observed["pc_before"] == 0x14F and observed["pc_after"] == 0x153
    assert observed["before"]["global_state"] == 0
    assert observed["after"] == {
        "global_state": 0, "local_state": 0, "draw_queue": [],
        "background_needs_redraw": True,
    }
    assert error is not None and "opcode" in error
    report = {
        "gate": "M25-canonical-setState-host", "result": "pass",
        "fixture": fixture["name"], "script_identity": script.identity,
        "script_sha256": script.sha256,
        "record_sha256": hashlib.sha256(args.cooked_room.read_bytes()).hexdigest(),
        "source_map": script.runtime_map(0x14F),
        "instruction": {"bytes": script.program[0x14F:0x153].hex(),
                        "object": 590, "state": 0,
                        "pc_before": 0x14F, "pc_after": 0x153},
        "object_590": {
            "global_id": 590, "owner": 15, "owner_meaning": "room",
            "initial_global_state": 0, "room": 49, "local_index": local_index,
            "resource": {
                "position": [resource_object.x, resource_object.y],
                "size": [resource_object.width, resource_object.height],
                "walk": [resource_object.walk_x, resource_object.walk_y],
                "flags": resource_object.flags, "parent": resource_object.parent,
            },
        },
        **observed,
        "next_blocker": {"offset": engine.state.scripts[-1].pc - 1,
                         "opcode": engine.state.last_opcode,
                         "bytes": script.program[max(0, engine.state.scripts[-1].pc - 9):engine.state.scripts[-1].pc + 15].hex(),
                         "error": error},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
