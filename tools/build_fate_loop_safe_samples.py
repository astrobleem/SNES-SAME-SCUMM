#!/usr/bin/env python3
"""Build periodic BRR-safe Fate candidates from reviewed MI timbres."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import wave


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "audio/fate_s6/samples"
MANIFEST = SAMPLES / "loop_safe_manifest.json"

# output, source, source loop start, source frequency, exact output period
JOBS = (
    ("mt32_organ_cycle.wav", "mt32_organ.wav", 4800, 330.275, 96),
    ("mt32_p74_cycle.wav", "mt32_p74_low.wav", 3200, 164.948, 192),
    ("mt32_p74_cycle_x2.wav", "mt32_p74_low.wav", 3200, 164.948, 96),
    ("mt32_p74_cycle_x4.wav", "mt32_p74_low.wav", 3200, 164.948, 48),
    ("mt32_p88_cycle.wav", "mt32_p88.wav", 3840, 523.49, 64),
    ("mt32_p88_cycle_x2.wav", "mt32_p88.wav", 3840, 523.49, 32),
)


def load_mono(path: Path) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as source:
        if source.getnchannels() != 1 or source.getsampwidth() != 2:
            raise ValueError(f"{path} is not mono signed-16 PCM")
        rate = source.getframerate()
        raw = source.readframes(source.getnframes())
        data = [float(value) for value in struct.unpack(f"<{len(raw) // 2}h", raw)]
    if rate != 32000:
        raise ValueError(f"{path} is not 32 kHz")
    return data, rate


def averaged_cycle(loop: list[float], cycles: int, period: int) -> list[int]:
    # Sample every source cycle at a shared normalized phase, average away the
    # long-loop chorus/modulation, then retain only harmonics representable by
    # the requested output period. The resulting WAV is one exact period.
    output = [0.0] * period
    source_period = len(loop) / cycles
    for cycle in range(cycles):
        for index in range(period):
            position = (cycle + index / period) * source_period
            left = int(position)
            fraction = position - left
            right = min(left + 1, len(loop) - 1)
            output[index] += loop[left] * (1.0 - fraction) + loop[right] * fraction
    output = [value / cycles for value in output]
    mean = sum(output) / len(output)
    output = [value - mean for value in output]
    peak = max(abs(value) for value in output)
    if peak < 1:
        raise ValueError("phase-averaged source is silent")
    scale = 26000.0 / peak
    return [max(-32768, min(32767, round(value * scale))) for value in output]


def write_wav(path: Path, samples: list[int], rate: int) -> None:
    pcm = struct.pack(f"<{len(samples)}h", *samples)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm)


def main() -> int:
    records = []
    for output_name, source_name, loop_start, source_freq, period in JOBS:
        source_path = SAMPLES / source_name
        data, rate = load_mono(source_path)
        loop = data[loop_start:]
        cycles = round(len(loop) * source_freq / rate)
        if cycles < 1 or period % 16:
            raise ValueError(f"invalid periodic job for {output_name}")
        output_path = SAMPLES / output_name
        write_wav(output_path, averaged_cycle(loop, cycles, period), rate)
        raw = output_path.read_bytes()
        records.append({
            "output": output_name,
            "source": source_name,
            "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "source_loop_start": loop_start,
            "source_cycles_averaged": cycles,
            "period_samples": period,
            "frequency": round(rate / period, 6),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
    MANIFEST.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8", newline="\n")
    for record in records:
        print(f"{record['output']}: {record['period_samples']} samples, {record['frequency']} Hz")
    print(MANIFEST)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
