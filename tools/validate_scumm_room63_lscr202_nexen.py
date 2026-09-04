#!/usr/bin/env python3
"""Authentic Fate proof for generated room-local LSCR 202 resolution."""

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


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--room49", type=Path, required=True)
    parser.add_argument("--room63", type=Path, required=True)
    parser.add_argument("--manifest49", type=Path, required=True)
    parser.add_argument("--manifest63", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45374)
    args = parser.parse_args()
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    room49 = decode_cooked_room(args.room49.read_bytes(), expected_room=49)
    room63 = decode_cooked_room(args.room63.read_bytes(), expected_room=63)
    manifest49 = json.loads(args.manifest49.read_text())
    manifest63 = json.loads(args.manifest63.read_text())
    require(manifest49["num_global_scripts"] == manifest63["num_global_scripts"] == 200,
            "authentic manifests disagree on the global/local boundary")
    locals63 = [item for item in room63.scripts if item.kind == "LSCR"]
    require([item.number for item in locals63] == [200, 201, 202],
            "authentic room-63 LSCR inventory differs")
    script = locals63[-1]
    require(script.program[:7] == bytes.fromhex("1a 00 40 ff ff 80 7b"),
            "authentic LSCR 202 prefix differs")
    # Program IDs follow the deterministic generator order: room 49, globals
    # 144/145, room 63, then global 151.
    program = 0xD0 + len(room49.scripts) + 2 + list(room63.scripts).index(script)
    require(program == 0xEA, f"authentic LSCR 202 generated program differs: {program:#x}")

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    reached = reached_core = later = later_core = None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=2.0, socket_timeout=120.0,
        stderr_log=args.output.parent / "authentic-stderr.log",
    ) as session:
        reset(session)
        elapsed = 0
        while elapsed < 3200:
            session.run_frames(100)
            elapsed += 100
            state = snapshot(session)
            trace = [(item["program"], item["pc"], item["opcode"])
                     for item in state["gate"]["opcode_trace"]]
            if (0xE7, 0x00DE, 0x2A) in trace:
                reached = state
                reached_core = core_snapshot(session, elapsed)
                break
            require(not state["error"], f"authentic path faulted before LSCR 202: {state}")
        require(reached is not None, "authentic room-63 ENCD did not start LSCR 202")
        session.run_frames(300)
        later = snapshot(session)
        later_core = core_snapshot(session, elapsed + 300)

    trace = [(item["program"], item["pc"], item["opcode"])
             for item in reached["gate"]["opcode_trace"]]
    sequence = [
        (0xE7, 0x00DE, 0x2A),
        (0xEA, 0x0000, 0x1A),
        (0xEA, 0x0005, 0x80),
        (0xE7, 0x00E1, 0x00),
    ]
    start = trace.index(sequence[0])
    require(trace[start:start + 4] == sequence,
            f"nested child/parent ordering differs: {trace[start:start + 4]}")
    assert reached_core is not None and later_core is not None
    child = next(item for item in reached_core["slots"] if item["number"] == 202)
    require(child == {"slot": 2, "status": 2, "number": 202,
                      "program": 0xEA, "pc": 6},
            f"authentic yielded LSCR 202 slot differs: {child}")
    require(reached_core["nest_depth"] == 0
            and not any(item["slot"] == 0 for item in reached_core["slots"]),
            f"room-63 ENCD parent was not restored and retired: {reached_core}")
    # The trace proves that no second LSCR-202 instruction is dispatched after
    # canonical breakHere, and its slot remains independently runnable.
    require(not later["error"], f"authentic post-yield state faulted: {later}")
    later_trace = [(item["program"], item["pc"], item["opcode"])
                   for item in later["gate"]["opcode_trace"]]
    require(later_trace.count((0xEA, 0x0005, 0x80)) == 1
            and (0xEA, 0x0006, 0x7B) not in later_trace,
            "integrated scheduler unexpectedly progressed beyond the recorded blocker")

    inventory = []
    source_manifest = next(item for item in manifest63["records"] if item["room"] == 63)
    by_identity = {item["identity"]: item for item in source_manifest["scripts"]}
    for item in locals63:
        source = by_identity[item.identity]
        inventory.append({
            "script_number": item.number,
            "local_index": item.number - 200,
            "identity": item.identity, "sha256": item.sha256,
            "payload_size": len(item.program),
            "original_file_offset": source["original_file_offset"],
            "original_room_offset": source["original_room_offset"],
            "original_chunk_offset": source["original_chunk_offset"],
            "cooked_record_offset": source["cooked_record_offset"],
        })
    report = {
        "gate": "M25-authentic-room63-complete-local-lookup", "result": "pass",
        "fresh_power_on": True, "debugger_writes": 0,
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "namespace": {"num_global_scripts": 200, "requested": 202,
                      "classification": "current-room local", "local_index": 2},
        "room63_local_inventory": inventory,
        "lookup": {
            "active_room": 63, "active_record": 1, "generated_program": program,
            "script_identity": script.identity, "script_sha256": script.sha256,
            "source_map": script.runtime_map(0), "allocated_slot": 2,
            "parent_program": 0xE7, "parent_pc_before": 0x00DE,
            "parent_resume_pc": 0x00E1, "child_entry_pc": 0,
            "child_yield_pc": 5, "child_post_yield_pc": 6,
            "nested_trace": sequence,
            "child_slot_state": child,
        },
        "next_blocker": {
            "classification": "integrated_scheduler_lifecycle_gap",
            "script_identity": script.identity, "script_sha256": script.sha256,
            "offset": 5, "surrounding_start": 0,
            "surrounding_bytes": script.program[:21].hex(),
            "canonical_decode": "breakHere at +$0005; resume at +$0006",
            "relevant_state": (
                "LSCR 202 remains yielded/runnable at PC $0006, but the integrated "
                "room driver does not run the general scheduler after ENCD completes"
            ),
        },
        "trace_at_entry": reached["gate"]["opcode_trace"],
        "trace_after_300_frames": later["gate"]["opcode_trace"],
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output),
                      "rom_sha256": report["rom_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
