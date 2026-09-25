#!/usr/bin/env python3
"""Authoritative host trace for authentic room-49 LSCR 201 getActorFacing."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from same.errors import EngineExecutionError
from same.engines.scumm_v5.cooked_room import decode_cooked_room
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
    script = next(item for item in cooked.scripts if item.kind == "LSCR" and item.number == 201)
    assert script.program[:4] == bytes.fromhex("63 00 00 0a")

    host, _ = make_host(args.archive, args.manifest)
    engine = host.engine
    engine.state.scripts[0].active = False
    for bit in fixture["bits_set"]:
        engine.state.bit_variables[int(bit)] = True
    for key, spec in fixture["strings"].items():
        engine.state.strings[int(key)] = bytearray([int(spec["fill"])] * int(spec["length"]))
    engine._load_room(host.context, 49, required=True)

    trace: list[dict[str, object]] = []
    parent_trace: list[dict[str, object]] = []
    original = engine._op_get_actor_facing
    original_step = engine._step

    def traced_step(slot, context):
        pc_before = slot.pc
        variables_before = list(engine.state.variables)
        original_step(slot, context)
        if slot.resource_key == "room.49/LSCR.200" and pc_before >= 0x150:
            parent_trace.append({
                "pc_before": pc_before, "pc_after": slot.pc,
                "opcode": slot.program[pc_before],
                "variable_changes": [
                    [index, variables_before[index], engine.state.variables[index]]
                    for index in range(len(variables_before))
                    if variables_before[index] != engine.state.variables[index]
                ],
            })

    engine._step = traced_step

    def traced(slot, context):
        actor_id = (
            engine._read_var(slot, int.from_bytes(slot.program[slot.pc + 2:slot.pc + 4], "little")) & 0xFF
            if engine.state.last_opcode & 0x80 else slot.program[slot.pc + 2]
        )
        actor = engine.state.actors[actor_id]
        before_actor = actor.to_dict()
        before_variables = list(engine.state.variables)
        pc_before = slot.pc - 1
        result = original(slot, context)
        result_ref = int.from_bytes(slot.program[pc_before + 1:pc_before + 3], "little")
        trace.append({
            "script": slot.resource_key, "pc_before": pc_before, "pc_after": slot.pc,
            "opcode": engine.state.last_opcode, "operand_mode": "variable" if engine.state.last_opcode & 0x80 else "direct",
            "actor": actor_id, "raw_facing": actor.facing,
            "converted": engine._new_dir_to_old_dir(actor.facing),
            "result_reference": result_ref,
            "result_before": before_variables[result_ref],
            "result_after": engine.state.variables[result_ref],
            "actor_before": before_actor, "actor_after": actor.to_dict(),
            "other_variables_unchanged": all(
                index == result_ref or value == engine.state.variables[index]
                for index, value in enumerate(before_variables)
            ),
        })
        return result

    engine._handlers[0x63] = traced
    engine._handlers[0xE3] = traced
    error = None
    try:
        host.tick()
    except EngineExecutionError as exc:
        error = str(exc)
    assert trace and trace[0]["script"] == "room.49/LSCR.201"
    assert trace[0]["pc_before"] == 0 and trace[0]["pc_after"] == 4
    assert trace[0]["actor"] == 10 and trace[0]["result_reference"] == 0
    assert trace[0]["actor_before"] == trace[0]["actor_after"]
    assert trace[0]["other_variables_unchanged"]
    assert error is not None
    match = re.search(r"opcode \$([0-9A-Fa-f]{2}).*script ([^,]+), offset \$([0-9A-Fa-f]+)", error)
    if match is not None:
        blocker_opcode = int(match.group(1), 16)
        blocker_script = match.group(2)
        blocker_offset = int(match.group(3), 16)
        blocker_kind = "opcode_gap"
    else:
        yielded = next(
            candidate for candidate in engine.state.scripts
            if candidate.active and candidate.resource_key == "room.49/LSCR.201"
        )
        blocker_script = yielded.resource_key
        blocker_offset = yielded.pc
        blocker_opcode = yielded.program[yielded.pc]
        blocker_kind = "engine_subsystem"
    blocker_descriptor = next(
        item for item in cooked.scripts if item.identity == blocker_script
    )
    around_start = max(0, blocker_offset - 8)
    report = {
        "gate": "M25-canonical-getActorFacing-host", "result": "pass",
        "fixture": fixture["name"], "script_identity": script.identity,
        "script_sha256": script.sha256,
        "record_sha256": hashlib.sha256(args.cooked_room.read_bytes()).hexdigest(),
        "source_map": script.runtime_map(0),
        "instruction": {"bytes": script.program[:4].hex(), "pc_before": 0, "pc_after": 4},
        "queries": trace, "parent_trace": parent_trace,
        "next_blocker": {
            "script": blocker_script, "offset": blocker_offset,
            "opcode": blocker_opcode, "kind": blocker_kind, "error": error,
            "surrounding_start": around_start,
            "surrounding_bytes": blocker_descriptor.program[
                around_start:blocker_offset + 16
            ].hex(),
            "source_map": blocker_descriptor.runtime_map(blocker_offset),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
