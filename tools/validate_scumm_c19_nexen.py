#!/usr/bin/env python3
"""Validate C19 SCUMM v5 cutscene/override semantics in Nexen."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fate_replay import ControllerInputLease  # noqa: E402
from validate_scumm_startup42_nexen import (  # noqa: E402
    mapped_cpu_address_for_rom,
    verified_symbol_map_for_rom,
)

DEFAULT_ROM = ROOT / "build" / "same-scumm-v5.sfc"
DEFAULT_NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
COMMON_ADDRESS = 0x7E2300
C19_ADDRESS = 0x7FD348
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ID = 43
FIRST_YIELD_PC = 287
OVERRIDE_PC = 283
FINAL_PC = 300


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def s16(raw: bytes, offset: int = 0) -> int:
    value = u16(raw, offset)
    return value - 0x10000 if value & 0x8000 else value


def stack_pointer(cpu: dict[str, object]) -> int:
    for key in ("sp", "SP", "stackPointer", "stack_pointer"):
        if key in cpu:
            value = cpu[key]
            if isinstance(value, str):
                return int(value[1:], 16) if value.startswith("$") else int(value, 0)
            return int(value)
    raise GateFailure(f"CPU state does not expose a stack pointer: {cpu}")


def snapshot(session: object, variables_address: int) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON_ADDRESS, 0x64)
    cutscene = session.read_memory("snesMemory", C19_ADDRESS, 0x38)
    room = session.read_memory("snesMemory", 0x7FF2BE, 0x0A)
    reset = session.read_memory("snesMemory", 0x7FF46B, 0x20)
    variable_bytes = session.read_memory("snesMemory", variables_address, 0x20)
    return {
        "pc": u16(common), "status": common[0x02], "error": common[0x03],
        "last_opcode": common[0x06], "frame_count": u16(common, 0x08),
        "frame_ops": u16(common, 0x0A), "total_ops": u16(common, 0x0C),
        "fixture_active": common[0x5F], "program_select": common[0x62],
        "variables_address": variables_address,
        "variables": [s16(variable_bytes, index * 2) for index in range(16)],
        "variables_window_hex": variable_bytes.hex(),
        "result_offset": session.read_memory("snesMemory", 0x7E2340, 2).hex(),
        "operand": session.read_memory("snesMemory", 0x7E2342, 2).hex(),
        "current_slot": session.read_memory("snesMemory", 0x7E2A88, 1)[0],
        "stack_pointer": cutscene[0],
        "data": [s16(cutscene, 2 + index * 2) for index in range(5)],
        "override_pc": [u16(cutscene, 12 + index * 2) for index in range(5)],
        "override_slots": list(cutscene[22:27]),
        "slot_depths": list(cutscene[27:52]),
        "cutscene_script_index": cutscene[52],
        "fixture_request": session.read_memory("snesMemory", FIXTURE_REQUEST, 1)[0],
        "room": room[1], "pending_room": room[3], "room_phase": room[4],
        "m23a_phase": session.read_memory("snesMemory", 0x7FF2C2, 1)[0],
        "m23a_requests": session.read_memory("snesMemory", 0x7FF2C5, 1)[0],
        "engine_lifecycle": session.read_memory("snesMemory", 0x7E2221, 1)[0],
        "engine_boot_count": session.read_memory("snesMemory", 0x7E5451, 1)[0],
        "reset_count": u16(reset), "reset_stage": reset[4],
        "reset_pc": u16(reset, 6), "reset_pbr": reset[5],
        "abort_stack_witness": [
            u16(session.read_memory("snesMemory", 0x7E56B0, 8), offset)
            for offset in (0, 2, 4)
        ],
        "skip_gate_sample": session.read_memory("snesMemory", 0x7E56B6, 2).hex(),
        "native_selected_slot": session.read_memory("snesMemory", 0x7E56B8, 1)[0],
        "native_selected_program": session.read_memory("snesMemory", 0x7E56B9, 1)[0],
        "native_selected_pc": session.read_memory("snesMemory", 0x7E56BA, 2)[0]
        | (session.read_memory("snesMemory", 0x7E56BA, 2)[1] << 8),
        "native_selection_count": session.read_memory("snesMemory", 0x7E56BC, 1)[0],
    }


def step_video_frame(session: object) -> None:
    for _ in range(20):
        run = session.run_frames(1)
        if run["framesAdvanced"] == 1 and not run.get("timedOut", False):
            return
    raise GateFailure(f"one-frame step made no progress: {run}")


def listed_constant(listing: Path, name: str) -> int:
    pattern = re.compile(
        rf"^;\s*{re.escape(name)}\s*=\s*\$([0-9A-Fa-f]+)\s+\(Constant\)\s*$"
    )
    for line in listing.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return int(match.group(1), 16)
    raise GateFailure(f"ROM-bound listing has no constant {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44001)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    map_path, _symbols = verified_symbol_map_for_rom(rom)
    listing_path = rom.with_suffix(".lst")
    variables_address = listed_constant(listing_path, "SAME_SCUMM_VARIABLES")
    slot_pc_address = listed_constant(listing_path, "SAME_SCUMM_C4_SLOT_PC")
    require(0x7E0000 <= variables_address <= 0x7EFFC0,
            f"variable table is outside WRAM: ${variables_address:06X}")
    abort_address = mapped_cpu_address_for_rom(
        rom, "ScummV5_C19_AbortOverride_Far", bank=0
    )
    after_abort_address = mapped_cpu_address_for_rom(
        rom, "ScummV5_Engine_Frame__skip_caller_recorded", bank=0
    )
    selected_address = mapped_cpu_address_for_rom(
        rom, "ScummV5_Engine_RunSelected", bank=0
    )
    complete_address = mapped_cpu_address_for_rom(
        rom, "ScummV5_Engine_Frame__complete_success", bank=0
    )
    index_boundaries = {
        name: mapped_cpu_address_for_rom(rom, f"ScummV5_C19_AbortOverride_Far__{name}", bank=0)
        for name in (
            "override_slot_read", "slot_status_read", "slot_depth_read",
            "slot_pc_write", "override_slot_clear", "override_pc_clear",
        )
    }
    output = (args.output or ROOT / "build" / f"scumm-c19-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C19-cutscene", "result": "running", "rom": str(rom),
        "rom_sha256": rom_hash, "fresh_power_on": True, "frame_limit": 240,
        "map": str(map_path),
        "map_sha256": hashlib.sha256(map_path.read_bytes()).hexdigest(),
        "symbols": {
            "ScummV5_C19_AbortOverride_Far": abort_address,
            "ScummV5_Engine_Frame__skip_done": after_abort_address,
            "ScummV5_Engine_RunSelected": selected_address,
            "ScummV5_Engine_Frame__complete_success": complete_address,
            "SAME_SCUMM_VARIABLES": variables_address,
            "SAME_SCUMM_C4_SLOT_PC": slot_pc_address,
            **{f"C19_index_{name}": address for name, address in index_boundaries.items()},
        },
        "donor_rom_used": False, "screenshots_captured": False, "audio_captured": False,
    }

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    try:
        with mcp_session.McpSession(
            rom=rom, mesen=nexen, cwd=ROOT, port=args.port, boot_wait=2.0,
            socket_timeout=30.0, stderr_log=output / "nexen-stderr.log",
        ) as session, ControllerInputLease(session) as controller:
            session.pause()
            session.tool("reset_emulator", {"power": True})
            session.pause()
            require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")
            start_frame = int(session.get_state()["frameCount"])
            fixture_entry: dict[str, object] = {"reason": "not-yet-reached"}
            bootstrap = None
            frames_advanced = 0
            for frames_advanced in range(1, 121):
                step_video_frame(session)
                common = session.read_memory("snesMemory", COMMON_ADDRESS, 0x64)
                active = session.read_memory("snesMemory", 0x7E235F, 1)[0]
                if common[0x03]:
                    raise GateFailure(
                        f"C19 profile raised SCUMM error {common[0x03]} during boot"
                    )
                if active == FIXTURE_ID and u16(common) == FIRST_YIELD_PC:
                    bootstrap = snapshot(session, variables_address)
                    fixture_entry = {
                        "reason": "exact-video-frame-boundary",
                        "framesAdvanced": frames_advanced,
                        "frameCount": int(session.get_state()["frameCount"]),
                    }
                    break
            require(bootstrap is not None,
                    "bounded exact-frame startup did not reach the first C19 yield")
            session.pause()
            report["bootstrap"] = {
                "snapshot": bootstrap,
                "cpu": session.get_cpu_state(),
                "ppu": session.get_ppu_state(),
                "io_4212": session.read_memory("snesMemory", 0x004212, 1).hex(),
                "io_4200": session.read_memory("snesMemory", 0x004200, 1).hex(),
                "hook": fixture_entry,
                "start_frame": start_frame,
                "actual_frames_advanced": frames_advanced,
            }
            require(bootstrap["fixture_request"] == FIXTURE_ID,
                    "C19 fixture was not selected by the generated diagnostic boot profile")
            require(bootstrap["error"] == 0,
                    f"C19 fixture dispatch entered error {bootstrap['error']}")
            require(bootstrap["reset_count"] == 1,
                    f"diagnostic profile performed an unexpected reset: {bootstrap['reset_count']}")
            report["fixture_selection"] = {
                "kind": "generated-c19-native-fixture-profile",
                "selected_by_engine_boot": True,
                "value": FIXTURE_ID,
                "validator_fixture_request_write": False,
            }
            first = dict(bootstrap)
            first["video_frame"] = session.get_state()["frameCount"]
            report["first_progress"] = [{
                key: first[key] for key in (
                    "pc", "status", "error", "last_opcode", "frame_count",
                    "frame_ops", "total_ops", "fixture_active", "program_select",
                    "stack_pointer", "override_pc", "override_slots", "slot_depths",
                )
            }]
            report["first_tick"] = first
            expected_first = {
                "pc": FIRST_YIELD_PC, "status": 2, "error": 0, "last_opcode": 0x80,
                "frame_count": 0, "frame_ops": 8, "total_ops": 8,
                "fixture_active": FIXTURE_ID, "program_select": FIXTURE_ID,
                "stack_pointer": 2,
                "data": [0, 0x1234, 7, 0, 0],
                "override_pc": [0, 0, OVERRIDE_PC, 0, 0],
                "override_slots": [0, 0, 1, 0, 0],
                "slot_depths": [0, 2] + [0] * 23,
                "cutscene_script_index": 0xFF,
            }
            for key, value in expected_first.items():
                require(first[key] == value, f"first {key}={first[key]!r}, expected {value!r}")
            require(first["variables"][0] == 7 and first["variables"][4] == 0
                    and first["variables"][6] == 0,
                    f"first C19 values are wrong: {first['variables']}")
            require(first["current_slot"] == 1,
                    f"C19 fixture is not running in the expected C4 activation: {first['current_slot']}")

            # Give neighboring records unmistakable sentinels after the fixture
            # has opened the target override. The skip handler must consume only
            # record 2; these are test preconditions, not gameplay state edits.
            # Depth 1 is the live outer cutscene owner and is legitimately
            # consumed by the final endCutscene. These sentinels are inactive
            # neighboring records outside the active depth/target.
            neighbor_indices = (0, 3, 4)
            neighbor_pcs = {index: 0xA100 + index for index in neighbor_indices}
            neighbor_slots = {index: 0x40 + index for index in neighbor_indices}
            for index in neighbor_indices:
                session.write_u16(C19_ADDRESS + 12 + index * 2, neighbor_pcs[index])
                session.write_u8(C19_ADDRESS + 22 + index, neighbor_slots[index])
            neighbors_before = {
                "pc": [
                    u16(session.read_memory("snesMemory", C19_ADDRESS + 12 + index * 2, 2))
                    for index in neighbor_indices
                ],
                "slot": [
                    session.read_memory("snesMemory", C19_ADDRESS + 22 + index, 1)[0]
                    for index in neighbor_indices
                ],
            }
            require(neighbors_before["pc"] == list(neighbor_pcs.values()),
                    "could not seed neighboring override-PC sentinels")
            require(neighbors_before["slot"] == list(neighbor_slots.values()),
                    "could not seed neighboring override-slot sentinels")

            abort_entry_hook = session.add_exec_hook(abort_address)
            after_abort_hook = session.add_exec_hook(after_abort_address)
            selected_hook = session.add_exec_hook(selected_address)
            complete_hook = session.add_exec_hook(complete_address)
            index_hooks = {
                name: session.add_exec_hook(address)
                for name, address in index_boundaries.items()
            }
            resumed_slot = int(first["current_slot"])
            resumed_pc_address = slot_pc_address + resumed_slot * 2
            pc_write_hook = session.add_write_hook(resumed_pc_address, resumed_pc_address + 1)
            gate_sample_hook = session.add_write_hook(0x7E56B6, 0x7E56B7)
            controller.hold(session.BTN_X)
            input_history: list[dict[str, object]] = []
            event_hits: list[dict[str, object]] = []
            for frame_index in range(1, 9):
                step_video_frame(session)
                input_bytes = session.read_memory("snesMemory", 0x7E2200, 8)
                input_history.append({
                    "frame_index": frame_index,
                    "held": u16(input_bytes, 0),
                    "previous": u16(input_bytes, 2),
                    "pressed": u16(input_bytes, 4),
                    "released": u16(input_bytes, 6),
                    "video_frame": int(session.get_state()["frameCount"]),
                    "gate_sample": session.read_memory("snesMemory", 0x7E56B6, 2).hex(),
                })
                rows = session.drain_notifications(timeout=0.05)
                event_hits.extend(
                    item["params"] for item in rows
                    if item.get("method") == "notifications/mesen/hookFired"
                )
                if any(int(item.get("handle", -1)) == abort_entry_hook for item in event_hits):
                    break
            controller.release()
            require(any(int(item.get("handle", -1)) == abort_entry_hook for item in event_hits),
                    f"normal X input did not execute cutscene abort: {input_history}; {event_hits}")
            gate_sample_events = [item for item in event_hits
                                  if int(item.get("handle", -1)) == gate_sample_hook]
            require(any(int(item.get("address", -1)) == 0x7E56B6
                        and (int(item.get("value", -1)) & 0xFF) == 0x40
                        for item in gate_sample_events),
                    f"no event-time store proves the X edge reached the native gate: {gate_sample_events}")
            session.remove_hook(after_abort_hook)
            hit_handles = {int(item.get("handle", -1)) for item in event_hits}
            for handle, label in ((abort_entry_hook, "cutscene abort entry"),
                                  (after_abort_hook, "cutscene abort return")):
                require(handle in hit_handles,
                        f"{label} was not executed: {event_hits}")
            reached_indices = [
                name for name, handle in index_hooks.items()
                if handle in hit_handles
            ]
            require(set(reached_indices) == set(index_hooks),
                    f"not all native descriptor index boundaries executed: {reached_indices}")
            abort_cycles = [int(item.get("cycleCount", -1)) for item in event_hits
                            if int(item.get("handle", -1)) == abort_entry_hook]
            require(abort_cycles, "no event-time native abort-entry observation")
            abort_cycle = min(abort_cycles)
            return_cycles = [int(item.get("cycleCount", -1)) for item in event_hits
                             if int(item.get("handle", -1)) == after_abort_hook
                             and int(item.get("cycleCount", -1)) > abort_cycle]
            require(return_cycles, "no event-time native abort-return observation")
            return_cycle = min(return_cycles)
            selected_events = [item for item in event_hits
                               if int(item.get("handle", -1)) == selected_hook
                               and int(item.get("cycleCount", -1)) > return_cycle]
            completion_events = [item for item in event_hits
                                 if int(item.get("handle", -1)) == complete_hook
                                 and int(item.get("cycleCount", -1)) > return_cycle]
            require(len(selected_events) == 1,
                    f"resumed activation selected {len(selected_events)} times after abort: {selected_events}")
            # This shared return label is also reached while nested C18/outer
            # frame bookkeeping unwinds, so it is not an activation counter.
            # The slot-load hook and fixture continuation marker below are
            # the one-resume assertions; retain every completion hit as
            # supporting event-time evidence without assigning it that role.
            require(completion_events,
                    "resumed activation did not reach frame completion")
            pc_write_events = [
                item for item in event_hits if int(item.get("handle", -1)) == pc_write_hook
            ]
            saved_low = OVERRIDE_PC & 0xFF
            saved_high = OVERRIDE_PC >> 8
            saved_pc_observed = any(
                int(item.get("address", -1)) == resumed_pc_address
                and (int(item.get("value", -1)) & 0xFFFF) == OVERRIDE_PC
                for item in pc_write_events
            ) or any(
                int(first_event.get("address", -1)) == resumed_pc_address
                and (int(first_event.get("value", -1)) & 0xFF) == saved_low
                and int(second_event.get("address", -1)) == resumed_pc_address + 1
                and (int(second_event.get("value", -1)) & 0xFF) == saved_high
                for first_event, second_event in zip(pc_write_events, pc_write_events[1:])
            )
            require(saved_pc_observed,
                    f"native slot descriptor never received resume PC ${OVERRIDE_PC:04X}: {pc_write_events}")
            after_abort = snapshot(session, variables_address)
            abort_stack = after_abort["abort_stack_witness"]
            entry_sp, pre_rtl_sp, caller_sp = abort_stack
            stack_balanced = (
                ((entry_sp + 1) & 0xFFFF) == pre_rtl_sp
                and ((pre_rtl_sp + 3) & 0xFFFF) == caller_sp
            )
            require(stack_balanced,
                    f"C19 JSL/RTL frame did not unwind exactly: witness={abort_stack}")
            neighbors_after = {
                "pc": [
                    u16(session.read_memory("snesMemory", C19_ADDRESS + 12 + index * 2, 2))
                    for index in neighbor_indices
                ],
                "slot": [
                    session.read_memory("snesMemory", C19_ADDRESS + 22 + index, 1)[0]
                    for index in neighbor_indices
                ],
            }
            report["skip_abort_observation"] = {
                "controller_input_frames": input_history,
                "event_time_gate_store": gate_sample_events,
                "event_hits": event_hits,
                "reached_index_boundaries": reached_indices,
                "pc_write_events": pc_write_events,
                "saved_pc_observed": saved_pc_observed,
                "neighbors_before": neighbors_before,
                "neighbors_after": neighbors_after,
                "after_abort": after_abort,
                "stack_witness": abort_stack,
            }
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            require(neighbors_after == neighbors_before,
                    f"abort modified neighboring override records: {neighbors_after}")
            require(after_abort["override_pc"][2] == 0
                    and after_abort["override_slots"][2] == 0,
                    "selected override record was not consumed")
            report["skip_abort"] = {
                "input": {"port": 0, "button": "X", "mask": session.BTN_X,
                          "frame_state": input_history},
                "event_hits": event_hits,
                "saved_resume_pc_observed": OVERRIDE_PC,
                "resumed_slot": resumed_slot,
                "resumed_slot_pc_address": resumed_pc_address,
                "slot_pc_write_events": pc_write_events,
                "stack_balanced": stack_balanced,
                "native_stack_witness": abort_stack,
                "neighbors_before": neighbors_before,
                "neighbors_after": neighbors_after,
                "after_abort": after_abort,
            }

            after_resume = after_abort
            report["resume_boundary"] = {
                "hook": "ScummV5_Engine_RunSelected",
                "selected_by_C4": selected_events[0],
                "activation_selection_count_after_abort": len(selected_events),
                "shared_completion_boundary_events": completion_events,
                "vm_program": after_resume["program_select"],
                "resumed_slot": after_resume["current_slot"],
                "saved_resume_pc": OVERRIDE_PC,
                "final_vm_pc": after_resume["pc"],
                "skip_only_marker_v6": after_resume["variables"][6],
                "resume_count": len(selected_events),
                "native_index_boundaries_executed": reached_indices,
            }
            require(after_resume["error"] == 0, "C19 skip raised a SCUMM error")
            require(after_resume["variables"][6] == 1,
                    "skip-only continuation marker did not execute exactly once")
            require(after_resume["stack_pointer"] == 0,
                    "cutscene stack did not unwind after skip")
            require(after_resume["native_selected_slot"] == resumed_slot
                    and after_resume["native_selected_program"] == FIXTURE_ID
                    and after_resume["native_selected_pc"] == OVERRIDE_PC,
                    "native C4 handoff did not load the saved slot/program/PC exactly")
            report["after_resume"] = after_resume
            session.remove_hook(abort_entry_hook)
            session.remove_hook(selected_hook)
            session.remove_hook(complete_hook)
            session.remove_hook(pc_write_hook)
            session.remove_hook(gate_sample_hook)
            for hook in index_hooks.values():
                session.remove_hook(hook)

            # The selected tail has just yielded at FINAL_PC. Do not schedule it
            # again: that would test exact-EOF policy, not the skip ABI.
            terminal = dict(after_resume)
            terminal["video_frame"] = session.get_state()["frameCount"]
            terminal["frames_since_first_yield"] = (
                terminal["video_frame"] - first["video_frame"]
            )
            report["terminal"] = terminal
            expected_terminal = {**expected_first,
                "pc": FINAL_PC, "frame_ops": 6,
                "stack_pointer": 0,
            }
            terminal_keys = (
                "pc", "status", "error", "last_opcode", "frame_ops",
                "fixture_active", "program_select",
                "stack_pointer", "data", "cutscene_script_index",
            )
            for key in terminal_keys:
                value = expected_terminal[key]
                require(terminal[key] == value, f"terminal {key}={terminal[key]!r}, expected {value!r}")
            require(terminal["variables"][0] == 7
                    and terminal["variables"][4] == 0
                    and terminal["variables"][6] == 1,
                    f"terminal C19 variables are wrong: {terminal['variables']}")
            require(terminal["override_pc"][2] == 0
                    and terminal["override_slots"][2] == 0,
                    "selected override record reappeared after resume")
            require(0 <= terminal["frames_since_first_yield"] <= 10,
                    "skip gate exceeded ten frames after the first yielded boundary")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C19 SCUMM cutscene: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("C19 SCUMM cutscene: PASS (nested data, override markers, exact unwind)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
