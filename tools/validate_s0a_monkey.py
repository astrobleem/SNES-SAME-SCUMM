#!/usr/bin/env python3
"""Freeze the supplied Super Monkey Island binary's observed frontier.

This is a characterization baseline, not a correctness oracle.  It preserves
working and broken behavior alike and never edits the donor checkout.
"""

from __future__ import annotations

import argparse
import array
import base64
import hashlib
import json
import math
from pathlib import Path
import sys
import wave


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = Path("/home/chad/SuperMonkeyIsland-pcm")
NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")

ROM_SHA256 = "89090a712861492b2573812c220e2dd77d241c9e1b55c87e1e126207132fe803"
MSU_SHA256 = "b2da89560389496968b11eaf9dca01699bb8884189c1d75c365aeee29fa240b2"
SYM_SHA256 = "ede3933e989292fef2490cf9a68707006221bc153db9e623d8d221ef2a7b2f96"

SCUMM_CUTSCENE = 0x7EF7E3
SCUMM_CURRENT_ROOM = 0x7EF7E5
SCUMM_NEW_ROOM = 0x7EF7E7
SCUMM_MUSIC_MODE = 0x7EF7EB
FRAME_COUNTER = 0x7EFC7C
SCREEN_BRIGHTNESS = 0x7EFC83
INPUT_DEVICE = 0x7EFD7C
LAST_CHECKPOINT = 0x7E1A5D
EXC_ERR = 0x7E19A2
EXC_PC = 0x7E19A0


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def capture(session: object, path: Path) -> dict[str, object]:
    result = session.take_screenshot(format="base64")
    raw = base64.b64decode(result["base64"])
    path.write_bytes(raw)
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def snapshot(session: object, label: str) -> dict[str, object]:
    room = session.read_memory("snesMemory", SCUMM_CUTSCENE, 10)
    frame = session.read_memory("snesMemory", FRAME_COUNTER, 9)
    inp = session.read_memory("snesMemory", INPUT_DEVICE, 8)
    cpu = session.get_cpu_state()
    ppu = session.get_ppu_state()
    return {
        "label": label,
        "video_frame": session.get_state()["frameCount"],
        "engine_frame": u16(frame),
        "room": room[2],
        "new_room": room[4],
        "cutscene_nest": room[0],
        "music_mode": u16(room, 8),
        "last_checkpoint": u16(session.read_memory("snesMemory", LAST_CHECKPOINT, 2)),
        "brightness_shadow": frame[7],
        "input_press": u16(inp),
        "input_trigger": u16(inp, 2),
        "cpu": cpu,
        "ppu": {
            "forcedBlank": ppu.get("forcedBlank"),
            "brightness": ppu.get("brightness"),
            "bgMode": ppu.get("bgMode"),
            "mainScreenLayers": ppu.get("mainScreenLayers"),
        },
    }


def state_digest(session: object) -> dict[str, str]:
    regions = {
        "scumm_wram": session.read_memory("snesMemory", 0x7E8000, 0x8000),
        "upper_wram": session.read_memory("snesMemory", 0x7F0000, 0x10000),
        "vram": session.read_memory("snesVideoRam", 0, 0x10000),
        "cgram": session.read_memory("snesCgRam", 0, 0x200),
        "oam": session.read_memory("snesSpriteRam", 0, 0x220),
    }
    return {name: hashlib.sha256(raw).hexdigest() for name, raw in regions.items()}


def wav_evidence(path: Path) -> dict[str, object]:
    count = 0
    total_square = 0
    peak = 0
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        rate = wav.getframerate()
        frames = wav.getnframes()
        require(width == 2, f"unexpected WAV sample width: {width}")
        while raw := wav.readframes(65536):
            samples = array.array("h")
            samples.frombytes(raw)
            if sys.byteorder != "little":
                samples.byteswap()
            count += len(samples)
            for sample in samples:
                peak = max(peak, abs(sample))
                total_square += sample * sample
    rms = math.sqrt(total_square / count) if count else 0.0
    return {
        "path": str(path),
        "sha256": sha(path),
        "bytes": path.stat().st_size,
        "channels": channels,
        "sample_width": width,
        "sample_rate": rate,
        "frames": frames,
        "seconds": frames / rate if rate else 0,
        "peak": peak,
        "rms": rms,
        "nonzero": peak > 0 and rms > 0,
    }


def hook_events(notifications: list[dict[str, object]], handles: dict[str, int]) -> dict[str, list[dict[str, object]]]:
    by_handle = {value: key for key, value in handles.items()}
    events = {key: [] for key in handles}
    for note in notifications:
        params = note.get("params", {})
        name = by_handle.get(params.get("handle"))
        if name is not None:
            events[name].append(params)
    return events


def advance_exact(session: object, frames: int) -> None:
    """Advance exactly in bounded calls so recorded audio stays below timeout."""
    while frames:
        count = min(frames, 100)
        result = session.run_frames(count)
        advanced = int(result["framesAdvanced"])
        require(
            0 < advanced <= count,
            f"frame advance made invalid progress: requested={count}, response={result}",
        )
        frames -= advanced


def drive_input(session: object, buttons: int, frames: int) -> None:
    """Hold an exact controller state while frame-exact advancement runs."""
    session.tool("set_input", {"port": 0, "buttons": buttons, "hold": True})
    try:
        advance_exact(session, frames)
    finally:
        session.tool("set_input", {"port": 0, "buttons": 0, "hold": True})


def advance_released(session: object, frames: int) -> None:
    drive_input(session, 0, frames)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=43983)
    parser.add_argument("--bursts", type=int, default=16)
    parser.add_argument(
        "--deep-msu-hooks",
        action="store_true",
        help="also trace MSU data reads and seek/volume/control writes (short probes only)",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rom = BUNDLE / "SuperMonkeyIsland.sfc"
    msu = BUNDLE / "SuperMonkeyIsland.msu"
    sym = BUNDLE / "SuperMonkeyIsland.sym"
    for path in (rom, msu, sym, NEXEN):
        require(path.is_file(), f"missing artifact: {path}")
    require(sha(rom) == ROM_SHA256, "ROM identity changed")
    require(sha(msu) == MSU_SHA256, "MSU identity changed")
    require(sha(sym) == SYM_SHA256, "SYM identity changed")

    out = (args.output or ROOT / "build" / f"s0a-monkey-{ROM_SHA256[:16]}").resolve()
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "report.json"
    audio_path = out / "intro-through-frontier.wav"
    save_path = out / "dock-frontier.mss"
    report: dict[str, object] = {
        "gate": "S0A",
        "classification": "known-incomplete behavioral baseline, not semantic oracle",
        "result": "running",
        "fresh_power_on": True,
        "bundle": str(BUNDLE),
        "rom": {"path": str(rom), "bytes": rom.stat().st_size, "sha256": ROM_SHA256},
        "msu": {"path": str(msu), "bytes": msu.stat().st_size, "sha256": MSU_SHA256},
        "sym": {"path": str(sym), "bytes": sym.stat().st_size, "sha256": SYM_SHA256},
        "timeline": [],
        "screenshots": [],
        "save_reload": {"attempted": False},
    }

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session

    mcp_session.validate_mesen_build = lambda _path: None
    handles: dict[str, int] = {}
    try:
        with mcp_session.McpSession(
            rom=rom,
            mesen=NEXEN,
            cwd=BUNDLE,
            port=args.port,
            boot_wait=3.0,
            socket_timeout=180.0,
            stderr_log=out / "nexen-stderr.log",
        ) as session:
            session.pause()
            session.tool("reset_emulator", {"power": True})
            session.pause()
            require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")

            handles["msu_track_writes"] = session.add_write_hook(0x002004, 0x002005)
            if args.deep_msu_hooks:
                handles["msu_data_reads"] = session.add_read_hook(0x002001)
                handles["msu_seek_control_writes"] = session.add_write_hook(0x002002, 0x002007)
            handles["error_trigger"] = session.add_exec_hook(0x005F88)

            session.record_audio(audio_path)
            advance_released(session, 300)
            state = snapshot(session, "boot-300")
            report["timeline"].append(state)
            shot = {"label": state["label"], "room": state["room"], "video_frame": state["video_frame"]}
            shot.update(capture(session, out / "boot-300.png"))
            report["screenshots"].append(shot)

            saved = False
            previous_room = state["room"]
            for index in range(args.bursts):
                drive_input(session, session.BTN_START, 40)
                advance_released(session, 760)
                state = snapshot(session, f"start-burst-{index + 1:02d}")
                report["timeline"].append(state)
                room_changed = state["room"] != previous_room
                if room_changed or state["room"] in {33, 38} or index in {0, 3, 7, 11, 15}:
                    name = f"burst-{index + 1:02d}-room-{int(state['room']):03d}.png"
                    shot = {"label": state["label"], "room": state["room"], "video_frame": state["video_frame"]}
                    shot.update(capture(session, out / name))
                    report["screenshots"].append(shot)

                if state["room"] == 33 and not saved:
                    advance_released(session, 120)
                    before = snapshot(session, "dock-save-before")
                    before_digest = state_digest(session)
                    before_shot = capture(session, out / "dock-save-before.png")
                    session.save_state(save_path)
                    advance_released(session, 180)
                    session.load_state(save_path)
                    session.pause()
                    after = snapshot(session, "dock-save-after-load")
                    after_digest = state_digest(session)
                    after_shot = capture(session, out / "dock-save-after-load.png")
                    report["save_reload"] = {
                        "attempted": True,
                        "path": str(save_path),
                        "before": before,
                        "after": after,
                        "before_digest": before_digest,
                        "after_digest": after_digest,
                        "state_exact": before_digest == after_digest,
                        "before_screenshot": before_shot,
                        "after_screenshot": after_shot,
                        "screenshot_exact": before_shot["sha256"] == after_shot["sha256"],
                    }
                    saved = True
                previous_room = state["room"]

            session.stop_audio()
            notifications = session.drain_notifications(timeout=0.5)
            report["hooks"] = hook_events(notifications, handles)
            report["audio"] = wav_evidence(audio_path)
            final = snapshot(session, "final")
            report["final"] = final
            report["exception_state"] = {
                "exc_err": u16(session.read_memory("snesMemory", EXC_ERR, 2)),
                "exc_pc": u16(session.read_memory("snesMemory", EXC_PC, 2)),
            }
            report["result"] = "observed"
    except Exception as exc:
        try:
            if audio_path.exists():
                report["audio"] = wav_evidence(audio_path)
        except Exception:
            pass
        report["result"] = "harness-failure"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"S0A: HARNESS FAILURE: {exc}", file=sys.stderr)
        print(report_path)
        return 1

    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("S0A: OBSERVED")
    print("rooms:", [(x["label"], x["room"], x["new_room"]) for x in report["timeline"]])
    print("audio:", report["audio"])
    print("save/reload:", report["save_reload"])
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
