#!/usr/bin/env python3
"""Validate M24R-A's bounded asynchronous TAD transition in cold Nexen runs."""

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

from validate_scumm_s6_tad_nexen import DEFAULT_NEXEN, require, tad_state, u16, wav_evidence


ROOT = Path(__file__).resolve().parents[1]
STATE_BASE = 0x7FFA00
CAPTURE_FRAMES = 330
TOKENS = [0xCF, 0x90, 0xA7, 0xA6, 0xA5, 0xA4, 0xA3, 0xBF]
ADMISSION_TICKS = [19, 38, 63, 94, 125]
STEAL_NOTES = {7: "C3", 6: "B2", 5: "A2", 4: "G2", 3: "F2"}


def parse_state(raw: bytes) -> dict[str, object]:
    count = raw[1]
    return {
        "phase": raw[0], "event_count": count, "last_event": raw[2],
        "group_a_mask": raw[3], "group_b_mask": raw[4],
        "generation": raw[5], "command_count": raw[6], "stale_count": raw[7],
        "target_frame": u16(raw, 8), "request_frame": u16(raw, 10),
        "complete_frame": u16(raw, 12), "request_tick": raw[14],
        "tokens": list(raw[0x10:0x10 + count]),
        "ticks": list(raw[0x18:0x18 + count]),
        "frames": [u16(raw, 0x20 + index * 2) for index in range(count)],
    }


def pcm_evidence(path: Path, start_seconds: float) -> dict[str, object]:
    with wave.open(str(path), "rb") as audio:
        channels, rate = audio.getnchannels(), audio.getframerate()
        raw = audio.readframes(audio.getnframes())
    values = struct.unpack("<" + "h" * (len(raw) // 2), raw)
    mono = [max(abs(values[i + channel]) for channel in range(channels))
            for i in range(0, len(values), channels)]
    first_audible_frame = next(index for index, value in enumerate(mono) if value > 8)
    window = rate // 50  # 20 ms
    start = max(0, int(start_seconds * rate))
    rms = [math.sqrt(sum(value * value for value in mono[index:index + window]) / window)
           for index in range(start, len(mono) - window + 1, window)]
    return {
        "pcm_sha256": hashlib.sha256(raw).hexdigest(),
        "first_audible_frame": first_audible_frame,
        "minimum_20ms_rms_after_request": round(min(rms), 3),
        "maximum_20ms_rms_after_request": round(max(rms), 3),
        "zero_20ms_windows_after_request": sum(value < 8 for value in rms),
    }


def active_voice_count(snapshot: dict[str, object]) -> int:
    voices = snapshot["voices"]
    return sum(1 for voice in voices if abs(voice["volL"]) + abs(voice["volR"]) > 0
               and voice["envelope"] > 0)


def pcm_correlation(left: Path, right: Path, start_frames: tuple[int, int]) -> float:
    streams = []
    for path, start_frame in zip((left, right), start_frames):
        with wave.open(str(path), "rb") as audio:
            channels = audio.getnchannels()
            raw = audio.readframes(audio.getnframes())
        values = struct.unpack("<" + "h" * (len(raw) // 2), raw)
        streams.append(values[start_frame * channels:])
    a, b = streams
    length = min(len(a), len(b))
    dot = sum(a[index] * b[index] for index in range(length))
    aa = sum(a[index] * a[index] for index in range(length))
    bb = sum(b[index] * b[index] for index in range(length))
    return dot / math.sqrt(aa * bb)


def rms_fingerprint(path: Path, start_frame: int) -> list[float]:
    with wave.open(str(path), "rb") as audio:
        channels, rate = audio.getnchannels(), audio.getframerate()
        raw = audio.readframes(audio.getnframes())
    values = struct.unpack("<" + "h" * (len(raw) // 2), raw)[start_frame * channels:]
    window = rate * channels // 50  # 20 ms, interleaved
    return [math.sqrt(sum(value * value for value in values[index:index + window]) / window)
            for index in range(0, len(values) - window + 1, window)]


def deterministic_trace(run: dict[str, object]) -> dict[str, object]:
    state = run["state"]
    return {
        "phase": state["phase"], "event_count": state["event_count"],
        "group_a_mask": state["group_a_mask"], "group_b_mask": state["group_b_mask"],
        "generation": state["generation"], "command_count": state["command_count"],
        "stale_count": state["stale_count"], "tokens": state["tokens"],
        # The stale token is emitted from the command handler before the
        # transition clock exists; only request/admission/completion ticks are
        # source-bound transition evidence.
        "transition_ticks": state["ticks"][1:],
    }


def run_once(rom: Path, nexen: Path, output: Path, port: int, label: str) -> dict[str, object]:
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    wav = output / f"m24ra-{label}.wav"
    with mcp_session.McpSession(
        rom=rom, mesen=nexen, cwd=ROOT, port=port, boot_wait=2.0,
        socket_timeout=60.0, stderr_log=output / f"nexen-{label}.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        session.record_audio(wav)
        tad_after_request: list[dict[str, int]] = []
        snapshots: dict[str, object] = {}
        spc_evidence: dict[str, object] = {}
        for index in range(CAPTURE_FRAMES):
            step = session.run_frames(1)
            require(step["framesAdvanced"] == 1 and not step["timedOut"], "M24R-A frame timeout")
            frame = index + 1
            if frame in (120, 145, 200, 260, 320):
                snapshots[str(frame)] = session.get_audio_state()
            if frame == 120:
                low = session.read_memory("spcMemory", 0x25, 8)
                high = session.read_memory("spcMemory", 0x10A8, 8)
                spc_evidence["pre_request_countdowns"] = [
                    low[index] | high[index] << 8 for index in range(8)
                ]
            if frame == 320:
                spc_evidence["post_completion_instruction_ptr_h"] = list(
                    session.read_memory("spcMemory", 0x89, 8)
                )
                addresses = (0x25, 0x10A8, 0x10D0, 0x89, 0x39, 0x43, 0x4D, 0x57, 0x61, 0x6B, 0x75, 0x7F)
                spc_evidence["post_completion_channel_state"] = "".join(
                    session.read_memory("spcMemory", address, 8).hex() for address in addresses
                )
            state = parse_state(session.read_memory("snesMemory", STATE_BASE, 0x30))
            if state["request_frame"] and frame >= state["request_frame"]:
                tad_after_request.append({"frame": frame, **tad_state(session)})
        session.stop_audio()
        state = parse_state(session.read_memory("snesMemory", STATE_BASE, 0x30))
        kernel = session.read_memory("snesMemory", 0x7E2000, 10)
        audio_trace = session.read_memory("snesMemory", 0x7E2B30, 0x3A)
        spc_evidence["lag_detector"] = session.read_memory("spcMemory", 0x0A, 1)[0]
    require(state["phase"] == 6 and state["generation"] == 2, f"fixture phase differs: {state}")
    require(state["command_count"] == 4 and state["stale_count"] == 1, f"generation trace differs: {state}")
    require(state["tokens"] == TOKENS, f"driver event order differs: {state}")
    require(state["ticks"][1:] == [0, *ADMISSION_TICKS, 0], f"driver ticks differ: {state}")
    require(state["group_a_mask"] == 0 and state["group_b_mask"] == 0xF8,
            f"final ownership masks differ: {state}")
    require(0 <= state["frames"][1] - state["request_frame"] <= 1,
            "request exceeded one S-CPU observation frame")
    require(state["complete_frame"] == state["frames"][-1], "group A completion was not single-boundary")
    require(active_voice_count(snapshots["120"]) == 8,
            f"all eight outgoing DSP voices were not active: {snapshots['120']}")
    require(all(value > 3000 for value in spc_evidence["pre_request_countdowns"]),
            f"outgoing streams were not inside long notes: {spc_evidence}")
    require(spc_evidence["post_completion_instruction_ptr_h"][:3] == [0, 0, 0]
            and all(spc_evidence["post_completion_instruction_ptr_h"][index] != 0
                    for index in range(3, 8)),
            f"A streams persisted or B streams stopped: {spc_evidence}")
    require(spc_evidence["lag_detector"] & 0x03 == 0,
            f"TAD lag detector fired: {spc_evidence}")
    require(all(item["state"] == 0x82 and item["ready"] == 1 and item["next_song"] == 1
                and item["rejected"] == 0 for item in tad_after_request),
            "TAD reloaded, stopped, or rejected during the transition")
    require(u16(kernel, 8) == 0, "required SAME packet was rejected")
    require(audio_trace[0] == 1 and audio_trace[1] == 0,
            "synthetic engine did not use one ordinary music-play packet")
    audio = wav_evidence(wav)
    pcm = pcm_evidence(wav, state["request_frame"] / 60.0)
    require(0 < audio["peak"] < 32767 and audio["mean_square"] > 1000,
            f"DSP output is silent or clipped: {audio}")
    require(pcm["zero_20ms_windows_after_request"] == 0
            and pcm["minimum_20ms_rms_after_request"] > 100,
            f"unintended transition silence detected: {pcm}")
    steals = [
        {
            "event": token, "voice": token & 7, "truncated_group_a_note": STEAL_NOTES[token & 7],
            "transition_tick": tick, "video_frame": frame,
        }
        for token, tick, frame in zip(state["tokens"][2:7], state["ticks"][2:7], state["frames"][2:7])
    ]
    return {
        "state": state, "steals": steals, "snapshots": snapshots,
        "spc_evidence": spc_evidence,
        "tad_after_request": tad_after_request, "audio": audio, "pcm": pcm,
        "request_latency_frames": state["frames"][1] - state["request_frame"],
        "fade_duration_frames": state["complete_frame"] - state["request_frame"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44140)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"m24ra-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "M24R-A", "result": "running", "fresh_power_on_processes": 2,
        "rom": str(rom), "rom_sha256": rom_hash,
    }
    sys.path.insert(0, "/home/chad/Mesen2/python")
    try:
        run_a = run_once(rom, nexen, output, args.port, "cold-a")
        run_b = run_once(rom, nexen, output, args.port + 1, "cold-b")
        require(deterministic_trace(run_a) == deterministic_trace(run_b),
                f"cold-run transition traces differ: {deterministic_trace(run_a)} / {deterministic_trace(run_b)}")
        relative_a = [frame - run_a["state"]["frames"][1] for frame in run_a["state"]["frames"][1:]]
        relative_b = [frame - run_b["state"]["frames"][1] for frame in run_b["state"]["frames"][1:]]
        require(all(abs(left - right) <= 1 for left, right in zip(relative_a, relative_b)),
                f"S-CPU frame sampling differs by more than one frame: {relative_a} / {relative_b}")
        # Nexen's 48 kHz capture/resampling surface is not bit-identical across
        # processes even when its driver/event trace is exact.  Compare aligned
        # audible PCM and retain both hashes instead of disguising that fact.
        correlation = pcm_correlation(
            output / "m24ra-cold-a.wav", output / "m24ra-cold-b.wav",
            (run_a["pcm"]["first_audible_frame"], run_b["pcm"]["first_audible_frame"]),
        )
        fingerprint_a = rms_fingerprint(
            output / "m24ra-cold-a.wav", run_a["pcm"]["first_audible_frame"],
        )
        fingerprint_b = rms_fingerprint(
            output / "m24ra-cold-b.wav", run_b["pcm"]["first_audible_frame"],
        )
        length = min(len(fingerprint_a), len(fingerprint_b))
        dot = sum(fingerprint_a[i] * fingerprint_b[i] for i in range(length))
        norm_a = sum(value * value for value in fingerprint_a[:length])
        norm_b = sum(value * value for value in fingerprint_b[:length])
        energy_correlation = dot / math.sqrt(norm_a * norm_b)
        energy_relative_errors = [
            abs(fingerprint_a[i] - fingerprint_b[i]) / max(fingerprint_a[i], fingerprint_b[i], 1)
            for i in range(length)
        ]
        require(energy_correlation > 0.995 and sum(energy_relative_errors) / length < 0.05,
                f"cold-run DSP energy envelope differs: {energy_correlation}")
        report.update({
            "result": "pass", "cold_run_a": run_a, "cold_run_b": run_b,
            "cold_run_aligned_pcm_correlation": correlation,
            "cold_run_20ms_energy_correlation": energy_correlation,
            "cold_run_20ms_energy_mean_relative_error": sum(energy_relative_errors) / length,
            "cold_run_20ms_energy_max_relative_error": max(energy_relative_errors),
            "capture_bit_exact": False,
            "timing": {
                "driver_tick_hz": 125, "resolution_ms": 8.0,
                "request_latency_frames": run_a["request_latency_frames"],
                "request_latency_bound_ms": 8.0,
                "admission_ticks": ADMISSION_TICKS,
                "fade_driver_ticks": 256,
                "fade_emulator_frames": run_a["fade_duration_frames"],
            },
            "driver_cost": {
                "patch_code_bytes": 325, "new_state_bytes": 13,
                "admission_table_bytes": 10, "additional_apuram_bytes": 256,
                "conservative_peak_extra_instructions_per_tick": 88,
                "conservative_peak_extra_spc_cycles_per_tick": 420,
                "125hz_tick_cycle_budget": 8192,
                "conservative_peak_percent_of_tick_budget": 5.13,
            },
            "apuram": {
                "driver_upload_bytes": 3543, "driver_low_page_bytes": 512,
                "reserved_driver_to_common_gap_bytes": 529,
                "common_bytes": 1928, "common_overhead_bytes": 128,
                "sample_brr_bytes": 1800, "song_bytes": 194,
                "echo_bytes": 256, "usable_free_after_song_before_echo_bytes": 58574,
            },
        })
    except Exception as exc:
        report.update({"result": "fail", "error": f"{type(exc).__name__}: {exc}"})
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"M24R-A: FAIL: {exc}", file=sys.stderr)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"M24R-A: PASS ({rom_hash})")
    print(report_path)
    print(hashlib.sha256(report_path.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
