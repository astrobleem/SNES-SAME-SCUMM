#!/usr/bin/env python3
"""Generate deterministic, copyright-free SCUMM v5 and AGI engine fixtures."""

from __future__ import annotations

from pathlib import Path
import json
import struct

ROOT = Path(__file__).resolve().parents[1]


def scumm_script() -> bytes:
    # Real SCUMM v5 opcode numbers:
    # startMusic 1; loadRoom 0; var[20]++; breakHere; jump back to increment.
    return bytes(
        [
            0x02,
            0x01,
            0x72,
            0x00,
            0x46,
            0x14,
            0x00,
            0x80,
            0x18,
            0xF9,
            0xFF,
        ]
    )


def scumm_core_conformance_script() -> bytes:
    """Copyright-free SCUMM v5 control-flow/arithmetic fixture.

    Opcode numbers and operand shapes follow upstream ScummVM's v5 dispatch and
    handlers.  The script has no game resources, cursor, actors, or room policy.
    """
    return bytes(
        [
            0x1A, 0x01, 0x00, 0x0A, 0x00,  # v1 = 10
            0x5A, 0x01, 0x00, 0x05, 0x00,  # v1 += 5
            0x3A, 0x01, 0x00, 0x03, 0x00,  # v1 -= 3
            0x48, 0x01, 0x00, 0x0C, 0x00, 0x05, 0x00,  # true: fall through
            0x1A, 0x02, 0x00, 0x11, 0x11,  # v2 = $1111
            0x48, 0x01, 0x00, 0x63, 0x00, 0x05, 0x00,  # false: skip 5
            0x1A, 0x02, 0x00, 0x22, 0x22,  # skipped
            0x80,                          # breakHere
            0x46, 0x01, 0x00,              # v1++
            0x2E, 0x02, 0x00, 0x00,        # delay 2
            0x9A, 0x03, 0x00, 0x01, 0x00,  # v3 = v1
            0x18, 0x05, 0x00,              # skip 5
            0x1A, 0x04, 0x00, 0xAD, 0xDE,  # skipped
            0x00,                          # stopObjectCode
        ]
    )


def scumm_c2_success_script() -> bytes:
    """Extended signed arithmetic, comparison, and variable-delay fixture."""
    return bytes(
        [
            0x1A, 0x01, 0x00, 0xF4, 0xFF,  # v1 = -12
            0x1B, 0x01, 0x00, 0xFD, 0xFF,  # v1 *= -3 -> 36
            0x5B, 0x01, 0x00, 0x05, 0x00,  # v1 /= 5 -> 7
            0x17, 0x01, 0x00, 0x06, 0x00,  # v1 &= 6 -> 6
            0x57, 0x01, 0x00, 0x08, 0x00,  # v1 |= 8 -> 14
            0xC6, 0x01, 0x00,              # v1-- -> 13
            0x1A, 0x02, 0x00, 0xFE, 0xFF,  # v2 = -2
            0x44, 0x02, 0x00, 0xFD, 0xFF, 0x05, 0x00,  # -3 < -2
            0x1A, 0x03, 0x00, 0x11, 0x11,              # v3 = $1111
            0x78, 0x02, 0x00, 0xFD, 0xFF, 0x05, 0x00,  # -3 > -2: skip
            0x1A, 0x03, 0x00, 0xAD, 0xDE,              # skipped
            0x38, 0x02, 0x00, 0xFE, 0xFF, 0x05, 0x00,  # -2 <= -2
            0x04, 0x01, 0x00, 0x0D, 0x00, 0x05, 0x00,  # 13 >= 13
            0x08, 0x01, 0x00, 0x63, 0x00, 0x05, 0x00,  # 13 != 99
            0x28, 0x04, 0x00, 0x05, 0x00,              # v4 == 0
            0xA8, 0x01, 0x00, 0x05, 0x00,              # v1 != 0
            0x1A, 0x05, 0x00, 0x02, 0x00,              # v5 = 2
            0x2B, 0x05, 0x00,                          # delayVariable(v5)
            0x9A, 0x06, 0x00, 0x01, 0x00,              # v6 = v1
            0x00,                                       # stopObjectCode
        ]
    )


def scumm_c2_fixtures() -> list[tuple[str, bytes]]:
    return [
        ("extended", scumm_c2_success_script()),
        ("unknown_opcode", bytes([0x2F])),
        ("bad_variable", bytes([0x1A, 0x00, 0x08, 0x01, 0x00])),
        ("truncated_operand", bytes([0x1A, 0x01])),
        ("budget_exhaustion", bytes([0x46, 0x00, 0x00]) * 32 + bytes([0x00])),
        ("division_by_zero", bytes([0x1A, 0x01, 0x00, 0x09, 0x00, 0x5B, 0x01, 0x00, 0x00, 0x00])),
        ("jump_escape", bytes([0x18, 0xFF, 0x7F])),
        ("delay_range", bytes([0x2E, 0x00, 0x00, 0x01])),
        ("c3_operands", scumm_c3_operand_script()),
        ("c3_scheduler", bytes([0x00])),
        ("c3_slot0", bytes([0x2E, 0x02, 0x00, 0x00, 0x46, 0x0A, 0x00, 0x80, 0x18, 0xF9, 0xFF])),
        ("c3_slot1", bytes([0x46, 0x0B, 0x00, 0x80, 0x18, 0xF9, 0xFF])),
        ("c3_bit_variable", bytes([0x1A, 0x00, 0x80, 0x01, 0x00, 0x00])),
        ("c4_lifecycle", scumm_c4_lifecycle_script()),
        ("c4_child2", bytes([0x9A, 0x01, 0x00, 0x00, 0x40, 0x46, 0x00, 0x40, 0x80])),
        ("c4_child3", bytes([0x9A, 0x02, 0x00, 0x00, 0x40, 0x46, 0x00, 0x40,
                             0x9A, 0x03, 0x00, 0x00, 0x40, 0x62, 0x00])),
        ("c4_child4", bytes([0x9A, 0x04, 0x00, 0x00, 0x40, 0x80])),
        ("c4_capacity", bytes([0x2A, 0x02, 0xFF])),
        ("c5_scheduler", scumm_c5_scheduler_script()),
        ("c5_child5", bytes([0x46, 0x0A, 0x00, 0x80, 0x18, 0xF9, 0xFF])),
        ("c5_child6", bytes([0x46, 0x0B, 0x00, 0x80, 0x18, 0xF9, 0xFF])),
        ("c5_child7", bytes([0x46, 0x0C, 0x00, 0x80, 0x18, 0xF9, 0xFF])),
        ("c6_scheduler", scumm_c6_scheduler_script()),
        ("c6_chain10", bytes([0x9A, 0x00, 0x00, 0x00, 0x40,
                               0x42, 0x0C, 0x80, 0x00, 0x40, 0xFF,
                               0x1A, 0x0F, 0x00, 0x01, 0x00, 0x00])),
        ("c6_target12", bytes([0x9A, 0x01, 0x00, 0x00, 0x40, 0x80,
                                0x18, 0xF7, 0xFF])),
        ("c6_chain11", bytes([0x1A, 0x04, 0x00, 0x0D, 0x00,
                               0xC2, 0x04, 0x00, 0x80, 0x00, 0x40, 0xFF,
                               0x1A, 0x0F, 0x00, 0x02, 0x00, 0x00])),
        ("c6_target13", bytes([0x9A, 0x07, 0x00, 0x00, 0x40, 0x80])),
        ("c6_missing", bytes([0x42, 0x0E, 0xFF])),
        ("c6_capacity", bytes([0x42, 0x0C, 0xFF])),
        ("s5_binding", scumm_s5_binding_script()),
        ("c7_cursor_bits", scumm_c7_cursor_bits_script()),
        ("c8_string_ops", scumm_c8_string_ops_script()),
        ("c9_set_var_range", scumm_c9_set_var_range_script()),
        ("c10_room_ops", scumm_c10_room_ops_script()),
        ("c11_random", scumm_c11_random_script()),
        ("c12_pseudo_room", scumm_c12_pseudo_room_script()),
        ("c13_resource_routines", scumm_c13_resource_routines_script()),
        ("c14_actor_ops", scumm_c14_actor_ops_script()),
        ("c15_actor_follow_camera", scumm_c15_actor_follow_camera_script()),
        ("c16_set_class", scumm_c16_set_class_script()),
        ("c17_verb_ops", scumm_c17_verb_ops_script()),
        ("c18_expression", scumm_c18_expression_script()),
        ("c19_cutscene", scumm_c19_cutscene_script()),
        ("c20_do_sentence", scumm_c20_do_sentence_script()),
        ("c21_draw_object", scumm_c21_draw_object_script()),
        ("c22_null_room", scumm_c22_null_room_script()),
        ("c23_print", scumm_c23_print_script()),
        ("c24_override_sentinel", scumm_c24_override_sentinel_script()),
        ("c25_sound_kludge", scumm_c25_sound_kludge_script()),
        ("c26_save_restore_verbs", scumm_c26_save_restore_verbs_script()),
        ("c28_animate_actor", scumm_c28_animate_actor_script()),
    ]


def scumm_s5_binding_script() -> bytes:
    """Two-tick active-engine semantic and normalized-audio fixture."""
    return bytes(
        [
            0x1A, 0x00, 0x00, 0x34, 0x12,  # v0 = $1234
            0x02, 0x07,                    # startMusic(7)
            0x1C, 0x09,                    # startSound(9)
            0x80,                          # breakHere
            0x3C, 0x09,                    # stopSound(9)
            0x20,                          # stopMusic
            0x00,                          # stopObjectCode
        ]
    )


def scumm_c7_cursor_bits_script() -> bytes:
    """Bit variables and the complete v5 cursorCommand operand surface."""
    return bytes(
        [
            0x1A, 0x05, 0x80, 0x01, 0x00,        # bit[5] = 1
            0x9A, 0x00, 0x00, 0x05, 0x80,        # v0 = bit[5]
            0x1A, 0x01, 0x00, 0x07, 0x00,        # v1 = 7
            0x2C, 0x8D, 0x01, 0x00,              # charset = v1
            0x2C, 0x02,                          # cursor off
            0x2C, 0x05,                          # cursor soft-on
            0x2C, 0x04,                          # userput off
            0x2C, 0x07,                          # userput soft-on
            0x2C, 0x0A, 0x03, 0x04,              # cursor image 3, char 4
            0x2C, 0x0B, 0x03, 0x05, 0x06,        # hotspot cursor 3 at 5,6
            0x2C, 0x0C, 0x09,                    # active cursor 9
            0x2C, 0x0E, 0x00, 0x0A, 0x00,        # charset colors [10, v1]
            0x80, 0x01, 0x00, 0xFF,
            0x80,
        ]
    )


def scumm_c8_string_ops_script() -> bytes:
    """All five v5 stringOps subcommands with encoded text controls."""
    return bytes(
        [
            0x1A, 0x00, 0x00, 0x05, 0x00,              # v0 = string id 5
            0x1A, 0x01, 0x00, 0x01, 0x00,              # v1 = index 1
            0x1A, 0x02, 0x00, 0x5A, 0x00,              # v2 = 'Z'
            0x1A, 0x03, 0x00, 0x0C, 0x00,              # v3 = allocation size 12
            0x27, 0xC5, 0x00, 0x00, 0x03, 0x00,        # create(v0, v3)
            0x27, 0x81, 0x00, 0x00,                    # load(v0, encoded text)
            0x41, 0x42, 0xFF, 0x04, 0x34, 0x12, 0x43, 0x00,
            0x27, 0xC4, 0x04, 0x00, 0x00, 0x00, 0x01, 0x00,  # v4 = str[v0][v1]
            0x27, 0xE3, 0x00, 0x00, 0x01, 0x00, 0x02, 0x00,  # str[v0][v1] = v2
            0x27, 0x42, 0x06, 0x00, 0x00,              # copy(6, v0)
            0x27, 0x04, 0x05, 0x00, 0x06, 0x01,        # v5 = str[6][1]
            0x27, 0x04, 0x06, 0x00, 0x06, 0x03,        # v6 = control code 4
            0x27, 0x05, 0x07, 0x04,                    # create(7, 4)
            0x27, 0x02, 0x07, 0x08,                    # copy missing 8 -> nukes 7
            0x80,
        ]
    )


def scumm_c9_set_var_range_script() -> bytes:
    """Byte/word ranges with indexed globals, locals, and packed bits."""
    return bytes(
        [
            0x1A, 0x00, 0x00, 0x02, 0x00,              # v0 = index 2
            0x26, 0x04, 0x20, 0x00, 0x20, 0x03,        # v[4+v0] = [1,255,128]
            0x01, 0xFF, 0x80,
            0xA6, 0x00, 0x40, 0x03,                    # local[0..2] = [-1,32767,-32768]
            0xFF, 0xFF, 0xFF, 0x7F, 0x00, 0x80,
            0x26, 0x05, 0x80, 0x03, 0x00, 0x02, 0x01,  # bit[5..7] = [0,1,1]
            0x80,
        ]
    )


def scumm_c10_room_ops_script() -> bytes:
    """Complete v5 roomOps intent surface, including auxiliary strings."""
    return bytes(
        [
            0x27, 0x01, 0x05, 0x41, 0x42, 0x43, 0x00,  # string 5 = "ABC"
            0x33, 0x01, 0x64, 0x00, 0xF4, 0x01,        # scroll 100..500
            0x33, 0x03, 0x10, 0x00, 0xB8, 0x00,        # screen 16..184
            0x33, 0x04, 10, 0, 20, 0, 30, 0, 0, 7,    # palette[7] = (10,20,30)
            0x33, 0x05,                                # shake on
            0x33, 0x07, 100, 20, 0, 200, 180, 0, 2,   # scale slot 2
            0x33, 0x08, 128, 4, 9,                     # intensity
            0x33, 0x09, 1, 3,                          # temporary save request -> slot 99
            0x33, 0x0A, 0x34, 0x12,                    # fade effect $1234
            0x33, 0x0B, 100, 0, 110, 0, 120, 0, 0, 2, 8,
            0x33, 0x0C, 50, 0, 60, 0, 70, 0, 0, 3, 9,
            0x33, 0x0D, 5, 0x61, 0x75, 0x78, 0,        # save string 5 as "aux"
            0x27, 0x03, 5, 0, 0x5A,                    # mutate string[5][0]
            0x33, 0x0E, 5, 0x61, 0x75, 0x78, 0,        # load restores "ABC"
            0x33, 0x0F, 6, 0, 2, 10, 0, 12,            # transform
            0x33, 0x10, 3, 2,                          # cycle 3 speed 2
            0x33, 0x06,                                # shake off
            0x33, 0x05,                                # shake on
            0x80,
        ]
    )


def scumm_c11_random_script() -> bytes:
    """Inclusive direct/variable random bounds with varied result storage."""
    return bytes(
        [
            0x1A, 0x00, 0x00, 0x09, 0x00,  # v0 = variable maximum 9
            0x16, 0x01, 0x00, 10,          # v1 = random(0..10)
            0x96, 0x02, 0x00, 0x00, 0x00, # v2 = random(0..v0)
            0x16, 0x03, 0x00, 0,           # v3 = random(0..0)
            0x16, 0x04, 0x00, 255,         # v4 = random(0..255)
            0x96, 0x00, 0x40, 0x00, 0x00, # local[0] = random(0..v0)
            0x80,
        ]
    )


def scumm_c12_pseudo_room_script() -> bytes:
    """Pseudo-room mapping, ignored low entries, overwrite, and tick survival."""
    return bytes(
        [
            0xCC, 0x12, 0x80, 0x81, 0x7F, 0xFF, 0x00,
            0x80,
            0xCC, 0x34, 0x81, 0x82, 0x00,
            0x80,
        ]
    )


def scumm_c13_resource_routines_script() -> bytes:
    """Complete generic resource intent matrix across two scheduler ticks."""
    return bytes(
        [
            0xCC, 0x2A, 0x80, 0x00,  # pseudo room $80 -> room 42
            0x0C, 1, 5,              # load script 5
            0x0C, 2, 6,              # load sound 6
            0x0C, 3, 7,              # load costume 7
            0x0C, 4, 0x80,           # load mapped room 42
            0x0C, 18, 1,             # load charset 1
            0x0C, 9, 5,              # lock script 5
            0x0C, 10, 6,             # lock sound 6
            0x0C, 11, 7,             # lock costume 7
            0x0C, 12, 0x80,          # lock mapped room 42
            0x80,
            0x0C, 13, 5,             # unlock script 5
            0x0C, 14, 6,             # unlock sound 6
            0x0C, 15, 7,             # unlock costume 7
            0x0C, 16, 0x80,          # unlock mapped room 42
            0x0C, 5, 5,              # nuke script 5
            0x0C, 6, 6,              # nuke sound 6
            0x0C, 7, 7,              # nuke costume 7
            0x0C, 8, 0x80,           # nuke mapped room 42
            0x0C, 19, 1,             # nuke charset 1
            0x1A, 0x00, 0x00, 8, 0,  # v0 = sound 8
            0x8C, 0x82, 0x00, 0x00,  # load sound v0 (variable selector)
            0x0C, 17,                 # clear heap (canonical no-op)
            0x0C, 20, 42, 0x34, 0x12,# load object $1234 from room 42
            0x80,
        ]
    )


def scumm_c14_actor_ops_script() -> bytes:
    """Full-header actor configuration matrix across two scheduler ticks."""
    return bytes(
        [
            0x1A, 0x00, 0x00, 2, 0,       # v0 = actor 2
            0x1A, 0x01, 0x00, 55, 0,      # v1 = costume 55
            0x1A, 0x02, 0x00, 3, 0,       # v2 = speed x 3
            0x1A, 0x03, 0x00, 4, 0,       # v3 = speed y 4
            0x13, 1,                       # actor 1
            0x01, 7,                       # costume
            0xC2, 0x02, 0, 0x03, 0,       # step distance from variables
            0x03, 5, 0x04, 6,              # sound, walk animation
            0x05, 7, 8, 0x06, 9,           # talk and stand animation
            0x07, 10, 11, 12,              # consumed legacy animation tuple
            0x09, 0xFE, 0xFF,              # elevation -2
            0x0A,                           # animation defaults
            0x0E, 16, 0x04, 17, 0x06, 18,  # explicit init/walk/stand
            0x05, 19, 20,                   # talk frames
            0x0B, 2, 33, 0x0C, 34,         # palette and talk color
            0x0D, *b"Actor One\0",         # encoded actor name
            0x10, 35, 0x11, 36, 37,        # width and scale
            0x13, 38, 0x14,                 # always clip, then ignore boxes
            0x16, 39, 0x17, 40,             # animation speed and shadow
            0x12, 0x15,                     # never clip, follow boxes
            0x00, 99,                       # dummy consumes one operand
            0xFF, 0x80,
            0x93, 0x00, 0x00,              # actor v0 (actor 2)
            0x81, 0x01, 0x00,              # costume v1
            0x0B, 3, 44,                    # palette survives SO_DEFAULT
            0x0D, *b"Actor Two\0",
            0x13, 77,                       # state reset by SO_DEFAULT
            0x14,                           # ignore boxes
            0x08,                           # Actor::initActor(0)
            0xFF, 0x80,
        ]
    )


def scumm_c15_actor_follow_camera_script() -> bytes:
    """Direct and variable actor-follow intent across two scheduler ticks."""
    return bytes(
        [
            0x1A, 0x00, 0x00, 7, 0,  # v0 = actor 7
            0x52, 3,                  # follow actor 3 directly
            0x80,
            0xD2, 0x00, 0x00,        # follow actor v0 (actor 7)
            0x80,
        ]
    )


def scumm_c16_set_class_script() -> bytes:
    """Direct/variable objects and class selectors across two scheduler ticks."""
    return bytes(
        [
            0x1A, 0x00, 0x00, 0x2C, 0x01,  # v0 = object 300
            0x1A, 0x01, 0x00, 0x85, 0x00,  # v1 = set class 5
            0x5D, 42, 0,                    # object 42 directly
            0x01, 0x81, 0x00,              # set class 1
            0x01, 0x85, 0x00,              # set class 5
            0x01, 0x01, 0x00,              # remove class 1
            0xFF,
            0xDD, 0x00, 0x00,              # object v0 (300)
            0x81, 0x01, 0x00,              # class operation from v1 (set 5)
            0x01, 0x82, 0x00,              # set class 2
            0xFF,
            0x80,
            0x5D, 42, 0,                    # object 42 directly
            0x01, 0x00, 0x00,              # clear all classes
            0xFF,
            0xDD, 0x00, 0x00,              # object v0 (300)
            0x01, 0x05, 0x00,              # remove class 5
            0x01, 0x83, 0x00,              # set class 3
            0xFF,
            0x80,
        ]
    )


def scumm_c17_verb_ops_script() -> bytes:
    """Complete v5 verb configuration surface across two scheduler ticks."""
    return bytes(
        [
            0x27, 0x01, 7, *b"Use\0",        # string 7 = "Use"
            0x1A, 0, 0, 11, 0,               # v0 = verb 11
            0x1A, 1, 0, 100, 0,              # v1 = left 100
            0x1A, 2, 0, 0x56, 0x34,          # v2 = object $3456
            0x1A, 3, 0, 6, 0,                # v3 = color 6
            0x1A, 4, 0, 150, 0,              # v4 = top 150
            0x1A, 5, 0, 7, 0,                # v5 = string 7
            0x1A, 6, 0, 42, 0,               # v6 = room 42
            0x7A, 5,                          # direct verb 5
            0x09,                             # new
            0x02, *b"Look\0",               # inline encoded name
            0x83, 3, 0,                       # color from v3
            0x04, 7,                          # highlight color
            0xC5, 1, 0, 4, 0,                # position from v1/v4
            0x10, 8,                          # dim color
            0x12, ord("L"),                  # key
            0x13,                             # centered
            0x06,                             # on
            0x17, 9,                          # background color
            0xFF,
            0xFA, 0, 0,                       # variable verb v0 (11)
            0x09,                             # new
            0x01, 0x22, 0x22,                # image from current room/object $2222
            0x11,                             # dim
            0xFF,
            0x80,
            0x7A, 5,                          # existing verb 5
            0x09,                             # reset NEW fields, retain geometry/name/background
            0x94, 5, 0,                       # name from string v5
            0xD6, 2, 0, 6, 0,                # object v2 from room v6
            0x07,                             # off
            0xFF,
            0x7A, 11, 0x08, 0xFF,            # delete verb 11
            0x80,
        ]
    )


def scumm_c18_expression_script() -> bytes:
    """Signed stack arithmetic, indexed results, and nested opcode evaluation."""
    return bytes(
        [
            0x1A, 0, 0, 2, 0,                    # v0 = indexed result offset 2
            0x1A, 1, 0, 7, 0,                    # v1 = 7
            0x1A, 2, 0, 0xFD, 0xFF,              # v2 = -3
            0xAC, 3, 0,                           # v3 = ((v1 + 5) * v2) / 5
            0x81, 1, 0, 0x01, 5, 0, 0x02,
            0x81, 2, 0, 0x04, 0x01, 5, 0, 0x05,
            0x20, 0xFF,                           # reserved token, terminator
            0xAC, 4, 0x20, 0, 0x20,              # v[4+v0] = (30000*3)/2
            0x01, 0x30, 0x75, 0x01, 3, 0, 0x04,
            0x01, 2, 0, 0x05, 0xFF,
            0x80,
            0xAC, 0, 0x40,                       # local0 = nested move(v0=9) + 4
            0x06, 0x1A, 0, 0, 9, 0,
            0x01, 4, 0, 0x02, 0xFF,
            0xAC, 7, 0,                           # v7 = -7 / 2 -> -3
            0x01, 0xF9, 0xFF, 0x01, 2, 0, 0x05, 0xFF,
            0xAC, 5, 0x80, 0x01, 0, 0, 0xFF,     # bit 5 = false
            0xAC, 6, 0x80, 0x01, 1, 0, 0xFF,     # bit 6 = true
            0x80,
        ]
    )


def scumm_c19_cutscene_script() -> bytes:
    """Nested cutscenes plus canonical begin/end override markers."""
    return bytes(
        [
            0x1A, 0, 0, 7, 0,                 # v0 = 7
            0x40, 0x01, 0x34, 0x12, 0xFF,     # cutscene([0x1234])
            0x40, 0x81, 0, 0, 0xFF,           # cutscene([v0])
            0x58, 0x01, 0x18, 0x08, 0x00,     # beginOverride; skip its jump
            0x1A, 4, 0, 1, 0,                 # normal path v4 = 1
            0x80,
            0x58, 0x00,                       # endOverride
            0xC0,                             # end inner cutscene
            0xC0,                             # end outer cutscene
            0x80,
        ]
    )


def scumm_c20_do_sentence_script() -> bytes:
    """All operand flag combinations, cancellation, freeze, and LIFO state."""
    return bytes(
        [
            0x1A, 0, 0, 7, 0,                 # v0 = verb / objectB source
            0x1A, 1, 0, 0x11, 0x11,           # v1 = objectA source
            0x1A, 2, 0, 0x22, 0x22,           # v2 = objectB source
            0x19, 1, 100, 0, 0, 0,            # direct/direct/direct
            0x39, 2, 101, 0, 0, 0,            # variable objectB
            0x59, 3, 1, 0, 102, 0,            # variable objectA
            0x79, 4, 1, 0, 2, 0,              # variable objects A/B
            0x60, 1,                           # freeze queued sentences
            0x80,
            0x60, 0,                           # unfreeze before cancellation
            0x19, 0xFE,                        # consumes no object operands
            0x99, 0, 0, 103, 0, 0, 0,         # variable verb
            0xB9, 0, 0, 104, 0, 2, 0,         # variable verb/objectB
            0xD9, 0, 0, 1, 0, 105, 0,         # variable verb/objectA
            0xF9, 0, 0, 1, 0, 2, 0,           # all variable
            0x60, 1,
            0x80,
        ]
    )


def scumm_c21_draw_object_script() -> bytes:
    """Object/state operands, relocation, overlap clearing, and absent lookup."""
    return bytes(
        [
            0x1A, 0, 0, 100, 0,
            0x1A, 1, 0, 12, 0,
            0x1A, 2, 0, 13, 0,
            0x1A, 3, 0, 5, 0,
            0x85, 0, 0, 0xC1, 1, 0, 2, 0,
            0x05, 101, 0, 0x02, 3, 0,
            0x85, 0, 0, 0x82, 3, 0,
            0x05, 0xE7, 0x03, 0xFF,
            0x80,
            0x00,
        ]
    )


def scumm_c22_null_room_script() -> bytes:
    """Variable room load followed by the resource-less room-zero transition."""
    return bytes(
        [
            0x1A, 0, 0, 1, 0,
            0x80,
            0xF2, 0, 0,
            0x80,
            0x72, 0,
            0x80,
            0x00,
        ]
    )


def scumm_c23_print_script() -> bytes:
    """Persistent defaults, variable actors/parameters, printEgo, and text."""
    return bytes(
        [
            0x1A, 0, 0, 253, 0,
            0x1A, 1, 0, 70, 0,
            0x1A, 2, 0, 20, 0,
            0x1A, 3, 0, 31, 0,
            0x14, 252, 0xC0, 1, 0, 2, 0, 0x81, 3, 0, 0x04, 0x07, 0xFF,
            0x94, 0, 0, 0x0F, ord("S"), 0,
            0xD8, 0x00, 100, 0, 30, 0, 0x06,
            0x0F, ord("F"), 0xFF, 0x03, 0,
            0x80,
            0x00,
        ]
    )


def scumm_c24_override_sentinel_script() -> bytes:
    """Install and clear an override at canonical cutscene stack depth zero."""
    return bytes(
        [
            0x58, 1, 0x18, 8, 0,
            0x1A, 4, 0, 1, 0,
            0x80,
            0x58, 0,
            0x1A, 8, 0, 9, 0,
            0x80,
            0x00,
        ]
    )


def scumm_c25_sound_kludge_script() -> bytes:
    """Queue iMUSE stop-all command 11, then flush it on the next tick."""
    return bytes(
        [
            0x4C, 0x00, 0x0B, 0x00, 0xFF, 0x80,
            0x4C, 0x00, 0xFF, 0xFF, 0xFF, 0x80,
            0x00,
        ]
    )


def scumm_c26_save_restore_verbs_script() -> bytes:
    """Save active verbs, replace one, restore it, and delete the other."""
    return bytes(
        [
            0x7A, 1, 9, 3, 3, 0xFF,
            0x7A, 2, 9, 3, 4, 0xFF,
            0xAB, 1, 1, 2, 5,
            0x80,
            0x7A, 1, 9, 3, 9, 0xFF,
            0xAB, 2, 1, 1, 5,
            0x80,
            0xAB, 3, 2, 2, 5,
            0xAB, 1, 2, 1, 7,
            0x80,
            0x00,
        ]
    )


def scumm_c28_animate_actor_script() -> bytes:
    """Request direct and fully-variable animations across two VM ticks."""
    return bytes(
        [
            0x11, 10, 250,
            0x80,
            0x1A, 0, 0, 10, 0,
            0x1A, 1, 0, 6, 0,
            0xD1, 0, 0, 1, 0,
            0x80,
            0x00,
        ]
    )


def scumm_c3_operand_script() -> bytes:
    """Indexed results, variable operands, signed wrap, and comparisons."""
    return bytes(
        [
            0x1A, 0x00, 0x00, 0x02, 0x00,                    # v0 = 2
            0x1A, 0x04, 0x20, 0x03, 0x00, 0x34, 0x12,        # v[4+3] = $1234
            0x1A, 0x04, 0x20, 0x00, 0x20, 0x05, 0x00,        # v[4+v0] = 5
            0x1A, 0x01, 0x00, 0xFF, 0x7F,                    # v1 = 32767
            0x1A, 0x02, 0x00, 0x01, 0x00,                    # v2 = 1
            0xDA, 0x01, 0x00, 0x02, 0x00,                    # v1 += v2 -> -32768
            0x80,
            0xBA, 0x01, 0x00, 0x02, 0x00,                    # v1 -= v2 -> 32767
            0x80,
            0x9B, 0x01, 0x00, 0x02, 0x00,                    # v1 *= v2
            0x1A, 0x03, 0x00, 0x07, 0x00,                    # v3 = 7
            0xDB, 0x01, 0x00, 0x03, 0x00,                    # v1 /= v3 -> 4681
            0x1A, 0x04, 0x00, 0xFF, 0x00,
            0x1A, 0x05, 0x00, 0x0F, 0x0F,
            0x97, 0x05, 0x00, 0x04, 0x00,                    # v5 &= v4 -> $000F
            0x1A, 0x04, 0x00, 0xF0, 0x00,
            0xD7, 0x05, 0x00, 0x04, 0x00,                    # v5 |= v4 -> $00FF
            0x1A, 0x04, 0x00, 0xFF, 0x00,
            0xC8, 0x05, 0x00, 0x04, 0x00, 0x00, 0x00,        # v5 == v4
            0x88, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00,        # v1 != v2
            0xC4, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00,        # v2 < v1
            0xF8, 0x02, 0x00, 0x01, 0x00, 0x00, 0x00,        # v1 > v2
            0xB8, 0x02, 0x00, 0x02, 0x00, 0x00, 0x00,        # v2 <= v2
            0x84, 0x02, 0x00, 0x01, 0x00, 0x00, 0x00,        # v1 >= v2
            0x46, 0x04, 0x20, 0x00, 0x20,                    # v[4+v0]++ -> 6
            0x00,
        ]
    )


def scumm_c4_lifecycle_script() -> bytes:
    """Nested starts, local arguments, peer/self stops, and slot reuse."""
    return bytes(
        [
            0x2A, 0x02, 0x00, 0x0A, 0x00, 0xFF,  # start script 2 with local0=10
            0x1A, 0x00, 0x00, 0x01, 0x00,
            0x80,
            0x62, 0x02,                          # stop script 2
            0x2A, 0x03, 0x00, 0x14, 0x00, 0xFF,  # reuse slot, local0=20
            0x1A, 0x00, 0x00, 0x02, 0x00,
            0x80,
            0x2A, 0x04, 0x00, 0x1E, 0x00, 0xFF,  # reuse slot, local0=30
            0x62, 0x04,                          # peer stop
            0x00,
        ]
    )


def scumm_c5_scheduler_script() -> bytes:
    """Recursive replacement, nested freezes, resistance, and live queries."""
    return bytes(
        [
            0x0A, 0x05, 0xFF,                    # normal script 5
            0x4A, 0x05, 0xFF,                    # recursive second script 5
            0x68, 0x00, 0x00, 0x05,              # v0 = isScriptRunning(5)
            0x80,
            0x0A, 0x05, 0xFF,                    # replace both script 5 slots
            0x68, 0x01, 0x00, 0x05,              # v1 = isScriptRunning(5)
            0x0A, 0x06, 0xFF,                    # normal script 6
            0x2A, 0x07, 0xFF,                    # freeze-resistant script 7
            0x60, 0x01,                          # freeze normal peers
            0x68, 0x02, 0x00, 0x05,              # frozen still counts as running
            0x80,
            0x60, 0x01,                          # nested freeze count = 2
            0x60, 0x00,                          # one thaw leaves peers frozen
            0x68, 0x03, 0x00, 0x06,
            0x80,
            0x60, 0x00,                          # final thaw
            0x68, 0x04, 0x00, 0x05,
            0x68, 0x05, 0x00, 0x08,              # absent script -> zero
            0x80,
            0x62, 0x05,
            0x62, 0x06,
            0x62, 0x07,
            0x68, 0x06, 0x00, 0x05,
            0x00,
        ]
    )


def scumm_c6_scheduler_script() -> bytes:
    """Direct/variable chain targets and caller non-resumption."""
    return bytes(
        [
            0x6A, 0x0A, 0x00, 0x6F, 0x00, 0xFF,  # flagged script 10, local0=111
            0x68, 0x02, 0x00, 0x0A,
            0x68, 0x03, 0x00, 0x0C,
            0x80,
            0x0A, 0x0B, 0x00, 0xDE, 0x00, 0xFF,  # script 11, local0=222
            0x68, 0x05, 0x00, 0x0B,
            0x68, 0x06, 0x00, 0x0D,
            0x80,
            0x62, 0x0C,
            0x62, 0x0D,
            0x68, 0x08, 0x00, 0x0C,
            0x68, 0x09, 0x00, 0x0D,
            0x00,
        ]
    )


def poppy_byte_rows(data: bytes) -> str:
    rows = []
    for offset in range(0, len(data), 12):
        encoded = ",".join(f"${value:02X}" for value in data[offset : offset + 12])
        rows.append(f"    .byte {encoded}")
    return "\n".join(rows)


def poppy_fixture_include(c1: bytes, c2: list[tuple[str, bytes]]) -> str:
    sections = [
        "; Generated by tools/generate_engine_fixtures.py.\n"
        f"SCUMM_V5_CONFORMANCE_PROGRAM_SIZE = ${len(c1):04X}\n"
        "ScummV5_Conformance_Program:\n"
        f"{poppy_byte_rows(c1)}\n"
    ]
    for index, (name, data) in enumerate(c2, start=1):
        symbol = name.upper()
        sections.append(
            f"SCUMM_C2_FIXTURE_{symbol} = ${index:02X}\n"
            f"SCUMM_C2_PROGRAM_{symbol}_SIZE = ${len(data):04X}\n"
            f"ScummV5_C2_Program_{name}:\n"
            f"{poppy_byte_rows(data)}\n"
        )
    sections.append(f"SCUMM_C2_FIXTURE_COUNT = ${len(c2) + 1:02X}\n")
    return "".join(sections)


def scumm_room() -> bytes:
    width, height = 256, 224
    colors = []
    for index in range(32):
        colors.append((index * 7 % 256, index * 5 % 256, index * 11 % 256))
    pixels = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            if y < 72:
                value = 3 + ((x // 32 + y // 16) % 5)
            elif y < 168:
                value = 10 + ((x // 24 + y // 12) % 8)
            else:
                value = 20 + ((x // 16) % 6)
            if 70 < x < 185 and 85 < y < 155:
                value = 27 if ((x + y) // 8) % 2 else 28
            pixels[y * width + x] = value
    header = struct.pack("<4sBHHH", b"SC5R", 1, width, height, len(colors))
    palette = bytes(component for color in colors for component in color)
    return header + palette + pixels


def _scumm_chunk(tag: str, payload: bytes) -> bytes:
    return tag.encode("ascii") + struct.pack(">I", len(payload) + 8) + payload


def _scumm_directory(entries: list[tuple[int, int]]) -> bytes:
    rooms = bytes(room for room, _ in entries)
    offsets = b"".join(struct.pack("<I", offset) for _, offset in entries)
    return struct.pack("<H", len(entries)) + rooms + offsets


def scumm_s2_raw_files() -> tuple[bytes, bytes]:
    """Tiny encrypted v5 index/data pair for resource-service conformance."""
    room = _scumm_chunk("ROOM", b"S2-ROOM-PAYLOAD")
    script1 = _scumm_chunk("SCRP", bytes((0x80, 0x18, 0xFC, 0xFF)))
    script2 = _scumm_chunk("SCRP", bytes((0x46, 0x2A, 0x00, 0x00)))
    sound1 = _scumm_chunk("SOUN", b"S2-SOUND-PAYLOAD")
    costume1 = _scumm_chunk("COST", b"S2-COSTUME-PAYLOAD")
    charset1 = _scumm_chunk("CHAR", b"S2-CHARSET-PAYLOAD")
    script1_offset = len(room)
    script2_offset = script1_offset + len(script1)
    sound1_offset = script2_offset + len(script2)
    costume1_offset = sound1_offset + len(sound1)
    charset1_offset = costume1_offset + len(costume1)
    lflf = _scumm_chunk(
        "LFLF", room + script1 + script2 + sound1 + costume1 + charset1
    )

    # LOFF offsets identify the first payload byte, eight bytes after LFLF.
    loff_size = 8 + 1 + 5
    lflf_payload_offset = 8 + loff_size + 8
    loff = _scumm_chunk("LOFF", bytes((1, 1)) + struct.pack("<I", lflf_payload_offset))
    data = _scumm_chunk("LECF", loff + lflf)
    index = b"".join(
        (
            _scumm_chunk(
                "DSCR",
                _scumm_directory([(0, 0), (1, script1_offset), (1, script2_offset)]),
            ),
            _scumm_chunk("DSOU", _scumm_directory([(0, 0), (1, sound1_offset)])),
            # Entry 2 deliberately points at an absent room. Shareware/demo
            # indexes can retain full-game directory entries; providers must
            # not advertise them as readable resources.
            _scumm_chunk(
                "DCOS", _scumm_directory([(0, 0), (1, costume1_offset), (2, 0)])
            ),
            _scumm_chunk("DCHR", _scumm_directory([(0, 0), (1, charset1_offset)])),
        )
    )
    encrypt = lambda payload: bytes(value ^ 0x69 for value in payload)
    return encrypt(index), encrypt(data)


_S3_GLYPHS = {
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
}


def scumm_s3_charset() -> bytes:
    header_size = 4 + 15 + 256 * 4
    data = bytearray(header_size)
    data[4:19] = bytes(range(1, 16))
    for character, rows in sorted(_S3_GLYPHS.items()):
        offset = len(data)
        struct.pack_into("<I", data, 19 + ord(character) * 4, offset)
        bits = [int(value) for row in rows for value in row]
        packed = bytearray((len(bits) + 7) // 8)
        for index, value in enumerate(bits):
            packed[index // 8] |= value << (7 - index % 8)
        data.extend(bytes((5, 7, 0, 0)))
        data.extend(packed)
    struct.pack_into("<I", data, 0, len(data))
    return bytes(data)


def scumm_s3_scene() -> bytes:
    width, height = 320, 200
    palette = [
        (0, 0, 0),
        (28, 42, 68),
        (45, 72, 98),
        (70, 105, 125),
        (22, 82, 62),
        (38, 115, 78),
        (75, 145, 85),
        (120, 90, 48),
        (155, 120, 60),
        (190, 155, 82),
    ]
    while len(palette) < 32:
        index = len(palette)
        palette.append(((index * 47) & 0xFF, (index * 29) & 0xFF, (index * 71) & 0xFF))
    background = bytearray(width * height)
    z_mask = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            if y < 76:
                color = 1 + ((x // 40 + y // 24) % 3)
            elif y < 150:
                color = 4 + ((x // 32 + y // 18) % 3)
            else:
                color = 7 + ((x // 20) % 3)
            background[y * width + x] = color
    for y in range(62, 150):
        for x in range(140, 148):
            background[y * width + x] = 5
            z_mask[y * width + x] = 3

    actor1_width, actor1_height = 24, 40
    actor1 = bytearray(actor1_width * actor1_height)
    for y in range(actor1_height):
        for x in range(actor1_width):
            if 2 <= x < 22 and (y >= 8 or 7 <= x < 17):
                actor1[y * actor1_width + x] = 28 if (x + y) % 2 else 29
    actor2_width, actor2_height = 16, 20
    actor2 = bytes(30 if 2 <= x < 14 and 2 <= y < 19 else 0
                   for y in range(actor2_height) for x in range(actor2_width))

    result = bytearray(
        struct.pack("<4sBHHHHHBB", b"SCN3", 1, width, height, len(palette), 32, 0, 2, 2)
    )
    result.extend(bytes(component for color in palette for component in color))
    result.extend(background)
    result.extend(z_mask)
    result.extend(struct.pack("<hhHHBB", 130, 82, actor1_width, actor1_height, 0, 2))
    result.extend(actor1)
    result.extend(struct.pack("<hhHHBB", 143, 96, actor2_width, actor2_height, 0, 4))
    result.extend(actor2)
    for x, y, color, text in ((48, 16, 31, "SAME S3"), (236, 180, 31, "FONT!")):
        font_key = b"font.s3"
        encoded = text.encode("latin-1")
        result.extend(struct.pack("<hhBBH", x, y, color, len(font_key), len(encoded)))
        result.extend(font_key)
        result.extend(encoded)
    return bytes(result)


def scumm_s3_cursor() -> bytes:
    width = height = 8
    pixels = bytes(
        31 if x == 0 or y == 0 or x == y else 0
        for y in range(height)
        for x in range(width)
    )
    return struct.pack("<4sBBBBBB", b"SCC3", 1, width, height, 0, 0, 0) + pixels


def scumm_s4_room(accent: int) -> bytes:
    width, height = 256, 224
    palette = [(0, 0, 0), (24, 40, 72), (65, 92, 120), (180, 140, 72), (220, 190, 105)]
    pixels = bytes(
        accent if 48 <= x < 208 and 56 <= y < 176 else 1 + ((x // 32 + y // 28) & 1)
        for y in range(height)
        for x in range(width)
    )
    return (
        struct.pack("<4sBHHH", b"SC5R", 1, width, height, len(palette))
        + bytes(component for color in palette for component in color)
        + pixels
    )


def scumm_s4_score() -> bytes:
    return json.dumps(
        {
            "schema": "same_score_v1",
            "ticks_per_second": 60,
            "length": 8,
            "loop": [2, 8],
            "events": [
                {"tick": 0, "kind": "program", "voice": 0, "a": 12, "b": 0},
                {"tick": 0, "kind": "note_on", "voice": 0, "a": 60, "b": 96},
                {"tick": 2, "kind": "note_off", "voice": 0, "a": 60, "b": 0},
                {"tick": 2, "kind": "note_on", "voice": 1, "a": 67, "b": 88},
                {"tick": 6, "kind": "note_off", "voice": 1, "a": 67, "b": 0},
                {"tick": 7, "kind": "marker", "voice": 0, "a": 1, "b": 0},
            ],
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def scumm_s4_manifest() -> bytes:
    return json.dumps(
        {
            "schema": "same_scumm_audio_v1",
            "music": {
                "7": {
                    "resource": "score.s4",
                    "duration": 8,
                    "loop": True,
                    "tad_song": 3,
                    "msu_track": 107,
                }
            },
            "sfx": {
                "9": {
                    "resource": "sfx.s4",
                    "duration": 6,
                    "pan": 96,
                    "priority": 4,
                }
            },
            "speech": {
                "5": {"resource": "speech.s4", "duration": 12}
            },
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


EGA = (
    (0, 0, 0),
    (0, 0, 170),
    (0, 170, 0),
    (0, 170, 170),
    (170, 0, 0),
    (170, 0, 170),
    (170, 85, 0),
    (170, 170, 170),
    (85, 85, 85),
    (85, 85, 255),
    (85, 255, 85),
    (85, 255, 255),
    (255, 85, 85),
    (255, 85, 255),
    (255, 255, 85),
    (255, 255, 255),
)


def agi_logic() -> bytes:
    # Decoded AGI v2 logic resource: increment v20, set flag 40, return.
    bytecode = bytes((0x01, 0x14, 0x0C, 0x28, 0x00))
    message = b"SAME AGI CONFORMANCE\0"
    message_count = 1
    # Message offsets are relative to the byte immediately after message_count.
    offset = 2 + message_count * 2
    message_payload = struct.pack("<H", offset) + message
    messages_size = 2 + len(message_payload)
    message_section = bytes((message_count,)) + struct.pack("<H", messages_size) + message_payload
    return struct.pack("<H", len(bytecode)) + bytecode + message_section


def agi_picture() -> bytes:
    width, height = 160, 168
    pixels = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            if y < 70:
                color = 9
            elif y < 125:
                color = 10 if (x // 12 + y // 8) % 2 else 2
            else:
                color = 6 if (x // 8) % 2 else 14
            if 50 <= x < 110 and 55 <= y < 122:
                color = 4 if (x + y) % 7 else 12
            if 73 <= x < 87 and 91 <= y < 126:
                color = 15
            pixels[y * width + x] = color
    header = struct.pack("<4sBHHH", b"AGIP", 1, width, height, len(EGA))
    palette = bytes(component for color in EGA for component in color)
    return header + palette + pixels


def write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f"{path.relative_to(ROOT)} {len(data)} bytes")


def write_text(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")
    print(f"{path.relative_to(ROOT)} {len(data.encode('utf-8'))} bytes")


def main() -> int:
    write(ROOT / "examples/resources/scumm_v5/boot.scrp", scumm_script())
    conformance = scumm_core_conformance_script()
    c2 = scumm_c2_fixtures()
    write(ROOT / "examples/resources/scumm_v5/core_conformance.scrp", conformance)
    for name, data in c2:
        prefix = "" if name.startswith(("c3_", "c4_", "c5_", "c6_", "c7_", "c8_", "c9_", "c10_", "c11_", "c12_", "c13_", "c14_", "c15_", "c16_", "c17_", "c18_", "c19_", "c20_", "c21_", "c22_", "c23_", "c24_", "c25_", "c26_", "c28_", "s5_")) else "c2_"
        write(ROOT / f"examples/resources/scumm_v5/{prefix}{name}.scrp", data)
    write_text(
        ROOT / "runtime/snes/generated/scumm_v5_conformance.inc.pasm",
        poppy_fixture_include(conformance, c2),
    )
    write(ROOT / "examples/resources/scumm_v5/room0.sc5r", scumm_room())
    s2_index, s2_data = scumm_s2_raw_files()
    write(ROOT / "examples/resources/scumm_v5/s2_index.000", s2_index)
    write(ROOT / "examples/resources/scumm_v5/s2_data.001", s2_data)
    write(ROOT / "examples/resources/scumm_v5/s2_sound_map.bin", b"S2SM\x01\x00")
    write(ROOT / "examples/resources/scumm_v5/s2_voice_table.bin", b"S2VI\x01\x00")
    write(ROOT / "examples/resources/scumm_v5/s2_speech.sou", b"S2-SPEECH")
    write(ROOT / "examples/resources/scumm_v5/s3_scene.scn3", scumm_s3_scene())
    write(ROOT / "examples/resources/scumm_v5/s3_font.char", scumm_s3_charset())
    write(ROOT / "examples/resources/scumm_v5/s3_cursor.scc3", scumm_s3_cursor())
    write(
        ROOT / "examples/resources/scumm_v5/s4_boot.scrp",
        bytes((0x02, 0x07, 0x1C, 0x09, 0x80, 0x72, 0x01, 0x80, 0x18, 0xFC, 0xFF)),
    )
    write(ROOT / "examples/resources/scumm_v5/s4_room0.sc5r", scumm_s4_room(3))
    write(ROOT / "examples/resources/scumm_v5/s4_room1.sc5r", scumm_s4_room(4))
    write(ROOT / "examples/resources/scumm_v5/s4_score.json", scumm_s4_score())
    write(ROOT / "examples/resources/scumm_v5/s4_audio.json", scumm_s4_manifest())
    write(ROOT / "examples/resources/scumm_v5/s4_sfx.bin", b"SAME-S4-SYNTHETIC-SFX")
    write(ROOT / "examples/resources/scumm_v5/s4_speech.bin", b"SAME-S4-SYNTHETIC-SPEECH")
    write(ROOT / "examples/resources/agi/logic0.bin", agi_logic())
    write(ROOT / "examples/resources/agi/picture0.agip", agi_picture())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
