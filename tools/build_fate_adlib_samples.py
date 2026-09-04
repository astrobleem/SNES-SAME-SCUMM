#!/usr/bin/env python3
"""Build compact loop-safe sound-154 sources from independent Nuked captures."""

from __future__ import annotations

import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct
import wave


ROOT = Path(__file__).resolve().parents[1]
RATE_IN = 44_100
RATE_OUT = 32_000
# name, patch capture, scale-note index (C2..C6), root frequency, octave bounds
JOBS = (
    ("fate154_ch1_low", 1, 0, 65.406391, 2, 2),
    ("fate154_ch1_high", 1, 3, 523.251131, 4, 5),
    ("fate154_ch2_mid", 2, 2, 261.625565, 3, 4),
    ("fate154_ch4_mid", 3, 2, 261.625565, 3, 4),
    ("fate154_ch5_high", 4, 4, 1046.502261, 5, 6),
    ("fate154_ch6_low", 5, 1, 130.812783, 2, 2),
    ("fate154_ch6_high", 5, 3, 523.251131, 4, 5),
)
PATCH_CHANNELS = (1, 2, 4, 5, 6)


def read_raw(path: Path) -> list[float]:
    samples = array("h")
    samples.frombytes(path.read_bytes())
    if len(samples) % 2:
        raise ValueError(f"{path} is not stereo signed-16 PCM")
    return [(samples[i] + samples[i + 1]) / 2 for i in range(0, len(samples), 2)]


def first_audible(samples: list[float], threshold: float = 16.0) -> int:
    try:
        return next(i for i, value in enumerate(samples) if abs(value) > threshold)
    except StopIteration as exc:
        raise ValueError("Nuked capture is silent") from exc


def estimate_note_step(captures: dict[int, list[float]]) -> int:
    starts: list[int] = []
    for patch in (2, 5):
        samples = captures[patch]
        active = [
            max(map(abs, samples[start:start + 441]), default=0) > 16
            for start in range(0, len(samples), 441)
        ]
        onset = [
            index * 441 for index, value in enumerate(active)
            if value and (index == 0 or not active[index - 1])
        ]
        starts.extend(right - left for left, right in zip(onset, onset[1:]))
    if len(starts) < 6:
        raise ValueError("cannot measure the Nuked scale cadence")
    return round(statistics.median(starts))


def resample(values: list[float]) -> list[float]:
    count = round(len(values) * RATE_OUT / RATE_IN)
    output = []
    for index in range(count):
        position = index * RATE_IN / RATE_OUT
        left = min(len(values) - 1, int(position))
        right = min(len(values) - 1, left + 1)
        fraction = position - left
        output.append(values[left] * (1 - fraction) + values[right] * fraction)
    return output


def seam_score(values: list[float], start: int, length: int) -> float:
    width = 64
    left = values[start:start + width]
    right = values[start + length:start + length + width]
    energy = math.sqrt(sum(value * value for value in left + right) / (width * 2))
    if energy < 8:
        return math.inf
    value_error = math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)) / width)
    slope_error = math.sqrt(sum(
        ((left[i] - left[i - 1]) - (right[i] - right[i - 1])) ** 2
        for i in range(1, width)
    ) / (width - 1))
    # Prefer longer loops when seams are otherwise comparable; they retain the
    # slow OPL modulation that one-period samples erase.
    return (value_error + slope_error * 0.5) / energy + 0.02 * (4096 - length) / 2048


def choose_loop(values: list[float]) -> tuple[list[int], int, float]:
    best: tuple[float, int, int] | None = None
    maximum_start = min(len(values) - 4096 - 64, 6400)
    for start in range(0, maximum_start + 1, 16):
        for length in range(2048, 4097, 16):
            if start + length + 64 > len(values):
                break
            score = seam_score(values, start, length)
            if best is None or score < best[0]:
                best = score, start, length
    if best is None:
        raise ValueError("no BRR-aligned loop candidate")
    score, start, length = best
    selected = values[start:start + length]
    mean = sum(selected) / len(selected)
    selected = [value - mean for value in selected]
    peak = max(map(abs, selected))
    if peak < 8:
        raise ValueError("selected loop is silent")
    scale = 26000 / peak
    return [max(-32768, min(32767, round(v * scale))) for v in selected], start, score


def write_wave(path: Path, samples: list[int]) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE_OUT)
        output.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def add_phase_correct_attack(loop: list[int], prefix_samples: int = 256) -> list[int]:
    if prefix_samples % 16 or len(loop) < prefix_samples:
        raise ValueError("attack prefix must be BRR aligned and fit inside the loop")
    # Copy the waveform immediately preceding the loop point, fading it up from
    # zero. The final prefix samples therefore establish nearly the same BRR
    # predictor history as the end of every subsequent loop iteration.
    prefix = [
        round(loop[len(loop) - prefix_samples + index] * (index + 1) / prefix_samples)
        for index in range(prefix_samples)
    ]
    return prefix + loop


def patch_fingerprints(path: Path) -> dict[int, str]:
    raw = path.read_bytes()
    if len(raw) % 31:
        raise ValueError(f"{path} is not a sequence of channel + 30-byte patches")
    patches = {raw[offset]: raw[offset + 1:offset + 31]
               for offset in range(0, len(raw), 31)}
    missing = set(PATCH_CHANNELS) - set(patches)
    if missing:
        raise ValueError(f"{path} is missing AdLib channels {sorted(missing)}")
    return {channel: hashlib.sha256(patches[channel]).hexdigest()
            for channel in PATCH_CHANNELS}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument(
        "--patch-records", type=Path,
        default=Path("/home/chad/fate154-adlib-patches.bin"),
    )
    parser.add_argument("--output", type=Path, default=ROOT / "audio/fate_s6/samples")
    args = parser.parse_args()
    captures = {
        patch: read_raw(args.captures / f"patch{patch}.raw")
        for patch in range(1, 6)
    }
    fingerprints = patch_fingerprints(args.patch_records)
    step = estimate_note_step(captures)
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for name, patch, note_index, frequency, first_octave, last_octave in JOBS:
        source = captures[patch]
        onset = first_audible(source) + note_index * step
        window = source[onset + round(0.25 * RATE_IN):onset + round(0.90 * RATE_IN)]
        loop, loop_start, score = choose_loop(resample(window))
        path = args.output / f"{name}.wav"
        source = add_phase_correct_attack(loop)
        write_wave(path, source)
        records.append({
            "name": name, "patch": patch, "scale_note_index": note_index,
            "patch_sha256": fingerprints[PATCH_CHANNELS[patch - 1]],
            "sample_resource": f"audio/fate_s6/samples/{name}.wav",
            "frequency": frequency, "first_octave": first_octave,
            "last_octave": last_octave, "note_step_frames": step,
            "root_pitch": round(69 + 12 * math.log2(frequency / 440.0)),
            "first_pitch": (first_octave + 1) * 12,
            "last_pitch": (last_octave + 2) * 12 - 1,
            "window_loop_start": loop_start, "loop_point": 256,
            "loop_samples": len(loop), "source_samples": len(source),
            "seam_score": round(score, 8),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "review_status": "accepted",
        })
        print(f"{name}: {len(loop)} samples, seam={score:.6f}")
    manifest = args.output / "fate154_adlib_manifest.json"
    bank = {
        "schema": "same_instrument_bank_v1",
        "name": "Fate sound 154 reviewed SCUMM v5 AdLib zones",
        "source_device": "scumm_v5_adlib",
        "capture_velocity": 100,
        "capture_cc7": 127,
        "reference_volume": 96,
        "zones": records,
    }
    manifest.write_text(json.dumps(bank, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
