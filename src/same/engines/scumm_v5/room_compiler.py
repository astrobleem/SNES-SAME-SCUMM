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
from .v5_opcode_schema import OpcodeSchema, opcode_schema


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
    base_opcode: int | None = None
    opcode_family: str | None = None
    parameter_flags: int = 0
    instruction_width: int = 0
    raw_operand_hex: str = ""
    subopcode: int | None = None
    structural_status: str = "STRUCTURALLY_DECODED"
    semantic_status: str = "SEMANTIC_IR_AVAILABLE"
    semantic_capability: str | None = None
    control_flow: str = "FALLTHROUGH"
    fallthrough: bool | None = True
    branch_targets: tuple[int, ...] = ()
    opcode_variant_flags: int = 0


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


class _StructuralUnknown(ValueError):
    """The opcode family is known, but this operand/control-flow form is not."""

    def __init__(self, message: str, *, subopcode: int | None = None) -> None:
        super().__init__(message)
        self.subopcode = subopcode


def _read_structural_family(
    cursor: _Cursor, opcode: int, schema: OpcodeSchema, *, depth: int = 0,
) -> tuple[dict[str, Any], int | None, int | None]:
    """Read a known v5 instruction shape without asserting semantic support.

    The return values are decoded operands, one relative branch target, and
    an optional command subopcode. Unknown variable layouts fail closed.
    """
    if depth > 8:
        raise _StructuralUnknown("nested opcode structure exceeds bounded depth")
    family = schema.family
    form, _capability = (schema.operand_form, schema.semantic_capability)
    if form is None:
        raise _StructuralUnknown(f"no structural operand form registered for {family}")
    operands: dict[str, Any] = {}
    target: int | None = None
    subopcode: int | None = None

    def result() -> dict[str, Any]:
        return cursor.varref()

    def word_args() -> list[dict[str, Any]]:
        values = []
        while True:
            selector = cursor.u8()
            if selector == 0xFF:
                return values
            values.append({"selector": selector, "value": cursor.u16(),
                           "mode": "variable" if selector & 0x80 else "direct"})
            if len(values) > 256:
                raise _StructuralUnknown("argument list exceeds structural bound")

    if form == "string_ops":
        selector = cursor.u8()
        subopcode = selector
        key = selector & 0x1F
        operands["subopcode"] = selector
        if key == 1:
            operands["string"] = cursor.byte_operand(selector, 0x80)
            operands["text_hex"] = cursor.encoded_string().hex()
        elif key == 2:
            operands["destination"] = cursor.byte_operand(selector, 0x80)
            operands["source"] = cursor.byte_operand(selector, 0x40)
        elif key == 3:
            operands["string"] = cursor.byte_operand(selector, 0x80)
            operands["index"] = cursor.byte_operand(selector, 0x40)
            operands["character"] = cursor.byte_operand(selector, 0x20)
        elif key == 4:
            operands["result"] = result()
            operands["string"] = cursor.byte_operand(selector, 0x80)
            operands["index"] = cursor.byte_operand(selector, 0x40)
        elif key == 5:
            operands["string"] = cursor.byte_operand(selector, 0x80)
            operands["size"] = cursor.byte_operand(selector, 0x40)
        # ScummVM v5's default arm consumes only the selector.  The instruction
        # is structurally bounded, while its unrecognized semantic stays opaque
        # at the semantic layer.
    elif form == "if_class_of_is":
        operands["object"] = cursor.word_operand(opcode, 0x80)
        classes = []
        while True:
            selector = cursor.u8()
            if selector == 0xFF:
                break
            classes.append(cursor.word_operand(selector, 0x80))
            if len(classes) > 256:
                raise _StructuralUnknown("class list exceeds structural bound")
        operands["classes"] = classes
        displacement = cursor.signed16()
        operands["displacement"] = displacement
        target = cursor.pc + displacement
    elif form in {"room_ops", "actor_ops", "verb_ops", "resource_routines",
                  "cursor_command", "matrix_ops", "draw_object", "draw_box",
                  "expression", "print", "print_ego", "set_var_range",
                  "set_class", "wait", "sentence", "pseudo_room",
                  "save_restore_verbs"}:
        subopcode, command_operands, target = _read_structural_command(
            cursor, opcode, family, form, depth=depth,
        )
        operands.update(command_operands)
    else:
        # Declarative fixed-width operand grammar.  Every field consumes from
        # the same cursor used by semantic decoding and honors flag bits.
        for index, token in enumerate(form.split(",")):
            key = f"operand_{index}"
            if token == "none":
                continue
            if token == "result":
                operands[key] = result()
            elif token.startswith("p8_"):
                operands[key] = cursor.byte_operand(opcode, int(token.split("_", 1)[1], 16))
            elif token.startswith("p16_"):
                operands[key] = cursor.word_operand(opcode, int(token.split("_", 1)[1], 16))
            elif token == "p16":
                operands[key] = cursor.word_operand(opcode, 0x80)
            elif token == "varref":
                operands[key] = cursor.varref()
            elif token == "u8":
                operands[key] = cursor.u8()
            elif token == "u16":
                operands[key] = cursor.u16()
            elif token == "i16":
                operands[key] = cursor.signed16()
            elif token == "rel16":
                displacement = cursor.signed16()
                operands["displacement"] = displacement
                target = cursor.pc + displacement
            elif token == "word_args":
                operands[key] = word_args()
            elif token == "u8_string":
                start = cursor.pc
                while cursor.u8() != 0:
                    if cursor.pc - start > 4096:
                        raise _StructuralUnknown("string exceeds structural bound")
                operands[key] = cursor.data[start:cursor.pc].hex()
            elif token == "encoded_string":
                operands[key] = cursor.encoded_string().hex()
            else:
                raise _StructuralUnknown(f"unknown structural operand token {token}")
    return operands, target, subopcode


def _expression_semantic_ir(operands: dict[str, Any]) -> dict[str, Any]:
    """Normalize the SCUMM v5 RPN expression stream into explicit IR nodes.

    The nested opcode remains a generic VM dispatch node. Its family and
    structurally decoded operands are retained; this does not certify that
    every nested opcode has backend/runtime support.
    """
    names = {
        1: "push_word_operand", 2: "add", 3: "subtract",
        4: "multiply", 5: "divide", 6: "execute_nested_opcode",
    }
    normalized = []
    for item in operands.get("operations", []):
        token = int(item["subopcode"])
        subop = token & 0x1F
        row: dict[str, Any] = {
            "token": token,
            "operation": names.get(subop, "reserved_noop"),
            "parameter_flags": token & 0xE0,
        }
        if subop == 1:
            row["operand"] = item["operand"]
        elif subop == 6:
            nested = item["nested"]
            row["nested_opcode"] = {
                "opcode": nested["opcode"],
                "family": nested["family"],
                "operands": nested["operands"],
                "control_flow": opcode_schema(nested["opcode"]).control_flow,
                "branch_target": nested["target"],
                "subopcode": nested["subopcode"],
                "result_variable": {"namespace": "global", "index": 0},
            }
        normalized.append(row)
    return {
        "result": operands["result"],
        "operations": normalized,
        "evaluation": "left-to-right RPN with signed 32-bit intermediate stack",
        "maximum_stack_entries": 256,
        "reserved_token_behavior": "no-op per SCUMM v5 o5_expression default arm",
    }


def _string_ops_semantic_ir(operands: dict[str, Any]) -> dict[str, Any]:
    """Normalize one SCUMM v5 stringOps command without losing flag modes."""
    selector = int(operands["subopcode"])
    key = selector & 0x1F
    value: dict[str, Any] = {
        "subopcode": selector,
        "parameter_flags": selector & 0xE0,
    }
    if key == 1:
        value.update(operation="load_string", destination=operands["string"],
                     encoded_text_hex=operands["text_hex"])
    elif key == 2:
        value.update(operation="copy_string", destination=operands["destination"],
                     source=operands["source"])
    elif key == 3:
        value.update(operation="set_string_char", string=operands["string"],
                     index=operands["index"], character=operands["character"])
    elif key == 4:
        value.update(operation="get_string_char", result=operands["result"],
                     string=operands["string"], index=operands["index"])
    elif key == 5:
        value.update(operation="create_empty_string", string=operands["string"],
                     size=operands["size"])
    else:
        # ScummEngine_v5::o5_stringOps consumes the selector and takes its
        # default arm without further operands or state changes.
        value.update(operation="reserved_noop", reserved=True)
    return value


def _verb_ops_semantic_ir(operands: dict[str, Any]) -> dict[str, Any]:
    """Name the SCUMM v5 verb-slot commands and retain decoded flag operands."""
    names = {
        1: "set_image", 2: "set_inline_name", 3: "set_color",
        4: "set_highlight_color", 5: "set_position", 6: "enable",
        7: "disable", 8: "delete", 9: "create", 16: "set_dim_color",
        17: "dim", 18: "set_key", 19: "center", 20: "set_name_from_string",
        22: "assign_object", 23: "set_background_color",
    }
    commands = []
    for command in operands["commands"]:
        selector = int(command["subopcode"])
        key = selector & 0x1F
        row: dict[str, Any] = {
            "subopcode": selector,
            "operation": names[key],
            "parameter_flags": selector & 0xE0,
        }
        values = command["values"]
        if key == 2:
            row["encoded_name_hex"] = values[0]
        elif key in (1, 3, 4, 16, 18, 20, 23):
            row["value"] = values[0]
        elif key == 5:
            row["position"] = {"x": values[0], "y": values[1]}
        elif key == 22:
            row["object"] = values[0]
            row["room"] = values[1]
        elif values:
            row["values"] = values
        commands.append(row)
    return {"verb": operands["verb"], "commands": commands}


def _room_ops_semantic_ir(operands: dict[str, Any]) -> dict[str, Any]:
    """Name the v5 roomOps effect while retaining all source argument modes."""
    names = {
        1: "set_scroll_range", 2: "room_color_legacy", 3: "set_screen_range",
        4: "set_palette_color", 5: "enable_shake", 6: "disable_shake",
        7: "set_scale_slot", 8: "set_intensity", 9: "request_savegame",
        10: "set_fade_effect", 11: "set_rgb_intensity", 12: "set_shadow",
        13: "save_string_resource", 14: "load_string_resource",
        15: "transform_room", 16: "set_color_cycle_speed",
    }
    selector = int(operands["subopcode"])
    value = {
        "subopcode": selector,
        "operation": names[selector & 0x1F],
        "parameter_flags": selector & 0xE0,
    }
    for key, item in operands.items():
        if key != "subopcode":
            value[key] = item
    return value


def _script_lifecycle_semantic_ir(family: str, operands: dict[str, Any]) -> dict[str, Any]:
    if family == "stopScript":
        return {"script_number": operands["operand_0"]}
    if family == "isScriptRunning":
        return {
            "result": operands["operand_0"],
            "script_number": operands["operand_1"],
        }
    raise ValueError(f"unsupported lifecycle IR family {family}")


_RESULT_QUERY_IR = {
    "getRandomNr": ("get_random_nr", "maximum"),
    "actorFromPos": ("actor_from_pos", "x", "y"),
    "findObject": ("find_object", "x", "y"),
    "findInventory": ("find_inventory", "owner", "index"),
    "getActorCostume": ("get_actor_costume", "actor"),
    "getActorRoom": ("get_actor_room", "actor"),
    "getActorElevation": ("get_actor_elevation", "actor"),
    "getActorFacing": ("get_actor_facing", "actor"),
    "getActorMoving": ("get_actor_moving", "actor"),
    "getActorScale": ("get_actor_scale", "actor"),
    "getActorWalkBox": ("get_actor_walkbox", "actor"),
    "getActorWidth": ("get_actor_width", "actor"),
    "getAnimCounter": ("get_anim_counter", "actor"),
    "getActorX": ("get_actor_x", "actor"),
    "getActorY": ("get_actor_y", "actor"),
    "getClosestObjActor": ("get_closest_obj_actor", "actor"),
    "getDist": ("get_distance", "first_object_or_actor", "second_object_or_actor"),
    "getInventoryCount": ("get_inventory_count", "owner"),
    "getObjectState": ("get_object_state", "object"),
    "getObjectOwner": ("get_object_owner", "object"),
    "getStringWidth": ("get_string_width", "string"),
    "getVerbEntrypoint": ("get_verb_entrypoint", "object", "verb"),
    "isSoundRunning": ("is_sound_running", "sound"),
}

_CAMERA_COMMAND_IR = {
    "setCameraAt": "set_camera_at",
    "panCameraTo": "pan_camera_to",
}


def _result_query_semantic_ir(family: str, operands: dict[str, Any]) -> dict[str, Any]:
    operation, *argument_names = _RESULT_QUERY_IR[family]
    result = {"operation": operation, "result": operands["operand_0"]}
    for index, argument_name in enumerate(argument_names, 1):
        result[argument_name] = operands[f"operand_{index}"]
    if family == "getRandomNr":
        result["range"] = "inclusive 0..maximum"
    elif family == "findInventory":
        result["indexing"] = "one-based inventory order; zero when absent"
    return result


def _freeze_scripts_semantic_ir(operands: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation": "freeze_scripts",
        "flag": operands["operand_0"],
        "zero_behavior": "unfreeze previously frozen scripts and sentences",
        "nonzero_behavior": "freeze eligible scripts and sentences",
        "force_freeze_resistant_when_at_least": 0x80,
        "cutscene_override_slot_excluded": True,
    }


def _save_restore_verbs_semantic_ir(
    operands: dict[str, Any],
) -> dict[str, Any]:
    selector = int(operands["subopcode"])
    command = selector & 0x1F
    names = {1: "save", 2: "restore", 3: "delete"}
    values = operands["values"]
    return {
        "operation": "save_restore_verbs",
        "subopcode": selector,
        "parameter_flags": selector & 0xE0,
        "command": names.get(command, "invalid_subopcode"),
        "valid_subopcode": command in names and selector == command,
        "range_first": values[0],
        "range_last": values[1],
        "bank": values[2],
        "invalid_command_behavior": "SCUMM v5 execution error",
    }


def _object_ownership_semantic_ir(
    family: str, operands: dict[str, Any],
) -> dict[str, Any]:
    if family == "setOwnerOf":
        return {"operation": "set_object_owner", "object": operands["operand_0"],
                "owner": operands["operand_1"]}
    if family == "pickupObject":
        return {"operation": "pickup_object", "object": operands["operand_0"],
                "source_room": operands["operand_1"],
                "recipient": "VAR_EGO", "sets_state": 1,
                "adds_untouchable_class": True}
    raise ValueError(f"unsupported object ownership IR family {family}")


def _actor_ops_semantic_ir(operands: dict[str, Any]) -> dict[str, Any]:
    """Normalize v5 actor configuration commands while retaining operand modes."""
    names = {
        0: "consume_dummy_operand", 1: "set_costume", 2: "set_step_distance",
        3: "set_sound", 4: "set_walk_animation", 5: "set_talk_animation",
        6: "set_stand_animation", 7: "consume_legacy_animation_tuple",
        8: "reset_defaults", 9: "set_elevation", 10: "set_animation_defaults",
        11: "set_palette", 12: "set_talk_color", 13: "set_actor_name",
        14: "set_init_animation", 16: "set_width", 17: "set_scale",
        18: "never_clip", 19: "always_clip", 20: "ignore_boxes",
        21: "follow_boxes", 22: "set_animation_speed", 23: "set_shadow",
    }
    commands = []
    for command in operands["commands"]:
        selector = int(command["subopcode"])
        key = selector & 0x1F
        row: dict[str, Any] = {
            "subopcode": selector,
            "operation": names[key],
            "parameter_flags": selector & 0xE0,
            "arguments": command["values"],
        }
        if key == 13:
            # o5_actorOps passes the current script stream to
            # loadPtrToResource(rtActorName, actor, nullptr), so this operand
            # is an encoded string despite the runtime storing it as a resource.
            row["resource_kind"] = "actor_name"
            row["encoded_name_hex"] = command["values"][0]
        commands.append(row)
    return {"actor": operands["actor"], "commands": commands}


_SIMPLE_ACTOR_IR = {
    "putActorAtObject": ("put_actor_at_object", ("actor", "object")),
    "walkActorToObject": ("walk_actor_to_object", ("actor", "object")),
    "faceActor": ("face_actor", ("actor", "object_or_actor")),
}


def _simple_actor_semantic_ir(
    family: str, operands: dict[str, Any],
) -> dict[str, Any]:
    operation, names = _SIMPLE_ACTOR_IR[family]
    return {"operation": operation, **{
        name: operands[f"operand_{index}"] for index, name in enumerate(names)
    }}


def _class_test_semantic_ir(operands: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation": "if_class_of_is",
        "object": operands["object"],
        "class_predicates": [
            {"class_value": value,
             "match": "present when bit7 is set; absent otherwise"}
            for value in operands["classes"]
        ],
        "combination": "all predicates must match",
        "false_branch_displacement": operands["displacement"],
    }


def _draw_object_semantic_ir(operands: dict[str, Any]) -> dict[str, Any]:
    subopcode = int(operands["subopcode"])
    operation = {1: "draw_at_position", 2: "draw_state", 0x1F: "draw_current_state"}[subopcode & 0x1F]
    value: dict[str, Any] = {
        "operation": "draw_object",
        "object": operands["object"],
        "draw_operation": operation,
        "subopcode": subopcode,
        "parameter_flags": subopcode & 0xE0,
    }
    values = operands.get("values", [])
    if subopcode & 0x1F == 1:
        value["x"], value["y"] = values
    elif subopcode & 0x1F == 2:
        value["state"] = values[0]
    return value


def _set_var_range_semantic_ir(operands: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation": "set_var_range",
        "destination": operands["destination"],
        "count": operands["count"],
        "encoded_count": operands["encoded_count"],
        "value_width_bits": operands["value_width_bits"],
        "values": operands["values"],
    }


def _pseudo_room_semantic_ir(operands: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation": "pseudo_room_map",
        "mappings": [
            {"resource_room": resource, "pseudo_room": pseudo}
            for resource, pseudo in operands["room_map"]
        ],
    }


def _debug_semantic_ir(operands: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation": "debug_log",
        "value": operands["operand_0"],
        "effect": "diagnostic-only; does not mutate SCUMM game state",
    }


def _draw_box_semantic_ir(operands: dict[str, Any]) -> dict[str, Any]:
    values = operands["values"]
    return {
        "operation": "draw_box",
        "x1": values[0], "y1": values[1],
        "x2": values[2], "y2": values[3], "color": values[4],
        "auxiliary_parameter_flags": int(operands["aux_selector"]) & 0xE0,
        "effect": "draw SCUMM v5 debug-box primitive on the current graphics surface",
    }


def _system_ops_semantic_ir(operands: dict[str, Any]) -> dict[str, Any]:
    selector = int(operands["operand_0"])
    names = {1: "restart", 2: "pause", 3: "quit"}
    return {
        "operation": "system_operation",
        "selector": selector,
        "command": names.get(selector, "invalid_subopcode"),
        "valid_selector": selector in names,
        "invalid_command_behavior": "SCUMM v5 runtime error",
    }


def _sentence_semantic_ir(operands: dict[str, Any]) -> dict[str, Any]:
    verb = operands["verb"]
    if verb.get("mode") == "direct" and verb.get("value") == 0xFE:
        return {"operation": "cancel_sentence_queue", "verb": verb}
    return {
        "operation": "submit_sentence",
        "verb": verb,
        "object_a": operands["object_a"],
        "object_b": operands["object_b"],
    }


def _wait_semantic_ir(operands: dict[str, Any]) -> dict[str, Any]:
    kind = int(operands["subopcode"]) & 0x1F
    names = {1: "actor_stopped", 2: "message_acknowledged",
             3: "camera_arrived", 4: "sentence_finished"}
    result: dict[str, Any] = {"operation": "wait", "condition": names[kind],
                              "subopcode": int(operands["subopcode"])}
    if kind == 1:
        result["actor"] = operands["actor"]
    return result


def _read_structural_command(
    cursor: _Cursor, opcode: int, family: str, form: str, *, depth: int,
) -> tuple[int | None, dict[str, Any], int | None]:
    """Read selected variable-form v5 instructions and command lists."""
    value: dict[str, Any] = {}
    sub: int | None = None
    target: int | None = None

    def p8(selector: int, mask: int) -> dict[str, Any]:
        return cursor.byte_operand(selector, mask)

    def p16(selector: int, mask: int = 0x80) -> dict[str, Any]:
        return cursor.word_operand(selector, mask)

    def result() -> dict[str, Any]:
        return cursor.varref()

    def cstring() -> str:
        start = cursor.pc
        while cursor.u8() != 0:
            if cursor.pc - start > 4096:
                raise _StructuralUnknown("string exceeds structural bound")
        return cursor.data[start:cursor.pc].hex()

    if form == "sentence":
        verb = p8(opcode, 0x80)
        value["verb"] = verb
        if verb.get("mode") == "direct" and verb.get("value") == 0xFE:
            value["special"] = "stop_sentence"
        else:
            value["object_a"] = p16(opcode, 0x40)
            value["object_b"] = p16(opcode, 0x20)
    elif form == "room_ops":
        sub = cursor.u8()
        key = sub & 0x1F
        value["subopcode"] = sub
        fixed = {
            1: ("p16", "p16"), 2: (), 3: ("p16", "p16"),
            5: (), 6: (), 8: ("p8", "p8", "p8"),
            9: ("p8", "p8"), 10: ("p16",), 16: ("p8", "p8"),
        }
        if key in (1, 3):
            value["values"] = [p16(sub, 0x80), p16(sub, 0x40)]
        elif key == 2 or key in (5, 6):
            value["values"] = []
        elif key == 4:
            value["values"] = [p16(sub, mask) for mask in (0x80, 0x40, 0x20)]
            aux = cursor.u8()
            value["aux_selector"] = aux
            value["index"] = p8(aux, 0x80)
        elif key == 7:
            value["values"] = [p8(sub, 0x80), p8(sub, 0x40)]
            aux = cursor.u8()
            value["aux_selectors"] = [aux]
            value["values"].extend((p8(aux, 0x80), p8(aux, 0x40)))
            aux = cursor.u8()
            value["aux_selectors"].append(aux)
            value["values"].append(p8(aux, 0x40))
        elif key == 8:
            value["values"] = [p8(sub, mask) for mask in (0x80, 0x40, 0x20)]
        elif key == 9:
            value["values"] = [p8(sub, 0x80), p8(sub, 0x40)]
        elif key == 10:
            value["values"] = [p16(sub, 0x80)]
        elif key in (11, 12):
            value["values"] = [p16(sub, mask) for mask in (0x80, 0x40, 0x20)]
            aux = cursor.u8()
            value["aux_selector"] = aux
            value["values"].extend((p8(aux, 0x80), p8(aux, 0x40)))
        elif key in (13, 14):
            value["resource"] = p8(sub, 0x80)
            value["filename_hex"] = cstring()
        elif key == 15:
            value["resource"] = p8(sub, 0x80)
            aux = cursor.u8()
            value["aux_selectors"] = [aux]
            value["range"] = [p8(aux, 0x80), p8(aux, 0x40)]
            aux = cursor.u8()
            value["aux_selectors"].append(aux)
            value["time"] = p8(aux, 0x80)
        elif key == 16:
            value["values"] = [p8(sub, 0x80), p8(sub, 0x40)]
        else:
                raise _StructuralUnknown(f"roomOps sub-op {key} has unknown width", subopcode=sub)
    elif form == "actor_ops":
        value["actor"] = p8(opcode, 0x80)
        commands = []
        while True:
            selector = cursor.u8()
            if selector == 0xFF:
                break
            key = selector & 0x1F
            counts = {0: (0x80,), 1: (0x80,), 2: (0x80, 0x40),
                      3: (0x80,), 4: (0x80,), 5: (0x80, 0x40),
                      6: (0x80,), 7: (0x80, 0x40, 0x20), 8: (),
                      9: ("p16_80",), 10: (), 11: (0x80, 0x40),
                      12: (0x80,), 13: ("encoded_string",), 14: (0x80,),
                      16: (0x80,), 17: (0x80, 0x40), 18: (),
                      19: (0x80,), 20: (), 21: (), 22: (0x80,),
                      23: (0x80,)}
            if key not in counts:
                raise _StructuralUnknown(f"actorOps sub-op {key} has unknown width", subopcode=selector)
            widths = counts[key]
            args = ([p16(selector, 0x80)] if widths == ("p16_80",) else
                    [cursor.encoded_string().hex()] if widths == ("encoded_string",) else
                    [p8(selector, mask) for mask in widths])
            commands.append({"subopcode": selector, "values": args})
            if len(commands) > 256:
                raise _StructuralUnknown("actorOps list exceeds structural bound")
        value["commands"] = commands
    elif form == "verb_ops":
        value["verb"] = p8(opcode, 0x80)
        commands = []
        while True:
            selector = cursor.u8()
            if selector == 0xFF:
                break
            key = selector & 0x1F
            forms = {
                1: ("p16_80",), 2: ("encoded_string",), 3: (0x80,), 4: (0x80,),
                5: ("p16_80", "p16_40"), 6: (), 7: (), 8: (), 9: (),
                16: (0x80,), 17: (), 18: (0x80,), 19: (),
                20: ("p16_80",), 22: ("p16_80", 0x40), 23: (0x80,),
            }
            if key not in forms:
                raise _StructuralUnknown(f"verbOps sub-op {key} has unknown width", subopcode=selector)
            args = []
            for item in forms[key]:
                if isinstance(item, str) and item.startswith("p16_"):
                    args.append(p16(selector, int(item.split("_", 1)[1], 16)))
                elif item == "encoded_string":
                    args.append(cursor.encoded_string().hex())
                else:
                    args.append(p8(selector, item))
            commands.append({"subopcode": selector, "values": args})
            if len(commands) > 256:
                raise _StructuralUnknown("verbOps list exceeds structural bound")
        value["commands"] = commands
    elif form in {"print", "print_ego"}:
        if form == "print":
            value["actor"] = p8(opcode, 0x80)
        commands = []
        while True:
            selector = cursor.u8()
            if selector == 0xFF:
                break
            key = selector & 0x0F
            if key == 0:
                args = [cursor.word_operand(selector, 0x80),
                        cursor.word_operand(selector, 0x40)]
            elif key == 1:
                args = [p8(selector, 0x80)]
            elif key == 2:
                args = [p16(selector, 0x80)]
            elif key == 3:
                args = [p16(selector, 0x80), p16(selector, 0x40)]
            elif key in (4, 6, 7):
                args = []
            elif key == 8:
                args = [p16(selector, 0x80), p16(selector, 0x40)]
            elif key == 15:
                args = [cursor.encoded_string().hex()]
            else:
                raise _StructuralUnknown(f"print sub-op {key} has unknown width", subopcode=selector)
            commands.append({"subopcode": selector, "values": args})
            if key == 15:
                break
            if len(commands) > 256:
                raise _StructuralUnknown("print command list exceeds structural bound")
        value["commands"] = commands
    elif form == "set_var_range":
        value["destination"] = result()
        encoded_count = cursor.u8()
        count = encoded_count or 256
        value["encoded_count"] = encoded_count
        value["count"] = count
        value["value_width_bits"] = 16 if opcode & 0x80 else 8
        value["values"] = ([cursor.u16() for _ in range(count)] if opcode & 0x80
                           else [cursor.u8() for _ in range(count)])
    elif form == "set_class":
        value["object"] = p16(opcode, 0x80)
        classes = []
        while True:
            selector = cursor.u8()
            if selector == 0xFF:
                break
            classes.append(p16(selector, 0x80))
            if len(classes) > 256:
                raise _StructuralUnknown("setClass list exceeds structural bound")
        value["classes"] = classes
    elif form == "draw_object":
        value["object"] = p16(opcode, 0x80)
        sub = cursor.u8()
        key = sub & 0x1F
        value["subopcode"] = sub
        if key == 1:
            value["values"] = [p16(sub, 0x80), p16(sub, 0x40)]
        elif key == 2:
            value["values"] = [p16(sub, 0x80)]
        elif key == 0x1F:
            value["values"] = []
        else:
            raise _StructuralUnknown(f"drawObject sub-op {key} has unknown width", subopcode=sub)
    elif form == "draw_box":
        value["values"] = [p16(opcode, 0x80), p16(opcode, 0x40)]
        aux = cursor.u8()
        value["aux_selector"] = aux
        value["values"].extend((p16(aux, 0x80), p16(aux, 0x40), p8(aux, 0x20)))
    elif form == "matrix_ops":
        sub = cursor.u8()
        key = sub & 0x1F
        value["subopcode"] = sub
        if key in (1, 2, 3):
            value["values"] = [p8(sub, 0x80), p8(sub, 0x40)]
        elif key == 4:
            value["values"] = []
        else:
            raise _StructuralUnknown(f"matrixOps sub-op {key} has unknown width", subopcode=sub)
    elif form == "cursor_command":
        sub = cursor.u8()
        key = sub & 0x1F
        value["subopcode"] = sub
        counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0,
                  10: 2, 11: 3, 12: 1, 13: 1}
        if key == 14:
            items = []
            while True:
                selector = cursor.u8()
                if selector == 0xFF:
                    break
                items.append(cursor.word_operand(selector, 0x80))
                if len(items) > 32:
                    raise _StructuralUnknown("cursor color list exceeds structural bound")
            value["values"] = items
        elif key in counts:
            value["values"] = [p8(sub, mask) for mask in (0x80, 0x40, 0x20)[:counts[key]]]
        else:
            raise _StructuralUnknown(f"cursorCommand sub-op {key} has unknown width", subopcode=sub)
    elif form == "resource_routines":
        sub = cursor.u8()
        key = sub & 0x3F
        value["subopcode"] = sub
        if key in set(range(1, 17)) | {18, 19, 32, 33, 34}:
            value["resource"] = p8(sub, 0x80)
        elif key == 17:
            pass
        elif key == 20:
            value["resource"] = p8(sub, 0x80)
            value["object"] = cursor.word_operand(sub, 0x40)
        elif key in (35, 37):
            value["resource"] = p8(sub, 0x80)
            value["parameter_2"] = p8(sub, 0x40)
        elif key == 36:
            value["resource"] = p8(sub, 0x80)
            value["parameter_2"] = p8(sub, 0x40)
            value["literal"] = cursor.u8()
        else:
            raise _StructuralUnknown(f"resourceRoutines sub-op {key} has unknown width", subopcode=sub)
    elif form == "expression":
        value["result"] = result()
        operations = []
        while True:
            selector = cursor.u8()
            if selector == 0xFF:
                break
            key = selector & 0x1F
            operation: dict[str, Any] = {"subopcode": selector}
            if key == 1:
                operation["operand"] = cursor.word_operand(selector, 0x80)
            elif key in (2, 3, 4, 5):
                pass
            elif key == 6:
                nested = cursor.u8()
                nested_schema = opcode_schema(nested)
                if nested_schema is None:
                    raise _StructuralUnknown(f"expression embeds unknown opcode ${nested:02X}")
                nested_args, nested_target, nested_sub = _read_structural_family(
                    cursor, nested, nested_schema, depth=depth + 1,
                )
                operation["nested"] = {
                    "opcode": nested, "family": nested_schema.family,
                    "operands": nested_args, "target": nested_target,
                    "subopcode": nested_sub,
                }
            else:
                # ScummEngine_v5::o5_expression's default arm consumes the
                # token and performs no stack operation. Retain it explicitly
                # as a reserved token; do not lose the following boundary.
                operation["reserved"] = True
            operations.append(operation)
            if len(operations) > 256:
                raise _StructuralUnknown("expression exceeds structural bound")
        value["operations"] = operations
    elif form == "wait":
        sub = cursor.u8()
        key = sub & 0x1F
        value["subopcode"] = sub
        if key == 1:
            value["actor"] = p8(sub, 0x80)
        elif key not in (2, 3, 4):
            raise _StructuralUnknown(f"wait sub-op {key} has unknown width", subopcode=sub)
    elif form == "pseudo_room":
        pairs = []
        resource = cursor.u8()
        while True:
            room = cursor.u8()
            if room == 0:
                break
            pairs.append((resource, room))
            resource = cursor.u8()
            if len(pairs) > 256:
                raise _StructuralUnknown("pseudoRoom list exceeds structural bound")
        value["room_map"] = pairs
    elif form == "save_restore_verbs":
        sub = cursor.u8()
        value["subopcode"] = sub
        value["values"] = [p8(sub, mask) for mask in (0x80, 0x40, 0x20)]
    else:
        raise _StructuralUnknown(f"structural command form {form} is not implemented")
    return sub, value, target


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
    """Decode v5 instruction structure, keeping semantic gaps explicit."""
    instructions: list[InstructionIR] = []
    pc = 0
    opaque_from = None
    while pc < len(program):
        start = pc
        opcode = program[pc]
        schema = opcode_schema(opcode)
        cursor = _Cursor(program, pc + 1)
        operation = "unknown"
        operands: dict[str, Any] = {}
        branch_target = None
        semantic_status = "SEMANTIC_IR_AVAILABLE"
        structural_status = "STRUCTURALLY_DECODED"
        diagnostic = None
        subopcode = None
        try:
            if opcode in _STOP:
                operation = "stop_object_code"
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
            elif opcode == 0x27:
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = "string_ops"
                operands = _string_ops_semantic_ir(raw_operands)
            elif schema is not None and schema.family == "verbOps":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = "verb_ops"
                operands = _verb_ops_semantic_ir(raw_operands)
            elif schema is not None and schema.family == "roomOps":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = "room_ops"
                operands = _room_ops_semantic_ir(raw_operands)
            elif schema is not None and schema.family in {"stopScript", "isScriptRunning"}:
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = ("stop_script" if schema.family == "stopScript"
                             else "is_script_running")
                operands = _script_lifecycle_semantic_ir(schema.family, raw_operands)
            elif schema is not None and schema.family == "setObjectName":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = "set_object_name"
                operands = {
                    "object": raw_operands["operand_0"],
                    "encoded_name_hex": raw_operands["operand_1"],
                }
            elif schema is not None and schema.family == "actorOps":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = "actor_ops"
                operands = _actor_ops_semantic_ir(raw_operands)
            elif schema is not None and schema.family == "ifClassOfIs":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = "if_class_of_is"
                operands = _class_test_semantic_ir(raw_operands)
            elif schema is not None and schema.family == "drawObject":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = "draw_object"
                operands = _draw_object_semantic_ir(raw_operands)
            elif schema is not None and schema.family == "delayVariable":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = "delay_variable"
                operands = {"duration_variable": raw_operands["operand_0"]}
            elif schema is not None and schema.family == "pseudoRoom":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = "pseudo_room_map"
                operands = _pseudo_room_semantic_ir(raw_operands)
            elif schema is not None and schema.family == "debug":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = "debug_log"
                operands = _debug_semantic_ir(raw_operands)
            elif schema is not None and schema.family == "drawBox":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = "draw_box"
                operands = _draw_box_semantic_ir(raw_operands)
            elif schema is not None and schema.family == "systemOps":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = "system_operation"
                operands = _system_ops_semantic_ir(raw_operands)
            elif schema is not None and schema.family == "setVarRange":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = "set_var_range"
                operands = _set_var_range_semantic_ir(raw_operands)
            elif schema is not None and schema.family == "doSentence":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operands = _sentence_semantic_ir(raw_operands)
                operation = operands["operation"]
            elif schema is not None and schema.family == "beginOverride":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = "set_cutscene_override"
                operands = {"enabled": raw_operands["operand_0"]}
            elif schema is not None and schema.family == "wait":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operands = _wait_semantic_ir(raw_operands)
                operation = "wait"
            elif schema is not None and schema.family == "freezeScripts":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operands = _freeze_scripts_semantic_ir(raw_operands)
                operation = "freeze_scripts"
            elif schema is not None and schema.family == "saveRestoreVerbs":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operands = _save_restore_verbs_semantic_ir(raw_operands)
                operation = "save_restore_verbs"
            elif schema is not None and schema.family in _CAMERA_COMMAND_IR:
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = _CAMERA_COMMAND_IR[schema.family]
                operands = {"x": raw_operands["operand_0"]}
            elif schema is not None and schema.family in _RESULT_QUERY_IR:
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = _RESULT_QUERY_IR[schema.family][0]
                operands = _result_query_semantic_ir(schema.family, raw_operands)
            elif schema is not None and schema.family in {"setOwnerOf", "pickupObject"}:
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = ("set_object_owner" if schema.family == "setOwnerOf"
                             else "pickup_object")
                operands = _object_ownership_semantic_ir(schema.family, raw_operands)
            elif schema is not None and schema.family == "walkActorToActor":
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = "walk_actor_to_actor"
                operands = {
                    "actor": raw_operands["operand_0"],
                    "target_actor": raw_operands["operand_1"],
                    "distance": raw_operands["operand_2"],
                }
            elif schema is not None and schema.family in _SIMPLE_ACTOR_IR:
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = _SIMPLE_ACTOR_IR[schema.family][0]
                operands = _simple_actor_semantic_ir(schema.family, raw_operands)
            elif schema is not None and schema.family in {
                "add", "subtract", "multiply", "divide", "and", "or",
            }:
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = schema.family
                operands["destination"] = raw_operands["operand_0"]
                operands["right_operand"] = raw_operands["operand_1"]
            elif opcode == 0xAC:
                raw_operands, branch_target, subopcode = _read_structural_family(
                    cursor, opcode, schema,
                )
                operation = "expression"
                operands = _expression_semantic_ir(raw_operands)
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
        except (ValueError, IndexError) as semantic_error:
            fallback_cursor = _Cursor(program, start + 1)
            try:
                if schema is None:
                    raise _StructuralUnknown(
                        "instruction width is not in the SCUMM v5 opcode schema"
                    ) from semantic_error
                operands, branch_target, subopcode = _read_structural_family(
                    fallback_cursor, opcode, schema,
                )
                cursor = fallback_cursor
                operation = f"structural_only:{schema.family}"
                semantic_status = "SEMANTIC_UNSUPPORTED"
                diagnostic = f"semantic IR unavailable: {semantic_error}"
            except (ValueError, IndexError) as structural_error:
                opaque_from = pc_base + start
                text = str(structural_error)
                truncated = text.startswith("truncated") or "truncated" in text.lower()
                structural_status = "TRUNCATED" if truncated else "STRUCTURAL_UNKNOWN"
                instructions.append(InstructionIR(
                    pc_base + start, opcode, "opaque_bytecode_tail", (), program[start:].hex(),
                    source_offset + start, False, None, text,
                    None if schema is None else schema.opcode,
                    None if schema is None else schema.family,
                    0 if schema is None else opcode & schema.parameter_flag_mask,
                    0, program[start + 1:].hex(), getattr(structural_error, "subopcode", None),
                    structural_status, "SEMANTIC_UNKNOWN",
                    None if schema is None else schema.semantic_capability,
                    "UNKNOWN", None, (),
                    0 if schema is None else opcode ^ schema.opcode,
                ))
                break
        pc = cursor.pc
        flow = (schema.control_flow if schema is not None else "UNKNOWN")
        if operation == "jump":
            flow = "UNCONDITIONAL_BRANCH"
        elif operation.startswith("branch_"):
            flow = "CONDITIONAL_BRANCH"
        elif operation == "stop_object_code":
            flow = "TERMINATOR"
        elif operation == "stop_script":
            script_number = operands["script_number"]
            if script_number["mode"] == "direct":
                flow = ("TERMINATOR" if script_number["value"] == 0
                        else "FALLTHROUGH")
            else:
                flow = "CONDITIONAL_TERMINATOR"
        next_targets = () if branch_target is None else (pc_base + branch_target,)
        instructions.append(InstructionIR(
            pc_base + start, opcode, operation, tuple(sorted(operands.items())),
            program[start:pc].hex(), source_offset + start, True,
            None if branch_target is None else pc_base + branch_target,
            diagnostic,
            None if schema is None else schema.opcode,
            None if schema is None else schema.family,
            0 if schema is None else opcode & schema.parameter_flag_mask,
            pc - start, program[start + 1:pc].hex(), subopcode,
            structural_status, semantic_status,
            None if schema is None else schema.semantic_capability,
            flow,
            flow not in {"UNCONDITIONAL_BRANCH", "TERMINATOR", "UNKNOWN"},
            next_targets,
            0 if schema is None else opcode ^ schema.opcode,
        ))
        if operation == "stop_object_code":
            # Object-code records end here; unlike stopScript(0), this is the
            # resource-level terminator for the current object program.
            # stopScript(0) only terminates the current execution path: a
            # conditional branch may target a later basic block in the same
            # global-script body, so structural census must continue scanning
            # the source body after recording its TERMINATOR control flow.
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
        "src/same/engines/scumm_v5/game_analysis.py",
        "src/same/engines/scumm_v5/program_units.py",
        "src/same/engines/scumm_v5/selector_demand.py",
        "src/same/engines/scumm_v5/residency.py",
        "src/same/engines/scumm_v5/residency_contract.py",
        "src/same/engines/scumm_v5/v5_opcode_schema.py",
        "src/same/engines/scumm_v5/room.py",
        "src/same/engines/scumm_v5/resources.py",
        "src/same/engines/scumm_v5/cooked_room.py",
        "src/same/engines/scumm_v5/text.py",
        "src/same/engines/scumm_v5/policy.py",
        "src/same/profile.py",
        "src/same/resources.py",
        "tools/compile_scumm_game.py",
    )
    return {
        component: sha256((repository_root / component).read_bytes())
        for component in components
    }


def compiler_source_sha256() -> str:
    """Identity of compiler and reused front-end/backend-record sources."""
    return sha256(_json_bytes(compiler_source_manifest()))
