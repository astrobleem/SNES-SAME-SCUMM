#!/usr/bin/env python3
"""Generate profile-owned SNES lookup tables for cooked SCUMM room records."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from same.engines.scumm_v5.cooked_room import HEADER, decode_cooked_room
from same.engines.scumm_v5.room import decode_room


KIND = {"ENCD": 1, "EXCD": 2, "LSCR": 3}


def rows(data: bytes, indent: str = "    ") -> str:
    return "\n".join(
        indent + ".byte " + ",".join(f"${value:02X}" for value in data[index:index + 16])
        for index in range(0, len(data), 16)
    )


def portal_table(room) -> bytes:
    """Cook every BOXD shared-edge portal; BOXM still selects route topology."""
    output = bytearray()
    for source in room.walkboxes:
        for target in room.walkboxes:
            portal: tuple[int, int, int, int] | None = None
            first, second = source.points, target.points
            for edge_a in range(4):
                a0, a1 = first[edge_a], first[(edge_a + 1) & 3]
                for edge_b in range(4):
                    b0, b1 = second[edge_b], second[(edge_b + 1) & 3]
                    if a0[0] == a1[0] == b0[0] == b1[0]:
                        a_low, a_high = sorted((a0[1], a1[1]))
                        b_low, b_high = sorted((b0[1], b1[1]))
                        touching = ((a_high == b_low or b_high == a_low)
                                    and a_low != a_high and b_low != b_high)
                        if not (a_low > b_high or b_low > a_high or touching):
                            portal = (1, a0[0], max(a_low, b_low), min(a_high, b_high))
                            break
                    if a0[1] == a1[1] == b0[1] == b1[1]:
                        a_low, a_high = sorted((a0[0], a1[0]))
                        b_low, b_high = sorted((b0[0], b1[0]))
                        touching = ((a_high == b_low or b_high == a_low)
                                    and a_low != a_high and b_low != b_high)
                        if not (a_low > b_high or b_low > a_high or touching):
                            portal = (2, a0[1], max(a_low, b_low), min(a_high, b_high))
                            break
                if portal is not None:
                    break
            output.extend(struct.pack("<Bhhh", *(portal or (0, 0, 0, 0))))
    return bytes(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-output", type=Path, required=True)
    parser.add_argument(
        "--far-validator-output",
        type=Path,
        help="emit the cold cooked-record validator separately for a far ROM bank",
    )
    parser.add_argument("--long-object-fail-branch", action="store_true")
    parser.add_argument("--binary-dir", type=Path, required=True)
    parser.add_argument("--first-bank", type=int, default=3)
    parser.add_argument("--entry-only-room", type=int, action="append", default=[])
    parser.add_argument(
        "--executable-local-script-room", action="append", type=int,
        default=[], metavar="ROOM",
        help="keep all local scripts executable while omitting dormant room objects",
    )
    parser.add_argument("--entry-exit-room", type=int, action="append", default=[])
    parser.add_argument("--executable-local", action="append", default=[], metavar="ROOM:SCRIPT")
    parser.add_argument(
        "--executable-local-object", action="append", default=[],
        metavar="ROOM:OBJECT",
        help="make one OBCD descriptor in an entry-only room executable",
    )
    parser.add_argument(
        "--executable-local-room",
        action="append",
        type=int,
        default=[],
        metavar="ROOM",
        help="make every LSCR descriptor in ROOM executable and resolvable",
    )
    parser.add_argument(
        "--scenario-class-overlay", action="append", default=[], metavar="OBJECT:MASK",
        help="fixture-only OR mask applied after source DOBJ loading",
    )
    parser.add_argument(
        "--scenario-bit-overlay", action="append", default=[], metavar="BIT",
        help="fixture-only set of source-justified bit variables",
    )
    parser.add_argument(
        "--scenario-state-overlay", action="append", default=[], metavar="OBJECT:STATE",
        help="fixture-only source-justified object state at a sentence boundary",
    )
    parser.add_argument(
        "--far-programs",
        action="store_true",
        help="place executable script bytes with profile data instead of bank-0 lookup code",
    )
    args = parser.parse_args()
    scenario_class_overlays = []
    for raw in args.scenario_class_overlay:
        object_text, separator, mask_text = raw.partition(":")
        if not separator:
            parser.error(f"invalid --scenario-class-overlay {raw!r}; expected OBJECT:MASK")
        try:
            object_id, mask = int(object_text, 0), int(mask_text, 0)
        except ValueError:
            parser.error(f"invalid --scenario-class-overlay {raw!r}; expected numeric OBJECT:MASK")
        if not 0 <= object_id < 0x10000 or not 0 <= mask < 0x100000000:
            parser.error(f"out-of-range --scenario-class-overlay {raw!r}")
        scenario_class_overlays.append((object_id, mask))
    scenario_bit_overlays = []
    for raw in args.scenario_bit_overlay:
        try:
            bit = int(raw, 0)
        except ValueError:
            parser.error(f"invalid --scenario-bit-overlay {raw!r}; expected numeric bit")
        if not 0 <= bit < 4096:
            parser.error(f"out-of-range --scenario-bit-overlay {raw!r}")
        scenario_bit_overlays.append(bit)
    scenario_state_overlays = []
    for raw in args.scenario_state_overlay:
        object_text, separator, state_text = raw.partition(":")
        if not separator:
            parser.error(f"invalid --scenario-state-overlay {raw!r}; expected OBJECT:STATE")
        try:
            object_id, state = int(object_text, 0), int(state_text, 0)
        except ValueError:
            parser.error(f"invalid --scenario-state-overlay {raw!r}; expected numeric OBJECT:STATE")
        if not 0 <= object_id < 0x10000 or not 0 <= state <= 0xFF:
            parser.error(f"out-of-range --scenario-state-overlay {raw!r}")
        scenario_state_overlays.append((object_id, state))
    executable_locals = {
        tuple(int(value) for value in item.split(":")) for item in args.executable_local
    }
    if any(len(item) != 2 for item in executable_locals):
        raise RuntimeError("--executable-local requires ROOM:SCRIPT")
    executable_local_objects = {
        tuple(int(value) for value in item.split(":"))
        for item in args.executable_local_object
    }
    if any(len(item) != 2 for item in executable_local_objects):
        raise RuntimeError("--executable-local-object requires ROOM:OBJECT")
    args.binary_dir.mkdir(parents=True, exist_ok=True)
    records = []
    programs = []
    global_scripts = []
    global_states: bytes | None = None
    global_owners: bytes | None = None
    global_classes: tuple[int, ...] | None = None
    num_global_scripts: int | None = None
    hold_after_started_global_script: int | None = None
    actor_facings: tuple[int, ...] | None = None
    actor_positions: tuple[tuple[int, int], ...] | None = None
    actor_walkboxes: tuple[int, ...] | None = None
    next_program = 0xD0
    for manifest_path in args.manifest:
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("schema") != "same_scumm_v5_cooked_rooms_v1":
            raise RuntimeError(f"{manifest_path}: cooked-room schema differs")
        manifest_global_scripts = manifest.get("num_global_scripts")
        if (
            isinstance(manifest_global_scripts, bool)
            or not isinstance(manifest_global_scripts, int)
            or not 0 <= manifest_global_scripts <= 256
        ):
            raise RuntimeError(f"{manifest_path}: num_global_scripts must be in 0..256")
        if num_global_scripts is not None and manifest_global_scripts != num_global_scripts:
            raise RuntimeError("cooked-room manifests disagree on num_global_scripts")
        num_global_scripts = manifest_global_scripts
        gate = manifest.get("execution_gate")
        if gate is not None:
            value = gate.get("hold_after_started_global_script") if isinstance(gate, dict) else None
            if isinstance(value, bool) or not isinstance(value, int) or not 0 < value < manifest_global_scripts:
                raise RuntimeError(f"{manifest_path}: execution gate is malformed")
            if (hold_after_started_global_script is not None
                    and hold_after_started_global_script != value):
                raise RuntimeError("cooked-room manifests disagree on execution gate")
            hold_after_started_global_script = value
        global_spec = manifest.get("global_objects")
        if global_spec is not None:
            source_states = (manifest_path.parent / global_spec["states_output"]).read_bytes()
            # Neutral interaction fixtures begin from a zero mutable table.
            # A controlled source-root manifest may opt into source DOBJ
            # states when room-entry bytecode consumes them before the first
            # semantic sentence boundary (for example actor placement gates).
            candidate = (source_states if manifest.get("source_initial_states")
                         else bytes(len(source_states)))
            if len(candidate) != int(global_spec["count"]):
                raise RuntimeError(f"{manifest_path}: global-object state count differs")
            # A source-root manifest may establish the canonical initial
            # table; companion room manifests retain the neutral legacy
            # declaration and must not erase or contradict that table.
            if (global_states is not None and candidate != global_states
                    and any(global_states)
                    and any(candidate)):
                raise RuntimeError("cooked-room manifests disagree on global-object state")
            if global_states is None or any(candidate):
                global_states = candidate
            source_owners = (manifest_path.parent / global_spec["owners_output"]).read_bytes()
            if len(source_owners) != int(global_spec["count"]):
                raise RuntimeError(f"{manifest_path}: global-object owner count differs")
            if global_owners is not None and source_owners != global_owners:
                raise RuntimeError("cooked-room manifests disagree on global-object owners")
            global_owners = bytes(source_owners)
            classes_name = global_spec.get("classes_output")
            if classes_name is not None:
                source_classes = (manifest_path.parent / classes_name).read_bytes()
                if len(source_classes) != int(global_spec["count"]) * 4:
                    raise RuntimeError(f"{manifest_path}: global-object class count differs")
                candidate_classes = tuple(
                    int.from_bytes(source_classes[index:index + 4], "little")
                    for index in range(0, len(source_classes), 4)
                )
                if global_classes is not None and candidate_classes != global_classes:
                    raise RuntimeError("cooked-room manifests disagree on global-object classes")
                global_classes = candidate_classes
        manifest_facings = manifest.get("actor_facings")
        if manifest_facings is not None:
            candidate_facings = tuple(int(value) for value in manifest_facings)
            if len(candidate_facings) != 32 or any(
                not 0 <= value <= 0xFFFF for value in candidate_facings
            ):
                raise RuntimeError(f"{manifest_path}: actor_facings must contain 32 u16 values")
            if actor_facings is not None and candidate_facings != actor_facings:
                raise RuntimeError("cooked-room manifests disagree on actor facings")
            actor_facings = candidate_facings
        manifest_positions = manifest.get("actor_positions")
        if manifest_positions is not None:
            candidate_positions = tuple(
                (int(item[0]), int(item[1])) for item in manifest_positions
            )
            if len(candidate_positions) != 32 or any(
                not -0x8000 <= value <= 0x7FFF
                for point in candidate_positions for value in point
            ):
                raise RuntimeError(f"{manifest_path}: actor_positions must contain 32 s16 pairs")
            if actor_positions is not None and candidate_positions != actor_positions:
                raise RuntimeError("cooked-room manifests disagree on actor positions")
            actor_positions = candidate_positions
        manifest_walkboxes = manifest.get("actor_walkboxes")
        if manifest_walkboxes is not None:
            candidate_walkboxes = tuple(int(value) for value in manifest_walkboxes)
            if len(candidate_walkboxes) != 32 or any(
                not 0 <= value <= 0xFF for value in candidate_walkboxes
            ):
                raise RuntimeError(f"{manifest_path}: actor_walkboxes must contain 32 u8 values")
            if actor_walkboxes is not None and candidate_walkboxes != actor_walkboxes:
                raise RuntimeError("cooked-room manifests disagree on actor walkboxes")
            actor_walkboxes = candidate_walkboxes
        for source_record in manifest["records"]:
            path = manifest_path.parent / source_record["output"]
            raw = path.read_bytes()
            decoded = decode_cooked_room(raw, expected_room=int(source_record["room"]))
            decoded_room = decode_room(decoded.room_payload, key=f"room.{decoded.room}")
            record_index = len(records)
            script_records = []
            for script in decoded.scripts:
                executable = (
                    not decoded.registration_only
                    and (
                        decoded.room in args.executable_local_room
                        or decoded.room in args.executable_local_script_room
                        or (decoded.room, script.number) in executable_locals
                        or script.kind in {"ENCD", "EXCD"}
                        or decoded.room not in args.entry_only_room
                    )
                )
                # Entry-only rooms retain their source directory metadata but
                # do not consume scarce executable program identities for
                # dormant local scripts.
                if not executable:
                    continue
                if next_program > 0xFF:
                    raise RuntimeError("cooked script program-id space exhausted")
                item = {
                    "id": next_program, "record": record_index, "room": decoded.room,
                    "kind": KIND[script.kind], "kind_name": script.kind,
                    "number": script.number, "length": len(script.program),
                    "program": script.program, "identity": script.identity,
                    "source": script,
                    # Resolvability is distinct from lifecycle scheduling.
                    # Every LSCR in an executable complete room may be started;
                    # ENCD/EXCD selection remains governed by room lifecycle.
                    "executable": executable,
                }
                programs.append(item)
                script_records.append(item)
                next_program += 1
            source_objects = {
                int(item["object_id"]): item for item in source_record.get("objects", [])
            }
            object_programs = []
            selected_objects_for_room = {
                object_id for room, object_id in executable_local_objects
                if room == decoded.room
            }
            include_objects = (
                not decoded.registration_only
                and (
                    decoded.room in args.executable_local_room
                    or any(
                        (decoded.room, int(item.object_id)) in executable_local_objects
                        for item in decoded_room.objects
                    )
                    or decoded.room not in args.entry_only_room
                )
            )
            for local_index, item in enumerate(decoded_room.objects, 1):
                selected_object = (decoded.room, item.object_id) in executable_local_objects
                if not include_objects or (
                    decoded.room in args.entry_only_room
                    and selected_objects_for_room
                    and not selected_object
                ):
                    continue
                if next_program > 0xFF:
                    raise RuntimeError(
                        f"cooked object-program id space exhausted at room {decoded.room} "
                        f"object {item.object_id} (next id {next_program:#x})"
                    )
                source = source_objects.get(item.object_id)
                if source is not None:
                    if (
                        int(source["local_object_index"]) != local_index
                        or int(source["obcd_room_offset"]) != item.obcd_room_offset
                        or int(source["obcd_length"]) != len(item.obcd)
                        or source["obcd_sha256"] != hashlib.sha256(item.obcd).hexdigest()
                    ):
                        raise RuntimeError(
                            f"room {decoded.room} object {item.object_id} OBCD provenance differs"
                        )
                program_item = {
                    "id": next_program, "record": record_index, "room": decoded.room,
                    "kind": 4, "kind_name": "OBCD", "number": item.object_id,
                    "length": len(item.obcd), "program": item.obcd,
                    "identity": f"room.{decoded.room}/object.{item.object_id}/OBCD",
                    "source": source, "executable": not decoded.registration_only,
                    "entrypoints": item.verb_entries,
                    "local_object_index": local_index,
                }
                programs.append(program_item)
                object_programs.append(program_item)
                next_program += 1
            records.append({
                "room": decoded.room, "flags": decoded.flags, "raw": raw,
                "checksum": decoded.compact_checksum, "scripts": script_records,
                "entry": next((x["id"] for x in script_records if x["kind_name"] == "ENCD"), 0),
                "exit": next((x["id"] for x in script_records if x["kind_name"] == "EXCD"), 0),
                "locals": [x for x in script_records if x["kind_name"] == "LSCR"],
                "executable_locals": [x for x in script_records
                                      if x["kind_name"] == "LSCR" and x["executable"]],
                "object_programs": object_programs,
                "walkbox_flags": bytes(box.flags for box in decoded_room.walkboxes),
                "walkbox_geometry": b"".join(
                    struct.pack(
                        "<hhhhhhhhH", *(value for point in box.points for value in point),
                        box.scale,
                    )
                    for box in decoded_room.walkboxes
                ),
                "box_routes": bytes(
                    0xFF if route is None else route
                    for route_row in decoded_room.box_routes for route in route_row
                ),
                "portals": portal_table(decoded_room),
                "objects": b"".join(
                    struct.pack(
                        "<HhhhhB",
                        item.object_id, item.x, item.y, item.width, item.height,
                        item.flags,
                    )
                    for item in decoded_room.objects
                ),
                "object_walk": b"".join(
                    struct.pack(
                        "<HhhBhhB",
                        item.object_id,
                        item.walk_x,
                        item.walk_y,
                        item.actor_direction,
                        *decoded_room.adjust_point(item.walk_x, item.walk_y)[0],
                        decoded_room.adjust_point(item.walk_x, item.walk_y)[1],
                    )
                    for item in decoded_room.objects
                ),
                "verb_entries": tuple(
                    (item.object_id, verb, offset)
                    for item in decoded_room.objects
                    for verb, offset in item.verb_entries
                ),
            })
            local_numbers = [item["number"] for item in script_records if item["kind_name"] == "LSCR"]
            if len(set(local_numbers)) != len(local_numbers):
                raise RuntimeError(f"room {decoded.room} has duplicate executable local-script IDs")
            if any(number < manifest_global_scripts for number in local_numbers):
                raise RuntimeError(
                    f"room {decoded.room} has LSCR below global-script boundary "
                    f"{manifest_global_scripts}"
                )
        for source_script in manifest.get("global_scripts", []):
            number = int(source_script["number"])
            program = (manifest_path.parent / source_script["output"]).read_bytes()
            if len(program) != int(source_script["length"]):
                raise RuntimeError(f"global script {number} length differs")
            existing_global = next(
                (item for item in global_scripts if item["number"] == number), None
            )
            if existing_global is not None:
                if existing_global["program"] != program:
                    raise RuntimeError(
                        f"global script {number} differs between cooked-room manifests"
                    )
                continue
            if next_program > 0xFF:
                raise RuntimeError("cooked script program-id space exhausted")
            item = {
                "id": next_program, "record": None, "room": None,
                "kind": 0, "kind_name": "GLOBAL", "number": number,
                "length": len(program), "program": program,
                "identity": f"script.{number}", "source": source_script,
                "executable": True,
            }
            programs.append(item)
            global_scripts.append(item)
            next_program += 1
    if len({item["room"] for item in records}) != len(records):
        raise RuntimeError("generated cooked-room tables contain duplicate room numbers")
    if len({item["number"] for item in global_scripts}) != len(global_scripts):
        raise RuntimeError("generated global-script tables contain duplicate numbers")
    if global_states is None:
        global_states = bytes(4096)
    if global_owners is None:
        global_owners = bytes(len(global_states))
    if global_classes is None:
        global_classes = (0,) * len(global_states)
    if scenario_class_overlays:
        classes = list(global_classes)
        for object_id, mask in scenario_class_overlays:
            if object_id >= len(classes):
                raise RuntimeError(f"scenario class overlay object {object_id} is outside the source table")
            classes[object_id] |= mask
        global_classes = tuple(classes)
    if actor_facings is None:
        actor_facings = (180,) * 32
    if actor_positions is None:
        actor_positions = ((0, 0),) * 32
    if actor_walkboxes is None:
        actor_walkboxes = (0,) * 32
    hold_after_started_global_program = 0
    if hold_after_started_global_script is not None:
        match = next(
            (item for item in global_scripts
             if item["number"] == hold_after_started_global_script),
            None,
        )
        if match is None:
            raise RuntimeError("execution-gate global script is not generated")
        hold_after_started_global_program = int(match["id"])

    bank = args.first_bank
    data_lines = ["; Generated cooked-room bytes; never commit the source payloads."]
    for record_index, record in enumerate(records):
        segments = []
        raw = record["raw"]
        for segment_index, start in enumerate(range(0, len(raw), 0x8000)):
            # M24R-B owns LoROM bank 9 for its cold lifecycle closure. Keep
            # generated room payloads out of that bank; otherwise a later
            # code include silently overwrites the room-63 record used by the
            # asynchronous storage validator.
            if args.far_programs and bank == 9:
                bank = 10
            payload = raw[start:start + 0x8000]
            binary = args.binary_dir / f"record-{record_index}-segment-{segment_index}.bin"
            binary.write_bytes(payload)
            label = f"ScummV5_M23A_Record_{record_index}_Segment_{segment_index}"
            data_lines.extend((
                f".bank {bank}", ".org $8000", f"{label}:",
                f'    .incbin "{binary.resolve()}"',
            ))
            segments.append((label, len(payload), start))
            bank += 1
        record["segments"] = segments

    # Bank 9 is reserved by the M24R-B validator/lifecycle closure.  Keep all
    # generated data sections out of it, not just the large room payloads;
    # otherwise adding a room can move the initializer into bank 9 and the
    # later validator include silently overwrites it.
    if args.far_programs and bank == 9:
        bank = 10
    # Immutable header/directories are validation data, not executable code.
    # Keep them in the generated profile-data banks so the generic engine and
    # lookup routines retain bank-0 space.
    data_lines.extend((f".bank {bank}", ".org $8000"))
    for index, record in enumerate(records):
        prefix = record["raw"][:HEADER.size + len(record["scripts"]) * 96]
        data_lines.extend((f"ScummV5_M23A_Record_{index}_ExpectedDirectory:", rows(prefix)))
    if args.far_programs:
        for item in programs:
            if item["executable"]:
                data_lines.extend((
                    f"ScummV5_M23A_Program_{item['id']:02X}:",
                    rows(item["program"]),
                ))
    # Keep immutable navigation/object tables out of the executable-program
    # bank.  Poppy intentionally does not roll a label whose offset exceeds
    # $FFFF into a new LoROM bank, so every generated region is explicit.
    bank += 1
    if args.far_programs and bank == 9:
        bank = 10
    data_lines.extend((f".bank {bank}", ".org $8000"))
    for index, record in enumerate(records):
        if len(record["walkbox_flags"]) > 32:
            raise RuntimeError(
                f"room {record['room']} has {len(record['walkbox_flags'])} walkboxes; "
                "SNES putActor placement capacity is 32"
            )
        data_lines.extend((
            f"ScummV5_Matrix_Record_{index}_InitialFlags:",
            rows(record["walkbox_flags"]),
            f"ScummV5_PutActor_Record_{index}_Geometry:",
            rows(record["walkbox_geometry"]),
            f"ScummV5_Movement_Record_{index}_Routes:",
            rows(record["box_routes"]),
            f"ScummV5_Movement_Record_{index}_Portals:",
            rows(record["portals"]),
            f"ScummV5_Movement_Record_{index}_ObjectWalk:",
            rows(record["object_walk"]),
            f"ScummV5_Verb_Record_{index}_Count = ${len(record['verb_entries']):04X}",
            f"ScummV5_Verb_Record_{index}_Entries:",
            "    .word " + ",".join(
                f"${object_id:04X},${verb:04X},${offset:04X}"
                for object_id, verb, offset in record["verb_entries"]
            ) if record["verb_entries"] else "    .word $0000,$0000,$0000",
            f"ScummV5_SetState_Record_{index}_Objects:",
            rows(record["objects"]),
        ))
    # C16 is a bounded sparse runtime table.  A Fate profile can describe
    # more initially-classed objects than the runtime can hold at once; keep
    # Keep a small mutation reserve for authored setClass operations.  The
    # generated source order is object-id order, so the low-id startup/object
    # set stays stable and the bounded omission is explicit in the count.
    initial_class_items = [
        (index, value) for index, value in enumerate(global_classes) if value
    ][:0x01F0]
    data_lines.extend((
        "ScummV5_SetState_InitialStates:", rows(global_states),
        "ScummV5_ObjectOwner_InitialOwners:", rows(global_owners),
        "ScummV5_ObjectClass_InitialCount = $%04X" % len(initial_class_items),
        "ScummV5_ObjectClass_Initial:",
        *[f"    .word ${index:04X},${value & 0xFFFF:04X},${(value >> 16) & 0xFFFF:04X}"
          for index, value in initial_class_items],
        "ScummV5_GetActorFacing_InitialAngles:",
        "    .word " + ",".join(f"${value:04X}" for value in actor_facings),
        "ScummV5_GetActorWalkbox_InitialPositions:",
        "    .word " + ",".join(
            f"${x & 0xffff:04X},${y & 0xffff:04X}" for x, y in actor_positions
        ),
        "ScummV5_GetActorWalkbox_InitialBoxes:", rows(bytes(actor_walkboxes)),
    ))
    bank += 1
    if args.far_programs and bank == 9:
        bank = 10
    data_lines.extend((f".bank {bank}", ".org $8000"))
    # This source-bound initializer is executable profile data. Both the
    # ordinary bank-0 lifecycle and the relocated lifecycle call it with JSL;
    # it never parses or special-cases a title, room number, or script.
    data_lines.extend((
        "ScummV5_Matrix_LoadActiveRoom_Far:",
        "    sep #$20", "    .a8", "    rep #$10", "    .i16",
        "    lda #$00", "    sta.l SAME_SCUMM_MATRIX_BOX_COUNT",
        "    sta.l SAME_SCUMM_MATRIX_EXEC_COUNT",
        "    sta.l SAME_SCUMM_MATRIX_LAST_SUBOP",
        "    sta.l SAME_SCUMM_MATRIX_LAST_BOX",
        "    sta.l SAME_SCUMM_MATRIX_LAST_FLAGS",
        "    sta.l SAME_SCUMM_MATRIX_TRACE_COUNT",
        "    sta.l SAME_SCUMM_PUT_ACTOR_EXEC_COUNT",
        "    sta.l SAME_SCUMM_PUT_ACTOR_ACTOR",
        "    sta.l SAME_SCUMM_PUT_ACTOR_TRACE_COUNT",
        "    sta.l SAME_SCUMM_SETSTATE_LOCAL_COUNT",
        "    sta.l SAME_SCUMM_SETSTATE_BG_REDRAW",
        "    sta.l SAME_SCUMM_SETSTATE_DIRTY_COUNT",
        "    sta.l SAME_SCUMM_SETSTATE_DRAW_QUEUE_COUNT",
        "    sta.l SAME_SCUMM_SETSTATE_TRACE_COUNT",
        "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(records):
        data_lines.extend((
            f"    cmp #${index:02X}",
            f"    bne ScummV5_Matrix_LoadActiveRoom__next_{index}",
            f"    lda #${len(record['walkbox_flags']):02X}",
            "    sta.l SAME_SCUMM_MATRIX_BOX_COUNT",
            "    ldx #$0000",
            f"ScummV5_Matrix_LoadActiveRoom__copy_{index}:",
            "    .a8", "    .i16",
            f"    cpx #${len(record['walkbox_flags']):04X}",
            f"    bcs ScummV5_Matrix_LoadActiveRoom__done_{index}",
            f"    lda.l ScummV5_Matrix_Record_{index}_InitialFlags,x",
            "    sta.l SAME_SCUMM_MATRIX_BOX_FLAGS,x",
            "    inx",
            f"    bra ScummV5_Matrix_LoadActiveRoom__copy_{index}",
            f"ScummV5_Matrix_LoadActiveRoom__done_{index}:",
            "    .a8", "    .i16",
            "    rep #$20", "    .a16",
            "    ldx #$0000",
            f"ScummV5_PutActor_LoadActiveRoom__copy_{index}:",
            "    .a16", "    .i16",
            f"    cpx #${len(record['walkbox_geometry']):04X}",
            f"    bcs ScummV5_PutActor_LoadActiveRoom__done_{index}",
            f"    lda.l ScummV5_PutActor_Record_{index}_Geometry,x",
            "    sta.l SAME_SCUMM_PUT_ACTOR_BOXES,x",
            "    inx", "    inx",
            f"    bra ScummV5_PutActor_LoadActiveRoom__copy_{index}",
            f"ScummV5_PutActor_LoadActiveRoom__done_{index}:",
            "    sep #$20", "    .a8", "    ldx #$0000",
            f"ScummV5_SetState_LoadActiveRoom__copy_{index}:",
            "    .a8", "    .i16",
            f"    cpx #${len(record['objects']):04X}",
            f"    bcs ScummV5_SetState_LoadActiveRoom__done_{index}",
            f"    lda.l ScummV5_SetState_Record_{index}_Objects,x",
            "    sta.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS,x", "    inx",
            f"    bra ScummV5_SetState_LoadActiveRoom__copy_{index}",
            f"ScummV5_SetState_LoadActiveRoom__done_{index}:",
            "    .a8", "    .i16",
            "    lda #$%02X" % (len(record["objects"]) // 11),
            "    sta.l SAME_SCUMM_SETSTATE_LOCAL_COUNT",
            "    rtl",
            f"ScummV5_Matrix_LoadActiveRoom__next_{index}:", "    .a8", ".i16",
        ))
    data_lines.extend(("    rtl",))
    # Read-only profile-generated queries used by the semantic sentence and
    # movement closures.  All dispatch is selected by active record; no title,
    # room number, object number, verb, or route is embedded in engine code.
    data_lines.extend((
        "ScummV5_ObjectOwner_Query_Far:",
        "; Input X=u16 object; output A=u8 owner, carry set on success.",
        "    rep #$10", "    .i16", "    cpx #SCUMM_M23A_GLOBAL_OBJECT_COUNT",
        "    bcs ScummV5_ObjectOwner_Query_Far__fail", "    sep #$20", "    .a8",
        "    lda.l SAME_SCUMM_OBJECT_OWNERS,x", "    sec", "    rtl",
        "ScummV5_ObjectOwner_Query_Far__fail:", "    sep #$20", "    .a8",
        "    clc", "    rtl",
        "ScummV5_ObjectOwner_LoadInitial_Far:",
        "    rep #$30", "    .a16", "    .i16", "    ldx #$0000",
        "ScummV5_ObjectOwner_LoadInitial_Far__copy:",
        "    .a16", "    .i16",
        "    cpx #SCUMM_M23A_GLOBAL_OBJECT_COUNT", "    bcs ScummV5_ObjectOwner_LoadInitial_Far__done",
        "    sep #$20", "    .a8", "    lda.l ScummV5_ObjectOwner_InitialOwners,x",
        "    sta.l SAME_SCUMM_OBJECT_OWNERS,x", "    rep #$20", "    .a16", "    inx",
        "    bra ScummV5_ObjectOwner_LoadInitial_Far__copy",
        "ScummV5_ObjectOwner_LoadInitial_Far__done:",
        "    sep #$20", "    .a8", "    rtl",
    ))
    data_lines.extend((
        "ScummV5_ObjectClass_LoadInitial_Far:",
        "    rep #$30", "    .a16", "    .i16",
        "    lda #$0000", "    ldx #$0000",
        "ScummV5_ObjectClass_LoadInitial_Far__clear:", "    .a16", "    .i16",
        "    sta.l SAME_SCUMM_C16_RECORDS,x", "    inx", "    inx",
        "    cpx #$1000", "    bcc ScummV5_ObjectClass_LoadInitial_Far__clear",
        "    lda #$0000", "    sta.l SAME_SCUMM_C16_MASK_OFFSET",
        "    sta.l SAME_SCUMM_C16_RECORD_OFFSET",
        "ScummV5_ObjectClass_LoadInitial_Far__copy:",
        "    .a16", "    .i16",
        "    lda.l SAME_SCUMM_C16_MASK_OFFSET",
        "    cmp #(ScummV5_ObjectClass_InitialCount * 6)",
        "    bcs ScummV5_ObjectClass_LoadInitial_Far__done",
        "    tax", "    lda.l ScummV5_ObjectClass_Initial,x",
        "    pha", "    lda.l SAME_SCUMM_C16_RECORD_OFFSET", "    tax",
        "    pla", "    sta.l SAME_SCUMM_C16_RECORDS+2,x",
        "    lda #$0001", "    sta.l SAME_SCUMM_C16_RECORDS,x",
        "    lda.l SAME_SCUMM_C16_MASK_OFFSET", "    clc", "    adc #$0002",
        "    tax", "    lda.l ScummV5_ObjectClass_Initial,x",
        "    pha", "    lda.l SAME_SCUMM_C16_RECORD_OFFSET", "    tax", "    pla",
        "    sta.l SAME_SCUMM_C16_RECORDS+4,x",
        "    lda.l SAME_SCUMM_C16_MASK_OFFSET", "    clc", "    adc #$0004",
        "    tax", "    lda.l ScummV5_ObjectClass_Initial,x",
        "    pha", "    lda.l SAME_SCUMM_C16_RECORD_OFFSET", "    tax", "    pla",
        "    sta.l SAME_SCUMM_C16_RECORDS+6,x",
        "    lda.l SAME_SCUMM_C16_MASK_OFFSET", "    clc", "    adc #$0006",
        "    sta.l SAME_SCUMM_C16_MASK_OFFSET",
        "    lda.l SAME_SCUMM_C16_RECORD_OFFSET", "    clc", "    adc #$0008",
        "    sta.l SAME_SCUMM_C16_RECORD_OFFSET",
        "    bra ScummV5_ObjectClass_LoadInitial_Far__copy",
        "ScummV5_ObjectClass_LoadInitial_Far__done:",
        "    sep #$20", "    .a8", "    lda #$01", "    sta.l SAME_SCUMM_C16_INITIALIZED", "    rtl",
        "ScummV5_ObjectClass_ApplyScenarioOverlay_Far:",
        "    sep #$20", "    .a8",
        f"    lda #${len(scenario_class_overlays):02X}",
        "    beq ScummV5_ObjectClass_ApplyScenarioOverlay_Far__done",
    ))
    for overlay_index, (object_id, mask) in enumerate(scenario_class_overlays):
        data_lines.extend((
            "    rep #$20", "    .a16", f"    lda #${object_id:04X}",
            "    sta.l SAME_SCUMM_C16_OBJECT", "    jsl ScummV5_C16_FindRecord_Far",
            "    lda.l SAME_SCUMM_C16_RECORD_OFFSET", "    cmp #$FFFF",
            f"    beq ScummV5_ObjectClass_ApplyScenarioOverlay_Far__next_{overlay_index}",
            "    tax", f"    lda.l SAME_SCUMM_C16_RECORDS+4,x", "    ora #${:04X}".format(mask & 0xFFFF),
            "    sta.l SAME_SCUMM_C16_RECORDS+4,x", f"    lda.l SAME_SCUMM_C16_RECORDS+6,x",
            "    ora #${:04X}".format((mask >> 16) & 0xFFFF), "    sta.l SAME_SCUMM_C16_RECORDS+6,x",
            f"ScummV5_ObjectClass_ApplyScenarioOverlay_Far__next_{overlay_index}:",
        ))
    data_lines.extend((
        "ScummV5_ObjectClass_ApplyScenarioOverlay_Far__done:",
        "    sep #$20", "    .a8", "    rtl",
    ))
    data_lines.extend((
        "ScummV5_Bit_ApplyScenarioOverlay_Far:",
        "    php", "    rep #$30", "    .a16", "    .i16",
        f"    lda #${len(scenario_bit_overlays):02X}",
        "    beq ScummV5_Bit_ApplyScenarioOverlay_Far__done",
    ))
    for bit in scenario_bit_overlays:
        byte_index, bit_index = divmod(bit, 8)
        data_lines.extend((
            f"    ldx #${byte_index:04X}",
            "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_C7_BITS,x",
            f"    ora #${1 << bit_index:02X}", "    sta.l SAME_SCUMM_C7_BITS,x",
        ))
    data_lines.extend((
        "ScummV5_Bit_ApplyScenarioOverlay_Far__done:",
        "    plp", "    rtl",
        "ScummV5_ObjectState_ApplyScenarioOverlay_Far:", "    sep #$20", "    .a8",
        f"    lda #${len(scenario_state_overlays):02X}",
        "    beq ScummV5_ObjectState_ApplyScenarioOverlay_Far__done",
    ))
    for object_id, state in scenario_state_overlays:
        data_lines.extend((f"    lda #${state:02X}",
                           f"    sta.l SAME_SCUMM_OBJECT_STATES+${object_id:04X}"))
    data_lines.extend((
        "ScummV5_ObjectState_ApplyScenarioOverlay_Far__done:", "    rtl",
        "ScummV5_Movement_NextBox_Far:",
        "; Inputs scratch source/destination; output A=u8 next box, carry set.",
        "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(records):
        count = len(record["walkbox_flags"])
        data_lines.extend((
            f"    cmp #${index:02X}", f"    beq ScummV5_Movement_NextBox_Far__match_{index}",
            f"    brl ScummV5_Movement_NextBox_Far__next_{index}",
            f"ScummV5_Movement_NextBox_Far__match_{index}:",
            "    .a8",
            "    lda.l SAME_SCUMM_MOVE_ROUTE_SOURCE", f"    cmp #${count:02X}",
            f"    bcc ScummV5_Movement_NextBox_Far__source_ok_{index}",
            "    brl ScummV5_Movement_NextBox_Far__fail",
            f"ScummV5_Movement_NextBox_Far__source_ok_{index}:",
            "    .a8",
            "    lda.l SAME_SCUMM_MOVE_ROUTE_DEST", f"    cmp #${count:02X}",
            f"    bcc ScummV5_Movement_NextBox_Far__dest_ok_{index}",
            "    brl ScummV5_Movement_NextBox_Far__fail",
            f"ScummV5_Movement_NextBox_Far__dest_ok_{index}:",
            "    rep #$20", "    .a16", "    and #$00FF",
            "    sta.l SAME_SCUMM_MOVE_ROUTE_DEST",
            "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_MOVE_ROUTE_SOURCE",
            "    rep #$20", "    .a16", "    and #$00FF",
            f"    sta.l SAME_SCUMM_MOVE_TEMP", f"    lda #${count:04X}",
            "    sta.l SAME_SCUMM_MOVE_TEMP2", "    lda #$0000",
            f"ScummV5_Movement_NextBox_Far__mul_{index}:",
            "    clc", "    adc.l SAME_SCUMM_MOVE_TEMP", "    pha",
            "    lda.l SAME_SCUMM_MOVE_TEMP2", "    dec", "    sta.l SAME_SCUMM_MOVE_TEMP2",
            f"    beq ScummV5_Movement_NextBox_Far__mul_done_{index}", "    pla",
            f"    bra ScummV5_Movement_NextBox_Far__mul_{index}",
            f"ScummV5_Movement_NextBox_Far__mul_done_{index}:", "    pla",
            "    clc", "    adc.l SAME_SCUMM_MOVE_ROUTE_DEST", "    tax",
            "    sep #$20", "    .a8", f"    lda.l ScummV5_Movement_Record_{index}_Routes,x",
            "    cmp #$FF", f"    bne ScummV5_Movement_NextBox_Far__success_{index}",
            "    brl ScummV5_Movement_NextBox_Far__fail",
            f"ScummV5_Movement_NextBox_Far__success_{index}:", "    sec", "    rtl",
            f"ScummV5_Movement_NextBox_Far__next_{index}:", "    .a8",
        ))
    data_lines.extend(("ScummV5_Movement_NextBox_Far__fail:", "    clc", "    rtl"))
    data_lines.extend((
        "ScummV5_Movement_Portal_Far:",
        "; Inputs route source and route-next; publishes canonical shared edge.",
        "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(records):
        count = len(record["walkbox_flags"])
        data_lines.extend((
            f"    cmp #${index:02X}", f"    beq ScummV5_Movement_Portal_Far__match_{index}",
            f"    brl ScummV5_Movement_Portal_Far__next_{index}",
            f"ScummV5_Movement_Portal_Far__match_{index}:",
            "    .a8",
            "    lda.l SAME_SCUMM_MOVE_ROUTE_SOURCE", f"    cmp #${count:02X}",
            f"    bcc ScummV5_Movement_Portal_Far__source_ok_{index}",
            "    brl ScummV5_Movement_Portal_Far__fail",
            f"ScummV5_Movement_Portal_Far__source_ok_{index}:",
            "    .a8",
            "    lda.l SAME_SCUMM_MOVE_ROUTE_NEXT", f"    cmp #${count:02X}",
            f"    bcc ScummV5_Movement_Portal_Far__next_ok_{index}",
            "    brl ScummV5_Movement_Portal_Far__fail",
            f"ScummV5_Movement_Portal_Far__next_ok_{index}:",
            "    rep #$20", "    .a16", "    and #$00FF",
            "    sta.l SAME_SCUMM_MOVE_ROUTE_DEST",
            "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_MOVE_ROUTE_SOURCE",
            "    rep #$20", "    .a16", "    and #$00FF", "    sta.l SAME_SCUMM_MOVE_TEMP",
            f"    lda #${count:04X}", "    sta.l SAME_SCUMM_MOVE_TEMP2", "    lda #$0000",
            f"ScummV5_Movement_Portal_Far__mul_{index}:",
            "    clc", "    adc.l SAME_SCUMM_MOVE_TEMP", "    pha",
            "    lda.l SAME_SCUMM_MOVE_TEMP2", "    dec", "    sta.l SAME_SCUMM_MOVE_TEMP2",
            f"    beq ScummV5_Movement_Portal_Far__mul_done_{index}", "    pla",
            f"    bra ScummV5_Movement_Portal_Far__mul_{index}",
            f"ScummV5_Movement_Portal_Far__mul_done_{index}:", "    pla",
            "    clc", "    adc.l SAME_SCUMM_MOVE_ROUTE_DEST",
            "    sta.l SAME_SCUMM_MOVE_TEMP",
            "    asl", "    asl", "    asl", "    sec", "    sbc.l SAME_SCUMM_MOVE_TEMP",
            "    tax", "    sep #$20", "    .a8",
            f"    lda.l ScummV5_Movement_Record_{index}_Portals,x",
            "    sta.l SAME_SCUMM_MOVE_PORTAL_TYPE", f"    bne ScummV5_Movement_Portal_Far__success_{index}",
            "    brl ScummV5_Movement_Portal_Far__fail",
            f"ScummV5_Movement_Portal_Far__success_{index}:",
            "    rep #$20", "    .a16",
            # Keep the far-bank relocation on the base symbol.  Poppy 0.7
            # currently drops the bank byte from ``far_label+N,x`` operands,
            # so advance X to each packed field instead of applying an
            # arithmetic expression to the long label.
            "    inx",
            f"    lda.l ScummV5_Movement_Record_{index}_Portals,x", "    sta.l SAME_SCUMM_MOVE_PORTAL_FIXED",
            "    inx", "    inx",
            f"    lda.l ScummV5_Movement_Record_{index}_Portals,x", "    sta.l SAME_SCUMM_MOVE_PORTAL_LOW",
            "    inx", "    inx",
            f"    lda.l ScummV5_Movement_Record_{index}_Portals,x", "    sta.l SAME_SCUMM_MOVE_PORTAL_HIGH",
            "    sep #$20", "    .a8", "    sec", "    rtl",
            f"ScummV5_Movement_Portal_Far__next_{index}:", "    .a8",
        ))
    data_lines.extend(("ScummV5_Movement_Portal_Far__fail:", "    sep #$20", "    .a8", "    clc", "    rtl"))
    data_lines.extend((
        "ScummV5_Movement_ObjectWalk_Far:",
        "; Input object in scratch; output walk x/y/direction in scratch, carry set.",
        "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(records):
        data_lines.extend((
            f"    cmp #${index:02X}", f"    beq ScummV5_Movement_ObjectWalk_Far__match_{index}",
            f"    brl ScummV5_Movement_ObjectWalk_Far__next_{index}",
            f"ScummV5_Movement_ObjectWalk_Far__match_{index}:",
            "    rep #$30", "    .a16", "    .i16", "    ldx #$0000",
            f"ScummV5_Movement_ObjectWalk_Far__scan_{index}:",
            "    .a16", "    .i16",
            f"    cpx #${len(record['object_walk']):04X}",
            f"    bcc ScummV5_Movement_ObjectWalk_Far__scan_ok_{index}",
            "    brl ScummV5_Movement_ObjectWalk_Far__fail",
            f"ScummV5_Movement_ObjectWalk_Far__scan_ok_{index}:",
            "    .a16", "    .i16",
            f"    lda.l ScummV5_Movement_Record_{index}_ObjectWalk,x",
            "    cmp.l SAME_SCUMM_MOVE_OBJECT", f"    beq ScummV5_Movement_ObjectWalk_Far__found_{index}",
            "    txa", "    clc", "    adc #$000C", "    tax",
            f"    bra ScummV5_Movement_ObjectWalk_Far__scan_{index}",
            f"ScummV5_Movement_ObjectWalk_Far__found_{index}:",
            "    inx", "    inx",
            f"    lda.l ScummV5_Movement_Record_{index}_ObjectWalk,x",
            "    sta.l SAME_SCUMM_MOVE_REQUEST_X",
            "    inx", "    inx",
            f"    lda.l ScummV5_Movement_Record_{index}_ObjectWalk,x",
            "    sta.l SAME_SCUMM_MOVE_REQUEST_Y", "    sep #$20", "    .a8",
            "    inx", "    inx",
            f"    lda.l ScummV5_Movement_Record_{index}_ObjectWalk,x",
            "    sta.l SAME_SCUMM_MOVE_QUERY_DIR",
            "    inx", "    rep #$20", "    .a16",
            f"    lda.l ScummV5_Movement_Record_{index}_ObjectWalk,x",
            "    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_X",
            "    inx", "    inx",
            f"    lda.l ScummV5_Movement_Record_{index}_ObjectWalk,x",
            "    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_Y",
            "    inx", "    inx", "    sep #$20", "    .a8",
            f"    lda.l ScummV5_Movement_Record_{index}_ObjectWalk,x",
            "    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_BOX", "    sec", "    rtl",
            f"ScummV5_Movement_ObjectWalk_Far__next_{index}:", "    .a8",
        ))
    data_lines.extend(("ScummV5_Movement_ObjectWalk_Far__fail:", "    sep #$20", "    .a8", "    clc", "    rtl"))
    data_lines.extend((
        "ScummV5_Verb_Query_Far:",
        "; Inputs object/verb scratch; output u16 OBCD-relative entry in result.",
        "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
        "    sta.l $7E5465",
        "    rep #$20", "    .a16", "    lda.l SAME_SCUMM_VERB_OBJECT", "    sta.l $7E5466",
        "    lda.l SAME_SCUMM_VERB_ID", "    sta.l $7E5468",
        # Diagnostic only: use the first generated table, which is always
        # present even for a one-room scenario fixture.  The actual lookup
        # below dispatches by active record and never relies on this probe.
        f"    lda.l ScummV5_Verb_Record_0_Entries", "    sta.l $7E546A",
        "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(records):
        entries = record["verb_entries"]
        lookup = [
            f"    cmp #${index:02X}", f"    beq ScummV5_Verb_Query_Far__match_{index}",
            f"    brl ScummV5_Verb_Query_Far__next_{index}",
            f"ScummV5_Verb_Query_Far__match_{index}:",
            "    rep #$30", "    .a16", "    .i16", "    ldx #$0000",
        ]
        for entry_index, (object_id, verb, offset) in enumerate(entries):
            skip = f"ScummV5_Verb_Query_Far__skip_{index}_{entry_index}"
            found = f"ScummV5_Verb_Query_Far__found_{index}_{entry_index}"
            nxt = f"ScummV5_Verb_Query_Far__entry_{index}_{entry_index + 1}"
            lookup.extend((
                f"    lda #${object_id:04X}", "    cmp.l SAME_SCUMM_VERB_OBJECT",
                f"    bne {skip}", f"    lda #${verb:04X}",
                "    cmp.l SAME_SCUMM_VERB_ID", f"    beq {found}",
                "    cmp #$00FF", f"    beq {found}",
                f"{skip}:", "    .a16", f"    bra {nxt}", f"{found}:", "    .a16",
                f"    lda #${offset:04X}", "    sta.l SAME_SCUMM_VERB_RESULT",
                "    sec", "    rtl", f"{nxt}:", "    .a16",
            ))
        lookup.extend((
            "    brl ScummV5_Verb_Query_Far__absent",
            f"ScummV5_Verb_Query_Far__next_{index}:",
            # The scan leaves A holding the last verb-table value.  Reload
            # the room generation's active record before selecting the next
            # table; otherwise a miss in an earlier room can dispatch based
            # on arbitrary table data instead of the current room.
            "    sep #$20", "    .a8",
            "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
            "    rep #$20", "    .a16",
        ))
        data_lines.extend(lookup)
    data_lines.extend((
        "ScummV5_Verb_Query_Far__absent:", "    .a16", "    lda #$0000",
        "    sta.l SAME_SCUMM_VERB_RESULT", "    sec", "    rtl",
    ))
    data_lines.extend((
        "ScummV5_ObjectProgram_Resolve_Far:",
        "; Inputs object/verb scratch; output A=u8 OBCD program, entry in verb result.",
        "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
        "    sta.l $7E545C",
        "    rep #$20",
        "    .a16",
        "    lda.l SAME_SCUMM_VERB_OBJECT",
        "    sta.l $7E545D",
        "    sep #$20",
        "    .a8",
        "    jsl ScummV5_Verb_Query_Far", "    bcs ScummV5_ObjectProgram_Resolve_Far__verb_found",
        "    brl ScummV5_ObjectProgram_Resolve_Far__fail",
        "ScummV5_ObjectProgram_Resolve_Far__verb_found:",
        "    rep #$20",
        "    .a16",
        "    lda.l SAME_SCUMM_VERB_RESULT",
        "    sta.l $7E5461",
        "    sep #$20",
        "    .a8",
        "    rep #$20", "    .a16", "    lda.l SAME_SCUMM_VERB_RESULT",
        "    bne ScummV5_ObjectProgram_Resolve_Far__entry_found",
        "    brl ScummV5_ObjectProgram_Resolve_Far__fail16",
        "ScummV5_ObjectProgram_Resolve_Far__entry_found:",
        "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(records):
        data_lines.extend((
            f"    cmp #${index:02X}",
            f"    bne ScummV5_ObjectProgram_Resolve_Far__record_next_{index}",
            f"    brl ScummV5_ObjectProgram_Resolve_Far__record_{index}",
            f"ScummV5_ObjectProgram_Resolve_Far__record_next_{index}:", "    .a8",
        ))
    # The source-sized object table can exceed a short branch range even in a
    # focused scenario. This cold resolver therefore always uses a long
    # failure transfer.
    data_lines.extend(("    brl ScummV5_ObjectProgram_Resolve_Far__fail",))
    for index, record in enumerate(records):
        data_lines.extend((
            f"ScummV5_ObjectProgram_Resolve_Far__record_{index}:",
            "    rep #$20", "    .a16", "    lda.l SAME_SCUMM_VERB_OBJECT",
        ))
        for item in record["object_programs"]:
            if not item["executable"]:
                continue
            data_lines.extend((
                f"    cmp #${item['number']:04X}",
                f"    beq ScummV5_ObjectProgram_Resolve_Far__object_{item['id']:02X}",
            ))
        # Room/object dispatch tables can make this cold failure path larger
        # than a short-branch range when a real room is joined to a fixture.
        data_lines.extend(("    brl ScummV5_ObjectProgram_Resolve_Far__fail16",))
        for item in record["object_programs"]:
            if not item["executable"]:
                continue
            data_lines.extend((
                f"ScummV5_ObjectProgram_Resolve_Far__object_{item['id']:02X}:",
                "    sep #$20", "    .a8", f"    lda #${item['id']:02X}",
                "    sta.l $7E5460",
                "    sec", "    rtl",
            ))
    data_lines.extend((
        "ScummV5_ObjectProgram_Resolve_Far__fail16:", "    sep #$20", "    .a8",
        "ScummV5_ObjectProgram_Resolve_Far__fail:", "    clc", "    rtl",
    ))
    data_lines.extend((
        "ScummV5_SetState_Reset_Far:",
        "    rep #$30", "    .a16", "    .i16", "    lda #$0000",
        "    sta.l SAME_SCUMM_SETSTATE_OBJECT",
        "    sta.l SAME_SCUMM_SETSTATE_PC_BEFORE",
        "    sta.l SAME_SCUMM_SETSTATE_PC_AFTER", "    ldx #$0000",
        "ScummV5_SetState_Reset_Far__copy:",
        "    .a16", "    .i16",
        f"    cpx #${len(global_states):04X}",
        "    bcs ScummV5_SetState_Reset_Far__tail",
        "    sep #$20", "    .a8",
        "    lda.l ScummV5_SetState_InitialStates,x",
        "    sta.l SAME_SCUMM_OBJECT_STATES,x", "    rep #$20", "    .a16",
        "    inx", "    bra ScummV5_SetState_Reset_Far__copy",
        "ScummV5_SetState_Reset_Far__tail:",
        "    sep #$20", "    .a8", "    lda #$00",
        "ScummV5_SetState_Reset_Far__clear:",
        "    .a8", "    .i16",
        "    cpx #$1000", "    bcs ScummV5_SetState_Reset_Far__done",
        "    sta.l SAME_SCUMM_OBJECT_STATES,x", "    inx",
        "    bra ScummV5_SetState_Reset_Far__clear",
        "ScummV5_SetState_Reset_Far__done:",
        "    .a8", "    .i16",
        "    sta.l SAME_SCUMM_SETSTATE_VALUE",
        "    sta.l SAME_SCUMM_SETSTATE_LOCAL_FOUND",
        "    sta.l SAME_SCUMM_SETSTATE_BG_REDRAW",
        "    sta.l SAME_SCUMM_SETSTATE_EXEC_COUNT",
        "    sta.l SAME_SCUMM_SETSTATE_LOCAL_COUNT",
        "    sta.l SAME_SCUMM_SETSTATE_DIRTY_COUNT",
        "    sta.l SAME_SCUMM_SETSTATE_DRAW_QUEUE_COUNT",
        "    sta.l SAME_SCUMM_GET_FACING_EXEC_COUNT",
        "    sta.l SAME_SCUMM_GET_FACING_TRACE_COUNT",
        "    sta.l SAME_SCUMM_GET_FACING_STAGE",
        "    rep #$30", "    .a16", "    .i16", "    ldx #$0000",
        "ScummV5_GetActorFacing_Reset_Far__copy:",
        "    .a16", "    .i16",
        "    lda.l ScummV5_GetActorFacing_InitialAngles,x",
        "    sta.l SAME_SCUMM_ACTOR_FACINGS,x", "    inx", "    inx",
        "    cpx #$0040", "    bcc ScummV5_GetActorFacing_Reset_Far__copy",
        "    ldx #$0000",
        "ScummV5_GetActorWalkbox_Reset_Far__copy:",
        "    .a16", ".i16",
        "    lda.l ScummV5_GetActorWalkbox_InitialPositions,x",
        "    sta.l SAME_SCUMM_C31_POSITIONS,x", "    inx", "    inx",
        "    cpx #$0080", "    bcc ScummV5_GetActorWalkbox_Reset_Far__copy",
        "    sep #$20", "    .a8",
        "    ldx #$0000",
        "ScummV5_GetActorWalkbox_Reset_Far__copy_boxes:",
        "    .a8", ".i16",
        "    lda.l ScummV5_GetActorWalkbox_InitialBoxes,x",
        "    sta.l SAME_SCUMM_PUT_ACTOR_WALKBOX,x",
        "    sta.l SAME_SCUMM_PUT_ACTOR_DESTBOX,x", "    inx",
        "    cpx #$0020", "    bcc ScummV5_GetActorWalkbox_Reset_Far__copy_boxes",
        "    rep #$20", "    .a16", "    lda #$0000", "    ldx #$0000",
        "ScummV5_Movement_Reset_Far__clear:",
        "    sep #$20", "    .a8", "    sta.l SAME_SCUMM_MOVE_STATE,x", "    inx",
        "    cpx #SAME_SCUMM_MOVE_STATE_SIZE", "    bcc ScummV5_Movement_Reset_Far__clear",
        "    rep #$20", "    .a16", "    lda #$FFFF", "    ldx #$0000",
        "ScummV5_Movement_Reset_Far__inactive_destinations:",
        "    .a16", "    .i16",
        "    sta.l SAME_SCUMM_PUT_ACTOR_DEST_X,x", "    inx", "    inx",
        "    cpx #$0040", "    bcc ScummV5_Movement_Reset_Far__inactive_destinations",
        "    lda #$01", "    sta.l SAME_SCUMM_C31_INITIALIZED",
        f"    lda #${len(global_states) & 0xff:02X}",
        "    sta.l SAME_SCUMM_OBJECT_COUNT",
        f"    lda #${len(global_states) >> 8:02X}",
        "    sta.l SAME_SCUMM_OBJECT_COUNT+1", "    rtl",
    ))
    bank += 1
    if args.far_programs and bank == 9:
        bank = 10
    # The SAME-owned cold helper closure follows this include. Give it a
    # fresh bank rather than relying on implicit overflow from generated code.
    data_lines.extend((f".bank {bank}", ".org $8000"))

    lines = [
        "; Generated by tools/generate_snes_cooked_rooms.py.",
        f"SCUMM_V5_NUM_GLOBAL_SCRIPTS = ${num_global_scripts:04X}",
        f"SCUMM_V5_HOLD_AFTER_STARTED_GLOBAL_ENABLED = ${1 if hold_after_started_global_script is not None else 0:02X}",
        f"SCUMM_V5_HOLD_AFTER_STARTED_GLOBAL_SCRIPT = ${(hold_after_started_global_script or 0):02X}",
        f"SCUMM_V5_HOLD_AFTER_STARTED_GLOBAL_PROGRAM = ${hold_after_started_global_program:02X}",
        f"SCUMM_M23A_ROOM_COUNT = ${len(records):02X}",
        f"SCUMM_M23A_PROGRAM_FIRST = ${programs[0]['id']:02X}",
        f"SCUMM_M23A_PROGRAM_COUNT = ${len(programs):02X}",
        f"SCUMM_M23A_LAST_BANK = ${bank:02X}",
        f"SCUMM_M23A_GLOBAL_OBJECT_COUNT = ${len(global_states):04X}",
        "ScummV5_M23A_RoomNumbers:",
        rows(bytes(item["room"] for item in records)),
        "ScummV5_M23A_RoomFlags:",
        rows(bytes(item["flags"] for item in records)),
        "ScummV5_M23A_RoomScriptCounts:",
        rows(bytes(len(item["scripts"]) for item in records)),
        "ScummV5_M23A_RoomEntryPrograms:",
        rows(bytes(item["entry"] for item in records)),
        "ScummV5_M23A_RoomExitPrograms:",
        rows(bytes(item["exit"] for item in records)),
        "ScummV5_M23A_RoomLocalCounts:",
        rows(bytes(len(item["locals"]) for item in records)),
        "ScummV5_M23A_RoomExecutableLocalCounts:",
        rows(bytes(len(item["executable_locals"]) for item in records)),
        "ScummV5_M23A_RoomDescriptorChecksums:",
        "    .word " + ",".join(
            f"${sum(x['id'] + x['kind'] + (x['number'] & 0xFF) + x['length'] for x in item['scripts']) & 0xffff:04X}"
            for item in records
        ),
    ]
    for record_index, record in enumerate(records):
        locals_ = record["executable_locals"]
        lines.extend((
            f"; Complete executable-local directory for room {record['room']}.",
            f"ScummV5_M23A_RoomLocalNumbers_{record_index}:",
            rows(bytes(item["number"] for item in locals_)) if locals_ else "    .byte $00",
            f"ScummV5_M23A_RoomLocalIndices_{record_index}:",
            "    .word " + ",".join(
                f"${item['number'] - num_global_scripts:04X}" for item in locals_
            ) if locals_ else "    .word $0000",
            f"ScummV5_M23A_RoomLocalPrograms_{record_index}:",
            rows(bytes(item["id"] for item in locals_)) if locals_ else "    .byte $00",
        ))
    for item in programs:
        if item["executable"] and not args.far_programs:
            lines.extend((f"ScummV5_M23A_Program_{item['id']:02X}:", rows(item["program"])))

    # Generated lookup routines keep title/resource identities out of the core.
    lines.extend((
        "ScummV5_M23A_FindRoom:",
        "    sep #$20", "    .a8", "    rep #$10", "    .i16",
        "    ldx #$0000", "ScummV5_M23A_FindRoom__loop:", "    .a8", "    .i16",
        "    cmp.l ScummV5_M23A_RoomNumbers,x",
        "    beq ScummV5_M23A_FindRoom__found", "    inx",
        "    cpx #SCUMM_M23A_ROOM_COUNT", "    bcc ScummV5_M23A_FindRoom__loop",
        "    sec", "    rts", "ScummV5_M23A_FindRoom__found:",
        "    txa", "    clc", "    rts",
    ))
    size_lines = ["    sep #$20", "    .a8"]
    for item in programs:
        size_lines.extend((
            f"    cmp #${item['id']:02X}", f"    bne ScummV5_M23A_GetProgramSize__next_{item['id']:02X}",
            "    rep #$20", "    .a16", f"    lda #${item['length']:04X}",
            "    sec", "    " + ("rtl" if args.far_programs else "rts"),
            f"ScummV5_M23A_GetProgramSize__next_{item['id']:02X}:", "    .a8",
        ))
    size_lines.extend(("    clc", "    " + ("rtl" if args.far_programs else "rts")))
    if args.far_programs:
        lines.extend(("ScummV5_M23A_GetProgramSize:",
                      "    jsl ScummV5_M23A_GetProgramSize_Far", "    rts"))
        data_lines.extend(("ScummV5_M23A_GetProgramSize_Far:", *size_lines))
    else:
        lines.extend(("ScummV5_M23A_GetProgramSize:", *size_lines))
    # Far-callable twin used by cold production scheduler helpers.  Both
    # resolvers are generated from the identical profile-owned directory.
    data_lines.extend((
        "ScummV5_M23A_ResolveGlobalScript_Far:",
        "; Input A=u8 script number; output A=program and carry set.",
        "    sep #$20", "    .a8",
    ))
    for item in global_scripts:
        data_lines.extend((
            f"    cmp #${item['number'] & 0xff:02X}",
            f"    bne ScummV5_M23A_ResolveGlobalScript_Far__next_{item['id']:02X}",
            f"    lda #${item['id']:02X}", "    sec", "    rtl",
            f"ScummV5_M23A_ResolveGlobalScript_Far__next_{item['id']:02X}:", "    .a8",
        ))
    data_lines.extend(("    clc", "    rtl"))
    lines.extend((
        "ScummV5_M23A_FetchProgramByte:",
        "    sep #$20", "    .a8",
    ))
    for item in programs:
        if item["executable"]:
            lines.extend((
                f"    cmp #${item['id']:02X}", f"    bne ScummV5_M23A_FetchProgramByte__next_{item['id']:02X}",
                f"    lda.l ScummV5_M23A_Program_{item['id']:02X},x", "    clc", "    rts",
                f"ScummV5_M23A_FetchProgramByte__next_{item['id']:02X}:", "    .a8",
            ))
    lines.extend(("    sec", "    rts"))

    if args.far_programs:
        lines.extend((
            "ScummV5_M23A_ResolveGlobalScript:",
            "; Cold profile-global lookup is owned by the generated far bank.",
            "    jsl ScummV5_M23A_ResolveGlobalScript_Far", "    rts",
        ))
    else:
        lines.extend((
            "ScummV5_M23A_ResolveGlobalScript:",
            "; Input: A=script number; output A=profile-generated program with carry set.",
            "    sep #$20", "    .a8",
        ))
        for item in global_scripts:
            lines.extend((
                f"    cmp #${item['number'] & 0xff:02X}",
                f"    bne ScummV5_M23A_ResolveGlobalScript__next_{item['id']:02X}",
                f"    lda #${item['id']:02X}", "    sec", "    rts",
                f"ScummV5_M23A_ResolveGlobalScript__next_{item['id']:02X}:", "    .a8",
            ))
        lines.extend(("    clc", "    rts"))

    far_local_resolver = args.far_programs and any(
        record["executable_locals"] for record in records
    )
    local_lines = [
        (
            "ScummV5_M23A_ResolveLocalScript_Far:"
            if far_local_resolver
            else "ScummV5_M23A_ResolveLocalScript:"
        ),
        "; Input: A=script number, active record; output A=program and carry set.",
        "    sep #$20", "    .a8",
    ]
    local_return = "rtl" if far_local_resolver else "rts"
    for record_index, record in enumerate(records):
        if not record["executable_locals"]:
            continue
        local_lines.extend((
            "    pha", "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
            f"    cmp #${record_index:02X}", f"    bne ScummV5_M23A_ResolveLocalScript__dispatch_{record_index}",
            "    pla", f"    jmp ScummV5_M23A_ResolveLocalScript__record_{record_index}",
            f"ScummV5_M23A_ResolveLocalScript__dispatch_{record_index}:", "    .a8", "    pla",
        ))
    local_lines.extend(("    clc", f"    {local_return}"))
    for record_index, record in enumerate(records):
        if not record["executable_locals"]:
            continue
        local_lines.extend((f"ScummV5_M23A_ResolveLocalScript__record_{record_index}:", "    .a8"))
        for local in record["executable_locals"]:
            local_lines.extend((f"    cmp #${local['number'] & 0xff:02X}",
                                f"    bne ScummV5_M23A_ResolveLocalScript__next_{local['id']:02X}",
                                f"    lda #${local['id']:02X}", "    sec", f"    {local_return}",
                                f"ScummV5_M23A_ResolveLocalScript__next_{local['id']:02X}:", "    .a8"))
        local_lines.extend(("    clc", f"    {local_return}"))
    if far_local_resolver:
        lines.extend((
            "ScummV5_M23A_ResolveLocalScript:",
            "    sep #$20", "    .a8", "    sta.l SAME_SCUMM_VERB_OBJECT",
            "    jsl ScummV5_M23A_ResolveLocalScript_Far",
            "    bcc ScummV5_M23A_ResolveLocalScript__diagnostic_fail",
            "    sta.l SAME_SCUMM_MOVE_QUERY_DIR", "    sec", "    rts",
            "ScummV5_M23A_ResolveLocalScript__diagnostic_fail:",
            "    .a8",
            "    lda #$FF", "    sta.l SAME_SCUMM_MOVE_QUERY_DIR", "    clc", "    rts",
        ))
        data_lines.extend(local_lines)
    else:
        lines.extend(local_lines)

    # Record validators compare the immutable header/directory byte-for-byte,
    # then checksum the complete pre-trailer record while excluding mutable
    # checksum fields 32..37 exactly as the host encoder does.
    validator_lines = ["ScummV5_M23A_ValidateRecord:", "    sep #$20", "    .a8"]
    for index in range(len(records)):
        validator_lines.extend((f"    cmp #${index:02X}", f"    bne ScummV5_M23A_ValidateRecord__dispatch_{index}",
                                f"    jmp ScummV5_M23A_ValidateRecord__{index}",
                                f"ScummV5_M23A_ValidateRecord__dispatch_{index}:", "    .a8"))
    validator_lines.extend(("    sec", "    rts"))
    for index, record in enumerate(records):
        directory_size = HEADER.size + len(record["scripts"]) * 96
        first_label = record["segments"][0][0]
        validator_lines.extend((
            f"ScummV5_M23A_ValidateRecord__{index}:",
            "    rep #$30", "    .a16", "    .i16", "    ldx #$0000",
            f"ScummV5_M23A_ValidateRecord__{index}_directory:",
            "    sep #$20", "    .a8", f"    lda.l {first_label},x",
            f"    cmp.l ScummV5_M23A_Record_{index}_ExpectedDirectory,x",
            f"    beq ScummV5_M23A_ValidateRecord__{index}_directory_ok",
            f"    jmp ScummV5_M23A_ValidateRecord__{index}_bad",
            f"ScummV5_M23A_ValidateRecord__{index}_directory_ok:", "    .a8",
            "    rep #$20", "    .a16", "    inx", f"    cpx #${directory_size:04X}",
            f"    bcc ScummV5_M23A_ValidateRecord__{index}_directory",
            "    lda #$0000", "    sta.l SAME_SCUMM_M23A_CHECKSUM",
        ))
        for segment_index, (label, size, start) in enumerate(record["segments"]):
            validator_lines.extend((
                "    ldx #$0000", f"ScummV5_M23A_ValidateRecord__{index}_segment_{segment_index}:",
                "    .a16", "    .i16",
            ))
            if segment_index == 0:
                validator_lines.extend((
                    "    cpx #$0020", f"    bcc ScummV5_M23A_ValidateRecord__{index}_segment_{segment_index}_add",
                    "    cpx #$0026", f"    bcc ScummV5_M23A_ValidateRecord__{index}_segment_{segment_index}_next",
                    f"ScummV5_M23A_ValidateRecord__{index}_segment_{segment_index}_add:", "    .a16",
                ))
            validator_lines.extend((
                "    lda #$0000", "    sta.l SAME_SCUMM_M23A_BYTE",
                "    sep #$20", "    .a8", f"    lda.l {label},x", "    sta.l SAME_SCUMM_M23A_BYTE",
                "    rep #$20", "    .a16", "    lda.l SAME_SCUMM_M23A_CHECKSUM",
                "    clc", "    adc.l SAME_SCUMM_M23A_BYTE", "    sta.l SAME_SCUMM_M23A_CHECKSUM",
            ))
            if segment_index == 0:
                validator_lines.extend((f"ScummV5_M23A_ValidateRecord__{index}_segment_{segment_index}_next:",
                                        "    .a16", "    .i16"))
            effective_size = size
            if segment_index == len(record["segments"]) - 1:
                effective_size -= 32  # host SHA-256 trailer is not in compact sum
            validator_lines.extend((
                "    inx", f"    cpx #${effective_size:04X}",
                f"    bcc ScummV5_M23A_ValidateRecord__{index}_segment_{segment_index}",
            ))
        validator_lines.extend((
            "    lda.l SAME_SCUMM_M23A_CHECKSUM", f"    cmp #${record['checksum']:04X}",
            f"    bne ScummV5_M23A_ValidateRecord__{index}_bad", "    clc", "    rts",
            f"ScummV5_M23A_ValidateRecord__{index}_bad:", "    sep #$20", "    .a8", "    sec", "    rts",
        ))

    if args.far_validator_output:
        validator_lines.extend((
            "ScummV5_M23A_ValidateRecord_FarEntry:",
            "    jsr ScummV5_M23A_ValidateRecord",
            "    rtl",
        ))
        args.far_validator_output.parent.mkdir(parents=True, exist_ok=True)
        args.far_validator_output.write_text("\n".join(validator_lines) + "\n")
    else:
        lines.extend(validator_lines)
        # Poppy validates include existence even when the conditional include
        # is disabled.  Keep the conventional far-validator include inert for
        # inline-validator builds so stale labels from a prior M24 build cannot
        # collide with this generated table.
        inert_far = args.output.with_name("scumm_v5_room_validator_far.inc.pasm")
        inert_far.write_text("; Validator is emitted inline for this build.\n")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.data_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n")
    args.data_output.write_text("\n".join(data_lines) + "\n")
    print(json.dumps({
        "rooms": [item["room"] for item in records], "programs": len(programs),
        "last_bank": bank, "output": str(args.output), "data": str(args.data_output),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
