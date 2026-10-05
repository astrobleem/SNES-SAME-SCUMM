"""Source-bound SCUMM v5 room bundle compiler (initial bounded dialect slice).

The front end reuses SAME's checked room/resource decoders.  Script bytes are
kept losslessly for the existing VM; the analysis decoder only lowers operand
forms whose boundaries are known and leaves an explicit opaque tail otherwise.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from ...errors import ResourceError
from .cooked_room import (
    FLAG_REGISTRATION_ONLY,
    HEADER,
    SCRIPT,
    ScriptChunkInput,
    decode_cooked_room,
    encode_cooked_room,
)
from .room import ScummV5Room, ScummV5RoomObject, decode_room, iter_scumm_chunks
from .text import control_argument_count


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_member_pair(names: list[str] | tuple[str, ...]) -> dict[str, str]:
    """Locate the unique standard SCUMM v5 index/data members in an archive."""
    result: dict[str, str] = {}
    for key, suffix in (("game.index", ".000"), ("game.data", ".001")):
        matches = [name for name in names if name.upper().endswith(suffix)]
        if len(matches) != 1:
            raise ResourceError(f"archive must contain one SCUMM {suffix} member")
        result[key] = matches[0]
    return result


def profile_game_identity(profile: Any) -> str:
    value = f"{profile.engine_id}\0{profile.game_id}\0{profile.variant}".encode()
    return sha256(value)


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    game: str
    resource_key: str
    source_member: str
    room: int
    script_kind: str
    resource_offset: int
    source_offset: int
    source_length: int
    source_sha256: str
    script_number: int | None = None
    object_id: int | None = None
    verb_id: int | None = None


@dataclass(frozen=True, slots=True)
class InstructionIR:
    pc: int
    opcode: int
    operation: str
    operands: tuple[tuple[str, Any], ...]
    raw_hex: str
    source_offset: int
    boundary_known: bool = True
    branch_target: int | None = None
    diagnostic: str | None = None


@dataclass(frozen=True, slots=True)
class ScriptIR:
    identity: str
    kind: str
    number: int | None
    object_id: int | None
    verb_id: int | None
    source: SourceIdentity
    program: bytes
    instructions: tuple[InstructionIR, ...]
    decode_complete: bool
    opaque_from_pc: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "kind": self.kind,
            "number": self.number,
            "object_id": self.object_id,
            "verb_id": self.verb_id,
            "source": asdict(self.source),
            "program_length": len(self.program),
            "program_sha256": sha256(self.program),
            "decode_complete": self.decode_complete,
            "opaque_from_pc": self.opaque_from_pc,
            "instructions": [
                {**asdict(item), "operands": dict(item.operands)}
                for item in self.instructions
            ],
        }


@dataclass(frozen=True, slots=True)
class ObjectVerbIR:
    verb_id: int
    entry_offset: int
    script_identity: str
    source_offset: int
    source_sha256: str


@dataclass(frozen=True, slots=True)
class ObjectIR:
    object_id: int
    x: int
    y: int
    width: int
    height: int
    flags: int
    parent: int
    walk_x: int
    walk_y: int
    actor_direction: int
    owner: int | None
    initial_state: int | None
    initial_classes: int | None
    source_offset: int
    obcd_sha256: str
    verbs: tuple[ObjectVerbIR, ...]


@dataclass(frozen=True, slots=True)
class Dependency:
    kind: str
    target: int | str | None
    resolution: str
    source_script: str
    source_pc: int
    expression: str | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class CapabilityReport:
    scumm_dialect: str
    operations: tuple[str, ...]
    runtime_primitives: tuple[str, ...]
    unsupported_operations: tuple[str, ...]
    unclassified_operations: tuple[str, ...]
    decode_incomplete_scripts: tuple[str, ...]
    static_dependencies: tuple[Dependency, ...]
    dynamic_dependencies: tuple[Dependency, ...]
    capacity: tuple[tuple[str, int], ...]
    state_reads: tuple[str, ...]
    state_writes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "same_scumm_v5_room_capabilities_v1",
            "scumm_dialect": self.scumm_dialect,
            "operations": list(self.operations),
            "runtime_primitives": list(self.runtime_primitives),
            "unsupported_operations": list(self.unsupported_operations),
            "unclassified_operations": list(self.unclassified_operations),
            "decode_incomplete_scripts": list(self.decode_incomplete_scripts),
            "static_dependencies": [asdict(item) for item in self.static_dependencies],
            "dynamic_dependencies": [asdict(item) for item in self.dynamic_dependencies],
            "capacity": dict(self.capacity),
            "state_reads": list(self.state_reads),
            "state_writes": list(self.state_writes),
            "status": "partial" if (
                self.unsupported_operations or self.unclassified_operations
            ) else "analyzed",
        }


@dataclass(frozen=True, slots=True)
class RoomIR:
    room: int
    resource_key: str
    source_member: str
    room_source_offset: int
    source_container_offset: int
    room_length: int
    room_sha256: str
    width: int
    height: int
    walkbox_count: int
    objects: tuple[ObjectIR, ...]
    scripts: tuple[ScriptIR, ...]
    dependencies: tuple[Dependency, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "same_scumm_v5_room_ir_v1",
            "room": self.room,
            "resource_key": self.resource_key,
            "source_member": self.source_member,
            "room_source_offset": self.room_source_offset,
            "source_container_offset": self.source_container_offset,
            "room_length": self.room_length,
            "room_sha256": self.room_sha256,
            "geometry": {
                "width": self.width,
                "height": self.height,
                "walkbox_count": self.walkbox_count,
            },
            "objects": [asdict(item) for item in self.objects],
            "scripts": [item.to_dict() for item in self.scripts],
            "dependencies": [asdict(item) for item in self.dependencies],
        }


@dataclass(frozen=True, slots=True)
class RoomBundleCompilation:
    room_ir: RoomIR
    capabilities: CapabilityReport
    cooked_record: bytes
    record_manifest: dict[str, Any]

    def ir_json(self) -> bytes:
        return _json_bytes(self.room_ir.to_dict())

    def analysis_json(self) -> bytes:
        return _json_bytes(self.capabilities.to_dict())


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


class _Cursor:
    def __init__(self, data: bytes, pc: int) -> None:
        self.data, self.pc = data, pc

    def u8(self) -> int:
        if self.pc >= len(self.data):
            raise ValueError("truncated byte operand")
        value = self.data[self.pc]
        self.pc += 1
        return value

    def u16(self) -> int:
        if self.pc + 2 > len(self.data):
            raise ValueError("truncated word operand")
        value = int.from_bytes(self.data[self.pc:self.pc + 2], "little")
        self.pc += 2
        return value

    def signed16(self) -> int:
        value = self.u16()
        return value - 0x10000 if value & 0x8000 else value

    def varref(self) -> dict[str, Any]:
        reference = self.u16()
        indexed = bool(reference & 0x2000)
        index = self.u16() if indexed else None
        namespace = "bit" if reference & 0x8000 else "local" if reference & 0x4000 else "global"
        return {
            "mode": "variable",
            "namespace": namespace,
            "index": reference & 0x0FFF,
            "indexed": indexed,
            "index_reference": index,
        }

    def byte_operand(self, opcode: int, mask: int) -> dict[str, Any]:
        return self.varref() if opcode & mask else {"mode": "direct", "value": self.u8()}

    def word_operand(self, opcode: int, mask: int) -> dict[str, Any]:
        if opcode & mask:
            return self.varref()
        value = self.signed16()
        return {"mode": "direct", "value": value}

    def word_args(self) -> list[dict[str, Any]]:
        result = []
        while True:
            selector = self.u8()
            if selector == 0xFF:
                return result
            value = self.u16()
            result.append({
                "mode": "variable" if selector & 0x80 else "direct",
                "selector": selector,
                "value": value,
            })
            if len(result) > 256:
                raise ValueError("argument list exceeds bounded SCUMM limit")

    def encoded_string(self) -> bytes:
        start = self.pc
        while True:
            value = self.u8()
            if value == 0:
                return self.data[start:self.pc]
            if value == 0xFF:
                control = self.u8()
                for _ in range(control_argument_count(control)):
                    self.u8()
            if self.pc - start > 4096:
                raise ValueError("encoded string exceeds bounded SCUMM limit")


_COMPARISONS = {
    0x48: "equal", 0xC8: "equal", 0x08: "not_equal", 0x88: "not_equal",
    0x44: "less_than", 0xC4: "less_than", 0x78: "greater_than", 0xF8: "greater_than",
    0x38: "less_equal", 0xB8: "less_equal", 0x04: "greater_equal", 0x84: "greater_equal",
}
_START_SCRIPT = frozenset((0x0A, 0x2A, 0x4A, 0x6A, 0x8A, 0xAA, 0xCA, 0xEA))
_CHAIN_SCRIPT = frozenset((0x42, 0xC2))
_START_OBJECT = frozenset((0x37, 0x77, 0xB7, 0xF7))
_LOAD_ROOM_WITH_EGO = frozenset((0x24, 0x64, 0xA4, 0xE4))
_WALK_ACTOR_TO = frozenset((0x1E, 0x3E, 0x5E, 0x7E, 0x9E, 0xBE, 0xDE, 0xFE))
_PUT_ACTOR = frozenset((0x01, 0x21, 0x41, 0x61, 0x81, 0xA1, 0xC1, 0xE1))
_END_CUTSCENE = frozenset((0xC0,))
_STOP = frozenset((0x00, 0xA0))


def decode_script(
    program: bytes,
    *,
    identity: str,
    kind: str,
    number: int | None,
    room: int,
    resource_key: str,
    game_name: str,
    source_member: str,
    resource_offset: int,
    source_offset: int,
    object_id: int | None = None,
    verb_id: int | None = None,
    source_body_sha256: str | None = None,
    pc_base: int = 0,
) -> ScriptIR:
    """Decode the bounded v5 instruction subset without guessing unknown widths."""
    instructions: list[InstructionIR] = []
    pc = 0
    opaque_from = None
    while pc < len(program):
        start = pc
        opcode = program[pc]
        cursor = _Cursor(program, pc + 1)
        operation = "unknown"
        operands: dict[str, Any] = {}
        branch_target = None
        try:
            if opcode in _STOP:
                operation = "stop_script"
            elif opcode in _END_CUTSCENE:
                operation = "end_cutscene"
            elif opcode == 0x80:
                operation = "yield"
            elif opcode == 0x18:
                operation = "jump"
                displacement = cursor.signed16()
                branch_target = cursor.pc + displacement
                operands["displacement"] = displacement
            elif opcode in (0x28, 0xA8):
                operation = "branch_equal_zero" if opcode == 0x28 else "branch_not_equal_zero"
                operands["value"] = cursor.varref()
                displacement = cursor.signed16()
                branch_target = cursor.pc + displacement
                operands["displacement"] = displacement
            elif opcode in _COMPARISONS:
                operation = f"branch_{_COMPARISONS[opcode]}"
                operands["left"] = cursor.varref()
                operands["right"] = cursor.word_operand(opcode, 0x80)
                displacement = cursor.signed16()
                branch_target = cursor.pc + displacement
                operands["displacement"] = displacement
            elif opcode in _START_SCRIPT or opcode in _CHAIN_SCRIPT:
                operation = "chain_script" if opcode in _CHAIN_SCRIPT else "start_script"
                operands["script"] = cursor.byte_operand(opcode, 0x80)
                operands["arguments"] = cursor.word_args()
            elif opcode in _START_OBJECT:
                operation = "start_object"
                operands["object"] = cursor.word_operand(opcode, 0x80)
                operands["entry"] = cursor.byte_operand(opcode, 0x40)
                operands["arguments"] = cursor.word_args()
            elif opcode in (0x72, 0xF2):
                operation = "load_room"
                operands["room"] = cursor.byte_operand(opcode, 0x80)
            elif opcode in _LOAD_ROOM_WITH_EGO:
                operation = "load_room_with_ego"
                operands["entry_object"] = cursor.word_operand(opcode, 0x80)
                operands["room"] = cursor.byte_operand(opcode, 0x40)
                # v5 takes signed literal coordinates; the actor is implicit
                # VAR_EGO (global variable 1), not another encoded operand.
                operands["x"] = cursor.signed16()
                operands["y"] = cursor.signed16()
                operands["ego_actor"] = {
                    "mode": "implicit_variable", "namespace": "global", "index": 1,
                }
            elif opcode in (0x11, 0x51, 0x91, 0xD1):
                operation = "animate_actor"
                operands["actor"] = cursor.byte_operand(opcode, 0x80)
                operands["animation"] = cursor.byte_operand(opcode, 0x40)
            elif opcode in _WALK_ACTOR_TO:
                operation = "walk_actor_to"
                operands["actor"] = cursor.byte_operand(opcode, 0x80)
                operands["x"] = cursor.word_operand(opcode, 0x40)
                operands["y"] = cursor.word_operand(opcode, 0x20)
            elif opcode in _PUT_ACTOR:
                operation = "put_actor"
                operands["actor"] = cursor.byte_operand(opcode, 0x80)
                operands["x"] = cursor.word_operand(opcode, 0x40)
                operands["y"] = cursor.word_operand(opcode, 0x20)
            elif opcode == 0x40:
                operation = "begin_cutscene"
                operands["arguments"] = cursor.word_args()
            elif opcode == 0x4C:
                operation = "sound_kludge"
                operands["arguments"] = cursor.word_args()
            elif opcode in (0x0C, 0x8C):
                operation = "resource_routines"
                selector = cursor.u8()
                subop = selector & 0x3F
                operands["subop"] = subop
                if subop != 17:
                    operands["resource"] = cursor.byte_operand(selector, 0x80)
                    if subop == 20:
                        operands["object"] = cursor.word_operand(selector, 0x40)
            elif opcode in (0x14, 0x94):
                operation = "print_text"
                operands["actor"] = cursor.byte_operand(opcode, 0x80)
                commands = []
                while True:
                    selector = cursor.u8()
                    if selector == 0xFF:
                        break
                    subop = selector & 0x0F
                    item: dict[str, Any] = {"subop": subop}
                    text_ends_instruction = False
                    if subop == 0:
                        item["values"] = [cursor.word_operand(selector, mask)
                                          for mask in (0x80, 0x40)]
                    elif subop in (1, 2, 3, 8):
                        count = {1: 1, 2: 1, 3: 2, 8: 2}[subop]
                        operand_kind = "word" if subop in (2, 3, 8) else "byte"
                        masks = (0x80, 0x40)
                        item["values"] = [
                            (cursor.word_operand if operand_kind == "word" else cursor.byte_operand)(
                                selector, mask
                            ) for mask in masks[:count]
                        ]
                    elif subop == 15:
                        item["encoded_text_hex"] = cursor.encoded_string().hex()
                        # The text-string print command completes this SCUMM
                        # instruction; the next byte is an opcode, not another
                        # print selector. This matches the runtime's early
                        # return from decodeParseString/SO_TEXTSTRING.
                        text_ends_instruction = True
                    elif subop not in (4, 6, 7):
                        raise ValueError(f"print sub-op {subop} has unknown width")
                    commands.append(item)
                    if len(commands) > 128:
                        raise ValueError("print command list exceeds bound")
                    if text_ends_instruction:
                        break
                operands["commands"] = commands
            elif opcode == 0xD8:
                operation = "print_ego"
                # printEgo uses the same print-command sequence without an
                # explicit actor operand. Keep the parsed command records in
                # the same operand field as ordinary print.
                commands = []
                while True:
                    selector = cursor.u8()
                    if selector == 0xFF:
                        break
                    subop = selector & 0x0F
                    item = {"subop": subop}
                    text_ends_instruction = False
                    if subop == 15:
                        item["encoded_text_hex"] = cursor.encoded_string().hex()
                        text_ends_instruction = True
                    elif subop == 0:
                        item["values"] = [cursor.word_operand(selector, mask)
                                          for mask in (0x80, 0x40)]
                    elif subop in (1, 2, 3, 8):
                        count = {1: 1, 2: 1, 3: 2, 8: 2}[subop]
                        operand_kind = "word" if subop in (2, 3, 8) else "byte"
                        item["values"] = [
                            (cursor.word_operand if operand_kind == "word" else cursor.byte_operand)(
                                selector, mask
                            ) for mask in (0x80, 0x40)[:count]
                        ]
                    elif subop not in (4, 6, 7):
                        raise ValueError(f"print sub-op {subop} has unknown width")
                    commands.append(item)
                    if len(commands) > 128:
                        raise ValueError("print command list exceeds bound")
                    if text_ends_instruction:
                        break
                operands["commands"] = commands
            elif opcode in (0x07, 0x47, 0x87, 0xC7):
                operation = "set_object_state"
                operands["object"] = cursor.word_operand(opcode, 0x80)
                operands["state"] = cursor.byte_operand(opcode, 0x40)
            elif opcode == 0x2C:
                operation = "cursor_command"
                selector = cursor.u8()
                subop = selector & 0x1F
                operands["subop"] = subop
                counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0,
                          7: 0, 8: 0, 10: 2, 11: 3, 12: 1, 13: 1}
                if subop == 14:
                    values = []
                    while True:
                        value_selector = cursor.u8()
                        if value_selector == 0xFF:
                            break
                        values.append(cursor.word_operand(value_selector, 0x80))
                        if len(values) > 16:
                            raise ValueError("cursor color list exceeds bound")
                    operands["values"] = values
                elif subop not in counts:
                    raise ValueError(f"cursor command sub-op {subop} has unknown width")
                else:
                    operands["values"] = [
                        cursor.byte_operand(selector, mask)
                        for mask in (0x80, 0x40, 0x20)[:counts[subop]]
                    ]
            elif opcode == 0x30:
                operation = "matrix_ops"
                selector = cursor.u8()
                subop = selector & 0x1F
                operands["subop"] = subop
                if subop == 1:
                    operands["box"] = cursor.byte_operand(selector, 0x80)
                    operands["flags"] = cursor.byte_operand(selector, 0x40)
                elif subop != 4:
                    raise ValueError(f"matrixOps sub-op {subop} has unknown width")
            elif opcode in (0x1A, 0x9A):
                operation = "write_variable"
                operands["destination"] = cursor.varref()
                operands["value"] = cursor.word_operand(opcode, 0x80)
            elif opcode in (0x46, 0xC6):
                operation = "increment_variable" if opcode == 0x46 else "decrement_variable"
                operands["destination"] = cursor.varref()
            elif opcode in (0x2E,):
                operation = "delay"
                operands["frames_low"] = cursor.u16()
                operands["frames_high"] = cursor.u8()
            elif opcode in (0x02, 0x82, 0x1C, 0x9C, 0x3C, 0xBC):
                operation = {
                    0x02: "start_music", 0x82: "start_music",
                    0x1C: "start_sound", 0x9C: "start_sound",
                    0x3C: "stop_sound", 0xBC: "stop_sound",
                }[opcode]
                operands["resource"] = cursor.byte_operand(opcode, 0x80)
            elif opcode in (0x5D, 0xDD):
                operation = "set_object_class"
                operands["object"] = cursor.word_operand(opcode, 0x80)
                selectors = []
                while True:
                    selector = cursor.u8()
                    if selector == 0xFF:
                        break
                    selectors.append(cursor.word_operand(selector, 0x80))
                    if len(selectors) > 64:
                        raise ValueError("class selector list exceeds bound")
                operands["classes"] = selectors
            elif opcode in (0x13, 0x53, 0x93, 0xD3):
                operation = "actor_ops"
                operands["actor"] = cursor.byte_operand(opcode, 0x80)
                subops = []
                selectors = []
                while True:
                    selector = cursor.u8()
                    if selector == 0xFF:
                        break
                    subop = selector & 0x1F
                    subops.append(subop)
                    counts = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 1,
                              7: 3, 8: 0, 9: 1, 10: 0, 11: 2, 12: 1,
                              14: 1, 16: 1, 17: 2, 18: 0, 19: 1,
                              20: 0, 21: 0, 22: 1, 23: 1}
                    if subop == 13:
                        raise ValueError("actor name string requires string decoder")
                    if subop not in counts:
                        raise ValueError(f"actorOps sub-op {subop} has unknown width")
                    values = []
                    for mask_bit in (0x80, 0x40, 0x20)[:counts[subop]]:
                        values.append(cursor.byte_operand(selector, mask_bit))
                    selectors.append({"subop": subop, "values": values})
                operands["subops"] = subops
                operands["selectors"] = selectors
            elif opcode in (0x52, 0xD2):
                operation = "actor_follow_camera"
                operands["actor"] = cursor.byte_operand(opcode, 0x80)
            elif opcode in (0x2D, 0x6D, 0xAD, 0xED):
                operation = "put_actor_in_room"
                operands["actor"] = cursor.byte_operand(opcode, 0x80)
                operands["room"] = cursor.byte_operand(opcode, 0x40)
            elif opcode == 0xAE:
                selector = cursor.u8()
                operation = "wait_for_actor" if selector & 0x1F == 1 else "wait"
                operands["selector"] = selector
                if selector & 0x1F == 1:
                    operands["actor"] = cursor.byte_operand(selector, 0x80)
                elif selector & 0x1F != 2:
                    raise ValueError(f"wait sub-op {selector & 0x1F} has unknown width")
            else:
                raise ValueError("instruction width is not in the current decoder subset")
        except (ValueError, IndexError) as exc:
            opaque_from = pc_base + start
            instructions.append(InstructionIR(
                pc_base + start, opcode, "opaque_bytecode_tail", (), program[start:].hex(),
                source_offset + start, False, None, str(exc),
            ))
            break
        pc = cursor.pc
        instructions.append(InstructionIR(
            pc_base + start, opcode, operation, tuple(sorted(operands.items())),
            program[start:pc].hex(), source_offset + start, True,
            None if branch_target is None else pc_base + branch_target,
        ))
        if operation == "stop_script":
            # Trailing padding/data is retained in the program; it is not
            # mistaken for executable operations after the authored terminator.
            break
    return ScriptIR(
        identity, kind, number, object_id, verb_id,
        SourceIdentity(
            game_name, resource_key, source_member, room, kind,
            resource_offset, source_offset, len(program),
            source_body_sha256 or sha256(program), number, object_id, verb_id,
        ),
        bytes(program), tuple(instructions), opaque_from is None, opaque_from,
    )


def _static_value(operand: Any) -> int | None:
    return int(operand["value"]) if isinstance(operand, dict) and operand.get("mode") == "direct" else None


def analyze_room(room_ir: RoomIR, *, global_script_count: int) -> CapabilityReport:
    dependencies: list[Dependency] = []
    dynamic: list[Dependency] = []
    operations: set[str] = set()
    unsupported: set[str] = set()
    unclassified: set[str] = set()
    incomplete: set[str] = set()
    reads: set[str] = set()
    writes: set[str] = set()
    local_ids = {item.number for item in room_ir.scripts if item.kind == "LSCR"}
    object_verbs = {
        item.object_id: {verb.verb_id for verb in item.verbs}
        for item in room_ir.objects
    }
    for obj in room_ir.objects:
        for verb in obj.verbs:
            dependencies.append(Dependency(
                "object-verb", obj.object_id, "resolved", verb.script_identity, 0,
                detail=f"verb {verb.verb_id}",
            ))
    for script in room_ir.scripts:
        if not script.decode_complete:
            incomplete.add(script.identity)
        for instruction in script.instructions:
            operation = instruction.operation
            operations.add(operation)
            operands = dict(instruction.operands)
            if operation in {"start_script", "chain_script"}:
                target = _static_value(operands.get("script"))
                if target is None:
                    dynamic.append(Dependency(
                        "script", None, "dynamic", script.identity, instruction.pc,
                        expression="script operand is variable-indirect",
                    ))
                else:
                    detail = "local" if target >= global_script_count else "global"
                    resolved = target in local_ids if detail == "local" else None
                    dependencies.append(Dependency(
                        "script", target,
                        "resolved" if resolved is True else "external" if resolved is None else "missing",
                        script.identity, instruction.pc, detail=detail,
                    ))
            elif operation == "start_object":
                target = _static_value(operands.get("object"))
                entry = _static_value(operands.get("entry"))
                if target is None or entry is None:
                    dynamic.append(Dependency(
                        "object-script", target, "dynamic", script.identity, instruction.pc,
                        expression="object or entry operand is variable-indirect",
                    ))
                else:
                    resolved = entry in object_verbs.get(target, set())
                    dependencies.append(Dependency(
                        "object-script", target,
                        "resolved" if resolved else "missing",
                        script.identity, instruction.pc, detail=f"entry {entry}",
                    ))
            elif operation == "load_room":
                target = _static_value(operands.get("room"))
                (dependencies if target is not None else dynamic).append(Dependency(
                    "room-transition", target,
                    "static" if target is not None else "dynamic",
                    script.identity, instruction.pc,
                    expression=None if target is not None else "room operand is variable-indirect",
                ))
            elif operation == "load_room_with_ego":
                target = _static_value(operands.get("room"))
                (dependencies if target is not None else dynamic).append(Dependency(
                    "room-transition", target,
                    "static" if target is not None else "dynamic",
                    script.identity, instruction.pc,
                    expression=None if target is not None else "room operand is variable-indirect",
                ))
                entry_object = _static_value(operands.get("entry_object"))
                (dependencies if target is not None and entry_object is not None else dynamic).append(
                    Dependency(
                        "room-entry-object",
                        f"{target}:{entry_object}" if target is not None and entry_object is not None else None,
                        "static" if target is not None and entry_object is not None else "dynamic",
                        script.identity, instruction.pc,
                        expression=(None if target is not None and entry_object is not None
                                    else "room or entry object operand is variable-indirect"),
                    )
                )
                reads.add("global:1")
            elif operation == "actor_follow_camera":
                dynamic.append(Dependency(
                    "room-transition", None, "dynamic", script.identity, instruction.pc,
                    expression="followed actor room is runtime state",
                    detail="actorFollowCamera may install the actor's scene",
                ))
            elif operation == "put_actor_in_room":
                target = _static_value(operands.get("room"))
                (dependencies if target is not None else dynamic).append(Dependency(
                    "actor-placement", target,
                    "static" if target is not None else "dynamic",
                    script.identity, instruction.pc,
                    expression=None if target is not None else "room operand is variable-indirect",
                    detail="actor room assignment; scene transition is separate",
                ))
            elif operation in {"start_sound", "stop_sound", "start_music"}:
                target = _static_value(operands.get("resource"))
                (dependencies if target is not None else dynamic).append(Dependency(
                    "sound" if operation != "start_music" else "music", target,
                    "static" if target is not None else "dynamic",
                    script.identity, instruction.pc,
                ))
            elif operation == "actor_ops":
                for selector in operands.get("selectors", []):
                    subop = int(selector["subop"])
                    kind = "costume" if subop == 1 else "sound" if subop == 3 else None
                    if kind is not None:
                        value = selector["values"][0] if selector["values"] else None
                        target = _static_value(value)
                        (dependencies if target is not None else dynamic).append(Dependency(
                            kind, target, "static" if target is not None else "dynamic",
                            script.identity, instruction.pc,
                            expression=None if target is not None else "actorOps resource operand is variable-indirect",
                        ))
            elif operation == "resource_routines":
                subop = int(operands.get("subop", 0))
                if subop == 17:
                    continue
                resource = _static_value(operands.get("resource"))
                if subop in (18, 19):
                    kind = "charset"
                elif subop == 20:
                    kind = "room-object-resource"
                else:
                    kind = ("script", "sound", "costume", "room")[(subop - 1) % 4]
                (dependencies if resource is not None else dynamic).append(Dependency(
                    kind, resource,
                    "static" if resource is not None else "dynamic",
                    script.identity, instruction.pc,
                    expression=None if resource is not None else "resource ID is variable-indirect",
                    detail=f"resource routine {subop}",
                ))
            for key in ("value", "left", "right", "destination", "script", "object",
                        "entry", "entry_object", "room", "resource"):
                operand = operands.get(key)
                if isinstance(operand, dict) and operand.get("mode") == "variable":
                    namespace = str(operand.get("namespace"))
                    index = int(operand.get("index", 0))
                    target_set = writes if key == "destination" else reads
                    target_set.add(f"{namespace}:{index}")
            if operation == "opaque_bytecode_tail":
                unclassified.add(
                    f"opcode ${instruction.opcode:02X} at {script.identity}+${instruction.pc:04X}"
                )
            if operation == "set_object_state":
                object_id = _static_value(operands.get("object"))
                if object_id is not None:
                    writes.add(f"object-state:{object_id}")
            if operation == "set_object_class":
                object_id = _static_value(operands.get("object"))
                if object_id is not None:
                    writes.add(f"object-class:{object_id}")
    capacity = (
        ("room_scripts", sum(item.kind in {"ENCD", "EXCD", "LSCR"} for item in room_ir.scripts)),
        ("objects", len(room_ir.objects)),
        ("object_verb_entries", sum(len(item.verbs) for item in room_ir.objects)),
        ("decoded_operations", sum(len(item.instructions) for item in room_ir.scripts)),
        ("source_program_bytes", sum(len(item.program) for item in room_ir.scripts)),
    )
    return CapabilityReport(
        "SCUMM v5", tuple(sorted(operations)),
        tuple(sorted(operations - {"opaque_bytecode_tail"})),
        tuple(sorted(unsupported)), tuple(sorted(unclassified)), tuple(sorted(incomplete)),
        tuple(dependencies), tuple(dynamic), capacity,
        tuple(sorted(reads)), tuple(sorted(writes)),
    )


def compile_room_payload(
    room_payload: bytes,
    *,
    room_number: int,
    game_name: str,
    resource_key: str,
    source_member: str,
    source_container_offset: int,
    original_room_file_offset: int,
    profile_sha256: str,
    game_identity_sha256: str,
    archive_sha256: str,
    index_sha256: str,
    data_sha256: str,
    global_script_count: int,
    global_object_states: bytes = b"",
    global_object_owners: bytes = b"",
    global_object_classes: tuple[int, ...] = (),
    executable: bool = True,
) -> RoomBundleCompilation:
    """Compile one raw v5 ROOM through parser, IR, analysis and SC5C backend."""
    decoded = decode_room(room_payload, key=resource_key)
    chunks = iter_scumm_chunks(room_payload, owner=resource_key)
    script_inputs: list[ScriptChunkInput] = []
    scripts: list[ScriptIR] = []
    script_manifest: list[dict[str, Any]] = []
    for chunk in chunks:
        if chunk.tag not in {"ENCD", "EXCD", "LSCR"}:
            continue
        body_chunk_offset = 9 if chunk.tag == "LSCR" else 8
        if chunk.tag == "LSCR":
            if not chunk.payload:
                raise ResourceError(f"{resource_key} LSCR at {chunk.offset} has no script number")
            number = chunk.payload[0]
            body = chunk.payload[1:]
            if number < global_script_count:
                raise ResourceError(f"{resource_key} LSCR {number} is below global namespace boundary")
            identity = f"{resource_key}/LSCR.{number}"
        else:
            number = 10002 if chunk.tag == "ENCD" else 10001
            body = chunk.payload
            identity = f"{resource_key}/{chunk.tag}"
        script_inputs.append(ScriptChunkInput(
            chunk.tag, number, identity, chunk.offset, body_chunk_offset, len(body),
        ))
        body_room_offset = chunk.offset + body_chunk_offset
        source_offset = original_room_file_offset + body_room_offset
        ir = decode_script(
            body, identity=identity, kind=chunk.tag, number=number if chunk.tag == "LSCR" else None,
            room=room_number, resource_key=resource_key, game_name=game_name,
            source_member=source_member,
            resource_offset=source_container_offset, source_offset=source_offset,
        )
        scripts.append(ir)
        script_manifest.append({
            "kind": chunk.tag, "number": number, "identity": identity,
            "chunk_length": chunk.size, "program_length": len(body),
            "sha256": sha256(body), "original_file_offset": source_offset,
            "original_room_offset": body_room_offset,
            "original_chunk_offset": body_chunk_offset,
            "normalized_script_offset": 0,
            **({"local_script_index": number - global_script_count} if chunk.tag == "LSCR" else {}),
        })

    objects: list[ObjectIR] = []
    object_manifest = []
    for local_index, obj in enumerate(decoded.objects, 1):
        owner = global_object_owners[obj.object_id] if obj.object_id < len(global_object_owners) else None
        state = global_object_states[obj.object_id] if obj.object_id < len(global_object_states) else None
        classes = global_object_classes[obj.object_id] if obj.object_id < len(global_object_classes) else None
        verb_irs: list[ObjectVerbIR] = []
        object_manifest.append({
            "object_id": obj.object_id, "local_object_index": local_index,
            "obcd_original_file_offset": original_room_file_offset + obj.obcd_room_offset,
            "obcd_room_offset": obj.obcd_room_offset, "obcd_length": len(obj.obcd),
            "obcd_sha256": sha256(obj.obcd), "cdhd_offset": 8,
            "verb_table_offset": obj.verb_table_offset,
            "verb_table_length": obj.verb_table_length,
            "verb_entries": [{"verb": verb, "entry_offset": entry}
                             for verb, entry in obj.verb_entries],
        })
        # Object verb bytecode remains in the OBCD source container.  Each
        # entry is analyzed from its original offset; the complete OBCD remains
        # the backend program to preserve existing runtime entrypoint semantics.
        offsets = sorted({offset for _verb, offset in obj.verb_entries})
        for verb, entry_offset in obj.verb_entries:
            if entry_offset not in offsets or not 0 <= entry_offset < len(obj.obcd):
                continue
            end = next((value for value in offsets if value > entry_offset), len(obj.obcd))
            body = obj.obcd[entry_offset:end]
            source_offset = original_room_file_offset + obj.obcd_room_offset + entry_offset
            verb_identity = f"{resource_key}/object.{obj.object_id}/verb.{verb}"
            verb_irs.append(ObjectVerbIR(
                verb, entry_offset, verb_identity, source_offset, sha256(body),
            ))
            scripts.append(decode_script(
                body, identity=verb_identity,
                kind="OBCD", number=None, room=room_number, resource_key=resource_key,
                game_name=game_name, source_member=source_member,
                resource_offset=source_container_offset,
                source_offset=source_offset, object_id=obj.object_id, verb_id=verb,
                source_body_sha256=sha256(body), pc_base=entry_offset,
            ))
        objects.append(ObjectIR(
            obj.object_id, obj.x, obj.y, obj.width, obj.height, obj.flags, obj.parent,
            obj.walk_x, obj.walk_y, obj.actor_direction, owner, state, classes,
            original_room_file_offset + obj.obcd_room_offset, sha256(obj.obcd),
            tuple(verb_irs),
        ))

    room_ir = RoomIR(
        room_number, resource_key, source_member, original_room_file_offset,
        source_container_offset,
        len(room_payload), sha256(room_payload), decoded.width, decoded.height,
        len(decoded.walkboxes),
        tuple(objects), tuple(scripts),
    )
    analysis = analyze_room(room_ir, global_script_count=global_script_count)
    room_ir = replace(
        room_ir,
        dependencies=analysis.static_dependencies + analysis.dynamic_dependencies,
    )
    cooked = encode_cooked_room(
        room_payload, room=room_number,
        flags=0 if executable else FLAG_REGISTRATION_ONLY,
        original_room_file_offset=original_room_file_offset,
        profile_sha256=profile_sha256, game_identity_sha256=game_identity_sha256,
        archive_sha256=archive_sha256, index_sha256=index_sha256, data_sha256=data_sha256,
        scripts=tuple(script_inputs),
    )
    cooked_room = decode_cooked_room(
        cooked, expected_room=room_number, expected_profile_sha256=profile_sha256,
        expected_game_identity_sha256=game_identity_sha256,
        expected_archive_sha256=archive_sha256, expected_index_sha256=index_sha256,
        expected_data_sha256=data_sha256,
    )
    cooked_offsets = {item.identity: item.cooked_record_offset for item in cooked_room.scripts}
    for item in script_manifest:
        item["cooked_record_offset"] = cooked_offsets[item["identity"]]
    cooked_room_offset = HEADER.size + len(script_inputs) * SCRIPT.size
    for item in object_manifest:
        item["cooked_record_offset"] = cooked_room_offset + item["obcd_room_offset"]
    record_manifest = {
        "room": room_number, "resource_key": resource_key,
        "output": f"room-{room_number}.sc5c",
        "registration_only": cooked_room.registration_only,
        "original_room_file_offset": original_room_file_offset,
        "original_room_length": len(room_payload),
        "original_room_sha256": sha256(room_payload),
        "record_length": len(cooked), "record_sha256": sha256(cooked),
        "compact_checksum": cooked_room.compact_checksum,
        "scripts": script_manifest, "objects": object_manifest,
        "compiler": {
            "ir_sha256": sha256(_json_bytes(room_ir.to_dict())),
            "analysis_sha256": sha256(_json_bytes(analysis.to_dict())),
        },
    }
    return RoomBundleCompilation(room_ir, analysis, cooked, record_manifest)


def compiler_source_manifest() -> dict[str, str]:
    """Hash compiler/front-end/record sources without embedding checkout paths."""
    repository_root = Path(__file__).resolve().parents[4]
    components = (
        "src/same/engines/scumm_v5/room_compiler.py",
        "src/same/engines/scumm_v5/room.py",
        "src/same/engines/scumm_v5/resources.py",
        "src/same/engines/scumm_v5/cooked_room.py",
        "src/same/engines/scumm_v5/text.py",
        "src/same/engines/scumm_v5/policy.py",
        "src/same/profile.py",
        "src/same/resources.py",
    )
    return {
        component: sha256((repository_root / component).read_bytes())
        for component in components
    }


def compiler_source_sha256() -> str:
    """Identity of compiler and reused front-end/backend-record sources."""
    return sha256(_json_bytes(compiler_source_manifest()))
