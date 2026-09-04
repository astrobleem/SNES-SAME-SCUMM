#!/usr/bin/env python3
"""Authoritative host trace for authentic room-49 LSCR 216 getActorWalkBox."""

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
    script = next(item for item in cooked.scripts if item.kind == "LSCR" and item.number == 216)
    assert script.program[:4] == bytes.fromhex("7b ba 01 01")

    host, _ = make_host(args.archive, args.manifest)
    engine = host.engine
    # Costume 45 is independently unavailable in the supplied demo. This
    # semantic oracle intentionally follows the already accepted headless lane.
    host.context.profile.options["headless_presentation"] = True
    engine.state.scripts[0].active = False
    for bit in fixture["bits_set"]:
        engine.state.bit_variables[int(bit)] = True
    for key, spec in fixture["strings"].items():
        engine.state.strings[int(key)] = bytearray([int(spec["fill"])] * int(spec["length"]))
    engine._load_room(host.context, 49, required=True)

    trace: list[dict[str, object]] = []
    original = engine._op_get_actor_walkbox

    def traced(slot, context):
        pc_before = slot.pc - 1
        result_ref = int.from_bytes(slot.program[slot.pc:slot.pc + 2], "little")
        actor_cursor = slot.pc + 2
        if engine.state.last_opcode & 0x80:
            actor_ref = int.from_bytes(slot.program[actor_cursor:actor_cursor + 2], "little")
            actor_id = engine._read_var(slot, actor_ref) & 0xFF
            operand_mode = "variable"
        else:
            actor_id = slot.program[actor_cursor]
            operand_mode = "direct"
        actor = engine.state.actors[actor_id]
        before_actor = actor.to_dict()
        before_variables = list(engine.state.variables)
        result = original(slot, context)
        trace.append({
            "script": slot.resource_key, "pc_before": pc_before, "pc_after": slot.pc,
            "opcode": engine.state.last_opcode, "operand_mode": operand_mode,
            "actor": actor_id, "stored_walkbox": before_actor["walkbox"],
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

    engine._handlers[0x7B] = traced
    engine._handlers[0xFB] = traced
    error = None
    # A tick may stop at breakHere while the talk clock advances globally.
    # Continue bounded canonical frames until LSCR 216 queries or faults.
    for _frame in range(600):
        try:
            host.tick()
        except EngineExecutionError as exc:
            error = str(exc)
            break
        # Once the query executes, keep following ordinary scheduler frames to
        # the first later unsupported script-visible semantic.
    assert trace and trace[0]["script"] == "room.49/LSCR.216"
    assert trace[0]["pc_before"] == 0 and trace[0]["pc_after"] == 4
    assert trace[0]["actor"] == 1 and trace[0]["result_reference"] == 442
    assert trace[0]["stored_walkbox"] == 11 and trace[0]["result_after"] == 11
    assert trace[0]["actor_before"] == trace[0]["actor_after"]
    assert trace[0]["other_variables_unchanged"]
    next_blocker = None
    if error is not None:
        match = re.search(
            r"opcode \$([0-9A-Fa-f]{2}).*script ([^,]+), offset \$([0-9A-Fa-f]+)", error
        )
        assert match is not None, error
        blocker_opcode = int(match.group(1), 16)
        blocker_script = match.group(2)
        blocker_offset = int(match.group(3), 16)
        blocker_descriptor = next(item for item in cooked.scripts if item.identity == blocker_script)
        around_start = max(0, blocker_offset - 8)
        next_blocker = {
            "script": blocker_script, "offset": blocker_offset,
            "opcode": blocker_opcode, "kind": "opcode_gap", "error": error,
            "surrounding_start": around_start,
            "surrounding_bytes": blocker_descriptor.program[
                around_start:blocker_offset + 16
            ].hex(),
            "source_map": blocker_descriptor.runtime_map(blocker_offset),
        }
    report = {
        "gate": "M25-canonical-getActorWalkBox-host", "result": "pass",
        "fixture": fixture["name"], "script_identity": script.identity,
        "script_sha256": script.sha256,
        "record_sha256": hashlib.sha256(args.cooked_room.read_bytes()).hexdigest(),
        "source_map": script.runtime_map(0),
        "instruction": {"bytes": script.program[:4].hex(), "pc_before": 0, "pc_after": 4},
        "queries": trace,
        "next_blocker": next_blocker,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
