#!/usr/bin/env python3
"""Prove the generic M5 Monkey song through real S-SMP/DSP execution."""

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

from validate_scumm_s6_tad_nexen import (
    DEFAULT_NEXEN, GateFailure, require, run_exact_frames, tad_state, u16,
    wav_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "build/same-scumm-v5-monkey-m5.sfc"
DEFAULT_BUILD_REPORT = ROOT / "build/monkey-v5-tad-m5/report.json"
CAPTURE_FRAMES = 3_900


def _mono(path: Path) -> tuple[int, list[int]]:
    with wave.open(str(path), "rb") as audio:
        channels = audio.getnchannels()
        rate = audio.getframerate()
        raw = audio.readframes(audio.getnframes())
    samples = struct.unpack(f"<{len(raw) // 2}h", raw)
    if channels == 1:
        return rate, list(samples)
    return rate, [
        sum(samples[index:index + channels]) // channels
        for index in range(0, len(samples), channels)
    ]


def loop_evidence(path: Path, loop_ticks: int) -> dict[str, object]:
    rate, samples = _mono(path)
    first = next((index for index, value in enumerate(samples) if abs(value) > 8), None)
    require(first is not None, "M5 capture has no audible sample")
    nominal_shift = round(loop_ticks * rate / 125)
    # Nexen models the configured 32,040 Hz SPC clock; TAD's score timing is
    # authored against nominal 32 kHz, so real playback is faster by 32040/32000.
    clock_corrected_shift = round(loop_ticks * rate * 32_000 / (125 * 32_040))
    window_start = first + rate // 2
    window_length = rate // 2
    expected = window_start + clock_corrected_shift
    require(expected + window_length + rate // 10 < len(samples),
            "M5 capture does not extend far enough beyond the loop")
    def correlation(offset: int, stride: int) -> float | None:
        candidate_start = expected + offset
        left = samples[window_start:window_start + window_length:stride]
        candidate = samples[candidate_start:candidate_start + window_length:stride]
        if len(candidate) != len(left):
            return None
        dot = sum(a * b for a, b in zip(left, candidate))
        left_power = sum(value * value for value in left)
        right_power = sum(value * value for value in candidate)
        return dot / math.sqrt(max(1, left_power * right_power))

    best_offset = best_correlation = None
    for offset in range(-rate // 50, rate // 50 + 1, 8):
        score = correlation(offset, 16)
        if score is not None and (best_correlation is None or score > best_correlation):
            best_offset, best_correlation = offset, score
    require(best_offset is not None and best_correlation is not None,
            "M5 loop correlation search produced no candidate")
    for offset in range(best_offset - 8, best_offset + 9):
        score = correlation(offset, 4)
        if score is not None and score > best_correlation:
            best_offset, best_correlation = offset, score
    repeat_start = expected + best_offset
    repeated_energy = sum(
        value * value for value in samples[repeat_start:repeat_start + window_length]
    ) // window_length
    return {
        "loop_ticks": loop_ticks,
        "nominal_loop_seconds": loop_ticks / 125,
        "nominal_shift_samples": nominal_shift,
        "clock_corrected_shift_samples": clock_corrected_shift,
        "clock_corrected_seconds": round(clock_corrected_shift / rate, 6),
        "best_shift_samples": clock_corrected_shift + best_offset,
        "best_shift_seconds": round((clock_corrected_shift + best_offset) / rate, 6),
        "correlation": round(best_correlation, 6),
        "repeat_window_mean_square": repeated_energy,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--build-report", type=Path, default=DEFAULT_BUILD_REPORT)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44005)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    build_report_path = args.build_report.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(build_report_path.is_file(), f"music build report not found: {build_report_path}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    build_report = json.loads(build_report_path.read_text(encoding="utf-8"))
    if build_report.get("schema") == "same_monkey_v5_tad_m5_v1":
        compiled_song_id = build_report.get("compiled_song_id")
        loop = build_report.get("loop")
    elif build_report.get("schema") == "same_music_build_report_v1":
        catalog_path = build_report_path.with_name("catalog.json")
        require(catalog_path.is_file(), "M7 compiled catalog is missing")
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        entry = next(
            (item for item in catalog.get("entries", ()) if item.get("logical_id") == 154),
            None,
        )
        require(entry is not None, "M7 compiled catalog has no Monkey cue 154")
        compiled_song_id = entry.get("compiled_song_id")
        loop = entry.get("loop")
    else:
        raise GateFailure("music build report schema differs")
    require(compiled_song_id == 26, "compiled song ID differs")
    require(isinstance(loop, list) and len(loop) == 2 and loop[0] < loop[1],
            "M5 build loop is invalid")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"monkey-m5-tad-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    wav_path = output / "monkey-m5-church-tad.wav"
    baseline_path = output / "tad-blank-baseline.wav"
    report: dict[str, object] = {
        "gate": "M5-generic-sampled-TAD", "result": "running",
        "rom": str(rom), "rom_sha256": rom_hash, "fresh_power_on": True,
        "logical_sound_id": 154, "compiled_song_id": 26,
        "capture_frames": CAPTURE_FRAMES,
        "build_report_sha256": hashlib.sha256(build_report_path.read_bytes()).hexdigest(),
    }
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    try:
        with mcp_session.McpSession(
            rom=rom, mesen=nexen, cwd=ROOT, port=args.port, boot_wait=2.0,
            socket_timeout=90.0, stderr_log=output / "nexen-stderr.log",
        ) as session:
            session.pause()
            session.tool("reset_emulator", {"power": True})
            session.pause()
            ready_timeline = []
            for frame in range(300):
                step = session.run_frames(1)
                require(step["framesAdvanced"] == 1 and not step["timedOut"],
                        "M5 TAD boot frame timed out")
                state = tad_state(session)
                ready_timeline.append({"video_frame": frame + 1, **state})
                if state["state"] == 0x82 and state["ready"] == 1:
                    break
            else:
                raise GateFailure(f"M5 TAD did not reach PLAYING: {ready_timeline[-1]}")
            session.record_audio(baseline_path)
            run_exact_frames(session, 30, "M5 blank baseline")
            session.stop_audio()
            baseline = wav_evidence(baseline_path)
            start_video = session.get_state()["frameCount"]
            start_counter = u16(session.read_memory("snesMemory", 0x7E2210, 2), 0)
            session.record_audio(wav_path)
            # Exercise M6's generated logical-resource catalog, not the
            # debugger's direct compiled-song fallback.
            session.write_u8(0x7E225D, 154)
            run_exact_frames(session, CAPTURE_FRAMES, "M5 loop capture")
            session.stop_audio()
            end_video = session.get_state()["frameCount"]
            end_counter = u16(session.read_memory("snesMemory", 0x7E2210, 2), 0)
            final = tad_state(session)
            audio = wav_evidence(wav_path)
            loop_proof = loop_evidence(wav_path, loop[1] - loop[0])
            require(final["state"] == 0x82 and final["ready"] == 1
                    and final["next_song"] == 26 and final["rejected"] == 0,
                    f"M5 TAD playback state differs: {final}")
            require(audio["peak"] > 0 and audio["peak"] < 32767,
                    f"M5 capture is silent or clipped: {audio}")
            require(audio["mean_square"] > int(baseline["mean_square"]) * 4 + 100,
                    f"M5 energy does not exceed blank output: {baseline} / {audio}")
            require(loop_proof["repeat_window_mean_square"] > 100,
                    f"M5 repeated loop window is silent: {loop_proof}")
            require(loop_proof["correlation"] > 0.99,
                    f"M5 repeated loop window is unstable: {loop_proof}")
            require(end_video - start_video == CAPTURE_FRAMES
                    and (end_counter - start_counter) & 0xFFFF == CAPTURE_FRAMES,
                    "M5 playback changed video/NMI pacing")
            report.update({
                "result": "pass", "ready_timeline": ready_timeline,
                "final_tad_state": final, "blank_audio": baseline,
                "audio": audio, "loop_evidence": loop_proof,
                "video_frames": end_video - start_video,
                "same_frame_counter_delta": (end_counter - start_counter) & 0xFFFF,
            })
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        if wav_path.exists():
            try:
                report["audio"] = wav_evidence(wav_path)
            except Exception:
                pass
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"M5 generic sampled TAD: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"M5 generic sampled TAD: PASS ({rom_hash})")
    print(report_path)
    print(hashlib.sha256(report_path.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
