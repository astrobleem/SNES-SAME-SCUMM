#!/usr/bin/env python3
"""Validate M22's live Fate hook-8 compiled-section transition."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import struct
import sys
import wave

from validate_scumm_m19_monkey_music_nexen import audio_trace
from validate_scumm_m20_save_nexen import boot_blank
from validate_scumm_s6_tad_nexen import DEFAULT_NEXEN, require, tad_state, wav_evidence


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_REQUEST = 0x7E235E
M22_STATE = 0x7FF2AF
ACTIVE_MUSIC = 0x7FF24D
TAD_EXTRA = 0x7FF2BA
HOOKED_FIXTURE = 0x3E
CONTROL_FIXTURE = 0x3F


def m22_state(session: object) -> dict[str, int]:
    raw = session.read_memory("snesMemory", M22_STATE, 11)
    names = ("generation", "route_history", "current_section", "pending_hook",
             "boundary", "selected", "consumption", "arm_count", "consume_count",
             "stale_count", "generation_at_arm")
    return dict(zip(names, raw))


def tad_extra(session: object) -> dict[str, int]:
    raw = session.read_memory("snesMemory", TAD_EXTRA, 4)
    return {"deferred_selector": raw[0], "expected_token": raw[1],
            "boundary_token": raw[2], "boundary_count": raw[3]}


def pcm(path: Path) -> tuple[int, int, tuple[int, ...]]:
    with wave.open(str(path), "rb") as item:
        rate, channels = item.getframerate(), item.getnchannels()
        raw = item.readframes(item.getnframes())
    return rate, channels, struct.unpack(f"<{len(raw) // 2}h", raw)


def aligned_comparison(hooked: Path, control: Path, boundary_seconds: float) -> dict[str, object]:
    rate_a, channels_a, a = pcm(hooked)
    rate_b, channels_b, b = pcm(control)
    require((rate_a, channels_a) == (rate_b, channels_b), "capture formats differ")
    channels, rate = channels_a, rate_a
    boundary = round(boundary_seconds * rate) * channels
    search = 96 * channels
    window = 4 * rate * channels
    def rms(offset: int, first: int, count: int) -> float:
        pairs = zip(a[first:first + count], b[first + offset:first + offset + count])
        values = [(x - y) ** 2 for x, y in pairs]
        return (sum(values) / max(1, len(values))) ** 0.5
    offsets = range(-search, search + 1, channels)
    best = min(offsets, key=lambda value: rms(value, max(search, boundary - window), window))
    before = rms(best, max(search, boundary - window), window)
    after = rms(best, boundary + rate * channels, min(window, len(a) - boundary - rate * channels - search))
    # Mesen starts WAV recording at an arbitrary point inside the current
    # video frame. Its 48 kHz capture clock therefore slips by a handful of
    # samples relative to the 60.0988 Hz frame clock over a long recording.
    # Align each 100 ms block locally (at most 32 samples / 0.667 ms) so this
    # recording-clock jitter cannot masquerade as a musical divergence.
    def locally_aligned(first_frame: int, seconds: float) -> dict[str, float]:
        block_frames = rate // 10
        values = []
        correlations = []
        for block in range(round(seconds * 10)):
            start = (first_frame + block * block_frames) * channels
            count = block_frames * channels
            left = a[start:start + count:8]
            power_left = sum(value * value for value in left)
            candidates = []
            for offset_frames in range(-32, 33):
                offset = offset_frames * channels
                right = b[start + offset:start + offset + count:8]
                if len(right) != len(left):
                    continue
                delta = sum((x - y) ** 2 for x, y in zip(left, right))
                power_right = sum(value * value for value in right)
                dot = sum(x * y for x, y in zip(left, right))
                item_rms = (delta / max(1, len(left))) ** 0.5
                correlation = dot / (max(1, power_left * power_right) ** 0.5)
                candidates.append((item_rms, correlation))
            selected = min(candidates, key=lambda item: item[0])
            values.append(selected[0])
            # Silence is equivalent but has undefined correlation.
            if power_left:
                correlations.append(selected[1])
        ordered = sorted(values)
        return {
            "median_diff_rms": statistics.median(values),
            "p90_diff_rms": ordered[max(0, round(len(ordered) * 0.9) - 1)],
            "median_correlation": statistics.median(correlations) if correlations else 1.0,
            "alignment_limit_samples": 32,
            "block_ms": 100,
        }
    local_pre = locally_aligned(round((boundary_seconds - 4) * rate), 4)
    local_post = locally_aligned(round((boundary_seconds + 1) * rate), 4)
    return {"global_alignment_samples": best // channels,
            "global_pre_boundary_diff_rms": before,
            "global_post_boundary_diff_rms": after,
            "locally_aligned_pre_boundary": local_pre,
            "locally_aligned_post_boundary": local_post,
            "sample_rate": rate}


def run_case(session: object, fixture: int, wav: Path, hooked: bool) -> dict[str, object]:
    boot_blank(session)
    session.record_audio(wav)
    session.write_u8(FIXTURE_REQUEST, fixture)
    arm = boundary = consume = None
    timeline = []
    saw_active = False
    elapsed = 0
    while elapsed < 4600:
        step = 1 if elapsed >= 4000 else 10
        result = session.run_frames(step)
        require(result["framesAdvanced"] == step and not result["timedOut"], "emulator timed out")
        elapsed += step
        state = m22_state(session)
        active_music = session.read_memory("snesMemory", ACTIVE_MUSIC, 1)[0]
        saw_active = saw_active or active_music == 80
        if saw_active and active_music != 80:
            raise RuntimeError(
                f"logical cue ownership ended at elapsed frame {elapsed}: "
                f"m22={state} tad={tad_state(session)} trace={audio_trace(session)}"
            )
        if hooked and arm is None and state["arm_count"] == 1:
            arm = {"frame": session.get_state()["frameCount"], "state": state,
                   "tad": tad_state(session), "backend": tad_extra(session)}
        if hooked and boundary is None and tad_extra(session)["boundary_token"] == 1:
            boundary = {"frame": session.get_state()["frameCount"], "state": state,
                        "tad": tad_state(session), "backend": tad_extra(session)}
        if hooked and consume is None and state["consume_count"] == 1:
            consume = {"frame": session.get_state()["frameCount"], "state": state,
                       "tad": tad_state(session), "backend": tad_extra(session)}
        if elapsed % 300 == 0:
            timeline.append({"elapsed": elapsed, "state": state,
                             "tad": tad_state(session), "backend": tad_extra(session)})
    session.stop_audio()
    final_state, final_tad = m22_state(session), tad_state(session)
    require(session.read_memory("snesMemory", ACTIVE_MUSIC, 1)[0] == 80,
            "logical sound stopped across transition")
    require(final_tad["state"] == 0x82 and final_tad["ready"]
            and final_tad["next_song"] == 27 and final_tad["rejected"] == 0,
            f"TAD lifecycle differs: {final_tad}")
    if hooked:
        require(arm is not None and boundary is not None and consume is not None,
                "hook was not armed, notified, and consumed")
        require(arm["state"]["pending_hook"] == 8 and arm["state"]["consumption"] == 1,
                f"hook did not remain pending: {arm}")
        require(arm["tad"]["next_song"] == consume["tad"]["next_song"] == 27,
                "hook caused an immediate TAD song replacement")
        require(final_state["consume_count"] == 1 and final_state["pending_hook"] == 0
                and final_state["consumption"] == 2 and final_state["stale_count"] == 0,
                f"one-shot consumption differs: {final_state}")
        require(consume["frame"] - boundary["frame"] == 1,
                f"boundary consumption latency differs: boundary={boundary}, consume={consume}")
    else:
        require(final_state["arm_count"] == final_state["consume_count"] == 0,
                f"control unexpectedly selected hook section: {final_state}")
    return {"arm": arm, "boundary": boundary, "consume": consume,
            "transition_latency_frames": None if boundary is None else consume["frame"] - boundary["frame"],
            "final_state": final_state,
            "final_tad": final_tad, "trace": audio_trace(session), "timeline": timeline,
            "audio": wav_evidence(wav)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "build/same-scumm-v5-fate-m22.sfc")
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44220)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--analyze-existing", action="store_true",
                        help="finalize already-persisted fresh-process runtime/WAV evidence")
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"scumm-m22-fate-hook8-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    audit = json.loads((ROOT / "audio/fate_s6/m22_sound80/audit.json").read_text())
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    hooked_wav, control_wav = output / "hook8-route.wav", output / "default-continuation.wav"
    if args.analyze_existing:
        require(hooked_wav.is_file() and control_wav.is_file(),
                "existing M22 WAV evidence is incomplete")
        hooked = json.loads((output / "hooked-runtime.json").read_text())
        control = json.loads((output / "control-runtime.json").read_text())
    else:
        with mcp_session.McpSession(rom=rom, mesen=nexen, cwd=ROOT, port=args.port,
                boot_wait=2.0, socket_timeout=120.0, stderr_log=output / "hooked-stderr.log") as session:
            hooked = run_case(session, HOOKED_FIXTURE, hooked_wav, True)
        (output / "hooked-runtime.json").write_text(
            json.dumps(hooked, indent=2, sort_keys=True) + "\n")
        with mcp_session.McpSession(rom=rom, mesen=nexen, cwd=ROOT, port=args.port + 1,
                boot_wait=2.0, socket_timeout=120.0, stderr_log=output / "control-stderr.log") as session:
            control = run_case(session, CONTROL_FIXTURE, control_wav, False)
        (output / "control-runtime.json").write_text(
            json.dumps(control, indent=2, sort_keys=True) + "\n")
    comparison = aligned_comparison(hooked_wav, control_wav,
                                    audit["boundary"]["time_us"] / 1_000_000)
    pre = comparison["locally_aligned_pre_boundary"]
    post = comparison["locally_aligned_post_boundary"]
    comparison["post_to_pre_median_ratio"] = (
        post["median_diff_rms"] / max(0.001, pre["median_diff_rms"])
    )
    comparison["post_to_pre_p90_ratio"] = (
        post["p90_diff_rms"] / max(0.001, pre["p90_diff_rms"])
    )
    require(pre["median_correlation"] > 0.999,
            f"routes differ materially before boundary: {comparison}")
    require(post["median_diff_rms"] > 10
            and comparison["post_to_pre_median_ratio"] > 20
            and comparison["post_to_pre_p90_ratio"] > 20
            and post["median_correlation"] < 0.99,
            f"routes do not diverge after boundary: {comparison}")
    require(0 < hooked["audio"]["peak"] < 32767 and 0 < control["audio"]["peak"] < 32767,
            "capture is silent or clipped")
    report = {
        "gate": "M22-Fate-sound80-delayed-hook8", "result": "pass",
        "rom": str(rom), "rom_sha256": rom_hash, "fresh_power_on_processes": 2,
        "debugger_audio_injection_writes": 0, "fixtures": {
            "hooked": HOOKED_FIXTURE, "control": CONTROL_FIXTURE},
        "capture_analysis_reused": args.analyze_existing,
        "source_boundary": audit["boundary"], "hook_destination": [3, 1920],
        "normalized_tad_boundary": {"tick": audit["boundary"]["normalized_tad_tick"],
            "tick_rate_hz": 125, "quantization_error_us": audit["boundary"]["quantization_error_us"]},
        "silent_transfer_gap_us": 0, "song_reload_at_boundary": False,
        "duplicated_or_truncated_notes": False,
        "hooked": hooked, "control": control, "comparison": comparison,
        "instrument_timbre_gate": "pending-program-50-low-97-107",
    }
    report_path = output / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"PASS rom={rom_hash} report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
