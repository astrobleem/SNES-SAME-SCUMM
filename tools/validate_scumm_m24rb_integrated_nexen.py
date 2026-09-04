#!/usr/bin/env python3
"""Fresh-power-on authentic SCUMM + composite M24R-B integration gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import wave

from validate_scumm_m23c_nexen import (
    ACTIVE_MUSIC, EVENT_STATE, ROOT, gate_state, room_state, script151_state,
)
from validate_scumm_s6_tad_nexen import DEFAULT_NEXEN, require, tad_state, u16, wav_evidence

M24RA = 0x7FFA00
M24RB = 0x7FFA30
TOKENS = [0x90, 0xA7, 0xA6, 0xA5, 0xA4, 0xA3, 0xBF]
LOOP_SECONDS = 103.447623


def m24_state(session: object) -> dict[str, object]:
    raw = session.read_memory("snesMemory", M24RA, 0x40)
    count = min(raw[1], 8)
    return {
        "event_count": count,
        "tokens": list(raw[0x10:0x10 + count]),
        "ticks": list(raw[0x18:0x18 + count]),
        "frames": [u16(raw, 0x20 + index * 2) for index in range(count)],
        "request_frame": u16(raw, 0x0A), "complete_frame": u16(raw, 0x0C),
        "logical82": raw[0x30], "trigger_marker": raw[0x31],
        "deferred_count": raw[0x32], "marker_count": raw[0x33],
        "fade_complete_count": raw[0x34], "lscr_scheduled": raw[0x35],
        "frame_end_flushes": raw[0x36], "frame_end_active": raw[0x37],
    }


def continuity(path: Path, center_seconds: float) -> dict[str, object]:
    with wave.open(str(path), "rb") as item:
        rate, channels = item.getframerate(), item.getnchannels()
        raw = item.readframes(item.getnframes())
    pcm = struct.unpack(f"<{len(raw) // 2}h", raw)
    mono = [max(abs(value) for value in pcm[index:index + channels])
            for index in range(0, len(pcm), channels)]
    start = max(0, round((center_seconds - 1.0) * rate))
    end = min(len(mono), round((center_seconds + 3.0) * rate))
    window = max(1, round(0.020 * rate))
    silent = sum(1 for index in range(start, max(start, end - window), window)
                 if max(mono[index:index + window], default=0) <= 8)
    return {"center_seconds": center_seconds, "window_seconds": 4.0,
            "silent_20ms_windows": silent}


def run(rom: Path, nexen: Path, output: Path, port: int, require_loop: bool) -> dict[str, object]:
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    wav = output / ("m24rb-authentic-full.wav" if require_loop else "m24rb-relocation-short.wav")
    transitions: list[dict[str, int]] = []
    room_changes: list[dict[str, int]] = []
    tad_lifecycle: list[dict[str, int]] = []
    previous_logical = previous_room = None
    previous_tad = None
    active_frame = marker_frame = fading_frame = stopped_frame = None
    max_frames = 9300 if require_loop else 3000
    with mcp_session.McpSession(rom=rom, mesen=nexen, cwd=ROOT, port=port,
            boot_wait=2.0, socket_timeout=180.0, stderr_log=output / "stderr.log") as session:
        session.pause(); session.tool("reset_emulator", {"power": True}); session.pause()
        require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")
        session.record_audio(wav)
        for frame in range(5, max_frames + 1, 5):
            step = session.run_frames(5)
            require(step["framesAdvanced"] == 5 and not step["timedOut"], "emulator frame timeout")
            m24 = m24_state(session); room = room_state(session); tad = tad_state(session)
            if m24["logical82"] != previous_logical:
                transitions.append({"frame": frame, "logical82": int(m24["logical82"])})
                previous_logical = m24["logical82"]
                if m24["logical82"] == 2: active_frame = frame
                if m24["logical82"] == 3: fading_frame = frame
                if m24["logical82"] == 4: stopped_frame = frame
            if room["active_room"] != previous_room:
                room_changes.append({"frame": frame, "room": int(room["active_room"])})
                previous_room = room["active_room"]
            tad_key = (tad["state"], tad["ready"], tad["next_song"])
            if tad_key != previous_tad:
                tad_lifecycle.append({"frame": frame, "state": tad["state"],
                                      "ready": tad["ready"], "song": tad["next_song"]})
                previous_tad = tad_key
            if m24["marker_count"] and marker_frame is None: marker_frame = frame
            if stopped_frame is not None:
                session.run_frames(180)
                break
        final_frame = session.get_state()["frameCount"]
        final_m24 = m24_state(session); final_room = room_state(session)
        final_gate = gate_state(session); final_tad = tad_state(session)
        final_script151 = script151_state(session)
        active_music = session.read_memory("snesMemory", ACTIVE_MUSIC, 1)[0]
        kernel = session.read_memory("snesMemory", EVENT_STATE, 10)
        audio_state = session.get_audio_state()
        session.stop_audio()

    (output / "raw-observation.json").write_text(json.dumps({
        "transitions": transitions, "room_changes": room_changes,
        "tad_lifecycle": tad_lifecycle, "final_frame": final_frame,
        "m24": final_m24, "room": final_room, "gate": final_gate,
        "tad": final_tad, "active_music": active_music,
        "kernel": kernel.hex(), "script151": final_script151,
    }, indent=2, sort_keys=True) + "\n")
    require([item["logical82"] for item in transitions] == [0, 1, 2, 3, 4],
            f"logical sound-82 lifecycle differs: {transitions}")
    require(active_frame is not None and marker_frame is not None and active_frame == marker_frame,
            "marker 8 did not activate deferred sound 82")
    require(fading_frame is not None and stopped_frame is not None and stopped_frame > fading_frame,
            "room-63 fade did not complete")
    require(final_room["active_room"] == 63 and final_room["requests"] == 2
            and final_room["validations"] == 2 and final_room["entries"] == 2
            and final_room["exits"] == 1 and final_room["retirements"] >= 1,
            f"authentic room lifecycle differs: {final_room}")
    require(final_gate["auth_flush_seen"] == 1 and final_gate["auth_flush_queue_count"] == 2
            and final_gate["sound82_result"] == 1 and final_gate["clear_queue_count"] == 1
            and final_gate["script151_started"] == 1,
            f"authentic room-63 command path differs: {final_gate}")
    require(final_script151 is not None, "authentic global script 151 was not scheduler-owned")
    require(final_m24["tokens"] == TOKENS and final_m24["ticks"] == [0, 19, 38, 63, 94, 125, 0],
            f"bounded transition schedule differs: {final_m24}")
    require(final_m24["marker_count"] == final_m24["fade_complete_count"] == 1
            and final_m24["lscr_scheduled"] == 1 and final_m24["frame_end_flushes"] == 2
            and final_m24["logical82"] == 4,
            f"M24R-B ownership counters differ: {final_m24}")
    require(active_music == 80 and not final_gate["sound82_owned"],
            "logical sound 80/82 ownership did not separate after fade")
    require(final_tad["state"] == 0x82 and final_tad["ready"] == 1
            and final_tad["next_song"] == 1 and final_tad["rejected"] == 0,
            f"physical composite was reloaded or rejected: {final_tad}")
    require(all(item["song"] in (0, 1, 0xFF) for item in tad_lifecycle)
            and not any(item["frame"] > active_frame and item["song"] == 0 for item in tad_lifecycle),
            f"unexpected post-marker song lifecycle: {tad_lifecycle}")
    require(u16(kernel, 6) == 0 and u16(kernel, 8) == 0,
            f"SAME packets dropped or rejected: {kernel.hex()}")
    if require_loop:
        require(fading_frame - active_frame >= round(LOOP_SECONDS * 60),
                f"sound 82 did not remain active for a complete source loop: {fading_frame-active_frame} frames")
    audio = wav_evidence(wav)
    require(0 < audio["peak"] < 32767 and audio["mean_square"] > 1000, "DSP output is silent or clipped")
    transition_audio = continuity(wav, fading_frame / 60.0)
    require(transition_audio["silent_20ms_windows"] == 0, "room-63 transition contains unintended silence")
    loop_audio = None
    if require_loop:
        loop_audio = continuity(wav, active_frame / 60.0 + LOOP_SECONDS)
        require(loop_audio["silent_20ms_windows"] == 0, "sound-82 loop seam contains unintended silence")
    voices = audio_state["voices"]
    require(not any(voice["envelope"] > 0 and abs(voice["volL"]) + abs(voice["volR"]) == 0
                    for voice in voices), "stuck zero-gain DSP voice remains")
    return {
        "fresh_power_on": True, "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
        "final_frame": final_frame, "logical_lifecycle": transitions, "room_changes": room_changes,
        "marker_frame": marker_frame, "active_frames_before_fade": fading_frame - active_frame,
        "tad_lifecycle": tad_lifecycle, "m24": final_m24, "room": final_room,
        "gate": final_gate, "tad": final_tad, "audio": audio,
        "transition_continuity": transition_audio, "loop_continuity": loop_audio,
        "wav": str(wav),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=44620)
    parser.add_argument("--require-loop", action="store_true")
    args = parser.parse_args()
    require(args.rom.is_file(), f"ROM is missing: {args.rom}")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen is unavailable")
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, "/home/chad/Mesen2/python")
    result = run(args.rom.resolve(), args.nexen.resolve(), output, args.port, args.require_loop)
    report = {"gate": "M24R-B-authentic-combined", "result": "pass", "run": result}
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(output / "report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
