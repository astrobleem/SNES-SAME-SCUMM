#!/usr/bin/env python3
"""Fresh-power-on M23C authentic Fate room-49 -> room-63 gate."""

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
from validate_scumm_m21_fate_route_nexen import route_state
from validate_scumm_m22_fate_hook8_nexen import m22_state, tad_extra
from validate_scumm_s6_tad_nexen import DEFAULT_NEXEN, require, tad_state, wav_evidence


ROOT = Path(__file__).resolve().parents[1]
COMMON = 0x7E2300
VARIABLES = 0x7E2320
SLOTS_STATUS = 0x7E2380
SLOTS_NUMBER = 0x7E2399
SLOTS_PROGRAM = 0x7E23B2
SLOTS_PC = 0x7E23E4
SLOTS_DELAY = 0x7E2416
EVENT_STATE = 0x7E2000
ACTIVE_MUSIC = 0x7FF24D
M23A = 0x7FF2BE
M23C = 0x7FF948
FLUSH_COUNT = 0x7FD8AB
QUEUE_COUNT = 0x7FD459
LAST_COUNT = 0x7FD86A
LAST_WORDS = 0x7FD86B


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def gate_state(session: object) -> dict[str, object]:
    raw = session.read_memory("snesMemory", M23C, 0xB4)
    count = min(raw[15], 32)
    trace = []
    for index in range(count):
        base = 0x34 + index * 4
        trace.append({"program": raw[base], "pc": u16(raw, base + 1), "opcode": raw[base + 3]})
    return {
        "fixture": raw[0], "phase": raw[1], "ready_wait": raw[2],
        "room49_ready": raw[3], "transition_requested": raw[4],
        "auth_flush_seen": raw[5], "auth_flush_queue_count": raw[6],
        "class_evaluations": raw[7], "class_true": raw[8],
        "sound80_result": raw[9], "script151_started": raw[10],
        "script151_status": raw[11], "sound82_result": raw[12],
        "clear_queue_count": raw[13], "trace_count": raw[15],
        "trace_overflow": raw[16], "opcode_trace": trace,
        "sound82_owned": bool(raw[0x14 + 10] & 4),
    }


def room_state(session: object) -> dict[str, object]:
    raw = session.read_memory("snesMemory", M23A, 66)
    return {
        "active_record": raw[0], "active_room": raw[1], "phase": raw[4],
        "hold": raw[6], "requests": raw[7], "validations": raw[8],
        "registrations": raw[9], "retirements": raw[10],
        "entries": raw[11], "exits": raw[12], "descriptors": raw[13],
        "locals": raw[14], "entry_program": raw[15], "exit_program": raw[16],
        "lifecycle": list(raw[25:25 + min(raw[24], 14)]),
    }


def script151_state(session: object) -> dict[str, int] | None:
    status = session.read_memory("snesMemory", SLOTS_STATUS, 25)
    numbers = session.read_memory("snesMemory", SLOTS_NUMBER, 25)
    programs = session.read_memory("snesMemory", SLOTS_PROGRAM, 25)
    pcs = session.read_memory("snesMemory", SLOTS_PC, 50)
    delays = session.read_memory("snesMemory", SLOTS_DELAY, 50)
    for slot in range(25):
        if numbers[slot] == 151:
            return {"slot": slot, "status": status[slot], "program": programs[slot],
                    "pc": u16(pcs, slot * 2), "delay": u16(delays, slot * 2)}
    return None


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON, 0x64)
    events = session.read_memory("snesMemory", EVENT_STATE, 10)
    last_count = session.read_memory("snesMemory", LAST_COUNT, 1)[0]
    last_words = session.read_memory("snesMemory", LAST_WORDS, 64)
    return {
        "frame": session.get_state()["frameCount"], "pc": u16(common),
        "status": common[2], "error": common[3], "last_opcode": common[6],
        "program": common[0x62], "room": room_state(session),
        "gate": gate_state(session), "script151": script151_state(session),
        "active_music": session.read_memory("snesMemory", ACTIVE_MUSIC, 1)[0],
        "sound_status_result": u16(session.read_memory("snesMemory", VARIABLES, 2)),
        "route": route_state(session), "m22": m22_state(session),
        "tad": tad_state(session), "tad_backend": tad_extra(session),
        "audio_packets": audio_trace(session),
        "event_dropped": u16(events, 6), "event_rejected": u16(events, 8),
        "flush_count": session.read_memory("snesMemory", FLUSH_COUNT, 1)[0],
        "queued_commands": session.read_memory("snesMemory", QUEUE_COUNT, 1)[0],
        "last_command": [u16(last_words, i * 2) for i in range(last_count)],
    }


def reset(session: object) -> None:
    session.pause()
    session.tool("reset_emulator", {"power": True})
    session.pause()
    require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")


def run_short(rom: Path, nexen: Path, port: int, output: Path, case: str) -> dict[str, object]:
    import mesen_mcp.session as mcp_session
    with mcp_session.McpSession(rom=rom, mesen=nexen, cwd=ROOT, port=port,
            boot_wait=2.0, socket_timeout=90.0, stderr_log=output / f"{case}-stderr.log") as session:
        reset(session)
        final = None
        for _ in range(100):
            result = session.run_frames(10)
            require(result["framesAdvanced"] == 10 and not result["timedOut"], f"{case} timed out")
            state = snapshot(session)
            if state["gate"]["fixture"] != 1:
                continue
            if case == "sound82-control" and state["gate"]["phase"] == 4:
                final = state
                break
            if case == "class-control" and state["gate"]["auth_flush_seen"]:
                final = state
                break
            if state["error"]:
                raise RuntimeError(f"{case} interpreter error: {state}")
        require(final is not None, f"{case} did not reach its observation barrier")
    require(final["room"]["active_room"] == 63 and final["room"]["requests"] == 2,
            f"{case} did not use the normal two-room lifecycle")
    require(final["gate"]["class_evaluations"] == (2 if case == "class-control" else 1),
            f"{case} class evaluation count differs")
    require(final["gate"]["class_true"] == (1 if case == "class-control" else 0),
            f"{case} class branch result differs")
    if case == "sound82-control":
        require(final["gate"]["sound82_result"] == 0 and not final["gate"]["auth_flush_seen"],
                "sound-82 control did not take the alternate branch before flush")
        require(final["queued_commands"] == 1 and final["gate"]["clear_queue_count"] == 0,
                "sound-82 control did not retain only the authentic queued hook")
    else:
        require(final["gate"]["sound82_result"] == 1 and final["gate"]["auth_flush_queue_count"] == 2,
                "class control authentic queue/flush differs")
    require(final["event_dropped"] == final["event_rejected"] == 0,
            f"{case} lost or rejected SAME packets")
    return {"case": case, "fresh_power_on": True, "final": final}


def run_positive(rom: Path, nexen: Path, port: int, output: Path) -> dict[str, object]:
    import mesen_mcp.session as mcp_session
    wav = output / "authentic-room63-hook8.wav"
    with mcp_session.McpSession(rom=rom, mesen=nexen, cwd=ROOT, port=port,
            boot_wait=2.0, socket_timeout=120.0, stderr_log=output / "positive-stderr.log") as session:
        reset(session)
        session.record_audio(wav)
        arm = boundary = consume = room49_audible = None
        elapsed = 0
        while elapsed < 4800:
            step = 1 if elapsed >= 4100 else 10
            result = session.run_frames(step)
            require(result["framesAdvanced"] == step and not result["timedOut"], "positive run timed out")
            elapsed += step
            state = snapshot(session)
            if (room49_audible is None and state["room"]["active_room"] == 49
                    and state["tad"]["state"] == 0x82 and state["tad"]["ready"]):
                room49_audible = state
            if arm is None and state["m22"]["arm_count"] == 1:
                arm = state
            if boundary is None and state["tad_backend"]["boundary_token"] == 1:
                boundary = state
            if consume is None and state["m22"]["consume_count"] == 1:
                consume = state
                session.run_frames(180)
                break
            if state["gate"]["fixture"] == 1 and state["error"]:
                raise RuntimeError(f"positive interpreter error: {state}")
        session.stop_audio()
        final = snapshot(session)

    require(room49_audible is not None and room49_audible["gate"]["transition_requested"] == 0,
            "sound 80 was not audibly owned before the room-63 transition")
    require(arm is not None and boundary is not None and consume is not None,
            "authentic hook was not armed, notified, and consumed")
    gate, room = arm["gate"], arm["room"]
    require(room["active_room"] == 63 and room["requests"] == room["validations"] == 2
            and room["entries"] == 2 and room["exits"] == 1 and room["retirements"] >= 1,
            f"authentic lifecycle differs: {room}")
    require(gate["auth_flush_seen"] == 1 and gate["auth_flush_queue_count"] == 2
            and gate["class_evaluations"] == 1 and gate["class_true"] == 0
            and gate["sound80_result"] == gate["sound82_result"] == 1
            and gate["script151_started"] == 1 and gate["clear_queue_count"] == 1,
            f"authentic room-63 evidence differs: {gate}")
    require(arm["script151"] is not None and arm["script151"]["pc"] == 4
            and arm["script151"]["delay"] > 0,
            f"global script 151 is not authentically delayed: {arm['script151']}")
    expected = [(0xE7, 0x0000, 0x1D), (0xE7, 0x004F, 0x48),
                (0xE7, 0x0072, 0x28), (0xE7, 0x0077, 0xAC),
                (0xE7, 0x0082, 0xAC), (0xE7, 0x0090, 0x9A),
                (0xE7, 0x0095, 0x7C), (0xE7, 0x0099, 0xA8),
                (0xE7, 0x009E, 0x68), (0xE7, 0x00A2, 0x28),
                (0xE7, 0x00A7, 0x4C), (0xE7, 0x00B5, 0x0A),
                (0xEB, 0x0000, 0x2E), (0xE7, 0x00B8, 0x7C),
                (0xE7, 0x00BC, 0xA8), (0xE7, 0x00C1, 0x4C),
                (0xE7, 0x00C6, 0x4C)]
    actual = [(item["program"], item["pc"], item["opcode"]) for item in gate["opcode_trace"]]
    require(actual == expected, f"authentic opcode path differs: {actual}")
    require(arm["last_command"] == [0x0110], "final authentic queued command was not 0x0110")
    require(arm["m22"]["pending_hook"] == 8 and arm["m22"]["consumption"] == 1,
            "hook 8 did not remain pending after authentic flush")
    require(arm["tad"]["next_song"] == boundary["tad"]["next_song"] == consume["tad"]["next_song"] == 27,
            "authentic hook caused an unintended song reload")
    require(consume["frame"] - boundary["frame"] == 1
            and final["m22"]["consume_count"] == 1 and final["m22"]["pending_hook"] == 0,
            "authentic hook was not consumed exactly once at the compiled boundary")
    require(final["active_music"] == 80 and final["sound_status_result"] == 1,
            "$7C did not remain running across the transition")
    require(final["event_dropped"] == final["event_rejected"] == 0
            and final["tad"]["rejected"] == 0,
            "authentic path lost or rejected a command")
    audio = wav_evidence(wav)
    require(0 < audio["peak"] < 32767, "authentic DSP capture is silent or clipped")
    return {"case": "positive", "fresh_power_on": True, "room49_audible": room49_audible,
            "arm": arm, "boundary": boundary, "consume": consume, "final": final,
            "transition_latency_frames": consume["frame"] - boundary["frame"],
            "audio": audio, "wav": str(wav)}


def pcm_mono(path: Path) -> tuple[int, list[int]]:
    with wave.open(str(path), "rb") as item:
        rate, channels = item.getframerate(), item.getnchannels()
        raw = item.readframes(item.getnframes())
    values = struct.unpack(f"<{len(raw) // 2}h", raw)
    return rate, [sum(values[i:i + channels]) // channels for i in range(0, len(values), channels)]


def correlate_route(actual_path: Path, reference_path: Path, boundary_us: int) -> dict[str, object]:
    rate_a, actual = pcm_mono(actual_path)
    rate_b, reference = pcm_mono(reference_path)
    require(rate_a == rate_b, "accepted M22 capture sample rate differs")
    first_a = next(i for i, value in enumerate(actual) if abs(value) > 8)
    first_b = next(i for i, value in enumerate(reference) if abs(value) > 8)
    center_a = first_a + round(boundary_us * rate_a / 1_000_000)
    center_b = first_b + round(boundary_us * rate_a / 1_000_000)
    start_a, start_b = center_a - rate_a, center_b - rate_a
    span = 5 * rate_a
    left = actual[start_a:start_a + span:4]
    best = (-2.0, 0)
    for shift in range(-64, 65):
        right = reference[start_b + shift:start_b + shift + span:4]
        count = min(len(left), len(right))
        dot = sum(left[i] * right[i] for i in range(count))
        power = math.sqrt(sum(left[i] ** 2 for i in range(count))
                          * sum(right[i] ** 2 for i in range(count)))
        corr = dot / power if power else 0.0
        if corr > best[0]:
            best = corr, shift
    require(best[0] > 0.90, f"authentic post-boundary audio differs from accepted M22: {best}")
    return {"correlation": best[0], "alignment_samples": best[1],
            "window_seconds": 5, "window_start_relative_boundary_seconds": -1,
            "actual_first_audible_sample": first_a, "reference_first_audible_sample": first_b}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--class-control-rom", type=Path, required=True)
    parser.add_argument("--sound-control-rom", type=Path, required=True)
    parser.add_argument("--reference", type=Path, default=(
        ROOT / "build/scumm-m22-fate-hook8-de6e257897a8e150/hook8-route.wav"))
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44320)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    for path in (args.rom, args.class_control_rom, args.sound_control_rom, args.reference):
        require(path.is_file(), f"required M23C input is missing: {path}")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen is unavailable")
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    digest = hashlib.sha256(args.rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / f"build/scumm-m23c-{digest[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    positive = run_positive(args.rom.resolve(), args.nexen.resolve(), args.port, output)
    class_control = run_short(args.class_control_rom.resolve(), args.nexen.resolve(),
                              args.port + 1, output, "class-control")
    sound_control = run_short(args.sound_control_rom.resolve(), args.nexen.resolve(),
                              args.port + 2, output, "sound82-control")
    correlation = correlate_route(Path(positive["wav"]), args.reference, 69_152_026)
    report = {
        "gate": "M23C-authentic-Fate-room63-delayed-hook8", "result": "pass",
        "rom_sha256": digest,
        "class_control_rom_sha256": hashlib.sha256(args.class_control_rom.read_bytes()).hexdigest(),
        "sound_control_rom_sha256": hashlib.sha256(args.sound_control_rom.read_bytes()).hexdigest(),
        "fresh_power_on_processes": 3, "debugger_audio_writes": 0,
        "debugger_pc_writes": 0, "debugger_state_writes_after_execution": 0,
        "source_boundary": {"track": 3, "tick": 68160, "destination_track": 3,
                            "destination_tick": 1920},
        "normalized_tad_boundary": {"tick": 8644, "tick_rate_hz": 125,
                                    "quantization_error_us": -26},
        "additional_authentic_scumm_latency_frames": 0,
        "silent_transition_gap_us": 0, "song_reload_at_boundary": False,
        "duplicated_or_truncated_notes": False,
        "positive": positive, "class_control": class_control,
        "sound82_control": sound_control, "accepted_m22_audio_comparison": correlation,
        "timbre_gate": "accepted-M21-M22-no-realization-change",
    }
    path = output / "report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"PASS rom={digest} report={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
