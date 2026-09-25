#!/usr/bin/env python3
"""Fresh-emulator proof for M25's authentic headless actor-talk lifecycle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from same.engines.scumm_v5.cooked_room import decode_cooked_room
from validate_scumm_m25_authentic_next_nexen import snapshot

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
TALK = 0x7E7A20
VARIABLES = 0x7FF500
ACTORS = 0x7F36C0
POSITIONS = 0x7FF1A0
MOVING = 0x7FF220
PUT_ACTOR = 0x7FFB65
EXPECTED = b"Well, here I am on\x10Thera.\0"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def talk_snapshot(session: object, emulator_frame: int) -> dict[str, object]:
    raw = session.read_memory("snesMemory", TALK, 0xB9)
    variables = session.read_memory("snesMemory", VARIABLES, 2 * 38)
    legacy_variables = session.read_memory("snesMemory", 0x7E2320, 32)
    events = []
    for index in range(min(raw[0x30], 16)):
        base = 0x31 + index * 8
        events.append({
            "kind": raw[base], "actor": raw[base + 1],
            "animation": raw[base + 2], "generation": u16(raw, base + 3),
            "logical_frame": u16(raw, base + 5), "have_msg": raw[base + 7],
        })
    return {
        "emulator_frame": emulator_frame,
        "active": raw[0], "internal_have_msg": raw[1], "actor": raw[2],
        "charinc": raw[3], "delay": u16(raw, 4), "generation": u16(raw, 6),
        "raw_length": raw[8], "start_count": raw[9], "stop_count": raw[10],
        "completion_count": raw[11], "started_logical_frame": u16(raw, 12),
        "completed_logical_frame": u16(raw, 14),
        "encoded": list(raw[0x10:0x10 + raw[8]]), "events": events,
        "wait_blocks": raw[0xB1], "wait_resumes": raw[0xB2],
        "wait_pc": u16(raw, 0xB3),
        "print_pc_before": u16(raw, 0xB5), "print_pc_after": u16(raw, 0xB7),
        "var_have_msg": u16(legacy_variables, 3 * 2),
        "var_talk_actor": u16(variables, 25 * 2),
        "var_charinc": u16(variables, 37 * 2),
    }


def actor_snapshot(session: object, actor: int) -> dict[str, object]:
    record = session.read_memory("snesMemory", ACTORS + actor * 0x40, 0x20)
    position = session.read_memory("snesMemory", POSITIONS + actor * 4, 4)
    walkbox = session.read_memory("snesMemory", PUT_ACTOR + 0x240 + actor, 1)[0]
    return {
        "actor": actor, "position": [u16(position), u16(position, 2)],
        "moving": session.read_memory("snesMemory", MOVING + actor, 1)[0],
        "facing": u16(record, 0x0A), "scale": [record[0x0D], record[0x0E]],
        "visible": record[0x15], "room": record[0x16], "walkbox": walkbox,
        "costume": record[0], "frame": record[0x0F],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--cooked-room", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45240)
    args = parser.parse_args()
    require(args.rom.is_file() and args.cooked_room.is_file(), "input is missing")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    room = decode_cooked_room(args.cooked_room.read_bytes(), expected_room=49)
    script = next(item for item in room.scripts if item.kind == "LSCR" and item.number == 200)
    instruction = script.program[0x1A8:0x1C5]
    require(instruction == bytes((0x14, 1, 0x0F)) + EXPECTED,
            f"authentic print bytes differ: {instruction.hex()}")

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    changes: list[dict[str, object]] = []
    started = completed = published_clear = terminal = None
    previous = None
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=2.0, socket_timeout=90.0,
        stderr_log=args.output.parent / "nexen-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")
        for frame in range(1, 501):
            step = session.run_frames(1)
            require(step["framesAdvanced"] == 1 and not step["timedOut"], "emulator timeout")
            talk = talk_snapshot(session, frame)
            engine = snapshot(session, frame)
            key = (talk["active"], talk["delay"], talk["var_have_msg"],
                   talk["actor"], talk["stop_count"], engine["error"])
            if key != previous:
                changes.append({"talk": talk, "engine": engine})
                previous = key
            if started is None and talk["start_count"] == 1:
                started = {"talk": talk, "engine": engine,
                           "speaker_state": actor_snapshot(session, 1)}
            if terminal is None and engine["error"]:
                terminal = {"talk": talk, "engine": engine}
            if completed is None and talk["completion_count"] == 1:
                completed = {"talk": talk, "engine": engine}
            if completed is not None and talk["var_have_msg"] == 0:
                published_clear = {"talk": talk, "engine": engine}
                break

    require(started is not None, "authentic actor-talk did not start")
    start = started["talk"]
    require(start["encoded"] == list(EXPECTED) and start["raw_length"] == 26,
            f"encoded message differs: {start}")
    require(start["print_pc_before"] == 0x1A8 and start["print_pc_after"] == 0x1C5,
            f"authentic print PC consumption differs: {start}")
    require(start["active"] == 1 and start["actor"] == 1 and start["delay"] == 160,
            f"initial talk ownership/timing differs: {start}")
    require(start["charinc"] == start["var_charinc"] == 4
            and start["var_have_msg"] == 0xFF and start["var_talk_actor"] == 1,
            f"canonical variables differ at start: {start}")
    require(start["events"] == [{
        "kind": 1, "actor": 1, "animation": 4, "generation": 1,
        "logical_frame": start["started_logical_frame"], "have_msg": 1,
    }], f"talk-start event differs: {start['events']}")
    require(terminal is not None and terminal["engine"]["last_opcode"] == 0x7B,
            f"next fail-closed blocker differs: {terminal}")
    require(completed is not None and published_clear is not None,
            "talk did not complete and publish clear after the script fault")
    done = completed["talk"]
    require(done["active"] == 0 and done["actor"] == 0xFF and done["delay"] == 0,
            f"completion ownership differs: {done}")
    require(done["stop_count"] == done["completion_count"] == 1,
            f"completion was not exactly once: {done}")
    require(done["events"][-1]["kind"] == 2 and done["events"][-1]["actor"] == 1
            and done["events"][-1]["animation"] == 5,
            f"talk-stop event differs: {done['events']}")
    require(done["completed_logical_frame"] - done["started_logical_frame"] == 40,
            f"completion is not 40 logical loops after start: {done}")
    require(done["var_have_msg"] == 1,
            "VAR_HAVE_MSG cleared during completion rather than next loop")
    require(published_clear["talk"]["var_have_msg"] == 0,
            "VAR_HAVE_MSG did not publish clear on the following loop")

    next_script = next(item for item in room.scripts if item.kind == "LSCR" and item.number == 216)
    report = {
        "gate": "M25-authentic-headless-message-lifecycle", "result": "pass",
        "fresh_power_on": True, "debugger_writes": 0,
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "resource": {"room_record_sha256": hashlib.sha256(args.cooked_room.read_bytes()).hexdigest(),
                     "script_identity": script.identity, "script_sha256": script.sha256,
                     "source_map": script.runtime_map(0x1A8),
                     "instruction": instruction.hex(), "next_pc": 0x1C5},
        "oracle": {"base_delay": 60, "glyph_count": 25, "charinc": 4,
                   "initial_delay": 160, "jiffies_per_loop": 4,
                   "completion_after_loops": 40, "publish_clear_after_loops": 41},
        "started": started, "terminal": terminal, "completed": completed,
        "published_clear": published_clear, "changes": changes,
        "next_blocker": {"script_identity": next_script.identity,
                         "script_sha256": next_script.sha256,
                         "offset": 0, "source_map": next_script.runtime_map(0),
                         "bytes": next_script.program[:16].hex(),
                         "opcode": 0x7B, "decode": "getActorWalkBox(Var[442], actor 1)"},
        "limitations": [
            "Costume presentation remains blocked because authentic costume.45 is absent from the supplied Fate demo and the SNES costume renderer does not yet exist.",
            "Text glyph rendering is not implemented by this milestone.",
            "Talk-start and talk-stop are logical SCUMM actor events only; no visible mouth animation is claimed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output),
                      "rom_sha256": report["rom_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
