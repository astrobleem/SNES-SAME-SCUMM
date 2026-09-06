#!/usr/bin/env python3
"""Controller-only replay for the visible Fate room-42 locker fixture.

Manual controls in an attached SNES controller/emulator are intentionally
ordinary input: D-pad moves the on-screen cursor; A selects the highlighted
object or action; Y changes the verb (Open before the locker is opened, Inspect
afterward).  No mailbox or game-state writes are part of the manual route.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from same.engines.scumm_v5.room_visual import decode_room_visual  # noqa: E402

STARTUP = ROOT / "tools" / "validate_scumm_startup42_nexen.py"
_startup_ns = {"__name__": "startup42_helpers", "__file__": str(STARTUP)}
exec(compile(STARTUP.read_text(), str(STARTUP), "exec"), _startup_ns)
DEFAULT_NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
snap = _startup_ns["snap"]
room42_sentence_ready = _startup_ns["room42_sentence_ready"]
def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)

ACTOR_POSITIONS = 0x7FF1A0
ACTOR_WALKBOX = 0x7FFDA5
OBJECT_STATES = 0x7E6000
CONTROLLER = 0x7E5FE0
VISUAL = 0x401080


def u16(raw: bytes) -> int:
    return int.from_bytes(raw[:2], "little")


def read_scene(session) -> dict[str, int]:
    room = session.read_memory("snesMemory", 0x7FF2BE, 0x42)
    actor = session.read_memory("snesMemory", ACTOR_POSITIONS + 4, 4)
    state = session.read_memory("snesMemory", OBJECT_STATES + 490, 1)[0]
    ctl = session.read_memory("snesMemory", CONTROLLER, 0x10)
    return {
        "room": room[1], "phase": room[4],
        "actor_x": u16(actor), "actor_y": u16(actor[2:]),
        "walkbox": session.read_memory("snesMemory", ACTOR_WALKBOX + 1, 1)[0],
        "moving1": session.read_memory("snesMemory", 0x7FF221, 1)[0],
        "moving2": session.read_memory("snesMemory", 0x7FF222, 1)[0],
        "moving11": session.read_memory("snesMemory", 0x7FF22B, 1)[0],
        "actor11_x": u16(session.read_memory("snesMemory", 0x7FF1CC, 2)),
        "actor11_y": u16(session.read_memory("snesMemory", 0x7FF1CE, 2)),
        "actor11_box": session.read_memory("snesMemory", 0x7FFDB0, 1)[0],
        "actor11_dest_x": u16(session.read_memory("snesMemory", 0x7FFDF0, 2)),
        "actor11_dest_y": u16(session.read_memory("snesMemory", 0x7E7BC0, 2)),
        "actor11_current_box": session.read_memory("snesMemory", 0x7E7BF5, 1)[0],
        "actor11_dest_box": session.read_memory("snesMemory", 0x7FFDD0, 1)[0],
        "actor11_walkbox": session.read_memory("snesMemory", 0x7FFDB0, 1)[0],
        "actor11_result_box": session.read_memory("snesMemory", 0x7FFECE, 1)[0],
        "movement_actor": session.read_memory("snesMemory", 0x7E7EB4, 1)[0],
        "actor1_dest_x": u16(session.read_memory("snesMemory", 0x7FFDE7, 2)),
        "actor1_dest_y": u16(session.read_memory("snesMemory", 0x7E7BAC, 2)),
        "actor1_current_box": session.read_memory("snesMemory", 0x7E7BEB, 1)[0],
        "actor1_dest_box": session.read_memory("snesMemory", 0x7FFDC6, 1)[0],
        "actor1_route_target_x": u16(session.read_memory("snesMemory", 0x7E7C8C, 2)),
        "actor1_route_target_y": u16(session.read_memory("snesMemory", 0x7E7CCC, 2)),
        "actor1_route_origin_x": u16(session.read_memory("snesMemory", 0x7E7C0C, 2)),
        "actor1_route_origin_y": u16(session.read_memory("snesMemory", 0x7E7C4C, 2)),
        "actor1_step_count": session.read_memory("snesMemory", 0x7E5016, 1)[0],
        "actor1_x_write_count": session.read_memory("snesMemory", 0x7E5024, 1)[0],
        "actor1_last_x": u16(session.read_memory("snesMemory", 0x7E5008, 2)),
        "actor1_last_y": u16(session.read_memory("snesMemory", 0x7E500A, 2)),
        "actor1_scale_x": session.read_memory("snesMemory", 0x7F370D, 1)[0],
        "actor1_scale_y": session.read_memory("snesMemory", 0x7F370E, 1)[0],
        "actor1_speed_x": session.read_memory("snesMemory", 0x7F3701, 1)[0],
        "actor1_speed_y": session.read_memory("snesMemory", 0x7F3702, 1)[0],
        "room_box_count": session.read_memory("snesMemory", 0x7FFA40, 1)[0],
        "cutscene": u16(session.read_memory("snesMemory", 0x7FD348, 2)),
        "talk_active": session.read_memory("snesMemory", 0x7E7A20, 1)[0],
        "talk_have_msg": session.read_memory("snesMemory", 0x7E7A21, 1)[0],
        "actor11_leg_target_x": u16(session.read_memory("snesMemory", 0x7E7CA0, 2)),
        "actor11_leg_target_y": u16(session.read_memory("snesMemory", 0x7E7CE0, 2)),
        "actor11_leg_origin_x": u16(session.read_memory("snesMemory", 0x7E7C20, 2)),
        "actor11_leg_origin_y": u16(session.read_memory("snesMemory", 0x7E7C60, 2)),
        "actor11_room": session.read_memory("snesMemory", 0x7F3996, 1)[0],
        "actor11_speed_x": session.read_memory("snesMemory", 0x7F3981, 1)[0],
        "actor11_speed_y": session.read_memory("snesMemory", 0x7F3982, 1)[0],
        "actor11_ignore_boxes": session.read_memory("snesMemory", 0x7F3991, 1)[0],
        "actor11_dest_x": u16(session.read_memory("snesMemory", 0x7FFDF0, 2)),
        "actor11_dest_y": u16(session.read_memory("snesMemory", 0x7E7BC0, 2)),
        "actor11_current_box": session.read_memory("snesMemory", 0x7E7BF5, 1)[0],
        "actor11_dest_box": session.read_memory("snesMemory", 0x7FFDD0, 1)[0],
        "actor11_walkbox": session.read_memory("snesMemory", 0x7FFDB0, 1)[0],
        "actor11_result_box": session.read_memory("snesMemory", 0x7FFECE, 1)[0],
        "movement_actor": session.read_memory("snesMemory", 0x7E7EB4, 1)[0],
        "room_box_count": session.read_memory("snesMemory", 0x7FFA40, 1)[0],
        "actor11_leg_target_x": u16(session.read_memory("snesMemory", 0x7E7CA0, 2)),
        "actor11_leg_target_y": u16(session.read_memory("snesMemory", 0x7E7CE0, 2)),
        "actor11_leg_origin_x": u16(session.read_memory("snesMemory", 0x7E7C20, 2)),
        "actor11_leg_origin_y": u16(session.read_memory("snesMemory", 0x7E7C60, 2)),
        "scumm_error": session.read_memory("snesMemory", 0x7E2303, 1)[0],
        "error": session.read_memory("snesMemory", 0x7E2303, 1)[0],
        "object490_state": state, "mode": ctl[0], "cursor_x": u16(ctl[1:]),
        "cursor_y": u16(ctl[3:]), "verb": ctl[5], "object": u16(ctl[6:]),
        "hud_dirty": ctl[8], "submissions": ctl[9], "last_action": ctl[10],
        "controller_diag": ctl[12],
        "controller_diag_room": ctl[13], "controller_diag_phase": ctl[14],
        "controller_diag_input": ctl[15],
        "input_held": u16(session.read_memory("snesMemory", 0x7E2200, 2)),
        "input_pressed": u16(session.read_memory("snesMemory", 0x7E2204, 2)),
        "c20": session.read_memory("snesMemory", 0x7FD380, 1)[0],
        "sentence_api_pending": session.read_memory("snesMemory", 0x7E7EC7, 1)[0],
    }


def read_ready(session) -> dict[str, int]:
    room = session.read_memory("snesMemory", 0x7FF2BE, 0x05)
    movement_flags = session.read_memory("snesMemory", 0x7FF220, 32)
    state = {
        "room": room[1], "phase": room[4],
        "movement_nonzero": [i for i, value in enumerate(movement_flags) if value],
        "error": session.read_memory("snesMemory", 0x7E2303, 1)[0],
        "walkbox": session.read_memory("snesMemory", ACTOR_WALKBOX + 1, 1)[0],
        "moving1": session.read_memory("snesMemory", 0x7FF221, 1)[0],
        "moving2": session.read_memory("snesMemory", 0x7FF222, 1)[0],
        "moving11": session.read_memory("snesMemory", 0x7FF22B, 1)[0],
        "actor11_x": u16(session.read_memory("snesMemory", 0x7FF1CC, 2)),
        "actor11_y": u16(session.read_memory("snesMemory", 0x7FF1CE, 2)),
        "actor11_box": session.read_memory("snesMemory", 0x7FFDB0, 1)[0],
        "actor11_dest_x": u16(session.read_memory("snesMemory", 0x7FFDFB, 2)),
        "actor11_dest_y": u16(session.read_memory("snesMemory", 0x7E7BC0, 2)),
        "actor11_current_box": session.read_memory("snesMemory", 0x7E7BF5, 1)[0],
        "actor11_room": session.read_memory("snesMemory", 0x7F3996, 1)[0],
        "actor11_speed_x": session.read_memory("snesMemory", 0x7F3981, 1)[0],
        "actor11_speed_y": session.read_memory("snesMemory", 0x7F3982, 1)[0],
        "actor11_ignore_boxes": session.read_memory("snesMemory", 0x7F3991, 1)[0],
        "actor11_dest_box": session.read_memory("snesMemory", 0x7FFDD0, 1)[0],
        "actor11_walkbox": session.read_memory("snesMemory", 0x7FFDB0, 1)[0],
        "room_box_count": session.read_memory("snesMemory", 0x7FFA40, 1)[0],
        "actor11_leg_target_x": u16(session.read_memory("snesMemory", 0x7E7CA0, 2)),
        "actor11_leg_target_y": u16(session.read_memory("snesMemory", 0x7E7CE0, 2)),
        "actor11_leg_origin_x": u16(session.read_memory("snesMemory", 0x7E7C20, 2)),
        "actor11_leg_origin_y": u16(session.read_memory("snesMemory", 0x7E7C60, 2)),
        "moving1": session.read_memory("snesMemory", 0x7FF221, 1)[0],
        "moving2": session.read_memory("snesMemory", 0x7FF222, 1)[0],
        "moving11": session.read_memory("snesMemory", 0x7FF22B, 1)[0],
        "cutscene": u16(session.read_memory("snesMemory", 0x7FD348, 2)),
        "talk_active": session.read_memory("snesMemory", 0x7E7A20, 1)[0],
        "talk_have_msg": session.read_memory("snesMemory", 0x7E7A21, 1)[0],
        "c19_stack_pointer": session.read_memory("snesMemory", 0x7FD348, 1)[0],
        "c19_depth0": session.read_memory("snesMemory", 0x7FD363, 1)[0],
        "c19_depth1": session.read_memory("snesMemory", 0x7FD364, 1)[0],
        "c19_depth2": session.read_memory("snesMemory", 0x7FD365, 1)[0],
        "c20": session.read_memory("snesMemory", 0x7FD380, 1)[0],
        "pending": session.read_memory("snesMemory", 0x7E7EC7, 1)[0],
        "talk": session.read_memory("snesMemory", 0x7E7A20, 1)[0],
        "pending_room": session.read_memory("snesMemory", 0x7FF2C1, 1)[0],
        "pending_record": session.read_memory("snesMemory", 0x7FF2C0, 1)[0],
        "validation_count": session.read_memory("snesMemory", 0x7FF2C8, 1)[0],
        "lifecycle_count": session.read_memory("snesMemory", 0x7FF2C9, 1)[0],
        "checksum": u16(session.read_memory("snesMemory", 0x7FF2D0, 2)),
        "byte": u16(session.read_memory("snesMemory", 0x7FF2D2, 2)),
        "active_record": session.read_memory("snesMemory", 0x7FF2BE, 1)[0],
        "fixture_requested": session.read_memory("snesMemory", 0x7E5600, 1)[0],
        "controller_request": session.read_memory("snesMemory", 0x7E5FEB, 1)[0],
        "error_site": session.read_memory("snesMemory", 0x7FF466, 1)[0],
        "m23a_error_site": session.read_memory("snesMemory", 0x7E57B1, 1)[0],
        "program": session.read_memory("snesMemory", 0x7E2362, 1)[0],
        "pc": u16(session.read_memory("snesMemory", 0x7E2300, 2)),
        "status": session.read_memory("snesMemory", 0x7E2302, 1)[0],
        "current_slot": session.read_memory("snesMemory", 0x7E2A88, 1)[0],
        "active_count": session.read_memory("snesMemory", 0x7E2A8A, 1)[0],
        "last_allocated": session.read_memory("snesMemory", 0x7E2A89, 1)[0],
        "seed_count_before": session.read_memory("snesMemory", 0x7E5981, 1)[0],
        "seed_count_after": session.read_memory("snesMemory", 0x7E5982, 1)[0],
        "m23a_hold": session.read_memory("snesMemory", 0x7FF2C4, 1)[0],
        "nested": session.read_memory("snesMemory", 0x7FD335, 1)[0],
        "return_mode": session.read_memory("snesMemory", 0x7E2363, 1)[0],
        "parent_slot": session.read_memory("snesMemory", 0x7E2A8C, 1)[0],
        "error_count": session.read_memory("snesMemory", 0x7E5F20, 1)[0],
        "error_code": session.read_memory("snesMemory", 0x7E5F21, 1)[0],
        "error_program": session.read_memory("snesMemory", 0x7E5F22, 1)[0],
        "error_pc": u16(session.read_memory("snesMemory", 0x7E5F23, 2)),
        "error_opcode": session.read_memory("snesMemory", 0x7E5F25, 1)[0],
    }
    # Slot/program breadcrumbs are observational only.  They distinguish an
    # ENCD that yielded at its first instruction from one that launched a
    # child and then stalled or reused its parent slot.
    state.update({
        "last_op_program": session.read_memory("snesMemory", 0x7E5F00, 1)[0],
        "last_op_pc": u16(session.read_memory("snesMemory", 0x7E5F01, 2)),
        "last_op_opcode": session.read_memory("snesMemory", 0x7E5F03, 1)[0],
        "slot0_status": session.read_memory("snesMemory", 0x7E2380, 1)[0],
        "slot0_number": session.read_memory("snesMemory", 0x7E2399, 1)[0],
        "slot0_program": session.read_memory("snesMemory", 0x7E23B2, 1)[0],
        "slot0_pc": u16(session.read_memory("snesMemory", 0x7E23E4, 2)),
        "slot1_status": session.read_memory("snesMemory", 0x7E2381, 1)[0],
        "slot1_number": session.read_memory("snesMemory", 0x7E239A, 1)[0],
        "slot1_program": session.read_memory("snesMemory", 0x7E23B3, 1)[0],
        "slot1_pc": u16(session.read_memory("snesMemory", 0x7E23E6, 2)),
        "slot1_delay": u16(session.read_memory("snesMemory", 0x7E2418, 2)),
        "slot1_freeze": session.read_memory("snesMemory", 0x7E24A1, 1)[0],
        "slot2_status": session.read_memory("snesMemory", 0x7E2382, 1)[0],
        "slot2_number": session.read_memory("snesMemory", 0x7E239B, 1)[0],
        "slot2_program": session.read_memory("snesMemory", 0x7E23B4, 1)[0],
        "slot2_pc": u16(session.read_memory("snesMemory", 0x7E23E8, 2)),
        "slot2_delay": u16(session.read_memory("snesMemory", 0x7E241A, 2)),
        "slot2_freeze": session.read_memory("snesMemory", 0x7E24A2, 1)[0],
        "string64_size": session.read_memory("snesMemory", 0x7E2DE0, 1)[0],
        "string30_size": session.read_memory("snesMemory", 0x7E2DBE, 1)[0],
        "c19_error_selector": session.read_memory("snesMemory", 0x7E5684, 1)[0],
        "c19_error_operand": u16(session.read_memory("snesMemory", 0x7E5685, 2)),
        "c19_error_stack": session.read_memory("snesMemory", 0x7E5687, 1)[0],
        "c19_error_slot": session.read_memory("snesMemory", 0x7E5698, 1)[0],
        "c19_error_depth": session.read_memory("snesMemory", 0x7E5699, 1)[0],
        "c19_error_last_opcode": session.read_memory("snesMemory", 0x7E569A, 1)[0],
        "c8_subop": session.read_memory("snesMemory", 0x7E2EA0, 1)[0],
        "c8_string_id": session.read_memory("snesMemory", 0x7E2EA1, 1)[0],
        "c8_index": session.read_memory("snesMemory", 0x7E2EA3, 1)[0],
        "c8_value": session.read_memory("snesMemory", 0x7E2EA4, 1)[0],
        "c8_length": session.read_memory("snesMemory", 0x7E2EA5, 1)[0],
        "c8_source_base": u16(session.read_memory("snesMemory", 0x7E2EA6, 2)),
        "c8_dest_base": u16(session.read_memory("snesMemory", 0x7E2EA8, 2)),
    })
    return state


def step(session, count: int = 1) -> None:
    for _ in range(count):
        session.resume()
        result = session.run_frames(1)
        if result["framesAdvanced"] != 1 or result["timedOut"]:
            raise RuntimeError(f"unsafe/incomplete frame: {result}")


def advance_safe(session, frames: int = 8) -> None:
    """Advance only after a stable boundary, without sampling mid-frame."""
    session.resume()
    result = session.run_frames(frames)
    if result["framesAdvanced"] != frames or result["timedOut"]:
        raise RuntimeError(f"unsafe/incomplete frame batch: {result}")


def tap(session, button: int) -> None:
    # set_input is itself a bounded emulator run.  Advancing once more after
    # it clears the one-frame edge before SAME_Input_Poll can consume it.
    # Hold through two emulated frames: the first frame creates the edge and
    # the second keeps the controller level present across the NMI/frame seam.
    session.set_input(button, 2)
    session.set_input(0, 2)


def capture_mode3_surface(session, path: Path) -> None:
    """Save the actual SA-1 indexed surface, independent of PPU screenshots."""
    pixels = session.read_memory("snesMemory", 0x402000, 256 * 224)
    palette = session.read_memory("snesMemory", 0x41E200, 768)
    rgb = bytearray()
    for index in pixels:
        raw = int.from_bytes(palette[index * 3:index * 3 + 3], "little")
        # The surface palette is RGB8 in the backend contract; retain that
        # contract for the diagnostic capture rather than interpreting it as
        # SNES BGR555/CGRAM data.
        rgb.extend(palette[index * 3:index * 3 + 3])
    path.write_bytes(
        (f"P6\n256 224\n255\n".encode("ascii")) + bytes(rgb)
    )
    session.set_input(0, 1)
    step(session)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "build/controller-room42.sfc")
    parser.add_argument("--output", type=Path, default=ROOT / "build/controller-room42-run")
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44331)
    parser.add_argument("--startup-frames", type=int, default=5000)
    parser.add_argument("--capture-only", action="store_true",
                        help="stop at the stable visible room-42 checkpoint")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    require(args.rom.is_file(), f"missing ROM: {args.rom}")
    require(args.nexen.is_file(), f"missing Nexen: {args.nexen}")
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    events: list[dict[str, object]] = []
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=2.0, socket_timeout=10.0,
        stderr_log=args.output / "nexen-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        # Power-reset WRAM is not a frame-safe observation point.  The
        # accepted startup42 validator lets the reset prologue and first NMI
        # complete before reading SCUMM state; keep the controller harness on
        # the same boundary so uninitialized bytes cannot be mistaken for a
        # room transition or runtime error.
        session.run_frames(2)
        session.pause()
        session.drain_notifications(timeout=0.0)
        started = False
        start_release = None
        ready = 0
        last_room = None
        # Startup title input is a real one-frame controller boundary.  Do not
        # batch this observation window: room 75 can be installed and consumed
        # between two eight-frame samples, which loses the START edge while
        # leaving the production lifecycle healthy.
        for frame in range(1, args.startup_frames):
            if frame % 400 == 1:
                print(f"controller frame {frame}", flush=True)
            pre = read_ready(session)
            if (pre["room"], pre["phase"], pre["error"]) != last_room:
                print(f"transition frame {frame}: {pre}", flush=True)
                last_room = (pre["room"], pre["phase"], pre["error"])
            # Some current startup profiles expose room 68 as the interactive
            # title/input boundary before the authored 68 -> 75 handoff;
            # accepting either room keeps this controller replay on the real
            # input path instead of depending on an observation of the brief
            # intermediate room-75 install.
            if not started and pre["room"] in (68, 75) and pre["phase"] in (0, 2):
                session.set_input(session.BTN_START, 40)
                started = True
                start_release = frame + 40
            elif start_release is not None and frame >= start_release:
                session.set_input(0, 1)
                start_release = None
            step(session)
            post = read_ready(session)
            if post["room"] == 42 and frame >= 225:
                print(
                    "room42 frame %d: program=%d pc=%d last=%02x:%04x/%02x "
                    "slot0=%d/%d/%d/%d slot1=%d/%d/%d/%d active=%d phase=%d err=%d"
                    % (
                        frame, post["program"], post["pc"], post["last_op_program"],
                        post["last_op_pc"], post["last_op_opcode"],
                        post["slot0_status"], post["slot0_number"],
                        post["slot0_program"], post["slot0_pc"],
                        post["slot1_status"], post["slot1_number"],
                        post["slot1_program"], post["slot1_pc"],
                        post["active_count"], post["phase"], post["error"],
                    ), flush=True,
                )
                if post["error"]:
                    print(
                        "  c8 subop=%02x id=%02x index=%02x value=%02x len=%02x "
                        "src=%04x dst=%04x c19=%02x/%04x/%02x/%02x/%02x/%02x"
                        % (
                            post["c8_subop"], post["c8_string_id"], post["c8_index"],
                            post["c8_value"], post["c8_length"], post["c8_source_base"],
                            post["c8_dest_base"], post["c19_error_selector"],
                            post["c19_error_operand"], post["c19_error_stack"],
                            post["c19_error_slot"], post["c19_error_depth"],
                            post["c19_error_last_opcode"],
                        ), flush=True,
                    )
                elif frame % 100 == 0:
                    print(
                        "  readiness walkbox=%d cutscene=%d c20=%d pending=%d "
                        "talk=%d/%d active=%d moving=%d/%d"
                        % (post["walkbox"], post["cutscene"], post["c20"],
                           post["pending"], post["talk_active"],
                           post["talk_have_msg"], post["active_count"],
                           post["moving1"], post["moving2"]), flush=True)
            # Controller-scene room installation remains in its stable
            # authored phase-2 publication state on this profile.  Phase 0
            # is also accepted for builds which retire the entry callback
            # one frame earlier; neither phase is a transient transition when
            # the remaining semantic gates below are clear.
            if (post["room"] == 42 and post["phase"] in (0, 2) and post["error"] == 0
                    and post["walkbox"] != 0 and post["cutscene"] == 0
                    and post["c20"] == 0 and post["pending"] == 0
                    and post["talk"] == 0):
                ready += 1
            else:
                ready = 0
            if ready >= 6:
                break
        require(ready >= 6, f"room-42 semantic readiness was not reached; last={post} started={started}")
        events.append({"stage": "ready", "frame": frame, "state": read_scene(session)})
        # Semantic readiness and visible presentation have separate lifetimes:
        # the room surface may still be converting while SCUMM is already
        # accepting input.  Wait at a stable frame boundary for the normal
        # pending-room service to publish room 42; do not bypass it or write
        # the PPU from the validator.
        visual_ready = False
        for _ in range(300):
            surface_state = session.read_memory("snesMemory", 0x401080, 0x34)
            backend = session.read_memory("snesMemory", 0x401000, 0x40)
            event_state = session.read_memory("snesMemory", 0x7E2000, 0x06)
            accepted_present = int.from_bytes(backend[0x1A:0x1C], "little")
            event_count = int.from_bytes(event_state[0x04:0x06], "little")
            # Surface validity is only the producer-side condition.  Native
            # presentation is ready only after a present was accepted, the
            # event FIFO is drained, and the committed character/CGRAM planes
            # match the ROM-backed DMA shadows in the actual PPU memories.
            if (surface_state[0] == 42 and surface_state[4] == 1
                    and surface_state[0x26] == 0 and accepted_present > 0
                    and event_count == 0
                    and session.read_memory("snesVideoRam", 0, 0xE000)
                    == session.read_memory("snesMemory", 0x410000, 0xE000)
                    and session.read_memory("snesCgRam", 0, 0x200)
                    == session.read_memory("snesMemory", 0x41E000, 0x200)):
                visual_ready = True
                break
            advance_safe(session, 8)
        if not visual_ready:
            print("visual wait CPU:", session.get_cpu_state("Snes"), flush=True)
            print("visual wait SA1:", session.get_cpu_state("Sa1"), flush=True)
        require(visual_ready, f"room-42 visual publication was not reached; state={list(surface_state)}")
        events.append({"stage": "visual_ready", "state": read_scene(session)})
        session.take_screenshot(format="base64")
        (args.output / "01-ready.png").write_bytes(
            base64.b64decode(session.take_screenshot(format="base64")["base64"])
        )
        capture_mode3_surface(session, args.output / "01-ready-surface.ppm")
        tilemap = session.tool("render_tilemap", {"layer": 5, "scale": 1, "format": "base64"})
        (args.output / "01-ready-main.png").write_bytes(base64.b64decode(tilemap["base64"]))
        if args.capture_only:
            surface_reads = {}
            for memory_type, address in (
                ("snesMemory", 0x402000), ("snesMemory", 0x6000),
                ("sa1Memory", 0x2000), ("sa1Memory", 0x402000),
            ):
                try:
                    raw = bytes(session.read_memory(memory_type, address, 64))
                    surface_reads[f"{memory_type}:{address:06x}"] = {
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "prefix": list(raw[:16]),
                    }
                except Exception as exc:
                    surface_reads[f"{memory_type}:{address:06x}"] = {"error": str(exc)}
            (args.output / "report.json").write_text(json.dumps({
                "result": "ready", "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
                "events": events, "controller_only": True,
                "ppu": session.get_ppu_state(),
                "cpu": session.get_cpu_state("Snes"),
                "direct_page_f0_f8": list(session.read_memory("snesMemory", 0x00F0, 9)),
                "room_row_table": list(session.read_memory("snesMemory", 0x5E8316, 15)),
                "room_row_source": list(session.read_memory("snesMemory", 0x5C8000, 32)),
                "vram": {
                    "sha256": hashlib.sha256(bytes(session.read_memory("snesVideoRam", 0, 0x10000))).hexdigest(),
                    "tilemap_prefix": list(session.read_memory("snesVideoRam", 0xE000, 64)),
                    "char_prefix": list(session.read_memory("snesVideoRam", 0, 64)),
                    "char_sha256": hashlib.sha256(bytes(session.read_memory("snesVideoRam", 0, 0xE000))).hexdigest(),
                    "tile_shadow_sha256": hashlib.sha256(bytes(session.read_memory("snesMemory", 0x410000, 0xE000))).hexdigest(),
                },
                "surface_state": list(session.read_memory("snesMemory", 0x401080, 0x34)),
                "surface_sample_y40": list(session.read_memory("snesMemory", 0x402000 + 40 * 256, 64)),
                "event_state": list(session.read_memory("snesMemory", 0x7E2000, 0x24)),
                "event_buffer": list(session.read_memory("snesMemory", 0x7E2100, 0x100)),
                "overlay_state": list(session.read_memory("snesMemory", 0x41F614, 0x20)),
                "visual_directory": list(session.read_memory("snesMemory", 0x6A8000, 96)),
                "logical_frame": int.from_bytes(session.read_memory("snesMemory", 0x7E2210, 2), "little"),
                "engine_phase": session.read_memory("snesMemory", 0x7E5F10, 1)[0],
                "tile_shadow_prefix": list(session.read_memory("snesMemory", 0x410000, 64)),
                "palette_prefix": list(session.read_memory("snesMemory", 0x41E200, 48)),
                "cgram_prefix": list(session.read_memory("snesCgRam", 0, 48)),
                "cgram_shadow_prefix": list(session.read_memory("snesMemory", 0x41E000, 48)),
                "surface_reads": surface_reads,
                "backend_control": list(session.read_memory("snesMemory", 0x401000, 0x80)),
                "dma_state": list(session.read_memory("snesMemory", 0x7E223A, 0x2E)),
                "nmi_count": int.from_bytes(session.read_memory("snesMemory", 0x7E102E, 2), "little"),
                "vram_prefix": list(session.read_memory("snesVideoRam", 0, 64)),
            }, indent=2) + "\n")
            return 0

        # Move the scene cursor into the authored locker hotspot using repeated
        # ordinary controller taps; no mailbox or game-state writes are made.
        # Use only ordinary controller taps and adapt to the cursor position;
        # this avoids a coordinate write while tolerating input-edge
        # coalescing during the first visible room frames.
        for _ in range(120):
            cursor_x = read_scene(session)["cursor_x"]
            if 190 <= cursor_x <= 240:
                break
            tap(session, session.BTN_RIGHT if cursor_x < 190 else session.BTN_LEFT)
        require(190 <= read_scene(session)["cursor_x"] <= 240,
                "controller cursor did not reach locker hotspot")
        events.append({"stage": "locker_hover", "frame": frame, "state": read_scene(session)})
        (args.output / "02-hover.png").write_bytes(
            base64.b64decode(session.take_screenshot(format="base64")["base64"])
        )
        capture_mode3_surface(session, args.output / "02-hover-surface.ppm")
        tap(session, session.BTN_A)
        events.append({"stage": "object_selected", "state": read_scene(session)})
        tap(session, session.BTN_Y)
        events.append({"stage": "verb_selected", "state": read_scene(session)})
        tap(session, session.BTN_A)
        events.append({"stage": "open_submitted", "state": read_scene(session)})
        print("controller open sequence:", events[-4:], flush=True)
        for _ in range(150):
            advance_safe(session, 8)
            state = read_scene(session)
            if state["object490_state"] == 1 and state["walkbox"] != 0 and state["actor_x"] == 218:
                break
        require(state["object490_state"] == 1, f"locker did not open through controller sentence: {state}")
        events.append({"stage": "opened", "state": state})
        (args.output / "03-opened.png").write_bytes(
            base64.b64decode(session.take_screenshot(format="base64")["base64"])
        )
        capture_mode3_surface(session, args.output / "03-opened-surface.ppm")
        for _ in range(30):
            if read_scene(session)["mode"] == 3:
                break
            advance_safe(session, 1)
        require(read_scene(session)["mode"] == 3,
                "controller did not publish the authored inspect mode after opening")
        tap(session, session.BTN_A)
        events.append({"stage": "inspect_submitted", "state": read_scene(session)})
        message_seen = False
        dialogue_captured = False
        for _ in range(150):
            advance_safe(session, 8)
            current = read_scene(session)
            talk = session.read_memory("snesMemory", 0x7E7A20, 2)
            message_seen |= bool(talk[0] or talk[1])
            if message_seen and not dialogue_captured:
                (args.output / "04-dialogue-active.png").write_bytes(
                    base64.b64decode(session.take_screenshot(format="base64")["base64"])
                )
                capture_mode3_surface(session, args.output / "04-dialogue-active-surface.ppm")
                dialogue_captured = True
            if message_seen and not talk[0] and current["error"] == 0:
                break
        require(message_seen, "inspection dialogue never became logically active")
        require(dialogue_captured, "inspection dialogue was not captured while active")
        require(current["error"] == 0, f"SCUMM error after inspection: {current}")
        events.append({"stage": "inspection_complete", "state": current})
        (args.output / "04-dialogue-complete.png").write_bytes(
            base64.b64decode(session.take_screenshot(format="base64")["base64"])
        )
        capture_mode3_surface(session, args.output / "04-dialogue-complete-surface.ppm")
    report = {
        "result": "pass", "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "events": events, "controller_only": True,
        "visual_record": "build/m25a-validator/startup42/room42/room-42.sc5v",
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
