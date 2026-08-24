#!/usr/bin/env python3
"""Map the supplied Super Monkey Island binary's natural fresh-power timeline."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = Path("/home/chad/SuperMonkeyIsland-pcm")
NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def snap(session: object) -> dict[str, object]:
    scumm = session.read_memory("snesMemory", 0x7EF7E3, 10)
    core = session.read_memory("snesMemory", 0x7E1A5D, 2)
    frame = session.read_memory("snesMemory", 0x7EFC7C, 9)
    inp = session.read_memory("snesMemory", 0x7EFD7C, 8)
    cpu = session.get_cpu_state()
    ppu = session.get_ppu_state()
    return {
        "video_frame": session.get_state()["frameCount"],
        "engine_frame": u16(frame),
        "room": scumm[2],
        "new_room": scumm[4],
        "cutscene_nest": scumm[0],
        "music_mode": u16(scumm, 8),
        "last_checkpoint": u16(core),
        "brightness": frame[7],
        "input_press": u16(inp, 0),
        "input_trigger": u16(inp, 2),
        "cpu": cpu,
        "ppu": {
            "forcedBlank": ppu.get("forcedBlank"),
            "brightness": ppu.get("brightness"),
            "bgMode": ppu.get("bgMode"),
            "mainScreenLayers": ppu.get("mainScreenLayers"),
        },
    }


def screenshot(session: object, path: Path) -> dict[str, object]:
    shot = session.take_screenshot(format="base64")
    raw = base64.b64decode(shot["base64"])
    path.write_bytes(raw)
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=int, default=6000)
    parser.add_argument("--step", type=int, default=100)
    parser.add_argument("--port", type=int, default=43982)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rom = BUNDLE / "SuperMonkeyIsland.sfc"
    msu = BUNDLE / "SuperMonkeyIsland.msu"
    sym = BUNDLE / "SuperMonkeyIsland.sym"
    for path in (rom, msu, sym, NEXEN):
        if not path.is_file():
            raise SystemExit(f"missing: {path}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    out = (args.output or ROOT / "build" / f"s0a-probe-{rom_hash[:16]}").resolve()
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "timeline.json"
    report: dict[str, object] = {
        "result": "running",
        "fresh_power_on": True,
        "bundle": str(BUNDLE),
        "rom_sha256": rom_hash,
        "msu_sha256": hashlib.sha256(msu.read_bytes()).hexdigest(),
        "sym_sha256": hashlib.sha256(sym.read_bytes()).hexdigest(),
        "requested_frames": args.frames,
        "step": args.step,
        "timeline": [],
        "screenshots": [],
    }

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session

    mcp_session.validate_mesen_build = lambda _path: None
    fixed_shots = {100, 500, 1000, 1500, 2000, 3000, 4000, 5000, 6000}
    try:
        with mcp_session.McpSession(
            rom=rom,
            mesen=NEXEN,
            cwd=BUNDLE,
            port=args.port,
            boot_wait=3.0,
            socket_timeout=60.0,
            stderr_log=out / "nexen-stderr.log",
        ) as session:
            session.pause()
            session.tool("reset_emulator", {"power": True})
            session.pause()
            if session.get_state()["frameCount"] != 0:
                raise RuntimeError("power reset did not reach frame zero")
            initial = snap(session)
            report["timeline"].append(initial)
            previous_room = initial["room"]
            advanced = 0
            while advanced < args.frames:
                count = min(args.step, args.frames - advanced)
                run = session.run_frames(count)
                if run["framesAdvanced"] != count or run["timedOut"]:
                    raise RuntimeError(f"frame step failed at {advanced}: {run}")
                advanced += count
                state = snap(session)
                report["timeline"].append(state)
                room_changed = state["room"] != previous_room
                if room_changed or advanced in fixed_shots:
                    tag = f"frame-{advanced:06d}-room-{int(state['room']):03d}"
                    item = {"frame": advanced, "room": state["room"]}
                    item.update(screenshot(session, out / f"{tag}.png"))
                    report["screenshots"].append(item)
                previous_room = state["room"]
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"S0A probe: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1

    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    rooms = [(x["video_frame"], x["room"], x["new_room"]) for x in report["timeline"]]
    compressed = []
    for item in rooms:
        if not compressed or item[1:] != compressed[-1][1:]:
            compressed.append(item)
    print("S0A probe: PASS")
    print("room timeline:", compressed)
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
