#!/usr/bin/env python3
"""Capture listener-facing Fate instrument auditions from the real SNES DSP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import wave

from fate_audition_pitch import PITCH_SCHEDULES, validate_capture_pitch


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "build/same-scumm-v5.sfc"
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
AUDITIONS = (
    (2, "r5_01_organ_reset_loop", "filter-reset exact-period source; C2, A3, D4, C5 sustains"),
    (4, "r5_02_flute_reset_zones", "filter-reset low/mid/high sustains and exact seams"),
    (5, "r5_03_pad_reset_zones", "filter-reset C2, G3, B4; B4/C5 seam; upper sustains"),
)
VERDICTS = (
    "pass", "wrong timbre", "low strained", "high strained",
    "transition audible", "out of tune", "bad loop", "attack/tail problem",
)


class CaptureFailure(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise CaptureFailure(message)


def u16(raw: bytes, offset: int) -> int:
    return raw[offset] | raw[offset + 1] << 8


def tad_state(session: object) -> dict[str, int]:
    raw = session.read_memory("snesMemory", 0x7E2250, 16)
    return {
        "state": raw[0], "next_song": raw[7], "rejected": raw[12],
        "ready": raw[15], "transfer_offset": u16(raw, 2),
        "transfer_size": u16(raw, 4),
    }


def trim_capture(source: Path, destination: Path) -> dict[str, object]:
    with wave.open(str(source), "rb") as audio:
        params = audio.getparams()
        require(params.sampwidth == 2, "Nexen capture is not signed 16-bit PCM")
        raw = audio.readframes(params.nframes)
    channels, rate = params.nchannels, params.framerate
    first = last = None
    peak = energy = samples = 0
    for frame in range(params.nframes):
        audible = False
        for channel in range(channels):
            offset = (frame * channels + channel) * 2
            value = int.from_bytes(raw[offset:offset + 2], "little", signed=True)
            peak = max(peak, abs(value))
            energy += value * value
            samples += 1
            audible |= abs(value) > 8
        if audible:
            first = frame if first is None else first
            last = frame
    require(first is not None and last is not None and peak > 0, f"silent audition: {source.name}")
    require(params.nframes - last > rate // 2,
            f"audition capture ends before trailing silence: {source.name}")
    padding = rate // 4
    first = max(0, first - padding)
    last = min(params.nframes, last + padding + 1)
    pcm = raw[first * channels * 2:last * channels * 2]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm)
    return {
        "file": destination.name,
        "channels": channels,
        "sample_rate": rate,
        "frames": last - first,
        "seconds": round((last - first) / rate, 3),
        "peak": peak,
        "mean_square": energy // max(1, samples),
        "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
        "raw_file": str(source.relative_to(destination.parent)),
    }


def write_review(path: Path, rom_hash: str, captures: list[dict[str, object]]) -> None:
    lines = [
        "# Fate S6 isolated instrument review — round 5", "",
        f"ROM SHA-256: `{rom_hash}`", "",
        "Listen on headphones if practical. Check every applicable verdict and add a timestamp/short note.", "",
    ]
    for capture in captures:
        lines += [
            f"## {capture['file']}", "", str(capture["sequence"]), "",
            *(f"- [ ] {verdict}" for verdict in VERDICTS),
            "- Notes:", "", "---", "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=43993)
    parser.add_argument("--capture-frames", type=int, default=2400)
    parser.add_argument("--spc-sample-rate", type=float, default=32040.0,
                        help="Nexen SPC clock, including its configured adjustment")
    parser.add_argument("--pitch-tolerance-cents", type=float, default=3.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    require(600 <= args.capture_frames <= 2400, "capture frames must be in 600..2400")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"fate-instrument-auditions-round5-{rom_hash[:16]}").resolve()
    raw_dir = output / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C42-Fate-instrument-auditions-round5", "result": "running",
        "rom": str(rom), "rom_sha256": rom_hash, "captures": [],
        "pitch_gate": {
            "spc_sample_rate": args.spc_sample_rate,
            "tolerance_cents": args.pitch_tolerance_cents,
            "reference": "equal temperament, A4=440 Hz, adjusted from TAD's 32000 Hz reference",
        },
        "verdict_vocabulary": list(VERDICTS),
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
            for _ in range(240):
                step = session.run_frames(1)
                require(step["framesAdvanced"] == 1 and not step["timedOut"], "TAD boot timed out")
                state = tad_state(session)
                if state["state"] == 0x82 and state["ready"] == 1:
                    break
            else:
                raise CaptureFailure(f"TAD audition pool did not become ready: {state}")

            captures: list[dict[str, object]] = []
            for song_id, name, sequence in AUDITIONS:
                session.write_u8(0x7E225D, song_id)
                for _ in range(30):
                    step = session.run_frames(1)
                    require(step["framesAdvanced"] == 1 and not step["timedOut"], f"song {song_id} load timed out")
                    state = tad_state(session)
                    if state["state"] == 0x82 and state["next_song"] == song_id:
                        break
                else:
                    raise CaptureFailure(f"song {song_id} did not reach playing state: {state}")
                require(state["rejected"] == 0, f"song {song_id} request was rejected: {state}")

                raw_path = raw_dir / f"{name}.wav"
                session.record_audio(raw_path)
                start_counter = u16(session.read_memory("snesMemory", 0x7E2210, 2), 0)
                run = session.run_frames(args.capture_frames)
                end_counter = u16(session.read_memory("snesMemory", 0x7E2210, 2), 0)
                session.stop_audio()
                require(run["framesAdvanced"] == args.capture_frames and not run["timedOut"],
                        f"song {song_id} capture timed out")
                require((end_counter - start_counter) & 0xFFFF == args.capture_frames,
                        f"song {song_id} changed SAME frame pacing")
                evidence = trim_capture(raw_path, output / f"{name}.wav")
                pitch = validate_capture_pitch(
                    output / f"{name}.wav", PITCH_SCHEDULES[name],
                    spc_sample_rate=args.spc_sample_rate,
                    tolerance_cents=args.pitch_tolerance_cents,
                )
                evidence.update({"song_id": song_id, "sequence": sequence,
                                 "video_frames": args.capture_frames,
                                 "pitch": pitch})
                captures.append(evidence)
                failed_notes = [note for note in pitch if note["result"] != "pass"]
                require(not failed_notes, f"song {song_id} pitch gate failed: {failed_notes}")
            report["captures"] = captures
            report["result"] = "pass"
            write_review(output / "REVIEW.md", rom_hash, captures)
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C42 Fate auditions: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1

    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"C42 Fate auditions: PASS ({len(report['captures'])} isolated captures)")
    print(output / "REVIEW.md")
    print(report_path)
    print(hashlib.sha256(report_path.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
