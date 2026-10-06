"""SCUMM v5 opcode-family and structural operand schema.

This table describes the byte-level dialect, not runtime support.  The active
family assignments follow ``ScummEngine_v5::setupOpcodes``; parameter masks
and operand forms follow the corresponding v5 fetch routines.  Game-specific
workarounds are intentionally excluded.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OpcodeSchema:
    opcode: int
    family: str
    operand_form: str | None
    parameter_flag_mask: int
    parameter_flags: int
    control_flow: str
    semantic_capability: str


# Opcode bytes that share a handler family.  Bits 7..5 are parameter flags
# where that family's operand form says so; they are not separate semantics.
_FAMILY_VARIANTS: dict[str, tuple[int, ...]] = {
    "actorFollowCamera": (0x52, 0xD2),
    "actorFromPos": (0x15, 0x55, 0x95, 0xD5),
    "actorOps": (0x13, 0x53, 0x93, 0xD3),
    "add": (0x5A, 0xDA), "and": (0x17, 0x97),
    "animateActor": (0x11, 0x51, 0x91, 0xD1),
    "beginOverride": (0x58,), "breakHere": (0x80,),
    "chainScript": (0x42, 0xC2), "cursorCommand": (0x2C,),
    "cutscene": (0x40,), "debug": (0x6B, 0xEB),
    "decrement": (0xC6,), "delay": (0x2E,), "delayVariable": (0x2B,),
    "divide": (0x5B, 0xDB),
    "doSentence": (0x19, 0x39, 0x59, 0x79, 0x99, 0xB9, 0xD9, 0xF9),
    "drawBox": (0x3F, 0x7F, 0xBF, 0xFF), "drawObject": (0x05, 0x85),
    "dummy": (0xA7,), "endCutscene": (0xC0,), "equalZero": (0x28,),
    "expression": (0xAC,), "faceActor": (0x09, 0x49, 0x89, 0xC9),
    "findInventory": (0x3D, 0x7D, 0xBD, 0xFD),
    "findObject": (0x35, 0x75, 0xB5, 0xF5),
    "freezeScripts": (0x60, 0xE0),
    "getActorCostume": (0x71, 0xF1), "getActorElevation": (0x06, 0x86),
    "getActorFacing": (0x63, 0xE3), "getActorMoving": (0x56, 0xD6),
    "getActorRoom": (0x03, 0x83), "getActorScale": (0x3B, 0xBB),
    "getActorWalkBox": (0x7B, 0xFB), "getActorWidth": (0x6C, 0xEC),
    "getActorX": (0x43, 0xC3), "getActorY": (0x23, 0xA3),
    "getAnimCounter": (0x22, 0xA2), "getClosestObjActor": (0x66, 0xE6),
    "getDist": (0x34, 0x74, 0xB4, 0xF4),
    "getInventoryCount": (0x31, 0xB1), "getObjectOwner": (0x10, 0x90),
    "getObjectState": (0x0F, 0x8F), "getRandomNr": (0x16, 0x96),
    "getStringWidth": (0x67, 0xE7),
    "getVerbEntrypoint": (0x0B, 0x4B, 0x8B, 0xCB),
    "ifClassOfIs": (0x1D, 0x9D), "increment": (0x46,),
    "isActorInBox": (0x1F, 0x5F, 0x9F, 0xDF),
    "isEqual": (0x48, 0xC8), "isGreater": (0x78, 0xF8),
    "isGreaterEqual": (0x04, 0x84), "isLess": (0x44, 0xC4),
    "isLessEqual": (0x38, 0xB8), "isNotEqual": (0x08, 0x88),
    "isScriptRunning": (0x68, 0xE8), "isSoundRunning": (0x7C, 0xFC),
    "jumpRelative": (0x18,), "lights": (0x70, 0xF0),
    "loadRoom": (0x72, 0xF2), "loadRoomWithEgo": (0x24, 0x64, 0xA4, 0xE4),
    "matrixOps": (0x30, 0xB0), "move": (0x1A, 0x9A),
    "multiply": (0x1B, 0x9B), "notEqualZero": (0xA8,),
    "or": (0x57, 0xD7), "panCameraTo": (0x12, 0x92),
    "pickupObject": (0x25, 0x65, 0xA5, 0xE5),
    "print": (0x14, 0x94), "printEgo": (0xD8,),
    "pseudoRoom": (0xCC,),
    "putActor": (0x01, 0x21, 0x41, 0x61, 0x81, 0xA1, 0xC1, 0xE1),
    "putActorAtObject": (0x0E, 0x4E, 0x8E, 0xCE),
    "putActorInRoom": (0x2D, 0x6D, 0xAD, 0xED),
    "resourceRoutines": (0x0C, 0x8C),
    "roomOps": (0x33, 0x73, 0xB3, 0xF3),
    "saveRestoreVerbs": (0xAB,), "setCameraAt": (0x32, 0xB2),
    "setClass": (0x5D, 0xDD), "setObjectName": (0x54, 0xD4),
    "setOwnerOf": (0x29, 0x69, 0xA9, 0xE9),
    "setState": (0x07, 0x47, 0x87, 0xC7), "setVarRange": (0x26, 0xA6),
    "soundKludge": (0x4C,), "startMusic": (0x02, 0x82),
    "startObject": (0x37, 0x77, 0xB7, 0xF7),
    "startScript": (0x0A, 0x2A, 0x4A, 0x6A, 0x8A, 0xAA, 0xCA, 0xEA),
    "startSound": (0x1C, 0x9C), "stopMusic": (0x20,),
    "stopObjectCode": (0x00, 0xA0), "stopObjectScript": (0x6E, 0xEE),
    "stopScript": (0x62, 0xE2), "stopSound": (0x3C, 0xBC),
    "stringOps": (0x27,), "subtract": (0x3A, 0xBA),
    "systemOps": (0x98,), "verbOps": (0x7A, 0xFA), "wait": (0xAE,),
    "walkActorTo": (0x1E, 0x3E, 0x5E, 0x7E, 0x9E, 0xBE, 0xDE, 0xFE),
    "walkActorToActor": (0x0D, 0x4D, 0x8D, 0xCD),
    "walkActorToObject": (0x36, 0x76, 0xB6, 0xF6),
}


_FAMILY_FOR_OPCODE = {
    opcode: family for family, opcodes in _FAMILY_VARIANTS.items()
    for opcode in opcodes
}

# Forms in this table are a byte-level grammar.  They deliberately do not
# assert that the SAME IR, backend, host, or SNES runtime implements a family.
_OPERAND_FORMS = {
    "actorFollowCamera": ("p8_80", "actor"),
    "actorFromPos": ("result,p16_80,p16_40", "actors"),
    "actorOps": ("actor_ops", "actors"),
    "add": ("result,p16_80", "variables"), "and": ("result,p16_80", "variables"),
    "animateActor": ("p8_80,p8_40", "actors"),
    "beginOverride": ("u8", "cutscenes"), "breakHere": ("none", "scheduler"),
    "chainScript": ("p8_80,word_args", "script_lifecycle"),
    "cursorCommand": ("cursor_command", "input_ui"),
    "cutscene": ("word_args", "cutscenes"), "debug": ("p16", "debug"),
    "decrement": ("result", "variables"), "delay": ("u16,u8", "timers"),
    "delayVariable": ("varref", "timers"), "divide": ("result,p16_80", "variables"),
    "doSentence": ("sentence", "verbs"), "drawBox": ("draw_box", "graphics"),
    "drawObject": ("draw_object", "objects"), "dummy": ("none", "unknown"),
    "endCutscene": ("none", "cutscenes"), "equalZero": ("varref,rel16", "control_flow"),
    "expression": ("expression", "variables"), "faceActor": ("p8_80,p16_40", "actors"),
    "findInventory": ("result,p8_80,p8_40", "inventory"),
    "findObject": ("result,p8_80,p8_40", "objects"),
    "freezeScripts": ("p8_80", "script_lifecycle"),
    "getActorCostume": ("result,p8_80", "actors"),
    "getActorElevation": ("result,p8_80", "actors"),
    "getActorFacing": ("result,p8_80", "actors"),
    "getActorMoving": ("result,p8_80", "actors"),
    "getActorRoom": ("result,p8_80", "actors"),
    "getActorScale": ("result,p8_80", "actors"),
    "getActorWalkBox": ("result,p8_80", "actors"),
    "getActorWidth": ("result,p8_80", "actors"),
    "getActorX": ("result,p16_80", "actors"),
    "getActorY": ("result,p16_80", "actors"),
    "getAnimCounter": ("result,p8_80", "actors"),
    "getClosestObjActor": ("result,p16_80", "actors"),
    "getDist": ("result,p16_80,p16_40", "objects"),
    "getInventoryCount": ("result,p8_80", "inventory"),
    "getObjectOwner": ("result,p16_80", "objects"),
    "getObjectState": ("result,p16_80", "objects"),
    "getRandomNr": ("result,p8_80", "random"),
    "getStringWidth": ("result,p8_80", "text"),
    "getVerbEntrypoint": ("result,p16_80,p16_40", "verbs"),
    "ifClassOfIs": ("if_class_of_is", "objects"), "increment": ("result", "variables"),
    "isActorInBox": ("p8_80,p8_40,rel16", "actors"),
    "isEqual": ("varref,p16_80,rel16", "control_flow"),
    "isGreater": ("varref,p16_80,rel16", "control_flow"),
    "isGreaterEqual": ("varref,p16_80,rel16", "control_flow"),
    "isLess": ("varref,p16_80,rel16", "control_flow"),
    "isLessEqual": ("varref,p16_80,rel16", "control_flow"),
    "isNotEqual": ("varref,p16_80,rel16", "control_flow"),
    "isScriptRunning": ("result,p8_80", "script_lifecycle"),
    "isSoundRunning": ("result,p8_80", "audio"), "jumpRelative": ("rel16", "control_flow"),
    "lights": ("p8_80,u8,u8", "room"), "loadRoom": ("p8_80", "room_transitions"),
    "loadRoomWithEgo": ("p16_80,p8_40,i16,i16", "room_transitions"),
    "matrixOps": ("matrix_ops", "walkboxes"), "move": ("result,p16_80", "variables"),
    "multiply": ("result,p16_80", "variables"), "notEqualZero": ("varref,rel16", "control_flow"),
    "or": ("result,p16_80", "variables"), "panCameraTo": ("p16_80", "camera"),
    "pickupObject": ("p16_80,p8_40", "inventory"), "print": ("print", "text"),
    "printEgo": ("print_ego", "text"), "pseudoRoom": ("pseudo_room", "room"),
    "putActor": ("p8_80,p16_40,p16_20", "actors"),
    "putActorAtObject": ("p8_80,p16_40", "actors"),
    "putActorInRoom": ("p8_80,p8_40", "actors"),
    "resourceRoutines": ("resource_routines", "resource_services"),
    "roomOps": ("room_ops", "room"), "saveRestoreVerbs": ("save_restore_verbs", "verbs"),
    "setCameraAt": ("p16_80", "camera"), "setClass": ("set_class", "objects"),
    "setObjectName": ("p16_80,encoded_string", "objects"),
    "setOwnerOf": ("p16_80,p8_40", "inventory"),
    "setState": ("p16_80,p8_40", "objects"), "setVarRange": ("set_var_range", "variables"),
    "soundKludge": ("word_args", "audio"), "startMusic": ("p8_80", "audio"),
    "startObject": ("p16_80,p8_40,word_args", "script_lifecycle"),
    "startScript": ("p8_80,word_args", "script_lifecycle"),
    "startSound": ("p8_80", "audio"), "stopMusic": ("none", "audio"),
    "stopObjectCode": ("none", "script_lifecycle"),
    "stopObjectScript": ("p16_80", "script_lifecycle"),
    "stopScript": ("p8_80", "script_lifecycle"), "stopSound": ("p8_80", "audio"),
    "stringOps": ("string_ops", "strings"), "subtract": ("result,p16_80", "variables"),
    "systemOps": ("u8", "system"), "verbOps": ("verb_ops", "verbs"),
    "wait": ("wait", "scheduler"),
    "walkActorTo": ("p8_80,p16_40,p16_20", "actors"),
    "walkActorToActor": ("p8_80,p8_40,u8", "actors"),
    "walkActorToObject": ("p8_80,p16_40", "actors"),
}

_CONDITIONAL_FAMILIES = frozenset({
    "equalZero", "notEqualZero", "isEqual", "isNotEqual", "isGreater",
    "isGreaterEqual", "isLess", "isLessEqual", "ifClassOfIs", "isActorInBox",
})
_TERMINATOR_FAMILIES = frozenset({"chainScript", "stopObjectCode"})
_PARAMETER_FLAG_MASKS = {
    "ifClassOfIs": 0x80, "doSentence": 0xE0, "drawObject": 0x80,
    "drawBox": 0xC0, "setVarRange": 0x80, "print": 0x80,
    "setClass": 0x80, "verbOps": 0x80,
}


def opcode_schema(opcode: int) -> OpcodeSchema | None:
    family = _FAMILY_FOR_OPCODE.get(opcode)
    if family is None:
        return None
    form = _OPERAND_FORMS.get(family)
    flags = _PARAMETER_FLAG_MASKS.get(family, 0)
    if form and not flags:
        for token in form[0].split(","):
            if token == "p16":
                flags |= 0x80
            elif token.startswith(("p8_", "p16_")):
                flags |= int(token.split("_", 1)[1], 16)
    flow = ("TERMINATOR" if family in _TERMINATOR_FAMILIES else
            "UNCONDITIONAL_BRANCH" if family == "jumpRelative" else
            "CONDITIONAL_BRANCH" if family in _CONDITIONAL_FAMILIES else "FALLTHROUGH")
    return OpcodeSchema(min(_FAMILY_VARIANTS[family]), family,
                        form[0] if form else None, flags, opcode & flags, flow,
                        form[1] if form else "unknown")


def schema_coverage() -> dict[str, int]:
    variant_assignments = sum(len(opcodes) for opcodes in _FAMILY_VARIANTS.values())
    return {"registered_v5_opcode_bytes": len(_FAMILY_FOR_OPCODE),
            "unregistered_opcode_bytes": 256 - len(_FAMILY_FOR_OPCODE),
            "family_variant_assignments": variant_assignments,
            "family_assignment_collisions": variant_assignments - len(_FAMILY_FOR_OPCODE),
            "families": len(_FAMILY_VARIANTS),
            "families_with_operand_forms": len(_OPERAND_FORMS)}
