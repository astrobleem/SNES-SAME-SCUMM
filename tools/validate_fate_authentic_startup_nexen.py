#!/usr/bin/env python3
"""Cold-trace authentic Fate startup with ROM-bound native breakpoints.

The diagnostic root schedules the source-authentic boot global as an ordinary
top-level C4 activation in the resource-less room-zero startup state. It does
not install a synthetic room or rewrite game state from the debugger. Gameplay
rooms and original script bodies come from the external cooked-resource
profile. This tool records CPU execution and read-only WRAM snapshots only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RESET_DIAG_BASE = 0x7FF46B
NEXEN_DEFAULT = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
sys.path.insert(0, str(ROOT / "tools"))
from fate_replay import (  # noqa: E402
    ControllerInputLease,
    activation_observation,
    advance_bounded,
    next_input_safe_window,
)
from validate_scumm_startup42_nexen import (  # noqa: E402
    mapped_cpu_address_for_rom,
    verified_symbol_map_for_rom,
)

ROOM_BLOCK = 0x7FF2BE
COMMON = 0x7E2300
SLOT_STATUS = 0x7E2380
SLOT_NUMBER = 0x7E2399
SLOT_PROGRAM = 0x7E23B2
SLOT_PC = 0x7E23E4
SLOT_OWNER = 0x7FF2E7
SLOT_WHERE = 0x7E7F46
SLOT_COUNT = 25
# This cold-start diagnostic uses the compact SCUMM bootstrap profile
# (PHASE6HB/PHASE6LA1D are false), so VAR_EGO lives at variables[1] in the
# legacy table rooted at $7E2320. The authored full-MAXS builds select a
# different table and must use their own generated profile identity.
STARTUP_VAR_EGO = 0x7E2322


def u16(raw: bytes, offset: int = 0) -> int:
    return int.from_bytes(raw[offset:offset + 2], "little")


def snapshot(session) -> dict[str, object]:
    room = session.read_memory("snesMemory", ROOM_BLOCK, 0x42)
    common = session.read_memory("snesMemory", COMMON, 0x64)
    statuses = session.read_memory("snesMemory", SLOT_STATUS, SLOT_COUNT)
    numbers = session.read_memory("snesMemory", SLOT_NUMBER, SLOT_COUNT)
    programs = session.read_memory("snesMemory", SLOT_PROGRAM, SLOT_COUNT)
    pcs = session.read_memory("snesMemory", SLOT_PC, SLOT_COUNT * 2)
    owners = session.read_memory("snesMemory", SLOT_OWNER, SLOT_COUNT)
    where = session.read_memory("snesMemory", SLOT_WHERE, SLOT_COUNT)
    actor1 = session.read_memory("snesMemory", 0x7F3700, 64)
    ego_position = session.read_memory("snesMemory", 0x7FF1A4, 4)
    controller = session.read_memory("snesMemory", 0x7E5FE0, 10)
    live = []
    for slot in range(SLOT_COUNT):
        if statuses[slot] or numbers[slot] or programs[slot]:
            live.append({
                "slot": slot,
                "status": statuses[slot],
                "script": numbers[slot],
                "program": programs[slot],
                "pc": u16(pcs, slot * 2),
                "room_owner": owners[slot],
                "where": where[slot],
            })
    return {
        "frame": session.get_state()["frameCount"],
        "room": room[1],
        "active_record": room[0],
        "pending_room": room[3],
        "phase": room[4],
        "var_ego": u16(session.read_memory("snesMemory", STARTUP_VAR_EGO, 2)),
        "actor1": {
            "room": actor1[0x16],
            "present": actor1[0x1F],
            "visible": actor1[0x15],
            "position": [u16(ego_position), u16(ego_position, 2)],
        },
        "controller": {
            "mode": controller[0],
            "cursor": [u16(controller, 1), u16(controller, 3)],
            "verb": controller[5],
            "object": u16(controller, 6),
            "submissions": controller[9],
            "ready": session.read_memory("snesMemory", 0x7E5E8A, 1)[0],
        },
        "m23a_phase": session.read_memory("snesMemory", 0x7FF2C2, 1)[0],
        "m23a_hold": session.read_memory("snesMemory", 0x7FF2C4, 1)[0],
        "m23a_current_kind": session.read_memory("snesMemory", 0x7FF2CF, 1)[0],
        "return_valid": session.read_memory("snesMemory", 0x7FF467, 1)[0],
        "return_program": session.read_memory("snesMemory", 0x7FF2C3, 1)[0],
        "return_pc": u16(session.read_memory("snesMemory", 0x7FF2E5, 2)),
        "return_slot": session.read_memory("snesMemory", 0x7FF468, 1)[0],
        "return_mode": session.read_memory("snesMemory", 0x7FF469, 1)[0],
        "entry_program": session.read_memory("snesMemory", 0x7FF2CD, 1)[0],
        "exit_program": session.read_memory("snesMemory", 0x7FF2CE, 1)[0],
        "error": common[3],
        "scenario_error": {
            "count": session.read_memory("snesMemory", 0x7E5F20, 1)[0],
            "code": session.read_memory("snesMemory", 0x7E5F21, 1)[0],
            "program": session.read_memory("snesMemory", 0x7E5F22, 1)[0],
            "pc": u16(session.read_memory("snesMemory", 0x7E5F23, 2)),
            "opcode": session.read_memory("snesMemory", 0x7E5F25, 1)[0],
            "room": session.read_memory("snesMemory", 0x7E5F26, 1)[0],
            "caller_return": session.read_memory("snesMemory", 0x7E5F2E, 2).hex(),
        },
        "c21": {
            "object": session.read_memory("snesMemory", 0x7FD3F0, 2).hex(),
            "selector": session.read_memory("snesMemory", 0x7FD3F2, 1)[0],
            "initialized": session.read_memory("snesMemory", 0x7FD3AC, 1)[0],
        },
        "current_program": common[0x62],
        "vm_pc": u16(common),
        "lifecycle": session.read_memory("snesMemory", 0x7E2221, 1)[0],
        "current_slot": session.read_memory("snesMemory", 0x7E2A88, 1)[0],
        "active_count": session.read_memory("snesMemory", 0x7E2A8A, 1)[0],
        "input_held": int.from_bytes(
            session.read_memory("snesMemory", 0x7E2200, 2), "little"),
        "fixture_requested": session.read_memory("snesMemory", 0x7E5600, 1)[0],
        "fixture_ready": session.read_memory("snesMemory", 0x7E5601, 1)[0],
        "engine_boot_count": session.read_memory("snesMemory", 0x7E5451, 1)[0],
        # Preserve room-loader and checked-provider diagnostics in the cold
        # startup artifact.  A terminal SCUMM_ERR_RESOURCE alone does not tell
        # whether the failure was the generated room descriptor, a bounded
        # transfer, or SC5LIVE validation.
        "msu_provider": {
            "status": session.read_memory("snesMemory", 0x7E2F00, 1)[0],
            "error": session.read_memory("snesMemory", 0x7E2F01, 1)[0],
            "flags": session.read_memory("snesMemory", 0x7E2F02, 1)[0],
            "last_check_stage": session.read_memory("snesMemory", 0x7E2F03, 1)[0],
            "section_temp": u16(session.read_memory("snesMemory", 0x7E2F46, 2)),
            "request_offset": session.read_memory("snesMemory", 0x7E2F04, 4).hex(),
            "request_length": session.read_memory("snesMemory", 0x7E2F08, 4).hex(),
            "destination": session.read_memory("snesMemory", 0x7E2F0C, 3).hex(),
            "destination_capacity": u16(session.read_memory("snesMemory", 0x7E2F0F, 2)),
            "remaining": session.read_memory("snesMemory", 0x7E2F15, 4).hex(),
            "seek_count": u16(session.read_memory("snesMemory", 0x7E2F2B, 2)),
            "bytes_read": int.from_bytes(
                session.read_memory("snesMemory", 0x7E2F2D, 4), "little"),
            "read_count": u16(session.read_memory("snesMemory", 0x7E2F31, 2)),
            "range_reject_count": u16(
                session.read_memory("snesMemory", 0x7E2F35, 2)),
            "verify_count": u16(session.read_memory("snesMemory", 0x7E2F37, 2)),
        },
        "msu_room_service": {
            "state": session.read_memory("snesMemory", 0x7E2FEB, 1)[0],
            "room": session.read_memory("snesMemory", 0x7E2FEC, 1)[0],
            "requests": u16(session.read_memory("snesMemory", 0x7E2FED, 2)),
            "validations": u16(session.read_memory("snesMemory", 0x7E2FEF, 2)),
            "failures": u16(session.read_memory("snesMemory", 0x7E2FF1, 2)),
            "last_length": u16(session.read_memory("snesMemory", 0x7E2FF7, 2)),
        },
        "stream_error": {
            "program_unit": u16(session.read_memory("snesMemory", 0x7E5F13, 2)),
            "logical_pc": u16(session.read_memory("snesMemory", 0x7E5F15, 2)),
            "site": session.read_memory("snesMemory", 0x7E5F17, 1)[0],
            "capture_valid": session.read_memory("snesMemory", 0x7E5F18, 1)[0],
        },
        "live_room_diagnostics": {
            "control": session.read_memory("snesMemory", 0x401384, 0x40).hex(),
            "stage": session.read_memory("snesMemory", 0x401384, 1)[0],
            "room": session.read_memory("snesMemory", 0x401385, 1)[0],
            "chunk_index": u16(session.read_memory("snesMemory", 0x4013A8, 2)),
            "chunk_mode": session.read_memory("snesMemory", 0x4013A7, 1)[0],
            "read_length": u16(session.read_memory("snesMemory", 0x401386, 2)),
            "pending_header": session.read_memory("snesMemory", 0x4013C4, 0x40).hex(),
            "active_header": session.read_memory("snesMemory", 0x41E800, 0x40).hex(),
            "chunk_state": session.read_memory("snesMemory", 0x4013A7, 0x10).hex(),
        },
        "reset_diag": session.read_memory("snesMemory", RESET_DIAG_BASE, 0x50).hex(),
        "c25": {
            "queue_count": session.read_memory("snesMemory", 0x7FD459, 1)[0],
            "last_count": session.read_memory("snesMemory", 0x7FD86A, 1)[0],
            "flush_count": session.read_memory("snesMemory", 0x7FD8AB, 1)[0],
            "pending_count": session.read_memory("snesMemory", 0x7FD8AC, 1)[0],
            "command_index": session.read_memory("snesMemory", 0x7FD8ED, 1)[0],
            "last_words": session.read_memory("snesMemory", 0x7FD86B, 64).hex(),
        },
        "m23a_request_count": session.read_memory("snesMemory", 0x7FF2C5, 1)[0],
        "m23a_lifecycle_count": session.read_memory("snesMemory", 0x7FF2D6, 1)[0],
        "m23a_lifecycle": session.read_memory("snesMemory", 0x7FF2D7, 14).hex(),
        "globals": session.read_memory("snesMemory", 0x7E2364, 0x80).hex(),
        "cpu": session.get_cpu_state(),
        "native_stack_page": session.read_memory("snesMemory", 0x1F00, 0x100).hex(),
        "low_bus_47a0": session.read_memory("snesMemory", 0x47A0, 16).hex(),
        "live_slots": live,
    }


def quick_gate(session) -> tuple[int, int, int, int, int, int]:
    room = session.read_memory("snesMemory", ROOM_BLOCK, 5)
    talk_active = session.read_memory("snesMemory", 0x7E7A20, 1)[0]
    error = session.read_memory("snesMemory", COMMON + 3, 1)[0]
    lifecycle = session.read_memory("snesMemory", 0x7E2221, 1)[0]
    return room[0], room[1], room[4], talk_active, error, lifecycle


def _drive_title_saw_prior_scene(
    active_record: int, room: int, target_room: int
) -> bool:
    """Treat the authentic resource-less room-zero boot as prior scene state.

    Older fixture-root replays began in a loaded carrier room, so the input
    gate only counted a different room after a record was installed.  The
    authentic Global1 root intentionally begins with no active room record;
    that null scene must still arm a later, explicitly selected target room.
    """
    if room == target_room:
        return False
    return active_record != 0xFF or room == 0


def _button_names(mask: int) -> list[str]:
    """Return the SNES pad buttons represented by the recorded input mask."""
    names = (
        (0x001, "A"), (0x002, "B"), (0x004, "SELECT"), (0x008, "START"),
        (0x010, "UP"), (0x020, "DOWN"), (0x040, "LEFT"),
        (0x080, "RIGHT"), (0x100, "X"), (0x200, "L"),
        (0x400, "R"), (0x800, "Y"),
    )
    return [name for bit, name in names if mask & bit]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=NEXEN_DEFAULT)
    parser.add_argument("--dotnet-host", type=Path,
                        help="launch this Nexen release DLL through an explicit .NET host")
    parser.add_argument("--port", type=int, default=44729)
    parser.add_argument("--frames", type=int, default=1800)
    parser.add_argument("--sample-interval", type=int, default=30)
    parser.add_argument("--drive-title", action="store_true",
                        help="send one ordinary title input at --start-room")
    parser.add_argument("--title-start-buttons", type=lambda value: int(value, 0),
                        default=0x008,
                        help="button mask for the initial title input (default: START / 0x8)")
    parser.add_argument("--start-room", type=int, default=75,
                        help="room in which --drive-title sends START (default: 75)")
    parser.add_argument("--stop-at-engine-error", action="store_true",
                        help="use Nexen run-until to stop exactly at the first SCUMM frame error label after title input")
    parser.add_argument("--stop-at-second-boot", action="store_true",
                        help="stop at the second native ScummV5_Engine_Boot entry and capture reset/stack state")
    parser.add_argument("--stop-at-low-pc", type=lambda value: int(value, 0),
                        help="stop on first execution of an observed non-ROM CPU address (diagnostic only)")
    args = parser.parse_args()
    rom = args.rom.resolve()
    if args.frames <= 0 or args.sample_interval <= 0:
        parser.error("frames and sample interval must be positive")
    if args.title_start_buttons <= 0 or args.title_start_buttons & ~0x7FF:
        parser.error("--title-start-buttons must be a nonzero SNES button mask")
    if not args.nexen.is_file():
        parser.error(f"Nexen executable missing: {args.nexen}")

    # Validate the exact ROM/map/listing/build-identity tuple before launching
    # Nexen or registering hooks. All code breakpoints come from this map.
    map_path, symbols = verified_symbol_map_for_rom(rom)
    hook_banks = {"brk_handler": 0}
    hook_banks.update({
        name: 0 for name in (
            "reset",
            "Same_Engine_Reset",
            "Same_Engine_Boot",
            "ScummV5_Engine_Boot",
            "Same_Main_Loop",
            "Same_Engine_Frame",
            "Same_Engine_Frame__running",
            "Same_Engine_Frame__failed",
            "Same_ActiveEngine_Frame",
            "Same_ActiveEngine_Frame__error",
            "Same_ActiveEngine_Frame__production_error",
            "ScummV5_Engine_Frame",
            "ScummV5_Engine_Frame__error",
            "ScummV5_Engine_Frame__m23a_error",
            "ScummV5_Engine_Frame__m23a_failed",
            "ScummV5_Engine_Frame__m23a_ready",
            "ScummV5_Engine_Frame__complete_success",
            "ScummV5_Engine_Frame__outer_return_success",
            "ScummV5_M24RB_Far_RequestRoom",
            "ScummV5_M24RB_Far_CommitRoom",
            "ScummV5_M24RB_Far_CommitRoom__begin_live_install",
            "ScummV5_M24RB_Far_CommitRoom__begin_live_visuals",
            "ScummV5_M24RB_Far_CommitRoom__load_incoming_bundle",
            "ScummV5_M24RB_Far_CommitRoom__new_bundle_loaded",
            "ScummV5_M24RB_Far_CommitRoom__live_visual_published",
            "ScummV5_M24RB_Far_CommitRoom__execute",
            "ScummV5_M23A_PollLifecycleChain_FarEntry",
            "ScummV5_M23A_PollLifecycleChain__complete",
            "ScummV5_M23A_HandoffLifecycleChain",
            "ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__ready",
            "ScummV5_RequestRoom",
            "ScummV5_M23A_RequestRoom_FarEntry",
            "ScummV5_Engine_Frame__scenario_request_done",
            "ScummV5_Engine_Frame__m23a_error",
            "ScummV5_Engine_Frame__scenario_ready_overlay_done",
            "ScummV5_Engine_Frame__scenario_sched_not_ready",
            "ScummV5_C4_Scheduler_Frame",
            "ScummV5_Engine_Frame__m23a_run_room_script",
            "ScummV5_Engine_Frame__m23a_continue",
            "ScummV5_Engine_Frame__m23a_rehydrate",
            "ScummV5_Engine_Frame__m23a_room_runnable",
            "ScummV5_Engine_Frame__m23a_driver",
            "ScummV5_Engine_RunSelected",
            "ScummV5_Op_SoundKludge",
            "ScummV5_Op_RoomOps",
            "ScummV5_Op_Stop",
            "ScummV5_Op_LoadRoom",
            "ScummV5_M23A_CommitNullRoom",
            "ScummV5_M24RB_Far_CommitNullRoom",
            "ScummV5_C25_Flush",
        )
    })
    # main.pasm switches to PBR bank 9 before including the far room-service
    # implementation and its adapters. Map PCs are bank-local, so resolving
    # these labels with PBR 0 installs plausible-looking but unrelated hooks.
    for name in tuple(hook_banks):
        if (
            name.startswith("ScummV5_M24RB_Far_")
            or name.startswith("ScummV5_M23A_PollLifecycleChain")
            or name.startswith("ScummV5_MsuLiveRoom_ValidateCompletedRead_Far")
        ):
            hook_banks[name] = 9
    for name in (
        "ScummV5_M23A_RequestRoom_FarEntry",
        "ScummV5_M23A_ResourceReady_FarEntry",
        "ScummV5_M23A_EndRoomScript_FarEntry",
        "ScummV5_M23A_CommitRoom_FarEntry",
        "ScummV5_M23A_Trace_FarEntry",
    ):
        if name in symbols:
            hook_banks[name] = 9
    boundary_names = (
        "ScummV5_M24RB_Far_RequestRoom__new",
        "ScummV5_M24RB_Far_RequestRoom__queued",
        "ScummV5_M24RB_Far_ResourceReady__run_exit",
        "ScummV5_M24RB_Far_BeginRoomScript",
        "ScummV5_M24RB_Far_EndRoomScript",
        "ScummV5_M24RB_Far_CommitNullRoom",
        "ScummV5_M24RB_Far_CommitRoom",
        "ScummV5_M24RB_Far_CommitRoom__begin_live_install",
        "ScummV5_M24RB_Far_CommitRoom__begin_live_visuals",
        "ScummV5_M24RB_Far_CommitRoom__load_incoming_bundle",
        "ScummV5_M24RB_Far_CommitRoom__new_bundle_loaded",
        "ScummV5_M24RB_Far_CommitRoom__live_visual_published",
        "ScummV5_M24RB_Far_CommitRoom__execute",
        "ScummV5_M23A_PollLifecycleChain_FarEntry",
        "ScummV5_M23A_PollLifecycleChain__complete",
        "ScummV5_M23A_HandoffLifecycleChain",
        "ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__ready",
        "ScummV5_Engine_Frame__m23a_ready",
        "ScummV5_M23A_ResourceReady_FarEntry",
        "ScummV5_M23A_EndRoomScript_FarEntry",
        "ScummV5_M23A_CommitRoom_FarEntry",
        "ScummV5_Engine_Frame__m23a_run_room_script",
        "ScummV5_Op_Stop__m23a_exit_complete",
        "ScummV5_Op_Stop__m23a_entry_complete",
        "ScummV5_Op_Stop__m23a_restore_return",
        "ScummV5_Op_Stop__m23a_no_return",
        "ScummV5_Op_RoomOps",
        "ScummV5_Op_SoundKludge",
    )
    for name in boundary_names:
        if name in symbols:
            hook_banks[name] = (
                9 if (
                    name.startswith("ScummV5_M24RB_Far_")
                    or name.startswith("ScummV5_M23A_PollLifecycleChain")
                    or name.startswith("ScummV5_MsuLiveRoom_ValidateCompletedRead_Far")
                    or name.endswith("_FarEntry")
                )
                else 0
            )
    # The C25 far body is deliberately placed in bank 83; its bank-0 entry is
    # only a JSL/RTS adapter. Keep each execution hook tied to the assembled PBR.
    hook_banks.update({
        "ScummV5_C25_Flush_Far": 83,
        "ScummV5_C25_Flush__complete": 83,
    })
    hook_addresses = {
        name: mapped_cpu_address_for_rom(rom, name, bank=bank)
        for name, bank in hook_banks.items() if name in symbols
    }
    if "Same_Main_Loop" not in hook_addresses:
        raise RuntimeError(f"Same_Main_Loop missing from verified map {map_path}")

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mesen_session
    # Nexen's repository runner invokes the verified release directly; skip
    # only the legacy Mesen-specific package-version check.
    mesen_session.validate_mesen_build = lambda _path: None

    session_type = mesen_session.McpSession
    nexen = args.nexen.resolve()
    dotnet_host = args.dotnet_host.resolve() if args.dotnet_host else None
    nexen_assembly = nexen.with_suffix(".dll")
    nexen_native = nexen.parent / "NexenCore.so"
    if dotnet_host is not None:
        if not dotnet_host.is_file() or not nexen_assembly.is_file() or not nexen_native.is_file():
            parser.error("--dotnet-host requires existing dotnet, Nexen.dll, and NexenCore.so files")
        original_popen = mesen_session.subprocess.Popen

        def launch_nexen(command, *popen_args, **popen_kwargs):
            if command and Path(command[0]).resolve() == nexen:
                command = [str(dotnet_host), str(nexen_assembly), *command[1:]]
            return original_popen(command, *popen_args, **popen_kwargs)

        mesen_session.subprocess.Popen = launch_nexen

    args.output.parent.mkdir(parents=True, exist_ok=True)
    nexen_sha = hashlib.sha256(nexen.read_bytes()).hexdigest()
    runtime_launch: dict[str, object] = {
        "mode": "apphost",
        "nexen_apphost_sha256": nexen_sha,
    }
    if dotnet_host is not None:
        runtime_launch = {
            "mode": "dotnet-host",
            "command_prefix": [str(dotnet_host), str(nexen_assembly)],
            "dotnet_host_sha256": hashlib.sha256(dotnet_host.read_bytes()).hexdigest(),
            "nexen_apphost_sha256": nexen_sha,
            "nexen_assembly_sha256": hashlib.sha256(nexen_assembly.read_bytes()).hexdigest(),
            "nexen_native_sha256": hashlib.sha256(nexen_native.read_bytes()).hexdigest(),
        }
    events: list[dict[str, object]] = []
    samples: list[dict[str, object]] = []
    request_contexts: list[dict[str, object]] = []
    hit_counts = {name: 0 for name in hook_addresses}
    control_events: list[dict[str, object]] = []
    boundary_events: list[dict[str, object]] = []
    phase_events: list[dict[str, object]] = []
    watched_writes: list[dict[str, object]] = []
    write_addresses = {
        # Reset-entry count is persistent across the engine's reset prologue.
        # Watching it distinguishes a genuine return to reset from an ordinary
        # room-0/null-scene install or a second engine-frame invocation.
        RESET_DIAG_BASE: "reset_diag_count_low",
        RESET_DIAG_BASE + 1: "reset_diag_count_high",
        0x7E2200: "input_held",
        STARTUP_VAR_EGO: "var_ego_low",
        0x7F3776: "actor1_room",
        0x7FF1A4: "actor1_x_low",
        0x7FF1A5: "actor1_x_high",
        0x7FF1A6: "actor1_y_low",
        0x7FF1A7: "actor1_y_high",
        0x7E5FE1: "controller_x_low",
        0x7E5FE2: "controller_x_high",
        0x7E5FE3: "controller_y_low",
        0x7E5FE4: "controller_y_high",
        0x7E2300: "shared_vm_pc_low",
        0x7E2301: "shared_vm_pc_high",
        0x7E2306: "shared_vm_last_opcode",
        0x7E5600: "scenario_fixture_request_flag",
        0x7FF2C5: "m23a_request_count",
        0x7FF2C1: "pending_room",
        0x7FF2C2: "m23a_phase",
        0x7FF2C4: "m23a_hold",
        0x7FF2CE: "m23a_exit_program",
        0x7FF2CF: "m23a_current_kind",
        0x7FF2BF: "active_room",
        0x7E2303: "scumm_error",
        0x7E1032: "brk_count",
        0x7E1034: "cop_count",
        0x7E2221: "engine_lifecycle",
        # The diagnostic BRK handler snapshots the native interrupt
        # frame before STP. Watching these stores gives the precise fault PC
        # even when Nexen's asynchronous execution-hook notification is only
        # drained after the CPU has halted.
        0x7FF470: "brk_saved_pbr",
        0x7FF471: "brk_saved_pc_low",
        0x7FF472: "brk_saved_pc_high",
        0x7FF473: "brk_saved_sp_low",
        0x7FF474: "brk_saved_sp_high",
        0x7FF475: "brk_saved_p",
        0x7FF48B: "brk_saved_a_low",
        0x7FF48C: "brk_saved_a_high",
        0x7FF48D: "brk_saved_x_low",
        0x7FF48E: "brk_saved_x_high",
        0x7FF48F: "brk_saved_y_low",
        0x7FF490: "brk_saved_y_high",
        0x7FF2C3: "return_program",
        0x7FF2E5: "return_pc_low",
        0x7FF2E6: "return_pc_high",
        0x7FF467: "return_valid",
        0x7FF468: "return_slot",
        0x7FF469: "return_mode",
        0x7E2A88: "current_slot",
        0x7E2362: "program_select",
        # Slot descriptor writes let cycle-stamped VM-PC/opcode writes be
        # attributed to the executing activation without sampling WRAM later
        # at notification-drain time. Slots 0..4 cover the boot global and
        # startup globals used by this harness.
        0x7E2380: "slot0_status",
        0x7E2381: "slot1_status",
        0x7E2382: "slot2_status",
        0x7E2383: "slot3_status",
        0x7E2384: "slot4_status",
        0x7E2399: "slot0_script",
        0x7E239A: "slot1_script",
        0x7E239B: "slot2_script",
        0x7E239C: "slot3_script",
        0x7E239D: "slot4_script",
        0x7E23B2: "slot0_program",
        0x7E23B3: "slot1_program",
        0x7E23B4: "slot2_program",
        0x7E23B5: "slot3_program",
        0x7E23B6: "slot4_program",
        0x7E23E4: "slot0_saved_pc_low",
        0x7E23E5: "slot0_saved_pc_high",
        0x7E23E6: "slot1_saved_pc_low",
        0x7E23E7: "slot1_saved_pc_high",
        0x7E23E8: "slot2_saved_pc_low",
        0x7E23E9: "slot2_saved_pc_high",
        0x7E23EA: "slot3_saved_pc_low",
        0x7E23EB: "slot3_saved_pc_high",
        0x7E23EC: "slot4_saved_pc_low",
        0x7E23ED: "slot4_saved_pc_high",
    }
    with session_type(
        rom=rom, mesen=nexen, cwd=ROOT, port=args.port,
        boot_wait=2.0, socket_timeout=600.0,
        stderr_log=args.output.with_suffix(".nexen-stderr.log"),
    ) as session, ControllerInputLease(session) as controller:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        # Enable the trace ring before any authored execution.  For room
        # requests, the notification is drained at the next frame boundary;
        # the instruction ring lets us recover the actual caller/operand
        # rather than guessing from the room number observed afterward.
        session.trace_log(1)
        handles = {
            name: session.add_exec_hook(address)
            for name, address in hook_addresses.items()
        }
        watched = {
            session.add_write_hook(address): name
            for address, name in write_addresses.items()
        }
        low_pc_handle = (session.add_exec_hook(args.stop_at_low_pc)
                         if args.stop_at_low_pc is not None else None)

        def capture_hook(name: str, params: dict[str, object]) -> None:
            hit_counts[name] += 1
            boundary_candidate = name in {
                "reset", "Same_Engine_Reset", "brk_handler"
            } or name in boundary_names or name in {
                "ScummV5_Op_LoadRoom",
                "ScummV5_M23A_RequestRoom_FarEntry",
                "ScummV5_M24RB_Far_RequestRoom",
                "ScummV5_M24RB_Far_ResourceReady",
                "ScummV5_Op_Stop",
            }
            if boundary_candidate and name in {"ScummV5_Op_RoomOps", "ScummV5_Op_SoundKludge"}:
                boundary_candidate = session.read_u8(0x7FF2C2) in (1, 2)
            if boundary_candidate:
                cpu = session.get_cpu_state()
                boundary_events.append({
                    "symbol": name,
                    **params,
                    "cpu_at_drain": cpu,
                    "room_state_at_drain": session.read_memory(
                        "snesMemory", ROOM_BLOCK, 0x12).hex(),
                    "error": session.read_u8(COMMON + 3),
                    "program_select": session.read_u8(0x7E2362),
                    "vm_pc": session.read_u16(COMMON),
                    "current_slot": session.read_u8(0x7E2A88),
                    "return_state": session.read_memory(
                        "snesMemory", 0x7FF467, 4).hex(),
                    "return_pc": session.read_memory(
                        "snesMemory", 0x7FF2E5, 2).hex(),
                    "trace_tail": session.trace_log(192).get("rows", [])[-96:],
                })
            if name in {
                "ScummV5_Engine_Frame__m23a_continue",
                "ScummV5_Engine_Frame__m23a_run_room_script",
                "ScummV5_Engine_Frame__m23a_rehydrate",
                "ScummV5_Engine_Frame__m23a_room_runnable",
                "ScummV5_Engine_Frame__m23a_driver",
            }:
                phase_events.append({
                    "symbol": name,
                    **params,
                    "phase_at_drain": session.read_u8(0x7FF2C2),
                    "room_at_drain": session.read_u8(0x7FF2BF),
                    "exit_program_at_drain": session.read_u8(0x7FF2CE),
                    "current_program_at_drain": session.read_u8(COMMON + 0x62),
                    "current_pc_at_drain": session.read_u16(COMMON),
                    "slot_at_drain": session.read_u8(0x7E2A88),
                })
            if name in {
                "Same_Engine_Frame__failed",
                "Same_ActiveEngine_Frame__error",
                "Same_ActiveEngine_Frame__production_error",
                "ScummV5_Engine_Frame__error",
                "ScummV5_Engine_Frame__m23a_error",
                "ScummV5_Engine_Frame__m23a_failed",
            }:
                control_events.append({
                    "symbol": name,
                    **params,
                    "room_state_at_drain": session.read_memory(
                        "snesMemory", ROOM_BLOCK, 8).hex(),
                    "error": session.read_u8(COMMON + 3),
                    "lifecycle": session.read_u8(0x7E2221),
                    "cpu_at_drain": session.get_cpu_state(),
                    "trace_tail": (
                        session.trace_log(1000).get("rows", [])[-512:]
                        if name == "ScummV5_Engine_Frame__error" else []
                    ),
                })
            if name in {"ScummV5_RequestRoom",
                        "ScummV5_M23A_RequestRoom_FarEntry"}:
                trace = session.trace_log(256)
                rows = trace.get("rows", []) if isinstance(trace, dict) else []
                request_contexts.append({
                    "symbol": name,
                    **params,
                    "cpu_at_drain": session.get_cpu_state(),
                    "room_state_at_drain": session.read_memory(
                        "snesMemory", ROOM_BLOCK, 8).hex(),
                    "fixture_flags_at_drain": session.read_memory(
                        "snesMemory", 0x7E5600, 2).hex(),
                    "trace_tail": rows[-96:],
                })
            if name == "ScummV5_Engine_RunSelected":
                # Notifications are drained in batches. Preserve the hook's
                # frame/cycle as event data, but label current WRAM separately
                # as a drain-time snapshot; it may describe a later slot.
                current_slot = session.read_memory("snesMemory", 0x7E2A88, 1)[0]
                slot_number = session.read_memory(
                    "snesMemory", 0x7E2399 + current_slot, 1)[0]
                room = session.read_memory("snesMemory", ROOM_BLOCK, 5)
                common = session.read_memory("snesMemory", COMMON, 0x64)
                events.append({
                    "symbol": name,
                    **activation_observation(
                        params,
                        snapshot={
                            "slot": current_slot,
                            "script": slot_number,
                            "program": common[0x62],
                            "pc": u16(common),
                            "room": room[1],
                            "phase": room[4],
                        },
                        synchronized=False,
                    ),
                })
                return
            if name in {
                "reset",
                "Same_Engine_Reset",
                "Same_Engine_Boot",
                "ScummV5_Engine_Boot",
                "ScummV5_M24RB_Far_RequestRoom",
                "ScummV5_M24RB_Far_CommitRoom",
                "ScummV5_RequestRoom",
                "ScummV5_M23A_RequestRoom_FarEntry",
                "ScummV5_Engine_Frame__m23a_error",
                "ScummV5_Op_SoundKludge",
                "ScummV5_Op_RoomOps",
                "ScummV5_Op_Stop",
                "ScummV5_Engine_Frame__m23a_run_room_script",
                "ScummV5_Op_LoadRoom",
                "ScummV5_M23A_CommitNullRoom",
                "ScummV5_M24RB_Far_CommitNullRoom",
                "ScummV5_C25_Flush",
                "ScummV5_C25_Flush_Far",
                "ScummV5_C25_Flush__complete",
                "ScummV5_Engine_Frame__m23a_continue",
                "ScummV5_Engine_Frame__m23a_run_room_script",
                "ScummV5_Engine_Frame__m23a_rehydrate",
                "ScummV5_Engine_Frame__m23a_room_runnable",
                "ScummV5_Engine_Frame__m23a_driver",
            } and len(events) < 4000:
                events.append({"symbol": name, **params})

        session.run_frames(2)
        # The localhost MCP pushes execution-hook notifications asynchronously.
        # Drain the cold-boot hit before a run-until wait; otherwise that wait
        # can consume the stale first-boot notification and stop several
        # frames later, falsely appearing to have reached a re-entry.
        for message in session.drain_notifications(
                timeout=1.0 if args.stop_at_second_boot else 0.0):
            params = message.get("params", message)
            handle = params.get("handle")
            name = next((n for n, h in handles.items() if h == handle), None)
            if name is not None:
                capture_hook(name, params)
            elif handle in watched:
                watched_writes.append({
                    "write": watched[handle], **params,
                    "drain_time_snapshot": snapshot(session),
                    "snapshot_timing": "drain-time; hook frame/cycle are event-time",
                })
        samples.append(snapshot(session))
        second_boot_stop: dict[str, object] | None = None
        if args.stop_at_second_boot:
            # run_until treats an execution hook as already satisfied if it
            # fired anywhere since registration. Replace the cold-boot hook
            # with a fresh handle so only a later entry can release the wait.
            session.remove_hook(handles["ScummV5_Engine_Boot"])
            handles["ScummV5_Engine_Boot"] = session.add_exec_hook(
                hook_addresses["ScummV5_Engine_Boot"]
            )
            stopped = session.run_until(
                max_frames=args.frames,
                hook_handle=handles["ScummV5_Engine_Boot"],
            )
            session.pause()
            for message in session.drain_notifications(timeout=0.0):
                params = message.get("params", message)
                handle = params.get("handle")
                name = next((n for n, h in handles.items() if h == handle), None)
                if name is not None:
                    capture_hook(name, params)
                elif handle in watched:
                    write = watched[handle]
                    watched_writes.append({
                        "write": write,
                        **params,
                        "drain_time_snapshot": snapshot(session),
                        "snapshot_timing": "drain-time; hook frame/cycle are event-time",
                        **({
                            "error_context_at_drain": snapshot(session),
                            "trace_tail_at_drain": session.trace_log(256).get(
                                "rows", [])[-128:],
                        } if write == "scumm_error" and params.get("value") else {}),
                    })
            second_boot_stop = {
                "run_until": stopped,
                "cpu_at_stop": session.get_cpu_state(),
                "reset_diagnostics": session.read_memory("snesMemory", RESET_DIAG_BASE, 0x50).hex(),
                "stack_page": session.read_memory("snesMemory", 0x000100, 0x100).hex(),
                "frame_counter": session.read_memory("snesMemory", 0x7E2100, 2).hex(),
                "room_state": session.read_memory("snesMemory", ROOM_BLOCK, 0x42).hex(),
                "lifecycle": session.read_u8(0x7E2221),
                "scenario_flags": session.read_memory("snesMemory", 0x7E5600, 2).hex(),
                "trace_tail": session.trace_log(1000).get("rows", [])[-256:],
            }
        low_pc_stop: dict[str, object] | None = None
        low_pc_notifications: list[dict[str, object]] = []
        if low_pc_handle is not None:
            # The target is an address observed only in the corrupted low-WRAM
            # trace. This synchronous run-until proves its first CPU visit.
            stopped = session.run_until(
                max_frames=args.frames,
                hook_handle=low_pc_handle,
            )
            session.pause()
            for message in session.drain_notifications(timeout=0.5):
                params = message.get("params", message)
                handle = params.get("handle")
                name = next((n for n, h in handles.items() if h == handle), None)
                if name is not None:
                    capture_hook(name, params)
                elif handle == low_pc_handle:
                    # Preserve the exact hook cycle/address. The CPU may have
                    # advanced by the time the host-side pause completes, so
                    # get_cpu_state() alone is not proof of the address hit.
                    low_pc_notifications.append(params)
                elif handle in watched:
                    watched_writes.append({
                        "write": watched[handle], **params,
                        "drain_time_snapshot": snapshot(session),
                        "snapshot_timing": "drain-time; hook frame/cycle are event-time",
                    })
            low_pc_stop = {
                "address": args.stop_at_low_pc,
                "run_until": stopped,
                "hook_notifications": low_pc_notifications,
                "cpu_at_stop": session.get_cpu_state(),
                "state": snapshot(session),
                "stack_page": session.read_memory("snesMemory", 0x000100, 0x100).hex(),
                "low_bank_fault_window": session.read_memory(
                    "snesMemory", 0x00004360, 0x40).hex(),
                "trace_tail": session.trace_log(1000).get("rows", [])[-1000:],
            }
        start_sent = False
        title_ack = False
        start_release = None
        input_events: list[dict[str, object]] = []
        error_stop: dict[str, object] | None = None
        host_frame = 0
        saw_other_loaded_room = False
        while host_frame < args.frames:
            if args.stop_at_second_boot or low_pc_handle is not None:
                break
            active_record, room, phase, talk_active, error, lifecycle = quick_gate(session)
            if _drive_title_saw_prior_scene(active_record, room, args.start_room):
                saw_other_loaded_room = True
            if (args.drive_title and not start_sent and room == args.start_room
                    and phase in (0, 2) and saw_other_loaded_room
                    and (active_record != 0xFF or room == 0)):
                # Install the controller level without advancing the emulator.
                # set_input(frames=...) uses a wall-clock sleep and can advance
                # beyond its nominal duration under max-speed execution. The
                # host_frame loop below is frame-exact, so hold the level and
                # let run_frames own the full 40-frame interval.
                input_start_frame = session.get_state()["frameCount"]
                controller.hold(args.title_start_buttons)
                start_sent = True
                start_release = host_frame + 40
                input_events.append({"frame": host_frame,
                                     "emulator_frame": input_start_frame,
                                     "buttons": _button_names(args.title_start_buttons),
                                     "button_mask": args.title_start_buttons,
                                     "duration": 40, "room": room,
                                     "phase": phase})
            elif (args.drive_title and start_sent and not title_ack
                  and room == 68 and talk_active):
                input_start_frame = session.get_state()["frameCount"]
                controller.hold(1)
                title_ack = True
                start_release = host_frame + 2
                input_events.append({"frame": host_frame, "buttons": ["A"],
                                     "emulator_frame": input_start_frame,
                                     "duration": 2, "room": room, "phase": phase})
            if start_release is not None and host_frame >= start_release:
                controller.release()
                start_release = None
            # Advance in bounded batches. During a held input, never cross its
            # release boundary; message acknowledgements are sampled before
            # each batch and remain active until acknowledged.
            step = next_input_safe_window(
                host_frame,
                args.frames,
                release_frame=start_release,
                sample_interval=args.sample_interval,
            )
            if step == 0:
                break
            advancement = advance_bounded(
                session,
                step,
                error_hook=(
                    handles["ScummV5_Engine_Frame__error"]
                    if args.stop_at_engine_error and start_sent else None
                ),
            )
            host_frame += int(advancement["frames_advanced"])
            if advancement["hook_fired"]:
                session.pause()
                error_stop = {
                    **advancement,
                    "cpu_at_stop": session.get_cpu_state(),
                    "phase": session.read_u8(0x7FF2C2),
                    "room": session.read_u8(0x7FF2BF),
                    "program": session.read_u8(COMMON + 0x62),
                    "vm_pc": session.read_u16(COMMON),
                    "current_slot": session.read_u8(0x7E2A88),
                    "nested": session.read_u8(0x7FD335),
                    "return_mode": session.read_u8(0x7E2363),
                    "error": session.read_u8(COMMON + 3),
                    "lifecycle": session.read_u8(0x7E2221),
                    "trace_tail": (session.trace_log(256).get("rows", [])[-96:]),
                }
                for message in session.drain_notifications(timeout=0.0):
                    params = message.get("params", message)
                    handle = params.get("handle")
                    name = next((n for n, h in handles.items() if h == handle), None)
                    if name is not None:
                        capture_hook(name, params)
                if error_stop["error"] != 0:
                    break
            for message in session.drain_notifications(timeout=0.0):
                params = message.get("params", message)
                handle = params.get("handle")
                name = next((n for n, h in handles.items() if h == handle), None)
                if name is not None:
                    capture_hook(name, params)
                elif handle in watched:
                    write = watched[handle]
                    watched_writes.append({
                        "write": write,
                        **params,
                        **({
                            "error_context_at_drain": snapshot(session),
                            "trace_tail_at_drain": session.trace_log(256).get(
                                "rows", [])[-128:],
                        } if write == "scumm_error" and params.get("value") else {}),
                    })
            if (host_frame % args.sample_interval == 0 or host_frame >= args.frames
                    or error != 0 or lifecycle == 0xFF):
                samples.append(snapshot(session))
            if samples[-1]["error"] != 0 or samples[-1]["lifecycle"] == 0xFF:
                break
        extra_handles = ((low_pc_handle,) if low_pc_handle is not None else ())
        for handle in (*handles.values(), *watched, *extra_handles):
            session.remove_hook(handle)
        trace = session.trace_log(512)
        trace_rows = trace.get("rows", []) if isinstance(trace, dict) else []

    report = {
        "rom": str(rom),
        "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
        "map": str(map_path),
        "nexen": str(args.nexen.resolve()),
        "nexen_sha256": nexen_sha,
        "runtime_launch": runtime_launch,
        "hook_addresses": {k: f"${v:06X}" for k, v in hook_addresses.items()},
        "hook_hits": hit_counts,
        "input_events": input_events,
        "title_start_sent": start_sent,
        "title_ack_sent": title_ack,
        "error_stop": error_stop,
        "second_boot_stop": second_boot_stop,
        "low_pc_stop": low_pc_stop,
        "events": events,
        "request_contexts": request_contexts,
        "control_events": control_events,
        "boundary_events": boundary_events,
        "phase_events": phase_events,
        "watched_writes": watched_writes,
        "final_trace_tail": trace_rows[-128:],
        "samples": samples,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": str(args.output),
        "rom_sha256": report["rom_sha256"],
        "hook_hits": hit_counts,
        "samples": len(samples),
        "last": samples[-1] if samples else None,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
