#!/usr/bin/env python3
"""Native M23A control: a global requester resumes in its original slot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/"
    "linux-x64/publish/Nexen"
)
ROOM = 0x7FF2BF
PHASE = 0x7FF2C2
RETURN_VALID = 0x7FF467
RETURN_SLOT = 0x7FF468
RETURN_MODE = 0x7FF469
RETURN_PROGRAM = 0x7FF2C3
RETURN_PC = 0x7FF2E5
VALIDATION_COUNT = 0x7FF2C6
ERROR = 0x7E2303
LIFECYCLE = 0x7E2221
VARIABLES = 0x7E0800
STATUS = 0x7E2380
NUMBER = 0x7E2399
PROGRAM = 0x7E23B2
WHERE = 0x7E7F46
PC = 0x7E23E4
LOCALS = 0x7E2448
SLOT_STRIDE = 0x40
PENDING_ROOM = 0x7FF2C1
ACTIVE_RECORD = 0x7FF2BE
REQUEST_COUNT = 0x7FF2C5
PENDING_RECORD = 0x7FF2C0
LIFECYCLE_TRACE = 0x7FF2D7


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45741)
    args = parser.parse_args()
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK),
            f"Nexen unavailable: {args.nexen}")
    require(args.rom.is_file() and args.manifest.is_file(), "ROM or manifest missing")
    manifest = json.loads(args.manifest.read_text())
    require(manifest.get("room_provenance", "").startswith("synthetic fixture"),
            "native control must identify both rooms as synthetic")
    require({record["room"] for record in manifest["records"]} >= {49, 50},
            "global-return control is missing its destination room")

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    snapshots: list[dict[str, object]] = []
    observed_valid_transaction = None
    commit_events: list[dict[str, int]] = []
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=2.0, socket_timeout=60.0,
        stderr_log=args.output.with_suffix(".stderr.log"),
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0, "cold reset not at frame zero")
        from validate_scumm_startup42_nexen import mapped_cpu_address_for_rom
        commit_hooks = {
            session.add_exec_hook(mapped_cpu_address_for_rom(
                args.rom.resolve(), "ScummV5_M24RB_Far_CommitRoom", bank=9
            )): "room",
            session.add_exec_hook(mapped_cpu_address_for_rom(
                args.rom.resolve(), "ScummV5_M24RB_Far_CommitNullRoom", bank=9
            )): "null",
        }
        last_validation_count = 0
        destination_entry_seen = False
        continuation_seen_frame: int | None = None
        continuation_later_frames = 0
        for frame in range(1, 181):
            result = session.run_frames(1)
            require(result["framesAdvanced"] == 1 and not result["timedOut"],
                    f"frame did not advance: {result}")
            for event in session.drain_notifications(0.005):
                if event.get("method") != "notifications/mesen/hookFired":
                    continue
                handle = event.get("params", {}).get("handle")
                if handle in commit_hooks:
                    commit_events.append({
                        "kind": 1 if commit_hooks[handle] == "room" else 0,
                        "frame": frame,
                        "pending_room": session.read_memory(
                            "snesMemory", PENDING_ROOM, 1)[0],
                        "pending_record": session.read_memory(
                            "snesMemory", PENDING_RECORD, 1)[0],
                        "active_record": session.read_memory(
                            "snesMemory", ACTIVE_RECORD, 1)[0],
                        "request_count": session.read_memory(
                            "snesMemory", REQUEST_COUNT, 1)[0],
                        "lifecycle_trace": list(session.read_memory(
                            "snesMemory", LIFECYCLE_TRACE, 14)),
                    })
            room = session.read_memory("snesMemory", ROOM, 1)[0]
            phase = session.read_memory("snesMemory", PHASE, 1)[0]
            error = session.read_memory("snesMemory", ERROR, 1)[0]
            count = session.read_memory("snesMemory", VALIDATION_COUNT, 1)[0]
            valid = session.read_memory("snesMemory", RETURN_VALID, 1)[0]
            return_slot = session.read_memory("snesMemory", RETURN_SLOT, 1)[0]
            numbers = session.read_memory("snesMemory", NUMBER, 25)
            statuses = session.read_memory("snesMemory", STATUS, 25)
            programs = session.read_memory("snesMemory", PROGRAM, 25)
            wheres = session.read_memory("snesMemory", WHERE, 25)
            pcs = session.read_memory("snesMemory", PC, 50)
            locals_raw = session.read_memory("snesMemory", LOCALS, 25 * SLOT_STRIDE)
            globals_raw = session.read_memory("snesMemory", VARIABLES, 26)
            globals_now = [u16(globals_raw, i * 2) for i in range(13)]
            global_slots = []
            for slot in range(1, 25):
                if numbers[slot] == 75 and wheres[slot] == 2:
                    global_slots.append({
                        "slot": slot, "status": statuses[slot],
                        "program": programs[slot],
                        "pc": u16(pcs, slot * 2),
                        "local0": u16(locals_raw, slot * SLOT_STRIDE),
                    })
            if count > last_validation_count:
                validation_observation = {
                    "frame": frame, "validation_count": count,
                    "room": room, "phase": phase,
                    "return_valid_after_storage_validation": valid,
                    "return_slot": return_slot,
                    "return_mode": session.read_memory(
                        "snesMemory", RETURN_MODE, 1)[0],
                    "return_program": session.read_memory(
                        "snesMemory", RETURN_PROGRAM, 1)[0],
                    "return_pc": u16(session.read_memory(
                        "snesMemory", RETURN_PC, 2)),
                    "global_requester": global_slots,
                }
                if valid == 1 and global_slots:
                    observed_valid_transaction = validation_observation
                last_validation_count = count
            if frame <= 40 or room in (49, 50) or phase in (4, 5):
                snapshots.append({
                    "frame": frame, "room": room, "phase": phase,
                    "pending_room": session.read_memory("snesMemory", PENDING_ROOM, 1)[0],
                    "pending_record": session.read_memory("snesMemory", PENDING_RECORD, 1)[0],
                    "active_record": session.read_memory("snesMemory", ACTIVE_RECORD, 1)[0],
                    "request_count": session.read_memory("snesMemory", REQUEST_COUNT, 1)[0],
                    "lifecycle_trace": list(session.read_memory(
                        "snesMemory", LIFECYCLE_TRACE, 14)),
                    "error": error, "lifecycle": session.read_memory(
                        "snesMemory", LIFECYCLE, 1)[0],
                    "current_slot": session.read_memory("snesMemory", 0x7E2A88, 1)[0],
                    "program_select": session.read_memory("snesMemory", 0x7E2362, 1)[0],
                    "shared_pc": u16(session.read_memory("snesMemory", 0x7E2300, 2)),
                    "shared_status": session.read_memory("snesMemory", 0x7E2380, 1)[0],
                    "return_mode": session.read_memory("snesMemory", 0x7E2363, 1)[0],
                    "c18_nested": session.read_memory("snesMemory", 0x7FD335, 1)[0],
                    "nest_depth": session.read_memory("snesMemory", 0x7FF465, 1)[0],
                    "parent_slot": session.read_memory("snesMemory", 0x7E2A8C, 1)[0],
                    "frame_entry_sp": u16(session.read_memory("snesMemory", 0x7E7FCA, 2)),
                    "valid": valid, "return_slot": return_slot,
                    "saved_return_mode": session.read_memory(
                        "snesMemory", RETURN_MODE, 1)[0],
                    "saved_return_program": session.read_memory(
                        "snesMemory", RETURN_PROGRAM, 1)[0],
                    "saved_return_pc": u16(session.read_memory(
                        "snesMemory", RETURN_PC, 2)),
                    "validation_count": count, "global_slots": global_slots,
                    "V10": globals_now[10], "V11": globals_now[11],
                    "V12": globals_now[12],
                })
            require(error == 0,
                    f"SCUMM error ${error:02X} at frame {frame}; "
                    f"room={room} phase={phase} valid={valid} slot={return_slot}; "
                    f"program={session.read_memory('snesMemory', 0x7E2362, 1)[0]} "
                    f"pc={u16(session.read_memory('snesMemory', 0x7E2300, 2))}; "
                    f"slots={global_slots}; trace={session.read_memory('snesMemory', LIFECYCLE_TRACE, 14)}")
            if frame >= 6 and globals_now[12] == 0xBEEF:
                destination_entry_seen = True
            if destination_entry_seen and globals_now[11] == 1:
                if continuation_seen_frame is None:
                    continuation_seen_frame = frame
                elif frame > continuation_seen_frame:
                    continuation_later_frames += 1
                if continuation_later_frames >= 3:
                    break

        final_error = session.read_memory("snesMemory", ERROR, 1)[0]
        final_lifecycle = session.read_memory("snesMemory", LIFECYCLE, 1)[0]
        final_room = session.read_memory("snesMemory", ROOM, 1)[0]
        final_phase = session.read_memory("snesMemory", PHASE, 1)[0]
        final_validation = session.read_memory("snesMemory", VALIDATION_COUNT, 1)[0]
        final_globals = [u16(session.read_memory("snesMemory", VARIABLES, 26), i * 2)
                         for i in range(13)]
        final_slots = []
        numbers = session.read_memory("snesMemory", NUMBER, 25)
        statuses = session.read_memory("snesMemory", STATUS, 25)
        programs = session.read_memory("snesMemory", PROGRAM, 25)
        wheres = session.read_memory("snesMemory", WHERE, 25)
        pcs = session.read_memory("snesMemory", PC, 50)
        locals_raw = session.read_memory("snesMemory", LOCALS, 25 * SLOT_STRIDE)
        for slot in range(1, 25):
            if numbers[slot] != 0 or statuses[slot] not in (0, 4):
                final_slots.append({
                    "slot": slot, "number": numbers[slot],
                    "status": statuses[slot], "program": programs[slot],
                    "where": wheres[slot], "pc": u16(pcs, slot * 2),
                    "local0": u16(locals_raw, slot * SLOT_STRIDE),
                })

    if not destination_entry_seen or final_globals[12] != 0xBEEF:
        failure = {
            "result": "fail", "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
            "destination_entry_seen": destination_entry_seen,
            "final_room": final_room, "final_phase": final_phase,
            "validation_count": final_validation, "globals": final_globals,
            "slots": final_slots, "commit_events": commit_events,
            "timeline": snapshots,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n")
        raise RuntimeError(
            f"destination ENCD marker missing: room={final_room} phase={final_phase}; "
            f"evidence written to {args.output}")
    if final_error != 0 or final_lifecycle != 2:
        failure = {
            "result": "fail", "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
            "reason": "runtime unhealthy after destination ENCD and global continuation",
            "final": {
                "room": final_room, "phase": final_phase,
                "error": final_error, "lifecycle": final_lifecycle,
                "globals": final_globals, "validation_count": final_validation,
                "live_slots": final_slots,
            },
            "observed_global_request_storage_validation": observed_valid_transaction,
            "timeline": snapshots, "commit_events": commit_events,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n")
        raise RuntimeError(
            f"runtime unhealthy: error={final_error} lifecycle={final_lifecycle}; "
            f"room={final_room} phase={final_phase} globals={final_globals}; "
            f"evidence written to {args.output}")
    require(final_globals[10] == 0x1234,
            f"global resumed in wrong activation locals: V10=${final_globals[10]:04X}")
    require(final_globals[11] == 1,
            f"global continuation did not execute exactly once: V11={final_globals[11]}")
    require(final_validation >= 2, "destination storage validation was not observed")
    require(observed_valid_transaction is not None
            and observed_valid_transaction["return_valid_after_storage_validation"] == 1
            and observed_valid_transaction["global_requester"]
            and observed_valid_transaction["return_slot"] == 1
            and observed_valid_transaction["return_mode"] == 1
            and observed_valid_transaction["return_program"]
                == observed_valid_transaction["global_requester"][0]["program"]
            and observed_valid_transaction["return_pc"] == 8,
            f"valid global continuation did not survive storage validation: "
            f"{observed_valid_transaction}")
    require(continuation_later_frames >= 3,
            f"did not observe three later scheduler frames after continuation: "
            f"{continuation_later_frames}")
    require(final_room == 50 and final_phase == 0,
            f"fixture did not remain in destination room 50 phase 0: "
            f"room={final_room} phase={final_phase}")
    surviving_global_slots = [slot for slot in final_slots
                              if slot["number"] == 75 and slot["where"] == 2]
    require(len(surviving_global_slots) == 1
            and surviving_global_slots[0]["local0"] == 0x1234
            and surviving_global_slots[0]["status"] == 2
            and surviving_global_slots[0]["pc"] in (16, 17),
            f"global activation did not remain in its original yielded slot: "
            f"{surviving_global_slots}")

    report = {
        "gate": "M23A-global-room-return-restores-activation",
        "result": "pass",
        "evidence_kind": "fresh-power-on-Nexen-native-execution",
        "debugger_state_writes": 0,
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "manifest_rooms": [record["room"] for record in manifest["records"]],
        "observed_global_request_storage_validation": observed_valid_transaction,
        "final": {
            "room": final_room, "phase": final_phase,
            "error": final_error, "lifecycle": final_lifecycle,
            "V10_global_local0_copy": final_globals[10],
            "V11_continuation_count": final_globals[11],
            "validation_count": final_validation,
            "live_slots": final_slots,
        },
        "timeline": snapshots,
        "commit_events": commit_events,
        "assertions": {
            "destination_enCD_executed": destination_entry_seen,
            "return_valid_survived_storage_validation": (
                observed_valid_transaction is not None
                and observed_valid_transaction["return_valid_after_storage_validation"] == 1
            ),
            "original_global_slot_locals_restored": final_globals[10] == 0x1234,
            "continuation_executed_once": final_globals[11] == 1,
            "destination_enCD_marker": final_globals[12] == 0xBEEF,
            "original_global_slot_remains_yielded": len(surviving_global_slots) == 1,
            "continuation_pc_saved_by_c4": (
                len(surviving_global_slots) == 1
                and surviving_global_slots[0]["pc"] in (16, 17)
            ),
            "three_post_resume_frames_observed": continuation_later_frames >= 3,
            "engine_healthy": final_error == 0 and final_lifecycle == 2,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
