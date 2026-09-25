#!/usr/bin/env python3
"""Prove the Fate S6 TAD rendition through real S-SMP/DSP execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import wave


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "build/same-scumm-v5-tad.sfc"
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
SOUND_CASES = {
    17: {
        "song_id": 8, "capture_frames": 900,
        "first_audible_range": (4.6, 4.9), "last_audible_range": (13.5, 13.9),
    },
    18: {
        "song_id": 11, "capture_frames": 780,
        "first_audible_range": (2.3, 2.7), "last_audible_range": (11.2, 11.7),
    },
    78: {
        "song_id": 22, "capture_frames": 5280,
        "first_audible_range": (6.1, 6.55), "last_audible_range": (82.7, 83.2),
    },
    81: {
        "song_id": 23, "capture_frames": 1500,
        "first_audible_range": (2.55, 3.0), "last_audible_range": (22.1, 22.55),
    },
    83: {
        "song_id": 10, "capture_frames": 840,
        "first_audible_range": (3.0, 3.3), "last_audible_range": (12.3, 12.7),
    },
    91: {
        "song_id": 20, "capture_frames": 240,
        "first_audible_range": (2.1, 2.5), "last_audible_range": (2.8, 3.2),
    },
    117: {
        "song_id": 21, "capture_frames": 360,
        "first_audible_range": (2.1, 2.5), "last_audible_range": (3.7, 4.2),
    },
    141: {
        "song_id": 15, "capture_frames": 480,
        "first_audible_range": (2.8, 3.2), "last_audible_range": (6.9, 7.4),
    },
    150: {
        "song_id": 25, "capture_frames": 1800,
        "first_audible_range": (3.4, 3.9), "last_audible_range": (21.9, 22.4),
    },
    153: {
        "song_id": 24, "capture_frames": 1920,
        "first_audible_range": (2.9, 3.4), "last_audible_range": (28.1, 28.65),
    },
    154: {
        "song_id": 9, "capture_frames": 840,
        # The ADL oracle's unconditional jump skips the former linear-SMF
        # setup delay. Bounds include TAD transfer/start latency.
        "first_audible_range": (0.35, 0.65), "last_audible_range": (9.7, 10.2),
    },
    172: {"song_id": 1, "capture_frames": 120},
    183: {
        "song_id": 19, "capture_frames": 1140,
        "first_audible_range": (0.2, 0.55), "last_audible_range": (17.6, 18.1),
    },
    185: {
        "song_id": 12, "capture_frames": 120,
        "first_audible_range": (0.4, 0.7), "last_audible_range": (1.4, 1.8),
    },
    190: {
        "song_id": 13, "capture_frames": 90,
        "first_audible_range": (0.2, 0.5), "last_audible_range": (1.0, 1.4),
    },
    192: {
        "song_id": 14, "capture_frames": 90,
        "first_audible_range": (0.25, 0.55), "last_audible_range": (0.85, 1.25),
    },
    201: {
        "song_id": 16, "capture_frames": 360,
        "first_audible_range": (0.2, 0.5), "last_audible_range": (5.3, 5.8),
    },
    202: {
        "song_id": 17, "capture_frames": 360,
        "first_audible_range": (0.2, 0.5), "last_audible_range": (5.3, 5.8),
    },
    207: {
        "song_id": 18, "capture_frames": 120,
        "first_audible_range": (0.2, 0.5), "last_audible_range": (1.6, 1.95),
    },
}


class GateFailure(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise GateFailure(message)


def u16(raw: bytes, offset: int) -> int:
    return raw[offset] | raw[offset + 1] << 8


def tad_state(session: object) -> dict[str, int]:
    raw = session.read_memory("snesMemory", 0x7E2250, 16)
    return {
        "state": raw[0], "previous_command": raw[1],
        "transfer_offset": u16(raw, 2), "transfer_size": u16(raw, 4),
        "spin": raw[6], "next_song": raw[7], "next_command": raw[8],
        "parameter0": raw[9], "parameter1": raw[10],
        "last_command": raw[11], "rejected": raw[12],
        "probe_request": raw[13], "ready": raw[15],
    }


def run_exact_frames(session: object, count: int, label: str) -> None:
    remaining = count
    while remaining:
        chunk = min(300, remaining)
        result = session.run_frames(chunk)
        require(
            result["framesAdvanced"] == chunk and not result["timedOut"],
            f"{label} timed out after {count - remaining} of {count} frames: {result}",
        )
        remaining -= chunk


def wav_evidence(path: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    energy = peak = samples = 0
    first_audible = last_audible = None
    with wave.open(str(path), "rb") as audio:
        require(audio.getsampwidth() == 2, "Nexen audio is not signed 16-bit PCM")
        channels, rate, frames = audio.getnchannels(), audio.getframerate(), audio.getnframes()
        frame_cursor = 0
        while block := audio.readframes(65536):
            digest.update(block)
            frame_bytes = channels * 2
            for frame_offset in range(0, len(block), frame_bytes):
                audible = False
                for index in range(frame_offset, frame_offset + frame_bytes, 2):
                    value = int.from_bytes(block[index:index + 2], "little", signed=True)
                    energy += value * value
                    peak = max(peak, abs(value))
                    samples += 1
                    audible |= abs(value) > 8
                if audible:
                    frame = frame_cursor + frame_offset // frame_bytes
                    first_audible = frame if first_audible is None else first_audible
                    last_audible = frame
            frame_cursor += len(block) // frame_bytes
    return {
        "path": str(path), "sha256": digest.hexdigest(), "channels": channels,
        "sample_rate": rate, "frames": frames, "samples": samples,
        "peak": peak, "mean_square": energy // max(1, samples),
        "first_audible_seconds": (
            None if first_audible is None else round(first_audible / rate, 3)
        ),
        "last_audible_seconds": (
            None if last_audible is None else round(last_audible / rate, 3)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=43989)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sound", type=int, choices=sorted(SOUND_CASES), default=172)
    parser.add_argument("--capture-frames", type=int)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    case = SOUND_CASES[args.sound]
    capture_frames = args.capture_frames or case["capture_frames"]
    require(60 <= capture_frames <= 6000, "capture frames must be in 60..6000")
    output = (args.output or ROOT / "build" / f"scumm-s6-tad-sound{args.sound}-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    wav_path = output / f"fate-sound-{args.sound}-tad.wav"
    baseline_path = output / "tad-blank-baseline.wav"
    report: dict[str, object] = {
        "gate": "S6-TAD", "result": "running", "rom": str(rom),
        "rom_sha256": rom_hash, "rom_size": rom.stat().st_size,
        "sound": args.sound, "tad_song": case["song_id"], "fresh_power_on": True,
    }

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    try:
        with mcp_session.McpSession(
            rom=rom, mesen=nexen, cwd=ROOT, port=args.port, boot_wait=2.0,
            socket_timeout=60.0, stderr_log=output / "nexen-stderr.log",
        ) as session:
            session.pause()
            session.tool("reset_emulator", {"power": True})
            session.pause()
            ready_timeline = []
            # The reviewed audition pool is ~42 KiB and intentionally loads at
            # the conservative 256-byte/frame production transfer budget.
            for frame in range(240):
                step = session.run_frames(1)
                require(step["framesAdvanced"] == 1 and not step["timedOut"], "TAD boot frame timed out")
                state = tad_state(session)
                ready_timeline.append({"video_frame": frame + 1, **state})
                if state["state"] == 0x82 and state["ready"] == 1:
                    break
            else:
                raise GateFailure(f"TAD did not reach PLAYING: {ready_timeline[-1]}")
            require(state["next_song"] == 0 and state["rejected"] == 0,
                    f"TAD blank-song boot state differs: {state}")

            session.record_audio(baseline_path)
            run_exact_frames(session, 30, "blank baseline capture")
            session.stop_audio()
            baseline = wav_evidence(baseline_path)

            start_video = session.get_state()["frameCount"]
            start_counter = u16(session.read_memory("snesMemory", 0x7E2210, 2), 0)
            session.record_audio(wav_path)
            session.write_u8(0x7E225D, args.sound)
            run_exact_frames(session, capture_frames, "audio capture")
            session.stop_audio()
            end_video = session.get_state()["frameCount"]
            end_counter = u16(session.read_memory("snesMemory", 0x7E2210, 2), 0)
            final = tad_state(session)
            dsp = session.get_audio_state()
            audio = wav_evidence(wav_path)
            require(final["state"] == 0x82 and final["ready"] == 1
                    and final["next_song"] == case["song_id"] and final["rejected"] == 0,
                    f"TAD Fate playback state differs: {final}")
            require(audio["peak"] > 0 and audio["mean_square"] > 0,
                    f"TAD capture contains no sample energy: {audio}")
            require(audio["mean_square"] > int(baseline["mean_square"]) * 4 + 100,
                    f"Fate rendition energy does not exceed blank TAD output: {baseline} / {audio}")
            if "first_audible_range" in case:
                first_low, first_high = case["first_audible_range"]
                last_low, last_high = case["last_audible_range"]
                require(
                    audio["first_audible_seconds"] is not None
                    and first_low <= audio["first_audible_seconds"] <= first_high,
                    f"Fate cue entrance timing differs: {audio}",
                )
                require(
                    audio["last_audible_seconds"] is not None
                    and last_low <= audio["last_audible_seconds"] <= last_high,
                    f"Fate cue tail timing differs: {audio}",
                )
            require(end_video - start_video == capture_frames
                    and (end_counter - start_counter) & 0xFFFF == capture_frames,
                    "TAD playback changed video/NMI frame pacing")
            report.update({
                "result": "pass", "ready_timeline": ready_timeline,
                "final_tad_state": final, "dsp": dsp, "blank_audio": baseline,
                "audio": audio,
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
        print(f"S6 TAD: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"S6 TAD: PASS ({rom_hash})")
    print(report_path)
    print(hashlib.sha256(report_path.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
