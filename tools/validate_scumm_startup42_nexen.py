#!/usr/bin/env python3
"""Focused controlled startup-root validation for Fate room 42."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
COMMON = 0x7E2300
ROOM = 0x7FF2BE
SLOTS_STATUS = 0x7E2380
SLOTS_NUMBER = 0x7E2399
SLOTS_PROGRAM = 0x7E23B2
SLOTS_PC = 0x7E23E4


def build_identity_for(rom: Path) -> dict[str, str] | None:
    sidecar = rom.with_suffix(".build_identity.json")
    if not sidecar.is_file():
        return None
    raw = sidecar.read_bytes()
    return {"path": str(sidecar), "sha256": hashlib.sha256(raw).hexdigest()}


def u16(b: bytes, n: int = 0) -> int:
    return int.from_bytes(b[n:n + 2], "little")


def room42_sentence_ready(state: dict, expected_room: int = 42) -> bool:
    """Require the completed room-entry handoff, not just room publication.

    M24RB publishes the new room before its resource/ENCD pass has completed.
    The accepted room-42 input boundary is the subsequent stable frame where
    the persistent room scripts are installed and the semantic mailbox is
    idle.  This remains observational and does not require a particular slot
    number or force any VM state.
    """
    if expected_room != 42:
        # Room-specific authored scripts are not a readiness contract for a
        # generic scenario root.  Require only the common semantic boundary:
        # installed room, idle actor, no pending sentence, and no cutscene or
        # talk owner.  This keeps room-55 validation observational and avoids
        # borrowing room-42's persistent-script assumptions.
        return (
            state.get("room") == expected_room
            and state.get("room_phase") == 0
            and state.get("error") == 0
            and state.get("actor1_moving") == 0
            and state.get("actor1_walkbox", 0) != 0
            and state.get("cutscene", [1])[0] == 0
            and state.get("c20_count", 0) == 0
            and state.get("sentence_pending", 0) == 0
            and state.get("talk_lifetime", {}).get("active", 1) == 0
        )
    slots = state.get("slots", [])
    live_numbers = {
        item["number"] for item in slots if item.get("status") not in (0, 4)
    }
    return (
        state.get("room") == 42
        and state.get("room_phase") == 0
        and state.get("error") == 0
        and state.get("actor1_moving") == 0
        and state.get("actor1_walkbox", 0) != 0
        and state.get("cutscene", [1])[0] == 0
        and state.get("c20_count", 0) == 0
        # Source script numbers are stable across cooker/resource-order
        # changes; generated program identities are not.  LSCR 208 is the
        # persistent ambient loop.  LSCR 201 is an authored one-shot that may
        # have retired before the room becomes input-ready, so its presence is
        # neither a readiness requirement nor evidence of a pending action.
        # Global script 1 owns startup and must retire.  LSCR 200 can retain
        # a yielded post-cutscene slot after user control is restored; its
        # physical retirement is not an input-readiness condition.
        and 208 in live_numbers
        and 1 not in live_numbers
    )


def mapped_cpu_address(symbol: str) -> int:
    """Resolve a bank-0 symbol from the build map, avoiding stale hooks."""
    map_path = ROOT / "build" / "same-engine-host.map"
    for line in map_path.read_text().splitlines():
        fields = line.split()
        if len(fields) >= 3 and fields[0] == ";" and fields[2] == symbol:
            return int(fields[1].lstrip("$"), 16)
    raise RuntimeError(f"{symbol} not found in {map_path}")


def mapped_cpu_address_for_rom(rom: Path, symbol: str) -> int:
    """Resolve a bank-0 symbol from the map emitted beside this ROM."""
    map_path = rom.with_suffix(".map")
    if not map_path.is_file():
        return mapped_cpu_address(symbol)
    for line in map_path.read_text().splitlines():
        fields = line.split()
        if len(fields) >= 3 and fields[0] == ";" and fields[2] == symbol:
            return int(fields[1].lstrip("$"), 16)
    raise RuntimeError(f"{symbol} not found in {map_path}")


def class_mask(s, object_id: int) -> int | None:
    """Read the sparse C16 record for an object at a sentence boundary."""
    raw = s.read_memory("snesMemory", 0x7F5F10, 0x1000)
    for offset in range(0, len(raw), 8):
        if raw[offset] and int.from_bytes(raw[offset + 2:offset + 4], "little") == object_id:
            return int.from_bytes(raw[offset + 4:offset + 8], "little")
    return None


def snap(s):
    c = s.read_memory("snesMemory", COMMON, 0x64)
    c23 = s.read_memory("snesMemory", 0x7FD408, 0x51)
    talk = s.read_memory("snesMemory", 0x7E7A20, 0xAD)
    r = s.read_memory("snesMemory", ROOM, 0x42)
    st = s.read_memory("snesMemory", SLOTS_STATUS, 25)
    no = s.read_memory("snesMemory", SLOTS_NUMBER, 25)
    pr = s.read_memory("snesMemory", SLOTS_PROGRAM, 25)
    didexec = s.read_memory("snesMemory", 0x7E23CB, 25)
    freeze = s.read_memory("snesMemory", 0x7E2B08, 25)
    pc = s.read_memory("snesMemory", SLOTS_PC, 50)
    freeze = s.read_memory("snesMemory", 0x7E2B08, 25)
    delay = s.read_memory("snesMemory", 0x7E2416, 50)
    didexec = s.read_memory("snesMemory", 0x7E23CB, 25)
    where = s.read_memory("snesMemory", 0x7E7F46, 25)
    return {
        "frame": s.get_state()["frameCount"], "room": r[1], "room_phase": r[4],
        "m23a": list(s.read_memory("snesMemory", 0x7FF2BE, 0x42)),
        "room_request_diag": list(s.read_memory("snesMemory", 0x7E5450, 8)),
        "title_gate_diag": list(s.read_memory("snesMemory", 0x7E565C, 7)),
        "input": list(s.read_memory("snesMemory", 0x7E2200, 8)),
        "event": list(s.read_memory("snesMemory", 0x7E2000, 12)),
        "event_queue": list(s.read_memory("snesMemory", 0x7E2100, 0x100)),
        "room_lifecycle": list(r[25:25 + min(r[24], 16)]),
        "pc": u16(c), "opcode": c[6], "error": c[3], "program": c[0x62],
        "c23_text": {"actor": c23[0x4C], "raw_index": c23[0x30],
                     "last_length": c23[0x31],
                     "raw": list(c23[0x32:0x32 + min(c23[0x30], 16)])},
        "talk": {"active": talk[0], "have_msg": talk[1],
                 "raw_length": talk[8], "keep_text": talk[0xA6]},
        # The frame phase is the final byte of the reset-diagnostic block:
        # SAME_RESET_DIAG_ENGINE_PHASE = $7E103C.  $7E1024 is unrelated.
        "diag_stage": s.read_memory("snesMemory", 0x7E103C, 1)[0],
        "engine_lifecycle": s.read_memory("snesMemory", 0x7E2221, 1)[0],
        # M23A lifecycle trace is an engine-owned diagnostic ring.  Keep this
        # in the validator snapshot so room-script completion can be compared
        # at coherent frame boundaries without adding production probes.
        "m23a_lifecycle_count": s.read_memory("snesMemory", 0x7FF2D6, 1)[0],
        "m23a_lifecycle": list(s.read_memory("snesMemory", 0x7FF2D7, 14)),
        "engine_frame_busy": s.read_memory("snesMemory", 0x7E2231, 1)[0],
        "c4_error_origin": s.read_memory("snesMemory", 0x7E57B1, 1)[0],
        "c4_return": {
            "p": s.read_memory("snesMemory", 0x7E57B2, 1)[0],
            "slot": s.read_memory("snesMemory", 0x7E57B3, 1)[0],
            "program": s.read_memory("snesMemory", 0x7E57B4, 1)[0],
            "pc": u16(s.read_memory("snesMemory", 0x7E57B5, 2)),
            "status": s.read_memory("snesMemory", 0x7E57B7, 1)[0],
            "error": s.read_memory("snesMemory", 0x7E57B8, 1)[0],
        },
        "reset_diag": list(s.read_memory("snesMemory", 0x7E1020, 0x20)),
        "m25a_trace": list(s.read_memory("snesMemory", 0x7E5000, 0x80)),
        "start_trace": list(s.read_memory("snesMemory", 0x7E7ED7, 0x41)),
        "alloc_trace": list(s.read_memory("snesMemory", 0x7E5900, 0x81)),
        "op_trace": list(s.read_memory("snesMemory", 0x7E5A00, 0x402)),
        "m23c_trace_count": s.read_memory("snesMemory", 0x7FF957, 1)[0],
        "m23c_trace_overflow": s.read_memory("snesMemory", 0x7FF958, 1)[0],
        "m23c_trace": list(s.read_memory("snesMemory", 0x7FF97C, 0x80)),
        "m24rb_alloc": list(s.read_memory("snesMemory", 0x7E5980, 4)),
        "error_site": s.read_memory("snesMemory", 0x7E5F08, 1)[0],
        "error_setter": list(s.read_memory("snesMemory", 0x7E5F20, 32)),
        "error_context": list(s.read_memory("snesMemory", 0x7E5F20, 16)),
        "c16_diag": list(s.read_memory("snesMemory", 0x7F6F10, 12)),
        "cutscene": list(s.read_memory("snesMemory", 0x7FD348, 0x38)),
        "c19_diag": list(s.read_memory("snesMemory", 0x7E5680, 32)),
        "stop_diag": list(s.read_memory("snesMemory", 0x7E5624, 5)),
        "compare_zero_diag": list(s.read_memory("snesMemory", 0x7E9000, 16)),
        "compare_zero_diag": list(s.read_memory("snesMemory", 0x7E56A0, 16)),
        "c25_entry": s.read_memory("snesMemory", 0x7E5654, 1)[0],
        "c25_stable": list(s.read_memory("snesMemory", 0x7E5654, 8)),
        "setclass": list(s.read_memory("snesMemory", 0x7E5476, 4)),
        "c16_state": list(s.read_memory("snesMemory", 0x7F6F10, 12)),
        "c16_records": list(s.read_memory("snesMemory", 0x7F5F10, 0x1000)),
        "c25": list(s.read_memory("snesMemory", 0x7FD459, 1)) + list(s.read_memory("snesMemory", 0x7FD86A, 7)),
        "c25_error": list(s.read_memory("snesMemory", 0x7E5990, 11)),
        "c25_error_detail": list(s.read_memory("snesMemory", 0x7E5F27, 10)),
        "c25_observation": list(s.read_memory("snesMemory", 0x7E5F40, 18)),
        "c25_producer": list(s.read_memory("snesMemory", 0x7E5F52, 14)),
        "c25_error_record": list(s.read_memory("snesMemory", 0x7E5F60, 65)),
        "c25_dispatch": list(s.read_memory("snesMemory", 0x7E5F80, 5)),
        "save_context": list(s.read_memory("snesMemory", 0x7E5F86, 7)),
        "c25_error_meta": list(s.read_memory("snesMemory", 0x7E5F09, 9)),
        "c25_queue_raw": list(s.read_memory("snesMemory", 0x7FD45A, 0x145)),
        "c25_error_last_op": list(s.read_memory("snesMemory", 0x7E5F04, 15)),
        "start_diag": list(s.read_memory("snesMemory", 0x7E5636, 10)) + list(s.read_memory("snesMemory", 0x7E5650, 4)),
        "scenario": list(s.read_memory("snesMemory", 0x7E5600, 4)),
        "active_count": s.read_memory("snesMemory", 0x7E2A87, 1)[0],
        "slot_raw": {"status": list(st), "number": list(no), "program": list(pr)},
        "slot_freeze": list(freeze), "slot_didexec": list(didexec),
        "slot_where": list(where),
        "scheduler": {"calls": s.read_memory("snesMemory", 0x7E5623, 1)[0],
                      "ready": s.read_memory("snesMemory", 0x7E561E, 1)[0],
                      "gate": s.read_memory("snesMemory", 0x7E5622, 1)[0],
                      "sentence_gate": s.read_memory("snesMemory", 0x7E57A4, 1)[0],
                      "cursor": s.read_memory("snesMemory", 0x7E2B22, 1)[0],
                      "active_count": s.read_memory("snesMemory", 0x7E2A8A, 1)[0],
                      "sentence_fetch_count": s.read_memory("snesMemory", 0x7E562A, 1)[0],
                      "sentence_fetch_pc": u16(s.read_memory("snesMemory", 0x7E562B, 2)),
        "sentence_fetch_opcode": s.read_memory("snesMemory", 0x7E562D, 1)[0],
        "logical_frame": u16(s.read_memory("snesMemory", 0x7E2308, 2)),
        "m23a_phase": s.read_memory("snesMemory", 0x7FF2C2, 1)[0],
        "m23a_hold": s.read_memory("snesMemory", 0x7FF2C4, 1)[0],
        "c1_hold_after": u16(s.read_memory("snesMemory", 0x7E2364, 2)),
        "talk": {"active": s.read_memory("snesMemory", 0x7E7A20, 1)[0],
                 "have_msg": s.read_memory("snesMemory", 0x7E7A21, 1)[0],
                 "delay": u16(s.read_memory("snesMemory", 0x7E7A24, 2)),
                 "cursor": s.read_memory("snesMemory", 0x7E7AC1, 1)[0],
                 "raw_length": s.read_memory("snesMemory", 0x7E7A28, 1)[0]},
        },
        "m25a_trace": list(s.read_memory("snesMemory", 0x7E5000, 0x80)),
        "sentence_scheduler_handoff": {
            "phase": s.read_memory("snesMemory", 0x7E5674, 1)[0],
            "slot": s.read_memory("snesMemory", 0x7E5675, 1)[0],
            "program": s.read_memory("snesMemory", 0x7E5676, 1)[0],
            "vm_pc": u16(s.read_memory("snesMemory", 0x7E5677, 2)),
            "slot_pc": u16(s.read_memory("snesMemory", 0x7E5679, 2)),
            "status": s.read_memory("snesMemory", 0x7E567B, 1)[0],
            "current": s.read_memory("snesMemory", 0x7E567C, 1)[0],
        },
        "scheduler_gate_trace": {
            "last_scan_gate": s.read_memory("snesMemory", 0x7E57A4, 1)[0],
            "sentence_status": s.read_memory("snesMemory", 0x7E561B, 1)[0],
            "sentence_didexec": s.read_memory("snesMemory", 0x7E561F, 1)[0],
            "sentence_freeze": s.read_memory("snesMemory", 0x7E5620, 1)[0],
        },
        "slot_delay": [u16(delay, i * 2) for i in range(25)],
        "slots": [{"slot": i, "status": st[i], "number": no[i],
                   "program": pr[i], "pc": u16(pc, i * 2),
                   "didexec": didexec[i], "freeze": freeze[i]}
                  for i in range(25) if st[i] or no[i] or pr[i]],
    }


def snap_light(s):
    """Frame-safe scenario snapshot with a bounded MCP transaction count.

    The original "light" snapshot still made several dozen independent MCP
    reads every frame.  That is both slow enough to cross debugger timing
    boundaries and needlessly noisy during the long authored title/dialogue
    lead-in.  Keep the semantic readiness fields in a handful of bulk reads;
    the detailed snapshot remains available for targeted diagnostic runs.
    """
    common = s.read_memory("snesMemory", COMMON, 0x64)
    room = s.read_memory("snesMemory", ROOM, 0x42)
    # Slot fields used by readiness occupy one compact scheduler region.
    slots_raw = s.read_memory("snesMemory", SLOTS_STATUS, 0x98)
    slot_freeze = s.read_memory("snesMemory", 0x7E2B08, 25)
    slot_delay = s.read_memory("snesMemory", 0x7E2416, 50)
    actor_pos = s.read_memory("snesMemory", 0x7FF1A4, 4)
    actor_moving = s.read_memory("snesMemory", 0x7FF221, 1)[0]
    actor_walkbox = s.read_memory("snesMemory", 0x7FFDA6, 1)[0]
    # C31 positions are a packed four-byte record starting at $7FF1A0;
    # actor 2 therefore begins at $7FF1A8.  C31 moving is a byte table at
    # $7FF220, so actor 2 is $7FF222.  Keep these reads observational: the
    # fixture must not repair or otherwise write actor state here.
    actor2_pos = s.read_memory("snesMemory", 0x7FF1A0 + 8, 4)
    actor2_moving = s.read_memory("snesMemory", 0x7FF220 + 2, 1)[0]
    actor2_walkbox = s.read_memory("snesMemory", 0x7FFDA6 + 2, 1)[0]
    put_actor_last = s.read_memory("snesMemory", 0x7FFEC5, 10)
    put_actor_work = s.read_memory("snesMemory", 0x7FFB65, 0x12)
    put_actor_trace = s.read_memory("snesMemory", 0x7FFF00, 0x100)
    actor_identity = s.read_memory("snesMemory", 0x7F3700, 0x17)
    c20 = s.read_memory("snesMemory", 0x7FD380, 1)[0]
    cutscene = s.read_memory("snesMemory", 0x7FD348, 1)[0]
    object_states = s.read_memory("snesMemory", 0x7E6000 + 489, 12)
    object_owners = s.read_memory("snesMemory", 0x7E8000 + 489, 12)
    m24rb = s.read_memory("snesMemory", 0x7FFA30, 0x08)
    active_record = s.read_memory("snesMemory", 0x7FF2BE, 1)[0]
    move_state = s.read_memory("snesMemory", 0x7E7BAA, 0x330)
    talk_state = s.read_memory("snesMemory", 0x7E7A20, 0xB5)
    setstate_count = s.read_memory("snesMemory", 0x7E78A1, 1)[0]
    surface_diag = s.read_memory("snesMemory", 0x401000, 0x40)
    surface_state = s.read_memory("snesMemory", 0x401080, 0x34)
    event_state = s.read_memory("snesMemory", 0x7E2000, 0x10)
    dma_state = s.read_memory("snesMemory", 0x7E223A, 0x0C)
    # Existing fixture-only opcode trace: keep the light snapshot able to
    # identify the ENCD divergence without switching to the large snapshot.
    # This is observation only; the trace is written by the target fixture.
    op_trace = s.read_memory("snesMemory", 0x7E5A00, 0x402)
    c4_return = s.read_memory("snesMemory", 0x7E57B1, 8)
    save_context = s.read_memory("snesMemory", 0x7E5F86, 7)
    m23a_lifecycle_count = s.read_memory("snesMemory", 0x7FF2D6, 1)[0]
    m23a_lifecycle = s.read_memory("snesMemory", 0x7FF2D7, 14)

    def slot_byte(address: int, index: int) -> int:
        return slots_raw[address - SLOTS_STATUS + index]

    def slot_word(address: int, index: int) -> int:
        offset = address - SLOTS_STATUS + index * 2
        return u16(slots_raw, offset)

    slots = []
    for index in range(25):
        status = slot_byte(SLOTS_STATUS, index)
        if status in (0, 4):
            continue
        slots.append({
            "slot": index,
            "status": status,
            "number": slot_byte(SLOTS_NUMBER, index),
            "program": slot_byte(SLOTS_PROGRAM, index),
            "pc": slot_word(SLOTS_PC, index),
            "didexec": slot_byte(0x7E23CB, index),
            "freeze": slot_freeze[index],
            "delay": u16(slot_delay, index * 2),
            # A sentence launcher may execute its complete prelude within a
            # frame.  Preserve its source-visible locals in the light trace
            # so a tuple-to-dispatch divergence can be diagnosed without
            # adding emulated-memory instrumentation.
            "locals": [u16(s.read_memory("snesMemory", 0x7E2448 + index * 64 + word * 2, 2))
                       for word in range(3)],
        })
    return {
        "frame": s.get_state()["frameCount"],
        "cpu": s.get_cpu_state("Snes"),
        "cpu_io": {
            "nmitimen": s.read_memory("snesMemory", 0x4200, 1)[0],
            "hvbjoy": s.read_memory("snesMemory", 0x4212, 1)[0],
        },
        "room": room[1], "room_phase": room[4], "active_record": active_record,
        "video": {
            "surface": list(surface_state),
            "backend": list(surface_diag),
            "events": list(event_state),
            "dma": list(dma_state),
        },
        "op_trace": list(op_trace),
        "c4_return": list(c4_return),
        "save_context": list(save_context),
        "m23a_lifecycle_count": m23a_lifecycle_count,
        "m23a_lifecycle": list(m23a_lifecycle),
        "pc": u16(common), "opcode": common[6], "error": common[3],
        "program": common[0x62],
        # Same_Frame_Run writes 1 on entry, 2 immediately before
        # Same_Engine_Frame, and 3 only after the engine returns.  This is a
        # coherent end-of-observation diagnostic, not a backend hook state.
        "engine_phase": s.read_memory("snesMemory", 0x7E103C, 1)[0],
        "actor1_position": [u16(actor_pos), u16(actor_pos, 2)],
        "actor1_moving": actor_moving,
        "actor1_walkbox": actor_walkbox,
        "actor1_costume": actor_identity[0], "actor1_room": actor_identity[0x16],
        "movement": {
            "current_box": move_state[0x41],
            "leg_origin": [u16(move_state, 0x62), u16(move_state, 0xA2)],
            "leg_target": [u16(move_state, 0xE2), u16(move_state, 0x122)],
            "fraction": [u16(move_state, 0x162), u16(move_state, 0x1A2)],
            "delta_hi": [u16(move_state, 0x222), u16(move_state, 0x2A2)],
            "route_source": move_state[0x300], "route_dest": move_state[0x301],
            "route_next": move_state[0x322], "portal_type": move_state[0x323],
            "portal_fixed": u16(move_state, 0x324),
            "portal_low": u16(move_state, 0x326), "portal_high": u16(move_state, 0x328),
        },
        "actor2_position": [u16(actor2_pos), u16(actor2_pos, 2)],
        "actor2_moving": actor2_moving,
        "actor2_walkbox": actor2_walkbox,
        "put_actor_last": {
            "actor": put_actor_last[0],
            "request": [u16(put_actor_last, 1), u16(put_actor_last, 3)],
            "result": [u16(put_actor_last, 5), u16(put_actor_last, 7)],
            "result_box": put_actor_last[9],
            "count": s.read_memory("snesMemory", 0x7FFEE6, 1)[0],
            "trace_count": s.read_memory("snesMemory", 0x7FFF00, 1)[0],
            "box_count": s.read_memory("snesMemory", 0x7FFA40, 1)[0],
            "geometry_work": list(put_actor_work),
            "flags_sample": list(s.read_memory("snesMemory", 0x7FFA41, 64)),
            "trace": list(put_actor_trace),
            "target_accessor_witness": s.read_memory("snesMemory", 0x7FFB40, 1)[0],
        },
        # C14 actor records are indexed by actor number; actor 1 starts at
        # 0x7F3700, so actor 2 is the next 0x40-byte record.
        "actor2_costume": s.read_memory("snesMemory", 0x7F3700 + 0x40, 1)[0],
        "actor2_room": s.read_memory("snesMemory", 0x7F3700 + 0x40 + 0x16, 1)[0],
        "cutscene": [cutscene], "c20_count": c20,
        "m24rb": {"state": m24rb[0], "trigger_marker": m24rb[1],
                  "deferred_count": m24rb[2], "marker_count": m24rb[3],
                  "fade_complete_count": m24rb[4],
                  "lscr_scheduled": m24rb[5],
                  "frame_end_flushes": m24rb[6],
                  "frame_end_active": m24rb[7]},
        "talk_lifetime": {
            "active": talk_state[0], "have_msg": talk_state[1],
            "delay": u16(talk_state, 4), "raw_length": talk_state[8],
            "cursor": talk_state[0xA1],
            "stop_count": talk_state[0x0A],
            "complete_count": talk_state[0x0B],
            "wait_blocks": talk_state[0xB1],
            "wait_resumes": talk_state[0xB2],
            "completed_frame": u16(talk_state, 0x0E),
        },
        "setstate_count": setstate_count,
        "sentence_pending": s.read_memory("snesMemory", 0x7E7EC7, 1)[0],
        "sentence_debug": {
            "slot": s.read_memory("snesMemory", 0x7E5617, 1)[0],
            "program": s.read_memory("snesMemory", 0x7E5618, 1)[0],
            "pc": u16(s.read_memory("snesMemory", 0x7E5619, 2)),
            "allocs": s.read_memory("snesMemory", 0x7E5606, 1)[0],
            "current": s.read_memory("snesMemory", 0x7E2A88, 1)[0],
        },
        "sentence_scheduler_handoff": {
            "phase": s.read_memory("snesMemory", 0x7E5674, 1)[0],
            "slot": s.read_memory("snesMemory", 0x7E5675, 1)[0],
            "program": s.read_memory("snesMemory", 0x7E5676, 1)[0],
            "vm_pc": u16(s.read_memory("snesMemory", 0x7E5677, 2)),
            "slot_pc": u16(s.read_memory("snesMemory", 0x7E5679, 2)),
            "status": s.read_memory("snesMemory", 0x7E567B, 1)[0],
            "current": s.read_memory("snesMemory", 0x7E567C, 1)[0],
        },
        "room42_object_state": {str(i): object_states[i - 489] for i in range(489, 501)},
        "object488_state": s.read_memory("snesMemory", 0x7E6000 + 488, 1)[0],
        "room42_object_owner": {str(i): object_owners[i - 489] for i in range(489, 501)},
        "scheduler": {"calls": s.read_memory("snesMemory", 0x7E561D, 1)[0],
                      "c4_calls": s.read_memory("snesMemory", 0x7E5623, 1)[0],
                      "m23a_phase": s.read_memory("snesMemory", 0x7FF2C2, 1)[0],
                      "m23a_hold": s.read_memory("snesMemory", 0x7FF2C4, 1)[0],
                      "active_record": s.read_memory("snesMemory", 0x7FF2BE, 1)[0],
                      "active_room": s.read_memory("snesMemory", 0x7FF2BF, 1)[0],
                      "frame_stage": s.read_memory("snesMemory", 0x7E567D, 1)[0],
                      "frame_stage_count": s.read_memory("snesMemory", 0x7E567E, 1)[0],
                      "c1_hold_after": u16(s.read_memory("snesMemory", 0x7E2364, 2)),
                      "scumm_status": s.read_memory("snesMemory", 0x7E2302, 1)[0],
                      "return_mode": s.read_memory("snesMemory", 0x7E2363, 1)[0],
                      "nested": s.read_memory("snesMemory", 0x7E2303, 1)[0],
                      "fixture_request": s.read_memory("snesMemory", 0x7E235E, 1)[0],
                      "fixture_active": s.read_memory("snesMemory", 0x7E235F, 1)[0],
                      "gate": s.read_memory("snesMemory", 0x7E5622, 1)[0],
                      "last_scan_gate": s.read_memory("snesMemory", 0x7E57A4, 1)[0],
                      "last_scan_slot": s.read_memory("snesMemory", 0x7E57A5, 1)[0],
                      "scan_count": s.read_memory("snesMemory", 0x7E57A6, 1)[0],
                      "match_count": s.read_memory("snesMemory", 0x7E57A7, 1)[0],
                      "alloc_frame": u16(s.read_memory("snesMemory", 0x7E57A8, 2)),
                      "alloc_c4": s.read_memory("snesMemory", 0x7E57AA, 1)[0],
                      "frame_entry_count": s.read_memory("snesMemory", 0x7E57AB, 1)[0],
                      "prepass_count": s.read_memory("snesMemory", 0x7E57AC, 1)[0],
                      "post_alloc_entry": s.read_memory("snesMemory", 0x7E57AD, 1)[0],
                      "post_alloc_c4": s.read_memory("snesMemory", 0x7E57AE, 1)[0],
                      "post_alloc_phase": s.read_memory("snesMemory", 0x7E57AF, 1)[0],
                      "sentence_gate_status": s.read_memory("snesMemory", 0x7E561B, 1)[0],
                      "sentence_gate_didexec": s.read_memory("snesMemory", 0x7E561F, 1)[0],
                      "sentence_gate_freeze": s.read_memory("snesMemory", 0x7E5620, 1)[0],
                      "ready": s.read_memory("snesMemory", 0x7E561E, 1)[0],
                      "cursor": s.read_memory("snesMemory", 0x7E2B22, 1)[0],
                      "active_count": s.read_memory("snesMemory", 0x7E2A8A, 1)[0],
                      "sentence_fetch_count": s.read_memory("snesMemory", 0x7E562A, 1)[0],
                      "sentence_fetch_pc": u16(s.read_memory("snesMemory", 0x7E562B, 2)),
                      "nmi_count": u16(s.read_memory("snesMemory", 0x7E102E, 2)),
                      "sentence_fetch_opcode": s.read_memory("snesMemory", 0x7E562D, 1)[0]},
        "slots": slots,
    }


def coherent_service_snapshot(s, state):
    """Read service state only at a completed logical-frame boundary.

    This is deliberately a validator-side snapshot.  It does not steer the
    engine and must not be used from write/FIFO/backend hooks, where the
    accepted-PRESENT routine is legitimately between its lock and state
    stores.
    """
    backend = bytes(s.read_memory("snesMemory", 0x401000, 0x40))
    surface = bytes(s.read_memory("snesMemory", 0x401080, 0x40))
    event = bytes(s.read_memory("snesMemory", 0x7E2000, 0x06))
    head = int.from_bytes(event[0:2], "little")
    tail = int.from_bytes(event[2:4], "little")
    count = int.from_bytes(event[4:6], "little")
    live_head = None
    if count:
        raw = bytes(s.read_memory("snesMemory", 0x7E2100 + (head & 0x0F) * 0x10, 0x10))
        live_head = {
            "service": raw[0], "opcode": raw[1], "flags": raw[2],
            "source": raw[3], "destination": raw[4],
            "arg0": int.from_bytes(raw[6:8], "little"),
            "arg1": int.from_bytes(raw[8:10], "little"),
            "arg2": int.from_bytes(raw[10:12], "little"),
            "sequence": int.from_bytes(raw[12:14], "little"),
        }
    dma = bytes(s.read_memory("snesMemory", 0x7E223A, 0x0C))
    return {
        "frame": state.get("frame"),
        "room": state.get("room"), "room_phase": state.get("room_phase"),
        "error": state.get("error"),
        "scumm_frame_ops": u16(s.read_memory("snesMemory", 0x7E230A, 2)),
        "scumm_total_ops": u16(s.read_memory("snesMemory", 0x7E230C, 2)),
        "scumm_budget": u16(s.read_memory("snesMemory", 0x7E2344, 2)),
        "scumm_last_opcode": s.read_memory("snesMemory", 0x7E2306, 1)[0],
        "scumm_program": s.read_memory("snesMemory", 0x7E2362, 1)[0],
        "scumm_pc": u16(s.read_memory("snesMemory", 0x7E2300, 2)),
        "engine_frame_busy": s.read_memory("snesMemory", 0x7E2231, 1)[0],
        "engine_lifecycle": s.read_memory("snesMemory", 0x7E2221, 1)[0],
        "nmi_counter": int.from_bytes(s.read_memory("snesMemory", 0x7E102E, 2), "little"),
        "pending_visual": surface[0x26],
        "pending_room": surface[0x27],
        "pending_room_generation": int.from_bytes(surface[0x28:0x2A], "little"),
        "surface_generation": int.from_bytes(surface[2:4], "little"),
        "backend_state": backend[0x13],
        "surface_locked": backend[0x14],
        "backend_pending_generation": int.from_bytes(backend[0x0E:0x10], "little"),
        "backend_committed_generation": int.from_bytes(backend[0x10:0x12], "little"),
        "accepted_present": int.from_bytes(backend[0x1A:0x1C], "little"),
        "rejected_present": int.from_bytes(backend[0x1C:0x1E], "little"),
        "backend_step_count": int.from_bytes(s.read_memory("snesMemory", 0x7E5EBC, 2), "little"),
        "event_head": head, "event_tail": tail, "event_count": count,
        "live_head": live_head,
        "dma_current": int.from_bytes(dma[0:2], "little"),
        "dma_pending": int.from_bytes(dma[2:4], "little"),
        "dma_committed": int.from_bytes(dma[4:6], "little"),
        "dma_deferred_blank": int.from_bytes(dma[6:8], "little"),
        "dma_deferred_budget": int.from_bytes(dma[8:10], "little"),
        "dma_rejected": int.from_bytes(dma[10:12], "little"),
        "cpu": s.get_cpu_state("Snes"),
    }


def snap_detail(s):
    """Full diagnostic snapshot for a targeted failure, not every frame."""
    c = s.read_memory("snesMemory", COMMON, 0x64)
    r = s.read_memory("snesMemory", ROOM, 0x08)
    st = s.read_memory("snesMemory", SLOTS_STATUS, 25)
    no = s.read_memory("snesMemory", SLOTS_NUMBER, 25)
    pr = s.read_memory("snesMemory", SLOTS_PROGRAM, 25)
    pc = s.read_memory("snesMemory", SLOTS_PC, 50)
    didexec = s.read_memory("snesMemory", 0x7E23CB, 25)
    freeze = s.read_memory("snesMemory", 0x7E2B08, 25)
    variables = s.read_memory("snesMemory", 0x7E0800, 0x400)
    locals3 = s.read_memory("snesMemory", 0x7E2448 + 3 * 64, 8)
    locals_by_slot = {
        str(slot): [u16(s.read_memory("snesMemory", 0x7E2448 + slot * 64, 8), i * 2)
                    for i in range(4)]
        for slot in (1, 2, 3, 4)
    }
    setstate_count = s.read_memory("snesMemory", 0x7E78A1, 1)[0]
    setstate_trace = []
    for i in range(min(setstate_count, 8)):
        b = s.read_memory("snesMemory", 0x7E78B0 + i * 8, 8)
        setstate_trace.append({"object": u16(b), "value": b[2],
                               "opcode": b[3], "pc_before": u16(b, 4),
                               "pc_after": u16(b, 6)})
    return {
        "frame": s.get_state()["frameCount"], "room": r[1], "room_phase": r[4],
        "actor1_position": [u16(s.read_memory("snesMemory", 0x7FF1A4, 2)),
                            u16(s.read_memory("snesMemory", 0x7FF1A6, 2))],
        "actor1_moving": s.read_memory("snesMemory", 0x7FF221, 1)[0],
        # PUT_ACTOR_WALKBOX is the engine-owned 32-byte actor array at
        # $7FFDA5; actor 1 is entry +1.  $7E7BEB is unrelated room scratch
        # and must not be used as sentence readiness state.
        "actor1_walkbox": s.read_memory("snesMemory", 0x7FFDA6, 1)[0],
        "actor1_costume": s.read_memory("snesMemory", 0x7F3700, 1)[0],
        "actor1_room": s.read_memory("snesMemory", 0x7F3716, 1)[0],
        # Bit 2049 is the source-authored locker-open gate used by the
        # focused scenario root (packed byte 0x100, mask 0x02).
        "bit2049": bool(s.read_memory("snesMemory", 0x7E2BA0 + 0x100, 1)[0] & 0x02),
        "scenario_sentence": list(s.read_memory("snesMemory", 0x7E5602, 5)),
        "sentence_pending": s.read_memory("snesMemory", 0x7E7EC7, 1)[0],
        "c20_count": s.read_memory("snesMemory", 0x7FD380, 1)[0],
        "scumm_status": s.read_memory("snesMemory", 0x7E2302, 1)[0],
        "engine_lifecycle": s.read_memory("snesMemory", 0x7E2221, 1)[0],
        "c1_hold_after": s.read_memory("snesMemory", 0x7E2364, 1)[0],
        "m23a_hold": s.read_memory("snesMemory", 0x7FF2C4, 1)[0],
        "engine_stage": s.read_memory("snesMemory", 0x7E103C, 1)[0],
        "setstate_trace": setstate_trace,
        "camera": list(s.read_memory("snesMemory", 0x7F5F0A, 2)),
        "room42_object_state": {str(i): s.read_memory("snesMemory", 0x7E6000 + i, 1)[0]
                                 for i in (489, 490, 491, 492, 493, 496, 497, 500)},
        "room42_object_owner": {str(i): s.read_memory("snesMemory", 0x7E8000 + i, 1)[0]
                                  for i in (489, 490, 491, 492, 493, 496, 497, 500)},
        "m23a": list(s.read_memory("snesMemory", 0x7FF2BE, 0x09)),
        "walk_object_diag": list(s.read_memory("snesMemory", 0x7E5700, 0x08)),
        "movement_start_count": s.read_memory("snesMemory", 0x7E7F18, 1)[0],
        "actor1_movement_control": {
            "moving": s.read_memory("snesMemory", 0x7FF221, 1)[0],
            "dest_x": u16(s.read_memory("snesMemory", 0x7FFDE7, 2)),
            "dest_y": u16(s.read_memory("snesMemory", 0x7E7BAC, 2)),
            "dest_box": s.read_memory("snesMemory", 0x7FFDC6, 1)[0],
        },
        # Read-only snapshot of the route query/result scratch.  This narrows
        # a rejected movement request to NextBox versus Portal without adding
        # target-side diagnostics or perturbing the movement lifecycle.
        "actor1_route_control": {
            "current_box": s.read_memory("snesMemory", 0x7E7BEB, 1)[0],
            "route_source": s.read_memory("snesMemory", 0x7E7EAA, 1)[0],
            "route_dest": u16(s.read_memory("snesMemory", 0x7E7EAB, 2)),
            "route_next": s.read_memory("snesMemory", 0x7E7ECC, 1)[0],
            "portal_type": s.read_memory("snesMemory", 0x7E7ECD, 1)[0],
            "portal_fixed": u16(s.read_memory("snesMemory", 0x7E7ECE, 2)),
            "portal_low": u16(s.read_memory("snesMemory", 0x7E7ED0, 2)),
            "portal_high": u16(s.read_memory("snesMemory", 0x7E7ED2, 2)),
        },
        "room_request_diag": list(s.read_memory("snesMemory", 0x7E5450, 8)),
        "title_gate_diag": list(s.read_memory("snesMemory", 0x7E565C, 7)),
        "input": list(s.read_memory("snesMemory", 0x7E2200, 8)),
        # Include the low sentence-dispatch variables in the focused trace:
        # program 2's authored walk/object gate uses these after its move
        # setup.  This is validator-side observation only.
        "variables_selected": {str(i): u16(variables, i * 2)
                                for i in tuple(range(0, 12)) + (19, 24, 28, 29, 30, 32, 33, 35, 36, 37, 43, 57, 58, 107, 111, 117, 118, 120, 182, 237, 321, 322, 323, 324, 325, 338, 339, 342, 442, 0x171)},
        "slot3_locals": [u16(locals3, i * 2) for i in range(4)],
        "locals_by_slot": locals_by_slot,
        "pc": u16(c), "opcode": c[6], "error": c[3], "program": c[0x62],
        "last_opcode": s.read_memory("snesMemory", 0x7E2306, 1)[0],
        "reset_diag": list(s.read_memory("snesMemory", 0x7E1020, 0x20)),
        "error_site": s.read_memory("snesMemory", 0x7E5F08, 1)[0],
        "error_setter": list(s.read_memory("snesMemory", 0x7E5F20, 32)),
        "c16_diag": list(s.read_memory("snesMemory", 0x7F6F10, 12)),
        "cutscene": list(s.read_memory("snesMemory", 0x7FD348, 0x38)),
        "c19_diag": list(s.read_memory("snesMemory", 0x7E5680, 32)),
        "stop_diag": list(s.read_memory("snesMemory", 0x7E5624, 5)),
        "compare_zero_diag": list(s.read_memory("snesMemory", 0x7E9000, 16)),
        "compare_zero_diag": list(s.read_memory("snesMemory", 0x7E56A0, 16)),
        "op_trace": list(s.read_memory("snesMemory", 0x7E5A00, 0x80)),
        "slots": [{"slot": i, "status": st[i], "number": no[i],
                   "program": pr[i], "pc": u16(pc, i * 2),
                   "didexec": didexec[i], "freeze": freeze[i]}
                  for i in range(25) if st[i] or no[i] or pr[i]],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--nexen", type=Path,
                    default=Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"))
    ap.add_argument("--port", type=int, default=44542)
    ap.add_argument("--frames", type=int, default=2400)
    ap.add_argument("--expected-room", type=int, default=42,
                    help="scenario room used by readiness/final validation")
    ap.add_argument("--load-state", type=Path,
                    help="resume a frame-safe emulator checkpoint instead of power-resetting")
    ap.add_argument("--save-state", type=Path,
                    help="write a frame-safe emulator checkpoint after this run")
    ap.add_argument("--light", action="store_true")
    ap.add_argument("--minimal-observation", action="store_true",
                    help="disable optional execution/write hooks for a long, frame-safe lifecycle run")
    ap.add_argument("--coherent-frame-trace", action="store_true",
                    help="record one service snapshot after every completed logical frame")
    ap.add_argument("--logical-frame-trace", action="store_true",
                    help="fence snapshots at bank-0 Same_Main_Loop re-entry")
    ap.add_argument("--logical-frame-exact", action="store_true",
                    help="use synchronous CPU stop at Same_Main_Loop for the frame fence")
    ap.add_argument("--trace-video-writers", action="store_true",
                    help="record backend state/lock writer routine boundaries")
    ap.add_argument("--sentence", type=int, nargs=3, metavar=("VERB", "OBJECT1", "OBJECT2"),
                    help="submit one sentence through the production mailbox after room 42 settles")
    ap.add_argument("--sentence2", type=int, nargs=3, metavar=("VERB", "OBJECT1", "OBJECT2"),
                    help="submit a second sentence after the first authored branch completes")
    ap.add_argument("--sentence2-after-object-state", type=int, nargs=2,
                    metavar=("OBJECT", "STATE"),
                    help="require this authored object state before publishing sentence 2")
    ap.add_argument("--sentence2-after-script-retired", type=int, action="append", default=[],
                    metavar="SCRIPT",
                    help="require each listed source script number to retire before publishing sentence 2")
    ap.add_argument("--capture-put-actor-sequence", action="store_true",
                    help="observe each production putActor/accessor result")
    ap.add_argument("--capture-final", action="store_true",
                    help="save the native emulator framebuffer at the final checkpoint")
    ap.add_argument("--reset-hook", action="store_true")
    ap.add_argument("--atomic-reset", action="store_true",
                    help="stop synchronously at the unique reset-prologue XCE")
    ap.add_argument("--exact-reset-stop", action="store_true",
                    help="use Nexen's synchronous exact CPU execution stop at reset entry")
    ap.add_argument("--exact-flight", action="store_true",
                    help="stop at the late pre-reset lookup and single-step to bootstrap")
    ap.add_argument("--exact-brk-stop", action="store_true",
                    help="synchronously stop at the first BRK handler entry after room 42 settles")
    ap.add_argument("--exact-exec-stop", type=lambda value: int(value, 0),
                    help="synchronously stop at an arbitrary 24-bit S-CPU address after sentence publication")
    ap.add_argument("--exact-exec-stop-room42", action="store_true",
                    help="allow --exact-exec-stop once room 42 ENCD is active (diagnostic only)")
    ap.add_argument("--exact-exec-steps", type=int, default=0,
                    help="single-step this many CPU boundaries after --exact-exec-stop")
    ap.add_argument("--pre-event-trace-start", type=int, default=780,
                    help="first frame whose preceding CPU trace is retained")
    ap.add_argument("--pre-event-trace-end", type=int,
                    help="last frame whose preceding CPU trace is retained")
    ap.add_argument("--pre-event-trace-count", type=int, default=1000,
                    help="number of synchronous CPU trace rows retained per selected frame")
    args = ap.parse_args()
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as ms
    ms.validate_mesen_build = lambda _: None
    args.output.mkdir(parents=True, exist_ok=True)
    trace = []
    trace_tail = None
    c25_error_hits = []
    compare_zero_hits = []
    reset_trace = None
    reset_vector_hits = []
    room_transition_hits = []
    lifecycle_write_hits = []
    run_results = []
    final_class_records = []
    reset_event_snapshot = None
    null_room_snapshot = None
    pre_event_traces = []
    coherent_frames = []
    logical_frames = []
    video_writer_hits = []
    video_state_write_hits = []
    engine_phase_write_hits = []
    service_path_hits = []
    fence_errors = []
    control_flow_hits = []
    exact_exec_handle = None
    pre_run_snapshot = None
    # The reset counter belongs to a dedicated diagnostic build, not the
    # generic scenario ABI.  Treating an arbitrary uninitialised WRAM region
    # as a counter made ordinary frame-safe validation abort at frame three.
    # Normal gameplay scenarios already prove health through completed-frame
    # room/error/lifecycle observations; enable this optional diagnostic only
    # for an explicit reset/control-flow probe.
    track_reset_counter = bool(
        args.reset_hook or args.atomic_reset or args.exact_reset_stop
        or args.exact_brk_stop or args.exact_exec_stop is not None
    )
    capture_instruction_history = bool(
        args.pre_event_trace_start < args.frames
        or args.exact_reset_stop or args.exact_brk_stop
        or args.exact_exec_stop is not None
    )
    with ms.McpSession(rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
                       port=args.port, boot_wait=2, socket_timeout=120,
                       stderr_log=args.output / "nexen-stderr.log") as session:
        session.pause()
        if args.load_state:
            session.load_state(args.load_state.resolve()); session.pause()
        else:
            session.tool("reset_emulator", {"power": True}); session.pause()
        # The persistent reset counter is authoritative.  A bank-local
        # execution hook at $8000 may also catch relocated LoROM code, so the
        # candidate probe is opt-in and never defines reset classification.
        reset_vector_handle = (session.add_exec_hook(0x008000)
                               if args.reset_hook else None)
        nmi_vector_handle = None
        irq_vector_handle = None
        # This is the unique XCE in the bank-0 reset prologue for the current
        # generated image.  Match the opcode and bank explicitly; unlike a
        # broad $8000 hook it cannot confuse relocated LoROM entries.
        atomic_reset_handle = None
        # Exact bank-0 M24RB transition hooks.  These are symbol-derived for
        # this generated image and are observational; unlike a broad $8000
        # hook they cannot confuse relocated LoROM entries with reset.
        observe_hooks = not args.atomic_reset and not args.minimal_observation
        logical_frame_handle = None
        # Install the logical-frame fence after the two power-reset frames
        # below.  Installing it before warm-up leaves a stale boot hit in the
        # asynchronous hook channel; run_until can then return immediately
        # and the validator would snapshot uninitialised gameplay state.
        null_room_handle = None if not observe_hooks else session.add_exec_hook(0x008C74)
        request_room_handle = None if not observe_hooks else session.add_exec_hook(0x008CEA)
        resource_ready_handle = None if not observe_hooks else session.add_exec_hook(0x008D97)
        commit_room_handle = None if not observe_hooks else session.add_exec_hook(0x008E80)
        storage_handle = None if not observe_hooks else session.add_exec_hook(0x008DC2)
        active_room_write_handle = (None if not observe_hooks else
                                    session.add_write_hook(0x7FF2BF))
        pending_room_write_handle = (None if not observe_hooks else
                                     session.add_write_hook(0x7FF2C1))
        active_record_write_handle = (None if not observe_hooks else
                                      session.add_write_hook(0x7FF2BE))
        # State-effect witnesses are narrow WRAM write hooks.  They are kept
        # independent of the optional reset/lifecycle hooks so the frame-safe
        # hoist run can capture authored effects without enabling broad trace
        # traffic.
        effect_handles = {
            session.add_write_hook(0x7E61F4): "object500_state",
            session.add_write_hook(0x7E61E8): "object488_state",
            session.add_write_hook(0x7E2BD7): "bit444_byte",
        }
        # Host-side write witnesses for the outer engine lifecycle and SCUMM
        # error byte.  These are observational and let a transient carry/error
        # be attributed to the exact frame before the engine stops servicing
        # the scheduler.
        engine_lifecycle_write_handle = (None if not observe_hooks else
                                         session.add_write_hook(0x7E2221))
        scumm_error_write_handle = (None if not observe_hooks else
                                    session.add_write_hook(0x7E2303))
        # The reset counter write is an exact WRAM event (unlike a bank-local
        # execution address), so retain it for the atomic flight recorder.
        reset_count_write_handle = (None if not observe_hooks else
                                    session.add_write_hook(0x7E1020))
        # Narrow late control-flow probes.  These are deliberately external
        # execution hooks with no memory reads, so they cannot perturb the
        # SCUMM VM and remain cheap enough for frame-granular stepping.
        control_flow_handles = {} if not observe_hooks else {
            session.add_exec_hook(0x008F6A): "program_size_wrapper",
            session.add_exec_hook(0x008F6E): "program_size_wrapper_return",
            session.add_exec_hook(0x128000): "program_size_far",
            session.add_exec_hook(0x1280B1): "program_size_far_return",
        }
        # Symbol-derived routine boundaries for the two accepted-PRESENT
        # stores and the normal completion stores in this ROM.  These are
        # diagnostic execution hooks only; coherent readiness snapshots are
        # still taken after run_frames returns.
        video_writer_handles = {}
        video_state_write_handles = {}
        if args.trace_video_writers:
            for address, label in (
                (0x0F83BA, "present_accept_before_lock_state"),
                (0x0F81E7, "step_complete_before_unlock_idle"),
                (0x0F81BF, "step_converting"),
                (0x0F81DF, "step_queueing"),
                (0x0F81E3, "step_waiting_dma"),
            ):
                video_writer_handles[session.add_exec_hook(address)] = label
            for address, label in (
                (0x401013, "backend_state_write"),
                (0x401014, "surface_lock_write"),
            ):
                video_state_write_handles[session.add_write_hook(address)] = label
            engine_phase_write_handle = session.add_write_hook(0x7E103C)
        else:
            engine_phase_write_handle = None
        # Optional service/control-flow trace. Hooks are observational; the
        # authoritative snapshot remains the synchronous Main_Loop fence.
        service_path_handles = {}
        if args.exact_exec_stop is not None:
            # The old validator used a Nexen-specific
            # run_to_exact_exec_stop tool that is not present in the
            # post-reboot MCP server. Keep the diagnostic semantics, but use
            # the supported synchronous execution hook/run_until pair.
            # A high-bank probe may need to cover a whole generated/corrupt
            # bank: the exact bad resume address is itself part of the
            # observation.  Keep the ordinary argument exact, but allow a
            # 24-bit bank base as a validator-only range request.
            if args.exact_exec_stop >= 0x10000 and (args.exact_exec_stop & 0xFFFF) == 0:
                exact_exec_handle = session.add_exec_hook(
                    args.exact_exec_stop, args.exact_exec_stop + 0xFFFF)
            else:
                exact_exec_handle = session.add_exec_hook(args.exact_exec_stop)
        if args.logical_frame_exact or args.logical_frame_trace:
            for symbol, label in (
                ("Same_Frame_Run", "frame_entry"),
                ("Same_Engine_Frame", "engine_entry"),
                ("ScummV5_Engine_Frame", "scumm_engine_entry"),
                ("ScummV5_Engine_Frame__return_success", "scumm_engine_return"),
                ("ScummV5_Engine_Frame__outer_return_success", "scumm_engine_outer_return"),
                ("Same_ActiveEngine_Frame", "active_engine_entry"),
                ("Same_ActiveEngine_Frame__error", "active_engine_error"),
                ("Same_ActiveEngine_Frame__production_error", "active_engine_production_error"),
                ("ScummV5_Engine_Frame__m23a_ready", "scumm_m23a_ready"),
                ("ScummV5_Engine_Frame__m23a_wait", "scumm_m23a_wait"),
                ("ScummV5_Engine_Frame__m23a_run_room_script", "scumm_run_room_script"),
                ("ScummV5_Engine_Frame__m23a_room_runnable", "scumm_room_runnable"),
                ("ScummV5_Engine_Frame__controller_driver_done", "scumm_controller_done"),
                ("ScummV5_Engine_Frame__m23a_continue", "scumm_m23a_continue"),
                ("ScummV5_Engine_RunSelected", "scumm_run_selected"),
                ("ScummV5_Engine_Frame__next", "scumm_next"),
                ("ScummV5_Engine_Frame__budget_error", "scumm_budget_error"),
                ("ScummV5_Engine_Frame__complete_success", "scumm_complete_success"),
                ("ScummV5_Engine_Frame__error", "scumm_error_path"),
                ("ScummV5_Engine_Frame__start_runnable", "scumm_start_runnable"),
                ("ScummV5_C4_Scheduler_Frame", "c4_scheduler_frame"),
                ("ScummV5_C4_RunNestedChild", "c4_run_nested_child"),
                ("ScummV5_C4_RunNestedChild__success", "c4_nested_success"),
                ("ScummV5_C4_RunAllocatedNoParent", "c4_allocated_no_parent"),
                ("ScummV5_C4_RetireStoppedSlot", "c4_retire_stopped"),
                ("ScummV5_C4_SaveCurrentSlot", "c4_save_current_slot"),
                ("Same_Kernel_DrainEvents", "drain_entry"),
                ("Same_Kernel_DrainEvents__done", "drain_done"),
                ("Same_Event_Pop", "event_pop"),
                ("Same_Video_Handle", "video_handle"),
                ("Same_Mode3_Handle_Far", "mode3_handle"),
                ("Same_Mode3_HandleDirty", "mode3_dirty"),
                ("Same_Mode3_HandleDirty__done", "dirty_done"),
                ("Same_Mode3_HandleDirty__reject", "dirty_reject"),
                ("Same_Mode3_HandlePalette", "mode3_palette"),
                ("Same_Mode3_HandlePresent", "mode3_present"),
                ("Same_VideoSurface_ComposeRoom_Far", "compose_entry"),
                ("Same_VideoSurface_PushDamagePresent_Far", "push_entry"),
                ("Same_Mode3_Step", "backend_step"),
                ("Same_Mode3_HandlePresent__accept", "present_accept_store"),
                ("Same_Mode3_Step__complete", "present_complete_store"),
                ("Same_Mode3_QueueBatch__finish", "queue_finish"),
                ("Same_Mode3_ObserveBatch__complete", "dma_complete"),
            ):
                try:
                    # The map's symbol value is bank-local.  Kernel/frame
                    # routines are in bank 0, while the generated Mode3 and
                    # surface service sections are placed in bank $0F in the
                    # accepted ROMs.  Installing a bank-0 hook for the latter
                    # observes unrelated bytes and can falsely identify a
                    # dirty-handler stall.
                    hook_bank = 0x0F if (
                        symbol.startswith("Same_Mode3_")
                        or symbol.startswith("Same_VideoSurface_")
                    ) else 0x00
                    service_path_handles[session.add_exec_hook(
                        (hook_bank << 16)
                        | mapped_cpu_address_for_rom(args.rom.resolve(), symbol))] = label
                except RuntimeError:
                    pass
            # Same_Frame_Run has no source label after its JSR to
            # Same_Engine_Frame. In these ROMs JSR $85A9 at $8EE0 returns to
            # $8EE3. This hook is observational; completed-frame phase data
            # remains authoritative.
            service_path_handles[session.add_exec_hook(0x008EE3)] = "engine_frame_return"
        # Current-ROM synchronous branch witnesses.  These are deliberately
        # host hooks, not ROM traps; they separate SentenceProcess/prepass
        # failure from the scheduler's own error path when the outer engine
        # marks itself failed.
        if observe_hooks:
            for address, label in (
                (0x009512, "engine_frame_error"),
                (0x00A387, "c4_scheduler_error"),
                (0x00959E, "sentence_process"),
                (0x0095A8, "m23a_driver"),
                (0x009EC7, "engine_frame_complete"),
            ):
                control_flow_handles[session.add_exec_hook(address)] = label
            # The far sentence/scheduler entry points may be linked into the
            # relocated bank in this profile.  Register both bank forms so a
            # missing notification cannot be mistaken for a missing call.
            for address, label in (
                (0x00959E, "sentence_process_bank0"),
                (0x09959E, "sentence_process_far"),
                (0x0093C6, "scheduler_ready_bank0"),
                (0x0993C6, "scheduler_ready_far"),
            ):
                control_flow_handles[session.add_exec_hook(address)] = label
        lifecycle_hooks = {}
        for bank in (() if not observe_hooks else range(20)):
            for local, label in ((0x8C74, "commit_null_room"),
                                 (0x8CEA, "request_room"),
                                 (0x8D97, "resource_ready"),
                                 (0x8E80, "commit_room"),
                                 (0x8DC2, "storage_handle"),
                                 (0x908F, "resource_ready_far"),
                                 (0x9093, "end_room_script_far"),
                                 (0x9097, "commit_room_far")):
                lifecycle_hooks[session.add_exec_hook((bank << 16) | local)] = (bank, label)
        # Trace logging is intentionally opt-in for a normal long scenario:
        # enabling Mesen's instruction ring while no requested frame can
        # consume it slows the frame-safe startup observation substantially.
        if capture_instruction_history:
            session.tool("trace_log", {"count": 1, "cpuType": "Snes"})
        # Map symbols are bank-local CPU addresses.  SetError is the stable
        # common publication point for every SCUMM error in this build.
        if not args.light:
            session.add_exec_hook(0x00F1A7)
            session.add_exec_hook(0x00F1D3)
        # Keep a narrow range around the generated C25 error label as a
        # diagnostic guard; this also catches a map-label/call-site mismatch.
        if not args.light:
            session.add_exec_hook(0x00D780, 0x00D795)
            session.add_exec_hook(0x09D780, 0x09D795)
            session.add_exec_hook(0x09F1A7)
        # Symbols are bank-local; install observational hooks in each
        # populated LoROM bank and retain the full PBR in notifications.
        compare_zero_hooks = {}
        for bank in (() if not observe_hooks else range(0, 20)):
            for local, label in ((0xDECE, "compare_entry"),
                                 (0xEBD5, "result_offset_after_fetch"),
                                 (0xEBA9, "apply_offset_entry"),
                                 (0xEBCC, "apply_offset_done")):
                compare_zero_hooks[session.add_exec_hook((bank << 16) | local)] = label
        # Error is sampled from the engine state below.  A write hook here
        # also fires for ordinary error clears, which can truncate a healthy
        # long startup trace before the authored branch is reached.
        # Hook every JSR whose encoded target is the current SetError address.
        # The caller address is more useful than a post-error VM snapshot, and
        # this remains valid when bank-0 diagnostics shift the routine.
        rom_bytes = args.rom.read_bytes()
        set_error_target = 0xF1D3
        call_pat = bytes((0x20, set_error_target & 0xFF,
                          (set_error_target >> 8) & 0xFF))
        if not args.light:
            for off in range(0, len(rom_bytes) - 2):
                if rom_bytes[off:off + 3] != call_pat:
                    continue
                bank = off // 0x8000
                cpu = 0x8000 + (off % 0x8000)
                session.add_exec_hook((bank << 16) | cpu)
        # Keep this validator observational.  These addresses are engine-owned
        # diagnostic/publication areas in some authored profiles; clearing them
        # here can alter startup inputs or scratch state before the first
        # semantic frame.  Reset-time initialization owns their lifetime.
        # Let the power-on reset finish before sampling the persistent reset
        # counter; reading immediately after the debugger reset can race the
        # vector and mistake its first write for a later runtime reset.
        session.run_frames(2)
        session.pause()
        previous = None
        reset_baseline = (
            int.from_bytes(session.read_memory("snesMemory", 0x7E5500, 2), "little")
            if track_reset_counter else None
        )
        # Discard hook notifications generated by the debugger's initial
        # power reset.  In particular, an atomic reset-prologue flight
        # recorder must not consume that boot hit when it is armed for the
        # late frontier.
        session.drain_notifications(timeout=0.0)
        if args.logical_frame_trace or args.logical_frame_exact:
            logical_frame_handle = session.add_exec_hook(
                # The label is the branch target immediately after the
                # completed JSR Same_Frame_Run.  It is the safe boundary before
                # SEP/WAI, without depending on debugger behavior around the
                # WAI opcode itself.
                mapped_cpu_address_for_rom(args.rom.resolve(), "Same_Main_Loop"))
            # Installing an execution hook can itself leave a notification for
            # the current debugger transaction.  It is not a completed-frame
            # observation; discard it before arming the run-until fence.
            session.drain_notifications(timeout=0.0)
        # The startup-root ENCD is deliberately allowed to run the real
        # script-1/title chain.  START is a title-room input boundary, not an
        # initial room-49 fixture action; sending it at the root can be
        # latched before room 75 is installed and changes the lifecycle.
        start_sent = False
        sentence_sent = False
        sentence2_sent = False
        sentence2_frame = None
        sentence2_pre_state = None
        sentence2_ready_frames = 0
        sentence_frame = None
        start_release_frame = None
        last_state = None
        readiness_debug = []
        mailbox_debug = []
        put_actor_sequence = []
        observed_put_actor_count = None
        sentence_pre_trace = None
        stable_room42_frames = 0
        stale_logical_fence_hits = 0
        elapsed = 0
        while elapsed < args.frames:
            # Refresh the observation for every frame.  The title START edge
            # is one-time, but sentence readiness is a later room-42
            # boundary and must never inspect the stale room-75 snapshot
            # from the input-arm frame.
            pre = snap_light(session) if args.light else snap(session)
            last_full_state = pre
            if not start_sent:
                # Arm the real controller edge at the source-backed 68 -> 75
                # title boundary.  The startup root intentionally begins in
                # room 68, before the title room is installed.
                # The target input latch is sampled during the NMI/frame
                # boundary.  Arm while room installation is in its final
                # phase so the edge is visible to the first idle title pass.
                if pre["room"] == 75 and pre["room_phase"] in (0, 2):
                    # Mesen's SNES controller mask is the native joypad word;
                    # START is bit $1000 (the low bits are face buttons).
                    # The MCP input API uses its abstract controller mask;
                    # session.BTN_START is the value mapped to native $1000
                    # by the emulator's joypad service.
                    session.set_input(session.BTN_START, 40)
                    start_sent = True
                    # Keep the edge held across several NMI/frame boundaries;
                    # the title gate samples the debounced controller state,
                    # not the debugger transaction itself.
                    start_release_frame = elapsed + 40
            if start_release_frame is not None and elapsed >= start_release_frame:
                session.set_input(0, 1)
                start_release_frame = None
            # Script 200 is an authored room-42 loop and normally remains
            # yielded/delayed (status 2), rather than retiring.  The stable
            # sentence boundary is therefore the room-idle/error-free actor
            # checkpoint with LSCR 201 and 208 installed, not status=4 on
            # program 223.  This keeps sentence injection at the semantic
            # mailbox boundary without depending on a transient slot state.
            # Readiness is based on completed frame observations, not the
            # pre-step snapshot: the latter can expose the next room's
            # published fields one transaction before its installation pass
            # commits.  This keeps the mailbox from racing room lifecycle.
            ready_observation = last_state or {}
            if room42_sentence_ready(ready_observation, args.expected_room):
                stable_room42_frames += 1
            else:
                stable_room42_frames = 0
            if (args.sentence and not sentence_sent
                    # Let the room's post-install frame-owner handoff settle
                    # fully; the first three completed observations are
                    # stable visually but can precede the next main-loop
                    # ownership boundary on Nexen.
                    and stable_room42_frames >= 6
                    and room42_sentence_ready(pre, args.expected_room)
                    # Room installation publishes the actor coordinates one
                    # pass before the canonical BOXM membership is committed.
                    # An idle actor outside a walkbox is not a valid sentence
                    # boundary: walkActorToObject would route from the
                    # transient box zero and silently take its no-route path.
                    and pre.get("actor1_walkbox", 0) != 0
                    # LSCR 201 and 208 are intentionally persistent delayed
                    # loops.  The semantic readiness boundary is the global
                    # cutscene stack being empty, not a transient status of
                    # program 223: on some valid scheduler passes LSCR 200
                    # is still represented by a yielded slot after its
                    # cutscene ownership has already been released.
                    and pre.get("cutscene", [1])[0] == 0
                    # The room-entry dialogue remains a real logical C23
                    # owner in headless mode.  Input may be visually idle
                    # before that owner releases, but a sentence submitted
                    # during the interval is only allocated and must wait at
                    # PC zero.  Use the canonical release boundary instead
                    # of relying on the old fixture-only auto-clear behavior.
                    and pre.get("talk_lifetime", {}).get("active", 1) == 0
                    # Program 211/222 are persistent authored startup/global
                    # identities in this scenario, not room-install guards.
                    # Their presence is compatible with the accepted stable
                    # room-42 input boundary; lifecycle stability is already
                    # established by the completed-frame run and room phase.
                    # Input is accepted after the room-entry cutscene's
                    # owning frame has been released.  LSCR 200/program 223
                    # is an authored delayed loop in some valid scheduler
                    # passes and can remain yielded after releasing that
                    # frame; requiring physical retirement here made the
                    # fixture wait forever and was not part of the semantic
                    # input boundary.  The cutscene/freeze and actor gates
                    # above are the authoritative readiness checks.  Three
                    # consecutive room-phase-zero observations prevent a
                    # transient room-install publication from being mistaken
                    # for an established gameplay checkpoint.
            ):
                verb, object1, object2 = args.sentence
                # Keep the publication operation identical to the established
                # validator path: pause at the observed semantic checkpoint,
                # write only the production mailbox, then resume via the
                # normal frame primitive.  Exact CPU breakpoints perturb the
                # SNES autojoy/NMI rendezvous in Nexen and are not used here.
                session.pause()
                # Preserve the synchronous emulator instruction history at
                # the semantic publication boundary.  This is host-only
                # observation: it proves whether the CPU is returning to the
                # main frame loop before attributing an unconsumed request to
                # the mailbox itself.
                if capture_instruction_history:
                    sentence_pre_trace = {
                        "frame": elapsed,
                        "cpu": session.get_cpu_state("Snes"),
                        "trace": session.tool(
                            "trace_log", {"count": 1000, "cpuType": "Snes"}
                        ),
                    }
                # Hand the mailbox to the production frame loop at its
                # synchronous entry boundary.  `run_frames` stops on the
                # frame counter, which can leave the CPU in NMI or halfway
                # through the previous frame; a debugger write there may
                # remain asserted without ever reaching Engine_Frame.
                # Stop in the CPU thread at the actual generated
                session.write_memory("snesMemory", 0x7FD3A6, bytes((verb & 0xFF, (verb >> 8) & 0xFF)).hex())
                session.write_memory("snesMemory", 0x7FD3A8, int(object1).to_bytes(2, "little").hex())
                session.write_memory("snesMemory", 0x7FD3AA, int(object2).to_bytes(2, "little").hex())
                session.write_memory("snesMemory", 0x7E7EC7, "01")
                # The mailbox write is performed while Nexen is paused at a
                # completed-frame boundary.  Explicitly wake the CPU before
                # the next frame request; otherwise the host video counter
                # can advance while the S-CPU remains in its WAI loop and
                # the production SCUMM consumer is never reached.
                mailbox_debug.append({
                    "frame": elapsed,
                    "pending_readback": session.read_memory("snesMemory", 0x7E7EC7, 1)[0],
                    "verb_readback": list(session.read_memory("snesMemory", 0x7FD3A6, 6)),
                })
                sentence_sent = True
                sentence_frame = elapsed
            elif (args.sentence and not sentence_sent and pre.get("room") == 42
                  and len(readiness_debug) < 8):
                readiness_debug.append({
                    "frame": elapsed,
                    "room_phase": pre.get("room_phase"),
                    "error": pre.get("error"),
                    "moving": pre.get("actor1_moving"),
                    "walkbox": pre.get("actor1_walkbox"),
                    "cutscene0": pre.get("cutscene", [None])[0],
                    "requested": list(args.sentence),
                })
            if (sentence_sent and sentence_frame is not None
                    and elapsed <= sentence_frame + 64):
                mailbox_debug.append({
                    "frame": elapsed,
                    "pending": session.read_memory("snesMemory", 0x7E7EC7, 1)[0],
                    "payload": list(session.read_memory("snesMemory", 0x7FD3A6, 6)),
                    "c20_count": session.read_memory("snesMemory", 0x7FD380, 1)[0],
                    "c20_records": list(session.read_memory("snesMemory", 0x7FD382, 36)),
                    "engine_stage": session.read_memory("snesMemory", 0x7E103C, 1)[0],
                    "engine_lifecycle": session.read_memory("snesMemory", 0x7E2221, 1)[0],
                    "engine_frame_busy": session.read_memory("snesMemory", 0x7E2231, 1)[0],
                    "scumm_error_set_count": int.from_bytes(session.read_memory("snesMemory", 0x7E5500, 2), "little"),
                    "scumm_error_code": session.read_memory("snesMemory", 0x7E5501, 1)[0],
                    "scumm_error_site": session.read_memory("snesMemory", 0x7E5F08, 1)[0],
                    "scheduler_c4_calls": session.read_memory("snesMemory", 0x7E5623, 1)[0],
                    "scheduler_calls": session.read_memory("snesMemory", 0x7E561D, 1)[0],
                    "m23a_phase": session.read_memory("snesMemory", 0x7FF2C2, 1)[0],
                    "m23a_hold": session.read_memory("snesMemory", 0x7FF2C4, 1)[0],
                    "frame_count": int.from_bytes(session.read_memory("snesMemory", 0x7E2308, 2), "little"),
                    "nmi_count": int.from_bytes(session.read_memory("snesMemory", 0x7E102E, 2), "little"),
                    "cpu": session.get_cpu_state("Snes"),
                    "frame_stage": session.read_memory("snesMemory", 0x7E567D, 1)[0],
                    "sentence_slot": session.read_memory("snesMemory", 0x7E5617, 1)[0],
                    "sched_ready": session.read_memory("snesMemory", 0x7E561E, 1)[0],
                    "sched_gate": session.read_memory("snesMemory", 0x7E5622, 1)[0],
                    "sched_phase": session.read_memory("snesMemory", 0x7E5621, 1)[0],
                    "handoff": {
                        "phase": session.read_memory("snesMemory", 0x7E5674, 1)[0],
                        "slot": session.read_memory("snesMemory", 0x7E5675, 1)[0],
                        "program": session.read_memory("snesMemory", 0x7E5676, 1)[0],
                        "pc": int.from_bytes(session.read_memory("snesMemory", 0x7E5677, 2), "little"),
                        "status": session.read_memory("snesMemory", 0x7E567B, 1)[0],
                    },
                    "active_count": session.read_memory("snesMemory", 0x7FF2A0, 1)[0],
                    "slots": pre.get("slots", []),
                    "room": pre.get("room"), "error": pre.get("error"),
                    "cutscene_depth": pre.get("cutscene", [None])[0],
                })
            # A chained sentence is submitted only after the first authored
            # action has exposed its source-backed object mutation.  This is
            # stronger than an elapsed-frame guess: global script 2 may spend
            # hundreds of frames in its prelude before dispatching the OBCD.
            required_state_ready = True
            if args.sentence2_after_object_state:
                object_id, state = args.sentence2_after_object_state
                required_state_ready = (
                    pre.get("room42_object_state", {}).get(str(object_id)) == state
                )
            live_script_numbers = {
                slot.get("number") for slot in pre.get("slots", [])
                if slot.get("status") not in (0, 4)
            }
            required_scripts_retired = not any(
                number in live_script_numbers
                for number in args.sentence2_after_script_retired
            )
            # Sentence 2 is another semantic player boundary.  Do not key it
            # to a generated program id or one fixture's class record: wait
            # for the first sentence script to retire and for its explicitly
            # requested authored state witness, if any, to be visible.
            first_action_ready = (
                args.sentence2 and sentence_sent and not sentence2_sent
                and pre.get("room") == 42 and pre.get("error") == 0
                and pre.get("actor1_moving") == 0
                and pre.get("cutscene", [1])[0] == 0
                and pre.get("sentence_pending") == 0
                and pre.get("c20_count") == 0
                and not any(
                    slot.get("number") == 2 and slot.get("status") not in (0, 4)
                    for slot in pre.get("slots", [])
                )
                and required_state_ready
                and required_scripts_retired
            )
            if first_action_ready:
                sentence2_ready_frames += 1
            else:
                sentence2_ready_frames = 0
            if first_action_ready and sentence2_ready_frames >= 3:
                verb, object1, object2 = args.sentence2
                # Keep the second semantic transaction at the same completed
                # frame boundary as the first.  A state mutation becomes
                # visible one observation before the sentence-launch slot is
                # fully handed back to C4; publishing during that transient
                # leaves a valid slot at PC zero until the next ownership pass.
                session.pause()
                sentence2_frame = elapsed
                sentence2_pre_state = pre
                session.write_memory("snesMemory", 0x7FD3A6, bytes((verb & 0xFF, (verb >> 8) & 0xFF)).hex())
                session.write_memory("snesMemory", 0x7FD3A8, int(object1).to_bytes(2, "little").hex())
                session.write_memory("snesMemory", 0x7FD3AA, int(object2).to_bytes(2, "little").hex())
                session.write_memory("snesMemory", 0x7E7EC7, "01")
                sentence2_sent = True
            # Long authored title waits are not a semantic reason to spend a
            # debugger round-trip on every frame.  Keep full-resolution
            # stepping for diagnostics, while the light trace advances in
            # small frame batches after the input boundary has been armed.
            # Once the authored room-42 lifecycle is installed, return to
            # frame-granular stepping.  Batched light-mode stepping can jump
            # across the dialogue/cutscene handoff and make a harness reset
            # look like a room transition, which obscures the next semantic
            # boundary we are validating.
            if args.capture_put_actor_sequence:
                # The fixture's observable records are produced by separate
                # yielded instructions.  Keep this diagnostic run at one
                # completed frame so host observation cannot collapse them.
                batch = 1
            elif args.coherent_frame_trace:
                # The trace is an A/B diagnostic, not a readiness gate.  Keep
                # every observation at one completed logical-frame boundary
                # so room/service transitions cannot be hidden by batching.
                batch = 1
            elif args.light and not sentence_sent:
                # No validator write is pending during the authored title or
                # room-42 dialogue.  Poll completed frames in bounded batches
                # until a stable semantic input boundary is observed; return
                # to frame-granular stepping before publishing a sentence.
                # Before the title START edge is seen, retain enough resolution
                # to notice room 75 without spending one MCP round-trip per
                # frame through the long room-68 prelude.
                batch = min(16 if not start_sent else (512 if pre["room"] != 42 else 64),
                            args.frames - elapsed)
            else:
                batch = 1
            if batch == 1:
                pre_run_snapshot = {
                    "frame": elapsed,
                    "cpu": session.get_cpu_state("Snes"),
                    "room": pre.get("room"),
                    "program": pre.get("program"),
                    "pc": pre.get("pc"),
                    "slots": pre.get("slots"),
                }
                if args.exact_brk_stop and elapsed >= 780:
                    session.tool("trace_log", {
                        "count": 1, "cpuType": "Snes", "clear": True,
                    })
                if (elapsed >= args.pre_event_trace_start
                        and (args.pre_event_trace_end is None
                             or elapsed <= args.pre_event_trace_end)):
                    pre_event_traces.append({
                        "frame": elapsed,
                        "cpu": session.get_cpu_state("Snes"),
                        "state": pre,
                        "trace": session.tool("trace_log", {
                            "count": args.pre_event_trace_count,
                            "cpuType": "Snes",
                        }),
                        "stack_1f00": list(session.read_memory("snesMemory", 0x1F00, 0x100)),
                    })
            # Keep the atomic probe frame-granular.  The MCP run_until
            # primitive can wait on a bank-local hook notification that was
            # already queued by another mapped LoROM address; one-frame
            # stepping avoids that debugger transaction ambiguity while the
            # unique opcode filter still identifies the reset prologue.
            if args.atomic_reset and elapsed % 50 == 0:
                print(f"flight frame {elapsed}", flush=True)
            elif args.light and elapsed % 128 == 0:
                print(f"startup42 frame {elapsed} room {pre['room']} phase {pre['room_phase']}", flush=True)
            # Do not let the final pre-reset window cross a debugger/frame
            # transaction boundary.  One frame per call makes the exact
            # reset-count write the stopping event, rather than a later
            # bootstrap snapshot.
            if args.atomic_reset and not args.exact_reset_stop and elapsed >= 840:
                batch = 1
            # Nexen returns paused at each completed observation boundary.
            # Explicitly resume before every requested step so a host video
            # frame cannot advance while the S-CPU remains parked in WAI.
            # Every observation primitive leaves Nexen paused.  This includes
            # the publication boundary and any synchronous execution stop.
            # Always resume before the next frame request; skipping the
            # publication iteration lets the video counter advance while the
            # S-CPU remains parked before Same_Frame_Run, so a freshly queued
            # sentence is never scheduled.  The unconditional resume is
            # idempotent for callers that are already running.
            session.resume()
            if args.logical_frame_exact:
                # run_until performs one atomic hook-driven pause.  Unlike a
                # batched run_frames call, it cannot return on an NMI while
                # the main loop is still inside Same_Frame_Run.
                try:
                    run_result = session.run_until(max_frames=600,
                                                   hook_handle=logical_frame_handle)
                except Exception as exc:
                    # A timed-out/closed debugger transaction is an
                    # observation result, not permission to discard the last
                    # paused CPU state.  Preserve it as the fence failure and
                    # classify from the state read below.
                    fence_errors.append({"frame": elapsed, "error": repr(exc)})
                    run_result = {"framesAdvanced": 0, "timedOut": True}
            elif args.exact_brk_stop and elapsed >= 780:
                run_result = session.tool("run_to_exact_exec_stop", {
                    "address": 0x008131, "cpuType": "Snes",
                    "maxFrames": 1, "occurrences": 1})
            elif (args.exact_exec_stop is not None
                  and ((sentence_sent and sentence_frame is not None
                        and elapsed >= sentence_frame)
                       or (args.exact_exec_stop_room42
                           and pre.get("room") == 42
                           and pre.get("room_phase") == 2))):
                run_result = session.run_until(max_frames=600,
                                               hook_handle=exact_exec_handle)
            elif args.exact_reset_stop and elapsed >= 866:
                # Nexen's exact execution stop is a CPU-thread breakpoint,
                # unlike MCP hook notifications which are delivered after
                # the CPU may have executed the bootstrap prologue.
                exact_target = 0x008F87 if args.exact_flight else 0x008000
                run_result = session.tool("run_to_exact_exec_stop", {
                    "address": exact_target, "cpuType": "Snes",
                    "maxFrames": 5, "occurrences": 1})
            elif args.atomic_reset and elapsed >= 867:
                # A bank-local run_until hook is delivered at a debugger
                # transaction boundary, before the frame's state is always
                # committed. Poll one safe frame instead; persistent reset,
                # room, and error state remain the authoritative evidence.
                run_result = session.run_frames(1)
            else:
                # A mailbox write made while paused at a completed-frame
                # boundary can otherwise be observed by the intervening NMI
                # transaction before the next main-engine pass. Give the
                # production frame loop two complete frame opportunities;
                # this changes observation timing only, not production state.
                if sentence_frame == elapsed:
                    # A paused write can land immediately after the NMI edge;
                    # a few video frames are not always a complete SCUMM
                    # main-loop pass when the consumer is parked in WAI. Give
                    # the production consumer a small bounded rendezvous
                    # window, while retaining exact frame observations before
                    # and after publication.
                    batch = 8
                run_result = session.run_frames(batch)
            if (args.logical_frame_exact and run_result.get("reason") in (
                    "hookFired", "hook")
                    and run_result.get("framesAdvanced", 0) > 0):
                # The synchronous CPU stop is the fence itself.  It is not a
                # debugger hook notification and therefore must be recorded
                # from the post-stop paused snapshot below.
                logical_frames.append({
                    "frame": elapsed + run_result.get("framesAdvanced", 0),
                    "address": mapped_cpu_address_for_rom(args.rom.resolve(), "Same_Main_Loop"),
                    "cpu": session.get_cpu_state("Snes"),
                    "state": snap_light(session) if args.light else snap(session),
                })
                if args.coherent_frame_trace:
                    coherent_frames.append(
                        coherent_service_snapshot(
                            session, logical_frames[-1]["state"]))
            run_results.append({"requested": batch, **run_result})
            elapsed += run_result.get("framesAdvanced", batch)
            if args.logical_frame_exact and run_result.get("framesAdvanced", 0) == 0:
                # A synchronous Main_Loop fence that times out is itself the
                # classification boundary: NMI may still be alive, but the
                # main frame did not return.  Do not spin on the same paused
                # transaction and manufacture more observations.
                if run_result.get("reason") in ("hookFired", "hook"):
                    # A stale asynchronous notification can report the hook
                    # without advancing the CPU.  It is not a frame and must
                    # not be snapshotted.  Tolerate a bounded number before
                    # treating the fence as unusable.
                    stale_logical_fence_hits += 1
                    if stale_logical_fence_hits <= 8:
                        continue
                stalled = snap_light(session) if args.light else snap(session)
                last_state = stalled
                if args.coherent_frame_trace:
                    coherent_frames.append(coherent_service_snapshot(session, stalled))
                break
            if (args.exact_reset_stop or args.exact_brk_stop
                    or args.exact_exec_stop is not None) and (
                        run_result.get("hit")
                        or run_result.get("reason") in ("hook", "hookFired")):
                reset_event_snapshot = {
                    "classification": ("synchronous_first_brk_entry" if args.exact_brk_stop
                                       else "synchronous_requested_exec_stop" if args.exact_exec_stop is not None
                                       else "synchronous_exact_exec_stop"),
                    "frame": run_result.get("triggerFrame"),
                    "address": run_result.get("address"),
                    "cpu": session.get_cpu_state("Snes"),
                    "trace": session.tool("trace_log", {"count": 1000, "cpuType": "Snes"}),
                    "diag": list(session.read_memory("snesMemory", 0x7E1020, 0x20)),
                    "stack_1f00": list(session.read_memory("snesMemory", 0x1F00, 0x100)),
                }
                if args.exact_flight:
                    flight = []
                    for step in range(512):
                        cpu = session.get_cpu_state("Snes")
                        flight.append({"step": step, **cpu})
                        address = ((cpu.get("k", 0) << 16) | cpu.get("pc", 0))
                        if address == 0x008000:
                            break
                        session.tool("run_to_next_cpu_boundary", {
                            "cpuType": "Snes", "maxFrames": 1})
                    reset_event_snapshot["exact_flight"] = flight
                if args.exact_exec_stop is not None and args.exact_exec_steps:
                    flight = []
                    for step in range(args.exact_exec_steps):
                        cpu = session.get_cpu_state("Snes")
                        flight.append({
                            "step": step, **cpu,
                            "route": {
                                "active_record": session.read_memory("snesMemory", 0x7FF2BE, 1)[0],
                                "source": session.read_memory("snesMemory", 0x7E7EAA, 1)[0],
                                "dest": int.from_bytes(session.read_memory("snesMemory", 0x7E7EAB, 2), "little"),
                                "next": session.read_memory("snesMemory", 0x7E7ECC, 1)[0],
                                "portal_type": session.read_memory("snesMemory", 0x7E7ECD, 1)[0],
                            },
                        })
                        session.tool("run_to_next_cpu_boundary", {
                            "cpuType": "Snes", "maxFrames": 1})
                    reset_event_snapshot["exact_exec_flight"] = flight
                break
            hits = session.drain_notifications(timeout=0.0)
            if hits:
                c25_error_hits.extend(hits)
                for hit in hits:
                    params = hit.get("params", {})
                    address = params.get("address")
                    handle = params.get("handle")
                    if handle in video_writer_handles:
                        backend = bytes(session.read_memory("snesMemory", 0x401000, 0x40))
                        video_writer_hits.append({
                            "label": video_writer_handles[handle],
                            "frame": params.get("frame"),
                            "address": address,
                            "cpu": session.get_cpu_state("Snes"),
                            "state": backend[0x13],
                            "locked": backend[0x14],
                            "accepted_present": int.from_bytes(backend[0x1A:0x1C], "little"),
                            "pending_generation": int.from_bytes(backend[0x0E:0x10], "little"),
                            "committed_generation": int.from_bytes(backend[0x10:0x12], "little"),
                        })
                    if handle in service_path_handles:
                        backend = bytes(session.read_memory("snesMemory", 0x401000, 0x40))
                        service_path_hits.append({
                            "label": service_path_handles[handle],
                            "frame": params.get("frame"),
                            "address": address,
                            "cpu": session.get_cpu_state("Snes"),
                            "state": backend[0x13],
                            "locked": backend[0x14],
                            "accepted_present": int.from_bytes(backend[0x1A:0x1C], "little"),
                            "pending_generation": int.from_bytes(backend[0x0E:0x10], "little"),
                            "committed_generation": int.from_bytes(backend[0x10:0x12], "little"),
                            "scumm": {
                                "program": session.read_memory("snesMemory", 0x7E2300 + 0x62, 1)[0],
                                "pc": u16(session.read_memory("snesMemory", 0x7E2300, 2)),
                                "slot": session.read_memory("snesMemory", 0x7FF2BE, 1)[0],
                                "room": session.read_memory("snesMemory", 0x7FF2BF, 1)[0],
                                "m23a_phase": session.read_memory("snesMemory", 0x7FF2C2, 1)[0],
                                "nested": session.read_memory("snesMemory", 0x7FD335, 1)[0],
                                "slot_status": list(session.read_memory("snesMemory", 0x7E2380, 8)),
                                "slot_number": list(session.read_memory("snesMemory", 0x7E2399, 8)),
                                "slot_program": list(session.read_memory("snesMemory", 0x7E23B2, 8)),
                                "slot_pc": list(session.read_memory("snesMemory", 0x7E23E4, 16)),
                            },
                        })
                    if handle in video_state_write_handles:
                        backend = bytes(session.read_memory("snesMemory", 0x401000, 0x40))
                        video_state_write_hits.append({
                            "label": video_state_write_handles[handle],
                            "frame": params.get("frame"),
                            "address": address,
                            "value": params.get("value"),
                            "cpu": session.get_cpu_state("Snes"),
                            "state": backend[0x13],
                            "locked": backend[0x14],
                            "accepted_present": int.from_bytes(backend[0x1A:0x1C], "little"),
                            "pending_generation": int.from_bytes(backend[0x0E:0x10], "little"),
                            "committed_generation": int.from_bytes(backend[0x10:0x12], "little"),
                        })
                    if handle == engine_phase_write_handle:
                        engine_phase_write_hits.append({
                            "frame": params.get("frame"),
                            "address": address,
                            "value": params.get("value"),
                            "cpu": session.get_cpu_state("Snes"),
                            "room": session.read_memory("snesMemory", 0x7FF2BF, 1)[0],
                            "backend": list(session.read_memory("snesMemory", 0x401000, 0x20)),
                        })
                    if handle in (reset_vector_handle,
                                  nmi_vector_handle, atomic_reset_handle,
                                  irq_vector_handle, null_room_handle,
                                  request_room_handle, resource_ready_handle,
                                  commit_room_handle, storage_handle):
                        if handle == reset_vector_handle:
                            # On SNES, a bank-local execution hook can also
                            # observe a relocated routine at $8000.  Treat it
                            # as a reset candidate only when the persistent
                            # reset counter has advanced; otherwise it is an
                            # ordinary far-bank entry (not a reset event).
                            candidate_count = int.from_bytes(
                                session.read_memory("snesMemory", 0x7E1020, 2),
                                "little")
                            if candidate_count != reset_baseline:
                                # Stop at the notification boundary.  Let the
                                # reset handler's counter prove the event,
                                # while preserving the pre-bootstrap trace.
                                session.pause()
                                reset_event_snapshot = {
                                    "frame": params.get("frame"),
                                    "address": address,
                                    "candidate_count": candidate_count,
                                    "cpu": session.get_cpu_state("Snes"),
                                    "trace": session.tool("trace_log", {"count": 256, "cpuType": "Snes"}),
                                }
                        reset_vector_hits.append({
                            "kind": ("reset" if handle == reset_vector_handle else
                                     "nmi" if handle == nmi_vector_handle else
                                     "atomic_reset_prologue" if handle == atomic_reset_handle else "irq"),
                            "frame": params.get("frame"),
                            "address": address,
                            "cpu": session.get_cpu_state("Snes"),
                            "stack_1f00": list(session.read_memory("snesMemory", 0x1F00, 0x100)),
                            "diag": list(session.read_memory("snesMemory", 0x7E1020, 0x20)),
                            "entry_stack_window": list(session.read_memory("snesMemory", 0x7E5520, 0x20)),
                            "scumm": list(session.read_memory("snesMemory", 0x7E5F00, 0x30)),
                            })
                    if handle == atomic_reset_handle:
                        session.pause()
                        reset_event_snapshot = {
                            "classification": "synchronous_reset_prologue_hit",
                            "frame": params.get("frame"),
                            "address": address,
                            "cpu": session.get_cpu_state("Snes"),
                            "trace": session.tool("trace_log", {"count": 1000, "cpuType": "Snes"}),
                            "diag": list(session.read_memory("snesMemory", 0x7E1020, 0x20)),
                            "stack_1f00": list(session.read_memory("snesMemory", 0x1F00, 0x100)),
                        }
                    if handle in lifecycle_hooks:
                        bank, label = lifecycle_hooks[handle]
                        room_transition_hits.append({
                            "kind": label,
                            "bank": bank,
                            "frame": params.get("frame"),
                            "address": address,
                            "cpu": session.get_cpu_state("Snes"),
                            "room": snap_light(session) if args.light else snap(session),
                        })
                    if handle in (active_room_write_handle, pending_room_write_handle,
                                  active_record_write_handle):
                        room_transition_hits.append({
                            "kind": ("active_room_write" if handle == active_room_write_handle
                                      else "pending_room_write" if handle == pending_room_write_handle
                                      else "active_record_write"),
                            "frame": params.get("frame"),
                            "address": address,
                            "value": params.get("value"),
                            "cpu": session.get_cpu_state("Snes"),
                            "room": snap_light(session) if args.light else snap(session),
                                "trace": session.tool("trace_log", {"count": 32, "cpuType": "Snes"}),
                        })
                    if handle in effect_handles:
                        room_transition_hits.append({
                            "kind": effect_handles[handle],
                            "frame": params.get("frame"),
                            "address": address,
                            "value": params.get("value"),
                            "cpu": session.get_cpu_state("Snes"),
                            "room": snap_light(session) if args.light else snap(session),
                        })
                        if handle in (null_room_handle, request_room_handle,
                                      resource_ready_handle, commit_room_handle,
                                      storage_handle):
                            room_transition_hits.append({
                                "kind": ("commit_null_room" if handle == null_room_handle
                                          else "request_room" if handle == request_room_handle
                                          else "resource_ready" if handle == resource_ready_handle
                                          else "commit_room" if handle == commit_room_handle
                                          else "storage_handle"),
                                "frame": params.get("frame"),
                                "address": address,
                                "cpu": session.get_cpu_state("Snes"),
                                "room": snap_light(session) if args.light else snap(session),
                                "trace": session.tool("trace_log", {"count": 64, "cpuType": "Snes"}),
                            })
                    if handle in (engine_lifecycle_write_handle,
                                  scumm_error_write_handle):
                        lifecycle_trace = None
                        if (handle == engine_lifecycle_write_handle
                                and params.get("value") == 0xFF):
                            # Capture synchronously in the notification path,
                            # before the main loop can advance and overwrite
                            # the useful tail.  This is host-side only.
                            lifecycle_trace = session.tool(
                                "trace_log", {"count": 1000, "cpuType": "Snes"}
                            )
                        lifecycle_write_hits.append({
                            "kind": ("engine_lifecycle" if handle == engine_lifecycle_write_handle
                                      else "scumm_error"),
                            "frame": params.get("frame"),
                            "address": address,
                            "value": params.get("value"),
                            "cpu": session.get_cpu_state("Snes"),
                            "scumm": list(session.read_memory("snesMemory", 0x7E5F00, 0x30)),
                            "room": snap_light(session) if args.light else snap(session),
                            "trace": lifecycle_trace,
                        })
                    if handle == reset_count_write_handle:
                        reset_vector_hits.append({
                            "kind": "reset_diag_count_write",
                            "frame": params.get("frame"),
                            "address": address,
                            "value": params.get("value"),
                            "cpu": session.get_cpu_state("Snes"),
                            "stack_1f00": list(session.read_memory("snesMemory", 0x1F00, 0x100)),
                            "diag": list(session.read_memory("snesMemory", 0x7E1020, 0x20)),
                            "entry_stack_window": list(session.read_memory("snesMemory", 0x7E5520, 0x20)),
                            "trace": session.tool("trace_log", {"count": 1000, "cpuType": "Snes"}),
                        })
                    if handle in control_flow_handles and params.get("frame", 0) >= 840:
                        hit = {
                            "label": control_flow_handles[handle],
                            "frame": params.get("frame"),
                            "address": address,
                            "cpu": session.get_cpu_state("Snes"),
                        }
                        if control_flow_handles[handle] == "engine_frame_error":
                            hit["trace"] = session.tool(
                                "trace_log", {"count": 1000, "cpuType": "Snes"}
                            )
                        control_flow_hits.append(hit)
                    if handle == logical_frame_handle and not args.logical_frame_exact:
                        # Same_Main_Loop is reached only after Same_Frame_Run
                        # has returned and the CPU is about to enter WAI.
                        # This is the logical-frame fence; unlike NMI and
                        # service hooks it cannot observe an interior handler.
                        logical_frames.append({
                            "frame": params.get("frame"),
                            "address": address,
                            "cpu": session.get_cpu_state("Snes"),
                            "state": snap_light(session) if args.light else snap(session),
                        })
                        if args.coherent_frame_trace:
                            coherent_frames.append(
                                coherent_service_snapshot(
                                    session, logical_frames[-1]["state"]))
                    if handle in compare_zero_hooks:
                        vm = session.read_memory("snesMemory", COMMON, 0x64)
                        compare_zero_hits.append({
                            "label": compare_zero_hooks[handle],
                            "handle": handle,
                            "frame": params.get("frame"),
                            "address": address,
                            "pc": u16(vm), "opcode": vm[6],
                            "program": vm[0],
                            "result_offset": u16(session.read_memory("snesMemory", 0x7E2340, 2)),
                            "operand": u16(session.read_memory("snesMemory", 0x7E2342, 2)),
                            "condition": session.read_memory("snesMemory", 0x7E2347, 1)[0],
                        })
            state = snap_light(session) if args.light else snap(session)
            last_state = state
            if args.capture_put_actor_sequence:
                count = state.get("put_actor_last", {}).get("count", 0)
                if observed_put_actor_count is None:
                    observed_put_actor_count = count
                elif count != observed_put_actor_count:
                    work = list(session.read_memory("snesMemory", 0x7FFB65, 0x12))
                    put_actor_sequence.append({
                        "count": count,
                        "actor": state["put_actor_last"]["actor"],
                        "request": state["put_actor_last"]["request"],
                        "result": state["put_actor_last"]["result"],
                        "result_box": state["put_actor_last"]["result_box"],
                        "geometry_work": work,
                    })
                    observed_put_actor_count = count
            if (null_room_snapshot is None and state.get("room") == 0 and
                    trace and trace[-1].get("room") == 42):
                # Capture the first observer-visible null-room state without
                # changing engine state.  This distinguishes a real room
                # commit/CPU control-flow event from the later final snapshot.
                session.pause()
                null_room_snapshot = {
                    "frame": state.get("frame"),
                    "cpu": session.get_cpu_state("Snes"),
                    "state": state,
                    "trace": session.tool("trace_log", {"count": 256, "cpuType": "Snes"}),
                    "emulator": session.get_state(),
                }
            reset_count = (int.from_bytes(bytes(state.get("reset_diag", [0, 0])[:2]), "little")
                           if track_reset_counter else None)
            if (track_reset_counter and not args.atomic_reset and not args.exact_reset_stop and
                    reset_count and reset_count != reset_baseline):
                reset_trace = session.tool("trace_log", {"count": 256, "cpuType": "Snes"})
                break
            if args.atomic_reset and reset_event_snapshot is not None:
                # Kept for exact-stop mode; the ordinary atomic profile no
                # longer creates a reset-prologue hook and therefore reaches
                # this only when an independent synchronous stop supplied a
                # snapshot.
                break
            if track_reset_counter:
                reset_baseline = reset_count
            key = (state["room"], state["room_phase"],
                   state["scheduler"].get("m23a_phase"),
                   state["scheduler"].get("c4_calls"), state["pc"],
                   state["program"], state["error"], tuple(
                       (x["number"], x["pc"], x["status"]) for x in state["slots"]),
                   tuple(state.get("actor1_position", ())), state.get("actor1_moving"),
                   state.get("movement", {}).get("current_box"),
                   state.get("movement", {}).get("route_source"),
                   state.get("movement", {}).get("route_dest"))
            if key != previous:
                trace.append(state); previous = key
            # Room 42 phase 0 is the intended post-entry gameplay state, not
            # a terminal checkpoint.  Keep observing its authored locals and
            # input boundary instead of truncating the scenario there.
            if state["error"]:
                break
        if sentence_sent:
            # The sentence handoff is the only point at which a newly
            # allocated slot can be confused with a CPU/frame rendezvous.
            # Retain the synchronous tail for the post-publication control
            # path even when SCUMM reports no error.
            trace_tail = session.tool("trace_log", {"count": 1000, "cpuType": "Snes"})
        if trace and trace[-1]["error"]:
            trace_tail = session.tool("trace_log", {"count": 1000, "cpuType": "Snes"})
            # A single full snapshot at an actual error is observational and
            # retains the engine-owned setter/operand diagnostics omitted by
            # light-mode polling.
            last_full_state = snap(session)
        # C16 class state is sparse and is intentionally sampled only once at
        # the end; reading the complete table on every light frame would turn
        # this observational validator into a timing perturbation.
        class_raw = session.read_memory("snesMemory", 0x7F5F10, 0x1000)
        for offset in range(0, len(class_raw), 8):
            if class_raw[offset]:
                final_class_records.append({
                    "object": int.from_bytes(class_raw[offset + 2:offset + 4], "little"),
                    "mask": int.from_bytes(class_raw[offset + 4:offset + 8], "little"),
                })
        # `run_frames` intentionally leaves Nexen paused at each observation
        # boundary. Retain the synchronous CPU state while the session is
        # still open so a quiescent VM can be distinguished from an emulator
        # that is merely advancing its video-frame counter while CPU
        # execution has ceased. This is host-side observation only.
        final_cpu = session.get_cpu_state("Snes")
        if sentence_sent:
            # One detailed terminal snapshot is observational and lets the
            # compressor handoff distinguish "allocated but never fetched"
            # from a script which ran and corrupted its saved context.
            last_full_state = snap(session)
        if args.save_state:
            session.save_state(args.save_state.resolve())
        if args.capture_final:
            (args.output / "final-native.png").write_bytes(
                base64.b64decode(session.take_screenshot(format="base64")["base64"])
            )
    # The change-filtered trace intentionally omits steady-state frames; take
    # one actual end snapshot so long waits and debugger pauses are not
    # mistaken for an early termination.
    final = last_state if 'last_state' in locals() and last_state else (trace[-1] if trace else {})
    report = {"scenario": "controlled-script-1-startup-root", "trace": trace,
              "final": final, "trace_tail": trace_tail,
              # Preserve existing engine-owned diagnostics in the report even
              # though the compact final snapshot omits high-volume fields.
              "final_diagnostics": {
                  key: last_full_state.get(key) for key in (
                      "error_setter", "error_context", "setclass",
                      "c16_diag", "c16_state", "error_site", "c25_error",
                      "c25_error_detail", "c4_return",
                      "c25_observation",
                      "c25_producer",
                      "c25_error_record",
                      "m23c_trace_count", "m23c_trace_overflow", "m23c_trace",
                      "c25_dispatch",
                      "save_context",
                      "c25_error_meta",
                      "c25_queue_raw",
                      "c23_text", "talk", "scheduler", "op_trace",
                      "engine_lifecycle", "engine_frame_busy",
                      "c4_error_origin",
                  )
              } if 'last_full_state' in locals() and last_full_state else {},
              "c25_error_hits": c25_error_hits,
              "reset_trace": reset_trace,
              "reset_vector_hits": reset_vector_hits,
              "room_transition_hits": room_transition_hits,
              "lifecycle_write_hits": lifecycle_write_hits,
              "run_results": run_results,
              "final_class_records": final_class_records,
              "reset_event_snapshot": reset_event_snapshot,
              "null_room_snapshot": null_room_snapshot,
              "pre_event_traces": pre_event_traces,
              "coherent_frames": coherent_frames,
              "logical_frames": logical_frames,
              "video_writer_hits": video_writer_hits,
              "video_state_write_hits": video_state_write_hits,
              "engine_phase_write_hits": engine_phase_write_hits,
              "service_path_hits": service_path_hits,
              "fence_errors": fence_errors,
              "pre_run_snapshot": pre_run_snapshot,
              "compare_zero_hooks": compare_zero_hits,
              "control_flow_hits": control_flow_hits,
              "sentence_sent": sentence_sent,
              "sentence_frame": sentence_frame,
              "sentence2_sent": sentence2_sent,
              "sentence2_frame": sentence2_frame,
              "sentence2_pre_state": sentence2_pre_state,
              "readiness_debug": readiness_debug,
              "mailbox_debug": mailbox_debug,
              "put_actor_sequence": put_actor_sequence,
              "sentence_pre_trace": sentence_pre_trace,
              "final_cpu": final_cpu,
              "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
              "build_identity": build_identity_for(args.rom)}
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(final, sort_keys=True))
    if final.get("room") != args.expected_room or final.get("error"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
