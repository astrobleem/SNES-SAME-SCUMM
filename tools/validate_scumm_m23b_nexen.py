#!/usr/bin/env python3
"""Fresh-power-on M23B authentic Fate room-49 execution gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
import wave

from validate_scumm_m19_monkey_music_nexen import audio_trace
from validate_scumm_s6_tad_nexen import DEFAULT_NEXEN, require, tad_state, wav_evidence


ROOT = Path(__file__).resolve().parents[1]
COMMON = 0x7E2300
M23A = 0x7FF2BE
M23B = 0x7FF460
ACTIVE_MUSIC = 0x7FF24D
ROUTE = 0x7FF25A
FLUSH_COUNT = 0x7FD8AB
EVENT_STATE = 0x7E2000


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def route_state(session: object) -> dict[str, object]:
    raw = session.read_memory("snesMemory", ROUTE, 85)
    count = min(raw[4], 16)
    return {
        "kind": raw[0], "value": raw[1], "song": raw[2],
        "resolution_count": raw[3], "history_count": raw[4],
        "operations": list(raw[5:5 + count]),
        "kinds": list(raw[21:21 + count]),
        "values": list(raw[37:37 + count]),
        "songs": list(raw[53:53 + count]),
        "logical_ids": list(raw[69:69 + count]),
    }


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON, 0x64)
    room = session.read_memory("snesMemory", M23A, 66)
    gate = session.read_memory("snesMemory", M23B, 7)
    events = session.read_memory("snesMemory", EVENT_STATE, 10)
    return {
        "pc": u16(common), "status": common[2], "error": common[3],
        "last_opcode": common[6], "frame_ops": u16(common, 10),
        "total_ops": u16(common, 12), "fixture": common[0x5F],
        "program": common[0x62], "active_room": room[1], "phase": room[4],
        "hold": room[6], "requests": room[7], "validations": room[8],
        "registrations": room[9], "entry_count": room[11],
        "entry_program": room[15], "lifecycle": list(room[25:25 + min(room[24], 14)]),
        "fixture_applied": gate[0], "auth_flush_seen": gate[1],
        "auth_flush_queue_count": gate[2], "hold_after_flush": gate[3],
        "hold_after_condition": gate[4],
        "nest_depth": gate[5], "error_site": gate[6],
        "flush_count": session.read_memory("snesMemory", FLUSH_COUNT, 1)[0],
        "active_music": session.read_memory("snesMemory", ACTIVE_MUSIC, 1)[0],
        "route": route_state(session), "tad": tad_state(session),
        "audio_trace": audio_trace(session),
        "event_dropped": u16(events, 6), "event_rejected": u16(events, 8),
    }


def pcm(path: Path) -> tuple[int, list[int]]:
    with wave.open(str(path), "rb") as audio:
        rate, channels = audio.getframerate(), audio.getnchannels()
        raw = audio.readframes(audio.getnframes())
    values = struct.unpack(f"<{len(raw) // 2}h", raw)
    mono = [sum(values[i:i + channels]) // channels
            for i in range(0, len(values), channels)]
    return rate, mono


def prefix_correlation(actual: Path, reference: Path) -> dict[str, object]:
    rate_a, left = pcm(actual)
    rate_b, right = pcm(reference)
    require(rate_a == rate_b, "M21 reference sample rate differs")
    first_l = next(i for i, value in enumerate(left) if abs(value) > 8)
    first_r = next(i for i, value in enumerate(right) if abs(value) > 8)
    # Compare a decimated two-second audible prefix. Local alignment absorbs
    # only capture-start jitter; it cannot hide a different arrangement.
    span = min(rate_a * 2, len(left) - first_l, len(right) - first_r)
    a = left[first_l:first_l + span:4]
    best = (-2.0, 0)
    for shift in range(-32, 33):
        if shift < 0:
            x, y = a[-shift:], right[first_r:first_r + span:4][:len(a) + shift]
        else:
            x, y = a[:len(a) - shift], right[first_r:first_r + span:4][shift:]
        count = min(len(x), len(y))
        dot = sum(x[i] * y[i] for i in range(count))
        power = math.sqrt(sum(x[i] * x[i] for i in range(count)) *
                          sum(y[i] * y[i] for i in range(count)))
        corr = dot / power if power else 0.0
        if corr > best[0]:
            best = corr, shift * 4
    return {"correlation": best[0], "alignment_samples": best[1],
            "actual_first_audible": first_l, "reference_first_audible": first_r,
            "compared_samples": span}


def run(rom: Path, nexen: Path, port: int, output: Path, *, negative: bool) -> dict[str, object]:
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    case = "negative" if negative else "positive"
    wav = output / f"m23b-{case}.wav"
    with mcp_session.McpSession(
        rom=rom, mesen=nexen, cwd=ROOT, port=port, boot_wait=2.0,
        socket_timeout=90.0, stderr_log=output / f"{case}-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")
        if not negative:
            session.record_audio(wav)
        timeline = []
        final = None
        state = snapshot(session)
        # Authentic scripts 144/145 execute before the room's music block;
        # leave the accepted TAD loader its normal post-command frame budget.
        for _ in range(650):
            result = session.run_frames(1)
            require(result["framesAdvanced"] == 1 and not result["timedOut"],
                    f"{case} frame timed out")
            state = snapshot(session)
            if not timeline or (state["phase"], state["pc"], state["tad"]["state"]) != (
                    timeline[-1]["phase"], timeline[-1]["pc"], timeline[-1]["tad"]["state"]):
                timeline.append(state)
            if negative and state["hold"]:
                final = state
                break
            if (not negative and state["auth_flush_seen"] and state["hold"]
                    and state["tad"]["state"] == 0x82 and state["tad"]["ready"]
                    and state["tad"]["next_song"] == 27):
                final = state
                session.run_frames(150)
                break
        require(final is not None,
                f"{case} did not reach its observation barrier; final={state}")
        if not negative:
            session.stop_audio()

    require(final["fixture_applied"] == 1 and final["fixture"] == 0x42,
            f"{case} did not use boot-bound state/room driver")
    require(final["active_room"] == 49 and final["requests"] == 1
            and final["validations"] == 1 and final["entry_count"] == 1,
            f"{case} normal room lifecycle differs")
    require(final["event_dropped"] == 0 and final["event_rejected"] == 0,
            f"{case} lost or rejected SAME packets")
    if negative:
        require(final["pc"] == 0x006D and final["auth_flush_seen"] == 0
                and final["flush_count"] == 0 and final["active_music"] == 81,
                f"negative authentic branch differs: {final}")
        require(final["audio_trace"] == [], "negative control emitted an audio packet")
    else:
        require(final["pc"] == 0x006A and final["auth_flush_seen"] == 1
                and final["auth_flush_queue_count"] == 2 and final["flush_count"] == 1,
                f"authentic single flush differs: {final}")
        require(final["active_music"] == 80 and (final["route"]["kind"],
                final["route"]["value"], final["route"]["song"]) == (1, 14, 27),
                f"hook-14 route ownership differs: {final['route']}")
        require(not any(item["tad"]["state"] == 0x82 and item["tad"]["ready"]
                        and item["tad"]["next_song"] == 26 for item in timeline),
                "default route reached ready/playing ownership before hook replacement")
        require(final["tad"]["rejected"] == 0, "TAD rejected an authentic-path command")
        audio = wav_evidence(wav)
        require(0 < audio["peak"] < 32767, "authentic hook-14 capture is silent or clipped")
        return {"case": case, "fresh_power_on": True, "final": final,
                "timeline": timeline, "audio": audio, "wav": str(wav)}
    return {"case": case, "fresh_power_on": True, "final": final, "timeline": timeline}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--negative-rom", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reference", type=Path, default=(
        ROOT / "build/scumm-m21-fate-route-b16fcb68583506d0/hook14-route-excerpt.wav"))
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44230)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    for path in (args.rom, args.negative_rom, args.reference, args.manifest):
        require(path.is_file(), f"required M23B input is missing: {path}")
    default_reference = args.reference.with_name("default-route-excerpt.wav")
    require(default_reference.is_file(),
            f"accepted M21 default-route control is missing: {default_reference}")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen is unavailable")
    digest = hashlib.sha256(args.rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / f"build/scumm-m23b-{digest[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {"gate": "M23B-authentic-Fate-room49-ENCD", "result": "running",
              "rom_sha256": digest,
              "negative_rom_sha256": hashlib.sha256(args.negative_rom.read_bytes()).hexdigest(),
              "debugger_audio_writes": 0, "debugger_pc_writes": 0,
              "debugger_state_writes_after_execution": 0,
              "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest()}
    path = output / "report.json"
    try:
        positive = run(args.rom.resolve(), args.nexen.resolve(), args.port, output, negative=False)
        negative = run(args.negative_rom.resolve(), args.nexen.resolve(), args.port + 1,
                       output, negative=True)
        comparison = prefix_correlation(Path(positive["wav"]), args.reference)
        default_comparison = prefix_correlation(Path(positive["wav"]), default_reference)
        require(comparison["correlation"] > 0.80
                and comparison["correlation"] - default_comparison["correlation"] > 0.70,
                "authentic DSP prefix does not discriminate the accepted M21 "
                f"hook route from its default-route control: hook={comparison}, "
                f"default={default_comparison}")
        report.update({"result": "pass", "positive": positive, "negative": negative,
                       "accepted_m21_audio": str(args.reference),
                       "accepted_m21_default_control": str(default_reference),
                       "audio_comparison": comparison,
                       "default_control_comparison": default_comparison})
    except Exception as exc:
        report.update({"result": "fail", "error": f"{type(exc).__name__}: {exc}"})
        path.write_text(json.dumps(report, indent=2) + "\n")
        print(f"M23B: FAIL: {exc}", file=sys.stderr)
        print(path)
        return 1
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("M23B: PASS (authentic room-49 ENCD -> single flush -> hook-14 DSP)")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
