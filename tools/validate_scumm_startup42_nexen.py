#!/usr/bin/env python3
"""Focused controlled startup-root validation for Fate room 42."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
COMMON = 0x7E2300
ROOM = 0x7FF2BE
SLOTS_STATUS = 0x7E2380
SLOTS_NUMBER = 0x7E2399
SLOTS_PROGRAM = 0x7E23B2
SLOTS_PC = 0x7E23E4


def u16(b: bytes, n: int = 0) -> int:
    return int.from_bytes(b[n:n + 2], "little")


def room42_sentence_ready(state: dict) -> bool:
    """Require the completed room-entry handoff, not just room publication.

    M24RB publishes the new room before its resource/ENCD pass has completed.
    The accepted room-42 input boundary is the subsequent stable frame where
    the persistent room scripts are installed and the semantic mailbox is
    idle.  This remains observational and does not require a particular slot
    number or force any VM state.
    """
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


def class_mask(s, object_id: int) -> int | None:
    """Read the sparse C16 record for an object at a sentence boundary."""
    raw = s.read_memory("snesMemory", 0x7F5F10, 0x1000)
    for offset in range(0, len(raw), 8):
        if raw[offset] and int.from_bytes(raw[offset + 2:offset + 4], "little") == object_id:
            return int.from_bytes(raw[offset + 4:offset + 8], "little")
    return None


def snap(s):
    c = s.read_memory("snesMemory", COMMON, 0x64)
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
        "diag_stage": s.read_memory("snesMemory", 0x7E1024, 1)[0],
        "reset_diag": list(s.read_memory("snesMemory", 0x7E1020, 0x20)),
        "m25a_trace": list(s.read_memory("snesMemory", 0x7E5000, 0x80)),
        "start_trace": list(s.read_memory("snesMemory", 0x7E7ED7, 0x41)),
        "alloc_trace": list(s.read_memory("snesMemory", 0x7E5900, 0x81)),
        "op_trace": list(s.read_memory("snesMemory", 0x7E5A00, 0x402)),
        "m24rb_alloc": list(s.read_memory("snesMemory", 0x7E5980, 4)),
        "error_site": s.read_memory("snesMemory", 0x7E5F08, 1)[0],
        "error_setter": list(s.read_memory("snesMemory", 0x7E5F20, 24)),
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
        "c25_error_last_op": list(s.read_memory("snesMemory", 0x7E5F04, 15)),
        "start_diag": list(s.read_memory("snesMemory", 0x7E5636, 10)) + list(s.read_memory("snesMemory", 0x7E5650, 4)),
        "scenario": list(s.read_memory("snesMemory", 0x7E5600, 4)),
        "active_count": s.read_memory("snesMemory", 0x7E2A87, 1)[0],
        "slot_raw": {"status": list(st), "number": list(no), "program": list(pr)},
        "slot_freeze": list(freeze), "slot_didexec": list(didexec),
        "slot_where": list(where),
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
    actor_identity = s.read_memory("snesMemory", 0x7F3700, 0x17)
    c20 = s.read_memory("snesMemory", 0x7FD380, 1)[0]
    cutscene = s.read_memory("snesMemory", 0x7FD348, 1)[0]
    object_states = s.read_memory("snesMemory", 0x7E6000 + 489, 12)
    object_owners = s.read_memory("snesMemory", 0x7E8000 + 489, 12)

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
        "room": room[1], "room_phase": room[4],
        "pc": u16(common), "opcode": common[6], "error": common[3],
        "program": common[0x62],
        "actor1_position": [u16(actor_pos), u16(actor_pos, 2)],
        "actor1_moving": actor_moving,
        "actor1_walkbox": actor_walkbox,
        "actor1_costume": actor_identity[0], "actor1_room": actor_identity[0x16],
        "actor2_position": [u16(actor2_pos), u16(actor2_pos, 2)],
        "actor2_moving": actor2_moving,
        "actor2_walkbox": actor2_walkbox,
        "put_actor_last": {
            "actor": put_actor_last[0],
            "request": [u16(put_actor_last, 1), u16(put_actor_last, 3)],
            "result": [u16(put_actor_last, 5), u16(put_actor_last, 7)],
            "result_box": put_actor_last[9],
            "count": s.read_memory("snesMemory", 0x7FFEE6, 1)[0],
        },
        # C14 actor records are indexed by actor number; actor 1 starts at
        # 0x7F3700, so actor 2 is the next 0x40-byte record.
        "actor2_costume": s.read_memory("snesMemory", 0x7F3700 + 0x40, 1)[0],
        "actor2_room": s.read_memory("snesMemory", 0x7F3700 + 0x40 + 0x16, 1)[0],
        "cutscene": [cutscene], "c20_count": c20,
        "sentence_pending": s.read_memory("snesMemory", 0x7E7EC7, 1)[0],
        "room42_object_state": {str(i): object_states[i - 489] for i in range(489, 501)},
        "object488_state": s.read_memory("snesMemory", 0x7E6000 + 488, 1)[0],
        "room42_object_owner": {str(i): object_owners[i - 489] for i in range(489, 501)},
        "slots": slots,
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
        "engine_stage": s.read_memory("snesMemory", 0x7E1024, 1)[0],
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
        "error_setter": list(s.read_memory("snesMemory", 0x7E5F20, 24)),
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
    ap.add_argument("--load-state", type=Path,
                    help="resume a frame-safe emulator checkpoint instead of power-resetting")
    ap.add_argument("--save-state", type=Path,
                    help="write a frame-safe emulator checkpoint after this run")
    ap.add_argument("--light", action="store_true")
    ap.add_argument("--minimal-observation", action="store_true",
                    help="disable optional execution/write hooks for a long, frame-safe lifecycle run")
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
    run_results = []
    final_class_records = []
    reset_event_snapshot = None
    null_room_snapshot = None
    pre_event_traces = []
    control_flow_hits = []
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
        # The startup-root ENCD is deliberately allowed to run the real
        # script-1/title chain.  START is a title-room input boundary, not an
        # initial room-49 fixture action; sending it at the root can be
        # latched before room 75 is installed and changes the lifecycle.
        start_sent = False
        sentence_sent = False
        sentence2_sent = False
        sentence_frame = None
        start_release_frame = None
        last_state = None
        readiness_debug = []
        mailbox_debug = []
        sentence_pre_trace = None
        stable_room42_frames = 0
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
            if room42_sentence_ready(ready_observation):
                stable_room42_frames += 1
            else:
                stable_room42_frames = 0
            if (args.sentence and not sentence_sent
                    # Let the room's post-install frame-owner handoff settle
                    # fully; the first three completed observations are
                    # stable visually but can precede the next main-loop
                    # ownership boundary on Nexen.
                    and stable_room42_frames >= 6
                    and room42_sentence_ready(pre)
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
                    "engine_stage": session.read_memory("snesMemory", 0x7E1024, 1)[0],
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
                verb, object1, object2 = args.sentence2
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
            if args.light and start_sent and not sentence_sent:
                # No validator write is pending during the authored title or
                # room-42 dialogue.  Poll completed frames in bounded batches
                # until a stable semantic input boundary is observed; return
                # to frame-granular stepping before publishing a sentence.
                batch = min(128 if pre["room"] != 42 else 16,
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
            if args.exact_brk_stop and elapsed >= 780:
                run_result = session.tool("run_to_exact_exec_stop", {
                    "address": 0x008131, "cpuType": "Snes",
                    "maxFrames": 1, "occurrences": 1})
            elif (args.exact_exec_stop is not None and sentence_sent
                  and sentence_frame is not None and elapsed >= sentence_frame):
                run_result = session.tool("run_to_exact_exec_stop", {
                    "address": args.exact_exec_stop, "cpuType": "Snes",
                    "maxFrames": 1, "occurrences": 1})
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
                    batch = 2
                run_result = session.run_frames(batch)
            run_results.append({"requested": batch, **run_result})
            elapsed += run_result.get("framesAdvanced", batch)
            if (args.exact_reset_stop or args.exact_brk_stop
                    or args.exact_exec_stop is not None) and run_result.get("hit"):
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
                        control_flow_hits.append({
                            "label": control_flow_handles[handle],
                            "frame": params.get("frame"),
                            "address": address,
                        })
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
            key = (state["room"], state["room_phase"], state["pc"],
                   state["program"], state["error"], tuple(
                       (x["number"], x["pc"], x["status"]) for x in state["slots"]))
            if key != previous:
                trace.append(state); previous = key
            # Room 42 phase 0 is the intended post-entry gameplay state, not
            # a terminal checkpoint.  Keep observing its authored locals and
            # input boundary instead of truncating the scenario there.
            if state["error"]:
                break
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
        if args.save_state:
            session.save_state(args.save_state.resolve())
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
                  )
              } if 'last_full_state' in locals() and last_full_state else {},
              "c25_error_hits": c25_error_hits,
              "reset_trace": reset_trace,
              "reset_vector_hits": reset_vector_hits,
              "room_transition_hits": room_transition_hits,
              "run_results": run_results,
              "final_class_records": final_class_records,
              "reset_event_snapshot": reset_event_snapshot,
              "null_room_snapshot": null_room_snapshot,
              "pre_event_traces": pre_event_traces,
              "pre_run_snapshot": pre_run_snapshot,
              "compare_zero_hooks": compare_zero_hits,
              "control_flow_hits": control_flow_hits,
              "sentence_sent": sentence_sent,
              "sentence_frame": sentence_frame,
              "sentence2_sent": sentence2_sent,
              "readiness_debug": readiness_debug,
              "mailbox_debug": mailbox_debug,
              "sentence_pre_trace": sentence_pre_trace,
              "final_cpu": final_cpu,
              "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest()}
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(final, sort_keys=True))
    if final.get("room") != 42 or final.get("error"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
