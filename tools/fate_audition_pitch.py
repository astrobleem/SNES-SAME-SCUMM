#!/usr/bin/env python3
"""Measure known sustained notes in Fate's real-DSP audition captures.

The estimator deliberately searches near an expected note instead of trying to
identify arbitrary music. That makes harmonic-rich SCUMM timbres tractable and
turns octave, zone, or tuning mistakes into a deterministic build gate.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import struct
import wave


@dataclass(frozen=True)
class ExpectedNote:
    label: str
    start_seconds: float
    frequency: float


PITCH_SCHEDULES: dict[str, tuple[ExpectedNote, ...]] = {
    "r5_01_organ_reset_loop": (
        ExpectedNote("C2", 0.250, 65.406391),
        ExpectedNote("A3", 3.706, 220.000000),
        ExpectedNote("D4", 7.162, 293.664768),
        ExpectedNote("C5", 10.618, 523.251131),
    ),
    "r5_02_flute_reset_zones": (
        ExpectedNote("G3 low", 0.250, 195.997718),
        ExpectedNote("D#4 low", 3.706, 311.126984),
        ExpectedNote("A4 mid", 9.466, 440.000000),
        ExpectedNote("B5 mid", 12.922, 987.766603),
        ExpectedNote("C6 high", 18.682, 1046.502261),
        ExpectedNote("G6 high", 22.138, 1567.981744),
    ),
    "r5_03_pad_reset_zones": (
        ExpectedNote("C2 low", 0.250, 65.406391),
        ExpectedNote("G3 low", 3.130, 195.997718),
        ExpectedNote("B4 low", 6.010, 493.883301),
        ExpectedNote("C5 high", 11.194, 523.251131),
        ExpectedNote("G5 high", 14.074, 783.990872),
        ExpectedNote("C6 high", 16.954, 1046.502261),
    ),
}


def read_mono_wave(path: Path) -> tuple[int, list[float]]:
    with wave.open(str(path), "rb") as source:
        if source.getsampwidth() != 2:
            raise ValueError(f"{path} is not signed 16-bit PCM")
        rate = source.getframerate()
        channels = source.getnchannels()
        raw = source.readframes(source.getnframes())
    values = struct.unpack(f"<{len(raw) // 2}h", raw)
    mono = [sum(values[i:i + channels]) / channels
            for i in range(0, len(values), channels)]
    return rate, mono


def measure_expected_pitch(
    samples: list[float], sample_rate: int, start_seconds: float,
    expected_frequency: float,
) -> tuple[float, float]:
    """Return (frequency, correlation) for a known sustained note."""
    decimation = 4 if expected_frequency < 700.0 else 1
    start = int((start_seconds + 0.35) * sample_rate)
    end = int((start_seconds + 0.85) * sample_rate)
    window = samples[start:end:decimation]
    if len(window) < 256:
        raise ValueError("pitch-analysis window is outside the capture")
    mean = sum(window) / len(window)
    window = [value - mean for value in window]
    rate = sample_rate / decimation
    expected_lag = rate / expected_frequency
    low = max(2, int(expected_lag * 0.92))
    high = min(len(window) // 3, int(expected_lag * 1.08) + 1)
    correlations: list[float] = []
    for lag in range(low, high + 1):
        count = len(window) - lag
        numerator = sum(window[i] * window[i + lag] for i in range(count))
        left_energy = sum(window[i] * window[i] for i in range(count))
        right_energy = sum(window[i + lag] * window[i + lag] for i in range(count))
        denominator = math.sqrt(left_energy * right_energy)
        correlations.append(numerator / denominator if denominator else 0.0)
    if len(correlations) < 3:
        raise ValueError("pitch-analysis lag range is empty")
    peak = max(range(1, len(correlations) - 1), key=correlations.__getitem__)
    lag = low + peak
    left, center, right = correlations[peak - 1:peak + 2]
    curvature = left - 2.0 * center + right
    correction = 0.5 * (left - right) / curvature if curvature else 0.0
    return rate / (lag + correction), center


def validate_capture_pitch(
    path: Path, schedule: tuple[ExpectedNote, ...], *,
    spc_sample_rate: float = 32040.0, tolerance_cents: float = 3.0,
) -> list[dict[str, object]]:
    rate, samples = read_mono_wave(path)
    clock_ratio = spc_sample_rate / 32000.0
    results: list[dict[str, object]] = []
    for note in schedule:
        expected = note.frequency * clock_ratio
        observed, correlation = measure_expected_pitch(
            samples, rate, note.start_seconds, expected,
        )
        cents = 1200.0 * math.log2(observed / expected)
        passed = abs(cents) <= tolerance_cents and correlation >= 0.75
        results.append({
            "note": note.label,
            "nominal_hz": round(note.frequency, 6),
            "clock_adjusted_expected_hz": round(expected, 6),
            "observed_hz": round(observed, 6),
            "error_cents": round(cents, 3),
            "correlation": round(correlation, 6),
            "result": "pass" if passed else "fail",
        })
    return results
