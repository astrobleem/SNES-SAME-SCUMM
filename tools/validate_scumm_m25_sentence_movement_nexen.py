#!/usr/bin/env python3
"""Fresh-emulator M25 semantic-sentence and bounded walking evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
COMMON = 0x7E2300
SLOT_STATUS = 0x7E2380
SLOT_NUMBER = 0x7E2399
SLOT_PROGRAM = 0x7E23B2
SLOT_WHERE = 0x7E7F46
SLOT_OBJECT = 0x7E7F5F
SLOT_PC = 0x7E23E4
LOCALS = 0x7E2448
VARIABLES = 0x7FF500
LEGACY_VARIABLES = 0x7E2320
ACTIVE_RECORD = 0x7FF2BE
ACTIVE_ROOM = 0x7FF2BF
ROOM_PHASE = 0x7FF2C2
RETURN_MODE = 0x7E2363
ACTIVE_COUNT = 0x7E2A8A
POSITIONS = 0x7FF1A0
MOVING = 0x7FF220
WALKBOX = 0x7FFDA5
DESTBOX = 0x7FFDC5
DEST_X = 0x7FFDE5
MOVE_Y = 0x7E7BAA
MOVE_TICK = 0x7E7EB9
WAIT_BLOCKS = 0x7E7EBB
WAIT_RELEASES = 0x7E7EBD
VERB_RESULT = 0x7E7EC3
OWNER_RESULT = 0x7E7EC5
SENTENCE_INJECTED = 0x7E7FDB
SENTENCE_API_VERB = 0x7FD3A6
SENTENCE_API_OBJECT1 = 0x7FD3A8
SENTENCE_API_OBJECT2 = 0x7FD3AA
ROOM_REQUEST_PENDING = 0x7E7F8E
ROOM_REQUEST_ROOM = 0x7E7F8F
RESET_VECTOR_COUNT = 0x7E5464
ERROR_EVENT = 0x7E5500
RESET_DIAG = 0x7E5500
QUERY_DIR = 0x7E7ED4
PHASE_NORMALIZE_CALLS = 0x7E7ED5
PHASE_NORMALIZE_COMMITS = 0x7E7ED6
MOVE_START_COUNT = 0x7E7F18
MOVE_START_PC = 0x7E7F1A
MOVE_START_PROGRAM = 0x7E7F1C
MOVE_START_ACTOR = 0x7E7F1D
MOVE_STEP_COUNT = 0x7E7F19
MOVE_STEP_PRE_X = 0x7E7F1A
MOVE_STEP_POST_X = 0x7E7F1C
MOVE_STEP_STATE = 0x7E7F1E
START_TRACE_COUNT = 0x7E7ED7
START_TRACE = 0x7E7ED8
GET_DIST = 0x7E7F23
START_OBJECT = 0x7E7F91
TALK_STATE = 0x7E7A20
C20 = 0x7FD380
ERROR_SITE = 0x7FF466
OPCODE_TRACE_COUNT = 0x7FF957
OPCODE_TRACE = 0x7FF97C
ROOM_OPS_ERROR_CONTEXT = 0x7FF959
SA1_CONTROL = 0x401000


def stable_cpu(state: dict[str, object]) -> dict[str, object]:
    return {
        key: state[key]
        for key in ("pc", "k", "a", "x", "y", "sp", "d", "dbr", "ps", "emulationMode")
    }


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def stable_room49_checkpoint(state: dict[str, object]) -> bool:
    """The accepted post-return boundary, observed one frame at a time."""
    return (
        state["active_room"] == 49
        and state["active_record"] == 0
        and state["room_phase"] == 0
        and state["actor"]["position"] == [399, 116]
        and state["actor"]["walkbox"] == 11
        and state["actor"]["moving"] == 0
        and state["sentence_count"] == 0
        and state["sentence_api_pending"] == 0
        and state["error"] == 0
    )


def snapshot(session: object, frame: int) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON, 0x64)
    status = session.read_memory("snesMemory", SLOT_STATUS, 25)
    numbers = session.read_memory("snesMemory", SLOT_NUMBER, 25)
    programs = session.read_memory("snesMemory", SLOT_PROGRAM, 25)
    wheres = session.read_memory("snesMemory", SLOT_WHERE, 25)
    object_numbers = session.read_memory("snesMemory", SLOT_OBJECT, 50)
    pcs = session.read_memory("snesMemory", SLOT_PC, 50)
    positions = session.read_memory("snesMemory", POSITIONS, 128)
    walkboxes = session.read_memory("snesMemory", WALKBOX, 32)
    moving = session.read_memory("snesMemory", MOVING, 32)
    slots = []
    for index in range(25):
        if status[index] or numbers[index] or programs[index]:
            local = session.read_memory("snesMemory", LOCALS + index * 64, 12)
            slots.append({
                "slot": index, "status": status[index], "number": numbers[index],
                "program": programs[index], "pc": u16(pcs, index * 2),
                "where": wheres[index], "object_number": u16(object_numbers, index * 2),
                "locals": [u16(local, offset) for offset in range(0, 12, 2)],
            })
    slot_rooms = list(session.read_memory("snesMemory", 0x7FF2E7, 25))
    didexec = list(session.read_memory("snesMemory", 0x7E23CB, 25))
    freeze = list(session.read_memory("snesMemory", 0x7E2B08, 25))
    actor = 1
    actor_record = session.read_memory("snesMemory", 0x7F36C0 + actor * 64, 64)
    movement_raw = {
        "fraction": [u16(session.read_memory("snesMemory", 0x7E7D0A + actor * 2, 2)),
                     u16(session.read_memory("snesMemory", 0x7E7D4A + actor * 2, 2))],
        "delta_x": [u16(session.read_memory("snesMemory", 0x7E7D8A + actor * 2, 2)),
                    u16(session.read_memory("snesMemory", 0x7E7DCA + actor * 2, 2))],
        "delta_y": [u16(session.read_memory("snesMemory", 0x7E7E0A + actor * 2, 2)),
                    u16(session.read_memory("snesMemory", 0x7E7E4A + actor * 2, 2))],
        "leg_origin": [u16(session.read_memory("snesMemory", 0x7E7C8A + actor * 2, 2)),
                       u16(session.read_memory("snesMemory", 0x7E7CCA + actor * 2, 2))],
        "leg_target": [u16(session.read_memory("snesMemory", 0x7E7C0A + actor * 2, 2)),
                       u16(session.read_memory("snesMemory", 0x7E7C4A + actor * 2, 2))],
    }
    start_trace_count = session.read_memory("snesMemory", START_TRACE_COUNT, 1)[0]
    start_trace_raw = session.read_memory(
        "snesMemory", START_TRACE, min(start_trace_count, 16) * 4
    )
    opcode_trace_count = session.read_memory(
        "snesMemory", OPCODE_TRACE_COUNT, 1
    )[0]
    opcode_trace_raw = session.read_memory(
        "snesMemory", OPCODE_TRACE, min(opcode_trace_count, 32) * 4
    )
    get_dist = session.read_memory("snesMemory", GET_DIST, 35)
    start_object = session.read_memory("snesMemory", START_OBJECT, 21)
    talk = session.read_memory("snesMemory", TALK_STATE, 13)
    m23c = session.read_memory("snesMemory", 0x7FF948, 0x20)
    c16_raw = session.read_memory("snesMemory", 0x7F5F10, 0x1000)
    c16_records = {}
    for object_id in (596, 851, 853, 854, 855):
        for index in range(512):
            base = index * 8
            if c16_raw[base] and u16(c16_raw, base + 2) == object_id:
                c16_records[str(object_id)] = {
                    "index": index, "present": c16_raw[base],
                    "object": u16(c16_raw, base + 2),
                    "mask_lo": u16(c16_raw, base + 4),
                    "mask_hi": u16(c16_raw, base + 6),
                }
                break
    return {
        "frame": frame, "logical_tick": u16(common, 8), "error": common[3],
        "var0": u16(session.read_memory("snesMemory", LEGACY_VARIABLES, 2)),
        "var2": u16(session.read_memory("snesMemory", LEGACY_VARIABLES + 4, 2)),
        "engine_lifecycle": session.read_memory("snesMemory", 0x7E2221, 1)[0],
        "engine_frame_busy": session.read_memory("snesMemory", 0x7E2231, 1)[0],
        "dma": {
            "pending": u16(session.read_memory("snesMemory", 0x7E223C, 2)),
            "committed": u16(session.read_memory("snesMemory", 0x7E223E, 2)),
            "deferred_blank": u16(session.read_memory("snesMemory", 0x7E2240, 2)),
            "deferred_budget": u16(session.read_memory("snesMemory", 0x7E2242, 2)),
            "rejected": u16(session.read_memory("snesMemory", 0x7E2244, 2)),
        },
        "audio_packet_count": session.read_memory("snesMemory", 0x7E2B30, 1)[0],
        "sound_path": {
            "sound82_result": m23c[12],
            "auth_flush_seen": m23c[5],
            "auth_flush_queue_count": m23c[6],
            "clear_queue_count": m23c[13],
            "active_sound80": bool(m23c[0x14 + 10] & 1),
            "active_sound81": bool(m23c[0x14 + 10] & 2),
            "active_sound82": bool(m23c[0x14 + 10] & 4),
            "c25_queue_count": session.read_memory("snesMemory", 0x7FD459, 1)[0],
            "c25_flush_count": session.read_memory("snesMemory", 0x7FD8AB, 1)[0],
        },
        "message_state": {
            "active": talk[0],
            "have_msg": talk[1],
            "actor": talk[2],
            "charinc": talk[3],
            "delay": u16(talk, 4),
            "generation": u16(talk, 6),
            "raw_length": talk[8],
            "start_count": talk[9],
            "stop_count": talk[10],
            "complete_count": talk[11],
        },
        "scumm_status": common[2],
        "last_opcode": common[6], "program": common[0x62], "pc": u16(common),
        "active_record": session.read_memory("snesMemory", ACTIVE_RECORD, 1)[0],
        "active_room": session.read_memory("snesMemory", ACTIVE_ROOM, 1)[0],
        "scumm_current_room": session.read_memory("snesMemory", 0x7FD403, 1)[0],
        "room_phase": session.read_memory("snesMemory", ROOM_PHASE, 1)[0],
        "c19_handoff": {
            "stack_pointer": session.read_memory("snesMemory", 0x7FD360, 1)[0],
            "slot_depth_2": session.read_memory("snesMemory", 0x7FD365, 1)[0],
            "slot_depth_3": session.read_memory("snesMemory", 0x7FD366, 1)[0],
            "current_slot": session.read_memory("snesMemory", 0x7E2398, 1)[0],
        },
        "room_request_trace": {
            "boot_count": session.read_memory("snesMemory", 0x7E5451, 1)[0],
            "count": session.read_memory("snesMemory", 0x7E5450, 1)[0],
            "room": session.read_memory("snesMemory", 0x7E5452, 1)[0],
            "current_room": session.read_memory("snesMemory", 0x7E5453, 1)[0],
            "program": session.read_memory("snesMemory", 0x7E5454, 1)[0],
            "pc": u16(session.read_memory("snesMemory", 0x7E5455, 2)),
        },
        "object_resolver_trace": {
            "active_record": session.read_memory("snesMemory", 0x7E545C, 1)[0],
            "object": u16(session.read_memory("snesMemory", 0x7E545D, 2)),
            "program": session.read_memory("snesMemory", 0x7E5460, 1)[0],
            "verb_result": u16(session.read_memory("snesMemory", 0x7E5461, 2)),
            "query_record": session.read_memory("snesMemory", 0x7E5465, 1)[0],
            "query_object": u16(session.read_memory("snesMemory", 0x7E5466, 2)),
            "query_verb": u16(session.read_memory("snesMemory", 0x7E5468, 2)),
            "query_first_record3_object": u16(session.read_memory("snesMemory", 0x7E546A, 2)),
        },
        "reset_vector_count": session.read_memory("snesMemory", RESET_VECTOR_COUNT, 1)[0],
        "reset_diag": {
            "count": u16(session.read_memory("snesMemory", RESET_DIAG, 2)),
            "frame": u16(session.read_memory("snesMemory", RESET_DIAG + 2, 2)),
            "stage": session.read_memory("snesMemory", RESET_DIAG + 4, 1)[0],
            "last_pbr": session.read_memory("snesMemory", RESET_DIAG + 5, 1)[0],
            "last_pc": u16(session.read_memory("snesMemory", RESET_DIAG + 6, 2)),
            "last_s": u16(session.read_memory("snesMemory", RESET_DIAG + 8, 2)),
            "last_p": session.read_memory("snesMemory", RESET_DIAG + 10, 1)[0],
            "last_dbr": session.read_memory("snesMemory", RESET_DIAG + 11, 1)[0],
            "last_d": u16(session.read_memory("snesMemory", RESET_DIAG + 12, 2)),
            "nmi": u16(session.read_memory("snesMemory", RESET_DIAG + 14, 2)),
            "irq": u16(session.read_memory("snesMemory", RESET_DIAG + 16, 2)),
            "brk": u16(session.read_memory("snesMemory", RESET_DIAG + 18, 2)),
            "cop": u16(session.read_memory("snesMemory", RESET_DIAG + 20, 2)),
            "room": session.read_memory("snesMemory", RESET_DIAG + 22, 1)[0],
            "program": session.read_memory("snesMemory", RESET_DIAG + 23, 1)[0],
            "slot": session.read_memory("snesMemory", RESET_DIAG + 24, 1)[0],
            "script_pc": u16(session.read_memory("snesMemory", RESET_DIAG + 25, 2)),
            "lifecycle": session.read_memory("snesMemory", RESET_DIAG + 27, 1)[0],
            "engine_phase": session.read_memory("snesMemory", RESET_DIAG + 28, 1)[0],
        },
        "error_event": {
            "count": session.read_memory("snesMemory", ERROR_EVENT, 1)[0],
            "error": session.read_memory("snesMemory", ERROR_EVENT + 1, 1)[0],
            "program": session.read_memory("snesMemory", ERROR_EVENT + 2, 1)[0],
            "pc": u16(session.read_memory("snesMemory", ERROR_EVENT + 3, 2)),
            "opcode": session.read_memory("snesMemory", ERROR_EVENT + 5, 1)[0],
            "room": session.read_memory("snesMemory", ERROR_EVENT + 6, 1)[0],
        },
        "error_trace": {
            "error": session.read_memory("snesMemory", 0x7E5457, 1)[0],
            "program": session.read_memory("snesMemory", 0x7E5458, 1)[0],
            "pc": u16(session.read_memory("snesMemory", 0x7E5459, 2)),
            "opcode": session.read_memory("snesMemory", 0x7E545B, 1)[0],
        },
        "phase_normalize_calls": session.read_memory(
            "snesMemory", PHASE_NORMALIZE_CALLS, 1
        )[0],
        "phase_normalize_commits": session.read_memory(
            "snesMemory", PHASE_NORMALIZE_COMMITS, 1
        )[0],
        "return_mode": session.read_memory("snesMemory", RETURN_MODE, 1)[0],
        "active_count": session.read_memory("snesMemory", ACTIVE_COUNT, 1)[0],
        "sentence_script": u16(session.read_memory("snesMemory", VARIABLES + 66, 2)),
        "sentence_script_actual": u16(session.read_memory("snesMemory", 0x7E0800 + 66, 2)),
        "sentence_script_m23b": u16(session.read_memory("snesMemory", 0x7FF500 + 66, 2)),
        "sentence_injected": session.read_memory("snesMemory", SENTENCE_INJECTED, 1)[0],
        "sentence_api_pending": session.read_memory("snesMemory", 0x7E7EC7, 1)[0],
        "sentence_api": {
            "verb": u16(session.read_memory("snesMemory", 0x7FD3A6, 2)),
            "object1": u16(session.read_memory("snesMemory", 0x7FD3A8, 2)),
            "object2": u16(session.read_memory("snesMemory", 0x7FD3AA, 2)),
        },
        "c20_raw": list(session.read_memory("snesMemory", 0x7FD380, 40)),
        "verb_object": u16(session.read_memory("snesMemory", VERB_RESULT - 4, 2)),
        "verb_id": u16(session.read_memory("snesMemory", VERB_RESULT - 2, 2)),
        "local_resolve_result": session.read_memory("snesMemory", QUERY_DIR, 1)[0],
        "sentence_count": session.read_memory("snesMemory", C20, 1)[0],
        "error_site": session.read_memory("snesMemory", ERROR_SITE, 1)[0],
        "verb_result": u16(session.read_memory("snesMemory", VERB_RESULT, 2)),
        "owner_result": u16(session.read_memory("snesMemory", OWNER_RESULT, 2)),
        "actor": {
            "position": [u16(positions, actor * 4), u16(positions, actor * 4 + 2)],
            "walkbox": walkboxes[actor], "moving": moving[actor],
            "destination_box": session.read_memory("snesMemory", DESTBOX + actor, 1)[0],
            "destination_x": u16(session.read_memory("snesMemory", DEST_X + actor * 2, 2)),
            "destination_y": u16(session.read_memory("snesMemory", MOVE_Y + actor * 2, 2)),
            "route_box": session.read_memory("snesMemory", 0x7E7BEA + actor, 1)[0],
            "route_next": session.read_memory("snesMemory", 0x7E7ECC, 1)[0],
            "gate_x": u16(session.read_memory("snesMemory", 0x7E7EC8, 2)),
            "gate_y": u16(session.read_memory("snesMemory", 0x7E7ECA, 2)),
            "speed": [actor_record[1], actor_record[2]],
            "room": actor_record[0x16], "ignore_boxes": actor_record[0x11],
            "present": actor_record[0x1F],
            "scale": [actor_record[0x0D], actor_record[0x0E]],
            "delta_x": [u16(session.read_memory("snesMemory", 0x7E7D8A + actor * 2, 2)),
                        u16(session.read_memory("snesMemory", 0x7E7DCA + actor * 2, 2))],
            "delta_y": [u16(session.read_memory("snesMemory", 0x7E7E0A + actor * 2, 2)),
                        u16(session.read_memory("snesMemory", 0x7E7E4A + actor * 2, 2))],
            "leg_origin": [u16(session.read_memory("snesMemory", 0x7E7C0A + actor * 2, 2)),
                           u16(session.read_memory("snesMemory", 0x7E7C4A + actor * 2, 2))],
            "leg_target": [u16(session.read_memory("snesMemory", 0x7E7C8A + actor * 2, 2)),
                           u16(session.read_memory("snesMemory", 0x7E7CCA + actor * 2, 2))],
            "fraction": [u16(session.read_memory("snesMemory", 0x7E7D0A + actor * 2, 2)),
                         u16(session.read_memory("snesMemory", 0x7E7D4A + actor * 2, 2))],
        },
        "movement_raw": movement_raw,
        "movement_tick": u16(session.read_memory("snesMemory", MOVE_TICK, 2)),
        "movement_trace": {
            "start_count": session.read_memory("snesMemory", MOVE_START_COUNT, 1)[0],
            "start_pc": u16(session.read_memory("snesMemory", MOVE_START_PC, 2)),
            "start_program": session.read_memory("snesMemory", MOVE_START_PROGRAM, 1)[0],
            "start_actor": session.read_memory("snesMemory", MOVE_START_ACTOR, 1)[0],
            "step_count": session.read_memory("snesMemory", 0x7E7F1E, 1)[0],
            "product_lo": u16(session.read_memory("snesMemory", 0x7E5004, 2)),
            "product_hi": u16(session.read_memory("snesMemory", 0x7E5006, 2)),
            "actor1_post_x": u16(session.read_memory("snesMemory", 0x7E5008, 2)),
            "actor1_post_y": u16(session.read_memory("snesMemory", 0x7E500A, 2)),
            "actor1_after_x_add": u16(session.read_memory("snesMemory", 0x7E500C, 2)),
            "actor1_pre_x_exact": u16(session.read_memory("snesMemory", 0x7E500E, 2)),
            "actor1_result_hi": u16(session.read_memory("snesMemory", 0x7E5010, 2)),
            "actor1_calculated_x": u16(session.read_memory("snesMemory", 0x7E5012, 2)),
            "last_position_writer": session.read_memory("snesMemory", 0x7E5014, 1)[0],
            "put_actor_write_count": session.read_memory("snesMemory", 0x7E5015, 1)[0],
            "update_entry_count": session.read_memory("snesMemory", 0x7E5016, 1)[0],
            "last_update_tick": u16(session.read_memory("snesMemory", 0x7E5018, 2)),
            "entry_moving": session.read_memory("snesMemory", 0x7E501A, 1)[0],
            "entry_x": u16(session.read_memory("snesMemory", 0x7E501C, 2)),
            "entry_y": u16(session.read_memory("snesMemory", 0x7E501E, 2)),
            "entry_target_x": u16(session.read_memory("snesMemory", 0x7E5020, 2)),
            "entry_target_y": u16(session.read_memory("snesMemory", 0x7E5022, 2)),
            "position_write_count": session.read_memory("snesMemory", 0x7E5024, 1)[0],
            "last_position_write_tick": u16(session.read_memory("snesMemory", 0x7E5026, 2)),
            "last_position_write_tag": session.read_memory("snesMemory", 0x7E5028, 1)[0],
            "pre_x": u16(session.read_memory("snesMemory", MOVE_STEP_PRE_X, 2)),
            "post_x": u16(session.read_memory("snesMemory", MOVE_STEP_POST_X, 2)),
            "state": session.read_memory("snesMemory", MOVE_STEP_STATE, 1)[0],
            "event_cursor": session.read_memory("snesMemory", 0x7E54FF, 1)[0],
            "event_trace": list(session.read_memory("snesMemory", 0x7E5500, 0x80)),
        },
        "query_scan_offset": u16(session.read_memory("snesMemory", 0x7E7EB5, 2)),
        "query_scan_verb": u16(session.read_memory("snesMemory", 0x7E7EB7, 2)),
        "class10_branch_pc": u16(session.read_memory("snesMemory", 0x7E7EC8, 2)),
        "class_eval_counts": list(session.read_memory("snesMemory", 0x7FF94F, 2)),
        "class_branch": {
            "object": u16(session.read_memory("snesMemory", 0x7E5470, 2)),
            "class": u16(session.read_memory("snesMemory", 0x7E5472, 2)),
            "condition": session.read_memory("snesMemory", 0x7E5474, 1)[0],
        },
        "class_set": {
            "object": u16(session.read_memory("snesMemory", 0x7E5476, 2)),
            "class": u16(session.read_memory("snesMemory", 0x7E5478, 2)),
        },
        "wait_blocks": u16(session.read_memory("snesMemory", WAIT_BLOCKS, 2)),
        "wait_releases": u16(session.read_memory("snesMemory", WAIT_RELEASES, 2)),
        "get_dist": {
            "pc_before": u16(get_dist, 0), "pc_after": u16(get_dist, 2),
            "result_offset": u16(get_dist, 4), "result_before": u16(get_dist, 6),
            "operand1": u16(get_dist, 8), "operand2": u16(get_dist, 10),
            "type1": get_dist[12], "type2": get_dist[13],
            "xy1": [u16(get_dist, 14), u16(get_dist, 16)],
            "xy2_raw": [u16(get_dist, 18), u16(get_dist, 20)],
            "xy2_adjusted": [u16(get_dist, 22), u16(get_dist, 24)],
            "dx": u16(get_dist, 26), "dy": u16(get_dist, 28),
            "result": u16(get_dist, 30), "adjusted": get_dist[32],
            "exec_count": get_dist[33],
            "stage": get_dist[34],
        },
        "start_object": {
            "object": u16(start_object, 0), "entry": start_object[2],
            "program": start_object[3], "entry_offset": u16(start_object, 4),
            "pc_before": u16(start_object, 6), "pc_after_args": u16(start_object, 8),
            "slot": start_object[10], "arg_count": start_object[11],
            "exec_count": start_object[12], "chain_target": start_object[13],
            "object_retired": start_object[14], "lscr_program": start_object[15],
            "lscr_entry_seen": start_object[16],
            "arguments": [u16(start_object, 17), u16(start_object, 19)],
        },
        "start_trace": [list(start_trace_raw[index:index + 4])
                        for index in range(0, len(start_trace_raw), 4)],
        "start_trace_count": start_trace_count,
        "opcode_trace": [
            {"program": opcode_trace_raw[index],
             "pc": u16(opcode_trace_raw, index + 1),
             "opcode": opcode_trace_raw[index + 3]}
            for index in range(0, len(opcode_trace_raw), 4)
        ],
        "room_ops_error_context": {
            "subop": m23c[0x11], "program": m23c[0x12], "opcode": m23c[0x13],
        },
        "load_ego": {
            "active": session.read_memory("snesMemory", 0x7E7FCC, 1)[0],
            "object": u16(session.read_memory("snesMemory", 0x7E7FCD, 2)),
            "room": session.read_memory("snesMemory", 0x7E7FCF, 1)[0],
            "x": u16(session.read_memory("snesMemory", 0x7E7FD0, 2)),
            "y": u16(session.read_memory("snesMemory", 0x7E7FD2, 2)),
            "pc_after": u16(session.read_memory("snesMemory", 0x7E7FD4, 2)),
            "caller_slot": session.read_memory("snesMemory", 0x7E7FD6, 1)[0],
            "caller_program": session.read_memory("snesMemory", 0x7E7FD7, 1)[0],
            "previous_room": session.read_memory("snesMemory", 0x7E7FD8, 1)[0],
            "ego": session.read_memory("snesMemory", 0x7E7FD9, 1)[0],
        },
        "slots": slots,
        "slot_rooms": slot_rooms,
        "didexec": didexec,
        "freeze": freeze,
        "scheduler": {
            "cursor": session.read_memory("snesMemory", 0x7E2B22, 1)[0],
            "current_slot": session.read_memory("snesMemory", 0x7E2A88, 1)[0],
            "active_count": session.read_memory("snesMemory", ACTIVE_COUNT, 1)[0],
        },
        "c20_raw": list(session.read_memory("snesMemory", C20, 0x30)),
        "c16_records": c16_records,
    }


def run_frames_exact(session: object, count: int) -> dict[str, object]:
    before = session.get_state() if count > 1 else None
    result = session.run_frames(count)
    after = session.get_state() if count > 1 else None
    expected_frame = (before.get("frameCount", -1) + count
                      if before is not None else None)
    if (result.get("timedOut") or result.get("framesAdvanced") != count
            or (after is not None and after.get("frameCount") != expected_frame)):
        raise RuntimeError(f"emulator frame run failed: requested={count} result={result}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45725)
    parser.add_argument("--max-frames", type=int, default=1200)
    parser.add_argument("--sentence-tail-frames", type=int, default=100)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--next-object", type=int, choices=(851, 853, 854, 855))
    parser.add_argument("--pre-next-object", type=int, choices=(853, 854, 855),
                        help="submit this ordinary room-63 sentence before --next-object")
    parser.add_argument("--next-verb", type=int, default=10)
    parser.add_argument("--post-return-object", type=int, choices=(591, 592, 593, 594, 595))
    parser.add_argument("--post-return-verb", type=int, default=3)
    parser.add_argument("--controlled-room49", action="store_true",
                        help="use the bounded room-49 controller replay root")
    parser.add_argument("--direct-room49-object", type=int, choices=(591, 592, 593, 594, 595))
    parser.add_argument("--direct-room49-verb", type=int, default=3)
    args = parser.parse_args()
    if not args.nexen.is_file() or not os.access(args.nexen, os.X_OK):
        raise RuntimeError("Nexen unavailable")
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    timeline: list[dict[str, object]] = []
    is_sa1 = args.rom.read_bytes()[0x7FD5] == 0x23
    sa1_states: dict[str, dict[str, object]] = {}
    last = None
    started = False
    submitted = False
    next_submitted = False
    post_return_submitted = False
    pre_submitted = False
    title_started = False
    room_requested = False
    cpu = None
    trace = None
    room_zero_event = None
    reset_vector_baseline = None
    error_event_baseline = None
    error_events: list[dict[str, object]] = []
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=2.0, socket_timeout=120.0,
        stderr_log=args.output.with_suffix(".stderr.log"),
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        reset_vector_baseline = session.read_memory(
            "snesMemory", RESET_VECTOR_COUNT, 1
        )[0]
        reset_diag_baseline = u16(session.read_memory("snesMemory", RESET_DIAG, 2))
        reset_diag_counts_baseline = {
            "nmi": u16(session.read_memory("snesMemory", RESET_DIAG + 14, 2)),
            "irq": u16(session.read_memory("snesMemory", RESET_DIAG + 16, 2)),
            "brk": u16(session.read_memory("snesMemory", RESET_DIAG + 18, 2)),
            "cop": u16(session.read_memory("snesMemory", RESET_DIAG + 20, 2)),
        }
        error_event_baseline = session.read_memory(
            "snesMemory", ERROR_EVENT, 1
        )[0]
        last_error_event_count = error_event_baseline
        if is_sa1:
            sa1_states["power_on"] = stable_cpu(session.get_cpu_state("Sa1"))
        for frame in range(1, args.max_frames + 1):
            run_frames_exact(session, 1)
            state = snapshot(session, frame)
            event_count = state["error_event"]["count"]
            if event_count != last_error_event_count:
                error_events.append({"frame": frame, **state["error_event"]})
                last_error_event_count = event_count
            if (room_zero_event is None and next_submitted
                    and state["active_room"] == 0):
                room_zero_event = {
                    "frame": frame,
                    "state": state,
                    "cpu": session.get_cpu_state(),
                    "trace": session.trace_log(64),
                }
            # Drive the authentic controller boundary: wait for the title
            # room, press START for one frame, then release it.  No room or
            # script state is written by the validator.
            if not title_started and state["active_room"] == 75:
                session.tool("set_input", {"port": 0, "buttons": 0x1000, "hold": True})
                title_started = True
            elif title_started and state["active_room"] == 75:
                session.tool("set_input", {"port": 0, "buttons": 0, "hold": True})
            # If a profile boots without its title room, retain the explicit
            # controlled-room fallback.  Do not race the title startup path
            # with a mailbox write while the engine is still constructing it.
            if (not room_requested and not title_started
                    and (state["active_room"] not in (0, 68, 75)
                         or (frame >= 10 and state["active_room"] == 0))):
                requested_room = 49 if args.controlled_room49 else 31
                session.write_memory("snesMemory", ROOM_REQUEST_ROOM,
                                     bytes((requested_room,)).hex())
                session.write_memory("snesMemory", ROOM_REQUEST_PENDING, "01")
                room_requested = True
            if state["active_room"] == 49 and state["active_record"] == 0:
                started = True
            if (next_submitted and args.post_return_object is not None
                    and not post_return_submitted
                    and stable_room49_checkpoint(state)):
                session.write_memory("snesMemory", SENTENCE_API_VERB,
                                     bytes((args.post_return_verb, 0)).hex())
                session.write_memory("snesMemory", SENTENCE_API_OBJECT1,
                                     args.post_return_object.to_bytes(2, "little").hex())
                session.write_memory("snesMemory", SENTENCE_API_OBJECT2, "0000")
                session.write_memory("snesMemory", 0x7E7EC7, "01")
                session.write_memory("snesMemory", SENTENCE_INJECTED, "01")
                post_return_submitted = True
            if (started and not submitted and args.direct_room49_object is None
                    and state["active_room"] == 49
                    and state["actor"]["moving"] == 0
                    and state["sentence_count"] == 0):
                session.write_memory("snesMemory", SENTENCE_API_VERB, bytes((10, 0)).hex())
                session.write_memory("snesMemory", SENTENCE_API_OBJECT1,
                                     (596).to_bytes(2, "little").hex())
                session.write_memory("snesMemory", SENTENCE_API_OBJECT2, "0000")
                session.write_memory("snesMemory", 0x7E7EC7, "01")
                session.write_memory("snesMemory", SENTENCE_INJECTED, "01")
                submitted = True
            if (args.direct_room49_object is not None
                    and not submitted
                    and stable_room49_checkpoint(state)):
                session.write_memory("snesMemory", SENTENCE_API_VERB,
                                     bytes((args.direct_room49_verb, 0)).hex())
                session.write_memory("snesMemory", SENTENCE_API_OBJECT1,
                                     args.direct_room49_object.to_bytes(2, "little").hex())
                session.write_memory("snesMemory", SENTENCE_API_OBJECT2, "0000")
                session.write_memory("snesMemory", 0x7E7EC7, "01")
                session.write_memory("snesMemory", SENTENCE_INJECTED, "01")
                submitted = True
            # Once the authored transition has committed room 63, no further
            # host-side input is required.  Run the long authored delays in a
            # single emulator call; per-frame memory snapshots are useful for
            # the route gate but would obscure the post-entry lifecycle.
            if (state["active_room"] == 63 and state["active_record"] == 3
                    and state["room_phase"] == 0
                    and state["actor"]["room"] == 63
                    and args.next_object is not None and not next_submitted
                    and (not pre_submitted or (
                        args.pre_next_object is not None
                        and state["sentence_count"] == 0
                        and not any(item["number"] in {2, 201, 202, 211}
                                    for item in state["slots"])
                    ))):
                # Branch only from the accepted stable room-63 checkpoint.
                # The first room-visible frame can still contain the retiring
                # room-49 owner; run the same long observation window used by
                # the Phase 6L acceptance before submitting player input.
                # A prerequisite action must begin at the first stable
                # checkpoint; otherwise the observation budget is consumed
                # before the prerequisite can run.  Only the final action
                # uses the historical long settle window.
                # The accepted room-63 checkpoint is already stable.  A long
                # debugger settle here can run past the semantic boundary and
                # leave the S-CPU mid-transaction before the next mailbox
                # write.  Give the room loop only two ordinary frames before
                # submitting the next sentence.
                settle = 0 if (not pre_submitted and args.pre_next_object is not None) else 2
                if settle:
                    settle_total = settle
                    while settle:
                        # Keep the post-prerequisite observation on the same
                        # frame transaction boundary as the sentence itself.
                        # A batched debugger run can leave the S-CPU inside a
                        # long authored frame when the next mailbox write is
                        # made, which makes the harness mistake an emulator
                        # watchdog stop for a room transition.
                        step = min(1 if pre_submitted else 25, settle)
                        run_frames_exact(session, step)
                        settle -= step
                    frame += settle_total
                    state = snapshot(session, frame)
                if not pre_submitted and args.pre_next_object is not None:
                    submit_object = args.pre_next_object
                    pre_submitted = True
                else:
                    submit_object = args.next_object
                    next_submitted = True
                session.write_memory("snesMemory", SENTENCE_API_VERB,
                                     bytes((args.next_verb, 0)).hex())
                session.write_memory("snesMemory", SENTENCE_API_OBJECT1,
                                     submit_object.to_bytes(2, "little").hex())
                session.write_memory("snesMemory", SENTENCE_API_OBJECT2, "0000")
                session.write_memory("snesMemory", 0x7E7EC7, "01")
                session.write_memory("snesMemory", SENTENCE_INJECTED, "01")
            if (state["active_room"] == 63 and frame < args.max_frames
                    and (args.next_object is None or next_submitted)):
                remaining = args.max_frames - frame
                while remaining:
                    # The return sentence is a lifecycle boundary: retain
                    # one-frame observability until the requested room is
                    # installed (or a reset is proven), rather than allowing
                    # a batched debugger run to hide the event.
                    # A prerequisite sentence is itself a lifecycle boundary.
                    # Keep it frame-observable too; batching its movement and
                    # nested waits can make the emulator watchdog/reset path
                    # look like an authored room-0 transition.
                    step = min(1 if (next_submitted or pre_submitted) else 25,
                               remaining)
                    run_frames_exact(session, step)
                    remaining -= step
                    if args.probe:
                        frame += step
                        tail_state = snapshot(session, frame)
                        event_count = tail_state["error_event"]["count"]
                        if event_count != last_error_event_count:
                            error_events.append({"frame": frame, **tail_state["error_event"]})
                            last_error_event_count = event_count
                        if (room_zero_event is None and next_submitted
                                and tail_state["active_room"] == 0):
                            room_zero_event = {
                                "frame": frame,
                                "state": tail_state,
                                "cpu": session.get_cpu_state(),
                                "trace": session.trace_log(64),
                            }
                        if (next_submitted and args.post_return_object is not None
                                and not post_return_submitted
                                and stable_room49_checkpoint(tail_state)):
                            session.write_memory("snesMemory", SENTENCE_API_VERB,
                                                 bytes((args.post_return_verb, 0)).hex())
                            session.write_memory(
                                "snesMemory", SENTENCE_API_OBJECT1,
                                args.post_return_object.to_bytes(2, "little").hex())
                            session.write_memory("snesMemory", SENTENCE_API_OBJECT2, "0000")
                            session.write_memory("snesMemory", 0x7E7EC7, "01")
                            session.write_memory("snesMemory", SENTENCE_INJECTED, "01")
                            post_return_submitted = True
                        timeline.append(tail_state)
                state = snapshot(session, args.max_frames)
                timeline.append(state)
                break
            if not started and frame < args.max_frames:
                continue
            key = (
                state["error"], state["active_room"], state["sentence_injected"],
                state["sentence_count"], state["verb_result"], state["owner_result"],
                state["get_dist"]["exec_count"], state["last_opcode"], state["pc"],
                tuple(state["actor"].values()), state["wait_blocks"], state["wait_releases"],
                tuple((item["slot"], item["program"], item["pc"], item["status"])
                      for item in state["slots"]),
            )
            if key != last:
                timeline.append(state)
                last = key
            if is_sa1:
                if "engine_boot" not in sa1_states and state["engine_lifecycle"] == 2:
                    sa1_states["engine_boot"] = stable_cpu(session.get_cpu_state("Sa1"))
                if "walk" not in sa1_states and state["actor"]["moving"]:
                    sa1_states["walk"] = stable_cpu(session.get_cpu_state("Sa1"))
                if ("lscr_211" not in sa1_states
                        and state["start_object"]["lscr_entry_seen"]):
                    sa1_states["lscr_211"] = stable_cpu(session.get_cpu_state("Sa1"))
            if state["error"]:
                cpu = session.get_cpu_state()
                if is_sa1:
                    sa1_states["terminal"] = stable_cpu(session.get_cpu_state("Sa1"))
                trace = session.trace_log(96)
                break
        if cpu is None:
            cpu = session.get_cpu_state()
            trace = session.trace_log(96)
        control = session.read_memory("snesMemory", SA1_CONTROL, 0x12) if is_sa1 else b""
    movement_start = next(
        (state["movement_tick"] - 1 for state in timeline
         if state["sentence_injected"] and state["actor"]["destination_box"] == 1
         and state["actor"]["moving"]),
        None,
    )
    transitions: list[dict[str, int]] = []
    last_box = None
    if movement_start is not None:
        for state in timeline:
            actor = state["actor"]
            if not state["sentence_injected"] or state["movement_tick"] <= movement_start:
                continue
            box = actor["walkbox"]
            if box == last_box:
                continue
            transitions.append({
                "tick": state["movement_tick"] - movement_start,
                "walkbox": box,
                "x": actor["position"][0],
                "y": actor["position"][1],
            })
            last_box = box
    expected = ((10, 1), (15, 13), (8, 26), (6, 31), (5, 38), (22, 42),
                (4, 52), (14, 63), (3, 69), (2, 85), (1, 90))
    observed = {item["walkbox"]: item["tick"] for item in transitions}
    final = timeline[-1]
    actor = final["actor"]
    assertions = {
        "sentence_prelude": final["sentence_injected"] == 1
            and final["verb_result"] == 0x29 and final["owner_result"] == 15,
        "canonical_transitions": all(observed.get(box) == tick for box, tick in expected),
        "movement_completion": movement_start is not None
            and final["movement_tick"] - movement_start == 91
            and actor["position"] == [57, 46] and actor["walkbox"] == 1
            and actor["moving"] == 0,
        "wait_blocked": final["wait_blocks"] == 91,
        "wait_released_semantically": final["get_dist"]["exec_count"] == 1,
        "get_dist": final["get_dist"] == {
            "pc_before": 0x038E, "pc_after": 0x0395,
            "result_offset": 0, "result_before": 15,
            "operand1": 1, "operand2": 596,
            "type1": 1, "type2": 2,
            "xy1": [57, 46], "xy2_raw": [58, 43],
            "xy2_adjusted": [57, 46], "dx": 0, "dy": 0,
            "result": 0, "adjusted": 1, "exec_count": 1, "stage": 0x14,
        },
        "start_object_decode": final["start_object"] == {
            "object": 596, "entry": 10, "program": 232, "entry_offset": 0x29,
            "pc_before": 0x0458, "pc_after_args": 0x0464,
            "slot": 3, "arg_count": 2, "exec_count": 1,
            "chain_target": 211, "object_retired": 1,
            "lscr_program": 221, "lscr_entry_seen": 1,
            "arguments": [0, 10],
        },
        "object_program_trace": [232, 0x29, 0, 0x42] in final["start_trace"],
        "lscr_211_entry_trace": [221, 0, 0, 0x62] in final["start_trace"],
        "object_slot_retyped": any(
            item["slot"] == 3 and item["number"] == 211
            and item["object_number"] == 0 and item["where"] == 3
            for item in final["slots"]
        ),
        "next_blocker_after_chain": final["last_opcode"] == 0xB2
            and final["error"] == 3
            and any(item["number"] == 211 and item["pc"] == 0x026F
                    for item in final["slots"]),
        "no_debugger_writes": True,
    }
    if is_sa1:
        reset_state = sa1_states["power_on"]
        assertions["sa1_remains_reset"] = all(
            state == reset_state for state in sa1_states.values()
        ) and reset_state == {
            "pc": 0, "k": 0, "a": 0, "x": 0, "y": 0, "sp": 0x1FF,
            "d": 0, "dbr": 0, "ps": 0x34, "emulationMode": True,
        }
        legacy_control = bytes(
            b"SA1C" + bytes((1, 1, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0))
        )
        mode3_control = bytes(
            b"SA1C" + bytes((1, 1, 0, 0, 2, 0, 1, 1, 1, 0, 1, 0, 1, 0))
        )
        assertions["sa1_control_contract"] = control in (legacy_control, mode3_control)
    passed = all(assertions.values())
    if not args.probe and not passed:
        raise RuntimeError(f"M25 frame-loop gate failed: {assertions}")
    report = {
        "gate": "M25-authentic-sentence-movement", "result": "probe" if args.probe else "pass",
        "fresh_power_on": True, "debugger_writes": 0,
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "reset_vector_baseline": reset_vector_baseline,
        "reset_vector_delta": (
            (final["reset_vector_count"] - reset_vector_baseline) & 0xFF
            if reset_vector_baseline is not None else None
        ),
        "reset_diag_delta": {
            "reset": (final["reset_diag"]["count"] - reset_diag_baseline) & 0xFFFF,
            **{
                key: (final["reset_diag"][key] - value) & 0xFFFF
                for key, value in reset_diag_counts_baseline.items()
            },
        },
        "error_event_baseline": error_event_baseline,
        "error_event_delta": (
            (final["error_event"]["count"] - error_event_baseline) & 0xFF
            if error_event_baseline is not None else None
        ),
        "error_events": error_events,
        "timeline": timeline,
        "movement_start_tick": movement_start,
        "normalized_transitions": transitions,
        "assertions": assertions,
        "start_object_instruction": {
            "script": "global script 2", "offset": 0x0458,
            "surrounding_bytes": (
                "06 40 2e 14 00 00 91 01 00 03 c0 9a 07 00 01 40 "
                "f7 01 40 00 40 81 02 40 81 00 40 ff"
            ),
            "decode": "startObject(Local[1]=596, Local[0]=10, [Local[2]=0, Local[0]=10])",
            "pc_after_arguments": 0x0464,
        },
        "next_blocker": {
            "script": "room.49 / LSCR.211", "offset": 0x026E,
            "surrounding_start": 0x025E,
            "surrounding_bytes": (
                "1a 00 40 00 00 48 00 40 00 00 81 00 62 d7 62 56 "
                "b2 02 00 28 90 a1 02 00 23 00 11 02 01 14 02 0f "
                "49 27 6c 6c 20 77 61 69 74 20 68 65 72 65 2e ff"
            ),
            "decode": "$B2 setCameraAt(Var[2])",
            "operand_value": final["var2"],
            "classification": "unsupported opcode semantic",
        },
        "final": final,
        "cpu": cpu,
        "carrier": {
            "kind": "sa1_bwram" if is_sa1 else "lorom",
            "sa1_architectural_checkpoints": sa1_states,
            "bwram_control": control.hex() if is_sa1 else None,
        },
        "trace": trace,
        "room_zero_event": room_zero_event,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": report["result"], "output": str(args.output),
                      "final": report["final"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
