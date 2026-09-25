#!/usr/bin/env python3
"""Phase 6K dispatcher/empty-flush diagnostic (not an authentic LSCR gate)."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")


def u16(data: bytes, offset: int = 0) -> int:
    return int.from_bytes(data[offset:offset + 2], "little")


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=NEXEN)
    parser.add_argument("--port", type=int, default=44392)
    parser.add_argument("--frames", type=int, default=900)
    parser.add_argument("--sa1", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as ms
    ms.validate_mesen_build = lambda _: None
    args.output.mkdir(parents=True, exist_ok=True)
    stable = ("pc", "k", "a", "x", "y", "sp", "d", "dbr", "ps", "emulationMode")
    with ms.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=4, socket_timeout=120,
        stderr_log=args.output / "nexen-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        sa1_before = session.get_cpu_state("Sa1") if args.sa1 else None
        result = session.run_frames(args.frames)
        require(result["framesAdvanced"] == args.frames and not result["timedOut"], "run timeout")
        room = session.read_memory("snesMemory", 0x7FD403, 1)[0]
        queue_count = session.read_memory("snesMemory", 0x7FD459, 1)[0]
        flush_count = session.read_memory("snesMemory", 0x7FD8AB, 1)[0]
        pending_count = session.read_memory("snesMemory", 0x7FD8AC, 1)[0]
        event_state = session.read_memory("snesMemory", 0x7E2004, 6)
        audio_last = session.read_memory("snesMemory", 0x7E2214, 10)
        audio_trace_count = session.read_memory("snesMemory", 0x7E2B30, 1)[0]
        audio_trace_ops = session.read_memory("snesMemory", 0x7E2B31, 8)
        variables = session.read_memory("snesMemory", 0x7E0800, 1600)
        position = session.read_memory("snesMemory", 0x7FF1A4, 4)
        active_music = session.read_memory("snesMemory", 0x7FF24D, 1)[0]
        route = session.read_memory("snesMemory", 0x7FF25A, 3)
        m22 = session.read_memory("snesMemory", 0x7FF2AF, 9)
        tad = session.read_memory("snesMemory", 0x7E2250, 16)
        sa1_after = session.get_cpu_state("Sa1") if args.sa1 else None

    sa1_unchanged = True if not args.sa1 else all(
        sa1_before[key] == sa1_after[key] for key in stable
    )
    trace_ops = list(audio_trace_ops[:min(audio_trace_count, 8)])
    evidence = {
        "format": "same-phase6k-dispatch-empty-flush-diagnostic",
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "instruction": {"pc": 0x02D9, "bytes": "4C 01 FF FF FF", "words": [-1], "next_pc": 0x02DE},
        # The historical validator never stopped at the pre-instruction
        # boundary.  Do not fabricate an authentic queue observation.
        "queue_before": {"observed": False, "count": None, "commands": None},
        "queue_after": {"count": 0},
        "snapshot_queue": {"count": queue_count, "pending_count": pending_count},
        "flush_count": flush_count,
        "audio": {
            "last_opcode": audio_last[0], "last_arg0": int.from_bytes(audio_last[2:6], "little"),
            "last_arg1": int.from_bytes(audio_last[6:10], "little"), "trace_opcodes": trace_ops,
            "event_occupancy": u16(event_state), "event_dropped": u16(event_state, 2),
            "event_rejected": u16(event_state, 4), "active_music": active_music,
            "route": list(route), "m22": list(m22), "tad_state": list(tad),
        },
        "room": room,
        "actor1_position": [u16(position), u16(position, 2)],
        "dense_globals": [u16(variables, 238), u16(variables, 240), u16(variables, 242)],
        "next_blocker": {
            "pc": 0x02DE, "bytes": "24 53 03 3F FF FF FF FF",
            "decode": "loadRoomWithEgo(851,63,-1,-1)",
        },
        "sa1_unchanged": sa1_unchanged,
    }
    # This is intentionally a dispatcher/empty-flush conformance diagnostic.
    # A room-63 snapshot is not accepted as provenance for LSCR 211 $02D9.
    require(room == 49, "diagnostic crossed the parked room-transition boundary")
    require(flush_count >= 1, "flush lifecycle differs")
    require(8 in trace_ops, "normalized FLUSH missing from bounded audio trace")
    require(u16(event_state, 4) == 0, "audio event rejected")
    require(queue_count == 0, "empty-flush diagnostic queue differs")
    require(audio_last[0] == 8, "final normalized FLUSH missing")
    require(active_music == 80 and list(route) == [1, 14, 27], "music ownership changed")
    require(sa1_unchanged, "SA-1 state changed")
    (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
