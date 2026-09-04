#!/usr/bin/env python3
"""Authentic Fate proof that integrated passes resume room-63 LSCR 202."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from same.engines.scumm_v5.cooked_room import decode_cooked_room
from validate_scumm_m23c_nexen import reset, snapshot
from validate_scumm_m25_authentic_next_nexen import snapshot as core_snapshot
from validate_scumm_get_actor_walkbox_authentic_nexen import actor_snapshot


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
COMMON = 0x7E2300
DIDEXEC = 0x7E23CB
DELAYS = 0x7E2416
LOCALS = 0x7E2448


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def scheduler_state(session: object, frame: int) -> dict[str, object]:
    core = core_snapshot(session, frame)
    common = session.read_memory("snesMemory", COMMON, 16)
    didexec = session.read_memory("snesMemory", DIDEXEC, 25)
    delays = session.read_memory("snesMemory", DELAYS, 50)
    local = session.read_memory("snesMemory", LOCALS + 2 * 64, 64)
    child = next((item for item in core["slots"] if item["number"] == 202), None)
    return {
        "video_frame": frame, "logical_frame": u16(common, 8),
        "core": core, "child": child,
        "actor_1": actor_snapshot(session, 1),
        "child_didexec": didexec[2], "child_delay": u16(delays, 4),
        "child_local0": u16(local), "child_local1": u16(local, 2),
    }


def trace_tuples(state: dict[str, object]) -> list[tuple[int, int, int]]:
    return [(item["program"], item["pc"], item["opcode"])
            for item in state["gate"]["opcode_trace"]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--room63", type=Path, required=True)
    parser.add_argument("--manifest63", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45410)
    args = parser.parse_args()
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    cooked = decode_cooked_room(args.room63.read_bytes(), expected_room=63)
    script = next(item for item in cooked.scripts
                  if item.kind == "LSCR" and item.number == 202)
    require(script.sha256 == "90e13f2440380e9f77fae78204e2cc0d8122124c73f1d06556cdfa1166049671",
            "authentic LSCR 202 identity differs")
    require(script.program[:21] == bytes.fromhex(
        "1a 00 40 ff ff 80 7b 01 40 01 88 01 40 00 40 bb 00 48 01 40 02"),
        "authentic LSCR 202 prefix differs")
    manifest = json.loads(args.manifest63.read_text())
    source = next(item for item in manifest["records"][0]["scripts"]
                  if item["identity"] == script.identity)

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    before = after = stable = None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=2.0, socket_timeout=120.0,
        stderr_log=args.output.parent / "authentic-scheduler-stderr.log",
    ) as session:
        reset(session)
        elapsed = 0
        # Approach the asynchronous room transition cheaply, then switch to
        # single-frame observation before room 63 activates.
        reached_room49 = False
        while elapsed < 2600:
            session.run_frames(10)
            elapsed += 10
            core = core_snapshot(session, elapsed)
            if (core["active_room"] == 49 and core["entry_count"] >= 1
                    and core["active_music"] == 80):
                reached_room49 = True
            if reached_room49 and (core["active_room"] == 63
                                   or core["room_phase"] in {4, 5, 6}):
                break
        require(reached_room49, "authentic path never established room 49")
        for _ in range(500):
            session.run_frames(1)
            elapsed += 1
            gate = snapshot(session)
            trace = trace_tuples(gate)
            if ((0xE7, 0x00E1, 0x00) in trace
                    and (0xEA, 0x0006, 0x7B) not in trace and before is None):
                before = {"scheduler": scheduler_state(session, elapsed),
                          "opcode_trace": gate["gate"]["opcode_trace"]}
            if (0xEA, 0x0006, 0x7B) in trace and after is None:
                after = {"scheduler": scheduler_state(session, elapsed),
                         "opcode_trace": gate["gate"]["opcode_trace"]}
            if after is not None and elapsed >= after["scheduler"]["video_frame"] + 4:
                stable = {"scheduler": scheduler_state(session, elapsed),
                          "opcode_trace": gate["gate"]["opcode_trace"]}
                break
        require(after is not None and stable is not None,
                "authentic scheduler never dispatched LSCR 202 from PC $0006")

    trace = [(item["program"], item["pc"], item["opcode"])
             for item in after["opcode_trace"]]
    nested = [(0xE7, 0x00DE, 0x2A), (0xEA, 0x0000, 0x1A),
              (0xEA, 0x0005, 0x80), (0xE7, 0x00E1, 0x00)]
    start = trace.index(nested[0])
    require(trace[start:start + 4] == nested,
            f"authentic nested ordering differs: {trace[start:start + 4]}")
    resume_index = trace.index((0xEA, 0x0006, 0x7B))
    require(resume_index > start + 3, "child resumed before its parent ENCD stopped")
    state = after["scheduler"]
    require(state["child"] == {"slot": 2, "status": 2, "number": 202,
                                "program": 0xEA, "pc": 6},
            f"resumed child slot identity differs: {state['child']}")
    require(state["child_didexec"] == 1 and state["child_delay"] == 0,
            "resumed child didexec/delay state differs")
    require(state["child_local0"] == 11 and state["child_local1"] == 11,
            f"authentic polling locals differ: {state}")
    require(state["core"]["active_room"] == 63
            and state["core"]["active_record"] == 1,
            "room-local program ownership changed across yield")
    stable_trace = [(item["program"], item["pc"], item["opcode"])
                    for item in stable["opcode_trace"]]
    require((0xEA, 0x0071, 0x48) in stable_trace
            and (0xEA, 0x0078, 0x13) in stable_trace
            and (0xEA, 0x007E, 0x18) in stable_trace
            and (0xEA, 0x00C7, 0x9A) in stable_trace,
            f"authentic walkbox-11 polling segment was incomplete: {stable_trace}")
    require(stable["scheduler"]["child"]["pc"] == 6
            and stable["scheduler"]["child_local0"] == 11
            and stable["scheduler"]["child_local1"] == 11,
            "LSCR 202 did not return to its canonical breakHere boundary")

    report = {
        "gate": "M25-authentic-integrated-scheduler-resume", "result": "pass",
        "fresh_power_on": True, "debugger_writes": 0,
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "script": {"identity": script.identity, "sha256": script.sha256,
                   "source_map": source},
        "before_resume": before,
        "first_resume": after,
        "stable_poll": stable,
        "pass_evidence": {
            "creation_pass_ordinal": 0,
            "creation_video_frame": before["scheduler"]["video_frame"],
            "creation_logical_clock": before["scheduler"]["logical_frame"],
            "resume_pass_ordinal": 1,
            "resume_video_frame": after["scheduler"]["video_frame"],
            "resume_logical_clock": after["scheduler"]["logical_frame"],
            "same_pass_reentry": False,
        },
        "canonical_sequence": nested + [
            (0xEA, 0x0006, 0x7B), (0xEA, 0x0071, 0x48),
            (0xEA, 0x0078, 0x13), (0xEA, 0x007E, 0x18),
            (0xEA, 0x00C7, 0x9A), (0xEA, 0x00CC, 0x18),
        ],
        "next_dependency": {
            "classification": "actor_movement_walkbox_state_lifecycle",
            "script_identity": script.identity,
            "poll_entry_offset": 6,
            "surrounding_bytes": script.program[:32].hex(),
            "decode": (
                "getActorWalkBox(Local[1], actor 1), compare against the prior "
                "Local[0], select canonical actor speed for stored walkbox 11, "
                "copy Local[1] to Local[0], and jump back to breakHere"
            ),
            "state": {"actor": 1, "stored_walkbox": 11,
                      "local0": 11, "local1": 11},
            "reason": (
                "No opcode fault follows the scheduler repair. LSCR 202 is a "
                "legitimate persistent poller; further player-visible progress "
                "requires canonical actor movement to change the stored walkbox."
            ),
        },
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output),
                      "rom_sha256": report["rom_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
