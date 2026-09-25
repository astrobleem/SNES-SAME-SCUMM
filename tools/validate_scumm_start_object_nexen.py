#!/usr/bin/env python3
"""Copyright-free SNES conformance for production v5 object-script execution."""

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
VARIABLES = 0x7E0800  # Generated MAXS include owns this profile's word table.
SLOT_STATUS = 0x7E2380
SLOT_NUMBER = 0x7E2399
SLOT_WHERE = 0x7E7F46
SLOT_OBJECT = 0x7E7F5F
SLOT_PC = 0x7E23E4
START_OBJECT = 0x7E7F91
START_TRACE_COUNT = 0x7E7ED7
START_TRACE = 0x7E7ED8
ERROR = 0x7E2303
NEST_DEPTH = 0x7FF465
ACTIVE_ROOM = 0x7FF2BF
PENDING_ROOM = 0x7FF2C1
ROOM_PHASE = 0x7FF2C2
ACTIVE_ENGINE = 0x7E2220
ENGINE_LIFECYCLE = 0x7E2221
FIXTURE_READY = 0x7E5601
CURRENT_PROGRAM = 0x7E2362
CURRENT_PC = 0x7E2300
CURRENT_STATUS = 0x7E2302
FRAME_OPS = 0x7E230A
NATIVE_DIAG = 0x7E7FDA


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45725)
    parser.add_argument(
        "--case", choices=("normal", "replacement", "replacement-long", "nested"),
        default="normal"
    )
    parser.add_argument(
        "--trace", action="store_true",
        help="retain compact per-frame slot/context observations for diagnosis",
    )
    args = parser.parse_args()
    replacement_case = args.case in {"replacement", "replacement-long"}
    if not args.nexen.is_file() or not os.access(args.nexen, os.X_OK):
        raise RuntimeError("Nexen unavailable")
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=2.0, socket_timeout=60.0,
        stderr_log=args.output.with_suffix(".stderr.log"),
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        from validate_scumm_startup42_nexen import mapped_cpu_address_for_rom
        # The initial StartObject is a normal nested child. Its same-object
        # replacement must then take the bank-0 JSL/RTL no-parent adapter.
        # Resolve both boundaries only from this ROM's verified map/listing.
        nested_adapter = session.add_exec_hook(mapped_cpu_address_for_rom(
            args.rom.resolve(), "ScummV5_M25A_RunNestedChildFar", bank=0))
        replacement_adapter = session.add_exec_hook(mapped_cpu_address_for_rom(
            args.rom.resolve(), "ScummV5_C4_RunAllocatedNoParent_FarEntry", bank=0))
        replacement_adapter_address = mapped_cpu_address_for_rom(
            args.rom.resolve(), "ScummV5_C4_RunAllocatedNoParent_FarEntry", bank=0)
        adapter_hits = {nested_adapter: 0, replacement_adapter: 0}
        replacement_frame_ops: list[int] = []
        replacement_call_stack: dict[str, int] | None = None
        replacement_yield = None
        timeline = []
        for frame in range(1, 180):
            session.run_frames(1)
            for event in session.drain_notifications(0.01):
                if event.get("method") == "notifications/mesen/hookFired":
                    handle = event.get("params", {}).get("handle")
                    if handle in adapter_hits:
                        adapter_hits[handle] += 1
            variables = session.read_memory("snesMemory", VARIABLES, 32)
            error = session.read_memory("snesMemory", ERROR, 1)[0]
            start_count = session.read_memory("snesMemory", START_OBJECT + 12, 1)[0]
            room_now = session.read_memory("snesMemory", ACTIVE_ROOM, 1)[0]
            phase_now = session.read_memory("snesMemory", ROOM_PHASE, 1)[0]
            lifecycle_now = session.read_memory(
                "snesMemory", ENGINE_LIFECYCLE, 1
            )[0]
            fixture_ready = session.read_memory("snesMemory", FIXTURE_READY, 1)[0]
            ready = (room_now == 49 and phase_now == 0 and lifecycle_now == 2
                     and fixture_ready == 1)
            if args.trace:
                statuses_now = session.read_memory("snesMemory", SLOT_STATUS, 25)
                numbers_now = session.read_memory("snesMemory", SLOT_NUMBER, 25)
                programs_now = session.read_memory("snesMemory", 0x7E23B2, 25)
                pcs_now = session.read_memory("snesMemory", SLOT_PC, 50)
                wheres_now = session.read_memory("snesMemory", SLOT_WHERE, 25)
                timeline.append({
                    "frame": frame,
                    "room": room_now,
                    "phase": phase_now,
                    "lifecycle": lifecycle_now,
                    "error": error,
                    "fixture_ready": fixture_ready,
                    "start_count": start_count,
                    "depth": session.read_memory("snesMemory", NEST_DEPTH, 1)[0],
                    "current_slot": session.read_memory("snesMemory", 0x7E2A88, 1)[0],
                    "program": session.read_memory("snesMemory", CURRENT_PROGRAM, 1)[0],
                    "pc": u16(session.read_memory("snesMemory", CURRENT_PC, 2)),
                    "globals10_13": [u16(variables, index * 2)
                                      for index in range(10, 14)],
                    "slots": [
                        {"slot": index, "status": statuses_now[index],
                         "number": numbers_now[index], "program": programs_now[index],
                         "pc": u16(pcs_now, index * 2), "where": wheres_now[index]}
                        for index in range(25) if statuses_now[index]
                    ],
                })
            if not ready:
                continue
            if replacement_case:
                values = [u16(variables, index * 2) for index in (10, 11)]
                if error or values[1] == 0xDEAD:
                    break
                if start_count >= 2 and values[0] == 0xBEEF:
                    start = session.read_memory("snesMemory", START_OBJECT, 23)
                    replacement_slot = start[10]
                    statuses = session.read_memory("snesMemory", SLOT_STATUS, 25)
                    programs = session.read_memory("snesMemory", 0x7E23B2, 25)
                    pcs = session.read_memory("snesMemory", SLOT_PC, 50)
                    locals_now = session.read_memory(
                        "snesMemory", 0x7E2448, 25 * 64
                    )
                    replacement_yield = {
                        "slot": replacement_slot,
                        "status": statuses[replacement_slot],
                        "program": programs[replacement_slot],
                        "pc": u16(pcs, replacement_slot * 2),
                        "local0": u16(locals_now, replacement_slot * 64),
                    }
                    break
            elif args.case == "nested":
                values = [u16(variables, index * 2) for index in (10, 11)]
                depth = session.read_memory("snesMemory", NEST_DEPTH, 1)[0]
                if error or (values == [0xCAFE, 1] and depth == 0):
                    break
            elif args.trace and start_count > 4:
                break
            elif error or all(u16(variables, index * 2) for index in range(10, 14)):
                break
        start = session.read_memory("snesMemory", START_OBJECT, 23)
        native_diag = session.read_memory("snesMemory", NATIVE_DIAG, 12)
        native_values = [u16(native_diag, index) for index in range(0, 12, 2)]
        if replacement_case:
            (caller_sp, adapter_sp, adapter_return_sp, caller_return_sp,
             slot_index, native_frame_ops) = native_values
            replacement_frame_ops.append(native_frame_ops)
            replacement_call_stack = {
                "caller_sp_before_jsl": caller_sp,
                "adapter_sp_at_entry": adapter_sp,
                "adapter_sp_after_jsr_rts": adapter_return_sp,
                "caller_sp_after_rtl": caller_return_sp,
                "slot_index_at_descriptor_access": slot_index,
                "live_frame_ops_at_handoff": native_frame_ops,
                "jsl_entry_delta": (adapter_sp - caller_sp) & 0xFFFF,
                "inner_jsr_rts_delta": (adapter_return_sp - adapter_sp) & 0xFFFF,
                "caller_return_delta": (caller_return_sp - caller_sp) & 0xFFFF,
            }
        nest_depth = session.read_memory("snesMemory", NEST_DEPTH, 1)[0]
        status = session.read_memory("snesMemory", SLOT_STATUS, 25)
        numbers = session.read_memory("snesMemory", SLOT_NUMBER, 25)
        wheres = session.read_memory("snesMemory", SLOT_WHERE, 25)
        objects = session.read_memory("snesMemory", SLOT_OBJECT, 50)
        pcs = session.read_memory("snesMemory", SLOT_PC, 50)
        trace_count = session.read_memory("snesMemory", START_TRACE_COUNT, 1)[0]
        trace_raw = session.read_memory(
            "snesMemory", START_TRACE, min(trace_count, 16) * 4
        )
        trace = [list(trace_raw[index:index + 4])
                 for index in range(0, len(trace_raw), 4)]
        scenario_child = session.read_memory("snesMemory", 0x7E5607, 7)
        locals_raw = session.read_memory("snesMemory", 0x7E2448, 25 * 64)
        if replacement_case and replacement_yield is not None:
            for _ in range(5):
                session.run_frames(1)
                final_status = session.read_memory(
                    "snesMemory", SLOT_STATUS + replacement_yield["slot"], 1
                )[0]
                if final_status == 0:
                    break
            variables = session.read_memory("snesMemory", VARIABLES, 32)
            error = session.read_memory("snesMemory", ERROR, 1)[0]
            status = session.read_memory("snesMemory", SLOT_STATUS, 25)
            wheres = session.read_memory("snesMemory", SLOT_WHERE, 25)
        runtime_state = {
            "active_engine": session.read_memory("snesMemory", ACTIVE_ENGINE, 1)[0],
            "engine_lifecycle": session.read_memory("snesMemory", ENGINE_LIFECYCLE, 1)[0],
            "fixture_ready": session.read_memory("snesMemory", FIXTURE_READY, 1)[0],
            "active_room": session.read_memory("snesMemory", ACTIVE_ROOM, 1)[0],
            "pending_room": session.read_memory("snesMemory", PENDING_ROOM, 1)[0],
            "room_phase": session.read_memory("snesMemory", ROOM_PHASE, 1)[0],
            "current_program": session.read_memory("snesMemory", CURRENT_PROGRAM, 1)[0],
            "current_pc": u16(session.read_memory("snesMemory", CURRENT_PC, 2)),
            "current_status": session.read_memory("snesMemory", CURRENT_STATUS, 1)[0],
        }
    slots = [{
        "slot": index, "status": status[index], "number": numbers[index],
        "where": wheres[index], "object": u16(objects, index * 2),
        "pc": u16(pcs, index * 2),
    } for index in range(25) if status[index] != 0]
    observed = [u16(variables, index * 2) for index in range(10, 14)]
    if replacement_case:
        observed_frame_ops = max(replacement_frame_ops, default=0)
        assertions = {
            "fresh_verb_received_argument": observed[0] == 0xBEEF,
            "old_verb_continuation_did_not_run": observed[1] == 0,
            "both_authored_verb_entries_started": start[12] == 2,
            "replacement_entry_is_verb_8": start[2] == 8,
            "replacement_reused_stopped_activation_slot": (
                start[10] == start[22] and start[22] != 0
            ),
            "replacement_has_no_self_parent": nest_depth == 0,
            "initial_child_uses_nested_adapter_once": adapter_hits[nested_adapter] == 1,
            "replacement_uses_no_parent_far_adapter_once": (
                adapter_hits[replacement_adapter] == 1
            ),
            "replacement_after_256_native_operations": (
                args.case != "replacement-long"
                or (observed_frame_ops >= 256
                    and observed_frame_ops <= 0x1000)
            ),
            "frame_ops_high_byte_nonzero": (
                args.case != "replacement-long"
                or any(value >> 8 for value in replacement_frame_ops)
            ),
            "replacement_slot_index_zero_extended": (
                replacement_call_stack is not None
                and replacement_call_stack["slot_index_at_descriptor_access"]
                == start[22]
                and replacement_call_stack["slot_index_at_descriptor_access"] < 0x100
            ),
            "far_no_parent_call_frame_balanced": (
                replacement_call_stack is not None
                and adapter_hits[replacement_adapter] == 1
                and replacement_call_stack["jsl_entry_delta"] == 0xFFFD
                and replacement_call_stack["inner_jsr_rts_delta"] == 0
                and replacement_call_stack["caller_return_delta"] == 0
            ),
            "replacement_local_argument_preserved": (
                replacement_yield is not None
                and replacement_yield["local0"] == 0xBEEF
            ),
            "replacement_yielded_from_authored_entry": (
                replacement_yield is not None
                and replacement_yield["status"] == 2
                and replacement_yield["program"] == start[3]
                and replacement_yield["pc"] == u16(start, 4) + 6
            ),
            "replacement_resolved_verb_is_8": start[2] == 8,
            "replacement_entry_matches_loaded_slot": (
                replacement_yield is not None
                and replacement_yield["pc"] == u16(start, 4) + 6
            ),
            "no_runnable_object_activation_remains": all(
                item["where"] != 1 or item["status"] in (0, 4)
                for item in slots
            ),
            "no_runtime_error": error == 0,
        }
        if not all(assertions.values()):
            raise RuntimeError(
                f"same-object replacement failed: {assertions}; values={observed}; "
                f"start={list(start)}; child={list(scenario_child)}; "
                f"depth={nest_depth}; slots={slots}; trace={trace}; "
                f"state={runtime_state}; yield={replacement_yield}; "
                f"adapter_hits={adapter_hits}; "
                f"frame_ops={replacement_frame_ops}; "
                f"call_stack={replacement_call_stack}; "
                f"adapter_address={replacement_adapter_address:06X}; "
                f"native_diag={native_values}"
            )
        report = {
            "gate": ("M25-startObject-long-operation-same-activation-replacement-SNES"
                     if args.case == "replacement-long"
                     else "M25-startObject-same-activation-replacement-SNES"),
            "result": "pass", "fresh_power_on": True, "debugger_writes": 0,
            "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
            "frame": frame, "global10_argument_result": observed[0],
            "global11_old_continuation": observed[1],
            "start_object_exec_count": start[12],
            "replacement_entry_offset": u16(start, 4),
            "replaced_slot": start[22],
            "replacement_yield": replacement_yield,
            "frame_ops_at_replacement_adapter": replacement_frame_ops,
            "max_frame_ops_at_replacement_adapter": observed_frame_ops,
            "replacement_call_stack": replacement_call_stack,
            "scenario_child": list(scenario_child), "slots": slots,
            "native_adapter_hits": {
                "nested": adapter_hits[nested_adapter],
                "replacement_no_parent": adapter_hits[replacement_adapter],
            },
            "trace_count": trace_count, "trace": trace,
            "assertions": assertions,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"result": "pass", "output": str(args.output)}, sort_keys=True))
        return 0
    if args.case == "nested":
        assertions = {
            "child_received_authored_argument": observed[0] == 0xCAFE,
            "parent_continuation_resumed_once": observed[1] == 1,
            "both_distinct_object_activations_started": start[12] == 2,
            "nested_depth_returned_to_zero": nest_depth == 0,
            "ordinary_nested_adapter_used_twice": adapter_hits[nested_adapter] == 2,
            "replacement_no_parent_adapter_not_used": adapter_hits[replacement_adapter] == 0,
            "no_runtime_error": error == 0,
            "no_live_object_activation_remains": all(
                item["where"] != 1 or item["status"] in (0, 4)
                for item in slots
            ),
        }
        if not all(assertions.values()):
            raise RuntimeError(
                f"different-object nested start failed: {assertions}; "
                f"values={observed}; start={list(start)}; depth={nest_depth}; "
                f"slots={slots}; trace={trace}; state={runtime_state}; "
                f"adapter_hits={adapter_hits}"
            )
        report = {
            "gate": "M25-startObject-different-activation-nesting-SNES",
            "result": "pass", "fresh_power_on": True, "debugger_writes": 0,
            "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
            "frame": frame, "variables_10_11": observed[:2],
            "start_object_exec_count": start[12], "slots": slots,
            "native_adapter_hits": {
                "nested": adapter_hits[nested_adapter],
                "replacement_no_parent": adapter_hits[replacement_adapter],
            },
            "trace_count": trace_count, "trace": trace,
            "assertions": assertions,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"result": "pass", "output": str(args.output)}, sort_keys=True))
        return 0
    if args.trace:
        print(json.dumps({"frame": frame, "timeline": timeline,
                          "variables_10_13": observed, "error": error,
                          "nest_depth": nest_depth, "slots": slots},
                         sort_keys=True))
    assertions = {
        "distinct_programs": observed == [0xA00A, 0xA008, 0xA0FF, 0xB00A],
        "four_object_programs_executed": start[12] == 4,
        "missing_entry_did_not_fault": error == 0,
        "missing_entry_did_not_leave_runnable_object_slot": all(
            item["where"] != 1 or item["status"] in (0, 4)
            for item in slots
        ),
        "nested_depth_returned_to_zero": nest_depth == 0,
    }
    if not all(assertions.values()):
        raise RuntimeError(
            f"startObject conformance failed: {assertions}; values={observed}; "
            f"exec={start[12]}; depth={nest_depth}; slots={slots}; trace={trace}"
        )
    report = {
        "gate": "M25-startObject-copyright-free-SNES",
        "result": "pass", "fresh_power_on": True, "debugger_writes": 0,
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "frame": frame, "variables_10_13": observed,
        "start_object_exec_count": start[12], "slots": slots,
        "trace_count": trace_count, "trace": trace, "assertions": assertions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
