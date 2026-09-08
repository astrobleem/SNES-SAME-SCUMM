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
import time
from pathlib import Path
import sys
from io import BytesIO

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_NATIVE_ENABLED = True
INPUT_HOLD_FRAMES = 40
RESTORE_DEBUG_HOOK = None
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


def build_identity_for(rom: Path) -> dict[str, str] | None:
    """Return the build sidecar identity without making it a runtime input."""
    sidecar = rom.with_suffix(".build_identity.json")
    if not sidecar.is_file():
        return None
    raw = sidecar.read_bytes()
    return {
        "path": str(sidecar),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def u16(raw: bytes, offset: int = 0) -> int:
    """Read a little-endian word from a debugger memory response."""
    return int.from_bytes(raw[offset:offset + 2], "little")


def active_room_objects(session) -> list[dict[str, int]]:
    """Read the source-backed active-room CDHD records copied by room load."""
    count = session.read_memory("snesMemory", 0x7E5FFC, 1)[0]
    raw = session.read_memory("snesMemory", 0x7E7000, count * 11)
    result = []
    for offset in range(0, len(raw), 11):
        result.append({
            "object": u16(raw, offset),
            "x": int.from_bytes(raw[offset + 2:offset + 4], "little", signed=True),
            "y": int.from_bytes(raw[offset + 4:offset + 6], "little", signed=True),
            "width": u16(raw, offset + 6),
            "height": u16(raw, offset + 8),
            "flags": raw[offset + 10],
        })
    return result


def object_center_from_source_records(session, object_id: int) -> tuple[int, int, dict[str, int]]:
    objects = active_room_objects(session)
    target = next((item for item in objects if item["object"] == object_id), None)
    if target is not None:
        # Choose a point from the source rectangle whose canonical forward
        # object scan resolves to this object.  Centers are not sufficient:
        # v5 permits overlapping CDHD rectangles and the first source object
        # wins.  This remains a source-derived controller target, not a
        # Fate-specific coordinate.
        cursor_x = u16(session.read_memory("snesMemory", 0x7E5FE1, 2))
        cursor_y = u16(session.read_memory("snesMemory", 0x7E5FE3, 2))
        camera_x = u16(session.read_memory("snesMemory", 0x7E7FB8, 2))
        camera_y = u16(session.read_memory("snesMemory", 0x7E7FAA, 2))
        for y in range(target["y"] + target["height"] - 1, target["y"] - 1, -1):
            screen_y = y - camera_y + 0x64
            if (screen_y - cursor_y) & 1:
                continue
            for x in range(target["x"] + target["width"] - 1, target["x"] - 1, -1):
                screen_x = x - camera_x
                if (screen_x - cursor_x) & 1:
                    continue
                first = next((item for item in objects
                              if item["x"] <= x < item["x"] + item["width"]
                              and item["y"] <= y < item["y"] + item["height"]), None)
                if first is target:
                    return x, y, target
        raise RuntimeError(f"source object {object_id} has no canonical selectable point")
    raise RuntimeError(f"source object {object_id} is absent from active room metadata")


def move_cursor_to_source_object(session, object_id: int, limit: int = 128) -> tuple[dict[str, int], int, int]:
    """Move the real cursor to a source-derived selectable CDHD point."""
    target_x, target_y, record = object_center_from_source_records(session, object_id)
    for _ in range(limit):
        cursor_x = u16(session.read_memory("snesMemory", 0x7E5FE1, 2))
        cursor_y = u16(session.read_memory("snesMemory", 0x7E5FE3, 2))
        camera_x = u16(session.read_memory("snesMemory", 0x7E7FB8, 2))
        camera_y = u16(session.read_memory("snesMemory", 0x7E7FAA, 2))
        room_x = cursor_x + camera_x
        room_y = (cursor_y + camera_y - 0x64) & 0xFFFF
        if (record["x"] <= room_x < record["x"] + record["width"]
                and record["y"] <= room_y < record["y"] + record["height"]):
            return record, room_x, room_y
        screen_x = target_x - camera_x
        screen_y = target_y - camera_y + 0x64
        if cursor_x < screen_x:
            button = session.BTN_RIGHT
        elif cursor_x > screen_x:
            button = session.BTN_LEFT
        elif cursor_y < screen_y:
            button = session.BTN_DOWN
        else:
            button = session.BTN_UP
        tap(session, button)
    raise RuntimeError(f"cursor did not reach source object {object_id}: {record}")


def read_scene(session) -> dict[str, int]:
    room = session.read_memory("snesMemory", 0x7FF2BE, 0x42)
    actor = session.read_memory("snesMemory", ACTOR_POSITIONS + 4, 4)
    state = session.read_memory("snesMemory", OBJECT_STATES + 490, 1)[0]
    ctl = session.read_memory("snesMemory", CONTROLLER, 0x10)
    surface_state = session.read_memory("snesMemory", 0x401080, 0x40)
    return {
        "room": room[1], "phase": room[4],
        "actor_x": u16(actor), "actor_y": u16(actor[2:]),
            "frame_counter": u16(session.read_memory("snesMemory", 0x7E2210, 2)),
            "engine_frame": u16(session.read_memory("snesMemory", 0x7E2308, 2)),
            "engine_busy": session.read_memory("snesMemory", 0x7E2231, 1)[0],
        "actor_facing_angle": u16(session.read_memory("snesMemory", 0x7E78F2, 2)),
        "selected_cooked_pose": (
            1 if session.read_memory("snesMemory", 0x7FF221, 1)[0]
            and ((u16(session.read_memory("snesMemory", 0x7E2210, 2)) >> 3) & 1)
            else 0
        ),
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
        "talk_visual_status": session.read_memory("snesMemory", 0x7E7AC7, 1)[0],
        "talk_segment_start": session.read_memory("snesMemory", 0x7E7AC2, 1)[0],
        "talk_segment_length": session.read_memory("snesMemory", 0x7E7AC3, 1)[0],
        "talk_raw": list(session.read_memory("snesMemory", 0x7E7A30, 32)),
        "c23_slot0": list(session.read_memory("snesMemory", 0x7FD409, 11)),
        "overlay_descriptor": list(session.read_memory("snesMemory", 0x41F000, 32)),
        "overlay_work": list(session.read_memory("snesMemory", 0x41F614, 32)),
        "overlay_producer": list(session.read_memory("snesMemory", 0x41F694, 32)),
        "overlay_pixels_nonzero": sum(
            value != 0 for value in session.read_memory("snesMemory", 0x41F020, 640)),
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
        "interaction": {
            "x": u16(session.read_memory("snesMemory", 0x7E5F90, 2)),
            "y": u16(session.read_memory("snesMemory", 0x7E5F92, 2)),
            "object": u16(session.read_memory("snesMemory", 0x7E5F94, 2)),
            "flags": session.read_memory("snesMemory", 0x7E5F96, 1)[0],
            "index": session.read_memory("snesMemory", 0x7E5F97, 1)[0],
            "limit": u16(session.read_memory("snesMemory", 0x7E5F98, 2)),
            "local_count": session.read_memory("snesMemory", 0x7E5FFC, 1)[0],
        },
        "hud_dirty": ctl[8], "submissions": ctl[9], "last_action": ctl[10],
        "controller_diag": ctl[12],
        "controller_diag_room": ctl[13], "controller_diag_phase": ctl[14],
        "controller_diag_input": ctl[15],
        "input_held": u16(session.read_memory("snesMemory", 0x7E2200, 2)),
        "input_pressed": u16(session.read_memory("snesMemory", 0x7E2204, 2)),
        "c20": session.read_memory("snesMemory", 0x7FD380, 1)[0],
        "sentence_api_pending": session.read_memory("snesMemory", 0x7E7EC7, 1)[0],
        "scumm_stack_pointer": session.read_memory("snesMemory", 0x7FD348, 1)[0],
        "desired_visual_x": u16(session.read_memory("snesMemory", 0x7E5E42, 2)),
        "desired_visual_y": u16(session.read_memory("snesMemory", 0x7E5E44, 2)),
        "desired_visual_select": session.read_memory("snesMemory", 0x7E5E46, 1)[0],
        "desired_visual_dest": u16(session.read_memory("snesMemory", 0x7E5E48, 2)),
        "desired_visual_facing": u16(session.read_memory("snesMemory", 0x7E5E4A, 2)),
        "desired_visual_costume": session.read_memory("snesMemory", 0x7E5E4C, 1)[0],
        "desired_visual_visible": session.read_memory("snesMemory", 0x7E5E4D, 1)[0],
        "accepted_visual_x": u16(session.read_memory("snesMemory", 0x7E5E10, 2)),
        "accepted_visual_y": u16(session.read_memory("snesMemory", 0x7E5E12, 2)),
        "accepted_visual_select": session.read_memory("snesMemory", 0x7E5E3C, 1)[0],
        "accepted_visual_facing": u16(session.read_memory("snesMemory", 0x7E5E4E, 2)),
        "accepted_visual_costume": session.read_memory("snesMemory", 0x7E5E50, 1)[0],
        "accepted_visual_visible": session.read_memory("snesMemory", 0x7E5E51, 1)[0],
        "visual_retry": session.read_memory("snesMemory", 0x7E5E24, 1)[0],
        "render_valid": session.read_memory("snesMemory", 0x7E5E16, 1)[0],
        "cursor_render_valid": session.read_memory("snesMemory", 0x7E5E2A, 1)[0],
        "cursor_render_x": u16(session.read_memory("snesMemory", 0x7E5E26, 2)),
        "cursor_render_y": u16(session.read_memory("snesMemory", 0x7E5E28, 2)),
        "render_base": u16(session.read_memory("snesMemory", 0x7E5E20, 2)),
        "actor_render_base": u16(session.read_memory("snesMemory", 0x7E5E38, 2)),
        "actor_render_frame_base": u16(session.read_memory("snesMemory", 0x7E5E3A, 2)),
        "actor_render_select": session.read_memory("snesMemory", 0x7E5E3C, 1)[0],
        "actor_render_moving_sample": session.read_memory("snesMemory", 0x7E5E3D, 1)[0],
        "actor_render_mode_sample": session.read_memory("snesMemory", 0x7E5E3E, 1)[0],
        "actor_render_dest_sample": u16(session.read_memory("snesMemory", 0x7E5E40, 2)),
        "render_src": u16(session.read_memory("snesMemory", 0x7E5E18, 2)),
        "render_rowsrc": u16(session.read_memory("snesMemory", 0x7E5E22, 2)),
        "mode3_state": session.read_memory("snesMemory", 0x401013, 1)[0],
        "mode3_locked": session.read_memory("snesMemory", 0x401014, 1)[0],
        "mode3_event_count": u16(session.read_memory("snesMemory", 0x7E2004, 2)),
        "mode3_accepted_present": u16(session.read_memory("snesMemory", 0x40101A, 2)),
        "mode3_rejected_present": u16(session.read_memory("snesMemory", 0x40101C, 2)),
        "mode3_rejected_dirty": u16(session.read_memory("snesMemory", 0x40101E, 2)),
        "mode3_candidate_count": u16(session.read_memory("snesMemory", 0x401022, 2)),
        "mode3_pending_count": u16(session.read_memory("snesMemory", 0x401024, 2)),
        "mode3_inflight_count": u16(session.read_memory("snesMemory", 0x401026, 2)),
        "mode3_expected_dma": u16(session.read_memory("snesMemory", 0x401028, 2)),
        "mode3_converted_count": u16(session.read_memory("snesMemory", 0x40102A, 2)),
        "mode3_scan_tile": u16(session.read_memory("snesMemory", 0x401038, 2)),
        "mode3_scan_palette": u16(session.read_memory("snesMemory", 0x40103A, 2)),
        "surface_compose": {
            "entries": u16(session.read_memory("snesMemory", 0x7E5E94, 2)),
            "canwrite_fail": u16(session.read_memory("snesMemory", 0x7E5E96, 2)),
            "status": session.read_memory("snesMemory", 0x7E5E98, 1)[0],
            "push_fail": session.read_memory("snesMemory", 0x7E5E99, 1)[0],
            "exits": u16(session.read_memory("snesMemory", 0x7E5E9A, 2)),
        },
        "surface_blit": {
            "entries": u16(session.read_memory("snesMemory", 0x7E5EC2, 2)),
            "fail_stage": session.read_memory("snesMemory", 0x7E5EC4, 1)[0],
            "exits": u16(session.read_memory("snesMemory", 0x7E5EC5, 2)),
            "state_at_failure": session.read_memory("snesMemory", 0x7E5EC6, 1)[0],
            "locked_at_failure": session.read_memory("snesMemory", 0x7E5EC7, 1)[0],
            "entry_state": session.read_memory("snesMemory", 0x7E5EC8, 1)[0],
            "entry_locked": session.read_memory("snesMemory", 0x7E5EC9, 1)[0],
        },
        "witness_diag": {
            "attempts": u16(session.read_memory("snesMemory", 0x7E5ECA, 2)),
            "skips": u16(session.read_memory("snesMemory", 0x7E5ECC, 2)),
            "moving": session.read_memory("snesMemory", 0x7E5ECE, 1)[0],
            "render_entries": u16(session.read_memory("snesMemory", 0x7E5ED0, 2)),
            "render_desired": u16(session.read_memory("snesMemory", 0x7E5ED2, 2)),
            "render_moving_entries": u16(session.read_memory("snesMemory", 0x7E5ED4, 2)),
        },
        # These addresses mirror SAME_VIDEO_DIAG_BASE=$7E5E90 in
        # runtime/snes/services/video_surface.pasm.  Keep this observation
        # map tied to the service-owned diagnostic block; the old $7E5Fxx
        # offsets were stale and reported unrelated WRAM as video state.
        "mode3_backend_steps": u16(session.read_memory("snesMemory", 0x7E5EBC, 2)),
        "video_service_calls": u16(session.read_memory("snesMemory", 0x7E5EAE, 2)),
        "kernel_entries": u16(session.read_memory("snesMemory", 0x7E5EB6, 2)),
        "kernel_pops": u16(session.read_memory("snesMemory", 0x7E5EB8, 2)),
        "surface_push": {
            "entries": u16(session.read_memory("snesMemory", 0x7E5E9C, 2)),
            "event_before": u16(session.read_memory("snesMemory", 0x7E5E9E, 2)),
            "generation": u16(session.read_memory("snesMemory", 0x7E5EA0, 2)),
            "fail_stage": session.read_memory("snesMemory", 0x7E5EA2, 1)[0],
            "event_after": u16(session.read_memory("snesMemory", 0x7E5EA3, 2)),
        },
        # Surface state is in the selected carrier's service window.  Keep
        # this observation map tied to the generated carrier constants rather
        # than the SCUMM WRAM diagnostic block.
        "surface_damage": {
            "x": u16(session.read_memory("snesMemory", 0x4010B4, 2)),
            "y": u16(session.read_memory("snesMemory", 0x4010B6, 2)),
            "width": u16(session.read_memory("snesMemory", 0x4010B8, 2)),
            "height": u16(session.read_memory("snesMemory", 0x4010BA, 2)),
        },
        "surface_projection": {
            "source_x": u16(surface_state[0x0C:0x0E]),
            "source_y": u16(surface_state[0x0E:0x10]),
            "dest_x": u16(surface_state[0x10:0x12]),
            "dest_y": u16(surface_state[0x12:0x14]),
            "copy_width": u16(surface_state[0x14:0x16]),
            "copy_height": u16(surface_state[0x16:0x18]),
        },
        "controller_damage": {
            "x0": u16(session.read_memory("snesMemory", 0x7E5E2E, 2)),
            "y0": u16(session.read_memory("snesMemory", 0x7E5E30, 2)),
            "x1": u16(session.read_memory("snesMemory", 0x7E5E32, 2)),
            "y1": u16(session.read_memory("snesMemory", 0x7E5E34, 2)),
        },
        "surface_status": session.read_memory("snesMemory", 0x401084, 1)[0],
        "restore_stage": session.read_memory("snesMemory", 0x7E5EBF, 1)[0],
        "restore_input": {
            "x": u16(session.read_memory("snesMemory", 0x7E5E6C, 2)),
            "y": u16(session.read_memory("snesMemory", 0x7E5E6E, 2)),
            "width": u16(session.read_memory("snesMemory", 0x7E5E70, 2)),
            "height": u16(session.read_memory("snesMemory", 0x7E5E72, 2)),
        },
        "restore_calls": u16(session.read_memory("snesMemory", 0x7E5E74, 2)),
        "restore_after_canwrite": {
            "a": u16(session.read_memory("snesMemory", 0x7E5E76, 2)),
            "x": u16(session.read_memory("snesMemory", 0x7E5E78, 2)),
        },
        "restore_caller": {
            "a": u16(session.read_memory("snesMemory", 0x7E5E7A, 2)),
            "x": u16(session.read_memory("snesMemory", 0x7E5E7C, 2)),
        },
        "restore_loop": {
            "row": u16(session.read_memory("snesMemory", 0x7E5E7E, 2)),
            "col": u16(session.read_memory("snesMemory", 0x7E5E80, 2)),
            "width": u16(session.read_memory("snesMemory", 0x7E5E82, 2)),
            "height": u16(session.read_memory("snesMemory", 0x7E5E84, 2)),
            "dst": u16(session.read_memory("snesMemory", 0x7E5E86, 2)),
            "src": u16(session.read_memory("snesMemory", 0x7E5E88, 2)),
        },
        "surface_pending_visual": session.read_memory("snesMemory", 0x4010A6, 1)[0],
        "surface_next_generation": u16(session.read_memory("snesMemory", 0x40109C, 2)),
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
        "m23a_phase": session.read_memory("snesMemory", 0x7FF2C2, 1)[0],
        "m23a_request_count": session.read_memory("snesMemory", 0x7FF2C5, 1)[0],
        "m23a_active_room": session.read_memory("snesMemory", 0x7FF2BF, 1)[0],
        "m23a_active_record": session.read_memory("snesMemory", 0x7FF2BE, 1)[0],
        "event_count": u16(session.read_memory("snesMemory", 0x7E2004, 2)),
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


def read_startup_gate(session) -> dict[str, int]:
    """Read only the fields needed while crossing the title/room handoff.

    The full scene snapshot is intentionally expensive and is reserved for
    transitions and accepted checkpoints.  Polling it twice per startup
    frame created thousands of MCP memory transactions and made the native
    controller replay appear to stall before room 42.
    """
    room = session.read_memory("snesMemory", 0x7FF2BE, 0x05)
    return {
        "room": room[1], "phase": room[4],
        "error": session.read_memory("snesMemory", 0x7E2303, 1)[0],
        "talk_active": session.read_memory("snesMemory", 0x7E7A20, 1)[0],
        "cutscene": u16(session.read_memory("snesMemory", 0x7FD348, 2)),
        "walkbox": session.read_memory("snesMemory", ACTOR_WALKBOX + 1, 1)[0],
        "c20": session.read_memory("snesMemory", 0x7FD380, 1)[0],
        "pending": session.read_memory("snesMemory", 0x7E7EC7, 1)[0],
    }


def read_locker_progress(session) -> dict[str, int]:
    """Small post-sentence poll used while the actor/script is active."""
    actor = session.read_memory("snesMemory", ACTOR_POSITIONS + 4, 4)
    return {
        "room": session.read_memory("snesMemory", 0x7FF2BF, 1)[0],
        "actor_x": u16(actor), "actor_y": u16(actor[2:]),
        "walkbox": session.read_memory("snesMemory", ACTOR_WALKBOX + 1, 1)[0],
        "moving1": session.read_memory("snesMemory", 0x7FF221, 1)[0],
        "object490_state": session.read_memory("snesMemory", OBJECT_STATES + 490, 1)[0],
        "talk_active": session.read_memory("snesMemory", 0x7E7A20, 1)[0],
        "talk_have_msg": session.read_memory("snesMemory", 0x7E7A21, 1)[0],
        "error": session.read_memory("snesMemory", 0x7E2303, 1)[0],
    }


def step(session, count: int = 1) -> None:
    for _ in range(count):
        session.resume()
        result = session.run_frames(1)
        if result["framesAdvanced"] != 1 or result["timedOut"]:
            raise RuntimeError(f"unsafe/incomplete frame: {result}")


def advance_safe(session, frames: int = 8) -> None:
    """Advance only after a stable boundary, without sampling mid-frame."""
    global RESTORE_DEBUG_HOOK
    session.resume()
    if RESTORE_DEBUG_HOOK is not None:
        result = session.run_until(max_frames=frames,
                                   hook_handle=RESTORE_DEBUG_HOOK)
        if "timedOut" not in result:
            # The hook stops at the completion label before the routine's
            # epilogue. Remove it, let that epilogue return normally, and
            # continue the same frame boundary. The hook is observational;
            # it must not become a second scheduler or a validator stop.
            session.remove_hook(RESTORE_DEBUG_HOOK)
            RESTORE_DEBUG_HOOK = None
            session.resume()
            result = session.run_frames(frames)
    else:
        result = session.run_frames(frames)
    session.pause()
    if result["framesAdvanced"] != frames or result["timedOut"]:
        raise RuntimeError(f"unsafe/incomplete frame batch: {result}")


def tap(session, button: int) -> None:
    # set_input is itself a bounded emulator run.  Advancing once more after
    # it clears the one-frame edge before SAME_Input_Poll can consume it.
    # Keep the real controller level present across the NMI/autojoy seam long
    # enough for the production input poll to sample it; the controller logic
    # still reacts only to the first pressed edge.
    session.set_input(button, INPUT_HOLD_FRAMES)
    session.set_input(0, 1)


def action_tap(session, button: int) -> None:
    """Submit one action edge without consuming the authored walk window."""
    # Cursor navigation uses the longer hold above because its bridge advances
    # one logical pixel edge at a time.  A sentence action must not be held
    # for that duration: Open's short authored walk can complete while the
    # validator is still inside set_input, hiding every in-flight generation.
    # Auto-joypad is sampled at a hardware-defined seam; four frames spans
    # the seam while leaving the authored locker walk observable.  The caller
    # then advances complete frames and waits on the actual movement state.
    session.set_input(button, 8)
    session.set_input(0, 1)


def advance_until(session, predicate, limit: int, description: str) -> dict:
    """Advance complete frames until a semantic controller boundary exists."""
    def poll():
        actor = session.read_memory("snesMemory", ACTOR_POSITIONS + 4, 4)
        ctl = session.read_memory("snesMemory", 0x7E5FE0, 0x3A)
        backend = session.read_memory("snesMemory", 0x401000, 0x40)
        return {
            "room": session.read_memory("snesMemory", 0x7FF2BF, 1)[0],
            "actor_x": u16(actor),
            "actor_y": u16(actor[2:]),
            "moving1": session.read_memory("snesMemory", 0x7FF221, 1)[0],
            "mode": ctl[0],
            "submissions": ctl[9],
            "last_action": ctl[10],
            "sentence_api_pending": session.read_memory("snesMemory", 0x7E7EC7, 1)[0],
            "c20": session.read_memory("snesMemory", 0x7FD380, 1)[0],
            "engine_frame": u16(session.read_memory("snesMemory", 0x7E2308, 2)),
            "engine_busy": session.read_memory("snesMemory", 0x7E2231, 1)[0],
            "scumm_stack_pointer": session.read_memory("snesMemory", 0x7FD348, 1)[0],
            "mode3_state": backend[0x13],
            "mode3_event_count": u16(session.read_memory("snesMemory", 0x7E2004, 2)),
            "error": session.read_memory("snesMemory", 0x7E2303, 1)[0],
            "desired_visual_x": u16(session.read_memory("snesMemory", 0x7E5E42, 2)),
            "desired_visual_select": session.read_memory("snesMemory", 0x7E5E46, 1)[0],
            "accepted_visual_x": u16(session.read_memory("snesMemory", 0x7E5E10, 2)),
            "accepted_visual_select": session.read_memory("snesMemory", 0x7E5E3C, 1)[0],
            "controller_diag": session.read_memory("snesMemory", 0x7E5FEC, 4).hex(),
            "controller_diag_input": session.read_memory("snesMemory", 0x7E5FEF, 1)[0],
            "raw_pressed": list(session.read_memory("snesMemory", 0x7E5F8E, 2)),
            "interaction_scratch": list(session.read_memory("snesMemory", 0x7E5F90, 13)),
            "active_record": session.read_memory("snesMemory", 0x7FF2BE, 1)[0],
            "verb_object": u16(session.read_memory("snesMemory", 0x7E7EBF, 2)),
            "verb_id": u16(session.read_memory("snesMemory", 0x7E7EC1, 2)),
            "verb_result": u16(session.read_memory("snesMemory", 0x7E7EC3, 2)),
            "controller_object": u16(session.read_memory("snesMemory", 0x7E5FE6, 2)),
            "active_object_records": [
                list(session.read_memory("snesMemory", 0x7E7000 + i * 11, 11))
                for i in range(session.read_memory("snesMemory", 0x7E5FFC, 1)[0])
            ],
        }
    state = poll()
    for _ in range(limit):
        if predicate(state):
            return read_scene(session)
        advance_safe(session, 1)
        state = poll()
    state["cpu"] = session.get_cpu_state("Snes")
    state["frame_counter"] = u16(session.read_memory("snesMemory", 0x7E2210, 2))
    state["trace_tail"] = session.trace_log(cpu_type="Snes", count=12)
    raise RuntimeError(f"did not reach {description}: {state}")


def capture_mode3_surface(session, path: Path, *, region: tuple[int, int, int, int] | None = None,
                          advance_after: bool = True) -> dict[str, int]:
    if not CAPTURE_NATIVE_ENABLED:
        return {}
    """Save the actual indexed surface using its published descriptor.

    The carrier surface is not necessarily a 256-byte-pitch framebuffer.  In
    the current Mode-3 service the descriptor is 408x144 with a 408-byte
    pitch.  Reading 256*224 contiguous bytes silently splices rows and is not
    evidence for a surface crop, even when the resulting RGB image changes.
    """
    state = session.read_memory("snesMemory", 0x401080, 0x40)
    width = u16(state, 0x06)
    height = u16(state, 0x08)
    pitch = u16(state, 0x0A)
    require(width > 0 and height > 0 and pitch >= width,
            f"invalid live surface descriptor: width={width} height={height} pitch={pitch}")
    # The descriptor's pitch describes the installed room source projection;
    # the active indexed carrier is the documented 256x224 live surface.
    backing_width, backing_height, backing_pitch = 256, 224, 256
    if region is None:
        # Keep the established ready-only diagnostic inexpensive.  Exact
        # actor evidence uses an explicit descriptor-backed crop below.
        x, y, capture_width, capture_height = 0, 0, backing_width, backing_height
        raw = bytes(session.read_memory("snesMemory", 0x402000,
                                       capture_width * capture_height))
        rows = [raw[row * capture_width:(row + 1) * capture_width]
                for row in range(capture_height)]
    else:
        x, y, capture_width, capture_height = region
    require(0 <= x < backing_width and 0 <= y < backing_height and capture_width > 0 and
            capture_height > 0 and x + capture_width <= backing_width and
            y + capture_height <= backing_height,
            f"surface capture outside carrier: region={region} carrier={(backing_width, backing_height, backing_pitch)}")
    if region is not None:
        raw = bytes(session.read_memory(
            "snesMemory", 0x402000 + y * backing_pitch, backing_pitch * capture_height))
        rows = [raw[row * backing_pitch + x:row * backing_pitch + x + capture_width]
                for row in range(capture_height)]
    pixels = b"".join(rows)
    path.with_suffix(".indexed.bin").write_bytes(pixels)
    palette = session.read_memory("snesMemory", 0x41E200, 768)
    rgb = bytearray()
    for index in pixels:
        raw = int.from_bytes(palette[index * 3:index * 3 + 3], "little")
        # The surface palette is RGB8 in the backend contract; retain that
        # contract for the diagnostic capture rather than interpreting it as
        # SNES BGR555/CGRAM data.
        rgb.extend(palette[index * 3:index * 3 + 3])
    path.write_bytes(
        (f"P6\n{capture_width} {capture_height}\n255\n".encode("ascii")) + bytes(rgb)
    )
    if advance_after:
        session.set_input(0, 1)
        step(session)
    return {"x": x, "y": y, "width": capture_width, "height": capture_height,
            "surface_width": width, "surface_height": height, "surface_pitch": pitch}


def capture_native_current(session, path: Path) -> None:
    """Capture exactly the current emulator frame without advancing it."""
    if not CAPTURE_NATIVE_ENABLED:
        return
    raw = base64.b64decode(session.take_screenshot(format="base64")["base64"])
    path.write_bytes(raw)


def read_publication_witness(session) -> dict[str, int]:
    raw = bytes(session.read_memory("snesMemory", 0x7E5E52, 0x1A))
    return {
        "serial": u16(raw, 0x00),
        "frame": u16(raw, 0x02),
        "x": u16(raw, 0x04),
        "y": u16(raw, 0x06),
        "moving": raw[0x08],
        "dest_x": u16(raw, 0x09),
        "dest_y": u16(raw, 0x0B),
        "pose": raw[0x0D],
        "damage_x": u16(raw, 0x0E),
        "damage_y": u16(raw, 0x10),
        "damage_w": u16(raw, 0x12),
        "damage_h": u16(raw, 0x14),
        "present_generation": u16(raw, 0x16),
        "valid": raw[0x18],
    }


def wait_for_moving_publication(session, hook_handle: int,
                                baseline_serial: int, limit: int = 32) -> dict[str, int]:
    """Stop on the success witness, not on a guessed logical-frame poll."""
    for _ in range(limit):
        # Keep each debugger transaction below the emulator's notification
        # timeout.  The write hook remains the stop condition; the bounded
        # windows only make an absent notification observable and recoverable.
        result = session.run_until(max_frames=600, hook_handle=hook_handle)
        witness = read_publication_witness(session)
        if (witness["valid"] and witness["serial"] != baseline_serial
                and witness["moving"] and witness["x"] not in (150, 218)):
            return witness
        # A write hook may stop on the low-byte/intermediate write that
        # precedes the committed-generation value.  That is an observation
        # boundary, not a stalled emulator.  Re-read the generation and keep
        # waiting for the requested value; only the bounded outer limit is a
        # failure condition.
        if int(result.get("framesAdvanced", 0)) <= 0:
            continue
    raise RuntimeError(
        f"no successful moving actor publication: witness={witness} "
        f"scene={read_scene(session)} "
        f"cpu={session.get_cpu_state('Snes')} "
        f"nmi={u16(session.read_memory('snesMemory', 0x7E102E, 2))}")


def wait_for_semantic_moving_snapshot(session, hook_handle: int,
                                      limit: int = 32) -> dict[str, int]:
    """Fence the SCUMM desired-state publication before surface composition.

    This is deliberately a validator/debugger boundary.  The production
    engine remains free to compose later in its established visual phase; the
    hook merely proves that the walking semantic snapshot was published
    before the successful actor PRESENT witness is awaited.
    """
    last: dict[str, int] = {}
    for _ in range(limit):
        result = session.run_until(max_frames=600, hook_handle=hook_handle)
        raw = bytes(session.read_memory("snesMemory", 0x7E5E42, 0x0C))
        last = {
            "x": u16(raw, 0x00),
            "y": u16(raw, 0x02),
            "select": raw[0x04],
            "dest_x": u16(raw, 0x06),
            "facing": u16(raw, 0x08),
            "costume": raw[0x0A],
            "visible": raw[0x0B],
            "frames_advanced": int(result.get("framesAdvanced", 0)),
        }
        if last["select"] == 1 and last["visible"]:
            return last
        if last["frames_advanced"] <= 0:
            break
    raise RuntimeError(f"no semantic moving snapshot publication: {last}")


def wait_for_committed_generation(session, hook_handle: int,
                                  generation: int, limit: int = 32) -> dict:
    """Fence the exact PRESENT generation using the backend commit write."""
    for _ in range(limit):
        result = session.run_until(max_frames=1200, hook_handle=hook_handle)
        backend = bytes(session.read_memory("snesMemory", 0x401000, 0x40))
        committed = u16(backend, 0x10)
        if committed == generation:
            return {
                "committed_generation": committed,
                "backend_state": backend[0x13],
                "backend_locked": backend[0x14],
                "frames_advanced": int(result.get("framesAdvanced", 0)),
            }
        if int(result.get("framesAdvanced", 0)) <= 0:
            break
    dma = bytes(session.read_memory("snesMemory", 0x7E223A, 0x0C))
    mode3 = bytes(session.read_memory("snesMemory", 0x401022, 0x20))
    queue = bytes(session.read_memory("snesMemory", 0x7E2260, 0x40))
    slot = u16(dma, 0) & 0x003F
    work = bytes(session.read_memory("snesMemory", 0x41E750, 0x24))
    pending_bits = bytes(session.read_memory("snesMemory", 0x41E570, 0x70))
    inflight_bits = bytes(session.read_memory("snesMemory", 0x41E5E0, 0x70))
    pending_palette = bytes(session.read_memory("snesMemory", 0x41E670, 0x20))
    raise RuntimeError(
        f"PRESENT generation did not commit: wanted={generation} "
        f"committed={committed} state={backend[0x13]} lock={backend[0x14]} "
        f"dma_current={u16(dma, 0)} dma_pending={u16(dma, 2)} "
        f"dma_committed={u16(dma, 4)} expected_dma={u16(backend, 0x28)} "
        f"records={u16(backend, 0x3E)} inflight={u16(backend, 0x26)} "
        f"candidates={u16(backend, 0x22)} pending_tiles={u16(backend, 0x24)} "
        f"converted={u16(backend, 0x2A)} mode3_last={u16(mode3, 0)} "
        f"queue_slot={slot} queue_desc={list(queue[slot:slot+8])} "
        f"work_index={u16(work, 0x0C)} work_row={u16(work, 0x04)} "
        f"work_run={u16(work, 0x12)} cpu={session.get_cpu_state('Snes')} "
        f"pending_bytes={list(pending_bits[:8])} inflight_bytes={list(inflight_bits[:8])} "
        f"pending_palette={list(pending_palette[:20])}")


def wait_for_backend_idle(session, hook_handle: int, limit: int = 8) -> None:
    """Fence an already-owned conversion with a state-write hook."""
    for _ in range(limit):
        state = session.read_memory("snesMemory", 0x401013, 1)[0]
        if state == 1:
            return
        result = session.run_until(max_frames=600, hook_handle=hook_handle)
        state = session.read_memory("snesMemory", 0x401013, 1)[0]
        if state == 1:
            return
        if int(result.get("framesAdvanced", 0)) <= 0:
            break
    raise RuntimeError("backend did not reach idle at its state transition")


def settle_native_capture(session, frames: int = 1800) -> None:
    """Wait for the real native display planes to converge.

    A fixed delay is insufficient after an input-driven redraw: the backend
    converts dirty tiles incrementally and a screenshot taken during that
    window is a legitimate partial frame.  Observe the same committed PPU
    planes used by the visual-readiness gate, while still advancing only at
    complete frame boundaries.
    """
    # Give the presentation backend one bounded conversion window before
    # sampling counters.  A newly accepted full-surface publish can otherwise
    # expose the previous PPU contents even though the producer is idle.
    advance_safe(session, 32)
    for _ in range(max(1, frames // 32)):
        surface_state = session.read_memory("snesMemory", 0x401080, 0x34)
        backend = session.read_memory("snesMemory", 0x401000, 0x40)
        event_state = session.read_memory("snesMemory", 0x7E2000, 0x06)
        # The backend's committed generation and drained event FIFO are the
        # native-readiness contract.  Surface status is a producer-side
        # diagnostic and may describe a later rejected/retried compose while
        # the committed generation is already valid; do not turn that
        # auxiliary byte into a false capture timeout.
        if (surface_state[0] == 42
                and surface_state[0x26] == 0
                and int.from_bytes(backend[0x1A:0x1C], "little") > 0
                and int.from_bytes(event_state[0x04:0x06], "little") == 0
                and int.from_bytes(backend[0x22:0x24], "little") == 0
                and int.from_bytes(backend[0x24:0x26], "little") == 0
                and int.from_bytes(backend[0x26:0x28], "little") == 0):
            # The native screenshot below is the acceptance evidence.  The
            # complete plane equality check remains available in the separate
            # capture-only diagnostic, but is not allowed to turn the
            # controller replay into a host-memory transfer benchmark.
            # Leave the polling loop at a complete frame boundary.  Mesen's
            # screenshot service samples the native framebuffer asynchronously
            # relative to the MCP transaction; one quiet frame prevents a
            # just-committed surface from being captured during that seam.
            advance_safe(session, 1)
            return
        # The mode-3 backend converts a bounded tile budget per frame.  Move
        # in safe 32-frame batches while polling; one-frame MCP transactions
        # make a legitimate conversion look like a validator hang.
        advance_safe(session, 32)
    print("native display timeout:", {
        "cpu": session.get_cpu_state("Snes"),
        "ppu": session.get_ppu_state(),
        "reset_diag": list(session.read_memory("snesMemory", 0x7E1020, 0x20)),
        "scene": read_scene(session),
        "surface": list(session.read_memory("snesMemory", 0x401080, 0x34)),
        "backend": list(session.read_memory("snesMemory", 0x401000, 0x40)),
        "backend_work": list(session.read_memory("snesMemory", 0x41E750, 0xB0)),
        "events": list(session.read_memory("snesMemory", 0x7E2000, 0x06)),
        "overlay": list(session.read_memory("snesMemory", 0x41F614, 0x20)),
                "service_diag": list(session.read_memory("snesMemory", 0x7E5FB0, 0x2E)),
        "scenario_error": list(session.read_memory("snesMemory", 0x7E5F20, 0x20)),
        "scumm_error": list(session.read_memory("snesMemory", 0x7E2300, 0x10)),
        "service_progress": read_service_progress(session),
        "fifo_snapshot": read_event_fifo(session),
    }, flush=True)
    try:
        trace = session.tool("trace_log", {"count": 1000, "cpuType": "Snes"})
        (ROOT / "build/controller-room42-last-timeout-trace.json").write_text(
            json.dumps(trace, indent=2) + "\n")
    except Exception as exc:
        print("native timeout trace unavailable:", exc, flush=True)
    raise RuntimeError("native display did not converge before capture")


def read_event_fifo(session) -> dict:
    """Decode the live FIFO without treating stale packet slots as queued."""
    state = bytes(session.read_memory("snesMemory", 0x7E2000, 6))
    head = int.from_bytes(state[0:2], "little")
    tail = int.from_bytes(state[2:4], "little")
    count = int.from_bytes(state[4:6], "little")
    packets = []
    for n in range(min(count, 16)):
        index = (head + n) & 0x0F
        raw = bytes(session.read_memory("snesMemory", 0x7E2100 + index * 0x10, 0x10))
        packets.append({
            "index": index,
            "service": raw[0], "opcode": raw[1], "flags": raw[2],
            "source": raw[3], "destination": raw[4],
            "arg0": int.from_bytes(raw[6:8], "little"),
            "arg1": int.from_bytes(raw[8:10], "little"),
            "arg2": int.from_bytes(raw[10:12], "little"),
            "sequence": int.from_bytes(raw[12:14], "little"),
        })
    return {"head": head, "tail": tail, "count": count, "packets": packets}


def read_service_progress(session) -> dict:
    """Read only service-owned progress and the existing engine frame guard."""
    # Read through the legacy backend-stage byte as well.  It is outside the
    # 0x30-byte diagnostic prefix and is retained only for old reports; do not
    # use it as a service-progress counter because that address is shared with
    # the controller mode in current layouts.
    # SAME_VIDEO_DIAG_BASE=$7E5E90; the former $7E5FB0 read was an obsolete
    # map and made service progress appear unrelated or frozen.
    diag = bytes(session.read_memory("snesMemory", 0x7E5E90, 0x31))
    backend = bytes(session.read_memory("snesMemory", 0x401000, 0x40))
    engine = bytes(session.read_memory("snesMemory", 0x7E2220, 0x12))
    def w(offset):
        return int.from_bytes(diag[offset:offset + 2], "little")
    return {
        "nmi": int.from_bytes(session.read_memory("snesMemory", 0x7E102E, 2), "little"),
        "frame_counter": int.from_bytes(session.read_memory("snesMemory", 0x7E2210, 2), "little"),
        "logical_frame_count": int.from_bytes(session.read_memory("snesMemory", 0x7E2308, 2), "little"),
        "engine_frame_busy": engine[0x11],
        "engine_lifecycle": engine[1],
        "engine_phase": session.read_memory("snesMemory", 0x7E103C, 1)[0],
        "kernel_entries": w(0x26),
        "kernel_pops": w(0x28),
        "kernel_last_service": diag[0x2A],
        "kernel_last_opcode": diag[0x2B],
        "backend_steps": w(0x2C),
        "backend_stage": diag[0x30],
        "backend_state": backend[0x13],
        "backend_locked": backend[0x14],
        "accepted_present": int.from_bytes(backend[0x1A:0x1C], "little"),
        "rejected_present": int.from_bytes(backend[0x1C:0x1E], "little"),
    }


def read_presentation_binding(session) -> dict:
    """Snapshot the service/backend generation carrying the current pixels.

    This is deliberately validator-side observation.  The engine exposes only
    the pixel-space damage contract; backend state is read here to bind a
    capture to a committed presentation, not to steer production execution.
    """
    surface = bytes(session.read_memory("snesMemory", 0x401080, 0x40))
    backend = bytes(session.read_memory("snesMemory", 0x401000, 0x40))
    fifo = read_event_fifo(session)
    return {
        "surface_room": surface[0],
        "surface_generation": int.from_bytes(surface[2:4], "little"),
        "surface_status": surface[4],
        "surface_next_generation": int.from_bytes(surface[0x1C:0x1E], "little"),
        "surface_pending_visual": surface[0x26],
        "surface_projection": {
            "width": int.from_bytes(surface[0x06:0x08], "little"),
            "height": int.from_bytes(surface[0x08:0x0A], "little"),
            "pitch": int.from_bytes(surface[0x0A:0x0C], "little"),
            "source_x": int.from_bytes(surface[0x0C:0x0E], "little"),
            "source_y": int.from_bytes(surface[0x0E:0x10], "little"),
            "dest_x": int.from_bytes(surface[0x10:0x12], "little"),
            "dest_y": int.from_bytes(surface[0x12:0x14], "little"),
        },
        "damage": {
            "x": int.from_bytes(surface[0x34:0x36], "little"),
            "y": int.from_bytes(surface[0x36:0x38], "little"),
            "width": int.from_bytes(surface[0x38:0x3A], "little"),
            "height": int.from_bytes(surface[0x3A:0x3C], "little"),
        },
        "backend_state": backend[0x13],
        "backend_locked": backend[0x14],
        "backend_pending_generation": int.from_bytes(backend[0x0E:0x10], "little"),
        "backend_committed_generation": int.from_bytes(backend[0x10:0x12], "little"),
        "backend_candidate_tiles": int.from_bytes(backend[0x22:0x24], "little"),
        "backend_pending_tiles": int.from_bytes(backend[0x24:0x26], "little"),
        "backend_inflight_tiles": int.from_bytes(backend[0x26:0x28], "little"),
        "accepted_present": int.from_bytes(backend[0x1A:0x1C], "little"),
        "rejected_present": int.from_bytes(backend[0x1C:0x1E], "little"),
        "event_count": fifo["count"],
        "event_head": fifo["head"],
        "event_tail": fifo["tail"],
    }


def capture_native(session, path: Path, *, min_overlay_generation: int | None = None,
                   wait_for_quiet: bool = True,
                   sample_current_frame: bool = False) -> None:
    if not CAPTURE_NATIVE_ENABLED:
        return
    """Capture an emulator framebuffer with a source-stage landmark check.

    A Mesen screenshot can race the final PPU commit and return an all-black
    frame even after the backend counters are idle.  Retry only at complete
    frame boundaries, and compare an unaffected harbor crop against the
    previously inspected native room-42 baseline.  This is an emulator-frame
    check, not a host-rendered replacement or a generic nonblack test.
    """
    # Use the inspected full-room native capture as the landmark reference.
    # The older visualfix9 image has a large empty/letterboxed left region;
    # comparing only that crop allowed black partial frames to pass.
    reference_path = ROOT / "build/controller-room42-visualfix26-run1/01-ready.png"
    reference = Image.open(reference_path).convert("RGB") if reference_path.is_file() else None
    last = None
    # Publication and native presentation have separate lifetimes.  A PRESENT
    # packet being accepted only means that the backend has started converting
    # the indexed surface; the SNES planes are not valid evidence until the
    # bounded conversion/DMA turn has completed.  Keep this wait in the
    # validator rather than teaching SCUMM about backend state.
    if wait_for_quiet:
        settle_native_capture(session, frames=2048)
    # A hide/show layer is a normal queued presentation transaction.  The
    # room path usually settles in a few iterations, but a talk completion
    # can follow a committed surface and require the full backend/DMA turn.
    # Keep polling at safe frame boundaries instead of treating that latency
    # as a missing capture.
    for _ in range(300):
        overlay = session.read_memory("snesMemory", 0x41F614, 0x20)
        overlay_state = overlay[0]
        overlay_generation = int.from_bytes(overlay[2:4], "little")
        overlay_committed = int.from_bytes(overlay[6:8], "little")
        # A visible overlay is legitimately left in the backend's in-flight
        # state while its BG2 realization remains active.  Requiring the
        # state byte to return to IDLE made HUD captures wait forever after
        # the text service was correctly enabled.  The screenshot landmark
        # below is the actual display proof; only an unpublished generation
        # or an explicitly requested minimum generation blocks sampling.
        if ((min_overlay_generation is not None
             and overlay_generation < min_overlay_generation)
                or (overlay_state != 0 and overlay_generation == 0)):
            advance_safe(session, 8)
            continue
        if not (sample_current_frame and last is None):
            advance_safe(session, 1)
        raw = base64.b64decode(session.take_screenshot(format="base64")["base64"])
        image = Image.open(BytesIO(raw)).convert("RGB")
        last = raw
        if reference is None:
            path.write_bytes(raw)
            return
        # Compare the complete displayed gameplay viewport, excluding only
        # the 40-pixel top letterbox and the bottom border.  The previous
        # left-side crop was empty in the reference and admitted black
        # partial frames as false visual evidence.
        landmark = (0, 40, 256, 184)
        crop = ImageChops.difference(image.crop(landmark),
                                     reference.crop(landmark))
        mean = ImageStat.Stat(crop).mean
        if max(mean) < 12.0:
            path.write_bytes(raw)
            return
    if last is None:
        raise RuntimeError(
            f"native capture did not reach a committed frame: {path}; "
            f"overlay={list(session.read_memory('snesMemory', 0x41F614, 0x20))}")
    path.write_bytes(last)
    print("native capture ppu:", session.get_ppu_state(), flush=True)
    print("native capture reset diag:", list(session.read_memory("snesMemory", 0x7E1020, 0x20)), flush=True)
    print("native capture surface:", list(session.read_memory("snesMemory", 0x401080, 0x34)), flush=True)
    print("native capture backend:", list(session.read_memory("snesMemory", 0x401000, 0x40)), flush=True)
    raise RuntimeError(f"native capture did not match the inspected room-42 landmark: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "build/controller-room42.sfc")
    parser.add_argument("--output", type=Path, default=ROOT / "build/controller-room42-run")
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44331)
    parser.add_argument("--startup-frames", type=int, default=5000)
    parser.add_argument("--capture-only", action="store_true",
                        help="stop at the stable visible room-42 checkpoint")
    parser.add_argument("--no-native-captures", action="store_true",
                        help="diagnostic mode: run the real controller path without emulator screenshots")
    parser.add_argument("--fast-observation-input", action="store_true",
                        help="diagnostic mode: use short real input holds to reduce MCP observation latency")
    args = parser.parse_args()
    global CAPTURE_NATIVE_ENABLED, INPUT_HOLD_FRAMES
    CAPTURE_NATIVE_ENABLED = not args.no_native_captures
    if args.fast_observation_input:
        INPUT_HOLD_FRAMES = 8
    args.output.mkdir(parents=True, exist_ok=True)
    require(args.rom.is_file(), f"missing ROM: {args.rom}")
    require(args.nexen.is_file(), f"missing Nexen: {args.nexen}")
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    events: list[dict[str, object]] = []
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        # Hook-fenced conversion can span the bounded backend budget without
        # being an observation failure.  This only enlarges the debugger
        # transaction timeout; production timing is unchanged.
        port=args.port, boot_wait=2.0, socket_timeout=600.0,
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
        # Fixture-only success witnesses.  The actor serial is written last
        # by the production compositor, so a write hook is an exact boundary
        # for a completed actor publication.  The backend generation hook
        # is installed only after the moving witness, so ordinary startup
        # commits cannot flood the observer.
        # Hook the post-success validity byte rather than the final serial
        # word.  The emulator's WRAM write notification does not reliably
        # report the two-byte long store at the serial address; VALID is
        # written after every witness field and immediately before serial.
        # The production witness publishes its fields first, marks the record
        # valid, and increments SERIAL last.  Fence on SERIAL so the debugger
        # observes the complete record rather than stopping between VALID and
        # the final publication store.
        actor_publication_hook = session.add_write_hook(0x7E5E52)
        # A moving render may be deferred behind the hover PRESENT.  Fence
        # that already-accepted generation by its backend state transition;
        # this is a service boundary, not a production wait.
        backend_idle_hook = session.add_write_hook(
            0x401013, match_value=1, match_value_mask=0xFF)
        started = False
        title_ack = False
        start_release = None
        ready = 0
        last_room = None
        last_start_edge = -10_000
        # Startup title input is a real one-frame controller boundary.  Do not
        # batch this observation window: room 75 can be installed and consumed
        # between two eight-frame samples, which loses the START edge while
        # leaving the production lifecycle healthy.
        for frame in range(1, args.startup_frames):
            if frame % 400 == 1:
                print(f"controller frame {frame}", flush=True)
            pre = read_startup_gate(session)
            if (pre["room"], pre["phase"], pre["error"]) != last_room:
                print(f"transition frame {frame}: {pre}", flush=True)
                last_room = (pre["room"], pre["phase"], pre["error"])
            # Some current startup profiles expose room 68 as the interactive
            # title/input boundary before the authored 68 -> 75 handoff;
            # accepting either room keeps this controller replay on the real
            # input path instead of depending on an observation of the brief
            # intermediate room-75 install.
            if (not started and pre["room"] in (68, 75) and pre["phase"] in (0, 2)):
                # The current headless presentation keeps the authored title
                # message logically alive.  START enters the title boundary;
                # A is the normal controller acknowledgement for that
                # visible message, and neither path writes SCUMM state.
                session.set_input(session.BTN_START | session.BTN_A, 40)
                started = True
                start_release = frame + 40
                last_start_edge = frame
            elif (started and pre["room"] in (68, 75)
                  and frame - last_start_edge >= 32
                  and frame < 180):
                # Some title profiles expose the room-68 phase boundary one
                # frame before the authored input consumer is alive.  A
                # bounded repeat of the same real controller edge preserves
                # the input path without writing a room/mailbox state or
                # selecting the target room from the validator.
                session.set_input(session.BTN_START | session.BTN_A, 40)
                start_release = frame + 40
                last_start_edge = frame
            elif (started and not title_ack and pre["room"] == 68
                  and pre["talk_active"]):
                # The title script may begin its logical message after the
                # START edge has been released.  Acknowledge that authored
                # message with a second real controller edge; do not clear
                # talk state or construct a sentence in the validator.
                session.set_input(session.BTN_A, 2)
                title_ack = True
            elif start_release is not None and frame >= start_release:
                session.set_input(0, 1)
                start_release = None
            step(session)
            post = read_startup_gate(session)
            if post["room"] == 42 and frame >= 225:
                if frame % 100 == 0 or post["error"]:
                    detailed = read_ready(session)
                    print("room42 frame %d: room=%d phase=%d walkbox=%d "
                          "cutscene=%d c20=%d pending=%d err=%d" %
                          (frame, detailed["room"], detailed["phase"],
                           detailed["walkbox"], detailed["cutscene"],
                           detailed["c20"], detailed["pending"],
                           detailed["error"]), flush=True)
                    post = {**post, **detailed}
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
                    and post["talk_active"] == 0):
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
        for visual_poll in range(300):
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
                    and event_count == 0):
                visual_ready = True
                break
            advance_safe(session, 8)
        if not visual_ready:
            control_events = session.drain_notifications(timeout=0.2)
            control_events = [
                e for e in control_events
                if e.get("method") == "notifications/mesen/hookFired"
            ]
            print("host control-flow hooks:", control_events[-24:], flush=True)
            print("visual wait CPU:", session.get_cpu_state("Snes"), flush=True)
            print("visual wait SA1:", session.get_cpu_state("Sa1"), flush=True)
            print("visual service diagnostics:", list(session.read_memory("snesMemory", 0x7E5FB0, 0x28)), flush=True)
            print("backend control:", list(session.read_memory("snesMemory", 0x401000, 0x40)), flush=True)
            print("event state:", list(session.read_memory("snesMemory", 0x7E2000, 0x10)), flush=True)
            print("event buffer services/opcodes:", [
                list(session.read_memory("snesMemory", 0x7E2100 + i * 0x10, 3))
                for i in range(16)
            ], flush=True)
        require(visual_ready, f"room-42 visual publication was not reached; state={list(surface_state)}")
        events.append({"stage": "visual_ready", "state": read_scene(session)})
        print("native stage: ready checkpoint", flush=True)
        advance_safe(session, 32)
        # The ready gate proves that a PRESENT was accepted and its FIFO was
        # drained; it does not promise that an incremental backend conversion
        # has already reached idle.  Fence that existing conversion before
        # sending cursor input so the observation path cannot hold the input
        # bridge behind a busy presentation.
        if read_scene(session)["mode3_state"] != 1:
            wait_for_backend_idle(session, backend_idle_hook)
        print("native stage: ready settled", read_scene(session), flush=True)
        capture_native(session, args.output / "01-ready.png")
        capture_mode3_surface(session, args.output / "01-ready-surface.ppm",
                              advance_after=False)
        if args.capture_only:
            capture_mode3_surface(session, args.output / "01-ready-surface.ppm")
            tilemap = session.tool("render_tilemap", {"layer": 5, "scale": 1, "format": "base64"})
            (args.output / "01-ready-main.png").write_bytes(base64.b64decode(tilemap["base64"]))
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
                "service_progress": read_service_progress(session),
                "fifo_snapshot": read_event_fifo(session),
                "dma_state": list(session.read_memory("snesMemory", 0x7E223A, 0x2E)),
                "nmi_count": int.from_bytes(session.read_memory("snesMemory", 0x7E102E, 2), "little"),
                "vram_prefix": list(session.read_memory("snesVideoRam", 0, 64)),
            }, indent=2) + "\n")
            return 0

        # Resolve the regression object's source CDHD record from the active
        # room table, then move the cursor with ordinary controller edges.
        # The object id identifies the regression action; its rectangle and
        # center are never duplicated in the controller or validator.
        locker_x, locker_y, locker_record = object_center_from_source_records(session, 490)
        locker_left = locker_record["x"]
        locker_right = locker_left + locker_record["width"]
        locker_top = locker_record["y"]
        locker_bottom = locker_top + locker_record["height"]
        cursor_trace = []
        # Cursor motion is a normal controller path; allow for the real
        # two-pixel edge steps and occasional frame where the input edge is
        # sampled while the presentation service is busy.
        for _ in range(128):
            # Keep this polling path narrow: a complete scene snapshot here
            # would issue dozens of MCP memory reads for every two-frame tap.
            cursor_x = u16(session.read_memory("snesMemory", 0x7E5FE1, 2))
            cursor_y = u16(session.read_memory("snesMemory", 0x7E5FE3, 2))
            # Controller coordinates are screen-relative.  The production
            # hit-test converts them to room/world coordinates using the
            # active camera projection, so the validator makes the same
            # conversion instead of comparing the two coordinate spaces.
            room_x = cursor_x + u16(session.read_memory("snesMemory", 0x7E7FB8, 2))
            room_y = (cursor_y + u16(session.read_memory("snesMemory", 0x7E7FAA, 2)) - 0x64) & 0xFFFF
            if locker_left <= room_x < locker_right and locker_top <= room_y < locker_bottom:
                break
            target_x = locker_x - u16(session.read_memory("snesMemory", 0x7E7FB8, 2))
            target_y = locker_y - u16(session.read_memory("snesMemory", 0x7E7FAA, 2)) + 0x64
            if cursor_x < target_x:
                button = session.BTN_RIGHT
            elif cursor_x > target_x:
                button = session.BTN_LEFT
            elif cursor_y < target_y:
                button = session.BTN_DOWN
            else:
                button = session.BTN_UP
            before_x = cursor_x
            tap(session, button)
            after_x = u16(session.read_memory("snesMemory", 0x7E5FE1, 2))
            if len(cursor_trace) < 12:
                cursor_trace.append({
                    "before": before_x,
                    "after": after_x,
                    "button": button,
                    "held": u16(session.read_memory("snesMemory", 0x7E2200, 2)),
                    "pressed": u16(session.read_memory("snesMemory", 0x7E2204, 2)),
                    "mode": session.read_memory("snesMemory", 0x7E5FE0, 1)[0],
                })
        final_cursor_x = u16(session.read_memory("snesMemory", 0x7E5FE1, 2))
        final_cursor_y = u16(session.read_memory("snesMemory", 0x7E5FE3, 2))
        final_room_x = final_cursor_x + u16(session.read_memory("snesMemory", 0x7E7FB8, 2))
        final_room_y = (final_cursor_y + u16(session.read_memory("snesMemory", 0x7E7FAA, 2)) - 0x64) & 0xFFFF
        if not (locker_left <= final_room_x < locker_right and locker_top <= final_room_y < locker_bottom):
            print("controller input at hover failure:", {
                "cursor": (final_cursor_x, final_cursor_y),
                "room_point": (final_room_x, final_room_y),
                "held": u16(session.read_memory("snesMemory", 0x7E2200, 2)),
                "pressed": u16(session.read_memory("snesMemory", 0x7E2204, 2)),
                "diag_input": session.read_memory("snesMemory", 0x7E5FEF, 1)[0],
                "diag": session.read_memory("snesMemory", 0x7E5FEC, 4).hex(),
                "active_objects": active_room_objects(session),
                "interaction_scratch": list(session.read_memory("snesMemory", 0x7E5F90, 13)),
                "raw_pressed": list(session.read_memory("snesMemory", 0x7E5F8E, 2)),
                "cursor_trace": cursor_trace,
            }, flush=True)
        require(
            locker_left <= final_room_x < locker_right
            and locker_top <= final_room_y < locker_bottom,
            f"controller cursor did not reach source object 490 bounds: "
            f"screen=({final_cursor_x},{final_cursor_y}) room=({final_room_x},{final_room_y}) record={locker_record}",
        )
        print("native stage: locker hover", flush=True)
        events.append({"stage": "locker_hover", "frame": frame, "state": read_scene(session)})
        if CAPTURE_NATIVE_ENABLED:
            advance_safe(session, 32)
            advance_until(session, lambda s: s["scumm_stack_pointer"] == 0,
                          128, "settled SCUMM scheduler stack")
            # Cursor/HUD movement can leave a presentation conversion in
            # flight. The visual run waits for it; the hook-driven run does
            # not need an unrelated hover screenshot boundary.
            advance_until(
                session,
                lambda s: (s["mode3_state"] == 1
                           and s["mode3_event_count"] == 0),
                2048, "settled video presentation",
            )
        elif read_scene(session)["mode3_state"] != 1:
            # The hook-driven fidelity run must enter the controller only
            # after the room PRESENT has committed.  Otherwise the authored
            # walk can finish while that initial full-room conversion is
            # still in flight, leaving no writable surface for its moving
            # publication.  This is an observation fence, not a gameplay
            # delay or production wait.
            wait_for_backend_idle(session, backend_idle_hook)
        print("native stage: hover settled", read_scene(session), flush=True)
        capture_native(session, args.output / "02-hover.png")
        global RESTORE_DEBUG_HOOK
        RESTORE_DEBUG_HOOK = session.add_exec_hook(0x14863B)
        overlay_before_dialogue = int.from_bytes(
            session.read_memory("snesMemory", 0x41F616, 2), "little")
        tap(session, session.BTN_A)
        events.append({"stage": "object_selected", "state": advance_until(
            session, lambda s: s["mode"] == 1, 32, "object-selection mode")})
        tap(session, session.BTN_Y)
        events.append({"stage": "verb_selected", "state": advance_until(
            session, lambda s: s["mode"] == 1, 32, "verb-selection mode")})
        # Object/verb HUD selection can publish its own presentation.  Fence
        # that already-accepted conversion before submitting Open so the
        # authored movement's first actor damage request is not rejected by a
        # still-busy surface.  This is debugger-side observation fencing only;
        # production movement and presentation timing are unchanged.
        if read_scene(session)["mode3_state"] != 1:
            wait_for_backend_idle(session, backend_idle_hook)
        # Snapshot before submission: the first moving publication can occur
        # while the sentence-consumed wait observes movement becoming active.
        baseline_witness = read_publication_witness(session)["serial"]
        # The authored sentence/mailbox boundary is sampled asynchronously;
        # retain the established long A edge for submission.  The walking
        # evidence is captured by frame-boundary observation after the
        # sentence is consumed, not by shortening the production input edge.
        # Arm this only at the sentence boundary: standing snapshots emitted
        # during hover/verb selection must not leave stale notifications in
        # the debugger queue.  desired_visible is the final field written by
        # the semantic publisher; hooking desired_select would observe a
        # partially written snapshot.
        semantic_moving_hook = session.add_write_hook(
            0x7E5E4D, match_value=1, match_value_mask=0xFF)
        action_tap(session, session.BTN_A)
        semantic_snapshot = wait_for_semantic_moving_snapshot(
            session, semantic_moving_hook)
        open_state = read_scene(session)
        if not open_state["moving1"]:
            raise RuntimeError(
                f"semantic moving snapshot fired without authored movement: {open_state}")
        events.append({"stage": "open_submitted", "state": open_state})
        events.append({"stage": "semantic_moving_snapshot",
                       "state": semantic_snapshot})
        print("semantic moving boundary diagnostics:", {
            "scene": read_scene(session),
            "surface_pending_visual": session.read_memory("snesMemory", 0x4010A6, 1)[0],
            "surface_pending_room": session.read_memory("snesMemory", 0x4010A7, 1)[0],
            "surface_pending_generation": u16(session.read_memory("snesMemory", 0x4010A8, 2)),
            "surface_presented_source_x": u16(session.read_memory("snesMemory", 0x4010A4, 2)),
            "camera_present_count": u16(session.read_memory("snesMemory", 0x4010AC, 2)),
            "camera_defer_count": u16(session.read_memory("snesMemory", 0x4010B0, 2)),
            "camera_stale_count": u16(session.read_memory("snesMemory", 0x4010B2, 2)),
        }, flush=True)
        print("controller open sequence:", events[-4:], flush=True)
        # The witness hook, not a repeated logical-frame poll, identifies the
        # first successful in-flight actor publication.  Standing publishes
        # are ignored; failed PRESENTs never advance the witness serial.
        # Snapshot before submitting the sentence.  The first movement frame
        # may publish and increment the witness while the sentence-consumed
        # wait below is still returning; sampling afterward would erase the
        # very event the hook is meant to catch.
        walking_witness = wait_for_moving_publication(
            session, actor_publication_hook, baseline_witness)
        walking_state = read_scene(session)
        events.append({"stage": "walking_intermediate", "state": walking_state,
                       "publication_witness": walking_witness})
        backend_commit_hook = session.add_write_hook(0x401010, 0x401011)
        walking_commit = wait_for_committed_generation(
            session, backend_commit_hook, walking_witness["present_generation"])
        # The committed-generation write can precede the normal state=idle
        # transition by a bounded backend step.  Keep those observations
        # separate: generation identity is already fenced, and the idle
        # hook below only establishes that the committed transaction is no
        # longer locked before capture.
        session.remove_hook(backend_commit_hook)
        if walking_commit["backend_state"] != 1 or walking_commit["backend_locked"]:
            wait_for_backend_idle(session, backend_idle_hook)
        walking_binding = read_presentation_binding(session)
        walking_binding["publication_witness"] = walking_witness
        walking_binding["commit_witness"] = walking_commit
        # No logical frame is advanced between the exact backend completion
        # hook and these two captures.
        capture_native_current(session, args.output / "03-walking.png")
        # Keep the indexed surface from the same no-advance boundary as the
        # native screenshot.  This is intermediate evidence: it binds the
        # actor pixels to the committed generation without making the native
        # capture depend on a host-rendered replacement.
        projection = walking_binding["surface_projection"]
        witness = walking_witness
        surface_x = witness["x"] - 16 + projection["dest_x"] - projection["source_x"]
        surface_y = witness["y"] - 55 + projection["dest_y"] - projection["source_y"]
        # The active room surface is 144 pixels high; retain the visible
        # portion of the 32x64 actor canvas when its feet extend below it.
        surface_region = (surface_x, surface_y, 32,
                          min(64, projection["height"] - surface_y))
        surface_capture = capture_mode3_surface(
            session, args.output / "03-walking-surface.ppm",
            region=surface_region, advance_after=False)
        walking_presentation = {"stage": "walking_presentation",
                                "state": read_scene(session),
                                "presentation": walking_binding,
                                "surface_region": surface_region,
                                "surface_descriptor_capture": surface_capture}
        if CAPTURE_NATIVE_ENABLED:
            walking_presentation["surface_capture"] = {
                "path": str(args.output / "03-walking-surface.ppm"),
                "sha256": hashlib.sha256(
                    (args.output / "03-walking-surface.ppm").read_bytes()
                ).hexdigest(),
            }
        events.append(walking_presentation)
        for _ in range(24):
            advance_safe(session, 16)
            state = read_locker_progress(session)
            if state["object490_state"] == 1 and state["walkbox"] != 0 and state["actor_x"] == 218:
                break
        require(state["object490_state"] == 1, f"locker did not open through controller sentence: {state}")
        events.append({"stage": "opened", "state": state})
        print("native stage: locker opened", state, flush=True)
        # Keep the inspection input in the same authored room/session.  The
        # live actor redraw can keep the backend non-idle while it is still a
        # valid native frame, so observe a bounded conversion window and let
        # the screenshot landmark check decide when the committed frame is
        # visible instead of waiting for perpetual backend quiescence.
        advance_safe(session, 128)
        capture_native(session, args.output / "03-opened.png", wait_for_quiet=False)
        require(read_scene(session)["room"] == 42,
                "room changed before controller inspection input")
        # A full-surface actor redraw can still be converting after the
        # authored locker state has settled.  This is an observation window,
        # not a production wait: keep stepping complete frames until the
        # target-neutral text service can hand the HUD back.
        for _ in range(600):
            if read_scene(session)["mode"] == 3:
                break
            advance_safe(session, 1)
        if read_scene(session)["mode"] != 3:
            print("controller inspect handoff timeout:", {
                "scene": read_scene(session),
                "backend": list(session.read_memory("snesMemory", 0x401000, 0x40)),
                "overlay": list(session.read_memory("snesMemory", 0x41F614, 0x20)),
                "events": list(session.read_memory("snesMemory", 0x7E2000, 0x06)),
                "service_progress": read_service_progress(session),
            }, flush=True)
        require(read_scene(session)["mode"] == 3,
                "controller did not publish the authored inspect mode after opening")
        action_tap(session, session.BTN_A)
        events.append({"stage": "inspect_submitted", "state": read_scene(session)})
        print("native stage: inspect submitted", events[-1]["state"], flush=True)
        print("inspect boundary diagnostics", {
            "cpu": session.get_cpu_state("Snes"),
            "reset_diag": list(session.read_memory("snesMemory", 0x7E1020, 0x20)),
            "events": list(session.read_memory("snesMemory", 0x7E2000, 0x06)),
            "service_diag": list(session.read_memory("snesMemory", 0x7E5FB0, 0x32)),
            "backend": list(session.read_memory("snesMemory", 0x401000, 0x40)),
            "surface": list(session.read_memory("snesMemory", 0x401080, 0x34)),
        }, flush=True)
        try:
            trace = session.trace_log(200)
            (args.output / "inspect-boundary-trace.json").write_text(
                json.dumps(trace, indent=2) + "\n")
        except Exception as exc:
            print("inspect boundary trace unavailable:", exc, flush=True)
        message_seen = False
        dialogue_captured = False
        # Encoded text controls can own a substantial authored delay before
        # the printable continuation segment is exposed.  Continue sampling
        # the real active message rather than declaring the two-glyph control
        # prefix to be the complete dialogue.
        for _ in range(300):
            # Inspection text can be shorter than a 16-frame observation
            # batch.  Keep the real controller/message lifecycle intact and
            # sample at a two-frame boundary so the active presentation is
            # captured rather than skipped.
            advance_safe(session, 2)
            current = read_locker_progress(session)
            talk = session.read_memory("snesMemory", 0x7E7A20, 2)
            message_seen |= bool(talk[0] or talk[1])
            # The first logical segment is the encoded control prefix and can
            # contain only two visible glyphs.  Capture once the authored
            # continuation has exposed a substantive printable segment, while
            # the message is still active.
            talk_scene = read_scene(session) if message_seen and not dialogue_captured else None
            if (talk_scene is not None and talk_scene["talk_active"]
                    and talk_scene["talk_segment_length"] >= 8):
                # Do not wait a full room conversion here: that would cross
                # the authored message delay and capture the post-dialogue
                # HUD instead of the live talk layer. capture_native waits
                # only for the overlay generation to commit.
                capture_native(
                    session, args.output / "04-dialogue-active.png",
                    min_overlay_generation=overlay_before_dialogue + 1,
                    wait_for_quiet=False,
                )
                visual_state = read_scene(session)
                require(visual_state["overlay_pixels_nonzero"] > 0,
                        "native dialogue overlay committed with no glyph pixels")
                dialogue_captured = True
            if message_seen and not talk[0] and current["error"] == 0:
                break
        require(message_seen, "inspection dialogue never became logically active")
        require(dialogue_captured, "inspection dialogue was not captured while active")
        require(current["error"] == 0, f"SCUMM error after inspection: {current}")
        events.append({"stage": "inspection_complete", "state": current})
        capture_native(session, args.output / "04-dialogue-complete.png")
        # Genericity witness: after the locker path has completed, select a
        # different source object from its own CDHD rectangle.  Stop at the
        # object-selection mode; do not submit its authored verb or mutate
        # the Fate scenario a second time.
        second_record, second_room_x, second_room_y = move_cursor_to_source_object(session, 492)
        action_tap(session, session.BTN_A)
        second_state = advance_until(
            session,
            lambda s: s["mode"] == 1,
            128,
            "second source object selection",
        )
        second_scene = read_scene(session)
        require(second_scene["object"] == 492,
                f"second CDHD object selection resolved incorrectly: {second_scene}")
        events.append({"stage": "second_object_selected", "state": second_state,
                       "scene": second_scene,
                       "source_record": second_record,
                       "room_point": [second_room_x, second_room_y]})
        # Prove that the real controller path remains live after the authored
        # message releases its wait.  This is an ordinary input edge, not a
        # sentence/mailbox injection, and must produce a fresh HUD layer.
        cursor_before = u16(session.read_memory("snesMemory", 0x7E5FE1, 2))
        tap(session, session.BTN_RIGHT)
        advance_safe(session, 2)
        post_dialogue = read_scene(session)
        print("post-dialogue input boundary:", {
            "cursor_before": cursor_before,
            "cursor_after": post_dialogue["cursor_x"],
            "mode": post_dialogue["mode"],
            "talk_active": post_dialogue["talk_active"],
            "input_held": post_dialogue["input_held"],
            "input_pressed": post_dialogue["input_pressed"],
            "controller_diag": post_dialogue["controller_diag"],
            "hud_dirty": post_dialogue["hud_dirty"],
            "stack": post_dialogue["scumm_stack_pointer"],
            "c20": post_dialogue["c20"],
            "pending": post_dialogue["sentence_api_pending"],
        }, flush=True)
        require(not post_dialogue["talk_active"],
                "dialogue remained logically active after completion boundary")
        require(post_dialogue["cursor_x"] > cursor_before,
                "controller input did not remain usable after dialogue")
        advance_safe(session, 32)
        capture_native(session, args.output / "05-post-dialogue.png")
    report = {
        "result": "pass", "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "build_identity": build_identity_for(args.rom),
        "events": events, "controller_only": True,
        "visual_record": "build/m25a-validator/startup42/room42/room-42.sc5v",
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
