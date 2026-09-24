#!/usr/bin/env python3
"""Native near/far M23A transaction serialization regression."""

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
PENDING_ROOM = 0x7FF2C1
REQUESTS = 0x7FF2C5
VALIDATIONS = 0x7FF2C6
RETURN_PROGRAM = 0x7FF2C3
RETURN_VALID = 0x7FF467
RETURN_SLOT = 0x7FF468
RETURN_MODE = 0x7FF469
ERROR = 0x7E2303
LIFECYCLE = 0x7E2221
API_PENDING = 0x7E7F8E
API_ROOM = 0x7E7F8F
DIAG_COUNT = 0x7E57BF
DIAG_RECORDS = 0x7E57C0
DIAG_INJECT_MODE = 0x7E5885
DIAG_INJECT_TARGET = 0x7E5886
DIAG_INJECT_ROUTE = 0x7E588A
DIAG_INJECT_ORIGIN = 0x7E588B
EVENT_COUNT = 0x7E2004
EVENT_HEAD = 0x7E2000
EVENT_TAIL = 0x7E2002
EVENT_SEQUENCE = 0x7E200A
EVENT_REJECTED = 0x7E2008
EVENT_STAGING = 0x7E2020


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--route", choices=("near", "far"), required=True)
    parser.add_argument("--phase", type=int, choices=(4, 5), required=True)
    parser.add_argument("--mode", choices=("same", "conflict", "direct"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45761)
    args = parser.parse_args()
    require(args.rom.is_file() and args.manifest.is_file(), "ROM or manifest missing")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    manifest = json.loads(args.manifest.read_text())
    require(manifest.get("case") == "pending-room-request", "wrong fixture case")
    require(manifest.get("room_provenance", "").startswith("synthetic fixture"),
            "pending transaction fixture provenance is not explicit")
    require({item["room"] for item in manifest["records"]} >= {49, 50, 51},
            "fixture must contain the source and both destination records")

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    timeline: list[dict[str, int]] = []
    transaction_snapshot: dict[str, int] | None = None
    phase5_rejection: dict[str, int] | None = None
    deferred_retry: dict[str, int] | None = None
    expected_room = 50 if args.mode == "same" else 51

    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=2.0, socket_timeout=60.0,
        stderr_log=args.output.with_suffix(".stderr.log"),
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0, "cold power reset failed")

        def snap() -> dict[str, int]:
            return {
                "frame": session.get_state()["frameCount"],
                "room": session.read_memory("snesMemory", ROOM, 1)[0],
                "phase": session.read_memory("snesMemory", PHASE, 1)[0],
                "pending_room": session.read_memory("snesMemory", PENDING_ROOM, 1)[0],
                "requests": session.read_memory("snesMemory", REQUESTS, 1)[0],
                "validations": session.read_memory("snesMemory", VALIDATIONS, 1)[0],
                "return_program": session.read_memory("snesMemory", RETURN_PROGRAM, 1)[0],
                "return_valid": session.read_memory("snesMemory", RETURN_VALID, 1)[0],
                "return_slot": session.read_memory("snesMemory", RETURN_SLOT, 1)[0],
                "return_mode": session.read_memory("snesMemory", RETURN_MODE, 1)[0],
                "api_pending": session.read_memory("snesMemory", API_PENDING, 1)[0],
                "api_room": session.read_memory("snesMemory", API_ROOM, 1)[0],
                "event_count": int.from_bytes(session.read_memory(
                    "snesMemory", EVENT_COUNT, 2), "little"),
                "event_head": int.from_bytes(session.read_memory(
                    "snesMemory", EVENT_HEAD, 2), "little"),
                "event_tail": int.from_bytes(session.read_memory(
                    "snesMemory", EVENT_TAIL, 2), "little"),
                "event_sequence": int.from_bytes(session.read_memory(
                    "snesMemory", EVENT_SEQUENCE, 2), "little"),
                "event_rejected": int.from_bytes(session.read_memory(
                    "snesMemory", EVENT_REJECTED, 2), "little"),
                "staging_service": session.read_memory("snesMemory", EVENT_STAGING, 1)[0],
                "staging_opcode": session.read_memory("snesMemory", EVENT_STAGING + 1, 1)[0],
                "staging_arg0": int.from_bytes(session.read_memory(
                    "snesMemory", EVENT_STAGING + 8, 2), "little"),
                "error": session.read_memory("snesMemory", ERROR, 1)[0],
                "lifecycle": session.read_memory("snesMemory", LIFECYCLE, 1)[0],
            }

        def step_frame() -> dict[str, int]:
            # Starting paused at VBlank, one frame-count increment can stop
            # before the following engine tick has been serviced. Advancing
            # two increments guarantees a complete scheduler/service interval.
            session.run_frames(2)
            state = snap()
            timeline.append(state)
            return state

        # Reach the normal, ROM-authored scenario startup room before using the
        # engine's public one-byte host request mailbox as the test stimulus.
        for _ in range(60):
            session.run_frames(1)
            state = snap()
            if state["room"] == 49 and state["phase"] == 0:
                break
        require(state["room"] == 49 and state["phase"] == 0,
                f"synthetic source room did not settle: {state}")
        require(state["error"] == 0 and state["lifecycle"] == 2,
                f"source room unhealthy: {state}")
        initial_request_count = state["requests"]
        initial_validation_count = state["validations"]
        initial_event_sequence = state["event_sequence"]
        require(initial_request_count == 1 and initial_validation_count == 1,
                f"unexpected startup storage history: {state}")
        # Clear only fixture diagnostic evidence, then stage a second request
        # for injection by the native validator hook at the exact phase under
        # test. The production transaction and Storage queue remain untouched.
        session.write_u8(DIAG_COUNT, 0)
        session.write_u8(DIAG_INJECT_MODE, 1 if args.phase == 4 else 2)
        session.write_u8(DIAG_INJECT_TARGET, 50 if args.mode == "same" else 51)
        session.write_u8(DIAG_INJECT_ROUTE, 0 if args.route == "near" else 1)
        session.write_u8(DIAG_INJECT_ORIGIN, 0 if args.mode == "direct" else 1)

        # First request is a normal public room-request mailbox submission.
        session.write_u8(API_ROOM, 50)
        session.write_u8(API_PENDING, 1)
        first_queued = step_frame()
        decision_live = first_queued
        if args.phase == 5:
            decision_live = step_frame()
        second_target = 50 if args.mode == "same" else 51
        decisions = []
        record_count = session.read_memory(
            "snesMemory", 0x7E57BF, 1)[0]
        for index in range(record_count):
            record = session.read_memory(
                "snesMemory", 0x7E57C0 + index * 24, 24)
            decisions.append({
                "stage": record[0], "phase": record[1],
                "input_room": record[2], "pending_room": record[3],
                "request_count": record[4], "return_valid": record[5],
                "return_program": record[6], "return_slot": record[7],
                "return_mode": record[8],
                "event_count": int.from_bytes(record[14:16], "little"),
                "event_sequence": int.from_bytes(record[16:18], "little"),
                "api_active": record[11], "api_pending": record[12],
                "api_room": record[13], "error": record[18],
                "lifecycle": record[19], "pending_record": record[20],
                "active_record": record[21], "room": record[22],
                "route": record[23],
            })
        require(any(item["stage"] == 1 and item["phase"] == 4
                    and item["input_room"] == 50 and item["pending_room"] == 50
                    and item["request_count"] == initial_request_count + 1
                    and item["event_sequence"] == initial_event_sequence + 1
                    for item in decisions),
                f"no native queued snapshot for first READ: {decisions}")
        expected_decision = {"same": 2, "conflict": 3, "direct": 4}[args.mode]
        expected_phase = args.phase
        require(any(item["stage"] == expected_decision and item["phase"] == expected_phase
                    and item["input_room"] == second_target
                    and item["pending_room"] == 50
                    and item["api_active"] == (0 if args.mode == "direct" else 1)
                    and item["route"] == (0 if args.route == "near" else 1)
                    for item in decisions),
                f"no native phase-{expected_phase} decision snapshot: {decisions}; "
                f"live={decision_live}")
        first_record = next(item for item in decisions
                            if item["stage"] == 1 and item["input_room"] == 50)
        second_record = next(item for item in decisions
                             if item["stage"] == expected_decision
                             and item["phase"] == expected_phase)
        transaction_snapshot = {
            "pending_room": first_record["pending_room"],
            "return_program": first_record["return_program"],
            "return_valid": first_record["return_valid"],
            "return_slot": first_record["return_slot"],
            "return_mode": first_record["return_mode"],
            "requests": first_record["request_count"],
        }
        require(second_record["pending_room"] == transaction_snapshot["pending_room"]
                and second_record["request_count"] == transaction_snapshot["requests"]
                and second_record["return_program"] == transaction_snapshot["return_program"]
                and second_record["return_valid"] == transaction_snapshot["return_valid"]
                and second_record["return_slot"] == transaction_snapshot["return_slot"]
                and second_record["return_mode"] == transaction_snapshot["return_mode"]
                and second_record["event_sequence"] == first_record["event_sequence"],
                f"second request mutated or requeued the accepted transaction: {decisions}")
        phase5_rejection = second_record
        if args.mode == "same":
            require(phase5_rejection["api_pending"] == 1,
                    "second request decision was not made under the public API origin")
        elif args.mode == "conflict":
            require(phase5_rejection["api_pending"] == 1
                    and phase5_rejection["api_room"] == 51,
                    "different target was not retained for serialization")

        if args.mode == "direct":
            require(second_record["api_pending"] == 0
                    and second_record["event_sequence"] == first_record["event_sequence"]
                    and second_record["request_count"] == first_record["request_count"]
                    and second_record["error"] == 13,
                    f"direct conflict did not reject while preserving the transaction: {decisions}")
            after = snap()
            require(after["pending_room"] == 50 and after["phase"] == args.phase
                    and after["requests"] == first_record["request_count"]
                    and after["event_sequence"] == first_record["event_sequence"]
                    and after["error"] == 13,
                    f"direct conflict changed the accepted transaction or lacked error: {after}")
            report = {
                "gate": "M23A-pending-room-request-serialization",
                "result": "pass", "evidence_kind": "fresh-power-on-Nexen-native-execution",
                "route": args.route, "request_route": args.route,
                "request_phase": args.phase, "mode": args.mode,
                "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
                "native_decision_records": decisions,
                "accepted_transaction": transaction_snapshot,
                "rejected_request": second_record, "after_rejection": after,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
            print(f"M23A {args.route} phase-{args.phase} pending-room direct: PASS ({args.output})")
            return 0

        for _ in range(80):
            state = step_frame()
            if args.mode == "conflict" and state["phase"] == 4 \
                    and state["pending_room"] == 51:
                deferred_retry = state
            if state["room"] == expected_room and state["phase"] == 0 \
                    and state["api_pending"] == 0:
                break
            require(state["error"] == 0 and state["lifecycle"] == 2,
                    f"room transaction failed while serialized: {state}; "
                    f"timeline={timeline}; cpu={session.get_cpu_state()}")
        final = snap()
        require(final["room"] == expected_room and final["phase"] == 0
                and final["api_pending"] == 0,
                f"serialized room request did not complete: {final}; "
                f"timeline={timeline}; state={session.get_state()}; "
                f"cpu={session.get_cpu_state()}")
        require(final["error"] == 0 and final["lifecycle"] == 2,
                f"serialized request left engine unhealthy: {final}")
        expected_total = initial_request_count + (1 if args.mode == "same" else 2)
        require(final["requests"] == expected_total,
                f"unexpected request count for {args.mode}: {final}")
        require(final["validations"] == initial_validation_count
                + (1 if args.mode == "same" else 2),
                f"unexpected Storage READ validation count for {args.mode}: {final}")
        if args.mode == "conflict":
            require(deferred_retry is not None and deferred_retry["phase"] == 4
                    and deferred_retry["pending_room"] == 51,
                    f"second target was not retried after the first lifecycle: {deferred_retry}")

    report = {
        "gate": "M23A-pending-room-request-serialization",
        "result": "pass", "evidence_kind": "fresh-power-on-Nexen-native-execution",
        "route": args.route,
        "request_route": args.route,
        "request_phase": args.phase,
        "first_request_after_push": first_queued,
        "native_decision_records": decisions,
        "test_stimulus": "public SCUMM room-request API mailbox; no VM state patched",
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "mode": args.mode,
        "accepted_transaction": transaction_snapshot,
        "second_request_decision": phase5_rejection,
        "deferred_retry": deferred_retry,
        "timeline": timeline, "final": final,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"M23A {report['route']} pending-room {args.mode}: PASS ({args.output})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
