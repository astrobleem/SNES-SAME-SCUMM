#!/usr/bin/env python3
"""Fresh-emulator target-neutral Phase 6F camera semantic proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
COMMON = 0x7E2300
CAMERA = 0x7E7FA8
VARIABLES = 0x7FF500
POSITIONS = 0x7FF1A0
MOVING = 0x7FF220
WALKBOX = 0x7FFDA5
MOVE_TICK = 0x7E7EB9
WAIT_BLOCKS = 0x7E7EBB
WAIT_RELEASES = 0x7E7EBD
GET_DIST = 0x7E7F23
START_OBJECT = 0x7E7F91
ACTIVE_ROOM = 0x7FF2BF
TALK = 0x7E7A20
AUDIO_PACKETS = 0x7E2B30


def u16(data: bytes, offset: int = 0) -> int:
    return int.from_bytes(data[offset:offset + 2], "little")


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def stable_cpu(value: dict[str, object]) -> dict[str, object]:
    return {key: value[key] for key in
            ("pc", "k", "a", "x", "y", "sp", "d", "dbr", "ps", "emulationMode")}


def camera_state(raw: bytes, frame: int) -> dict[str, int]:
    return {
        "frame": frame, "current_x": u16(raw, 0), "current_y": u16(raw, 2),
        "destination_x": u16(raw, 4), "destination_y": u16(raw, 6),
        "last_x": u16(raw, 8), "last_y": u16(raw, 10),
        "screen_start_strip": u16(raw, 12), "screen_end_strip": u16(raw, 14),
        "xstart": u16(raw, 16), "requested_x": u16(raw, 18),
        "pc_before": u16(raw, 20), "pc_after": u16(raw, 22),
        "immediate_count": u16(raw, 24), "publish_count": u16(raw, 26),
        "scroll_script_count": u16(raw, 28), "update_pending": raw[30],
        "scroll_script": raw[31], "frame_phase_count": u16(raw, 32),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44188)
    parser.add_argument("--max-frames", type=int, default=1800)
    args = parser.parse_args()
    require(args.rom.is_file(), f"ROM missing: {args.rom}")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    immediate = None
    published = None
    is_sa1 = args.rom.read_bytes()[0x7FD5] == 0x23
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT, port=args.port,
        boot_wait=2.0, socket_timeout=90.0, stderr_log=args.output.with_suffix(".stderr.log"),
    ) as session:
        session.pause(); session.tool("reset_emulator", {"power": True}); session.pause()
        sa1_start = stable_cpu(session.get_cpu_state("Sa1")) if is_sa1 else None
        terminal_frame = 0
        for frame in range(1, args.max_frames + 1):
            run = session.run_frames(1)
            require(run["framesAdvanced"] == 1 and not run["timedOut"], "frame execution timed out")
            camera = session.read_memory("snesMemory", CAMERA, 0x24)
            if u16(camera, 24) == 1 and immediate is None:
                immediate = camera_state(camera, frame)
            if u16(camera, 26) == 1 and camera[30] == 0 and published is None:
                published = camera_state(camera, frame)
            common = session.read_memory("snesMemory", COMMON, 0x10)
            if (u16(common) == 0x0296 and common[3] == 0x0E
                    and u16(camera, 26) == 1 and camera[30] == 0):
                terminal_frame = frame
                break
        require(terminal_frame != 0, "authentic execution did not reach the post-camera blocker")
        common = session.read_memory("snesMemory", COMMON, 0x64)
        camera = session.read_memory("snesMemory", CAMERA, 0x24)
        variables = session.read_memory("snesMemory", VARIABLES, 64)
        positions = session.read_memory("snesMemory", POSITIONS, 8)
        get_dist = session.read_memory("snesMemory", GET_DIST, 35)
        start_object = session.read_memory("snesMemory", START_OBJECT, 21)
        talk = session.read_memory("snesMemory", TALK, 13)
        walkbox = session.read_memory("snesMemory", WALKBOX + 1, 1)[0]
        moving = session.read_memory("snesMemory", MOVING + 1, 1)[0]
        movement_tick = u16(session.read_memory("snesMemory", MOVE_TICK, 2))
        wait_blocks = u16(session.read_memory("snesMemory", WAIT_BLOCKS, 2))
        wait_releases = u16(session.read_memory("snesMemory", WAIT_RELEASES, 2))
        active_room = session.read_memory("snesMemory", ACTIVE_ROOM, 1)[0]
        audio_packet_count = session.read_memory("snesMemory", AUDIO_PACKETS, 1)[0]
        sa1_end = stable_cpu(session.get_cpu_state("Sa1")) if is_sa1 else None

    final_camera = camera_state(camera, terminal_frame)
    actor = {
        "position": [u16(positions, 4), u16(positions, 6)],
        "walkbox": walkbox, "moving": moving,
    }
    semantics = {
        "logical_tick": u16(common, 8), "pc": u16(common), "status": common[2],
        "error": common[3], "last_opcode": common[6], "active_room": active_room,
        "var2": u16(variables, 4), "actor": actor, "movement_tick": movement_tick,
        "wait_blocks": wait_blocks, "wait_releases": wait_releases,
        "get_dist": {"pc_before": u16(get_dist), "pc_after": u16(get_dist, 2),
                     "result": u16(get_dist, 30), "exec_count": get_dist[33]},
        "start_object": {"object": u16(start_object), "entry": start_object[2],
                         "entry_offset": u16(start_object, 4), "chain_target": start_object[13],
                         "object_retired": start_object[14], "lscr_entry_seen": start_object[16]},
        "message": {"active": talk[0], "have_msg": talk[1], "actor": talk[2]},
        "audio_packet_count": audio_packet_count,
        "camera": {key: final_camera[key] for key in (
            "current_x", "current_y", "destination_x", "destination_y", "last_x", "last_y",
            "screen_start_strip", "screen_end_strip", "xstart", "requested_x", "pc_before",
            "pc_after", "immediate_count", "publish_count", "scroll_script_count",
            "update_pending", "scroll_script")},
    }
    require(immediate is not None and published is not None, "camera checkpoints not observed")
    require((immediate["current_x"], immediate["destination_x"], immediate["requested_x"],
             immediate["pc_before"], immediate["pc_after"], immediate["update_pending"]) ==
            (160, 0, 0, 0x026E, 0x0271, 1), f"immediate state differs: {immediate}")
    require((published["current_x"], published["destination_x"], published["screen_start_strip"],
             published["screen_end_strip"], published["xstart"]) == (160, 160, 0, 39, 0),
            f"published state differs: {published}")
    require((semantics["logical_tick"], semantics["pc"], semantics["status"], semantics["error"],
             semantics["last_opcode"], semantics["active_room"], semantics["var2"]) ==
            (93, 0x0296, 2, 0x0E, 0x14, 49, 160), f"terminal state differs: {semantics}")
    require(actor == {"position": [57, 46], "walkbox": 1, "moving": 0}, f"actor differs: {actor}")
    require((semantics["movement_tick"], semantics["wait_blocks"], semantics["wait_releases"]) ==
            (92, 91, 0), f"movement/wait diagnostic oracle differs: "
            f"{semantics['movement_tick']},{semantics['wait_blocks']},{semantics['wait_releases']}")
    require(semantics["get_dist"] == {"pc_before": 0x038E, "pc_after": 0x0395,
                                      "result": 0, "exec_count": 1}, "getDist differs")
    require(semantics["start_object"] == {"object": 596, "entry": 10, "entry_offset": 0x29,
                                          "chain_target": 211, "object_retired": 1,
                                          "lscr_entry_seen": 1}, "startObject differs")
    require(final_camera["scroll_script"] == 214 and final_camera["scroll_script_count"] == 1,
            "scroll-script callback differs")
    if is_sa1:
        require(sa1_start == sa1_end, "SA-1 architectural state changed")
    report = {
        "gate": "Phase 6F canonical setCameraAt target semantics", "result": "pass",
        "fresh_power_on": True, "debugger_writes": 0, "terminal_frame": terminal_frame,
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "immediate": immediate, "published": published, "semantics": semantics,
        "next_blocker": {"resource": "room.49/LSCR.211", "offset": "027B",
                         "bytes": "14020f49276c6c207761697420686572652eff032a736967682a00",
                         "decode": "print actor 2: I'll wait here. <FF 03> *sigh*",
                         "classification": "encoded talk/text subsystem gap"},
        "sa1_start": sa1_start, "sa1_end": sa1_end,
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output),
                      "rom_sha256": report["rom_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
